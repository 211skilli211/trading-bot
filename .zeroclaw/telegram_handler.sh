#!/bin/bash
# Personal Bot Handler v7.0 - Agentic Commands with Master Control

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
    data=data, headers={'Content-Type': 'application/json'}
)
try:
    urllib.request.urlopen(req, timeout=10)
except:
    pass
PYCODE
}

# Route commands
case "$MSG_LOWER" in

  # Main Menu - Agentic Commands
  "menu"|"/menu"|"start"|"/start")
    KEYBOARD=$(python3 -c "import json; print(json.dumps({'keyboard': [[{'text': '🌐 Web Research'}, {'text': '💸 Log Expense'}, {'text': '🔗 Save Link'}], [{'text': '🎛️ Master Control'}, {'text': '🌐 Reset Tunnel'}, {'text': '🧠 Memory'}], [{'text': '❓ Help'}]], 'resize_keyboard': True, 'one_time_keyboard': False}))")
    send_msg "🤖 <b>ZeroClaw Agent</b> - Your Mobile Command Center

Choose your superpower:" "$KEYBOARD"
    echo "✅ Agent menu sent!"
    ;;

  # Web Research
  "🌐 web research"*)
    QUERY=$(echo "$MESSAGE" | sed 's/^🌐 Web Research //i')
    if [ -z "$QUERY" ]; then
      send_msg "🌐 <b>Web Research Agent</b>

What should I research?

Examples:
• Best mechanical keyboards 2026
• Latest AI model releases
• Crypto market trends

Type: 🌐 Web Research [topic]"
    else
      send_msg "🔍 Researching: <b>$QUERY</b>...

⏳ This takes ~15 seconds. I'll search and summarize key findings."
      # Run research in background (would take too long for sync response)
      echo "🌐 Research: $QUERY"  # ZeroClaw skill will handle this
    fi
    ;;

  # Expense Logger
  "💸 log expense"*)
    EXPENSE=$(echo "$MESSAGE" | sed 's/^💸 Log Expense //i')
    if [ -z "$EXPENSE" ]; then
      send_msg "💸 <b>Quick Expense Logger</b>

What did you spend?

Examples:
• 💸 Log Expense 25 lunch with client
• 💸 Log Expense Gas was 45 dollars
• 💸 Log Expense Coffee 5

Just type naturally - I'll extract amount and category!"
    else
      # Parse and log
      EXPENSE_FILE="$HOME/.zeroclaw/workspace/expenses.csv"
      [ ! -f "$EXPENSE_FILE" ] && echo "date,description,amount,category" > "$EXPENSE_FILE"

      # Simple parsing
      AMOUNT=$(echo "$EXPENSE" | grep -oP '\d+(\.\d{2})?' | head -1)
      AMOUNT=${AMOUNT:-0}

      # Detect category
      CATEGORY="Other"
      echo "$EXPENSE" | grep -qi "lunch\|dinner\|food\|coffee\|meal" && CATEGORY="Food"
      echo "$EXPENSE" | grep -qi "gas\|uber\|taxi\|transport" && CATEGORY="Transport"
      echo "$EXPENSE" | grep -qi "movie\|netflix\|game\|fun" && CATEGORY="Entertainment"

      DATE=$(date '+%Y-%m-%d')
      echo "$DATE,\"$EXPENSE\",$AMOUNT,$CATEGORY" >> "$EXPENSE_FILE"

      MONTH_TOTAL=$(awk -F',' "BEGIN{sum=0} \$1 ~ /^$(date +%Y-%m)/ {sum+=\$3} END{printf \"%.2f\", sum}" "$EXPENSE_FILE" 2>/dev/null || echo "0")

      send_msg "💸 <b>Expense Logged!</b>

📝 $EXPENSE
💰 $$AMOUNT
🏷️ $CATEGORY
📅 $DATE

📊 This month: $$MONTH_TOTAL"
    fi
    ;;

  # Link Archiver
  "🔗 save link"*)
    URL=$(echo "$MESSAGE" | grep -oP 'https?://[^\s<>"{}|\\^`\[\]]+' | head -1)
    if [ -z "$URL" ]; then
      send_msg "🔗 <b>Link Archiver</b>

Send me a URL to save!

I'll extract the title and create a one-sentence summary.

