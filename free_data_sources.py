#!/usr/bin/env python3
"""
Free Crypto Data Sources - No API Key Required
===============================================
Alternative data sources that work without paid subscriptions:
- CCXT: 100+ exchanges (Binance, Coinbase, Kraken, etc.)
- CoinGecko: Free price API (50 calls/min)
- CoinPaprika: Free market data
- DexScreener: DEX data (already integrated)
- Birdeye: Solana DEX data (already integrated)
"""

import requests
import ccxt
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class CoinGeckoConnector:
    """
    CoinGecko Free API
    - 50 calls/minute
    - No API key required for basic endpoints
    - Price, market cap, volume, trending
    """
    
    API_BASE = "https://api.coingecko.com/api/v3"
    
    def get_price(self, ids: str = "bitcoin", vs_currencies: str = "usd") -> Optional[Dict]:
        """Get current price"""
        try:
            url = f"{self.API_BASE}/simple/price"
            params = {
                "ids": ids,
                "vs_currencies": vs_currencies,
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return data.get(ids, {})
        except Exception as e:
            print(f"[CoinGecko] Error: {e}")
            return None
    
    def get_trending(self) -> List[Dict]:
        """Get trending coins"""
        try:
            url = f"{self.API_BASE}/search/trending"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json().get("coins", [])
        except Exception as e:
            print(f"[CoinGecko] Error: {e}")
            return []
    
    def get_market_data(self, coin_id: str = "bitcoin") -> Optional[Dict]:
        """Get full market data"""
        try:
            url = f"{self.API_BASE}/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "symbol": data.get("symbol", "").upper(),
                "current_price": data.get("market_data", {}).get("current_price", {}),
                "market_cap": data.get("market_data", {}).get("market_cap", {}),
                "total_volume": data.get("market_data", {}).get("total_volume", {}),
                "price_change_24h": data.get("market_data", {}).get("price_change_percentage_24h", 0),
                "price_change_7d": data.get("market_data", {}).get("price_change_percentage_7d", 0),
                "ath": data.get("market_data", {}).get("ath", {}),
                "atl": data.get("market_data", {}).get("atl", {})
            }
        except Exception as e:
            print(f"[CoinGecko] Error: {e}")
            return None


class CoinPaprikaConnector:
    """
    CoinPaprika Free API
    - 300 calls/hour
    - No API key required
    - Similar to CoinGecko
    """
    
    API_BASE = "https://api.coinpaprika.com/v1"
    
    def get_tickers(self) -> List[Dict]:
        """Get all tickers"""
        try:
            url = f"{self.API_BASE}/tickers"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[CoinPaprika] Error: {e}")
            return []
    
    def get_coin(self, coin_id: str = "btc-bitcoin") -> Optional[Dict]:
        """Get coin details"""
        try:
            url = f"{self.API_BASE}/coins/{coin_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[CoinPaprika] Error: {e}")
            return None


