# 📱 Telegram Alerts Setup Guide

## Quick Setup (2 minutes)

### Step 1: Create Telegram Bot
1. Open Telegram app
2. Search for **@BotFather**
3. Start chat and type: `/newbot`
4. Follow prompts:
   - Name your bot (e.g., "MyTradingBot")
   - Choose username (e.g., "mytrade_bot") - must end in 'bot'
5. Copy the **API token** (looks like: `123456789:ABCdefGHIjklMNOpqrSTUvwxyz`)

### Step 2: Get Your Chat ID
1. Search for **@userinfobot**
2. Start chat - it will reply with your ID
3. Copy the number (looks like: `123456789`)

### Step 3: Configure the Bot
```bash
proot-distro login ubuntu
cd ~/trading-bot
source ~/botenv/bin/activate
python setup_telegram.py
```

Enter when prompted:
- Bot Token: `123456789:ABCdefGHIjklMNOpqrSTUvwxyz`
- Chat ID: `123456789`

### Step 4: Test
The setup will send a test message. Check Telegram!

---

## What You'll Get

✅ **Instant alerts for:**
- Trade executions (buy/sell)
- P&L updates
- Error conditions
- Daily summaries

✅ **Message format:**
```
🟢 Trade Executed

Type: BUY
Exchange: Binance
Symbol: BTCUSDT
Amount: 0.001
Price: $68,234.50
P&L: +$12.34

⏰ 2026-02-17 14:32:15
```

---

## Troubleshooting

**"Chat not found" error:**
- Make sure you messaged @userinfobot first
- Try @RawDataBot as alternative

**"Unauthorized" error:**
- Check bot token is correct
- Ensure you didn't include extra spaces

**No messages received:**
- Check internet connection
- Verify bot is not blocked
- Try sending `/start` to your bot

---

## Alternative: Manual Config

Create file `alerts_config.json`:
```json
{
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": 123456789,
  "bot_name": "211Skilli Bot",
  "enabled": true,
  "alert_on_trade": true,
  "alert_on_error": true,
  "alert_daily_summary": true
}
```

