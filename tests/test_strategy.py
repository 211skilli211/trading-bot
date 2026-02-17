#!/usr/bin/env python3
"""
Strategy Engine Tests
Run with: pytest tests/test_strategy.py -v
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy_engine import StrategyEngine, SpreadCalculator


class TestStrategyEngine:
    """Test suite for Strategy Engine."""
    
    def test_no_arbitrage_opportunity(self):
        """Test when spread is below threshold."""
        engine = StrategyEngine(fee_rate=0.001, slippage=0.0005)
        
        # Small spread - should be NO_TRADE
        price_data = [
            {"exchange": "Binance", "price": 68614.37},
            {"exchange": "Coinbase", "price": 68585.42}
        ]
        
        signal = engine.evaluate(price_data)
        
        assert signal.decision == "NO_TRADE"
        assert "below" in signal.reason.lower()
    
    def test_arbitrage_opportunity(self):
        """Test when spread exceeds threshold."""
        engine = StrategyEngine(fee_rate=0.001, slippage=0.0005)
        
        # Large spread - should be TRADE
        price_data = [
            {"exchange": "Binance", "price": 68000.00},
            {"exchange": "Coinbase", "price": 69000.00}
        ]
        
        signal = engine.evaluate(price_data)
        
        assert signal.decision == "TRADE"
        assert signal.buy_exchange == "Binance"
        assert signal.sell_exchange == "Coinbase"
        assert signal.expected_profit_pct is not None
        assert signal.expected_profit_pct > 0
    
    def test_insufficient_data(self):
        """Test with only one exchange."""
        engine = StrategyEngine()
        
        price_data = [
            {"exchange": "Binance", "price": 68614.37}
        ]
        
        signal = engine.evaluate(price_data)
        
        assert signal.decision == "NO_TRADE"
        assert "insufficient" in signal.reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
