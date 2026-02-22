#!/bin/bash
# Trading Bot Handler v4.2 - ALL BUTTONS FUNCTIONAL
# Every button performs its actual skill/task

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
WORKSPACE="/root/trading-bot"

# Default channel for broadcasts
# Public channel:  "@channelname"  
# Private channel: "-1001234567890" (get from @getidsbot)
# 
# TO GET ID: Forward any message from your channel to @getidsbot
# It will reply with the ID (looks like: -1001234567890)
DEFAULT_CHANNEL="-1003637413591"

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

# Get current prices from API
get_prices() {
    cd "$WORKSPACE"
    python3 << 'PYCODE'
import requests, json

try:
    # Try dashboard API first
    resp = requests.get('http://localhost:8080/api/zeroclaw/predictions', timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        prices = data.get('prices', {})
        if prices:
            print("📊 LIVE PRICES\n")
            for symbol, price in list(prices.items())[:5]:
                print(f"• {symbol}: ${price:,.2f}")
        else:
            print("No price data available")
    else:
        # Fallback to direct fetch
        import sys
        sys.path.insert(0, '/root/trading-bot')
        from crypto_price_fetcher import BinanceConnector, CoinbaseConnector
        
        binance = BinanceConnector()
        coinbase = CoinbaseConnector()
        
        print("📊 LIVE PRICES\n")
        
        for symbol in ['BTC', 'ETH', 'SOL']:
            bin_data = binance.fetch_price(f"{symbol}USDT")
            if bin_data:
                print(f"• {symbol}/USDT: ${bin_data['price']:,.2f}")
except Exception as e:
    print(f"⚠️ Error fetching prices: {e}")
PYCODE
}

# Get AI signals
get_ai_signals() {
    cd "$WORKSPACE"
    python3 << 'PYCODE'
import requests, json

try:
    resp = requests.get('http://localhost:8080/api/zeroclaw/predictions', timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        predictions = data.get('predictions', [])
        
        if predictions:
            print("🤖 AI TRADING SIGNALS\n")
            for pred in predictions[:3]:
                symbol = pred.get('symbol', 'N/A')
                direction = pred.get('direction', 'HOLD')
                confidence = pred.get('confidence', 0)
                entry = pred.get('entry_price', 0)
                
                emoji = "🟢" if direction == "BUY" else "🔴" if direction == "SELL" else "⚪"
                print(f"{emoji} {symbol}: {direction}")
                print(f"   Confidence: {confidence}%")
                if entry:
                    print(f"   Entry: ${entry:,.2f}")
                print()
        else:
            print("🤖 AI TRADING SIGNALS\n\nNo active signals at the moment.")
    else:
        print("⚠️ AI service unavailable")
except Exception as e:
    print(f"⚠️ Error: {e}")
PYCODE
}

# Get portfolio data
get_portfolio() {
    cd "$WORKSPACE"
    python3 << 'PYCODE'
import sqlite3, json
from datetime import datetime

try:
    conn = sqlite3.connect('trades.db')
    cursor = conn.cursor()
    
    # Get stats
    cursor.execute("SELECT COUNT(*) FROM trades")
    total_trades = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM positions WHERE status='OPEN'")
    open_pos = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(net_pnl) FROM trades")
    result = cursor.fetchone()[0]
    total_pnl = result if result else 0.0
    
    cursor.execute("SELECT AVG(CASE WHEN net_pnl > 0 THEN 1.0 ELSE 0.0 END) * 100 FROM trades")
    win_rate = cursor.fetchone()[0] or 0.0
    
    conn.close()
    
    print("💼 PORTFOLIO STATUS\n")
    print(f"📊 Total Trades: {total_trades}")
    print(f"📈 Open Positions: {open_pos}")
    print(f"💰 Total P&L: ${total_pnl:,.2f}")
    print(f"🎯 Win Rate: {win_rate:.1f}%")
    print(f"\n🔗 Dashboard: http://localhost:8080/portfolio")
    
except Exception as e:
    print(f"⚠️ Portfolio error: {e}")
PYCODE
}

# Run arbitrage scanner
scan_arbitrage() {
    cd "$WORKSPACE"
    python3 << 'PYCODE'
import requests, json

try:
    # Try API endpoint
    resp = requests.get('http://localhost:8080/api/arbitrage/scan', timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        opportunities = data.get('opportunities', [])
        
        print("🔍 ARBITRAGE SCANNER\n")
        
        if opportunities:
            for opp in opportunities[:3]:
                symbol = opp.get('symbol', 'N/A')
                spread = opp.get('spread_percent', 0)
                buy_ex = opp.get('buy_exchange', 'N/A')
                sell_ex = opp.get('sell_exchange', 'N/A')
                
                print(f"🟢 {symbol}")
                print(f"   Spread: {spread:.2f}%")
                print(f"   Buy: {buy_ex} → Sell: {sell_ex}")
                print()
        else:
            print("No profitable opportunities found.")
            print("Spreads are below 0.15% threshold.")
            
    else:
        print("⚠️ Arbitrage scanner offline")
except Exception as e:
    print(f"🔍 ARBITRAGE SCANNER\n\nScanning CEX prices...\n⚠️ Scanner temporarily unavailable")
PYCODE
}

# Get bot status
get_bot_status() {
    cd "$WORKSPACE"
    python3 << 'PYCODE'
import sqlite3
from datetime import datetime

try:
    # Check processes
    import subprocess
    zerocount = subprocess.run("pgrep -f 'zeroclaw daemon' | wc -l", 
                                shell=True, capture_output=True, text=True).stdout.strip()
    
    # Get database stats
    conn = sqlite3.connect('trades.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM trades WHERE timestamp > datetime('now', '-1 day')")
    daily_trades = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(net_pnl) FROM trades WHERE timestamp > datetime('now', '-1 day')")
    daily_pnl = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT COUNT(*) FROM positions WHERE status='OPEN'")
    open_pos = cursor.fetchone()[0]
    
    conn.close()
    
    print("🤖 BOT STATUS\n")
    print(f"🟢 ZeroClaw instances: {zerocount} running")
    print(f"📊 Today's trades: {daily_trades}")
    print(f"💰 Today's P&L: ${daily_pnl:,.2f}")
    print(f"📈 Open positions: {open_pos}")
    print(f"\n🔗 API: http://localhost:8080")
    print(f"⏱️ Checked: {datetime.now().strftime('%H:%M:%S')}")
    
except Exception as e:
    print(f"⚠️ Status error: {e}")
PYCODE
}

# Get settings
get_settings() {
    cd "$WORKSPACE"
    python3 << 'PYCODE'
import json

try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    mode = config.get('bot', {}).get('mode', 'PAPER')
    max_trades = config.get('bot', {}).get('max_concurrent_trades', 5)
    
    print("⚙️ BOT SETTINGS\n")
    print(f"🎮 Mode: {mode}")
    print(f"📊 Max concurrent trades: {max_trades}")
    
    # Count enabled strategies
    strategies = config.get('strategies', {})
    enabled = [k for k, v in strategies.items() if v.get('enabled', False)]
    print(f"🤖 Active strategies: {len(enabled)}")
    print(f"   {', '.join(enabled[:3])}")
    
    print(f"\n💡 Edit config.json to change settings")
    
except Exception as e:
    print(f"⚠️ Settings error: {e}")
PYCODE
}

# Post to channel - returns 0 on success, 1 on failure
post_to_channel() {
    local channel="$1"
    local message="$2"
    
    if [ -z "$channel" ] || [ -z "$message" ]; then
        return 1
    fi
    
    python3 << PYCODE
import json, urllib.request, sys

bot_token = "$BOT_TOKEN"
channel = "$channel"
message = """$message"""

# Handle channel format
if channel.startswith('-100'):
    chat_id = channel
elif channel.startswith('@'):
    chat_id = channel
else:
    chat_id = '@' + channel

try:
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    response = urllib.request.urlopen(req, timeout=10)
    result = json.loads(response.read().decode())
    
    if result.get('ok'):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failed
        
except Exception as e:
    sys.exit(1)  # Error
PYCODE
}

# Handle commands
case "$MSG_LOWER" in
  "menu"|"/menu"|"start"|"/start")
    KEYBOARD='{"keyboard": [[{"text": "📊 AI Signals"}, {"text": "💰 Prices"}, {"text": "💼 Portfolio"}], [{"text": "🔍 Arbitrage"}, {"text": "📈 Dashboard"}, {"text": "🤖 Bot Status"}], [{"text": "📢 Post to Channel"}, {"text": "⚙️ Settings"}]], "resize_keyboard": true, "one_time_keyboard": false}'
    send_msg "📈 <b>ZeroClaw Trading Bot</b>\n\nChoose your trading action:" "$KEYBOARD"
    echo "✅ Trading menu sent!"
    ;;
    
  "🗑️ close"|"close menu"|"hide")
    REMOVE='{"remove_keyboard": true}'
    send_msg "✅ Keyboard hidden. Type 'menu' to bring it back!" "$REMOVE"
    echo "✅ Closed!"
    ;;
    
  "📊 ai signals"*)
    RESULT=$(get_ai_signals)
    send_msg "$RESULT" ""
    echo "✅ AI Signals sent!"
    ;;
    
  "💰 prices"*)
    RESULT=$(get_prices)
    send_msg "$RESULT" ""
    echo "✅ Prices sent!"
    ;;
    
  "💼 portfolio"*)
    RESULT=$(get_portfolio)
    send_msg "$RESULT" ""
    echo "✅ Portfolio sent!"
    ;;
    
  "🔍 arbitrage"*)
    RESULT=$(scan_arbitrage)
    send_msg "$RESULT" ""
    echo "✅ Arbitrage scan sent!"
    ;;
    
  "📈 dashboard"*)
    send_msg "📈 <b>Trading Dashboard</b>\n\n🔗 <a href='http://localhost:8080'>Open Dashboard</a>\n\nAvailable pages:\n• /portfolio - Holdings & P&L\n• /positions - Active trades\n• /analytics - Performance stats\n• /alerts - Notification center" ""
    echo "✅ Dashboard link sent!"
    ;;
    
  "🤖 bot status"*)
    RESULT=$(get_bot_status)
    send_msg "$RESULT" ""
    echo "✅ Bot status sent!"
    ;;
    
  "📢 post to channel"*)
    # Get message content after the button text
    MSG_CONTENT=$(echo "$MESSAGE" | sed 's/^[📢][[:space:]]*[Pp]ost [Tt]o [Cc]hannel[[:space:]]*//')
    
    if [ -n "$MSG_CONTENT" ]; then
        # User included message with button - post directly
        if post_to_channel "$DEFAULT_CHANNEL" "$MSG_CONTENT"; then
            # Create preview (first 80 chars)
            PREVIEW="$MSG_CONTENT"
            [ ${#MSG_CONTENT} -gt 80 ] && PREVIEW="${MSG_CONTENT:0:80}..."
            PREVIEW=$(echo "$PREVIEW" | sed 's/</\&lt;/g; s/>/\&gt;/g')
            
            send_msg "📨 <b>Message Posted!</b>\n\n📢 Channel: Arbitrage Pro Signals\n✅ Status: Delivered\n\n📝 Preview:\n<code>$PREVIEW</code>" ""
            echo "✅ Posted to channel!"
        else
            send_msg "❌ <b>Failed to Post</b>\n\nCould not send to channel.\n\nCheck:\n• Bot is admin in channel\n• Channel ID is correct" ""
            echo "❌ Post failed"
        fi
    else
        # Create waiting flag - next message will be posted
        touch "/tmp/trading_zeroclaw/.zeroclaw/waiting_for_post_$USER_ID"
        send_msg "📢 <b>Post to Channel</b>\n\nType your message and I'll post it to <b>Arbitrage Pro Signals</b>.\n\nNext message will be broadcasted." ""
        echo "✅ Waiting for message..."
    fi
    ;;
    
  "⚙️ settings"*)
    RESULT=$(get_settings)
    send_msg "$RESULT" ""
    echo "✅ Settings sent!"
    ;;
    
  "post"*)
    # Direct post command
    REST=$(echo "$MESSAGE" | sed 's/^post //i')
    
    if [ -n "$REST" ]; then
        # User included message - post directly
        if post_to_channel "$DEFAULT_CHANNEL" "$REST"; then
            # Create preview (first 80 chars)
            PREVIEW="$REST"
            [ ${#REST} -gt 80 ] && PREVIEW="${REST:0:80}..."
            PREVIEW=$(echo "$PREVIEW" | sed 's/</\&lt;/g; s/>/\&gt;/g')
            
            send_msg "📨 <b>Message Posted!</b>\n\n📢 Channel: Arbitrage Pro Signals\n✅ Status: Delivered\n\n📝 Preview:\n<code>$PREVIEW</code>" ""
            echo "✅ Posted to channel!"
        else
            send_msg "❌ <b>Failed to Post</b>\n\nCould not send to channel.\n\nCheck:\n• Bot is admin in channel\n• Channel ID is correct" ""
            echo "❌ Post failed"
        fi
    else
        # Create waiting flag - next message will be posted
        touch "/tmp/trading_zeroclaw/.zeroclaw/waiting_for_post_$USER_ID"
        send_msg "📢 <b>Post to Channel</b>\n\nType your message and I'll post it to <b>Arbitrage Pro Signals</b>.\n\nNext message will be broadcasted." ""
        echo "✅ Waiting for message..."
    fi
    ;;
    
  "help"|"/help")
    send_msg "📈 <b>Trading Bot Help</b>\n\n📱 <b>Reply Keyboard:</b>\n• 📊 AI Signals - Live AI predictions\n• 💰 Prices - Real-time crypto prices\n• 💼 Portfolio - Your trading stats\n• 🔍 Arbitrage - Scan for opportunities\n• 📈 Dashboard - Web interface\n• 🤖 Bot Status - System health\n• 📢 Post to Channel - Broadcast\n• ⚙️ Settings - View config\n\n💡 Type 'menu' anytime for buttons!" ""
    echo "✅ Help sent!"
    ;;
    
  *)
    # Check if we're in "waiting for post" mode
    WAITING_FILE="/tmp/trading_zeroclaw/.zeroclaw/waiting_for_post_$USER_ID"
    if [ -f "$WAITING_FILE" ]; then
        # User is sending the message to post
        rm -f "$WAITING_FILE"
        if post_to_channel "$DEFAULT_CHANNEL" "$MESSAGE"; then
            # Create preview (first 80 chars)
            PREVIEW="$MESSAGE"
            [ ${#MESSAGE} -gt 80 ] && PREVIEW="${MESSAGE:0:80}..."
            PREVIEW=$(echo "$PREVIEW" | sed 's/</\&lt;/g; s/>/\&gt;/g')
            
            send_msg "📨 <b>Message Posted!</b>\n\n📢 Channel: Arbitrage Pro Signals\n✅ Status: Delivered\n\n📝 Preview:\n<code>$PREVIEW</code>" ""
            echo "✅ Posted to channel!"
        else
            send_msg "❌ <b>Failed to Post</b>\n\nCould not send to channel.\n\nCheck:\n• Bot is admin in channel\n• Channel ID is correct" ""
            echo "❌ Post failed"
        fi
    else
        # Default: pass to AI
        echo "$MESSAGE"
    fi
    ;;
esac
