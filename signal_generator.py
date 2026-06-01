#!/usr/bin/env python3
"""
Advanced Signal Generator (ported from Fincept-Corporation/FinceptTerminal)
==========================================================================
Multi-indicator signal generation for crypto trading.

Adapted from: fincept-qt/scripts/Analytics/backtesting/backtestingpy/btp_signals.py
Extended with crypto-specific signals.

Signal Types:
- crossover       — Fast/slow indicator crossover
- threshold       — Oscillator overbought/oversold
- divergence      — Price/indicator divergence
- breakout        — Support/resistance break
- momentum        — Rate of change confirmation
- volume          — Volume confirmation signals
- trend           — Multi-timeframe trend alignment
- composite       — Multi-signal consensus

Usage:
    from signal_generator import SignalGenerator
    sg = SignalGenerator()
    signals = sg.generate_all(df)  # df with OHLCV columns
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class TradeSignal:
    name: str
    action: str          # "BUY" or "SELL"
    strength: float      # 0.0 - 1.0
    indicator: str       # Which indicator generated it
    timestamp: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "action": self.action,
            "strength": self.strength, "indicator": self.indicator,
            "timestamp": self.timestamp, "metadata": self.metadata,
        }


class SignalGenerator:
    """
    Multi-indicator signal generator.
    Combines signals from multiple indicators with strength-based filtering.
    """

    def __init__(self, min_strength: float = 0.3):
        self.min_strength = min_strength

    def generate_all(self, df: pd.DataFrame) -> List[TradeSignal]:
        """Generate all signal types from OHLCV DataFrame."""
        signals = []
        signals.extend(self.crossover_signals(df))
        signals.extend(self.threshold_signals(df))
        signals.extend(self.divergence_signals(df))
        signals.extend(self.breakout_signals(df))
        signals.extend(self.momentum_signals(df))
        signals.extend(self.volume_signals(df))
        signals.extend(self.trend_signals(df))

        # Sort by strength descending
        signals.sort(key=lambda s: s.strength, reverse=True)
        return signals

    def composite_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate composite consensus signal from all indicators.
        Returns: {"action": "BUY"/"SELL"/"HOLD", "confidence": 0-1, "signals": [...]}
        """
        all_signals = self.generate_all(df)
        buy_strength = sum(s.strength for s in all_signals if s.action == "BUY")
        sell_strength = sum(s.strength for s in all_signals if s.action == "SELL")
        total = buy_strength + sell_strength

        if total == 0:
            return {"action": "HOLD", "confidence": 0.0, "signals": []}

        buy_ratio = buy_strength / total
        if buy_ratio > 0.6:
            action, confidence = "BUY", buy_ratio
        elif buy_ratio < 0.4:
            action, confidence = "SELL", 1 - buy_ratio
        else:
            action, confidence = "HOLD", 0.5

        return {
            "action": action,
            "confidence": round(confidence, 4),
            "buy_strength": round(buy_strength, 4),
            "sell_strength": round(sell_strength, 4),
            "num_signals": len(all_signals),
            "signals": [s.to_dict() for s in all_signals],
        }

    # ─── Individual Signal Methods ──────────────────────────────

    def crossover_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """MA crossovers, MACD crossovers."""
        signals = []
        if len(df) < 50:
            return signals

        close = df["Close"] if "Close" in df else df["close"]

        # SMA crossover (fast=20, slow=50)
        sma_fast = close.rolling(20).mean()
        sma_slow = close.rolling(50).mean()
        if len(sma_fast) > 2 and sma_fast.iloc[-2] <= sma_slow.iloc[-2] and sma_fast.iloc[-1] > sma_slow.iloc[-1]:
            signals.append(TradeSignal("SMA20/50 Golden Cross", "BUY", 0.7, "SMA Crossover"))
        elif len(sma_fast) > 2 and sma_fast.iloc[-2] >= sma_slow.iloc[-2] and sma_fast.iloc[-1] < sma_slow.iloc[-1]:
            signals.append(TradeSignal("SMA20/50 Death Cross", "SELL", 0.7, "SMA Crossover"))

        # EMA crossover (fast=12, slow=26)
        ema_fast = close.ewm(span=12).mean()
        ema_slow = close.ewm(span=26).mean()
        if len(ema_fast) > 2 and ema_fast.iloc[-2] <= ema_slow.iloc[-2] and ema_fast.iloc[-1] > ema_slow.iloc[-1]:
            signals.append(TradeSignal("EMA12/26 Crossover", "BUY", 0.6, "EMA Crossover"))
        elif len(ema_fast) > 2 and ema_fast.iloc[-2] >= ema_slow.iloc[-2] and ema_fast.iloc[-1] < ema_slow.iloc[-1]:
            signals.append(TradeSignal("EMA12/26 Crossunder", "SELL", 0.6, "EMA Crossover"))

        return signals

    def threshold_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """RSI oversold/overbought, Stochastic."""
        signals = []
        if len(df) < 15:
            return signals

        close = df["Close"] if "Close" in df else df["close"]

        # RSI(14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        if len(rsi.dropna()) > 1:
            rsi_val = rsi.iloc[-1]
            prev = rsi.iloc[-2]
            if prev < 30 and rsi_val >= 30:
                signals.append(TradeSignal("RSI Oversold Bounce", "BUY", 0.6, "RSI", metadata={"rsi": round(rsi_val, 1)}))
            elif prev > 70 and rsi_val <= 70:
                signals.append(TradeSignal("RSI Overbought Pullback", "SELL", 0.6, "RSI", metadata={"rsi": round(rsi_val, 1)}))
            elif rsi_val < 25:
                signals.append(TradeSignal("RSI Extreme Oversold", "BUY", 0.8, "RSI", metadata={"rsi": round(rsi_val, 1)}))
            elif rsi_val > 75:
                signals.append(TradeSignal("RSI Extreme Overbought", "SELL", 0.8, "RSI", metadata={"rsi": round(rsi_val, 1)}))

        return signals

    def divergence_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """Price/indicator divergence (simplified)."""
        signals = []
        if len(df) < 30:
            return signals

        close = df["Close"] if "Close" in df else df["close"]
        rsi = self._calc_rsi(close)

        if rsi is None or len(rsi) < 20:
            return signals

        # Bullish divergence: price lower low, RSI higher low
        price_low1 = close.iloc[-10:-5].min()
        price_low2 = close.iloc[-5:].min()
        rsi_low1 = rsi.iloc[-10:-5].min()
        rsi_low2 = rsi.iloc[-5:].min()

        if price_low2 < price_low1 and rsi_low2 > rsi_low1:
            signals.append(TradeSignal("Bullish RSI Divergence", "BUY", 0.65, "RSI Divergence"))
        elif price_low2 > price_low1 and rsi_low2 < rsi_low1:
            signals.append(TradeSignal("Bearish RSI Divergence", "SELL", 0.65, "RSI Divergence"))

        return signals

    def breakout_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """Bollinger Band breakouts, support/resistance."""
        signals = []
        if len(df) < 25:
            return signals

        close = df["Close"] if "Close" in df else df["close"]

        # Bollinger Bands
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper = sma20 + 2 * std20
        lower = sma20 - 2 * std20

        if len(upper.dropna()) > 1:
            if close.iloc[-2] <= upper.iloc[-2] and close.iloc[-1] > upper.iloc[-1]:
                signals.append(TradeSignal("BB Upper Breakout", "BUY", 0.5, "Bollinger Bands"))
            elif close.iloc[-2] >= lower.iloc[-2] and close.iloc[-1] < lower.iloc[-1]:
                signals.append(TradeSignal("BB Lower Breakdown", "SELL", 0.5, "Bollinger Bands"))

        return signals

    def momentum_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """Rate of change, momentum confirmation."""
        signals = []
        if len(df) < 15:
            return signals

        close = df["Close"] if "Close" in df else df["close"]

        # ROC(10)
        roc = close.pct_change(10) * 100
        if len(roc.dropna()) > 1:
            if roc.iloc[-2] <= 0 and roc.iloc[-1] > 0:
                signals.append(TradeSignal("ROC Bullish Flip", "BUY", 0.5, "ROC", metadata={"roc": round(roc.iloc[-1], 2)}))
            elif roc.iloc[-2] >= 0 and roc.iloc[-1] < 0:
                signals.append(TradeSignal("ROC Bearish Flip", "SELL", 0.5, "ROC", metadata={"roc": round(roc.iloc[-1], 2)}))

        return signals

    def volume_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """Volume confirmation signals."""
        signals = []
        vol_col = None
        for c in ["Volume", "volume", "vol"]:
            if c in df:
                vol_col = c
                break

        if vol_col is None or len(df) < 25:
            return signals

        close = df["Close"] if "Close" in df else df["close"]
        volume = df[vol_col]

        vol_sma = volume.rolling(20).mean()
        if len(vol_sma.dropna()) > 1:
            vol_ratio = volume.iloc[-1] / vol_sma.iloc[-1] if vol_sma.iloc[-1] > 0 else 1
            if vol_ratio > 2.0:
                price_up = close.iloc[-1] > close.iloc[-2]
                action = "BUY" if price_up else "SELL"
                signals.append(TradeSignal(
                    f"Volume Spike ({vol_ratio:.1f}x)",
                    action, min(0.8, vol_ratio / 5),
                    "Volume",
                    metadata={"volume_ratio": round(vol_ratio, 2)},
                ))

        return signals

    def trend_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """Multi-timeframe trend alignment using ADX proxy."""
        signals = []
        if len(df) < 50:
            return signals

        close = df["Close"] if "Close" in df else df["close"]

        # Simple trend: compare short-term vs long-term MA
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()

        if len(sma50.dropna()) > 1:
            price_above_20 = close.iloc[-1] > sma20.iloc[-1]
            price_above_50 = close.iloc[-1] > sma50.iloc[-2]
            ma20_above_50 = sma20.iloc[-1] > sma50.iloc[-1]

            if price_above_20 and price_above_50 and ma20_above_50:
                signals.append(TradeSignal("Strong Uptrend", "BUY", 0.4, "Trend"))
            elif not price_above_20 and not price_above_50 and not ma20_above_50:
                signals.append(TradeSignal("Strong Downtrend", "SELL", 0.4, "Trend"))

        return signals

    # ─── Helpers ─────────────────────────────────────────────────

    def _calc_rsi(self, close: pd.Series, period: int = 14) -> Optional[pd.Series]:
        try:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss.replace(0, np.nan)
            return 100 - (100 / (1 + rs))
        except Exception:
            return None


# ── CLI / Test ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📡 Advanced Signal Generator (Fincept-derived)")
    print("=" * 50)

    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "Close": 100 + np.cumsum(np.random.normal(0.001, 0.02, n)),
        "volume": np.random.randint(1000000, 5000000, n),
    })

    sg = SignalGenerator()
    signals = sg.generate_all(df)
    composite = sg.composite_signal(df)

    print(f"\nGenerated {len(signals)} signals:")
    for s in signals[:5]:
        print(f"   {s.action:4} | {s.name} (strength={strength:.2f}, {s.indicator})")

    print(f"\n🎯 Composite: {composite['action']} (confidence={composite['confidence']:.0%})")
    print(f"   Buy strength: {composite['buy_strength']:.2f}, Sell: {composite['sell_strength']:.2f}")
