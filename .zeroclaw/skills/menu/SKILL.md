---
name: show-menu
description: Use this when the user says "menu", "start", "show menu", "buttons", or "keyboard".
triggers:
  - menu
  - start
  - show menu
  - buttons
  - keyboard
---

# Show Menu

Send a Telegram Reply Keyboard with quick access to common features.

## Instructions

1. Send a message with a Reply Keyboard to the user's Telegram chat
2. The keyboard should have buttons for: Capture, Search, Dashboard, Daily Summary, Help
3. Use the Telegram Bot API sendMessage endpoint

## Execute

```bash
# Read chat_id from environment or stdin
CHAT_ID="${TELEGRAM_CHAT_ID:-$USER_ID}"

curl -s -X POST "https://api.telegram.org/bot8539644338:AAG5We86Wqcrzbj0ijn01-IO6YUC_BKVCSk/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{
    \"chat_id\": \"$CHAT_ID\",
    \"text\": \"🤖 ZeroClaw Personal Bot\\n\\nChoose an action:\",
    \"parse_mode\": \"HTML\",
    \"reply_markup\": {
      \"keyboard\": [
        [{\"text\": "💾 Capture Note"}, {\"text\": "🔍 Search Memory"}],
        [{\"text\": "📊 Dashboard"}, {\"text\": "📅 Daily Summary"}],
        [{\"text\": "❓ Help"}, {\"text\": "🗑️ Close Menu"}]
      ],
      \"resize_keyboard\": true,
      \"one_time_keyboard\": false
    }
  }"

echo "✅ Menu sent! Use the buttons below or type commands."
```

## Output

Sends a Reply Keyboard with 6 buttons to the user's Telegram chat.
