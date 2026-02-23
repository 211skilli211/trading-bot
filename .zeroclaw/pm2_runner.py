#!/usr/bin/env python3
"""
PM2 runner - checks for posts every minute
Restarts automatically if killed
"""

import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from cron_poster import check_and_post
import time
from datetime import datetime

print(f"[{datetime.now()}] PM2 Runner started")
print(f"Checking for posts every 60 seconds...")

while True:
    try:
        sent = check_and_post()
        if sent > 0:
            print(f"[{datetime.now()}] Sent {sent} post(s)")
        time.sleep(60)  # Check every minute
    except Exception as e:
        print(f"[{datetime.now()}] Error: {e}")
        time.sleep(60)
