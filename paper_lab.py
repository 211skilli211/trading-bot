#!/usr/bin/env python3
"""
Live Paper-Trading Lab
======================
Runs the sweep-validated strategies against *live* exchange data on a
simulated account, using the EXACT same per-bar engine as the backtester
(``nautilus_integration.step_bars``) — so paper fills are backtest
semantics by construction: same slippage, same fees, same SL/TP rules,
same sizing.

What it is / is not
-------------------
- Live quotes/bars from the exchange (default: Binance public OHLCV, no keys).
- Simulated fills only — no orders ever leave this machine.
- State persists between runs in ``data/paper_state.json`` (equity, open
  position, trade log, last-processed-bar timestamp).
- Not a replacement for backtesting: use the sweep + backtester to validate
  edge; use this lab to watch the strategy operate on the live tape.

Default slots (the two cross-validated winners of the 365-day sweep,
see ``research/strategy_sweep_report.md``):

- ``eth-1d``  ETH/USDT 1d  regime_momentum lb=20 thr=5%  ema=5/20  SL/TP 5%/10%
              5% position sizing — +4.16%/365d, Sharpe 1.64, 46 trades,
              cross-validated on BTC (+0.70%, Sharpe 0.40)
- ``eth-4h``  ETH/USDT 4h  regime_momentum lb=10 thr=0.5%  ema=50/100  SL/TP 15%/30%
              1% position sizing — +0.81%/365d, Sharpe 1.42, 16 trades,
              cross-validated on BTC (+0.41%, Sharpe 1.00)

Usage (via main CLI or standalone):
    python3 trading_bot.py --paper-run            # process new closed bars, print dashboard
    python3 trading_bot.py --paper-status        # offline view of saved state
    python3 trading_bot.py --paper-reset --yes   # re-initialize at --paper-capital
    python3 trading_bot.py --paper-monitor 900   # run every 15 min, forever
    python3 paper_lab.py                          # standalone = --paper-run
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional

from nautilus_integration import (
    INTERVAL_MS,
    NautilusConfig,
    NautilusDataAdapter,
    bars_per_day,
    get_strategy,
    step_bars,
)

logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "data", "paper_state.json")
DEFAULT_CAPITAL = 10_000.0
DEFAULT_EXCHANGE = "binance"

#: How many bars of history to keep feeding the strategy on every run
#: (must cover strategy warmup; ~matches the sweep's data window).
FETCH_WINDOW = {"1d": 365, "4h": 220, "1h": 660}

# ── Default slots: the cross-validated sweep winners ─────────────────────────

SLOTS: List[Dict[str, Any]] = [
    {
        "name": "eth-1d",
        "symbol": "ETH/USDT",
        "tf": "1d",
        "strategy": "regime_momentum",
        "strategy_config": {
            "lookback": 20,
            "momentum_threshold": 0.05,
            "ema_fast": 5,
            "ema_slow": 20,
            "max_position_pct": 0.05,
        },
        "sl": 0.05,
        "tp": 0.10,
        "warmup_bars": FETCH_WINDOW["1d"],
        "stats": "+4.16%/365d sharpe=1.64 46tr  xval BTC +0.70%",
    },
    {
        "name": "eth-4h",
        "symbol": "ETH/USDT",
        "tf": "4h",
        "strategy": "regime_momentum",
        "strategy_config": {
            "lookback": 10,
            "momentum_threshold": 0.005,
            "ema_fast": 50,
            "ema_slow": 100,
        },  # no max_position_pct -> regime default (1%)
        "sl": 0.15,
        "tp": 0.30,
        "warmup_bars": FETCH_WINDOW["4h"],
        "stats": "+0.81%/365d sharpe=1.42 16tr  xval BTC +0.41%",
    },
]


# ── bars ──────────────────────────────────────────────────────────────────────


def filter_closed_bars(bars: List[Dict], tf: str, now_ms: Optional[int] = None) -> List[Dict]:
    """Drop the in-progress (still-open) candle.

    A bar with open-time ``ts`` closes at ``ts + step_ms``; it is only
    tradeable-once-known after that instant.
    """
    step_ms = INTERVAL_MS.get(tf, 3_600_000)
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    return [b for b in bars if b["timestamp"] + step_ms <= now_ms]


def slot_cfg(slot: Dict[str, Any]) -> NautilusConfig:
    return NautilusConfig(
        symbol=slot["symbol"],
        days=1,
        interval=slot["tf"],
        commission_pct=0.001,
        slippage_pct=0.0005,
        stop_loss_pct=slot["sl"],
        take_profit_pct=slot["tp"],
        strategy_name=slot["strategy"],
        strategy_config=dict(slot["strategy_config"]),
        use_synthetic_fallback=False,
    )


def fetch_slot_bars(
    slot: Dict[str, Any],
    last_ts_ms: int = 0,
    exchange: str = DEFAULT_EXCHANGE,
    now_ms: Optional[int] = None,
) -> List[Dict]:
    """Fetch closed bars covering the strategy window + everything since the
    last processed bar (so a long absence still replays the missed bars)."""
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    tf = slot["tf"]
    bpd = bars_per_day(tf)
    step_ms = INTERVAL_MS.get(tf, 3_600_000)
    window = slot.get("warmup_bars", FETCH_WINDOW.get(tf, 200))
    missed = int((now_ms - last_ts_ms) / step_ms) + 2 if last_ts_ms else 0
    total = window + missed
    days = int(math.ceil(total / bpd)) + 1

    adapter = NautilusDataAdapter(NautilusConfig(
        symbol=slot["symbol"], days=days, interval=tf,
        use_synthetic_fallback=False,
    ))
    bars = adapter.fetch_historical_data(
        symbol=slot["symbol"], days=days, interval=tf,
        exchange_id=exchange, use_cache=False,
    )
    bars = filter_closed_bars(bars, tf, now_ms)
    if len(bars) > total:
        bars = bars[-total:]
    return bars


# ── state ─────────────────────────────────────────────────────────────────────


def load_state() -> Optional[Dict[str, Any]]:
    if not os.path.exists(STATE_PATH):
        return None
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE_PATH)


def init_slot_state(slot: Dict[str, Any], bars: List[Dict], capital: float) -> Dict[str, Any]:
    """First run: adopt the strategy as of the latest closed bar, FLAT.

    Historical bars are warmup only — the account starts fresh 'now', which
    is what a paper account should do (no replaying a year of trades).
    """
    return {
        "equity": capital,
        "initial_capital": capital,
        "position": None,
        "trades": [],
        "fees_paid": 0.0,
        "last_processed_ts": bars[-1]["timestamp"] if bars else 0,
        "runs": 0,
    }


def _resume_position(position: Optional[Dict]) -> Optional[Dict]:
    """Mark a persisted position's entry as 'in the past' so SL/TP is live on
    every bar of the upcoming batch."""
    if position is None:
        return None
    p = dict(position)
    p["entry_idx"] = -1
    return p


# ── the run ──────────────────────────────────────────────────────────────────


def run_slot(
    slot: Dict[str, Any],
    state: Optional[Dict[str, Any]],
    capital: float,
    exchange: str = DEFAULT_EXCHANGE,
    now_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """Process new closed bars for one slot. Returns a report dict; the slot's
    updated state is in the global state (caller persists)."""
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    bars = fetch_slot_bars(slot, 0 if not state else state.get("last_processed_ts", 0),
                           exchange, now_ms)
    if not bars:
        return {"slot": slot["name"], "error": "no market data"}

    last_ts = bars[-1]["timestamp"]

    if state is None:
        st = init_slot_state(slot, bars, capital)
        return {"slot": slot["name"], "adopted": True, "new_bars": 0,
                "state": st, "last_ts": last_ts}

    if state.get("last_processed_ts", 0) >= last_ts:
        return {"slot": slot["name"], "new_bars": 0, "state": state, "last_ts": last_ts}

    # split: warmup (already priced into state) vs. new bars to trade
    last_ts_saved = state.get("last_processed_ts", 0)
    k = 0
    while k < len(bars) and bars[k]["timestamp"] <= last_ts_saved:
        k += 1
    gap = last_ts_saved > 0 and k == 0

    strategy = get_strategy(slot["strategy"], dict(slot["strategy_config"]))
    for b in bars[:k]:
        strategy.on_bar(b)  # warmup only — these bars are already priced in

    st: Dict[str, Any] = {
        "equity": float(state["equity"]),
        "position": _resume_position(state.get("position")),
        "trades": list(state.get("trades", [])),
        "fees_paid": float(state.get("fees_paid", 0.0)),
    }
    n_trades_before = len(st["trades"])
    step_bars(st, strategy, bars[k:], slot_cfg(slot))

    out_state = {
        "equity": st["equity"],
        "initial_capital": state.get("initial_capital", capital),
        "position": st["position"],
        "trades": st["trades"],
        "fees_paid": st["fees_paid"],
        "last_processed_ts": last_ts,
        "runs": int(state.get("runs", 0)) + 1,
        "last_run_ts": now_ms,
    }
    return {
        "slot": slot["name"],
        "adopted": False,
        "new_bars": len(bars) - k,
        "gap": gap,
        "new_trades": st["trades"][n_trades_before:],
        "state": out_state,
        "last_ts": last_ts,
    }


def run_all(capital: float = DEFAULT_CAPITAL, exchange: str = DEFAULT_EXCHANGE,
            slots: Optional[List[Dict]] = None, now_ms: Optional[int] = None) -> Dict[str, Any]:
    """Run every slot once; persist combined state; return it."""
    slots = slots or SLOTS
    old = load_state()
    old_slots = (old or {}).get("slots", {})
    state = {"slots": old_slots, "created_ts": (old or {}).get("created_ts", now_ms or int(time.time() * 1000))}
    reports: List[Dict[str, Any]] = []
    for slot in slots:
        rep = run_slot(slot, state["slots"].get(slot["name"]), capital, exchange, now_ms)
        if "error" in rep:
            logger.warning("[paper] %s: %s", rep["slot"], rep["error"])
            reports.append(rep)
            continue
        state["slots"][slot["name"]] = rep["state"]
        reports.append(rep)
    save_state(state)
    return {"state": state, "reports": reports}


# ── display ───────────────────────────────────────────────────────────────────


def _iso(ms: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ms / 1000.0)) + " UTC"


def _slot_line(slot: Dict[str, Any], st: Dict[str, Any], live_price: Optional[float] = None) -> List[str]:
    lines: List[str] = []
    eq = st["equity"]
    init = st.get("initial_capital", eq)
    ret = (eq / init - 1) * 100 if init else 0.0
    pos = st.get("position")
    name = f'[{slot["name"]}] {slot["symbol"]} {slot["tf"]} · {slot["strategy"]}'
    p = slot["strategy_config"]
    size = p.get("max_position_pct")
    sig = (f'lb={p.get("lookback")} thr={p.get("momentum_threshold"):.3g} '
           f'ema={p.get("ema_fast")}/{p.get("ema_slow")}'
           + (f" size={size}" if size else ""))
    lines.append(f"{name} · {sig} · SL {slot['sl']:.0%} / TP {slot['tp']:.0%}")
    if pos:
        px = live_price if live_price else pos["entry"]
        entry = pos["entry"]
        side = "LONG" if pos["side"] == "long" else "SHORT"
        sl_px = entry * (1 - slot["sl"]) if pos["side"] == "long" else entry * (1 + slot["sl"])
        tp_px = entry * (1 + slot["tp"]) if pos["side"] == "long" else entry * (1 - slot["tp"])
        unreal = pos["qty"] * (px - entry) if pos["side"] == "long" else pos["qty"] * (entry - px)
        lines.append(
            f"  {side} {pos['qty']:.6f} @ {entry:,.2f} · "
            f"SL {sl_px:,.2f} · TP {tp_px:,.2f} · uPnL {unreal:+,.2f}"
        )
    else:
        lines.append("  flat")
    lines.append(
        f"  equity {eq:,.2f} ({ret:+.2f}%) · {len(st.get('trades', []))} closed trades · "
        f"fees {st.get('fees_paid', 0.0):,.2f}"
    )
    if st.get("last_processed_ts"):
        lines.append(f"  last bar {_iso(st['last_processed_ts'])}")
    last = (st.get("trades") or [None])[-1]
    if last:
        lines.append(
            f"  last trade: {last['side']} {last['entry']:,.2f} -> {last['exit']:,.2f} "
            f"{last['pnl']:+,.2f} ({last['exit_reason']}) @ {_iso(last['exit_ts'])}"
        )
    return lines


def dashboard(state: Dict[str, Any], reports: Optional[List[Dict]] = None) -> str:
    lines = [f"📄 PAPER LAB — {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC"]
    slots = state.get("slots", {})
    for slot in SLOTS:
        st = slots.get(slot["name"])
        if not st:
            lines.append(f"[{slot['name']}] (not started — run --paper-run)")
            continue
        for ln in _slot_line(slot, st):
            lines.append(ln)
        rep = next((r for r in (reports or []) if r.get("slot") == slot["name"]), None)
        if rep and rep.get("new_bars"):
            extra = f" · +{len(rep['new_trades'])} new trades" if rep.get("new_trades") else ""
            lines.append(f"  just processed {rep['new_bars']} new closed bars{extra}")
        if rep and rep.get("gap"):
            lines.append("  ⚠️ history gap: some bars were unavailable; state kept as-is")
        lines.append(f"  sweep: {slot['stats']}")
    lines.append("(paper: simulated fills via the backtest engine — no real orders)")
    return "\n".join(lines)


# ── CLI entry points (used by trading_bot.py and standalone) ─────────────────


def cmd_run(capital: float = DEFAULT_CAPITAL, exchange: str = DEFAULT_EXCHANGE,
            monitor: int = 0, yes: bool = False) -> int:
    while True:
        out = run_all(capital=capital, exchange=exchange)
        print(dashboard(out["state"], out["reports"]))
        if not monitor:
            return 0
        for rep in out["reports"]:
            if rep.get("error"):
                print(f"⚠️ {rep['slot']}: {rep['error']} — retrying next cycle", file=sys.stderr)
        time.sleep(monitor)


def cmd_status() -> int:
    state = load_state()
    if not state:
        print("No paper state yet — run --paper-run first.")
        return 1
    print(dashboard(state))
    return 0


def cmd_reset(capital: float = DEFAULT_CAPITAL, yes: bool = False,
              exchange: str = DEFAULT_EXCHANGE) -> int:
    old = load_state()
    if old and old.get("slots"):
        if not yes:
            print("Refusing to reset without --yes (would erase the paper trade log).")
            return 1
    state: Dict[str, Any] = {"slots": {}, "created_ts": int(time.time() * 1000)}
    for slot in SLOTS:
        bars = fetch_slot_bars(slot, 0, exchange)
        if not bars:
            print(f"⚠️ {slot['name']}: no market data; slot not initialized")
            continue
        state["slots"][slot["name"]] = init_slot_state(slot, bars, capital)
    save_state(state)
    print(f"Paper lab reset: all slots flat at {capital:,.2f}, "
          f"strategy state adopted as of now (see below).")
    print(dashboard(state))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Live paper-trading lab (sweep-winning strategies, live data, simulated fills).")
    ap.add_argument("--status", action="store_true", help="offline view of saved state")
    ap.add_argument("--reset", action="store_true", help="re-initialize all slots (needs --yes)")
    ap.add_argument("--monitor", type=int, default=0, metavar="SEC",
                    help="run continuously every SEC seconds")
    ap.add_argument("--capital", type=float, default=DEFAULT_CAPITAL)
    ap.add_argument("--exchange", default=DEFAULT_EXCHANGE)
    ap.add_argument("--yes", action="store_true", help="confirm destructive/reset actions")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    if args.status:
        return cmd_status()
    if args.reset:
        return cmd_reset(args.capital, args.yes, args.exchange)
    return cmd_run(capital=args.capital, exchange=args.exchange, monitor=args.monitor, yes=args.yes)


if __name__ == "__main__":
    sys.exit(main())
