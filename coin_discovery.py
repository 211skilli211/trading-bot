#!/usr/bin/env python3
"""
Coin Discovery Module
=====================
Discovers new coins with potential using multiple sources:
- CoinGecko: Trending, new listings, top gainers
- Binance: New listings, top volume
- DEXScreener: Emerging tokens, pump detection

Usage:
    from coin_discovery import CoinDiscovery
    
    discovery = CoinDiscovery()
    
    # Find trending coins
    trending = discovery.get_trending()
    
    # Find new listings
    new_coins = discovery.get_new_listings()
    
    # Find top gainers (potential opportunities)
    gainers = discovery.get_top_gainers()
"""

import requests
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class DiscoveredCoin:
    """Represents a discovered cryptocurrency"""
    symbol: str
    name: str
    source: str  # 'coingecko', 'binance', 'dexscreener'
    price_usd: float
    market_cap: Optional[float]
    volume_24h: Optional[float]
    price_change_24h: Optional[float]
    price_change_7d: Optional[float]
    reason: str  # Why it was discovered (trending, new listing, gainer, etc.)
    icon_url: Optional[str]
    discovered_at: str
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "source": self.source,
            "price_usd": self.price_usd,
            "market_cap": self.market_cap,
            "volume_24h": self.volume_24h,
            "price_change_24h": self.price_change_24h,
            "price_change_7d": self.price_change_7d,
            "reason": self.reason,
            "icon_url": self.icon_url,
            "discovered_at": self.discovered_at
        }


