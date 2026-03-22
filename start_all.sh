#!/data/data/com.termux/files/usr/bin/bash
# Start Trading Bot + Dashboard

PYTHON=/root/trading-bot-venv/bin/python
BOT_DIR=/sdcard/zeroclaw-workspace/trading-bot

echo "Starting Trading Bot & Dashboard..."

cd $BOT_DIR

# Kill existing processes
pkill -f "dashboard.py" 2>/dev/null
pkill -f "trading_bot.py" 2>/dev/null
sleep 1

# Start dashboard on port 7777
$PYTHON dashboard.py 7777 > $BOT_DIR/dashboard.log 2>&1 &

sleep 2

echo "✅ Started!"
echo "   Dashboard: http://localhost:7777"
echo "   Analytics: http://localhost:7777/analytics"
