#!/bin/bash
# Personal Bot Handler - Sends Reply Keyboard directly via Telegram API

read -r JSON_PAYLOAD

# Extract fields
MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8539644338:AAG5We86Wqcrzbj0ijn01-IO6YUC_BKVCSk"

# Function to send message with Reply Keyboard
send_reply_keyboard() {
    local text="$1"
    
    python3 << PYCODE
import json
import urllib.request

text = """$text"""

payload = {
    "chat_id": "$USER_ID",
    "text": text,
    "parse_mode": "HTML",
    "reply_markup": {
        "keyboard": [
            [{"text": "💾 Capture Note"}, {"text": "🔍 Search Memory"}],
            [{"text": "📊 Dashboard"}, {"text": "📅 Daily Summary"}],
            [{"text": "❓ Help"}, {"text": "🗑️ Close Menu"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    f"https://api.telegram.org/bot${BOT_TOKEN}/sendMessage",
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    urllib.request.urlopen(req, timeout=10)
except Exception as e:
    print(f"Error: {e}")
PYCODE
}

# Function to hide keyboard
hide_keyboard() {
    python3 << PYCODE
import json
import urllib.request

payload = {
    "chat_id": "$USER_ID",
    "text": "✅ Keyboard hidden. Type 'menu' anytime to bring it back!",
    "reply_markup": {
        "remove_keyboard": True
    }
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    f"https://api.telegram.org/bot${BOT_TOKEN}/sendMessage",
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    urllib.request.urlopen(req, timeout=10)
except:
    pass
PYCODE
}

# Function to send plain message
send_message() {
    local text="$1"
    
    python3 << PYCODE
import json
import urllib.request

text = """$text"""

payload = {
    "chat_id": "$USER_ID",
    "text": text,
    "parse_mode": "HTML"
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    f"https://api.telegram.org/bot${BOT_TOKEN}/sendMessage",
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    urllib.request.urlopen(req, timeout=10)
except:
    pass
PYCODE
}

# Route commands
case "$MSG_LOWER" in
    
  "menu"|"/menu"|"start"|"/start"|"buttons"|"keyboard")
    send_reply_keyboard "🤖 <b>ZeroClaw Personal Bot</b>

Choose an action:"
    ;;
    
  "🗑️ close menu"|"close menu"|"hide keyboard")
    hide_keyboard
    ;;
    
  "💾 capture note"*)
    CONTENT=$(echo "$MESSAGE" | sed 's/^💾 Capture Note //i')
    if [ -z "$CONTENT" ]; then
        send_message "📝 What would you like to capture?

Type after the button:
💾 Capture Note My wifi password is XYZ123"
    else
        RESULT=$(python3 "$HOME/.zeroclaw/memory_system.py" capture "$CONTENT" 2>/dev/null)
        send_message "✅ <b>Saved to Memory Vault!</b>

💾 $CONTENT"
    fi
    ;;
    
  "🔍 search memory"*)
    QUERY=$(echo "$MESSAGE" | sed 's/^🔍 Search Memory //i')
    if [ -z "$QUERY" ]; then
        send_message "🔍 What would you like to search for?

Type after the button:
🔍 Search Memory wifi password"
    else
        send_message "🔍 <b>Searching for:</b> $QUERY

(use 'search $QUERY' for full results)"
    fi
    ;;
    
  "📊 dashboard")
    DASHBOARD=$(python3 "$HOME/.zeroclaw/visual_dashboard.py" 2>/dev/null)
    send_message "$DASHBOARD"
    ;;
    
  "📅 daily summary"|"daily"|"today")
    RESULT=$(python3 "$HOME/.zeroclaw/memory_system.py" daily 2>/dev/null)
    send_message "📅 <b>Daily Summary</b>

$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Notes: {d.get('total_notes',0)}\")" 2>/dev/null)"
    ;;
    
  "❓ help"|"help"|"/help")
    send_message "🤖 <b>Help</b>

📱 <b>Buttons:</b>
• 💾 Capture Note - Save with auto-tags
• 🔍 Search Memory - Find notes
• 📊 Dashboard - Activity overview
• 📅 Daily Summary - Today's stats
• 🗑️ Close Menu - Hide keyboard

💡 Type 'menu' anytime to show buttons."
    ;;
    
  *)
    # Auto-capture long or keyword-rich messages
    WORD_COUNT=$(echo "$MESSAGE" | wc -w)
    
    if [ $WORD_COUNT -gt 15 ] || echo "$MSG_LOWER" | grep -qE "(remember|important|idea|decided|plan|todo|task|meeting)"; then
        python3 "$HOME/.zeroclaw/memory_system.py" capture "$MESSAGE" > /dev/null 2>&1
        send_message "✅ Auto-saved to Memory Vault!"
    else
        # Unknown command - let ZeroClaw AI handle it
        echo "$MESSAGE"
    fi
    ;;
esac
