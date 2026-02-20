#!/usr/bin/env python3
"""
Execution Layer - Order Placement & Trade Execution
Turns approved signals into actual trades (paper or live).
Part of the modular trading bot blueprint.

Core Responsibilities:
- Order Placement: Connect to exchange APIs
- Retry Logic: Handle failed orders gracefully
- Latency Tracking: Measure signal → execution time
- Mode Toggle: Paper trading (default) vs Live trading
"""

import requests
import time
import json
import hashlib
import hmac
import base64
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import random  # For simulating latency in paper mode

# Import security and retry utilities
try:
    from security_utils import sanitize_for_log, SecureLogger, generate_idempotency_key
    from retry_utils import with_retry, CircuitBreaker, RETRY_NETWORK
    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False
    print("[ExecutionLayer] Warning: security_utils/retry_utils not available")

# Setup logger
logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution mode types."""
    PAPER = "PAPER"
    LIVE = "LIVE"


class OrderStatus(Enum):
    """Order status types."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL_FILL"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TradeExecution:
    """Complete trade execution record."""
    trade_id: str
    timestamp: str
    mode: str
    status: str
    
    # Strategy info
    strategy_decision: str
    spread_pct: float
    
    # Risk info
    risk_decision: str
    position_size_btc: float
    allocation_usd: float
    stop_loss_price: Optional[float]
    
    # Execution details
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    quantity: float
    
    # Latency tracking
    signal_latency_ms: float
    risk_latency_ms: float
    execution_latency_ms: float
    total_latency_ms: float
    
    # Results
    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    actual_buy_price: Optional[float] = None
    actual_sell_price: Optional[float] = None
    fees_paid: Optional[float] = None
    net_pnl: Optional[float] = None
    error_message: Optional[str] = None


