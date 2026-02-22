#!/bin/bash
# Trading Bot Handler v4.5 - Hybrid: Handler for commands, AI for chat
# Returns EMPTY for unknown messages (lets AI respond)

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
WORKSPACE="/root/trading-bot"
SCHEDULER_DIR="/tmp/trading_zeroclaw/.zeroclaw"

# Start scheduler if not running
if ! pgrep -f "scheduler.py" > /dev/null; then
    python3 "$SCHEDULER_DIR/scheduler.py" > /dev/null 2>&1 &
fi

# Function to send message via Telegram API
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
    pass
PYCODE
}

# Schedule a post
schedule_post() {
    local message="$1"
    local when="$2"
    python3 << PYCODE
import sys
sys.path.insert(0, '$SCHEDULER_DIR')
from scheduler import get_scheduler
scheduler = get_scheduler()
result = scheduler.schedule_post("""$message""", """$when""", "$USER_ID")
if result["success"]:
    print(f"✅ Scheduled for {result['scheduled_time']}")
else:
    print(f"❌ {result['error']}")
PYCODE
}

# Auto-schedule content
schedule_auto() {
    local content_type="$1"
    local frequency="$2"
    python3 << PYCODE
import sys
sys.path.insert(0, '$SCHEDULER_DIR')
from scheduler import get_scheduler
scheduler = get_scheduler()
result = scheduler.create_auto_schedule("""$content_type""", """$frequency""", "$USER_ID")
if result["success"]:
    print(f"✅ Auto-schedule created!")
    print(f"📋 Type: {result['content_type']}")
    print(f"⏰ Frequency: {result['frequency']}")
    print(f"🕐 Next run: {result['next_run']}")
else:
    print(f"❌ {result['error']}")
PYCODE
}

# List user's schedules
list_schedules() {
    python3 << PYCODE
import sys
sys.path.insert(0, '$SCHEDULER_DIR')
from scheduler import get_scheduler
scheduler = get_scheduler()
posts = scheduler.get_user_posts("$USER_ID")
autos = scheduler.list_auto_schedules("$USER_ID")

if not posts and not autos:
    print("📭 No scheduled posts")
else:
    if posts:
        print("📅 <b>Scheduled Posts:</b>")
        for p in posts[:5]:
            msg = p['message'][:40] + "..." if len(p['message']) > 40 else p['message']
            print(f"• {msg}")
            print(f"  🕐 {p['scheduled_time'][:16]}")
    if autos:
        print("\n🤖 <b>Auto-Schedules:</b>")
        for a in autos:
            status = "✅" if a['enabled'] else "⏸️"
            print(f"{status} {a['content_type']} - {a['frequency']}")
PYCODE
}

# Get prices for AI context
get_prices() {
    cd "$WORKSPACE"
    python3 << 'PYCODE'
import requests, json
try:
    resp = requests.get('http://localhost:8080/api/zeroclaw/predictions', timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        prices = data.get('prices', {})
        if prices:
            print("Current Prices:")
            for symbol, price in list(prices.items())[:5]:
                print(f"• {symbol}: ${price:,.2f}")
        else:
            print("No price data available")
    else:
        print("Price service unavailable")
except Exception as e:
    print(f"Error fetching prices: {e}")
PYCODE
}

# Get AI signals
get_signals() {
    cd "$WORKSPACE"
    python3 << 'PYCODE'
import requests, json
try:
    resp = requests.get('http://localhost:8080/api/zeroclaw/predictions', timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        predictions = data.get('predictions', [])
        if predictions:
            print("AI Signals:")
            for pred in predictions[:3]:
                symbol = pred.get('symbol', 'N/A')
                direction = pred.get('direction', 'HOLD')
                confidence = pred.get('confidence', 0)
                print(f"• {symbol}: {direction} ({confidence}% confidence)")
        else:
            print("No active signals")
    else:
        print("Signal service unavailable")
except Exception as e:
    print(f"Error fetching signals: {e}")
PYCODE
}

# Handle specific commands - if matched, we handle it
# If not matched, output NOTHING so AI can respond

case "$MSG_LOWER" in
  "menu"|"/menu"|"start"|"/start")
    KEYBOARD='{"keyboard": [[{"text": "📊 AI Signals"}, {"text": "💰 Prices"}, {"text": "💼 Portfolio"}], [{"text": "🔍 Arbitrage"}, {"text": "📈 Dashboard"}, {"text": "🤖 Bot Status"}], [{"text": "📢 Post to Channel"}, {"text": "📅 Schedule Post"}, {"text": "⚙️ Settings"}]], "resize_keyboard": true, "one_time_keyboard": false}'
    send_msg "📈 <b>ZeroClaw Trading Bot</b>\n\nChoose your action:" "$KEYBOARD"
    # Output empty so AI doesn't duplicate
    ;;
    
  "📅 schedule post"|"schedule help")
    send_msg "📅 <b>Smart Post Scheduler</b>\n\n<b>Schedule a message:</b>\n<code>schedule [message] for [when]</code>\n\nExamples:\n• schedule Buy BTC now! for tomorrow 9am\n• schedule Price alert for in 2 hours\n• schedule Market update for 2026-02-25 08:00\n\n<b>Auto-generate content:</b>\n<code>auto [type] [frequency]</code>\n\nTypes: arbitrage, prices, signals\nFrequencies: hourly, every_4_hours, twice_daily, 3x_daily, daily\n\nExamples:\n• auto arbitrage twice_daily\n• auto prices every_4_hours\n• auto signals 3x_daily" ""
    ;;
    
  "schedule "*)
    # Parse: schedule [message] for [when]
    REST=$(echo "$MESSAGE" | sed 's/^schedule //i')
    
    if echo "$REST" | grep -qi " for "; then
        MSG_PART=$(echo "$REST" | sed 's/ for .*//i')
        TIME_PART=$(echo "$REST" | sed 's/.* for //i')
        
        RESULT=$(schedule_post "$MSG_PART" "$TIME_PART")
        send_msg "📅 <b>Post Scheduled!</b>\n\n$RESULT" ""
    else
        send_msg "❌ Format: <code>schedule [message] for [when]</code>\n\nExample: schedule Buy BTC for tomorrow 9am" ""
    fi
    ;;
    
  "auto "*)
    # Parse: auto [type] [frequency]
    REST=$(echo "$MESSAGE" | sed 's/^auto //i')
    CONTENT_TYPE=$(echo "$REST" | awk '{print $1}')
    FREQUENCY=$(echo "$REST" | awk '{print $2}')
    
    if [ -n "$CONTENT_TYPE" ] && [ -n "$FREQUENCY" ]; then
        RESULT=$(schedule_auto "$CONTENT_TYPE" "$FREQUENCY")
        send_msg "🤖 <b>Auto-Schedule Created!</b>\n\n$RESULT" ""
    else
        send_msg "❌ Format: <code>auto [type] [frequency]</code>\n\nExample: auto arbitrage twice_daily" ""
    fi
    ;;
    
  "my schedules"|"list schedules"|"show schedules")
    RESULT=$(list_schedules)
    send_msg "📅 <b>Your Scheduled Posts</b>\n\n$RESULT" ""
    ;;
    
  "cancel schedule "*)
    SCHEDULE_ID=$(echo "$MESSAGE" | sed 's/^cancel schedule //i')
    python3 << PYCODE
