#!/usr/bin/env python3
"""
Nautilus Trader Integration
===========================
Wraps the bot's strategy logic into the Nautilus Trader architecture for
deterministic backtesting, with a phone-runnable fallback.

Layers
------
1. ``nautilus_strategies`` — pure-Python strategy classes (regime momentum,
   Minervini stage-2, sniper, cross-venue arb). Engine-agnostic,
   deterministic, run anywhere.
2. ``NautilusDataAdapter`` — historical OHLCV via CCXT with exchange fallback
   (Binance -> Kraken -> Coinbase), JSON cache, and a seeded synthetic
   generator for offline tests.
3. ``NautilusBacktestRunner`` — event-driven backtest simulator: long/short,
   regime-gated position sizing, commission, slippage, stop-loss,
   take-profit. Runs the SAME strategy classes the Rust engine will run —
   backtest-to-live parity.
4. ``NautilusStrategyAdapter`` / ``NautilusLiveRunner`` — wiring for the real
   ``nautilus_trader`` engine when installed.

Platform note
-------------
``nautilus_trader`` (Rust core) requires **Python >= 3.11**. This phone runs
Python 3.8, so the Rust engine installs on the server (Render) only. On the
phone the integration runs in full simulator mode with identical strategy
code paths.

Usage
-----
    python3 nautilus_integration.py                 # status + offline demo
    python3 nautilus_integration.py --real-data     # status + live-data backtest
    python3 trading_bot.py --nautilus-backtest      # via main CLI
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from nautilus_strategies import get_strategy, list_strategies

logger = logging.getLogger(__name__)

# ─── Availability checks ─────────────────────────────────────────────────────

try:
    import nautilus_trader
    NAUTILUS_AVAILABLE = True
    NAUTILUS_VERSION = getattr(nautilus_trader, "__version__", "unknown")
except ImportError:
    nautilus_trader = None
    NAUTILUS_AVAILABLE = False
    NAUTILUS_VERSION = None

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    ccxt = None
    CCXT_AVAILABLE = False

PY_VERSION = sys.version_info
#: nautilus_trader (Rust core) requires Python >= 3.11 (checked on PyPI:
#: wheels published for cp311/cp312 only).
NAUTILUS_MIN_PYTHON = (3, 11)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CACHE_DIR = os.path.join(PROJECT_DIR, "data", "nautilus_cache")

#: Approximate bars-per-year per interval (for Sharpe annualization)
INTERVAL_BARS_PER_YEAR = {
    "1m": 525600, "3m": 175200, "5m": 105120, "15m": 35040,
    "30m": 17520, "1h": 8760, "2h": 4380, "4h": 2190,
    "6h": 1460, "8h": 1095, "12h": 730, "1d": 365, "3d": 121.67, "1w": 52,
}

INTERVAL_MS = {
    "1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000, "30m": 1800000,
    "1h": 3600000, "2h": 7200000, "4h": 14400000, "6h": 21600000,
    "8h": 28800000, "12h": 43200000, "1d": 86400000, "3d": 259200000,
    "1w": 604800000,
}

INTERVAL_BARS_PER_DAY = {
    "1m": 1440, "3m": 480, "5m": 288, "15m": 96, "30m": 48,
    "1h": 24, "2h": 12, "4h": 6, "6h": 4, "8h": 3, "12h": 2, "1d": 1,
    "3d": 1 / 3, "1w": 1 / 7,
}


def bars_per_day(interval: str) -> float:
    """Bars per day for an interval string (e.g. '1h' -> 24)."""
    return INTERVAL_BARS_PER_DAY.get(interval, 24)


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat()


# ─── Configuration ─────────────────────────────────────────────────────────────


@dataclass
class NautilusConfig:
    """Configuration for the Nautilus Trader integration."""
    # Trading mode
    mode: str = "BACKTEST"  # BACKTEST, PAPER, LIVE

    # Instruments
    instruments: Optional[List[str]] = None  # kept for API compat
    symbol: str = "BTC/USDT"
    venue: str = "BINANCE"

    # Data
    days: int = 30
    interval: str = "1h"  # 1m, 5m, 1h, 4h, 1d ...
    cache_dir: str = DEFAULT_CACHE_DIR
    use_synthetic_fallback: bool = True

    # Risk / execution
    initial_capital: float = 10000.0
    commission_pct: float = 0.001   # 0.1% per side
    slippage_pct: float = 0.0005    # 0.05% adverse fill
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10
    max_position_pct: float = 0.02  # used when a signal has no size_pct

    # Strategy
    strategy_name: str = "regime_momentum"
    regime: Optional[str] = None    # fixed regime for backtests (None = strategy default)
    strategy_config: Optional[Dict] = None

    # Compat: macro thresholds for core.regime.RegimeDetector (live regime use)
    regime_config: Dict = None

    def __post_init__(self):
        if self.instruments is None:
            self.instruments = [self.symbol]
        if self.strategy_config is None:
            self.strategy_config = {}
        if self.regime_config is None:
            self.regime_config = {
                "usdt_dom_defensive": 8.5,
                "usdt_dom_risk_on": 7.0,
                "stable_supply_threshold": 150,
            }


# ─── Data Adapter ──────────────────────────────────────────────────────────────


class NautilusDataAdapter:
    """
    Market data for backtesting.

    - Historical OHLCV via CCXT with exchange fallback
      (binance -> kraken -> coinbase) and USDT->USD quote fallback.
    - JSON cache under ``cache_dir`` (one file per exchange/symbol/lookback).
    - Seeded synthetic generator for offline/deterministic tests.
    """

    EXCHANGE_FALLBACK: Tuple[str, ...] = ("binance", "kraken", "coinbase")

    def __init__(self, config: NautilusConfig):
        self.config = config
        self.last_source: str = "none"

    # ── real market data ───────────────────────────────────────────────────

    def fetch_historical_data(
        self,
        symbol: Optional[str] = None,
        days: Optional[int] = None,
        interval: Optional[str] = None,
        exchange_id: str = "auto",
        use_cache: bool = True,
    ) -> List[Dict]:
        """
        Fetch historical OHLCV bars as a list of dicts:
        {"timestamp": ms, "open", "high", "low", "close", "volume"}

        Returns [] if no exchange is reachable (caller may fall back to
        synthetic data).
        """
        symbol = symbol or self.config.symbol
        days = days or self.config.days
        interval = interval or self.config.interval

        os.makedirs(self.config.cache_dir, exist_ok=True)
        safe_symbol = symbol.replace("/", "-")
        cache_file = os.path.join(
            self.config.cache_dir,
            f"{exchange_id}_{safe_symbol}_{days}d_{interval}.json",
        )
        if use_cache and os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                data = json.load(f)
            self.last_source = "cache"
            logger.info(f"[Nautilus] Loaded {len(data)} cached bars from {cache_file}")
            return data

        now_ms = int(time.time() * 1000)
        since_ms = now_ms - days * 86400 * 1000

        chain = list(self.EXCHANGE_FALLBACK) if exchange_id == "auto" else [exchange_id]
        for ex_id in chain:
            data = self._fetch_via_ccxt(ex_id, symbol, since_ms, now_ms, interval)
            if data:
                self.last_source = f"exchange:{ex_id}"
                with open(cache_file, "w") as f:
                    json.dump(data, f)
                logger.info(f"[Nautilus] Cached {len(data)} bars to {cache_file}")
                return data

        self.last_source = "none"
        logger.warning(f"[Nautilus] No data from any exchange: {chain}")
        return []

    def _fetch_via_ccxt(
        self, ex_id: str, symbol: str, since_ms: int, until_ms: int, interval: str
    ) -> List[Dict]:
        if not CCXT_AVAILABLE:
            logger.warning("[Nautilus] ccxt not installed; skipping %s", ex_id)
            return []

        # Kraken/Coinbase have thin USDT liquidity -> try USD quote as fallback
        symbols = [symbol]
        if symbol.endswith("/USDT"):
            symbols.append(symbol[: -len("/USDT")] + "/USD")

        try:
            exchange = getattr(ccxt, ex_id)({"enableRateLimit": True})
        except Exception as e:  # noqa: BLE001
            logger.warning("[Nautilus] Cannot init exchange %s: %s", ex_id, e)
            return []

        step_ms = INTERVAL_MS.get(interval, 3600000)
        for sym in symbols:
            try:
                first = exchange.fetch_ohlcv(sym, timeframe=interval, since=since_ms, limit=1000)
            except Exception as e:  # noqa: BLE001
                logger.warning("[Nautilus] %s %s %s: %s", ex_id, sym, interval, e)
                continue
            if not first:
                continue

            rows = list(first)
            # Paginate forward until we reach now
            guard = 0
            while rows and rows[-1][0] < until_ms - 2 * step_ms and guard < 50:
                guard += 1
                try:
                    nxt = exchange.fetch_ohlcv(
                        sym, timeframe=interval, since=rows[-1][0] + 1, limit=1000
                    )
                except Exception:  # noqa: BLE001
                    break
                if not nxt:
                    break
                rows.extend(nxt)

            rows = [r for r in rows if since_ms <= r[0] <= until_ms]
            rows.sort(key=lambda r: r[0])
            dedup: Dict[int, List] = {int(r[0]): r for r in rows}
            data = [
                {
                    "timestamp": int(ts),
                    "open": float(r[1]),
                    "high": float(r[2]),
                    "low": float(r[3]),
                    "close": float(r[4]),
                    "volume": float(r[5] or 0.0),
                }
                for ts, r in sorted(dedup.items())
            ]
            if data:
                logger.info(
                    "[Nautilus] Fetched %d %s bars for %s from %s",
                    len(data), interval, sym, ex_id,
                )
                return data
        return []

    # ── synthetic data (offline / deterministic) ───────────────────────────

    def generate_synthetic_bars(
        self,
        n_bars: int = 500,
        start_price: float = 100.0,
        vol_per_bar: float = 0.01,
        drift_per_bar: float = 0.0002,
        seed: int = 42,
        interval_ms: int = 3600000,
        start_ts_ms: Optional[int] = None,
    ) -> List[Dict]:
        """
        Deterministic geometric random-walk bars (seeded). No network needed.
        """
        rng = random.Random(seed)
        ts0 = (
            start_ts_ms
            if start_ts_ms is not None
            else int(time.time() * 1000) - n_bars * interval_ms
        )
        price = start_price
        out: List[Dict] = []
        for i in range(n_bars):
            ret = drift_per_bar + rng.gauss(0.0, vol_per_bar)
            o = price
            c = max(o * (1.0 + ret), 1e-9)
            hi = max(o, c) * (1.0 + abs(rng.gauss(0.0, vol_per_bar * 0.5)))
            lo = min(o, c) * (1.0 - abs(rng.gauss(0.0, vol_per_bar * 0.5)))
            vol = abs(rng.gauss(1000.0, 500.0))
            out.append({
                "timestamp": ts0 + i * interval_ms,
                "open": o, "high": hi, "low": lo, "close": c, "volume": vol,
            })
            price = c
        self.last_source = "synthetic"
        return out

    # ── save / load ─────────────────────────────────────────────────────────

    def save_bars(self, data: List[Dict], filename: str) -> str:
        """Save bars as JSON (Parquet if pandas is installed)."""
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        try:
            import pandas as pd  # noqa: F401
            if filename.endswith(".parquet"):
                pd.DataFrame(data).to_parquet(filename)
            else:
                with open(filename, "w") as f:
                    json.dump(data, f)
        except ImportError:
            fallback = filename.replace(".parquet", ".json")
            with open(fallback, "w") as f:
                json.dump(data, f)
            return fallback
        return filename

    def load_bars(self, filename: str) -> List[Dict]:
        """Load bars from JSON (or Parquet if pandas is installed)."""
        if filename.endswith(".parquet"):
            try:
                import pandas as pd
                return pd.read_parquet(filename).to_dict("records")
            except ImportError:
                pass
        with open(filename.replace(".parquet", ".json") if filename.endswith(".parquet") else filename, "r") as f:
            return json.load(f)


# ─── Backtest Runner (event-driven simulator) ────────────────────────────────


# ─── Shared per-bar engine (backtest + paper lab) ─────────────────────────────


def _close_trade(
    position: Dict, exit_price: float, ts: int, reason: str, fee_rate: float
) -> Tuple[float, Dict]:
    """
    Realize P&L on a close.

    Returns (net_pnl, trade) where net_pnl = gross - entry fee - exit fee
    (the full trade P&L; caller adds it to the flat-basis equity).
    """
    qty = position["qty"]
    if position["side"] == "long":
        gross = qty * (exit_price - position["entry"])
    else:
        gross = qty * (position["entry"] - exit_price)
    fee_open = position["notional"] * fee_rate
    fee_close = qty * exit_price * fee_rate
    pnl = gross - fee_close - fee_open
    trade = {
        "side": position["side"],
        "entry_ts": position["entry_ts"],
        "exit_ts": ts,
        "entry": round(position["entry"], 8),
        "exit": round(exit_price, 8),
        "qty": round(qty, 8),
        "pnl": round(pnl, 8),
        "gross_pnl": round(gross, 8),
        "fees": round(fee_open + fee_close, 8),
        "exit_reason": reason,
    }
    return pnl, trade


def step_bars(
    state: Dict[str, Any],
    strategy: Any,
    bars: List[Dict],
    cfg: NautilusConfig,
) -> List[float]:
    """
    Advance a backtest/paper position state through ``bars`` (mutates state).

    Single source of truth for per-bar engine semantics — used by the
    backtest runner (fresh state over the full history) and the paper lab
    (persisted state over only the bars that closed since the last run), so
    paper fills are exact backtest semantics by construction.

    Per bar (in order):
      1. ``strategy.on_bar(bar)`` — the strategy consumes the bar (internal
         state accumulates; a signal may be returned).
      2. Open position: SL/TP against the bar high/low, effective from the
         bar AFTER entry. A position carried over from a previous batch has
         ``entry_idx == -1`` so SL/TP is live on every bar of this batch.
      3. Signal actions ("close"/"buy"/"sell") executed at the bar close with
         slippage; opposite-direction signals reverse.
      4. Mark to market.

    ``state`` (mutated in place)::

        {
            "equity": float,            # flat basis (cash; fees netted on close)
            "position": Optional[dict], # side/entry/qty/notional/entry_ts/entry_idx
            "trades": List[dict],
            "fees_paid": float,
        }

    Returns:
        Per-bar marked equity (equity + unrealized), one entry per processed
        bar (does not include the starting equity).
    """
    fee_rate = cfg.commission_pct
    slip = cfg.slippage_pct
    sl = cfg.stop_loss_pct
    tp = cfg.take_profit_pct

    equity = float(state["equity"])
    position = state["position"]
    trades: List[Dict] = state.setdefault("trades", [])
    fees_paid = float(state.get("fees_paid", 0.0))
    curve: List[float] = []

    for i, bar in enumerate(bars):
        o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
        ts = bar["timestamp"]

        # 1) Strategy decision on this bar's close
        signal = strategy.on_bar(bar)
        action = signal.get("action") if isinstance(signal, dict) else None

        # 2) Manage open position: SL/TP against the bar range
        #    (effective from the bar AFTER entry)
        if position and i > position.get("entry_idx", 0):
            exit_price: Optional[float] = None
            reason = None
            entry = position["entry"]
            if position["side"] == "long":
                if l <= entry * (1 - sl):
                    exit_price, reason = entry * (1 - sl) * (1 - slip), "stop_loss"
                elif h >= entry * (1 + tp):
                    exit_price, reason = entry * (1 + tp) * (1 - slip), "take_profit"
            else:  # short
                if h >= entry * (1 + sl):
                    exit_price, reason = entry * (1 + sl) * (1 + slip), "stop_loss"
                elif l <= entry * (1 - tp):
                    exit_price, reason = entry * (1 - tp) * (1 + slip), "take_profit"
            if exit_price is not None:
                pnl, trade = _close_trade(position, exit_price, ts, reason, fee_rate)
                equity += pnl
                fees_paid += trade["fees"]
                trades.append(trade)
                position = None

        # 3) Signal-driven action at the bar close
        if position:
            if action == "close":
                fill = c * (1 - slip) if position["side"] == "long" else c * (1 + slip)
                pnl, trade = _close_trade(position, fill, ts, "signal_close", fee_rate)
                equity += pnl
                fees_paid += trade["fees"]
                trades.append(trade)
                position = None
            elif action in ("buy", "sell"):
                same_dir = (
                    (action == "buy" and position["side"] == "long")
                    or (action == "sell" and position["side"] == "short")
                )
                if not same_dir:
                    fill = c * (1 - slip) if position["side"] == "long" else c * (1 + slip)
                    pnl, trade = _close_trade(position, fill, ts, "reversed", fee_rate)
                    equity += pnl
                    fees_paid += trade["fees"]
                    trades.append(trade)
                    position = None

        if position is None and action in ("buy", "sell"):
            side = "long" if action == "buy" else "short"
            fill = c * (1 + slip) if side == "long" else c * (1 - slip)
            size_pct = signal.get("size_pct", cfg.max_position_pct) if isinstance(signal, dict) else cfg.max_position_pct
            size_pct = max(float(size_pct), 0.0)
            notional = equity * size_pct
            if notional > 0 and fill > 0:
                qty = notional / fill
                position = {
                    "side": side,
                    "entry": fill,
                    "qty": qty,
                    "notional": notional,
                    "entry_ts": ts,
                    "entry_idx": i,
                }

        # 4) Mark to market
        if position:
            if position["side"] == "long":
                unreal = position["qty"] * (c - position["entry"])
            else:
                unreal = position["qty"] * (position["entry"] - c)
        else:
            unreal = 0.0
        curve.append(equity + unreal)

    state["equity"] = equity
    state["position"] = position
    state["fees_paid"] = fees_paid
    return curve


class NautilusBacktestRunner:
    """
    Runs backtests with an event-driven matching account.

    The same strategy class that Nautilus's Rust engine will run in live
    mode is fed bar-by-bar here; the account applies commission, slippage,
    stop-loss and take-profit. Deterministic given identical bars.
    """

    def __init__(self, config: NautilusConfig):
        self.config = config
        self.data_adapter = NautilusDataAdapter(config)
        self.last_result: Optional[Dict[str, Any]] = None

    # ── public API ──────────────────────────────────────────────────────────

    def run_backtest(
        self,
        bars: Optional[List[Dict]] = None,
        strategy_name: Optional[str] = None,
        regime: Optional[str] = None,
        exchange_id: str = "auto",
    ) -> Dict[str, Any]:
        """
        Run a backtest.

        Args:
            bars: pre-fetched bars; if None, fetched via the data adapter
                  (exchange fallback -> synthetic if allowed).
            strategy_name: overrides config.strategy_name
            regime: fixed regime for the strategy (default: strategy default)
            exchange_id: "auto" or a ccxt exchange id

        Returns:
            Result dict (see module docstring / print_report).
        """
        cfg = self.config
        name = strategy_name or cfg.strategy_name
        regime = regime or cfg.regime

        if bars is None:
            bars = self.data_adapter.fetch_historical_data(exchange_id=exchange_id)
            if not bars and cfg.use_synthetic_fallback:
                n = int(cfg.days * bars_per_day(cfg.interval))
                logger.warning(
                    "[Nautilus] No market data available; using %d synthetic bars "
                    "(offline test mode)", n,
                )
                bars = self.data_adapter.generate_synthetic_bars(
                    n_bars=n,
                    vol_per_bar=0.01,
                    drift_per_bar=0.0,
                    interval_ms=INTERVAL_MS.get(cfg.interval, 3600000),
                )
            if not bars:
                return {"status": "error", "message": "no market data available"}

        strategy_cfg = dict(cfg.strategy_config or {})
        if regime:
            strategy_cfg["regime"] = regime
        strategy = get_strategy(name, strategy_cfg)

        result = self._simulate(strategy, name, bars)
        result["data_source"] = self.data_adapter.last_source
        self.last_result = result
        return result

    # ── engine ──────────────────────────────────────────────────────────────

    def _simulate(
        self,
        strategy: Any,
        name: str,
        bars: List[Dict],
    ) -> Dict[str, Any]:
        cfg = self.config
        initial = cfg.initial_capital
        slip = cfg.slippage_pct

        state: Dict[str, Any] = {
            "equity": initial,
            "position": None,
            "trades": [],
            "fees_paid": 0.0,
        }
        curve = step_bars(state, strategy, bars, cfg)
        equity = state["equity"]
        position = state["position"]
        equity_curve = [initial] + curve

        # 5) Force-close any open position at the final close
        if position and bars:
            last = bars[-1]
            fill = last["close"] * (1 - slip) if position["side"] == "long" else last["close"] * (1 + slip)
            pnl, trade = self._close_position(position, fill, last["timestamp"], "end_of_data")
            equity += pnl
            state["fees_paid"] += trade["fees"]
            state["trades"].append(trade)
            equity_curve[-1] = equity

        return self._build_result(name, bars, initial, equity, equity_curve,
                                  state["trades"], state["fees_paid"],
                                  cfg.commission_pct, slip,
                                  cfg.stop_loss_pct, cfg.take_profit_pct, cfg.interval)

    def _close_position(
        self, position: Dict, exit_price: float, ts: int, reason: str
    ) -> Tuple[float, Dict]:
        """Realize P&L on a close (see module-level :func:`_close_trade`)."""
        return _close_trade(position, exit_price, ts, reason, self.config.commission_pct)

    @staticmethod
    def _build_result(
        name: str,
        bars: List[Dict],
        initial: float,
        final_equity: float,
        equity_curve: List[float],
        trades: List[Dict],
        fees_paid: float,
        fee_rate: float,
        slip: float,
        sl: float,
        tp: float,
        interval: str = "1h",
    ) -> Dict[str, Any]:
        total_return_pct = (final_equity - initial) / initial * 100.0

        profits = [t["pnl"] for t in trades if t["pnl"] > 0]
        losses = [t["pnl"] for t in trades if t["pnl"] <= 0]
        wins, losses_n = len(profits), len(losses)
        gross_win, gross_loss = sum(profits), abs(sum(losses))

        rets = [
            equity_curve[i] / equity_curve[i - 1] - 1.0
            for i in range(1, len(equity_curve))
            if equity_curve[i - 1] > 0
        ]
        if len(rets) > 2:
            mean = sum(rets) / len(rets)
            var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
            std = math.sqrt(var)
            bars_per_year = INTERVAL_BARS_PER_YEAR.get(interval, 8760)
            sharpe = (mean / std) * math.sqrt(bars_per_year) if std > 0 else 0.0
        else:
            sharpe = 0.0

        peak = equity_curve[0]
        max_dd = 0.0
        for eq in equity_curve:
            peak = max(peak, eq)
            if peak > 0:
                max_dd = max(max_dd, (peak - eq) / peak)

        return {
            "engine": "nautilus-rust" if NAUTILUS_AVAILABLE else "simulator",
            "mode": "BACKTEST",
            "strategy": name,
            "interval": interval,
            "initial_capital": initial,
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return_pct, 4),
            "bars": len(bars),
            "start": _iso(bars[0]["timestamp"]),
            "end": _iso(bars[-1]["timestamp"]),
            "total_trades": len(trades),
            "winning_trades": wins,
            "losing_trades": losses_n,
            "win_rate_pct": round(wins / len(trades) * 100, 2) if trades else 0.0,
            "avg_profit": round(gross_win / wins, 4) if wins else 0.0,
            "avg_loss": round(-gross_loss / losses_n, 4) if losses_n else 0.0,
            "profit_factor": round(gross_win / gross_loss, 4) if gross_loss > 0 else None,
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown_pct": round(max_dd * 100, 4),
            "fees_paid": round(fees_paid, 4),
            "commission_pct": fee_rate,
            "slippage_pct": slip,
            "stop_loss_pct": sl,
            "take_profit_pct": tp,
            "trades": trades,
            "equity_curve": [round(x, 4) for x in equity_curve],
        }


def print_report(result: Dict[str, Any]) -> None:
    """Print a human-readable backtest report."""
    print()
    print("=" * 70)
    print("NAUTILUS BACKTEST REPORT  (engine: %s)" % result.get("engine", "?"))
    print("=" * 70)
    print(f"Strategy:      {result.get('strategy')}")
    print(f"Period:        {str(result.get('start'))[:10]} -> {str(result.get('end'))[:10]}"
          f"  ({result.get('bars')} bars, source: {result.get('data_source')})")
    print(f"Capital:       ${result.get('initial_capital'):,.2f} -> ${result.get('final_equity'):,.2f}")
    print(f"Total Return:  {result.get('total_return_pct', 0):+.2f}%")
    print()
    print("Trade Statistics:")
    print(f"  Total Trades:  {result.get('total_trades')}")
    print(f"  Win Rate:      {result.get('win_rate_pct', 0):.1f}% "
          f"({result.get('winning_trades')}W / {result.get('losing_trades')}L)")
    pf = result.get("profit_factor")
    print(f"  Profit Factor: {'n/a' if pf is None else f'{pf:.2f}'}")
    print(f"  Avg Profit:    ${result.get('avg_profit', 0):,.2f}")
    print(f"  Avg Loss:      ${result.get('avg_loss', 0):,.2f}")
    print(f"  Fees Paid:     ${result.get('fees_paid', 0):,.2f}")
    print()
    print("Risk Metrics:")
    print(f"  Sharpe Ratio:  {result.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown:  {result.get('max_drawdown_pct', 0):.2f}%")
    if result.get("trades"):
        print()
        print("Last 5 Trades:")
        for t in result["trades"][-5:]:
            print(f"  {t['side']:<5} {t['entry']:,.4f} -> {t['exit']:,.4f}  "
                  f"pnl=${t['pnl']:+,.2f}  [{t['exit_reason']}]")
    print("=" * 70)


# ─── Strategy Adapter (for the real Nautilus engine) ─────────────────────────


class NautilusStrategyAdapter:
    """
    Bridges our strategy classes to Nautilus Trader's event-driven interface.

    With ``nautilus_trader`` installed, ``build_nautilus_strategy()`` returns
    a real ``Strategy`` subclass; without it, a lightweight shim with the
    same event surface so backtests run anywhere.
    """

    def __init__(self, config: NautilusConfig, strategy: Optional[Any] = None):
        self.config = config
        strat_cfg = dict(config.strategy_config or {})
        if config.regime:
            strat_cfg["regime"] = config.regime
        self.strategy = strategy or get_strategy(config.strategy_name, strat_cfg)
        self.current_regime = getattr(self.strategy, "regime", None) or "NEUTRAL"
        self.signals_generated = 0
        self.trades_executed = 0

    def on_tick(self, tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sig = self.strategy.on_tick(tick)
        if sig:
            self.signals_generated += 1
        return sig

    def on_bar(self, bar: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sig = self.strategy.on_bar(bar)
        if sig:
            self.signals_generated += 1
        return sig

    def on_order_filled(self, order: Any) -> None:
        self.trades_executed += 1
        logger.info("[Nautilus] Order filled: %s", order)

    def build_nautilus_strategy(self):
        """
        Build a strategy class for Nautilus's BacktestEngine / LiveEngine.

        NOTE: the exact callback signatures (on_bar/on_tick arguments) depend
        on the installed nautilus_trader version — verify against the
        installed release before deploying on the server.
        """
        adapter = self

        if NAUTILUS_AVAILABLE:
            from nautilus_trader.trading.strategy import Strategy

            class NautilusBotStrategy(Strategy):
                """Nautilus Strategy wrapping our regime-based approach."""

                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self._adapter = adapter

                def on_start(self) -> None:
                    logger.info("[Nautilus] NautilusBotStrategy started")

                def on_bar(self, instrument_id, bar) -> None:  # type: ignore[no-redef]
                    payload = {
                        "timestamp": getattr(bar, "ts_event", None) or getattr(bar, "timestamp", 0),
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "volume": float(bar.volume),
                    }
                    self._adapter.on_bar(payload)

                def on_tick(self, instrument_id, tick) -> None:  # type: ignore[no-redef]
                    payload = {
                        "timestamp": getattr(tick, "ts_event", None) or 0,
                        "price": float(tick.price),
                    }
                    self._adapter.on_tick(payload)

                def on_order_filled(self, order, trade) -> None:  # type: ignore[no-redef]
                    self._adapter.on_order_filled(order)

                def on_stop(self) -> None:
                    logger.info(
                        "[Nautilus] stopped. signals=%d fills=%d",
                        adapter.signals_generated, adapter.trades_executed,
                    )

            return NautilusBotStrategy

        class ShimStrategy:
            """Lightweight strategy shim (same event surface, no engine)."""

            def __init__(self):
                self.adapter = adapter

            def on_start(self):
                logger.info("[Nautilus] Shim strategy started")

            def on_bar(self, bar):
                return self.adapter.on_bar(bar)

            def on_tick(self, tick):
                return self.adapter.on_tick(tick)

            def on_order_filled(self, order, trade=None):
                self.adapter.on_order_filled(order)

            def on_stop(self):
                logger.info(
                    "[Nautilus] Strategy stopped. signals=%d fills=%d",
                    self.adapter.signals_generated, self.adapter.trades_executed,
                )

        return ShimStrategy


# ─── Live Runner ──────────────────────────────────────────────────────────────


class NautilusLiveRunner:
    """
    Runs live/paper trading with Nautilus Trader's LiveEngine.

    Uses the same strategy class as backtest — just swap the engine.
    Phase 3 (server, Python 3.11+): wire LiveEngine + venue adapters.
    """

    def __init__(self, config: NautilusConfig):
        self.config = config
        self.strategy_adapter = NautilusStrategyAdapter(config)
        self.running = False

    def start(self, strategy_class: Optional[Any] = None, mode: str = "PAPER") -> None:
        if not NAUTILUS_AVAILABLE:
            logger.info("[Nautilus] nautilus_trader not installed — live/paper trading "
                        "via the Rust engine requires Python 3.11+ (server). "
                        "Scaffold: would start %s trading.", mode)
            return
        self.running = True
        logger.info("[Nautilus] Starting %s trading...", mode)
        # Phase 3:
        # from nautilus_trader.live import LiveEngine, LiveEngineConfig
        # engine = LiveEngine(config=LiveEngineConfig())
        # engine.add_strategy(strategy_class or self.strategy_adapter.build_nautilus_strategy())
        # engine.add_venue(venue_config)
        # engine.run()

    def stop(self) -> None:
        self.running = False
        logger.info("[Nautilus] Trading stopped")


# ─── Integration Status ───────────────────────────────────────────────────────


def _component_available(module: str, attr: str) -> bool:
    try:
        import importlib
        mod = importlib.import_module(module)
        return hasattr(mod, attr)
    except Exception:  # noqa: BLE001
        return False


def get_integration_status() -> Dict[str, Any]:
    """Check Nautilus Trader integration status."""
    py = PY_VERSION
    installable = py >= NAUTILUS_MIN_PYTHON
    status: Dict[str, Any] = {
        "nautilus_installed": NAUTILUS_AVAILABLE,
        "nautilus_version": NAUTILUS_VERSION,
        "python_version": f"{py[0]}.{py[1]}.{py[2]}",
        "nautilus_installable": installable,
        "ccxt_available": CCXT_AVAILABLE,
        "components": {
            "NautilusStrategyAdapter": True,
            "NautilusDataAdapter": True,
            "NautilusBacktestRunner": True,
            "NautilusLiveRunner": True,
        },
        "existing_components": {
            "RegimeDetector": _component_available("core.regime", "RegimeDetector"),
            "BaseStrategy": _component_available("strategies.strategy_template", "BaseStrategy"),
            "CCXTConnector": _component_available("ccxt_connector", "CCXTConnector"),
            "Backtester": _component_available("backtester", "Backtester"),
        },
        "strategies": list_strategies(),
        "next_steps": [],
    }

    if not installable:
        status["platform_notes"] = [
            f"Python {py[0]}.{py[1]} < 3.11: nautilus_trader (Rust core) installs on the "
            "server (Render) only; phone runs the identical strategy logic in the "
            "event-driven simulator",
        ]
    if not CCXT_AVAILABLE:
        status["next_steps"].append("pip install ccxt")
    if not NAUTILUS_AVAILABLE:
        status["next_steps"].append("pip install nautilus_trader  # server (Python 3.11+)")
    return status


# ─── CLI Entry Point ───────────────────────────────────────────────────────────


def _main(argv: Optional[List[str]] = None) -> int:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Nautilus Trader integration")
    parser.add_argument("--real-data", action="store_true",
                        help="Backtest on real exchange data (default: synthetic, offline)")
    parser.add_argument("--strategy", default="regime_momentum")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--regime", default=None)
    args = parser.parse_args(argv)

    print("=" * 60)
    print("NAUTILUS TRADER INTEGRATION")
    print("=" * 60)

    status = get_integration_status()
    print(f"\nNautilus Installed: {'YES' if status['nautilus_installed'] else 'NO (simulator mode)'}")
    print(f"Python: {status['python_version']} (nautilus needs >= 3.11)")
    print(f"CCXT: {'yes' if status['ccxt_available'] else 'no'}")

    print("\nExisting Components:")
    for name, available in status["existing_components"].items():
        print(f"  {'OK ' if available else 'MISS'} {name}")

    if status.get("platform_notes"):
        print("\nPlatform Notes:")
        for note in status["platform_notes"]:
            print(f"  * {note}")

    if status.get("next_steps"):
        print("\nNext Steps:")
        for step in status["next_steps"]:
            print(f"  -> {step}")

    print("\n" + "-" * 60)
    print("BACKTEST")
    print("-" * 60)

    config = NautilusConfig(
        mode="BACKTEST",
        symbol=args.symbol,
        days=args.days,
        interval=args.interval,
        strategy_name=args.strategy,
        regime=args.regime,
    )
    runner = NautilusBacktestRunner(config)

    if args.real_data:
        result = runner.run_backtest()
    else:
        # Offline deterministic demo: 30 days of 1h synthetic bars
        n = int(config.days * bars_per_day(config.interval))
        bars = runner.data_adapter.generate_synthetic_bars(n_bars=n)
        result = runner.run_backtest(bars=bars)

    if "error" in result:
        print(f"\nError: {result['message']}")
        return 1

    print_report(result)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
