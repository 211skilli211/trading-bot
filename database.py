#!/usr/bin/env python3
"""
SQLite Database Layer
Store trades, P&L, strategy performance for analysis and dashboards
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from contextlib import contextmanager


class TradingDatabase:
    """
    SQLite database for trading bot persistence.
    
    Tables:
    - trades: All executed trades
    - positions: Open/closed positions
    - price_history: OHLCV data
    - performance: Daily/monthly summaries
    """
    
    def __init__(self, db_path: str = "trades.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self._init_tables()
        print(f"[Database] Connected: {db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_tables(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            # Trades table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    timestamp TEXT,
                    mode TEXT,
                    strategy TEXT,
                    buy_exchange TEXT,
                    sell_exchange TEXT,
                    buy_price REAL,
                    sell_price REAL,
                    quantity REAL,
                    spread_pct REAL,
                    fees_paid REAL,
                    net_pnl REAL,
                    latency_ms REAL,
                    status TEXT,
                    raw_data TEXT
                )
            """)
            
            # Positions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id TEXT UNIQUE,
                    timestamp TEXT,
                    exchange TEXT,
                    side TEXT,
                    entry_price REAL,
                    quantity REAL,
                    stop_loss_price REAL,
                    take_profit_price REAL,
                    close_price REAL,
                    close_timestamp TEXT,
                    unrealized_pnl REAL,
                    status TEXT
                )
            """)
            
            # Price history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    exchange TEXT,
                    symbol TEXT,
                    price REAL,
                    bid REAL,
                    ask REAL,
                    volume_24h REAL
                )
            """)
            
            # Daily performance
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE,
                    starting_balance REAL,
                    ending_balance REAL,
                    total_pnl REAL,
                    num_trades INTEGER,
                    win_rate REAL,
                    max_drawdown REAL
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prices_time ON price_history(timestamp)")
    
    def save_trade(self, trade: Dict[str, Any]):
        """Save a trade to database."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trades 
                (trade_id, timestamp, mode, strategy, buy_exchange, sell_exchange,
                 buy_price, sell_price, quantity, spread_pct, fees_paid, net_pnl,
                 latency_ms, status, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.get('trade_id'),
                trade.get('timestamp'),
                trade.get('mode'),
                trade.get('strategy'),
                trade.get('buy_exchange'),
                trade.get('sell_exchange'),
                trade.get('buy_price'),
                trade.get('sell_price'),
                trade.get('quantity'),
                trade.get('spread_pct'),
                trade.get('fees_paid'),
                trade.get('net_pnl'),
                trade.get('latency_ms'),
                trade.get('status'),
                json.dumps(trade)
            ))
    
    def save_position(self, position):
        """Save a position to database."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO positions
                (position_id, timestamp, exchange, side, entry_price, quantity,
                 stop_loss_price, take_profit_price, close_price, close_timestamp,
                 unrealized_pnl, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.position_id,
                position.timestamp,
                position.exchange,
                position.side,
                position.entry_price,
                position.quantity,
                position.stop_loss_price,
                position.take_profit_price,
                position.close_price,
                position.close_timestamp,
                position.unrealized_pnl,
                position.status
            ))
    
    def save_price(self, exchange: str, symbol: str, price_data: Dict):
        """Save price snapshot."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO price_history (timestamp, exchange, symbol, price, bid, ask, volume_24h)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                exchange,
                symbol,
                price_data.get('price'),
                price_data.get('bid'),
                price_data.get('ask'),
                price_data.get('volume_24h')
            ))
    
    def get_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent trades."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM positions WHERE status = 'OPEN' ORDER BY timestamp DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_performance_summary(self, days: int = 7) -> Dict:
        """Get trading performance summary."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(net_pnl) as total_pnl,
                    AVG(net_pnl) as avg_pnl,
                    AVG(latency_ms) as avg_latency
                FROM trades
                WHERE timestamp > datetime('now', '-{} days')
            """.format(days))
            
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def cleanup_old_data(self, days: int = 30):
        """Remove old price history to save space."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM price_history WHERE timestamp < datetime('now', '-{} days')".format(days)
            )
            print(f"[Database] Cleaned up data older than {days} days")


if __name__ == "__main__":
    print("Database Module - Test Mode")
    print("=" * 60)
    
    db = TradingDatabase("test_trades.db")
    
    # Test save trade
    print("\n[Test 1] Save trade")
    test_trade = {
        "trade_id": "TEST_001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "PAPER",
        "strategy": "arbitrage",
        "buy_exchange": "Binance",
        "sell_exchange": "Coinbase",
        "buy_price": 68000,
        "sell_price": 69000,
        "quantity": 0.01,
        "spread_pct": 1.47,
        "fees_paid": 1.37,
        "net_pnl": 8.63,
        "latency_ms": 250,
        "status": "FILLED"
    }
    db.save_trade(test_trade)
    print("  Trade saved")
    
    # Test get trades
    print("\n[Test 2] Get trades")
    trades = db.get_trades(limit=5)
    print(f"  Retrieved {len(trades)} trades")
    for t in trades:
        print(f"    {t['trade_id']}: ${t['net_pnl']:+.2f}")
    
    # Test performance summary
    print("\n[Test 3] Performance summary")
    summary = db.get_performance_summary(days=7)
    print(f"  Total P&L: ${summary.get('total_pnl', 0):.2f}")
    print(f"  Total trades: {summary.get('total_trades', 0)}")
    
    print("\n✅ Database tests passed")
