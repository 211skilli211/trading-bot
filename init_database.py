#!/usr/bin/env python3
"""
Initialize and fix trading database
"""

import sqlite3
import os

def init_db():
    db_path = "trades.db"
    
    print(f"[DB] Initializing database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Main trades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT UNIQUE,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT DEFAULT 'BTCUSDT',
            side TEXT,  -- BUY or SELL
            exchange TEXT,
            entry_price REAL,
            exit_price REAL,
            quantity REAL,
            pnl REAL,
            pnl_percent REAL,
            fees REAL DEFAULT 0,
            net_pnl REAL,
            status TEXT,  -- OPEN, CLOSED, PENDING
            mode TEXT DEFAULT 'PAPER',  -- PAPER or LIVE
            strategy TEXT DEFAULT 'simple',
            metadata TEXT  -- JSON extra data
        )
    ''')
    
    # Positions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id TEXT UNIQUE,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT,
            exchange TEXT,
            side TEXT,
            entry_price REAL,
            quantity REAL,
            current_price REAL,
            unrealized_pnl REAL,
            status TEXT DEFAULT 'OPEN',
            mode TEXT DEFAULT 'PAPER'
        )
    ''')
    
    # Bot activity log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            level TEXT,  -- INFO, WARNING, ERROR
            message TEXT,
            source TEXT
        )
    ''')
    
    # Price history for analysis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            exchange TEXT,
            symbol TEXT,
            bid REAL,
            ask REAL,
            spread_percent REAL
        )
    ''')
    
    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_mode ON trades(mode)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON price_history(timestamp)')
    
    conn.commit()
    conn.close()
    
    print("[DB] ✅ Database initialized successfully")
    print(f"[DB] Tables created: trades, positions, activity_log, price_history")
    
    # Test the connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"[DB] Existing tables: {[t[0] for t in tables]}")
    conn.close()

if __name__ == "__main__":
    init_db()
