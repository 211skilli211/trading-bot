#!/usr/bin/env python3
"""
PM2 Runner v2 - Smart Scheduler with Heartbeat
Runs continuously under PM2 management
"""

import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from scheduler_watchdog_v2 import ScheduleWatchdog
from cron_poster_v2 import check_and_post, emit_heartbeat, HEARTBEAT_FILE
from datetime import datetime
import time
import os

# Create initial heartbeat
emit_heartbeat()

print(f"[{datetime.now()}] PM2 Smart Scheduler started")
print(f"Features: Manual signals | Auto-detect | Alerts | Reminders | News")
print(f"Heartbeat file: {HEARTBEAT_FILE}")
print(f"Checking for posts every 60 seconds...")
print("-" * 60)

# Initialize
watchdog = ScheduleWatchdog()
loop_count = 0

# Main loop
while True:
    try:
        loop_count += 1
        
        # Check and send posts
        sent = check_and_post()
        
        # Log activity
        if sent > 0:
            print(f"[{datetime.now()}] ✅ Sent {sent} post(s)")
        
        # Heartbeat every loop (even when idle)
        emit_heartbeat()
        
        # Periodic status log (every 10 loops = 10 minutes)
        if loop_count % 10 == 0:
            stats = watchdog.get_stats()
            print(f"[{datetime.now()}] 💓 Heartbeat #{loop_count} | Pending: {stats['pending']} | Total: {stats['total_scheduled']}")
        
        time.sleep(60)  # Check every minute
        
    except KeyboardInterrupt:
        print(f"[{datetime.now()}] Shutting down...")
        break
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Error: {e}")
        import traceback
        print(f"[{datetime.now()}] Trace: {traceback.format_exc()}")
        time.sleep(60)
