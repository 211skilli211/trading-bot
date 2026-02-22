#!/bin/bash
# Personal Bot Handler - Sends Reply Keyboard via Telegram API

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8539644338:AAG5We86Wqcrzbj0ijn01-IO6YUC_BKVCSk"

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

case "$MSG_LOWER" in
  
  "menu"|"/menu"|"start"|"/start")
    KEYBOARD='{"keyboard": [[{"text": "💾 Capture Note"}, {"text": "🔍 Search Memory"}], [{"text": "📊 Dashboard"}, {"text": "📅 Daily Summary"}], [{"text": "❓ Help"}, {"text": "🗑️ Close Menu"}]], "resize_keyboard": true, "one_time_keyboard": false}'
    send_msg "🤖 <b>ZeroClaw Personal Bot</b>\\n\\nChoose an action:" "$KEYBOARD"
    echo "✅ Menu sent!"
    ;;
    
  "🗑️ close menu"|"close menu")
    REMOVE='{"remove_keyboard": true}'
    send_msg "✅ Keyboard hidden. Type 'menu' anytime to bring it back!" "$REMOVE"
    echo "✅ Closed!"
    ;;
    
  "💾 capture note"*)
    CONTENT=$(echo "$MESSAGE" | sed 's/^💾 Capture Note //i')
    if [ -z "$CONTENT" ]; then
      send_msg "📝 What to capture?\\n\\nType: 💾 Capture Note [your text]"
      echo "📝 Awaiting..."
    else
      python3 "$HOME/.zeroclaw/memory_system.py" capture "$CONTENT" > /dev/null 2>&1
      send_msg "✅ <b>Saved!</b>\\n\\n💾 $CONTENT"
      echo "✅ Saved!"
    fi
    ;;
    
  "🔍 search memory"*)
    QUERY=$(echo "$MESSAGE" | sed 's/^🔍 Search Memory //i')
    if [ -z "$QUERY" ]; then
      send_msg "🔍 What to search?\\n\\nType: 🔍 Search Memory [query]"
      echo "🔍 Awaiting..."
    else
      send_msg "🔍 <b>Searching:</b> $QUERY"
      echo "🔍 Done!"
    fi
    ;;
    
  "📊 dashboard")
    DASH=$(python3 "$HOME/.zeroclaw/visual_dashboard.py" 2>/dev/null)
    send_msg "$DASH"
    echo "📊 Sent!"
    ;;
    
  "📅 daily summary"|"daily")
    RESULT=$(python3 "$HOME/.zeroclaw/memory_system.py" daily 2>/dev/null)
    NOTES=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('total_notes',0))" 2>/dev/null)
    send_msg "📅 <b>Daily Summary</b>\\n\\n📝 Notes: $NOTES"
    echo "📅 Sent!"
    ;;
    
  "❓ help"|"help")
    send_msg "🤖 <b>Help</b>\\n\\n📱 Buttons work!\\n💡 Type 'menu' for keyboard."
    echo "❓ Sent!"
    ;;
    
  *)
    WORDS=$(echo "$MESSAGE" | wc -w)
    if [ $WORDS -gt 15 ] || echo "$MSG_LOWER" | grep -qE "(remember|important|idea)"; then
      python3 "$HOME/.zeroclaw/memory_system.py" capture "$MESSAGE" > /dev/null 2>&1
      send_msg "✅ Auto-saved! ($WORDS words)"
      echo "✅ Auto!"
    else
      echo "$MESSAGE"
    fi
    ;;
esac
