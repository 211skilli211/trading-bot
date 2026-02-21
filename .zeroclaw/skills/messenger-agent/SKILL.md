# Messenger Agent Skill

## Purpose
Transforms raw data into beautiful, human-readable Telegram messages with professional formatting, emojis, and markdown styling.

## Features

### Message Types
- 💰 **Price Alerts** - Clean price updates with change indicators
- ⚡ **Trade Notifications** - Execution confirmations with P&L
- 🚨 **Opportunity Alerts** - Arbitrage/opportunity highlights
- 📊 **Performance Reports** - P&L summaries with insights
- 🔍 **Diagnostic Reports** - System status with recommendations
- 📰 **Sentiment Analysis** - Market mood with sources

### Smart Formatting
- Auto-detects bullish/bearish sentiment
- Adds appropriate emojis
- Highlights key metrics
- Provides actionable insights
- Handles MarkdownV2 properly

## Usage

### Direct Usage
```bash
python3 messenger-agent/handler.py price '{"symbol": "BTC", "price": 68500, "change_24h": 2.5}'
```

### From Other Skills
Other skills can pipe data to messenger-agent for formatting:
```python
import subprocess
import json

data = {"symbol": "BTC", "price": 68500, "change_24h": 2.5}
result = subprocess.run(
    ["python3", "messenger-agent/handler.py", "price", json.dumps(data)],
    capture_output=True, text=True
)
formatted_message = result.stdout
```

### Format Types

#### 1. Price Format
Input:
```json
{
  "symbol": "BTC",
  "price": 68516.00,
  "change_24h": 2.37,
  "volume": 36900000000
}
```

Output:
```
💰 *BTC PRICE UPDATE*

💵 Price: `$68,516.00`
📈 24h Change: `+2.37%`
📊 Volume: `$36,900,000,000`

⏰ 14:48 UTC
```

#### 2. Diagnostic Format
Input:
```json
{
  "exchange_status": "✅ All connected",
  "zc_personal": "✅ Running",
  "zc_trading": "✅ Running",
  "disk_status": "45% used",
  "memory_status": "62% used",
  "cpu_status": "Normal"
}
```

Output:
```
🔍 *SYSTEM STATUS* - 14:48 UTC

✅ *ALL SYSTEMS OPERATIONAL*

🌐 Exchanges:
✅ All connected

🤖 ZeroClaw:
• Personal: ✅ Running
• Trading: ✅ Running

💾 Resources:
• Disk: 45% used
• Memory: 62% used
• CPU: Normal

🚀 Ready for trading!
```

#### 3. Performance Format
Input:
```json
{
  "period": "TODAY",
  "total_pnl": 125.50,
  "win_rate": 65.5,
  "wins": 13,
  "losses": 7,
  "best_trade": 45.20,
  "worst_trade": -12.30
}
```

Output:
```
📊 *PERFORMANCE REPORT* - TODAY

📈 PnL: `+$125.50`
🎯 Win Rate: `65.5%`
📈 Trades: 13W / 7L

💎 Best: `+$45.20`
💔 Worst: `-$12.30`

🚀 *Strong performance!* Win rate above 60%
```

## Integration

### With Price Check Skill
The price-check skill can call messenger-agent to format its output:
```python
# In price-check/handler.py
raw_data = fetch_price(symbol)
formatted = call_messenger_agent("price", raw_data)
print(formatted)
```

### With System Diagnostic
```python
# In system-diagnostic/handler.py
raw_status = check_system()
formatted = call_messenger_agent("diagnostic", raw_status)
print(formatted)
```

## Customization

### Adding New Formats
Edit `handler.py` and add to `formatters` dict:
```python
def format_my_custom(data):
    return f"""
🎯 *CUSTOM ALERT*

Data: {data['value']}
"""

formatters = {
    # ... existing formats
    "custom": format_my_custom,
}
```

### Emoji Customization
Edit the `EMOJIS` dict in `handler.py`:
```python
EMOJIS = {
    "up": "🚀",      # Change to rocket
    "down": "💥",    # Change to explosion
    # ... etc
}
```

## Best Practices

1. **Always pass valid JSON** - The handler expects proper JSON input
2. **Use the right format type** - Each format has specific expected fields
3. **Let it handle markdown** - Don't pre-escape special characters
4. **Test in Telegram** - Some characters need escaping for MarkdownV2

## Example: Complete Integration

```python
#!/usr/bin/env python3
"""Example: Price check with messenger formatting"""
import subprocess
import json

def get_price(symbol):
    # Fetch raw data
    raw_data = {
        "symbol": symbol,
        "price": 68516.00,
        "change_24h": 2.37,
        "volume": 36900000000
    }
    
    # Format with messenger
    result = subprocess.run(
        ["python3", "/root/trading-bot/.zeroclaw/skills/messenger-agent/handler.py", 
         "price", json.dumps(raw_data)],
        capture_output=True, text=True
    )
    
    return result.stdout

# Usage
message = get_price("BTC")
print(message)  # Beautiful formatted output!
```
