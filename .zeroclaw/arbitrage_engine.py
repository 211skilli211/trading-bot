#!/usr/bin/env python3
"""
ZeroClaw Arbitrage Engine
Scan and execute arbitrage opportunities across exchanges
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
import time

@dataclass
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_pct: float
    profit_potential: float
    timestamp: str
    
    def to_dict(self):
        return asdict(self)

class ArbitrageEngine:
    def __init__(self):
        self.workspace = "/tmp/trading_zeroclaw/.zeroclaw"
        self.db_path = f"{self.workspace}/arbitrage.db"
        self.min_spread_threshold = 0.3  # 0.3%
        self.exchanges = ['binance', 'coinbase', 'kucoin', 'okx', 'coingecko']
        
        os.makedirs(f"{self.workspace}/logs", exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize arbitrage database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                buy_exchange TEXT NOT NULL,
                sell_exchange TEXT NOT NULL,
                buy_price REAL NOT NULL,
                sell_price REAL NOT NULL,
                spread_pct REAL NOT NULL,
                profit_potential REAL NOT NULL,
                timestamp TEXT NOT NULL,
                executed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id INTEGER,
                symbol TEXT NOT NULL,
                buy_exchange TEXT NOT NULL,
                sell_exchange TEXT NOT NULL,
                amount REAL NOT NULL,
                expected_profit REAL NOT NULL,
                actual_profit REAL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                executed_at TEXT,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_price_from_exchange(self, symbol: str, exchange: str) -> Optional[float]:
        """Get price from specific exchange"""
        try:
            if exchange == 'coingecko':
                from urllib.request import urlopen
                coin_id = symbol.lower()
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
                with urlopen(url, timeout=5) as r:
                    data = json.loads(r.read())
                    return data.get(coin_id, {}).get('usd')
            
            # Simulated exchange prices with slight variations
            base_prices = {
                'BTC': 45230.0, 'ETH': 3120.0, 'SOL': 98.5,
                'ADA': 0.52, 'XRP': 0.58, 'DOGE': 0.082,
                'BNB': 320.0, 'DOT': 7.2, 'MATIC': 0.85
            }
            base = base_prices.get(symbol.upper(), 100.0)
            
            # Add exchange-specific variance (±0.2%)
            variance = {
                'binance': 0.0,
                'coinbase': 0.001,
                'kucoin': -0.0005,
                'okx': 0.0008
            }
            return base * (1 + variance.get(exchange, 0))
            
        except Exception as e:
            return None
    
    def scan_arbitrage(self, symbol: str = None, min_spread_pct: float = None) -> List[Dict]:
        """Scan for arbitrage opportunities"""
        if min_spread_pct is None:
            min_spread_pct = self.min_spread_threshold
        
        symbols = [symbol.upper()] if symbol else ['BTC', 'ETH', 'SOL', 'ADA', 'XRP']
        opportunities = []
        
        for sym in symbols:
            prices = {}
            for exchange in self.exchanges:
                price = self.get_price_from_exchange(sym, exchange)
                if price:
                    prices[exchange] = price
            
            if len(prices) < 2:
                continue
            
            # Find best arbitrage
            min_price = min(prices.values())
            max_price = max(prices.values())
            min_ex = [k for k, v in prices.items() if v == min_price][0]
            max_ex = [k for k, v in prices.items() if v == max_price][0]
            
            spread_pct = ((max_price - min_price) / min_price) * 100
            
            if spread_pct >= min_spread_pct:
                # Calculate profit potential (assuming $1000 trade size)
                trade_size = 1000
                amount = trade_size / min_price
                gross_profit = amount * (max_price - min_price)
                
                # Estimate fees (0.1% per trade on each exchange)
                fees = trade_size * 0.001 * 2
                net_profit = gross_profit - fees
                
                opp = ArbitrageOpportunity(
                    symbol=sym,
                    buy_exchange=min_ex,
                    sell_exchange=max_ex,
                    buy_price=min_price,
                    sell_price=max_price,
                    spread_pct=spread_pct,
                    profit_potential=net_profit,
                    timestamp=datetime.now().isoformat()
                )
                
                opportunities.append(opp.to_dict())
                
                # Store in database
                self._store_opportunity(opp)
        
        # Sort by profit potential
        opportunities.sort(key=lambda x: x['profit_potential'], reverse=True)
        
        return opportunities
    
    def _store_opportunity(self, opp: ArbitrageOpportunity):
        """Store opportunity in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO opportunities 
            (symbol, buy_exchange, sell_exchange, buy_price, sell_price, spread_pct, profit_potential, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (opp.symbol, opp.buy_exchange, opp.sell_exchange, 
              opp.buy_price, opp.sell_price, opp.spread_pct, 
              opp.profit_potential, opp.timestamp))
        
        conn.commit()
        conn.close()
    
    def execute_arbitrage(self, symbol: str, buy_exchange: str, sell_exchange: str,
                         amount: float) -> Dict:
        """Execute an arbitrage trade"""
        
        # Get current prices
        buy_price = self.get_price_from_exchange(symbol, buy_exchange)
        sell_price = self.get_price_from_exchange(symbol, sell_exchange)
        
        if not buy_price or not sell_price:
            return {"success": False, "error": "Could not get prices"}
        
        # Calculate expected profit
        gross_profit = amount * (sell_price - buy_price)
        fees = (amount * buy_price * 0.001) + (amount * sell_price * 0.001)
        expected_profit = gross_profit - fees
        
        # This would integrate with trading engine in real implementation
        # For now, simulate execution
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        execution_id = cursor.execute('''
            INSERT INTO executions 
            (symbol, buy_exchange, sell_exchange, amount, expected_profit, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, buy_exchange, sell_exchange, amount, expected_profit, 
              "PENDING", datetime.now().isoformat())).lastrowid
        
        conn.commit()
        conn.close()
        
        # Send notification
        self._notify_arbitrage(symbol, buy_exchange, sell_exchange, 
                               expected_profit, execution_id)
        
        return {
            "success": True,
            "execution_id": execution_id,
            "symbol": symbol,
            "buy_exchange": buy_exchange,
            "sell_exchange": sell_exchange,
            "amount": amount,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "expected_profit": expected_profit,
            "status": "PENDING",
            "message": "Arbitrage opportunity queued for execution"
        }
    
    def _notify_arbitrage(self, symbol: str, buy_ex: str, sell_ex: str,
                         profit: float, execution_id: int):
        """Send arbitrage notification"""
        try:
            import subprocess
            
            message = f"""🔄 ARBITRAGE OPPORTUNITY DETECTED

Symbol: {symbol}
Buy: {buy_ex}
Sell: {sell_ex}
Expected Profit: ${profit:.2f}
ID: {execution_id}

Auto-execution: Pending approval"""
            
            subprocess.run([
                'python3', '/root/trading-bot/.zeroclaw/telegram_notifier.py',
                'send_alert', message, 'warning'
            ], capture_output=True, timeout=10)
        except:
            pass
    
    def get_opportunities(self, hours: int = 24) -> List[Dict]:
        """Get recent opportunities"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT symbol, buy_exchange, sell_exchange, buy_price, sell_price,
                   spread_pct, profit_potential, timestamp, executed
            FROM opportunities
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        ''', (since,))
        
        opportunities = []
        for row in cursor.fetchall():
            opportunities.append({
                "symbol": row[0],
                "buy_exchange": row[1],
                "sell_exchange": row[2],
                "buy_price": row[3],
                "sell_price": row[4],
                "spread_pct": row[5],
                "profit_potential": row[6],
                "timestamp": row[7],
                "executed": row[8]
            })
        
        conn.close()
        return opportunities
    
    def get_statistics(self) -> Dict:
        """Get arbitrage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM opportunities")
        total_opportunities = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM executions")
        total_executions = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(spread_pct) FROM opportunities")
        avg_spread = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(expected_profit) FROM executions")
        total_expected_profit = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_opportunities": total_opportunities,
            "total_executions": total_executions,
            "avg_spread_pct": round(avg_spread, 4),
            "total_expected_profit": round(total_expected_profit, 2),
            "min_spread_threshold": self.min_spread_threshold,
            "exchanges_monitored": self.exchanges
        }
    
    def set_threshold(self, threshold: float) -> Dict:
        """Set minimum spread threshold"""
        self.min_spread_threshold = threshold
        return {
            "success": True,
            "min_spread_threshold": threshold,
            "message": f"Threshold set to {threshold}%"
        }


def main():
    import sys
    
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No action specified"}))
        return
    
    action = sys.argv[1]
    engine = ArbitrageEngine()
    
    if action == "scan":
        symbol = sys.argv[2] if len(sys.argv) > 2 else None
        min_spread = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
        result = {
            "success": True,
            "opportunities": engine.scan_arbitrage(symbol, min_spread)
        }
        
    elif action == "execute":
        symbol = sys.argv[2] if len(sys.argv) > 2 else "BTC"
        buy_ex = sys.argv[3] if len(sys.argv) > 3 else "binance"
        sell_ex = sys.argv[4] if len(sys.argv) > 4 else "coinbase"
        amount = float(sys.argv[5]) if len(sys.argv) > 5 else 0.01
        result = engine.execute_arbitrage(symbol, buy_ex, sell_ex, amount)
        
    elif action == "get_opportunities":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        result = {"success": True, "opportunities": engine.get_opportunities(hours)}
        
    elif action == "set_threshold":
        threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
        result = engine.set_threshold(threshold)
        
    elif action == "stats":
        result = {"success": True, "statistics": engine.get_statistics()}
        
    else:
        result = {"error": f"Unknown action: {action}"}
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
