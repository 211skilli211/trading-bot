#!/usr/bin/env python3
"""
Simple Post Scheduler - No external dependencies
Uses only Python standard library
"""

import json
import os
import time
from datetime import datetime, timedelta
from threading import Thread, Lock

SCHEDULE_FILE = "/tmp/trading_zeroclaw/.zeroclaw/scheduled_posts.json"
BOT_TOKEN = "8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
DEFAULT_CHANNEL = "-1003637413591"

class SimpleScheduler:
    def __init__(self):
        self.posts = []
        self.lock = Lock()
        self.running = False
        self.thread = None
        self.load_posts()
    
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
    
    def schedule_post(self, message: str, when: str, user_id: str) -> dict:
        """Schedule a new post"""
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
        
        # Handle "in X minutes"
        if "minute" in when_lower:
            import re
            match = re.search(r'(\d+)\s*min', when_lower)
            if match:
                minutes = int(match.group(1))
                return now + timedelta(minutes=minutes)
        
        # Handle "in X hours"
        if "hour" in when_lower:
            import re
            match = re.search(r'(\d+)\s*hour', when_lower)
            if match:
                hours = int(match.group(1))
                return now + timedelta(hours=hours)
        
        # Handle "tomorrow"
        if "tomorrow" in when_lower:
            tomorrow = now + timedelta(days=1)
            # Try to extract time
            for hour in range(24):
                for suffix in [f"{hour}am", f"{hour}:00am"]:
                    if suffix in when_lower.replace(" ", ""):
                        return tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
                for suffix in [f"{hour}pm", f"{hour}:00pm"]:
                    if suffix in when_lower.replace(" ", ""):
                        hour_24 = hour + 12 if hour != 12 else 12
                        return tomorrow.replace(hour=hour_24, minute=0, second=0, microsecond=0)
            # Default to 9am tomorrow
            return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Try ISO format
        try:
            return datetime.fromisoformat(when)
        except:
            pass
        
        return None
    
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
            print(f"[Scheduler] Error sending: {e}")
            return False
    
    def check_and_send(self):
        """Check for posts that need to be sent"""
        now = datetime.now()
        posts_to_send = []
        
        with self.lock:
            for post in self.posts:
                if post.get("sent"):
                    continue
                try:
                    scheduled = datetime.fromisoformat(post["scheduled_time"])
                    if scheduled <= now:
                        posts_to_send.append(post)
                except:
                    continue
        
        for post in posts_to_send:
            print(f"[Scheduler] Sending post: {post['id']}")
            if self.send_post(post):
                post["sent"] = True
                post["sent_at"] = datetime.now().isoformat()
                print(f"[Scheduler] Sent successfully")
            else:
                print(f"[Scheduler] Failed to send")
        
        if posts_to_send:
            self.save_posts()
    
    def run(self):
        """Main scheduler loop - runs forever"""
        print("[Scheduler] Started")
        while self.running:
            try:
                self.check_and_send()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                print(f"[Scheduler] Error in loop: {e}")
                time.sleep(10)
    
    def start(self):
        """Start the scheduler thread"""
        if self.running:
            print("[Scheduler] Already running")
            return
        
        self.running = True
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()
        print("[Scheduler] Thread started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[Scheduler] Stopped")
    
    def get_user_posts(self, user_id: str) -> list:
        """Get all scheduled posts for a user"""
        return [p for p in self.posts if p["user_id"] == user_id and not p.get("sent")]
    
    def cancel_post(self, post_id: str, user_id: str) -> bool:
        """Cancel a scheduled post"""
        with self.lock:
            original_len = len(self.posts)
            self.posts = [p for p in self.posts if not (p["id"] == post_id and p["user_id"] == user_id)]
            if len(self.posts) < original_len:
                self.save_posts()
                return True
        return False

# Global instance
_scheduler = None

def get_scheduler():
    """Get or create scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = SimpleScheduler()
    return _scheduler

if __name__ == "__main__":
    scheduler = SimpleScheduler()
    scheduler.start()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
