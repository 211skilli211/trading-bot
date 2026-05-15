"""
Polymarket Smart Money Module — Database Schema & Operations
"""
import sqlite3
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from config import config


def get_db() -> sqlite3.Connection:
    """Get database connection with row factory."""
    db_path = config.database.db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_db()
    conn.executescript("""
        -- Tracked wallets
        CREATE TABLE IF NOT EXISTS wallets (
            address TEXT PRIMARY KEY,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            total_trades INTEGER DEFAULT 0,
            total_volume REAL DEFAULT 0.0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            avg_trade_size REAL DEFAULT 0.0,
            smart_money_score REAL DEFAULT 0.0,
            strategy TEXT DEFAULT 'unknown',  -- whale, win_rate, early_bird, composite
            is_smart INTEGER DEFAULT 0,
            notes TEXT DEFAULT ''
        );

        -- Individual wallet trades
        CREATE TABLE IF NOT EXISTS wallet_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address TEXT NOT NULL,
            market_id TEXT NOT NULL,
            market_question TEXT,
            side TEXT NOT NULL,  -- BUY or SELL
            outcome TEXT NOT NULL,  -- YES or NO
            price REAL NOT NULL,
            size REAL NOT NULL,
            usd_value REAL NOT NULL,
            timestamp TEXT NOT NULL,
            block_number INTEGER,
            tx_hash TEXT,
            FOREIGN KEY (wallet_address) REFERENCES wallets(address)
        );

        -- Tracked markets
        CREATE TABLE IF NOT EXISTS markets (
            market_id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            slug TEXT,
            volume REAL DEFAULT 0.0,
            liquidity REAL DEFAULT 0.0,
            outcome_prices TEXT,  -- JSON array
            created_at TEXT,
            updated_at TEXT,
            resolved INTEGER DEFAULT 0,
            outcome TEXT,
            tags TEXT  -- JSON array
        );

        -- Smart money signals
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address TEXT NOT NULL,
            market_id TEXT NOT NULL,
            market_question TEXT,
            strategy TEXT NOT NULL,  -- whale, win_rate, early_bird
            score REAL NOT NULL,
            details TEXT,  -- JSON with context
            timestamp TEXT NOT NULL,
            alerted INTEGER DEFAULT 0,
            FOREIGN KEY (wallet_address) REFERENCES wallets(address),
            FOREIGN KEY (market_id) REFERENCES markets(market_id)
        );

        -- Scan history
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_type TEXT NOT NULL,
            markets_found INTEGER DEFAULT 0,
            wallets_found INTEGER DEFAULT 0,
            signals_generated INTEGER DEFAULT 0,
            duration_seconds REAL,
            timestamp TEXT NOT NULL
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_wallet_trades_wallet ON wallet_trades(wallet_address);
        CREATE INDEX IF NOT EXISTS idx_wallet_trades_market ON wallet_trades(market_id);
        CREATE INDEX IF NOT EXISTS idx_wallet_trades_timestamp ON wallet_trades(timestamp);
        CREATE INDEX IF NOT EXISTS idx_signals_wallet ON signals(wallet_address);
        CREATE INDEX IF NOT EXISTS idx_signals_market ON signals(market_id);
        CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
        CREATE INDEX IF NOT EXISTS idx_signals_alerted ON signals(alerted);
        CREATE INDEX IF NOT EXISTS idx_markets_volume ON markets(volume);
        CREATE INDEX IF NOT EXISTS idx_wallets_score ON wallets(smart_money_score DESC);
    """)
    conn.commit()
    conn.close()


# --- Wallet operations ---

