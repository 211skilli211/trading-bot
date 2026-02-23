#!/usr/bin/env python3
"""
WebSocket Price Feed - Low Latency Market Data
Addresses Manus Audit: Latency Reduction

Features:
- Binance WebSocket streams for real-time price data
- Coinbase WebSocket feeds
- Automatic reconnection with exponential backoff
- Order book depth tracking for slippage calculation
- Multi-symbol support
- Thread-safe data access
"""

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("[WebSocketPriceFeed] websocket-client not installed. WebSocket features disabled.")

import json
import time
import threading
from typing import Dict, Optional, Callable, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class PriceTick:
    """Single price tick from WebSocket."""
    symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    timestamp: float
    exchange: str
    latency_ms: float = 0.0


@dataclass
class OrderBookLevel:
    """Order book price level."""
    price: float
    quantity: float


@dataclass
class OrderBook:
    """Order book snapshot."""
    symbol: str
    exchange: str
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    timestamp: float = 0.0
    
    def get_best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None
    
    def get_best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None
    
    def get_spread(self) -> Optional[float]:
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid and ask:
            return (ask - bid) / bid * 100
        return None
    
    def estimate_slippage(self, quantity: float, side: str) -> float:
        """
        Estimate slippage for a given order size.
        
        Args:
            quantity: Order size in base currency (e.g., BTC)
            side: "buy" or "sell"
        
        Returns:
            Estimated slippage percentage
        """
        levels = self.asks if side == "buy" else self.bids
        if not levels:
            return 0.0
        
        remaining = quantity
        total_cost = 0.0
        original_price = levels[0].price
        
        for level in levels:
            if remaining <= 0:
                break
            fill_qty = min(remaining, level.quantity)
            total_cost += fill_qty * level.price
            remaining -= fill_qty
        
        if remaining > 0:
            # Order larger than book depth - high slippage
            return 0.02  # 2% max estimation
        
        avg_price = total_cost / quantity
        slippage = abs(avg_price - original_price) / original_price
        return slippage


