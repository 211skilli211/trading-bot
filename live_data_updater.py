#!/usr/bin/env python3
"""Live data updater for dashboard"""

import json
import requests
import sqlite3
from datetime import datetime

def update_dashboard_data():
    """Fetch live data and update dashboard cache"""
    
    # Fetch live prices
    prices = []
    try:
        # CoinGecko
        cg = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true", timeout=5).json()
        for coin, data in cg.items():
            prices.append({
                "exchange": "CoinGecko",
                "symbol": coin.upper()[:3],
                "price": data["usd"],
                "change24h": data.get("usd_24h_change", 0),
                "volume24h": 0,
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        print(f"CG Error: {e}")
    
    try:
        # Binance
        for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
            bn = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=5).json()
            prices.append({
                "exchange": "Binance",
                "symbol": symbol.replace("USDT", ""),
                "price": float(bn["lastPrice"]),
                "change24h": float(bn["priceChangePercent"]),
                "volume24h": float(bn["volume"]),
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        print(f"BN Error: {e}")
    
    # Update price cache file
    with open('/tmp/price_cache.json', 'w') as f:
        json.dump(prices, f)
    
    print(f"✅ Updated {len(prices)} price feeds")
    return prices

if __name__ == "__main__":
    update_dashboard_data()
