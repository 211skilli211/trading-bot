---
name: memory-capture
description: Use this when the user says "💾 Capture Note", "capture", "save note", "remember", or wants to save something to memory.
triggers:
  - "💾 Capture Note"
  - capture
  - save note
  - remember
---

# Capture Note to Memory

Save a note to the Memory Vault with automatic tagging and categorization.

## Instructions

1. Check if the user provided content after "capture" or "remember"
2. If no content, ask what they want to save
3. If content provided, save it using the memory system
4. Confirm the save with category and tags

## Execute

```bash
#!/bin/bash

# Extract content after trigger
CONTENT="$1"

if [ -z "$CONTENT" ]; then
  echo "📝 What would you like to capture?"
  echo ""
  echo "Examples:"
  echo "• 💾 Capture Note My wifi password is XYZ123"
  echo "• remember Server IP is 192.168.1.100"
  exit 0
fi

# Save to memory
RESULT=$(python3 "$HOME/.zeroclaw/memory_system.py" capture "$CONTENT" 2>/dev/null)

# Parse result
echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    print(f\"✅ <b>Saved to Memory Vault!</b>\")
    print(f\"\")
    print(f\"💾 {d['message']}\")
    if d.get('tags'):
        print(f\"🏷️  Auto-tags: {', '.join(d['tags'])}\")
    print(f\"\")
    print(f\"Use 🔍 Search Memory to find it later.\")
else:
    print(f\"❌ Failed: {d.get('error', 'Unknown error')}\")
"
```

## Output

Confirmation message with saved content, category, and auto-generated tags.
