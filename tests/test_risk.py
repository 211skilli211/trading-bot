#!/usr/bin/env python3
"""
Risk Manager Tests
Run with: pytest tests/test_risk.py -v
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_manager import RiskManager


class TestRiskManager:
    """Test suite for Risk Manager."""
    
    def test_trade_approval(self):
        """Test normal trade approval."""
        rm = RiskManager(
            max_position_btc=0.05,
            stop_loss_pct=0.02,
            capital_pct_per_trade=0.05,
            initial_balance=10000
        )
        
        trade_signal = {"decision": "TRADE"}
        risk_check = rm.assess_trade(trade_signal, current_price=68000)
        
        assert risk_check.decision in ["APPROVE", "MODIFY"]
        assert risk_check.position_size_btc > 0
        assert risk_check.stop_loss_price is not None
    
    def test_daily_loss_limit(self):
        """Test trading halt when daily loss limit hit."""
        from decimal import Decimal
        
        rm = RiskManager(
            max_position_btc=0.05,
            stop_loss_pct=0.02,
            daily_loss_limit_pct=0.05,
            initial_balance=10000
        )
        
        # Simulate daily loss
        rm.daily_pnl = Decimal('-600')  # $600 loss = 6%
        
        trade_signal = {"decision": "TRADE"}
        risk_check = rm.assess_trade(trade_signal, current_price=68000)
        
        assert risk_check.decision == "REJECT"
        assert rm.trading_halted == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
