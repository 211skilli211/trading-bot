"""Polymarket CLOB v2 (pUSD-era) order signing — phone-native, no SDK needed.

Since the pUSD upgrade (Oct 2026) Polymarket settles all trading on two NEW
exchange contracts and the order EIP-712 domain moved to version "2" with a
new Order struct:

    domain:  {name: "Polymarket CTF Exchange", version: "2", chainId: 137,
              verifyingContract: <exchange>}
    Order:   (salt, maker, signer, tokenId, makerAmount, takerAmount,
              side, signatureType, timestamp, metadata, builder)

The old py-clob-client 0.34.6 signs the v1 domain against the (now
deprecated) CLOB-v1 exchanges, so its orders are no longer valid. This
module signs v2 orders locally with eth-account (already installed for the
Polymarket key material) and posts them to clob.polymarket.com with the
unchanged L2 HMAC credential scheme.

Verified sources (fetched 2026-10-05):
  - docs.polymarket.com/resources/contracts   (exchange + pUSD addresses)
  - docs.polymarket.com/trading/place-orders  (typed data, amount rules,
    /order body, L2 HMAC)
  - docs.polymarket.com/concepts/pusd         (collateral model)

EOA accounts (ours): signatureType=0, maker=signer=EOA, sign the Order
typed data directly (no deposit-wallet wrapping).
"""

import base64
import hashlib
import hmac
import json
import random
import time
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from eth_account import Account
except ImportError:  # pragma: no cover
    Account = None

CLOB_HOST = "https://clob.polymarket.com"
CHAIN_ID = 137

# ---- pUSD-era contract addresses (docs resources/contracts) --------------
EXCHANGE_STANDARD = "0xE111180000d2663C0091e4f400237545B87B996B"
EXCHANGE_NEG_RISK = "0xe2222d279d744050d28e00520010520000310F59"
CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"          # collateral token
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"        # wrap/unwrap asset
USDC_NATIVE = "0x3c499c542cEF5E3811E1192ce70d8cC03d5c3359"   # native USDC
COLLATERAL_ONRAMP = "0x93070a847efEf7F70739046A929D47a521F5B8ee"
COLLATERAL_OFFRAMP = "0x2957922Eb93258b93368531d39fAcCA3B4dC5854"

# ---- bridge (polymarket.com bridge API) -----------------------------------
BRIDGE_API = "https://bridge.polymarket.com"

DOMAIN_BASE = {
    "name": "Polymarket CTF Exchange",
    "version": "2",
    "chainId": CHAIN_ID,
}

ORDER_TYPES = {"Order": [
    {"name": "salt", "type": "uint256"},
    {"name": "maker", "type": "address"},
    {"name": "signer", "type": "address"},
    {"name": "tokenId", "type": "uint256"},
    {"name": "makerAmount", "type": "uint256"},
    {"name": "takerAmount", "type": "uint256"},
    {"name": "side", "type": "uint8"},
    {"name": "signatureType", "type": "uint8"},
    {"name": "timestamp", "type": "uint256"},
    {"name": "metadata", "type": "bytes32"},
    {"name": "builder", "type": "bytes32"},
]}

Z32 = "0x" + "00" * 32

# tick_size -> (price decimals, size decimals, amount decimals)
# docs.polymarket.com/trading/place-orders (amount-precision table)
TICK_PRECISION = {
    "0.1": (1, 2, 3),
    "0.01": (2, 2, 4),
    "0.005": (3, 2, 5),
    "0.0025": (4, 2, 6),
    "0.001": (3, 2, 5),
    "0.0001": (4, 2, 6),
}


class PmSignerError(Exception):
    pass


def _require_eth_account():
    if Account is None:
        raise PmSignerError("eth-account not installed")


def _safe_salt() -> int:
    # docs: keep salt within Number.MAX_SAFE_INTEGER (serialized as JSON number)
    return random.randint(1, 2 ** 52)


def wallet_address(private_key: str) -> str:
    _require_eth_account()
    key = private_key.strip()
    if not key.startswith("0x"):
        key = "0x" + key
    return Account.from_key(key).address


def fetch_book(token_id: str, host: str = CLOB_HOST,
               timeout: int = 20) -> Optional[Dict]:
    """Public order book: {bids, asks, tick_size, neg_risk, min_order_size}.

    pUSD-era CLOB API: query-param form (?token_id=), not path segments.
    """
    if requests is None:
        raise PmSignerError("requests not installed")
    try:
        r = requests.get(host + "/book",
                         params={"token_id": token_id}, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "bids" in data and "asks" in data:
                return data
    except (requests.RequestException, ValueError):
        pass
    return None


def fetch_books(token_ids: List[str], host: str = CLOB_HOST,
                timeout: int = 30) -> Dict[str, Dict]:
    """Batch order books (max 500 ids per request). Returns {token_id: book}.

    Books that fail individually come back with empty bids/asks or are
    omitted; missing ids are simply absent from the result.
    """
    if requests is None:
        raise PmSignerError("requests not installed")
    out: Dict[str, Dict] = {}
    ids = [t for t in token_ids if t]
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        try:
            r = requests.post(
                host + "/books",
                json=[{"token_id": t} for t in chunk],
                headers={"Content-Type": "application/json"},
                timeout=timeout)
            if r.status_code != 200:
                continue
            data = r.json()
        except (requests.RequestException, ValueError):
            continue
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, dict):
                continue
            tid = item.get("asset_id") or item.get("token_id")
            if tid and "bids" in item and "asks" in item:
                out[str(tid)] = item
    return out


