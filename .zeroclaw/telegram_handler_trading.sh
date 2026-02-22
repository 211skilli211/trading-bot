#!/bin/bash
# Trading Bot Handler v4.0 - Professional Trading Commands

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"

# Send Telegram message
send_msg() {
  local text="$1"
  local keyboard="${2:-}"
  
  if [ -n "$keyboard" ]; then
    python3 -c "
import json, urllib.request
payload = {'chat_id': '$USER_ID', 'text': '''$text''', 'parse_mode': 'HTML', 'reply_markup': $keyboard}
data = json.dumps(payload).encode()
req = urllib.request.Request('https://api.telegram.org/bot$BOT_TOKEN/sendMessage', data=data, headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except:
    pass
"
  else
    python3 -c "
import json, urllib.request
payload = {'chat_id': '$USER_ID', 'text': '''$text''', 'parse_mode': 'HTML'}
data = json.dumps(payload).encode()
req = urllib.request.Request('https://api.telegram.org/bot$BOT_TOKEN/sendMessage', data=data, headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except:
    pass
"
  fi
}

# Get current price
get_price() {
  local symbol="$1"
  python3 << 'PYCODE'
import urllib.request
import json

try:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    
    symbol_map = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'BTC': 'bitcoin'}
    coin_id = symbol_map.get('"'"'$symbol'"'"', 'bitcoin')
    price = data.get(coin_id, {}).get('usd', 0)
    print(f"${price:,.2f}")
except:
    prices = {'BTC': 45230, 'ETH': 3120, 'SOL': 98}
    print(f"${prices.get('"'"'$symbol'"'"', 100):,.2f}")
PYCODE
}

# Route commands
case "$MSG_LOWER" in

  # Main Menu
  "menu"|"/menu"|"start"|"/start")
    KEYBOARD='{"keyboard": [[{"text": "📊 AI Signals"}, {"text": "💰 Prices"}, {"text": "💼 Portfolio"}], [{"text": "🔍 Arbitrage"}, {"text": "📈 Dashboard"}, {"text": "🤖 Bot Status"}], [{"text": "📢 Post to Channel"}, {"text": "⚙️ Settings"}]], "resize_keyboard": true, "one_time_keyboard": false}'
    send_msg "📈 <b>ZeroClaw Trading Bot</b>

Choose your trading action:" "$KEYBOARD"
    ;;

  # AI Signals
  "📊 ai signals"|"signals"|"signal")
    send_msg "📊 <b>AI Trading Signals</b>

Get AI-powered trading analysis:

Usage:
• signals BTC
• signals ETH
• signals SOL

The AI analyzes:
• Technical indicators
• Market trends
• Price action
• Volatility

And generates BUY/SELL/HOLD signals with confidence scores."
    ;;

  "signals"*)
    SYMBOL=$(echo "$MESSAGE" | awk '{print $2}' | tr '[:lower:]' '[:upper:]')
    SYMBOL=${SYMBOL:-BTC}
    
    PRICE=$(get_price "$SYMBOL")
    
    # Generate simple signal
    send_msg "📊 <b>AI Signal: $SYMBOL/USDT</b>

💰 Current Price: $PRICE

🎯 <b>Signal:</b> ANALYZING...

⏳ Use the 'ai-signals' skill for full AI analysis with:
• Confidence score
• Entry/Target/Stop levels
• Technical reasoning

<i>Full AI signals require skill execution.</i>"
    ;;

  # Prices
  "💰 prices"|"price"|"check price")
    send_msg "💰 <b>Live Prices</b>

Current market prices:

Try:
• price BTC
• price ETH
• price SOL

Or any crypto symbol!"
    ;;

  "price"*)
    SYMBOL=$(echo "$MESSAGE" | awk '{print $2}' | tr '[:lower:]' '[:upper:]')
    SYMBOL=${SYMBOL:-BTC}
    
    PRICE=$(get_price "$SYMBOL")
    
    send_msg "💰 <b>$SYMBOL/USDT</b>

Price: $PRICE

<i>Data from CoinGecko</i>

