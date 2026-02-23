#!/usr/bin/env python3
"""Test immediate send to verify system works"""
import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from scheduler_watchdog_v2 import get_watchdog
from message_templates import MessageParser
from datetime import datetime

print(f"Time now: {datetime.now().isoformat()}")

watchdog = get_watchdog()
parser = MessageParser()

# Schedule for immediate delivery (0 minutes = overdue immediately)
msg = "🧪 IMMEDIATE TEST - If you see this in channel, PM2 + timezone is fixed!"
result = watchdog.schedule_post(msg, "in 0 minutes", "7745772764", msg_type="reminder")

print(f"Scheduled ID {result.get('post_id')} for immediate delivery")
print("This should be picked up by PM2 in next 20-second check...")
