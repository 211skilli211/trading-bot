#!/usr/bin/env python3
"""
ZeroClaw Telegram Notifier
Send notifications, alerts, and trade updates via Telegram
"""

import json
import os
import sqlite3
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional

class TelegramNotifier:
    def __init__(self):
        self.workspace = "/tmp/trading_zeroclaw/.zeroclaw"
        self.db_path = f"{self.workspace}/notifications.db"
        
        # Load config
        self.bot_token = "8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
        self.chat_id = "7745772764"
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        
        self._init_database()
    
    def _init_database(self):
        """Initialize notifications database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                sent BOOLEAN DEFAULT FALSE,
                timestamp TEXT NOT NULL,
                telegram_message_id INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                condition TEXT NOT NULL,
                symbol TEXT,
                threshold REAL,
                active BOOLEAN DEFAULT TRUE,
                triggered_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_triggered TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> Dict:
        """Send a text message"""
        url = f"{self.api_base}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        
        try:
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(url, data=data, method='POST')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read())
                
                if result.get('ok'):
                    message_id = result['result']['message_id']
                    self._store_notification('message', 'info', message, True, message_id)
                    return {
                        "success": True,
                        "message_id": message_id,
                        "chat_id": self.chat_id
                    }
                else:
                    return {"success": False, "error": result.get('description')}
                    
        except Exception as e:
            self._store_notification('message', 'info', message, False)
            return {"success": False, "error": str(e)}
    
    def send_alert(self, message: str, level: str = "info") -> Dict:
        """Send an alert with proper formatting"""
        # Format based on level
        emojis = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "🚨"
        }
        
        emoji = emojis.get(level, "ℹ️")
        formatted = f"{emoji} <b>ZeroClaw Alert</b>\n\n{message}"
        
        result = self.send_message(formatted)
        
        if result['success']:
            self._store_notification('alert', level, message, True, result.get('message_id'))
        
        return result
    
    def send_trade_notification(self, trade_data: Dict) -> Dict:
        """Send trade execution notification"""
        side_emoji = "🟢" if trade_data.get('side') == 'buy' else "🔴"
        mode_emoji = "📝" if trade_data.get('mode') == 'paper' else "💰"
        
        message = f"""{side_emoji} {mode_emoji} <b>Trade Executed</b>

<b>Symbol:</b> {trade_data.get('symbol')}
<b>Side:</b> {trade_data.get('side', '').upper()}
<b>Amount:</b> {trade_data.get('amount')}
<b>Price:</b> ${trade_data.get('price', 0):,.2f}
<b>Total:</b> ${trade_data.get('total', 0):,.2f}
<b>Fees:</b> ${trade_data.get('fees', 0):,.4f}
<b>Mode:</b> {trade_data.get('mode', 'unknown').upper()}
<b>ID:</b> <code>{trade_data.get('trade_id', 'N/A')}</code>

<i>{trade_data.get('reason', '')}</i>"""
        
        if trade_data.get('pnl') is not None:
            pnl_emoji = "📈" if trade_data['pnl'] > 0 else "📉"
            message += f"\n\n{pnl_emoji} <b>P&L:</b> ${trade_data['pnl']:,.2f}"
        
        result = self.send_message(message)
        
        if result['success']:
            self._store_notification('trade', 'success', 
                                   f"Trade: {trade_data.get('symbol')} {trade_data.get('side')}", 
                                   True, result.get('message_id'))
        
        return result
    
    def send_arbitrage_alert(self, arb_data: Dict) -> Dict:
        """Send arbitrage opportunity alert"""
        message = f"""🔄 <b>Arbitrage Opportunity</b>

<b>Symbol:</b> {arb_data.get('symbol')}
<b>Buy:</b> {arb_data.get('buy_exchange')} @ ${arb_data.get('buy_price', 0):,.2f}
<b>Sell:</b> {arb_data.get('sell_exchange')} @ ${arb_data.get('sell_price', 0):,.2f}
<b>Spread:</b> {arb_data.get('spread_pct', 0):.2f}%
<b>Est. Profit:</b> ${arb_data.get('profit_potential', 0):,.2f}

<i>Auto-execution pending approval</i>"""
        
        result = self.send_message(message)
        
        if result['success']:
            self._store_notification('arbitrage', 'warning', 
                                   f"Arbitrage: {arb_data.get('symbol')}", 
                                   True, result.get('message_id'))
        
        return result
    
    def send_price_alert(self, symbol: str, price: float, threshold: float,
                        condition: str) -> Dict:
        """Send price alert"""
        emoji = "📈" if condition == "above" else "📉"
        
        message = f"""{emoji} <b>Price Alert Triggered</b>

