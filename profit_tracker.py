#!/usr/bin/env python3
"""
Real-time Profit Tracker
Shows daily/weekly/monthly earnings
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict

class ProfitTracker:
    """Track trading profits in real-time"""
    
    def __init__(self, db_path='trades.db'):
        self.db_path = db_path
    
    def get_profit_summary(self) -> Dict:
        """Get comprehensive profit summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        summary = {
            'today': {'pnl': 0, 'trades': 0},
            'week': {'pnl': 0, 'trades': 0},
            'month': {'pnl': 0, 'trades': 0},
            'all_time': {'pnl': 0, 'trades': 0}
        }
        
        try:
            # Today
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute(
                "SELECT SUM(net_pnl), COUNT(*) FROM trades WHERE date(timestamp) = ?",
                (today,)
            )
            result = cursor.fetchone()
            summary['today']['pnl'] = result[0] or 0
            summary['today']['trades'] = result[1] or 0
            
            # This week
            week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            cursor.execute(
                "SELECT SUM(net_pnl), COUNT(*) FROM trades WHERE date(timestamp) >= ?",
                (week_start,)
            )
            result = cursor.fetchone()
            summary['week']['pnl'] = result[0] or 0
            summary['week']['trades'] = result[1] or 0
            
            # This month
            month_start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            cursor.execute(
                "SELECT SUM(net_pnl), COUNT(*) FROM trades WHERE date(timestamp) >= ?",
                (month_start,)
            )
            result = cursor.fetchone()
            summary['month']['pnl'] = result[0] or 0
            summary['month']['trades'] = result[1] or 0
            
            # All time
            cursor.execute("SELECT SUM(net_pnl), COUNT(*) FROM trades")
            result = cursor.fetchone()
            summary['all_time']['pnl'] = result[0] or 0
            summary['all_time']['trades'] = result[1] or 0
            
        except Exception as e:
            print(f"[ProfitTracker] Error: {e}")
        
        conn.close()
        return summary
    
    def print_report(self):
        """Print profit report"""
        profits = self.get_profit_summary()
        
        print("\n" + "=" * 60)
        print("💰 PROFIT TRACKER")
        print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        periods = [
            ('TODAY', 'today'),
            ('THIS WEEK', 'week'),
            ('THIS MONTH', 'month'),
            ('ALL TIME', 'all_time')
        ]
        
        for label, key in periods:
            data = profits[key]
            pnl = data['pnl']
            trades = data['trades']
            emoji = "🟢" if pnl >= 0 else "🔴"
            
            print(f"\n{emoji} {label}")
            print(f"   P&L:    ${pnl:+.2f}")
            print(f"   Trades: {trades}")
            if trades > 0:
                avg = pnl / trades
                print(f"   Avg:    ${avg:+.2f}/trade")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    tracker = ProfitTracker()
    tracker.print_report()
