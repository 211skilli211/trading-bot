"""
Polymarket Smart Money Module — WhatsApp Alerts
Sends smart money signals and summaries via WhatsApp.
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from config import config
from database import get_unalerted_signals, mark_signals_alerted, get_smart_wallets

logger = logging.getLogger(__name__)


class WhatsAppAlerter:
    """Sends WhatsApp alerts for smart money signals."""
    
    def __init__(self):
        self.enabled = config.alerts.whatsapp_enabled
        self.min_score = config.alerts.min_signal_score
    
    def send_signal_alerts(self) -> List[Dict]:
        """Send alerts for unalerted signals."""
        if not self.enabled:
            logger.info("WhatsApp alerts disabled")
            return []
        
        signals = get_unalerted_signals(min_score=self.min_score)
        if not signals:
            logger.info("No new signals to alert")
            return []
        
        sent = []
        for signal in signals:
            message = self._format_signal_message(signal)
            if message:
                success = self._send_whatsapp(message)
                if success:
                    mark_signals_alerted([signal["id"]])
                    sent.append({
                        "signal_id": signal["id"],
                        "strategy": signal["strategy"],
                        "score": signal["score"],
                        "wallet": signal["wallet_address"][:10] + "...",
                        "sent_at": datetime.now(timezone.utc).isoformat()
                    })
        
        logger.info(f"Sent {len(sent)} WhatsApp alerts")
        return sent
    
    def send_daily_summary(self) -> Optional[str]:
        """Send daily summary of smart money activity."""
        if not self.enabled:
            return None
        
        smart_wallets = get_smart_wallets(min_score=50, limit=10)
        signals = get_unalerted_signals(min_score=0)
        
        message = self._format_daily_summary(smart_wallets, signals)
        success = self._send_whatsapp(message)
        
        if success:
            logger.info("Daily summary sent")
            return message
        return None
    
    def _format_signal_message(self, signal: Dict) -> str:
        """Format a signal into a WhatsApp message."""
        strategy = signal.get("strategy", "unknown")
        score = signal.get("score", 0)
        wallet = signal.get("wallet_address", "unknown")
        market = signal.get("market_question", "Unknown market")
        win_rate = signal.get("win_rate", 0)
        wallet_volume = signal.get("wallet_volume", 0)
        
        # Strategy emoji and label
        if strategy == "whale":
            emoji = "🐋"
            label = "WHALE ALERT"
        elif strategy == "win_rate":
            emoji = "👑"
            label = "WINNER ALERT"
        elif strategy == "early_bird":
            emoji = "🐦"
            label = "EARLY BIRD"
        else:
            emoji = "📊"
            label = "SIGNAL"
        
        # Truncate market question
        if len(market) > 80:
            market = market[:77] + "..."
        
        message = f"""{emoji} *{label}*

📍 Market: {market}
💰 Wallet: `{wallet[:8]}...{wallet[-4:]}`
📊 Score: {score:.0f}/100
🎯 Win Rate: {win_rate:.0%}
💵 Volume: ${wallet_volume:,.0f}

_{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"""
        
        return message
    
    def _format_daily_summary(self, wallets: List[Dict], signals: List[Dict]) -> str:
        """Format daily summary message."""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Count signals by strategy
        whale_count = sum(1 for s in signals if s.get("strategy") == "whale")
        winner_count = sum(1 for s in signals if s.get("strategy") == "win_rate")
        early_count = sum(1 for s in signals if s.get("strategy") == "early_bird")
        
        # Top wallets
        top_wallets = ""
        for i, w in enumerate(wallets[:5], 1):
            addr = w["address"][:8] + "..." + w["address"][-4:]
            top_wallets += f"  {i}. `{addr}` — Score: {w['smart_money_score']:.0f} | Win: {w['win_rate']:.0%} | Vol: ${w['total_volume']:,.0f}\n"
        
        message = f"""📊 *Polymarket Smart Money Daily Summary*
📅 {today}

*Signals Today:*
🐋 Whale: {whale_count}
👑 Winner: {winner_count}
🐦 Early Bird: {early_count}

*Top Smart Wallets:*
{top_wallets}
_Keep tracking, stay sharp!_"""
        
        return message
    
    def _send_whatsapp(self, message: str) -> bool:
        """
        Send a WhatsApp message.
        
        This integrates with the Hermes Agent send_message tool.
        When running as a cron job or standalone script, this will
        use the Hermes CLI to send the message.
        """
        try:
            # When running inside Hermes Agent context, use the send_message tool
            # When running standalone, we'll use a subprocess call to hermes
            import subprocess
            import shlex
            
            # Escape the message for shell
            escaped = message.replace('"', '\\"').replace('$', '\\$')
            
            # Use hermes CLI to send WhatsApp message
            cmd = f'hermes send --to whatsapp:211 --message "{escaped}"'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                logger.info("WhatsApp message sent successfully")
                return True
            else:
                logger.error(f"WhatsApp send failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False


def run_alerts() -> List[Dict]:
    """Run alert cycle."""
    alerter = WhatsAppAlerter()
    return alerter.send_signal_alerts()


def send_daily_summary() -> Optional[str]:
    """Send daily summary."""
    alerter = WhatsAppAlerter()
    return alerter.send_daily_summary()
