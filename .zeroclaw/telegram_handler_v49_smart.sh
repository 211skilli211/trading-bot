#!/bin/bash
# Smart Trading Scheduler Handler v49
# Supports: Signals, Alerts, Reminders, News broadcasts
# Format: "schedule <message> for <time>"

read -r JSON_PAYLOAD

# Extract fields
MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))")
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))")
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')

DB_PATH="/tmp/trading_zeroclaw/.zeroclaw/scheduler.db"
CHANNEL="-1003637413591"

# Schedule post using Python for parsing
schedule_post() {
    local raw_msg="$1"
    local when="$2"
    
    python3 << PYCODE
import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from message_templates import MessageParser, MessageTemplates
from scheduler_watchdog import get_watchdog
import json

raw_msg = """$raw_msg"""
when = """$when"""
user_id = "$USER_ID"

# Parse the message to determine type and format it
parser = MessageParser()
parsed = parser.parse(raw_msg)

# Generate formatted message
formatted_msg = parser.generate(parsed)

# Schedule it
watchdog = get_watchdog()
result = watchdog.schedule_post(formatted_msg, when, user_id, channel="$CHANNEL")

if result['success']:
    print(f"✅ {parsed['type'].upper()} SCHEDULED!")
    print(f"📝 Type: {parsed['type']}")
    print(f"⏰ When: {result['scheduled_time']}")
    print(f"📊 Preview: {result['message_preview']}")
else:
    print(f"❌ Error: {result.get('error', 'Unknown error')}")
PYCODE
}

# Check pending posts
show_pending() {
    python3 << PYCODE
import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from scheduler_watchdog import get_watchdog

watchdog = get_watchdog()
posts = watchdog.list_user_posts("$USER_ID")

if not posts:
    print("📭 No pending scheduled posts")
else:
    print(f"📋 You have {len(posts)} pending post(s):\n")
    for i, (post_id, message, sched_time) in enumerate(posts[:5], 1):
        msg_preview = message[:40].replace('\n', ' ') + "..."
        print(f"{i}. ⏰ {sched_time}")
        print(f"   📝 {msg_preview}")
        print()
PYCODE
}

# Quick signal shortcut
quick_signal() {
    local pair="$1"
    local action="$2"  # buy or sell
    local price="$3"
    local when="$4"
    
    python3 << PYCODE
import sys
sys.path.insert(0, '/root/trading-bot/.zeroclaw')
from message_templates import MessageTemplates
from scheduler_watchdog import get_watchdog

templates = MessageTemplates()
watchdog = get_watchdog()

msg = templates.manual_signal(
    pair="$pair",
    action="$action",
    price="$price"
)

result = watchdog.schedule_post(msg, "$when", "$USER_ID", channel="$CHANNEL")

if result['success']:
    print(f"🚀 {('$action').upper()} SIGNAL SCHEDULED!")
    print(f"💱 Pair: $pair")
    print(f"💰 Price: $price")
    print(f"⏰ Time: {result['scheduled_time']}")
else:
    print(f"❌ Error: {result.get('error', 'Unknown')}")
PYCODE
}

# Aggressive pattern matching - intercept BEFORE AI
# Format: schedule <message> for <time>
case "$MSG_LOWER" in
  # Quick signal shortcuts
  "signal buy "*" in "*)
    # signal buy BTC/USDT at 67000 in 5 minutes
    REST="${MESSAGE#signal buy }"
    PAIR=$(echo "$REST" | awk '{print $1}')
    PRICE=$(echo "$REST" | grep -oP '(?<=at |@)\d+[\.,]?\d*' | head -1)
    WHEN=$(echo "$REST" | grep -oP 'in \d+ (minute|min|hour|hr)' | tail -1)
    [ -z "$WHEN" ] && WHEN="in 5 minutes"
    [ -z "$PRICE" ] && PRICE="market"
    quick_signal "$PAIR" "buy" "$PRICE" "$WHEN"
    ;;
    
  "signal sell "*" in "*)
    REST="${MESSAGE#signal sell }"
    PAIR=$(echo "$REST" | awk '{print $1}')
    PRICE=$(echo "$REST" | grep -oP '(?<=at |@)\d+[\.,]?\d*' | head -1)
    WHEN=$(echo "$REST" | grep -oP 'in \d+ (minute|min|hour|hr)' | tail -1)
    [ -z "$WHEN" ] && WHEN="in 5 minutes"
    [ -z "$PRICE" ] && PRICE="market"
    quick_signal "$PAIR" "sell" "$PRICE" "$WHEN"
    ;;

  # Show pending posts
  "pending"|"scheduled"|"my posts"|"show pending")
    show_pending
    ;;

  # General schedule pattern
  schedule*" for "*)
    # Extract message and time
    REST="${MESSAGE#schedule }"
    # Split on " for " 
    MSG_PART="${REST%% for *}"
    TIME_PART="${REST##* for }"
    
    # Clean up
    MSG_PART=$(echo "$MSG_PART" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    TIME_PART=$(echo "$TIME_PART" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    if [ -n "$MSG_PART" ] && [ -n "$TIME_PART" ]; then
        schedule_post "$MSG_PART" "$TIME_PART"
    else
        echo "❌ Usage: schedule <message> for <time>"
        echo "   Example: schedule Buy BTC at 67000 for in 5 minutes"
    fi
    ;;
    
  # Alert pattern
  "alert "*)
    # alert when BTC crosses above 70000 in 30 minutes
    schedule_post "$MESSAGE" "in 1 minute"
    ;;
    
  # Reminder pattern  
  "remind me "*)
    schedule_post "$MESSAGE" "in 1 minute"
    ;;

  # Broadcast pattern
  "broadcast "*)
    schedule_post "$MESSAGE" "in 1 minute"
    ;;

  # Help for scheduling
  "schedule help"|"how to schedule")
    echo "📅 <b>SCHEDULER HELP</b>"
    echo ""
    echo "<b>Quick Signals:</b>"
    echo "  • signal buy BTC/USDT at 67000 in 5 minutes"
    echo "  • signal sell ETH at 3500 in 1 hour"
    echo ""
    echo "<b>Manual Schedule:</b>"
    echo "  • schedule Buy the dip for in 10 minutes"
    echo "  • schedule BTC breaking out! for tomorrow 9am"
    echo ""
    echo "<b>Alerts & Reminders:</b>"
    echo "  • alert when BTC hits 70000 in 30 minutes"
    echo "  • remind me to check SOL position in 2 hours"
    echo ""
    echo "<b>Check Pending:</b>"
    echo "  • pending"
    echo "  • scheduled"
    ;;
    
  # Weather pattern
  "weather"*)
    CITY=$(echo "$MESSAGE" | sed 's/weather//i' | sed 's/in//i' | xargs)
    [ -z "$CITY" ] && CITY="Basseterre"
    /root/.zeroclaw/skills/weather/weather.sh "$CITY"
    ;;

  # Default: pass to AI
  *)
    echo "$MESSAGE"
    ;;
esac
