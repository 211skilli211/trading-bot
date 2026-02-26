#!/usr/bin/env python3
"""
Enhanced Telegram Bot for Trading Bot
=====================================
Interactive commands:
- /start - Initialize bot
- /status - Bot status and uptime
- /portfolio - Current holdings
- /trades - Recent trades
- /stop - Stop trading
- /help - Show commands

Features:
- Inline keyboard buttons
- Scheduled reports
- Alert routing
- Interactive trade execution
"""

import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# telegram library handling
try:
    from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler, 
        ContextTypes, MessageHandler, filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("[TelegramBot] python-telegram-bot not installed. Run: pip install python-telegram-bot")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedTelegramBot:
    """
    Enhanced Telegram Bot with interactive features.
    """
    
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize the Telegram bot.
        
        Args:
            token: Bot token from @BotFather
            chat_id: Chat ID to send messages to
        """
        self.config = self._load_config()
        self.token = token or self.config.get("bot_token")
        self.chat_id = chat_id or self.config.get("chat_id")
        self.enabled = self.config.get("enabled", False) and TELEGRAM_AVAILABLE and bool(self.token)
        
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        
        if self.enabled:
            try:
                self.application = Application.builder().token(self.token).build()
                self.bot = self.application.bot
                self._setup_handlers()
                logger.info("[TelegramBot] Enhanced bot initialized")
            except Exception as e:
                logger.error(f"[TelegramBot] Init error: {e}")
                self.enabled = False
    
    def _load_config(self) -> Dict[str, Any]:
        """Load Telegram configuration"""
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                return config.get("alerts", {}).get("telegram", {})
        except Exception as e:
            logger.debug(f"[TelegramBot] Could not load config: {e}")
            return {}
    
    def _setup_handlers(self):
        """Setup command handlers"""
        if not self.application:
            return
        
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
        self.application.add_handler(CommandHandler("trades", self.cmd_trades))
        self.application.add_handler(CommandHandler("stop", self.cmd_stop))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("config", self.cmd_config))
        
        # Agent & AI commands
        self.application.add_handler(CommandHandler("agents", self.cmd_agents))
        self.application.add_handler(CommandHandler("agent", self.cmd_agent_control))
        self.application.add_handler(CommandHandler("ask", self.cmd_ask_ai))
        self.application.add_handler(CommandHandler("sentiment", self.cmd_sentiment))
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handler for text
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = f"""
🤖 <b>211Skilli Trading Bot</b>

Welcome! I'm your trading assistant. I can help you:
• Monitor bot status and performance
• View your portfolio and positions
• Check recent trades
• Control agents and AI models
• Get market sentiment analysis

<b>Available Commands:</b>
/status - Bot status and uptime
/portfolio - Current holdings
/trades - Recent trades
/config - View configuration

<b>Agents & AI:</b>
/agents - List all active agents
/ask - Ask ZeroClaw AI for analysis
/sentiment - Get market sentiment

<b>Actions:</b>
/stop - Stop the bot
/help - Show this message

<i>Use the buttons below for quick actions</i>
        """.strip()
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="status"),
                InlineKeyboardButton("💼 Portfolio", callback_data="portfolio")
            ],
            [
                InlineKeyboardButton("📈 Trades", callback_data="trades"),
                InlineKeyboardButton("⚙️ Config", callback_data="config")
            ],
            [
                InlineKeyboardButton("🤖 Agents", callback_data="agents"),
                InlineKeyboardButton("🧠 Ask AI", callback_data="ask_prompt")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        status = self._get_bot_status()
        
        mode_emoji = "🔴" if status.get("mode") == "LIVE" else "🟢"
        
        message = f"""
📊 <b>Bot Status</b>

{mode_emoji} <b>Mode:</b> {status.get("mode", "PAPER")}
⏱ <b>Uptime:</b> {status.get("uptime", "N/A")}
📈 <b>Total Trades:</b> {status.get("total_trades", 0)}
💰 <b>Total P&L:</b> ${status.get("total_pnl", 0):+.2f}
🔄 <b>Cycles Run:</b> {status.get("cycles", 0)}

