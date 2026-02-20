#!/usr/bin/env python3
"""
Test suite for WebSocket Price Feed
Tests connection, data handling, and arbitrage detection.
"""

import pytest
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from websocket_price_feed import (
    WebSocketPriceFeed, PriceTick, OrderBook, OrderBookLevel
)


class TestPriceTick:
    """Test PriceTick dataclass."""
    
    def test_tick_creation(self):
        """Test creating a price tick."""
        tick = PriceTick(
            symbol="BTC/USDT",
            price=50000.0,
            bid=49990.0,
            ask=50010.0,
            volume_24h=1000000.0,
            timestamp=time.time(),
            exchange="binance",
            latency_ms=50.0
        )
        
        assert tick.symbol == "BTC/USDT"
        assert tick.price == 50000.0
        assert tick.bid == 49990.0
        assert tick.ask == 50010.0
    
    def test_spread_calculation(self):
        """Test spread calculation from bid/ask."""
        tick = PriceTick(
            symbol="BTC/USDT",
            price=50000.0,
            bid=49990.0,
            ask=50010.0,
            volume_24h=1000000.0,
            timestamp=time.time(),
            exchange="binance"
        )
        
        spread_pct = (tick.ask - tick.bid) / tick.bid * 100
        assert spread_pct == pytest.approx(0.04, rel=1e-3)


class TestOrderBook:
    """Test OrderBook functionality."""
    
    @pytest.fixture
    def sample_orderbook(self):
        """Create a sample order book."""
        return OrderBook(
            symbol="BTC/USDT",
            exchange="binance",
            bids=[
                OrderBookLevel(price=49990.0, quantity=1.5),
                OrderBookLevel(price=49980.0, quantity=2.0),
                OrderBookLevel(price=49970.0, quantity=3.0),
            ],
            asks=[
                OrderBookLevel(price=50010.0, quantity=1.0),
                OrderBookLevel(price=50020.0, quantity=2.5),
                OrderBookLevel(price=50030.0, quantity=4.0),
            ],
            timestamp=time.time()
        )
    
    def test_best_bid_ask(self, sample_orderbook):
        """Test getting best bid and ask."""
        assert sample_orderbook.get_best_bid() == 49990.0
        assert sample_orderbook.get_best_ask() == 50010.0
    
    def test_spread_calculation(self, sample_orderbook):
        """Test spread calculation."""
        spread = sample_orderbook.get_spread()
        assert spread is not None
        assert spread == pytest.approx(0.04, rel=1e-3)
    
    def test_slippage_estimation_small_order(self, sample_orderbook):
        """Test slippage for small order that fits in first level."""
        # Order of 0.5 BTC fits in first ask level (1.0 available)
        slippage = sample_orderbook.estimate_slippage(0.5, "buy")
        assert slippage == 0.0  # No slippage, fills at best price
    
    def test_slippage_estimation_large_order(self, sample_orderbook):
        """Test slippage for large order spanning multiple levels."""
        # Order of 5 BTC needs multiple levels
        slippage = sample_orderbook.estimate_slippage(5.0, "buy")
        assert slippage > 0.0  # Should have slippage
        assert slippage < 0.02  # But less than max
    
    def test_slippage_estimation_very_large_order(self, sample_orderbook):
        """Test slippage for order larger than book depth."""
        # Order of 100 BTC exceeds book depth
        slippage = sample_orderbook.estimate_slippage(100.0, "buy")
        assert slippage == 0.02  # Should hit max estimation


