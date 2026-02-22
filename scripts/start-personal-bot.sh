#!/bin/bash
# Start Personal Bot (Port 3000)

echo "🚀 Starting Personal Bot..."
echo "   Port: 3000"
echo "   Config: ~/.zeroclaw/"
echo ""

# Kill existing
pkill -f "zeroclaw daemon" 2>/dev/null
sleep 2

# Set environment
export HOME=/root
cd /root

# Create necessary directories
mkdir -p .zeroclaw/workspace
mkdir -p .zeroclaw/reminders
mkdir -p .zeroclaw/knowledge
mkdir -p .zeroclaw/logs

# Start daemon
nohup /root/.cargo/bin/zeroclaw daemon > .zeroclaw/zeroclaw.log 2>&1 &
PID=$!

sleep 3

# Check if running
if curl -s http://127.0.0.1:3000/health | grep -q "ok"; then
    echo "✅ Personal Bot started successfully!"
    echo "   PID: $PID"
    echo "   Health: http://127.0.0.1:3000/health"
    echo ""
    echo "Commands:"
    echo "   remember, recall, reminders"
    echo "   note, notes, system, health"
else
    echo "❌ Failed to start. Check logs:"
    echo "   tail -20 ~/.zeroclaw/zeroclaw.log"
fi