def upsert_wallet(address: str, trade_data: Dict[str, Any]) -> None:
    """Insert or update a wallet with new trade data."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    existing = conn.execute(
        "SELECT * FROM wallets WHERE address = ?", (address,)
    ).fetchone()
    
    if existing:
        total_trades = existing["total_trades"] + 1
        total_volume = existing["total_volume"] + trade_data.get("usd_value", 0)
        wins = existing["wins"] + (1 if trade_data.get("won") else 0)
        losses = existing["losses"] + (0 if trade_data.get("won") else 1)
        win_rate = wins / total_trades if total_trades > 0 else 0
        avg_size = total_volume / total_trades if total_trades > 0 else 0
        
        conn.execute("""
            UPDATE wallets SET
                last_seen = ?,
                total_trades = ?,
                total_volume = ?,
                wins = ?,
                losses = ?,
                win_rate = ?,
                avg_trade_size = ?
            WHERE address = ?
        """, (now, total_trades, total_volume, wins, losses, win_rate, avg_size, address))
    else:
        conn.execute("""
            INSERT INTO wallets (address, first_seen, last_seen, total_trades, total_volume, wins, losses, win_rate, avg_trade_size)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
        """, (address, now, now, trade_data.get("usd_value", 0),
              1 if trade_data.get("won") else 0,
              0 if trade_data.get("won") else 1,
              1.0 if trade_data.get("won") else 0.0,
              trade_data.get("usd_value", 0)))
    
    conn.commit()
    conn.close()


def get_smart_wallets(min_score: float = 50.0, limit: int = 50) -> List[Dict]:
    """Get top smart money wallets by score."""
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM wallets 
        WHERE is_smart = 1 AND smart_money_score >= ?
        ORDER BY smart_money_score DESC
        LIMIT ?
    """, (min_score, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Trade operations ---

def insert_trade(wallet_address: str, market_id: str, side: str, outcome: str,
                 price: float, size: float, usd_value: float,
                 market_question: str = "", tx_hash: str = None) -> None:
    """Insert a wallet trade."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO wallet_trades (wallet_address, market_id, market_question, side, outcome, price, size, usd_value, timestamp, tx_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (wallet_address, market_id, market_question, side, outcome, price, size, usd_value, now, tx_hash))
    conn.commit()
    conn.close()


def get_wallet_trades(wallet_address: str, limit: int = 100) -> List[Dict]:
    """Get recent trades for a wallet."""
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM wallet_trades 
        WHERE wallet_address = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (wallet_address, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Market operations ---

def upsert_market(market_data: Dict[str, Any]) -> None:
    """Insert or update a market."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    import json
    
    conn.execute("""
        INSERT OR REPLACE INTO markets (market_id, question, slug, volume, liquidity, outcome_prices, created_at, updated_at, resolved, outcome, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        market_data["market_id"],
        market_data.get("question", ""),
        market_data.get("slug", ""),
        market_data.get("volume", 0),
        market_data.get("liquidity", 0),
        json.dumps(market_data.get("outcome_prices", [])),
        market_data.get("created_at", now),
        now,
        1 if market_data.get("resolved") else 0,
        market_data.get("outcome", ""),
        json.dumps(market_data.get("tags", []))
    ))
    conn.commit()
    conn.close()


def get_active_markets(min_volume: float = 0, limit: int = 100) -> List[Dict]:
    """Get active (unresolved) markets."""
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM markets 
        WHERE resolved = 0 AND volume >= ?
        ORDER BY volume DESC
        LIMIT ?
    """, (min_volume, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Signal operations ---

def insert_signal(wallet_address: str, market_id: str, strategy: str,
                  score: float, details: Dict = None, market_question: str = "") -> int:
    """Insert a smart money signal."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    import json
    
    cursor = conn.execute("""
        INSERT INTO signals (wallet_address, market_id, market_question, strategy, score, details, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (wallet_address, market_id, market_question, strategy, score,
          json.dumps(details) if details else None, now))
    conn.commit()
    signal_id = cursor.lastrowid
    conn.close()
    return signal_id


def get_unalerted_signals(min_score: float = 60.0) -> List[Dict]:
    """Get signals that haven't been alerted yet."""
    conn = get_db()
    rows = conn.execute("""
        SELECT s.*, w.win_rate, w.total_volume as wallet_volume, w.smart_money_score
        FROM signals s
        JOIN wallets w ON s.wallet_address = w.address
        WHERE s.alerted = 0 AND s.score >= ?
        ORDER BY s.score DESC, s.timestamp DESC
    """, (min_score,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_signals_alerted(signal_ids: List[int]) -> None:
    """Mark signals as alerted."""
    conn = get_db()
    placeholders = ",".join("?" * len(signal_ids))
    conn.execute(f"UPDATE signals SET alerted = 1 WHERE id IN ({placeholders})", signal_ids)
    conn.commit()
    conn.close()


# --- Scan history ---

def log_scan(scan_type: str, markets: int, wallets: int, signals: int, duration: float) -> None:
    """Log a scan run."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO scan_history (scan_type, markets_found, wallets_found, signals_generated, duration_seconds, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (scan_type, markets, wallets, signals, duration, now))
    conn.commit()
    conn.close()
