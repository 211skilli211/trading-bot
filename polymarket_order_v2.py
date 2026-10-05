"""
Polymarket CLOB v2 order signing — pUSD era (post 2026-04-28 migration).

The exchange migrated to CTF Exchange V2:
  * domain version "1" -> "2"
  * exchange contracts replaced (see constants below)
  * Order struct replaced: taker/expiration/nonce/feeRateBps removed,
    timestamp/metadata/builder added (12 fields, same order as the docs)
  * API body now wraps the signed order: {deferExec, order, orderType, owner}

Old py-clob-client 0.34.6 signs the v1 struct -> the CLOB rejects it with
"invalid order version, please use the latest clob-client". This module signs
the v2 struct directly (pure Python: eth_account + poly_eip712_structs, both
already installed for py3.8) and posts with standard L2 HMAC headers.

Verified against the official docs:
  https://docs.polymarket.com/trading/place-orders (v2 typed data + /order body)
  https://docs.polymarket.com/resources/contracts (addresses)
  https://github.com/Polymarket/ctf-exchange-v2 (Hashing.sol: domain name/version)
"""
from __future__ import annotations

import json
import secrets
import time
from decimal import Decimal, ROUND_DOWN, ROUND_CEILING, ROUND_HALF_UP

from eth_account import Account
from eth_utils import keccak
from poly_eip712_structs import Address, EIP712Struct, Uint, make_domain
from poly_eip712_structs.types import EIP712Type

# ---------------------------------------------------------------------------
# Verified constants (docs.polymarket.com/resources/contracts, 2026-10-05)
# ---------------------------------------------------------------------------
POLYGON_CHAIN_ID = 137
CTF_EXCHANGE = "0xE111180000d2663C0091e4f400237545B87B996B"      # standard markets
NEG_RISK_EXCHANGE = "0xe2222d279d744050d28e00520010520000310F59"  # neg-risk groups
CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"               # ERC-1155 (unchanged)
PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"             # collateral (proxy)
PUSD_IMPL = "0x6bBCef9f7ef3B6C592c99e0f206a0DE94Ad0925f"
COLLATERAL_ONRAMP = "0x93070a847efEf7F70739046A929D47a521F5B8ee"  # USDC -> pUSD wrap
COLLATERAL_OFFRAMP = "0x2957922Eb93258b93368531d39fAcCA3B4dC5854"  # pUSD -> USDC unwrap
USDC_NATIVE = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"      # supported wrap asset
USDC_BRIDGED = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"     # supported wrap asset (legacy)

DOMAIN_NAME = "Polymarket CTF Exchange"
DOMAIN_VERSION = "2"
ZERO32 = "0x" + "00" * 32


# ---------------------------------------------------------------------------
# bytes32 struct member (poly_eip712_structs ships only dynamic `bytes`)
# ---------------------------------------------------------------------------
class Bytes32(EIP712Type):
    def __init__(self):
        super().__init__("bytes32", 0)

    def _encode_value(self, value):
        if isinstance(value, int):
            b = value.to_bytes(32, "big")
        elif isinstance(value, bytes):
            b = value
        else:
            h = str(value)
            if h.startswith("0x"):
                h = h[2:]
            b = bytes.fromhex(h)
        if len(b) > 32:
            raise ValueError("bytes32 value too long")
        return b.rjust(32, b"\x00")


# ---------------------------------------------------------------------------
# v2 Order struct — field order is part of the signature, keep exact
# ---------------------------------------------------------------------------
class OrderV2(EIP712Struct):
    salt = Uint(256)
    maker = Address()
    signer = Address()
    tokenId = Uint(256)
    makerAmount = Uint(256)
    takerAmount = Uint(256)
    side = Uint(8)
    signatureType = Uint(8)
    timestamp = Uint(256)
    metadata = Bytes32()
    builder = Bytes32()


def _domain(exchange: str):
    return make_domain(
        name=DOMAIN_NAME,
        version=DOMAIN_VERSION,
        chainId=str(POLYGON_CHAIN_ID),
        verifyingContract=exchange,
    )


def exchange_for(neg_risk: bool) -> str:
    return NEG_RISK_EXCHANGE if neg_risk else CTF_EXCHANGE


# ---------------------------------------------------------------------------
# amount math (docs precision table: tick -> price/size/amount decimals)
# ---------------------------------------------------------------------------
def tick_rounding(tick_size) -> tuple:
    t = float(tick_size)
    if abs(t - 0.1) < 1e-12:
        return 1, 2, 3
    if abs(t - 0.01) < 1e-12:
        return 2, 2, 4
    if abs(t - 0.005) < 1e-12:
        return 3, 2, 5
    if abs(t - 0.0025) < 1e-12:
        return 4, 2, 6
    if abs(t - 0.001) < 1e-12:
        return 3, 2, 5
    if abs(t - 0.0001) < 1e-12:
        return 4, 2, 6
    raise ValueError(f"unknown tick size {tick_size}")


def _q(d: Decimal, places: int, mode):
    return d.quantize(Decimal(1).scaleb(-places), rounding=mode)


