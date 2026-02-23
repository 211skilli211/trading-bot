#!/usr/bin/env python3
"""
Message Templates for Trading Bot Scheduler
Supports: Manual signals, Auto-detected, Alerts, News broadcasts
"""

from datetime import datetime, timedelta
import re
import subprocess

def get_local_time():
    """Get local AST time (UTC-4) for display"""
    try:
        # Get UTC time
        raw_utc = subprocess.check_output(['date', '-u', '+%Y-%m-%d %H:%M:%S']).decode().strip()
        utc_dt = datetime.strptime(raw_utc, '%Y-%m-%d %H:%M:%S')
        # Subtract 4 hours for AST (St. Kitts)
        local_dt = utc_dt - timedelta(hours=4)
        return local_dt
    except:
        # Fallback: assume UTC-4
        return datetime.now() - timedelta(hours=4)

class MessageTemplates:
    """Generate formatted messages for different schedule types"""
    
    @staticmethod
    def manual_signal(pair: str, action: str, price: str, exchange: str = "", notes: str = "") -> str:
        """
        Manual trading signal
        Example: "Buy BTC/USDT at 67000 on Binance"
        """
        emoji = "🚀" if action.lower() == "buy" else "🔴"
        exchange_text = f" on {exchange}" if exchange else ""
        notes_text = f"\n📝 {notes}" if notes else ""
        
        return f"""{emoji} <b>TRADING SIGNAL</b> {emoji}

💱 <b>Pair:</b> {pair.upper()}
📊 <b>Action:</b> {action.upper()}
💰 <b>Price:</b> {price}{exchange_text}
⏰ <b>Scheduled:</b> [DELIVERY_TIME]{notes_text}

⚡️ Execute with caution"""

    @staticmethod
    def auto_arbitrage(pair: str, spread_pct: float, buy_exchange: str, sell_exchange: str, 
                       buy_price: float, sell_price: float, profit_per_unit: float) -> str:
        """
        Auto-detected arbitrage opportunity
        """
        spread_emoji = "🔥" if spread_pct > 1.0 else "💰" if spread_pct > 0.5 else "📊"
        
        return f"""{spread_emoji} <b>ARBITRAGE OPPORTUNITY</b> {spread_emoji}

💱 <b>Pair:</b> {pair.upper()}
📈 <b>Spread:</b> {spread_pct:.2f}%

🏦 <b>Buy:</b> {buy_exchange} @ ${buy_price:,.2f}
🏦 <b>Sell:</b> {sell_exchange} @ ${sell_price:,.2f}
💵 <b>Profit:</b> ${profit_per_unit:,.2f} per unit

⏱️ <b>Valid for:</b> 5 minutes
⚡️ <i>Act fast - spreads change quickly!</i>"""

    @staticmethod
    def price_alert(pair: str, condition: str, target_price: float, current_price: float = None) -> str:
        """
        Price alert notification
        Example: "Alert when BTC/USDT crosses 70000"
        """
        direction = "🟢 ABOVE" if "above" in condition.lower() or ">" in condition else "🔴 BELOW"
        current_text = f"📊 <b>Current:</b> ${current_price:,.2f}\n" if current_price else ""
        
        return f"""🚨 <b>PRICE ALERT TRIGGERED</b> 🚨

💱 <b>Pair:</b> {pair.upper()}
{current_text}🎯 <b>Target:</b> ${target_price:,.2f}
📍 <b>Condition:</b> {direction}

⏰ <b>Triggered:</b> [DELIVERY_TIME]

💡 Check your positions!"""

    @staticmethod
    def reminder(text: str, user: str = "") -> str:
        """
        Personal reminder/alert
        """
        user_text = f" for {user}" if user else ""
        return f"""⏰ <b>REMINDER</b>{user_text}

📝 {text}

⏰ [DELIVERY_TIME]

<i>This is an automated reminder</i>"""

    @staticmethod
    def news_broadcast(title: str, content: str, source: str = "", urgency: str = "normal") -> str:
        """
        Scheduled news/market update
        """
        urgency_emoji = {"high": "🔴", "normal": "📰", "low": "📎"}.get(urgency, "📰")
        source_text = f"\n📡 <b>Source:</b> {source}" if source else ""
        
        return f"""{urgency_emoji} <b>MARKET UPDATE</b> {urgency_emoji}

<b>{title}</b>

{content}{source_text}

⏰ <b>Published:</b> [DELIVERY_TIME]

<i>Stay informed, trade smart</i>"""

    @staticmethod
    def market_summary(pairs_data: list) -> str:
        """
        Scheduled market summary with multiple pairs
        pairs_data: list of dicts with pair, price, change_24h
        """
        lines = []
        for data in pairs_data:
            change = data.get('change_24h', 0)
            emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪️"
            lines.append(f"{emoji} <b>{data['pair']}</b>: ${data['price']:,.2f} ({change:+.2f}%)")
        
        return f"""📊 <b>MARKET SUMMARY</b> 📊

{chr(10).join(lines)}

⏰ <b>Updated:</b> [DELIVERY_TIME]

<i>24h change shown</i>"""


