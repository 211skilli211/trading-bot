#!/usr/bin/env python3
"""Performance Monitor Skill Handler"""
import sys
import sqlite3
import json
from datetime import datetime, timedelta

def get_db_connection():
    """Connect to trades database"""
    try:
        conn = sqlite3.connect('/root/trading-bot/trades.db')
        return conn
    except:
        return None

def get_performance_stats():
    """Calculate trading performance"""
    conn = get_db_connection()
    if not conn:
        return {"error": "Database not available"}
    
    try:
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute("SELECT COUNT(*) FROM trades")
        total = cursor.fetchone()[0]
        
        # Today's trades
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM trades WHERE date(timestamp) = ?", (today,))
        today_trades = cursor.fetchone()[0]
        
        # Win/loss
        cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
        wins = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl < 0")
        losses = cursor.fetchone()[0]
        
        # Total P&L
        cursor.execute("SELECT SUM(pnl) FROM trades")
        total_pnl = cursor.fetchone()[0] or 0
        
        # Today's P&L
        cursor.execute("SELECT SUM(pnl) FROM trades WHERE date(timestamp) = ?", (today,))
        today_pnl = cursor.fetchone()[0] or 0
        
        conn.close()
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        return {
            "total_trades": total,
            "today_trades": today_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "today_pnl": today_pnl
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    stats = get_performance_stats()
    
    if "error" in stats:
        print(f"❌ Error: {stats['error']}")
        print("📊 No trading data available yet")
        print()
        print("💡 Start trading in paper mode to generate stats!")
    else:
        print(f"📊 PERFORMANCE REPORT")
        print()
        
        # Overall stats
        pnl_emoji = "📈" if stats["total_pnl"] >= 0 else "📉"
        print(f"💰 Total P&L: ${stats['total_pnl']:,.2f} {pnl_emoji}")
        print(f"📊 Win Rate: {stats['win_rate']:.1f}%")
        print(f"🎯 Total Trades: {stats['total_trades']}")
        print(f"   ✅ Wins: {stats['wins']} | ❌ Losses: {stats['losses']}")
        print()
        
        # Today's activity
        if stats["today_trades"] > 0:
            today_emoji = "📈" if stats["today_pnl"] >= 0 else "📉"
            print(f"📅 TODAY:")
            print(f"   Trades: {stats['today_trades']}")
            print(f"   P&L: ${stats['today_pnl']:,.2f} {today_emoji}")
        else:
            print(f"📅 TODAY: No trades yet")
        
        print()
        
        # Insights
        if stats["total_trades"] > 0:
            if stats["win_rate"] > 60:
                print("💡 Strong performance! Win rate above 60%")
            elif stats["win_rate"] < 40:
                print("⚠️  Low win rate. Consider reviewing strategy")
            else:
                print("💡 Win rate is within normal range")
