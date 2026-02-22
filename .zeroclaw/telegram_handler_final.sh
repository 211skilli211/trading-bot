#!/bin/bash
# Personal Bot Handler - Final Version with Reply Keyboard Support
# This handler passes messages to ZeroClaw AI which matches them to SKILL.md files

read -r JSON_PAYLOAD

# Extract fields
MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

# Export for use by skills
export USER_ID="$USER_ID"
export TELEGRAM_CHAT_ID="$USER_ID"

# File paths
NOTES_FILE="$HOME/.zeroclaw/workspace/notes.txt"

echo "$JSON_PAYLOAD" >> ~/.zeroclaw/last_message.json 2>/dev/null

# ============ SKILL-BASED COMMAND ROUTING ============
# ZeroClaw AI will match these to SKILL.md files

case "$MSG_LOWER" in
    
  # Menu/Start - triggers show-menu skill
  "/start"|"start"|"menu"|"show menu"|"buttons"|"keyboard")
    echo "🤖 Opening menu..."
    # The AI will match this to show-menu skill
    ;;
    
  # Capture - triggers memory-capture skill
  "💾 capture note"*)
    # Strip the button text and pass content to AI
    CONTENT=$(echo "$MESSAGE" | sed 's/^💾 Capture Note //')
    if [ -n "$CONTENT" ]; then
      echo "$CONTENT"
    fi
    ;;
    
  # Search - triggers memory-search skill
  "🔍 search memory"*)
    QUERY=$(echo "$MESSAGE" | sed 's/^🔍 Search Memory //')
    if [ -n "$QUERY" ]; then
      echo "$QUERY"
    fi
    ;;
    
  # Dashboard - triggers show-dashboard skill
  "📊 dashboard")
    echo "Showing dashboard..."
    ;;
    
  # Daily Summary - triggers daily-summary skill
  "📅 daily summary")
    echo "Generating daily summary..."
    ;;
    
  # Help - triggers show-help skill
  "❓ help"|"help")
    echo "Showing help..."
    ;;
    
  # Close Menu - triggers close-menu skill
  "🗑️ close menu"|"close menu")
    echo "Closing menu..."
    ;;
    
  # Remember command (legacy)
  "remember"*)
    # Pass to AI for memory-capture
    ;;
    
  # Capture command (legacy)
  "capture"*)
    # Pass to AI for memory-capture
    ;;
    
  # Search command (legacy)
  "search"*)
    # Pass to AI for memory-search
    ;;
    
  # Daily command (legacy)
  "daily")
    # Pass to AI for daily-summary
    ;;
    
  # Dashboard command (legacy)
  "dashboard"|"status")
    # Pass to AI for show-dashboard
    ;;
    
  # Auto-capture logic
  *)
    # Check if should auto-save (long or keyword-rich)
    WORD_COUNT=$(echo "$MESSAGE" | wc -w)
    
    if [ $WORD_COUNT -gt 15 ]; then
      # Long message - auto capture
      python3 "$HOME/.zeroclaw/memory_system.py" capture "$MESSAGE" > /dev/null 2>&1
      echo "✅ Auto-saved to Memory Vault (${WORD_COUNT} words)"
    else
      # Check for keywords
      if echo "$MSG_LOWER" | grep -qE "(remember|important|idea|decided|plan|todo|task|meeting|note)"; then
        python3 "$HOME/.zeroclaw/memory_system.py" capture "$MESSAGE" > /dev/null 2>&1
        echo "✅ Auto-saved: detected key phrase"
      fi
    fi
    ;;
esac