class ExecutionLayer:
    """
    Execution Layer for trading bot.
    
    Handles order placement to exchanges with:
    - Paper trading mode (default, safe)
    - Live trading mode (requires API keys)
    - Retry logic with exponential backoff
    - Comprehensive latency tracking
    """
    
    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.PAPER,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        binance_api_key: Optional[str] = None,
        binance_secret: Optional[str] = None,
        coinbase_api_key: Optional[str] = None,
        coinbase_secret: Optional[str] = None
    ):
        """
        Initialize Execution Layer.
        
        Args:
            mode: PAPER or LIVE execution mode
            max_retries: Maximum retry attempts for failed orders
            retry_delay: Base delay between retries (seconds)
            binance_api_key: Binance API key (required for LIVE)
            binance_secret: Binance API secret (required for LIVE)
            coinbase_api_key: Coinbase API key (required for LIVE)
            coinbase_secret: Coinbase API secret (required for LIVE)
        """
        self.mode = mode
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # API credentials (only used in LIVE mode)
        self.binance_api_key = binance_api_key
        self.binance_secret = binance_secret
        self.coinbase_api_key = coinbase_api_key
        self.coinbase_secret = coinbase_secret
        
        # Trade tracking
        self.trade_counter = 0
        self.executions: List[TradeExecution] = []
        
        # Statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.avg_latency_ms = 0.0
        
        # Initialize secure logger
        if UTILS_AVAILABLE:
            self.secure_logger = SecureLogger(logger)
        else:
            self.secure_logger = None
        
        # Circuit breaker for live trading
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0
        ) if mode == ExecutionMode.LIVE else None
        
        # Track executed orders for idempotency
        self.executed_orders = set()
        
        self._log_init_info()
    
    def _log_init_info(self):
        """Log initialization info securely."""
        log_msg = f"[ExecutionLayer] Initialized\n"
        log_msg += f"  Mode: {self.mode.value}\n"
        log_msg += f"  Max Retries: {self.max_retries}"
        
        if self.mode == ExecutionMode.LIVE:
            # Sanitize credentials in logs
            binance_ok = bool(self.binance_api_key and self.binance_secret)
            coinbase_ok = bool(self.coinbase_api_key and self.coinbase_secret)
            
            if not binance_ok:
                log_msg += "\n  ⚠️  WARNING: Binance credentials not provided"
            else:
                masked = sanitize_for_log(self.binance_api_key) if UTILS_AVAILABLE else "****"
                log_msg += f"\n  ✅ Binance API key: {masked}"
            
            if not coinbase_ok:
                log_msg += "\n  ⚠️  WARNING: Coinbase credentials not provided"
            
            log_msg += "\n  🔴 LIVE TRADING ENABLED - Real orders will be placed!"
        else:
            log_msg += "\n  📊 PAPER TRADING MODE - No real orders will be placed"
        
        print(log_msg)
        if self.secure_logger:
            self.secure_logger.info(log_msg)
    
    def _validate_inputs(self, strategy_signal: Dict, risk_result: Dict) -> Optional[str]:
        """Validate inputs before execution. Returns error message or None."""
        # Validate strategy signal
        if not isinstance(strategy_signal, dict):
            return "strategy_signal must be a dict"
        
        decision = strategy_signal.get("decision")
        if decision not in ["TRADE", "NO_TRADE", "HOLD"]:
            return f"Invalid decision: {decision}"
        
        if decision == "TRADE":
            buy_price = strategy_signal.get("buy_price")
            sell_price = strategy_signal.get("sell_price")
            
            if buy_price is not None and (not isinstance(buy_price, (int, float)) or buy_price <= 0):
                return f"Invalid buy_price: {buy_price}"
            if sell_price is not None and (not isinstance(sell_price, (int, float)) or sell_price <= 0):
                return f"Invalid sell_price: {sell_price}"
        
        # Validate risk result
        if not isinstance(risk_result, dict):
            return "risk_result must be a dict"
        
        risk_decision = risk_result.get("decision")
        if risk_decision not in ["APPROVE", "REJECT", "MODIFY", "HOLD"]:
            return f"Invalid risk decision: {risk_decision}"
        
        return None
    
    def _check_live_ready(self) -> bool:
        """Check if live trading is properly configured."""
        if self.mode != ExecutionMode.LIVE:
            return True
        
        # Need at least one exchange configured
        has_binance = bool(self.binance_api_key and self.binance_secret)
        has_coinbase = bool(self.coinbase_api_key and self.coinbase_secret)
        
        return has_binance or has_coinbase
    
    def execute_trade(
        self,
        strategy_signal: Dict[str, Any],
        risk_result: Dict[str, Any],
        signal_timestamp: float
    ) -> TradeExecution:
        """
        Execute a trade based on strategy and risk approval.
        
        Args:
            strategy_signal: Output from StrategyEngine
            risk_result: Output from RiskManager
            signal_timestamp: Timestamp when signal was generated
        
        Returns:
            TradeExecution record
        """
        # Generate unique trade ID with idempotency key
        if UTILS_AVAILABLE:
            trade_id = generate_idempotency_key("TRADE")
        else:
            self.trade_counter += 1
            trade_id = f"TRADE_{self.trade_counter:04d}_{uuid.uuid4().hex[:8]}"
        
        # Check for duplicate (idempotency)
        if trade_id in self.executed_orders:
            error_msg = f"Trade {trade_id} already executed (idempotency check)"
            print(f"⚠️  {error_msg}")
            return TradeExecution(
                trade_id=trade_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode=self.mode.value,
                status=OrderStatus.REJECTED.value,
                strategy_decision=strategy_signal.get("decision", "UNKNOWN"),
                spread_pct=0,
                risk_decision="REJECT",
                position_size_btc=0.0,
                allocation_usd=0.0,
                stop_loss_price=None,
                buy_exchange="N/A",
                sell_exchange="N/A",
                buy_price=0,
                sell_price=0,
                quantity=0.0,
                signal_latency_ms=0,
                risk_latency_ms=0,
                execution_latency_ms=0.0,
                total_latency_ms=0.0,
                error_message=error_msg
            )
        
        # Validate inputs
        validation_error = self._validate_inputs(strategy_signal, risk_result)
        if validation_error:
            return TradeExecution(
                trade_id=trade_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode=self.mode.value,
                status=OrderStatus.REJECTED.value,
                strategy_decision=strategy_signal.get("decision", "UNKNOWN"),
                spread_pct=strategy_signal.get("spread_pct", 0),
                risk_decision="REJECT",
                position_size_btc=0.0,
                allocation_usd=0.0,
                stop_loss_price=None,
                buy_exchange=strategy_signal.get("buy_exchange", "N/A"),
                sell_exchange=strategy_signal.get("sell_exchange", "N/A"),
                buy_price=strategy_signal.get("buy_price", 0) or 0,
                sell_price=strategy_signal.get("sell_price", 0) or 0,
                quantity=0.0,
                signal_latency_ms=0,
                risk_latency_ms=0,
                execution_latency_ms=0.0,
                total_latency_ms=0.0,
                error_message=f"Validation failed: {validation_error}"
            )
        
        # Check live trading readiness
        if self.mode == ExecutionMode.LIVE and not self._check_live_ready():
            error_msg = "Live mode not configured: API keys missing"
            print(f"❌ {error_msg}")
            return TradeExecution(
                trade_id=trade_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode=self.mode.value,
                status=OrderStatus.REJECTED.value,
                strategy_decision=strategy_signal.get("decision", "UNKNOWN"),
                spread_pct=strategy_signal.get("spread_pct", 0),
                risk_decision=risk_result.get("decision", "UNKNOWN"),
                position_size_btc=0.0,
                allocation_usd=0.0,
                stop_loss_price=None,
                buy_exchange=strategy_signal.get("buy_exchange", "N/A"),
                sell_exchange=strategy_signal.get("sell_exchange", "N/A"),
                buy_price=strategy_signal.get("buy_price", 0) or 0,
                sell_price=strategy_signal.get("sell_price", 0) or 0,
                quantity=0.0,
                signal_latency_ms=0,
                risk_latency_ms=0,
                execution_latency_ms=0.0,
                total_latency_ms=0.0,
                error_message=error_msg
            )
        
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            error_msg = f"Circuit breaker is {self.circuit_breaker.state} - trading halted"
            print(f"🛑 {error_msg}")
            return TradeExecution(
                trade_id=trade_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode=self.mode.value,
                status=OrderStatus.REJECTED.value,
                strategy_decision=strategy_signal.get("decision", "UNKNOWN"),
                spread_pct=strategy_signal.get("spread_pct", 0),
                risk_decision=risk_result.get("decision", "UNKNOWN"),
                position_size_btc=0.0,
                allocation_usd=0.0,
                stop_loss_price=None,
                buy_exchange=strategy_signal.get("buy_exchange", "N/A"),
                sell_exchange=strategy_signal.get("sell_exchange", "N/A"),
                buy_price=strategy_signal.get("buy_price", 0) or 0,
                sell_price=strategy_signal.get("sell_price", 0) or 0,
                quantity=0.0,
                signal_latency_ms=0,
                risk_latency_ms=0,
                execution_latency_ms=0.0,
                total_latency_ms=0.0,
                error_message=error_msg
            )
        
        start_time = time.time()
        
        # Calculate latencies
        current_time = time.time()
        signal_latency_ms = (current_time - signal_timestamp) * 1000
        
        # Simulate/record risk check latency
        risk_latency_ms = random.uniform(5, 20) if self.mode == ExecutionMode.PAPER else 10.0
        
        execution_start = time.time()
        
        # Check if we should proceed
        if strategy_signal.get("decision") != "TRADE":
            execution = TradeExecution(
                trade_id=trade_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode=self.mode.value,
                status=OrderStatus.REJECTED.value,
                strategy_decision=strategy_signal.get("decision", "UNKNOWN"),
                spread_pct=strategy_signal.get("spread_pct", 0),
                risk_decision=risk_result.get("decision", "UNKNOWN"),
                position_size_btc=0.0,
                allocation_usd=0.0,
                stop_loss_price=None,
                buy_exchange=strategy_signal.get("buy_exchange", "N/A"),
                sell_exchange=strategy_signal.get("sell_exchange", "N/A"),
                buy_price=strategy_signal.get("buy_price", 0) or 0,
                sell_price=strategy_signal.get("sell_price", 0) or 0,
                quantity=0.0,
                signal_latency_ms=signal_latency_ms,
                risk_latency_ms=risk_latency_ms,
                execution_latency_ms=0.0,
                total_latency_ms=signal_latency_ms + risk_latency_ms,
                error_message="Strategy did not signal TRADE"
            )
            self.executions.append(execution)
            return execution
        
        if risk_result.get("decision") not in ["APPROVE", "MODIFY"]:
            execution = TradeExecution(
                trade_id=trade_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode=self.mode.value,
                status=OrderStatus.REJECTED.value,
                strategy_decision=strategy_signal.get("decision"),
                spread_pct=strategy_signal.get("spread_pct", 0),
                risk_decision=risk_result.get("decision", "UNKNOWN"),
                position_size_btc=0.0,
                allocation_usd=0.0,
                stop_loss_price=None,
                buy_exchange=strategy_signal.get("buy_exchange", "N/A"),
                sell_exchange=strategy_signal.get("sell_exchange", "N/A"),
                buy_price=strategy_signal.get("buy_price", 0) or 0,
                sell_price=strategy_signal.get("sell_price", 0) or 0,
                quantity=0.0,
                signal_latency_ms=signal_latency_ms,
                risk_latency_ms=risk_latency_ms,
                execution_latency_ms=0.0,
                total_latency_ms=signal_latency_ms + risk_latency_ms,
                error_message=f"Risk check rejected: {risk_result.get('reason')}"
            )
            self.executions.append(execution)
            return execution
        
        # Extract trade parameters
        buy_exchange = strategy_signal.get("buy_exchange")
        sell_exchange = strategy_signal.get("sell_exchange")
        buy_price = strategy_signal.get("buy_price", 0)
        sell_price = strategy_signal.get("sell_price", 0)
        quantity = risk_result.get("position_size_btc", 0)
        allocation = risk_result.get("allocation_usd", 0)
        stop_loss = risk_result.get("stop_loss_price")
        
        # Execute based on mode
        if self.mode == ExecutionMode.PAPER:
            execution = self._execute_paper(
                trade_id=trade_id,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                quantity=quantity,
                allocation=allocation,
                stop_loss=stop_loss,
                strategy_signal=strategy_signal,
                risk_result=risk_result,
                signal_latency_ms=signal_latency_ms,
                risk_latency_ms=risk_latency_ms,
                execution_start=execution_start
            )
        else:
            execution = self._execute_live(
                trade_id=trade_id,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                quantity=quantity,
                allocation=allocation,
                stop_loss=stop_loss,
                strategy_signal=strategy_signal,
                risk_result=risk_result,
                signal_latency_ms=signal_latency_ms,
                risk_latency_ms=risk_latency_ms,
                execution_start=execution_start
            )
        
        self.executions.append(execution)
        self._update_stats(execution)
        
        # Track executed order for idempotency
        self.executed_orders.add(trade_id)
        
        # Update circuit breaker
        if self.circuit_breaker:
            if execution.status == OrderStatus.FILLED.value:
                self.circuit_breaker.record_success()
            elif execution.status == OrderStatus.FAILED.value:
                self.circuit_breaker.record_failure()
        
        return execution
    
    def _execute_paper(
        self,
        trade_id: str,
        buy_exchange: str,
        sell_exchange: str,
        buy_price: float,
        sell_price: float,
        quantity: float,
        allocation: float,
        stop_loss: Optional[float],
        strategy_signal: Dict[str, Any],
        risk_result: Dict[str, Any],
        signal_latency_ms: float,
        risk_latency_ms: float,
        execution_start: float
    ) -> TradeExecution:
        """Execute a paper trade (simulation)."""
        
        # Simulate execution latency (network + exchange processing)
        simulated_latency = random.uniform(100, 500)  # 100-500ms
        time.sleep(0.01)  # Tiny actual sleep for realism
        
        execution_end = time.time()
        execution_latency_ms = (execution_end - execution_start) * 1000 + simulated_latency
        total_latency_ms = signal_latency_ms + risk_latency_ms + execution_latency_ms
        
        # Simulate slippage
        slippage = random.uniform(-0.001, 0.001)  # ±0.1%
        actual_buy = buy_price * (1 + abs(slippage))
        actual_sell = sell_price * (1 - abs(slippage))
        
        # Calculate fees (0.1% per trade)
        fee_rate = 0.001
        buy_fees = actual_buy * quantity * fee_rate
        sell_fees = actual_sell * quantity * fee_rate
        total_fees = buy_fees + sell_fees
        
        # Calculate P&L
        gross_pnl = (actual_sell - actual_buy) * quantity
        net_pnl = gross_pnl - total_fees
        
        print(f"\n📊 PAPER TRADE EXECUTED: {trade_id}")
        print(f"   Buy:  {quantity:.4f} BTC on {buy_exchange} @ ${actual_buy:,.2f}")
        print(f"   Sell: {quantity:.4f} BTC on {sell_exchange} @ ${actual_sell:,.2f}")
        print(f"   Fees: ${total_fees:,.2f}")
        print(f"   Net P&L: ${net_pnl:,.2f}")
        print(f"   Latency: {total_latency_ms:.1f}ms")
        
        return TradeExecution(
            trade_id=trade_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode=ExecutionMode.PAPER.value,
            status=OrderStatus.FILLED.value,
            strategy_decision=strategy_signal.get("decision"),
            spread_pct=strategy_signal.get("spread_pct", 0),
            risk_decision=risk_result.get("decision"),
            position_size_btc=quantity,
            allocation_usd=allocation,
            stop_loss_price=stop_loss,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            quantity=quantity,
            signal_latency_ms=signal_latency_ms,
            risk_latency_ms=risk_latency_ms,
            execution_latency_ms=execution_latency_ms,
            total_latency_ms=total_latency_ms,
            buy_order_id=f"PAPER_BUY_{trade_id}",
            sell_order_id=f"PAPER_SELL_{trade_id}",
            actual_buy_price=actual_buy,
            actual_sell_price=actual_sell,
            fees_paid=total_fees,
            net_pnl=net_pnl
        )
    
    def _execute_live(
        self,
        trade_id: str,
        buy_exchange: str,
        sell_exchange: str,
        buy_price: float,
        sell_price: float,
        quantity: float,
        allocation: float,
        stop_loss: Optional[float],
        strategy_signal: Dict[str, Any],
        risk_result: Dict[str, Any],
        signal_latency_ms: float,
        risk_latency_ms: float,
        execution_start: float
    ) -> TradeExecution:
        """
        Execute a live trade on exchanges using CCXT.
        Supports Binance, Coinbase, and other exchanges.
        """
        execution = TradeExecution(
            trade_id=trade_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode=ExecutionMode.LIVE.value,
            status=OrderStatus.PENDING.value,
            strategy_decision=strategy_signal.get("decision"),
            spread_pct=strategy_signal.get("spread_pct", 0),
            risk_decision=risk_result.get("decision"),
            position_size_btc=quantity,
            allocation_usd=allocation,
            stop_loss_price=stop_loss,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            quantity=quantity,
            signal_latency_ms=signal_latency_ms,
            risk_latency_ms=risk_latency_ms,
            execution_latency_ms=0.0,
            total_latency_ms=0.0
        )
        
        # Try to import ccxt
        try:
            import ccxt
        except ImportError:
            execution.status = OrderStatus.FAILED.value
            execution.error_message = "CCXT not installed. Run: pip install ccxt"
            return execution
        
        # Initialize exchanges
        exchanges = {}
        
        if buy_exchange.lower() == "binance" and self.binance_api_key:
            exchanges["buy"] = ccxt.binance({
                "apiKey": self.binance_api_key,
                "secret": self.binance_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"}
            })
        elif buy_exchange.lower() == "coinbase" and self.coinbase_api_key:
            exchanges["buy"] = ccxt.coinbase({
                "apiKey": self.coinbase_api_key,
                "secret": self.coinbase_secret,
                "enableRateLimit": True
            })
        
        if sell_exchange.lower() == "binance" and self.binance_api_key:
            exchanges["sell"] = ccxt.binance({
                "apiKey": self.binance_api_key,
                "secret": self.binance_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"}
            })
        elif sell_exchange.lower() == "coinbase" and self.coinbase_api_key:
            exchanges["sell"] = ccxt.coinbase({
                "apiKey": self.coinbase_api_key,
                "secret": self.coinbase_secret,
                "enableRateLimit": True
            })
        
        # Check if we have the required exchanges
        if "buy" not in exchanges or "sell" not in exchanges:
            execution.status = OrderStatus.FAILED.value
            execution.error_message = f"Missing API credentials for {buy_exchange} or {sell_exchange}"
            print(f"\n❌ LIVE TRADE FAILED: {trade_id}")
            print(f"   Error: {execution.error_message}")
            return execution
        
        # Execute trades
        buy_order_id = None
        sell_order_id = None
        actual_buy_price = None
        actual_sell_price = None
        total_fees = 0.0
        
        try:
            symbol = "BTC/USDT"
            
            # Place BUY order
            print(f"\n🔴 EXECUTING LIVE TRADE: {trade_id}")
            print(f"   BUY: {quantity:.6f} BTC on {buy_exchange}")
            
            for attempt in range(self.max_retries):
                try:
                    buy_order = exchanges["buy"].create_market_buy_order(symbol, quantity)
                    buy_order_id = buy_order.get("id", f"LIVE_BUY_{trade_id}")
                    actual_buy_price = buy_order.get("price", buy_price)
                    buy_fee = buy_order.get("fee", {}).get("cost", 0) or 0
                    total_fees += buy_fee
                    print(f"   ✅ BUY filled: {buy_order_id}")
                    break
                except Exception as e:
                    print(f"   ⚠️  BUY attempt {attempt+1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                    else:
                        raise
            
            # Place SELL order
            print(f"   SELL: {quantity:.6f} BTC on {sell_exchange}")
            
            for attempt in range(self.max_retries):
                try:
                    sell_order = exchanges["sell"].create_market_sell_order(symbol, quantity)
                    sell_order_id = sell_order.get("id", f"LIVE_SELL_{trade_id}")
                    actual_sell_price = sell_order.get("price", sell_price)
                    sell_fee = sell_order.get("fee", {}).get("cost", 0) or 0
                    total_fees += sell_fee
                    print(f"   ✅ SELL filled: {sell_order_id}")
                    break
                except Exception as e:
                    print(f"   ⚠️  SELL attempt {attempt+1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                    else:
                        raise
            
            # Calculate results
            execution_end = time.time()
            execution_latency_ms = (execution_end - execution_start) * 1000
            total_latency_ms = signal_latency_ms + risk_latency_ms + execution_latency_ms
            
            gross_pnl = (actual_sell_price - actual_buy_price) * quantity
            net_pnl = gross_pnl - total_fees
            
            execution.status = OrderStatus.FILLED.value
            execution.execution_latency_ms = execution_latency_ms
            execution.total_latency_ms = total_latency_ms
            execution.buy_order_id = buy_order_id
            execution.sell_order_id = sell_order_id
            execution.actual_buy_price = actual_buy_price
            execution.actual_sell_price = actual_sell_price
            execution.fees_paid = total_fees
            execution.net_pnl = net_pnl
            
            print(f"   💰 Net P&L: ${net_pnl:,.2f}")
            print(f"   ⏱️  Latency: {total_latency_ms:.1f}ms")
            
        except Exception as e:
            execution.status = OrderStatus.FAILED.value
            execution.error_message = str(e)
            execution.execution_latency_ms = (time.time() - execution_start) * 1000
            print(f"   ❌ FAILED: {e}")
        
        return execution
    
    def _update_stats(self, execution: TradeExecution):
        """Update execution statistics."""
        self.total_executions += 1
        
        if execution.status == OrderStatus.FILLED.value:
            self.successful_executions += 1
        elif execution.status in [OrderStatus.FAILED.value, OrderStatus.REJECTED.value]:
            self.failed_executions += 1
        
        # Update average latency
        total_latency = sum(e.total_latency_ms for e in self.executions)
        self.avg_latency_ms = total_latency / len(self.executions) if self.executions else 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary statistics."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": self.mode.value,
            "total_executions": self.total_executions,
            "successful": self.successful_executions,
            "failed": self.failed_executions,
            "success_rate": round(self.successful_executions / self.total_executions * 100, 2) if self.total_executions > 0 else 0,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "executions": [asdict(e) for e in self.executions[-10:]]  # Last 10
        }
    
    def print_summary(self):
        """Print execution summary."""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("EXECUTION LAYER SUMMARY")
        print("=" * 60)
        print(f"Mode:             {summary['mode']}")
        print(f"Total Executions: {summary['total_executions']}")
        print(f"Successful:       {summary['successful']}")
        print(f"Failed:           {summary['failed']}")
        print(f"Success Rate:     {summary['success_rate']:.1f}%")
        print(f"Avg Latency:      {summary['avg_latency_ms']:.1f}ms")
        print("=" * 60)


# Example usage and testing
if __name__ == "__main__":
    print("Execution Layer - Test Mode")
    print("=" * 60)
    
    # Test 1: Paper trade execution
    print("\n[Test 1] Paper Trade Execution")
    print("-" * 40)
    
    executor = ExecutionLayer(mode=ExecutionMode.PAPER)
    
    strategy_signal = {
        "decision": "TRADE",
        "buy_exchange": "Binance",
        "sell_exchange": "Coinbase",
        "buy_price": 68000,
        "sell_price": 69000,
        "spread_pct": 0.0147
    }
    
    risk_result = {
        "decision": "APPROVE",
        "position_size_btc": 0.0074,
        "allocation_usd": 500,
        "stop_loss_price": 66640
    }
    
    execution = executor.execute_trade(
        strategy_signal=strategy_signal,
        risk_result=risk_result,
        signal_timestamp=time.time() - 0.1  # Signal 100ms ago
    )
    
    print(f"\nTrade Status: {execution.status}")
    print(f"Net P&L: ${execution.net_pnl:,.2f}" if execution.net_pnl else "")
    print(f"Total Latency: {execution.total_latency_ms:.1f}ms")
    
    # Test 2: Rejected trade (risk check failed)
    print("\n[Test 2] Rejected Trade (Risk)")
    print("-" * 40)
    
    risk_rejected = {
        "decision": "REJECT",
        "reason": "Max exposure limit reached"
    }
    
    execution2 = executor.execute_trade(
        strategy_signal=strategy_signal,
        risk_result=risk_rejected,
        signal_timestamp=time.time() - 0.1
    )
    
    print(f"\nTrade Status: {execution2.status}")
    print(f"Error: {execution2.error_message}")
    
    # Test 3: No trade signal
    print("\n[Test 3] No Trade Signal")
    print("-" * 40)
    
    no_signal = {
        "decision": "NO_TRADE",
        "reason": "Spread below threshold"
    }
    
    execution3 = executor.execute_trade(
        strategy_signal=no_signal,
        risk_result={"decision": "HOLD"},
        signal_timestamp=time.time() - 0.1
    )
    
    print(f"\nTrade Status: {execution3.status}")
    print(f"Error: {execution3.error_message}")
    
    # Print summary
    executor.print_summary()
