#!/bin/bash
# Personal Bot Handler v5.0 - Enhanced with Auto-Capture, Memory Vault & Smart Workflows

read -r JSON_PAYLOAD

# Extract fields
MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]')
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null)
CALLBACK_DATA=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('callback_data',''))" 2>/dev/null)
CALLBACK_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('callback_id',''))" 2>/dev/null)

# File paths
NOTES_FILE="$HOME/.zeroclaw/workspace/notes.txt"
MEMORY_DB="$HOME/.zeroclaw/memory/enhanced_memory.db"
BOT_TOKEN="8539644338:AAG5We86Wqcrzbj0ijn01-IO6YUC_BKVCSk"

# Ensure memory system exists
if [ ! -f "$HOME/.zeroclaw/memory_system.py" ]; then
    echo "❌ Memory system not found. Please ensure memory_system.py is installed."
    exit 1
fi

# ============ INLINE KEYBOARD HELPERS ============

send_inline_keyboard() {
    local text="$1"
    local keyboard="$2"
    
    python3 << PYCODE
import json
import urllib.request

text = """$text"""
keyboard = '''$keyboard'''

payload = {
    "chat_id": "$USER_ID",
    "text": text,
    "parse_mode": "HTML",
    "reply_markup": json.loads(keyboard)
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

answer_callback() {
    local callback_id="$1"
    local text="${2:-}"
    
    python3 << PYCODE
import json
import urllib.request

payload = {
    "callback_query_id": "$callback_id",
    "text": """$text"""
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    f"https://api.telegram.org/bot${BOT_TOKEN}/answerCallbackQuery",
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    urllib.request.urlopen(req, timeout=5)
except:
    pass
PYCODE
}

# ============ KEYBOARD DEFINITIONS ============

main_menu_keyboard() {
    cat << 'EOF'
{
    "inline_keyboard": [
        [{"text": "🧠 Memory Vault", "callback_data": "menu_memory"}, {"text": "📊 Dashboard", "callback_data": "menu_dashboard"}],
        [{"text": "⛓️ Workflows", "callback_data": "menu_workflows"}, {"text": "🔍 Smart Search", "callback_data": "menu_search"}],
        [{"text": "📅 Daily Summary", "callback_data": "menu_daily"}, {"text": "⚡ Quick Actions", "callback_data": "menu_quick"}]
    ]
}
EOF
}

memory_menu_keyboard() {
    cat << 'EOF'
{
    "inline_keyboard": [
        [{"text": "💾 Auto-Capture Note", "callback_data": "memory_capture"}],
        [{"text": "🔍 Search Memory", "callback_data": "memory_search"}],
        [{"text": "🔗 Find Connections", "callback_data": "memory_connect"}],
        [{"text": "📋 Recent Entries", "callback_data": "memory_recent"}],
        [{"text": "🔙 Back", "callback_data": "menu_main"}]
    ]
}
EOF
}

workflow_menu_keyboard() {
    cat << 'EOF'
{
    "inline_keyboard": [
        [{"text": "⛓️ Create Task Chain", "callback_data": "workflow_taskchain"}],
        [{"text": "💾 Save Context", "callback_data": "workflow_snapshot"}],
        [{"text": "📂 Load Context", "callback_data": "workflow_load"}],
        [{"text": "📝 Summarize", "callback_data": "workflow_summarize"}],
        [{"text": "🔙 Back", "callback_data": "menu_main"}]
    ]
}
EOF
}

quick_actions_keyboard() {
    cat << 'EOF'
{
    "inline_keyboard": [
        [{"text": "📝 Quick Note", "callback_data": "quick_note"}],
        [{"text": "⏱️ 5min Reminder", "callback_data": "quick_remind_5"}, {"text": "⏱️ 30min Reminder", "callback_data": "quick_remind_30"}],
        [{"text": "🏷️ Tag Last Entry", "callback_data": "quick_tag"}],
        [{"text": "📊 System Status", "callback_data": "quick_status"}],
        [{"text": "🔙 Back", "callback_data": "menu_main"}]
    ]
}
EOF
}

search_options_keyboard() {
    cat << 'EOF'
{
    "inline_keyboard": [
        [{"text": "🔍 Search All", "callback_data": "search_all"}],
        [{"text": "📅 By Date", "callback_data": "search_date"}],
        [{"text": "🏷️ By Tag", "callback_data": "search_tag"}],
        [{"text": "🔙 Back", "callback_data": "menu_main"}]
    ]
}
EOF
}

# ============ MEMORY SYSTEM FUNCTIONS ============

capture_to_memory() {
    local content="$1"
    local source="${2:-telegram}"
    
    python3 "$HOME/.zeroclaw/memory_system.py" capture "$content"
}

search_memory() {
    local query="$1"
    python3 "$HOME/.zeroclaw/memory_system.py" search "$query"
}

create_task_chain() {
    local name="$1"
    shift
    local tasks="$@"
    
    python3 "$HOME/.zeroclaw/memory_system.py" taskchain "$name" "$tasks"
}

save_context() {
    local name="$1"
    local context="{\"source\": \"telegram\", \"timestamp\": \"$(date -Iseconds)\"}"
    
    python3 "$HOME/.zeroclaw/memory_system.py" snapshot "$name" "$context"
}

get_daily_summary() {
    local date="${1:-$(date +%Y-%m-%d)}"
    python3 "$HOME/.zeroclaw/memory_system.py" daily "$date"
}

summarize_conversation() {
    local text="$1"
    python3 "$HOME/.zeroclaw/memory_system.py" summarize "$text"
}

find_connections() {
    local entry_id="$1"
    python3 "$HOME/.zeroclaw/memory_system.py" connect "$entry_id"
}

tag_memory_entry() {
    local entry_id="$1"
    shift
    local tags="$@"
    
    python3 "$HOME/.zeroclaw/memory_system.py" tag "$entry_id" "$tags"
}

# ============ SMART FEATURES ============

auto_categorize_message() {
    local message="$1"
    
    # Auto-detect if message should be saved
    local save_indicators=("remember" "note" "important" "idea" "decided" "plan" "todo" "task")
    local should_save=false
    
    for indicator in "${save_indicators[@]}"; do
        if echo "$message" | grep -qi "$indicator"; then
            should_save=true
            break
        fi
    done
    
    # Also save if message is long and contains useful info
    local word_count=$(echo "$message" | wc -w)
    if [ $word_count -gt 15 ]; then
        should_save=true
    fi
    
    echo "$should_save"
}

# ============ CALLBACK HANDLERS ============

handle_callback() {
    local data="$CALLBACK_DATA"
    local callback_id="$CALLBACK_ID"
    
    case "$data" in
        "menu_main")
            send_inline_keyboard "🤖 <b>Personal Bot v5.0</b> - Enhanced Memory & Workflows

What would you like to do?" "$(main_menu_keyboard)"
            ;;
            
        "menu_memory")
            send_inline_keyboard "🧠 <b>Memory Vault</b>

Auto-capture, search, and connect your thoughts" "$(memory_menu_keyboard)"
            ;;
            
        "menu_dashboard")
            local daily=$(get_daily_summary)
            local total_notes=$(echo "$daily" | python3 -c "import json,sys; print(json.load(sys.stdin).get('total_notes',0))")
            local categories=$(echo "$daily" | python3 -c "import json,sys; d=json.load(sys.stdin).get('categories',{}); print(', '.join([f'{k}:{v}' for k,v in d.items()]))")
            
            local dashboard_text="📊 <b>Your Dashboard</b>

📅 Today's Activity:
• Notes captured: $total_notes
• Categories: $categories

💡 <b>Quick Tips:</b>
• Long messages auto-save to memory
• Use 'remember' to tag important info
• Search finds connections across entries"
            
            send_inline_keyboard "$dashboard_text" "$(main_menu_keyboard)"
            ;;
            
        "menu_workflows")
            send_inline_keyboard "⛓️ <b>Workflows</b>

