#!/bin/bash
# Fixed handler - captures schedule commands IMMEDIATELY

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)
TOOL_DIR="/root/trading-bot/.zeroclaw"

# First: Check for any scheduled posts that need sending
SENT=$(python3 "$TOOL_DIR/schedule_tool.py" check 2>/dev/null)
if echo "$SENT" | grep -q "Sent [1-9]"; then
    echo "📨 Scheduled post was just sent to your channel!"
fi

# Check if message starts with "schedule" (case insensitive)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')

if [[ "$MSG_LOWER" == schedule* ]]; then
    # Extract the parts after "schedule "
    REST="${MESSAGE#schedule }"
    REST="${REST#Schedule }"
    
    # Check if it contains " for "
    if echo "$REST" | grep -qi " for "; then
        # Split on " for "
        MSG_PART=$(echo "$REST" | sed 's/ for .*//i')
        TIME_PART=$(echo "$REST" | sed 's/.* for //i')
        
        # Schedule it
        python3 -c "
import sys
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
from datetime import datetime
result = ScheduleTool.schedule('''$MSG_PART''', '''$TIME_PART''', '$USER_ID')
if result['success']:
    # Get local time
    now = datetime.now()
    print(f'''✅ POST SCHEDULED TO CHANNEL!

📝 Message: {result['message_preview']}
🕐 Scheduled: {result['scheduled_time']}
📢 Channel: Arbitrage Pro Signals

💡 This message will be posted automatically.
Send any message after the scheduled time to trigger delivery.''')
else:
    print('❌ Error: ' + result.get('error', 'Could not schedule'))
"
    else
        echo "❌ Format: schedule [your message] for [when]"
        echo ""
        echo "Examples:"
        echo "  schedule Buy BTC now! for in 2 minutes"
        echo "  schedule Price alert for tomorrow 9am"
        echo "  schedule Market update for in 1 hour"
    fi
    # Exit without passing to AI
    exit 0
fi

# Handle "my schedules" command
if [[ "$MSG_LOWER" == "my schedules" ]] || [[ "$MSG_LOWER" == "list schedules" ]]; then
    python3 -c "
import sys
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
posts = ScheduleTool.list_user_posts('$USER_ID')
if posts:
    print(f'📅 Your Scheduled Posts ({len(posts)} total):')
    print('')
    for i, p in enumerate(posts[:5], 1):
        msg = p['message'][:50] + '...' if len(p['message']) > 50 else p['message']
        time_str = p['scheduled_time'][:16].replace('T', ' ')
        print(f'{i}. {msg}')
        print(f'   🕐 {time_str}')
        print('')
    print('💡 These will post to Arbitrage Pro Signals automatically.')
else:
    print('📭 No scheduled posts.')
    print('')
    print('To schedule: schedule [message] for [when]')
"
    exit 0
fi

# For all other messages, let the AI handle it
echo "$MESSAGE"
