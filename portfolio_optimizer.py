#!/usr/bin/env python3
"""
Crypto Portfolio Optimizer (ported from Fincept-Corporation/FinceptTerminal)
============================================================================
Multi-strategy portfolio optimization for cryptocurrency portfolios.

Adapted from: fincept-qt/scripts/Analytics/portfolioManagement/portfolio_optimization.py
Strategies:
- max_sharpe        — Maximize Sharpe ratio
- min_volatility    — Minimum variance portfolio
- efficient_risk    — Target volatility
- efficient_return  — Target return
- max_quadratic     — Maximize quadratic utility
- risk_parity       — Equal risk contribution
- black_litterman   — Black-Litterman with views
- equal_weight      — Naive 1/N diversification
- inverse_vol       — Inverse volatility weighting
- momentum          — Momentum-weighted
- mean_var          — Mean-variance (Markowitz)

Usage:
    from portfolio_optimizer import PortfolioOptimizer
    opt = PortfolioOptimizer()
    result = opt.optimize(symbols=["BTC", "ETH", "SOL"], strategy="max_sharpe")
"""

import json
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _convert_numpy(obj):
    """Recursively convert numpy types to Python native."""
    if isinstance(obj, dict):
        return {k: _convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_numpy(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        v = float(obj)
        if np.isnan(v) or np.isinf(v):
            return 0.0
        return v
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return 0.0
    return obj


class PortfolioOptimizer:
    """
    Multi-strategy portfolio optimizer for crypto assets.

    Supports multiple optimization strategies and constraint configurations.
    Uses crypto exchange data (not yfinance — adapted from Fincept's original).
    """

    RISK_FREE_RATE = 0.04  # 4% annual

    def __init__(self, rf_rate: float = 0.04):
        self.rf_rate = rf_rate

    def optimize(
        self,
        symbols: List[str],
        strategy: str = "max_sharpe",
        returns: Optional[np.ndarray] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Optimize portfolio weights.

        Args:
            symbols: Asset symbols (e.g., ["BTC", "ETH", "SOL"])
            strategy: Optimization strategy name
            returns: NxT numpy array of returns (assets x time). If None, fetches from exchange.
            params: Strategy-specific parameters

        Returns:
            Dict with weights, expected_return, volatility, sharpe, and strategy info
        """
        params = params or {}

        if returns is None:
            returns = self._fetch_crypto_returns(symbols)
        if returns is None or returns.size ==0:
            return {"error": "Could not fetch return data for symbols"}

        # Ensure 2D: (n_assets, n_periods)
        if returns.ndim == 1:
            returns = returns.reshape(1, -1)

        n = returns.shape[0]
        mean_returns = returns.mean(axis=1) * 365  # Crypto trades 24/7
        cov_matrix = np.cov(returns) * 365

        try:
            if strategy == "max_sharpe":
                weights = self._max_sharpe(mean_returns, cov_matrix, n)
            elif strategy == "min_volatility":
                weights = self._min_volatility(cov_matrix, n)
            elif strategy == "efficient_risk":
                target = params.get("target_volatility", 0.15)
                weights = self._efficient_risk(mean_returns, cov_matrix, n, target)
            elif strategy == "efficient_return":
                target = params.get("target_return", 0.30)
                weights = self._efficient_return(mean_returns, cov_matrix, n, target)
            elif strategy == "max_quadratic_utility":
                risk_aversion = params.get("risk_aversion", 1.0)
                weights = self._max_quadratic_utility(mean_returns, cov_matrix, n, risk_aversion)
            elif strategy == "risk_parity":
                weights = self._risk_parity(cov_matrix, n)
            elif strategy == "black_litterman":
                weights = self._black_litterman(
                    mean_returns, cov_matrix, n,
                    views=params.get("views", {}),
                    confidence=params.get("confidence", 0.5),
                )
            elif strategy == "equal_weight":
                weights = np.ones(n) / n
            elif strategy == "inverse_vol":
                vols = np.sqrt(np.diag(cov_matrix))
                inv_vols = 1.0 / np.maximum(vols, 1e-8)
                weights = inv_vols / inv_vols.sum()
            elif strategy == "momentum":
                lookback = params.get("lookback", 90)
                if returns.shape[1] >= lookback:
                    momentum_scores = returns[:, -lookback:].sum(axis=1)
                else:
                    momentum_scores = returns.sum(axis=1)
                momentum_scores = np.maximum(momentum_scores, 0)
                total = momentum_scores.sum()
                weights = momentum_scores / total if total > 0 else np.ones(n) / n
            elif strategy == "mean_var":
                weights = self._mean_variance(mean_returns, cov_matrix, n, params.get("risk_aversion", 1.0))
            else:
                logger.warning(f"Unknown strategy '{strategy}', using equal weight")
                weights = np.ones(n) / n

            # Normalize
            weights = np.maximum(weights, 0)  # No shorting
            weights /= weights.sum()

            port_return = float(np.dot(weights, mean_returns))
            port_vol = float(np.sqrt(np.dot(weights, np.dot(cov_matrix, weights))))
            sharpe = float((port_return - self.rf_rate) / port_vol) if port_vol > 0 else 0

            return _convert_numpy({
                "strategy": strategy,
                "symbols": symbols,
                "weights": {s: float(w) for s, w in zip(symbols, weights)},
                "expected_annual_return": port_return,
                "expected_annual_volatility": port_vol,
                "sharpe_ratio": sharpe,
                "risk_free_rate": self.rf_rate,
                "n_assets": n,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            # Fallback to equal weight
            weights = np.ones(n) / n
            return _convert_numpy({
                "strategy": strategy,
                "symbols": symbols,
                "weights": {s: float(w) for s, w in zip(symbols, weights)},
                "error": str(e),
                "fallback": "equal_weight",
            })

    def optimize_all(
        self, symbols: List[str], returns: Optional[np.ndarray] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Run all optimization strategies and return comparative results."""
        strategies = [
            "max_sharpe", "min_volatility", "equal_weight",
            "inverse_vol", "momentum", "risk_parity", "mean_var",
        ]
        results = {}
        for strat in strategies:
            results[strat] = self.optimize(symbols, strategy=strat, returns=returns)

        # Rank by Sharpe
        ranked = sorted(
            [(s, r.get("sharpe_ratio", 0)) for s, r in results.items()],
            key=lambda x: x[1], reverse=True,
        )
        for rank, (name, sharpe) in enumerate(ranked):
            results[name]["rank"] = rank + 1
            results[name]["rank_by"] = "sharpe_ratio"

        return _convert_numpy(results)

    # ─── Optimization Methods ────────────────────────────────────

    def _max_sharpe(self, mean_ret, cov, n) -> np.ndarray:
        from scipy.optimize import minimize
        def neg_sharpe(w):
            r = np.dot(w, mean_ret)
            v = np.sqrt(np.dot(w, np.dot(cov, w)))
            return -(r - self.rf_rate) / v if v > 0 else 0
        bounds = tuple((0, 1) for _ in range(n))
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        w0 = np.ones(n) / n
        result = minimize(neg_sharpe, w0, bounds=bounds, constraints=constraints, method="SLSQP")
        return result.x if result.success else w0

    def _min_volatility(self, cov, n) -> np.ndarray:
        from scipy.optimize import minimize
        def vol(w):
            return np.sqrt(np.dot(w, np.dot(cov, w)))
        bounds = tuple((0, 1) for _ in range(n))
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        w0 = np.ones(n) / n
        result = minimize(vol, w0, bounds=bounds, constraints=constraints, method="SLSQP")
        return result.x if result.success else w0

    def _efficient_risk(self, mean_ret, cov, n, target_vol) -> np.ndarray:
        from scipy.optimize import minimize
        def neg_return(w):
            return -np.dot(w, mean_ret)
        bounds = tuple((0, 1) for _ in range(n))
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "ineq", "fun": lambda w: target_vol - np.sqrt(np.dot(w, np.dot(cov, w)))},
        ]
        w0 = np.ones(n) / n
        result = minimize(neg_return, w0, bounds=bounds, constraints=constraints, method="SLSQP")
        return result.x if result.success else w0

    def _efficient_return(self, mean_ret, cov, n, target_ret) -> np.ndarray:
        from scipy.optimize import minimize
        def vol(w):
            return np.sqrt(np.dot(w, np.dot(cov, w)))
        bounds = tuple((0, 1) for _ in range(n))
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w: np.dot(w, mean_ret) - target_ret},
        ]
        w0 = np.ones(n) / n
        result = minimize(vol, w0, bounds=bounds, constraints=constraints, method="SLSQP")
        return result.x if result.success else w0

    def _max_quadratic_utility(self, mean_ret, cov, n, risk_aversion) -> np.ndarray:
        from scipy.optimize import minimize
        def neg_utility(w):
            r = np.dot(w, mean_ret)
            var = np.dot(w, np.dot(cov, w))
            return -(r - 0.5 * risk_aversion * var)
        bounds = tuple((0, 1) for _ in range(n))
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        w0 = np.ones(n) / n
        result = minimize(neg_utility, w0, bounds=bounds, constraints=constraints, method="SLSQP")
        return result.x if result.success else w0

    def _risk_parity(self, cov, n) -> np.ndarray:
        from scipy.optimize import minimize
        def rp_obj(w):
            vol = np.sqrt(np.dot(w, np.dot(cov, w)))
            if vol == 0:
                return 0
            marginal = np.dot(cov, w)
            risk_contrib = w * marginal / vol
            target_rc = vol / n
            return np.sum((risk_contrib - target_rc) ** 2)
        bounds = tuple((0, 1) for _ in range(n))
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        w0 = np.ones(n) / n
        result = minimize(rp_obj, w0, bounds=bounds, constraints=constraints, method="SLSQP")
        return result.x if result.success else w0

    def _black_litterman(self, mean_ret, cov, n, views=None, confidence=0.5) -> np.ndarray:
        """Simplified Black-Litterman with investor views."""
        # Market cap weights as prior (equal weight as fallback)
        pi = mean_ret  # Equilibrium returns
        tau = 0.025  # Scaling factor

        if not views:
            return self._max_sharpe(mean_ret, cov, n)

        # Apply views to adjust expected returns
        adj_returns = pi.copy()
        if isinstance(views, dict):
            view_items = list(views.values())
        else:
            view_items = []
        for item in view_items:
            idx, view_ret = item
            if isinstance(idx, int) and 0 <= idx < n:
                adj_returns[idx] = confidence * view_ret + (1 - confidence) * pi[idx]

        return self._max_sharpe(adj_returns, cov, n)

    def _mean_variance(self, mean_ret, cov, n, risk_aversion) -> np.ndarray:
        """Direct mean-variance optimization (single-step)."""
        from scipy.optimize import minimize
        def objective(w):
            ret = np.dot(w, mean_ret)
            var = np.dot(w, np.dot(cov, w))
            return -(ret - 0.5 * risk_aversion * var)
        bounds = tuple((0, 1) for _ in range(n))
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        w0 = np.ones(n) / n
        result = minimize(objective, w0, bounds=bounds, constraints=constraints, method="SLSQP")
        return result.x if result.success else w0

    # ─── Data Fetching ───────────────────────────────────────────

    def _fetch_crypto_returns(self, symbols: List[str]) -> Optional[np.ndarray]:
        """Fetch returns from Binance public API (free, no key needed)."""
        try:
            import requests
            all_returns = []
            for symbol in symbols:
                pair = f"{symbol}USDT"
                resp = requests.get(
                    f"https://api.binance.com/api/v3/klines",
                    params={"symbol": pair, "interval": "1d", "limit": 365},
                    timeout=10,
                )
                if resp.status_code != 200:
                    # Try alternate pairs
                    resp = requests.get(
                        f"https://api.binance.com/api/v3/klines",
                        params={"symbol": pair + "T", "interval": "1d", "limit": 365},
                        timeout=10,
                    )
                    if resp.status_code != 200:
                        continue
                klines = resp.json()
                closes = np.array([float(k[4]) for k in klines])
                if len(closes) < 2:
                    continue
                returns = np.diff(closes) / closes[:-1]
                all_returns.append(returns)

            if not all_returns:
                return None
            # Trim to same length
            min_len = min(len(r) for r in all_returns)
            return np.array([r[-min_len:] for r in all_returns])
        except Exception as e:
            logger.debug(f"Could not fetch crypto returns: {e}")
            return None


