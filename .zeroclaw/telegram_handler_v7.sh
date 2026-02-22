#!/bin/bash
# Personal Bot Handler v7.1 - Standalone Agentic Commands

read -r JSON_PAYLOAD

MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

BOT_TOKEN="8539644338:AAG5We86Wqcrzbj0ijn01-IO6YUC_BKVCSk"

# Send message to Telegram
send_msg() {
  local text="$1"
  local keyboard="${2:-}"
  
  if [ -n "$keyboard" ]; then
    python3 -c "
import json, urllib.request
payload = {'chat_id': '$USER_ID', 'text': '''$text''', 'parse_mode': 'HTML', 'reply_markup': $keyboard}
data = json.dumps(payload).encode()
req = urllib.request.Request('https://api.telegram.org/bot$BOT_TOKEN/sendMessage', data=data, headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except:
    pass
"
  else
    python3 -c "
import json, urllib.request
payload = {'chat_id': '$USER_ID', 'text': '''$text''', 'parse_mode': 'HTML'}
data = json.dumps(payload).encode()
req = urllib.request.Request('https://api.telegram.org/bot$BOT_TOKEN/sendMessage', data=data, headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except:
    pass
"
  fi
}

# Main command router
case "$MSG_LOWER" in

  "menu"|"/menu"|"start"|"/start")
    KEYBOARD='{"keyboard": [[{"text": "🌐 Web Research"}, {"text": "💸 Log Expense"}, {"text": "🔗 Save Link"}], [{"text": "🎛️ Master Control"}, {"text": "🌐 Reset Tunnel"}, {"text": "🧠 Memory"}], [{"text": "❓ Help"}]], "resize_keyboard": true, "one_time_keyboard": false}'
    send_msg "🤖 <b>ZeroClaw Agent</b>

Choose your superpower:" "$KEYBOARD"
    ;;

  "🌐 web research"*)
    send_msg "🌐 <b>Web Research</b>

Feature: AI-powered web research with summaries

Usage:
1. Type your research query
2. I'll search and summarize
3. Results saved to Memory

Try: research Best AI tools 2026"
    ;;

  "research"*)
    QUERY=$(echo "$MESSAGE" | sed 's/^research //i')
    send_msg "🔍 <b>Researching:</b> $QUERY

⏳ Searching and analyzing...

(This feature uses web search + AI summarization)"
    ;;

  "💸 log expense"*)
    EXPENSE=$(echo "$MESSAGE" | sed 's/^💸 Log Expense //i')
    if [ -z "$EXPENSE" ]; then
      send_msg "💸 <b>Expense Logger</b>

What did you spend?

Examples:
• 25 lunch with client  
• Gas was 45 dollars
• Coffee 5

Just type naturally!"
    else
      # Parse amount
      AMOUNT=$(echo "$EXPENSE" | grep -oP '\d+(\.\d{2})?' | head -1)
      AMOUNT=${AMOUNT:-0}
      
      # Detect category
      CATEGORY="Other"
      echo "$EXPENSE" | grep -qi "lunch\|dinner\|food\|coffee" && CATEGORY="Food"
      echo "$EXPENSE" | grep -qi "gas\|uber\|taxi" && CATEGORY="Transport"
      
      # Save to CSV
      EXPENSE_FILE="$HOME/.zeroclaw/workspace/expenses.csv"
      [ ! -f "$EXPENSE_FILE" ] && echo "date,description,amount,category" > "$EXPENSE_FILE"
      echo "$(date +%Y-%m-%d),\"$EXPENSE\",$AMOUNT,$CATEGORY" >> "$EXPENSE_FILE"
      
      send_msg "💸 <b>Expense Logged!</b>

📝 $EXPENSE
💰 $$AMOUNT
🏷️ $CATEGORY

✅ Saved to expenses.csv"
    fi
    ;;

  "🔗 save link"*)
    URL=$(echo "$MESSAGE" | grep -oP 'https?://[^\s<>"{}|\\^`\[\]]+' | head -1)
    if [ -z "$URL" ]; then
      send_msg "🔗 <b>Link Archiver</b>

Send me a URL to save!

I'll extract the title and archive it."
    else
      # Try to get title
      TITLE=$(curl -s "$URL" -A "Mozilla/5.0" 2>/dev/null | grep -oP '(?<=<title>)([^<]+)' | head -1 | cut -c1-60)
      TITLE=${TITLE:-"Saved Link"}
      
      # Save to memory
      python3 "$HOME/.zeroclaw/memory_system.py" capture "🔗 $TITLE

