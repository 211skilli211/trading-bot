#!/bin/bash
# Direct Telegram message handler - routes to skills, no AI

# Log the call for debugging
echo "$(date): HANDLER CALLED with args: $*" >> /tmp/handler_debug.log

# Read the message from stdin
MESSAGE=$(cat)
echo "$(date): MESSAGE RECEIVED: $MESSAGE" >> /tmp/handler_debug.log

# Execute skill directly
RESULT=$(python3 /root/trading-bot/.zeroclaw/executor.py "$MESSAGE" 2>&1)
EXITCODE=$?

echo "$(date): RESULT: ${RESULT:0:100}... EXIT: $EXITCODE" >> /tmp/handler_debug.log

# Output the result
echo "$RESULT"
