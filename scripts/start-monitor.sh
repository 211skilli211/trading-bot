#!/bin/bash
# Start System Monitor (background alerts)

echo "🚀 Starting System Monitor..."
echo "   Checks: CPU, Memory, Disk every 60s"
echo ""

cd /root/trading-bot

# Kill existing
pkill -f "system_monitor.py" 2>/dev/null
sleep 1

# Start monitor
nohup python3 system_monitor.py > logs/monitor.log 2>&1 &
PID=$!

echo "✅ System Monitor started!"
echo "   PID: $PID"
echo "   Log: /root/trading-bot/logs/monitor.log"
