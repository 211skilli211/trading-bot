---
name: close-menu
description: Use this when the user says "🗑️ Close Menu", "close menu", "hide keyboard", or wants to remove the reply keyboard.
triggers:
  - "🗑️ Close Menu"
  - close menu
  - hide keyboard
---

# Close Menu

Hide the Reply Keyboard by sending a message with remove_keyboard.

## Execute

```bash
#!/bin/bash

CHAT_ID="${TELEGRAM_CHAT_ID:-$USER_ID}"

curl -s -X POST "https://api.telegram.org/bot8539644338:AAG5We86Wqcrzbj0ijn01-IO6YUC_BKVCSk/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{
    \"chat_id\": \"$CHAT_ID\",
    \"text\": \"✅ Keyboard hidden. Type 'menu' anytime to bring it back!\",
    \"reply_markup\": {
      \"remove_keyboard\": true
    }
  }" > /dev/null 2>&1

echo "✅ Reply keyboard removed."
echo ""
echo "Type 'menu' anytime to show the keyboard again."
```

## Output

Hides the reply keyboard and confirms removal.
