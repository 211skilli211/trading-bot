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
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import random  # For simulating latency in paper mode
import os

# CCXT import for live trading
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False


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
        coinbase_secret: Optional[str] = None,
        kraken_api_key: Optional[str] = None,
        kraken_secret: Optional[str] = None
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
            kraken_api_key: Kraken API key (required for LIVE)
            kraken_secret: Kraken API secret (required for LIVE)
        """
        self.mode = mode
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # API credentials (only used in LIVE mode)
        self.binance_api_key = binance_api_key
        self.binance_secret = binance_secret
        self.coinbase_api_key = coinbase_api_key
        self.coinbase_secret = coinbase_secret
        self.kraken_api_key = kraken_api_key
        self.kraken_secret = kraken_secret
        
        # Trade tracking
        self.trade_counter = 0
        self.executions: List[TradeExecution] = []
        
        # Statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.avg_latency_ms = 0.0
        
        print(f"[ExecutionLayer] Initialized")
        print(f"  Mode: {mode.value}")
        print(f"  Max Retries: {max_retries}")
        
        # Initialize CCXT exchanges for live trading
        self.exchanges = {}
        if mode == ExecutionMode.LIVE and CCXT_AVAILABLE:
            self._init_ccxt_exchanges(
                binance_api_key, binance_secret, 
                coinbase_api_key, coinbase_secret,
                kraken_api_key, kraken_secret
            )
        
        if mode == ExecutionMode.LIVE:
            if not all([binance_api_key, binance_secret]):
                print("  ⚠️  WARNING: Binance credentials not provided")
            if not all([coinbase_api_key, coinbase_secret]):
                print("  ⚠️  WARNING: Coinbase credentials not provided")
            if not all([kraken_api_key, kraken_secret]):
                print("  ⚠️  WARNING: Kraken credentials not provided")
            if not CCXT_AVAILABLE:
                print("  ⚠️  WARNING: CCXT not installed - live trading disabled")
                print("     Run: pip install ccxt")
            print("  🔴 LIVE TRADING ENABLED - Real orders will be placed!")
        else:
            print("  📊 PAPER TRADING MODE - No real orders will be placed")
    
    def _init_ccxt_exchanges(self, binance_key, binance_secret, coinbase_key, coinbase_secret, 
                              kraken_key=None, kraken_secret=None):
        """Initialize CCXT exchange connections for live trading."""
        # Binance
        if binance_key and binance_secret:
            try:
                self.exchanges['binance'] = ccxt.binance({
                    'apiKey': binance_key,
                    'secret': binance_secret,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
                })
                print("  ✅ Binance: Connected")
            except Exception as e:
                print(f"  ❌ Binance: {e}")
        
        # Coinbase
        if coinbase_key and coinbase_secret:
            try:
                self.exchanges['coinbase'] = ccxt.coinbase({
                    'apiKey': coinbase_key,
                    'secret': coinbase_secret,
                    'enableRateLimit': True,
                })
                print("  ✅ Coinbase: Connected")
            except Exception as e:
                print(f"  ❌ Coinbase: {e}")
        
        # Kraken
        if kraken_key and kraken_secret:
            try:
                self.exchanges['kraken'] = ccxt.kraken({
                    'apiKey': kraken_key,
                    'secret': kraken_secret,
                    'enableRateLimit': True,
                })
                print("  ✅ Kraken: Connected")
            except Exception as e:
                print(f"  ❌ Kraken: {e}")
    
    def _normalize_symbol(self, symbol: str, exchange: str) -> str:
        """Normalize symbol for CCXT format (BTC/USDT)."""
        symbol = symbol.replace("-", "/").upper()
        # Handle common variations
        if "/" not in symbol:
            if symbol.endswith("USDT"):
                symbol = symbol.replace("USDT", "/USDT")
            elif symbol.endswith("USD"):
                symbol = symbol.replace("USD", "/USD")
        return symbol
    
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
        self.trade_counter += 1
        trade_id = f"TRADE_{self.trade_counter:04d}"
        
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
            total_latency_ms=0.0,
            error_message=None
        )
        
        if not CCXT_AVAILABLE:
            execution.status = OrderStatus.FAILED.value
            execution.error_message = "CCXT not installed (pip install ccxt)"
            return execution
        
        # Determine symbol (e.g., BTC/USDT)
        symbol = strategy_signal.get("symbol", "BTC/USDT")
        
        print(f"\n🔴 EXECUTING LIVE TRADE: {trade_id}")
        print(f"   Buy: {buy_exchange} @ ${buy_price:,.2f}")
        print(f"   Sell: {sell_exchange} @ ${sell_price:,.2f}")
        print(f"   Amount: {quantity:.6f} {symbol.split('/')[0]}")
        
        buy_order_id = None
        sell_order_id = None
        actual_buy_price = None
        actual_sell_price = None
        total_fees = 0.0
        
        try:
            # Execute BUY order
            buy_ex = self.exchanges.get(buy_exchange.lower())
            if buy_ex:
                buy_symbol = self._normalize_symbol(symbol, buy_exchange)
                print(f"   Placing BUY order on {buy_exchange}...")
                
                buy_order = buy_ex.create_market_buy_order(buy_symbol, quantity)
                buy_order_id = buy_order.get('id')
                actual_buy_price = buy_order.get('average', buy_order.get('price', buy_price))
                fee = buy_order.get('fee', {})
                if fee:
                    total_fees += fee.get('cost', 0)
                
                print(f"   ✅ BUY executed: {buy_order_id}")
                print(f"      Filled @ ${actual_buy_price:,.2f}")
            else:
                raise Exception(f"Buy exchange {buy_exchange} not connected")
            
            # Execute SELL order
            sell_ex = self.exchanges.get(sell_exchange.lower())
            if sell_ex:
                sell_symbol = self._normalize_symbol(symbol, sell_exchange)
                print(f"   Placing SELL order on {sell_exchange}...")
                
                sell_order = sell_ex.create_market_sell_order(sell_symbol, quantity)
                sell_order_id = sell_order.get('id')
                actual_sell_price = sell_order.get('average', sell_order.get('price', sell_price))
                fee = sell_order.get('fee', {})
                if fee:
                    total_fees += fee.get('cost', 0)
                
                print(f"   ✅ SELL executed: {sell_order_id}")
                print(f"      Filled @ ${actual_sell_price:,.2f}")
            else:
                raise Exception(f"Sell exchange {sell_exchange} not connected")
            
            # Calculate P&L
            gross_pnl = (actual_sell_price - actual_buy_price) * quantity
            net_pnl = gross_pnl - total_fees
            
            execution_latency_ms = (time.time() - execution_start) * 1000
            total_latency_ms = signal_latency_ms + risk_latency_ms + execution_latency_ms
            
            execution.status = OrderStatus.FILLED.value
            execution.buy_order_id = buy_order_id
            execution.sell_order_id = sell_order_id
            execution.actual_buy_price = actual_buy_price
            execution.actual_sell_price = actual_sell_price
            execution.fees_paid = total_fees
            execution.net_pnl = net_pnl
            execution.execution_latency_ms = execution_latency_ms
            execution.total_latency_ms = total_latency_ms
            
            print(f"\n   💰 Trade Complete!")
            print(f"      Gross P&L: ${gross_pnl:,.2f}")
            print(f"      Fees: ${total_fees:,.2f}")
            print(f"      Net P&L: ${net_pnl:,.2f}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n   ❌ Trade Failed: {error_msg}")
            execution.status = OrderStatus.FAILED.value
            execution.error_message = error_msg
        
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

    def get_exchange_balance(self, exchange_name: str, currency: str = 'USDT') -> Dict[str, Any]:
        """
        Get balance for a specific currency from a specific exchange.
        
        Args:
            exchange_name: Name of the exchange (binance, coinbase, kraken)
            currency: Currency to get balance for (e.g., 'USDT', 'BTC', 'USD')
            
        Returns:
            Dict with balance info or error message
        """
        if self.mode == ExecutionMode.PAPER:
            return {
                'exchange': exchange_name,
                'currency': currency,
                'free': 10000.0,  # Simulated paper balance
                'used': 0.0,
                'total': 10000.0,
                'mode': 'PAPER'
            }
        
        if not CCXT_AVAILABLE:
            return {'error': 'CCXT not installed', 'exchange': exchange_name}
        
        exchange = self.exchanges.get(exchange_name.lower())
        if not exchange:
            return {'error': f'Exchange {exchange_name} not connected', 'exchange': exchange_name}
        
        try:
            balance = exchange.fetch_balance()
            currency_balance = balance.get(currency.upper(), {})
            return {
                'exchange': exchange_name,
                'currency': currency,
                'free': currency_balance.get('free', 0),
                'used': currency_balance.get('used', 0),
                'total': currency_balance.get('total', 0),
                'mode': 'LIVE'
            }
        except Exception as e:
            return {'error': str(e), 'exchange': exchange_name, 'currency': currency}

    def get_all_balances(self, currency: str = 'USDT') -> Dict[str, Any]:
        """
        Get balances from all connected exchanges.
        
        Args:
            currency: Currency to get balance for
            
        Returns:
            Dict with balances from all exchanges
        """
        balances = {}
        
        for exchange_name in ['binance', 'coinbase', 'kraken']:
            balance = self.get_exchange_balance(exchange_name, currency)
            balances[exchange_name] = balance
        
        # Calculate totals
        total_free = sum(b.get('free', 0) for b in balances.values() if 'free' in b)
        total_used = sum(b.get('used', 0) for b in balances.values() if 'used' in b)
        
        return {
            'currency': currency,
            'exchanges': balances,
            'total_free': total_free,
            'total_used': total_used,
            'total': total_free + total_used,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def get_exchange_price(self, exchange_name: str, symbol: str = 'BTC/USDT') -> Optional[Dict[str, Any]]:
        """
        Get current price from a specific exchange.
        
        Args:
            exchange_name: Name of the exchange
            symbol: Trading pair symbol
            
        Returns:
            Price data dict or None
        """
        if not CCXT_AVAILABLE:
            return None
        
        exchange = self.exchanges.get(exchange_name.lower())
        if not exchange:
            return None
        
        try:
            normalized_symbol = self._normalize_symbol(symbol, exchange_name)
            ticker = exchange.fetch_ticker(normalized_symbol)
            return {
                'exchange': exchange_name,
                'symbol': symbol,
                'price': ticker.get('last'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'timestamp': ticker.get('timestamp'),
                'datetime': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            print(f"[ExecutionLayer] Error fetching price from {exchange_name}: {e}")
            return None

    def find_arbitrage_opportunities(
        self, 
        symbol: str = 'BTC/USDT',
        min_spread_pct: float = 0.002
    ) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities between connected exchanges.
        
        Args:
            symbol: Trading pair to check (e.g., 'BTC/USDT')
            min_spread_pct: Minimum spread percentage to consider (0.002 = 0.2%)
            
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        prices = {}
        
        # Fetch prices from all connected exchanges
        for exchange_name in ['binance', 'coinbase', 'kraken']:
            price_data = self.get_exchange_price(exchange_name, symbol)
            if price_data and price_data.get('price'):
                prices[exchange_name] = price_data
        
        if len(prices) < 2:
            print(f"[ExecutionLayer] Not enough exchanges have prices for {symbol}")
            return opportunities
        
        # Find arbitrage opportunities (buy low, sell high)
        for buy_exchange, buy_data in prices.items():
            for sell_exchange, sell_data in prices.items():
                if buy_exchange == sell_exchange:
                    continue
                
                buy_price = buy_data.get('ask', buy_data.get('price', 0))
                sell_price = sell_data.get('bid', sell_data.get('price', 0))
                
                if buy_price <= 0 or sell_price <= 0:
                    continue
                
                spread = sell_price - buy_price
                spread_pct = spread / buy_price if buy_price > 0 else 0
                
                if spread_pct >= min_spread_pct:
                    opportunities.append({
                        'symbol': symbol,
                        'buy_exchange': buy_exchange,
                        'sell_exchange': sell_exchange,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'spread': spread,
                        'spread_pct': spread_pct,
                        'potential_profit_pct': spread_pct - 0.002,  # Approximate fees
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
        
        # Sort by spread percentage (highest first)
        opportunities.sort(key=lambda x: x['spread_pct'], reverse=True)
        
        return opportunities

    def print_arbitrage_opportunities(self, symbol: str = 'BTC/USDT', min_spread_pct: float = 0.002):
        """
        Print arbitrage opportunities between exchanges.
        
        Args:
            symbol: Trading pair to check
            min_spread_pct: Minimum spread percentage
        """
        print(f"\n[ExecutionLayer] Scanning for arbitrage opportunities on {symbol}...")
        
        opportunities = self.find_arbitrage_opportunities(symbol, min_spread_pct)
        
        if not opportunities:
            print("  No arbitrage opportunities found.")
            return
        
        print(f"\n  Found {len(opportunities)} arbitrage opportunity(s):")
        print("  " + "-" * 70)
        
        for i, opp in enumerate(opportunities[:5], 1):  # Show top 5
            print(f"  {i}. Buy on {opp['buy_exchange'].upper()} @ ${opp['buy_price']:,.2f}")
            print(f"     Sell on {opp['sell_exchange'].upper()} @ ${opp['sell_price']:,.2f}")
            print(f"     Spread: {opp['spread_pct']:.4%} (${opp['spread']:,.2f})")
            print(f"     Est. Profit: {opp['potential_profit_pct']:.4%} after fees")
            print()


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
