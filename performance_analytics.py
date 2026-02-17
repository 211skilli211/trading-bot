#!/usr/bin/env python3
"""
Performance Analytics Module for 211Skilli Trading Bot
Tracks P&L, win rate, Sharpe ratio, and generates reports
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics

@dataclass
class TradeStats:
    """Statistics for a single trade"""
    trade_id: str
    timestamp: datetime
    symbol: str
    side: str  # BUY or SELL
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_percent: float
    duration_minutes: float

class PerformanceAnalytics:
    """
    Track and analyze trading performance
    """
    
    def __init__(self, db_path: str = "trades.db", log_path: str = "trading_bot.log"):
        self.db_path = db_path
        self.log_path = log_path
        self.stats_cache = {}
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database tables exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                exchange TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                pnl REAL,
                pnl_percent REAL,
                fees REAL,
                net_pnl REAL,
                status TEXT,
                mode TEXT
            )
        ''')
        
        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                total_pnl REAL,
                win_rate REAL,
                avg_win REAL,
                avg_loss REAL,
                profit_factor REAL,
                sharpe_ratio REAL,
                max_drawdown REAL
            )
        ''')
        
        # Daily summary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                starting_balance REAL,
                ending_balance REAL,
                total_pnl REAL,
                num_trades INTEGER,
                best_trade REAL,
                worst_trade REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_trade(self, trade_data: Dict):
        """Log a trade to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO trades 
                (trade_id, timestamp, symbol, side, exchange, entry_price, exit_price, 
                 quantity, pnl, pnl_percent, fees, net_pnl, status, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('trade_id'),
                trade_data.get('timestamp'),
                trade_data.get('symbol'),
                trade_data.get('side'),
                trade_data.get('exchange'),
                trade_data.get('entry_price'),
                trade_data.get('exit_price'),
                trade_data.get('quantity'),
                trade_data.get('pnl'),
                trade_data.get('pnl_percent'),
                trade_data.get('fees'),
                trade_data.get('net_pnl'),
                trade_data.get('status'),
                trade_data.get('mode', 'PAPER')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[Analytics] Error logging trade: {e}")
            return False
    
    def get_trades(self, days: int = 30, mode: Optional[str] = None) -> List[Dict]:
        """Get trades from last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        if mode:
            cursor.execute('''
                SELECT * FROM trades 
                WHERE timestamp > ? AND mode = ?
                ORDER BY timestamp DESC
            ''', (since, mode))
        else:
            cursor.execute('''
                SELECT * FROM trades 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (since,))
        
        columns = [description[0] for description in cursor.description]
        trades = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return trades
    
    def calculate_metrics(self, days: int = 30) -> Dict:
        """Calculate performance metrics"""
        trades = self.get_trades(days)
        
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0
            }
        
        # Basic counts
        total_trades = len(trades)
        pnl_values = [t.get('net_pnl', 0) or 0 for t in trades]
        winning_trades = [p for p in pnl_values if p > 0]
        losing_trades = [p for p in pnl_values if p < 0]
        
        # Calculate metrics
        total_pnl = sum(pnl_values)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(winning_trades)
        gross_loss = abs(sum(losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe ratio (simplified - assumes risk-free rate = 0)
        if len(pnl_values) > 1:
            avg_return = statistics.mean(pnl_values)
            std_return = statistics.stdev(pnl_values)
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Max drawdown
        cumulative = 0
        peak = 0
        max_drawdown = 0
        for pnl in pnl_values:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            drawdown = peak - cumulative
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / total_trades,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'best_trade': max(pnl_values) if pnl_values else 0,
            'worst_trade': min(pnl_values) if pnl_values else 0
        }
    
    def generate_report(self, days: int = 7) -> str:
        """Generate a text performance report"""
        metrics = self.calculate_metrics(days)
        
        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║           📊 PERFORMANCE REPORT (Last {days} days)                 ║
╠══════════════════════════════════════════════════════════════════╣

TRADE STATISTICS:
  Total Trades:     {metrics['total_trades']}
  Winning Trades:   {metrics['winning_trades']} ({metrics['win_rate']:.1f}%)
  Losing Trades:    {metrics['losing_trades']}

P&L METRICS:
  Total P&L:        ${metrics['total_pnl']:.2f}
  Average P&L:      ${metrics['avg_pnl']:.2f}
  Average Win:      ${metrics['avg_win']:.2f}
  Average Loss:     ${metrics['avg_loss']:.2f}
  Best Trade:       ${metrics['best_trade']:.2f}
  Worst Trade:      ${metrics['worst_trade']:.2f}

RISK METRICS:
  Profit Factor:    {metrics['profit_factor']:.2f}
  Sharpe Ratio:     {metrics['sharpe_ratio']:.2f}
  Max Drawdown:     ${metrics['max_drawdown']:.2f}

╚══════════════════════════════════════════════════════════════════╝
        """
        
        return report
    
    def save_daily_summary(self):
        """Save daily performance summary"""
        today = datetime.now().strftime('%Y-%m-%d')
        metrics = self.calculate_metrics(days=1)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_summary 
            (date, total_pnl, num_trades, best_trade, worst_trade)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            today,
            metrics['total_pnl'],
            metrics['total_trades'],
            metrics['best_trade'],
            metrics['worst_trade']
        ))
        
        conn.commit()
        conn.close()
    
    def get_equity_curve(self, days: int = 30) -> List[Tuple[str, float]]:
        """Get equity curve data for charting"""
        trades = self.get_trades(days)
        if not trades:
            return []
        
        # Sort by timestamp
        trades_sorted = sorted(trades, key=lambda x: x.get('timestamp', ''))
        
        equity = 0
        curve = []
        for trade in trades_sorted:
            pnl = trade.get('net_pnl', 0) or 0
            equity += pnl
            timestamp = trade.get('timestamp', '')[:10]  # Just date
            curve.append((timestamp, equity))
        
        return curve

# Global instance
_analytics = None

def get_analytics() -> PerformanceAnalytics:
    """Get or create global analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = PerformanceAnalytics()
    return _analytics

if __name__ == "__main__":
    # Test mode
    analytics = PerformanceAnalytics()
    print(analytics.generate_report(days=30))
