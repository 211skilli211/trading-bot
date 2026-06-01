#!/usr/bin/env python3
"""
Discord Webhook Notifier
========================
Send trading alerts to Discord channels via webhook.

Features:
- Rich embed messages (colored, titled, fielded)
- Trade execution notifications
- Daily summary reports
- Error/alert notifications
- Rate limit handling (Discord allows 5/5s per webhook)

Usage:
    from discord_notifier import DiscordNotifier
    notifier = DiscordNotifier("https://discord.com/api/webhooks/...")
    notifier.send_trade_alert({"symbol": "BTC", "side": "buy", "price": 50000})
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord webhook notification handler."""

    # Discord color codes (integer)
    COLORS = {
        "buy": 0x00FF00,       # Green
        "sell": 0xFF0000,      # Red
        "profit": 0x00FF00,    # Green
        "loss": 0xFF4444,      # Red
        "info": 0x3498DB,      # Blue
        "warning": 0xFFA500,   # Orange
        "error": 0xFF0000,     # Red
        "summary": 0x9B59B6,   # Purple
        "neutral": 0x95A5A6,   # Gray
    }

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        username: str = "Trading Bot",
        avatar_url: str = "",
        rate_limit_per_5s: int = 5,
    ):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
        self.username = username
        self.avatar_url = avatar_url
        self.rate_limit = rate_limit_per_5s
        self._send_times: List[float] = []
        self._enabled = bool(self.webhook_url) and REQUESTS_AVAILABLE

        if self._enabled:
            logger.info("✅ Discord notifier enabled")
        else:
            logger.info("ℹ️ Discord notifier disabled (no webhook URL or requests)")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = time.time()
        self._send_times = [t for t in self._send_times if now - t < 5]
        return len(self._send_times) < self.rate_limit

    def _wait_for_rate_limit(self):
        """Block until rate limit allows sending."""
        while not self._check_rate_limit():
            time.sleep(0.5)

    def send(self, content: str = "", embed: Dict = None) -> bool:
        """Send a message to Discord."""
        if not self._enabled:
            return False

        self._wait_for_rate_limit()

        payload = {"username": self.username}
        if content:
            payload["content"] = content
        if embed:
            payload["embeds"] = [embed]
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            self._send_times.append(time.time())
            if resp.status_code in (200, 204):
                return True
            if resp.status_code == 429:
                # Rate limited — back off
                retry = float(resp.headers.get("Retry-After", 5))
                logger.warning(f"Discord rate limited, waiting {retry}s")
                time.sleep(retry)
                # Retry once
                return self.send(content, embed)
            logger.warning(f"Discord send failed: {resp.status_code} {resp.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Discord send error: {e}")
            return False

    def send_embed(
        self, title: str, description: str = "",
        color: int = 0x3498DB, fields: List[Dict] = None,
        footer: str = "", timestamp: bool = True,
    ) -> bool:
        """Send a rich embed message."""
        embed = {
            "title": title,
            "description": description,
            "color": color,
        }
        if fields:
            embed["fields"] = [{"name": f["name"], "value": f["value"], "inline": f.get("inline", True)} for f in fields]
        if footer:
            embed["footer"] = {"text": footer}
        if timestamp:
            embed["timestamp"] = datetime.now(timezone.utc).isoformat()
        return self.send(embed=embed)

    # ── Specialized notifications ──────────────────────────────

    def send_trade_alert(self, trade: Dict) -> bool:
        """Send trade execution notification."""
        side = trade.get("side", "buy").lower()
        color = self.COLORS.get(side, self.COLORS["neutral"])
        symbol = trade.get("symbol", "Unknown")
        price = trade.get("price", 0)
        quantity = trade.get("quantity", 0)
        value = trade.get("value", price * quantity)

        emoji = "🟢" if side == "buy" else "🔴"

        fields = [
            {"name": "💰 Price", "value": f"${price:,.2f}", "inline": True},
            {"name": "📊 Quantity", "value": f"{quantity:.6f}", "inline": True},
            {"name": "💵 Value", "value": f"${value:,.2f}", "inline": True},
        ]
        if trade.get("exchange"):
            fields.append({"name": "🏦 Exchange", "value": trade["exchange"], "inline": True})
        if trade.get("strategy"):
            fields.append({"name": "🎯 Strategy", "value": trade["strategy"], "inline": True})

        return self.send_embed(
            title=f"{emoji} Trade Executed: {symbol} {side.upper()}",
            color=color,
            fields=fields,
            footer="Trading Bot",
        )

    def send_pnl_update(self, total_pnl: float, return_pct: float, symbol: str = "Portfolio") -> bool:
        """Send P&L update."""
        emoji = "📈" if total_pnl >= 0 else "📉"
        color = self.COLORS["profit"] if total_pnl >= 0 else self.COLORS["loss"]

        return self.send_embed(
            title=f"{emoji} P&L Update: {symbol}",
            description=f"**${total_pnl:+,.2f}** ({return_pct:+.2f}%)",
            color=color,
            fields=[
                {"name": "P&L", "value": f"${total_pnl:+,.2f}", "inline": True},
                {"name": "Return", "value": f"{return_pct:+.2f}%", "inline": True},
            ],
        )

    def send_daily_summary(self, summary: Dict) -> bool:
        """Send daily trading summary."""
        fields = [
            {"name": "💰 Total P&L", "value": f"${summary.get('total_pnl', 0):+,.2f}", "inline": True},
            {"name": "📊 Return", "value": f"{summary.get('return_pct', 0):+.2f}%", "inline": True},
            {"name": "🎯 Trades", "value": str(summary.get("total_trades", 0)), "inline": True},
            {"name": "✅ Win Rate", "value": f"{summary.get('win_rate', 0):.0%}", "inline": True},
            {"name": "📉 Max Drawdown", "value": f"{summary.get('max_drawdown', 0):.2%}", "inline": True},
        ]
        if summary.get("top_performer"):
            fields.append({"name": "⭐ Top Strategy", "value": summary["top_performer"], "inline": True})

        pnl = summary.get("total_pnl", 0)
        emoji = "📊" if pnl >= 0 else "📉"
        color = self.COLORS["profit"] if pnl >= 0 else self.COLORS["loss"]

        return self.send_embed(
            title=f"{emoji} Daily Trading Summary",
            description=summary.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            color=color,
            fields=fields,
        )

    def send_alert(self, message: str, level: str = "info") -> bool:
        """Send an alert notification."""
        color = self.COLORS.get(level, self.COLORS["info"])
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(level, "ℹ️")
        return self.send_embed(
            title=f"{emoji} Trading Bot Alert",
            description=message,
            color=color,
        )


if __name__ == "__main__":
    print("💬 Discord Notifier - Test Mode")
    print("=" * 40)

    url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        print("Set DISCORD_WEBHOOK_URL env var to test")
        print("Example: export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
        exit(0)

    notifier = DiscordNotifier(url)

    # Test trade alert
    notifier.send_trade_alert({
        "symbol": "BTC/USDT",
        "side": "buy",
        "price": 67500.00,
        "quantity": 0.05,
        "exchange": "Binance",
        "strategy": "MACD Crossover",
    })

    # Test P&L
    notifier.send_pnl_update(1250.50, 12.5, "BTC/USDT")

    # Test summary
    notifier.send_daily_summary({
        "total_pnl": 2340.00,
        "return_pct": 23.4,
        "total_trades": 45,
        "win_rate": 0.67,
        "max_drawdown": 0.05,
        "top_performer": "RSI Mean Reversion",
    })

    print("✅ Test messages sent!")
