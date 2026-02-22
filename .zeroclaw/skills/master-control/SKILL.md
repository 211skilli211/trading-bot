---
name: master-control
description: Control other bots and check system status. Use when user says "status", "bots", "trading bot", or taps Master Control button.
triggers:
  - "🎛️ Master Control"
  - master control
  - bot status
  - system status
  - check bots
---

# Master Bot Controller

Control trading bots, check statuses, and manage deployments.

## Instructions

1. Check all running ZeroClaw instances
2. Query trading bot API for status
3. Show dashboard with all bot statuses
4. Provide control options

## Execute

```bash
#!/bin/bash
COMMAND="$1"

case "$COMMAND" in
  "status"|"")
    # Check all bot statuses
    PERSONAL_STATUS=$(pgrep -f "zeroclaw daemon.*HOME=/root" > /dev/null && echo "✅ Online" || echo "❌ Offline")
    TRADING_STATUS=$(pgrep -f "zeroclaw daemon.*HOME=/tmp/trading" > /dev/null && echo "✅ Online" || echo "❌ Offline")
    
    # Try to get trading bot metrics
    TRADING_METRICS=$(curl -s http://localhost:8080/api/trading/balance 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if d.get('success'):
        val=d.get('balance',{}).get('total_value_usd',0)
        pnl=d.get('balance',{}).get('total_pnl',0)
        print(f'💰 Portfolio: ${val:,.2f} | P&L: ${pnl:,.2f}')
    else:
        print('📊 Metrics unavailable')
except:
    print('📊 Metrics unavailable')
" 2>/dev/null)
    
    # Get memory stats
    MEMORY_ENTRIES=$(python3 "$HOME/.zeroclaw/memory_system.py" daily 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get('total_notes',0))
except:
    print('0')
" 2>/dev/null)
    
    echo "🎛️ <b>Master Control Dashboard</b>

🤖 <b>Bot Status:</b>
• Personal Bot: $PERSONAL_STATUS (Port 3000)
• Trading Bot: $TRADING_STATUS (Port 3001)

📈 <b>Trading:</b>
$TRADING_METRICS

🧠 <b>Memory:</b>
• Today's entries: $MEMORY_ENTRIES

🔧 <b>Quick Actions:</b>
• Check port 3001 health
• View trading dashboard
• Sync bot configs

Type '🎛️ Master Control status' to refresh"
    ;;
    
  "restart-trading")
    echo "🔄 Restarting Trading Bot..."
    pkill -f "zeroclaw daemon.*HOME=/tmp/trading" 2>/dev/null
    sleep 2
    (export HOME=/tmp/trading_zeroclaw; cd /tmp/trading_zeroclaw; nohup zeroclaw daemon > .zeroclaw/zeroclaw.log 2>&1 &)
    sleep 2
    if pgrep -f "zeroclaw daemon.*HOME=/tmp/trading" > /dev/null; then
      echo "✅ Trading Bot restarted successfully!"
    else
      echo "❌ Failed to restart Trading Bot"
    fi
    ;;
    
  "trading-dashboard")
    echo "📊 <b>Trading Dashboard</b>

🔗 http://localhost:8080

💡 Access via:
• Web browser on device
• Port forward for remote access
• Ngrok tunnel for external access

📈 Endpoints:
• /api/trading/balance
• /api/trading/positions
• /api/arbitrage/scan
• /api/bots/list"
    ;;
    
  "sync")
    echo "🔄 <b>Sync Configuration</b>

Syncing bot configs..."
    # Copy skills to trading bot
    cp -r ~/.zeroclaw/skills/* /tmp/trading_zeroclaw/.zeroclaw/skills/ 2>/dev/null || echo "Skills sync: some failed"
    echo "✅ Skills synced to trading bot"
    ;;
    
  *)
    echo "🎛️ <b>Master Control</b>

Commands:
• 🎛️ Master Control status - Show all bots
• 🎛️ Master Control restart-trading - Restart trading bot
• 🎛️ Master Control trading-dashboard - Trading info
• 🎛️ Master Control sync - Sync configs

You can also:
• Check individual bot logs
• Deploy new bot instances
• Monitor system resources"
    ;;
esac
```

## Output

Master dashboard showing all bot statuses and control options.
