#!/usr/bin/env python3
"""
CCXT Unified Exchange Connector
Replaces individual exchange connectors with CCXT library.
Supports 100+ exchanges with unified API.
"""

import ccxt
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


class CCXTConnector:
    """
    Unified exchange connector using CCXT.
    Supports Binance, Coinbase, Kraken, Bybit, KuCoin, and 100+ more.
    """
    
    EXCHANGE_MAP = {
        'binance': ccxt.binance,
        'coinbase': ccxt.coinbase,
        'kraken': ccxt.kraken,
        'bybit': ccxt.bybit,
        'kucoin': ccxt.kucoin,
        'okx': ccxt.okx,
        'gateio': ccxt.gateio,
        'bitget': ccxt.bitget,
    }
    
    def __init__(self, exchange_id: str, api_key: Optional[str] = None, 
                 secret: Optional[str] = None, sandbox: bool = True):
        """
        Initialize CCXT connector for specific exchange.
        
        Args:
            exchange_id: Exchange name (binance, coinbase, etc.)
            api_key: API key for authenticated requests
            secret: API secret
            sandbox: Use sandbox/testnet mode
        """
        self.exchange_id = exchange_id.lower()
        
        if self.exchange_id not in self.EXCHANGE_MAP:
            raise ValueError(f"Unsupported exchange: {exchange_id}")
        
        # Initialize exchange
        exchange_class = self.EXCHANGE_MAP[self.exchange_id]
        config = {
            'enableRateLimit': True,
            'sandbox': sandbox,
        }
        
        if api_key and secret:
            config['apiKey'] = api_key
            config['secret'] = secret
        
        self.exchange = exchange_class(config)
        self.name = self.exchange.name
        
        print(f"[CCXT] Initialized {self.name}")
        print(f"  Sandbox: {sandbox}")
        print(f"  Rate Limit: Enabled")
    
    def fetch_price(self, symbol: str = "BTC/USDT") -> Optional[Dict[str, Any]]:
        """
        Fetch ticker price for symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
        
        Returns:
            Normalized price data or None on error
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            
            return {
                "exchange": self.name,
                "symbol": symbol,
                "price": float(ticker['last']),
                "bid": float(ticker['bid']),
                "ask": float(ticker['ask']),
                "volume_24h": float(ticker['baseVolume'] or 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_response": ticker
            }
            
        except Exception as e:
            print(f"[CCXT:{self.name}] Error: {e}")
            return None
    
    def fetch_order_book(self, symbol: str = "BTC/USDT", limit: int = 10) -> Optional[Dict]:
        """
        Fetch order book depth for realistic slippage calculation.
        
        Args:
            symbol: Trading pair
            limit: Number of orders to fetch
        
        Returns:
            Order book data or None on error
        """
        try:
            order_book = self.exchange.fetch_order_book(symbol, limit)
            return {
                "exchange": self.name,
                "symbol": symbol,
                "bids": order_book['bids'][:limit],  # [price, amount]
                "asks": order_book['asks'][:limit],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            print(f"[CCXT:{self.name}] Order book error: {e}")
            return None
    
    def calculate_realistic_price(self, symbol: str, side: str, amount: float) -> Optional[float]:
        """
        Calculate realistic execution price including slippage from order book.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount to trade
        
        Returns:
            Average execution price or None
        """
        order_book = self.fetch_order_book(symbol)
        if not order_book:
            return None
        
        orders = order_book['asks'] if side == 'buy' else order_book['bids']
        remaining = amount
        total_cost = 0.0
        
        for price, qty in orders:
            if remaining <= 0:
                break
            
            fill_qty = min(remaining, qty)
            total_cost += fill_qty * price
            remaining -= fill_qty
        
        if remaining > 0:
            print(f"[CCXT:{self.name}] Warning: Not enough liquidity for {amount} {symbol}")
            return None
        
        return total_cost / amount


class MultiExchangeCCXT:
    """Connect to multiple exchanges via CCXT."""
    
    def __init__(self, exchanges: List[str], sandbox: bool = True):
        """
        Initialize multiple exchanges.
        
        Args:
            exchanges: List of exchange IDs
            sandbox: Use sandbox mode
        """
        self.connectors = {}
        
        for ex_id in exchanges:
            try:
                connector = CCXTConnector(ex_id, sandbox=sandbox)
                self.connectors[ex_id] = connector
            except Exception as e:
                print(f"[MultiCCXT] Failed to init {ex_id}: {e}")
        
        print(f"[MultiCCXT] Initialized {len(self.connectors)} exchanges")
    
    def fetch_all_prices(self, symbol: str = "BTC/USDT") -> List[Dict]:
        """Fetch prices from all connected exchanges."""
        prices = []
        
        for name, connector in self.connectors.items():
            print(f"[MultiCCXT] Fetching from {name}...")
            data = connector.fetch_price(symbol)
            if data:
                prices.append(data)
        
        return prices


if __name__ == "__main__":
    print("CCXT Connector - Test Mode")
    print("=" * 60)
    
    # Test single exchange
    print("\n[Test 1] Binance via CCXT")
    try:
        binance = CCXTConnector('binance', sandbox=True)
        data = binance.fetch_price("BTC/USDT")
        if data:
            print(f"  Price: ${data['price']:,.2f}")
            print(f"  Bid: ${data['bid']:,.2f}")
            print(f"  Ask: ${data['ask']:,.2f}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test order book
    print("\n[Test 2] Order Book Depth")
    try:
        book = binance.fetch_order_book("BTC/USDT", limit=5)
        if book:
            print(f"  Top 5 Bids: {[f'${b[0]:,.2f}' for b in book['bids']]}")
            print(f"  Top 5 Asks: {[f'${a[0]:,.2f}' for a in book['asks']]}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test realistic price
    print("\n[Test 3] Realistic Execution Price")
    try:
        price = binance.calculate_realistic_price("BTC/USDT", "buy", 0.01)
        if price:
            print(f"  Realistic buy price for 0.01 BTC: ${price:,.2f}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test multi-exchange
    print("\n[Test 4] Multi-Exchange")
    try:
        multi = MultiExchangeCCXT(['binance', 'kraken', 'bybit'], sandbox=True)
        prices = multi.fetch_all_prices("BTC/USDT")
        print(f"  Fetched {len(prices)} prices")
        for p in prices:
            print(f"    {p['exchange']}: ${p['price']:,.2f}")
    except Exception as e:
        print(f"  Error: {e}")
