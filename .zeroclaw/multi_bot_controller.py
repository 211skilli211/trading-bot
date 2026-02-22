#!/usr/bin/env python3
"""
ZeroClaw Multi-Bot Controller
Coordinate multiple trading bots and strategies
"""

import json
import os
import sqlite3
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import threading
import time

class BotStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"

class StrategyType(Enum):
    ARBITRAGE = "arbitrage"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    GRID = "grid"
    DCA = "dca"

class TradingBot:
    def __init__(self, bot_id: str, name: str, strategy: str, symbols: List[str]):
        self.bot_id = bot_id
        self.name = name
        self.strategy = strategy
        self.symbols = symbols
        self.status = BotStatus.STOPPED
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.trades_count = 0
        self.pnl = 0.0
        self.config = {}
        self.thread = None
        self._stop_event = threading.Event()
    
    def to_dict(self) -> Dict:
        return {
            "bot_id": self.bot_id,
            "name": self.name,
            "strategy": self.strategy,
            "symbols": self.symbols,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "trades_count": self.trades_count,
            "pnl": self.pnl,
            "config": self.config
        }

class MultiBotController:
    def __init__(self):
        self.workspace = "/tmp/trading_zeroclaw/.zeroclaw"
        self.db_path = f"{self.workspace}/bots.db"
        self.bots: Dict[str, TradingBot] = {}
        
        os.makedirs(f"{self.workspace}/bots", exist_ok=True)
        self._init_database()
        self._load_bots()
    
    def _init_database(self):
        """Initialize bots database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                bot_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                strategy TEXT NOT NULL,
                symbols TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                trades_count INTEGER DEFAULT 0,
                pnl REAL DEFAULT 0,
                config TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (bot_id) REFERENCES bots(bot_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                pnl REAL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (bot_id) REFERENCES bots(bot_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_bots(self):
        """Load bots from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT bot_id, name, strategy, symbols, status, created_at, 
                   started_at, trades_count, pnl, config
            FROM bots
        ''')
        
        for row in cursor.fetchall():
            bot = TradingBot(row[0], row[1], row[2], json.loads(row[3]))
            bot.status = BotStatus(row[4])
            bot.created_at = row[5]
            bot.started_at = row[6]
            bot.trades_count = row[7] or 0
            bot.pnl = row[8] or 0
            bot.config = json.loads(row[9]) if row[9] else {}
            self.bots[bot.bot_id] = bot
        
        conn.close()
    
    def _save_bot(self, bot: TradingBot):
        """Save bot to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO bots 
            (bot_id, name, strategy, symbols, status, created_at, started_at, 
             trades_count, pnl, config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bot.bot_id, bot.name, bot.strategy, json.dumps(bot.symbols),
            bot.status.value, bot.created_at, bot.started_at,
            bot.trades_count, bot.pnl, json.dumps(bot.config)
        ))
        
        conn.commit()
        conn.close()
    
    def create_bot(self, name: str, strategy: str, symbols: List[str],
                   config: Dict = None) -> Dict:
        """Create a new trading bot"""
        bot_id = f"bot_{int(datetime.now().timestamp())}_{name.lower().replace(' ', '_')}"
        
        bot = TradingBot(bot_id, name, strategy, symbols)
        if config:
            bot.config = config
        
        self.bots[bot_id] = bot
        self._save_bot(bot)
        
        self._log_bot_event(bot_id, "INFO", f"Bot '{name}' created with {strategy} strategy")
        
        return {
            "success": True,
            "bot": bot.to_dict(),
            "message": f"Bot '{name}' created successfully"
        }
    
    def start_bot(self, bot_id: str) -> Dict:
        """Start a bot"""
        if bot_id not in self.bots:
            return {"success": False, "error": f"Bot {bot_id} not found"}
        
        bot = self.bots[bot_id]
        
        if bot.status == BotStatus.RUNNING:
            return {"success": False, "error": "Bot already running"}
        
        bot.status = BotStatus.STARTING
        bot.started_at = datetime.now().isoformat()
        bot._stop_event.clear()
        
        # Start bot in background thread
        bot.thread = threading.Thread(target=self._run_bot, args=(bot_id,))
        bot.thread.daemon = True
        bot.thread.start()
        
        bot.status = BotStatus.RUNNING
        self._save_bot(bot)
        
        self._log_bot_event(bot_id, "INFO", f"Bot '{bot.name}' started")
        self._notify_bot_action(bot, "STARTED")
        
        return {
            "success": True,
            "bot": bot.to_dict(),
            "message": f"Bot '{bot.name}' started"
        }
    
    def _run_bot(self, bot_id: str):
        """Bot execution loop"""
        bot = self.bots[bot_id]
        
        while not bot._stop_event.is_set():
            try:
                # Execute strategy logic based on bot type
                if bot.strategy == StrategyType.ARBITRAGE.value:
                    self._run_arbitrage_strategy(bot)
                elif bot.strategy == StrategyType.MOMENTUM.value:
                    self._run_momentum_strategy(bot)
                elif bot.strategy == StrategyType.GRID.value:
                    self._run_grid_strategy(bot)
                elif bot.strategy == StrategyType.DCA.value:
                    self._run_dca_strategy(bot)
                
                # Sleep between iterations
                time.sleep(bot.config.get('interval', 60))
                
            except Exception as e:
                self._log_bot_event(bot_id, "ERROR", str(e))
                time.sleep(10)
    
    def _run_arbitrage_strategy(self, bot: TradingBot):
        """Run arbitrage strategy"""
        # This would integrate with arbitrage engine
        pass
    
    def _run_momentum_strategy(self, bot: TradingBot):
        """Run momentum trading strategy"""
        # Check for momentum signals
        pass
    
    def _run_grid_strategy(self, bot: TradingBot):
        """Run grid trading strategy"""
        # Grid trading logic
        pass
    
    def _run_dca_strategy(self, bot: TradingBot):
        """Run DCA strategy"""
        # Dollar cost averaging logic
        pass
    
    def stop_bot(self, bot_id: str) -> Dict:
        """Stop a bot"""
        if bot_id not in self.bots:
            return {"success": False, "error": f"Bot {bot_id} not found"}
        
        bot = self.bots[bot_id]
        
        if bot.status != BotStatus.RUNNING:
            return {"success": False, "error": "Bot not running"}
        
        bot._stop_event.set()
        if bot.thread:
            bot.thread.join(timeout=5)
        
        bot.status = BotStatus.STOPPED
        bot.started_at = None
        self._save_bot(bot)
        
        self._log_bot_event(bot_id, "INFO", f"Bot '{bot.name}' stopped")
        self._notify_bot_action(bot, "STOPPED")
        
        return {
            "success": True,
            "bot": bot.to_dict(),
            "message": f"Bot '{bot.name}' stopped"
        }
    
    def delete_bot(self, bot_id: str) -> Dict:
        """Delete a bot"""
        if bot_id not in self.bots:
            return {"success": False, "error": f"Bot {bot_id} not found"}
        
        bot = self.bots[bot_id]
        
        if bot.status == BotStatus.RUNNING:
            self.stop_bot(bot_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bots WHERE bot_id = ?", (bot_id,))
        conn.commit()
        conn.close()
        
        del self.bots[bot_id]
        
        return {
            "success": True,
            "message": f"Bot '{bot.name}' deleted"
        }
    
    def get_bot_status(self, bot_id: str = None) -> Dict:
        """Get bot status"""
        if bot_id:
            if bot_id not in self.bots:
                return {"success": False, "error": f"Bot {bot_id} not found"}
            return {"success": True, "bot": self.bots[bot_id].to_dict()}
        
        return {
            "success": True,
            "bots": [b.to_dict() for b in self.bots.values()],
            "summary": {
                "total": len(self.bots),
                "running": sum(1 for b in self.bots.values() if b.status == BotStatus.RUNNING),
                "stopped": sum(1 for b in self.bots.values() if b.status == BotStatus.STOPPED),
                "error": sum(1 for b in self.bots.values() if b.status == BotStatus.ERROR)
            }
        }
    
    def set_strategy(self, bot_id: str, strategy: str, params: Dict = None) -> Dict:
        """Set bot strategy"""
        if bot_id not in self.bots:
            return {"success": False, "error": f"Bot {bot_id} not found"}
        
        bot = self.bots[bot_id]
        was_running = bot.status == BotStatus.RUNNING
        
        if was_running:
            self.stop_bot(bot_id)
        
        bot.strategy = strategy
        if params:
            bot.config.update(params)
        
        self._save_bot(bot)
        
        if was_running:
            self.start_bot(bot_id)
        
        return {
            "success": True,
            "bot": bot.to_dict(),
            "message": f"Strategy updated to {strategy}"
        }
    
    def coordinate_bots(self, action: str, params: Dict = None) -> Dict:
        """Coordinate multiple bots"""
        if action == "stop_all":
            for bot in self.bots.values():
                if bot.status == BotStatus.RUNNING:
                    self.stop_bot(bot.bot_id)
            return {"success": True, "message": "All bots stopped"}
        
        elif action == "start_all":
            for bot in self.bots.values():
                if bot.status == BotStatus.STOPPED:
                    self.start_bot(bot.bot_id)
            return {"success": True, "message": "All bots started"}
        
        elif action == "report":
            total_pnl = sum(b.pnl for b in self.bots.values())
            total_trades = sum(b.trades_count for b in self.bots.values())
            return {
                "success": True,
                "report": {
                    "total_bots": len(self.bots),
                    "running": sum(1 for b in self.bots.values() if b.status == BotStatus.RUNNING),
                    "total_pnl": total_pnl,
                    "total_trades": total_trades,
                    "bots": [b.to_dict() for b in self.bots.values()]
                }
            }
        
        return {"success": False, "error": f"Unknown action: {action}"}
    
    def _log_bot_event(self, bot_id: str, level: str, message: str):
        """Log bot event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bot_logs (bot_id, level, message, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (bot_id, level, message, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def _notify_bot_action(self, bot: TradingBot, action: str):
        """Send bot notification"""
        try:
            emoji = "🟢" if action == "STARTED" else "🔴" if action == "STOPPED" else "⚠️"
            message = f"""{emoji} BOT {action}

Name: {bot.name}
Strategy: {bot.strategy}
Symbols: {', '.join(bot.symbols)}
Trades: {bot.trades_count}
PnL: ${bot.pnl:.2f}"""
            
            subprocess.run([
                'python3', '/root/trading-bot/.zeroclaw/telegram_notifier.py',
                'send_alert', message, 'info'
            ], capture_output=True, timeout=10)
        except:
            pass


def main():
    import sys
    
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No action specified"}))
        return
    
    action = sys.argv[1]
    controller = MultiBotController()
    
    if action == "list_bots":
        result = controller.get_bot_status()
        
    elif action == "create_bot":
        name = sys.argv[2] if len(sys.argv) > 2 else "New Bot"
        strategy = sys.argv[3] if len(sys.argv) > 3 else "arbitrage"
        symbols = sys.argv[4].split(",") if len(sys.argv) > 4 else ["BTC", "ETH"]
        result = controller.create_bot(name, strategy, symbols)
        
    elif action == "start_bot":
        bot_id = sys.argv[2] if len(sys.argv) > 2 else None
        if bot_id:
            result = controller.start_bot(bot_id)
        else:
            result = {"error": "No bot_id specified"}
        
    elif action == "stop_bot":
        bot_id = sys.argv[2] if len(sys.argv) > 2 else None
        if bot_id:
            result = controller.stop_bot(bot_id)
        else:
            result = {"error": "No bot_id specified"}
        
    elif action == "delete_bot":
        bot_id = sys.argv[2] if len(sys.argv) > 2 else None
        if bot_id:
            result = controller.delete_bot(bot_id)
        else:
            result = {"error": "No bot_id specified"}
        
    elif action == "get_status":
        bot_id = sys.argv[2] if len(sys.argv) > 2 else None
        result = controller.get_bot_status(bot_id)
        
    elif action == "set_strategy":
        bot_id = sys.argv[2] if len(sys.argv) > 2 else None
        strategy = sys.argv[3] if len(sys.argv) > 3 else "arbitrage"
        if bot_id:
            result = controller.set_strategy(bot_id, strategy)
        else:
            result = {"error": "No bot_id specified"}
        
    elif action == "coordinate":
        coord_action = sys.argv[2] if len(sys.argv) > 2 else "report"
        result = controller.coordinate_bots(coord_action)
        
    else:
        result = {"error": f"Unknown action: {action}"}
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
