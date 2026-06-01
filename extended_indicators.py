#!/usr/bin/env python3
"""
Extended Technical Indicators (ported from Fincept-Corporation/FinceptTerminal)
================================================================================
Comprehensive indicator library with talib → pandas → numpy → pure Python fallback cascade.

From: fincept-qt/scripts/agno_trading/tools/technical_indicators.py

Indicators: SMA, EMA, WMA, DEMA, TEMA, TRIMA, KAMA, T3, RSI, MACD, STOCH, STOCHRSI,
CCI, CMO, ROC, ROCR, AROON, BBANDS, ADX, MINUS_DI, PLUS_DI, MFI, ULTOSC, WILLR,
ATR, NATR, TRANGE, AD, ADOSC, OBV, HT_TRENDMODE, HT_DCPERIOD, HT_PHASOR, HT_SINE

Usage:
    from extended_indicators import IndicatorEngine
    engine = IndicatorEngine()
    result = engine.calculate("RSI", prices, period=14)
    all_indicators = engine.batch_calculate(prices, close_prices, high_prices, low_prices, volumes)
"""

import math
import logging
import numpy as np
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class IndicatorEngine:
    """
    Multi-source indicator engine with fallback cascade:
    1. TA-Lib (fastest, most accurate)
    2. Pandas (vectorized)
    3. NumPy (array math)
    4. Pure Python (always works)
    """

    def __init__(self):
        self._has_talib = False
        self._has_pandas = False

        try:
            import talib
            self._has_talib = True
            self._talib = talib
            logger.info("✅ Technical indicators: TA-Lib available")
        except ImportError:
            logger.info("ℹ️ TA-Lib not available, using pandas/numpy fallback")

        try:
            import pandas as pd
            self._has_pandas = True
            self._pd = pd
        except ImportError:
            logger.info("ℹ️ Pandas not available, using numpy fallback")

    def calculate(
        self, name: str,
        prices: Optional[List[float]] = None,
        close: Optional[List[float]] = None,
        high: Optional[List[float]] = None,
        low: Optional[List[float]] = None,
        volume: Optional[List[float]] = None,
        period: int = 14,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate any indicator by name.

        Args:
            name: Indicator name (e.g., "RSI", "MACD", "BBANDS")
            prices: Price series (for simple indicators)
            close: Close prices (for OHLCV-based)
            high: High prices
            low: Low prices
            volume: Volume
            period: Default period
            **kwargs: Additional parameters

        Returns:
            Dict with indicator name, values, current value, metadata
        """
        close = close or prices
        if not close:
            return {"error": "No price data provided"}

        try:
            if self._has_talib:
                return self._calc_talib(name, close, high, low, volume, period, **kwargs)

            if self._has_pandas:
                return self._calc_pandas(name, close, high, low, volume, period, **kwargs)

            return self._calc_numpy(name, close, high, low, volume, period, **kwargs)
        except Exception as e:
            logger.debug(f"Indicator {name} failed: {e}")
            return self._calc_pure(name, close, high, low, volume, period, **kwargs)

    def batch_calculate(
        self,
        prices: List[float],
        close: Optional[List[float]] = None,
        high: Optional[List[float]] = None,
        low: Optional[List[float]] = None,
        volume: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Calculate a standard set of indicators at once."""
        close = close or prices
        results = {}
        for name, period, kwargs in self._default_indicators():
            results[name] = self.calculate(name, close=close, high=high, low=low,
                                          volume=volume, period=period, **kwargs)
        return results

    # ─── TA-Lib Wrapper ──────────────────────────────────────────

    def _calc_talib(self, name, close, high, low, volume, period, **kwargs):
        arr = np.array(close, dtype=float)
        h_arr = np.array(high, dtype=float) if high else None
        l_arr = np.array(low, dtype=float) if low else None
        v_arr = np.array(volume, dtype=float) if volume else None

        func = getattr(self._talib, name, None)
        if func is None:
            return {"error": f"Unknown indicator: {name}"}

        # Build arguments based on indicator type
        if name in ("SMA", "EMA", "WMA", "RSI", "CCI", "CMO", "ROC", "MFI"):
            if name in ("CCI", "MFI"):
                out = func(h_arr, l_arr, arr, timeperiod=period)
            else:
                out = func(arr, timeperiod=period)
        elif name in ("MACD",):
            fast = kwargs.get("macd_fast", 12)
            slow = kwargs.get("macd_slow", 26)
            signal = kwargs.get("macd_signal", 9)
            out = func(arr, fastperiod=fast, slowperiod=slow, signalperiod=signal)
            return {"indicator": name, "macd": out[0][~np.isnan(out[0])].tolist(),
                    "signal": out[1][~np.isnan(out[1])].tolist(),
                    "histogram": out[2][~np.isnan(out[2])].tolist(),
                    "current_macd": float(out[0][-1]), "current_signal": float(out[1][-1]),
                    "source": "talib"}
        elif name in ("BBANDS",):
            nbdev = kwargs.get("nbdev", 2.0)
            out = func(arr, timeperiod=period, nbdevup=nbdev, nbdevdn=nbdev)
            return {"indicator": name, "upper": out[0][~np.isnan(out[0])].tolist(),
                    "middle": out[1][~np.isnan(out[1])].tolist(),
                    "lower": out[2][~np.isnan(out[2])].tolist(),
                    "bandwidth": ((out[0] - out[2]) / out[1])[~np.isnan(out[1])].tolist(),
                    "source": "talib"}
        elif name in ("STOCH",):
            out = func(h_arr, l_arr, arr)
            return {"indicator": name, "slowk": out[0][~np.isnan(out[0])].tolist(),
                    "slowd": out[1][~np.isnan(out[1])].tolist(), "source": "talib"}
        elif name == "ATR":
            out = func(h_arr, l_arr, arr, timeperiod=period)
        elif name == "ADX":
            out = func(h_arr, l_arr, arr, timeperiod=period)
        elif name == "OBV":
            out = func(arr, v_arr)
        else:
            out = func(arr, timeperiod=period)

        vals = np.asarray(out)
        clean = vals[~np.isnan(vals)]
        return {"indicator": name, "period": period, "values": clean.tolist(),
                "current": float(vals[-1]) if not np.isnan(vals[-1]) else None,
                "count": len(clean), "source": "talib"}

    # ─── Pandas Fallback ─────────────────────────────────────────

    def _calc_pandas(self, name, close, high, low, volume, period, **kwargs):
        s = self._pd.Series(close)
        h = self._pd.Series(high) if high else None
        l = self._pd.Series(low) if low else None
        v = self._pd.Series(volume) if volume else None

        if name == "SMA":
            vals = s.rolling(period).mean()
        elif name == "EMA":
            vals = s.ewm(span=period, adjust=False).mean()
        elif name == "RSI":
            delta = s.diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss.replace(0, np.nan)
            vals = 100 - (100 / (1 + rs))
        elif name == "MACD":
            fast = kwargs.get("macd_fast", 12)
            slow = kwargs.get("macd_slow", 26)
            sig = kwargs.get("macd_signal", 9)
            ema_f = s.ewm(span=fast).mean()
            ema_s = s.ewm(span=slow).mean()
            macd = ema_f - ema_s
            signal = macd.ewm(span=sig).mean()
            return {"indicator": "MACD", "macd": macd.dropna().tolist(),
                    "signal": signal.dropna().tolist(),
                    "histogram": (macd - signal).dropna().tolist(),
                    "current_macd": float(macd.iloc[-1]),
                    "source": "pandas"}
        elif name == "BBANDS":
            mid = s.rolling(period).mean()
            std = s.rolling(period).std()
            nbdev = kwargs.get("nbdev", 2)
            upper = mid + nbdev * std
            lower = mid - nbdev * std
            return {"indicator": "BBANDS", "upper": upper.dropna().tolist(),
                    "middle": mid.dropna().tolist(), "lower": lower.dropna().tolist(),
                    "bandwidth": ((upper - lower) / mid).dropna().tolist(),
                    "source": "pandas"}
        elif name == "ATR" and h is not None and l is not None:
            tr1 = h - l
            tr2 = (h - s.shift()).abs()
            tr3 = (l - s.shift()).abs()
            tr = self._pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            vals = tr.rolling(period).mean()
        elif name == "CCI" and h is not None and l is not None:
            tp = (h + l + s) / 3
            vals = (tp - tp.rolling(period).mean()) / (0.015 * tp.rolling(period).std())
        elif name == "WILLR" and h is not None and l is not None:
            hh = h.rolling(period).max()
            ll = l.rolling(period).min()
            vals = -100 * (hh - s) / (hh - ll)
        elif name == "MFI" and v is not None and h is not None and l is not None:
            tp = (h + l + s) / 3
            mf = tp * v
            pos_mf = mf.where(tp > tp.shift(), 0).rolling(period).sum()
            neg_mf = mf.where(tp < tp.shift(), 0).rolling(period).sum()
            mfr = pos_mf / neg_mf.replace(0, np.nan)
            vals = 100 - (100 / (1 + mfr))
        elif name == "ROC":
            vals = s.pct_change(period) * 100
        elif name == "CMO":
            delta = s.diff()
            up = delta.where(delta > 0, 0).rolling(period).sum()
            down = (-delta.where(delta < 0, 0)).rolling(period).sum()
            vals = 100 * (up - down) / (up + down).replace(0, np.nan)
        else:
            return {"indicator": name, "error": f"Not implemented in pandas fallback"}

        clean = vals.dropna()
        current = float(vals.iloc[-1]) if not vals.empty and not pd.isna(vals.iloc[-1]) else None
        return {"indicator": name, "period": period, "values": clean.tolist(),
                "current": current, "count": len(clean), "source": "pandas"}

    # ─── NumPy Fallback ──────────────────────────────────────────

    def _calc_numpy(self, name, close, high, low, volume, period, **kwargs):
        arr = np.array(close, dtype=float)

        if name == "SMA":
            kernel = np.ones(period) / period
            vals = np.convolve(arr, kernel, mode="valid")
        elif name == "EMA":
            alpha = 2.0 / (period + 1)
            vals = np.zeros_like(arr)
            vals[0] = arr[0]
            for i in range(1, len(arr)):
                vals[i] = alpha * arr[i] + (1 - alpha) * vals[i - 1]
        elif name == "RSI":
            deltas = np.diff(arr)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.convolve(gains, np.ones(period) / period, mode="valid")
            avg_loss = np.convolve(losses, np.ones(period) / period, mode="valid")
            rs = avg_gain / np.maximum(avg_loss, 1e-10)
            vals = 100 - (100 / (1 + rs))
        elif name == "BBANDS":
            kernel = np.ones(period) / period
            mid = np.convolve(arr, kernel, mode="valid")
            # Approximate std with rolling window
            std_vals = np.array([np.std(arr[max(0, i-period+1):i+1]) for i in range(period-1, len(arr))])
            nbdev = kwargs.get("nbdev", 2)
            upper = mid + nbdev * std_vals
            lower = mid - nbdev * std_vals
            return {"indicator": "BBANDS", "upper": upper.tolist(), "middle": mid.tolist(),
                    "lower": lower.tolist(), "source": "numpy"}
        elif name == "ROC":
            vals = np.zeros_like(arr)
            vals[:period] = np.nan
            vals[period:] = (arr[period:] / arr[:-period] - 1) * 100
            vals = vals[~np.isnan(vals)]
        else:
            return {"indicator": name, "error": f"Not in numpy fallback"}

        clean = vals[~np.isnan(vals)] if vals.dtype == float else vals
        return {"indicator": name, "period": period, "values": clean.tolist()[-50:],
                "current": float(clean[-1]) if len(clean) > 0 else None,
                "count": len(clean), "source": "numpy"}

    # ─── Pure Python Fallback ────────────────────────────────────

    def _calc_pure(self, name, close, high, low, volume, period, **kwargs):
        if name == "SMA":
            vals = [sum(close[max(0, i-period):i+1]) / min(period, i+1) for i in range(len(close))]
        elif name == "EMA":
            alpha = 2.0 / (period + 1)
            vals = [close[0]]
            for i in range(1, len(close)):
                vals.append(alpha * close[i] + (1 - alpha) * vals[-1])
        elif name == "RSI":
            deltas = [close[i] - close[i-1] for i in range(1, len(close))]
            gains = [max(d, 0) for d in deltas]
            losses = [max(-d, 0) for d in deltas]
            if len(gains) < period:
                return {"indicator": "RSI", "error": "Not enough data"}
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            rs = avg_gain / max(avg_loss, 1e-10)
            vals = [100 - (100 / (1 + rs))]
            for i in range(period, len(gains)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
                rs = avg_gain / max(avg_loss, 1e-10)
                vals.append(100 - (100 / (1 + rs)))
        elif name == "BBANDS":
            vals_mid, vals_upper, vals_lower = [], [], []
            nbdev = kwargs.get("nbdev", 2)
            for i in range(len(close)):
                window = close[max(0, i-period+1):i+1]
                mid = sum(window) / len(window)
                std = (sum((x - mid)**2 for x in window) / len(window)) ** 0.5
                vals_mid.append(mid)
                vals_upper.append(mid + nbdev * std)
                vals_lower.append(mid - nbdev * std)
            return {"indicator": "BBANDS", "upper": vals_upper, "middle": vals_mid,
                    "lower": vals_lower, "source": "pure_python"}
        else:
            return {"indicator": name, "error": "No fallback available"}

        clean = [v for v in vals if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))]
        return {"indicator": name, "period": period, "values": clean[-50:],
                "current": clean[-1] if clean else None,
                "count": len(clean), "source": "pure_python"}

    # ─── Default Indicator Set ───────────────────────────────────

    def _default_indicators(self):
        """Standard set of indicators for batch calculation."""
        return [
            ("RSI", 14, {}),
            ("MACD", 12, {}),
            ("BBANDS", 20, {}),
            ("SMA", 20, {}),
            ("SMA", 50, {}),
            ("EMA", 12, {}),
            ("EMA", 26, {}),
            ("ATR", 14, {}),
            ("CCI", 14, {}),
            ("ROC", 10, {}),
        ]


# ── CLI / Test ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📊 Extended Technical Indicators (Fincept-derived)")
    print("=" * 52)

    np.random.seed(42)
    n = 200
    prices = list(100 + np.cumsum(np.random.normal(0.001, 0.02, n)))
    high = [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices]
    low = [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices]
    volume = list(np.random.randint(1000000, 5000000, n))

    engine = IndicatorEngine()
    print(f"Engine: talib={engine._has_talib}, pandas={engine._has_pandas}\n")

    # Calculate key indicators
    for name in ["RSI", "MACD", "BBANDS", "SMA", "EMA", "ATR", "CCI"]:
        result = engine.calculate(name, close=prices, high=high, low=low, period=14)
        source = result.get("source", "error")
        if "error" not in result:
            current = result.get("current", "?")
            print(f"   {name:8s} ({source:>12s}): current={current}")
        else:
            print(f"   {name:8s}: ERROR - {result['error']}")

    # Batch calculation
    print(f"\n📊 Batch calculation (10 indicators)...")
    batch = engine.batch_calculate(prices, close=prices, high=high, low=low, volume=volume)
    ok = sum(1 for v in batch.values() if "error" not in v)
    print(f"   {ok}/{len(batch)} indicators computed successfully")
