#!/usr/bin/env python3
"""
Nautilus Trader Strategy Implementations
========================================
Concrete strategy classes for the Nautilus Trader integration.

Design principles
-----------------
- **Engine-agnostic pure Python.** Strategies compute signals from the bar/
  tick data they are handed and keep their own rolling state. Whether
  ``nautilus_trader`` (Rust core) is installed does NOT affect signal
  logic — only engine wiring in ``nautilus_integration``.
- **Deterministic.** No network access, no randomness, no wall clock.
- **Backtest-to-live parity.** The same classes run in the simulator,
  in paper mode, and (once the Rust engine is available on the server)
  inside Nautilus's event-driven engine.

Data formats
------------
bar:  {"timestamp": ms, "open", "high", "low", "close", "volume"}
tick: {"timestamp": ms, "price",
       optional "price_change_pct",
       optional "venue_prices": {"VENUE": price, ...}}

Signal format
-------------
None -> no action
dict -> {"action": "buy" | "sell" | "close" | "arbitrage",
         "reason": str,
         "confidence": float in [0, 1],
         ...optional extras ("size_pct", "spread", "conditions")}
    "buy"     -> open/keep long
    "sell"    -> open/keep short
    "close"   -> close current position
    "arbitrage" -> cross-venue spread opportunity
"""

import logging
from collections import deque
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Regime-based position sizing (mirrors core.regime.get_regime_config)
_REGIME_POSITION_PCT = {
    "DEFENSIVE": 0.005,
    "NEUTRAL": 0.010,
    "RISK_ON": 0.015,
}


def _ema_update(prev: Optional[float], price: float, period: int) -> Optional[float]:
    """Incremental EMA update. First call seeds with the price."""
    if prev is None:
        return price
    k = 2.0 / (period + 1)
    return price * k + prev * (1.0 - k)


# ─── Strategy 1: Regime-Gated Momentum ───────────────────────────────────────


