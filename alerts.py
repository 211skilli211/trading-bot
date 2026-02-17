#!/usr/bin/env python3
"""
Alert Module - Telegram & Discord Notifications
Sends alerts for trade events, stop-losses, and errors
"""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class AlertManager:
    """Manages alerts across multiple channels."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Alert Manager.
        
        Args:
            config: Alert configuration dictionary
        """
        self.config = config
        self.enabled = config.get("enabled", False)
        
        # Telegram
        self.telegram_config = config.get("telegram", {})
        self.telegram_enabled = self.telegram_config.get("enabled", False)
        self.telegram_token = self.telegram_config.get("bot_token")
        self.telegram_chat_id = self.telegram_config.get("chat_id")
        
        # Discord
        self.discord_config = config.get("discord", {})
        self.discord_enabled = self.discord_config.get("enabled", False)
        self.discord_webhook = self.discord_config.get("webhook_url")
        
        print(f"[AlertManager] Initialized")
        print(f"  Telegram: {'✅' if self.telegram_enabled else '❌'}")
        print(f"  Discord: {'✅' if self.discord_enabled else '❌'}")
    
    def send_trade_alert(self, execution: Dict[str, Any]):
        """Send alert for executed trade."""
        if not self.enabled:
            return
        
        if execution.get("status") != "FILLED":
            return
        
        title = f"🤖 Trade Executed - {execution.get('trade_id')}"
        message = f"""
<b>Trade Alert</b>

Mode: {execution.get('mode')}
Decision: {execution.get('strategy_decision')}
Buy: {execution.get('buy_exchange')} @ ${execution.get('buy_price'):,.2f}
Sell: {execution.get('sell_exchange')} @ ${execution.get('sell_price'):,.2f}
Quantity: {execution.get('quantity'):.4f} BTC
Net P&L: ${execution.get('net_pnl', 0):,.2f}
Latency: {execution.get('total_latency_ms', 0):.1f}ms

Timestamp: {execution.get('timestamp')}
        """.strip()
        
        self._send_telegram(title, message)
        self._send_discord(title, message, color=0x00ff00)
    
    def send_stop_loss_alert(self, position: Dict[str, Any]):
        """Send alert for stop-loss triggered."""
        if not self.enabled:
            return
        
        title = f"🚨 Stop-Loss Triggered - {position.get('position_id')}"
        message = f"""
<b>Stop-Loss Alert</b>

Position: {position.get('position_id')}
Exchange: {position.get('exchange')}
Entry: ${position.get('entry_price'):,.2f}
Exit: ${position.get('close_price'):,.2f}
P&L: ${position.get('unrealized_pnl', 0):,.2f}

Timestamp: {position.get('close_timestamp')}
        """.strip()
        
        self._send_telegram(title, message)
        self._send_discord(title, message, color=0xff0000)
    
    def send_daily_limit_alert(self, daily_pnl: float, limit_pct: float):
        """Send alert when daily loss limit is hit."""
        if not self.enabled:
            return
        
        title = "⚠️ Daily Loss Limit Reached"
        message = f"""
<b>Risk Alert</b>

Daily P&L: ${daily_pnl:,.2f}
Limit: {limit_pct:.2%}

Trading has been halted for today.
Please review your strategy and risk parameters.

Timestamp: {datetime.now(timezone.utc).isoformat()}
        """.strip()
        
        self._send_telegram(title, message)
        self._send_discord(title, message, color=0xffa500)
    
    def send_error_alert(self, error_message: str):
        """Send alert for critical errors."""
        if not self.enabled:
            return
        
        title = "❌ Trading Bot Error"
        message = f"""
<b>Error Alert</b>

{error_message}

Timestamp: {datetime.now(timezone.utc).isoformat()}
        """.strip()
        
        self._send_telegram(title, message)
        self._send_discord(title, message, color=0xff0000)
    
    def _send_telegram(self, title: str, message: str):
        """Send Telegram notification."""
        if not self.telegram_enabled or not self.telegram_token or not self.telegram_chat_id:
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": f"<b>{title}</b>\n\n{message}",
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"[AlertManager] Telegram alert sent")
            
        except Exception as e:
            print(f"[AlertManager] Telegram error: {e}")
    
    def _send_discord(self, title: str, message: str, color: int = 0x00ff00):
        """Send Discord notification via webhook."""
        if not self.discord_enabled or not self.discord_webhook:
            return
        
        try:
            # Clean message for Discord (remove HTML tags)
            clean_message = message.replace("<b>", "**").replace("</b>", "**")
            
            payload = {
                "embeds": [{
                    "title": title,
                    "description": clean_message,
                    "color": color,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }]
            }
            
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            print(f"[AlertManager] Discord alert sent")
            
        except Exception as e:
            print(f"[AlertManager] Discord error: {e}")


if __name__ == "__main__":
    print("Alert Manager - Test Mode")
    print("=" * 60)
    print("\nNote: Set your bot tokens in config.json to test real alerts")
    print("This test will simulate alerts without sending them\n")
    
    # Test configuration (disabled - won't send real alerts)
    config = {
        "enabled": False,  # Set to True and add tokens to test
        "telegram": {
            "enabled": False,
            "bot_token": "YOUR_BOT_TOKEN",
            "chat_id": "YOUR_CHAT_ID"
        },
        "discord": {
            "enabled": False,
            "webhook_url": "YOUR_WEBHOOK_URL"
        }
    }
    
    alerts = AlertManager(config)
    
    # Simulate trade alert
    print("[Test] Trade Alert")
    trade_data = {
        "trade_id": "TEST_001",
        "mode": "PAPER",
        "status": "FILLED",
        "strategy_decision": "TRADE",
        "buy_exchange": "Binance",
        "sell_exchange": "Coinbase",
        "buy_price": 68000,
        "sell_price": 69000,
        "quantity": 0.01,
        "net_pnl": 8.50,
        "total_latency_ms": 250,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    alerts.send_trade_alert(trade_data)
    
    # Simulate stop-loss alert
    print("\n[Test] Stop-Loss Alert")
    position_data = {
        "position_id": "POS_001",
        "exchange": "Binance",
        "entry_price": 68000,
        "close_price": 66640,
        "unrealized_pnl": -136,
        "close_timestamp": datetime.now(timezone.utc).isoformat()
    }
    alerts.send_stop_loss_alert(position_data)
    
    # Simulate daily limit alert
    print("\n[Test] Daily Limit Alert")
    alerts.send_daily_limit_alert(daily_pnl=-500, limit_pct=0.05)
    
    print("\n✅ Alert tests completed (simulated)")
    print("\nTo enable real alerts:")
    print("1. Telegram: Get bot token from @BotFather")
    print("2. Discord: Create webhook in channel settings")
    print("3. Update config.json with your tokens")
    print("4. Set 'enabled': true in config.json")
