#!/usr/bin/env python3
"""Probe: is the QCG demo account (login 6004342) visible / reachable via the
cTrader Open API gateways?

Checks, on BOTH live.ctraderapi.com and demo.ctraderapi.com:
  1. Fresh app-level account list (ctid + isLive + traderLogin per account).
  2. Direct account-auth with ctidTraderAccountId = 6004342 (wild guess:
     maybe the demo's ctid equals its login number). If it authenticates,
     that's the account — dump the Trader.
Also dumps the SDK's known endpoint hosts.
"""
import sys
sys.path.insert(0, "/workspace/clever-curie")

from ctrader_connector import resolve_credentials, CTraderSession, CTraderError
from ctrader_open_api.endpoints import EndPoints

creds, _store = resolve_credentials()
assert not creds["missing"], creds["missing"]

DEMO_LOGIN = 6004342

print("SDK endpoints:",
      {k: getattr(EndPoints, k) for k in dir(EndPoints) if not k.startswith("_")})
print()


def app_level_list(demo: bool):
    s = CTraderSession(creds, account_id=None, demo=demo,
                       use_default_account=False)
    results = s.execute([lambda s, r: s.account_list()], hard_timeout=40)
    res = results[1]
    tag = "demo" if demo else "live"
    print(f"[{tag}] app-level account list ({len(res.ctidTraderAccount)}):")
    for a in res.ctidTraderAccount:
        print(f"    ctid={a.ctidTraderAccountId}  isLive={a.isLive}  "
              f"login={a.traderLogin}  lastDeal={a.lastClosingDealTimestamp} "
              f"lastBal={a.lastBalanceUpdateTimestamp}")
    print()


def direct_auth(demo: bool, ctid: int):
    s = CTraderSession(creds, account_id=str(ctid), demo=demo)
    tag = "demo" if demo else "live"
    try:
        results = s.execute([lambda s, r: s.trader_info()], hard_timeout=40)
        t = results[1]
        print(f"[{tag}] DIRECT AUTH ctid={ctid}: *** SUCCESS ***")
        print(f"    trader: {t}")
        return True
    except CTraderError as e:
        print(f"[{tag}] DIRECT AUTH ctid={ctid}: failed -> {e.code}: {e.description}")
        return False


app_level_list(False)
app_level_list(True)
direct_auth(False, DEMO_LOGIN)
direct_auth(True, DEMO_LOGIN)
