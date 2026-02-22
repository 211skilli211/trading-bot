#!/bin/bash
# Start the schedule watchdog as a persistent background process

SCRIPT_DIR="/root/trading-bot/.zeroclaw"
LOG_FILE="/tmp/watchdog.log"

# Check if already running
if pgrep -f "scheduler_watchdog.py" > /dev/null; then
    echo "Watchdog already running (PID: $(pgrep -f 'scheduler_watchdog.py'))"
    exit 0
fi

# Kill any old instances
pkill -f "scheduler_watchdog.py" 2>/dev/null

# Start new instance
cd "$SCRIPT_DIR"
nohup python3 scheduler_watchdog.py > "$LOG_FILE" 2>&1 &

sleep 2

# Verify
NEW_PID=$(pgrep -f "scheduler_watchdog.py")
if [ -n "$NEW_PID" ]; then
    echo "✅ Watchdog started (PID: $NEW_PID)"
    echo "Log: $LOG_FILE"
else
    echo "❌ Failed to start"
    cat "$LOG_FILE" | tail -5
fi
