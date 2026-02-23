#!/usr/bin/env python3
"""
Cron-based poster - runs every minute via crontab
Most reliable for Termux/Android
"""

import sqlite3
import json
import urllib.request
from datetime import datetime
import os
import sys

DB_FILE = "/tmp/trading_zeroclaw/.zeroclaw/scheduler.db"
BOT_TOKEN = "8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
LOG_FILE = "/tmp/cron_poster.log"

def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now()}] {msg}\n")

def send_to_telegram(message, channel):
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
        log(f"Send error: {e}")
        return False

def check_and_post():
    if not os.path.exists(DB_FILE):
        log("Database not found")
        return 0
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    # Get overdue posts
    cursor.execute('''
        SELECT id, message, channel FROM scheduled_posts
        WHERE sent = 0 AND scheduled_time <= ?
    ''', (now,))
    
    posts = cursor.fetchall()
    sent_count = 0
    
    for post_id, message, channel in posts:
        log(f"Sending: {post_id}")
        if send_to_telegram(message, channel):
            cursor.execute('''
                UPDATE scheduled_posts SET sent = 1, sent_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), post_id))
            sent_count += 1
            log(f"Sent successfully: {post_id}")
        else:
            log(f"Failed to send: {post_id}")
    
    conn.commit()
    conn.close()
    
    if sent_count > 0:
        log(f"Total sent: {sent_count}")
    
    return sent_count

if __name__ == "__main__":
    sent = check_and_post()
    sys.exit(0 if sent >= 0 else 1)
