#!/usr/bin/env python3
"""
Strategy parameter sweep for the Nautilus simulator backtest engine.

Runs a coarse-to-fine grid over regime-momentum parameters on real
Binance data (cached 1h bars resampled to 4h / 1d), plus the
Minervini/SEA stage-2 template, then validates the top configs on
the *other* symbol so we do not crown a curve-fit.

Usage:
    python3 strategy_sweep.py                 # full sweep (2 symbols, ~2-5 min)
    python3 strategy_sweep.py --fast          # reduced grid for a quick check
    python3 strategy_sweep.py --symbols BTC/USDT

Outputs:
    research/sweep_results.json               # every grid cell (slim)
    research/strategy_sweep_report.md         # ranked report + armable configs
"""

import argparse
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from nautilus_integration import NautilusConfig, NautilusBacktestRunner

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.join(HERE, "research")
CACHE_DIR = os.path.join(HERE, "data", "nautilus_cache")

INITIAL_CAPITAL = 10_000.0
COMMISSION = 0.001      # 0.1% per side
SLIPPAGE = 0.0005       # 0.05% adverse
MIN_TRADES = {"1h": 15, "4h": 15, "1d": 12}

# ── grids ─────────────────────────────────────────────────────────────────────
# regime_momentum: signal timing x exits
GRIDS = {
    "1h": {
        "lookback": [20, 50, 100],
        "momentum_threshold": [0.005, 0.01, 0.02, 0.03],
        "ema": [(10, 30), (20, 50), (50, 100)],
    },
    "4h": {
        "lookback": [10, 25, 50],
        "momentum_threshold": [0.005, 0.01, 0.02, 0.03],
        "ema": [(10, 30), (20, 50), (50, 100)],
    },
    "1d": {
        "lookback": [5, 10, 20],
        "momentum_threshold": [0.01, 0.02, 0.03, 0.05],
        "ema": [(5, 20), (10, 40), (20, 50)],
    },
}
FAST_GRIDS = {
    tf: {
        "lookback": g["lookback"][1:2],
        "momentum_threshold": g["momentum_threshold"][1:3],
        "ema": g["ema"][1:2],
    }
    for tf, g in GRIDS.items()
}
SLTP_GRID = [(0.03, 0.06), (0.05, 0.10), (0.075, 0.15), (0.15, 0.30)]
FAST_SLTP = [(0.05, 0.10), (0.15, 0.30)]

SIZE_GRID = [0.02, 0.03, 0.05]   # stage-2 position sizing overrides

TOP_N_PER_TF = 5                  # configs promoted to stage 2
XVAL_TOP = 3                      # top configs cross-checked on other symbol


# ── data ──────────────────────────────────────────────────────────────────────

def load_bars(symbol: str, days: int = 365, interval: str = "1h") -> List[Dict]:
    safe = symbol.replace("/", "-")
    path = os.path.join(CACHE_DIR, f"binance_{safe}_{days}d_{interval}.json")
    if not os.path.exists(path):
        # fetch + cache
        cfg = NautilusConfig(symbol=symbol, days=days, interval=interval)
        from nautilus_integration import NautilusDataAdapter
        bars = NautilusDataAdapter(cfg).fetch_historical_data(exchange_id="binance")
        if not bars:
            raise SystemExit(f"no data available for {symbol}")
        return bars
    with open(path) as f:
        return json.load(f)


def resample(bars: List[Dict], factor_ms: int) -> List[Dict]:
    """Resample aligned bars (1h) to a wider timeframe. factor_ms = 4h or 1d."""
    groups: Dict[int, List[Dict]] = {}
    for b in bars:
        key = b["timestamp"] // factor_ms
        groups.setdefault(key, []).append(b)
    out = []
    for key in sorted(groups):
        g = groups[key]
        out.append({
            "timestamp": key * factor_ms,
            "open": g[0]["open"],
            "high": max(x["high"] for x in g),
            "low": min(x["low"] for x in g),
            "close": g[-1]["close"],
            "volume": sum(x["volume"] for x in g),
        })
    return out


