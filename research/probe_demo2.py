#!/usr/bin/env python3
"""Comprehensive demo-visibility diagnostic.

Checks:
  1. Access token freshness + validity (authenticated trader_info on the
     KNOWN live account proves the token + app creds work end-to-end).
  2. Full raw account-list payload on BOTH hosts (every field, every entry).
  3. Whether the demo host truly mirrors the live cluster.
"""
import sys, time, datetime
sys.path.insert(0, "/workspace/clever-curie")

from ctrader_connector import (resolve_credentials, CTraderSession,
                               CTraderError, ensure_fresh_token)

creds, store = resolve_credentials()
assert not creds["missing"], creds["missing"]
creds = ensure_fresh_token(creds, store)

# --- token freshness ------------------------------------------------------
exp = int(creds.get("access_token_expires_at") or 0)
now = int(time.time())
print(f"access_token_expires_at: {exp}  ({exp - now:+d}s from now)")

LIVE_CTID = 47848046
DEMO_LOGIN = 6004342


def raw_list(demo: bool):
    s = CTraderSession(creds, account_id=None, demo=demo,
                       use_default_account=False)
    results = s.execute([lambda s, r: s.account_list()], hard_timeout=40)
    res = results[1]
    tag = "demo" if demo else "live"
    print(f"\n[{tag}] GetAccountListByAccessTokenRes "
          f"(permissionScope={res.permissionScope}, "
          f"{len(res.ctidTraderAccount)} account(s)):")
    for a in res.ctidTraderAccount:
        print(f"    ctid={a.ctidTraderAccountId}  isLive={a.isLive}  "
              f"login={a.traderLogin}  lastDeal={a.lastClosingDealTimestamp}  "
              f"lastBal={a.lastBalanceUpdateTimestamp}")
    return [a for a in res.ctidTraderAccount]


def token_works(demo: bool):
    """Auth the KNOWN live account on this host: proves token+creds+host."""
    s = CTraderSession(creds, account_id=str(LIVE_CTID), demo=demo)
    tag = "demo" if demo else "live"
    try:
        results = s.execute([lambda s, r: s.trader_info()], hard_timeout=40)
        t = results[1]
        mdig = getattr(t, "moneyDigits", 2)
        bal = getattr(t, "balance", 0) / (10 ** mdig)
        print(f"[{tag}] live-account trader_info OK -> balance=${bal} "
              f"(token+creds valid on this host)")
        return True
    except CTraderError as e:
        print(f"[{tag}] live-account trader_info FAILED -> {e.code}: {e.description}")
        return False


print("=" * 60)
print("1) Token validity (auth the known live account on each host)")
print("=" * 60)
token_works(False)
token_works(True)

print("\n" + "=" * 60)
print("2) Full account list on each host")
print("=" * 60)
live_accts = raw_list(False)
demo_accts = raw_list(True)

print("\n" + "=" * 60)
print("3) Verdict")
print("=" * 60)
demo_in_list = any(a.traderLogin == DEMO_LOGIN for a in live_accts + demo_accts)
print(f"demo login {DEMO_LOGIN} present in either list: {demo_in_list}")
ctids = {a.ctidTraderAccountId: a.isLive for a in live_accts + demo_accts}
print("all ctids seen (ctid -> isLive):", ctids)
