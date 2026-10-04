#!/usr/bin/env python3
"""
Tests for the cTrader Open API connector (ctrader_connector.py).

Offline unit tests: unit conventions, token store, credential resolution,
auth URL construction, summarizers, and the Twisted errback-translation
regression (an errback that RETURNS an exception makes a Deferred succeed —
the bug that silently ate server errors).

One integration test (marked, network-gated) exercises the real phone ->
TLS -> protobuf round-trip against the demo host with fake credentials and
expects a clean CH_CLIENT_AUTH_FAILURE.
"""

import json
import os
import sys
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ctrader_connector as ct  # noqa: E402

SKIP_NO_SDK = pytest.mark.skipif(
    not ct.CT_SDK_AVAILABLE, reason="ctrader_open_api SDK not installed")


@pytest.fixture(autouse=True)
def _strip_ctrader_env(monkeypatch):
    """Keep credential tests hermetic.

    resolve_credentials() reads os.environ, and the surrounding shell (or a
    loaded .env) may export CTRADER_* values.  Remove them so tests observe
    only what they set explicitly.
    """
    for key in list(os.environ):
        if key.startswith("CTRADER_"):
            monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# Unit conventions
# ---------------------------------------------------------------------------
def test_price_protocol_scale():
    # Official proto: prices are "1/100000 of unit of a price" — a fixed
    # protocol scale, NOT the per-symbol digits field.
    assert ct.PRICE_SCALE == 100000
    assert ct.price_raw(1.08530) == 108530
    assert ct.price_float(108530) == pytest.approx(1.0853)
    assert ct.price_raw(84841.5) == 8484150000
    assert ct.price_float(0) == 0.0
    # same price whether symbol digits=2 or digits=5
    assert ct.price_float(ct.price_raw(4142.72)) == pytest.approx(4142.72)


def test_volume_convention():
    # 1 lot == 100 (0.01-lot granularity, per official Spotware sample)
    assert ct.volume_raw(1) == 100
    assert ct.volume_raw(0.05) == 5
    assert ct.lots_from_raw(5) == 0.05
    assert ct.lots_from_raw(100) == 1.0


def test_money_float():
    assert ct.money_float(1000000, 2) == 10000.0
    assert ct.money_float(12345, 0) == 12345.0
    assert ct.money_float(-500, 2) == -5.0


def test_normalize_name():
    assert ct.normalize_name("eur/usd") == "EURUSD"
    assert ct.normalize_name("xauusd") == "XAUUSD"
    assert ct.normalize_name("  btc/usd ") == "BTCUSD"


