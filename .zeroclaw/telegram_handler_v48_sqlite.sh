#!/bin/bash
# v4.8 - Uses SQLite Watchdog for reliable scheduling

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

TOOL_DIR="/root/trading-bot/.zeroclaw"
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')

# Ensure watchdog is running
if ! pgrep -f "scheduler_watchdog.py" > /dev/null; then
    "$TOOL_DIR/start_watchdog.sh" > /dev/null 2>&1
fi

# Handle commands
case "$MSG_LOWER" in
  schedule*)
    REST=$(echo "$MESSAGE" | sed 's/^[Ss]chedule //')
    
    if echo "$REST" | grep -qi " for "; then
        MSG_PART=$(echo "$REST" | sed 's/ for .*//i')
        TIME_PART=$(echo "$REST" | sed 's/.* for //i')
        
        # Use SQLite watchdog
        python3 -c "
import sys
sys.path.insert(0, '$TOOL_DIR')
from scheduler_watchdog import get_watchdog
wd = get_watchdog()
result = wd.schedule_post('''$MSG_PART''', '''$TIME_PART''', '$USER_ID')
if result['success']:
    print(f'''✅ SCHEDULED TO CHANNEL!

📝 {result['message_preview']}
🕐 {result['scheduled_time']}
📢 Arbitrage Pro Signals

Message will post automatically.''')
else:
    print('❌ ' + result['error'])
"
    else
        echo "❌ Usage: schedule [message] for [when]"
        echo ""
        echo "Examples:"
        echo "  schedule Buy BTC now! for in 2 minutes"
        echo "  schedule Price alert for tomorrow 9am"
    fi
    ;;
    
  "my schedules"|"list schedules")
    python3 -c "
import sys
sys.path.insert(0, '$TOOL_DIR')
from scheduler_watchdog import get_watchdog
wd = get_watchdog()
posts = wd.list_user_posts('$USER_ID')
if posts:
    print(f'📅 You have {len(posts)} scheduled post(s):\n')
    for i, (pid, msg, time) in enumerate(posts[:5], 1):
        short_msg = msg[:40] + '...' if len(msg) > 40 else msg
        time_str = time[:16].replace('T', ' ')
        print(f'{i}. {short_msg}')
        print(f'   🕐 {time_str}\n')
else:
    print('📭 No scheduled posts')
"
    ;;
    
  menu*|/menu|start|/start)
    echo "🤖 <b>ZeroClaw Trading Bot</b>

📅 <b>Schedule Posts:</b>
• schedule [msg] for [when]
• my schedules

💡 Posts auto-send to Arbitrage Pro Signals!"
    ;;
    
  *)
    # Pass to AI
    echo "$MESSAGE"
    ;;
esac
