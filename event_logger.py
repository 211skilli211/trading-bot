#!/usr/bin/env python3
"""
Structured Event Logger
=======================
Centralized structured logging with event categorization.

Features:
- JSON structured logs (one JSON object per line)
- Event types: TRADE, SIGNAL, RISK, SYSTEM, ERROR, PERFORMANCE
- Async-safe file writing
- Log rotation (max file size)
- In-memory ring buffer for recent events
- Query/filter recent events

Usage:
    from event_logger import EventLogger, EventType
    logger = EventLogger()
    logger.log(EventType.TRADE, {"symbol": "BTC", "side": "buy"})
    recent = logger.get_recent(event_type="TRADE", limit=10)
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from collections import deque


class EventType(Enum):
    TRADE = "TRADE"
    SIGNAL = "SIGNAL"
    RISK = "RISK"
    SYSTEM = "SYSTEM"
    ERROR = "ERROR"
    PERFORMANCE = "PERFORMANCE"
    STRATEGY = "STRATEGY"
    SENTIMENT = "SENTIMENT"
    API = "API"


class EventLogger:
    """
    Structured event logger for trading bot.

    All events are written as JSON Lines (one JSON object per file line)
    for easy parsing by external tools (jq, ELK, etc.)
    """

    def __init__(
        self,
        log_dir: str = "logs",
        max_file_size_mb: int = 50,
        ring_buffer_size: int = 1000,
    ):
        self.log_dir = log_dir
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.ring_buffer: deque = deque(maxlen=ring_buffer_size)
        self._lock = threading.Lock()

        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "events.jsonl")

        # Also set up standard Python logger
        self._py_logger = logging.getLogger("trading_bot.events")
        if not self._py_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s"
            ))
            self._py_logger.addHandler(handler)
            self._py_logger.setLevel(logging.INFO)

        self.log(EventType.SYSTEM, {"message": "EventLogger initialized"})

    def log(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        level: str = "INFO",
    ):
        """Log a structured event."""
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type.value,
            "level": level,
            **data,
        }

        # Write to ring buffer
        self.ring_buffer.append(event)

        # Write to file
        line = json.dumps(event, default=str)
        with self._lock:
            self._rotate_if_needed()
            with open(self.log_file, "a") as f:
                f.write(line + "\n")
                f.flush()

        # Also send to Python logger for console output
        msg = f"{event_type.value} | {json.dumps(data, default=str)[:200]}"
        if level == "ERROR":
            self._py_logger.error(msg)
        elif level == "WARNING":
            self._py_logger.warning(msg)
        else:
            self._py_logger.debug(msg)

    # ── Convenience methods ─────────────────────────────────────

    def log_trade(self, symbol: str, side: str, price: float, quantity: float, **extra):
        self.log(EventType.TRADE, {
            "symbol": symbol, "side": side, "price": price, "quantity": quantity, **extra
        })

    def log_signal(self, strategy: str, signal: str, confidence: float = 0.0, **extra):
        self.log(EventType.SIGNAL, {
            "strategy": strategy, "signal": signal, "confidence": confidence, **extra
        })

    def log_risk(self, check: str, decision: str, reason: str = "", **extra):
        self.log(EventType.RISK, {
            "check": check, "decision": decision, "reason": reason, **extra
        })

    def log_performance(self, metric: str, value: float, **extra):
        self.log(EventType.PERFORMANCE, {
            "metric": metric, "value": value, **extra
        })

    def log_error(self, error: str, **extra):
        self.log(EventType.ERROR, {"error": error, **extra}, level="ERROR")

    def log_system(self, message: str, **extra):
        self.log(EventType.SYSTEM, {"message": message, **extra})

    def log_sentiment(self, asset: str, score: float, signal: str, **extra):
        self.log(EventType.SENTIMENT, {
            "asset": asset, "score": score, "signal": signal, **extra
        })

    # ── Queries ─────────────────────────────────────────────────

    def get_recent(
        self,
        event_type: str = None,
        level: str = None,
        limit: int = 100,
        since: str = None,
    ) -> List[Dict]:
        """Query recent events from ring buffer."""
        results = []
        for event in reversed(self.ring_buffer):
            if len(results) >= limit:
                break
            if event_type and event.get("type") != event_type:
                continue
            if level and event.get("level") != level:
                continue
            if since and event.get("ts", "") < since:
                continue
            results.append(event)
        return list(reversed(results))

    def get_trades(self, limit: int = 50) -> List[Dict]:
        """Get recent trade events."""
        return self.get_recent(event_type="TRADE", limit=limit)

    def get_errors(self, limit: int = 20) -> List[Dict]:
        """Get recent error events."""
        return self.get_recent(level="ERROR", limit=limit)

    def get_stats(self) -> Dict:
        """Get event statistics."""
        type_counts = {}
        for event in self.ring_buffer:
            t = event.get("type", "UNKNOWN")
            type_counts[t] = type_counts.get(t, 0) + 1
        return {
            "total_buffered": len(self.ring_buffer),
            "type_counts": type_counts,
            "log_file": self.log_file,
            "log_file_size": os.path.getsize(self.log_file) if os.path.exists(self.log_file) else 0,
        }

    # ── Maintenance ─────────────────────────────────────────────

    def _rotate_if_needed(self):
        """Rotate log file if it exceeds max size."""
        if os.path.exists(self.log_file):
            if os.path.getsize(self.log_file) > self.max_file_size:
                backup = f"{self.log_file}.{int(time.time())}"
                os.rename(self.log_file, backup)
                # Keep max 3 backups
                backups = sorted([
                    f for f in os.listdir(self.log_dir)
                    if f.startswith("events.jsonl.")
                ])
                for old in backups[:-3]:
                    os.remove(os.path.join(self.log_dir, old))

    def flush(self):
        """Flush ring buffer to file (events are already written)."""
        pass


# ── Global singleton ──────────────────────────────────────────────

_logger: Optional[EventLogger] = None


def get_logger() -> EventLogger:
    """Get or create global event logger."""
    global _logger
    if _logger is None:
        _logger = EventLogger()
    return _logger


# ── CLI / Test ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📝 Structured Event Logger - Test Mode")
    print("=" * 45)

    logger = EventLogger()

    # Generate test events
    logger.log_trade("BTC/USDT", "buy", 67500, 0.05, exchange="Binance", strategy="MACD")
    logger.log_trade("ETH/USDT", "sell", 3500, 1.2, exchange="Bybit", strategy="RSI")
    logger.log_signal("BollingerBandBreakout", "BUY", 0.75, symbol="SOL/USDT")
    logger.log_risk("position_check", "APPROVE", "Within limits", symbol="BTC")
    logger.log_performance("sharpe_ratio", 2.3, period="30d")
    logger.log_sentiment("BTC", 0.45, "bullish")
    logger.log_error("Connection timeout", exchange="Kraken")

    print("\n📊 Event stats:")
    stats = logger.get_stats()
    print(f"   Buffered: {stats['total_buffered']}")
    print(f"   Types: {stats['type_counts']}")

    print("\n📜 Recent trades:")
    for trade in logger.get_trades(limit=5):
        print(f"   {trade['ts'][:19]} | {trade.get('symbol')} {trade.get('side')} @ ${trade.get('price')}")