def test_period_constants():
    assert ct.PERIOD_SECONDS["H1"] == 3600
    assert ct.PERIOD_NUM["H1"] == 9
    assert ct.PERIOD_SECONDS["M5"] == 300
    assert all(k in ct.PERIOD_NUM for k in
               ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"))


@SKIP_NO_SDK
def test_historical_bars_bad_period():
    s = ct.CTraderSession(
        {"client_id": "c", "client_secret": "s", "access_token": "t",
         "host": "live"}, account_id="1", demo=True)
    with pytest.raises(ct.CTraderError) as ei:
        s.historical_bars(1, period="X9")
    assert ei.value.code == "BAD_PERIOD"


@SKIP_NO_SDK
def test_open_orders_sets_required_timestamps():
    # Regression: ProtoOAOrderListReq has proto2 REQUIRED fromTimestamp /
    # toTimestamp — omitting them crashes the deferred with EncodeError
    # ("missing required fields") at send time.
    s = ct.CTraderSession(
        {"client_id": "c", "client_secret": "s", "access_token": "t",
         "host": "live"}, account_id="42")
    captured = {}

    class _D:
        def addCallback(self, *a, **k):
            return self
        def addErrback(self, *a, **k):
            return self

    def fake_send(req, timeout=None):
        captured["req"] = req
        return _D()

    s._send = fake_send
    s._ok = lambda d: d
    s.open_orders()
    req = captured["req"]
    assert req.fromTimestamp == 0
    assert req.toTimestamp > 0
    req.SerializeToString()  # must not raise EncodeError


# ---------------------------------------------------------------------------
# Token store + credential resolution
# ---------------------------------------------------------------------------
def test_token_store_roundtrip(tmp_path):
    path = str(tmp_path / "creds.json")
    store = ct.TokenStore(path)
    assert not store.exists()
    data = store.store_tokens(
        "cid", "sec", "https://x.com",
        {"accessToken": "AT", "refreshToken": "RT",
         "expiresIn": 3600, "tokenType": "Bearer"},
        account_id="42", is_live=True)
    assert data["access_token"] == "AT"
    assert data["refresh_token"] == "RT"
    assert data["account_id"] == "42"
    assert data["host"] == "live"
    assert data["access_token_expires_at"] > time.time()
    assert store.exists()
    loaded = store.load()
    assert loaded["client_id"] == "cid"
    assert loaded["client_secret"] == "sec"


def test_token_store_load_corrupt(tmp_path):
    path = str(tmp_path / "creds.json")
    with open(path, "w") as f:
        f.write("{not json")
    assert ct.TokenStore(path).load() == {}


def test_resolve_credentials_env_wins(tmp_path, monkeypatch):
    path = str(tmp_path / "creds.json")
    ct.TokenStore(path).save({
        "client_id": "file-id", "client_secret": "file-sec",
        "access_token": "file-at", "account_id": "111", "host": "demo"})
    monkeypatch.setenv("CTRADER_CLIENT_ID", "env-id")
    monkeypatch.setenv("CTRADER_ACCESS_TOKEN", "env-at")
    monkeypatch.delenv("CTRADER_ACCOUNT_ID", raising=False)
    creds, _ = ct.resolve_credentials(path)
    assert creds["client_id"] == "env-id"
    assert creds["client_secret"] == "file-sec"
    assert creds["access_token"] == "env-at"
    assert creds["account_id"] == "111"
    assert creds["host"] == "demo"
    assert creds["missing"] == []


def test_resolve_credentials_missing(tmp_path):
    creds, _ = ct.resolve_credentials(str(tmp_path / "none.json"))
    assert creds["missing"] == ["client_id", "client_secret", "access_token"]


def test_host_for():
    creds = {"host": "live"}
    assert ct.host_for(creds)[0] == "live"
    assert ct.host_for(creds, demo_flag=True)[0] == "demo"
    assert ct.host_for({"host": "bogus"})[0] == "live"
    live, demo = ct.host_for(creds), ct.host_for(creds, demo_flag=True)
    assert "live" in live[1] and "demo" in demo[1]
    assert live[2] == 5035


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------
@SKIP_NO_SDK
def test_auth_url():
    url = ct.CTraderAuth.auth_url("cid123", "sec456", "https://my.ctrader.com")
    # Docs-canonical consent endpoint (help.ctrader.com/open-api/
    # account-authentication/), mobile-friendly via product=web.
    assert url.startswith("https://id.ctrader.com/my/settings/openapi/grantingaccess?")
    assert "client_id=cid123" in url
    assert "scope=trading" in url
    # redirect_uri is URL-encoded
    assert "redirect_uri=https%3A%2F%2Fmy.ctrader.com" in url
    assert "product=web" in url


@SKIP_NO_SDK
def test_exchange_code_rejects_bad_response(monkeypatch):
    monkeypatch.setattr(
        ct.Auth, "getToken",
        lambda self, code: {"error": "invalid_grant"})
    auth = ct.CTraderAuth("c", "s", "https://x.com")
    with pytest.raises(ct.CTraderError) as ei:
        auth.exchange_code("badcode")
    assert ei.value.code == "OAUTH_ERROR"


@SKIP_NO_SDK
def test_refresh_rejects_bad_response(monkeypatch):
    monkeypatch.setattr(
        ct.Auth, "refreshToken",
        lambda self, tok: {"error": "invalid_refresh"})
    with pytest.raises(ct.CTraderError) as ei:
        ct.CTraderAuth.refresh("c", "s", "rt")
    assert ei.value.code == "TOKEN_REFRESH_FAILED"


@SKIP_NO_SDK
def test_ensure_fresh_token_refreshes_near_expiry(tmp_path, monkeypatch):
    path = str(tmp_path / "creds.json")
    store = ct.TokenStore(path)
    store.store_tokens("c", "s", "https://x.com",
                       {"accessToken": "OLD", "refreshToken": "RT",
                        "expiresIn": 1}, is_live=True)
    creds, _ = ct.resolve_credentials(path)
    creds["access_token_expires_at"] = int(time.time()) + 10  # within 300s

    captured = {}

    class FakeAuth:
        def __init__(self, *a, **k):
            pass

        @staticmethod
        def refreshToken(rt):
            captured["rt"] = rt
            return {"accessToken": "NEW", "refreshToken": "RT2",
                    "expiresIn": 3600}

    monkeypatch.setattr(ct, "Auth", FakeAuth)
    out = ct.ensure_fresh_token(creds, store, force=True)
    assert out["access_token"] == "NEW"
    assert captured["rt"] == "RT"
    saved = store.load()
    assert saved["access_token"] == "NEW"
    assert saved["refresh_token"] == "RT2"


@SKIP_NO_SDK
def test_ensure_fresh_token_noop_when_fresh(tmp_path):
    path = str(tmp_path / "creds.json")
    store = ct.TokenStore(path)
    store.store_tokens("c", "s", "https://x.com",
                       {"accessToken": "AT", "refreshToken": "RT",
                        "expiresIn": 7200}, is_live=True)
    creds, _ = ct.resolve_credentials(path)
    out = ct.ensure_fresh_token(creds, store)
    assert out["access_token"] == "AT"  # untouched


# ---------------------------------------------------------------------------
# Summarizers (fake protobuf-shaped objects)
# ---------------------------------------------------------------------------
def _mk_trader_res(balance_cents=1000000, md=2):
    return SimpleNamespace(trader=SimpleNamespace(
        ctidTraderAccountId=7, traderLogin=123456, balance=balance_cents,
        moneyDigits=md, maxLeverage=100, accountType=0, brokerName="QCG",
        swapFree=False, isLimitedRisk=False))


def test_summarize_trader():
    out = ct.summarize_trader(_mk_trader_res())
    assert out["balance"] == 10000.0
    assert out["broker"] == "QCG"
    assert out["account_id"] == 7


def test_summarize_account_list():
    res = SimpleNamespace(ctidTraderAccount=[
        SimpleNamespace(ctidTraderAccountId=101, isLive=True,
                        traderLogin=11, lastBalanceUpdateTimestamp=123),
        SimpleNamespace(ctidTraderAccountId=102, isLive=False,
                        traderLogin=22, lastBalanceUpdateTimestamp=456),
    ])
    rows = ct.summarize_account_list(res)
    assert rows[0]["account_id"] == 101 and rows[0]["is_live"] is True
    assert rows[1]["account_id"] == 102 and rows[1]["is_live"] is False


def _mk_position(sid=55, vol=100, side=1, price=1.08, status=1):
    return SimpleNamespace(
        positionId=900,
        tradeData=SimpleNamespace(symbolId=sid, volume=vol, tradeSide=side,
                                  openTimestamp=1700000000000, comment="x"),
        price=price, stopLoss=1.07, takeProfit=1.09, swap=-12,
        commission=0, usedMargin=5000, positionStatus=status)


def test_summarize_position_with_symbols():
    sym = SimpleNamespace(symbolName="EURUSD", digits=5)
    out = ct.summarize_position(_mk_position(), symbols={55: sym})
    assert out["symbol"] == "EURUSD"
    assert out["side"] == "BUY"
    assert out["volume_lots"] == 1.0
    assert out["price"] == 1.08
    assert out["stop_loss"] == 1.07
    assert out["status"] == "OPEN"


def test_summarize_order():
    o = SimpleNamespace(
        orderId=1, tradeData=SimpleNamespace(symbolId=7, volume=5,
                                             tradeSide=2),
        orderType=2, orderStatus=1, expirationTimestamp=0,
        executionPrice=0.0, executedVolume=0, utcLastUpdateTimestamp=0,
        baseSlippagePrice=0.0, slippageInPoints=0, closingOrder=False,
        limitPrice=1.0850, stopPrice=0.0, stopLoss=0.0, takeProfit=0.0,
        clientOrderId="cli-1", timeInForce=2, positionId=0)
    out = ct.summarize_order(o)
    assert out["type"] == "LIMIT"
    assert out["side"] == "SELL"
    assert out["volume_lots"] == 0.05
    assert out["limit_price"] == 1.085
    assert out["status"] == "ACCEPTED"


def test_summarize_deal():
    d = SimpleNamespace(
        dealId=2, orderId=1, positionId=3, volume=100, filledVolume=100,
        symbolId=9, createTimestamp=0, executionTimestamp=1700000000000,
        utcLastUpdateTimestamp=0, executionPrice=1.09, tradeSide=1,
        dealStatus=2, marginRate=0.0, commission=0,
        baseToUsdConversionRate=1.0)
    out = ct.summarize_deal(d)
    assert out["side"] == "BUY"
    assert out["volume_lots"] == 1.0
    assert out["price"] == 1.09
    assert out["status"] == "FILLED"


def test_summarize_quotes_fixed_point():
    spot = {10: {"bid_raw": 108530, "ask_raw": 108540, "ts": 1700000000000,
                 "trendbar": None}}
    syms = {10: SimpleNamespace(symbolName="EURUSD", digits=5)}
    q = ct.summarize_quotes(spot, syms)
    assert q[0]["symbol"] == "EURUSD"
    assert q[0]["bid"] == pytest.approx(1.0853)
    assert q[0]["ask"] == pytest.approx(1.0854)
    assert q[0]["spread"] == pytest.approx(0.0001)


def test_summarize_bars_delta_decode():
    class TB:
        pass
    t = TB()
    t.low, t.deltaOpen, t.deltaHigh, t.deltaClose = 108500, 10, 50, 20
    t.utcTimestampInMinutes, t.volume = 100, 7
    bars = ct.summarize_bars(SimpleNamespace(trendbar=[t]))
    assert bars[0]["low"] == pytest.approx(1.085)
    assert bars[0]["open"] == pytest.approx(1.0851)
    assert bars[0]["high"] == pytest.approx(1.0855)
    assert bars[0]["close"] == pytest.approx(1.0852)
    assert bars[0]["ts_ms"] == 100 * 60000


def test_summarize_executions():
    ev = SimpleNamespace(
        executionType=3, errorCode="",
        order=SimpleNamespace(orderId=5, orderStatus=2,
                              tradeData=SimpleNamespace(tradeSide=1)),
        deal=SimpleNamespace(dealId=6, executionPrice=1.09, volume=100),
        position=SimpleNamespace(positionId=0))
    out = ct.summarize_executions([ev])
    assert out[0]["type"] == "ORDER_FILLED"
    assert out[0]["order_id"] == 5
    assert out[0]["deal_id"] == 6
    assert out[0]["deal_volume_lots"] == 1.0


# ---------------------------------------------------------------------------
# Status report (TCP checks stubbed)
# ---------------------------------------------------------------------------
def test_status_report_no_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(ct, "_tcp_reachable", lambda *a, **k: True)
    rep = ct.status_report(str(tmp_path / "x.json"))
    assert rep["sdk_installed"] is ct.CT_SDK_AVAILABLE
    assert rep["endpoints"]["live.ctraderapi.com:5035"] is True
    assert rep["credentials"]["missing"] == [
        "client_id", "client_secret", "access_token"]
    assert rep["ready"] is False
    assert any("create API app" in s for s in rep["next_steps"])


def test_status_report_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(ct, "_tcp_reachable", lambda *a, **k: True)
    path = str(tmp_path / "creds.json")
    ct.TokenStore(path).store_tokens(
        "c", "s", "https://x.com",
        {"accessToken": "AT", "refreshToken": "RT", "expiresIn": 3600},
        account_id="77", is_live=True)
    rep = ct.status_report(path)
    assert rep["ready"] is True
    assert rep["credentials"]["account_id"] == "77"


# ---------------------------------------------------------------------------
# Session: construction + Twisted errback regression
# ---------------------------------------------------------------------------
def test_session_requires_credentials():
    with pytest.raises(ct.CTraderError) as ei:
        ct.CTraderSession({"client_id": "c", "client_secret": "s",
                           "access_token": None, "host": "live"},
                          account_id="1")
    assert ei.value.code == "MISSING_CREDENTIALS"


@SKIP_NO_SDK
def test_session_no_account_needed_only_when_flagged():
    s = ct.CTraderSession(
        {"client_id": "c", "client_secret": "s", "access_token": "t",
         "host": "live"}, account_id=None, demo=True)
    with pytest.raises(ct.CTraderError) as ei:
        s._acct()
    assert ei.value.code == "NO_ACCOUNT"


@SKIP_NO_SDK
def test_translate_failure_raises_not_returns():
    """Regression: an errback that RETURNS an exception object makes the
    Deferred SUCCEED with it (Twisted semantics).  _translate_failure must
    raise, so server errors keep propagating as failures."""
    from twisted.python.failure import Failure
    s = ct.CTraderSession(
        {"client_id": "c", "client_secret": "s", "access_token": "t",
         "host": "live"}, account_id="1", demo=True)
    with pytest.raises(ct.CTraderError) as ei:
        s._translate_failure(Failure(ct.CTraderError("CH_X", "boom")))
    assert ei.value.code == "CH_X"
    with pytest.raises(ct.CTraderError) as ei2:
        s._translate_failure(Failure(RuntimeError("net down")))
    assert ei2.value.code == "REQUEST_ERROR"


@SKIP_NO_SDK
def test_translate_timeout():
    from twisted.internet.defer import CancelledError
    from twisted.python.failure import Failure
    s = ct.CTraderSession(
        {"client_id": "c", "client_secret": "s", "access_token": "t",
         "host": "live"}, account_id="1", demo=True)
    with pytest.raises(ct.CTraderError) as ei:
        s._translate_failure(Failure(CancelledError()))
    assert ei.value.code == "TIMEOUT"


@SKIP_NO_SDK
def test_check_and_extract_raises_on_error_res():
    """_check_and_extract_msg must raise CTraderError on payload 2142."""
    from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAErrorRes, ProtoOATraderRes)
    env_err = ProtoMessage(
        payloadType=2142,
        payload=ProtoOAErrorRes(
            errorCode="CH_TEST", description="deliberate").SerializeToString())
    with pytest.raises(ct.CTraderError) as ei:
        ct._check_and_extract_msg(env_err)
    assert ei.value.code == "CH_TEST"
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATrader
    trader = ProtoOATrader(ctidTraderAccountId=1, balance=0, depositAssetId=0)
    ok = ProtoMessage(
        payloadType=ProtoOATraderRes().payloadType,
        payload=ProtoOATraderRes(ctidTraderAccountId=1, trader=trader)
        .SerializeToString())
    assert ct.Protobuf.extract(ct._check_and_extract_msg(ok)).ctidTraderAccountId == 1


# ---------------------------------------------------------------------------
# Integration (network-gated): phone -> TLS -> demo.ctraderapi.com
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not ct._tcp_reachable("demo.ctraderapi.com", 5035, timeout=6),
    reason="cTrader demo endpoint unreachable from this network")
def test_real_handshake_rejects_fake_credentials():
    """Full execute() pipeline against the real demo host: fake app
    credentials must surface a clean CH_CLIENT_AUTH_FAILURE — and twice
    in a row (reactor re-runs in one process must work)."""
    creds = {"client_id": "phone-test", "client_secret": "phone-test",
             "access_token": "fake", "host": "live", "account_id": "1"}
    for attempt in range(2):
        s = ct.CTraderSession(creds, demo=True, hard_timeout=30)
        with pytest.raises(ct.CTraderError) as ei:
            s.execute([lambda s, r: s.trader_info()])
        assert ei.value.code == "CH_CLIENT_AUTH_FAILURE", \
            f"attempt {attempt}: {ei.value.code}"
        assert "clientId or clientSecret" in ei.value.description
