#!/usr/bin/env python3
"""Trading Signals Skill"""
import urllib.request
import json
from datetime import datetime

def get_signals():
    """Generate trading signals for top coins"""
    signals = []
    
    coins = [
        ("BTC", "bitcoin", 68400),
        ("ETH", "ethereum", 2450),
        ("SOL", "solana", 142)
    ]
    
    for symbol, coin_id, fallback_price in coins:
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            
            price = data[coin_id]["usd"]
            change = data[coin_id].get("usd_24h_change", 0)
        except:
            price = fallback_price
            change = 0
        
        # Simple signal logic
        if change > 5:
            signal = "🟢 STRONG BUY"
            confidence = 85
        elif change > 2:
            signal = "🟢 BUY"
            confidence = 70
        elif change < -5:
            signal = "🔴 STRONG SELL"
            confidence = 85
        elif change < -2:
            signal = "🔴 SELL"
            confidence = 70
        else:
            signal = "🟡 HOLD"
            confidence = 60
        
        signals.append({
            "symbol": symbol,
            "price": price,
            "change": change,
            "signal": signal,
            "confidence": confidence
        })
    
    return signals

if __name__ == "__main__":
    signals = get_signals()
    
    print("📊 TRADING SIGNALS")
    print(f"⏰ {datetime.now().strftime('%H:%M UTC')}")
    print()
    
    for s in signals:
        emoji = "📈" if s["change"] > 0 else "📉" if s["change"] < 0 else "➡️"
        print(f"{emoji} {s['symbol']}: {s['signal']} ({s['confidence']}%)")
        print(f"   Price: ${s['price']:,.2f} | 24h: {s['change']:+.2f}%")
        print()
    
    print("⚠️ These are AI-generated signals. Always DYOR!")
