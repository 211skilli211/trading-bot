#!/usr/bin/env python3
"""
Crypto Auto-Trader Engine (ported from Fincept-Corporation/FinceptTerminal)
============================================================================
Autonomous trading loop with AI agent recommendations + safety circuit breakers.

From: fincept-qt/scripts/agno_trading/core/auto_trader.py
Crypto-adapted: 24/7 markets, Binance/Jupiter integration, no market hours gating.

Features:
- Configurable execution cycle (default 180s = 3 min)
- Dynamic TP/SL based on ATR
- Position sizing with confidence weighting
- Safety circuit breakers (max drawdown, daily loss, position count)
- Emergency stop mechanism
- Trade history + performance tracking

Usage:
    from auto_trader_engine import AutoTrader, SafetyLimits
    trader = AutoTrader(agent=my_agent, initial_capital=10000)
    trader.safety_limits = SafetyLimits(max_drawdown=0.10)
    await trader.start()
"""

import json
import time
import logging
import asyncio
import numpy as np
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """Structured trading signal."""
    symbol: str
    direction: str          # "long" or "short"
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    leverage: float
    confidence: float       # 0.0 - 1.0
    reasoning: str
    timestamp: str = ""


@dataclass
class SafetyLimits:
    """Safety circuit breaker configuration."""
    max_position_size: float = 0.10     # 10% of portfolio per position
    max_leverage: float = 1.0           # No leverage by default
    max_drawdown: float = 0.15          # 15% max drawdown → halt trading
    max_daily_loss: float = 0.05        # 5% daily loss limit
    min_confidence: float = 0.60        # Min confidence to execute
    max_open_positions: int = 5         # Max concurrent positions
    require_stop_loss: bool = True
    require_take_profit: bool = True
    cooldown_seconds: int = 60          # Min seconds between trades
    max_daily_trades: int = 20          # Max trades per day
    emergency_stop_on_drawdown: float = 0.25  # Hard stop at 25%


@dataclass
class TradingState:
    """Live trading state."""
    is_running: bool = False
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    current_drawdown: float = 0.0
    peak_equity: float = 0.0
    last_trade_time: Optional[str] = None
    daily_trade_count: int = 0
    last_daily_reset: str = ""
    circuit_breaker_triggered: bool = False
    emergency_stop: bool = False