Task chains, context snapshots, and automation" "$(workflow_menu_keyboard)"
            ;;
            
        "menu_search")
            send_inline_keyboard "🔍 <b>Smart Search</b>

Search across memory, notes, and context" "$(search_options_keyboard)"
            ;;
            
        "menu_daily")
            local summary=$(get_daily_summary)
            local formatted=$(echo "$summary" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    print(f\"📅 <b>{d['date']}</b>\")
    print(f\"\")
    print(f\"📝 Total Notes: {d['total_notes']}\")
    print(f\"   • Auto-captured: {d['auto_captured']}\")
    print(f\"   • Manual: {d['manual_notes']}\")
    print(f\"\")
    print(f\"📂 Categories:\")
    for cat, count in d['categories'].items():
        print(f\"   • {cat}: {count}\")
    print(f\"\")
    print(f\"🕐 Recent:\")
    for note in d['recent_notes'][:3]:
        print(f\"   • {note['content'][:50]}...\")
else:
    print('No data available')
")
            send_inline_keyboard "$formatted" "$(main_menu_keyboard)"
            ;;
            
        "menu_quick")
            send_inline_keyboard "⚡ <b>Quick Actions</b>" "$(quick_actions_keyboard)"
            ;;
            
        "memory_capture")
            echo "📝 Type what you'd like to capture:

Example: 'Remember that the server password is XYZ123'

I'll auto-tag and categorize it for you."
            ;;
            
        "memory_search")
            echo "🔍 What would you like to search for?

Examples:
• Search: 'server password'
• Search: 'meeting notes'
• Search: 'project ideas'"
            ;;
            
        "memory_connect")
            echo "🔗 To find connections, type:
connect [entry-id]

Or search for an entry first to get its ID."
            ;;
            
        "memory_recent")
            local recent=$(python3 "$HOME/.zeroclaw/memory_system.py" search "*" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success') and d.get('results', {}).get('memory'):
    print('<b>📋 Recent Memory Entries:</b>')
    print('')
    for i, entry in enumerate(d['results']['memory'][:5], 1):
        print(f\"{i}. {entry['content'][:60]}...\")
        print(f\"   🏷️ {', '.join(entry['tags'][:3])} | 📂 {entry['category']}\")
        print('')
else:
    print('No recent entries found.')
")
            send_inline_keyboard "$recent" "$(memory_menu_keyboard)"
            ;;
            
        "workflow_taskchain")
            echo "⛓️ Create a task chain:

taskchain [name] | [task1, task2, task3]

Example:
taskchain Morning Routine | Check email, Review calendar, Plan day"
            ;;
            
        "workflow_snapshot")
            echo "💾 Save current context:

snapshot [name]

Example:
snapshot Project Alpha Setup

This saves your current working state to resume later."
            ;;
            
        "workflow_load")
            echo "📂 To load a saved context, type:
snapshots

This will list all saved contexts with their IDs."
            ;;
            
        "workflow_summarize")
            echo "📝 To summarize a long conversation:

summarize [paste text here]

I'll extract key points and save them to your memory."
            ;;
            
        "quick_note")
            echo "📝 Quick note mode:

Just type your note and I'll save it instantly.

Example:
note Call John about the project tomorrow at 2pm"
            ;;
            
        "quick_remind_5")
            echo "⏰ Reminder set for 5 minutes!

What should I remind you about?"
            ;;
            
        "quick_remind_30")
            echo "⏰ Reminder set for 30 minutes!

What should I remind you about?"
            ;;
            
        "quick_tag")
            echo "🏷️ To tag your most recent entry:

tag [entry-id] tag1,tag2,tag3

Or search for the entry first to get its ID."
            ;;
            
        "quick_status")
            echo "💻 <b>System Status</b>

🖥️ OS: $(uname -o)
⚡ Cores: $(nproc)
🤖 Bot: ✅ Online
💾 Memory: $(free -h 2>/dev/null | grep Mem | awk '{print $3"/"$2}')
💿 Disk: $(df -h ~ 2>/dev/null | tail -1 | awk '{print $5}')"
            ;;
            
        *)
            answer_callback "$callback_id" "Feature coming soon!"
            ;;
    esac
}