class MessageParser:
    """Parse user input and route to appropriate template"""
    
    # Pattern matchers for different message types
    PATTERNS = {
        'signal': [
            r'(buy|sell)\s+([A-Z]+[/\-]?[A-Z]+)\s+(?:at|@)?\s*\$?(\d+[\.,]?\d*)',
            r'signal:\s*(buy|sell)\s+([A-Z]+)',
        ],
        'alert': [
            r'alert\s+(?:when|if)\s+([A-Z]+[/\-]?[A-Z]+)\s+(?:goes|crosses|hits)\s+(above|below)\s*\$?(\d+)',
            r'remind\s+me\s+(?:to|about)\s+(.+)',
            r'reminder:\s*(.+)',
        ],
        'arbitrage': [
            r'arbitrage\s+([A-Z]+[/\-]?[A-Z]+)\s+(\d+\.?\d*)%?\s+spread',
        ],
        'news': [
            r'news:\s*(.+)',
            r'broadcast:\s*(.+)',
            r'update:\s*(.+)',
        ],
        'reminder': [
            r'remind\s+me\s+(?:to\s+)?(.+)',
        ]
    }
    
    @classmethod
    def parse(cls, message: str) -> dict:
        """
        Parse message and return dict with type and parameters
        """
        msg_lower = message.lower().strip()
        
        # Check for signal
        for pattern in cls.PATTERNS['signal']:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return {
                    'type': 'signal',
                    'action': match.group(1),
                    'pair': match.group(2).replace('-', '/'),
                    'price': match.group(3).replace(',', ''),
                    'exchange': cls._extract_exchange(message),
                    'notes': cls._extract_notes(message)
                }
        
        # Check for alert (price-based)
        alert_price_pattern = r'alert\s+(?:when|if)\s+([A-Z]+[/\-]?[A-Z]+)\s+(?:goes|crosses|hits)\s+(above|below)\s*\$?(\d+)'
        match = re.search(alert_price_pattern, message, re.IGNORECASE)
        if match:
            return {
                'type': 'alert',
                'pair': match.group(1).replace('-', '/'),
                'condition': match.group(2),
                'target': float(match.group(3))
            }
        
        # Check for reminder (simple text-based, not price alert)
        reminder_pattern = r'remind\s+me\s+(?:to\s+)?(.+)'
        match = re.search(reminder_pattern, message, re.IGNORECASE)
        if match:
            # Make sure it's not a price alert
            if not re.search(r'(crosses|hits|above|below|\$?\d{3,})', match.group(1)):
                return {
                    'type': 'reminder',
                    'text': match.group(1).strip()
                }
        
        # Check for news/broadcast
        for pattern in cls.PATTERNS['news']:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return {
                    'type': 'news',
                    'title': 'Market Update',
                    'content': match.group(1)
                }
        
        # Default: treat as reminder
        return {
            'type': 'reminder',
            'text': message
        }
    
    @classmethod
    def generate(cls, parsed: dict) -> str:
        """Generate formatted message from parsed data"""
        templates = MessageTemplates()
        msg_type = parsed.get('type', 'reminder')
        
        if msg_type == 'signal':
            return templates.manual_signal(
                pair=parsed['pair'],
                action=parsed['action'],
                price=f"${parsed['price']}",
                exchange=parsed.get('exchange', ''),
                notes=parsed.get('notes', '')
            )
        
        elif msg_type == 'alert':
            return templates.price_alert(
                pair=parsed['pair'],
                condition=parsed['condition'],
                target_price=parsed['target']
            )
        
        elif msg_type == 'arbitrage':
            return templates.auto_arbitrage(
                pair=parsed['pair'],
                spread_pct=parsed.get('spread', 0.5),
                buy_exchange=parsed.get('buy_exchange', 'Exchange A'),
                sell_exchange=parsed.get('sell_exchange', 'Exchange B'),
                buy_price=parsed.get('buy_price', 0),
                sell_price=parsed.get('sell_price', 0),
                profit_per_unit=parsed.get('profit', 0)
            )
        
        elif msg_type == 'news':
            return templates.news_broadcast(
                title=parsed.get('title', 'Market Update'),
                content=parsed.get('content', ''),
                source=parsed.get('source', '')
            )
        
        else:  # reminder
            return templates.reminder(
                text=parsed.get('text', parsed.get('content', 'Reminder')),
                user=parsed.get('user', '')
            )
    
    @staticmethod
    def _extract_exchange(message: str) -> str:
        """Try to extract exchange name from message"""
        exchanges = ['binance', 'coinbase', 'kraken', 'bybit', 'okx', 'kucoin', 'gate', 'mexc']
        msg_lower = message.lower()
        for ex in exchanges:
            if ex in msg_lower:
                return ex.capitalize()
        return ""
    
    @staticmethod
    def _extract_notes(message: str) -> str:
        """Extract any additional notes after price"""
        # Remove common prefixes
        clean = re.sub(r'(buy|sell)\s+\w+\s+(at|@)?\s*\$?\d+', '', message, flags=re.IGNORECASE)
        clean = re.sub(r'on\s+\w+', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'schedule\s+', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'for\s+in\s+\d+\s*(min|hour)', '', clean, flags=re.IGNORECASE)
        return clean.strip()


if __name__ == "__main__":
    # Test the templates
    parser = MessageParser()
    templates = MessageTemplates()
    
    test_messages = [
        "Buy BTC/USDT at 67000 on Binance",
        "Sell ETH-USD at 3500",
        "Alert when BTC crosses above 70000",
        "Remind me to check SOL position",
        "News: Bitcoin ETF approvals driving institutional adoption",
    ]
    
    print("=== Template Tests ===\n")
    for msg in test_messages:
        parsed = parser.parse(msg)
        formatted = parser.generate(parsed)
        print(f"Input: {msg}")
        print(f"Type: {parsed['type']}")
        print(f"Output:\n{formatted}")
        print("-" * 50)
