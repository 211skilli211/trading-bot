#!/bin/bash
# Start Flask Dashboard (Port 8080)

echo "🚀 Starting Dashboard..."
echo "   Port: 8080"
echo "   Location: /root/trading-bot/"
echo ""

cd /root/trading-bot

# Kill existing
pkill -f "dashboard.py" 2>/dev/null
sleep 2

# Start dashboard
nohup python3 dashboard.py > dashboard.log 2>&1 &
PID=$!

sleep 4

# Check if running
if curl -s http://127.0.0.1:8080/ | grep -q "211Skilli"; then
    echo "✅ Dashboard started successfully!"
    echo "   PID: $PID"
    echo "   URL: http://127.0.0.1:8080"
    echo "   Pages: 18"
    echo ""
    echo "Key Pages:"
    echo "   / - Dashboard"
    echo "   /prices - Live prices"
    echo "   /portfolio - Portfolio"
    echo "   /zeroclaw - AI Panel"
else
    echo "❌ Failed to start. Check logs:"
    echo "   tail -20 /root/trading-bot/dashboard.log"
fi
