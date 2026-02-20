#!/usr/bin/env python3
"""
News Fetcher - Free Alternatives
===============================
Fetches crypto news from free sources with sentiment analysis.

Free Alternatives Used:
1. CryptoPanic API (free crypto news)
2. RSS Feeds (CoinDesk, CoinTelegraph, etc.)
3. Local sentiment analysis with textblob

Usage:
    python news_fetcher.py --save         # Fetch and save to memory
    python news_fetcher.py --test         # Test fetching
    python news_fetcher.py --source rss   # Use RSS only
"""

import os
import json
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import requests
except ImportError:
    requests = None

try:
    import feedparser
except ImportError:
    feedparser = None


class CryptoNewsFetcher:
    """Fetch crypto news from free sources with sentiment"""
    
    def __init__(self):
        self.session = requests.Session() if requests else None
    
    def fetch_cryptopanic(self, keywords: List[str] = None, limit: int = 50) -> List[Dict]:
        """
        Fetch from CryptoPanic (free crypto news API).
        https://cryptopanic.com/free/
        """
        if not requests:
            return []
        
        try:
            # CryptoPanik free API
            url = "https://cryptopanic.com/api/free/v1/posts/"
            params = {
                "auth_token": "free",  # Free tier
                "kind": "news",
                "public": "true"
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("results", [])[:limit]:
                title = item.get("title", "")
                source = item.get("domain", "")
                
                articles.append({
                    "title": title,
                    "url": item.get("url", ""),
                    "source": source,
                    "published": item.get("published_at", ""),
                    "sentiment": self._estimate_sentiment(title),
                    "bias": self._estimate_bias(source),
                    "keywords": keywords or ["crypto"]
                })
            
            logger.info(f"CryptoPanic: fetched {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.warning(f"CryptoPanic error: {e}")
            return []
    
    def fetch_rss(self, keywords: List[str] = None, limit: int = 30) -> List[Dict]:
        """
        Fetch from free RSS feeds.
        """
        if not feedparser:
            logger.warning("feedparser not installed. Run: pip install feedparser")
            return []
        
        rss_feeds = [
            ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
            ("CoinTelegraph", "https://cointelegraph.com/rss"),
            ("Bitcoinist", "https://bitcoinist.com/feed/"),
            ("Decrypt", "https://decrypt.co/feed"),
        ]
        
        articles = []
        
        for source_name, feed_url in rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:limit // len(rss_feeds)]:
                    title = entry.get("title", "")
                    
                    # Filter by keywords if provided
                    if keywords:
                        if not any(k.lower() in title.lower() for k in keywords):
                            continue
                    
                    articles.append({
                        "title": title,
                        "summary": entry.get("summary", ""),
                        "url": entry.get("link", ""),
                        "source": source_name,
                        "published": entry.get("published", ""),
                        "sentiment": self._estimate_sentiment(title),
                        "bias": "center",  # RSS feeds are generally center
                        "keywords": keywords or ["crypto"]
                    })
                    
            except Exception as e:
                logger.warning(f"RSS error ({source_name}): {e}")
        
        # Remove duplicates by title
        seen = set()
        unique_articles = []
        for a in articles:
            if a["title"] not in seen:
                seen.add(a["title"])
                unique_articles.append(a)
        
        logger.info(f"RSS: fetched {len(unique_articles)} unique articles")
        return unique_articles[:limit]
    
    def fetch_all(self, keywords: List[str] = None, limit: int = 50) -> List[Dict]:
        """
        Fetch from all sources and combine.
        """
        all_articles = []
        
        # Try CryptoPanic first
        cp_articles = self.fetch_cryptopanic(keywords, limit)
        all_articles.extend(cp_articles)
        
        # Add RSS feeds
        rss_articles = self.fetch_rss(keywords, limit)
        
        # Avoid duplicates
        existing_titles = {a["title"] for a in all_articles}
        for a in rss_articles:
            if a["title"] not in existing_titles:
                all_articles.append(a)
        
        return all_articles[:limit]
    
    def _estimate_sentiment(self, text: str) -> float:
        """
        Estimate sentiment from text.
        
        Returns: float between -1 (bearish) and +1 (bullish)
        """
        bullish_terms = [
            "up", "rise", "gain", "bull", "rally", "surge", "positive",
            "soar", "jump", "boost", "growth", "record", "high", "win",
            "breakout", "momentum", "optimistic", "bullish", "moon", "hodl",
            "all-time", "peak", "approve", "adoption", "partnership", "launch"
        ]
        bearish_terms = [
            "down", "fall", "loss", "bear", "crash", "drop", "negative",
            "plunge", "sink", "slump", "decline", "low", "fail", "risk",
            "breakdown", "fear", "pessimist", "bearish", "ban", "hack",
            "scam", "warning", "crackdown", "regulate", "selloff", "reject"
        ]
        
        text_lower = text.lower()
        
        bullish_count = sum(1 for term in bullish_terms if term in text_lower)
        bearish_count = sum(1 for term in bearish_terms if term in text_lower)
        
        if bullish_count > bearish_count:
            return min(0.5 + (bullish_count * 0.1), 1.0)
        elif bearish_count > bullish_count:
            return max(-0.5 - (bearish_count * 0.1), -1.0)
        
        return 0.0
    
    def _estimate_bias(self, source: str) -> str:
        """Estimate source bias based on domain."""
        source = source.lower()
        
        left_sources = ["huffpost", "vox", "motherjones"]
        right_sources = ["foxnews", "breitbart", "dailywire"]
        
        for s in left_sources:
            if s in source:
                return "left"
        for s in right_sources:
            if s in source:
                return "right"
        
        return "center"
    
    def save_to_memory(self, memory=None, keywords: List[str] = None) -> int:
        """Fetch and save to TradingMemory."""
        from trading_memory import TradingMemory
        
        if memory is None:
            memory = TradingMemory()
        
        articles = self.fetch_all(keywords)
        
        # Transform to standard format
        formatted = []
        for a in articles:
            formatted.append({
                "title": a.get("title", ""),
                "sentiment": a.get("sentiment", 0),
                "bias": a.get("bias", "center"),
                "sources": [a.get("source", "unknown")],
                "url": a.get("url", ""),
                "keywords": a.get("keywords", keywords or ["crypto"])
            })
        
        count = memory.add_news(formatted)
        logger.info(f"Saved {count} articles to memory")
        
        return count


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Crypto News Fetcher")
    parser.add_argument("--keywords", nargs="+", 
                       default=["Bitcoin", "Ethereum", "Solana", "Crypto", "SEC", "Fed"],
                       help="Keywords to search")
    parser.add_argument("--limit", type=int, default=50, help="Max articles")
    parser.add_argument("--test", action="store_true", help="Test fetching")
    parser.add_argument("--save", action="store_true", help="Save to memory")
    parser.add_argument("--source", choices=["all", "cryptopanic", "rss"], default="all",
                       help="Data source")
    
    args = parser.parse_args()
    
    fetcher = CryptoNewsFetcher()
    
    # Fetch articles
    if args.source == "cryptopanic":
        articles = fetcher.fetch_cryptopanic(args.keywords, args.limit)
    elif args.source == "rss":
        articles = fetcher.fetch_rss(args.keywords, args.limit)
    else:
        articles = fetcher.fetch_all(args.keywords, args.limit)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"FETCHED {len(articles)} ARTICLES")
    print(f"{'='*60}")
    
    # Group by sentiment
    bullish = [a for a in articles if a.get("sentiment", 0) > 0.2]
    bearish = [a for a in articles if a.get("sentiment", 0) < -0.2]
    neutral = [a for a in articles if -0.2 <= a.get("sentiment", 0) <= 0.2]
    
    print(f"\n📈 Bullish: {len(bullish)}")
    print(f"📉 Bearish: {len(bearish)}")
    print(f"➡️  Neutral: {len(neutral)}")
    
    # Show sample headlines
    print(f"\n🔝 Top Headlines:")
    for i, article in enumerate(articles[:5], 1):
        sentiment = article.get("sentiment", 0)
        icon = "🟢" if sentiment > 0.2 else "🔴" if sentiment < -0.2 else "⚪"
        print(f"{icon} {article.get('title', '')[:65]}...")
    
    # Save to memory if requested
    if args.save:
        count = fetcher.save_to_memory(keywords=args.keywords)
        print(f"\n✅ Saved {count} articles to memory/")
    
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
