#!/usr/bin/env python3
"""
cTrader Open API connector — direct phone-side control of cTrader accounts.

Broker: QCG (cTrader platform).  Uses the official Spotware SDK
(`pip install ctrader-open-api`) which speaks:

  * OAuth 2.0  -> https://openapi.ctrader.com/apps/{auth,token}
  * TLS protobuf (length-prefixed) -> live.ctraderapi.com:5035  (or demo.)

Session flow (verified against the Spotware console sample):
    1. TLS connect
    2. ProtoOAApplicationAuthReq(client_id, client_secret)
    3. ProtoOAGetAccountListByAccessTokenReq(access_token)   [optional]
    4. ProtoOAAccountAuthReq(account_id, access_token)
    5. request/response + push events (spot, execution, error, margin)

Unit conventions (cTrader Open API, per official OpenApiMessages.proto):
    - spot prices:  fixed-point, raw = price * 1e5 (PROTOCOL scale —
                    "1/100000 of unit of a price"; NOT the symbol digits
                    field, which is display precision only)
    - bar prices:   Trendbar.low is absolute (same 1e5 scale);
                    open/high/close = low + delta{Open,High,Close}
    - order/position prices in requests & models: plain double
    - relative SL/TP: int64 in 1/100000 of a price (same 1e5 scale)
    - volume:       int64, 1 lot == 100 (0.01-lot granularity); must
                    respect per-symbol minVolume/stepVolume (verify with
                    ProtoOAExpectedMarginReq before placing orders)
    - money:        int64 in smallest currency unit (USD -> cents;
                    divide by 10**money_digits)
    - timestamps:   int64 milliseconds since epoch (except bar
                    utcTimestampInMinutes = minutes since epoch)

Credentials:
    env:  CTRADER_CLIENT_ID, CTRADER_CLIENT_SECRET, CTRADER_REDIRECT_URI,
          CTRADER_ACCESS_TOKEN, CTRADER_REFRESH_TOKEN, CTRADER_ACCOUNT_ID,
          CTRADER_HOST (live|demo)
    file: data/ctrader_credentials.json (chmod 600, git-ignored)
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
import time

try:
    import ctrader_open_api  # noqa: F401
    from ctrader_open_api import Client, Protobuf, TcpProtocol, Auth
    from ctrader_open_api.endpoints import EndPoints
    from ctrader_open_api.messages import OpenApiMessages_pb2 as MSG
    from twisted.internet import reactor
    from twisted.internet.defer import Deferred, CancelledError
    CT_SDK_AVAILABLE = True
    CT_SDK_ERROR = ""
except Exception as _e:  # pragma: no cover - environment dependent
    CT_SDK_AVAILABLE = False
    CT_SDK_ERROR = str(_e)
    EndPoints = None
    Client = None
    TcpProtocol = None
    Auth = None
    Protobuf = None
    MSG = None
    reactor = None
    Deferred = None
    CancelledError = Exception

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CRED_PATH = os.path.join(_HERE, "data", "ctrader_credentials.json")

# ---------------------------------------------------------------------------
# Payload-type / enum constants (mirrors OpenApiMessages.proto)
# ---------------------------------------------------------------------------
PT_ERROR_RES = 2142
PT_EXECUTION_EVENT = 2126
PT_ORDER_ERROR_EVENT = 2132
PT_SPOT_EVENT = 2131

ORDER_TYPE_MARKET = 1
ORDER_TYPE_LIMIT = 2
ORDER_TYPE_STOP = 3
SIDE_BUY = 1
SIDE_SELL = 2
TIF_GTC = 2
TIF_IOC = 3

EXECUTION_TYPE = {
    2: "ORDER_ACCEPTED", 3: "ORDER_FILLED", 4: "ORDER_REPLACED",
    5: "ORDER_CANCELLED", 6: "ORDER_EXPIRED", 7: "ORDER_REJECTED",
    8: "ORDER_CANCEL_REJECTED", 9: "SWAP", 10: "DEPOSIT_WITHDRAW",
    11: "ORDER_PARTIAL_FILL", 12: "BONUS_DEPOSIT_WITHDRAW",
}

PERIOD_SECONDS = {
    "M1": 60, "M2": 120, "M3": 180, "M4": 240, "M5": 300, "M10": 600,
    "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "H12": 43200,
    "D1": 86400, "W1": 604800, "MN1": 2592000,
}
PERIOD_NUM = {
    "M1": 1, "M2": 2, "M3": 3, "M4": 4, "M5": 5, "M10": 6, "M15": 7,
    "M30": 8, "H1": 9, "H4": 10, "H12": 11, "D1": 12, "W1": 13, "MN1": 14,
}


class CTraderError(Exception):
    """cTrader session / request error. .code + .description"""

    def __init__(self, code: str, description: str):
        super().__init__(f"{code}: {description}" if description else code)
        self.code = code
        self.description = description


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------
# Per the official OpenApiMessages.proto (spotware/openapi-proto-messages):
# all fixed-point prices (spot bid/ask, trendbars, relative SL/TP) are
# "specified in 1/100000 of unit of a price" — a PROTOCOL-constant scale,
# NOT the symbol's `digits` field (that is display precision only).
PRICE_SCALE = 100000


def price_raw(price) -> int:
    """float price -> fixed-point int (price * 1e5, protocol scale)."""
    return int(round(float(price) * PRICE_SCALE))


def price_float(raw) -> float:
    """fixed-point int (1e5 scale) -> float price."""
    return int(raw) / PRICE_SCALE


def volume_raw(lots) -> int:
    """lots -> int64 volume (1 lot == 100, 0.01-lot granularity).

    This is the generic convention from the official Spotware sample
    (`int(volume) * 100`).  Brokers with custom contract sizes (e.g. QCG)
    define 1.0 lot = lotSize/100 raw units instead — use
    volume_for_symbol() with the symbol's full spec there.
    """
    return int(round(float(lots) * 100))


def lots_from_raw(raw) -> float:
    return int(raw) / 100.0


def lots_display(raw, spec=None) -> float:
    """Raw volume -> lots for display, honoring the symbol's contract size.

    With a full spec (or joined view) carrying `lotSize`: lots = raw*100/lotSize
    (verified QCG convention: 1.0 lot == lotSize/100 raw units).  Without a
    spec, falls back to the generic 1 lot == 100 raw units.
    """
    if spec is not None:
        ls = int(getattr(spec, "lotSize", 0) or 0)
        if ls > 0:
            return int(raw) * 100.0 / ls
    return int(raw) / 100.0


def volume_for_symbol(lots, spec) -> int:
    """Raw int64 volume for `lots` on a symbol with the given full spec.

    Verified on QCG (all 7 enabled symbols): the `lotSize` field equals
    100 x (raw units per 1.0 lot), so 1.0 lot == lotSize/100 raw units:
        EURUSD lotSize=10,000,000 -> 1 lot = 100,000 units = 10,000 EUR
        BTCUSD lotSize=1,000      -> 1 lot = 10 units = 1 BTC
        ETHUSD lotSize=100,000    -> 1 lot = 1,000 units = 100 ETH
    Check the result against minVolume/stepVolume/maxVolume with
    check_volume() before sending.
    """
    return int(round(float(lots) * int(spec.lotSize) / 100.0))


def check_volume(spec, raw) -> None:
    """Raise CTraderError(BAD_VOLUME) if raw volume breaks min/step/max."""
    mn, st, mx = int(spec.minVolume), int(spec.stepVolume), int(spec.maxVolume)
    problems = []
    if raw < mn:
        problems.append(f"below minVolume {mn}")
    if st > 0 and raw % st != 0:
        problems.append(f"not a multiple of stepVolume {st}")
    if raw > mx:
        problems.append(f"above maxVolume {mx}")
    if problems:
        raise CTraderError(
            "BAD_VOLUME",
            "volume " + str(raw) + " is " + "; ".join(problems))


def money_float(raw, digits) -> float:
    """int64 money (smallest currency unit) -> float."""
    return int(raw) / (10.0 ** int(digits)) if int(digits) else float(int(raw))


def normalize_name(name: str) -> str:
    return re.sub(r"[\s/.]", "", str(name)).upper()


def now_ms() -> int:
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
class TokenStore:
    """Persists OAuth tokens + app credentials in a chmod-600 JSON file."""

    def __init__(self, path: str = None):
        self.path = path or DEFAULT_CRED_PATH

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def load(self) -> dict:
        if not self.exists():
            return {}
        try:
            with open(self.path, "r") as f:
                return json.load(f) or {}
        except Exception:
            return {}

    def save(self, data: dict):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def store_tokens(self, client_id, client_secret, redirect_uri,
                     token_response, account_id=None, is_live=True, extra=None):
        """Merge an OAuth token response into the store."""
        data = self.load()
        data.update({
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "access_token": token_response.get("accessToken"),
            "refresh_token": token_response.get("refreshToken"),
            "token_type": token_response.get("tokenType"),
            "scope": token_response.get("scope"),
        })
        exp = token_response.get("expiresIn")
        if exp:
            data["access_token_expires_at"] = int(time.time()) + int(exp)
        if account_id:
            data["account_id"] = str(account_id)
        if is_live is not None:
            data["host"] = "live" if is_live else "demo"
        if extra:
            data.update(extra)
        self.save(data)
        return data


def resolve_credentials(path: str = None) -> tuple:
    """Merge file store + environment into a credentials dict.

    Returns (creds, TokenStore).  creds keys: client_id, client_secret,
    redirect_uri, access_token, refresh_token, account_id, host,
    access_token_expires_at, missing (list of required-but-absent keys).
    """
    store = TokenStore(path)
    data = store.load()
    env = os.environ
    creds = {
        "client_id": env.get("CTRADER_CLIENT_ID") or data.get("client_id"),
        "client_secret": env.get("CTRADER_CLIENT_SECRET") or data.get("client_secret"),
        "redirect_uri": (env.get("CTRADER_REDIRECT_URI")
                         or data.get("redirect_uri")
                         or "https://my.ctrader.com"),
        "access_token": env.get("CTRADER_ACCESS_TOKEN") or data.get("access_token"),
        "refresh_token": env.get("CTRADER_REFRESH_TOKEN") or data.get("refresh_token"),
        "account_id": env.get("CTRADER_ACCOUNT_ID") or data.get("account_id"),
        "host": (env.get("CTRADER_HOST") or data.get("host") or "live").lower(),
        "access_token_expires_at": int(data.get("access_token_expires_at") or 0),
    }
    creds["missing"] = [k for k in
                        ("client_id", "client_secret", "access_token")
                        if not creds.get(k)]
    return creds, store


def host_for(creds: dict, demo_flag: bool = False) -> tuple:
    host_type = "demo" if demo_flag else creds.get("host", "live")
    if host_type not in ("live", "demo"):
        host_type = "live"
    if not CT_SDK_AVAILABLE or EndPoints is None:
        return host_type, (host_type + ".ctraderapi.com"), 5035
    host = (EndPoints.PROTOBUF_LIVE_HOST if host_type == "live"
            else EndPoints.PROTOBUF_DEMO_HOST)
    return host_type, host, int(EndPoints.PROTOBUF_PORT)


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------
class CTraderAuth:
    """Thin wrapper over the SDK Auth for URL/code/refresh handling."""

    def __init__(self, client_id, client_secret, redirect_uri, scope="trading"):
        if not CT_SDK_AVAILABLE or Auth is None:
            raise CTraderError("SDK_MISSING", CT_SDK_ERROR)
        self.scope = scope
        self._auth = Auth(client_id, client_secret, redirect_uri)

    @staticmethod
    def auth_url(client_id, client_secret, redirect_uri, scope="trading") -> str:
        if not CT_SDK_AVAILABLE or Auth is None:
            raise CTraderError("SDK_MISSING", CT_SDK_ERROR)
        # Canonical URL per cTrader Open API docs
        # (help.ctrader.com/open-api/account-authentication/).
        # `product=web` renders a header/footer-free consent screen, which is
        # what we want on a phone.  Must equal a redirect URI registered on
        # the app in the Open API portal (openapi.ctrader.com/apps).
        from urllib.parse import quote
        return ("https://id.ctrader.com/my/settings/openapi/grantingaccess"
                f"?client_id={quote(client_id, safe='')}"
                f"&redirect_uri={quote(redirect_uri, safe='')}"
                f"&scope={scope}"
                f"&product=web")

    def exchange_code(self, code: str) -> dict:
        token = self._auth.getToken(code)
        if not isinstance(token, dict) or "accessToken" not in token:
            raise CTraderError(
                "OAUTH_ERROR",
                "token exchange failed: " + json.dumps(token)[:300])
        return token

    @staticmethod
    def refresh(client_id, client_secret, refresh_token) -> dict:
        if not CT_SDK_AVAILABLE or Auth is None:
            raise CTraderError("SDK_MISSING", CT_SDK_ERROR)
        token = Auth(client_id, client_secret, "https://my.ctrader.com").refreshToken(refresh_token)
        if not isinstance(token, dict) or "accessToken" not in token:
            raise CTraderError(
                "TOKEN_REFRESH_FAILED",
                "refresh failed: " + json.dumps(token)[:300])
        return token


def ensure_fresh_token(creds: dict, store: TokenStore, force: bool = False) -> dict:
    """Refresh the access token if (near) expiry; persists the new tokens.

    Returns the updated creds dict.  No-op when nothing to refresh.
    """
    if not force and not creds.get("access_token"):
        return creds
    expires_at = creds.get("access_token_expires_at") or 0
    near_expiry = expires_at and (expires_at - 300) < time.time()
    if not (force or near_expiry):
        return creds
    if not (creds.get("client_id") and creds.get("client_secret")
            and creds.get("refresh_token")):
        return creds
    token = CTraderAuth.refresh(
        creds["client_id"], creds["client_secret"], creds["refresh_token"])
    store.store_tokens(
        creds["client_id"], creds["client_secret"], creds.get("redirect_uri"),
        token, account_id=creds.get("account_id"),
        is_live=(creds.get("host") == "live"))
    creds["access_token"] = token.get("accessToken")
    exp = token.get("expiresIn")
    if exp:
        creds["access_token_expires_at"] = int(time.time()) + int(exp)
    return creds


# ---------------------------------------------------------------------------
# Session (Twisted reactor based)
# ---------------------------------------------------------------------------
_REACTOR_USES = {"count": 0}


def _new_reactor():
    """Install a fresh Twisted reactor.

    The default reactor cannot be re-run after stop() within one process
    (twisted.internet.error.ReactorNotRestartable), so every session after
    the first in a long-lived process needs a new instance.  Twisted resolves
    `from twisted.internet import reactor` at runtime in most places, and the
    SDK's captured module reference is patched explicitly.
    """
    global reactor
    import twisted.internet
    new_r = type(reactor)()
    twisted.internet.reactor = new_r
    try:
        import ctrader_open_api.client as _sdk_client_mod
        _sdk_client_mod.reactor = new_r
    except Exception:
        pass
    reactor = new_r
    return new_r


def _check_and_extract(msg):
    """Callback: raise CTraderError on error-res, else extract payload."""
    if CT_SDK_AVAILABLE and msg.payloadType == PT_ERROR_RES:
        e = Protobuf.extract(msg)
        raise CTraderError(e.errorCode or "CH_ERROR", e.description or "cTrader error")
    return Protobuf.extract(msg)


class CTraderSession:
    """One-shot protobuf session: handshake, then run steps under the reactor.

    Usage:
        s = CTraderSession(creds, account_id=..., demo=False)
        results = s.execute([
            lambda s, r: s.trader_info(),
            lambda s, r: s.open_orders(),
        ])
    Each step is ``callable(session, results)`` returning a Deferred or a
    plain value (plain values are auto-wrapped).  results[0] is the handshake
    result; later entries line up with the step list.
    """

    def __init__(self, creds: dict, account_id=None, demo: bool = False,
                 request_timeout: float = 15.0, hard_timeout: float = 90.0,
                 use_default_account: bool = True):
        if not CT_SDK_AVAILABLE:
            raise CTraderError("SDK_MISSING", CT_SDK_ERROR)
        missing = [k for k in ("client_id", "client_secret", "access_token")
                   if not creds.get(k)]
        if missing:
            raise CTraderError("MISSING_CREDENTIALS",
                               "missing: " + ", ".join(missing))
        self.client_id = creds["client_id"]
        self.client_secret = creds["client_secret"]
        self.access_token = creds["access_token"]
        if account_id:
            self.account_id = str(account_id)
        elif use_default_account:
            self.account_id = str(creds.get("account_id") or "") or None
        else:
            # App-level session (e.g. account listing): no account auth.
            self.account_id = None
        host_type, host, port = host_for(creds, demo_flag=demo)
        self.host_type = host_type
        self._host = host
        self._port = port
        self.request_timeout = request_timeout
        self.hard_timeout = hard_timeout

        self.spots = {}          # symbolId -> {bid_raw, ask_raw, ts, trendbar}
        self.executions = []     # ProtoOAExecutionEvent payloads
        self.order_errors = []   # ProtoOAOrderErrorEvent payloads
        self.protocol_errors = []  # ProtoOAErrorRes payloads (unsolicited)
        self._client = None      # created in execute() (reactor-aware)
        self._finished = False

    # -- event plumbing ----------------------------------------------------
    def _on_message(self, client, message):
        pt = message.payloadType
        try:
            if pt == PT_SPOT_EVENT:
                p = Protobuf.extract(message)
                self.spots[p.symbolId] = {
                    "bid_raw": p.bid, "ask_raw": p.ask,
                    "ts": p.timestamp,
                    "trendbar": p.trendbar[0] if len(p.trendbar) else None,
                }
            elif pt == PT_EXECUTION_EVENT:
                self.executions.append(Protobuf.extract(message))
            elif pt == PT_ORDER_ERROR_EVENT:
                self.order_errors.append(Protobuf.extract(message))
            elif pt == PT_ERROR_RES and not message.clientMsgId:
                self.protocol_errors.append(Protobuf.extract(message))
        except Exception:
            pass

    def _on_disconnected(self, client, reason):
        if self._finished:
            return
        self._finished = True
        if hasattr(reason, "value"):
            self._disconnect_reason = str(reason)
        else:
            self._disconnect_reason = str(reason)
        # Surface an error into any in-flight step.
        try:
            self._pending_fail(CTraderError(
                "DISCONNECTED", "connection lost: " + self._disconnect_reason))
        except Exception:
            pass

    # -- low-level send helpers -------------------------------------------
    def _send(self, req, timeout: float = None) -> Deferred:
        return self._client.send(req,
                                 responseTimeoutInSeconds=timeout or self.request_timeout)

    def _ok(self, d: Deferred) -> Deferred:
        """request deferred -> extracted payload, CTraderError on failure."""
        d.addCallback(_check_and_extract)
        d.addErrback(self._translate_failure)
        return d

    def _translate_failure(self, failure):
        """Errback: convert any failure to a CTraderError (raised, not
        returned — returning an exception from an errback would make the
        Deferred *succeed* with it, which is the classic Twisted trap)."""
        exc = getattr(failure, "value", None)
        if isinstance(exc, CTraderError):
            raise exc
        if isinstance(exc, CancelledError):
            raise CTraderError("TIMEOUT", "cTrader request timed out")
        raise CTraderError("REQUEST_ERROR", str(failure.getErrorMessage()))

    def _fire_and_watch(self, req, watch_seconds: float = 6.0) -> Deferred:
        """Send without expecting a response; collect execution events.

        Order placement / cancellation / close are confirmed through
        ProtoOAExecutionEvent (or OrderErrorEvent), not a response message.
        """
        exec_before = len(self.executions)
        d = self._client.whenConnected()

        def on_proto(proto):
            proto.send(req, clientMsgId=None)

        wait_d = Deferred()
        reactor.callLater(watch_seconds, wait_d.callback, None)
        chain = (d.addCallback(on_proto)
                 .addCallback(lambda _p: wait_d)
                 .addCallback(
                     lambda _w: [e for e in self.executions[exec_before:]]))
        chain.addErrback(self._translate_failure)
        return chain

    # -- handshake ----------------------------------------------------------
    def _handshake_step(self, s, _results):
        req = MSG.ProtoOAApplicationAuthReq(
            clientId=self.client_id, clientSecret=self.client_secret)
        d = self._send(req, timeout=10)

        def after_app(_res):
            _check_and_extract_msg(_res)
            if not self.account_id:
                return "app-authenticated"
            acc = MSG.ProtoOAAccountAuthReq(
                ctidTraderAccountId=int(self.account_id),
                accessToken=self.access_token)
            d2 = self._send(acc, timeout=10)

            def after_acc(res2):
                _check_and_extract_msg(res2)
                return "account-authenticated:" + str(self.account_id)

            return d2.addCallback(after_acc)

        d.addCallback(after_app)
        d.addErrback(self._translate_failure)
        return d

    # -- request API (each returns a step-callable result Deferred) ---------
    def trader_info(self):
        req = MSG.ProtoOATraderReq(ctidTraderAccountId=self._acct())
        return self._ok(self._send(req))

    def open_orders(self):
        req = MSG.ProtoOAOrderListReq(
            ctidTraderAccountId=self._acct(),
            fromTimestamp=0,
            toTimestamp=now_ms())
        return self._ok(self._send(req))

    def open_positions(self):
        """Reconcile: full snapshot of open positions + pending orders."""
        req = MSG.ProtoOAReconcileReq(ctidTraderAccountId=self._acct())
        return self._ok(self._send(req))

    def unrealized_pnl(self):
        req = MSG.ProtoOAGetPositionUnrealizedPnLReq(
            ctidTraderAccountId=self._acct())
        return self._ok(self._send(req))

    def deal_list(self, days: int = 30, max_rows: int = 100):
        req = MSG.ProtoOADealListReq(
            ctidTraderAccountId=self._acct(),
            fromTimestamp=now_ms() - days * 86400 * 1000,
            toTimestamp=now_ms(),
            maxRows=max_rows)
        return self._ok(self._send(req, timeout=30))

    def account_list(self):
        req = MSG.ProtoOAGetAccountListByAccessTokenReq(
            accessToken=self.access_token)
        return self._ok(self._send(req))

    def symbol_list(self, include_archived: bool = False):
        req = MSG.ProtoOASymbolsListReq(
            ctidTraderAccountId=self._acct(),
            includeArchivedSymbols=include_archived)
        return self._ok(self._send(req, timeout=30))

    def symbols_by_id(self, symbol_ids):
        req = MSG.ProtoOASymbolByIdReq(ctidTraderAccountId=self._acct())
        req.symbolId.extend([int(i) for i in symbol_ids])
        return self._ok(self._send(req, timeout=10))

    def joined_symbol_views(self, symbol_ids):
        """Fetch full symbol specs for the given ids, joined with their names.

        Two requests: symbols list (names) + by-id (full specs).  Resolves to
        {symbolId: SimpleNamespace(symbolName=..., **full spec fields)}.
        Archived symbols are included so positions in delisted symbols still
        resolve to a name.
        """
        from types import SimpleNamespace
        ids = [int(i) for i in dict.fromkeys(symbol_ids)]
        if not ids:
            return Deferred.succeed({})
        req = MSG.ProtoOASymbolsListReq(
            ctidTraderAccountId=self._acct(), includeArchivedSymbols=True)
        d = self._ok(self._send(req, timeout=30))

        def after_list(list_res):
            names = {int(x.symbolId): x.symbolName for x in list_res.symbol}
            req2 = MSG.ProtoOASymbolByIdReq(ctidTraderAccountId=self._acct())
            req2.symbolId.extend(ids)
            d2 = self._send(req2, timeout=10)
            d2.addCallback(_check_and_extract)
            d2.addErrback(self._translate_failure)

            def build(byid_res):
                out = {}
                for sym in byid_res.symbol:
                    fid = int(sym.symbolId)
                    view = SimpleNamespace(symbolName=names.get(fid, str(fid)))
                    for f in sym.DESCRIPTOR.fields:
                        setattr(view, f.name, getattr(sym, f.name))
                    out[fid] = view
                return out

            return d2.addCallback(build)

        return d.addCallback(after_list)

    def version(self):
        req = MSG.ProtoOAVersionReq()
        return self._ok(self._send(req))

    def spot_snapshot(self, symbol_ids, wait_seconds: float = 6.0):
        """Subscribe to spot events, wait, unsubscribe; return raw quotes."""
        self.spots.clear()
        sub = MSG.ProtoOASubscribeSpotsReq(
            ctidTraderAccountId=self._acct(), subscribeToSpotTimestamp=True)
        sub.symbolId.extend([int(i) for i in symbol_ids])
        d = self._send(sub, timeout=10)

        def after_sub(_res):
            wait_d = Deferred()
            reactor.callLater(wait_seconds, wait_d.callback, None)

            def after_wait(_w):
                uns = MSG.ProtoOAUnsubscribeSpotsReq(
                    ctidTraderAccountId=self._acct())
                uns.symbolId.extend([int(i) for i in symbol_ids])
                return self._client.send(uns, responseTimeoutInSeconds=10)

            return wait_d.addCallback(after_wait)

        d.addCallback(_check_and_extract)
        d.addCallback(after_sub)
        d.addErrback(self._translate_failure)
        d.addCallback(
            lambda _r: {int(k): dict(v) for k, v in self.spots.items()})
        d.addErrback(self._translate_failure)
        return d

    def historical_bars(self, symbol_id, period: str = "H1",
                       count: int = 100, days: int = None):
        period = period.upper()
        if period not in PERIOD_SECONDS:
            raise CTraderError(
                "BAD_PERIOD",
                "period must be one of " + ", ".join(PERIOD_SECONDS))
        to_ts = now_ms()
        from_ts = to_ts - int((days or (count * PERIOD_SECONDS[period]
                                        / 1000.0)) * 1000)
        req = MSG.ProtoOAGetTrendbarsReq(
            ctidTraderAccountId=self._acct(),
            fromTimestamp=int(from_ts), toTimestamp=int(to_ts),
            period=PERIOD_NUM[period], symbolId=int(symbol_id),
            count=count)
        return self._ok(self._send(req, timeout=45))

    def place_order(self, symbol_id, side: int, volume: int,
                    order_type: int = ORDER_TYPE_MARKET, price: float = None,
                    stop_loss: float = None, take_profit: float = None,
                    comment: str = None, slippage_points: int = 0,
                    client_order_id: str = None,
                    watch_seconds: float = 8.0):
        """Place an order.  volume = RAW int64 units (see volume_for_symbol /
        check_volume).  side: SIDE_BUY|SIDE_SELL.  Returns exec events."""
        req = MSG.ProtoOANewOrderReq(
            ctidTraderAccountId=self._acct(),
            symbolId=int(symbol_id),
            orderType=int(order_type),
            tradeSide=int(side),
            volume=int(volume))
        if order_type == ORDER_TYPE_LIMIT and price is not None:
            req.limitPrice = float(price)
        if order_type == ORDER_TYPE_STOP and price is not None:
            req.stopPrice = float(price)
        if stop_loss is not None:
            req.stopLoss = float(stop_loss)
        if take_profit is not None:
            req.takeProfit = float(take_profit)
        if comment:
            req.comment = str(comment)
        if slippage_points:
            req.slippageInPoints = int(slippage_points)
        if client_order_id:
            req.clientOrderId = str(client_order_id)
        return self._fire_and_watch(req, watch_seconds)

    def cancel_order(self, order_id, watch_seconds: float = 6.0):
        req = MSG.ProtoOACancelOrderReq(
            ctidTraderAccountId=self._acct(), orderId=int(order_id))
        return self._fire_and_watch(req, watch_seconds)

    def close_position(self, position_id, volume: int = None,
                       watch_seconds: float = 8.0):
        """Close all (or given RAW volume of) a position.  volume=None closes
        the whole position."""
        req = MSG.ProtoOAClosePositionReq(
            ctidTraderAccountId=self._acct(), positionId=int(position_id))
        if volume is not None:
            req.volume = int(volume)
        return self._fire_and_watch(req, watch_seconds)

    def _acct(self) -> int:
        if not self.account_id:
            raise CTraderError("NO_ACCOUNT",
                               "no trading account selected "
                               "(use --ctrader-account <id>)")
        return int(self.account_id)

    # -- symbol resolution helper ------------------------------------------
    def symbol_steps(self, names, include_archived: bool = False):
        """Build the two steps: list symbols -> fetch full defs.

        Returns (steps, results_box); results_box["full"] maps
        symbolId -> ProtoOASymbol once the second step completes.
        """
        wanted = [normalize_name(n) for n in names]
        box = {"list": None, "matched": {}, "full": {}, "names": {}}

        def step_list(s, _r):
            return s.symbol_list(include_archived=include_archived)

        def step_full(s, _r):
            box["list"] = _r[-1]
            found = {}
            for sym in box["list"].symbol:
                key = normalize_name(sym.symbolName)
                if key in wanted and sym.enabled and key not in found:
                    found[key] = sym
            missing = [w for w in wanted if w not in found]
            if missing:
                raise CTraderError(
                    "SYMBOL_NOT_FOUND",
                    "not found (enabled): " + ", ".join(missing)
                    + " — try --ctrader-symbols to list available symbols")
            ids = [found[w].symbolId for w in wanted if w in found]
            seen, uniq = set(), []
            for i in ids:
                if i not in seen:
                    seen.add(i)
                    uniq.append(i)
            req = MSG.ProtoOASymbolByIdReq(
                ctidTraderAccountId=self._acct())
            req.symbolId.extend([int(i) for i in uniq])
            d = self._send(req, timeout=10)
            d.addCallback(_check_and_extract)
            d.addErrback(self._translate_failure)

            def store(res):
                box["matched"] = found
                for sym in res.symbol:
                    box["full"][int(sym.symbolId)] = sym
                return res

            return d.addCallback(store)

        return [step_list, step_full], box

    # -- executor -----------------------------------------------------------
    def execute(self, steps, hard_timeout: float = None) -> list:
        """Run the handshake then each step sequentially under the reactor."""
        # The Twisted reactor cannot be re-run after stop() in one process,
        # so install a fresh reactor for every session after the first and
        # bind a fresh Client to it.
        _REACTOR_USES["count"] += 1
        if _REACTOR_USES["count"] > 1:
            _new_reactor()
        self._client = Client(self._host, self._port, TcpProtocol)
        self._client.setMessageReceivedCallback(self._on_message)
        self._client.setDisconnectedCallback(self._on_disconnected)

        self._finished = False
        step_list = [self._handshake_step] + list(steps)
        results = []
        error_box = []
        idx = [0]
        self._pending_fail = lambda _f: None

        def fail(failure):
            if not error_box:
                if not hasattr(failure, "getErrorMessage"):
                    failure = _failure_of(failure)
                error_box.append(failure)
            finish()
            exc = getattr(failure, "value", None)
            if isinstance(exc, Exception):
                raise exc
            raise CTraderError("SESSION_ERROR", str(failure.getErrorMessage()))

        def finish():
            if self._finished:
                return
            self._finished = True
            try:
                self._client.stopService()
            except Exception:
                pass
            reactor.callLater(0.3, reactor.stop)

        def advance():
            if self._finished:
                return
            if idx[0] >= len(step_list):
                return finish()
            step = step_list[idx[0]]
            try:
                out = step(self, results)
            except Exception as e:
                error_box.append(_failure_of(e))
                return finish()
            idx[0] += 1
            pos = idx[0] - 1
            results.append(None)  # reserve this step's slot
            if out is None or not hasattr(out, "addCallback"):
                results[pos] = out
                reactor.callLater(0, advance)
                return
            out.addCallback(
                lambda r: (results.__setitem__(pos, r), advance()))
            out.addErrback(fail)

        def watchdog():
            if self._finished:
                return
            self._finished = True
            if not error_box:
                error_box.append(_failure_of(CTraderError(
                    "CONNECT_TIMEOUT",
                    "no progress within %ss (check network / CTRADER_HOST)"
                    % str(hard_timeout or self.hard_timeout))))
            finish()

        self._pending_fail = fail

        self._client.setConnectedCallback(lambda _c: reactor.callLater(0, advance))
        reactor.callLater(hard_timeout or self.hard_timeout, watchdog)
        self._client.startService()
        reactor.run()

        if error_box:
            f = error_box[0]
            exc = getattr(f, "value", None)
            if isinstance(exc, CTraderError):
                raise exc
            tb = ""
            try:
                tb = "\n" + (f.getTraceback() or "")[-1500:]
            except Exception:
                pass
            raise CTraderError("SESSION_ERROR",
                               str(f.getErrorMessage()) + tb)
        return results


def _failure_of(exc):
    """Wrap a plain exception in a Twisted Failure (or return as-is)."""
    try:
        from twisted.python.failure import Failure
        return Failure(exc)
    except Exception:
        return exc


def _check_and_extract_msg(msg):
    if CT_SDK_AVAILABLE and msg.payloadType == PT_ERROR_RES:
        e = Protobuf.extract(msg)
        raise CTraderError(e.errorCode or "CH_ERROR", e.description or "cTrader error")
    return msg


# ---------------------------------------------------------------------------
# Summarizers (protobuf -> plain dict, units decoded)
# ---------------------------------------------------------------------------
def summarize_trader(res) -> dict:
    t = res.trader
    md = int(getattr(t, "moneyDigits", 2) or 2)
    lev = int(getattr(t, "leverageInCents", 0) or 0)
    return {
        "account_id": t.ctidTraderAccountId,
        "trader_login": t.traderLogin,
        "balance": round(money_float(t.balance, md), 2),
        "money_digits": md,
        # leverageInCents: 2000 <-> 1:200 on QCG (verified against
        # ExpectedMargin: notional == margin * 200).
        "leverage": lev / 10 if lev else t.maxLeverage,
        "account_type": _enum_name(t, "accountType"),
        "broker": t.brokerName,
        "swap_free": t.swapFree,
        "limited_risk": t.isLimitedRisk,
    }


def summarize_account_list(res) -> list:
    out = []
    for a in res.ctidTraderAccount:
        out.append({
            "account_id": int(a.ctidTraderAccountId),
            "is_live": bool(a.isLive),
            "trader_login": int(a.traderLogin),
            "last_balance_update_ms": int(a.lastBalanceUpdateTimestamp),
        })
    return out


def _enum_name(msg, field_name):
    """Resolve a proto enum field to its symbolic name ('HEDGED' etc.)."""
    try:
        fd = type(msg).DESCRIPTOR.fields_by_name[field_name]
        if fd.enum_type:
            return fd.enum_type.values_by_number[getattr(msg, field_name)].name
    except Exception:
        pass
    return None


def summarize_position(pos, symbols: dict = None) -> dict:
    td = pos.tradeData
    symbols = symbols or {}
    sym = symbols.get(int(td.symbolId), None)
    return {
        "position_id": int(pos.positionId),
        "symbol": getattr(sym, "symbolName", str(td.symbolId)),
        "side": "BUY" if td.tradeSide == SIDE_BUY else "SELL",
        "volume_lots": round(lots_display(td.volume, sym), 4),
        "opened_ms": int(td.openTimestamp),
        "comment": td.comment,
        "price": round(float(pos.price), 6) if pos.price else None,
        "stop_loss": round(float(pos.stopLoss), 6) if pos.stopLoss else None,
        "take_profit": round(float(pos.takeProfit), 6) if pos.takeProfit else None,
        "swap": pos.swap,
        "commission": pos.commission,
        "used_margin": int(pos.usedMargin),
        "status": "OPEN" if pos.positionStatus == 1 else str(pos.positionStatus),
    }


def summarize_order(o, symbols: dict = None) -> dict:
    symbols = symbols or {}
    sym = symbols.get(int(o.tradeData.symbolId), None)
    return {
        "order_id": int(o.orderId),
        "symbol": getattr(sym, "symbolName", str(o.tradeData.symbolId)),
        "type": {1: "MARKET", 2: "LIMIT", 3: "STOP", 4: "SLTP",
                 5: "MARKET_RANGE", 6: "STOP_LIMIT"}.get(o.orderType, o.orderType),
        "side": "BUY" if o.tradeData.tradeSide == SIDE_BUY else "SELL",
        "volume_lots": round(lots_display(o.tradeData.volume, sym), 4),
        "limit_price": round(float(o.limitPrice), 6) if o.limitPrice else None,
        "stop_price": round(float(o.stopPrice), 6) if o.stopPrice else None,
        "stop_loss": round(float(o.stopLoss), 6) if o.stopLoss else None,
        "take_profit": round(float(o.takeProfit), 6) if o.takeProfit else None,
        "status": {1: "ACCEPTED", 2: "FILLED", 3: "REJECTED",
                   4: "EXPIRED", 5: "CANCELLED"}.get(o.orderStatus, o.orderStatus),
        "position_id": int(o.positionId) if o.positionId else None,
        "client_order_id": o.clientOrderId,
    }


def summarize_deal(d, symbols: dict = None) -> dict:
    symbols = symbols or {}
    sym = symbols.get(int(d.symbolId), None)
    return {
        "deal_id": int(d.dealId),
        "symbol": getattr(sym, "symbolName", str(d.symbolId)),
        "side": "BUY" if d.tradeSide == SIDE_BUY else "SELL",
        "volume_lots": round(lots_display(d.volume, sym), 4),
        "filled_lots": round(lots_display(d.filledVolume, sym), 4),
        "price": round(float(d.executionPrice), 6) if d.executionPrice else None,
        "status": {2: "FILLED", 3: "PARTIAL", 4: "REJECTED",
                   5: "INTERNAL_REJECTED", 6: "ERROR", 7: "MISSED"
                   }.get(d.dealStatus, d.dealStatus),
        "commission": d.commission,
        "executed_ms": int(d.executionTimestamp),
        "position_id": int(d.positionId) if d.positionId else None,
    }


def summarize_quotes(spot_raw: dict, symbols: dict) -> list:
    out = []
    for sid, q in spot_raw.items():
        sym = symbols.get(int(sid))
        out.append({
            "symbol": getattr(sym, "symbolName", str(sid)),
            "bid": round(price_float(q["bid_raw"]), 8),
            "ask": round(price_float(q["ask_raw"]), 8),
            "spread": round(price_float(q["ask_raw"])
                            - price_float(q["bid_raw"]), 8),
            "ts_ms": int(q["ts"]),
        })
    out.sort(key=lambda x: x["symbol"])
    return out


def summarize_bars(res) -> list:
    out = []
    for tb in res.trendbar:
        low = int(tb.low)
        out.append({
            "ts_ms": int(tb.utcTimestampInMinutes) * 60000,
            "open": round(price_float(low + int(tb.deltaOpen)), 8),
            "high": round(price_float(low + int(tb.deltaHigh)), 8),
            "low": round(price_float(low), 8),
            "close": round(price_float(low + int(tb.deltaClose)), 8),
            "volume_units": int(tb.volume),
        })
    return out


def summarize_executions(events) -> list:
    out = []
    for ev in events:
        entry = {
            "type": EXECUTION_TYPE.get(ev.executionType, ev.executionType),
            "error_code": ev.errorCode or None,
        }
        if ev.order and ev.order.orderId:
            entry["order_id"] = int(ev.order.orderId)
            entry["order_status"] = ev.order.orderStatus
            entry["order_side"] = ("BUY" if ev.order.tradeData.tradeSide
                                   == SIDE_BUY else "SELL")
        if ev.deal and ev.deal.dealId:
            entry["deal_id"] = int(ev.deal.dealId)
            entry["deal_price"] = float(ev.deal.executionPrice) or None
            entry["deal_volume_lots"] = round(lots_from_raw(ev.deal.volume), 4)
        if ev.position and ev.position.positionId:
            entry["position_id"] = int(ev.position.positionId)
        out.append(entry)
    return out


def symbol_map_from(full_box: dict) -> dict:
    return {int(k): v for k, v in (full_box or {}).get("full", {}).items()}


def join_symbol_views(box: dict) -> dict:
    """{symbolId: SimpleNamespace} — join light-symbol names onto full specs
    from a symbol_steps() box.

    The full ProtoOASymbol model has NO symbolName field (names exist only on
    the light list model), so every display path must join by symbolId.
    """
    from types import SimpleNamespace
    out = {}
    for _nm, light in (box or {}).get("matched", {}).items():
        fid = int(light.symbolId)
        full = (box.get("full") or {}).get(fid)
        view = SimpleNamespace(symbolName=light.symbolName)
        if full is not None:
            for f in full.DESCRIPTOR.fields:
                setattr(view, f.name, getattr(full, f.name))
        out[fid] = view
    return out


# ---------------------------------------------------------------------------
# Status report (no session needed)
# ---------------------------------------------------------------------------
def _tcp_reachable(host: str, port: int, timeout: float = 6.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def status_report(path: str = None) -> dict:
    creds, store = resolve_credentials(path)
    report = {
        "sdk_installed": CT_SDK_AVAILABLE,
        "sdk_error": None if CT_SDK_AVAILABLE else CT_SDK_ERROR,
        "python": sys.version.split()[0],
        "endpoints": {
            "live.ctraderapi.com:5035": _tcp_reachable("live.ctraderapi.com", 5035),
            "demo.ctraderapi.com:5035": _tcp_reachable("demo.ctraderapi.com", 5035),
        },
        "credentials": {
            "client_id": bool(creds.get("client_id")),
            "client_secret": bool(creds.get("client_secret")),
            "redirect_uri": creds.get("redirect_uri"),
            "access_token": bool(creds.get("access_token")),
            "refresh_token": bool(creds.get("refresh_token")),
            "account_id": creds.get("account_id"),
            "host": creds.get("host"),
            "store_file": store.path if store.exists() else None,
            "missing": creds["missing"],
        },
    }
    steps = []
    if not CT_SDK_AVAILABLE:
        steps.append("pip install ctrader-open-api (and service-identity==24.2.0)")
    missing = creds["missing"]
    if "client_id" in missing or "client_secret" in missing:
        steps.append("create API app (see CTRADER_SETUP.md) and set "
                     "CTRADER_CLIENT_ID / CTRADER_CLIENT_SECRET")
    if "access_token" in missing:
        steps.append("run: python3 trading_bot.py --ctrader-auth  "
                     "(open the URL on your phone, paste the ?code= back)")
    if not creds.get("account_id"):
        steps.append("select account: python3 trading_bot.py "
                     "--ctrader-accounts --ctrader-account <id>")
    if not steps:
        steps.append("READY — try: python3 trading_bot.py --ctrader-info")
    report["next_steps"] = steps
    report["ready"] = (CT_SDK_AVAILABLE and not missing
                       and bool(creds.get("account_id")))
    return report
