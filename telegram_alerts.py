#!/usr/bin/env python3
"""
Telegram Alert Module for 211Skilli Trading Bot
"""

import json
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramAlerter:
    def __init__(self, config_path="alerts_config.json"):
        self.config_path = config_path
        self.config = None
        self.enabled = False
        self._load_config()
    
    def _load_config(self):
        """Load alert configuration"""
        try:
            with open(self.config_path) as f:
                self.config = json.load(f)
            self.enabled = self.config.get("enabled", False)
            if self.enabled:
                logger.info("✅ Telegram alerts enabled")
        except FileNotFoundError:
            logger.info("ℹ️  Telegram alerts not configured (alerts_config.json not found)")
        except Exception as e:
            logger.error(f"❌ Failed to load alerts config: {e}")
    
    def send_message(self, message, parse_mode="HTML", priority=False):
        """Send a message to Telegram"""
        if not self.enabled or not self.config:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.config['bot_token']}/sendMessage"
            payload = {
                "chat_id": self.config["chat_id"],
                "text": message,
                "parse_mode": parse_mode,
                "disable_notification": not priority
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    def trade_alert(self, trade_type, exchange, symbol, amount, price, pnl=None):
        """Send trade execution alert"""
        if not self.config.get("alert_on_trade", True):
            return
        
        emoji = "🟢" if trade_type == "BUY" else "🔴"
        pnl_text = ""
        if pnl is not None:
            pnl_emoji = "📈" if pnl >= 0 else "📉"
            pnl_text = f"\n{pnl_emoji} <b>P&L:</b> ${pnl:+.2f}"
        
        message = f"""
{emoji} <b>Trade Executed</b>

<b>Type:</b> {trade_type}
<b>Exchange:</b> {exchange}
<b>Symbol:</b> {symbol}
<b>Amount:</b> {amount}
<b>Price:</b> ${price:.4f}{pnl_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        self.send_message(message, priority=True)
    
    def solana_swap_alert(self, from_token, to_token, amount_in, amount_out, tx_signature=None):
        """Send Solana DEX swap alert"""
        tx_link = ""
        if tx_signature:
            tx_link = f"\n<a href='https://solscan.io/tx/{tx_signature}'>View on Solscan</a>"
        
        message = f"""
💎 <b>Solana Swap Executed</b>

<b>From:</b> {amount_in:.6f} {from_token}
<b>To:</b> {amount_out:.6f} {to_token}
<b>Rate:</b> 1 {from_token} = {amount_out/amount_in:.6f} {to_token}{tx_link}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        self.send_message(message, priority=True)
    
    def error_alert(self, error_message, component="Bot"):
        """Send error alert"""
        if not self.config.get("alert_on_error", True):
            return
        
        message = f"""
⚠️ <b>{component} Error</b>

<pre>{error_message[:500]}</pre>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        self.send_message(message, priority=True)
    
    def daily_summary(self, total_trades, total_pnl, win_rate, best_trade=None):
        """Send daily summary"""
        if not self.config.get("alert_daily_summary", True):
            return
        
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        
        message = f"""
📊 <b>Daily Trading Summary</b>

📈 <b>Total Trades:</b> {total_trades}
{pnl_emoji} <b>Total P&L:</b> ${total_pnl:+.2f}
🎯 <b>Win Rate:</b> {win_rate:.1f}%
        """.strip()
        
        if best_trade:
            message += f"\n⭐ <b>Best Trade:</b> ${best_trade:+.2f}"
        
        message += f"\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self.send_message(message)

# Singleton instance
_alerter = None

def get_alerter():
    global _alerter
    if _alerter is None:
        _alerter = TelegramAlerter()
    return _alerter

if __name__ == "__main__":
    # Test mode
    alerter = TelegramAlerter()
    if alerter.enabled:
        print("✅ Telegram alerter configured")
        alerter.send_message("🧪 <b>Test Alert</b>\n\nTelegram alerts are working!")
    else:
        print("ℹ️  Telegram alerts not configured. Run setup_telegram.py first.")
