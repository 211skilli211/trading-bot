#!/usr/bin/env python3
"""Enhance dashboard with live data from ZeroClaw bots and exchanges"""

import json
import sqlite3
import requests
from datetime import datetime

def get_live_prices():
    """Fetch live prices from 5 exchanges"""
    prices = []
    
    # CoinGecko
    try:
        cg = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true", timeout=5).json()
        for coin, data in cg.items():
            prices.append({
                "exchange": "CoinGecko",
                "symbol": coin.upper(),
                "price": data["usd"],
                "change24h": data.get("usd_24h_change", 0),
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        print(f"CG error: {e}")
    
    # Binance
    try:
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
        print(f"BN error: {e}")
    
    return prices

def get_zeroclaw_status():
    """Get ZeroClaw bot status"""
    status = {"personal": {"running": False}, "trading": {"running": False}}
    
    try:
        r = requests.get("http://127.0.0.1:3000/health", timeout=2)
        if r.status_code == 200:
            status["personal"] = {"running": True, **r.json()}
    except:
        pass
    
    try:
        r = requests.get("http://127.0.0.1:3001/health", timeout=2)
        if r.status_code == 200:
            status["trading"] = {"running": True, **r.json()}
    except:
        pass
    
    return status

def calculate_portfolio_metrics():
    """Calculate real portfolio metrics from database"""
    try:
        conn = sqlite3.connect("trades.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get all trades
        c.execute("SELECT * FROM trades ORDER BY timestamp DESC")
        trades = [dict(row) for row in c.fetchall()]
        
        # Get open positions
        c.execute("SELECT * FROM positions WHERE status='OPEN'")
        positions = [dict(row) for row in c.fetchall()]
        
        # Calculate PnL
        total_pnl = sum(t.get("net_pnl", 0) for t in trades if t.get("net_pnl"))
        winning_trades = len([t for t in trades if t.get("net_pnl", 0) > 0])
        total_trades = len(trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate daily PnL
        c.execute("SELECT SUM(net_pnl) FROM trades WHERE date(timestamp) = date('now')")
        daily_pnl = c.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "trades": trades,
            "positions": positions,
            "total_pnl": total_pnl,
            "daily_pnl": daily_pnl,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "winning_trades": winning_trades
        }
    except Exception as e:
        print(f"DB error: {e}")
        return {"trades": [], "positions": [], "total_pnl": 0, "daily_pnl": 0, "win_rate": 0}

if __name__ == "__main__":
    data = {
        "prices": get_live_prices(),
        "zeroclaw": get_zeroclaw_status(),
        "portfolio": calculate_portfolio_metrics(),
        "timestamp": datetime.now().isoformat()
    }
    print(json.dumps(data, indent=2))
