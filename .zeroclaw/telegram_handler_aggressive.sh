#!/bin/bash
# Aggressive handler - captures schedule commands immediately

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

TOOL_DIR="/root/trading-bot/.zeroclaw"

# Check for scheduled posts first
python3 "$TOOL_DIR/schedule_tool.py" check 2>/dev/null

# If message starts with "schedule" (case insensitive) - handle it
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')

if echo "$MSG_LOWER" | grep -q "^schedule "; then
    # Extract message and time
    REST=$(echo "$MESSAGE" | sed 's/^[Ss]chedule //')
    
    if echo "$REST" | grep -qi " for "; then
        MSG_PART=$(echo "$REST" | sed 's/ for .*//')
        TIME_PART=$(echo "$REST" | sed 's/.* for //')
        
        # Schedule and output result
        python3 -c "
import sys
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
result = ScheduleTool.schedule('''$MSG_PART''', '''$TIME_PART''', '$USER_ID')
if result['success']:
    print(f'''✅ POST SCHEDULED!

Message: {result['message_preview']}
Time: {result['scheduled_time']}
Channel: Arbitrage Pro Signals

This will be posted automatically.''')
else:
    print(f'❌ Error: ' + result.get('error', 'Unknown'))
"
        exit 0  # Exit here - don't let AI handle it
    else
        echo "❌ Usage: schedule [message] for [when]"
        echo "Example: schedule Buy BTC for tomorrow 9am"
        exit 0
    fi
fi

if echo "$MSG_LOWER" | grep -q "^my schedules"; then
    python3 -c "
import sys
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
posts = ScheduleTool.list_user_posts('$USER_ID')
if posts:
    print(f'📅 You have {len(posts)} scheduled post(s):')
    for p in posts[:5]:
        msg = p['message'][:40] + '...' if len(p['message']) > 40 else p['message']
        print(f'• {msg}')
        print(f'  🕐 {p[\"scheduled_time\"][:16]}')
else:
    print('📭 No scheduled posts')
"
    exit 0
fi

# For everything else - let AI handle it
echo "$MESSAGE"