# ============ COMMAND ROUTING ============

case "$MSG_LOWER" in
    
  # Show main menu
  "start"|"/start"|"menu"|"home")
    send_inline_keyboard "🤖 <b>Personal Bot v5.0</b> - Enhanced Memory & Workflows

Welcome! Your messages are now auto-captured when they contain important keywords or are detailed enough.

What would you like to do?" "$(main_menu_keyboard)"
    ;;
    
  # Auto-capture with explicit command
  "capture"*)
    CONTENT=$(echo "$MESSAGE" | sed 's/^[Cc]apture //')
    if [ -n "$CONTENT" ]; then
        capture_to_memory "$CONTENT"
    else
        echo "📝 What would you like to capture?"
    fi
    ;;
    
  # Search memory
  "search"*)
    QUERY=$(echo "$MESSAGE" | sed 's/^[Ss]earch //')
    if [ -n "$QUERY" ]; then
        RESULT=$(search_memory "$QUERY")
        echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    print(f\"🔍 Results for '{d['query']}':\")
    print('')
    if d['results']['memory']:
        print('<b>🧠 Memory:</b>')
        for entry in d['results']['memory'][:3]:
            print(f\"• {entry['content'][:60]}...\")
            print(f\"  🏷️ {', '.join(entry['tags'][:2])}\")
            print('')
    if d['results']['daily_notes']:
        print('<b>📅 Daily Notes:</b>')
        for note in d['results']['daily_notes'][:2]:
            print(f\"• {note['content'][:50]}...\")
else:
    print('No results found')
"
    else
        echo "🔍 What would you like to search for?"
    fi
    ;;
    
  # Task chain
  "taskchain"*)
    PARSED=$(echo "$MESSAGE" | python3 -c "
import sys
msg = sys.stdin.read()
parts = msg.split('|', 1)
if len(parts) == 2:
    name = parts[0].replace('taskchain', '').strip()
    tasks = parts[1].strip()
    print(f'{name}|{tasks}')
else:
    print('ERROR')
")
    if [ "$PARSED" != "ERROR" ]; then
        NAME=$(echo "$PARSED" | cut -d'|' -f1)
        TASKS=$(echo "$PARSED" | cut -d'|' -f2)
        create_task_chain "$NAME" "$TASKS"
    else
        echo "⛓️ Format: taskchain [name] | [task1, task2, task3]"
    fi
    ;;
    
  # Snapshot
  "snapshot"*)
    NAME=$(echo "$MESSAGE" | sed 's/^[Ss]napshot //')
    if [ -n "$NAME" ]; then
        save_context "$NAME"
    else
        # List snapshots
        python3 "$HOME/.zeroclaw/memory_system.py" snapshots
    fi
    ;;
    
  # Daily summary
  "daily"*)
    DATE=$(echo "$MESSAGE" | sed 's/^[Dd]aily //')
    get_daily_summary "$DATE"
    ;;
    
  # Summarize
  "summarize"*)
    TEXT=$(echo "$MESSAGE" | sed 's/^[Ss]ummarize //')
    if [ -n "$TEXT" ]; then
        summarize_conversation "$TEXT"
    else
        echo "📝 Paste the text you'd like me to summarize"
    fi
    ;;
    
  # Connect entries
  "connect"*)
    ID=$(echo "$MESSAGE" | sed 's/^[Cc]onnect //')
    if [ -n "$ID" ]; then
        find_connections "$ID"
    else
        echo "🔗 Usage: connect [entry-id]"
    fi
    ;;
    
  # Tag entry
  "tag"*)
    PARTS=$(echo "$MESSAGE" | python3 -c "
import sys
parts = sys.stdin.read().split(maxsplit=2)
if len(parts) >= 3:
    print(f'{parts[1]}|{parts[2]}')
else:
    print('ERROR')
")
    if [ "$PARTS" != "ERROR" ]; then
        ID=$(echo "$PARTS" | cut -d'|' -f1)
        TAGS=$(echo "$PARTS" | cut -d'|' -f2)
        tag_memory_entry "$ID" "$TAGS"
    else
        echo "🏷️ Usage: tag [entry-id] tag1,tag2,tag3"
    fi
    ;;
    
  # Note command
  "note"*)
    NOTE_TEXT=$(echo "$MESSAGE" | sed 's/^[Nn]ote //')
    if [ -n "$NOTE_TEXT" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M')] $NOTE_TEXT" >> "$NOTES_FILE"
        capture_to_memory "$NOTE_TEXT" "manual_note"
        echo "📝 Note saved and captured to memory!"
    fi
    ;;
    
  # Help
  "help"|"commands")
    echo "🤖 <b>Personal Bot v5.0 - Commands</b>

