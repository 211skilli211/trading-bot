#!/usr/bin/env python3
"""
ZeroClaw Sentiment Scanner Skill
Analyzes market sentiment from news, social media, and on-chain data
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Try to import sentiment analysis libraries
try:
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

class SentimentScanner:
    """Scan market sentiment from multiple sources"""
    
    def __init__(self):
        self.name = "sentiment-scanner"
        self.description = "Analyzes market sentiment from news and social signals"
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of a text snippet"""
        if not SENTIMENT_AVAILABLE:
            return {
                "polarity": 0.0,
                "subjectivity": 0.5,
                "sentiment": "neutral"
            }
        
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        if polarity > 0.2:
            sentiment = "positive"
        elif polarity < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"
            
        return {
            "polarity": round(polarity, 3),
            "subjectivity": round(subjectivity, 3),
            "sentiment": sentiment
        }
    
    def get_mock_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Get mock news for sentiment analysis (replace with real API)"""
        # This would integrate with news_fetcher.py in production
        mock_headlines = {
            "BTC": [
                "Bitcoin surges past $65K as institutional adoption grows",
                "Crypto markets show mixed signals amid regulatory concerns",
                "Analyst predicts BTC could reach $100K by year end"
            ],
            "ETH": [
                "Ethereum ETF approval sparks renewed interest",
                "DeFi protocols on Ethereum see record TVL",
                "ETH gas fees drop to lowest levels in months"
            ],
            "SOL": [
                "Solana ecosystem continues rapid expansion",
                "Network outages raise concerns about reliability",
                "SOL price action shows strong support levels"
            ]
        }
        
        base_symbol = symbol.replace("/USDT", "").replace("/USD", "")
        headlines = mock_headlines.get(base_symbol, [
            f"{base_symbol} shows interesting price action",
            "Markets await next catalyst for direction",
            f"Traders eye {base_symbol} support levels"
        ])
        
        news_items = []
        for headline in headlines:
            sentiment = self.analyze_text(headline)
            news_items.append({
                "headline": headline,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "Market Analysis",
                **sentiment
            })
        
        return news_items
    
    def scan_sentiment(self, symbol: str = None) -> Dict[str, Any]:
        """Scan overall market sentiment"""
        try:
            symbols = [symbol] if symbol else ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            results = {}
            
            overall_polarity = 0
            total_items = 0
            
            for sym in symbols:
                news = self.get_mock_news(sym)
                
                # Calculate average sentiment
                avg_polarity = sum(n["polarity"] for n in news) / len(news) if news else 0
                
                # Count sentiment types
                positive = sum(1 for n in news if n["sentiment"] == "positive")
                negative = sum(1 for n in news if n["sentiment"] == "negative")
                neutral = sum(1 for n in news if n["sentiment"] == "neutral")
                
                results[sym] = {
                    "average_polarity": round(avg_polarity, 3),
                    "sentiment_distribution": {
                        "positive": positive,
                        "negative": negative,
                        "neutral": neutral
                    },
                    "dominant_sentiment": "positive" if positive > negative else "negative" if negative > positive else "neutral",
                    "news_items": news[:3]  # Top 3
                }
                
                overall_polarity += avg_polarity
                total_items += 1
            
            # Overall market sentiment
            avg_market_sentiment = overall_polarity / total_items if total_items > 0 else 0
            
            sentiment_score = int((avg_market_sentiment + 1) * 50)  # Convert to 0-100
            
            return {
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_sentiment": {
                    "score": sentiment_score,
                    "rating": "bullish" if sentiment_score > 60 else "bearish" if sentiment_score < 40 else "neutral",
                    "confidence": "medium"
                },
                "by_symbol": results,
                "recommendation": self._generate_recommendation(sentiment_score)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _generate_recommendation(self, score: int) -> str:
        """Generate trading recommendation based on sentiment"""
        if score > 70:
            return "Strong bullish sentiment detected. Consider long positions with tight stops."
        elif score > 60:
            return "Moderate bullish sentiment. Good for swing trades."
        elif score > 40:
            return "Neutral sentiment. Wait for clear direction or scalp range."
        elif score > 30:
            return "Moderate bearish sentiment. Consider short positions or stay in cash."
        else:
            return "Strong bearish sentiment. Protect capital, avoid new longs."
    
    def handle(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main handler for the skill"""
        params = parameters or {}
        symbol = params.get("symbol")
        
        return self.scan_sentiment(symbol)


# Entry point for ZeroClaw
if __name__ == "__main__":
    import sys
    
    # Parse input from command line or stdin
    if len(sys.argv) > 1:
        try:
            params = json.loads(sys.argv[1])
        except:
            params = {"symbol": sys.argv[1]}
    else:
        params = {}
    
    scanner = SentimentScanner()
    result = scanner.handle(params)
    print(json.dumps(result, indent=2))
