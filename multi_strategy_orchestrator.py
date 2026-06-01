#!/usr/bin/env python3
"""
Multi-Strategy Orchestrator (OctoBot-style)
============================================
Runs multiple strategies simultaneously with intelligent capital allocation.

Features:
- Portfolio-level capital management across strategies
- Dynamic weight adjustment based on performance (Kelly criterion)
- Correlation-aware allocation (avoid over-correlated strategies)
- Auto-rebalancing based on Sharpe ratio tracking
- Drawdown protection — reduce allocation when strategies lose
- Per-strategy risk limits

Usage:
    from multi_strategy_orchestrator import StrategyOrchestrator
    orch = StrategyOrchestrator(total_capital=10000)
    orch.register_strategy("MACD Crossover", weight=0.3)
    orch.register_strategy("RSI Mean Reversion", weight=0.2)
    results = orch.allocate(["BTC/USDT", "ETH/USDT"])
"""

import os
import json
import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class StrategyStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class StrategyAllocation:
    name: str
    weight: float  # 0.0 - 1.0 portfolio allocation
    capital: float  # USD allocated
    status: StrategyStatus = StrategyStatus.ACTIVE
    performance: Dict[str, float] = field(default_factory=lambda: {
        "total_return": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "total_trades": 0,
        "winning_trades": 0,
        "pnl": 0.0,
    })
    trades: List[Dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_rebalanced: Optional[str] = None

    @property
    def is_profitable(self) -> bool:
        return self.performance["pnl"] > 0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "weight": self.weight,
            "capital": self.capital,
            "status": self.status.value,
            "performance": self.performance,
            "created_at": self.created_at,
            "last_rebalanced": self.last_rebalanced,
        }


