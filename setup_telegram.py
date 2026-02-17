#!/usr/bin/env python3
"""
Telegram Bot Setup for 211Skilli Trading Bot
Creates alerts configuration and sends test message
"""

import json
import os
import sys

def setup_telegram():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              📱 TELEGRAM ALERTS CONFIGURATION                     ║
╠══════════════════════════════════════════════════════════════════╣

To receive trade alerts on your phone, you need:

1. BOT TOKEN: Create a bot with @BotFather on Telegram
   • Message @BotFather → /newbot → follow instructions
   • Copy the API token (looks like: 123456789:ABCdefGHIjklMNOpqrSTUvwxyz)

2. CHAT ID: Get your Telegram user ID
   • Message @userinfobot → it will reply with your ID
   • Or message @RawDataBot and look for "chat": {"id": 123456789}

╚══════════════════════════════════════════════════════════════════╝
""")
    
    # Check if already configured
    if os.path.exists("alerts_config.json"):
        print("⚠️  alerts_config.json already exists!")
        with open("alerts_config.json") as f:
            config = json.load(f)
        print(f"   Current bot: {config.get('bot_name', 'Unknown')}")
        overwrite = input("\nOverwrite? (y/N): ").lower()
        if overwrite != 'y':
            print("Keeping existing config.")
            return
    
    # Get bot token
    print("\n🤖 Step 1: Enter your Telegram Bot Token")
    print("   (from @BotFather, format: 123456789:ABCdef...)")
    bot_token = input("Bot Token: ").strip()
    
    if not bot_token or ':' not in bot_token:
        print("❌ Invalid bot token format!")
        sys.exit(1)
    
    # Get chat ID
    print("\n👤 Step 2: Enter your Chat ID")
    print("   (from @userinfobot, format: 123456789)")
    chat_id = input("Chat ID: ").strip()
    
    if not chat_id.isdigit():
        print("❌ Chat ID should be numbers only!")
        sys.exit(1)
    
    # Get optional bot name
    print("\n📝 Step 3: Bot Name (optional)")
    bot_name = input("Bot name (default: 211Skilli Bot): ").strip() or "211Skilli Bot"
    
    # Save config
    config = {
        "bot_token": bot_token,
        "chat_id": int(chat_id),
        "bot_name": bot_name,
        "enabled": True,
        "alert_on_trade": True,
        "alert_on_error": True,
        "alert_daily_summary": True,
        "min_pnl_alert": 0.5,  # Only alert if P&L >= $0.50
        "created_at": "2026-02-17"
    }
    
    with open("alerts_config.json", "w") as f:
        json.dump(config, f, indent=2)
    os.chmod("alerts_config.json", 0o600)
    
    print(f"""
✅ Configuration saved to alerts_config.json

📋 CONFIGURATION:
─────────────────────────────────────────────────────────────────
Bot Token: {bot_token[:15]}...{bot_token[-5:]}
Chat ID: {chat_id}
Bot Name: {bot_name}
─────────────────────────────────────────────────────────────────

🧪 Testing connection...
""")
    
    # Test the connection
    try:
        import requests
        
        test_message = f"""
🚀 <b>{bot_name} - Test Alert</b>

✅ Your trading bot alerts are now configured!

You'll receive notifications for:
• Trade executions (buy/sell)
• P&L updates (if ≥ ${config['min_pnl_alert']})
• Error conditions
• Daily summary reports

Bot started monitoring at: 2026-02-17
        """.strip()
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": test_message,
            "parse_mode": "HTML",
            "disable_notification": False
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Test message sent successfully!")
            print("   Check your Telegram for the test message.")
        else:
            print(f"⚠️  Test failed: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"⚠️  Test failed: {e}")
        print("   Config saved, but test message could not be sent.")
        print("   The bot will retry when it starts trading.")
    
    print("""
─────────────────────────────────────────────────────────────────
📱 NEXT STEPS:
1. Check Telegram for test message
2. Pin the bot chat for easy access
3. Enable notifications for the bot
4. Start trading: ./start-bot.sh
─────────────────────────────────────────────────────────────────
""")

if __name__ == "__main__":
    setup_telegram()
