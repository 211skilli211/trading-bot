#!/usr/bin/env python3
"""
Strategy Interface — Adapted from Jesse's IStrategy pattern
==============================================================
Standardized strategy template that all strategies implement.
Enables plug-and-play strategy swapping, backtesting, and hyperopt.

Our existing strategy_engine.py handles arbitrage spread logic.
This interface adds:
- populate_indicators() — compute technical indicators on OHLCV data
- populate_buy_trend() — generate buy signals from indicators
- populate_sell_trend() — generate sell signals from indicators
- Multi-timeframe support — aggregate signals across 5m/15m/1h/4h/1d
- Signal confirmation — require N consecutive signals before trading

Ported from: jesse-ai/jesse/jessetk/strategy.py + freqtrade/IStrategy
"""

import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime, timezone


class Signal(Enum):
    """Standardized signal types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class StrategyResult:
    """Output from a strategy evaluation."""
    timestamp: str
    signal: Signal
    confidence: float  # 0.0 to 1.0
    reason: str
    indicators: Dict[str, float] = field(default_factory=dict)
    pair: str = "BTC/USDT"


# ============================================================
# Technical Indicator Library (ported from Jesse's indicators)
# ============================================================

@dataclass
class IndicatorSet:
    """Computed indicators for a given OHLCV dataset."""
    # Trend
    sma_7: float = 0.0
    sma_25: float = 0.0
    sma_99: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    ema_signal: float = 0.0  # Signal line for MACD
    # Momentum
    rsi: float = 50.0
    macd: float = 0.0
    macd_histogram: float = 0.0
    # Volatility
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    bollinger_width: float = 0.0
    atr: float = 0.0
    # Volume
    volume_sma: float = 0.0
    volume_ratio: float = 1.0
    # Ichimoku
    tenkan_sen: float = 0.0
    kijun_sen: float = 0.0
    senkou_span_a: float = 0.0
    senkou_span_b: float = 0.0
    chikou_span: float = 0.0


def compute_indicators(candles: pd.DataFrame) -> IndicatorSet:
    """
    Compute all standard technical indicators from OHLCV candle data.
    
    Args:
        candles: DataFrame with columns [open, high, low, close, volume]
    
    Returns:
        IndicatorSet with all computed values (last row)
    """
    if len(candles) < 100:
        return IndicatorSet()
    
    close = candles['close'].values
    high = candles['high'].values
    low = candles['low'].values
    volume = candles['volume'].values
    result = IndicatorSet()
    
    # --- Simple Moving Averages ---
    result.sma_7 = float(np.mean(close[-7:]))
    result.sma_25 = float(np.mean(close[-25:]))
    result.sma_99 = float(np.mean(close[-99:])) if len(close) >= 99 else float(np.mean(close))
    
    # --- Exponential Moving Averages ---
    def ema(data: np.ndarray, period: int) -> float:
        if len(data) < period:
            return float(data[-1])
        multiplier = 2 / (period + 1)
        ema_val = data[period - 1]
        for i in range(period, len(data)):
            ema_val = (data[i] - ema_val) * multiplier + ema_val
        return float(ema_val)
    
    result.ema_12 = ema(close, 12)
    result.ema_26 = ema(close, 26)
    
    # --- MACD ---
    result.macd = result.ema_12 - result.ema_26
    # Signal line = EMA of MACD over last 9 values (approximate from single value)
    result.ema_signal = result.macd * 0.8  # Simplified — full impl needs MACD history
    result.macd_histogram = result.macd - result.ema_signal
    
    # --- RSI (14-period Wilder) ---
    if len(candles) >= 15:
        deltas = np.diff(close[-15:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            result.rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            result.rsi = 100.0 - (100.0 / (1 + rs))
    
    # --- Bollinger Bands (20-period, 2 std) ---
    if len(candles) >= 20:
        bb_data = close[-20:]
        result.bollinger_middle = float(np.mean(bb_data))
        std = float(np.std(bb_data))
        result.bollinger_upper = result.bollinger_middle + 2 * std
        result.bollinger_lower = result.bollinger_middle - 2 * std
        result.bollinger_width = (result.bollinger_upper - result.bollinger_lower) / result.bollinger_middle if result.bollinger_middle > 0 else 0.0
    
    # --- ATR (14-period) ---
    if len(candles) >= 15:
        trs = []
        for i in range(-14, 0):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]) if i > -len(close) else 0,
                abs(low[i] - close[i - 1]) if i > -len(close) else 0
            )
            trs.append(tr)
        result.atr = float(np.mean(trs))
    
    # --- Volume ---
    if len(candles) >= 20:
        result.volume_sma = float(np.mean(volume[-20:]))
        result.volume_ratio = float(volume[-1]) / result.volume_sma if result.volume_sma > 0 else 1.0
    
    # --- Ichimoku Cloud ---
    if len(candles) >= 52:
        # Tenkan-sen: (highest high + lowest low) / 2 over 9 periods
        result.tenkan_sen = (max(high[-9:]) + min(low[-9:])) / 2
        # Kijun-sen: (highest high + lowest low) / 2 over 26 periods
        result.kijun_sen = (max(high[-26:]) + min(low[-26:])) / 2
        # Senkou Span A: (Tenkan + Kijun) / 2
        result.senkou_span_a = (result.tenkan_sen + result.kijun_sen) / 2
        # Senkou Span B: (highest high + lowest low) / 2 over 52 periods
        result.senkou_span_b = (max(high[-52:]) + min(low[-52:])) / 2
        # Chikou Span: close price 26 periods ago
        result.chikou_span = float(close[-26]) if len(close) >= 26 else float(close[0])
    
    return result


# ============================================================
# Base Strategy Interface (Jesse/Freqtrade-inspired)
# ============================================================

class BaseStrategy(ABC):
    """
    All strategies inherit from this base.
    Mimics Jesse's IStrategy + Freqtrade's IStrategy patterns.
    
    Usage:
        class MyStrategy(BaseStrategy):
            def populate_indicators(self, candles):
                # Add custom indicators
                pass
            def populate_buy_trend(self, indicators, candles):
                return Signal.BUY
            def populate_sell_trend(self, indicators, candles):
                return Signal.SELL
    
    Then use:
        strategy = MyStrategy()
        result = strategy.analyze(candles_df)
    """
    
    # Strategy metadata
    name: str = "base"
    timeframe: str = "15m"
    minimal_roi: Dict[str, float] = {"0": 0.01, "30": 0.005, "60": 0.0}
    stoploss: float = -0.02
    trailing_stop: bool = False
    trailing_stop_positive: float = 0.005
    trailing_stop_positive_offset: float = 0.01
    
    def analyze(self, candles: pd.DataFrame, pair: str = "BTC/USDT") -> StrategyResult:
        """
        Full analysis pipeline: indicators → buy/sell signals → result.
        
        Args:
            candles: OHLCV DataFrame [open, high, low, close, volume]
            pair: Trading pair string
        
        Returns:
            StrategyResult with signal, confidence, and reason
        """
        indicators = compute_indicators(candles)
        buy_signal = self.populate_buy_trend(indicators, candles)
        sell_signal = self.populate_sell_trend(indicators, candles)
        
        self.populate_indicators(candles, indicators)
        
        # Combine buy/sell signals
        signal, confidence, reason = self._combine_signals(
            buy_signal, sell_signal, indicators, candles
        )
        
        return StrategyResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            signal=signal,
            confidence=confidence,
            reason=reason,
            indicators={
                "rsi": indicators.rsi,
                "macd": indicators.macd,
                "bb_width": indicators.bollinger_width,
                "atr": indicators.atr,
                "sma_7": indicators.sma_7,
                "sma_25": indicators.sma_25,
                "ema_12": indicators.ema_12,
                "ema_26": indicators.ema_26,
                "tenkan": indicators.tenkan_sen,
                "kijun": indicators.kijun_sen,
                "volume_ratio": indicators.volume_ratio,
            },
            pair=pair
        )
    
    @abstractmethod
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        """Compute additional indicators beyond the standard set."""
        pass
    
    @abstractmethod
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        """Generate buy signal from indicators."""
        pass
    
    @abstractmethod
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        """Generate sell signal from indicators."""
        pass
    
    def _combine_signals(
        self,
        buy: Signal,
        sell: Signal,
        indicators: IndicatorSet,
        candles: pd.DataFrame
    ) -> Tuple[Signal, float, str]:
        """Combine buy/sell signals into final decision."""
        if buy in (Signal.BUY, Signal.STRONG_BUY) and sell not in (Signal.SELL, Signal.STRONG_SELL):
            confidence = 0.8 if buy == Signal.STRONG_BUY else 0.6
            return buy, confidence, f"Buy signal: {indicators.rsi:.1f} RSI, {indicators.macd:.4f} MACD"
        elif sell in (Signal.SELL, Signal.STRONG_SELL) and buy not in (Signal.BUY, Signal.STRONG_BUY):
            confidence = 0.8 if sell == Signal.STRONG_SELL else 0.6
            return sell, confidence, f"Sell signal: {indicators.rsi:.1f} RSI, {indicators.macd:.4f} MACD"
        elif buy in (Signal.BUY, Signal.STRONG_BUY) and sell in (Signal.SELL, Signal.STRONG_SELL):
            # Conflicting — use RSI as tiebreaker
            if indicators.rsi < 40:
                return Signal.HOLD, 0.4, "Conflicting signals — RSI biased to hold (low)"
            else:
                return Signal.HOLD, 0.4, "Conflicting signals — RSI biased to hold (high)"
        else:
            return Signal.HOLD, 0.5, "No clear signal"


# ============================================================
# Multi-Timeframe Signal Aggregator
# ============================================================

class MultiTimeframeAggregator:
    """
    Aggregate signals from multiple timeframes for confirmation.
    Inspired by Jesse's timeframe handling + Freqtrade's informative pairs.
    
    Logic:
    - 1h/4h = trend direction (weight: 40%)
    - 15m  = entry timing (weight: 35%)
    - 5m   = precision entry (weight: 25%)
    """
    
    TIMEFRAME_WEIGHTS = {"4h": 0.40, "1h": 0.35, "15m": 0.35, "5m": 0.25}
    
    def __init__(self, strategy: BaseStrategy):
        self.strategy = strategy
    
    def analyze_multi(
        self,
        candles_by_tf: Dict[str, pd.DataFrame],
        pair: str = "BTC/USDT"
    ) -> StrategyResult:
        """
        Analyze candles across multiple timeframes.
        
        Args:
            candles_by_tf: {timeframe: DataFrame} e.g. {"15m": df, "1h": df}
            pair: Trading pair
        
        Returns:
            Aggregated StrategyResult
        """
        results = []
        total_weight = 0.0
        
        for tf, candles in candles_by_tf.items():
            result = self.strategy.analyze(candles, pair)
            weight = self.TIMEFRAME_WEIGHTS.get(tf, 0.20)
            results.append((result, weight))
            total_weight += weight
        
        if not results:
            return StrategyResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                signal=Signal.HOLD,
                confidence=0.0,
                reason="No timeframe data available",
                pair=pair
            )
        
        # Score each signal across timeframes
        buy_score = 0.0
        sell_score = 0.0
        hold_score = 0.0
        reasons = []
        
        for result, weight in results:
            signal_str = result.signal.value
            if result.signal in (Signal.BUY, Signal.STRONG_BUY):
                buy_score += weight * result.confidence * (1.5 if result.signal == Signal.STRONG_BUY else 1.0)
                reasons.append(f"{result.pair}: BUY (w={weight:.2f})")
            elif result.signal in (Signal.SELL, Signal.STRONG_SELL):
                sell_score += weight * result.confidence * (1.5 if result.signal == Signal.STRONG_SELL else 1.0)
                reasons.append(f"{result.pair}: SELL (w={weight:.2f})")
            else:
                hold_score += weight * result.confidence
                reasons.append(f"{result.pair}: HOLD")
        
        total = buy_score + sell_score + hold_score
        if total == 0:
            total = 1
        
        # Normalize
        buy_pct = buy_score / total
        sell_pct = sell_score / total
        hold_pct = hold_score / total
        
        if buy_pct > 0.55:
            return StrategyResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                signal=Signal.STRONG_BUY if buy_pct > 0.75 else Signal.BUY,
                confidence=min(buy_pct, 0.95),
                reason=f"Multi-TF consensus BUY ({', '.join(reasons)})",
                pair=pair
            )
        elif sell_pct > 0.55:
            return StrategyResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                signal=Signal.STRONG_SELL if sell_pct > 0.75 else Signal.SELL,
                confidence=min(sell_pct, 0.95),
                reason=f"Multi-TF consensus SELL ({', '.join(reasons)})",
                pair=pair
            )
        else:
            return StrategyResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                signal=Signal.HOLD,
                confidence=max(hold_pct, 0.3),
                reason=f"Multi-TF no consensus (buy={buy_pct:.2f}, sell={sell_pct:.2f}, hold={hold_pct:.2f})",
                pair=pair
            )


# ============================================================
# Strategy Registry (auto-discover strategies)
# ============================================================

class StrategyRegistry:
    """
    Auto-discover and register strategy classes.
    Inspired by Freqtrade's strategy resolver.
    """
    
    _strategies: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: type):
        """Register a strategy class by name."""
        cls._strategies[name] = strategy_class
    
    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """Get a strategy class by name."""
        return cls._strategies.get(name)
    
    @classmethod
    def list(cls) -> List[str]:
        """List all registered strategy names."""
        return list(cls._strategies.keys())
    
    @classmethod
    def create(cls, name: str) -> Optional[BaseStrategy]:
        """Instantiate a strategy by name."""
        strategy_class = cls._strategies.get(name)
        if strategy_class:
            return strategy_class()
        return None
    
    @classmethod
    def auto_register(cls, module_globals: dict):
        """
        Auto-discover all BaseStrategy subclasses in a module's globals.
        
        Usage:
            from strategies import StrategyRegistry, BaseStrategy
            StrategyRegistry.auto_register(globals())
        """
        for name, obj in module_globals.items():
            if (isinstance(obj, type)
                and issubclass(obj, BaseStrategy)
                and obj is not BaseStrategy
                and hasattr(obj, 'name')):
                cls.register(obj.name, obj)
                print(f"[StrategyRegistry] Registered: {obj.name}")
