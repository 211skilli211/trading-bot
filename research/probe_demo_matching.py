#!/usr/bin/env python3
"""Demo matching probe: can QCG's demo book fill ANY order?

Context: demo market order 1056040 (2026-10-04) was accepted then
engine-cancelled with no fill, and the demo book is frozen at 2024-09-26.
This places a LIMIT BUY 0.01 BTC at the current frozen ask price.

  - fills immediately  -> the book CAN match at/beyond the frozen quotes
  - rests / cancels    -> the demo book is fully static; QCG demo cannot
                          execute orders at all (account plumbing only)

Any resulting position or pending order is closed/cancelled so the demo
account is left clean.

RESULT (2026-10-04): the LIMIT BUY 1056041 at the frozen ask (63780.033)
was accepted, then CANCELLED by the engine with no fill — same as the
market order 1056040. QCG's demo book is fully static: the demo matching
engine cancels orders instead of matching them. Demo = account/margin
plumbing only; it cannot execute trades.
"""
import sys
sys.path.insert(0, "/workspace/clever-curie")
from ctrader_connector import (resolve_credentials, ensure_fresh_token,
                               CTraderSession, CTraderError, SIDE_BUY,
                               ORDER_TYPE_LIMIT, summarize_executions,
                               price_float)

creds, store = resolve_credentials()
creds = ensure_fresh_token(creds, store)
s = CTraderSession(creds, account_id="49028696", demo=True)

state = {}


def step_symbols(_s, _r):
    return s.symbol_list()


def step_spot(_s, r):
    names = {a.symbolName: int(a.symbolId) for a in r[1].symbol}
    state["sid"] = names["BTCUSD"]
    return s.spot_snapshot([state["sid"]], wait_seconds=6)


def step_place(_s, _r):
    sp = s.spots.get(state["sid"]) or {}
    bid = price_float(sp.get("bid_raw")) if sp.get("bid_raw") else None
    ask = price_float(sp.get("ask_raw")) if sp.get("ask_raw") else None
    print(f"frozen demo book: bid={bid} ask={ask}")
    state["ask"] = ask
    # demo BTC: lotSize=100 -> 0.01 lot = 1 raw unit (minVolume)
    return s.place_order(state["sid"], SIDE_BUY, 1,
                         order_type=ORDER_TYPE_LIMIT, price=ask,
                         comment="demo matching probe",
                         watch_seconds=10)


def step_state(_s, _r):
    return s.open_orders()


r1 = s.execute([step_symbols, step_spot, step_place, step_state],
               hard_timeout=120)
execs = summarize_executions(r1[3])
print("exec events during the 10s watch window:")
for e in execs or []:
    print("  ", e)
orders = list(r1[4].order) if r1[4] else []
print("order state after window:")
for o in orders:
    print(f"   order={o.orderId} status={o.orderStatus} "
          f"executed={o.executedVolume}")

# phase 2: positions + cleanup
r2 = s.execute([lambda _s, _r: s.open_positions()], hard_timeout=60)
positions = list(r2[1].position) if r2[1] else []
print("positions:")
for p in positions:
    print(f"   position={p.positionId} {p.tradeData.symbolId} "
          f"vol={p.tradeData.volume}")

cleanup = []
for o in orders:
    if int(o.executedVolume) == 0:
        cleanup.append(("cancel", int(o.orderId)))
for p in positions:
    cleanup.append(("close", int(p.positionId)))
if cleanup:
    print("cleanup:", cleanup)

    idx = [0]

    def step_cleanup(_s, _r):
        kind, ident = cleanup[idx[0]]
        idx[0] += 1
        if kind == "cancel":
            return s.cancel_order(ident)
        return s.close_position(ident)

    for _ in cleanup:
        r3 = s.execute([step_cleanup], hard_timeout=60)
        for e in summarize_executions(r3[1]) or []:
            print("  ", e)

# final state
r4 = s.execute([lambda _s, _r: s.open_positions(),
                lambda _s, _r: s.open_orders()], hard_timeout=60)
print("final: positions=%d open_orders=%d"
      % (len(list(r4[1].position)), len(list(r4[2].order))))
