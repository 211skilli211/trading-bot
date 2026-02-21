#!/bin/bash
# ZeroClaw Trading Bot Responder
# Routes incoming messages to appropriate skill and returns plain text

MESSAGE="$1"
MESSAGE_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')

# Route based on keywords
case "$MESSAGE_LOWER" in
    *"price"*|*"btc"*|*"bitcoin"*|*"eth"*|*"ethereum"*)
        python3 /root/trading-bot/.zeroclaw/skills/price-check/handler.py "$MESSAGE" 2>&1
        ;;
    *"status"*|*"health"*|*"diagnose"*|*"check"*)
        python3 /root/trading-bot/.zeroclaw/skills/system-diagnostic/handler.py 2>&1
        ;;
    *"performance"*|*"pnl"*|*"profit"*|*"stats"*|*"how am i"*)
        python3 /root/trading-bot/.zeroclaw/skills/performance-monitor/handler.py 2>&1
        ;;
    *"debug"*|*"error"*|*"log"*|*"what happened"*)
        python3 /root/trading-bot/.zeroclaw/skills/debugger/handler.py 2>&1
        ;;
    *"help"*)
        cat << 'EOF'
🤖 TRADING BOT COMMANDS

📊 TRADING:
• "Price of BTC"
• "Check ETH"

🔍 DIAGNOSTICS:
• "System status"
• "Debug"

📈 ANALYSIS:
• "Performance"
• "Stats"

Type any command above!
EOF
        ;;
    *)
        echo "🤖 I can help with: price checks, system status, performance reports. Type 'help' for options."
        ;;
esac