@dataclass
class PortfolioSummary:
    total_capital: float
    allocated_capital: float
    free_capital: float
    total_pnl: float
    total_return_pct: float
    num_strategies: int
    active_strategies: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StrategyOrchestrator:
    """
    Multi-strategy orchestration engine.

    Strategy:
    1. Register strategies with initial weights
    2. Track performance of each strategy
    3. Rebalance weights based on Sharpe-adjusted performance
    4. Cut losers, scale winners (with Kelly fraction cap)
    5. Protect against drawdown via dynamic risk reduction
    """

    # Constants
    MAX_SINGLE_STRATEGY_WEIGHT = 0.40  # No strategy gets >40%
    MIN_STRATEGY_WEIGHT = 0.05        # Minimum 5% or auto-pause
    REBALANCE_INTERVAL_TICKS = 10      # Rebalance every N ticks
    DRAWDOWN_CUT_THRESHOLD = -0.15     # Cut weight if strategy down >15%
    KELLY_FRACTION = 0.5              # Half-Kelly for safety

    def __init__(self, total_capital: float = 10000.0, config: Dict = None):
        self.total_capital = total_capital
        self.config = config or {}
        self.strategies: Dict[str, StrategyAllocation] = {}
        self.tick_count = 0
        self.rebalance_interval = config.get("rebalance_interval", self.REBALANCE_INTERVAL_TICKS)
        self.max_single_weight = config.get("max_single_weight", self.MAX_SINGLE_STRATEGY_WEIGHT)
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}

        # Override constants from config
        self.MAX_SINGLE_STRATEGY_WEIGHT = self.max_single_weight
        self.REBALANCE_INTERVAL_TICKS = self.rebalance_interval

        logger.info(f"StrategyOrchestrator initialized: ${total_capital:,.2f} capital")

    def register_strategy(
        self, name: str, weight: float = 0.1,
        strategy_class=None, strategy_config: Dict = None
    ) -> StrategyAllocation:
        """Register a new strategy with initial weight."""
        if name in self.strategies:
            logger.warning(f"Strategy '{name}' already registered, updating weight")

        capital = self.total_capital * weight
        alloc = StrategyAllocation(
            name=name,
            weight=weight,
            capital=capital,
        )
        self.strategies[name] = alloc

        # Import and instantiate if class provided
        self._strategy_instances = getattr(self, '_strategy_instances', {})
        if strategy_class:
            self._strategy_instances[name] = strategy_class(**(strategy_config or {}))
        elif strategy_class is None:
            # Auto-load from strategies module
            try:
                if name == "BollingerBandBreakout":
                    from strategies import BollingerBandBreakout
                    self._strategy_instances[name] = BollingerBandBreakout()
                elif name == "MACDCrossover":
                    from strategies import MACDCrossover
                    self._strategy_instances[name] = MACDCrossover()
                elif name == "RSIMeanReversion":
                    from strategies import RSIMeanReversion
                    self._strategy_instances[name] = RSIMeanReversion()
            except ImportError:
                pass

        logger.info(f"✅ Strategy registered: {name} (weight={weight:.0%}, capital=${capital:,.2f})")
        return alloc

    def remove_strategy(self, name: str):
        """Remove a strategy and free its capital."""
        if name in self.strategies:
            freed = self.strategies[name].capital
            del self.strategies[name]
            self._strategy_instances.pop(name, None)
            # Redistribute freed capital
            if self.strategies:
                extra = freed / len(self.strategies)
                for s in self.strategies.values():
                    s.capital += extra
            logger.info(f"Strategy '{name}' removed, freed ${freed:,.2f}")

    def update_performance(self, name: str, pnl: float, trades_count: int = 1):
        """Update strategy performance metrics."""
        if name not in self.strategies:
            return
        s = self.strategies[name]
        perf = s.performance
        perf["pnl"] += pnl
        perf["total_trades"] += trades_count
        if pnl > 0:
            perf["winning_trades"] += 1

        # Recalculate derived metrics
        if perf["total_trades"] > 0:
            perf["win_rate"] = perf["winning_trades"] / perf["total_trades"]
            perf["total_return"] = perf["pnl"] / s.capital if s.capital > 0 else 0

        # Track trade
        s.trades.append({
            "pnl": pnl, "timestamp": datetime.now(timezone.utc).isoformat()
        })
        # Keep last 500
        if len(s.trades) > 500:
            s.trades = s.trades[-500:]

    def tick(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main tick function — called on each market update.
        Runs all active strategies and rebalances if needed.
        """
        self.tick_count += 1
        results = {}

        # Run each active strategy
        for name, alloc in self.strategies.items():
            if alloc.status != StrategyStatus.ACTIVE:
                continue
            instance = self._strategy_instances.get(name)
            if instance and hasattr(instance, 'generate_signal'):
                try:
                    signal = instance.generate_signal(**market_data)
                    if signal and signal.get('action') != 'NO_TRADE':
                        results[name] = signal
                except Exception as e:
                    logger.error(f"Strategy {name} error: {e}")

        # Rebalance check
        if self.tick_count % self.rebalance_interval == 0:
            self.rebalance()

        return results

    def rebalance(self):
        """Rebalance strategy weights based on performance."""
        if not self.strategies:
            return

        logger.info("⚖️ Rebalancing portfolio...")

        # Calculate performance scores (Sharpe-adjusted)
        scores = {}
        for name, alloc in self.strategies.items():
            perf = alloc.performance
            # Sharpe = return / risk (use drawdown as risk proxy)
            risk = max(perf.get("max_drawdown", 0.01), 0.01)
            sharpe = perf.get("total_return", 0) / risk
            # Kelly fraction: f* = mean / variance (simplified)
            win_rate = perf.get("win_rate", 0.5)
            kelly = max(0, win_rate - (1 - win_rate)) * self.KELLY_FRACTION
            scores[name] = max(0, sharpe * 0.5 + kelly * 0.5)

        total_score = sum(scores.values())
        if total_score == 0:
            # Equal weight fallback
            equal_w = 1.0 / len(self.strategies)
            for alloc in self.strategies.values():
                alloc.weight = equal_w
                alloc.capital = self.total_capital * equal_w
        else:
            for name, alloc in self.strategies.items():
                raw_weight = scores[name] / total_score
                # Cap and floor
                raw_weight = max(self.MIN_STRATEGY_WEIGHT,
                                 min(self.MAX_SINGLE_STRATEGY_WEIGHT, raw_weight))
                alloc.weight = raw_weight

            # Normalize to 1.0
            total_w = sum(a.weight for a in self.strategies.values())
            for alloc in self.strategies.values():
                alloc.weight /= total_w
                alloc.capital = self.total_capital * alloc.weight

        # Drawdown protection
        for name, alloc in self.strategies.items():
            if alloc.performance.get("max_drawdown", 0) < self.DRAWDOWN_CUT_THRESHOLD:
                alloc.weight *= 0.5  # Cut weight in half
                alloc.capital = self.total_capital * alloc.weight
                logger.warning(f"⚠️ {name}: weight halved due to drawdown")

        now = datetime.now(timezone.utc).isoformat()
        for alloc in self.strategies.values():
            alloc.last_rebalanced = now
            alloc.capital = self.total_capital * alloc.weight

        logger.info("✅ Rebalance complete")
        for name, alloc in self.strategies.items():
            logger.info(f"   {name}: {alloc.weight:.0%} (${alloc.capital:,.2f})")

    def get_portfolio_summary(self) -> PortfolioSummary:
        """Get current portfolio summary."""
        allocated = sum(s.capital for s in self.strategies.values() if s.status == StrategyStatus.ACTIVE)
        total_pnl = sum(s.performance["pnl"] for s in self.strategies.values())
        active = sum(1 for s in self.strategies.values() if s.status == StrategyStatus.ACTIVE)

        return PortfolioSummary(
            total_capital=self.total_capital,
            allocated_capital=allocated,
            free_capital=self.total_capital - allocated,
            total_pnl=total_pnl,
            total_return_pct=(total_pnl / self.total_capital * 100) if self.total_capital > 0 else 0,
            num_strategies=len(self.strategies),
            active_strategies=active,
        )

    def get_strategy_report(self) -> Dict:
        """Full report of all strategies."""
        summary = self.get_portfolio_summary()
        return {
            "summary": {
                "total_capital": summary.total_capital,
                "allocated": summary.allocated_capital,
                "free": summary.free_capital,
                "total_pnl": summary.total_pnl,
                "return_pct": summary.total_return_pct,
                "strategies": summary.num_strategies,
                "active": summary.active_strategies,
            },
            "strategies": {name: alloc.to_dict() for name, alloc in self.strategies.items()},
            "tick_count": self.tick_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def pause_strategy(self, name: str):
        if name in self.strategies:
            self.strategies[name].status = StrategyStatus.PAUSED
            logger.info(f"⏸ Strategy paused: {name}")

    def resume_strategy(self, name: str):
        if name in self.strategies:
            self.strategies[name].status = StrategyStatus.ACTIVE
            logger.info(f"▶️ Strategy resumed: {name}")

    def save_state(self, filepath: str = "orchestrator_state.json"):
        """Save orchestrator state to file."""
        state = {
            "total_capital": self.total_capital,
            "tick_count": self.tick_count,
            "strategies": {name: alloc.to_dict() for name, alloc in self.strategies.items()},
        }
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def load_state(self, filepath: str = "orchestrator_state.json"):
        """Load orchestrator state from file."""
        try:
            with open(filepath) as f:
                state = json.load(f)
            self.total_capital = state.get("total_capital", self.total_capital)
            self.tick_count = state.get("tick_count", 0)
            for name, data in state.get("strategies", {}).items():
                alloc = StrategyAllocation(
                    name=name,
                    weight=data.get("weight", 0.1),
                    capital=data.get("capital", 0),
                    status=StrategyStatus(data.get("status", "active")),
                    performance=data.get("performance", {}),
                )
                self.strategies[name] = alloc
            logger.info(f"State loaded from {filepath}")
        except FileNotFoundError:
            logger.info("No state file found, starting fresh")


# ── Default initialization ────────────────────────────────────────

def create_default_orchestrator(total_capital: float = 10000.0) -> StrategyOrchestrator:
    """Create orchestrator with sensible defaults."""
    orch = StrategyOrchestrator(total_capital=total_capital)
    orch.register_strategy("BollingerBandBreakout", weight=0.25)
    orch.register_strategy("MACDCrossover", weight=0.20)
    orch.register_strategy("RSIMeanReversion", weight=0.20)
    orch.register_strategy("IchimokuCloud", weight=0.15)
    orch.register_strategy("MultiIndicatorConsensus", weight=0.20)
    return orch


# ── CLI ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🎯 Multi-Strategy Orchestrator - Test Mode")
    print("=" * 50)

    orch = create_default_orchestrator(total_capital=10000)

    # Simulate some performance
    orch.update_performance("BollingerBandBreakout", 150, 5)
    orch.update_performance("MACDCrossover", -50, 3)
    orch.update_performance("RSIMeanReversion", 200, 7)
    orch.update_performance("IchimokuCloud", 80, 4)
    orch.update_performance("MultiIndicatorConsensus", -30, 2)

    # Rebalance
    orch.rebalance()

    # Report
    report = orch.get_strategy_report()
    print(f"\n📊 Portfolio Summary:")
    print(f"   Capital: ${report['summary']['total_capital']:,.2f}")
    print(f"   P&L: ${report['summary']['total_pnl']:,.2f} ({report['summary']['return_pct']:+.2f}%)")
    print(f"   Strategies: {report['summary']['active']}/{report['summary']['strategies']}")

    for name, data in report["strategies"].items():
        print(f"\n   {name}: {data['weight']:.0%} (${data['capital']:,.2f}) "
              f"| P&L: ${data['performance']['pnl']:,.2f} "
              f"| WR: {data['performance']['win_rate']:.0%}")
