#!/bin/bash
# Health Monitor - Restarts PM2 if heartbeat flatlines

HEARTBEAT_FILE="/tmp/smart_scheduler_heartbeat.txt"
MAX_AGE=300  # 5 minutes in seconds

if [ ! -f "$HEARTBEAT_FILE" ]; then
    echo "⚠️ No heartbeat file found!"
    echo "🔄 Restarting smart-scheduler..."
    pm2 restart smart-scheduler
    exit 1
fi

LAST_PULSE=$(cat "$HEARTBEAT_FILE")
LAST_EPOCH=$(date -d "$LAST_PULSE" +%s 2>/dev/null || date -j -f "%Y-%m-%d %H:%M:%S" "$LAST_PULSE" +%s)
NOW_EPOCH=$(date +%s)
DIFF=$((NOW_EPOCH - LAST_EPOCH))

if [ $DIFF -gt $MAX_AGE ]; then
    echo "⚠️ Heartbeat Flatlined! No activity for $DIFF seconds."
    echo "🔄 Restarting PM2..."
    pm2 restart smart-scheduler
    echo "✅ Restarted at $(date '+%H:%M:%S')"
else
    echo "💓 Heartbeat Strong. Last activity $DIFF seconds ago."
fi