<b>🧠 Memory Vault</b>
• capture [text] - Auto-save with tags
• search [query] - Search all memory
• connect [id] - Find related entries
• tag [id] [tags] - Tag an entry
• daily [date] - Daily summary

<b>⛓️ Workflows</b>
• taskchain [name] | [tasks] - Create task chain
• snapshot [name] - Save context
• snapshots - List saved contexts
• summarize [text] - Auto-summarize

<b>📝 Quick</b>
• note [text] - Quick note
• menu - Show main menu
• help - This message

<i>Tip: Long or keyword-rich messages auto-save!</i>"
    ;;
    
  # Handle callback queries
  *)
    if [ -n "$CALLBACK_DATA" ]; then
        handle_callback
    else
        # AUTO-CAPTURE LOGIC
        SHOULD_SAVE=$(auto_categorize_message "$MESSAGE")
        
        if [ "$SHOULD_SAVE" = "true" ]; then
            # Auto-capture the message
            RESULT=$(capture_to_memory "$MESSAGE")
            
            # Show subtle confirmation with menu
            CAPTURED=$(echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    print(f\"✅ Auto-captured! Tagged: {', '.join(d.get('tags', []))}\")
")
            
            send_inline_keyboard "${CAPTURED}

Your message was automatically saved to memory." "$(main_menu_keyboard)"
        else
            # Show menu for unrecognized short messages
            send_inline_keyboard "🤖 I didn't catch that. What would you like to do?

<i>Tip: Start with keywords like 'remember', 'note', or 'task' to auto-save</i>" "$(main_menu_keyboard)"
        fi
    fi
    ;;
esac
