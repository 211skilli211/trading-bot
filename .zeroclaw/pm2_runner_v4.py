#!/usr/bin/env python3
"""
PM2 Runner v4 - Simplified & Debugged
"""

import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')

from scheduler_watchdog_v2 import ScheduleWatchdog
from datetime import datetime
import time

print(f"[{datetime.now()}] PM2 Runner v4 starting...")

# Create watchdog once
watchdog = ScheduleWatchdog()
loop_count = 0

print(f"[{datetime.now()}] Entering main loop...")

while True:
    try:
        loop_count += 1
        now = datetime.now()
        
        # Check for posts
        sent = watchdog.check_and_send()
        
        if sent > 0:
            print(f"[{now}] ✅ Sent {sent} post(s)")
        
        # Every 5 loops (100 sec), log status
        if loop_count % 5 == 0:
            print(f"[{now}] 💓 Heartbeat #{loop_count}")
        
        time.sleep(20)
        
    except Exception as e:
        print(f"[{datetime.now()}] ❌ ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        time.sleep(20)