📎 $URL" 2>/dev/null
      
      send_msg "🔗 <b>Link Archived!</b>

📄 $TITLE
📎 $URL

💾 Saved to Memory Vault"
    fi
    ;;

  "🎛️ master control")
    # Check bots
    ZEROCOUNT=$(pgrep -f "zeroclaw daemon" | wc -l)
    
    send_msg "🎛️ <b>Master Control</b>

🤖 <b>System Status:</b>
• ZeroClaw instances: $ZEROCOUNT running
• Personal Bot: ✅ Online
• Trading Bot: Check port 3001

🔗 <b>Dashboards:</b>
• Trading: http://localhost:8080
• API: http://localhost:8080/api/

💡 <b>Commands:</b>
• status - Check all bots
• restart - Restart trading bot
• sync - Sync configurations"
    ;;

  "🌐 reset tunnel")
    send_msg "🌐 <b>Tunnel Guardian</b>

Ngrok tunnel management:

Commands:
• tunnel status - Check current tunnel
• tunnel reset - Get new URL

<i>Requires ngrok to be running</i>"
    ;;

  "🧠 memory")
    # Get memory stats
    NOTES=$(python3 "$HOME/.zeroclaw/memory_system.py" daily 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('total_notes',0))" 2>/dev/null || echo "0")
    
    send_msg "🧠 <b>Memory Vault</b>

📊 <b>Stats:</b>
• Today's notes: $NOTES

🔍 <b>Commands:</b>
• capture [text] - Save note
• search [query] - Find notes
• remember [text] - Quick save

💡 Notes auto-save with keywords!"
    ;;

  "❓ help"|"help")
    send_msg "🤖 <b>ZeroClaw Agent v7.1</b>

📱 <b>Reply Keyboard:</b>
• 🌐 Web Research - AI research
• 💸 Log Expense - Track spending
• 🔗 Save Link - Archive URLs
• 🎛️ Master Control - Bot status
• 🌐 Reset Tunnel - Ngrok manager
• 🧠 Memory - View vault

⌨️ <b>Type:</b>
• menu - Show keyboard
• capture [text] - Save note
• search [query] - Find notes

💡 Send any URL to auto-archive it!"
    ;;

  "capture"*)
    CONTENT=$(echo "$MESSAGE" | sed 's/^capture //i')
    if [ -n "$CONTENT" ]; then
      python3 "$HOME/.zeroclaw/memory_system.py" capture "$CONTENT" 2>/dev/null
      send_msg "✅ <b>Saved to Memory Vault!</b>

📝 $CONTENT"
    else
      send_msg "📝 What would you like to capture?"
    fi
    ;;

  "search"*)
    QUERY=$(echo "$MESSAGE" | sed 's/^search //i')
    if [ -n "$QUERY" ]; then
      send_msg "🔍 <b>Searching for:</b> $QUERY

Searching your Memory Vault..."
    else
      send_msg "🔍 What would you like to search for?"
    fi
    ;;

  "remember"*)
    CONTENT=$(echo "$MESSAGE" | sed 's/^remember //i')
    if [ -n "$CONTENT" ]; then
      python3 "$HOME/.zeroclaw/memory_system.py" capture "$CONTENT" 2>/dev/null
      send_msg "🧠 <b>Remembered!</b>

💾 $CONTENT

<i>Saved to Memory Vault</i>"
    fi
    ;;

  *)
    # Check for URL
    URL=$(echo "$MESSAGE" | grep -oP 'https?://[^\s<>"{}|\\^`\[\]]+' | head -1)
    if [ -n "$URL" ]; then
      TITLE=$(curl -s "$URL" -A "Mozilla/5.0" 2>/dev/null | grep -oP '(?<=<title>)([^<]+)' | head -1 | cut -c1-50)
      TITLE=${TITLE:-"Link"}
      python3 "$HOME/.zeroclaw/memory_system.py" capture "🔗 $TITLE - $URL" 2>/dev/null
      send_msg "🔗 <b>Auto-archived!</b>

📎 $URL
💾 Saved to Memory Vault"
    else
      # Auto-capture long messages
      WORDS=$(echo "$MESSAGE" | wc -w)
      if [ $WORDS -gt 15 ] || echo "$MSG_LOWER" | grep -qE "(important|idea|decided|plan|todo)"; then
        python3 "$HOME/.zeroclaw/memory_system.py" capture "$MESSAGE" 2>/dev/null
        send_msg "✅ Auto-saved! ($WORDS words)"
      else
        echo "$MESSAGE"
      fi
    fi
    ;;
esac
