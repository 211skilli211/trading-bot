#!/bin/bash
# Personal Bot Handler v7.5 - Agentic Superpowers (Fixed Pattern)

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
    KEYBOARD='{"keyboard": [[{"text": "🌐 Web Research"}, {"text": "💸 Log Expense"}, {"text": "🔗 Save Link"}], [{"text": "🎛️ Master Control"}, {"text": "🌐 Reset Tunnel"}, {"text": "🧠 Memory"}], [{"text": "❓ Help"}]], "resize_keyboard": true, "one_time_keyboard": false}'
    send_msg "🤖 <b>ZeroClaw Agent</b>\n\nChoose your superpower:" "$KEYBOARD"
    echo "✅ Agent menu sent!"
    ;;
    
  "🗑️ close"|"close menu"|"hide")
    REMOVE='{"remove_keyboard": true}'
    send_msg "✅ Keyboard hidden. Type 'menu' to bring it back!" "$REMOVE"
    echo "✅ Closed!"
    ;;
    
  "🌐 web research"*)
    send_msg "🌐 <b>Web Research Agent</b>\n\nWhat should I research?\n\nExamples:\n• Best AI tools 2026\n• Latest crypto news\n• Top programming languages\n\nJust type your topic!" ""
    echo "✅ Web research ready!"
    ;;
    
  "💸 log expense"*)
    EXPENSE=$(echo "$MESSAGE" | sed 's/^💸 Log Expense //i')
    if [ -z "$EXPENSE" ]; then
      send_msg "💸 <b>Quick Expense Logger</b>\n\nWhat did you spend?\n\nExamples:\n• 25 lunch with client\n• Gas was 45 dollars\n• Coffee 5\n\nJust type naturally!" ""
    else
      AMOUNT=$(echo "$EXPENSE" | grep -oP '\d+(\.\d{2})?' | head -1)
      AMOUNT=${AMOUNT:-0}
      CATEGORY="Other"
      echo "$EXPENSE" | grep -qi "lunch\|dinner\|food\|coffee" && CATEGORY="Food"
      echo "$EXPENSE" | grep -qi "gas\|uber\|taxi" && CATEGORY="Transport"
      
      EXPENSE_FILE="$HOME/.zeroclaw/workspace/expenses.csv"
      [ ! -f "$EXPENSE_FILE" ] && echo "date,description,amount,category" > "$EXPENSE_FILE"
      echo "$(date +%Y-%m-%d),\"$EXPENSE\",$AMOUNT,$CATEGORY" >> "$EXPENSE_FILE"
      
      send_msg "💸 <b>Expense Logged!</b>\n\n📝 $EXPENSE\n💰 $$AMOUNT\n🏷️ $CATEGORY\n\n✅ Saved to expenses.csv" ""
    fi
    echo "✅ Expense handled!"
    ;;
    
  "🔗 save link"*)
    URL=$(echo "$MESSAGE" | grep -oP 'https?://[^\s<>"{}|\\^`\[\]]+' | head -1)
    if [ -z "$URL" ]; then
      send_msg "🔗 <b>Link Archiver</b>\n\nSend me a URL to save!\n\nI'll extract the title and create a summary." ""
    else
      TITLE=$(curl -s "$URL" -A "Mozilla/5.0" 2>/dev/null | grep -oP '(?<=<title>)([^<]+)' | head -1 | cut -c1-60)
      TITLE=${TITLE:-"Saved Link"}
      python3 "$HOME/.zeroclaw/memory_system.py" capture "🔗 $TITLE\n\n📎 $URL" 2>/dev/null
      send_msg "🔗 <b>Link Archived!</b>\n\n📄 $TITLE\n📎 $URL\n\n💾 Saved to Memory Vault" ""
    fi
    echo "✅ Link handled!"
    ;;
    
  "🎛️ master control")
    ZEROCOUNT=$(pgrep -f "zeroclaw daemon" | wc -l)
    send_msg "🎛️ <b>Master Control</b>\n\n🤖 <b>System Status:</b>\n• ZeroClaw instances: $ZEROCOUNT running\n• Personal Bot: ✅ Online\n• Trading Bot: Check port 3001\n\n🔗 <b>Dashboards:</b>\n• Trading: http://localhost:8080\n• API: http://localhost:8080/api/\n\n💡 <b>Commands:</b>\n• status - Check all bots\n• restart - Restart trading bot" ""
    echo "✅ Master control sent!"
    ;;
    
  "🌐 reset tunnel")
    send_msg "🌐 <b>Tunnel Guardian</b>\n\nNgrok tunnel management:\n\nCommands:\n• tunnel status - Check current tunnel\n• tunnel reset - Get new URL\n\n<i>Free ngrok URLs expire on restart</i>" ""
    echo "✅ Tunnel info sent!"
    ;;
    
  "🧠 memory")
    NOTES=$(python3 "$HOME/.zeroclaw/memory_system.py" daily 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('total_notes',0))" 2>/dev/null)
    send_msg "🧠 <b>Memory Vault</b>\n\n📊 <b>Stats:</b>\n• Today's notes: $NOTES\n\n🔍 <b>Commands:</b>\n• capture [text] - Save note\n• search [query] - Find notes\n• remember [text] - Quick save\n\n💡 Notes auto-save with keywords!" ""
    echo "✅ Memory info sent!"
    ;;
    
  "❓ help"|"help")
    send_msg "🤖 <b>ZeroClaw Agent v7.5</b>\n\n📱 <b>Superpowers:</b>\n• 🌐 Web Research - AI research\n• 💸 Log Expense - Track spending\n• 🔗 Save Link - Archive URLs\n• 🎛️ Master Control - Bot status\n• 🌐 Reset Tunnel - Ngrok manager\n• 🧠 Memory - View vault\n\n⌨️ <b>Type:</b>\n• menu - Show keyboard\n• capture [text] - Save note\n\n💡 Send any URL to auto-archive!" ""
    echo "✅ Help sent!"
    ;;
    
  "💾 capture"*)
    CONTENT=$(echo "$MESSAGE" | sed 's/^💾 capture //i')
    if [ -n "$CONTENT" ]; then
      python3 "$HOME/.zeroclaw/memory_system.py" capture "$CONTENT" 2>/dev/null
      send_msg "✅ <b>Saved to Memory Vault!</b>\n\n📝 $CONTENT" ""
    else
      send_msg "📝 What would you like to capture?" ""
    fi
    echo "✅ Capture handled!"
    ;;
    
  "🔍 search"*)
    QUERY=$(echo "$MESSAGE" | sed 's/^🔍 search //i')
    if [ -n "$QUERY" ]; then
      send_msg "🔍 <b>Searching for:</b> $QUERY\n\nSearching your Memory Vault..." ""
    else
      send_msg "🔍 What would you like to search for?" ""
    fi
    echo "✅ Search handled!"
    ;;
    
  "remember"*)
    CONTENT=$(echo "$MESSAGE" | sed 's/^remember //i')
    if [ -n "$CONTENT" ]; then
      python3 "$HOME/.zeroclaw/memory_system.py" capture "$CONTENT" 2>/dev/null
      send_msg "🧠 <b>Remembered!</b>\n\n💾 $CONTENT\n\n<i>Saved to Memory Vault</i>" ""
    fi
    echo "✅ Remember handled!"
    ;;
    
  *)
    URL=$(echo "$MESSAGE" | grep -oP 'https?://[^\s<>"{}|\\^`\[\]]+' | head -1)
    if [ -n "$URL" ]; then
      TITLE=$(curl -s "$URL" -A "Mozilla/5.0" 2>/dev/null | grep -oP '(?<=<title>)([^<]+)' | head -1 | cut -c1-50)
      TITLE=${TITLE:-"Link"}
      python3 "$HOME/.zeroclaw/memory_system.py" capture "🔗 $TITLE - $URL" 2>/dev/null
      send_msg "🔗 <b>Auto-archived!</b>\n\n📎 $URL\n💾 Saved to Memory Vault" ""
    else
      WORDS=$(echo "$MESSAGE" | wc -w)
      if [ $WORDS -gt 15 ] || echo "$MSG_LOWER" | grep -qE "(important|idea|decided|plan|todo)"; then
        python3 "$HOME/.zeroclaw/memory_system.py" capture "$MESSAGE" 2>/dev/null
        send_msg "✅ Auto-saved! ($WORDS words)" ""
      else
        echo "$MESSAGE"
      fi
    fi
    ;;
esac
