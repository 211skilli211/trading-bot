#!/usr/bin/env python3
"""
Independent Schedule Watchdog
Runs outside of ZeroClaw - survives bot restarts
Uses SQLite for atomic writes (no corruption)
"""

import sqlite3
import json
import os
import time
import urllib.request
from datetime import datetime
from threading import Thread

# Config
DB_FILE = "/tmp/trading_zeroclaw/.zeroclaw/scheduler.db"
BOT_TOKEN = "8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
DEFAULT_CHANNEL = "-1003637413591"
CHECK_INTERVAL = 30  # seconds

class ScheduleWatchdog:
    def __init__(self):
        self.running = False
        self.init_db()
    
    def init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id TEXT PRIMARY KEY,
                message TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                user_id TEXT NOT NULL,
                channel TEXT DEFAULT '-1003637413591',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sent INTEGER DEFAULT 0,
                sent_at TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print(f"[Watchdog] Database ready: {DB_FILE}")
    
    def schedule_post(self, message: str, when: str, user_id: str) -> dict:
        """Schedule a new post"""
        # Parse time (local timezone)
        scheduled_time = self._parse_time(when)
        if not scheduled_time:
            return {"success": False, "error": f"Cannot parse: '{when}'"}
        
        post_id = f"post_{int(time.time())}_{user_id}"
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scheduled_posts (id, message, scheduled_time, user_id, channel)
            VALUES (?, ?, ?, ?, ?)
        ''', (post_id, message, scheduled_time.isoformat(), user_id, DEFAULT_CHANNEL))
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "post_id": post_id,
            "scheduled_time": scheduled_time.strftime("%A, %B %d at %I:%M %p %Z"),
            "message_preview": message[:50] + "..." if len(message) > 50 else message
        }
    
    def _parse_time(self, when: str) -> datetime:
        """Parse natural time (local timezone)"""
        now = datetime.now()
        when_lower = when.lower().strip()
        
        import re
        
        # "in X minutes"
        match = re.search(r'(\d+)\s*min', when_lower)
        if match:
            from datetime import timedelta
            return now + timedelta(minutes=int(match.group(1)))
        
        # "in X hours"
        match = re.search(r'(\d+)\s*hour', when_lower)
        if match:
            from datetime import timedelta
            return now + timedelta(hours=int(match.group(1)))
        
        # "tomorrow"
        if "tomorrow" in when_lower:
            from datetime import timedelta
            tomorrow = now + timedelta(days=1)
            # Try to extract time
            for hour in range(24):
                if f"{hour}am" in when_lower or f"{hour}:00am" in when_lower:
                    return tomorrow.replace(hour=hour, minute=0, second=0)
                if f"{hour}pm" in when_lower or f"{hour}:00pm" in when_lower:
                    hour_24 = hour + 12 if hour != 12 else 12
                    return tomorrow.replace(hour=hour_24, minute=0, second=0)
            return tomorrow.replace(hour=9, minute=0, second=0)
        
        # Try ISO format
        try:
            return datetime.fromisoformat(when)
        except:
            pass
        
        return None
    
    def check_and_send(self):
        """Check for due posts and send them"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # Get unsent posts that are due
        cursor.execute('''
            SELECT id, message, channel FROM scheduled_posts
            WHERE sent = 0 AND scheduled_time <= ?
        ''', (now,))
        
        posts = cursor.fetchall()
        sent_count = 0
        
        for post_id, message, channel in posts:
            if self._send_to_telegram(message, channel):
                cursor.execute('''
                    UPDATE scheduled_posts
                    SET sent = 1, sent_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), post_id))
                sent_count += 1
                print(f"[Watchdog] Sent: {post_id}")
        
        conn.commit()
        conn.close()
        return sent_count
    
    def _send_to_telegram(self, message: str, channel: str) -> bool:
        """Send message to Telegram"""
        try:
            payload = {
                'chat_id': channel,
                'text': message,
                'parse_mode': 'HTML'
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get('ok', False)
        except Exception as e:
            print(f"[Watchdog] Send error: {e}")
            return False
    
    def list_user_posts(self, user_id: str) -> list:
        """List scheduled posts for a user"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, message, scheduled_time FROM scheduled_posts
            WHERE user_id = ? AND sent = 0
            ORDER BY scheduled_time ASC
        ''', (user_id,))
        posts = cursor.fetchall()
        conn.close()
        return posts
    
    def run(self):
        """Main loop"""
        print("[Watchdog] Started - checking every 30 seconds")
        self.running = True
        
        while self.running:
            try:
                sent = self.check_and_send()
                if sent > 0:
                    print(f"[Watchdog] Sent {sent} post(s)")
                time.sleep(CHECK_INTERVAL)
            except Exception as e:
                print(f"[Watchdog] Error: {e}")
                time.sleep(CHECK_INTERVAL)
    
    def start_daemon(self):
        """Start in background thread"""
        thread = Thread(target=self.run, daemon=True)
        thread.start()
        return thread

# Global instance
_watchdog = None

def get_watchdog():
    global _watchdog
    if _watchdog is None:
        _watchdog = ScheduleWatchdog()
    return _watchdog

if __name__ == "__main__":
    # Run standalone
    watchdog = ScheduleWatchdog()
    watchdog.run()
