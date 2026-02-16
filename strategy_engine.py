#!/usr/bin/env python3
"""
Strategy Engine - Arbitrage Logic Module
Evaluates arbitrage opportunities and generates trade signals.
Part of the modular trading bot blueprint.
"""

import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class TradeDecision(Enum):
    """Trade decision types."""
    TRADE = "TRADE"
    NO_TRADE = "NO_TRADE"
    HOLD = "HOLD"


@dataclass
class TradeSignal:
    """Structured trade signal output."""
    timestamp: str
    decision: str
    reason: str
    buy_exchange: Optional[str]
    sell_exchange: Optional[str]
    buy_price: Optional[float]
    sell_price: Optional[float]
    spread_pct: float
    threshold_pct: float
    expected_profit_pct: Optional[float]
    confidence: str  # HIGH, MEDIUM, LOW


@dataclass
class PaperTrade:
    """Paper trade record for simulation."""
    trade_id: str
    timestamp: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    quantity: float
    spread_pct: float
    expected_profit: float
    status: str  # OPEN, CLOSED
    actual_profit: Optional[float] = None
    close_timestamp: Optional[str] = None


class StrategyEngine:
    """
    Arbitrage strategy engine.
    
    Evaluates price spreads between exchanges and determines
    if an arbitrage opportunity exists after accounting for
    trading fees and slippage.
    """
    
    def __init__(
        self,
        fee_rate: float = 0.001,      # 0.1% per trade (maker/taker average)
        slippage: float = 0.0005,      # 0.05% estimated slippage
        min_spread: float = 0.002,     # Minimum 0.2% spread to consider
        paper_trading: bool = True     # Default to paper trading for safety
    ):
        """
        Initialize strategy engine.
        
        Args:
            fee_rate: Trading fee per transaction (e.g., 0.001 = 0.1%)
            slippage: Estimated slippage per trade (e.g., 0.0005 = 0.05%)
            min_spread: Minimum spread threshold before considering trade
            paper_trading: If True, only simulate trades (recommended for testing)
        """
        self.fee_rate = Decimal(str(fee_rate))
        self.slippage = Decimal(str(slippage))
        self.min_spread = Decimal(str(min_spread))
        self.paper_trading = paper_trading
        
        # Total cost = buy fee + sell fee + slippage on both sides
        self.total_cost = (self.fee_rate * 2) + (self.slippage * 2)
        
        # Paper trading portfolio
        self.paper_trades: List[PaperTrade] = []
        self.trade_counter = 0
        
        print(f"[StrategyEngine] Initialized")
        print(f"  Fee rate: {float(self.fee_rate):.4%} per trade")
        print(f"  Slippage estimate: {float(self.slippage):.4%} per trade")
        print(f"  Total cost threshold: {float(self.total_cost):.4%}")
        print(f"  Paper trading mode: {'ENABLED' if paper_trading else 'DISABLED'}")
    
    def evaluate(self, price_data: List[Dict[str, Any]]) -> TradeSignal:
        """
        Evaluate arbitrage opportunity from price data.
        
        Args:
            price_data: List of normalized price data from multiple exchanges
        
        Returns:
            TradeSignal with decision and reasoning
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Need at least 2 exchanges to compare
        if len(price_data) < 2:
            return TradeSignal(
                timestamp=timestamp,
                decision=TradeDecision.NO_TRADE.value,
                reason="Insufficient price data (need at least 2 exchanges)",
                buy_exchange=None,
                sell_exchange=None,
                buy_price=None,
                sell_price=None,
                spread_pct=0.0,
                threshold_pct=float(self.total_cost),
                expected_profit_pct=None,
                confidence="LOW"
            )
        
        # Find highest and lowest prices
        sorted_by_price = sorted(price_data, key=lambda x: x['price'])
        lowest = sorted_by_price[0]
        highest = sorted_by_price[-1]
        
        buy_exchange = lowest['exchange']
        sell_exchange = highest['exchange']
        buy_price = Decimal(str(lowest['price']))
        sell_price = Decimal(str(highest['price']))
        
        # Calculate spread
        spread_abs = sell_price - buy_price
        spread_pct = spread_abs / buy_price
        
        # Calculate expected profit after fees
        # Buy cost: price * (1 + fee_rate + slippage)
        buy_cost = buy_price * (Decimal('1') + self.fee_rate + self.slippage)
        # Sell revenue: price * (1 - fee_rate - slippage)
        sell_revenue = sell_price * (Decimal('1') - self.fee_rate - self.slippage)
        expected_profit = sell_revenue - buy_cost
        expected_profit_pct = expected_profit / buy_price
        
        # Decision logic
        threshold = self.total_cost + self.min_spread
        
        if spread_pct <= threshold:
            decision = TradeDecision.NO_TRADE.value
            reason = f"Spread {float(spread_pct):.4%} below profitable threshold {float(threshold):.4%}"
            confidence = "LOW"
        else:
            decision = TradeDecision.TRADE.value
            reason = f"Arbitrage: Buy on {buy_exchange} (${float(buy_price):,.2f}), Sell on {sell_exchange} (${float(sell_price):,.2f})"
            confidence = "HIGH" if expected_profit_pct > Decimal('0.005') else "MEDIUM"
            
            # Execute or simulate trade
            if self.paper_trading:
                self._execute_paper_trade(
                    buy_exchange=buy_exchange,
                    sell_exchange=sell_exchange,
                    buy_price=float(buy_price),
                    sell_price=float(sell_price),
                    spread_pct=float(spread_pct),
                    expected_profit=float(expected_profit)
                )
        
        return TradeSignal(
            timestamp=timestamp,
            decision=decision,
            reason=reason,
            buy_exchange=buy_exchange if decision == TradeDecision.TRADE.value else None,
            sell_exchange=sell_exchange if decision == TradeDecision.TRADE.value else None,
            buy_price=float(buy_price) if decision == TradeDecision.TRADE.value else None,
            sell_price=float(sell_price) if decision == TradeDecision.TRADE.value else None,
            spread_pct=float(spread_pct),
            threshold_pct=float(threshold),
            expected_profit_pct=float(expected_profit_pct) if decision == TradeDecision.TRADE.value else None,
            confidence=confidence
        )
    
    def _execute_paper_trade(
        self,
        buy_exchange: str,
        sell_exchange: str,
        buy_price: float,
        sell_price: float,
        spread_pct: float,
        expected_profit: float,
        quantity: float = 0.01  # Simulate 0.01 BTC trades
    ) -> PaperTrade:
        """
        Execute a paper trade (simulation).
        
        Args:
            buy_exchange: Exchange to buy on
            sell_exchange: Exchange to sell on
            buy_price: Buy price
            sell_price: Sell price
            spread_pct: Spread percentage
            expected_profit: Expected profit in USD
            quantity: Quantity to trade (BTC)
        
        Returns:
            PaperTrade record
        """
        self.trade_counter += 1
        trade_id = f"PAPER_{self.trade_counter:04d}"
        
        trade = PaperTrade(
            trade_id=trade_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            quantity=quantity,
            spread_pct=spread_pct,
            expected_profit=expected_profit * quantity,  # Scale by quantity
            status="OPEN"
        )
        
        self.paper_trades.append(trade)
        
        print(f"\n📊 PAPER TRADE EXECUTED: {trade_id}")
        print(f"   Buy:  {quantity} BTC on {buy_exchange} @ ${buy_price:,.2f}")
        print(f"   Sell: {quantity} BTC on {sell_exchange} @ ${sell_price:,.2f}")
        print(f"   Expected P&L: ${trade.expected_profit:,.2f}")
        
        return trade
    
    def get_paper_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get summary of paper trading performance.
        
        Returns:
            Dictionary with portfolio statistics
        """
        if not self.paper_trades:
            return {
                "total_trades": 0,
                "open_trades": 0,
                "closed_trades": 0,
                "total_expected_profit": 0.0,
                "avg_spread_captured": 0.0
            }
        
        open_trades = [t for t in self.paper_trades if t.status == "OPEN"]
        closed_trades = [t for t in self.paper_trades if t.status == "CLOSED"]
        
        total_expected = sum(t.expected_profit for t in self.paper_trades)
        avg_spread = sum(t.spread_pct for t in self.paper_trades) / len(self.paper_trades)
        
        return {
            "total_trades": len(self.paper_trades),
            "open_trades": len(open_trades),
            "closed_trades": len(closed_trades),
            "total_expected_profit": round(total_expected, 2),
            "avg_spread_captured": round(avg_spread * 100, 4),
            "trades": [asdict(t) for t in self.paper_trades[-10:]]  # Last 10 trades
        }
    
    def print_summary(self):
        """Print portfolio summary to console."""
        summary = self.get_paper_portfolio_summary()
        
        print("\n" + "=" * 60)
        print("PAPER TRADING PORTFOLIO SUMMARY")
        print("=" * 60)
        print(f"Total Trades:     {summary['total_trades']}")
        print(f"Open Trades:      {summary['open_trades']}")
        print(f"Expected P&L:     ${summary['total_expected_profit']:,.2f}")
        print(f"Avg Spread:       {summary['avg_spread_captured']:.4f}%")
        print("=" * 60)


