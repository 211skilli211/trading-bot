#!/bin/bash
# Telegram Responder with Professional Output Formatting
# Receives JSON from ZeroClaw and formats output cleanly

read -r JSON_PAYLOAD

# Extract message
MESSAGE=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))")
USER_ID=$(echo "$JSON_PAYLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))")

# Create temp file for response
RESPONSE_FILE=$(mktemp)

# Run the actual handler and capture output
/root/trading-bot/.zeroclaw/telegram_handler_v49_smart.sh <<< "$JSON_PAYLOAD" > "$RESPONSE_FILE" 2>&1

# Read the response
RESPONSE=$(cat "$RESPONSE_FILE")
rm "$RESPONSE_FILE"

# Format the output professionally
# Remove JSON artifacts
CLEAN_RESPONSE=$(echo "$RESPONSE" | sed 's/<tool_call>//g; s/<\/tool_call>//g' | \
    sed 's/{"name":"[^"]*","arguments":{[^}]*}}//g' | \
    sed 's/\\n/\n/g' | \
    sed 's/\\"/"/g')

# Remove empty lines at start/end
CLEAN_RESPONSE=$(echo "$CLEAN_RESPONSE" | sed '/./,$!d' | tac | sed '/./,$!d' | tac)

# Output clean response
echo "$CLEAN_RESPONSE"
