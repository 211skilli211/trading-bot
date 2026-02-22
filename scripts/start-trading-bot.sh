#!/bin/bash
# Start Trading Bot (Port 3001)

echo "🚀 Starting Trading Bot..."
echo "   Port: 3001"
echo "   Config: /tmp/trading_zeroclaw/.zeroclaw/"
echo ""

# Kill existing processes
pkill -f "zeroclaw daemon" 2>/dev/null
sleep 2

# Set environment
export HOME=/tmp/trading_zeroclaw
cd /tmp/trading_zeroclaw

# Create necessary directories
mkdir -p .zeroclaw/workspace/portfolio
mkdir -p .zeroclaw/logs

# Start daemon
nohup /root/.cargo/bin/zeroclaw daemon > .zeroclaw/zeroclaw.log 2>&1 &
PID=$!

sleep 3

# Check if running
if curl -s http://127.0.0.1:3001/health | grep -q "ok"; then
    echo "✅ Trading Bot started successfully!"
    echo "   PID: $PID"
    echo "   Health: http://127.0.0.1:3001/health"
    echo ""
    echo "Commands:"
    echo "   price, arbitrage, btc, eth, sol"
    echo "   alert BTC > 70000"
    echo "   portfolio, signals"
else
    echo "❌ Failed to start. Check logs:"
    echo "   tail -20 /tmp/trading_zeroclaw/.zeroclaw/zeroclaw.log"
fi
