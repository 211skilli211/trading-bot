#!/usr/bin/env python3
"""
Quick bot status check with analytics
"""

from performance_analytics import get_analytics
from datetime import datetime
import sqlite3

def main():
    print("=" * 60)
    print("🤖 211SKILLI BOT STATUS")
    print("=" * 60)
    
    # Get analytics
    analytics = get_analytics()
    
    print("\n📊 LAST 24 HOURS:")
    print("-" * 60)
    daily = analytics.calculate_metrics(days=1)
    print(f"  Trades:     {daily['total_trades']}")
    print(f"  Win Rate:   {daily['win_rate']:.1f}%")
    print(f"  P&L:        ${daily['total_pnl']:.2f}")
    
    print("\n📊 LAST 7 DAYS:")
    print("-" * 60)
    weekly = analytics.calculate_metrics(days=7)
    print(f"  Trades:     {weekly['total_trades']}")
    print(f"  Win Rate:   {weekly['win_rate']:.1f}%")
    print(f"  P&L:        ${weekly['total_pnl']:.2f}")
    print(f"  Profit Factor: {weekly['profit_factor']:.2f}")
    
    print("\n📊 LAST 30 DAYS:")
    print("-" * 60)
    monthly = analytics.calculate_metrics(days=30)
    print(f"  Trades:     {monthly['total_trades']}")
    print(f"  Win Rate:   {monthly['win_rate']:.1f}%")
    print(f"  P&L:        ${monthly['total_pnl']:.2f}")
    
    # Check database
    print("\n🗄️  DATABASE STATUS:")
    print("-" * 60)
    try:
        conn = sqlite3.connect('trades.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM trades")
        total = cursor.fetchone()[0]
        print(f"  Total trades logged: {total}")
        
        cursor.execute("SELECT COUNT(*) FROM positions WHERE status='OPEN'")
        open_pos = cursor.fetchone()[0]
        print(f"  Open positions: {open_pos}")
        
        cursor.execute("SELECT SUM(net_pnl) FROM trades")
        result = cursor.fetchone()[0]
        total_pnl = result if result else 0.0
        print(f"  Total P&L: ${total_pnl:.2f}")
        
        conn.close()
    except Exception as e:
        print(f"  Database error: {e}")
    
    print("\n" + "=" * 60)
    print(f"Checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
