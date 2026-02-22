---
name: daily-summary
description: Use this when the user says "📅 Daily Summary", "daily", "today", "summary", or wants to see today's activity.
triggers:
  - "📅 Daily Summary"
  - daily
  - today
  - summary
---

# Daily Summary

Show today's captured notes, memory entries, and activity statistics.

## Instructions

1. Get today's summary from memory system
2. Display formatted results
3. Show category breakdown

## Execute

```bash
#!/bin/bash

RESULT=$(python3 "$HOME/.zeroclaw/memory_system.py" daily 2>/dev/null)

echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('success'):
    print(f\"📅 <b>{d['date']} Summary</b>\")
    print(f\"\")
    print(f\"📝 Total Notes: {d['total_notes']}\")
    print(f\"   • Auto-captured: {d['auto_captured']}\")
    print(f\"   • Manual: {d['manual_notes']}\")
    
    if d.get('categories'):
        print(f\"\")
        print(f\"📂 Categories:\")
        for cat, count in d['categories'].items():
            print(f\"   • {cat}: {count}\")
    
    if d.get('recent_notes'):
        print(f\"\")
        print(f\"🕐 Recent Notes:\")
        for note in d['recent_notes'][:3]:
            content = note['content'][:50] + '...' if len(note['content']) > 50 else note['content']
            print(f\"   • {content}\")
else:
    print(f\"📅 No data for today yet.\")
    print(f\"\")
    print(f\"Start capturing notes with:\")
    print(f\"• 💾 Capture Note [your text]\")
    print(f\"• remember [something important]\")
"
```

## Output

Daily activity report with notes count, categories, and recent entries.
