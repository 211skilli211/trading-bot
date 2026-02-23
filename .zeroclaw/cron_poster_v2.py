#!/usr/bin/env python3
"""
Smart Cron Poster v2 with Heartbeat
PM2-managed scheduler with template support & health monitoring
"""

import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from scheduler_watchdog_v2 import ScheduleWatchdog
from datetime import datetime
import time
import os

DB_FILE = "/tmp/trading_zeroclaw/.zeroclaw/scheduler.db"
LOG_FILE = "/tmp/cron_poster.log"
HEARTBEAT_FILE = "/tmp/smart_scheduler_heartbeat.txt"
HEARTBEAT_LOG = "/tmp/scheduler_heartbeat.log"

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

def emit_heartbeat():
    """Write heartbeat to file for health monitoring"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        # Main heartbeat file (last pulse)
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(timestamp)
        
        # Heartbeat log (history)
        with open(HEARTBEAT_LOG, "a") as f:
            f.write(f"{timestamp}\n")
        
        return True
    except Exception as e:
        log(f"Heartbeat error: {e}")
        return False

def check_and_post():
    """Main check and send function with heartbeat"""
    # Emit heartbeat first
    emit_heartbeat()
    
    try:
        watchdog = ScheduleWatchdog()
        sent = watchdog.check_and_send()
        
        if sent > 0:
            log(f"✅ Successfully sent {sent} post(s)")
        
        return sent
    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        log(f"Trace: {traceback.format_exc()}")
        return 0

if __name__ == "__main__":
    # When called directly, run once (for cron)
    sent = check_and_post()
    sys.exit(0 if sent >= 0 else 1)
