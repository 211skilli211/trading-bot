#!/usr/bin/env python3
"""
Birdeye.so API Connector
Best historical OHLCV, volume, liquidity data for Solana tokens.
Free tier available, paid for bulk data.
"""

import requests
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


BIRDEYE_API_BASE = "https://public-api.birdeye.so"


class BirdeyeConnector:
    """
    Birdeye.so API connector for Solana market data.
    
    Features:
    - Historical OHLCV data
    - Token metadata
    - Liquidity information
    - Price history
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Birdeye connector.
        
        Args:
            api_key: Birdeye API key (optional for public endpoints)
        """
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "X-API-KEY": api_key or ""
        }
        print(f"[Birdeye] Initialized")
    
    def get_ohlcv(
        self,
        token_address: str,
        vs_token: str = "So11111111111111111111111111111111111111112",  # SOL
        timeframe: str = "1H",
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        Get OHLCV historical data for a token.
        
        Args:
            token_address: Token mint address
            vs_token: Quote token (default SOL)
            timeframe: 1m, 5m, 15m, 1H, 4H, 1D
            limit: Number of candles (max 1000)
        
        Returns:
            List of OHLCV candles
        """
        try:
            url = f"{BIRDEYE_API_BASE}/defi/ohlcv"
            params = {
                "base_address": token_address,
                "quote_address": vs_token,
                "type": timeframe,
                "limit": limit
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                return data.get("data", {}).get("items", [])
            else:
                print(f"[Birdeye] API error: {data}")
                return None
                
        except Exception as e:
            print(f"[Birdeye] Error fetching OHLCV: {e}")
            return None
    
    def get_token_metadata(self, token_address: str) -> Optional[Dict]:
        """Get token metadata (name, symbol, decimals)."""
        try:
            url = f"{BIRDEYE_API_BASE}/defi/token_meta"
            params = {"address": token_address}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                return data.get("data")
            return None
            
        except Exception as e:
            print(f"[Birdeye] Error fetching metadata: {e}")
            return None
    
    def get_price(self, token_address: str) -> Optional[float]:
        """Get current token price in USD."""
        try:
            url = f"{BIRDEYE_API_BASE}/public/price"
            params = {"address": token_address}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                return data.get("data", {}).get("value")
            return None
            
        except Exception as e:
            print(f"[Birdeye] Error fetching price: {e}")
            return None
    
    def get_top_tokens(self, limit: int = 20) -> Optional[List[Dict]]:
        """Get top traded tokens on Solana."""
        try:
            url = f"{BIRDEYE_API_BASE}/defi/token_trending"
            params = {"limit": limit, "offset": 0}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                return data.get("data", {}).get("items", [])
            return None
            
        except Exception as e:
            print(f"[Birdeye] Error fetching trending: {e}")
            return None


if __name__ == "__main__":
    print("Birdeye Connector - Test Mode")
    print("=" * 60)
    
    birdeye = BirdeyeConnector()
    
    # Test price fetch
    print("\n[Test 1] Get SOL price")
    sol_price = birdeye.get_price("So11111111111111111111111111111111111111112")
    if sol_price:
        print(f"  SOL: ${sol_price:.2f}")
    
    # Test OHLCV
    print("\n[Test 2] Get SOL/USDC OHLCV (24h)")
    ohlcv = birdeye.get_ohlcv(
        "So11111111111111111111111111111111111111112",
        vs_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        timeframe="1H",
        limit=24
    )
    if ohlcv:
        print(f"  Fetched {len(ohlcv)} candles")
        print(f"  Latest: O:{ohlcv[-1]['o']:.2f} H:{ohlcv[-1]['h']:.2f} L:{ohlcv[-1]['l']:.2f} C:{ohlcv[-1]['c']:.2f}")
    
    # Test trending
    print("\n[Test 3] Top trending tokens")
    trending = birdeye.get_top_tokens(limit=5)
    if trending:
        for token in trending:
            print(f"  {token.get('symbol')}: ${token.get('price', 0):.4f}")