Example:
🔗 Save Link https://example.com/article"
    else
      # Try to get title
      TITLE=$(curl -s "$URL" -A "Mozilla/5.0" 2>/dev/null | grep -oP '(?<=<title>)([^<]+)' | head -1 | tr -d '\n' | cut -c1-80)
      TITLE=${TITLE:-"Saved Link"}

      # Save to memory
      python3 "$HOME/.zeroclaw/memory_system.py" capture "🔗 $TITLE

📎 $URL" > /dev/null 2>&1

      send_msg "🔗 <b>Link Archived!</b>

📄 ${TITLE}
📎 $URL

💾 Saved to Memory Vault"
    fi
    ;;

  # Master Control
  "🎛️ master control"*)
    # Check bot statuses
    PERSONAL=$(pgrep -f "zeroclaw daemon" | wc -l)
    DASHBOARD=$(curl -s http://localhost:8080/api/trading/balance 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"💰 ${d.get('balance',{}).get('total_value_usd',0):,.0f}\" if d.get('success') else \"📊 N/A\")" 2>/dev/null || echo "📊 N/A")

    send_msg "🎛️ <b>Master Control</b>

🤖 <b>Bot Status:</b>
• ZeroClaw instances: $PERSONAL running
• Dashboard: http://localhost:8080
• Trading: $DASHBOARD

🔧 <b>Commands:</b>
• restart-trading - Restart trading bot
• sync - Sync bot configs
• dashboard - Trading dashboard info

<i>You are the Master Bot operator.</i>"
    ;;

  # Tunnel Guardian
  "🌐 reset tunnel"*)
    send_msg "🌐 <b>Tunnel Guardian</b>

Commands:
• 🌐 Reset Tunnel status - Check ngrok
• 🌐 Reset Tunnel reset - Get new URL

<i>Free ngrok URLs expire every restart</i>"
    ;;

  # Memory Vault
  "🧠 memory")
    send_msg "🧠 <b>Memory Vault</b>

Commands:
• capture [text] - Save note
• search [query] - Find notes
• daily - Today's summary

<i>Notes auto-save when they contain keywords or are long.</i>"
    ;;

  # Help
  "❓ help"|"help")
    send_msg "🤖 <b>ZeroClaw Agent Help</b>

📱 <b>Superpowers:</b>
• 🌐 Web Research - AI-powered research
• 💸 Log Expense - Natural language expenses
• 🔗 Save Link - Archive with summary
• 🎛️ Master Control - Manage bots
• 🌐 Reset Tunnel - Fix ngrok
• 🧠 Memory - View vault

💡 Type 'menu' anytime for buttons!"
    ;;

  # Close/Hide
  "🗑️ close"|"close menu"|"hide")
    REMOVE=$(python3 -c "import json; print(json.dumps({'remove_keyboard': True}))")
    send_msg "✅ Menu hidden. Type 'menu' to bring it back!" "$REMOVE"
    ;;

  # Default - check for URL or auto-capture
  *)
    # Check if message contains URL (archive it)
    URL=$(echo "$MESSAGE" | grep -oP 'https?://[^\s<>"{}|\\^`\[\]]+' | head -1)
    if [ -n "$URL" ]; then
      TITLE=$(curl -s "$URL" -A "Mozilla/5.0" 2>/dev/null | grep -oP '(?<=<title>)([^<]+)' | head -1 | cut -c1-60)
      TITLE=${TITLE:-"Link"}
      python3 "$HOME/.zeroclaw/memory_system.py" capture "🔗 $TITLE

📎 $URL" > /dev/null 2>&1
      send_msg "🔗 <b>Auto-archived link!</b>

📄 ${TITLE}...
📎 $URL

💾 Saved to Memory Vault"
    else
      # Auto-capture long messages
      WORDS=$(echo "$MESSAGE" | wc -w)
      if [ $WORDS -gt 15 ] || echo "$MSG_LOWER" | grep -qE "(remember|important|idea|decided|plan|todo)"; then
        python3 "$HOME/.zeroclaw/memory_system.py" capture "$MESSAGE" > /dev/null 2>&1
        send_msg "✅ Auto-saved to Memory Vault! ($WORDS words)"
      else
        echo "$MESSAGE"
      fi
    fi
    ;;
esac
