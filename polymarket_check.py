#!/usr/bin/env python3
"""
Polymarket connection check — verifies the restored CLOB credentials.

Reads POLYMARKET_* from .env (via python-dotenv), then:
  1. Derives the wallet address from the private key
  2. Sets L2 API credentials (api key / secret / passphrase)
  3. Calls a private L2-authenticated endpoint (GET /data/orders)
  4. Pulls a public order book as a sanity check

Exit codes: 0 = credentials verified, 1 = auth failure, 2 = other error.
"""
import sys
import json

from dotenv import load_dotenv

load_dotenv()

import os

API_KEY = os.environ.get("POLYMARKET_API_KEY")
API_SECRET = os.environ.get("POLYMARKET_API_SECRET")
API_PASSPHRASE = os.environ.get("POLYMARKET_API_PASSPHRASE")
PRIVATE_KEY = os.environ.get("POLYMARKET_PRIVATE_KEY")
HOST = "https://clob.polymarket.com"

if not all([API_KEY, API_SECRET, API_PASSPHRASE, PRIVATE_KEY]):
    print("MISSING CREDENTIALS: need POLYMARKET_API_KEY/SECRET/PASSPHRASE/PRIVATE_KEY in .env")
    sys.exit(2)

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

client = ClobClient(HOST, key=PRIVATE_KEY, chain_id=137)
address = client.get_address()
print(f"wallet address: {address}")

creds = ApiCreds(api_key=API_KEY, api_secret=API_SECRET, api_passphrase=API_PASSPHRASE)
client.set_api_creds(creds)

# L2-authenticated private endpoint: list our open orders
try:
    orders = client.get_orders()
    print(f"L2 auth OK — GET /data/orders returned {len(orders)} open order(s)")
    for o in orders[:5]:
        print(json.dumps({k: o.get(k) for k in ("id", "status", "side", "size", "price") if k in o}))
except Exception as e:
    print(f"L2 AUTH FAILED: {type(e).__name__}: {e}")
    sys.exit(1)

# Public sanity: top of book on one active market
try:
    import requests as rq
    data = rq.get(HOST + "/sampling-markets", timeout=30).json().get("data", [])
    tok = None
    for m in data:
        ts = m.get("tokens")
        if isinstance(ts, list) and ts:
            tok = ts[0].get("token_id"); break
        elif isinstance(ts, dict) and ts:
            tok = ts[0]
    book = client.get_order_book(token_id=tok)
    bids = getattr(book, "bids", []) or []
    asks = getattr(book, "asks", []) or []
    best_bid = bids[-1] if bids else None
    best_ask = asks[-1] if asks else None
    print(f"public book OK — token={tok[:16]}... best bid={best_bid} best ask={best_ask}")
except Exception as e:
    print(f"PUBLIC BOOK CHECK FAILED (non-fatal): {type(e).__name__}: {e}")

print("POLYMARKET CONNECTED")