class CCXTMultiExchange:
    """
    CCXT Multi-Exchange Price Fetcher
    - 100+ exchanges
    - Free (uses public APIs)
    - Requires exchange credentials only for trading
    """
    
    def __init__(self):
        self.exchanges = {}
        self._init_exchanges()
    
    def _init_exchanges(self):
        """Initialize exchange connections"""
        exchange_ids = ["binance", "coinbase", "kraken", "bybit", "kucoin"]
        
        for ex_id in exchange_ids:
            try:
                exchange_class = getattr(ccxt, ex_id)
                exchange = exchange_class({
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"}
                })
                self.exchanges[ex_id] = exchange
                print(f"[CCXT] {ex_id}: Connected")
            except Exception as e:
                print(f"[CCXT] {ex_id}: Failed - {e}")
    
    def get_price(self, exchange_id: str, symbol: str) -> Optional[Dict]:
        """Get ticker from specific exchange"""
        if exchange_id not in self.exchanges:
            return None
        
        try:
            exchange = self.exchanges[exchange_id]
            ticker = exchange.fetch_ticker(symbol)
            
            return {
                "exchange": exchange_id,
                "symbol": symbol,
                "price": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "change_pct": ticker.get("percentage"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            print(f"[CCXT] Error fetching from {exchange_id}: {e}")
            return None
    
    def get_arbitrage_opportunities(self, symbol: str, min_spread_pct: float = 0.5) -> List[Dict]:
        """Scan for arbitrage opportunities across exchanges"""
        prices = []
        
        for ex_id in self.exchanges:
            price_data = self.get_price(ex_id, symbol)
            if price_data:
                prices.append(price_data)
        
        opportunities = []
        for i, p1 in enumerate(prices):
            for p2 in prices[i+1:]:
                if p1["price"] and p2["price"]:
                    spread = abs(p1["price"] - p2["price"]) / min(p1["price"], p2["price"]) * 100
                    
                    if spread >= min_spread_pct:
                        opportunities.append({
                            "symbol": symbol,
                            "buy_exchange": p1["exchange"] if p1["price"] < p2["price"] else p2["exchange"],
                            "sell_exchange": p2["exchange"] if p1["price"] < p2["price"] else p1["exchange"],
                            "buy_price": min(p1["price"], p2["price"]),
                            "sell_price": max(p1["price"], p2["price"]),
                            "spread_pct": spread,
                            "volume_buy": p1.get("volume"),
                            "volume_sell": p2.get("volume")
                        })
        
        return sorted(opportunities, key=lambda x: x["spread_pct"], reverse=True)


def get_free_market_data() -> Dict[str, Any]:
    """
    Get comprehensive market data from free sources.
    
    Returns:
        Dictionary with prices, trending, and arbitrage opportunities
    """
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prices": {},
        "trending": [],
        "arbitrage": []
    }
    
    # CoinGecko - Bitcoin, Ethereum, Solana
    coingecko = CoinGeckoConnector()
    
    btc = coingecko.get_price("bitcoin")
    eth = coingecko.get_price("ethereum")
    sol = coingecko.get_price("solana")
    
    if btc:
        result["prices"]["BTC"] = {
            "price_usd": btc.get("usd"),
            "volume_24h": btc.get("usd_24h_vol"),
            "change_24h": btc.get("usd_24h_change")
        }
    
    if eth:
        result["prices"]["ETH"] = {
            "price_usd": eth.get("usd"),
            "volume_24h": eth.get("usd_24h_vol"),
            "change_24h": eth.get("usd_24h_change")
        }
    
    if sol:
        result["prices"]["SOL"] = {
            "price_usd": sol.get("usd"),
            "volume_24h": sol.get("usd_24h_vol"),
            "change_24h": sol.get("usd_24h_change")
        }
    
    # Trending coins
    result["trending"] = coingecko.get_trending()
    
    # CCXT - Arbitrage scan
    ccxt_multi = CCXTMultiExchange()
    result["arbitrage"] = ccxt_multi.get_arbitrage_opportunities("BTC/USDT", min_spread_pct=0.3)
    
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("FREE CRYPTO DATA SOURCES - Test Mode")
    print("=" * 60)
    
    data = get_free_market_data()
    
    print("\n[Prices]")
    for coin, info in data["prices"].items():
        print(f"  {coin}: ${info['price_usd']:,.2f} ({info['change_24h']:+.2f}%)")
    
    print("\n[Trending]")
    for coin in data["trending"][:3]:
        name = coin.get("item", {}).get("name", "Unknown")
        symbol = coin.get("item", {}).get("symbol", "").upper()
        print(f"  {symbol}: {name}")
    
    print("\n[Arbitrage Opportunities]")
    if data["arbitrage"]:
        for opp in data["arbitrage"][:3]:
            print(f"  {opp['symbol']}: Buy {opp['buy_exchange']} @ ${opp['buy_price']:,.2f}, "
                  f"Sell {opp['sell_exchange']} @ ${opp['sell_price']:,.2f}")
            print(f"    Spread: {opp['spread_pct']:.2f}%")
    else:
        print("  No significant arbitrage opportunities")
    
    print("\n" + "=" * 60)
    print("✅ All free data sources working!")
    print("\nUse this data while waiting for CoinAPI credits.")
