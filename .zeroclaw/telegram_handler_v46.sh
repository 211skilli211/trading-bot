#!/bin/bash
# Trading Bot Handler v4.6 - Integrated Scheduler
# Checks for scheduled posts on EVERY message

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
WORKSPACE="/root/trading-bot"
TOOL_DIR="/root/trading-bot/.zeroclaw"

# ============================================
# CHECK SCHEDULED POSTS FIRST (on every message)
# ============================================
SENT_POSTS=$(python3 "$TOOL_DIR/schedule_tool.py" check 2>/dev/null)

# ============================================
# SEND CONFIRMATION FOR ANY SENT POSTS
# ============================================
if echo "$SENT_POSTS" | grep -q "Sent [1-9]"; then
    # Extract how many were sent
    python3 << PYCODE
import json, urllib.request
chat_id = "$USER_ID"
text = "📨 <b>Scheduled Post Sent!</b>\n\nYour scheduled message was posted to the channel."

payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
data = json.dumps(payload).encode()
req = urllib.request.Request(
    'https://api.telegram.org/bot' + '$BOT_TOKEN' + '/sendMessage',
    data=data,
    headers={'Content-Type': 'application/json'}
)
try:
    urllib.request.urlopen(req, timeout=5)
except:
    pass
PYCODE
fi

# ============================================
# HELPER FUNCTIONS
# ============================================
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

schedule_post() {
    python3 << PYCODE
import sys
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
result = ScheduleTool.schedule("""$1""", """$2""", """$3""")
if result["success"]:
    print(f"✅ Scheduled for {result['scheduled_time']}")
else:
    print(f"❌ {result['error']}")
PYCODE
}

list_schedules() {
    python3 << PYCODE
import sys
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
posts = ScheduleTool.list_user_posts("$USER_ID")
if not posts:
    print("📭 No scheduled posts")
else:
    print(f"📅 You have {len(posts)} scheduled post(s):\n")
    for i, p in enumerate(posts[:5], 1):
        msg = p['message'][:40] + "..." if len(p['message']) > 40 else p['message']
        time_str = p['scheduled_time'][:16].replace('T', ' ')
        print(f"{i}. {msg}")
        print(f"   🕐 {time_str}\n")
PYCODE
}

# ============================================
# COMMAND HANDLING
# ============================================
case "$MSG_LOWER" in
  "menu"|"/menu"|"start"|"/start")
    KEYBOARD='{"keyboard": [[{"text": "📊 AI Signals"}, {"text": "💰 Prices"}, {"text": "💼 Portfolio"}], [{"text": "🔍 Arbitrage"}, {"text": "📈 Dashboard"}, {"text": "🤖 Bot Status"}], [{"text": "📢 Post to Channel"}, {"text": "📅 Schedule Post"}, {"text": "⚙️ Settings"}]], "resize_keyboard": true, "one_time_keyboard": false}'
    send_msg "📈 <b>ZeroClaw Trading Bot</b>\n\nChoose your action:" "$KEYBOARD"
    ;;
    
  "📅 schedule post"|"schedule help"|"schedule")
    send_msg "📅 <b>Post Scheduler</b>\n\n<b>Schedule a message:</b>\n<code>schedule [message] for [when]</code>\n\nExamples:\n• schedule Buy BTC now! for tomorrow 9am\n• schedule Price alert for in 2 hours\n• schedule Update for in 30 minutes\n\n<b>See your schedules:</b>\n<code>my schedules</code>\n\nThe bot checks every message and sends scheduled posts automatically!" ""
    ;;
    
  "schedule "*)
    REST=$(echo "$MESSAGE" | sed 's/^schedule //i')
    
    if echo "$REST" | grep -qi " for "; then
        MSG_PART=$(echo "$REST" | sed 's/ for .*//i')
        TIME_PART=$(echo "$REST" | sed 's/.* for //i')
        
        RESULT=$(schedule_post "$MSG_PART" "$TIME_PART" "$USER_ID")
        send_msg "📅 <b>Post Scheduled!</b>\n\n$RESULT\n\n<i>I'll send it automatically when the time comes!</i>" ""
    else
        send_msg "❌ Format: <code>schedule [message] for [when]</code>\n\nExample: schedule Buy BTC for tomorrow 9am" ""
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
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
if ScheduleTool.cancel("""$SCHEDULE_ID""", "$USER_ID"):
    print("CANCELLED")
else:
    print("NOT_FOUND")
PYCODE
    ;;
    
  "📢 post to channel"*)
    MSG_CONTENT=$(echo "$MESSAGE" | sed 's/^[📢][[:space:]]*Post to Channel[[:space:]]*//')
    
    if [ -n "$MSG_CONTENT" ]; then
        python3 << PYCODE
import urllib.request, json
payload = {'chat_id': '-1003637413591', 'text': """$MSG_CONTENT""", 'parse_mode': 'HTML'}
data = json.dumps(payload).encode()
req = urllib.request.Request(f'https://api.telegram.org/bot$BOT_TOKEN/sendMessage', data=data, headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
    print("POSTED")
except:
    print("FAILED")
PYCODE
    else
        send_msg "📢 <b>Post to Channel</b>\n\nType your message and I'll post it.\n\nOr schedule it:\n<code>schedule [message] for [when]</code>" ""
    fi
    ;;
    
  "help"|"/help")
    send_msg "📈 <b>Trading Bot Help</b>\n\n<b>Quick Commands:</b>\n• 📊 AI Signals - Get predictions\n• 💰 Prices - Live prices\n• 📢 Post to Channel - Broadcast\n• 📅 Schedule Post - Schedule messages\n• my schedules - See scheduled posts\n\n<b>Examples:</b>\n• schedule Buy BTC for tomorrow 9am\n• schedule Alert for in 30 minutes\n\nOr just chat with me!" ""
    ;;
    
  *)
    # Let AI handle unknown commands
    echo "$MESSAGE"
    ;;
esac
