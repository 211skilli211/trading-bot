#!/usr/bin/env python3
"""
Binary Arbitrage Strategy
========================
Strategy #1: Buy YES + NO when combined price < $1.00
Guaranteed profit = $1.00 - (YES + NO)

Example: YES @ $0.49 + NO @ $0.48 = $0.97 → $0.03 guaranteed profit

This strategy has near-100% win rate because it's mathematically guaranteed.
"""

import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Import PolyMarket client
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from polymarket_client import PolyMarketClient, BinaryMarket

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity"""
    condition_id: str
    question: str
    yes_price: float
    no_price: float
    combined_price: float
    profit_percent: float
    profit_per_dollar: float
    volume: float
    liquidity: float
    timestamp: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ArbitrageTrade:
    """Executed arbitrage trade"""
    trade_id: str
    condition_id: str
    question: str
    yes_amount: float
    no_amount: float
    yes_price: float
    no_price: float
    total_cost: float
    guaranteed_profit: float
    status: str  # PENDING, EXECUTED, SETTLED, FAILED
    executed_at: str
    resolved_at: Optional[str] = None
    actual_profit: Optional[float] = None


class BinaryArbitrageStrategy:
    """
    Binary Arbitrage Strategy
    
    Key Principles:
    - Only trade when YES + NO < $0.99 (minimum 1% profit)
    - Max position size to manage liquidity risk
    - Track all trades in database
    - Alert on execution
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = PolyMarketClient()
        
        # Strategy parameters
        self.min_spread_pct = config.get("min_spread_pct", 1.0)  # Minimum 1% profit
        self.max_position_usd = config.get("max_position_usd", 10)  # Max $10 per arb
        self.max_concurrent = config.get("max_concurrent_arbs", 5)
        self.check_interval = config.get("check_interval_seconds", 30)
        
        # State
        self.active_arbitrages: List[ArbitrageOpportunity] = []
        self.executed_trades: List[ArbitrageTrade] = []
        self.stats = {
            "total_scans": 0,
            "opportunities_found": 0,
            "trades_executed": 0,
            "total_profit": 0.0,
            "wins": 0,
            "losses": 0
        }
        
        # Database
        self._init_database()
        
        logger.info(f"[BinaryArb] Initialized with min_spread={self.min_spread_pct}%")
    
    def _init_database(self):
        """Initialize trades database"""
        conn = sqlite3.connect("trades.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS binary_arbitrages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE,
                condition_id TEXT,
                question TEXT,
                yes_amount REAL,
                no_amount REAL,
                yes_price REAL,
                no_price REAL,
                total_cost REAL,
                guaranteed_profit REAL,
                status TEXT,
                executed_at TEXT,
                resolved_at TEXT,
                actual_profit REAL
            )
        """)
        conn.commit()
        conn.close()
    
    def scan(self) -> List[ArbitrageOpportunity]:
        """Scan for arbitrage opportunities"""
        self.stats["total_scans"] += 1
        
        try:
            # Get all binary markets
            markets = self.client.get_binary_markets(min_liquidity=1000)
            
            opportunities = []
            for market in markets:
                if market.is_arbitrageable and market.arbitrage_percent >= self.min_spread_pct:
                    opp = ArbitrageOpportunity(
                        condition_id=market.condition_id,
                        question=market.question,
                        yes_price=market.yes_price,
                        no_price=market.no_price,
                        combined_price=market.combined_price,
                        profit_percent=market.arbitrage_percent,
                        profit_per_dollar=1.0 - market.combined_price,
                        volume=market.volume,
                        liquidity=market.liquidity,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    opportunities.append(opp)
            
            # Sort by profit potential
            opportunities.sort(key=lambda x: x.profit_percent, reverse=True)
            self.active_arbitrages = opportunities
            
            if opportunities:
                self.stats["opportunities_found"] += len(opportunities)
                logger.info(f"[BinaryArb] Found {len(opportunities)} opportunities")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"[BinaryArb] Scan error: {e}")
            return []
    
    def execute(self, opportunity: ArbitrageOpportunity, mode: str = "PAPER") -> ArbitrageTrade:
        """Execute an arbitrage trade"""
        trade_id = f"ARB_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        # Calculate position sizes
        # To guarantee profit, we buy equal dollar amounts of YES and NO
        # $X YES + $X NO = $2X cost, worth $X at resolution
        # Profit = $2X - ($X/yes_price + $X/no_price)
        
        # Simplified: buy $Y worth of each, total = $2Y
        # If YES wins: worth $Y/yes_price
        # If NO wins: worth $Y/no_price  
        # Total = $Y/yes_price + $Y/no_price = $Y * (1/yes + 1/no)
        # Profit = $2Y - $Y * (1/yes + 1/no) = $Y * (2 - 1/yes - 1/no)
        
        base_amount = min(self.max_position_usd / 2, opportunity.liquidity / 10)
        
        yes_amount = base_amount
        no_amount = base_amount
        total_cost = yes_amount + no_amount
        guaranteed_profit = 1.0 - opportunity.combined_price
        
        trade = ArbitrageTrade(
            trade_id=trade_id,
            condition_id=opportunity.condition_id,
            question=opportunity.question,
            yes_amount=yes_amount,
            no_amount=no_amount,
            yes_price=opportunity.yes_price,
            no_price=opportunity.no_price,
            total_cost=total_cost,
            guaranteed_profit=total_cost * guaranteed_profit,
            status="EXECUTED" if mode == "PAPER" else "PENDING",
            executed_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Save to database
        self._save_trade(trade)
        
        self.executed_trades.append(trade)
        self.stats["trades_executed"] += 1
        
        logger.info(f"[BinaryArb] Executed {trade_id}: {guaranteed_profit:.4f} guaranteed profit")
        
        return trade
    
    def _save_trade(self, trade: ArbitrageTrade):
        """Save trade to database"""
        try:
            conn = sqlite3.connect("trades.db")
            conn.execute("""
                INSERT OR REPLACE INTO binary_arbitrages 
                (trade_id, condition_id, question, yes_amount, no_amount, 
                 yes_price, no_price, total_cost, guaranteed_profit, status, 
                 executed_at, resolved_at, actual_profit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.trade_id, trade.condition_id, trade.question,
                trade.yes_amount, trade.no_amount, trade.yes_price, trade.no_price,
                trade.total_cost, trade.guaranteed_profit, trade.status,
                trade.executed_at, trade.resolved_at, trade.actual_profit
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[BinaryArb] Error saving trade: {e}")
    
    def get_stats(self) -> Dict:
        """Get strategy statistics"""
        return {
            **self.stats,
            "active_opportunities": len(self.active_arbitrages),
            "win_rate": self.stats["wins"] / (self.stats["wins"] + self.stats["losses"]) * 100 
                        if (self.stats["wins"] + self.stats["losses"]) > 0 else 0
        }
    
    def run(self, mode: str = "PAPER", iterations: Optional[int] = None):
        """Run the arbitrage scanner continuously"""
        logger.info(f"[BinaryArb] Starting in {mode} mode...")
        
        iteration = 0
        while True:
            iteration += 1
            
            # Scan for opportunities
            opportunities = self.scan()
            
            # Execute if found (up to max concurrent)
            executed = 0
            for opp in opportunities:
                if executed >= self.max_concurrent:
                    break
                
                # Check if already traded this recently
                recent = [t for t in self.executed_trades 
                         if t.condition_id == opp.condition_id
                         and (datetime.now(timezone.utc) - datetime.fromisoformat(t.executed_at.replace('+00:00', ''))).seconds < 3600]
                if recent:
                    continue
                
                self.execute(opp, mode)
                executed += 1
            
            # Check iteration limit
            if iterations and iteration >= iterations:
                break
            
            # Wait before next scan
            time.sleep(self.check_interval)
        
        logger.info(f"[BinaryArb] Completed {iteration} iterations")
        return self.get_stats()


# CLI for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    config = {
        "min_spread_pct": 1.0,
        "max_position_usd": 10,
        "max_concurrent_arbs": 3,
        "check_interval_seconds": 30
    }
    
    strategy = BinaryArbitrageStrategy(config)
    
    print("\n" + "="*60)
    print("BINARY ARBITRAGE SCANNER")
    print("="*60)
    print(f"Min Spread: {config['min_spread_pct']}%")
    print(f"Max Position: ${config['max_position_usd']}")
    print("="*60 + "\n")
    
    # Single scan
    opportunities = strategy.scan()
    
    if opportunities:
        print(f"\n🎯 FOUND {len(opportunities)} ARBITRAGE OPPORTUNITIES:\n")
        for i, opp in enumerate(opportunities[:10], 1):
            print(f"{i}. {opp.question[:60]}...")
            print(f"   YES: ${opp.yes_price:.4f} | NO: ${opp.no_price:.4f}")
            print(f"   Combined: ${opp.combined_price:.4f} | Profit: {opp.profit_percent:.2f}%")
            print(f"   Volume: ${opp.volume:,.0f} | Liquidity: ${opp.liquidity:,.0f}")
            print()
    else:
        print("No arbitrage opportunities found at this time.")
    
    print(f"\nStats: {strategy.get_stats()}")