<b>{symbol}</b> is now <b>{condition.upper()}</b> ${threshold:,.2f}

<b>Current Price:</b> ${price:,.2f}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        result = self.send_message(message)
        
        if result['success']:
            self._store_notification('price_alert', 'warning', 
                                   f"{symbol} {condition} ${threshold}", 
                                   True, result.get('message_id'))
        
        return result
    
    def set_alert(self, name: str, condition: str, symbol: str = None,
                 threshold: float = None) -> Dict:
        """Set up a new alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (name, condition, symbol, threshold, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, condition, symbol, threshold, datetime.now().isoformat()))
        
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "alert_id": alert_id,
            "message": f"Alert '{name}' created"
        }
    
    def check_alerts(self, symbol: str, current_price: float) -> List[Dict]:
        """Check if any alerts should be triggered"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, condition, symbol, threshold
            FROM alerts
            WHERE active = TRUE AND symbol = ?
        ''', (symbol,))
        
        triggered = []
        for row in cursor.fetchall():
            alert_id, name, condition, sym, threshold = row
            
            should_trigger = False
            if condition == "above" and current_price > threshold:
                should_trigger = True
            elif condition == "below" and current_price < threshold:
                should_trigger = True
            
            if should_trigger:
                triggered.append({
                    "id": alert_id,
                    "name": name,
                    "condition": condition,
                    "threshold": threshold
                })
                
                # Update alert
                cursor.execute('''
                    UPDATE alerts 
                    SET triggered_count = triggered_count + 1,
                        last_triggered = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), alert_id))
        
        conn.commit()
        conn.close()
        
        # Send notifications for triggered alerts
        for alert in triggered:
            self.send_price_alert(symbol, current_price, alert['threshold'], alert['condition'])
        
        return triggered
    
    def _store_notification(self, notif_type: str, level: str, message: str,
                           sent: bool, telegram_id: int = None):
        """Store notification in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notifications (type, level, message, sent, timestamp, telegram_message_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (notif_type, level, message, sent, datetime.now().isoformat(), telegram_id))
        
        conn.commit()
        conn.close()
    
    def get_notification_history(self, limit: int = 50) -> List[Dict]:
        """Get notification history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT type, level, message, sent, timestamp
            FROM notifications
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                "type": row[0],
                "level": row[1],
                "message": row[2],
                "sent": row[3],
                "timestamp": row[4]
            })
        
        conn.close()
        return notifications
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, condition, symbol, threshold, triggered_count, created_at
            FROM alerts
            WHERE active = TRUE
            ORDER BY created_at DESC
        ''')
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                "id": row[0],
                "name": row[1],
                "condition": row[2],
                "symbol": row[3],
                "threshold": row[4],
                "triggered_count": row[5],
                "created_at": row[6]
            })
        
        conn.close()
        return alerts


def main():
    import sys
    
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No action specified"}))
        return
    
    action = sys.argv[1]
    notifier = TelegramNotifier()
    
    if action == "send_message":
        message = sys.argv[2] if len(sys.argv) > 2 else "Test message"
        result = notifier.send_message(message)
        
    elif action == "send_alert":
        message = sys.argv[2] if len(sys.argv) > 2 else "Test alert"
        level = sys.argv[3] if len(sys.argv) > 3 else "info"
        result = notifier.send_alert(message, level)
        
    elif action == "send_trade_notification":
        trade_data = {
            "symbol": sys.argv[2] if len(sys.argv) > 2 else "BTC",
            "side": sys.argv[3] if len(sys.argv) > 3 else "buy",
            "amount": float(sys.argv[4]) if len(sys.argv) > 4 else 0.1,
            "price": float(sys.argv[5]) if len(sys.argv) > 5 else 45000,
            "total": float(sys.argv[6]) if len(sys.argv) > 6 else 4500,
            "fees": 4.5,
            "mode": "paper",
            "trade_id": "TEST-001",
            "reason": "Test trade"
        }
        result = notifier.send_trade_notification(trade_data)
        
    elif action == "set_alert":
        name = sys.argv[2] if len(sys.argv) > 2 else "Price Alert"
        condition = sys.argv[3] if len(sys.argv) > 3 else "above"
        symbol = sys.argv[4] if len(sys.argv) > 4 else "BTC"
        threshold = float(sys.argv[5]) if len(sys.argv) > 5 else 50000
        result = notifier.set_alert(name, condition, symbol, threshold)
        
    elif action == "get_alerts":
        result = {"success": True, "alerts": notifier.get_active_alerts()}
        
    elif action == "get_history":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        result = {"success": True, "notifications": notifier.get_notification_history(limit)}
        
    else:
        result = {"error": f"Unknown action: {action}"}
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