def timeframe_bars(bars_1h: List[Dict], tf: str) -> List[Dict]:
    if tf == "1h":
        return bars_1h
    if tf == "4h":
        return resample(bars_1h, 4 * 3600 * 1000)
    if tf == "1d":
        return resample(bars_1h, 24 * 3600 * 1000)
    raise ValueError(tf)


# ── run one cell ──────────────────────────────────────────────────────────────

def run_cell(
    bars: List[Dict],
    tf: str,
    strategy: str,
    strategy_cfg: Dict[str, Any],
    sl: float,
    tp: float,
) -> Dict[str, Any]:
    cfg = NautilusConfig(
        symbol="BTC/USDT",           # label only; bars are injected directly
        days=1,
        interval=tf,
        initial_capital=INITIAL_CAPITAL,
        commission_pct=COMMISSION,
        slippage_pct=SLIPPAGE,
        stop_loss_pct=sl,
        take_profit_pct=tp,
        strategy_name=strategy,
        strategy_config=dict(strategy_cfg),
        use_synthetic_fallback=False,
    )
    runner = NautilusBacktestRunner(cfg)
    res = runner.run_backtest(bars=bars)
    return {
        "strategy": strategy,
        "interval": tf,
        "params": {k: v for k, v in strategy_cfg.items() if k != "regime"},
        "sl": sl,
        "tp": tp,
        "return_pct": res.get("total_return_pct", 0.0),
        "sharpe": res.get("sharpe_ratio", 0.0),
        "max_dd_pct": res.get("max_drawdown_pct", 0.0),
        "trades": res.get("total_trades", 0),
        "win_rate": res.get("win_rate_pct", 0.0),
        "profit_factor": res.get("profit_factor"),
        "fees": res.get("fees_paid", 0.0),
        "final_equity": res.get("final_equity"),
    }


def qualifies(cell: Dict[str, Any]) -> bool:
    return (
        cell["trades"] >= MIN_TRADES[cell["interval"]]
        and cell["return_pct"] > 0
        and (cell["profit_factor"] or 0) > 1.0
        and cell["sharpe"] > 0
    )


# ── the sweep ─────────────────────────────────────────────────────────────────

