#!/bin/bash
# Personal Bot Handler v6.0 - Text-Based with AI Enhancement (No Callback Dependency)

read -r JSON_PAYLOAD

# Extract fields
MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)

# File paths
NOTES_FILE="$HOME/.zeroclaw/workspace/notes.txt"
MEMORY_DB="$HOME/.zeroclaw/memory/enhanced_memory.db"

echo "$JSON_PAYLOAD" >> ~/.zeroclaw/last_message.json 2>/dev/null

# ============ MEMORY FUNCTIONS ============

capture_to_memory() {
    local content="$1"
    python3 "$HOME/.zeroclaw/memory_system.py" capture "$content" 2>/dev/null
}

search_memory() {
    local query="$1"
    python3 "$HOME/.zeroclaw/memory_system.py" search "$query" 2>/dev/null
}

get_daily_summary() {
    python3 "$HOME/.zeroclaw/memory_system.py" daily 2>/dev/null
}

show_dashboard() {
    python3 "$HOME/.zeroclaw/visual_dashboard.py" 2>/dev/null
}

# ============ COMMAND ROUTING ============

case "$MSG_LOWER" in
    
  # Start/Menu - Show dashboard
  "/start"|"start"|"/menu"|"menu"|"home")
    show_dashboard
    echo ""
    echo "📱 <b>Quick Commands:</b>"
    echo "  /capture [text] - Save to memory"
    echo "  /search [query] - Search memory"
    echo "  /daily - Today's summary"
    echo "  /help - All commands"
    ;;
    
  # Capture command
  "/capture"*)
    CONTENT=$(echo "$MESSAGE" | sed 's/^[Cc]apture //; s/^\/capture //')
    if [ -n "$CONTENT" ]; then
        RESULT=$(capture_to_memory "$CONTENT")
        echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    print(f\"✅ <b>Saved to Memory Vault!</b>\")
    print(f\"\")
    print(f\"📝 {d['message']}\")
    if d.get('tags'):
        print(f\"🏷️  Tags: {', '.join(d['tags'])}\")
else:
    print(f\"❌ Failed to save: {d.get('error', 'Unknown error')}\")
"
    else
        echo "📝 <b>Capture Mode</b>

Type what you'd like to save:
capture Remember that server IP is 192.168.1.100

I'll auto-tag and categorize it for you."
    fi
    ;;
    
  # Search command
  "/search"*)
    QUERY=$(echo "$MESSAGE" | sed 's/^[Ss]earch //; s/^\/search //')
    if [ -n "$QUERY" ]; then
        echo "🔍 <b>Searching for:</b> $QUERY"
        echo ""
        RESULT=$(search_memory "$QUERY")
        echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    mem = d.get('results', {}).get('memory', [])
    notes = d.get('results', {}).get('daily_notes', [])
    
    if mem:
        print(f\"🧠 <b>Memory ({len(mem)} results):</b>\")
        for entry in mem[:3]:
            print(f\"  • {entry['content'][:60]}...\")
            if entry.get('tags'):
                print(f\"    🏷️ {', '.join(entry['tags'][:3])}\")
        print()
    
    if notes:
        print(f\"📅 <b>Notes ({len(notes)} results):</b>\")
        for note in notes[:2]:
            print(f\"  • {note['content'][:50]}...\")
        print()
    
    if not mem and not notes:
        print(\"🤔 No results found.\")
        print(\"Try different keywords or capture new notes.\")
else:
    print(f\"❌ Search failed: {d.get('error', 'Unknown')}\")
"
    else
        echo "🔍 <b>Search Mode</b>

What would you like to search for?
search server password
search project ideas
search meeting notes"
    fi
    ;;
    
  # Daily summary
  "/daily"*)
    echo "📊 <b>Generating Daily Summary...</b>"
    echo ""
    RESULT=$(get_daily_summary)
    echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    print(f\"📅 <b>{d['date']} Summary</b>\")
    print(f\"\")
    print(f\"📝 Total Notes: {d['total_notes']}\")
    print(f\"   • Auto-captured: {d['auto_captured']}\")
    print(f\"   • Manual: {d['manual_notes']}\")
    print(f\"\")
    if d.get('categories'):
        print(f\"📂 Categories:\")
        for cat, count in d['categories'].items():
            print(f\"   • {cat}: {count}\")
    print(f\"\")
    if d.get('recent_notes'):
        print(f\"🕐 Recent Notes:\")
        for note in d['recent_notes'][:3]:
            print(f\"   • {note['content'][:50]}...\")
else:
    print(f\"📅 No data for today yet.\")
    print(f\"Start capturing notes with: capture [text]\")
"
    ;;
    
  # Note command (legacy)
  "note "*)
    NOTE_TEXT=$(echo "$MESSAGE" | sed 's/^[Nn]ote //')
    if [ -n "$NOTE_TEXT" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M')] $NOTE_TEXT" >> "$NOTES_FILE"
        capture_to_memory "$NOTE_TEXT" "manual_note" > /dev/null 2>&1
        echo "📝 Note saved to memory vault!"
    fi
    ;;
    
  # Remember command
  "remember"*)
    CONTENT=$(echo "$MESSAGE" | sed 's/^[Rr]emember //; s/^[Rr]emember that //')
    if [ -n "$CONTENT" ]; then
        RESULT=$(capture_to_memory "$CONTENT")
        echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    print(f\"🧠 <b>Remembered!</b>\")
    print(f\"\")
    print(f\"💾 Saved to category: {d.get('category', 'general')}\")
    if d.get('tags'):
        print(f\"🏷️  Auto-tagged: {', '.join(d['tags'])}\")
    print(f\"\")
    print(f\"Use 'search {d.get('tags', [''])[0] if d.get('tags') else 'keyword'}' to find it later.\")
"
    fi
    ;;
    
  # Help command
  "/help"|"help"|"commands")
    echo "🤖 <b>Personal Bot v6.0 - Commands</b>

<b>🧠 Memory Vault</b>
  /capture [text]    - Save with auto-tagging
  remember [text]    - Quick remember
  search [query]     - Search all memory
  /daily             - Today's summary

<b>📝 Notes</b>
  note [text]        - Quick note (legacy)

<b>📊 Dashboard</b>
  /start, /menu      - Show dashboard
  /help              - This message

<b>💡 Auto-Capture</b>
Messages with these keywords auto-save:
• remember, important, idea, decided
• plan, todo, task, meeting
• Long messages (>15 words)

<b>Example:</b>
capture My wifi password is XYZ123
search wifi
remember I need to call mom tomorrow"
    ;;
    
  # Auto-capture logic for unmatched messages
  *)
    # Check if should auto-save
    SHOULD_SAVE=$(echo "$MESSAGE" | python3 -c "
msg = input().lower()
keywords = ['remember', 'important', 'idea', 'decided', 'plan', 'todo', 'task', 'meeting', 'thinking', 'suggestion']
word_count = len(msg.split())
has_keyword = any(kw in msg for kw in keywords)
print('true' if (has_keyword or word_count > 15) else 'false')
")
    
    if [ "$SHOULD_SAVE" = "true" ] && [ ${#MESSAGE} -gt 10 ]; then
        # Auto-capture
        RESULT=$(capture_to_memory "$MESSAGE")
        SAVED=$(echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    print(f\"✅ Auto-saved!\")
else:
    print('')
")
        
        if [ -n "$SAVED" ]; then
            echo "$SAVED"
            echo ""
            echo "<i>Tip: Use /search to find this later, or /daily to see all notes.</i>"
        else
            echo "🤖 I didn't understand. Type /help for commands or /menu for dashboard."
        fi
    else
        # Short message - show help
        echo "🤖 Type /help for commands or /menu for dashboard."
        echo ""
        echo "<i>Tip: Start messages with 'remember', 'important', or 'idea' to auto-save!</i>"
    fi
    ;;
esac
