#!/usr/bin/env python3
"""
Social Sentiment Analysis Engine (OctoBot-style)
================================================
Analyzes social media sentiment for trading signals.

Data sources:
- Twitter/X API (v2) — crypto mentions, trending
- LunarCrush — social insights API
- News analysis — NLP sentiment on headlines
- Reddit — r/CryptoCurrency, r/SatoshiStreetBets

Output: sentiment score (-1.0 to +1.0) per asset

Usage:
    from social_sentiment import SentimentEngine
    engine = SentimentEngine()
    score = engine.get_sentiment("BTC")
"""

import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SentimentScore:
    asset: str
    score: float  # -1.0 (very bearish) to +1.0 (very bullish)
    volume: int       # number of mentions
    sources: Dict[str, float] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signal: str = "neutral"  # "buy", "sell", "neutral", "strong_buy", "strong_sell"
    confidence: float = 0.0   # 0.0 - 1.0

    def to_dict(self) -> Dict:
        return {
            "asset": self.asset,
            "score": self.score,
            "volume": self.volume,
            "sources": self.sources,
            "timestamp": self.timestamp,
            "signal": self.signal,
            "confidence": self.confidence,
        }


class BaseSentimentProvider:
    """Base class for sentiment data providers."""

    name: str = "base"
    enabled: bool = True

    def __init__(self, config: Dict = None):
        self.config = config or {}

    def get_sentiment(self, asset: str) -> Optional[float]:
        """Return sentiment score -1.0 to +1.0, or None if unavailable."""
        raise NotImplementedError