def best_price(token_id: str, side: str = "BUY", host: str = CLOB_HOST,
               timeout: int = 20) -> Optional[float]:
    """Best executable price: BUY -> lowest ask, SELL -> highest bid."""
    if requests is None:
        raise PmSignerError("requests not installed")
    try:
        r = requests.get(host + "/price",
                         params={"token_id": token_id, "side": side.upper()},
                         timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and data.get("price") not in (None, ""):
                return float(data["price"])
    except (requests.RequestException, ValueError, TypeError):
        pass
    return None


def encode_amounts(book: Dict, side: str, price: float,
                   size: float) -> Tuple[int, int]:
    """Encode (makerAmount, takerAmount) in 6-dec base units per the docs.

    BUY:  makerAmount = USD to spend,  takerAmount = shares
    SELL: makerAmount = shares,        takerAmount = USD to receive
    """
    side = side.upper()
    tick = str(book.get("tick_size", "0.01"))
    if tick not in TICK_PRECISION:
        raise PmSignerError("unsupported tick_size {!r}".format(tick))
    p_dec, s_dec, a_dec = TICK_PRECISION[tick]
    qty = Decimal(str(price)).quantize(
        Decimal(1).scaleb(-p_dec), rounding=ROUND_DOWN)
    sz = Decimal(str(size)).quantize(
        Decimal(1).scaleb(-s_dec), rounding=ROUND_DOWN)
    min_size = Decimal(str(book.get("min_order_size", 5)))
    if sz < min_size:
        raise PmSignerError(
            "size {} below market minimum {}".format(sz, min_size))
    usd = qty * sz  # exact Decimal
    # "If it exceeds amount decimals, round up first to amount decimals + 4,
    #  then down to amount decimals" (preserves BUY max price / SELL min price)
    step_hi = Decimal(1).scaleb(-(a_dec + 4))
    step_lo = Decimal(1).scaleb(-a_dec)
    # docs rounding dance: standard (half-up) round to amount+4 decimals,
    # then to amount decimals (JS Math.round semantics at each stage)
    usd_capped = usd.quantize(step_hi, rounding=ROUND_HALF_UP)
    usd_capped = usd_capped.quantize(step_lo, rounding=ROUND_HALF_UP)

    def micros(value: Decimal) -> int:
        return int((value * 10 ** 6).to_integral_value(rounding=ROUND_DOWN))

    if side == "BUY":
        return micros(usd_capped), micros(sz)
    return micros(sz), micros(usd_capped)


def market_buy_amounts(book: Dict, usd_amount: float,
                       max_price: float) -> Tuple[int, int]:
    """Market-BUY encoding per the docs (USD in, shares out).

    shares = usd / max_price, rounded up to amount+4 decimals then down to
    amount decimals. Docs example: tick 0.01, $10 @ max 0.52 ->
    maker 10000000, taker 19230800.
    """
    tick = str(book.get("tick_size", "0.01"))
    if tick not in TICK_PRECISION:
        raise PmSignerError("unsupported tick_size {!r}".format(tick))
    p_dec, s_dec, a_dec = TICK_PRECISION[tick]
    usd_r = Decimal(str(usd_amount)).quantize(
        Decimal(1).scaleb(-s_dec), rounding=ROUND_DOWN)
    price_r = Decimal(str(max_price)).quantize(
        Decimal(1).scaleb(-p_dec), rounding=ROUND_DOWN)
    if price_r <= 0:
        raise PmSignerError("max_price rounds to zero")
    shares = usd_r / price_r
    step_hi = Decimal(1).scaleb(-(a_dec + 4))
    step_lo = Decimal(1).scaleb(-a_dec)
    shares_r = shares.quantize(step_hi, rounding=ROUND_HALF_UP)
    shares_r = shares_r.quantize(step_lo, rounding=ROUND_HALF_UP)
    min_size = Decimal(str(book.get("min_order_size", 5)))
    if shares_r < min_size:
        raise PmSignerError(
            "market buy yields {} shares, below minimum {}".format(
                shares_r, min_size))

    def micros(value: Decimal) -> int:
        return int((value * 10 ** 6).to_integral_value(rounding=ROUND_DOWN))

    return micros(usd_r), micros(shares_r)


def sign_eoa_order(private_key: str, token_id: str, maker_amount: int,
                   taker_amount: int, side: str, neg_risk: bool = False,
                   salt: Optional[int] = None) -> Tuple[str, Dict]:
    """Sign a v2 EOA order (signatureType 0).

    Returns (signature_hex, order body dict for the /order request).
    """
    _require_eth_account()
    key = private_key.strip()
    if not key.startswith("0x"):
        key = "0x" + key
    wallet = Account.from_key(key).address
    exchange = EXCHANGE_NEG_RISK if neg_risk else EXCHANGE_STANDARD
    salt_val = int(salt) if salt is not None else _safe_salt()
    ts_ms = int(time.time() * 1000)

    domain = dict(DOMAIN_BASE, verifyingContract=exchange)
    msg = {
        "salt": salt_val,
        "maker": wallet,
        "signer": wallet,
        "tokenId": int(str(token_id)),
        "makerAmount": int(maker_amount),
        "takerAmount": int(taker_amount),
        "side": 0 if side.upper() == "BUY" else 1,
        "signatureType": 0,
        "timestamp": ts_ms,
        "metadata": Z32,
        "builder": Z32,
    }
    signed = Account.sign_typed_data(
        private_key=key, domain_data=domain,
        message_types=ORDER_TYPES, message_data=msg)
    sig = signed.signature.hex()
    if not sig.startswith("0x"):
        sig = "0x" + sig

    body = {
        "salt": salt_val,
        "maker": wallet,
        "signer": wallet,
        "tokenId": str(token_id),
        "makerAmount": str(int(maker_amount)),
        "takerAmount": str(int(taker_amount)),
        "side": "BUY" if side.upper() == "BUY" else "SELL",
        "signature": sig,
        "signatureType": 0,
        "timestamp": str(ts_ms),
        "metadata": Z32,
        "builder": Z32,
        "expiration": "0",
    }
    return sig, body


def l2_headers(api_key: str, api_secret: str, api_passphrase: str,
               address: str, method: str, path: str,
               body: str = "") -> Dict[str, str]:
    """L2 HMAC headers (scheme unchanged by the pUSD upgrade)."""
    ts = str(int(time.time()))
    message = "{}{}{}{}".format(ts, method.upper(), path, body)
    secret = base64.b64decode(api_secret)
    mac = hmac.new(secret, message.encode("utf-8"),
                   hashlib.sha256).digest()
    signature = base64.urlsafe_b64encode(mac).decode("ascii")
    return {
        "POLY_ADDRESS": address,
        "POLY_SIGNATURE": signature,
        "POLY_TIMESTAMP": ts,
        "POLY_API_KEY": api_key,
        "POLY_PASSPHRASE": api_passphrase,
        "Content-Type": "application/json",
    }


def post_order(api_key: str, api_secret: str, api_passphrase: str,
               address: str, order_body: Dict, order_type: str = "GTC",
               host: str = CLOB_HOST, defer_exec: bool = False,
               timeout: int = 25) -> Dict:
    """POST /order. Returns the parsed response dict.

    Success shape: {success, errorMsg, orderID, status, makingAmount,
    takingAmount, tradeIDs, transactionsHashes}
    """
    if requests is None:
        raise PmSignerError("requests not installed")
    body = json.dumps({
        "deferExec": defer_exec,
        "order": order_body,
        "orderType": order_type,
        "owner": api_key,
    })
    headers = l2_headers(api_key, api_secret, api_passphrase, address,
                         "POST", "/order", body)
    r = requests.post(host + "/order", data=body, headers=headers,
                      timeout=timeout)
    try:
        data = r.json()
    except ValueError:
        return {"success": False,
                "errorMsg": "HTTP {}: non-JSON response".format(
                    r.status_code),
                "orderID": "", "status": ""}
    if not isinstance(data, dict):
        return {"success": False,
                "errorMsg": "unexpected response: {}".format(str(data)[:200]),
                "orderID": "", "status": ""}
    return data


def bridge_addresses(wallet: str, host: str = BRIDGE_API,
                     timeout: int = 20) -> Optional[Dict]:
    """POST /deposit -> {evm, svm, tron, btc} bridge addresses for a wallet."""
    if requests is None:
        raise PmSignerError("requests not installed")
    try:
        r = requests.post(host + "/deposit",
                          json={"address": wallet}, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except (requests.RequestException, ValueError):
        pass
    return None


def bridge_status(bridge_address: str, host: str = BRIDGE_API,
                  timeout: int = 20) -> Optional[Dict]:
    """GET /status/<bridge_address> -> {transactions: [...]}.

    Each tx: {id, sourceChain, sourceToken, sourceAmount, amount (pUSD),
    status, pUSDReceived, bridgedAt, ...} (field set confirmed live).
    """
    if requests is None:
        raise PmSignerError("requests not installed")
    try:
        r = requests.get(
            "{}/status/{}".format(host, bridge_address), timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except (requests.RequestException, ValueError):
        pass
    return None
