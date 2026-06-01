#!/usr/bin/env python3
"""
Features Pipeline Adapter (ported from Fincept-Corporation/FinceptTerminal)
=============================================================================
Compute technical indicators from candle data (standalone, no agno dependencies).

Adapted from: fincept-qt/scripts/agno_trading/framework/features_pipeline.py

Usage:
    from features_pipeline import TechnicalFeaturesPipeline
    
    pipeline = TechnicalFeaturesPipeline()
    features = pipeline.compute(candles)
    print(features['rsi_14'], features['macd'])
"""

import numpy as np
from typing import Any, Dict, List, Optional


class TechnicalFeaturesPipeline:
    """
    Compute technical indicators from OHLCV candle data.
    """

    def __init__(self, lookback: int = 100):
        self.lookback = lookback

    def compute(self, candles: List[Dict[str, float]]) -> Dict[str, Optional[float]]:
        """
        Compute all technical indicators from candle data.
        
        Args:
            candles: List of dicts with keys: open, high, low, close, volume
            
        Returns:
            Dict of indicator values
        """
        if len(candles) < 30:
            return {}

        closes = np.array([c.get('close', 0) for c in candles], dtype=float)
        highs = np.array([c.get('high', 0) for c in candles], dtype=float)
        lows = np.array([c.get('low', 0) for c in candles], dtype=float)
        volumes = np.array([c.get('volume', 0) for c in candles], dtype=float)

        indicators = {}

        try:
            indicators['rsi_14'] = self._rsi(closes, 14)
            indicators['rsi_7'] = self._rsi(closes, 7)

            macd_data = self._macd(closes)
            indicators.update(macd_data)

            bb_data = self._bollinger_bands(closes)
            indicators.update(bb_data)

            indicators['atr_14'] = self._atr(highs, lows, closes, 14)
            indicators['atr_7'] = self._atr(highs, lows, closes, 7)

            # Moving averages
            indicators['ma_7'] = self._ma(closes, 7)
            indicators['ma_20'] = self._ma(closes, 20)
            indicators['ma_50'] = self._ma(closes, 50)
            indicators['ema_12'] = self._ema(closes, 12)
            indicators['ema_26'] = self._ema(closes, 26)

            # Volatility
            indicators['volatility_14'] = float(np.std(closes[-14:])) if len(closes) >= 14 else 0
            indicators['volatility_24'] = float(np.std(closes[-24:])) if len(closes) >= 24 else 0

            # Volume
            avg_vol = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else 0
            indicators['avg_volume_20'] = avg_vol
            indicators['volume_ratio'] = float(volumes[-1] / avg_vol) if avg_vol > 0 else 1.0

        except Exception:
            pass

        # Round all values
        return {k: round(v, 6) if v is not None else None for k, v in indicators.items()}

    def _rsi(self, prices: np.ndarray, period: int = 14) -> Optional[float]:
        if len(prices) < period + 1:
            return None
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100.0 - (100.0 / (1.0 + rs)))

    def _ema(self, prices: np.ndarray, period: int) -> Optional[float]:
        if len(prices) < period:
            return float(np.mean(prices))
        k = 2.0 / (period + 1.0)
        result = float(np.mean(prices[:period]))
        for p in prices[period:]:
            result = p * k + result * (1.0 - k)
        return result

    def _ma(self, prices: np.ndarray, period: int) -> Optional[float]:
        if len(prices) < period:
            return float(np.mean(prices))
        return float(np.mean(prices[-period:]))

    def _macd(self, prices: np.ndarray) -> Dict[str, Optional[float]]:
        if len(prices) < 35:
            return {'macd': None, 'macd_signal': None, 'macd_histogram': None}

        ema12 = self._ema(prices, 12)
        ema26 = self._ema(prices, 26)
        if ema12 is None or ema26 is None:
            return {'macd': None, 'macd_signal': None, 'macd_histogram': None}

        macd_line = ema12 - ema26

        # Signal line (EMA of MACD values)
        macd_values = []
        for i in range(26, len(prices) + 1):
            slice_ema12 = self._ema(prices[:i], 12)
            slice_ema26 = self._ema(prices[:i], 26)
            if slice_ema12 is not None and slice_ema26 is not None:
                macd_values.append(slice_ema12 - slice_ema26)

        signal = self._ema(np.array(macd_values), 9) if len(macd_values) >= 9 else macd_line
        histogram = macd_line - signal if signal else 0

        return {
            'macd': round(macd_line, 6),
            'macd_signal': round(float(signal), 6),
            'macd_histogram': round(float(histogram), 6)
        }

    def _bollinger_bands(self, prices: np.ndarray, period: int = 20, std_mult: float = 2.0) -> Dict:
        if len(prices) < period:
            return {'bb_upper': None, 'bb_middle': None, 'bb_lower': None}
        recent = prices[-period:]
        middle = float(np.mean(recent))
        std = float(np.std(recent))
        return {
            'bb_upper': round(middle + std_mult * std, 6),
            'bb_middle': round(middle, 6),
            'bb_lower': round(middle - std_mult * std, 6)
        }

    def _atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> Optional[float]:
        if len(highs) < period + 1:
            return None
        trs = []
        for i in range(1, len(highs)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            trs.append(tr)
        return float(np.mean(trs[-period:])) if trs else None
