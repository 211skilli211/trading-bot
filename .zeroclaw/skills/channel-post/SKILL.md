---
name: channel-post
description: Post trading updates, signals, and alerts to Telegram channels. Use when user wants to broadcast or post to a channel.
triggers:
  - post to channel
  - broadcast
  - send to channel
  - channel alert
---

# Channel Post

Post trading signals, alerts, and updates to Telegram channels.

## Instructions

1. Get channel ID from user or use default
2. Format message for channel (more concise, no buttons)
3. Send via Telegram Bot API
4. Confirm delivery

## Execute

```bash
#!/bin/bash

CHANNEL_ID="${1:-@your_trading_channel}"
MESSAGE="${2:-Trading update}"
BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"

# Format message for channel (no markdown issues)
FORMATTED=$(echo "$MESSAGE" | sed 's/"/\\"/g')

# Send to channel
curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{
    \"chat_id\": \"$CHANNEL_ID\",
    \"text\": \"$FORMATTED\",
    \"parse_mode\": \"HTML\",
    \"disable_notification\": false
  }" > /dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "✅ <b>Posted to Channel!</b>

📢 Channel: $CHANNEL_ID
📊 Message sent successfully."
else
  echo "❌ Failed to post. Check:
• Bot is admin in channel
• Channel ID is correct
• Bot has post permissions"
fi
```

## Output

Confirmation of channel post or error message.
