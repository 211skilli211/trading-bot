#!/usr/bin/env python3
"""
Telegram Post Scheduler - User-Requested Scheduling
Stores scheduled posts and sends them at the right time
Also supports auto-generated content (signals, prices, arbitrage)
"""

import json
import os
import time
from datetime import datetime, timedelta
from threading import Thread, Lock
import subprocess

SCHEDULE_FILE = "/tmp/trading_zeroclaw/.zeroclaw/scheduled_posts.json"
AUTO_SCHEDULE_FILE = "/tmp/trading_zeroclaw/.zeroclaw/auto_schedules.json"
BOT_TOKEN = "8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
DEFAULT_CHANNEL = "-1003637413591"

# Content generators
def generate_arbitrage_alert():
    """Generate arbitrage opportunity post"""
    try:
        # Try to get real arbitrage data
        import sys
        sys.path.insert(0, '/root/trading-bot')
        from find_arbitrage import ArbitrageFinder
        
        finder = ArbitrageFinder()
        opps = finder.find_cex_arbitrage(['BTC', 'ETH', 'SOL'])
        
        if opps:
            top = opps[0]
            return f"""🔍 <b>Arbitrage Alert!</b>

🟢 {top['symbol']} Price Difference

💰 Buy: {top['buy_exchange']} @ ${top['buy_price']:,.2f}
💰 Sell: {top['sell_exchange']} @ ${top['sell_price']:,.2f}
📊 Spread: {top['spread_percent']:.2f}%
💵 Est. Profit: {top['profit_after_fees']:.2f}%

⚡ Act fast - spreads change quickly!

<i>ZeroClaw Arbitrage Scanner</i>"""
    except:
        pass
    
    return None

