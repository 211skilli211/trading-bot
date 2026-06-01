#!/usr/bin/env python3
"""
Paper Trading Engine (ported from Fincept-Corporation/FinceptTerminal)
========================================================================
Simulates order fills without real exchange connection.

Adapted from: fincept-qt/scripts/agno_trading/framework/paper_execution.py

Usage:
    from paper_trading_engine import PaperTradingEngine
    
    engine = PaperTradingEngine(initial_capital=10000, fee_bps=10)
    result = engine.execute_order("BTC/USDT", "buy", 0.1, 50000)
    portfolio = engine.get_portfolio()
"""

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    side: str = "long"  # "long" or "short"
    unrealized_pnl: float = 0.0
    opened_at: float = 0.0


@dataclass 
class PaperTrade:
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    fee: float = 0.0
    opened_at: float = 0.0
    closed_at: Optional[float] = None


class PaperTradingEngine:
    """
    Paper trading execution engine.
    Simulates instant fills at market price with configurable slippage and fees.
    """

    def __init__(self, initial_capital: float = 10000.0, fee_bps: float = 10.0, slippage_bps: float = 5.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_bps = fee_bps  # 10 bps = 0.1%
        self.slippage_bps = slippage_bps  # 5 bps = 0.05%
        self.positions: Dict[str, Position] = {}
        self.trades: List[PaperTrade] = []
        self.total_realized_pnl = 0.0
        self.trades_count = 0

    def execute_order(
        self,
        symbol: str,
        side: str,  # "buy" or "sell"
        quantity: float,
        price: float,
        max_slippage_bps: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a paper trade order.
        
        Returns:
            Dict with fill details
        """
        slippage = min(max_slippage_bps or self.slippage_bps, self.slippage_bps)
        slippage_factor = slippage / 10000.0

        # Apply slippage
        if side == "buy":
            fill_price = price * (1 + slippage_factor)
        else:
            fill_price = price * (1 - slippage_factor)

        notional = quantity * fill_price
        fee = notional * (self.fee_bps / 10000.0)
        now = time.time()

        if side == "buy":
            cost = notional + fee
            if cost > self.cash:
                return {"success": False, "error": "Insufficient funds", "required": cost, "available": self.cash}
            self.cash -= cost

            if symbol in self.positions:
                pos = self.positions[symbol]
                total_qty = pos.quantity + quantity
                total_cost = (pos.quantity * pos.avg_entry_price) + (quantity * fill_price)
                pos.avg_entry_price = total_cost / total_qty
                pos.quantity = total_qty
                pos.current_price = fill_price
            else:
                self.positions[symbol] = Position(
                    symbol=symbol, quantity=quantity, avg_entry_price=fill_price,
                    current_price=fill_price, side="long", opened_at=now
                )
        else:  # sell
            proceeds = notional - fee
            self.cash += proceeds

            if symbol in self.positions:
                pos = self.positions[symbol]
                if pos.quantity >= quantity:
                    realized = (fill_price - pos.avg_entry_price) * quantity
                    self.total_realized_pnl += realized
                    pos.quantity -= quantity
                    if pos.quantity < 0.001:
                        del self.positions[symbol]
                    else:
                        pos.current_price = fill_price
                else:
                    return {"success": False, "error": "Insufficient position size"}
            else:
                # Short selling
                self.positions[symbol] = Position(
                    symbol=symbol, quantity=-quantity, avg_entry_price=fill_price,
                    current_price=fill_price, side="short", opened_at=now
                )

        trade = PaperTrade(
            symbol=symbol, side=side, quantity=quantity,
            entry_price=fill_price, fee=fee, opened_at=now
        )
        self.trades.append(trade)
        self.trades_count += 1

        return {
            "success": True,
            "symbol": symbol,
            "side": side,
            "fill_price": round(fill_price, 2),
            "quantity": quantity,
            "notional": round(notional, 2),
            "fee": round(fee, 4),
            "cash_remaining": round(self.cash, 2)
        }

    def mark_to_market(self, prices: Dict[str, float]):
        """Update unrealized P&L with current prices."""
        for symbol, pos in self.positions.items():
            if symbol in prices:
                pos.current_price = prices[symbol]
                if pos.side == "long":
                    pos.unrealized_pnl = (prices[symbol] - pos.avg_entry_price) * pos.quantity
                else:
                    pos.unrealized_pnl = (pos.avg_entry_price - prices[symbol]) * abs(pos.quantity)

    def get_portfolio(self) -> Dict[str, Any]:
        """Get current portfolio snapshot."""
        total_unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        gross_exposure = sum(abs(p.quantity) * p.current_price for p in self.positions.values())
        net_exposure = sum(
            p.quantity * p.current_price if p.side == "long" else -abs(p.quantity) * p.current_price
            for p in self.positions.values()
        )

        long_value = sum(p.quantity * p.current_price for p in self.positions.values() if p.side == "long")
        total_value = self.cash + long_value + sum(
            p.unrealized_pnl for p in self.positions.values() if p.side == "short"
        )

        return {
            "cash": round(self.cash, 2),
            "total_value": round(total_value, 2),
            "total_realized_pnl": round(self.total_realized_pnl, 2),
            "total_unrealized_pnl": round(total_unrealized, 2),
            "gross_exposure": round(gross_exposure, 2),
            "net_exposure": round(net_exposure, 2),
            "trades_count": self.trades_count,
            "positions": len(self.positions),
            "returns_pct": round((total_value - self.initial_capital) / self.initial_capital * 100, 2)
        }

    def get_positions(self) -> List[Dict]:
        """Get all open positions."""
        return [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_entry": round(p.avg_entry_price, 2),
                "current_price": round(p.current_price, 2),
                "side": p.side,
                "unrealized_pnl": round(p.unrealized_pnl, 2)
            }
            for p in self.positions.values()
        ]

    def reset(self, initial_capital: Optional[float] = None):
        """Reset to initial state."""
        self.cash = initial_capital or self.initial_capital
        self.positions = {}
        self.trades = []
        self.total_realized_pnl = 0.0
        self.trades_count = 0