class RegimeMomentumStrategy:
    """
    Regime-gated momentum.

    Enters when |momentum over ``lookback`` bars| >= ``momentum_threshold``
    AND the fast EMA is on the correct side of the slow EMA (trend filter).
    In the DEFENSIVE regime no new positions are taken — the strategy emits
    "close" so the engine flattens the book.

    Config keys:
        lookback (int, default 50)        momentum window in bars
        momentum_threshold (float, 0.01)  |return| required for entry
        ema_fast (int, default 20)        fast EMA period (trend filter)
        ema_slow (int, default 50)        slow EMA period (trend filter)
        regime (str, "NEUTRAL")           fixed regime (backtest/paper)
        max_position_pct (float, None)    overrides regime default sizing
        base_confidence (float, 0.6)      base signal confidence
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.lookback = int(config.get("lookback", 50))
        self.momentum_threshold = float(config.get("momentum_threshold", 0.01))
        self.ema_fast_period = int(config.get("ema_fast", 20))
        self.ema_slow_period = int(config.get("ema_slow", 50))
        self.regime = str(config.get("regime", "NEUTRAL")).upper()
        self.max_position_pct = config.get("max_position_pct")
        self.base_confidence = float(config.get("base_confidence", 0.6))

        # State
        self.closes: List[float] = []
        self.ema_fast: Optional[float] = None
        self.ema_slow: Optional[float] = None
        self.bars_seen = 0
        self.signals_emitted = 0

    @property
    def warmup_bars(self) -> int:
        return max(self.lookback, self.ema_slow_period)

    def on_tick(self, tick_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Momentum is a bar-based signal; ticks contribute nothing."""
        return None

    def on_bar(self, bar_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        close = float(bar_data["close"])
        self.closes.append(close)
        # Bound memory: keep warmup + lookback bars
        if len(self.closes) > self.warmup_bars + self.lookback:
            self.closes.pop(0)
        self.bars_seen += 1

        self.ema_fast = _ema_update(self.ema_fast, close, self.ema_fast_period)
        self.ema_slow = _ema_update(self.ema_slow, close, self.ema_slow_period)

        if self.bars_seen < self.warmup_bars:
            return None

        # DEFENSIVE: no new positions — flatten
        if self.regime == "DEFENSIVE":
            self.signals_emitted += 1
            return {
                "action": "close",
                "reason": "DEFENSIVE regime: no new positions",
                "confidence": 1.0,
            }

        ref = self.closes[-self.lookback]
        if ref <= 0:
            return None
        momentum = close / ref - 1.0

        fast_ok = self.bars_seen >= self.ema_fast_period
        slow_ok = self.bars_seen >= self.ema_slow_period
        if not (fast_ok and slow_ok and self.ema_fast is not None and self.ema_slow is not None):
            return None

        size_pct = float(self.max_position_pct or _REGIME_POSITION_PCT.get(self.regime, 0.010))
        magnitude = min(abs(momentum) / self.momentum_threshold, 3.0)
        confidence = min(0.95, self.base_confidence + magnitude * 0.10)

        if momentum >= self.momentum_threshold and self.ema_fast > self.ema_slow:
            self.signals_emitted += 1
            return {
                "action": "buy",
                "reason": f"momentum {momentum:+.2%} over {self.lookback} bars (regime {self.regime})",
                "confidence": round(confidence, 4),
                "size_pct": size_pct,
            }

        if momentum <= -self.momentum_threshold and self.ema_fast < self.ema_slow:
            self.signals_emitted += 1
            return {
                "action": "sell",
                "reason": f"momentum {momentum:+.2%} over {self.lookback} bars (regime {self.regime})",
                "confidence": round(confidence, 4),
                "size_pct": size_pct,
            }

        return None


# ─── Strategy 2: Minervini / Stage-2 Trend Template ──────────────────────────


class MinerviniSeaStrategy:
    """
    Minervini Stage-2 trend template (SEA family).

    Entry when ALL six conditions hold on a rolling 252-bar (≈52-week) window:
      1. close > SMA200
      2. SMA150 > SMA200
      3. SMA50 > SMA150
      4. close > SMA50
      5. close > 52-week low * 1.30
      6. close >= 52-week high * 0.75   (within 25% of the high)

    Exit: close < SMA50 (trend structure broken).

    Config keys:
        low_buffer_mult (float, 1.3)  condition 5 multiplier
        high_proximity (float, 0.75)  condition 6 multiplier
    """

    WINDOW = 252

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.low_buffer_mult = float(config.get("low_buffer_mult", 1.3))
        self.high_proximity = float(config.get("high_proximity", 0.75))
        self._closes = deque(maxlen=self.WINDOW)
        self.signals_emitted = 0

    def on_tick(self, tick_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Stage-2 template is bar-based."""
        return None

    def on_bar(self, bar_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        close = float(bar_data["close"])
        self._closes.append(close)
        if len(self._closes) < self.WINDOW:
            return None

        closes = list(self._closes)
        sma50 = sum(closes[-50:]) / 50.0
        sma150 = sum(closes[-150:]) / 150.0
        sma200 = sum(closes[-200:]) / 200.0
        win_low = min(closes)
        win_high = max(closes)

        # Exit: trend structure broken
        if close < sma50:
            self.signals_emitted += 1
            return {
                "action": "close",
                "reason": f"close {close:.2f} < SMA50 {sma50:.2f}: trend broken",
                "confidence": 0.80,
            }

        conditions = {
            "above_200_sma": close > sma200,
            "sma150_above_200": sma150 > sma200,
            "sma50_above_150": sma50 > sma150,
            "above_50_sma": close > sma50,
            "above_52w_low": close > win_low * self.low_buffer_mult,
            "near_52w_high": close >= win_high * self.high_proximity,
        }
        if all(conditions.values()):
            self.signals_emitted += 1
            return {
                "action": "buy",
                "reason": "all 6 Minervini/SEA stage-2 conditions met",
                "confidence": 0.85,
                "conditions": conditions,
            }
        return None


# ─── Strategy 3: Sniper (rapid-move scalp) ───────────────────────────────────


class SniperStrategy:
    """
    Fast entry/exit on sharp moves. Tick-driven; also works bar-by-bar
    (bar close vs previous close).

    Config keys:
        entry_threshold (float, 0.02)  |move| that triggers a signal
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.entry_threshold = float(config.get("entry_threshold", 0.02))
        self._last_price: Optional[float] = None
        self.signals_emitted = 0

    def on_tick(self, tick_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        price = tick_data.get("price")
        if price is None:
            return None
        price = float(price)
        pct = tick_data.get("price_change_pct")
        if pct is None and self._last_price:
            pct = price / self._last_price - 1.0
        self._last_price = price
        return self._from_pct(pct)

    def on_bar(self, bar_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        close = float(bar_data["close"])
        prev = self._last_price
        self._last_price = close
        if prev:
            return self._from_pct(close / prev - 1.0)
        return None

    def _from_pct(self, pct: Optional[float]) -> Optional[Dict[str, Any]]:
        if pct is None or abs(pct) <= self.entry_threshold:
            return None
        self.signals_emitted += 1
        direction = "buy" if pct > 0 else "sell"
        return {
            "action": direction,
            "reason": f"sniper: {pct:+.2%} move detected",
            "confidence": round(min(0.9, abs(pct) / self.entry_threshold * 0.5), 4),
        }


# ─── Strategy 4: Cross-Venue Arbitrage ───────────────────────────────────────


class BinaryArbitrageStrategy:
    """
    Cross-venue spread arbitrage (tick-driven).

    ``venue_prices`` maps venue -> mid/indicative price. When the spread
    between the best and worst venue exceeds ``min_spread`` an "arbitrage"
    signal is emitted. (Polymarket binary YES+NO<$1 variant handled by
    strategies/binary_arbitrage.py; this class targets CEX spread arb.)

    Config keys:
        venues (list, default ["BINANCE", "BYBIT"])  reference venues
        min_spread (float, 0.001)                    minimum spread to act
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.venues = list(config.get("venues", ["BINANCE", "BYBIT"]))
        self.min_spread = float(config.get("min_spread", 0.001))
        self.signals_emitted = 0

    def on_tick(self, tick_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        prices = tick_data.get("venue_prices") or {}
        if len(prices) < 2:
            return None

        best_bid = max(prices.values())
        best_ask = min(prices.values())
        if best_ask <= 0:
            return None

        spread = (best_bid - best_ask) / best_ask
        if spread > self.min_spread:
            self.signals_emitted += 1
            return {
                "action": "arbitrage",
                "reason": f"cross-venue spread {spread:.4%} > {self.min_spread:.4%}",
                "confidence": round(min(0.95, spread / self.min_spread * 0.5), 4),
                "spread": spread,
            }
        return None

    def on_bar(self, bar_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Arb opportunities are tick-level; bars carry no venue depth."""
        return None


# ─── Strategy Registry ───────────────────────────────────────────────────────

STRATEGY_REGISTRY = {
    "regime_momentum": RegimeMomentumStrategy,
    "minervini_sea": MinerviniSeaStrategy,
    "sniper": SniperStrategy,
    "binary_arbitrage": BinaryArbitrageStrategy,
}


def get_strategy(name: str, config: Optional[Dict[str, Any]] = None):
    """
    Get a strategy instance by name.

    Args:
        name: Strategy name (must be in STRATEGY_REGISTRY)
        config: Strategy configuration

    Returns:
        Strategy instance
    """
    if name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}"
        )
    return STRATEGY_REGISTRY[name](config or {})


def list_strategies() -> List[str]:
    """List available strategy names."""
    return list(STRATEGY_REGISTRY.keys())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("NAUTILUS STRATEGY REGISTRY")
    print("=" * 60)
    print(f"\nRegistered Strategies:")
    for name in list_strategies():
        print(f"  • {name}")

    # Quick self-test on synthetic data (no network)
    print("\nSelf-test: RegimeMomentum on synthetic uptrend")
    strat = get_strategy("regime_momentum", {"regime": "RISK_ON", "lookback": 20,
                                              "ema_fast": 5, "ema_slow": 10,
                                              "momentum_threshold": 0.005})
    n_signals = 0
    for i in range(1, 61):
        bar = {"timestamp": i * 3600000, "open": 100 + i, "high": 100 + i + 0.5,
               "low": 100 + i - 0.5, "close": 100 + i, "volume": 1000}
        sig = strat.on_bar(bar)
        if sig:
            n_signals += 1
            if n_signals == 1:
                print(f"  first signal: {sig['action']} @ bar {i} conf={sig['confidence']}")
    print(f"  {n_signals} signals over 60 uptrend bars "
          f"(expect >0: momentum + EMA alignment)")

    print("\nSelf-test: MinerviniSea on flat market (expect 0 signals)")
    strat2 = get_strategy("minervini_sea")
    flat_signals = 0
    for i in range(300):
        bar = {"timestamp": i * 86400000, "open": 100, "high": 100, "low": 100,
               "close": 100, "volume": 1000}
        if strat2.on_bar(bar):
            flat_signals += 1
    print(f"  {flat_signals} signals (expect 0: no 52w high, no trend)")
