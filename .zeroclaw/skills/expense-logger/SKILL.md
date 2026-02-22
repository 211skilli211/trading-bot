---
name: expense-logger
description: Log expenses with natural language parsing. Use when user says "expense", "spent", "cost", or taps the Log Expense button.
triggers:
  - "💸 Log Expense"
  - log expense
  - expense
  - spent
  - paid
---

# Quick Expense Logger

Parse natural language expenses and log to CSV with AI categorization.

## Instructions

1. Get expense description from user
2. Use AI to extract amount and category
3. Append to expenses.csv
4. Confirm the logged entry

## Execute

```bash
#!/bin/bash
EXPENSE_TEXT="$1"
EXPENSE_FILE="$HOME/.zeroclaw/workspace/expenses.csv"

if [ -z "$EXPENSE_TEXT" ]; then
  echo "💸 <b>Quick Expense Logger</b>

What did you spend?

Examples:
• 25 lunch with client
• Gas was 45 dollars
• Bought coffee for 5
• Monthly subscription 15

Just type naturally - I'll figure out the amount and category!"
  exit 0
fi

# Create file with headers if doesn't exist
if [ ! -f "$EXPENSE_FILE" ]; then
  echo "date,description,amount,category" > "$EXPENSE_FILE"
fi

# Parse with AI
PARSED=$(python3 << PYCODE
import json
import urllib.request
import os
import re

text = """$EXPENSE_TEXT"""

# Try regex first
amount = None
category = "Other"

# Find amount
amount_patterns = [
    r'\$(\d+(?:\.\d{2})?)',
    r'(\d+(?:\.\d{2})?)\s*(?:dollars?|usd)',
    r'spent\s+(\d+)',
    r'cost\s+(\d+)',
    r'(\d+)\s*(?:for|on)'
]

for pattern in amount_patterns:
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        amount = float(match.group(1))
        break

# Categorize
categories = {
    'food': ['lunch', 'dinner', 'breakfast', 'coffee', 'restaurant', 'meal', 'groceries', 'food'],
    'transport': ['gas', 'uber', 'taxi', 'bus', 'train', 'fuel', 'transport'],
    'entertainment': ['movie', 'game', 'netflix', 'spotify', 'subscription', 'fun'],
    'shopping': ['bought', 'purchase', 'amazon', 'shopping', 'clothes'],
    'bills': ['bill', 'rent', 'electric', 'water', 'internet', 'phone']
}

text_lower = text.lower()
for cat, keywords in categories.items():
    if any(kw in text_lower for kw in keywords):
        category = cat.capitalize()
        break

# If no amount found, use AI
if amount is None:
    api_key = os.getenv('OPENROUTER_API_KEY', '')
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps({
                "model": "arcee-ai/trinity-large-preview:free",
                "messages": [{"role": "user", "content": f"Extract amount from: '{text}'. Reply ONLY with the number."}],
                "max_tokens": 10
            }).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            amount_text = result['choices'][0]['message']['content']
            amount = float(re.search(r'\d+(?:\.\d{2})?', amount_text).group())
    except:
        amount = 0

print(f"{amount}|{category}|{text}")
PYCODE
)

AMOUNT=$(echo "$PARSED" | cut -d'|' -f1)
CATEGORY=$(echo "$PARSED" | cut -d'|' -f2)
DESC=$(echo "$PARSED" | cut -d'|' -f3)
DATE=$(date '+%Y-%m-%d')

# Append to CSV
echo "$DATE,\"$DESC\",$AMOUNT,$CATEGORY" >> "$EXPENSE_FILE"

# Calculate monthly total
MONTH_TOTAL=$(awk -F',' "BEGIN{sum=0} \$1 ~ /^$(date +%Y-%m)/ {sum+=\$3} END{printf \"%.2f\", sum}" "$EXPENSE_FILE")

echo "💸 <b>Expense Logged!</b>

📝 $DESC
💰 Amount: $$AMOUNT
🏷️ Category: $CATEGORY
📅 Date: $DATE

📊 This month: $$MONTH_TOTAL total

💾 Saved to expenses.csv"
```

## Output

Confirmation with logged expense details and monthly total.