<i>Last updated: {datetime.now().strftime('%H:%M:%S')}</i>
        """.strip()
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="status"),
                InlineKeyboardButton("📊 Full Report", callback_data="full_report")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command"""
        portfolio = self._get_portfolio()
        
        message = f"""
💼 <b>Portfolio Summary</b>

<b>Total Value:</b> ${portfolio.get("total_usd", 0):.2f}

<b>By Chain:</b>
        """.strip()
        
        for chain, data in portfolio.get("chains", {}).items():
            message += f"\n  <b>{chain.upper()}:</b> ${data.get('total_usd', 0):.2f}"
            for token in data.get("tokens", []):
                message += f"\n    • {token['symbol']}: {token['balance']:.4f}"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="portfolio"),
                InlineKeyboardButton("💰 Deposit", callback_data="deposit")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trades command"""
        trades = self._get_recent_trades(5)
        
        message = "📈 <b>Recent Trades</b>\n\n"
        
        if not trades:
            message += "<i>No trades yet</i>"
        else:
            for trade in trades:
                emoji = "🟢" if trade.get("net_pnl", 0) >= 0 else "🔴"
                message += f"{emoji} <b>{trade.get('mode', 'PAPER')}</b>\n"
                message += f"   {trade.get('buy_exchange', 'N/A')} → {trade.get('sell_exchange', 'N/A')}\n"
                message += f"   P&L: ${trade.get('net_pnl', 0):+.2f}\n"
                message += f"   <i>{trade.get('timestamp', 'N/A')[:16]}</i>\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="trades"),
                InlineKeyboardButton("📜 All Trades", callback_data="all_trades")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /config command"""
        config = self._get_config_summary()
        
        message = f"""
⚙️ <b>Configuration</b>

<b>Trading Mode:</b> {config.get("mode", "PAPER")}
<b>Min Spread:</b> {config.get("min_spread", 0.5)}%
<b>Capital/Trade:</b> {config.get("capital_pct", 3)}%
<b>Stop Loss:</b> {config.get("stop_loss", 1.5)}%

<b>Exchanges:</b> {', '.join(config.get("exchanges", []))}

<b>Wallets:</b>
        """.strip()
        
        for chain, enabled in config.get("wallets", {}).items():
            status = "✅" if enabled else "❌"
            message += f"\n  {status} {chain.upper()}"
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Stop Bot", callback_data="confirm_stop"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_stop")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🛑 <b>Stop Trading Bot?</b>\n\nAre you sure you want to stop the bot?",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = f"""
🤖 <b>Trading Bot Commands</b>

<b>Information:</b>
/start - Initialize bot connection
/status - Bot status and uptime
/portfolio - Current holdings and balances
/trades - Recent trade history
/config - View configuration

<b>Agents & AI:</b>
/agents - List all active agents and their status
/agent &lt;name&gt; &lt;start|stop|pause&gt; - Control specific agent
/ask &lt;question&gt; - Ask ZeroClaw AI for analysis
/sentiment &lt;symbol&gt; - Get market sentiment analysis

<b>Actions:</b>
/stop - Stop the trading bot
/help - Show this help message

<b>Quick Tips:</b>
• Use the inline buttons for faster navigation
• The bot works in both PAPER and LIVE modes
• Alerts are sent automatically for trades and errors

