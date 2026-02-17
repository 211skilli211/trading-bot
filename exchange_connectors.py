#!/usr/bin/env python3
"""
Extended Exchange Connectors
Adds Kraken, Bybit, and KuCoin to the Data Layer
"""

import requests
import base64
import hashlib
import hmac
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class KrakenConnector:
    """Kraken API connector."""
    
    API_BASE = "https://api.kraken.com"
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.name = "Kraken"
        self.api_key = api_key
        self.api_secret = api_secret
    
    def fetch_price(self, symbol: str = "XXBTZUSD") -> Optional[Dict[str, Any]]:
        """Fetch ticker price from Kraken."""
        try:
            endpoint = f"{self.API_BASE}/0/public/Ticker"
            params = {"pair": symbol}
            
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("error"):
                print(f"[Kraken] API Error: {data['error']}")
                return None
            
            result = data["result"][symbol]
            
            return {
                "exchange": self.name,
                "symbol": symbol,
                "price": float(result["c"][0]),  # Last trade closed price
                "bid": float(result["b"][0]),     # Best bid
                "ask": float(result["a"][0]),     # Best ask
                "volume_24h": float(result["v"][1]),  # 24h volume
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_response": result
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[Kraken] Error fetching price: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"[Kraken] Error parsing response: {e}")
            return None


class BybitConnector:
    """Bybit API connector."""
    
    API_BASE = "https://api.bybit.com"
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.name = "Bybit"
        self.api_key = api_key
        self.api_secret = api_secret
    
    def fetch_price(self, symbol: str = "BTCUSDT") -> Optional[Dict[str, Any]]:
        """Fetch ticker price from Bybit."""
        try:
            endpoint = f"{self.API_BASE}/v5/market/tickers"
            params = {"category": "spot", "symbol": symbol}
            
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("retCode") != 0:
                print(f"[Bybit] API Error: {data.get('retMsg')}")
                return None
            
            ticker = data["result"]["list"][0]
            
            return {
                "exchange": self.name,
                "symbol": symbol,
                "price": float(ticker["lastPrice"]),
                "bid": float(ticker["bid1Price"]),
                "ask": float(ticker["ask1Price"]),
                "volume_24h": float(ticker["volume24h"]),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_response": ticker
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[Bybit] Error fetching price: {e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            print(f"[Bybit] Error parsing response: {e}")
            return None


class KuCoinConnector:
    """KuCoin API connector."""
    
    API_BASE = "https://api.kucoin.com"
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, passphrase: Optional[str] = None):
        self.name = "KuCoin"
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
    
    def fetch_price(self, symbol: str = "BTC-USDT") -> Optional[Dict[str, Any]]:
        """Fetch ticker price from KuCoin."""
        try:
            endpoint = f"{self.API_BASE}/api/v1/market/orderbook/level1"
            params = {"symbol": symbol}
            
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("data"):
                print(f"[KuCoin] No data in response")
                return None
            
            ticker = data["data"]
            
            return {
                "exchange": self.name,
                "symbol": symbol,
                "price": float(ticker["price"]),
                "bid": float(ticker["bestBid"]),
                "ask": float(ticker["bestAsk"]),
                "volume_24h": float(ticker.get("volValue", 0)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_response": ticker
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[KuCoin] Error fetching price: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"[KuCoin] Error parsing response: {e}")
            return None


class MultiExchangeConnector:
    """Connect to multiple exchanges and aggregate prices."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.connectors = {}
        self._init_connectors()
    
    def _init_connectors(self):
        """Initialize all exchange connectors."""
        enabled = self.config.get("exchanges", {}).get("enabled", ["binance", "coinbase"])
        
        if "kraken" in enabled:
            self.connectors["kraken"] = KrakenConnector()
        if "bybit" in enabled:
            self.connectors["bybit"] = BybitConnector()
        if "kucoin" in enabled:
            self.connectors["kucoin"] = KuCoinConnector()
        
        print(f"[MultiExchange] Initialized {len(self.connectors)} additional connectors")
    
    def fetch_all_prices(self) -> list:
        """Fetch prices from all enabled exchanges."""
        prices = []
        
        symbol_mapping = {
            "kraken": "XXBTZUSD",
            "bybit": "BTCUSDT",
            "kucoin": "BTC-USDT"
        }
        
        for name, connector in self.connectors.items():
            print(f"[MultiExchange] Fetching from {name}...")
            symbol = symbol_mapping.get(name, "BTCUSDT")
            data = connector.fetch_price(symbol)
            if data:
                prices.append(data)
        
        return prices


if __name__ == "__main__":
    print("Extended Exchange Connectors - Test Mode")
    print("=" * 60)
    
    # Test Kraken
    print("\n[Test 1] Kraken")
    kraken = KrakenConnector()
    data = kraken.fetch_price("XXBTZUSD")
    if data:
        print(f"  Price: ${data['price']:,.2f}")
        print(f"  Bid: ${data['bid']:,.2f}")
        print(f"  Ask: ${data['ask']:,.2f}")
    
    # Test Bybit
    print("\n[Test 2] Bybit")
    bybit = BybitConnector()
    data = bybit.fetch_price("BTCUSDT")
    if data:
        print(f"  Price: ${data['price']:,.2f}")
        print(f"  Bid: ${data['bid']:,.2f}")
        print(f"  Ask: ${data['ask']:,.2f}")
    
    # Test KuCoin
    print("\n[Test 3] KuCoin")
    kucoin = KuCoinConnector()
    data = kucoin.fetch_price("BTC-USDT")
    if data:
        print(f"  Price: ${data['price']:,.2f}")
        print(f"  Bid: ${data['bid']:,.2f}")
        print(f"  Ask: ${data['ask']:,.2f}")
    
    # Test Multi-connector
    print("\n[Test 4] Multi-Exchange Connector")
    multi = MultiExchangeConnector({"exchanges": {"enabled": ["kraken", "bybit", "kucoin"]}})
    prices = multi.fetch_all_prices()
    print(f"  Fetched from {len(prices)} exchanges")