def sweep_symbol(
    symbol: str,
    bars_1h: List[Dict],
    grids: Dict[str, Dict],
    sltp_grid: List[Tuple[float, float]],
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    cells: List[Dict[str, Any]] = []
    other = "ETH/USDT" if "BTC" in symbol else "BTC/USDT"
    tf_bars = {tf: timeframe_bars(bars_1h, tf) for tf in ("1h", "4h", "1d")}

    total = sum(
        len(grids[tf]["lookback"]) * len(grids[tf]["momentum_threshold"])
        * len(grids[tf]["ema"]) * len(sltp_grid)
        for tf in ("1h", "4h", "1d")
    ) + 3 * len(sltp_grid)  # + minervini
    n = 0
    t0 = time.time()

    for tf in ("1h", "4h", "1d"):
        g = grids[tf]
        for lb in g["lookback"]:
            for thr in g["momentum_threshold"]:
                for (ef, es) in g["ema"]:
                    base = {"lookback": lb, "momentum_threshold": thr,
                            "ema_fast": ef, "ema_slow": es}
                    for (sl, tp) in sltp_grid:
                        cell = run_cell(tf_bars[tf], tf, "regime_momentum",
                                         base, sl, tp)
                        cell["symbol"] = symbol
                        cells.append(cell)
                        n += 1
                        if verbose and n % 96 == 0:
                            print(f"  {symbol} {tf}: {n}/{total} "
                                  f"({time.time() - t0:.0f}s)", flush=True)

        # minervini / SEA (fixed 252-bar template)
        for (sl, tp) in sltp_grid:
            cell = run_cell(tf_bars[tf], tf, "minervini_sea", {}, sl, tp)
            cell["symbol"] = symbol
            cells.append(cell)
            n += 1

    print(f"  {symbol}: {len(cells)} cells in {time.time() - t0:.0f}s", flush=True)
    return cells


def stage2_sizing(
    cells: List[Dict[str, Any]],
    tf_bars: Dict[str, List[Dict]],
    symbol: str,
) -> List[Dict[str, Any]]:
    """Re-run the top per-timeframe configs with larger position sizes."""
    extra: List[Dict[str, Any]] = []
    by_tf: Dict[str, List[Dict[str, Any]]] = {}
    for c in cells:
        if c["strategy"] == "regime_momentum" and qualifies(c):
            by_tf.setdefault(c["interval"], []).append(c)
    for tf, group in by_tf.items():
        group.sort(key=lambda c: c["sharpe"], reverse=True)
        for top in group[:TOP_N_PER_TF]:
            for size in SIZE_GRID:
                cfg = dict(top["params"])
                cfg["max_position_pct"] = size
                cell = run_cell(
                    tf_bars[tf], tf, "regime_momentum", cfg,
                    top["sl"], top["tp"],
                )
                cell["symbol"] = symbol
                cell["size"] = size
                cell["parent"] = top
                extra.append(cell)
    return extra


def cross_validate(
    cells: List[Dict[str, Any]],
    bars_by_symbol: Dict[str, List[Dict]],
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Run top configs on the OTHER symbol; key = (symbol, interval) -> cell."""
    results: Dict[Tuple[str, str], Dict[str, Any]] = {}
    by_tf: Dict[str, List[Dict[str, Any]]] = {}
    for c in cells:
        if c["strategy"] == "regime_momentum" and qualifies(c):
            by_tf.setdefault(c["interval"], []).append(c)
    for tf, group in by_tf.items():
        group.sort(key=lambda c: c["sharpe"], reverse=True)
        for top in group[:XVAL_TOP]:
            other = "ETH/USDT" if "BTC" in top["symbol"] else "BTC/USDT"
            other_bars = timeframe_bars(bars_by_symbol[other], tf)
            cell = run_cell(other_bars, tf, "regime_momentum",
                            dict(top["params"]), top["sl"], top["tp"])
            cell["symbol"] = other
            cell["xval_of"] = f'{top["symbol"]}/{tf}'
            results[(top["symbol"], tf)] = results.get((top["symbol"], tf)) or cell
    return results


# ── report ────────────────────────────────────────────────────────────────────

def fmt_cell(c: Dict[str, Any]) -> str:
    p = c["params"]
    if c["strategy"] == "minervini_sea":
        desc = "minervini"
    else:
        desc = (f"lb={p.get('lookback')} thr={p.get('momentum_threshold')} "
                f"ema={p.get('ema_fast')}/{p.get('ema_slow')}")
    pf = c["profit_factor"]
    return (f"| {c['symbol'].split('/')[0]} | {c['interval']} | {desc} | "
            f"{c['sl']:.3f}/{c['tp']:.3f} | {c['trades']} | "
            f"{c['return_pct']:+.2f}% | {c['sharpe']:+.2f} | "
            f"{c['win_rate']:.1f}% | {pf if pf else '-'} | "
            f"{c['max_dd_pct']:.2f}% |")


def write_report(
    path: str,
    all_cells: List[Dict[str, Any]],
    xval: Dict[Tuple[str, str], Dict[str, Any]],
    duration_s: float,
) -> None:
    lines: List[str] = []
    lines.append("# Strategy Parameter Sweep — Real Data (365 days, 1h base)\n")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M %Z')} · "
                 f"{len(all_cells)} cells · {duration_s:.0f}s\n")
    lines.append("Engine: Nautilus simulator (fees 0.1%/side + 0.05% slippage), "
                 f"${INITIAL_CAPITAL:,.0f} start, regime NEUTRAL 1% sizing "
                 "unless overridden.\n")

    # per symbol/timeframe top-10
    for sym in ("BTC/USDT", "ETH/USDT"):
        for tf in ("1h", "4h", "1d"):
            group = [c for c in all_cells
                     if c["symbol"] == sym and c["interval"] == tf
                     and "size" not in c]
            group.sort(key=lambda c: (qualifies(c), c["sharpe"]), reverse=True)
            top = group[:10]
            lines.append(f"\n## {sym} · {tf} — top 10 by (qualifies, sharpe)\n")
            lines.append("| Sym | TF | Signal | SL/TP | Trades | Return | Sharpe | Win% | PF | MaxDD |")
            lines.append("|---|---|---|---|---|---|---|---|---|---|")
            for c in top:
                lines.append(fmt_cell(c))
            nq = sum(1 for c in group if qualifies(c))
            lines.append(f"\nQualifying cells (return>0, PF>1, trades≥{MIN_TRADES[tf]}): "
                         f"{nq}/{len(group)}")

    # armable: cross-validated
    lines.append("\n## Cross-validated top configs (primary + other symbol)\n")
    lines.append("| Primary | TF | Signal | SL/TP | Prim Return | Prim Sharpe | XVal Return | XVal Sharpe |")
    lines.append("|---|---|---|---|---|---|---|---|")
    armable = []
    by_key: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for c in all_cells:
        if c["strategy"] == "regime_momentum" and qualifies(c):
            by_key.setdefault((c["symbol"], c["interval"]), []).append(c)
    for (sym, tf), group in sorted(by_key.items()):
        group.sort(key=lambda c: c["sharpe"], reverse=True)
        for top in group[:XVAL_TOP]:
            x = xval.get((sym, tf))
            if not x:
                continue
            ok = x["return_pct"] > 0 and x["sharpe"] > 0
            desc = (f"lb={top['params'].get('lookback')} "
                    f"thr={top['params'].get('momentum_threshold')} "
                    f"ema={top['params'].get('ema_fast')}/{top['params'].get('ema_slow')}")
            lines.append(
                f"| {sym.split('/')[0]} | {tf} | {desc} | {top['sl']:.3f}/{top['tp']:.3f} "
                f"| {top['return_pct']:+.2f}% | {top['sharpe']:+.2f} "
                f"| {x['return_pct']:+.2f}% | {x['sharpe']:+.2f} {'✅' if ok else '❌'} |")
            if ok:
                armable.append(top)
    if not armable:
        lines.append("\n**No config survived cross-symbol validation.**")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nreport -> {path}")
    if armable:
        print("ARMABLE (positive on both symbols):")
        for c in armable:
            p = c["params"]
            print(f"  {c['symbol']} {c['interval']} lb={p.get('lookback')} "
                  f"thr={p.get('momentum_threshold')} "
                  f"ema={p.get('ema_fast')}/{p.get('ema_slow')} "
                  f"sl={c['sl']} tp={c['tp']} ret={c['return_pct']:+.2f}%")
    else:
        print("NO CONFIG SURVIVED CROSS-SYMBOL VALIDATION")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbols", default="BTC/USDT ETH/USDT")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--fast", action="store_true",
                    help="reduced grid (quick sanity run)")
    args = ap.parse_args()

    os.makedirs(RESEARCH_DIR, exist_ok=True)
    symbols = args.symbols.split()
    grids = FAST_GRIDS if args.fast else GRIDS
    sltp = FAST_SLTP if args.fast else SLTP_GRID

    t0 = time.time()
    bars_by_symbol: Dict[str, List[Dict]] = {}
    for sym in symbols:
        print(f"loading {sym} {args.days}d 1h...", flush=True)
        bars_by_symbol[sym] = load_bars(sym, days=args.days)
        print(f"  {len(bars_by_symbol[sym])} bars", flush=True)

    all_cells: List[Dict[str, Any]] = []
    for sym in symbols:
        cells = sweep_symbol(sym, bars_by_symbol[sym], grids, sltp)
        all_cells.extend(cells)
        tf_bars = {tf: timeframe_bars(bars_by_symbol[sym], tf)
                   for tf in ("1h", "4h", "1d")}
        if not args.fast:
            extra = stage2_sizing(cells, tf_bars, sym)
            all_cells.extend(extra)
            print(f"  {sym}: +{len(extra)} sizing cells", flush=True)

    xval: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if len(symbols) == 2 and not args.fast:
        print("cross-validating top configs...", flush=True)
        xval = cross_validate(all_cells, bars_by_symbol)

    duration = time.time() - t0

    slim = [{k: v for k, v in c.items() if k != "parent"} for c in all_cells]
    out_json = os.path.join(RESEARCH_DIR, "sweep_results.json")
    with open(out_json, "w") as f:
        json.dump(slim, f, indent=1)
    print(f"results -> {out_json}")

    write_report(os.path.join(RESEARCH_DIR, "strategy_sweep_report.md"),
                 all_cells, xval, duration)


if __name__ == "__main__":
    main()
