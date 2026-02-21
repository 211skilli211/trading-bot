#!/bin/bash
# Telegram Responder for ZeroClaw
# Receives message from ZeroClaw and returns formatted response

# Read the message (from argument or stdin)
if [ -n "$1" ]; then
    MESSAGE="$1"
else
    read -r MESSAGE
fi

# Execute and output plain text
exec python3 /root/trading-bot/.zeroclaw/executor.py "$MESSAGE" 2>&1
