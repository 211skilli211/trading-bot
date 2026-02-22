#!/usr/bin/env python3
"""
ZeroClaw Trading Engine
AI-controlled trading operations with paper trading support
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import random

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class TradingMode(Enum):
    PAPER = "paper"
    LIVE = "live"

@dataclass
class Position:
    symbol: str
    side: str
    amount: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    opened_at: str
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Trade:
    id: str
    symbol: str
    side: str
    amount: float
    price: float
    total: float
    fees: float
    order_type: str
    status: str
    mode: str
    created_at: str
    executed_at: Optional[str] = None
    pnl: Optional[float] = None
    reason: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)

class TradingEngine:
    def __init__(self, db_path: str = None):
        self.workspace = "/tmp/trading_zeroclaw/.zeroclaw"
        self.db_path = db_path or f"{self.workspace}/trading.db"
        self.portfolio_path = f"{self.workspace}/workspace/portfolio"
        self.mode = TradingMode.PAPER
        self.initial_balance = 10000.0
        
        # Ensure directories exist
        os.makedirs(self.portfolio_path, exist_ok=True)
        os.makedirs(f"{self.workspace}/logs", exist_ok=True)
        
        self._init_database()
        self._init_portfolio()
    
    def _init_database(self):
        """Initialize SQLite database for trades"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                fees REAL NOT NULL,
                order_type TEXT NOT NULL,
                status TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                executed_at TEXT,
                pnl REAL,
                reason TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT PRIMARY KEY,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                realized_pnl REAL NOT NULL,
                opened_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balance (
                currency TEXT PRIMARY KEY,
                available REAL NOT NULL,
                locked REAL NOT NULL,
                total REAL NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_portfolio(self):
        """Initialize portfolio with starting balance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if balance exists
        cursor.execute("SELECT COUNT(*) FROM balance WHERE currency = 'USDT'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO balance (currency, available, locked, total)
                VALUES ('USDT', ?, 0, ?)
            ''', (self.initial_balance, self.initial_balance))
            conn.commit()
        
        conn.close()
    
    def get_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        # Import price fetcher
        try:
            from urllib.request import urlopen
            coin_id = symbol.lower()
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            with urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
                return data.get(coin_id, {}).get('usd', 0)
        except:
            # Fallback prices
            prices = {
                'BTC': 45230.0, 'ETH': 3120.0, 'SOL': 98.5,
                'ADA': 0.52, 'XRP': 0.58, 'DOGE': 0.082,
                'BNB': 320.0, 'DOT': 7.2, 'MATIC': 0.85
            }
            return prices.get(symbol.upper(), 100.0)
    
    def execute_trade(self, symbol: str, side: str, amount: float, 
                     price: float = None, order_type: str = "market",
                     reason: str = "") -> Dict[str, Any]:
        """Execute a trade"""
        
        symbol = symbol.upper()
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        
        # Get current price if not provided
        if price is None or price <= 0:
            price = self.get_price(symbol)
        
        # Calculate fees (0.1% per trade)
        fees = price * amount * 0.001
        total = price * amount + fees
        
        # Check balance for buy orders
        if side_enum == OrderSide.BUY:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT available FROM balance WHERE currency = 'USDT'")
            row = cursor.fetchone()
            available = row[0] if row else 0
            conn.close()
            
            if available < total:
                return {
                    "success": False,
                    "error": f"Insufficient balance. Need ${total:.2f}, have ${available:.2f}",
                    "symbol": symbol,
                    "side": side,
                    "amount": amount
                }
        
        # Check position for sell orders
        if side_enum == OrderSide.SELL:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT amount FROM positions WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            held = row[0] if row else 0
            conn.close()
            
            if held < amount:
                return {
                    "success": False,
                    "error": f"Insufficient {symbol} to sell. Have {held}, want to sell {amount}",
                    "symbol": symbol,
                    "side": side,
                    "amount": amount
                }
        
        # Generate trade ID
        trade_id = f"TRD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000,9999)}"
        
        # Record trade
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (id, symbol, side, amount, price, total, fees,
                              order_type, status, mode, created_at, executed_at, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_id, symbol, side, amount, price, total, fees,
            order_type, "FILLED", self.mode.value,
            datetime.now().isoformat(), datetime.now().isoformat(), reason
        ))
        
        # Update balance
        if side_enum == OrderSide.BUY:
            cursor.execute('''
                UPDATE balance 
                SET available = available - ?, total = total - ?
                WHERE currency = 'USDT'
            ''', (total, total))
            
            # Add to positions
            cursor.execute('''
                INSERT INTO positions (symbol, side, amount, entry_price, current_price,
                                     unrealized_pnl, realized_pnl, opened_at)
                VALUES (?, 'LONG', ?, ?, ?, 0, 0, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    amount = amount + ?,
                    entry_price = ((entry_price * amount) + (? * ?)) / (amount + ?)
            ''', (symbol, amount, price, price, datetime.now().isoformat(), 
                  amount, price, amount, amount))
        else:
            # Calculate P&L
            cursor.execute("SELECT entry_price, amount FROM positions WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            if row:
                entry_price, held = row
                pnl = (price - entry_price) * amount
            else:
                pnl = 0
            
            # Update balance
            proceeds = price * amount - fees
            cursor.execute('''
                UPDATE balance 
                SET available = available + ?, total = total + ?
                WHERE currency = 'USDT'
            ''', (proceeds, proceeds))
            
            # Update positions
            cursor.execute('''
                UPDATE positions 
                SET amount = amount - ?, realized_pnl = realized_pnl + ?
                WHERE symbol = ?
            ''', (amount, pnl, symbol))
            
            # Remove position if fully closed
            cursor.execute("DELETE FROM positions WHERE symbol = ? AND amount <= 0", (symbol,))
            
            # Update trade with P&L
            cursor.execute("UPDATE trades SET pnl = ? WHERE id = ?", (pnl, trade_id))
        
        conn.commit()
        conn.close()
        
        # Send notification
        self._notify_trade(trade_id, symbol, side, amount, price, total, self.mode.value)
        
        return {
            "success": True,
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "total": total,
            "fees": fees,
            "mode": self.mode.value,
            "status": "FILLED",
            "executed_at": datetime.now().isoformat(),
            "reason": reason
        }
    
    def _notify_trade(self, trade_id: str, symbol: str, side: str, 
                     amount: float, price: float, total: float, mode: str):
        """Send Telegram notification for trade"""
        try:
            import subprocess
            emoji = "🟢" if side == "buy" else "🔴"
            mode_emoji = "📝" if mode == "paper" else "💰"
            
            message = f"""{emoji} {mode_emoji} TRADE EXECUTED

Symbol: {symbol}
Side: {side.upper()}
Amount: {amount}
Price: ${price:,.2f}
Total: ${total:,.2f}
Mode: {mode.upper()}
ID: {trade_id}

View: http://localhost:8080/trades"""
            
            subprocess.run([
                'python3', '/root/trading-bot/.zeroclaw/telegram_notifier.py',
                'send_alert', message, 'success'
            ], capture_output=True, timeout=10)
        except:
            pass
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, side, amount, entry_price, current_price,
                   unrealized_pnl, realized_pnl, opened_at
            FROM positions WHERE amount > 0
        ''')
        
        positions = []
        for row in cursor.fetchall():
            # Update current price
            symbol = row[0]
            current_price = self.get_price(symbol)
            entry_price = row[3]
            amount = row[2]
            unrealized_pnl = (current_price - entry_price) * amount
            
            positions.append({
                "symbol": row[0],
                "side": row[1],
                "amount": row[2],
                "entry_price": row[3],
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": row[6],
                "opened_at": row[7]
            })
            
            # Update in DB
            cursor.execute('''
                UPDATE positions 
                SET current_price = ?, unrealized_pnl = ?
                WHERE symbol = ?
            ''', (current_price, unrealized_pnl, symbol))
        
        conn.commit()
        conn.close()
        
        return positions
    
    def get_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT currency, available, locked, total FROM balance")
        balances = []
        total_value = 0
        
        for row in cursor.fetchall():
            currency, available, locked, total = row
            
            # Calculate USD value
            if currency == 'USDT':
                usd_value = total
            else:
                price = self.get_price(currency)
                usd_value = total * price
            
            total_value += usd_value
            
            balances.append({
                "currency": currency,
                "available": available,
                "locked": locked,
                "total": total,
                "usd_value": usd_value
            })
        
        # Add positions value
        positions = self.get_positions()
        for pos in positions:
            total_value += pos['amount'] * pos['current_price']
        
        conn.close()
        
        return {
            "balances": balances,
            "total_value_usd": total_value,
            "initial_value": self.initial_balance,
            "total_pnl": total_value - self.initial_balance,
            "pnl_pct": ((total_value - self.initial_balance) / self.initial_balance) * 100,
            "mode": self.mode.value
        }
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, side, amount, price, total, fees,
                   order_type, status, mode, created_at, executed_at, pnl, reason
            FROM trades
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                "id": row[0],
                "symbol": row[1],
                "side": row[2],
                "amount": row[3],
                "price": row[4],
                "total": row[5],
                "fees": row[6],
                "order_type": row[7],
                "status": row[8],
                "mode": row[9],
                "created_at": row[10],
                "executed_at": row[11],
                "pnl": row[12],
                "reason": row[13]
            })
        
        conn.close()
        return trades
    
    def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close a position"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT amount FROM positions WHERE symbol = ?", (symbol.upper(),))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"success": False, "error": f"No position found for {symbol}"}
        
        amount = row[0]
        return self.execute_trade(
            symbol=symbol,
            side="sell",
            amount=amount,
            reason="Position close"
        )
    
    def set_mode(self, mode: str) -> Dict[str, Any]:
        """Set trading mode"""
        if mode.lower() == "live":
            self.mode = TradingMode.LIVE
        else:
            self.mode = TradingMode.PAPER
        
        return {
            "success": True,
            "mode": self.mode.value,
            "message": f"Trading mode set to {self.mode.value.upper()}"
        }
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get complete portfolio summary"""
        balance = self.get_balance()
        positions = self.get_positions()
        trades = self.get_trade_history(10)
        
        # Calculate metrics
        all_trades = self.get_trade_history(10000)
        total_trades = len(all_trades)
        winning_trades = sum(1 for t in all_trades if (t.get('pnl') or 0) > 0)
        
        return {
            "balance": balance,
            "positions": positions,
            "recent_trades": trades,
            "metrics": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                "open_positions": len(positions)
            }
        }


# Tool interface for ZeroClaw
def main():
    import sys
    
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No action specified"}))
        return
    
    action = sys.argv[1]
    engine = TradingEngine()
    
    if action == "buy":
        symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC"
        amount = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
        result = engine.execute_trade(symbol, "buy", amount, reason="User request")
        
    elif action == "sell":
        symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC"
        amount = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
        result = engine.execute_trade(symbol, "sell", amount, reason="User request")
        
    elif action == "get_positions":
        result = {"success": True, "positions": engine.get_positions()}
        
    elif action == "get_balance":
        result = {"success": True, "balance": engine.get_balance()}
        
    elif action == "get_history":
        result = {"success": True, "trades": engine.get_trade_history()}
        
    elif action == "close_position":
        symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC"
        result = engine.close_position(symbol)
        
    elif action == "set_mode":
        mode = sys.argv[2] if len(sys.argv) > 2 else "paper"
        result = engine.set_mode(mode)
        
    elif action == "summary":
        result = {"success": True, "portfolio": engine.get_portfolio_summary()}
        
    else:
        result = {"error": f"Unknown action: {action}"}
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
