#!/usr/bin/env python3
"""Live cTrader calibration: symbol specs, price scaling, margins, leverage.

Run:  python3 research/ct_calibration.py
Uses stored credentials + default account (live or per --demo).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ctrader_connector as ct
from ctrader_connector import CTraderError, normalize_name
from ctrader_open_api.messages import OpenApiMessages_pb2 as MSG

WANT = ["BTCUSD", "ETHUSD", "BCHUSD", "EURUSD", "EURGBP", "XAUUSD",
        "US30", "NAS100"]
MARGIN_VOLUMES = [1, 10, 100, 1000]


def main():
    demo = "--demo" in sys.argv
    creds, store = ct.resolve_credentials()
    ct.ensure_fresh_token(creds, store)
    acc = int(creds.get("account_id") or 0)
    if not acc:
        sys.exit("no default account set — run --ctrader-account first")
    print(f"account={acc} demo={demo}")

    s = ct.CTraderSession(creds, account_id=acc, demo=demo)
    out = {"found": {}}

    def step_list(_s, _r):
        return _s.symbol_list()

    def step_full(_s, r):
        lst = r[-1]
        want = {normalize_name(w) for w in WANT}
        for sym in lst.symbol:
            k = normalize_name(sym.symbolName)
            if sym.enabled and k in want:
                out["found"][k] = int(sym.symbolId)
        print("matched symbols:", json.dumps(out["found"], indent=1))
        if not out["found"]:
            sys.exit("no wanted symbols matched")
        return _s.symbols_by_id(list(out["found"].values()))

    def step_trader(_s, _r):
        return _s.trader_info()

    def step_spot(_s, _r):
        return _s.spot_snapshot(list(out["found"].values()), wait_seconds=5)

    def step_bars(_s, _r):
        bid = out["found"].get(normalize_name("BTCUSD"))
        if not bid:
            return None
        return _s.historical_bars(bid, period="H1", count=3)

    def make_margin_step(name):
        def f(_s, _r):
            sid = out["found"].get(normalize_name(name))
            if not sid:
                return None
            req = MSG.ProtoOAExpectedMarginReq(
                ctidTraderAccountId=acc, symbolId=sid)
            req.volume.extend(MARGIN_VOLUMES)
            return _s._ok(_s._send(req, timeout=10))
        return f

    steps = [step_list, step_full, step_trader, step_spot, step_bars]
    steps += [make_margin_step(w) for w in WANT]

    res = s.execute(steps)
    # res[0]=handshake, 1=list, 2=full, 3=trader, 4=spot, 5=bars, 6..=margins

    full = {int(x.symbolId): x for x in res[2].symbol} if res[2] else {}
    print("\n=== TRADER ===")
    t = res[3].trader if hasattr(res[3], "trader") else res[3]
    print(f"  broker={t.brokerName} login={t.traderLogin} "
          f"accountType={t.accountType} depositAssetId={t.depositAssetId}")
    print(f"  balance_cents={t.balance} moneyDigits={t.moneyDigits} "
          f"leverageInCents={t.leverageInCents} maxLeverage={t.maxLeverage} "
          f"totalMarginCalc={t.totalMarginCalculationType}")

    print("\n=== SYMBOL SPECS ===")
    for name, sid in sorted(out["found"].items()):
        sym = full.get(sid)
        if not sym:
            print(f"  {name} ({sid}): NO FULL SPEC")
            continue
        print(f"  {name} id={sid} digits={sym.digits} "
              f"minVol={sym.minVolume} step={sym.stepVolume} "
              f"maxVol={sym.maxVolume} lotSize={sym.lotSize} "
              f"slDist={sym.slDistance} tpDist={sym.tpDistance} "
              f"distSet={sym.distanceSetIn} comm={sym.commission} "
              f"commType={sym.commissionType} swapL={sym.swapLong} "
              f"swapS={sym.swapShort} shortOK={sym.enableShortSelling}")

    print("\n=== SPOT (raw) ===")
    spot = res[4] or {}
    for name, sid in sorted(out["found"].items()):
        raw = spot.get(sid)
        if not raw:
            print(f"  {name}: no spot")
            continue
        d = full[sid].digits
        for k in ("bid", "ask"):
            if k in raw:
                v = raw[k]
                print(f"  {name} {k}: raw={v} -> /10^{d}={v / 10**d:.5f}")

    print("\n=== BTCUSD H1 BARS (raw) ===")
    bars = res[5]
    if bars:
        import datetime
        for b in bars.trendbar:
            ts = datetime.datetime.fromtimestamp(
                b.utcTimestampInMinutes * 60, tz=datetime.timezone.utc)
            print(f"  {ts.isoformat()} low={b.low} dO={b.deltaOpen} "
                  f"dH={b.deltaHigh} dC={b.deltaClose} vol={b.volume}")

    print("\n=== EXPECTED MARGIN (USD) ===")
    for i, name in enumerate(WANT):
        m = res[6 + i]
        if not m:
            print(f"  {name}: none")
            continue
        print(f"  {name}: (moneyDigits={m.moneyDigits})")
        for em in m.margin:
            print(f"    vol={em.volume} ({em.volume/100:.2f} lots): "
                  f"buy=${em.buyMargin/10**m.moneyDigits:,.2f} "
                  f"sell=${em.sellMargin/10**m.moneyDigits:,.2f}")

    # cross-check BTC vs Binance
    try:
        import ccxt
        bx = ccxt.binance()
        tk = bx.fetch_ticker("BTC/USDT")
        print(f"\nBinance BTC/USDT last={tk['last']:.2f} "
              f"(high={tk['high']:.2f} low={tk['low']:.2f})")
    except Exception as e:
        print(f"\nbinance cross-check failed: {e}")


if __name__ == "__main__":
    main()