# ── CLI / Test ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📊 Crypto Portfolio Optimizer (Fincept-derived)")
    print("=" * 55)

    opt = PortfolioOptimizer()

    # Use synthetic test data (no network needed)
    np.random.seed(42)
    test_returns = np.random.normal(0.001, 0.03, (3, 252))  # 3 assets, 1 year

    results = opt.optimize_all(["BTC", "ETH", "SOL"], returns=test_returns)

    print("\nStrategy Comparison:")
    print(f"{'Strategy':<20} {'Sharpe':>8} {'Return':>10} {'Volatility':>12}")
    print("-" * 55)
    for name, result in sorted(results.items(), key=lambda x: x[1].get("rank", 99)):
        sharpe = result.get("sharpe_ratio", 0)
        ret = result.get("expected_annual_return", 0)
        vol = result.get("expected_annual_volatility", 0)
        rank = result.get("rank", "-")
        print(f"{name:<20} {sharpe:>8.3f} {ret:>10.2%} {vol:>12.2%}  (#{rank})")

    best = min(results.items(), key=lambda x: x[1].get("rank", 99))
    print(f"\n🏆 Best: {best[0]} (Sharpe: {best[1].get('sharpe_ratio', 0):.3f})")
    print(f"   Weights: {best[1].get('weights', {})}")