class TestWebSocketPriceFeed:
    """Test WebSocketPriceFeed functionality."""
    
    def test_initialization(self):
        """Test feed initialization."""
        feed = WebSocketPriceFeed(
            exchanges=["binance"],
            symbols=["BTC/USDT"],
            order_book_depth=5
        )
        
        assert feed.exchanges == ["binance"]
        assert feed.symbols == ["BTC/USDT"]
        assert feed.order_book_depth == 5
        assert not feed.connected
    
    def test_symbol_normalization(self):
        """Test symbol normalization for exchanges."""
        feed = WebSocketPriceFeed()
        
        # Binance: BTC/USDT -> btcusdt
        norm = feed._normalize_symbol("BTC/USDT", "binance")
        assert norm == "btcusdt"
        
        # Coinbase: BTC/USDT -> BTC-USDT
        norm = feed._normalize_symbol("BTC/USDT", "coinbase")
        assert norm == "BTC-USDT"
    
    def test_symbol_denormalization(self):
        """Test symbol denormalization."""
        feed = WebSocketPriceFeed()
        
        # Binance: btcusdt -> BTC/USDT
        denorm = feed._denormalize_symbol("btcusdt", "binance")
        assert denorm == "BTC/USDT"
    
    def test_price_storage(self):
        """Test price data storage."""
        feed = WebSocketPriceFeed()
        
        tick = PriceTick(
            symbol="BTC/USDT",
            price=50000.0,
            bid=49990.0,
            ask=50010.0,
            volume_24h=1000000.0,
            timestamp=time.time(),
            exchange="binance"
        )
        
        # Manually store price
        feed.prices["binance"]["BTC/USDT"] = tick
        
        # Retrieve
        retrieved = feed.get_price("BTC/USDT", "binance")
        assert retrieved is not None
        assert retrieved.price == 50000.0
    
    def test_price_callback_registration(self):
        """Test callback registration."""
        feed = WebSocketPriceFeed()
        
        received_ticks = []
        
        def callback(tick):
            received_ticks.append(tick)
        
        feed.register_price_callback(callback)
        assert callback in feed.price_callbacks
        
        # Simulate notification
        tick = PriceTick(
            symbol="BTC/USDT",
            price=50000.0,
            bid=49990.0,
            ask=50010.0,
            volume_24h=1000000.0,
            timestamp=time.time(),
            exchange="binance"
        )
        feed._notify_price_callbacks(tick)
        
        assert len(received_ticks) == 1
        assert received_ticks[0].price == 50000.0
        
        # Unregister
        feed.unregister_price_callback(callback)
        assert callback not in feed.price_callbacks
    
    def test_arbitrage_detection(self):
        """Test arbitrage opportunity detection."""
        feed = WebSocketPriceFeed(
            exchanges=["binance", "coinbase"],
            symbols=["BTC/USDT"]
        )
        
        # Set up prices with arbitrage opportunity
        feed.prices["binance"]["BTC/USDT"] = PriceTick(
            symbol="BTC/USDT",
            price=50000.0,
            bid=50050.0,  # Higher bid on Binance
            ask=50060.0,
            volume_24h=1000000.0,
            timestamp=time.time(),
            exchange="binance"
        )
        
        feed.prices["coinbase"]["BTC/USDT"] = PriceTick(
            symbol="BTC/USDT",
            price=50000.0,
            bid=50000.0,
            ask=50010.0,  # Lower ask on Coinbase
            volume_24h=1000000.0,
            timestamp=time.time(),
            exchange="coinbase"
        )
        
        opportunities = feed.find_arbitrage_opportunities(min_spread_pct=0.05)
        
        assert len(opportunities) > 0
        opp = opportunities[0]
        assert opp["symbol"] == "BTC/USDT"
        assert opp["buy_exchange"] == "coinbase"  # Buy low
        assert opp["sell_exchange"] == "binance"  # Sell high
        assert opp["spread_pct"] > 0.05
    
    def test_slippage_with_orderbook(self):
        """Test slippage estimation using order book."""
        feed = WebSocketPriceFeed()
        
        # Set up order book
        feed.order_books["binance"]["BTC/USDT"] = OrderBook(
            symbol="BTC/USDT",
            exchange="binance",
            bids=[
                OrderBookLevel(price=49990.0, quantity=1.0),
            ],
            asks=[
                OrderBookLevel(price=50010.0, quantity=1.0),
            ],
            timestamp=time.time()
        )
        
        slippage = feed.estimate_slippage("BTC/USDT", "binance", 0.5, "buy")
        assert slippage == 0.0  # Fits in first level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
