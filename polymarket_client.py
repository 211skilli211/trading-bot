#!/usr/bin/env python3
"""
PolyMarket API Client
=====================
Handles all interactions with PolyMarket API for binary options trading.

API Documentation: https://docs.polymarket.com/
Public endpoints: https://gamma-api.polymarket.com/markets (no auth required)
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# PolyMarket API Endpoints (Updated)
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


@dataclass
class BinaryMarket:
    """Represents a binary outcome market"""
    condition_id: str
    question: str
    slug: str
    clob_token_ids: List[str]  # [yes_token, no_token]
    yes_token: str
    no_token: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: float
    end_date: Optional[str]
    resolved: bool
    outcome: Optional[str]
    
    @property
    def combined_price(self) -> float:
        """Combined price of YES + NO - arbitrage opportunity if < $1.00"""
        return self.yes_price + self.no_price
    
    @property
    def arbitrage_percent(self) -> float:
        """Potential arbitrage profit percentage"""
        return max(0, (1.0 - self.combined_price) * 100)
    
    @property
    def is_arbitrageable(self) -> bool:
        """Check if arbitrage opportunity exists"""
        return self.combined_price < 0.99 and not self.resolved


class PolyMarketClient:
    """Client for interacting with PolyMarket API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
        })
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
    
    def get_markets(self, limit: int = 100, active: bool = True, closed: bool = False) -> List[Dict]:
        """Get list of markets from gamma-api (public, no auth needed)"""
        try:
            response = self.session.get(
                f"{GAMMA_API}/markets",
                params={
                    "active": str(active).lower(),
                    "closed": str(closed).lower(),
                    "limit": limit
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    def get_market_by_slug(self, slug: str) -> Optional[Dict]:
        """Get specific market by slug"""
        try:
            response = self.session.get(
                f"{GAMMA_API}/markets",
                params={"slug": slug},
                timeout=30
            )
            response.raise_for_status()
            markets = response.json()
            return markets[0] if markets else None
        except Exception as e:
            logger.error(f"Error fetching market {slug}: {e}")
            return None
    
    def get_market(self, condition_id: str) -> Optional[Dict]:
        """Get specific market by condition ID"""
        try:
            response = self.session.get(
                f"{GAMMA_API}/markets/{condition_id}",
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching market {condition_id}: {e}")
        return None
    
    def get_price(self, condition_id: str, outcome: str = "yes") -> Optional[float]:
        """Get current price for YES or NO outcome"""
        try:
            # Try market data first
            market = self.get_market(condition_id)
            if market:
                if outcome == "yes":
                    return float(market.get("yesPrice", 0))
                else:
                    return float(market.get("noPrice", 0))
        except Exception as e:
            logger.error(f"Error getting price: {e}")
        return None
    
    def get_binary_markets(self, min_liquidity: float = 1000) -> List[BinaryMarket]:
        """Get binary markets with arbitrage potential"""
        markets = []
        try:
            data = self.get_markets(limit=200, active=True, closed=False)
            
            for m in data:
                yes_price = float(m.get("yesPrice", 0) or 0)
                no_price = float(m.get("noPrice", 0) or 0)
                liquidity = float(m.get("liquidity", 0) or 0)
                volume = float(m.get("volume", 0) or 0)
                
                # Only include markets with meaningful liquidity
                if liquidity < min_liquidity:
                    continue
                
                if yes_price == 0 or no_price == 0:
                    continue
                
                clob_token_ids = m.get("clobTokenIds", [])
                
                market = BinaryMarket(
                    condition_id=m.get("conditionId", ""),
                    question=m.get("question", ""),
                    slug=m.get("slug", ""),
                    clob_token_ids=clob_token_ids,
                    yes_token=clob_token_ids[0] if len(clob_token_ids) > 0 else "",
                    no_token=clob_token_ids[1] if len(clob_token_ids) > 1 else "",
                    yes_price=yes_price,
                    no_price=no_price,
                    volume=volume,
                    liquidity=liquidity,
                    end_date=m.get("endDate"),
                    resolved=m.get("closed", False),
                    outcome=m.get("outcome")
                )
                markets.append(market)
            
            # Sort by arbitrage potential
            markets.sort(key=lambda x: x.arbitrage_percent, reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting binary markets: {e}")
        
        return markets
    
    def find_arbitrage_opportunities(self, min_spread: float = 0.5) -> List[BinaryMarket]:
        """Find markets where YES + NO < $1.00 (arbitrage opportunity)"""
        all_markets = self.get_binary_markets()
        opportunities = []
        
        for market in all_markets:
            if market.is_arbitrageable and market.arbitrage_percent >= min_spread:
                opportunities.append(market)
        
        return opportunities
    
    def get_trending_markets(self, limit: int = 10) -> List[Dict]:
        """Get trending markets by volume"""
        try:
            response = self.session.get(
                f"{GAMMA_API}/markets",
                params={"limit": limit, "closed": "false"},
                timeout=30
            )
            response.raise_for_status()
            markets = response.json()
            
            # Sort by volume
            markets.sort(key=lambda x: float(x.get("volume", 0) or 0), reverse=True)
            return markets[:limit]
        except Exception as e:
            logger.error(f"Error fetching trending markets: {e}")
            return []


# Helper function to get current prices (no API key needed)
def get_quick_price(condition_id: str, outcome: str = "yes") -> Optional[float]:
    """Quick price check without full client initialization"""
    client = PolyMarketClient()
    return client.get_price(condition_id, outcome)


# Test function
if __name__ == "__main__":
    print("Testing PolyMarket Client...")
    client = PolyMarketClient()
    
    # Get trending markets
    print("\n📊 Fetching trending markets...")
    trending = client.get_trending_markets(limit=5)
    print(f"Found {len(trending)} trending markets")
    
    for m in trending:
        print(f"  - {m.get('question', '')[:50]}...")
        print(f"    Volume: ${float(m.get('volume', 0) or 0):,.0f}")
    
    # Get some markets
    print("\n📊 Fetching markets...")
    markets = client.get_binary_markets(min_liquidity=1000)
    print(f"Found {len(markets)} markets with $1000+ liquidity")
    
    # Show top arbitrage opportunities
    print("\n🎯 Top Arbitrage Opportunities:")
    arbs = client.find_arbitrage_opportunities(min_spread=0.5)[:5]
    for arb in arbs:
        print(f"  {arb.question[:60]}...")
        print(f"    YES: ${arb.yes_price:.4f} | NO: ${arb.no_price:.4f}")
        print(f"    Combined: ${arb.combined_price:.4f} | Spread: {arb.arbitrage_percent:.2f}%")
        print()