def generate_price_update():
    """Generate price update post"""
    try:
        import requests
        resp = requests.get('http://localhost:8080/api/zeroclaw/predictions', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            prices = data.get('prices', {})
            
            msg = "📊 <b>Price Update</b>\n\n"
            for symbol, price in list(prices.items())[:5]:
                msg += f"• {symbol}: ${price:,.2f}\n"
            msg += "\n<i>Live from ZeroClaw</i>"
            return msg
    except:
        pass
    
    # Fallback
    return """📊 <b>Market Update</b>

Markets are active! 

Check the dashboard for live prices and signals.

🔗 http://localhost:8080

<i>ZeroClaw Trading Bot</i>"""

def generate_signal_summary():
    """Generate AI signals summary"""
    try:
        import requests
        resp = requests.get('http://localhost:8080/api/zeroclaw/predictions', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            predictions = data.get('predictions', [])
            
            if predictions:
                msg = "🤖 <b>AI Signal Update</b>\n\n"
                for pred in predictions[:3]:
                    symbol = pred.get('symbol', 'N/A')
                    direction = pred.get('direction', 'HOLD')
                    confidence = pred.get('confidence', 0)
                    emoji = "🟢" if direction == "BUY" else "🔴" if direction == "SELL" else "⚪"
                    msg += f"{emoji} {symbol}: <b>{direction}</b> ({confidence}%)\n"
                msg += "\n<i>AI-Powered by ZeroClaw</i>"
                return msg
    except:
        pass
    
    return None

CONTENT_GENERATORS = {
    'arbitrage': generate_arbitrage_alert,
    'prices': generate_price_update,
    'signals': generate_signal_summary,
    'market': generate_price_update,
}

class PostScheduler:
    def __init__(self):
        self.posts = []
        self.auto_schedules = []
        self.lock = Lock()
        self.running = False
        self.thread = None
        self.load_posts()
        self.load_auto_schedules()
    
    def load_posts(self):
        """Load scheduled posts from file"""
        if os.path.exists(SCHEDULE_FILE):
            try:
                with open(SCHEDULE_FILE, 'r') as f:
                    self.posts = json.load(f)
            except:
                self.posts = []
        else:
            self.posts = []
    
    def save_posts(self):
        """Save scheduled posts to file"""
        with self.lock:
            with open(SCHEDULE_FILE, 'w') as f:
                json.dump(self.posts, f, indent=2)
    
    def load_auto_schedules(self):
        """Load auto-generated content schedules"""
        if os.path.exists(AUTO_SCHEDULE_FILE):
            try:
                with open(AUTO_SCHEDULE_FILE, 'r') as f:
                    self.auto_schedules = json.load(f)
            except:
                self.auto_schedules = []
        else:
            self.auto_schedules = []
    
    def save_auto_schedules(self):
        """Save auto schedules to file"""
        with self.lock:
            with open(AUTO_SCHEDULE_FILE, 'w') as f:
                json.dump(self.auto_schedules, f, indent=2)
    
    def create_auto_schedule(self, content_type: str, frequency: str, user_id: str) -> dict:
        """
        Create auto-generated content schedule
        content_type: 'arbitrage', 'prices', 'signals', 'market'
        frequency: 'hourly', 'every_4_hours', 'twice_daily', 'daily', 'weekly'
        """
        if content_type not in CONTENT_GENERATORS:
            return {"success": False, "error": f"Unknown content type: {content_type}"}
        
        schedule_id = f"auto_{content_type}_{int(time.time())}"
        
        # Parse frequency
        schedule_info = self._parse_frequency(frequency)
        if not schedule_info:
            return {"success": False, "error": f"Unknown frequency: {frequency}"}
        
        auto_schedule = {
            "id": schedule_id,
            "content_type": content_type,
            "frequency": frequency,
            "user_id": user_id,
            "channel": DEFAULT_CHANNEL,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "enabled": True,
            "schedule_info": schedule_info
        }
        
        with self.lock:
            self.auto_schedules.append(auto_schedule)
        
        self.save_auto_schedules()
        
        return {
            "success": True,
            "schedule_id": schedule_id,
            "content_type": content_type,
            "frequency": frequency,
            "next_run": self._calculate_next_run(schedule_info).strftime("%Y-%m-%d %I:%M %p")
        }
    
    def _parse_frequency(self, frequency: str) -> dict:
        """Parse frequency string into schedule info"""
        freq_lower = frequency.lower().replace(" ", "_")
        
        schedules = {
            "hourly": {"interval_minutes": 60},
            "every_hour": {"interval_minutes": 60},
            "every_2_hours": {"interval_minutes": 120},
            "every_4_hours": {"interval_minutes": 240},
            "every_6_hours": {"interval_minutes": 360},
            "twice_daily": {"times": ["09:00", "21:00"]},
            "3x_daily": {"times": ["08:00", "14:00", "20:00"]},
            "daily": {"times": ["09:00"]},
            "weekly": {"times": ["monday 09:00"]},
        }
        
        return schedules.get(freq_lower)
    
    def _calculate_next_run(self, schedule_info: dict) -> datetime:
        """Calculate next run time from schedule info"""
        now = datetime.now()
        
        if "interval_minutes" in schedule_info:
            return now + timedelta(minutes=schedule_info["interval_minutes"])
        
        if "times" in schedule_info:
            for time_str in schedule_info["times"]:
                if "monday" in time_str.lower():
                    # Weekly
                    days_until_monday = (7 - now.weekday()) % 7
                    if days_until_monday == 0 and now.hour < 9:
                        return now.replace(hour=9, minute=0, second=0)
                    next_monday = now + timedelta(days=days_until_monday if days_until_monday > 0 else 7)
                    return next_monday.replace(hour=9, minute=0, second=0)
                else:
                    # Daily times
                    hour, minute = map(int, time_str.split(":"))
                    target = now.replace(hour=hour, minute=minute, second=0)
                    if target > now:
                        return target
            # All times passed, use first one tomorrow
            hour, minute = map(int, schedule_info["times"][0].split(":"))
            return (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0)
        
        return now + timedelta(hours=1)  # Default
    
    def check_auto_schedules(self):
        """Check and run auto schedules"""
        now = datetime.now()
        
        for schedule in self.auto_schedules:
            if not schedule.get("enabled", True):
                continue
            
            last_run = schedule.get("last_run")
            if last_run:
                last_run = datetime.fromisoformat(last_run)
            
            should_run = False
            schedule_info = schedule.get("schedule_info", {})
            
            if "interval_minutes" in schedule_info:
                if not last_run or (now - last_run).total_seconds() / 60 >= schedule_info["interval_minutes"]:
                    should_run = True
            
            elif "times" in schedule_info:
                for time_str in schedule_info["times"]:
                    hour, minute = map(int, time_str.split(":"))
                    if now.hour == hour and now.minute == minute:
                        if not last_run or (now - last_run).total_seconds() > 3600:  # Run once per hour
                            should_run = True
                            break
            
            if should_run:
                print(f"[Scheduler] Running auto schedule: {schedule['id']}")
                content_type = schedule["content_type"]
                generator = CONTENT_GENERATORS.get(content_type)
                
                if generator:
                    message = generator()
                    if message:
                        success = self.send_post({"channel": schedule["channel"], "message": message})
                        if success:
                            print(f"[Scheduler] Auto post sent: {content_type}")
                        else:
                            print(f"[Scheduler] Failed to send auto post")
                
                schedule["last_run"] = now.isoformat()
                self.save_auto_schedules()
    
    def list_auto_schedules(self, user_id: str) -> list:
        """List all auto schedules for a user"""
        return [s for s in self.auto_schedules if s["user_id"] == user_id]
    
    def delete_auto_schedule(self, schedule_id: str, user_id: str) -> bool:
        """Delete an auto schedule"""
        with self.lock:
            original_len = len(self.auto_schedules)
            self.auto_schedules = [s for s in self.auto_schedules 
                                   if not (s["id"] == schedule_id and s["user_id"] == user_id)]
            if len(self.auto_schedules) < original_len:
                self.save_auto_schedules()
                return True
        return False
    
    def schedule_post(self, message: str, when: str, user_id: str) -> dict:
        """
        Schedule a new post
        when: 'tomorrow 9am', 'in 2 hours', '2026-02-23 14:30', etc.
        """
        post_id = f"post_{int(time.time())}_{user_id}"
        
        # Parse the time
        scheduled_time = self._parse_time(when)
        
        if not scheduled_time:
            return {"success": False, "error": f"Could not understand time: '{when}'"}
        
        post = {
            "id": post_id,
            "message": message,
            "scheduled_time": scheduled_time.isoformat(),
            "user_id": user_id,
            "channel": DEFAULT_CHANNEL,
            "created_at": datetime.now().isoformat(),
            "sent": False
        }
        
        with self.lock:
            self.posts.append(post)
        
        self.save_posts()
        
        # Format time for display
        time_str = scheduled_time.strftime("%A, %B %d at %I:%M %p")
        
        return {
            "success": True,
            "post_id": post_id,
            "scheduled_time": time_str,
            "message": message[:50] + "..." if len(message) > 50 else message
        }
    
    def _parse_time(self, when: str) -> datetime:
        """Parse natural time expressions"""
        now = datetime.now()
        when_lower = when.lower().strip()
        
        # Tomorrow at specific time
        if "tomorrow" in when_lower:
            tomorrow = now + timedelta(days=1)
            # Try to extract time
            for hour in range(24):
                for suffix in [f"{hour}am", f"{hour}:00am", f"{hour} pm", f"{hour}:00pm"]:
                    if suffix in when_lower.replace(" ", ""):
                        if "pm" in suffix and hour != 12:
                            hour += 12
                        if "am" in suffix and hour == 12:
                            hour = 0
                        return tomorrow.replace(hour=hour % 24, minute=0, second=0, microsecond=0)
            # Default to 9am tomorrow
            return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # In X minutes/hours
        if "in" in when_lower:
            import re
            # Minutes
            match = re.search(r'(\d+)\s*min', when_lower)
            if match:
                minutes = int(match.group(1))
                return now + timedelta(minutes=minutes)
            # Hours
            match = re.search(r'(\d+)\s*hour', when_lower)
            if match:
                hours = int(match.group(1))
                return now + timedelta(hours=hours)
        
        # Specific time today
        for hour in range(24):
            for suffix in [f"{hour}am", f"{hour}:00am", f"{hour} pm", f"{hour}:00pm"]:
                if suffix in when_lower.replace(" ", ""):
                    if "pm" in suffix and hour != 12:
                        hour += 12
                    if "am" in suffix and hour == 12:
                        hour = 0
                    target = now.replace(hour=hour % 24, minute=0, second=0, microsecond=0)
                    if target < now:
                        target += timedelta(days=1)  # Next day if already passed
                    return target
        
        # Try ISO format
        try:
            return datetime.fromisoformat(when)
        except:
            pass
        
        return None
    
    def get_user_posts(self, user_id: str) -> list:
        """Get all scheduled posts for a user"""
        with self.lock:
            return [p for p in self.posts if p["user_id"] == user_id and not p["sent"]]
    
    def cancel_post(self, post_id: str, user_id: str) -> bool:
        """Cancel a scheduled post"""
        with self.lock:
            original_len = len(self.posts)
            self.posts = [p for p in self.posts if not (p["id"] == post_id and p["user_id"] == user_id)]
            if len(self.posts) < original_len:
                self.save_posts()
                return True
        return False
    
    def send_post(self, post: dict) -> bool:
        """Send a post to Telegram channel"""
        try:
            import urllib.request
            import json
            
            payload = {
                'chat_id': post["channel"],
                'text': post["message"],
                'parse_mode': 'HTML'
            }
            
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())
                return result.get('ok', False)
        except Exception as e:
            print(f"[Scheduler] Error sending post: {e}")
            return False
    
    def check_and_send(self):
        """Check for posts that need to be sent"""
        now = datetime.now()
        posts_to_send = []
        
        with self.lock:
            for post in self.posts:
                if post["sent"]:
                    continue
                scheduled = datetime.fromisoformat(post["scheduled_time"])
                if scheduled <= now:
                    posts_to_send.append(post)
        
        for post in posts_to_send:
            print(f"[Scheduler] Sending scheduled post: {post['id']}")
            if self.send_post(post):
                post["sent"] = True
                post["sent_at"] = datetime.now().isoformat()
                print(f"[Scheduler] Post sent successfully")
            else:
                print(f"[Scheduler] Failed to send post")
        
        if posts_to_send:
            self.save_posts()
        
        # Also check auto schedules
        self.check_auto_schedules()
    
    def run(self):
        """Main scheduler loop"""
        print("[Scheduler] Started")
        while self.running:
            self.check_and_send()
            time.sleep(30)  # Check every 30 seconds
    
    def start(self):
        """Start the scheduler thread"""
        if not self.running:
            self.running = True
            self.thread = Thread(target=self.run, daemon=True)
            self.thread.start()
            print("[Scheduler] Thread started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

# Global instance
_scheduler = None

def get_scheduler() -> PostScheduler:
    """Get or create scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = PostScheduler()
    return _scheduler

def start_scheduler():
    """Start the scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    # Test
    scheduler = PostScheduler()
    
    # Test scheduling
    result = scheduler.schedule_post(
        "🚀 BTC to the moon!",
        "in 1 minute",
        "test_user"
    )
    print(f"Scheduled: {result}")
    
    # Start and run
    scheduler.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
