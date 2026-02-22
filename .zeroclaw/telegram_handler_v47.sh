#!/bin/bash
# v4.7 - Direct output, no command substitution issues

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"
TOOL_DIR="/root/trading-bot/.zeroclaw"

# Check for scheduled posts first
python3 "$TOOL_DIR/schedule_tool.py" check > /dev/null 2>&1

# Handle commands
case "$MSG_LOWER" in
  "menu"|"/menu"|"start"|"/start")
    echo "🤖 <b>Trading Bot Menu</b>

Use the Reply Keyboard below!"
    ;;
    
  "schedule "*)
    REST=$(echo "$MESSAGE" | sed 's/^schedule //i')
    
    if echo "$REST" | grep -qi " for "; then
        MSG_PART=$(echo "$REST" | sed 's/ for .*//i')
        TIME_PART=$(echo "$REST" | sed 's/.* for //i')
        
        # Schedule directly and output result
        python3 << PYCODE
import sys
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
result = ScheduleTool.schedule("""$MSG_PART""", """$TIME_PART""", "$USER_ID")
if result["success"]:
    print(f"✅ SCHEDULED: {result['message_preview']}")
    print(f"🕐 When: {result['scheduled_time']}")
else:
    print(f"❌ Error: {result['error']}")
PYCODE
    else
        echo "❌ Format: schedule [message] for [when]"
        echo "Example: schedule Buy BTC for tomorrow 9am"
    fi
    ;;
    
  "my schedules"|"list schedules")
    python3 << PYCODE
import sys
sys.path.insert(0, '$TOOL_DIR')
from schedule_tool import ScheduleTool
posts = ScheduleTool.list_user_posts("$USER_ID")
if posts:
    print(f"📅 You have {len(posts)} scheduled post(s):")
    for p in posts[:3]:
        print(f"- {p['message'][:30]}... at {p['scheduled_time'][:16]}")
else:
    print("📭 No scheduled posts")
PYCODE
    ;;
    
  *)
    # Unknown - let AI handle
    echo "$MESSAGE"
    ;;
esac
