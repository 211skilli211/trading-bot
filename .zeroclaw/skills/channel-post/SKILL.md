---
name: channel-post
description: Post trading updates, signals, and alerts to Telegram channels. Use when user wants to broadcast or post to a channel.
triggers:
  - post to channel
  - broadcast
  - send to channel
  - channel alert
  - 📢 Post to Channel
---

# Channel Post

Post trading signals, alerts, and updates to Telegram channels.

## Default Channel

**Arbitrage Pro Signals**
- ID: `-1003637413591`
- Type: Private Channel
- Bot Status: Admin ✓

## Instructions

1. Format message for channel (concise, professional)
2. Use the execute script below to post
3. Confirm delivery to user

## Execute

```bash
#!/bin/bash

# Default to Arbitrage Pro Signals
CHANNEL_ID="${1:--1003637413591}"
MESSAGE="${2:-Trading update}"
BOT_TOKEN="8275696907:AAGF4IE-XGNoFSQCSCZ2j47iu2p5Rfs7Cvc"

# Send to channel using Python (more reliable than curl)
python3 << PYCODE
import json, urllib.request, sys

bot_token = "$BOT_TOKEN"
chat_id = "$CHANNEL_ID"
message = """$MESSAGE"""

payload = {
    'chat_id': chat_id,
    'text': message,
    'parse_mode': 'HTML',
    'disable_notification': False
}

data = json.dumps(payload).encode()
req = urllib.request.Request(
    f'https://api.telegram.org/bot{bot_token}/sendMessage',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    response = urllib.request.urlopen(req, timeout=10)
    result = json.loads(response.read().decode())
    if result.get('ok'):
        print(f"✅ <b>Posted to Channel!</b>\n\n📢 Channel: Arbitrage Pro Signals\n📊 Message sent successfully.")
        sys.exit(0)
    else:
        print(f"❌ Error: {result.get('description', 'Unknown error')}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Failed: {str(e)}")
    sys.exit(1)
PYCODE
```

## Usage Examples

User: "post BTC is pumping!"
→ Execute the script with message "BTC is pumping!"

User: "📢 Post to Channel New signal for ETH"
→ Execute with their message

User: "broadcast alert ETH breaking resistance at $3000"
→ Format professionally, then post

## Output

Confirmation of channel post or error message with troubleshooting steps.
