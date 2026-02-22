#!/bin/bash
# Trading Bot Handler v4.1 - Fixed Keyboard Pattern

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"

send_msg() {
python3 << PYCODE
import json, urllib.request
chat_id = "$USER_ID"
text = """$1"""
markup = """$2"""

payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
if markup:
    payload['reply_markup'] = json.loads(markup)

data = json.dumps(payload).encode()
req = urllib.request.Request(
    'https://api.telegram.org/bot' + '$BOT_TOKEN' + '/sendMessage',
    data=data,
    headers={'Content-Type': 'application/json'}
)
try:
    urllib.request.urlopen(req, timeout=10)
except Exception as e:
    print(f'Error: {e}')
PYCODE
}

case "$MSG_LOWER" in
  "menu"|"/menu"|"start"|"/start")
    KEYBOARD='{"keyboard": [[{"text": "📊 AI Signals"}, {"text": "💰 Prices"}, {"text": "💼 Portfolio"}], [{"text": "🔍 Arbitrage"}, {"text": "📈 Dashboard"}, {"text": "🤖 Bot Status"}], [{"text": "📢 Post to Channel"}, {"text": "⚙️ Settings"}]], "resize_keyboard": true, "one_time_keyboard": false}'
    send_msg "📈 <b>ZeroClaw Trading Bot</b>\n\nChoose your trading action:" "$KEYBOARD"
    echo "✅ Trading menu sent!"
    ;;
    
  "🗑️ close"|"close menu")
    REMOVE='{"remove_keyboard": true}'
    send_msg "✅ Keyboard hidden. Type 'menu' to bring it back!" "$REMOVE"
    echo "✅ Closed!"
    ;;
    
  "📊 ai signals"|"signals")
    send_msg "📊 <b>AI Trading Signals</b>\n\nType: signals [symbol]\n\nExample:\n• signals BTC\n• signals ETH\n• signals SOL" ""
    echo "✅ Signals info sent!"
    ;;
    
  "💰 prices"|"price")
    send_msg "💰 <b>Live Prices</b>\n\nType: price [symbol]\n\nExamples:\n• price BTC\n• price ETH\n• price SOL" ""
    echo "✅ Price info sent!"
    ;;
    
  "💼 portfolio"|"portfolio")
    send_msg "💼 <b>Portfolio Status</b>\n\nQuerying trading portfolio...\n\n🔗 Full dashboard:\nhttp://localhost:8080/portfolio" ""
    echo "✅ Portfolio info sent!"
    ;;
    
  "🔍 arbitrage"|"arbitrage")
    send_msg "🔍 <b>Arbitrage Scanner</b>\n\nScanning exchanges for price differences...\n\n<i>Checking: Binance, Coinbase, KuCoin, OKX</i>" ""
    echo "✅ Arbitrage info sent!"
    ;;
    
  "📈 dashboard"|"dashboard")
    send_msg "📈 <b>Trading Dashboard</b>\n\n🔗 http://localhost:8080\n\nAvailable:\n• Portfolio overview\n• Active positions\n• Trading history\n• AI predictions" ""
    echo "✅ Dashboard info sent!"
    ;;
    
  "🤖 bot status"|"status")
    ZEROCOUNT=$(pgrep -f "zeroclaw daemon" | wc -l)
    send_msg "🤖 <b>Bot Status</b>\n\n🤖 ZeroClaw instances: $ZEROCOUNT running\n📊 API: http://localhost:8080\n\n<i>Use Master Control for detailed status.</i>" ""
    echo "✅ Status sent!"
    ;;
    
  "📢 post to channel"|"broadcast")
    send_msg "📢 <b>Channel Broadcast</b>\n\nUsage:\n• broadcast @channel_name Message\n\n<i>Bot must be admin in target channel.</i>" ""
    echo "✅ Broadcast info sent!"
    ;;
    
  "⚙️ settings"|"settings")
    send_msg "⚙️ <b>Bot Settings</b>\n\nCurrent Configuration:\n• Mode: Paper Trading\n• Exchanges: 5 connected\n• AI Provider: OpenRouter\n• Model: arcee-ai/trinity-large-preview:free" ""
    echo "✅ Settings sent!"
    ;;
    
  "help"|"/help")
    send_msg "📈 <b>Trading Bot Help</b>\n\n📱 <b>Reply Keyboard:</b>\n• 📊 AI Signals - Trading analysis\n• 💰 Prices - Check crypto prices\n• 💼 Portfolio - View holdings\n• 🔍 Arbitrage - Scan opportunities\n• 📈 Dashboard - Web interface\n• 🤖 Bot Status - System health\n• 📢 Post to Channel - Broadcast\n• ⚙️ Settings - Configuration\n\n💡 Type 'menu' anytime for buttons!" ""
    echo "✅ Help sent!"
    ;;
    
  *)
    echo "$MESSAGE"
    ;;
esac