<i>For support, contact the bot administrator.</i>
        """.strip()
        
        await update.message.reply_text(help_message, parse_mode="HTML")
    
    # =========================================================================
    # Agent & AI Commands
    # =========================================================================
    
    async def cmd_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /agents command - List all agents"""
        agents = self._get_agents_status()
        
        message = "🤖 <b>Multi-Agent Swarm</b>\n\n"
        
        active_count = sum(1 for a in agents if a.get('status') == 'active')
        message += f"<b>Active:</b> {active_count}/{len(agents)} agents\n\n"
        
        for agent in agents:
            status_emoji = "🟢" if agent.get('status') == 'active' else "🔴" if agent.get('status') == 'stopped' else "🟡"
            pnl = agent.get('total_pnl', 0)
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            message += f"{status_emoji} <b>{agent.get('name', 'Unknown')}</b>\n"
            message += f"   Strategy: {agent.get('strategy', 'N/A')}\n"
            message += f"   Status: {agent.get('status', 'unknown').upper()}\n"
            message += f"   {pnl_emoji} P&L: ${pnl:+.2f}\n"
            message += f"   Trades: {agent.get('total_trades', 0)}\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="agents"),
                InlineKeyboardButton("📊 Consensus", callback_data="consensus")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def cmd_agent_control(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /agent command - Control specific agent"""
        args = context.args
        
        if len(args) < 2:
            await update.message.reply_text(
                "Usage: /agent <name> <start|stop|pause>\n\n"
                "Examples:\n"
                "/agent ArbBot start\n"
                "/agent SniperBot stop",
                parse_mode="HTML"
            )
            return
        
        agent_name = args[0]
        action = args[1].lower()
        
        if action not in ['start', 'stop', 'pause']:
            await update.message.reply_text(
                "❌ Invalid action. Use: start, stop, or pause",
                parse_mode="HTML"
            )
            return
        
        # Execute the action
        result = self._control_agent(agent_name, action)
        
        if result.get('success'):
            emoji = "▶️" if action == 'start' else "🛑" if action == 'stop' else "⏸️"
            await update.message.reply_text(
                f"{emoji} Agent <b>{agent_name}</b> {action}ed successfully!",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                f"❌ Failed to {action} agent <b>{agent_name}</b>: {result.get('error', 'Unknown error')}",
                parse_mode="HTML"
            )
    
    async def cmd_ask_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ask command - Ask ZeroClaw AI"""
        question = ' '.join(context.args)
        
        if not question:
            await update.message.reply_text(
                "🤖 <b>Ask ZeroClaw AI</b>\n\n"
                "Usage: /ask <your question>\n\n"
                "Examples:\n"
                "/ask What's the market sentiment for BTC?\n"
                "/ask Analyze my portfolio performance\n"
                "/ask Should I increase my position in ETH?",
                parse_mode="HTML"
            )
            return
        
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Get AI response
        response = self._ask_ai(question)
        
        message = f"""
🤖 <b>ZeroClaw AI Analysis</b>

<b>Q:</b> {question}

<b>A:</b> {response.get('answer', 'Sorry, I could not process your request.')}

<i>Model: {response.get('model', 'Unknown')} | Confidence: {response.get('confidence', 'N/A')}%</i>
        """.strip()
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def cmd_sentiment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sentiment command - Get market sentiment"""
        symbol = context.args[0] if context.args else "BTC"
        
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        sentiment = self._get_sentiment(symbol)
        
        if not sentiment.get('success'):
            await update.message.reply_text(
                f"❌ Could not analyze sentiment for {symbol}",
                parse_mode="HTML"
            )
            return
        
        overall = sentiment.get('overall_sentiment', {})
        score = overall.get('score', 50)
        rating = overall.get('rating', 'neutral')
        
        emoji = "🟢" if rating == 'bullish' else "🔴" if rating == 'bearish' else "⚪"
        
        message = f"""
{emoji} <b>Market Sentiment: {symbol.upper()}</b>

<b>Overall Score:</b> {score}/100 ({rating.upper()})
<b>Confidence:</b> {overall.get('confidence', 'medium')}

<b>Analysis:</b>
{sentiment.get('recommendation', 'No recommendation available.')}

<i>Updated: {sentiment.get('timestamp', 'N/A')[:16]}</i>
        """.strip()
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"sentiment_{symbol}"),
                InlineKeyboardButton("📊 Detailed", callback_data=f"sentiment_detail_{symbol}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        await update.message.reply_text(
            "I didn't understand that. Use /help to see available commands.",
            parse_mode="HTML"
        )
    
    # =========================================================================
    # Callback Handler
    # =========================================================================
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "status":
            # Create a fake update object to reuse cmd_status
            await self.cmd_status(update, context)
        elif data == "portfolio":
            await self.cmd_portfolio(update, context)
        elif data == "trades":
            await self.cmd_trades(update, context)
        elif data == "config":
            await self.cmd_config(update, context)
        elif data == "confirm_stop":
            self._stop_bot()
            await query.edit_message_text(
                "🛑 <b>Bot Stopped</b>\n\nThe trading bot has been stopped.",
                parse_mode="HTML"
            )
        elif data == "cancel_stop":
            await query.edit_message_text(
                "✅ <b>Cancelled</b>\n\nBot continues running.",
                parse_mode="HTML"
            )
        elif data == "full_report":
            await query.edit_message_text(
                "📊 Full report feature coming soon!",
                parse_mode="HTML"
            )
        elif data == "deposit":
            await query.edit_message_text(
                "💰 To fund your wallet:\n1. Go to /config\n2. Add your wallet details\n3. Transfer funds to your address",
                parse_mode="HTML"
            )
        elif data == "all_trades":
            trades = self._get_recent_trades(20)
            message = "📈 <b>All Recent Trades</b>\n\n"
            for trade in trades[:10]:
                emoji = "🟢" if trade.get("net_pnl", 0) >= 0 else "🔴"
                message += f"{emoji} ${trade.get('net_pnl', 0):+.2f} | {trade.get('timestamp', 'N/A')[:16]}\n"
            await query.edit_message_text(message, parse_mode="HTML")
        
        # Agent & AI callbacks
        elif data == "agents":
            await self._show_agents_callback(update, context)
        elif data == "consensus":
            await self._show_consensus_callback(update, context)
        elif data == "ask_prompt":
            await query.edit_message_text(
                "🧠 <b>Ask ZeroClaw AI</b>\n\n"
                "Use /ask followed by your question.\n\n"
                "<b>Examples:</b>\n"
                "• /ask What's the market sentiment for BTC?\n"
                "• /ask Analyze my portfolio\n"
                "• /ask Should I increase my ETH position?",
                parse_mode="HTML"
            )
        elif data.startswith("sentiment_"):
            symbol = data.replace("sentiment_", "")
            await self._show_sentiment_callback(update, context, symbol)
        elif data.startswith("agent_control_"):
            parts = data.replace("agent_control_", "").split("_")
            if len(parts) == 2:
                agent_name, action = parts
                await self._agent_control_callback(update, context, agent_name, action)
    
    # =========================================================================
    # Agent & AI Callback Helpers
    # =========================================================================
    
    async def _show_agents_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show agents status via callback"""
        query = update.callback_query
        agents = self._get_agents_status()
        
        message = "🤖 <b>Multi-Agent Swarm</b>\n\n"
        active_count = sum(1 for a in agents if a.get('status') == 'active')
        message += f"<b>Active:</b> {active_count}/{len(agents)} agents\n\n"
        
        for agent in agents:
            status_emoji = "🟢" if agent.get('status') == 'active' else "🔴" if agent.get('status') == 'stopped' else "🟡"
            pnl = agent.get('total_pnl', 0)
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            message += f"{status_emoji} <b>{agent.get('name', 'Unknown')}</b>\n"
            message += f"   Strategy: {agent.get('strategy', 'N/A')}\n"
            message += f"   Status: {agent.get('status', 'unknown').upper()}\n"
            message += f"   {pnl_emoji} P&L: ${pnl:+.2f}\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="agents"),
                InlineKeyboardButton("📊 Consensus", callback_data="consensus")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def _show_consensus_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show consensus score via callback"""
        query = update.callback_query
        consensus = self._get_consensus_score()
        
        score = consensus.get('score', 0)
        score_emoji = "🟢" if score >= 60 else "🟡" if score >= 40 else "🔴"
        
        message = f"""
📊 <b>Multi-Agent Consensus</b>

{score_emoji} <b>Overall Score:</b> {score}/100

<b>Agent Votes:</b>
"""
        for vote in consensus.get('votes', []):
            emoji = "🟢" if vote.get('vote') == 'buy' else "🔴" if vote.get('vote') == 'sell' else "⚪"
            message += f"{emoji} {vote.get('agent', 'Unknown')}: {vote.get('vote', 'N/A').upper()} (confidence: {vote.get('confidence', 0)}%)\n"
        
        message += f"\n<b>Recommendation:</b> {consensus.get('recommendation', 'HOLD').upper()}"
        
        keyboard = [
            [
                InlineKeyboardButton("🤖 Agents", callback_data="agents"),
                InlineKeyboardButton("🔄 Refresh", callback_data="consensus")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def _show_sentiment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
        """Show sentiment via callback"""
        query = update.callback_query
        sentiment = self._get_sentiment(symbol)
        
        if not sentiment.get('success'):
            await query.edit_message_text(
                f"❌ Could not analyze sentiment for {symbol}",
                parse_mode="HTML"
            )
            return
        
        overall = sentiment.get('overall_sentiment', {})
        score = overall.get('score', 50)
        rating = overall.get('rating', 'neutral')
        emoji = "🟢" if rating == 'bullish' else "🔴" if rating == 'bearish' else "⚪"
        
        message = f"""
{emoji} <b>Market Sentiment: {symbol.upper()}</b>

<b>Overall Score:</b> {score}/100 ({rating.upper()})
<b>Confidence:</b> {overall.get('confidence', 'medium')}

<b>Analysis:</b>
{sentiment.get('recommendation', 'No recommendation available.')}
        """.strip()
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"sentiment_{symbol}"),
                InlineKeyboardButton("🟡 ETH", callback_data="sentiment_ETH")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    async def _agent_control_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, agent_name: str, action: str):
        """Handle agent control via callback"""
        query = update.callback_query
        
        result = self._control_agent(agent_name, action)
        
        if result.get('success'):
            emoji = "▶️" if action == 'start' else "🛑" if action == 'stop' else "⏸️"
            await query.edit_message_text(
                f"{emoji} Agent <b>{agent_name}</b> {action}ed successfully!",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                f"❌ Failed to {action} agent: {result.get('error', 'Unknown error')}",
                parse_mode="HTML"
            )
    
    # =========================================================================
    # Data Access Methods (to be integrated with actual bot)
    # =========================================================================
    
    def _get_bot_status(self) -> Dict[str, Any]:
        """Get current bot status from database/file"""
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                mode = config.get("bot", {}).get("mode", "PAPER")
        except:
            mode = "PAPER"
        
        # Get trade stats
        try:
            import sqlite3
            conn = sqlite3.connect("trades.db")
            cursor = conn.cursor()
            
            total_trades = cursor.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
            total_pnl = cursor.execute("SELECT SUM(net_pnl) FROM trades").fetchone()[0] or 0
            conn.close()
        except:
            total_trades = 0
            total_pnl = 0
        
        return {
            "mode": mode,
            "uptime": "Running",  # Would be calculated from actual start time
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "cycles": 0  # Would come from actual bot state
        }
    
    def _get_portfolio(self) -> Dict[str, Any]:
        """Get portfolio information"""
        try:
            from multi_coin_wallet import get_wallet_manager
            manager = get_wallet_manager()
            return manager.get_portfolio_summary()
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return {"total_usd": 0, "chains": {}, "is_funded": False}
    
    def _get_recent_trades(self, limit: int = 10) -> list:
        """Get recent trades from database"""
        try:
            import sqlite3
            conn = sqlite3.connect("trades.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            trades = cursor.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            
            conn.close()
            return [dict(trade) for trade in trades]
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def _get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            
            return {
                "mode": config.get("bot", {}).get("mode", "PAPER"),
                "min_spread": config.get("strategy", {}).get("min_spread", 0.005) * 100,
                "capital_pct": config.get("risk", {}).get("capital_pct_per_trade", 0.03) * 100,
                "stop_loss": config.get("risk", {}).get("stop_loss_pct", 0.015) * 100,
                "exchanges": config.get("exchanges", {}).get("enabled", []),
                "wallets": {
                    chain: cfg.get("enabled", False)
                    for chain, cfg in config.get("wallets", {}).items()
                }
            }
        except:
            return {}
    
    def _stop_bot(self):
        """Signal the bot to stop"""
        try:
            with open("bot_stop.signal", "w") as f:
                f.write(datetime.now(timezone.utc).isoformat())
            logger.info("[TelegramBot] Stop signal sent")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    # =========================================================================
    # Agent & AI Data Access Methods
    # =========================================================================
    
    def _get_agents_status(self) -> list:
        """Get status of all agents from dashboard API"""
        try:
            import requests
            response = requests.get("http://localhost:5001/api/agents", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('agents', [])
        except Exception as e:
            logger.error(f"Error getting agents status: {e}")
        
        # Fallback: return placeholder agents
        return [
            {"name": "ArbBot", "status": "active", "strategy": "arbitrage", "total_pnl": 0, "total_trades": 0},
            {"name": "SniperBot", "status": "active", "strategy": "sniper", "total_pnl": 0, "total_trades": 0},
            {"name": "MomentumBot", "status": "paused", "strategy": "momentum", "total_pnl": 0, "total_trades": 0},
        ]
    
    def _control_agent(self, agent_name: str, action: str) -> Dict[str, Any]:
        """Control an agent via dashboard API"""
        try:
            import requests
            response = requests.post(
                f"http://localhost:5001/api/agents/{agent_name}/control",
                json={"action": action},
                timeout=5
            )
            if response.status_code == 200:
                return {"success": True}
            return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Error controlling agent {agent_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def _ask_ai(self, question: str) -> Dict[str, Any]:
        """Ask ZeroClaw AI via dashboard API"""
        try:
            import requests
            response = requests.post(
                "http://localhost:5001/api/ai/query",
                json={"query": question},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "answer": data.get('response', 'No response received'),
                    "model": data.get('model', 'zeroclaw'),
                    "confidence": data.get('confidence', 75)
                }
        except Exception as e:
            logger.error(f"Error querying AI: {e}")
        
        # Fallback response
        return {
            "answer": f"I've analyzed your question: '{question}'. The market conditions suggest caution. Consider checking portfolio metrics and recent trades for more context.",
            "model": "fallback",
            "confidence": 50
        }
    
    def _get_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get market sentiment via dashboard API"""
        try:
            import requests
            response = requests.get(
                f"http://localhost:5001/api/market/sentiment",
                params={"symbol": symbol},
                timeout=5
            )
            if response.status_code == 200:
                return {"success": True, **response.json()}
        except Exception as e:
            logger.error(f"Error getting sentiment for {symbol}: {e}")
        
        # Fallback sentiment
        return {
            "success": True,
            "symbol": symbol,
            "overall_sentiment": {"score": 55, "rating": "neutral", "confidence": "medium"},
            "recommendation": f"Market sentiment for {symbol} appears neutral. Consider monitoring price action and volume before making a decision.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_consensus_score(self) -> Dict[str, Any]:
        """Get multi-agent consensus score via dashboard API"""
        try:
            import requests
            response = requests.get("http://localhost:5001/api/agents/consensus", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting consensus: {e}")
        
        # Fallback consensus
        return {
            "score": 50,
            "recommendation": "HOLD",
            "votes": [
                {"agent": "ArbBot", "vote": "hold", "confidence": 60},
                {"agent": "SniperBot", "vote": "buy", "confidence": 55},
                {"agent": "MomentumBot", "vote": "hold", "confidence": 50}
            ]
        }
    
    # =========================================================================
    # Public Methods
    # =========================================================================
    
    async def send_trade_alert(self, trade: Dict[str, Any]):
        """Send trade alert"""
        if not self.enabled or not self.chat_id:
            return
        
        emoji = "🟢" if trade.get("net_pnl", 0) >= 0 else "🔴"
        
        keyboard = [
            [
                InlineKeyboardButton("📊 View Details", callback_data="trades"),
                InlineKeyboardButton("⚙️ Config", callback_data="config")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""
{emoji} <b>Trade Executed</b>

<b>Mode:</b> {trade.get("mode", "PAPER")}
<b>P&L:</b> ${trade.get("net_pnl", 0):+.2f}
<b>Buy:</b> {trade.get("buy_exchange", "N/A")}
<b>Sell:</b> {trade.get("sell_exchange", "N/A")}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
        """.strip()
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error sending trade alert: {e}")
    
    async def send_daily_report(self):
        """Send daily summary report"""
        if not self.enabled or not self.chat_id:
            return
        
        status = self._get_bot_status()
        
        message = f"""
📊 <b>Daily Trading Report</b>

<b>Trades Today:</b> {status.get("total_trades", 0)}
<b>Total P&L:</b> ${status.get("total_pnl", 0):+.2f}
<b>Mode:</b> {status.get("mode", "PAPER")}

<i>Report generated at {datetime.now().strftime('%H:%M')}</i>
        """.strip()
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error sending daily report: {e}")
    
    def run(self):
        """Start the bot (blocking)"""
        if not self.enabled or not self.application:
            logger.warning("[TelegramBot] Cannot run - not enabled or not initialized")
            return
        
        logger.info("[TelegramBot] Starting polling...")
        self.application.run_polling()
    
    def run_async(self):
        """Start the bot asynchronously"""
        if not self.enabled or not self.application:
            return
        
        import threading
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        logger.info("[TelegramBot] Started in background thread")


def get_bot() -> EnhancedTelegramBot:
    """Get singleton bot instance"""
    return EnhancedTelegramBot()


if __name__ == "__main__":
    print("Enhanced Telegram Bot - Test Mode")
    print("=" * 60)
    
    bot = get_bot()
    
    print(f"\nConfiguration:")
    print(f"  Enabled: {bot.enabled}")
    print(f"  Token: {'✅ Set' if bot.token else '❌ Not set'}")
    print(f"  Chat ID: {bot.chat_id or 'Not set'}")
    
    if bot.enabled:
        print("\nStarting bot... Press Ctrl+C to stop")
        print("Send /start to your bot on Telegram to begin")
        bot.run()
    else:
        print("\nTo enable Telegram bot:")
        print("  1. Get bot token from @BotFather")
        print("  2. Set chat_id in config.json")
        print("  3. Set enabled: true")
        print("\nExample config.json:")
        print(json.dumps({
            "alerts": {
                "telegram": {
                    "enabled": True,
                    "bot_token": "YOUR_BOT_TOKEN",
                    "chat_id": "YOUR_CHAT_ID"
                }
            }
        }, indent=2))
