#!/usr/bin/env python3
"""
Scheduled Posts Module for Trading Bot
Posts daily updates to Telegram channel at scheduled times
"""

import schedule
import time
import threading
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Default channel
DEFAULT_CHANNEL = "-1003637413591"
BOT_TOKEN = "8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"

class ScheduledPoster:
    """Handles scheduled posts to Telegram channel"""
    
    def __init__(self, channel_id: str = DEFAULT_CHANNEL):
        self.channel_id = channel_id
        self.bot_token = BOT_TOKEN
        self.running = False
        self.thread = None
        self.schedule_config = self._load_schedule()
        
    def _load_schedule(self) -> Dict[str, Any]:
        """Load schedule configuration"""
        config_file = "scheduled_posts_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        # Default schedule
        return {
            "enabled": True,
            "daily_summary": {
                "enabled": True,
                "time": "09:00",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            },
            "evening_update": {
                "enabled": True,
                "time": "18:00",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            },
            "market_open": {
                "enabled": False,
                "time": "09:30",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            },
            "market_close": {
                "enabled": False,
                "time": "16:00",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            }
        }
    
    def _save_schedule(self):
        """Save schedule configuration"""
        with open("scheduled_posts_config.json", 'w') as f:
            json.dump(self.schedule_config, f, indent=2)
    
    def post_to_channel(self, message: str) -> bool:
        """Post message to Telegram channel"""
        import urllib.request
        import json
        
        try:
            payload = {
                'chat_id': self.channel_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{self.bot_token}/sendMessage',
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())
                return result.get('ok', False)
                
        except Exception as e:
            print(f"[ScheduledPoster] Error posting: {e}")
            return False
    
    def generate_daily_summary(self) -> str:
        """Generate daily summary message"""
        from datetime import datetime
        
        # Try to get stats from database
        try:
            import sqlite3
            conn = sqlite3.connect('trades.db')
            cursor = conn.cursor()
            
            # Get today's stats
            cursor.execute("SELECT COUNT(*), SUM(net_pnl) FROM trades WHERE date(timestamp) = date('now')")
            today_trades, today_pnl = cursor.fetchone()
            today_trades = today_trades or 0
            today_pnl = today_pnl or 0
            
            # Get total stats
            cursor.execute("SELECT COUNT(*), SUM(net_pnl) FROM trades")
            total_trades, total_pnl = cursor.fetchone()
            total_trades = total_trades or 0
            total_pnl = total_pnl or 0
            
            # Get open positions
            cursor.execute("SELECT COUNT(*) FROM positions WHERE status='OPEN'")
            open_positions = cursor.fetchone()[0] or 0
            
            conn.close()
            
            pnl_emoji = "🟢" if today_pnl >= 0 else "🔴"
            total_pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
            
            message = f"""📊 <b>Daily Trading Summary</b>

📅 <b>{datetime.now().strftime('%A, %B %d, %Y')}</b>

📈 <b>Today's Performance:</b>
• Trades: {today_trades}
• P&L: {pnl_emoji} ${today_pnl:,.2f}

📊 <b>Overall Stats:</b>
• Total Trades: {total_trades}
• Total P&L: {total_pnl_emoji} ${total_pnl:,.2f}
• Open Positions: {open_positions}

💡 <b>Pro Tip:</b>
Check the dashboard for detailed analytics and AI signals!

🔗 <a href='http://localhost:8080'>Open Dashboard</a>

<i>Posted automatically by ZeroClaw Trading Bot</i>"""
            
        except Exception as e:
            print(f"[ScheduledPoster] Error generating summary: {e}")
            # Fallback message
            message = f"""📊 <b>Daily Trading Summary</b>

📅 <b>{datetime.now().strftime('%A, %B %d, %Y')}</b>

🤖 Bot is running and monitoring markets.

🔗 <a href='http://localhost:8080'>Check Dashboard</a> for live updates.

<i>Posted automatically by ZeroClaw Trading Bot</i>"""
        
        return message
    
    def generate_evening_update(self) -> str:
        """Generate evening market update"""
        message = f"""🌆 <b>Evening Market Update</b>

📅 <b>{datetime.now().strftime('%A, %B %d')}</b>

🌙 <b>Market Wrap-Up:</b>
• Day's trading completed
• Positions being monitored
• AI analyzing overnight opportunities

🎯 <b>What's Next:</b>
• Asian markets opening soon
• European session follows
• New York session tomorrow

💡 <b>Stay Tuned:</b>
Tomorrow's summary at 9:00 AM

🔗 <a href='http://localhost:8080'>View Dashboard</a>

<i>Good night from ZeroClaw Trading Bot 🤖</i>"""
        return message
    
    def send_daily_summary(self):
        """Send daily summary post"""
        print(f"[ScheduledPoster] Sending daily summary at {datetime.now()}")
        message = self.generate_daily_summary()
        if self.post_to_channel(message):
            print("[ScheduledPoster] Daily summary posted successfully")
        else:
            print("[ScheduledPoster] Failed to post daily summary")
    
    def send_evening_update(self):
        """Send evening update post"""
        print(f"[ScheduledPoster] Sending evening update at {datetime.now()}")
        message = self.generate_evening_update()
        if self.post_to_channel(message):
            print("[ScheduledPoster] Evening update posted successfully")
        else:
            print("[ScheduledPoster] Failed to post evening update")
    
    def setup_schedule(self):
        """Set up scheduled jobs"""
        # Clear existing jobs
        schedule.clear()
        
        if not self.schedule_config.get("enabled", True):
            print("[ScheduledPoster] Scheduling disabled")
            return
        
        # Daily summary
        daily_config = self.schedule_config.get("daily_summary", {})
        if daily_config.get("enabled", True):
            time_str = daily_config.get("time", "09:00")
            schedule.every().day.at(time_str).do(self.send_daily_summary)
            print(f"[ScheduledPoster] Daily summary scheduled for {time_str}")
        
        # Evening update
        evening_config = self.schedule_config.get("evening_update", {})
        if evening_config.get("enabled", True):
            time_str = evening_config.get("time", "18:00")
            schedule.every().day.at(time_str).do(self.send_evening_update)
            print(f"[ScheduledPoster] Evening update scheduled for {time_str}")
        
        # Market open (weekdays only)
        market_open_config = self.schedule_config.get("market_open", {})
        if market_open_config.get("enabled", False):
            time_str = market_open_config.get("time", "09:30")
            schedule.every().monday.at(time_str).do(self.send_market_open)
            schedule.every().tuesday.at(time_str).do(self.send_market_open)
            schedule.every().wednesday.at(time_str).do(self.send_market_open)
            schedule.every().thursday.at(time_str).do(self.send_market_open)
            schedule.every().friday.at(time_str).do(self.send_market_open)
            print(f"[ScheduledPoster] Market open scheduled for {time_str} (weekdays)")
        
        # Market close (weekdays only)
        market_close_config = self.schedule_config.get("market_close", {})
        if market_close_config.get("enabled", False):
            time_str = market_close_config.get("time", "16:00")
            schedule.every().monday.at(time_str).do(self.send_market_close)
            schedule.every().tuesday.at(time_str).do(self.send_market_close)
            schedule.every().wednesday.at(time_str).do(self.send_market_close)
            schedule.every().thursday.at(time_str).do(self.send_market_close)
            schedule.every().friday.at(time_str).do(self.send_market_close)
            print(f"[ScheduledPoster] Market close scheduled for {time_str} (weekdays)")
    
    def send_market_open(self):
        """Send market open notification"""
        message = """🔔 <b>Markets Are Open!</b>

📈 <b>New York Stock Exchange:</b> 9:30 AM EST
💹 <b>Crypto Markets:</b> 24/7 Active

🎯 <b>Today's Focus:</b>
• AI scanning for opportunities
• Multi-agents activated
• Risk management enabled

Good luck with today's trades! 🚀

<i>ZeroClaw Trading Bot</i>"""
        self.post_to_channel(message)
    
    def send_market_close(self):
        """Send market close notification"""
        message = """🔔 <b>Markets Closed</b>

📉 <b>New York Stock Exchange:</b> 4:00 PM EST
💹 <b>Crypto Markets:</b> Still trading 24/7

📊 <b>Day's Summary:</b>
• Check dashboard for full report
• After-hours analysis running
• Preparing for tomorrow

See you tomorrow! 👋

<i>ZeroClaw Trading Bot</i>"""
        self.post_to_channel(message)
    
    def run(self):
        """Run the scheduler loop"""
        print("[ScheduledPoster] Starting scheduler...")
        self.setup_schedule()
        
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            print("[ScheduledPoster] Already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        print("[ScheduledPoster] Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[ScheduledPoster] Scheduler stopped")
    
    def update_schedule(self, new_config: Dict[str, Any]):
        """Update schedule configuration"""
        self.schedule_config.update(new_config)
        self._save_schedule()
        self.setup_schedule()
        print("[ScheduledPoster] Schedule updated")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            "running": self.running,
            "channel_id": self.channel_id,
            "next_run": str(schedule.next_run()) if schedule.jobs else None,
            "jobs": [str(job) for job in schedule.jobs]
        }

# Global instance
_poster_instance: Optional[ScheduledPoster] = None

def get_poster() -> ScheduledPoster:
    """Get or create the scheduled poster instance"""
    global _poster_instance
    if _poster_instance is None:
        _poster_instance = ScheduledPoster()
    return _poster_instance

def start_scheduled_posts():
    """Start scheduled posting"""
    poster = get_poster()
    poster.start()
    return poster

def stop_scheduled_posts():
    """Stop scheduled posting"""
    global _poster_instance
    if _poster_instance:
        _poster_instance.stop()
        _poster_instance = None

if __name__ == "__main__":
    # Test the scheduler
    poster = ScheduledPoster()
    poster.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        poster.stop()
        print("Scheduler stopped")
