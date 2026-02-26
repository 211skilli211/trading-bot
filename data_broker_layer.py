#!/usr/bin/env python3
"""
Data Broker Layer - Institutional-Grade Market Data
====================================================
Integrates premium data providers for enriched trading signals:
- CoinAPI: 400+ exchanges, tick-level historical, real-time WebSocket
- Amberdata: On-chain + derivatives + DeFi data (Solana focus)
- Alternative data: Sentiment, social, news aggregation

Usage:
    from data_broker_layer import DataBrokerLayer

    broker = DataBrokerLayer(coinapi_key="...", amberdata_key="...")

    # Get enriched price data
    data = await broker.get_enriched_data("BTC/USDT")

    # Get on-chain flows
    flows = await broker.get_onchain_flows("SOL")

    # Get sentiment score
    sentiment = await broker.get_sentiment("BTC")
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import requests
from collections import defaultdict

logger = logging.getLogger(__name__)


class DataProvider(Enum):
    """Supported data providers."""
    COINAPI = "coinapi"
    AMBERDATA = "amberdata"
    BIRDEYE = "birdeye"
    DEXSCREENER = "dexscreener"
    SENTIMENT = "sentiment"
    ONCHAIN = "onchain"


@dataclass
class PriceData:
    """Normalized price data across all providers."""
    symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    high_24h: float
    low_24h: float
    change_24h_pct: float
    timestamp: str
    exchange: str
    provider: str
    raw: Dict = field(default_factory=dict)


@dataclass
class OrderBookData:
    """Level 2 order book data."""
    symbol: str
    bids: List[List[float]]  # [price, quantity]
    asks: List[List[float]]
    spread: float
    spread_pct: float
    timestamp: str
    exchange: str
    provider: str


@dataclass
class OnChainData:
    """On-chain metrics for a token."""
    token: str
    price_usd: float
    volume_24h: float
    liquidity_usd: float
    holder_count: int
    whale_transactions_24h: int
    whale_volume_24h_usd: float
    exchange_inflow_24h: float
    exchange_outflow_24h: float
    active_addresses_24h: int
    transaction_count_24h: int
    avg_transaction_size: float
    timestamp: str
    provider: str
    raw: Dict = field(default_factory=dict)


@dataclass
class SentimentData:
    """Sentiment analysis data."""
    token: str
    sentiment_score: float  # -1.0 (bearish) to 1.0 (bullish)
    social_volume: int
    news_sentiment: float
    twitter_sentiment: float
    reddit_sentiment: float
    trending_rank: int
    mention_count_24h: int
    positive_mentions: int
    negative_mentions: int
    timestamp: str
    provider: str
    raw: Dict = field(default_factory=dict)


@dataclass
class EnrichedData:
    """Combined enriched data for decision making."""
    symbol: str
    price: PriceData
    orderbook: Optional[OrderBookData]
    onchain: Optional[OnChainData]
    sentiment: Optional[SentimentData]
    
    # Computed signals
    signal_score: float = 0.0  # -1.0 to 1.0
    confidence: float = 0.0    # 0.0 to 1.0
    signals: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "price": self.price.__dict__ if self.price else None,
            "orderbook": self.orderbook.__dict__ if self.orderbook else None,
            "onchain": self.onchain.__dict__ if self.onchain else None,
            "sentiment": self.sentiment.__dict__ if self.sentiment else None,
            "signal_score": self.signal_score,
            "confidence": self.confidence,
            "signals": self.signals
        }


class CoinAPIConnector:
    """
    CoinAPI Connector - 400+ exchanges, tick-level data.
    Docs: https://docs.coinapi.io/
    Free tier: 100 calls/day
    Paid: $79-$499/month
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://rest.coinapi.io/v1"
        self.ws_url = "wss://ws.coinapi.io/v1"
        self.headers = {"X-CoinAPI-Key": api_key}
        self.rate_limit_remaining = 100
        logger.info("[CoinAPI] Initialized")
    
    def get_price(self, symbol: str, exchange: str = "BINANCE") -> Optional[PriceData]:
        """Get current price for a symbol."""
        try:
            # CoinAPI symbol format: BINANCE_SPOT_BTC_USDT
            coinapi_symbol = f"{exchange}_SPOT_{symbol.replace('/', '_')}"
            url = f"{self.base_url}/ticker/{coinapi_symbol}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            self.rate_limit_remaining = int(response.headers.get("X-CoinAPI-Requests-Remaining", 0))
            
            return PriceData(
                symbol=symbol,
                price=data.get("price_last", 0),
                bid=data.get("bid", 0),
                ask=data.get("ask", 0),
                volume_24h=data.get("volume_1hrs", 0) * 24,
                high_24h=data.get("high_1hrs", 0),
                low_24h=data.get("low_1hrs", 0),
                change_24h_pct=data.get("price_change", 0),
                timestamp=data.get("time", datetime.now(timezone.utc).isoformat()),
                exchange=exchange,
                provider="coinapi",
                raw=data
            )
        except Exception as e:
            logger.error(f"[CoinAPI] Error fetching price: {e}")
            return None
    
    def get_orderbook(self, symbol: str, exchange: str = "BINANCE", limit: int = 20) -> Optional[OrderBookData]:
        """Get Level 2 order book."""
        try:
            coinapi_symbol = f"{exchange}_SPOT_{symbol.replace('/', '_')}"
            url = f"{self.base_url}/bookspot/{coinapi_symbol}"
            params = {"limit_levels": limit}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            bids = [[b["price"], b["size"]] for b in data.get("bids", [])]
            asks = [[a["price"], a["size"]] for a in data.get("asks", [])]
            
            spread = asks[0][0] - bids[0][0] if bids and asks else 0
            spread_pct = (spread / bids[0][0]) * 100 if bids else 0
            
            return OrderBookData(
                symbol=symbol,
                bids=bids,
                asks=asks,
                spread=spread,
                spread_pct=spread_pct,
                timestamp=data.get("time", datetime.now(timezone.utc).isoformat()),
                exchange=exchange,
                provider="coinapi"
            )
        except Exception as e:
            logger.error(f"[CoinAPI] Error fetching orderbook: {e}")
            return None
    
    def get_historical_ohlcv(
        self,
        symbol: str,
        exchange: str = "BINANCE",
        timeframe: str = "1HRS",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        Get historical OHLCV data (tick-level accuracy).
        
        Timeframes: 1SEC, 1MIN, 5MIN, 15MIN, 30MIN, 1HRS, 2HRS, 4HRS, 1DAY
        """
        try:
            coinapi_symbol = f"{exchange}_SPOT_{symbol.replace('/', '_')}"
            url = f"{self.base_url}/ohlcv/{coinapi_symbol}/latest"
            params = {"period_id": timeframe, "limit": limit}
            
            if start:
                params["time_start"] = start.isoformat()
            if end:
                params["time_end"] = end.isoformat()
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return [
                {
                    "timestamp": item.get("time_period_start"),
                    "open": item.get("price_open"),
                    "high": item.get("price_high"),
                    "low": item.get("price_low"),
                    "close": item.get("price_close"),
                    "volume": item.get("volume_traded")
                }
                for item in data
            ]
        except Exception as e:
            logger.error(f"[CoinAPI] Error fetching OHLCV: {e}")
            return None
    
    def get_exchange_list(self) -> List[str]:
        """Get list of supported exchanges."""
        try:
            url = f"{self.base_url}/exchanges"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return [ex["exchange_id"] for ex in response.json()]
        except Exception as e:
            logger.error(f"[CoinAPI] Error fetching exchanges: {e}")
            return []


class AmberdataConnector:
    """
    Amberdata Connector - On-chain + derivatives + DeFi data.
    Perfect for Solana trading with whale tracking, DEX liquidity, etc.
    Docs: https://docs.amberdata.io/
    Free tier available, paid from $99/month
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://web3id.io/api/v2"
        self.headers = {
            "x-api-key": api_key,
            "Accept": "application/json"
        }
        self.rate_limit_remaining = 100
        logger.info("[Amberdata] Initialized")
    
    def get_token_price(self, token_address: str, blockchain: str = "solana") -> Optional[PriceData]:
        """Get token price with on-chain context."""
        try:
            url = f"{self.base_url}/blockchains/{blockchain}/tokens/{token_address}/price"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return PriceData(
                symbol=token_address,
                price=data.get("value", 0),
                bid=0,
                ask=0,
                volume_24h=data.get("volume24h", 0),
                high_24h=data.get("high24h", 0),
                low_24h=data.get("low24h", 0),
                change_24h_pct=data.get("change24h", 0),
                timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                exchange="onchain",
                provider="amberdata",
                raw=data
            )
        except Exception as e:
            logger.error(f"[Amberdata] Error fetching token price: {e}")
            return None
    
    def get_onchain_metrics(self, token_address: str, blockchain: str = "solana") -> Optional[OnChainData]:
        """Get comprehensive on-chain metrics."""
        try:
            # Get token transfers and holder data
            url = f"{self.base_url}/blockchains/{blockchain}/tokens/{token_address}/metrics"
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extract whale transactions (large transfers)
            whale_txs = data.get("whaleTransactions", [])
            whale_volume = sum(tx.get("value", 0) for tx in whale_txs)
            
            # Exchange flows
            inflows = data.get("exchangeInflows", {})
            outflows = data.get("exchangeOutflows", {})
            
            return OnChainData(
                token=token_address,
                price_usd=data.get("price", 0),
                volume_24h=data.get("volume24h", 0),
                liquidity_usd=data.get("liquidity", 0),
                holder_count=data.get("holderCount", 0),
                whale_transactions_24h=len(whale_txs),
                whale_volume_24h_usd=whale_volume,
                exchange_inflow_24h=inflows.get("total", 0),
                exchange_outflow_24h=outflows.get("total", 0),
                active_addresses_24h=data.get("activeAddresses", 0),
                transaction_count_24h=data.get("transactionCount", 0),
                avg_transaction_size=data.get("avgTransactionSize", 0),
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider="amberdata",
                raw=data
            )
        except Exception as e:
            logger.error(f"[Amberdata] Error fetching on-chain metrics: {e}")
            return None
    
    def get_whale_alerts(self, blockchain: str = "solana", min_value_usd: float = 10000) -> List[Dict]:
        """Get recent whale transactions."""
        try:
            url = f"{self.base_url}/blockchains/{blockchain}/transactions/whale"
            params = {"minValue": min_value_usd, "limit": 20}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("transactions", [])
        except Exception as e:
            logger.error(f"[Amberdata] Error fetching whale alerts: {e}")
            return []
    
    def get_dex_liquidity(self, token_address: str, blockchain: str = "solana") -> Optional[Dict]:
        """Get DEX liquidity pools for a token."""
        try:
            url = f"{self.base_url}/blockchains/{blockchain}/tokens/{token_address}/pools"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pools = data.get("pools", [])
            total_liquidity = sum(p.get("liquidity", 0) for p in pools)
            
            return {
                "total_liquidity_usd": total_liquidity,
                "pool_count": len(pools),
                "top_pools": sorted(pools, key=lambda x: x.get("liquidity", 0), reverse=True)[:5]
            }
        except Exception as e:
            logger.error(f"[Amberdata] Error fetching DEX liquidity: {e}")
            return None
    
    def get_defi_rates(self, blockchain: str = "solana") -> Optional[Dict]:
        """Get DeFi lending/borrowing rates."""
        try:
            url = f"{self.base_url}/blockchains/{blockchain}/defi/rates"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[Amberdata] Error fetching DeFi rates: {e}")
            return None


class SentimentAnalyzer:
    """
    Sentiment Analysis - Aggregates social/news sentiment.
    Can integrate with:
    - Twitter API v2
    - Reddit API
    - NewsAPI
    - LunarCrush (crypto-specific social metrics)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.twitter_key = self.config.get("twitter_api_key")
        self.news_api_key = self.config.get("news_api_key")
        self.lunarcrush_key = self.config.get("lunarcrush_api_key")
        logger.info("[SentimentAnalyzer] Initialized")
    
    def get_sentiment(self, token: str) -> Optional[SentimentData]:
        """
        Get aggregated sentiment score for a token.
        Combines multiple sources if available.
        """
        try:
            # Try LunarCrush first (best for crypto)
            if self.lunarcrush_key:
                lc_sentiment = self._get_lunarcrush_sentiment(token)
                if lc_sentiment:
                    return lc_sentiment
            
            # Fallback to basic aggregation
            return self._aggregate_sentiment(token)
        except Exception as e:
            logger.error(f"[SentimentAnalyzer] Error: {e}")
            return None
    
    def _get_lunarcrush_sentiment(self, token: str) -> Optional[SentimentData]:
        """Get sentiment from LunarCrush API."""
        try:
            url = "https://api.lunarcrush.com/v3"
            params = {
                "key": self.lunarcrush_key,
                "symbol": token.upper(),
                "include": "social_stats,sentiment"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            social = data.get("data", {}).get("social_stats", {})
            sentiment = data.get("data", {}).get("sentiment", {})
            
            return SentimentData(
                token=token,
                sentiment_score=sentiment.get("sentiment_score", 0),
                social_volume=social.get("social_volume", 0),
                news_sentiment=sentiment.get("news_sentiment", 0),
                twitter_sentiment=sentiment.get("twitter_sentiment", 0),
                reddit_sentiment=sentiment.get("reddit_sentiment", 0),
                trending_rank=social.get("trending_rank", 0),
                mention_count_24h=social.get("mention_count_24h", 0),
                positive_mentions=social.get("positive_mentions", 0),
                negative_mentions=social.get("negative_mentions", 0),
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider="lunarcrush",
                raw=data
            )
        except Exception as e:
            logger.error(f"[LunarCrush] Error: {e}")
            return None
    
    def _aggregate_sentiment(self, token: str) -> SentimentData:
        """
        Basic sentiment aggregation (fallback).
        In production, integrate actual Twitter/Reddit/News APIs.
        """
        # Placeholder - implement actual API calls here
        return SentimentData(
            token=token,
            sentiment_score=0.0,
            social_volume=0,
            news_sentiment=0.0,
            twitter_sentiment=0.0,
            reddit_sentiment=0.0,
            trending_rank=0,
            mention_count_24h=0,
            positive_mentions=0,
            negative_mentions=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider="aggregated"
        )


class DataBrokerLayer:
    """
    Unified Data Broker Layer
    
    Aggregates data from multiple providers:
    - CoinAPI: Exchange prices, orderbooks, historical
    - Amberdata: On-chain metrics, whale tracking, DEX liquidity
    - Birdeye: Solana-specific OHLCV
    - DEXScreener: New pool detection
    - Sentiment: Social/news sentiment
    
    Features:
    - Automatic fallback between providers
    - Rate limit management
    - Data caching
    - Signal computation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize connectors
        self.coinapi: Optional[CoinAPIConnector] = None
        self.amberdata: Optional[AmberdataConnector] = None
        self.sentiment: Optional[SentimentAnalyzer] = None
        
        # Initialize if API keys available
        coinapi_key = self.config.get("coinapi_key") or os.getenv("COINAPI_KEY")
        if coinapi_key:
            self.coinapi = CoinAPIConnector(coinapi_key)
        
        amberdata_key = self.config.get("amberdata_key") or os.getenv("AMBERDATA_KEY")
        if amberdata_key:
            self.amberdata = AmberdataConnector(amberdata_key)
        
        sentiment_config = {
            "twitter_api_key": self.config.get("twitter_api_key") or os.getenv("TWITTER_API_KEY"),
            "news_api_key": self.config.get("news_api_key") or os.getenv("NEWS_API_KEY"),
            "lunarcrush_api_key": self.config.get("lunarcrush_api_key") or os.getenv("LUNARCRUSH_API_KEY")
        }
        if any(sentiment_config.values()):
            self.sentiment = SentimentAnalyzer(sentiment_config)
        
        # Cache for rate limiting
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 60  # seconds
        
        logger.info("[DataBrokerLayer] Initialized")
    
    def get_enriched_data(self, symbol: str, include_onchain: bool = True, include_sentiment: bool = True) -> Optional[EnrichedData]:
        """
        Get comprehensive enriched data for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            include_onchain: Include on-chain metrics
            include_sentiment: Include sentiment data
        
        Returns:
            EnrichedData with all available signals
        """
        try:
            # Get price data (try CoinAPI first, fallback to existing connectors)
            price_data = self._get_price_data(symbol)
            
            # Get orderbook
            orderbook = None
            if self.coinapi:
                orderbook = self.coinapi.get_orderbook(symbol)
            
            # Get on-chain data (for Solana tokens)
            onchain = None
            if include_onchain and self.amberdata:
                # Map symbol to token address if needed
                token_address = self._symbol_to_token_address(symbol)
                if token_address:
                    onchain = self.amberdata.get_onchain_metrics(token_address)
            
            # Get sentiment
            sentiment_data = None
            if include_sentiment and self.sentiment:
                token = symbol.split("/")[0]
                sentiment_data = self.sentiment.get_sentiment(token)
            
            # Create enriched data
            enriched = EnrichedData(
                symbol=symbol,
                price=price_data,
                orderbook=orderbook,
                onchain=onchain,
                sentiment=sentiment_data
            )
            
            # Compute signals
            enriched.signal_score, enriched.confidence, enriched.signals = self._compute_signals(enriched)
            
            return enriched
        except Exception as e:
            logger.error(f"[DataBrokerLayer] Error getting enriched data: {e}")
            return None
    
    def _get_price_data(self, symbol: str) -> Optional[PriceData]:
        """Get price data with fallback chain."""
        # Try CoinAPI
        if self.coinapi:
            price = self.coinapi.get_price(symbol)
            if price:
                return price
        
        # Fallback to CCXT (existing implementation)
        try:
            from crypto_price_fetcher import BinanceConnector, CoinbaseConnector
            
            binance = BinanceConnector()
            coinbase = CoinbaseConnector()
            
            # Try Binance first
            binance_data = binance.fetch_price(symbol.replace("/", ""))
            if binance_data:
                return PriceData(
                    symbol=symbol,
                    price=binance_data["price"],
                    bid=binance_data["bid"],
                    ask=binance_data["ask"],
                    volume_24h=binance_data["volume_24h"],
                    high_24h=0,
                    low_24h=0,
                    change_24h_pct=0,
                    timestamp=binance_data["timestamp"],
                    exchange="Binance",
                    provider="ccxt",
                    raw=binance_data
                )
        except Exception as e:
            logger.error(f"[Fallback] Error fetching from CCXT: {e}")
        
        return None
    
    def _symbol_to_token_address(self, symbol: str) -> Optional[str]:
        """Map trading symbol to token address for on-chain lookups."""
        # Common Solana token addresses
        TOKEN_ADDRESSES = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "BTC": "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
            "ETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
            "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
            "SRM": "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt",
            "MNGO": "MangoCzJ36AjZyKwVj3VnYU4GTonjfVEnJmvvWaxLac",
        }
        
        token = symbol.split("/")[0].upper()
        return TOKEN_ADDRESSES.get(token)
    
    def _compute_signals(self, enriched: EnrichedData) -> tuple:
        """
        Compute trading signals from enriched data.
        
        Returns:
            (signal_score, confidence, signal_details)
            signal_score: -1.0 (strong sell) to 1.0 (strong buy)
            confidence: 0.0 to 1.0
        """
        signals = {}
        score_components = []
        weights = []
        
        # Price-based signals
        if enriched.price:
            # 24h momentum
            momentum = enriched.price.change_24h_pct / 100
            signals["momentum"] = momentum
            score_components.append(momentum)
            weights.append(0.3)
            
            # Orderbook imbalance
            if enriched.orderbook:
                bid_volume = sum(b[1] for b in enriched.orderbook.bids[:5])
                ask_volume = sum(a[1] for a in enriched.orderbook.asks[:5])
                if bid_volume + ask_volume > 0:
                    ob_imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
                    signals["orderbook_imbalance"] = ob_imbalance
                    score_components.append(ob_imbalance)
                    weights.append(0.2)
        
        # On-chain signals
        if enriched.onchain:
            # Exchange flow (outflows = bullish)
            net_flow = enriched.onchain.exchange_outflow_24h - enriched.onchain.exchange_inflow_24h
            if enriched.onchain.volume_24h > 0:
                flow_score = net_flow / enriched.onchain.volume_24h
                flow_score = max(-1, min(1, flow_score))  # Clamp to [-1, 1]
                signals["exchange_flow"] = flow_score
                score_components.append(flow_score)
                weights.append(0.25)
            
            # Whale activity
            if enriched.onchain.whale_transactions_24h > 10:
                signals["whale_activity"] = "high"
                score_components.append(0.3)  # Slightly bullish
                weights.append(0.15)
            else:
                signals["whale_activity"] = "normal"
        
        # Sentiment signals
        if enriched.sentiment:
            sentiment_score = enriched.sentiment.sentiment_score
            signals["sentiment"] = sentiment_score
            score_components.append(sentiment_score)
            weights.append(0.2)
            
            # Social volume spike
            if enriched.sentiment.social_volume > 10000:
                signals["social_volume"] = "high"
            else:
                signals["social_volume"] = "normal"
        
        # Compute weighted score
        if not score_components:
            return 0.0, 0.0, signals
        
        total_weight = sum(weights)
        signal_score = sum(s * w for s, w in zip(score_components, weights)) / total_weight
        
        # Confidence based on data availability
        data_points = sum([
            1 if enriched.price else 0,
            1 if enriched.orderbook else 0,
            1 if enriched.onchain else 0,
            1 if enriched.sentiment else 0
        ])
        confidence = min(1.0, data_points / 4.0)
        
        return signal_score, confidence, signals
    
    def get_whale_watch(self, blockchain: str = "solana", min_usd: float = 50000) -> List[Dict]:
        """Get recent whale transactions."""
        if self.amberdata:
            return self.amberdata.get_whale_alerts(blockchain, min_usd)
        return []
    
    def get_market_overview(self, symbols: List[str]) -> Dict[str, EnrichedData]:
        """Get enriched data for multiple symbols."""
        results = {}
        for symbol in symbols:
            data = self.get_enriched_data(symbol)
            if data:
                results[symbol] = data
        return results
    
    def scan_arbitrage_opportunities(
        self,
        symbol: str,
        exchanges: List[str] = None,
        min_spread_pct: float = 0.5
    ) -> List[Dict]:
        """
        Scan for arbitrage opportunities across exchanges.
        
        Args:
            symbol: Trading pair
            exchanges: List of exchanges to scan
            min_spread_pct: Minimum spread percentage
        
        Returns:
            List of arbitrage opportunities
        """
        if not self.coinapi:
            return []
        
        if exchanges is None:
            exchanges = ["BINANCE", "COINBASE", "KRAKEN", "BYBIT"]
        
        prices = []
        for exchange in exchanges:
            price = self.coinapi.get_price(symbol, exchange)
            if price:
                prices.append(price)
        
        opportunities = []
        for i, p1 in enumerate(prices):
            for p2 in prices[i+1:]:
                spread_pct = abs(p1.price - p2.price) / min(p1.price, p2.price) * 100
                if spread_pct >= min_spread_pct:
                    opportunities.append({
                        "symbol": symbol,
                        "exchange_1": p1.exchange,
                        "exchange_2": p2.exchange,
                        "price_1": p1.price,
                        "price_2": p2.price,
                        "spread_pct": spread_pct,
                        "spread_absolute": abs(p1.price - p2.price),
                        "volume_1": p1.volume_24h,
                        "volume_2": p2.volume_24h,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
        
        return sorted(opportunities, key=lambda x: x["spread_pct"], reverse=True)


# Convenience function for easy integration
def create_data_broker_layer() -> DataBrokerLayer:
    """Create DataBrokerLayer from environment variables."""
    config = {
        "coinapi_key": os.getenv("COINAPI_KEY"),
        "amberdata_key": os.getenv("AMBERDATA_KEY"),
        "twitter_api_key": os.getenv("TWITTER_API_KEY"),
        "news_api_key": os.getenv("NEWS_API_KEY"),
        "lunarcrush_api_key": os.getenv("LUNARCRUSH_API_KEY")
    }
    return DataBrokerLayer(config)


# Test / Demo
if __name__ == "__main__":
    print("=" * 60)
    print("Data Broker Layer - Test Mode")
    print("=" * 60)
    
    # Initialize from environment
    broker = create_data_broker_layer()
    
    # Test 1: Get enriched data for BTC
    print("\n[Test 1] Enriched Data for BTC/USDT")
    print("-" * 60)
    
    enriched = broker.get_enriched_data("BTC/USDT")
    if enriched:
        print(f"Symbol: {enriched.symbol}")
        if enriched.price:
            print(f"Price: ${enriched.price.price:,.2f}")
            print(f"24h Change: {enriched.price.change_24h_pct:+.2f}%")
        if enriched.onchain:
            print(f"\nOn-Chain Metrics:")
            print(f"  Holders: {enriched.onchain.holder_count:,}")
            print(f"  Whale Txns (24h): {enriched.onchain.whale_transactions_24h}")
            print(f"  Exchange Net Flow: ${enriched.onchain.exchange_outflow_24h - enriched.onchain.exchange_inflow_24h:,.0f}")
        if enriched.sentiment:
            print(f"\nSentiment:")
            print(f"  Score: {enriched.sentiment.sentiment_score:+.2f}")
            print(f"  Social Volume: {enriched.sentiment.social_volume:,}")
        
        print(f"\nSignal Score: {enriched.signal_score:+.2f}")
        print(f"Confidence: {enriched.confidence:.0%}")
        print(f"Signals: {json.dumps(enriched.signals, indent=2)}")
    else:
        print("No data available (API keys not configured?)")
    
    # Test 2: Whale watch
    print("\n[Test 2] Whale Watch (Solana)")
    print("-" * 60)
    
    whales = broker.get_whale_watch("solana", min_usd=50000)
    if whales:
        print(f"Found {len(whales)} whale transactions")
        for tx in whales[:5]:
            print(f"  ${tx.get('value', 0):,.0f} | {tx.get('fromAddress', '???')} → {tx.get('toAddress', '???')}")
    else:
        print("No whale data (Amberdata API key required)")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("\nTo enable full functionality, set these environment variables:")
    print("  COINAPI_KEY=your_coinapi_key")
    print("  AMBERDATA_KEY=your_amberdata_key")
    print("  LUNARCRUSH_API_KEY=your_lunarcrush_key")
    print("\nFree tiers available for testing!")
