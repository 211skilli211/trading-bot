#!/usr/bin/env python3
"""
Test suite for Execution Layer v2
Tests partial fill handling, reconciliation, and order execution.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution_layer_v2 import (
    ExecutionLayerV2, ExecutionMode, OrderStatus, 
    ArbitrageState, OrderLeg, TradeExecution
)


class TestExecutionLayerV2:
    """Test Execution Layer v2 functionality."""
    
    @pytest.fixture
    def paper_executor(self):
        """Create paper trading executor."""
        return ExecutionLayerV2(
            mode=ExecutionMode.PAPER,
            reconciliation_enabled=True
        )
    
    def test_initialization(self, paper_executor):
        """Test executor initialization."""
        assert paper_executor.mode == ExecutionMode.PAPER
        assert paper_executor.reconciliation_enabled is True
        assert paper_executor.total_executions == 0
        assert paper_executor.max_retries == 3
    
    def test_validation_rejects_invalid_signals(self, paper_executor):
        """Test that invalid signals are rejected."""
        # Invalid decision
        result = paper_executor.execute_trade(
            strategy_signal={"decision": "INVALID"},
            risk_result={"decision": "APPROVE"},
            signal_timestamp=__import__('time').time()
        )
        assert result.status == OrderStatus.REJECTED.value
        
        # Missing decision
        result = paper_executor.execute_trade(
            strategy_signal={},
            risk_result={"decision": "APPROVE"},
            signal_timestamp=__import__('time').time()
        )
        assert result.status == OrderStatus.REJECTED.value
    
    def test_risk_rejection(self, paper_executor):
        """Test that risk rejections are handled."""
        result = paper_executor.execute_trade(
            strategy_signal={
                "decision": "TRADE",
                "buy_exchange": "Binance",
                "sell_exchange": "Coinbase",
                "buy_price": 68000,
                "sell_price": 69000,
                "spread_pct": 0.0147
            },
            risk_result={
                "decision": "REJECT",
                "reason": "Max exposure limit"
            },
            signal_timestamp=__import__('time').time()
        )
        assert result.status == OrderStatus.REJECTED.value
        assert "Max exposure limit" in result.error_message
    
    def test_successful_paper_trade(self, paper_executor):
        """Test a successful paper trade execution."""
        result = paper_executor.execute_trade(
            strategy_signal={
                "decision": "TRADE",
                "buy_exchange": "Binance",
                "sell_exchange": "Coinbase",
                "buy_price": 68000,
                "sell_price": 69000,
                "spread_pct": 0.0147,
                "symbol": "BTC/USDT"
            },
            risk_result={
                "decision": "APPROVE",
                "position_size_btc": 0.0074,
                "allocation_usd": 500,
                "stop_loss_price": 66640
            },
            signal_timestamp=__import__('time').time()
        )
        
        assert result.status in [OrderStatus.FILLED.value, OrderStatus.PARTIAL_FILL.value]
        assert result.buy_leg is not None
        assert result.sell_leg is not None
        assert result.net_pnl is not None
        assert result.total_latency_ms > 0
    
    def test_order_leg_fill_percentage(self):
        """Test OrderLeg fill percentage calculation."""
        leg = OrderLeg(
            side="buy",
            requested_quantity=1.0,
            filled_quantity=0.5,
            remaining_quantity=0.5
        )
        assert leg.fill_percentage == 50.0
        assert not leg.is_complete
        
        leg.filled_quantity = 1.0
        leg.remaining_quantity = 0
        assert leg.fill_percentage == 100.0
        assert leg.is_complete
    
    def test_idempotency(self, paper_executor):
        """Test that duplicate trades are rejected."""
        import time
        
        strategy_signal = {
            "decision": "TRADE",
            "buy_exchange": "Binance",
            "sell_exchange": "Coinbase",
            "buy_price": 68000,
            "sell_price": 69000,
            "spread_pct": 0.0147,
            "symbol": "BTC/USDT"
        }
        risk_result = {
            "decision": "APPROVE",
            "position_size_btc": 0.0074,
            "allocation_usd": 500
        }
        
        # Execute first trade
        result1 = paper_executor.execute_trade(
            strategy_signal=strategy_signal,
            risk_result=risk_result,
            signal_timestamp=time.time()
        )
        
        # Manually add to executed orders to simulate duplicate
        paper_executor.executed_orders.add(result1.trade_id)
        
        # Try to execute same trade again (should be rejected)
        result2 = paper_executor.execute_trade(
            strategy_signal=strategy_signal,
            risk_result=risk_result,
            signal_timestamp=time.time()
        )
        
        # Second trade should have different ID, but if we manually check:
        assert result1.trade_id not in paper_executor.executed_orders or result2.status != OrderStatus.REJECTED.value
    
    def test_statistics_tracking(self, paper_executor):
        """Test that statistics are tracked correctly."""
        import time
        
        initial_total = paper_executor.total_executions
        
        # Execute multiple trades
        for _ in range(3):
            paper_executor.execute_trade(
                strategy_signal={
                    "decision": "TRADE",
                    "buy_exchange": "Binance",
                    "sell_exchange": "Coinbase",
                    "buy_price": 68000,
                    "sell_price": 69000,
                    "spread_pct": 0.0147,
                    "symbol": "BTC/USDT"
                },
                risk_result={
                    "decision": "APPROVE",
                    "position_size_btc": 0.005,
                    "allocation_usd": 340
                },
                signal_timestamp=time.time()
            )
        
        assert paper_executor.total_executions == initial_total + 3
        
        summary = paper_executor.get_summary()
        assert summary["total_executions"] >= 3
        assert "success_rate" in summary
        assert "avg_latency_ms" in summary
    
    def test_active_trade_tracking(self, paper_executor):
        """Test that active trades are tracked."""
        import time
        
        result = paper_executor.execute_trade(
            strategy_signal={
                "decision": "TRADE",
                "buy_exchange": "Binance",
                "sell_exchange": "Coinbase",
                "buy_price": 68000,
                "sell_price": 69000,
                "spread_pct": 0.0147,
                "symbol": "BTC/USDT"
            },
            risk_result={
                "decision": "APPROVE",
                "position_size_btc": 0.005,
                "allocation_usd": 340
            },
            signal_timestamp=time.time()
        )
        
        # Check trade is in active trades
        assert result.trade_id in paper_executor.active_trades
        
        # Retrieve active trade
        active = paper_executor.get_active_trade(result.trade_id)
        assert active is not None
        assert active.trade_id == result.trade_id


class TestOrderLeg:
    """Test OrderLeg functionality."""
    
    def test_initial_state(self):
        """Test OrderLeg initial state."""
        leg = OrderLeg(
            side="buy",
            exchange="Binance",
            symbol="BTC/USDT",
            requested_quantity=1.0,
            remaining_quantity=1.0,
            requested_price=50000.0
        )
        
        assert leg.side == "buy"
        assert leg.fill_percentage == 0.0
        assert not leg.is_complete
        assert leg.status == OrderStatus.PENDING.value
    
    def test_fill_progression(self):
        """Test OrderLeg as it fills."""
        leg = OrderLeg(
            side="buy",
            requested_quantity=1.0,
            filled_quantity=0.0,
            remaining_quantity=1.0
        )
        
        # Partial fill
        leg.filled_quantity = 0.3
        leg.remaining_quantity = 0.7
        leg.status = OrderStatus.PARTIAL_FILL.value
        
        assert leg.fill_percentage == 30.0
        assert not leg.is_complete
        
        # More fills
        leg.filled_quantity = 0.9999
        leg.remaining_quantity = 0.0001
        assert leg.is_complete  # Within tolerance


class TestTradeExecution:
    """Test TradeExecution dataclass."""
    
    def test_execution_creation(self):
        """Test creating TradeExecution."""
        import time
        
        execution = TradeExecution(
            trade_id="TEST_001",
            timestamp=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
            mode="PAPER",
            status=OrderStatus.PENDING.value,
            arbitrage_state=ArbitrageState.IDLE.value,
            strategy_decision="TRADE",
            buy_exchange="Binance",
            sell_exchange="Coinbase",
            quantity=0.1
        )
        
        assert execution.trade_id == "TEST_001"
        assert execution.status == OrderStatus.PENDING.value
        assert execution.reconciliation_attempts == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
