#!/usr/bin/env python3
"""
QuantStats Analyzer (ported from Fincept-Corporation/FinceptTerminal)
=====================================================================
Comprehensive quantitative statistics for crypto portfolios.

Adapted from: fincept-qt/scripts/Analytics/portfolioManagement/quantstats_analysis.py
Also incorporates: ffn_analysis.py, portfolio_analytics.py patterns.

Metrics:
- Performance: total_return, annualized_return, best/worst day
- Risk: volatility, max_drawdown, VaR, CVaR
- Ratios: Sharpe, Sortino, Calmar, Omega, Information ratio
- Distribution: skew, kurtosis, win rate, profit factor

Usage:
    from quantstats_analyzer import QuantAnalyzer
    qa = QuantAnalyzer()
    stats = qa.analyze(returns_array)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _safe_float(val) -> float:
    """Convert to safe float (handles nan/inf)."""
    try:
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return 0.0
        return v
    except (TypeError, ValueError):
        return 0.0


def _convert_numpy(obj):
    """Recursively convert numpy types to Python native."""
    if isinstance(obj, dict):
        return {k: _convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_numpy(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return _safe_float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, float):
        return _safe_float(obj)
    return obj


class QuantAnalyzer:
    """
    Comprehensive quantitative analysis engine.

    Analyzes portfolio returns and produces a full report with:
    performance metrics, risk ratios, distribution statistics,
    drawdown analysis, and rolling metrics.
    """

    ANNUAL_FACTOR = 365  # Crypto trades 24/7
    RF_RATE = 0.04

    def analyze(
        self,
        returns: np.ndarray,
        weights: Optional[np.ndarray] = None,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Full quantitative analysis of a return series or portfolio.

        Args:
            returns: Return series (1D) or matrix (assets x periods)
            weights: Portfolio weights (if returns is a matrix)
            symbols: Asset symbols

        Returns:
            Complete analysis dict with performance, risk, ratios, drawdown
        """
        returns = np.asarray(returns, dtype=float)
        if returns.ndim == 2 and weights is not None:
            weights = np.asarray(weights)
            port_returns = (returns * weights.reshape(-1, 1)).sum(axis=0)
        elif returns.ndim == 2:
            port_returns = returns.mean(axis=0)
        else:
            port_returns = returns

        port_returns = port_returns[~np.isnan(port_returns)]
        if len(port_returns) == 0:
            return {"error": "No valid returns data"}

        return _convert_numpy({
            "performance": self._performance(port_returns),
            "risk": self._risk(port_returns),
            "ratios": self._ratios(port_returns),
            "distribution": self._distribution(port_returns),
            "drawdown": self._drawdown(port_returns),
            "rolling": self._rolling(port_returns),
            "summary": self._summary(port_returns),
            "metadata": {
                "observations": len(port_returns),
                "annual_factor": self.ANNUAL_FACTOR,
                "risk_free_rate": self.RF_RATE,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        })

    def _performance(self, r: np.ndarray) -> Dict:
        cumulative = np.cumprod(1 + r)
        total_ret = cumulative[-1] / cumulative[0] - 1 if len(cumulative) > 0 else 0
        n = len(r)
        ann_ret = (1 + total_ret) ** (self.ANNUAL_FACTOR / max(n, 1)) - 1
        return {
            "total_return": _safe_float(total_ret),
            "annualized_return": _safe_float(ann_ret),
            "average_daily_return": _safe_float(r.mean()),
            "best_day": _safe_float(r.max()),
            "worst_day": _safe_float(r.min()),
            "positive_days": int((r > 0).sum()),
            "negative_days": int((r < 0).sum()),
            "total_days": n,
        }

    def _risk(self, r: np.ndarray) -> Dict:
        ann_vol = r.std() * np.sqrt(self.ANNUAL_FACTOR)
        downside = r[r < 0]
        sortino_vol = downside.std() * np.sqrt(self.ANNUAL_FACTOR) if len(downside) > 0 else 0

        var_95 = np.percentile(r, 5)
        var_99 = np.percentile(r, 1)
        cvar_95 = r[r <= var_95].mean() if len(r[r <= var_95]) > 0 else var_95
        cvar_99 = r[r <= var_99].mean() if len(r[r <= var_99]) > 0 else var_99

        return {
            "annualized_volatility": _safe_float(ann_vol),
            "daily_volatility": _safe_float(r.std()),
            "downside_volatility": _safe_float(sortino_vol),
            "var_95": _safe_float(var_95),
            "var_99": _safe_float(var_99),
            "cvar_95": _safe_float(cvar_95),
            "cvar_99": _safe_float(cvar_99),
            "max_consecutive_losses": self._max_consecutive(r < 0),
            "max_consecutive_wins": self._max_consecutive(r > 0),
        }

    def _ratios(self, r: np.ndarray) -> Dict:
        ann_ret = r.mean() * self.ANNUAL_FACTOR
        ann_vol = r.std() * np.sqrt(self.ANNUAL_FACTOR)

        # Sharpe
        sharpe = (ann_ret - self.RF_RATE) / ann_vol if ann_vol > 0 else 0

        # Sortino
        downside = r[r < 0]
        ds_vol = downside.std() * np.sqrt(self.ANNUAL_FACTOR) if len(downside) > 0 else 0
        sortino = (ann_ret - self.RF_RATE) / ds_vol if ds_vol > 0 else 0

        # Calmar
        cumulative = np.cumprod(1 + r)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_dd = abs(drawdown.min())
        calmar = ann_ret / max_dd if max_dd > 0 else 0

        # Omega
        gains = r[r > 0].sum()
        losses = abs(r[r < 0].sum())
        omega = gains / losses if losses > 0 else float('inf')

        # Information Ratio (vs benchmark = 0)
        ir = ann_ret / ann_vol if ann_vol > 0 else 0

        return {
            "sharpe_ratio": _safe_float(sharpe),
            "sortino_ratio": _safe_float(sortino),
            "calmar_ratio": _safe_float(calmar),
            "omega_ratio": _safe_float(omega),
            "information_ratio": _safe_float(ir),
        }

    def _distribution(self, r: np.ndarray) -> Dict:
        wins = r[r > 0]
        losses = r[r < 0]
        win_rate = len(wins) / len(r) if len(r) > 0 else 0
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        profit_factor = abs(avg_win * len(wins) / (avg_loss * len(losses))) if len(losses) > 0 and avg_loss != 0 else 0
        expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss

        return {
            "win_rate": _safe_float(win_rate),
            "avg_win": _safe_float(avg_win),
            "avg_loss": _safe_float(avg_loss),
            "profit_factor": _safe_float(profit_factor),
            "expectancy": _safe_float(expectancy),
            "skewness": _safe_float(pd.Series(r).skew()),
            "kurtosis": _safe_float(pd.Series(r).kurtosis()),
        }

    def _drawdown(self, r: np.ndarray) -> Dict:
        cumulative = np.cumprod(1 + r)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_dd = drawdown.min()

        # Max drawdown duration
        in_dd = drawdown < 0
        dd_starts = np.where(np.diff(in_dd.astype(int)) == 1)[0] + 1
        dd_ends = np.where(np.diff(in_dd.astype(int)) == -1)[0] + 1
        if len(dd_starts) > 0 and len(dd_ends) > 0:
            dd_ends = dd_ends[dd_ends > dd_starts[0]]
            if len(dd_ends) > 0:
                durations = dd_ends - dd_starts[:len(dd_ends)]
                max_dd_duration = int(durations.max()) if len(durations) > 0 else 0
            else:
                max_dd_duration = 0
        else:
            max_dd_duration = 0

        return {
            "max_drawdown": _safe_float(max_dd),
            "max_drawdown_pct": _safe_float(max_dd * 100),
            "max_drawdown_duration_days": max_dd_duration,
            "avg_drawdown": _safe_float(drawdown[drawdown < 0].mean()) if (drawdown < 0).any() else 0,
        }

    def _rolling(self, r: np.ndarray, window: int = 30) -> Dict:
        """Rolling metrics."""
        if len(r) < window:
            return {"note": f"Need at least {window} observations"}

        rolling_mean = pd.Series(r).rolling(window).mean().dropna()
        rolling_vol = pd.Series(r).rolling(window).std().dropna()

        return {
            f"rolling_{window}d_avg_return": _safe_float(rolling_mean.iloc[-1]),
            f"rolling_{window}d_volatility": _safe_float(rolling_vol.iloc[-1]),
            f"rolling_{window}d_sharpe": _safe_float(
                (rolling_mean.iloc[-1] * self.ANNUAL_FACTOR) /
                (rolling_vol.iloc[-1] * np.sqrt(self.ANNUAL_FACTOR))
            ) if rolling_vol.iloc[-1] > 0 else 0,
        }

    def _summary(self, r: np.ndarray) -> Dict:
        """One-line summary."""
        ann_ret = r.mean() * self.ANNUAL_FACTOR
        ann_vol = r.std() * np.sqrt(self.ANNUAL_FACTOR)
        sharpe = (ann_ret - self.RF_RATE) / ann_vol if ann_vol > 0 else 0
        cumulative = np.cumprod(1 + r)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_dd = abs(drawdown.min())

        return {
            "annual_return": f"{ann_ret:+.2%}",
            "annual_volatility": f"{ann_vol:.2%}",
            "sharpe_ratio": f"{sharpe:.3f}",
            "max_drawdown": f"{max_dd:.2%}",
            "win_rate": f"{(r > 0).mean():.1%}",
        }

    def _max_consecutive(self, condition: np.ndarray) -> int:
        """Count max consecutive True values."""
        if not condition.any():
            return 0
        max_count = 0
        current = 0
        for val in condition:
            if val:
                current += 1
                max_count = max(max_count, current)
            else:
                current = 0
        return int(max_count)


# ── CLI / Test ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📈 QuantStats Analyzer (Fincept-derived)")
    print("=" * 45)

    np.random.seed(42)
    test_returns = np.random.normal(0.002, 0.035, 252)

    qa = QuantAnalyzer()
    stats = qa.analyze(test_returns)

    print("\n📊 Summary:")
    for k, v in stats["summary"].items():
        print(f"   {k}: {v}")

    print("\n📐 Ratios:")
    for k, v in stats["ratios"].items():
        print(f"   {k}: {v}")

    print("\n⚠️ Risk:")
    for k, v in stats["risk"].items():
        print(f"   {k}: {v}")
