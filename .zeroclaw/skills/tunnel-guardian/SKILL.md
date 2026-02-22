---
name: tunnel-guardian
description: Manage Ngrok tunnels. Use when user says "tunnel", "ngrok", or taps Reset Tunnel button.
triggers:
  - "🌐 Reset Tunnel"
  - tunnel
  - ngrok
  - reset tunnel
---

# Ngrok Tunnel Guardian

Manage ngrok tunnels and auto-update webhooks.

## Execute

```bash
#!/bin/bash
COMMAND="$1"

if [ "$COMMAND" = "reset" ]; then
  echo "🔄 Resetting tunnel..."
  pkill -f ngrok 2>/dev/null
  sleep 2
  nohup ngrok http 3000 > /tmp/ngrok.log 2>&1 &
  sleep 5
  URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'] if d.get('tunnels') else 'Error')")
  
  if [ "$URL" != "Error" ]; then
    curl -s "https://api.telegram.org/bot8539644338:AAG5We86Wqcrzbj0ijn01-IO6YUC_BKVCSk/setWebhook?url=$URL/webhook" > /dev/null
    echo "✅ New tunnel: $URL"
  else
    echo "❌ Failed to create tunnel"
  fi
else
  echo "🌐 Tunnel Guardian

• status - Check tunnel
• reset - New tunnel"
fi
```
