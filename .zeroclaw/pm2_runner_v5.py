#!/usr/bin/env python3
"""
PM2 Runner v5 - Uses Unix timestamps for consistency
"""

import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from scheduler_watchdog_v2 import ScheduleWatchdog
from datetime import datetime
import time
import os

# Log file for debugging
DEBUG_LOG = "/tmp/scheduler_debug.log"

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(DEBUG_LOG, 'a') as f:
        f.write(line + "\n")

log("PM2 Runner v5 starting...")
log(f"PID: {os.getpid()}")

watchdog = ScheduleWatchdog()
loop_count = 0

while True:
    try:
        loop_count += 1
        
        # Debug: Check pending posts
        import sqlite3
        conn = sqlite3.connect("/tmp/trading_zeroclaw/.zeroclaw/scheduler.db")
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("SELECT COUNT(*) FROM scheduled_posts WHERE sent=0 AND scheduled_time <= ?", (now,))
        pending = c.fetchone()[0]
        conn.close()
        
        if pending > 0:
            log(f"Found {pending} posts to send")
        
        # Send posts
        sent = watchdog.check_and_send()
        
        if sent > 0:
            log(f"✅ SENT {sent} posts")
        
        if loop_count % 5 == 0:
            log(f"💓 Heartbeat #{loop_count}, pending: {pending}")
        
        time.sleep(20)
        
    except Exception as e:
        log(f"❌ ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        time.sleep(20)