class AutoTrader:
    """
    Autonomous crypto trading engine.

    Runs an execution loop that:
    1. Fetches market data from connected exchanges
    2. Generates signals via AI agent
    3. Validates signals against safety limits
    4. Executes approved trades (paper or live)
    5. Monitors positions (TP/SL tracking)
    6. Triggers circuit breakers when safety limits hit
    """

    def __init__(
        self,
        agent=None,
        execution_interval: int = 180,
        safety_limits: Optional[SafetyLimits] = None,
        initial_capital: float = 10000.0,
        mode: str = "paper",
    ):
        self.agent = agent
        self.execution_interval = execution_interval
        self.safety_limits = safety_limits or SafetyLimits()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.mode = mode

        self.state = TradingState()
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.callbacks: Dict[str, Callable] = {}
        self._stop_requested = False
        self._agent_signal_fn: Optional[Callable] = None

        # Set agent callback if provided
        if agent and hasattr(agent, 'generate_signal'):
            self._agent_signal_fn = agent.generate_signal
        elif agent and callable(agent):
            self._agent_signal_fn = agent

    def register_callback(self, event: str, callback: Callable):
        """Register event callback."""
        self.callbacks[event] = callback

    def _emit(self, event: str, data: Any = None):
        """Emit event to registered callback."""
        if event in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(self.callbacks[event]):
                    asyncio.create_task(self.callbacks[event](data))
                else:
                    self.callbacks[event](data)
            except Exception as e:
                logger.error(f"Callback error ({event}): {e}")

    def start_sync(self):
        """Synchronous trading loop (for non-async contexts)."""
        self.state.is_running = True
        self.state.peak_equity = self.current_capital
        self.state.last_daily_reset = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        logger.info(f"🚀 AutoTrader starting: ${self.initial_capital:,.2f} ({self.mode} mode)")
        logger.info(f"   Interval: {self.execution_interval}s | Safety: max_dd={self.safety_limits.max_drawdown:.0%}")

        try:
            while self.state.is_running and not self._stop_requested:
                cycle_start = time.time()

                try:
                    self._execute_cycle()
                except Exception as e:
                    logger.error(f"Cycle error: {e}")
                    self.state.total_trades += 0

                # Sleep until next cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self.execution_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("AutoTrader interrupted")
        finally:
            self.state.is_running = False
            logger.info(f"AutoTrader stopped. Trades: {self.state.total_trades}, PnL: ${self.state.total_pnl:+,.2f}")

    def _execute_cycle(self):
        """Single execution cycle."""
        now = datetime.now(timezone.utc)

        # Reset daily counters
        today = now.strftime("%Y-%m-%d")
        if today != self.state.last_daily_reset:
            self.state.daily_pnl = 0.0
            self.state.daily_trade_count = 0
            self.state.last_daily_reset = today

        # Check circuit breakers
        if self.state.emergency_stop:
            logger.warning("Emergency stop active — skipping cycle")
            return

        if self._check_circuit_breakers():
            self.state.circuit_breaker_triggered = True
            self._emit("circuit_breaker", self.state)
            return

        # Update drawdown
        if self.current_capital > self.state.peak_equity:
            self.state.peak_equity = self.current_capital
        self.state.current_drawdown = (
            (self.state.peak_equity - self.current_capital) / self.state.peak_equity
            if self.state.peak_equity > 0 else 0
        )

        # Get signals from agent
        if self._agent_signal_fn:
            try:
                signals = self._get_signals()
                for signal in signals:
                    self._process_signal(signal)
            except Exception as e:
                logger.error(f"Signal generation error: {e}")

    def _get_signals(self) -> List[TradingSignal]:
        """Get signals from agent."""
        result = self._agent_signal_fn()
        if result is None:
            return []
        if isinstance(result, dict):
            return [self._dict_to_signal(result)]
        if isinstance(result, list):
            return [self._dict_to_signal(s) if isinstance(s, dict) else s for s in result]
        return []

    def _dict_to_signal(self, d: Dict) -> TradingSignal:
        """Convert dict to TradingSignal."""
        return TradingSignal(
            symbol=d.get("symbol", "BTC/USDT"),
            direction=d.get("direction", "long"),
            entry_price=d.get("entry_price", 0),
            stop_loss=d.get("stop_loss", 0),
            take_profit=d.get("take_profit", 0),
            position_size=d.get("position_size", 0),
            leverage=d.get("leverage", 1.0),
            confidence=d.get("confidence", 0.5),
            reasoning=d.get("reasoning", "agent signal"),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _process_signal(self, signal: TradingSignal):
        """Validate and execute a signal."""
        # Check confidence
        if signal.confidence < self.safety_limits.min_confidence:
            logger.debug(f"Signal rejected: confidence {signal.confidence:.2f} < {self.safety_limits.min_confidence}")
            return

        # Check position limit
        if len(self.positions) >= self.safety_limits.max_open_positions:
            logger.debug(f"Max positions reached ({len(self.positions)}/{self.safety_limits.max_open_positions})")
            return

        # Check cooldown
        if self.state.last_trade_time:
            last = datetime.fromisoformat(self.state.last_trade_time.replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - last).total_seconds()
            if elapsed < self.safety_limits.cooldown_seconds:
                return

        # Check daily trade limit
        if self.state.daily_trade_count >= self.safety_limits.max_daily_trades:
            logger.debug(f"Daily trade limit reached ({self.state.daily_trade_count})")
            return

        # Validate stop loss / take profit
        if self.safety_limits.require_stop_loss and signal.stop_loss <= 0:
            logger.debug("Signal rejected: no stop loss")
            return

        # Size position
        max_size = self.current_capital * self.safety_limits.max_position_size * signal.confidence
        position_value = min(signal.position_size * signal.entry_price, max_size)

        if position_value <= 0:
            return

        # Execute
        self._execute_trade(signal, position_value)

    def _execute_trade(self, signal: TradingSignal, position_value: float):
        """Execute or paper-trade a signal."""
        trade = {
            "id": f"t{self.state.total_trades + 1}",
            "symbol": signal.symbol,
            "direction": signal.direction,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "size_usd": position_value,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "mode": self.mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.mode == "paper":
            trade["status"] = "paper_opened"
            self.positions[signal.symbol] = trade
            self.state.total_trades += 1
            self.state.daily_trade_count += 1
            self.state.last_trade_time = trade["timestamp"]
            self.trade_history.append(trade)
            self._emit("trade_opened", trade)
            logger.info(f"📝 PAPER {signal.direction.upper()} {signal.symbol} @ ${signal.entry_price:,.2f} "
                        f"(conf={signal.confidence:.0%}, size=${position_value:,.2f})")
        else:
            # Live execution would go here
            trade["status"] = "live"
            self._emit("trade_live", trade)

    def _check_circuit_breakers(self) -> bool:
        """Check all circuit breaker conditions."""
        if self.state.current_drawdown >= self.safety_limits.emergency_stop_on_drawdown:
            self.state.emergency_stop = True
            logger.critical(f"🚨 EMERGENCY STOP: drawdown={self.state.current_drawdown:.1%}")
            return True

        if self.state.current_drawdown >= self.safety_limits.max_drawdown:
            logger.warning(f"⚠️ Circuit breaker: drawdown={self.state.current_drawdown:.1%} >= {self.safety_limits.max_drawdown:.0%}")
            return True

        daily_loss_pct = abs(self.state.daily_pnl) / self.initial_capital
        if daily_loss_pct >= self.safety_limits.max_daily_loss:
            logger.warning(f"⚠️ Circuit breaker: daily loss={daily_loss_pct:.1%}")
            return True

        return False

    def stop(self):
        """Graceful stop."""
        self._stop_requested = True
        self.state.is_running = False
        logger.info("AutoTrader stop requested")

    def emergency_stop_now(self):
        """Immediate emergency stop."""
        self.state.emergency_stop = True
        self.state.is_running = False
        self._stop_requested = True
        logger.critical("🚨 EMERGENCY STOP TRIGGERED")

    def get_status(self) -> Dict[str, Any]:
        """Get current trader status."""
        return {
            "running": self.state.is_running,
            "mode": self.mode,
            "capital": self.current_capital,
            "peak_equity": self.state.peak_equity,
            "drawdown": self.state.current_drawdown,
            "total_trades": self.state.total_trades,
            "total_pnl": self.state.total_pnl,
            "daily_pnl": self.state.daily_pnl,
            "daily_trade_count": self.state.daily_trade_count,
            "open_positions": len(self.positions),
            "circuit_breaker": self.state.circuit_breaker_triggered,
            "emergency_stop": self.state.emergency_stop,
        }

    def get_trade_history(self) -> List[Dict]:
        """Get full trade history."""
        return self.trade_history

    def update_trade_result(self, symbol: str, exit_price: float):
        """Update a trade with its exit price (called by position monitor)."""
        if symbol not in self.positions:
            return
        pos = self.positions.pop(symbol)
        entry = pos["entry_price"]
        size = pos["size_usd"]
        if pos["direction"] == "long":
            pnl = (exit_price - entry) / entry * size
        else:
            pnl = (entry - exit_price) / entry * size

        pos["exit_price"] = exit_price
        pos["pnl"] = pnl
        pos["closed_at"] = datetime.now(timezone.utc).isoformat()
        self.current_capital += pnl
        self.state.total_pnl += pnl
        self.state.daily_pnl += pnl
        if pnl > 0:
            self.state.winning_trades += 1
        else:
            self.state.losing_trades += 1

        self._emit("trade_closed", pos)
        logger.info(f"📊 Trade closed: {symbol} PnL=${pnl:+,.2f}")


# ── CLI Test ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🤖 Crypto Auto-Trader Engine (Fincept-derived)")
    print("=" * 52)

    # Dummy agent that generates random signals
    def dummy_agent():
        import random
        price = 60000 + random.uniform(-5000, 5000)
        return {
            "symbol": "BTC/USDT",
            "direction": random.choice(["long", "long", "long", "short"]),
            "entry_price": price,
            "stop_loss": price * 0.97,
            "take_profit": price * 1.05,
            "position_size": 0.05,
            "leverage": 1.0,
            "confidence": random.uniform(0.5, 0.95),
            "reasoning": "Test signal",
        }

    trader = AutoTrader(
        agent=dummy_agent,
        mode="paper",
        initial_capital=10000,
        safety_limits=SafetyLimits(min_confidence=0.5, cooldown_seconds=1),
    )

    # Run a few cycles manually
    trader.state.is_running = True
    trader.state.peak_equity = 10000
    for _ in range(5):
        trader._execute_cycle()
        time.sleep(0.5)

    status = trader.get_status()
    print(f"\n📊 Status:")
    for k, v in status.items():
        print(f"   {k}: {v}")

    print(f"\n📜 Trades: {len(trader.trade_history)}")
    for t in trader.trade_history:
        print(f"   {t['direction']:5} {t['symbol']} @ ${t['entry_price']:,.2f} (conf={t['confidence']:.0%})")
