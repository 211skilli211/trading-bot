#!/bin/bash
# Output Formatter - Makes skill/tool output professional and readable
# Usage: command | /root/trading-bot/.zeroclaw/format-output.sh

# Read stdin
INPUT=$(cat)

# Remove JSON/tool call artifacts
CLEAN=$(echo "$INPUT" | sed 's/<tool_call>//g; s/<\/tool_call>//g' | \
        sed 's/{"name":"[^"]*","arguments":{[^}]*}}//g' | \
        sed 's/\\n/\n/g' | \
        sed 's/\\"/"/g')

# Remove empty lines at start/end
CLEAN=$(echo "$CLEAN" | sed '/./,$!d' | tac | sed '/./,$!d' | tac)

# If output is empty after cleaning, show nothing
[ -z "$CLEAN" ] && exit 0

# Check if already formatted (has emojis/boxes)
if echo "$CLEAN" | grep -q "^[┏━┗📊🏥]"; then
    # Already formatted, just output
    echo "$CLEAN"
else
    # Add professional formatting
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "$CLEAN" | head -25
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