def amounts_for(side: str, price, size, tick_size) -> tuple:
    """Return (maker_amount_raw, taker_amount_raw) as 6-decimal ints.

    BUY:  maker = USD,   taker = shares
    SELL: maker = shares, taker = USD
    """
    p_dec, s_dec, a_dec = tick_rounding(tick_size)
    p = _q(Decimal(str(price)), p_dec, ROUND_HALF_UP)
    s = _q(Decimal(str(size)), s_dec, ROUND_DOWN)
    usd = p * s
    if usd.as_tuple().exponent < -a_dec:
        usd = _q(usd, a_dec + 4, ROUND_CEILING)
        usd = _q(usd, a_dec, ROUND_DOWN)

    def raw(d: Decimal) -> int:
        return int(_q(d, 6, ROUND_HALF_UP) * 1_000_000)

    if side == "BUY":
        return raw(usd), raw(s)
    if side == "SELL":
        return raw(s), raw(usd)
    raise ValueError(side)


# ---------------------------------------------------------------------------
# signing + API
# ---------------------------------------------------------------------------
def sign_order(
    private_key: str,
    token_id,
    maker_amount_raw: int,
    taker_amount_raw: int,
    side: str,
    neg_risk: bool = False,
    signature_type: int = 0,
    builder: str = ZERO32,
) -> dict:
    """Sign a v2 order. Returns the JSON 'order' object for the /order body."""
    acct = Account.from_key(private_key)
    addr = acct.address.lower()
    sign_hash = lambda d: Account._sign_hash(d, private_key)
    salt = secrets.randbelow(2 ** 52)
    ts_ms = int(time.time() * 1000)

    o = OrderV2(
        salt=salt,
        maker=addr,
        signer=addr,
        tokenId=int(token_id),
        makerAmount=int(maker_amount_raw),
        takerAmount=int(taker_amount_raw),
        side=0 if side == "BUY" else 1,
        signatureType=signature_type,
        timestamp=ts_ms,
        metadata=ZERO32,
        builder=builder,
    )
    digest = keccak(o.signable_bytes(domain=_domain(exchange_for(neg_risk))))
    sig = "0x" + sign_hash(digest).signature.hex()

    return {
        "builder": builder,
        "expiration": "0",
        "maker": o["maker"],
        "makerAmount": str(o["makerAmount"]),
        "metadata": o["metadata"],
        "salt": int(o["salt"]),
        "side": "BUY" if side == "BUY" else "SELL",
        "signature": sig,
        "signatureType": signature_type,
        "signer": o["signer"],
        "takerAmount": str(o["takerAmount"]),
        "timestamp": str(o["timestamp"]),
        "tokenId": str(o["tokenId"]),
    }


def build_body(order: dict, order_type: str, api_key: str, post_only: bool = False,
               expiration: str = "0") -> dict:
    order = dict(order)
    if order_type in ("GTC", "GTD") and expiration:
        order["expiration"] = expiration
    if post_only:
        order["postOnly"] = True
    return {"deferExec": False, "order": order, "orderType": order_type, "owner": api_key}


def l2_headers(api_key, api_secret, api_passphrase, address, method, path, body: str):
    from py_clob_client.signing.hmac import build_hmac_signature
    ts = int(time.time())
    return {
        "POLY_ADDRESS": address,
        "POLY_SIGNATURE": build_hmac_signature(api_secret, ts, method, path, body),
        "POLY_TIMESTAMP": str(ts),
        "POLY_API_KEY": api_key,
        "POLY_PASSPHRASE": api_passphrase,
        "Content-Type": "application/json",
    }


def _client_creds(clob_client):
    creds = clob_client.create_or_derive_api_creds()
    clob_client.set_api_creds(creds)
    return creds


def post_order(clob_client, order: dict, order_type: str = "GTC", post_only: bool = False,
               expiration: str = "0", host: str = "https://clob.polymarket.com"):
    """POST /order with L2 auth. Returns the raw response dict."""
    import requests
    creds = _client_creds(clob_client)
    body = build_body(order, order_type, creds.api_key, post_only, expiration)
    serialized = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    headers = l2_headers(
        creds.api_key, creds.api_secret, creds.api_passphrase,
        clob_client.signer.address(), "POST", "/order", serialized,
    )
    r = requests.post(host + "/order", data=serialized, headers=headers, timeout=30)
    try:
        return r.json()
    except Exception:
        return {"success": False, "errorMsg": f"HTTP {r.status_code}: {r.text[:300]}"}


def cancel_order(clob_client, order_id: str, host: str = "https://clob.polymarket.com"):
    """DELETE /order/{id} with L2 auth. Returns the raw response dict."""
    import requests
    creds = _client_creds(clob_client)
    serialized = json.dumps({"orderID": order_id}, separators=(",", ":"), ensure_ascii=False)
    headers = l2_headers(
        creds.api_key, creds.api_secret, creds.api_passphrase,
        clob_client.signer.address(), "DELETE", f"/order/{order_id}", serialized,
    )
    r = requests.delete(host + "/order/" + order_id, data=serialized, headers=headers, timeout=30)
    try:
        return r.json()
    except Exception:
        return {"success": r.status_code == 200, "errorMsg": f"HTTP {r.status_code}: {r.text[:300]}"}


if __name__ == "__main__":
    print("module loads ok; exchange =", CTF_EXCHANGE, "domain v", DOMAIN_VERSION)
    print("pUSD =", PUSD)
