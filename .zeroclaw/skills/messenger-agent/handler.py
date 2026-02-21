#!/usr/bin/env python3
"""
Messenger Agent - Formats data into beautiful Telegram messages
"""
import sys
import json
from datetime import datetime

# Emoji mappings
EMOJIS = {
    "up": "📈",
    "down": "📉",
    "neutral": "➡️",
    "money": "💰",
    "alert": "🚨",
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
    "trade": "⚡",
    "chart": "📊",
    "search": "🔍",
    "time": "⏰",
    "rocket": "🚀",
    "fire": "🔥",
    "cool": "❄️",
    "think": "💭",
    "gear": "⚙️",
    "shield": "🛡️",
    "target": "🎯",
}

def format_price_alert(data):
    """Format price data into beautiful message"""
    change = data.get("change_24h", 0)
    emoji = EMOJIS["up"] if change > 0 else EMOJIS["down"] if change < 0 else EMOJIS["neutral"]
    
    return f"""
{EMOJIS['money']} *{data['symbol']} PRICE UPDATE*

💵 Price: `${data['price']:,.2f}`
{emoji} 24h Change: `{change:+.2f}%`
📊 Volume: `${data.get('volume', 0):,.0f}`

{EMOJIS['time']} {datetime.now().strftime('%H:%M UTC')}
""".strip()

def format_trade_alert(data):
    """Format trade execution"""
    pnl = data.get("pnl", 0)
    pnl_emoji = EMOJIS["up"] if pnl > 0 else EMOJIS["down"] if pnl < 0 else EMOJIS["neutral"]
    side_emoji = "🟢" if data['side'] == 'BUY' else "🔴"
    
    return f"""
{EMOJIS['trade']} *TRADE EXECUTED*

{side_emoji} *{data['side']}* {data['amount']} {data['symbol']}
💵 Price: `${data['price']:,.2f}`
💰 Total: `${data['total']:,.2f}`
{pnl_emoji} PnL: `${pnl:+.2f}`

{EMOJIS['success']} Status: {data.get('status', 'FILLED')}
""".strip()

def format_opportunity(data):
    """Format arbitrage opportunity"""
    spread = data.get("spread", 0)
    confidence = "🔥 HIGH" if spread > 2 else "⚠️ MEDIUM" if spread > 1 else "💭 LOW"
    
    return f"""
{EMOJIS['alert']} *ARBITRAGE OPPORTUNITY*

🪙 Token: *{data['symbol']}*
📊 Spread: `{spread:.2f}%`

🟢 Buy: `${data['buy_price']:,.2f}` on {data['buy_exchange']}
🔴 Sell: `${data['sell_price']:,.2f}` on {data['sell_exchange']}
💰 Est. Profit: `${data['profit']:,.2f}`

{confidence} Confidence
⏳ Expires: ~{data.get('time_left', 60)}s
""".strip()

def format_performance(data):
    """Format performance report"""
    pnl = data.get("total_pnl", 0)
    pnl_emoji = EMOJIS["up"] if pnl > 0 else EMOJIS["down"] if pnl < 0 else EMOJIS["neutral"]
    win_rate = data.get("win_rate", 0)
    
    # Insight based on performance
    if win_rate > 60:
        insight = f"{EMOJIS['rocket']} *Strong performance!* Win rate above 60%"
    elif win_rate < 40:
        insight = f"{EMOJIS['warning']} *Review strategy* - Win rate below 40%"
    else:
        insight = f"{EMOJIS['chart']} *Steady performance* - Within normal range"
    
    return f"""
{EMOJIS['chart']} *PERFORMANCE REPORT* - {data.get('period', 'ALL TIME')}

{pnl_emoji} PnL: `${pnl:+,.2f}`
🎯 Win Rate: `{win_rate:.1f}%`
📈 Trades: {data.get('wins', 0)}W / {data.get('losses', 0)}L

💎 Best: `+${data.get('best_trade', 0):,.2f}`
💔 Worst: `${data.get('worst_trade', 0):,.2f}`

{insight}
""".strip()

def format_diagnostic(data):
    """Format system diagnostic"""
    # Determine overall status
    errors = sum([
        "❌" in data.get("exchange_status", ""),
        "❌" in data.get("zc_personal", ""),
        "❌" in data.get("zc_trading", ""),
    ])
    
    if errors == 0:
        overall = f"{EMOJIS['success']} *ALL SYSTEMS OPERATIONAL*"
        rec = f"{EMOJIS['rocket']} Ready for trading!"
    elif errors < 2:
        overall = f"{EMOJIS['warning']} *DEGRADED PERFORMANCE*"
        rec = f"{EMOJIS['think']} Some services affected - check logs"
    else:
        overall = f"{EMOJIS['error']} *CRITICAL ISSUES DETECTED*"
        rec = f"{EMOJIS['shield']} Recommend immediate attention"
    
    return f"""
{EMOJIS['search']} *SYSTEM STATUS* - {datetime.now().strftime('%H:%M UTC')}

{overall}

🌐 Exchanges:
{data.get('exchange_status', 'Unknown')}

🤖 ZeroClaw:
• Personal: {data.get('zc_personal', 'Unknown')}
• Trading: {data.get('zc_trading', 'Unknown')}

💾 Resources:
• Disk: {data.get('disk_status', 'Unknown')}
• Memory: {data.get('memory_status', 'Unknown')}
• CPU: {data.get('cpu_status', 'Unknown')}

{rec}
""".strip()

def format_sentiment(data):
    """Format sentiment analysis"""
    score = data.get("score", 50)
    if score > 70:
        emoji = EMOJIS['fire']
        trend = "Bullish 🚀"
    elif score < 30:
        emoji = EMOJIS['cool']
        trend = "Bearish 📉"
    else:
        emoji = EMOJIS['neutral']
        trend = "Neutral ➡️"
    
    return f"""
📰 *MARKET SENTIMENT* - {data['symbol']}

{emoji} Score: `{score}/100`
📊 Trend: {trend}

💬 Sources:
{data.get('sources', 'No data')}

🔥 Key Mentions:
{data.get('mentions', 'None')}
""".strip()

def escape_markdown(text):
    """Escape markdown special characters for Telegram"""
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars:
        text = text.replace(char, f'\\{char}')
    return text

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: messenger-agent.py <format_type> [json_data]")
        print("Formats: price, trade, opportunity, performance, diagnostic, sentiment")
        return
    
    format_type = sys.argv[1]
    
    # Read data from stdin or args
    if len(sys.argv) > 2:
        try:
            data = json.loads(sys.argv[2])
        except:
            data = {"message": sys.argv[2]}
    else:
        try:
            data = json.loads(sys.stdin.read())
        except:
            data = {}
    
    # Format based on type
    formatters = {
        "price": format_price_alert,
        "trade": format_trade_alert,
        "opportunity": format_opportunity,
        "performance": format_performance,
        "diagnostic": format_diagnostic,
        "sentiment": format_sentiment,
    }
    
    if format_type in formatters:
        output = formatters[format_type](data)
        # Don't escape - Telegram handles basic markdown
        print(output)
    else:
        print(f"Unknown format type: {format_type}")

if __name__ == "__main__":
    main()
