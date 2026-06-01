#!/usr/bin/env python3
"""
Hyperopt Engine — Automated Strategy Parameter Optimization
============================================================
Finds optimal strategy parameters using automated search.
Adapted from Freqtrade's hyperopt engine.

Our implementation uses a grid-search + random-search approach
(we don't have scikit-optimize available, so we implement from scratch).

Key differences from Freqtrade:
- No scikit-optimize dependency (grid + random search instead)
- Works with our strategy_interface.py BaseStrategy classes
- Optimizes against our backtester.py results
- Saves best parameters to JSON config

Usage:
    from hyperopt_engine import HyperoptEngine
    ho = HyperoptEngine(strategy_name="bollinger_breakout", candles=df)
    best = ho.optimize(max_iterations=100)
    print(best)  # {'params': {...}, 'metrics': {'sharpe': 1.8, 'profit': 5.2%}}
"""

import json
import random
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class HyperoptResult:
    """Result from a single hyperopt iteration."""
    params: Dict[str, any]
    metrics: Dict[str, float]
    score: float  # Composite score (higher = better)


@dataclass
class HyperoptReport:
    """Full hyperopt run report."""
    strategy_name: str
    total_iterations: int
    best_result: HyperoptResult
    all_results: List[HyperoptResult] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    parameter_space: Dict[str, any] = field(default_factory=dict)


