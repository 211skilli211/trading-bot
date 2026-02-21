#!/usr/bin/env python3
"""Price Check Skill Handler"""
import sys
import json
import requests

SYMBOL_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ADA": "cardano",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "AAVE": "aave",
    "SNX": "synthetix",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "ATOM": "cosmos",
    "LTC": "litecoin",
}

def get_price(symbol):
    """Fetch price from CoinGecko with detailed info"""
    try:
        coin_id = SYMBOL_MAP.get(symbol.upper(), symbol.lower())
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if "market_data" in data:
            mkt = data["market_data"]
            return {
                "success": True,
                "price": mkt["current_price"]["usd"],
                "change_24h": mkt["price_change_percentage_24h"] or 0,
                "high_24h": mkt["high_24h"]["usd"],
                "low_24h": mkt["low_24h"]["usd"],
                "market_cap": mkt["market_cap"]["usd"],
                "volume_24h": mkt["total_volume"]["usd"],
                "circulating_supply": mkt["circulating_supply"],
                "ath": mkt["ath"]["usd"],
                "ath_change": mkt["ath_change_percentage"]["usd"],
                "symbol": symbol,
                "name": data.get("name", symbol)
            }
        
        return {"success": False, "error": f"No market data for {symbol}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Read input from ZeroClaw
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = sys.stdin.read().strip()
    
    # Extract symbol from query (e.g., "price of BTC" -> "BTC")
    words = query.upper().split()
    symbol = None
    
    for word in words:
        if word in SYMBOL_MAP:
            symbol = word
            break
    
    if not symbol and len(words) > 0:
        # Last word might be the symbol
        symbol = words[-1].replace("?", "").replace(".", "")
    
    if symbol:
        result = get_price(symbol)
        if result["success"]:
            change = result["change_24h"]
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            
            print(f"💰 {result['name']} ({symbol})")
            print(f"Current Price: ${result['price']:,.2f}")
            print(f"24h Change: {change_str}")
            print(f"24h Range: ${result['low_24h']:,.2f} - ${result['high_24h']:,.2f}")
            print(f"Market Cap: ${result['market_cap']/1e12:.2f}T")
            print(f"Volume: ${result['volume_24h']/1e9:.1f}B")
            print(f"Circulating Supply: {result['circulating_supply']/1e6:.2f}M {symbol}")
            print(f"ATH: ${result['ath']:,.2f} (down {result['ath_change']:.1f}%)")
        else:
            print(f"Error: {result['error']}")
    else:
        print("Please specify a cryptocurrency symbol (e.g., 'price of BTC')")
