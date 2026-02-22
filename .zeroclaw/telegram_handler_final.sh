#!/bin/bash
# Final working handler - outputs directly for zeroclaw

read -r JSON_PAYLOAD

# Extract message and user_id
MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('message',''))")
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('user_id',''))")

MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
TOOL_DIR="/root/trading-bot/.zeroclaw"

# Check for scheduled posts
python3 "$TOOL_DIR/schedule_tool.py" check 2>/dev/null

# Handle commands
case "$MSG_LOWER" in
  schedule*)
    REST=$(echo "$MESSAGE" | sed 's/^[Ss]chedule //')
    if echo "$REST" | grep -qi " for "; then
        MSG_PART=$(echo "$REST" | sed 's/ for .*//')
        TIME_PART=$(echo "$REST" | sed 's/.* for //')
        
        # Output schedule result directly
        python3 -c "
import sys
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
result = ScheduleTool.schedule('''$MSG_PART''', '''$TIME_PART''', '$USER_ID')
if result['success']:
    print(f'''✅ SCHEDULED: {result['message_preview']}
🕐 When: {result['scheduled_time']}
💡 I'll send this to the channel at the scheduled time!''')
else:
    print(f'❌ Error: ' + result.get('error', 'Unknown error'))
"
    else
        echo "❌ Format: schedule [message] for [when]
Example: schedule Buy BTC for tomorrow 9am"
    fi
    ;;
    
  "my schedules"|"list schedules")
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
    ;;
    
  menu*|/menu|start|/start)
    echo "🤖 <b>Trading Bot Menu</b>

Use the buttons below or type:
• schedule [msg] for [when]
• my schedules
• help"
    ;;
    
  *)
    # Pass to AI
    echo "$MESSAGE"
    ;;
esac
