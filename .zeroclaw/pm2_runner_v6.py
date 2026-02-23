#!/usr/bin/env python3
"""
PM2 Runner v6 - Fixes "Time Warp" bug by using system 'date' command
Gets real system time instead of cached Python env time
"""

import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from scheduler_watchdog_v2 import ScheduleWatchdog
from datetime import datetime
import subprocess
import time
import os

DEBUG_LOG = "/tmp/scheduler_debug.log"

def get_real_system_time():
    """Get real system time via 'date' command to bypass PM2's cached time"""
    try:
        raw_date = subprocess.check_output(['date', '+%Y-%m-%d %H:%M:%S']).decode().strip()
        return datetime.strptime(raw_date, '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        # Fallback to datetime.now() if date command fails
        return datetime.now()

def log(msg):
    ts = get_real_system_time().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(DEBUG_LOG, 'a') as f:
        f.write(line + "\n")

# Initial time check
real_now = get_real_system_time()
log(f"PM2 Runner v6 starting...")
log(f"Real System Time: {real_now}")
log(f"PID: {os.getpid()}")

watchdog = ScheduleWatchdog()
loop_count = 0

while True:
    try:
        loop_count += 1
        
        # Get REAL system time (not cached Python time)
        now = get_real_system_time()
        now_iso = now.isoformat()
        
        # Debug: Check pending posts using REAL time
        import sqlite3
        conn = sqlite3.connect("/tmp/trading_zeroclaw/.zeroclaw/scheduler.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM scheduled_posts WHERE sent=0 AND scheduled_time <= ?", (now_iso,))
        pending = c.fetchone()[0]
        
        if pending > 0:
            log(f"Found {pending} posts due (time: {now.strftime('%H:%M:%S')})")
        
        # Send posts
        sent = watchdog.check_and_send()
        
        if sent > 0:
            log(f"✅ SENT {sent} posts")
        
        if loop_count % 5 == 0:
            log(f"💓 Heartbeat #{loop_count}, pending: {pending}")
        
        conn.close()
        time.sleep(20)
        
    except Exception as e:
        log(f"❌ ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        time.sleep(20)
