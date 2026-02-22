#!/bin/bash
# Trading Bot Handler v4.5 - Smart Post Scheduler
# Users can schedule posts AND set up auto-generated content

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
WORKSPACE="/root/trading-bot"
SCHEDULER_DIR="/tmp/trading_zeroclaw/.zeroclaw"

# Start scheduler if not running
if ! pgrep -f "scheduler.py" > /dev/null; then
    python3 "$SCHEDULER_DIR/scheduler.py" &
fi

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

# Function to call Python scheduler
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

# Handle commands
case "$MSG_LOWER" in
  "menu"|"/menu"|"start"|"/start")
    KEYBOARD='{"keyboard": [[{"text": "📊 AI Signals"}, {"text": "💰 Prices"}, {"text": "💼 Portfolio"}], [{"text": "🔍 Arbitrage"}, {"text": "📈 Dashboard"}, {"text": "🤖 Bot Status"}], [{"text": "📢 Post to Channel"}, {"text": "📅 Schedule Post"}, {"text": "⚙️ Settings"}]], "resize_keyboard": true, "one_time_keyboard": false}'
    send_msg "📈 <b>ZeroClaw Trading Bot</b>\n\nChoose your action:" "$KEYBOARD"
    echo "✅ Menu sent!"
    ;;
    
  "📅 schedule post"*)
    REST=$(echo "$MESSAGE" | sed 's/^[📅][[:space:]]*Schedule Post[[:space:]]*//i')
    
    if [ -z "$REST" ]; then
        send_msg "📅 <b>Smart Post Scheduler</b>\n\n<b>Option 1: Schedule a specific message</b>\nType:\n<code>schedule [message] for [when]</code>\n\nExamples:\n• schedule Buy BTC now for tomorrow 9am\n• schedule Price alert for in 2 hours\n• schedule Good morning traders for 2026-02-25 08:00\n\n<b>Option 2: Auto-generate content</b>\nType:\n<code>auto [type] [frequency]</code>\n\nTypes:\n• arbitrage - Arbitrage opportunities\n• prices - Price updates\n• signals - AI trading signals\n\nFrequencies:\n• hourly, every_4_hours, twice_daily\n• 3x_daily, daily, weekly\n\nExamples:\n• auto arbitrage twice_daily\n• auto prices every_4_hours\n• auto signals 3x_daily" ""
    else
        send_msg "Use the commands above to schedule posts!" ""
    fi
    echo "✅ Schedule help sent!"
    ;;
    
  "schedule "*)
    # Parse: schedule [message] for [when]
    REST=$(echo "$MESSAGE" | sed 's/^schedule //i')
    
    # Extract message and time
    if echo "$REST" | grep -qi " for "; then
        MSG_PART=$(echo "$REST" | sed 's/ for .*//i')
        TIME_PART=$(echo "$REST" | sed 's/.* for //i')
        
        RESULT=$(schedule_post "$MSG_PART" "$TIME_PART")
        send_msg "📅 <b>Post Scheduled!</b>\n\n$RESULT" ""
    else
        send_msg "❌ Format: <code>schedule [message] for [when]</code>\n\nExample: schedule Buy BTC for tomorrow 9am" ""
    fi
    echo "✅ Schedule command handled!"
    ;;
    
  "auto "*)
    # Parse: auto [type] [frequency]
    REST=$(echo "$MESSAGE" | sed 's/^auto //i')
    CONTENT_TYPE=$(echo "$REST" | awk '{print $1}')
    FREQUENCY=$(echo "$REST" | awk '{print $2}')
    
    if [ -n "$CONTENT_TYPE" ] && [ -n "$FREQUENCY" ]; then
        RESULT=$(schedule_auto "$CONTENT_TYPE" "$FREQUENCY")
        send_msg "🤖 <b>Auto-Schedule Created!</b>\n\n$RESULT\n\nThe bot will automatically generate and post content." ""
    else
        send_msg "❌ Format: <code>auto [type] [frequency]</code>\n\nExample: auto arbitrage twice_daily\n\nTypes: arbitrage, prices, signals\nFrequencies: hourly, every_4_hours, twice_daily, 3x_daily, daily" ""
    fi
    echo "✅ Auto-schedule handled!"
    ;;
    
  "my schedules"|"list schedules"|"show schedules")
    RESULT=$(list_schedules)
    send_msg "📅 <b>Your Scheduled Posts</b>\n\n$RESULT" ""
    echo "✅ Schedules listed!"
    ;;
    
  "cancel schedule "*)
    SCHEDULE_ID=$(echo "$MESSAGE" | sed 's/^cancel schedule //i')
    python3 << PYCODE
import sys
sys.path.insert(0, '$SCHEDULER_DIR')
from scheduler import get_scheduler
scheduler = get_scheduler()
if scheduler.cancel_post("""$SCHEDULE_ID""", "$USER_ID"):
    print("✅ Schedule cancelled")
else:
    print("❌ Could not find schedule")
PYCODE
    echo "✅ Cancel handled!"
    ;;
    
  *)
    # Pass to regular handler
    echo "$MESSAGE"
    ;;
esac