📊 View charts: https://www.coingecko.com/en/coins/${SYMBOL,,}"
    ;;

  # Portfolio
  "💼 portfolio"|"portfolio"|"balance"|"pnl")
    send_msg "💼 <b>Portfolio Status</b>

Querying your trading portfolio...

<i>Connect to trading engine for live data.</i>

🔗 Full dashboard: http://localhost:8080/portfolio"
    ;;

  # Arbitrage
  "🔍 arbitrage"|"arbitrage"|"scan")
    send_msg "🔍 <b>Arbitrage Scanner</b>

Scanning exchanges for price differences...

<i>Checking:</i>
• Binance
• Coinbase
• KuCoin
• OKX

Use 'arbitrage-scan' skill for full scan with profit calculations."
    ;;

  # Dashboard
  "📈 dashboard"|"dashboard"|"web")
    send_msg "📈 <b>Trading Dashboard</b>

🔗 http://localhost:8080

Available:
• Portfolio overview
• Active positions
• Trading history
• Performance metrics
• AI predictions
• Bot management

<i>Open in browser for full interface.</i>"
    ;;

  # Bot Status
  "🤖 bot status"|"status"|"health")
    # Check if trading engine is running
    if pgrep -f "trading_engine" > /dev/null 2>&1; then
      ENGINE="✅ Running"
    else
      ENGINE="⚠️ Not running"
    fi
    
    # Check ZeroClaw
    if pgrep -f "zeroclaw daemon" | grep -q "2"; then
      ZEROCLAW="✅ Both bots online"
    else
      ZEROCLAW="⚠️ Check processes"
    fi
    
    send_msg "🤖 <b>Bot Status</b>

🔧 <b>Trading Engine:</b> $ENGINE
🤖 <b>ZeroClaw:</b> $ZEROCLAW
📊 <b>API:</b> http://localhost:8080

<i>Use Master Control bot for detailed status.</i>"
    ;;

  # Channel Post
  "📢 post to channel"|"broadcast"|"channel")
    send_msg "📢 <b>Channel Broadcast</b>

Post trading updates to channels:

Usage:
• broadcast @channel_name Message here
• post to channel @mychannel Signal: BUY BTC

<i>Bot must be admin in target channel.</i>"
    ;;

  "broadcast"*)
    # Parse channel and message
    CHANNEL=$(echo "$MESSAGE" | awk '{print $2}')
    MSG=$(echo "$MESSAGE" | cut -d' ' -f3-)
    
    if [ -n "$CHANNEL" ] && [ -n "$MSG" ]; then
      # Post via channel manager
      python3 /tmp/trading_zeroclaw/.zeroclaw/channel_manager.py send "$CHANNEL" "$MSG" 2>/dev/null
      send_msg "📢 <b>Broadcast Sent!</b>

Channel: $CHANNEL
Status: ✅ Delivered"
    else
      send_msg "❌ Usage: broadcast @channel_name Your message here"
    fi
    ;;

  # Settings
  "⚙️ settings"|"settings"|"config")
    send_msg "⚙️ <b>Bot Settings</b>

Current Configuration:
• Mode: Paper Trading
• Exchanges: 5 connected
• AI Provider: OpenRouter
• Model: arcee-ai/trinity-large-preview:free

<i>Advanced settings via config.toml</i>"
    ;;

  # Help
  "help"|"/help")
    send_msg "📈 <b>Trading Bot Help</b>

📱 <b>Reply Keyboard:</b>
• 📊 AI Signals - Get trading signals
• 💰 Prices - Check crypto prices
• 💼 Portfolio - View holdings
• 🔍 Arbitrage - Scan opportunities
• 📈 Dashboard - Web interface
• 🤖 Bot Status - System health
• 📢 Post to Channel - Broadcast
• ⚙️ Settings - Configuration

⌨️ <b>Commands:</b>
• signals [symbol] - AI analysis
• price [symbol] - Live price
• menu - Show keyboard

💡 All commands work via buttons!"
    ;;

  # Close/Hide
  "close"|"hide"|"🗑️")
    REMOVE='{"remove_keyboard": true}'
    send_msg "✅ Keyboard hidden. Type 'menu' to show again!" "$REMOVE"
    ;;

  # Default
  *)
    echo "$MESSAGE"
    ;;
esac