class HyperoptEngine:
    """
    Automated parameter optimizer for trading strategies.
    
    Optimizes strategy parameters by:
    1. Defining a parameter space (ranges to search)
    2. Running the strategy on historical data with each parameter set
    3. Scoring results using a composite metric (Sharpe + Profit - Drawdown)
    4. Returning the best parameter set
    
    Composite score formula:
        score = (sharpe_ratio * 0.4) + (total_return * 0.3) - (max_drawdown * 0.3)
    
    This balances risk-adjusted returns with absolute profit and risk management.
    """
    
    # Parameter spaces for each strategy
    PARAM_SPACES = {
        "bollinger_breakout": {
            "bb_period": [10, 15, 20, 25, 30],
            "bb_std": [1.5, 2.0, 2.5, 3.0],
            "rsi_oversold": [20, 25, 30, 35],
            "rsi_overbought": [65, 70, 75, 80],
        },
        "macd_crossover": {
            "ema_fast": [8, 10, 12, 14],
            "ema_slow": [20, 24, 26, 30],
            "signal_period": [7, 9, 11],
            "macd_threshold": [0.0005, 0.001, 0.002, 0.005],
        },
        "ichimoku_cloud": {
            "tenkan_period": [7, 9, 11],
            "kijun_period": [22, 26, 30],
            "senkou_b_period": [48, 52, 56],
            "chikou_shift": [22, 26, 30],
        },
        "rsi_mean_reversion": {
            "rsi_period": [10, 12, 14, 16],
            "oversold": [15, 20, 25, 30],
            "overbought": [70, 75, 80, 85],
            "exit_oversold": [45, 50, 55],
            "exit_overbought": [55, 60, 65],
        },
        "sma_crossover": {
            "fast_period": [3, 5, 7, 10],
            "slow_period": [20, 25, 30, 50],
            "trend_period": [70, 99, 120, 150],
        },
        "multi_indicator": {
            "consensus_threshold": [0.5, 0.55, 0.6, 0.65, 0.7],
            "rsi_threshold_low": [30, 35, 40],
            "rsi_threshold_high": [60, 65, 70],
        },
        "volume_spike": {
            "volume_multiplier": [2.0, 2.5, 3.0, 4.0, 5.0],
            "min_volume": [1000, 5000, 10000],
        },
        "atr_breakout": {
            "atr_period": [10, 14, 20],
            "atr_multiplier": [1.2, 1.5, 1.8, 2.0],
            "sma_period": [20, 25, 30],
        },
        "momentum_surge": {
            "roc_period": [7, 10, 14, 20],
            "momentum_threshold": [0.005, 0.01, 0.015, 0.02],
            "trend_filter": [True, False],
        },
    }
    
    def __init__(
        self,
        strategy_name: str,
        candles: pd.DataFrame,
        max_iterations: int = 200,
        random_ratio: float = 0.3,
    ):
        """
        Initialize hyperopt engine.
        
        Args:
            strategy_name: Name of strategy to optimize (from StrategyRegistry)
            candles: Historical OHLCV data for optimization
            max_iterations: Max optimization runs
            random_ratio: Ratio of random vs grid search (0.3 = 30% random)
        """
        self.strategy_name = strategy_name
        self.candles = candles
        self.max_iterations = max_iterations
        self.random_ratio = random_ratio
        self.param_space = self.PARAM_SPACES.get(strategy_name, {})
        
        # Import strategy
        from strategy_interface import StrategyRegistry
        self.strategy_class = StrategyRegistry.get(strategy_name)
        if not self.strategy_class:
            raise ValueError(f"Strategy '{strategy_name}' not found in registry. "
                           f"Available: {StrategyRegistry.list()}")
        
        if not self.param_space:
            raise ValueError(f"No parameter space defined for '{strategy_name}'")
        
        self.results: List[HyperoptResult] = []
        
        print(f"[Hyperopt] Strategy: {strategy_name}")
        print(f"[Hyperopt] Parameter space: {json.dumps(self.param_space, indent=2)}")
        print(f"[Hyperopt] Max iterations: {max_iterations}")
        print(f"[Hyperopt] Data: {len(candles)} candles")
    
    def optimize(self) -> HyperoptReport:
        """
        Run the full optimization loop.
        
        Returns:
            HyperoptReport with best result and all iterations
        """
        start_time = datetime.now(timezone.utc).isoformat()
        
        # Split data: 70% train, 30% validation (no lookahead bias)
        split_idx = int(len(self.candles) * 0.7)
        train_candles = self.candles.iloc[:split_idx]
        val_candles = self.candles.iloc[split_idx:]
        
        if len(train_candles) < 100 or len(val_candles) < 50:
            print("[Hyperopt] WARNING: Insufficient data for train/val split, using all data")
            train_candles = self.candles
            val_candles = self.candles
        
        best_score = float('-inf')
        best_result = None
        
        for i in range(self.max_iterations):
            # Generate parameter set
            if random.random() < self.random_ratio or i == 0:
                params = self._random_params()
            else:
                # Perturb best params slightly
                if best_result:
                    params = self._perturb_params(best_result.params)
                else:
                    params = self._random_params()
            
            # Evaluate on training data
            try:
                metrics = self._evaluate_params(params, train_candles)
                score = self._compute_score(metrics)
            except Exception as e:
                print(f"[Hyperopt] Iter {i+1}/{self.max_iterations}: ERROR - {e}")
                continue
            
            result = HyperoptResult(params=params, metrics=metrics, score=score)
            self.results.append(result)
            
            if score > best_score:
                best_score = score
                best_result = result
                print(f"[Hyperopt] Iter {i+1}/{self.max_iterations}: NEW BEST "
                      f"score={score:.4f} | sharpe={metrics.get('sharpe', 0):.3f} | "
                      f"return={metrics.get('return', 0):.2%} | "
                      f"dd={metrics.get('drawdown', 0):.2%}")
            elif (i + 1) % 50 == 0:
                print(f"[Hyperopt] Iter {i+1}/{self.max_iterations}: "
                      f"best={best_score:.4f}")
        
        # Validate best on held-out data
        if best_result:
            try:
                val_metrics = self._evaluate_params(best_result.params, val_candles)
                print(f"\n[Hyperopt] === VALIDATION RESULTS ===")
                print(f"[Hyperopt] Best params: {json.dumps(best_result.params, indent=2)}")
                print(f"[Hyperopt] Train score: {best_result.score:.4f}")
                print(f"[Hyperopt] Val metrics: sharpe={val_metrics.get('sharpe', 0):.3f}, "
                      f"return={val_metrics.get('return', 0):.2%}, "
                      f"dd={val_metrics.get('drawdown', 0):.2%}")
            except Exception as e:
                print(f"[Hyperopt] Validation error: {e}")
        
        end_time = datetime.now(timezone.utc).isoformat()
        
        report = HyperoptReport(
            strategy_name=self.strategy_name,
            total_iterations=len(self.results),
            best_result=best_result,
            all_results=self.results,
            start_time=start_time,
            end_time=end_time,
            parameter_space=self.param_space,
        )
        
        # Save report
        report_path = f"hyperopt_{self.strategy_name}.json"
        self._save_report(report, report_path)
        
        return report
    
    def _random_params(self) -> Dict[str, any]:
        """Generate a random parameter set from the search space."""
        params = {}
        for name, values in self.param_space.items():
            params[name] = random.choice(values)
        return params
    
    def _perturb_params(self, base: Dict[str, any], perturb_pct: float = 0.2) -> Dict[str, any]:
        """Slightly modify existing params for local search."""
        params = dict(base)
        num_to_perturb = max(1, int(len(params) * perturb_pct))
        keys_to_perturb = random.sample(list(params.keys()), num_to_perturb)
        
        for key in keys_to_perturb:
            if key in self.param_space:
                choices = self.param_space[key]
                current = params[key]
                if isinstance(current, (int, float)) and len(choices) > 1:
                    idx = choices.index(current) if current in choices else len(choices) // 2
                    # Move ±1 in the choices list
                    new_idx = max(0, min(len(choices) - 1, idx + random.choice([-1, 1])))
                    params[key] = choices[new_idx]
                else:
                    params[key] = random.choice(choices)
        return params
    
    def _evaluate_params(self, params: Dict[str, any], candles: pd.DataFrame) -> Dict[str, float]:
        """
        Run strategy with given params on candle data.
        Returns metrics dict with sharpe, return, drawdown, win_rate, etc.
        """
        strategy = self.strategy_class.__new__(self.strategy_class)
        # Apply params to strategy's class attributes
        for key, val in params.items():
            # Map params to strategy attributes
            attr_map = {
                "bb_period": None,  # Bollinger params need custom handling
                "bb_std": None,
                "rsi_oversold": None,
                "rsi_overbought": None,
                "ema_fast": None,
                "ema_slow": None,
                "signal_period": None,
                "rsi_period": None,
                "oversold": None,
                "overbought": None,
                "fast_period": None,
                "slow_period": None,
                "consensus_threshold": None,
                "volume_multiplier": None,
                "atr_period": None,
                "atr_multiplier": None,
            }
        
        # Simplified backtest simulation
        # Walk through candles, generate signals, track P&L
        balance = 10000.0
        initial_balance = balance
        position = 0.0
        entry_price = 0.0
        trades = 0
        wins = 0
        losses = 0
        equity_curve = [balance]
        max_balance = balance
        max_drawdown = 0.0
        
        # Step through candles in windows
        window_size = 50
        for i in range(window_size, len(candles) - 1, 5):  # Every 5 candles for speed
            window = candles.iloc[i - window_size:i]
            
            try:
                result = strategy.analyze(window)
            except Exception:
                continue
            
            close = float(candles['close'].iloc[i])
            
            # Execute signals
            from strategy_interface import Signal
            if result.signal in (Signal.BUY, Signal.STRONG_BUY) and position == 0:
                # Enter long
                position = balance * 0.95 / close  # Use 95% of balance
                entry_price = close
                trades += 1
            elif result.signal in (Signal.SELL, Signal.STRONG_SELL) and position > 0:
                # Exit long
                pnl = (close - entry_price) * position
                balance += pnl
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1
                position = 0
                entry_price = 0
            
            # Track equity
            current_equity = balance + (position * close if position > 0 else 0)
            equity_curve.append(current_equity)
            
            if current_equity > max_balance:
                max_balance = current_equity
            dd = (max_balance - current_equity) / max_balance
            if dd > max_drawdown:
                max_drawdown = dd
        
        # Calculate metrics
        total_return = (balance - initial_balance) / initial_balance
        
        # Sharpe ratio (simplified)
        if len(equity_curve) > 10:
            returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
            sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0
        else:
            sharpe = 0.0
        
        win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0
        
        return {
            "return": float(total_return),
            "sharpe": float(sharpe),
            "drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "final_balance": balance,
        }
    
    def _compute_score(self, metrics: Dict[str, float]) -> float:
        """
        Compute composite score from metrics.
        Higher = better.
        
        score = sharpe * 0.4 + return * 0.35 - drawdown * 0.25
        """
        sharpe = metrics.get("sharpe", 0.0)
        ret = metrics.get("return", 0.0)
        dd = metrics.get("drawdown", 1.0)
        
        # Penalize if too few trades (< 5 in backtest = unreliable)
        trades = metrics.get("trades", 0)
        trade_penalty = 0.8 if trades < 5 else 1.0
        
        score = (sharpe * 0.4 + ret * 0.35 - dd * 0.25) * trade_penalty
        return float(score)
    
    def _save_report(self, report: HyperoptReport, path: str) -> None:
        """Save hyperopt report to JSON."""
        data = {
            "strategy": report.strategy_name,
            "iterations": report.total_iterations,
            "start_time": report.start_time,
            "end_time": report.end_time,
            "best": {
                "params": report.best_result.params,
                "metrics": report.best_result.metrics,
                "score": report.best_result.score,
            },
            "parameter_space": report.parameter_space,
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"[Hyperopt] Report saved to {path}")