import sys
sys.path.insert(0, '$SCHEDULER_DIR')
from scheduler import get_scheduler
scheduler = get_scheduler()
if scheduler.cancel_post("""$SCHEDULE_ID""", "$USER_ID"):
    print("CANCELLED")
else:
    print("NOT_FOUND")
PYCODE
    ;;
    
  "📊 ai signals"|"ai signals"|"signals"|"get signals")
    RESULT=$(get_signals)
    send_msg "🤖 <b>AI Trading Signals</b>\n\n<code>$RESULT</code>" ""
    ;;
    
  "💰 prices"|"prices"|"get prices"|"price")
    RESULT=$(get_prices)
    send_msg "💰 <b>Live Prices</b>\n\n<code>$RESULT</code>" ""
    ;;
    
  "💼 portfolio"|"portfolio")
    # Let AI handle this with context
    echo "$MESSAGE"
    ;;
    
  "🔍 arbitrage"|"arbitrage"|"scan arbitrage")
    # Let AI handle this
    echo "$MESSAGE"
    ;;
    
  "📈 dashboard"|"dashboard")
    send_msg "📈 <b>Trading Dashboard</b>\n\n🔗 <a href='http://localhost:8080'>Open Dashboard</a>" ""
    ;;
    
  "🤖 bot status"|"bot status"|"status")
    # Let AI handle with dynamic data
    echo "$MESSAGE"
    ;;
    
  "📢 post to channel"*)
    MSG_CONTENT=$(echo "$MESSAGE" | sed 's/^[📢][[:space:]]*Post to Channel[[:space:]]*//')
    
    if [ -n "$MSG_CONTENT" ]; then
        # Post directly
        python3 << PYCODE
import json, urllib.request
payload = {
    'chat_id': '-1003637413591',
    'text': """$MSG_CONTENT""",
    'parse_mode': 'HTML'
}
data = json.dumps(payload).encode()
req = urllib.request.Request(
    f'https://api.telegram.org/bot$BOT_TOKEN/sendMessage',
    data=data,
    headers={'Content-Type': 'application/json'}
)
try:
    urllib.request.urlopen(req, timeout=10)
    print("POSTED")
except:
    print("FAILED")
PYCODE
    else
        send_msg "📢 <b>Post to Channel</b>\n\nType your message and I'll post it to <b>Arbitrage Pro Signals</b>.\n\nOr use:\n<code>schedule [message] for [when]</code>" ""
    fi
    ;;
    
  "⚙️ settings"|"settings")
    send_msg "⚙️ <b>Bot Settings</b>\n\nUse the dashboard for full configuration:\n🔗 <a href='http://localhost:8080/config'>Open Config</a>" ""
    ;;
    
  "help"|"/help")
    send_msg "📈 <b>Trading Bot Help</b>\n\n<b>Quick Commands:</b>\n• 📊 AI Signals - Get AI predictions\n• 💰 Prices - Live crypto prices\n• 📢 Post to Channel - Broadcast message\n• 📅 Schedule Post - Schedule messages\n\n<b>Examples:</b>\n• schedule Buy BTC for tomorrow 9am\n• auto arbitrage twice_daily\n• my schedules\n\nOr just chat with me about trading!" ""
    ;;
    
  *)
    # Unknown command - let AI handle it
    # Output the message so AI can respond dynamically
    echo "$MESSAGE"
    ;;
esac
