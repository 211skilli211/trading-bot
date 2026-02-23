---
name: check-health
description: Use when the user asks "are you alive?", "status", "scheduler status", "is it working?", or "health check".
triggers:
  - status
  - health
  - alive
  - working
  - scheduler status
  - check scheduler
---

# Health Check Skill

Check the status of the Smart Scheduler and PM2 processes.

## Execute

```bash
#!/bin/bash

echo "🏥 SCHEDULER HEALTH REPORT"
echo "=========================="
echo ""

# 1. Check heartbeat
if [ -f /tmp/smart_scheduler_heartbeat.txt ]; then
    LAST_PULSE=$(cat /tmp/smart_scheduler_heartbeat.txt)
    NOW=$(date '+%Y-%m-%d %H:%M:%S')
    echo "💓 Last Heartbeat: $LAST_PULSE"
    echo "🕒 Current Time:   $NOW"
    echo ""
else
    echo "❌ No heartbeat file found!"
    echo "   Scheduler may not be running"
    echo ""
fi

# 2. PM2 Status
echo "📦 PM2 Processes:"
pm2 status | grep -E "name|smart-scheduler|online|stopped|errored" || echo "   PM2 not responding"
echo ""

# 3. Recent log activity
echo "📋 Recent Activity (last 5 lines):"
if [ -f /tmp/cron_poster.log ]; then
    tail -5 /tmp/cron_poster.log | while read line; do
        echo "   $line"
    done
else
    echo "   No log file found"
fi
echo ""

# 4. Pending posts count
echo "📊 Pending Posts:"
python3 << 'PYCODE'
import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
try:
    from scheduler_watchdog_v2 import get_watchdog
    watchdog = get_watchdog()
    stats = watchdog.get_stats()
    print(f"   Pending: {stats['pending']}")
    print(f"   Total scheduled: {stats['total_scheduled']}")
    print(f"   Sent today: {stats['sent_today']}")
    print(f"   By type: {stats['by_type']}")
except Exception as e:
    print(f"   Error reading DB: {e}")
PYCODE

echo ""
echo "=========================="
echo "To restart: pm2 restart smart-scheduler"
