#!/bin/bash
# Start Complete Trading Platform

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         STARTING COMPLETE TRADING PLATFORM                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Create logs directory
mkdir -p /root/trading-bot/logs

# Start components
bash /root/trading-bot/scripts/start-trading-bot.sh
echo ""

bash /root/trading-bot/scripts/start-personal-bot.sh
echo ""

bash /root/trading-bot/scripts/start-dashboard.sh
echo ""

bash /root/trading-bot/scripts/start-monitor.sh
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              ✅ ALL SYSTEMS STARTED                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 SERVICES:"
echo "   Trading Bot:   http://127.0.0.1:3001 (Telegram: @zeroclaw_trading_bot)"
echo "   Personal Bot:  http://127.0.0.1:3000 (Telegram: @zeroclaw_personal_bot)"
echo "   Dashboard:     http://127.0.0.1:8080 (18 pages)"
echo "   System Monitor: Running (logs to file)"
echo ""
echo "📝 LOG FILES:"
echo "   Trading:  /tmp/trading_zeroclaw/.zeroclaw/zeroclaw.log"
echo "   Personal: ~/.zeroclaw/zeroclaw.log"
echo "   Dashboard: /root/trading-bot/dashboard.log"
echo "   Monitor:  /root/trading-bot/logs/monitor.log"
echo ""
echo "🛑 TO STOP ALL:"
echo "   pkill -f 'zeroclaw daemon'; pkill -f dashboard.py; pkill -f system_monitor.py"
