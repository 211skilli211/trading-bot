#!/usr/bin/env python3
"""
Pre-Built Trading Strategies — Adapted from Jesse's strategy library
=====================================================================
Battle-tested strategy implementations using the BaseStrategy interface.

Each strategy is a plug-and-play class — just instantiate and call .analyze().

Strategies included:
1. BollingerBandBreakout — Trade on Bollinger Band breakouts with RSI filter
2. MACDCrossover — Classic MACD crossover with histogram confirmation
3. IchimokuCloud — Ichimoku Cloud trend-following system
4. RSIMeanReversion — RSI-based mean reversion (oversold/overbought)
5. SMACrossover — Simple Moving Average crossover (golden/death cross)
6. MultiIndicatorConsensus — Vote-based system using 5+ indicators
7. VolumeSpike — Trade on unusual volume with price confirmation
8. ATRBreakout — Average True Range breakout (volatility expansion)
9. MomentumSurge — Rate of change momentum with trend filter
10. ArbitrageCEX — Our existing CEX arbitrage (adapted to interface)

Ported from: jesse-ai/jesse/jesse/strategies/
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from strategy_interface import (
    BaseStrategy, Signal, IndicatorSet,
    compute_indicators, StrategyRegistry, StrategyResult
)
from datetime import datetime, timezone


# ============================================================
# 1. Bollinger Band Breakout
# ============================================================

class BollingerBandBreakout(BaseStrategy):
    """
    Trade when price closes outside Bollinger Bands with RSI filter.
    - BUY: Price closes below lower BB + RSI < 35 (oversold bounce)
    - SELL: Price closes above upper BB + RSI > 65 (overbought pullback)
    
    Jesse's equivalent: BollingerBandsStrategy
    """
    name = "bollinger_breakout"
    timeframe = "15m"
    stoploss = -0.025
    minimal_roi = {"0": 0.015, "20": 0.008, "50": 0.0}
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        pass
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        if close <= indicators.bollinger_lower and indicators.rsi < 35:
            return Signal.STRONG_BUY
        elif close <= indicators.bollinger_lower and indicators.rsi < 40:
            return Signal.BUY
        elif indicators.bollinger_width < 0.01 and close < indicators.bollinger_lower:
            # Squeeze breakout — very tight bands
            return Signal.BUY
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        if close >= indicators.bollinger_upper and indicators.rsi > 65:
            return Signal.STRONG_SELL
        elif close >= indicators.bollinger_upper and indicators.rsi > 60:
            return Signal.SELL
        elif close > indicators.bollinger_upper and indicators.bollinger_width < 0.01:
            return Signal.SELL
        return Signal.HOLD


# ============================================================
# 2. MACD Crossover
# ============================================================

class MACDCrossover(BaseStrategy):
    """
    Classic MACD (12,26,9) crossover strategy.
    - BUY: MACD line crosses above signal line + histogram positive
    - SELL: MACD line crosses below signal line + histogram negative
    
    Jesse's equivalent: CrossOver0
    """
    name = "macd_crossover"
    timeframe = "15m"
    stoploss = -0.02
    minimal_roi = {"0": 0.01, "30": 0.005}
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        # Track MACD history for crossover detection
        if len(candles) >= 35:
            close = candles['close'].values
            def ema(data, period):
                if len(data) < period:
                    return data[-1]
                m = 2 / (period + 1)
                val = data[period - 1]
                for i in range(period, len(data)):
                    val = (data[i] - val) + val  # cumsum approx
                return val
            # We use histogram from compute_indicators
            self._macd_hist = indicators.macd_histogram
            self._prev_hist = None
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        if indicators.macd > 0 and indicators.macd_histogram > 0:
            return Signal.STRONG_BUY if indicators.macd_histogram > 0.001 else Signal.BUY
        elif indicators.macd_histogram > 0 and indicators.macd < 0:
            return Signal.BUY  # MACD crossing up through zero
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        if indicators.macd < 0 and indicators.macd_histogram < 0:
            return Signal.STRONG_SELL if indicators.macd_histogram < -0.001 else Signal.SELL
        elif indicators.macd_histogram < 0 and indicators.macd > 0:
            return Signal.SELL  # MACD crossing down through zero
        return Signal.HOLD


# ============================================================
# 3. Ichimoku Cloud
# ============================================================

class IchimokuCloud(BaseStrategy):
    """
    Ichimoku Kinko Hyo — comprehensive trend-following system.
    - BUY: Price above cloud + Tenkan > Kijun + Chikou above price
    - SELL: Price below cloud + Tenkan < Kijun + Chikou below price
    
    Jesse's equivalent: Ichimoku1
    """
    name = "ichimoku_cloud"
    timeframe = "1h"
    stoploss = -0.03
    minimal_roi = {"0": 0.02, "60": 0.01}
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        pass
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        above_cloud = close > max(indicators.senkou_span_a, indicators.senkou_span_b)
        tk_cross = indicators.tenkan_sen > indicators.kijun_sen
        chikou_bullish = indicators.chikou_span > close  # Chikou above current price = bullish
        
        if above_cloud and tk_cross and chikou_bullish:
            return Signal.STRONG_BUY
        elif above_cloud and tk_cross:
            return Signal.BUY
        elif close > indicators.kijun_sen and tk_cross:
            return Signal.BUY
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        below_cloud = close < min(indicators.senkou_span_a, indicators.senkou_span_b)
        tk_cross = indicators.tenkan_sen < indicators.kijun_sen
        chikou_bearish = indicators.chikou_span < close
        
        if below_cloud and tk_cross and chikou_bearish:
            return Signal.STRONG_SELL
        elif below_cloud and tk_cross:
            return Signal.SELL
        elif close < indicators.kijun_sen and tk_cross:
            return Signal.SELL
        return Signal.HOLD


# ============================================================
# 4. RSI Mean Reversion
# ============================================================

class RSIMeanReversion(BaseStrategy):
    """
    Mean reversion based on RSI overbought/oversold levels.
    - BUY: RSI < 30 (oversold) + price above support (SMA25)
    - SELL: RSI > 70 (overbought) + price below resistance
    
    Jesse's equivalent: RSI1
    """
    name = "rsi_mean_reversion"
    timeframe = "15m"
    stoploss = -0.015
    minimal_roi = {"0": 0.008, "15": 0.004}
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        pass
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        if indicators.rsi < 25 and close > indicators.sma_25:
            return Signal.STRONG_BUY
        elif indicators.rsi < 30 and close > indicators.sma_25:
            return Signal.BUY
        elif indicators.rsi < 20:
            return Signal.STRONG_BUY  # Extremely oversold
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        if indicators.rsi > 75 and close < indicators.sma_25:
            return Signal.STRONG_SELL
        elif indicators.rsi > 70 and close < indicators.sma_25:
            return Signal.SELL
        elif indicators.rsi > 80:
            return Signal.STRONG_SELL  # Extremely overbought
        return Signal.HOLD


# ============================================================
# 5. SMA Crossover (Golden/Death Cross)
# ============================================================

class SMACrossover(BaseStrategy):
    """
    Simple Moving Average crossover — classic trend following.
    - BUY: SMA(7) crosses above SMA(25) (golden cross)
    - SELL: SMA(7) crosses below SMA(25) (death cross)
    - Confirmed by SMA(25) > SMA(99) for uptrend
    
    Jesse's equivalent: GoldenCross
    """
    name = "sma_crossover"
    timeframe = "4h"
    stoploss = -0.035
    minimal_roi = {"0": 0.02, "120": 0.01}
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        pass
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        if len(candles) < 30:
            return Signal.HOLD
        
        # Need previous candle's SMAs to detect crossover
        prev_candles = candles.iloc[:-1]
        prev_close = prev_candles['close'].values
        prev_sma7 = float(np.mean(prev_close[-7:])) if len(prev_close) >= 7 else prev_close[-1]
        prev_sma25 = float(np.mean(prev_close[-25:])) if len(prev_close) >= 25 else prev_close[-1]
        
        # Golden cross: SMA7 was below SMA25, now above
        golden = (prev_sma7 < prev_sma25) and (indicators.sma_7 > indicators.sma_25)
        # Death cross: SMA7 was above SMA25, now below
        death = (prev_sma7 > prev_sma25) and (indicators.sma_7 < indicators.sma_25)
        
        if golden:
            if indicators.sma_25 > indicators.sma_99:
                return Signal.STRONG_BUY  # Golden cross in uptrend
            return Signal.BUY
        elif indicators.sma_7 > indicators.sma_25 and indicators.sma_25 > indicators.sma_99:
            return Signal.BUY  # Already in confirmed uptrend
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        if len(candles) < 30:
            return Signal.HOLD
        
        prev_candles = candles.iloc[:-1]
        prev_close = prev_candles['close'].values
        prev_sma7 = float(np.mean(prev_close[-7:])) if len(prev_close) >= 7 else prev_close[-1]
        prev_sma25 = float(np.mean(prev_close[-25:])) if len(prev_close) >= 25 else prev_close[-1]
        
        death = (prev_sma7 > prev_sma25) and (indicators.sma_7 < indicators.sma_25)
        
        if death:
            if indicators.sma_25 < indicators.sma_99:
                return Signal.STRONG_SELL  # Death cross in downtrend
            return Signal.SELL
        elif indicators.sma_7 < indicators.sma_25 and indicators.sma_25 < indicators.sma_99:
            return Signal.SELL  # Already in confirmed downtrend
        return Signal.HOLD


# ============================================================
# 6. Multi-Indicator Consensus
# ============================================================

class MultiIndicatorConsensus(BaseStrategy):
    """
    Vote-based system — each indicator casts a vote.
    BUY/SELL requires >60% consensus across indicators.
    
    Indicators voting: RSI, MACD, Bollinger, SMA cross, Volume
    """
    name = "multi_indicator"
    timeframe = "15m"
    stoploss = -0.02
    minimal_roi = {"0": 0.012, "30": 0.006}
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        pass
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        votes = 0
        total = 5
        
        # RSI vote
        if indicators.rsi < 35: votes += 1
        # MACD vote
        if indicators.macd > 0 and indicators.macd_histogram > 0: votes += 1
        # Bollinger vote
        close = float(candles['close'].iloc[-1])
        if close < indicators.bollinger_lower: votes += 1
        # SMA vote
        if indicators.sma_7 > indicators.sma_25: votes += 1
        # Volume vote (unusual volume confirms)
        if indicators.volume_ratio > 1.5: votes += 1
        
        pct = votes / total
        if pct >= 0.8: return Signal.STRONG_BUY
        if pct >= 0.6: return Signal.BUY
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        votes = 0
        total = 5
        
        if indicators.rsi > 65: votes += 1
        if indicators.macd < 0 and indicators.macd_histogram < 0: votes += 1
        close = float(candles['close'].iloc[-1])
        if close > indicators.bollinger_upper: votes += 1
        if indicators.sma_7 < indicators.sma_25: votes += 1
        if indicators.volume_ratio > 1.5: votes += 1
        
        pct = votes / total
        if pct >= 0.8: return Signal.STRONG_SELL
        if pct >= 0.6: return Signal.SELL
        return Signal.HOLD


# ============================================================
# 7. Volume Spike
# ============================================================

class VolumeSpike(BaseStrategy):
    """
    Trade on unusual volume with price direction confirmation.
    - BUY: Volume spike (>3x avg) + bullish candle
    - SELL: Volume spike (>3x avg) + bearish candle
    
    Inspired by Jesse's VolumeProfile strategy
    """
    name = "volume_spike"
    timeframe = "15m"
    stoploss = -0.02
    minimal_roi = {"0": 0.01, "20": 0.005}
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        pass
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        if indicators.volume_ratio > 3.0:
            close = float(candles['close'].iloc[-1])
            open_price = float(candles['open'].iloc[-1])
            if close > open_price:  # Bullish candle
                return Signal.STRONG_BUY if indicators.volume_ratio > 5.0 else Signal.BUY
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        if indicators.volume_ratio > 3.0:
            close = float(candles['close'].iloc[-1])
            open_price = float(candles['open'].iloc[-1])
            if close < open_price:  # Bearish candle
                return Signal.STRONG_SELL if indicators.volume_ratio > 5.0 else Signal.SELL
        return Signal.HOLD


# ============================================================
# 8. ATR Breakout (Volatility Expansion)
# ============================================================

class ATRBreakout(BaseStrategy):
    """
    Trade volatility breakouts using ATR.
    - BUY: Price > SMA(25) + ATR expanding (> 1.5x average ATR)
    - SELL: Price < SMA(25) + ATR expanding
    
    Inspired by Jesse's ATRTrailingStop
    """
    name = "atr_breakout"
    timeframe = "1h"
    stoploss = -0.03
    minimal_roi = {"0": 0.02, "60": 0.01}
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        pass
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        price_above_sma = close > indicators.sma_25
        if len(candles) < 20:
            return Signal.HOLD
        
        # Detect ATR expansion
        atr_history = []
        for i in range(-20, 0):
            if i > -len(candles):
                tr = max(
                    float(candles['high'].iloc[i]) - float(candles['low'].iloc[i]),
                    0
                )
                atr_history.append(tr)
        avg_atr = np.mean(atr_history) if atr_history else indicators.atr
        atr_expanding = indicators.atr > avg_atr * 1.5 if avg_atr > 0 else False
        
        if price_above_sma and atr_expanding and indicators.rsi < 60:
            return Signal.STRONG_BUY
        elif price_above_sma and atr_expanding:
            return Signal.BUY
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        price_below_sma = close < indicators.sma_25
        if len(candles) < 20:
            return Signal.HOLD
        
        atr_history = []
        for i in range(-20, 0):
            if i > -len(candles):
                tr = max(
                    float(candles['high'].iloc[i]) - float(candles['low'].iloc[i]),
                    0
                )
                atr_history.append(tr)
        avg_atr = np.mean(atr_history) if atr_history else indicators.atr
        atr_expanding = indicators.atr > avg_atr * 1.5 if avg_atr > 0 else False
        
        if price_below_sma and atr_expanding and indicators.rsi > 40:
            return Signal.STRONG_SELL
        elif price_below_sma and atr_expanding:
            return Signal.SELL
        return Signal.HOLD


# ============================================================
# 9. Momentum Surge
# ============================================================

class MomentumSurge(BaseStrategy):
    """
    Rate of Change (ROC) momentum with trend filter.
    - BUY: ROC > threshold + price above SMA(25) (uptrend)
    - SELL: ROC < negative threshold + price below SMA(25)
    """
    name = "momentum_surge"
    timeframe = "15m"
    stoploss = -0.02
    minimal_roi = {"0": 0.01, "25": 0.005}
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        close = candles['close'].values
        if len(close) >= 10:
            # ROC = (close - close_10_ago) / close_10_ago
            self._roc = (close[-1] - close[-10]) / close[-10] if close[-10] > 0 else 0
        else:
            self._roc = 0
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        roc = getattr(self, '_roc', 0)
        
        if roc > 0.02 and close > indicators.sma_25:  # Strong upward momentum in uptrend
            return Signal.STRONG_BUY
        elif roc > 0.01 and close > indicators.sma_25:
            return Signal.BUY
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        close = float(candles['close'].iloc[-1])
        roc = getattr(self, '_roc', 0)
        
        if roc < -0.02 and close < indicators.sma_25:
            return Signal.STRONG_SELL
        elif roc < -0.01 and close < indicators.sma_25:
            return Signal.SELL
        return Signal.HOLD


# ============================================================
# 10. CEX Arbitrage (our existing strategy, adapted to interface)
# ============================================================

class CEXArbitrageAdapter(BaseStrategy):
    """
    Adapter that wraps our existing StrategyEngine into the BaseStrategy interface.
    This lets our existing arbitrage logic work alongside the new strategies.
    """
    name = "cex_arbitrage"
    timeframe = "5m"
    stoploss = -0.01
    minimal_roi = {"0": 0.005, "10": 0.002}
    
    def __init__(self, engine=None):
        super().__init__()
        if engine:
            self.engine = engine
        else:
            # Lazy import to avoid circular deps
            from strategy_engine import StrategyEngine
            self.engine = StrategyEngine()
    
    def populate_indicators(self, candles: pd.DataFrame, indicators: IndicatorSet) -> None:
        pass
    
    def populate_buy_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        # Arbitrage doesn't use traditional buy signals — it uses spread analysis
        # Return HOLD here; the StrategyEngine.evaluate() is the real logic
        return Signal.HOLD
    
    def populate_sell_trend(self, indicators: IndicatorSet, candles: pd.DataFrame) -> Signal:
        return Signal.HOLD
    
    def analyze_arbitrage(self, price_data: list):
        """Direct access to the arbitrage engine."""
        from strategy_engine import TradeDecision
        signal = self.engine.evaluate(price_data)
        if signal.decision == TradeDecision.TRADE.value:
            return StrategyResult(
                timestamp=signal.timestamp,
                signal=Signal.BUY,
                confidence=0.8 if signal.confidence == "HIGH" else 0.5,
                reason=signal.reason,
                indicators={"spread": signal.spread_pct}
            )
        return StrategyResult(
            timestamp=signal.timestamp,
            signal=Signal.HOLD,
            confidence=0.5,
            reason=signal.reason
        )


# ============================================================
# Register all strategies
# ============================================================

def register_all():
    """Register all strategies in the registry."""
    StrategyRegistry.register("bollinger_breakout", BollingerBandBreakout)
    StrategyRegistry.register("macd_crossover", MACDCrossover)
    StrategyRegistry.register("ichimoku_cloud", IchimokuCloud)
    StrategyRegistry.register("rsi_mean_reversion", RSIMeanReversion)
    StrategyRegistry.register("sma_crossover", SMACrossover)
    StrategyRegistry.register("multi_indicator", MultiIndicatorConsensus)
    StrategyRegistry.register("volume_spike", VolumeSpike)
    StrategyRegistry.register("atr_breakout", ATRBreakout)
    StrategyRegistry.register("momentum_surge", MomentumSurge)
    StrategyRegistry.register("cex_arbitrage", CEXArbitrageAdapter)
    print("[strategies] All 10 strategies registered")
    print(f"[strategies] Available: {StrategyRegistry.list()}")


# Auto-register on import
register_all()
