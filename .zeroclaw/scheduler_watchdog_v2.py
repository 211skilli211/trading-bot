#!/usr/bin/env python3
"""
Smart Schedule Watchdog v2.1 - Time Warp Fix
Uses real system time via 'date' command
"""

import sqlite3
import json
import os
import time
import urllib.request
import subprocess
from datetime import datetime, timedelta
from threading import Thread
import re
import uuid

# Config
DB_FILE = "/tmp/trading_zeroclaw/.zeroclaw/scheduler.db"
BOT_TOKEN = "8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
DEFAULT_CHANNEL = "-1003637413591"
CHECK_INTERVAL = 30  # seconds

def get_real_system_time():
    """Get real system time via 'date' command to bypass PM2's cached time"""
    try:
        raw_date = subprocess.check_output(['date', '+%Y-%m-%d %H:%M:%S']).decode().strip()
        return datetime.strptime(raw_date, '%Y-%m-%d %H:%M:%S')
    except:
        return datetime.now()

class ScheduleWatchdog:
    """Persistent scheduler with PM2 management and time warp fix"""
    
    def __init__(self):
        self.running = False
        self.init_db()
    
    def init_db(self):
        """Initialize SQLite database with extended schema"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_uuid TEXT UNIQUE,
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'reminder',
                scheduled_time TEXT NOT NULL,
                user_id TEXT NOT NULL,
                channel TEXT DEFAULT '-1003637413591',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sent INTEGER DEFAULT 0,
                sent_at TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_uuid TEXT UNIQUE,
                pair TEXT NOT NULL,
                condition TEXT NOT NULL,
                target_price REAL NOT NULL,
                user_id TEXT NOT NULL,
                channel TEXT DEFAULT '-1003637413591',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                triggered INTEGER DEFAULT 0,
                triggered_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_type TEXT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                channel TEXT,
                user_id TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"[Watchdog] Database ready: {DB_FILE}")
    
    def schedule_post(self, message: str, when: str, user_id: str, 
                      channel: str = DEFAULT_CHANNEL, msg_type: str = 'reminder',
                      metadata: dict = None) -> dict:
        """Schedule a new post with type classification"""
        
        # Parse time using REAL system time
        scheduled_time = self._parse_time(when)
        if not scheduled_time:
            return {"success": False, "error": f"Cannot parse time: '{when}'"}
        
        # Convert scheduled time to AST for display in message
        scheduled_ast = scheduled_time - timedelta(hours=4)
        delivery_time_str = scheduled_ast.strftime('%I:%M %p AST')
        
        # Replace placeholder with actual delivery time
        message = message.replace('[DELIVERY_TIME]', delivery_time_str)
        
        post_uuid = str(uuid.uuid4())[:8]
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scheduled_posts 
            (post_uuid, message, message_type, scheduled_time, user_id, channel, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (post_uuid, message, msg_type, scheduled_time.isoformat(), 
              user_id, channel, json.dumps(metadata) if metadata else None))
        
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "post_id": post_id,
            "post_uuid": post_uuid,
            "scheduled_time": scheduled_ast.strftime("%A, %B %d at %I:%M %p AST"),
            "message_type": msg_type,
            "message_preview": message[:50] + "..." if len(message) > 50 else message
        }
    
    def _parse_time(self, when: str) -> datetime:
        """Parse natural time expressions using REAL system time"""
        now = get_real_system_time()  # Use REAL time
        when_lower = when.lower().strip()
        
        # "in X minutes"
        match = re.search(r'(\d+)\s*min', when_lower)
        if match:
            return now + timedelta(minutes=int(match.group(1)))
        
        # "in X hours"
        match = re.search(r'(\d+)\s*hour', when_lower)
        if match:
            return now + timedelta(hours=int(match.group(1)))
        
        # "in X seconds" (for testing)
        match = re.search(r'(\d+)\s*sec', when_lower)
        if match:
            return now + timedelta(seconds=int(match.group(1)))
        
        # "tomorrow at X"
        if "tomorrow" in when_lower:
            tomorrow = now + timedelta(days=1)
            time_match = re.search(r'(\d+):?(\d*)?\s*(am|pm)?', when_lower)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                ampm = time_match.group(3)
                if ampm == 'pm' and hour != 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Specific time today "at 3pm"
        time_match = re.search(r'at\s+(\d+):?(\d*)?\s*(am|pm)', when_lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3)
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target < now:
                target += timedelta(days=1)
            return target
        
        # Try ISO format
        try:
            return datetime.fromisoformat(when)
        except:
            pass
        
        return None
    
    def check_and_send(self) -> int:
        """Check for due posts and send them using REAL system time"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Use REAL system time for comparison
        now = get_real_system_time().isoformat()
        
        cursor.execute('''
            SELECT id, message, channel, message_type, user_id 
            FROM scheduled_posts
            WHERE sent = 0 AND scheduled_time <= ?
        ''', (now,))
        
        posts = cursor.fetchall()
        sent_count = 0
        
        for post_id, message, channel, msg_type, user_id in posts:
            if self._send_to_telegram(message, channel):
                cursor.execute('''
                    UPDATE scheduled_posts
                    SET sent = 1, sent_at = ?
                    WHERE id = ?
                ''', (get_real_system_time().isoformat(), post_id))
                
                cursor.execute('''
                    INSERT INTO sent_history (message_type, channel, user_id)
                    VALUES (?, ?, ?)
                ''', (msg_type, channel, user_id))
                
                sent_count += 1
                print(f"[Watchdog] Sent [{msg_type}]: ID {post_id}")
            else:
                print(f"[Watchdog] Failed to send: ID {post_id}")
        
        conn.commit()
        conn.close()
        return sent_count
    
    def _send_to_telegram(self, message: str, channel: str) -> bool:
        """Send message to Telegram with retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                payload = {
                    'chat_id': channel,
                    'text': message,
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': False
                }
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    result = json.loads(resp.read().decode())
                    return result.get('ok', False)
            except Exception as e:
                print(f"[Watchdog] Send error (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
        
        return False
    
    def list_user_posts(self, user_id: str, include_sent: bool = False) -> list:
        """List scheduled posts for a user"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        if include_sent:
            cursor.execute('''
                SELECT id, message, scheduled_time, message_type, sent 
                FROM scheduled_posts
                WHERE user_id = ?
                ORDER BY scheduled_time DESC
                LIMIT 10
            ''', (user_id,))
        else:
            cursor.execute('''
                SELECT id, message, scheduled_time, message_type, sent 
                FROM scheduled_posts
                WHERE user_id = ? AND sent = 0
                ORDER BY scheduled_time ASC
                LIMIT 10
            ''', (user_id,))
        
        posts = cursor.fetchall()
        conn.close()
        return posts
    
    def get_stats(self) -> dict:
        """Get scheduling statistics"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM scheduled_posts')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scheduled_posts WHERE sent = 0')
        pending = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM sent_history 
            WHERE date(sent_at) = date('now')
        ''')
        sent_today = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT message_type, COUNT(*) FROM scheduled_posts 
            GROUP BY message_type
        ''')
        by_type = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_scheduled": total,
            "pending": pending,
            "sent_today": sent_today,
            "by_type": by_type
        }
    
    def cancel_post(self, post_id: str, user_id: str) -> bool:
        """Cancel a scheduled post"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM scheduled_posts 
            WHERE id = ? AND user_id = ? AND sent = 0
        ''', (post_id, user_id))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def run(self):
        """Main loop for standalone execution"""
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

# Global instance
_watchdog = None

def get_watchdog():
    global _watchdog
    if _watchdog is None:
        _watchdog = ScheduleWatchdog()
    return _watchdog

if __name__ == "__main__":
    watchdog = ScheduleWatchdog()
    watchdog.run()