class TwitterSentimentProvider(BaseSentimentProvider):
    """Twitter/X v2 API sentiment analysis."""

    name = "twitter"

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN", "")
        self.base_url = "https://api.twitter.com/2"

    def get_sentiment(self, asset: str) -> Optional[float]:
        if not self.bearer_token or not REQUESTS_AVAILABLE:
            return None
        try:
            query = f"#{asset} OR ${asset} OR {asset} crypto -is:retweet lang:en"
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            resp = requests.get(
                f"{self.base_url}/tweets/search/recent",
                params={"query": query, "max_results": 100, "tweet.fields": "public_metrics,created_at"},
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            tweets = data.get("data", [])
            if not tweets:
                return 0.0

            # Simple word-based sentiment (production: use VADER or FinBERT)
            bullish_words = {"buy", "bull", "moon", "long", "pump", "breakout", "surge",
                             "rally", "up", "rise", "soar", "explode", "massive", "ATH"}
            bearish_words = {"sell", "bear", "dump", "short", "crash", "drop", "fall",
                             "down", "dip", "plunge", "rug", "scam", "dead", "death"}

            total_score = 0
            count = 0
            for tweet in tweets:
                text = tweet.get("text", "").lower()
                words = set(text.split())
                bull_count = len(words & bullish_words)
                bear_count = len(words & bearish_words)
                if bull_count + bear_count > 0:
                    total_score += (bull_count - bear_count) / (bull_count + bear_count)
                    count += 1

            if count == 0:
                return 0.0
            return max(-1.0, min(1.0, total_score / count))
        except Exception as e:
            logger.debug(f"Twitter sentiment error: {e}")
            return None


class LunarCrushProvider(BaseSentimentProvider):
    """LunarCrush social intelligence API."""

    name = "lunarcrush"

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.api_key = os.getenv("LUNARCRUSH_API_KEY", "")

    def get_sentiment(self, asset: str) -> Optional[float]:
        if not self.api_key or not REQUESTS_AVAILABLE:
            return None
        try:
            resp = requests.get(
                "https://api.lunarcrush.com/v2",
                params={
                    "data": "assets",
                    "key": self.api_key,
                    "symbol": asset,
                    "interval": "1d",
                },
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data.get("data", [])
            if not items:
                return None
            item = items[0]
            # Galactic score is 0-100, map to -1..1
            gal_score = item.get("galaxy_score", 50)
            social_score = item.get("social_score", 50)
            avg = (gal_score + social_score) / 2
            return (avg - 50) / 50  # -1.0 to 1.0
        except Exception as e:
            logger.debug(f"LunarCrush error: {e}")
            return None


class NewsSentimentProvider(BaseSentimentProvider):
    """News headline sentiment using NewsAPI."""

    name = "news"

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.api_key = os.getenv("NEWS_API_KEY", "")

    def get_sentiment(self, asset: str) -> Optional[float]:
        if not self.api_key or not REQUESTS_AVAILABLE:
            return None
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": f"{asset} cryptocurrency",
                    "sortBy": "publishedAt",
                    "pageSize": 50,
                    "apiKey": self.api_key,
                    "language": "en",
                },
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            articles = resp.json().get("articles", [])
            if not articles:
                return 0.0

            # Simple headline sentiment
            bullish = {"bull", "moon", "surge", "rally", "breakout", "adoption", "institutional",
                       "soar", "rise", "gain", "profit", "growth", "partnership", "launch"}
            bearish = {"bear", "crash", "dump", "hack", "ban", "regulation", "lawsuit",
                       "fraud", "scam", "collapse", "plunge", "loss", "sell-off"}
            total = 0
            count = 0
            for article in articles:
                title = article.get("title", "").lower()
                words = set(title.split())
                b = len(words & bullish)
                be = len(words & bearish)
                if b + be > 0:
                    total += (b - be) / (b + be)
                    count += 1

            if count == 0:
                return 0.0
            return max(-1.0, min(1.0, total / count))
        except Exception as e:
            logger.debug(f"News sentiment error: {e}")
            return None


class RedditSentimentProvider(BaseSentimentProvider):
    """Reddit crypto subreddits sentiment via public JSON API."""

    name = "reddit"

    SUBREDDITS = ["CryptoCurrency", "SatoshiStreetBets", "Bitcoin", "ethereum", "solana"]

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.subreddits = config.get("subreddits", self.SUBREDDITS) if config else self.SUBREDDITS

    def get_sentiment(self, asset: str) -> Optional[float]:
        if not REQUESTS_AVAILABLE:
            return None
        try:
            total_score = 0
            count = 0
            headers = {"User-Agent": "TradingBot-Sentiment/1.0"}
            for sub in self.subreddits[:3]:  # Limit to avoid rate limits
                try:
                    resp = requests.get(
                        f"https://www.reddit.com/r/{sub}/hot.json?limit=25",
                        headers=headers,
                        timeout=10,
                    )
                    if resp.status_code != 200:
                        continue
                    posts = resp.json().get("data", {}).get("children", [])
                    for post in posts:
                        title = post.get("data", {}).get("title", "").lower()
                        if asset.lower() in title.lower():
                            score_val = post.get("data", {}).get("score", 0)
                            total_score += min(1.0, max(-1.0, score_val / 1000))
                            count += 1
                except Exception:
                    continue

            if count == 0:
                return 0.0
            return total_score / count
        except Exception as e:
            logger.debug(f"Reddit sentiment error: {e}")
            return None


class SentimentCache:
    """TTL cache for sentiment results."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # key -> (timestamp, value)

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self.ttl:
                return val
            del self._cache[key]
        return None

    def set(self, key: str, val: Any):
        self._cache[key] = (time.time(), val)


# ── Main Sentiment Engine ─────────────────────────────────────────

class SentimentEngine:
    """
    Multi-source sentiment analysis engine.

    Aggregates sentiment from multiple providers into a single score:
    - Weight-based provider aggregation
    - Confidence scoring based on data volume
    - Signal classification (strong_buy / buy / neutral / sell / strong_sell)
    - Historical tracking with trend detection

    Usage:
        engine = SentimentEngine()
        score = engine.get_sentiment("BTC")
        # Returns SentimentScore with score, signal, confidence
    """

    # Provider weights (sum doesn't need to be 1.0, we normalize)
    DEFAULT_WEIGHTS = {
        "twitter": 0.35,
        "lunarcrush": 0.30,
        "news": 0.20,
        "reddit": 0.15,
    }

    # Signal thresholds
    SIGNAL_THRESHOLDS = {
        "strong_buy": 0.5,
        "buy": 0.2,
        "sell": -0.2,
        "strong_sell": -0.5,
    }

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.weights = self.config.get("provider_weights", self.DEFAULT_WEIGHTS)
        self.cache = SentimentCache(ttl_seconds=self.config.get("cache_ttl", 300))
        self.history: Dict[str, List[SentimentScore]] = defaultdict(list)
        self._init_providers()

    def _init_providers(self):
        self.providers: List[BaseSentimentProvider] = []
        provider_classes = {
            "twitter": TwitterSentimentProvider,
            "lunarcrush": LunarCrushProvider,
            "news": NewsSentimentProvider,
            "reddit": RedditSentimentProvider,
        }
        provider_config = self.config.get("providers", {})
        for name, cls in provider_classes.items():
            if self.config.get(f"enable_{name}", True):
                try:
                    prov = cls(provider_config.get(name, {}))
                    self.providers.append(prov)
                    logger.info(f"✅ Sentiment provider: {name}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to init {name}: {e}")

    def get_sentiment(self, asset: str) -> SentimentScore:
        """Get aggregated sentiment for an asset."""
        # Check cache
        cached = self.cache.get(asset)
        if cached:
            return cached

        # Gather from all providers
        source_scores = {}
        total_weight = 0
        weighted_sum = 0

        for provider in self.providers:
            score = provider.get_sentiment(asset)
            if score is not None:
                weight = self.weights.get(provider.name, 0.25)
                source_scores[provider.name] = score
                weighted_sum += score * weight
                total_weight += weight

        if total_weight == 0:
            result = SentimentScore(
                asset=asset, score=0.0, volume=0,
                sources={}, signal="neutral", confidence=0.0
            )
        else:
            avg_score = weighted_sum / total_weight
            signal = self._classify_signal(avg_score)
            confidence = min(1.0, total_weight) * min(1.0, len(source_scores) / 2)
            result = SentimentScore(
                asset=asset,
                score=round(avg_score, 4),
                volume=sum(1 for s in source_scores.values() if s != 0),
                sources=source_scores,
                signal=signal,
                confidence=round(confidence, 4),
            )

        # Store
        self.cache.set(asset, result)
        self.history[asset].append(result)
        # Keep last 100 entries
        if len(self.history[asset]) > 100:
            self.history[asset] = self.history[asset][-100:]

        return result

    def get_multi_sentiment(self, assets: List[str]) -> Dict[str, SentimentScore]:
        """Get sentiment for multiple assets."""
        return {asset: self.get_sentiment(asset) for asset in assets}

    def get_trend(self, asset: str, window: int = 10) -> str:
        """Detect sentiment trend: 'improving', 'deteriorating', 'stable'."""
        history = self.history.get(asset, [])[-window:]
        if len(history) < 3:
            return "unknown"
        recent = sum(h.score for h in history[-3:]) / 3
        older = sum(h.score for h in history[:3]) / 3
        diff = recent - older
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "deteriorating"
        return "stable"

    def get_top_bullish(self, assets: List[str], top_n: int = 5) -> List[Dict]:
        """Rank assets by bullish sentiment."""
        scores = self.get_multi_sentiment(assets)
        ranked = sorted(scores.values(), key=lambda s: s.score, reverse=True)
        return [s.to_dict() for s in ranked[:top_n]]

    def get_top_bearish(self, assets: List[str], top_n: int = 5) -> List[Dict]:
        """Rank assets by bearish sentiment."""
        scores = self.get_multi_sentiment(assets)
        ranked = sorted(scores.values(), key=lambda s: s.score)
        return [s.to_dict() for s in ranked[:top_n]]

    def _classify_signal(self, score: float) -> str:
        if score >= self.SIGNAL_THRESHOLDS["strong_buy"]:
            return "strong_buy"
        elif score >= self.SIGNAL_THRESHOLDS["buy"]:
            return "buy"
        elif score <= self.SIGNAL_THRESHOLDS["strong_sell"]:
            return "strong_sell"
        elif score <= self.SIGNAL_THRESHOLDS["sell"]:
            return "sell"
        return "neutral"


# ── CLI / Test ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🧠 Social Sentiment Engine - Test Mode")
    print("=" * 50)

    engine = SentimentEngine(config={"enable_twitter": False})  # Skip Twitter without bearer token

    test_assets = ["BTC", "ETH", "SOL"]
    for asset in test_assets:
        score = engine.get_sentiment(asset)
        print(f"\n{asset}:")
        print(f"  Score: {score.score:+.4f}")
        print(f"  Signal: {score.signal}")
        print(f"  Confidence: {score.confidence:.0%}")
        print(f"  Sources: {score.sources}")

    print(f"\nTrend (BTC): {engine.get_trend('BTC')}")
    print(f"\nTop bullish: {[s['asset'] for s in engine.get_top_bullish(test_assets)]}")
