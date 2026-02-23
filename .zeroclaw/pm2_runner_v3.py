#!/usr/bin/env python3
"""
PM2 Runner v3 - Smart Scheduler (UTC time)
"""

import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from scheduler_watchdog_v2 import ScheduleWatchdog
from cron_poster_v2 import check_and_post, emit_heartbeat, HEARTBEAT_FILE
from datetime import datetime
import time

print(f"[{datetime.now()}] PM2 Smart Scheduler started")
print(f"Using system default timezone")
print(f"Features: Manual signals | Auto-detect | Alerts | Reminders | News")
print(f"Checking every 20 seconds...")
print("-" * 60)

watchdog = ScheduleWatchdog()
loop_count = 0

while True:
    try:
        loop_count += 1
        
        # Check and send
        sent = check_and_post()
        
        if sent > 0:
            print(f"[{datetime.now()}] ✅ Sent {sent} post(s)")
        
        emit_heartbeat()
        
        if loop_count % 30 == 0:  # Every ~10 min
            stats = watchdog.get_stats()
            print(f"[{datetime.now()}] 💓 #{loop_count} | Pending: {stats['pending']}")
        
        time.sleep(20)
        
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Error: {e}")
        time.sleep(20)
