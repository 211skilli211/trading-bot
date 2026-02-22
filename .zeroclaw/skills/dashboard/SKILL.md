---
name: show-dashboard
description: Use this when the user says "📊 Dashboard", "dashboard", "status", "overview", or wants to see their activity summary.
triggers:
  - "📊 Dashboard"
  - dashboard
  - status
  - overview
---

# Show Dashboard

Display the visual ASCII dashboard with today's activity, categories, and recent entries.

## Instructions

1. Generate the dashboard using visual_dashboard.py
2. Display it to the user
3. Include helpful tips at the bottom

## Execute

```bash
#!/bin/bash

# Generate and display dashboard
python3 "$HOME/.zeroclaw/visual_dashboard.py" 2>/dev/null

echo ""
echo "📱 <b>Quick Actions:</b>"
echo "• 💾 Capture Note - Save something new"
echo "• 🔍 Search Memory - Find saved notes"
echo "• 📅 Daily Summary - Today's activity"
echo ""
echo "<i>Tip: Type 'menu' to show the button keyboard anytime!</i>"
```

## Output

Visual ASCII dashboard showing:
- Today's activity (notes count, memory entries)
- Category breakdown with bar chart
- Recent memory entries
- Quick action commands