class CoinDiscovery:
    """Discovers cryptocurrencies with potential"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "211Skilli-Trading-Bot/1.0"
        })
    
    def get_trending(self) -> List[DiscoveredCoin]:
        """Get trending coins from CoinGecko"""
        coins = []
        try:
            resp = self.session.get(
                "https://api.coingecko.com/api/v3/search/trending",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("coins", [])[:10]:
                    coin = item.get("item", {})
                    coins.append(DiscoveredCoin(
                        symbol=coin.get("symbol", "").upper(),
                        name=coin.get("name", ""),
                        source="coingecko",
                        price_usd=coin.get("data", {}).get("price", 0),
                        market_cap=coin.get("data", {}).get("market_cap"),
                        volume_24h=coin.get("data", {}).get("total_volume"),
                        price_change_24h=coin.get("data", {}).get("price_change_percentage_24h", {}).get("usd"),
                        price_change_7d=None,
                        reason="trending",
                        icon_url=coin.get("thumb") or coin.get("small"),
                        discovered_at=datetime.now(timezone.utc).isoformat()
                    ))
        except Exception as e:
            print(f"[CoinDiscovery] Trending error: {e}")
        return coins
    
    def get_top_gainers(self, limit: int = 20) -> List[DiscoveredCoin]:
        """Get top gaining coins (24h)"""
        coins = []
        try:
            resp = self.session.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "price_change_percentage_24h_desc",
                    "per_page": limit,
                    "page": 1
                },
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for coin in data:
                    change = coin.get("price_change_percentage_24h", 0)
                    if change > 10:  # Only significant gainers
                        coins.append(DiscoveredCoin(
                            symbol=coin.get("symbol", "").upper(),
                            name=coin.get("name", ""),
                            source="coingecko",
                            price_usd=coin.get("current_price", 0),
                            market_cap=coin.get("market_cap"),
                            volume_24h=coin.get("total_volume"),
                            price_change_24h=change,
                            price_change_7d=coin.get("price_change_percentage_7d_in_currency"),
                            reason=f"top_gainer_24h (+{change:.1f}%)",
                            icon_url=coin.get("image"),
                            discovered_at=datetime.now(timezone.utc).isoformat()
                        ))
        except Exception as e:
            print(f"[CoinDiscovery] Gainers error: {e}")
        return coins
    
    def get_new_listings(self) -> List[DiscoveredCoin]:
        """Get newly listed coins on Binance"""
        coins = []
        try:
            resp = self.session.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                # Sort by quote volume to find new/active coins
                sorted_coins = sorted(
                    [c for c in data if c.get("count", 0) < 1000],  # Low count = newer
                    key=lambda x: float(x.get("quoteVolume", 0)),
                    reverse=True
                )[:10]
                
                for coin in sorted_coins:
                    symbol = coin.get("symbol", "").replace("USDT", "")
                    if len(symbol) <= 5:  # Likely a coin, not a complex pair
                        coins.append(DiscoveredCoin(
                            symbol=symbol,
                            name=symbol,
                            source="binance",
                            price_usd=float(coin.get("lastPrice", 0)),
                            market_cap=None,
                            volume_24h=float(coin.get("volume", 0)),
                            price_change_24h=float(coin.get("priceChangePercent", 0)),
                            price_change_7d=None,
                            reason="new_listing_binance",
                            icon_url=None,
                            discovered_at=datetime.now(timezone.utc).isoformat()
                        ))
        except Exception as e:
            print(f"[CoinDiscovery] New listings error: {e}")
        return coins
    
    def get_high_potential(self) -> List[DiscoveredCoin]:
        """Get coins with high potential (low cap, high volume growth)"""
        coins = []
        try:
            resp = self.session.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_asc",
                    "per_page": 50,
                    "page": 1
                },
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for coin in data:
                    mc = coin.get("market_cap", 0) or 0
                    vol = coin.get("total_volume", 0) or 0
                    change = coin.get("price_change_percentage_24h", 0) or 0
                    
                    # High potential: Small cap ($10M-$500M) + high volume + positive momentum
                    if 10_000_000 < mc < 500_000_000 and vol > mc * 0.1 and change > 5:
                        coins.append(DiscoveredCoin(
                            symbol=coin.get("symbol", "").upper(),
                            name=coin.get("name", ""),
                            source="coingecko",
                            price_usd=coin.get("current_price", 0),
                            market_cap=mc,
                            volume_24h=vol,
                            price_change_24h=change,
                            price_change_7d=coin.get("price_change_percentage_7d_in_currency"),
                            reason="high_potential_small_cap",
                            icon_url=coin.get("image"),
                            discovered_at=datetime.now(timezone.utc).isoformat()
                        ))
        except Exception as e:
            print(f"[CoinDiscovery] High potential error: {e}")
        return coins[:10]
    
    def get_coin_icon_url(self, symbol: str) -> Optional[str]:
        """Get icon URL for a coin symbol from CoinGecko"""
        try:
            resp = self.session.get(
                f"https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "ids": symbol.lower(),
                    "per_page": 1
                },
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0].get("image")
        except:
            pass
        
        # Fallback to CryptoIcons
        return f"https://cryptoicons.org/api/icon/{symbol.lower()}/200"
    
    def scan_all(self) -> Dict:
        """Run all discovery methods"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trending": [c.to_dict() for c in self.get_trending()],
            "top_gainers": [c.to_dict() for c in self.get_top_gainers()],
            "new_listings": [c.to_dict() for c in self.get_new_listings()],
            "high_potential": [c.to_dict() for c in self.get_high_potential()]
        }


if __name__ == "__main__":
    print("Testing Coin Discovery...\n")
    
    discovery = CoinDiscovery()
    
    print("=== Trending Coins ===")
    for coin in discovery.get_trending()[:5]:
        print(f"  {coin.symbol}: {coin.name} (${coin.price_usd:,.4f}) - {coin.reason}")
    
    print("\n=== Top Gainers ===")
    for coin in discovery.get_top_gainers(5):
        print(f"  {coin.symbol}: +{coin.price_change_24h:.1f}% (${coin.price_usd:,.4f})")
    
    print("\n=== High Potential ===")
    for coin in discovery.get_high_potential()[:5]:
        print(f"  {coin.symbol}: MC ${coin.market_cap/1e6:.1f}M | Vol ${coin.volume_24h/1e6:.1f}M | +{coin.price_change_24h:.1f}%")
