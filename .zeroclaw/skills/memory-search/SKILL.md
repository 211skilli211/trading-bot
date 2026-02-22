---
name: memory-search
description: Use this when the user says "🔍 Search Memory", "search", "find", "lookup", or wants to search their saved notes.
triggers:
  - "🔍 Search Memory"
  - search
  - find
  - lookup
---

# Search Memory Vault

Search through all saved memory entries, daily notes, and context.

## Instructions

1. Check if user provided a search query
2. If no query, ask what to search for
3. Execute search using memory system
4. Display results formatted nicely

## Execute

```bash
#!/bin/bash

QUERY="$1"

if [ -z "$QUERY" ]; then
  echo "🔍 <b>Search Memory Vault</b>"
  echo ""
  echo "What would you like to search for?"
  echo ""
  echo "Examples:"
  echo "• 🔍 Search Memory wifi password"
  echo "• search project ideas"
  echo "• find meeting notes"
  exit 0
fi

echo "🔍 <b>Searching for:</b> $QUERY"
echo ""

RESULT=$(python3 "$HOME/.zeroclaw/memory_system.py" search "$QUERY" 2>/dev/null)

echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    mem = d.get('results', {}).get('memory', [])
    notes = d.get('results', {}).get('daily_notes', [])
    total = len(mem) + len(notes)
    
    if total == 0:
        print(\"🤔 No results found.\")
        print(\"Try different keywords or save new notes with 💾 Capture Note\")
    else:
        print(f\"Found {total} results:\")
        print()
        
        if mem:
            print(f\"🧠 Memory ({len(mem)}):\")
            for entry in mem[:3]:
                content = entry['content'][:60] + '...' if len(entry['content']) > 60 else entry['content']
                print(f\"  • {content}\")
                if entry.get('tags'):
                    print(f\"    🏷️ {', '.join(entry['tags'][:2])}\")
            print()
        
        if notes:
            print(f\"📅 Notes ({len(notes)}):\")
            for note in notes[:2]:
                content = note['content'][:50] + '...' if len(note['content']) > 50 else note['content']
                print(f\"  • {content}\")
else:
    print(f\"❌ Search failed. Try again later.\")
"
```

## Output

Search results from memory vault and daily notes.
