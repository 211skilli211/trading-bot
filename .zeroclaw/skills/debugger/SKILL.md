# Debugger Skill

## Purpose
Trace errors, analyze failures, and provide actionable fixes for trading bot issues.

## When to Use
- Error messages in Telegram
- Trades failing silently
- Unexpected behavior
- After crashes
- "Something went wrong"

## Debugging Process

### Step 1: Log Collection
Searches all relevant log files:
- `/root/trading-bot/bot.log` - Main trading log
- `/root/trading-bot/dashboard.log` - Web dashboard
- `/root/trading-bot/alerts.log` - Notification errors
- ZeroClaw logs

### Step 2: Pattern Matching
Looks for:
- Python tracebacks
- API errors (401, 403, 500)
- Connection timeouts
- Database errors
- Configuration issues

### Step 3: Root Cause Analysis
- Identifies the failing component
- Traces the error chain
- Checks configuration validity
- Tests connectivity

### Step 4: Solution Proposal
- Suggests immediate fix
- Provides workaround if needed
- Offers prevention tips
- Can apply fix (if safe)

## Example Scenarios

### Scenario 1: Trade Execution Failed
```
🔍 DEBUG ANALYSIS

Error: "Failed to execute trade: Connection timeout"

Source: execution_layer.py:247
Time: 2026-02-21 14:23:05

Root Cause:
Binance API connection timed out after 30s

Analysis:
- Network connectivity: OK
- API credentials: Valid
- Rate limits: Not exceeded
- Issue: Temporary Binance API lag

Solution:
✅ Automatic retry succeeded on 2nd attempt
- Trade executed at 14:23:35
- Slippage: 0.03% (acceptable)

Prevention:
- Increase timeout to 45s
- Consider fallback exchange
```

### Scenario 2: Telegram Not Responding
```
🔍 DEBUG ANALYSIS

Error: "Telegram sendMessage failed: 401 Unauthorized"

Source: telegram_alerts.py:89

Root Cause:
Bot token invalid or revoked

Solution:
1. Check @BotFather for token status
2. Regenerate if needed
3. Update /root/trading-bot/.env
4. Restart bot

⚠️  Requires manual intervention
```

## Safe Fixes (Auto-Applied)
- Restart stalled processes
- Clear temporary cache
- Reconnect to APIs
- Reset rate limiters

## Manual Fixes (Require Approval)
- Edit configuration files
- Change API credentials
- Modify strategy parameters
- Database migrations