class WebSocketPriceFeed:
    """
    WebSocket-based price feed for low-latency arbitrage.
    
    Supports:
    - Binance Spot WebSocket API
    - Coinbase Exchange WebSocket
    - Automatic reconnection
    - Order book depth tracking
    """
    
    def __init__(
        self,
        exchanges: List[str] = None,
        symbols: List[str] = None,
        order_book_depth: int = 10,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10
    ):
        """
        Initialize WebSocket price feed.
        
        Args:
            exchanges: List of exchanges to connect to ["binance", "coinbase"]
            symbols: List of trading pairs ["BTC/USDT", "ETH/USDT"]
            order_book_depth: Depth of order book to maintain
            reconnect_delay: Initial reconnection delay in seconds
            max_reconnect_attempts: Maximum reconnection attempts
        """
        self.exchanges = exchanges or ["binance"]
        self.symbols = symbols or ["BTC/USDT"]
        self.order_book_depth = order_book_depth
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Data storage
        self.prices: Dict[str, Dict[str, PriceTick]] = defaultdict(dict)
        self.order_books: Dict[str, Dict[str, OrderBook]] = defaultdict(dict)
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # WebSocket connections
        self.ws_connections: Dict[str, websocket.WebSocketApp] = {}
        self.ws_threads: Dict[str, threading.Thread] = {}
        
        # Connection state
        self.connected = False
        self.reconnect_attempts: Dict[str, int] = defaultdict(int)
        self.last_ping: Dict[str, float] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Callbacks
        self.price_callbacks: List[Callable[[PriceTick], None]] = []
        
        # Statistics
        self.messages_received = 0
        self.connection_start_time: Dict[str, float] = {}
        
    def _normalize_symbol(self, symbol: str, exchange: str) -> str:
        """Normalize symbol format for different exchanges."""
        if exchange == "binance":
            return symbol.replace("/", "").lower()
        elif exchange == "coinbase":
            return symbol.replace("/", "-")
        return symbol
    
    def _denormalize_symbol(self, symbol: str, exchange: str) -> str:
        """Convert exchange-specific format back to standard."""
        if exchange == "binance":
            # btcusdt -> BTC/USDT
            if "usdt" in symbol.lower():
                return symbol.upper().replace("USDT", "/USDT")
            elif "btc" in symbol.lower():
                return symbol.upper().replace("BTC", "/BTC")
        elif exchange == "coinbase":
            return symbol.replace("-", "/")
        return symbol
    
    def connect(self):
        """Connect to all configured WebSocket feeds."""
        print("[WebSocketPriceFeed] Connecting to exchanges...")
        
        for exchange in self.exchanges:
            if exchange == "binance":
                self._connect_binance()
            elif exchange == "coinbase":
                self._connect_coinbase()
        
        self.connected = True
        print("[WebSocketPriceFeed] All connections initiated")
    
    def _connect_binance(self):
        """Connect to Binance WebSocket."""
        # Binance WebSocket URL for combined streams
        streams = []
        for symbol in self.symbols:
            norm_symbol = self._normalize_symbol(symbol, "binance")
            # Ticker stream for price data
            streams.append(f"{norm_symbol}@ticker")
            # Depth stream for order book
            streams.append(f"{norm_symbol}@depth{self.order_book_depth}@100ms")
        
        stream_path = "/".join(streams)
        url = f"wss://stream.binance.com:9443/stream?streams={stream_path}"
        
        def on_message(ws, message):
            self._on_binance_message(message)
        
        def on_error(ws, error):
            print(f"[Binance WS] Error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print(f"[Binance WS] Closed: {close_status_code} - {close_msg}")
            self._schedule_reconnect("binance")
        
        def on_open(ws):
            print("[Binance WS] Connected")
            self.reconnect_attempts["binance"] = 0
            self.connection_start_time["binance"] = time.time()
        
        ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        self.ws_connections["binance"] = ws
        
        # Start connection in separate thread
        thread = threading.Thread(target=ws.run_forever, daemon=True)
        thread.start()
        self.ws_threads["binance"] = thread
    
    def _connect_coinbase(self):
        """Connect to Coinbase WebSocket."""
        url = "wss://ws-feed.exchange.coinbase.com"
        
        product_ids = [self._normalize_symbol(s, "coinbase") for s in self.symbols]
        
        subscribe_msg = {
            "type": "subscribe",
            "product_ids": product_ids,
            "channels": ["ticker", "level2"]
        }
        
        def on_message(ws, message):
            self._on_coinbase_message(message)
        
        def on_error(ws, error):
            print(f"[Coinbase WS] Error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print(f"[Coinbase WS] Closed: {close_status_code} - {close_msg}")
            self._schedule_reconnect("coinbase")
        
        def on_open(ws):
            print("[Coinbase WS] Connected, subscribing...")
            ws.send(json.dumps(subscribe_msg))
            self.reconnect_attempts["coinbase"] = 0
            self.connection_start_time["coinbase"] = time.time()
        
        ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        self.ws_connections["coinbase"] = ws
        
        thread = threading.Thread(target=ws.run_forever, daemon=True)
        thread.start()
        self.ws_threads["coinbase"] = thread
    
    def _schedule_reconnect(self, exchange: str):
        """Schedule reconnection with exponential backoff."""
        if self.reconnect_attempts[exchange] >= self.max_reconnect_attempts:
            print(f"[WebSocketPriceFeed] Max reconnection attempts reached for {exchange}")
            return
        
        delay = self.reconnect_delay * (2 ** self.reconnect_attempts[exchange])
        delay = min(delay, 60)  # Cap at 60 seconds
        
        self.reconnect_attempts[exchange] += 1
        print(f"[WebSocketPriceFeed] Reconnecting to {exchange} in {delay:.1f}s (attempt {self.reconnect_attempts[exchange]})")
        
        def reconnect():
            time.sleep(delay)
            if exchange == "binance":
                self._connect_binance()
            elif exchange == "coinbase":
                self._connect_coinbase()
        
        threading.Thread(target=reconnect, daemon=True).start()
    
    def _on_binance_message(self, message: str):
        """Process Binance WebSocket message."""
        try:
            data = json.loads(message)
            stream = data.get("stream", "")
            payload = data.get("data", {})
            
            receive_time = time.time()
            
            if "@ticker" in stream:
                # Ticker data
                symbol = self._denormalize_symbol(payload.get("s", ""), "binance")
                if not symbol:
                    return
                
                tick = PriceTick(
                    symbol=symbol,
                    price=float(payload.get("c", 0)),
                    bid=float(payload.get("b", 0)),
                    ask=float(payload.get("a", 0)),
                    volume_24h=float(payload.get("v", 0)),
                    timestamp=receive_time,
                    exchange="binance",
                    latency_ms=0  # Could calculate from server time
                )
                
                with self._lock:
                    self.prices["binance"][symbol] = tick
                    self.price_history[symbol].append(tick)
                
                self._notify_price_callbacks(tick)
                self.messages_received += 1
                
            elif "@depth" in stream:
                # Order book update
                symbol = self._denormalize_symbol(stream.split("@")[0], "binance")
                if not symbol:
                    return
                
                bids = [
                    OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
                    for b in payload.get("bids", [])[:self.order_book_depth]
                ]
                asks = [
                    OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
                    for a in payload.get("asks", [])[:self.order_book_depth]
                ]
                
                order_book = OrderBook(
                    symbol=symbol,
                    exchange="binance",
                    bids=bids,
                    asks=asks,
                    timestamp=receive_time
                )
                
                with self._lock:
                    self.order_books["binance"][symbol] = order_book
        
        except Exception as e:
            logger.error(f"Error processing Binance message: {e}")
    
    def _on_coinbase_message(self, message: str):
        """Process Coinbase WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")
            receive_time = time.time()
            
            if msg_type == "ticker":
                symbol = self._denormalize_symbol(data.get("product_id", ""), "coinbase")
                if not symbol:
                    return
                
                tick = PriceTick(
                    symbol=symbol,
                    price=float(data.get("price", 0)),
                    bid=float(data.get("best_bid", 0)),
                    ask=float(data.get("best_ask", 0)),
                    volume_24h=float(data.get("volume_24h", 0)),
                    timestamp=receive_time,
                    exchange="coinbase",
                    latency_ms=0
                )
                
                with self._lock:
                    self.prices["coinbase"][symbol] = tick
                    self.price_history[symbol].append(tick)
                
                self._notify_price_callbacks(tick)
                self.messages_received += 1
                
            elif msg_type == "snapshot":
                # Initial order book snapshot
                symbol = self._denormalize_symbol(data.get("product_id", ""), "coinbase")
                if not symbol:
                    return
                
                bids = [
                    OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
                    for b in data.get("bids", [])[:self.order_book_depth]
                ]
                asks = [
                    OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
                    for a in data.get("asks", [])[:self.order_book_depth]
                ]
                
                order_book = OrderBook(
                    symbol=symbol,
                    exchange="coinbase",
                    bids=bids,
                    asks=asks,
                    timestamp=receive_time
                )
                
                with self._lock:
                    self.order_books["coinbase"][symbol] = order_book
        
        except Exception as e:
            logger.error(f"Error processing Coinbase message: {e}")
    
    def _notify_price_callbacks(self, tick: PriceTick):
        """Notify registered callbacks of price update."""
        for callback in self.price_callbacks:
            try:
                callback(tick)
            except Exception as e:
                logger.error(f"Price callback error: {e}")
    
    def get_price(self, symbol: str, exchange: str) -> Optional[PriceTick]:
        """Get current price for a symbol on an exchange."""
        with self._lock:
            return self.prices.get(exchange, {}).get(symbol)
    
    def get_all_prices(self) -> Dict[str, Dict[str, PriceTick]]:
        """Get all current prices."""
        with self._lock:
            return dict(self.prices)
    
    def get_order_book(self, symbol: str, exchange: str) -> Optional[OrderBook]:
        """Get order book for a symbol on an exchange."""
        with self._lock:
            return self.order_books.get(exchange, {}).get(symbol)
    
    def get_spread(self, symbol: str, exchange: str) -> Optional[float]:
        """Get current bid-ask spread."""
        order_book = self.get_order_book(symbol, exchange)
        if order_book:
            return order_book.get_spread()
        
        tick = self.get_price(symbol, exchange)
        if tick and tick.bid > 0 and tick.ask > 0:
            return (tick.ask - tick.bid) / tick.bid * 100
        return None
    
    def estimate_slippage(
        self,
        symbol: str,
        exchange: str,
        quantity: float,
        side: str
    ) -> float:
        """
        Estimate slippage for an order.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            exchange: Exchange name
            quantity: Order size in base currency
            side: "buy" or "sell"
        
        Returns:
            Estimated slippage percentage
        """
        order_book = self.get_order_book(symbol, exchange)
        if order_book:
            return order_book.estimate_slippage(quantity, side)
        
        # Fallback to default slippage if no order book
        return 0.001  # 0.1% default
    
    def find_arbitrage_opportunities(
        self,
        min_spread_pct: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities between exchanges.
        
        Returns list of opportunities with spread > min_spread_pct.
        """
        opportunities = []
        
        with self._lock:
            for symbol in self.symbols:
                prices_for_symbol = {}
                
                for exchange in self.exchanges:
                    tick = self.prices.get(exchange, {}).get(symbol)
                    if tick:
                        prices_for_symbol[exchange] = tick
                
                if len(prices_for_symbol) < 2:
                    continue
                
                # Find best buy and sell prices
                best_bid = None
                best_ask = None
                bid_exchange = None
                ask_exchange = None
                
                for exchange, tick in prices_for_symbol.items():
                    if best_bid is None or tick.bid > best_bid:
                        best_bid = tick.bid
                        bid_exchange = exchange
                    if best_ask is None or tick.ask < best_ask:
                        best_ask = tick.ask
                        ask_exchange = exchange
                
                if best_bid and best_ask and bid_exchange != ask_exchange:
                    spread_pct = (best_bid - best_ask) / best_ask * 100
                    
                    if spread_pct >= min_spread_pct:
                        opportunities.append({
                            "symbol": symbol,
                            "buy_exchange": ask_exchange,
                            "sell_exchange": bid_exchange,
                            "buy_price": best_ask,
                            "sell_price": best_bid,
                            "spread_pct": spread_pct,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
        
        return sorted(opportunities, key=lambda x: x["spread_pct"], reverse=True)
    
    def register_price_callback(self, callback: Callable[[PriceTick], None]):
        """Register a callback for price updates."""
        self.price_callbacks.append(callback)
    
    def unregister_price_callback(self, callback: Callable[[PriceTick], None]):
        """Unregister a price callback."""
        if callback in self.price_callbacks:
            self.price_callbacks.remove(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket feed statistics."""
        stats = {
            "connected": self.connected,
            "messages_received": self.messages_received,
            "exchanges": {}
        }
        
        for exchange in self.exchanges:
            uptime = 0
            if exchange in self.connection_start_time:
                uptime = time.time() - self.connection_start_time[exchange]
            
            stats["exchanges"][exchange] = {
                "connected": exchange in self.ws_connections,
                "reconnect_attempts": self.reconnect_attempts[exchange],
                "uptime_seconds": uptime,
                "symbols_tracked": len(self.prices.get(exchange, {}))
            }
        
        return stats
    
    def disconnect(self):
        """Disconnect all WebSocket connections."""
        print("[WebSocketPriceFeed] Disconnecting...")
        
        for exchange, ws in self.ws_connections.items():
            try:
                ws.close()
                print(f"[WebSocketPriceFeed] Disconnected from {exchange}")
            except Exception as e:
                logger.error(f"Error disconnecting from {exchange}: {e}")
        
        self.connected = False


# Example usage
if __name__ == "__main__":
    print("WebSocket Price Feed - Test Mode")
    print("=" * 60)
    
    # Initialize feed
    feed = WebSocketPriceFeed(
        exchanges=["binance"],
        symbols=["BTC/USDT", "ETH/USDT"],
        order_book_depth=5
    )
    
    # Register callback
    def on_price_update(tick: PriceTick):
        print(f"\r{tick.exchange:10} {tick.symbol:12} ${tick.price:>12,.2f} "
              f"Bid: ${tick.bid:>10,.2f} Ask: ${tick.ask:>10,.2f}", end="", flush=True)
    
    feed.register_price_callback(on_price_update)
    
    # Connect
    feed.connect()
    
    # Run for 30 seconds
    print("\nRunning for 30 seconds...")
    print("-" * 60)
    
    for i in range(30):
        time.sleep(1)
        
        # Every 5 seconds, check for arbitrage
        if i % 5 == 0 and i > 0:
            print(f"\n\n--- Arbitrage Check (second {i}) ---")
            opportunities = feed.find_arbitrage_opportunities(min_spread_pct=0.01)
            if opportunities:
                for opp in opportunities[:3]:
                    print(f"  {opp['symbol']}: {opp['spread_pct']:.3f}% "
                          f"(Buy {opp['buy_exchange']}, Sell {opp['sell_exchange']})")
            else:
                print("  No opportunities found")
            print("-" * 40)
    
    # Print stats
    print("\n\n" + "=" * 60)
    print("STATISTICS")
    print("=" * 60)
    stats = feed.get_stats()
    print(f"Messages received: {stats['messages_received']}")
    for exchange, ex_stats in stats['exchanges'].items():
        print(f"\n{exchange}:")
        print(f"  Connected: {ex_stats['connected']}")
        print(f"  Uptime: {ex_stats['uptime_seconds']:.1f}s")
        print(f"  Symbols: {ex_stats['symbols_tracked']}")
    
    # Disconnect
    feed.disconnect()
