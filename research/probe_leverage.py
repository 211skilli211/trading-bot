#!/usr/bin/env python3
"""Leverage ground-truth probe.

For LIVE (47848046) and DEMO (49028696):
  1. raw trader fields (leverageInCents, maxLeverage, moneyDigits, balance)
  2. full symbol specs for the available subset of 6 symbols
  3. ExpectedMargin at each symbol's minVolume
  4. spot prices
  => effective leverage per symbol = notional / margin, under the QCG
     volume convention (1.0 lot = lotSize raw units).
"""
import sys
sys.path.insert(0, "/workspace/clever-curie")

from twisted.internet.defer import Deferred
from ctrader_connector import (resolve_credentials, CTraderSession,
                               CTraderError, ensure_fresh_token, MSG,
                               price_float, money_float)

creds, store = resolve_credentials()
assert not creds.get("missing"), creds
creds = ensure_fresh_token(creds, store)

SYMS = ["EURUSD", "XAUUSD", "BTCUSD", "ETHUSD", "BCHUSD", "US30"]
# contract size: how many underlying units 1.0 QCG lot represents
UNITS_PER_LOT = {
    "EURUSD": 100000.0,   # currency units
    "XAUUSD": 10.0,       # troy ounces
    "BTCUSD": 1.0,        # BTC
    "ETHUSD": 100.0,      # ETH
    "BCHUSD": 100.0,      # BCH
    "US30": 10.0,         # index points
}


EXCLUDE = {"LIVE": set(), "DEMO": {"BCHUSD"}}  # demo gateway can't quote BCH


def probe(demo, ctid, tag):
    s = CTraderSession(creds, account_id=str(ctid), demo=demo)
    found = {}
    syms = [n for n in SYMS if n not in EXCLUDE[tag]]

    def step_trader(s, r):
        return s.trader_info()

    def step_syms(s, r):
        return s.symbol_list()

    def step_specs(s, r):
        names = {a.symbolName: int(a.symbolId) for a in r[2].symbol}
        avail = [n for n in syms if n in names]
        found.update({n: names[n] for n in avail})
        if len(avail) < len(syms):
            print("  (skipping unavailable on %s: %s)" % (
                tag, [n for n in syms if n not in names]))
        return s.joined_symbol_views([names[n] for n in avail])

    def step_spot(s, r):
        def _spot():
            return s.spot_snapshot(list(found.values()), wait_seconds=7)

        d = _spot()

        def _ok(_res):
            return _res

        def _err(failure):
            print("  (spot snapshot failed: %s)"
                  % failure.getErrorMessage())
            return None

        return d.addCallback(_ok).addErrback(_err)

    def make_margin(i):
        def step(s, r):
            n = syms[i]
            spec = next((v for v in r[3].values() if v.symbolName == n),
                        None)
            if spec is None:
                return None
            req = MSG.ProtoOAExpectedMarginReq(
                ctidTraderAccountId=s._acct(),
                symbolId=int(spec.symbolId))
            req.volume.extend([int(spec.minVolume)])
            return s._ok(s._send(req, timeout=20))
        return step

    steps = [step_trader, step_syms, step_specs, step_spot]
    steps += [make_margin(i) for i in range(len(syms))]
    r = s.execute(steps, hard_timeout=120)

    t = r[1].trader
    print(f"\n=== [{tag}] account {ctid} ===")
    print("trader raw fields:")
    for f, v in t.ListFields():
        if f.name in ("leverageInCents", "maxLeverage", "moneyDigits",
                      "balance", "equity", "usedMargin", "freeMargin",
                      "brokerName", "swapFree", "isLimitedRisk"):
            print(f"  {f.name} = {v}")

    specs = {v.symbolName: v for v in r[3].values()}
    print(f"{'sym':8} {'lotSize':>10} {'minVol':>8} {'step':>8} "
          f"{'price':>12} {'minMargin$':>11} {'L_eff':>8}")
    for i, n in enumerate(syms):
        mres = r[5 + i]
        if n not in specs or mres is None:
            continue
        spec = specs[n]
        lot = int(spec.lotSize)
        mn = int(spec.minVolume)
        st = int(spec.stepVolume)
        sp = s.spots.get(found[n]) or {}
        px = price_float(sp.get("bid_raw")) if sp.get("bid_raw") else None
        md = int(mres.moneyDigits or 2)
        m = money_float(mres.margin[0].buyMargin, md)
        raw_per_lot = lot // 100 if lot >= 100 else 1
        upr = UNITS_PER_LOT[n] / raw_per_lot
        if px:
            notional = mn * upr * px
            leff = notional / m if m else float("nan")
            print(f"{n:8} {lot:>10} {mn:>8} {st:>8} {px:>12.5f} "
                  f"{m:>11,.2f} {leff:>8.2f}"
                  f"   (min={mn/raw_per_lot:.3f} lot, "
                  f"notional=${notional:,.2f})")
        else:
            print(f"{n:8} {lot:>10} {mn:>8} {st:>8} {'n/a':>12} "
                  f"{m:>11,.2f} {'n/a':>8}")


for demo, ctid, tag in ((False, 47848046, "LIVE"), (True, 49028696, "DEMO")):
    if len(sys.argv) > 1 and sys.argv[1] != tag.lower():
        continue
    try:
        probe(demo, ctid, tag)
    except CTraderError as e:
        print(f"[{tag}] FAILED: {e.code}: {e.description}")