class ArbitrageStrategy:
    """
    Higher-level arbitrage strategy with multiple configurations.
    
    Supports different arbitrage types:
    - Simple: Direct arbitrage between two exchanges
    - Triangular: Three-pair arbitrage (future extension)
    - Cross-chain: Cross-chain arbitrage (future extension)
    """
    
    def __init__(self, strategy_type: str = "simple", config: Optional[Dict] = None):
        """
        Initialize arbitrage strategy.
        
        Args:
            strategy_type: Type of arbitrage strategy
            config: Configuration dictionary
        """
        self.strategy_type = strategy_type
        self.config = config or {}
        
        # Initialize engine with config or defaults
        self.engine = StrategyEngine(
            fee_rate=self.config.get('fee_rate', 0.001),
            slippage=self.config.get('slippage', 0.0005),
            min_spread=self.config.get('min_spread', 0.002),
            paper_trading=self.config.get('paper_trading', True)
        )
    
    def analyze(self, price_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run full analysis on price data.
        
        Args:
            price_data: List of price data from exchanges
        
        Returns:
            Complete analysis results
        """
        signal = self.engine.evaluate(price_data)
        portfolio = self.engine.get_paper_portfolio_summary()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy_type": self.strategy_type,
            "signal": asdict(signal),
            "paper_portfolio": portfolio,
            "config": {
                "fee_rate": float(self.engine.fee_rate),
                "slippage": float(self.engine.slippage),
                "total_cost_threshold": float(self.engine.total_cost),
                "paper_trading": self.engine.paper_trading
            }
        }


# Example usage and testing
if __name__ == "__main__":
    print("Strategy Engine - Test Mode")
    print("=" * 60)
    
    # Test 1: No arbitrage opportunity
    print("\n[Test 1] No arbitrage opportunity")
    print("-" * 40)
    
    engine = StrategyEngine(paper_trading=True)
    
    test_prices_no_opportunity = [
        {"exchange": "Binance", "symbol": "BTCUSDT", "price": 68614.37, "bid": 68614.37, "ask": 68614.38},
        {"exchange": "Coinbase", "symbol": "BTC-USD", "price": 68585.42, "bid": 68585.42, "ask": 68585.43}
    ]
    
    signal = engine.evaluate(test_prices_no_opportunity)
    print(f"\nDecision: {signal.decision}")
    print(f"Reason: {signal.reason}")
    print(f"Spread: {signal.spread_pct:.4%}")
    print(f"Threshold: {signal.threshold_pct:.4%}")
    
    # Test 2: Arbitrage opportunity
    print("\n[Test 2] Arbitrage opportunity detected")
    print("-" * 40)
    
    # Create a larger spread scenario
    test_prices_opportunity = [
        {"exchange": "Binance", "symbol": "BTCUSDT", "price": 68000.00, "bid": 68000.00, "ask": 68000.01},
        {"exchange": "Coinbase", "symbol": "BTC-USD", "price": 69000.00, "bid": 69000.00, "ask": 69000.01}
    ]
    
    signal = engine.evaluate(test_prices_opportunity)
    print(f"\nDecision: {signal.decision}")
    print(f"Reason: {signal.reason}")
    print(f"Spread: {signal.spread_pct:.4%}")
    print(f"Expected Profit: {signal.expected_profit_pct:.4%}" if signal.expected_profit_pct else "")
    
    # Test 3: Full strategy analysis
    print("\n[Test 3] Full strategy analysis")
    print("-" * 40)
    
    strategy = ArbitrageStrategy(config={
        'fee_rate': 0.001,
        'slippage': 0.0005,
        'paper_trading': True
    })
    
    result = strategy.analyze(test_prices_opportunity)
    print(f"\nStrategy Type: {result['strategy_type']}")
    print(f"Signal: {json.dumps(result['signal'], indent=2)}")
    
    engine.print_summary()
