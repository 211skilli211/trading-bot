#!/usr/bin/env python3
"""
PolyMarket Trading Client
=========================
Full-featured client for PolyMarket trading including:
- Market data reading (public API)
- Order book access (CLOB API)
- Order placement and cancellation
- Portfolio tracking
- Trade execution

Requirements:
- Polygon wallet with USDC
- CLOB API credentials from PolyMarket
- py-clob-client (optional but recommended)
"""

import os
import json
import logging
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

# Try to import official client, fall back to custom implementation
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCredentials, OrderArgs, OrderType
    CLOB_CLIENT_AVAILABLE = True
except ImportError:
    CLOB_CLIENT_AVAILABLE = False
    logging.warning("py-clob-client not installed. Using custom implementation.")

from polymarket_client import PolyMarketClient, BinaryMarket, GAMMA_API, CLOB_API

logger = logging.getLogger(__name__)


@dataclass
class PolyMarketCredentials:
    """PolyMarket API credentials"""
    api_key: str
    api_secret: str
    passphrase: str
    private_key: Optional[str] = None  # For on-chain transactions


@dataclass
class Order:
    """Represents a PolyMarket order"""
    id: str
    market_id: str
    side: str  # BUY or SELL
    outcome: str  # YES or NO
    price: float  # 0.01 to 0.99
    size: float  # Number of shares
    status: str  # OPEN, FILLED, CANCELLED
    created_at: str
    filled_size: float = 0.0
    remaining_size: float = 0.0


@dataclass
class PortfolioPosition:
    """Represents a portfolio position"""
    market_id: str
    question: str
    outcome: str  # YES or NO
    shares: float
    avg_price: float
    current_price: float
    value: float
    pnl: float
    pnl_percent: float


class PolyMarketTradingClient(PolyMarketClient):
    """
    Extended PolyMarket client with trading capabilities.
    
    Inherits from PolyMarketClient for market data,
    adds CLOB API for order management.
    """
    
    def __init__(self, credentials: Optional[PolyMarketCredentials] = None):
        """
        Initialize trading client.
        
        Args:
            credentials: PolyMarket API credentials (optional for read-only)
        """
        super().__init__(api_key=credentials.api_key if credentials else None)
        
        self.credentials = credentials
        self.clob_client = None
        self._init_clob_client()
    
    def _init_clob_client(self):
        """Initialize CLOB client if credentials available"""
        if not CLOB_CLIENT_AVAILABLE:
            logger.warning("CLOB client not available. Install with: pip install py-clob-client")
            return
        
        if not self.credentials or not self.credentials.api_key:
            logger.info("No API credentials. Read-only mode.")
            return
        
        try:
            # Initialize CLOB client
            host = CLOB_API
            
            # Create API credentials
            api_creds = ApiCredentials(
                api_key=self.credentials.api_key,
                api_secret=self.credentials.api_secret,
                api_passphrase=self.credentials.passphrase
            )
            
            self.clob_client = ClobClient(host, creds=api_creds)
            logger.info("CLOB client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize CLOB client: {e}")
            self.clob_client = None
    
    def is_trading_enabled(self) -> bool:
        """Check if trading is enabled (has CLOB client)"""
        return self.clob_client is not None
    
    def get_order_book(self, token_id: str) -> Optional[Dict]:
        """
        Get order book for a specific token.
        
        Args:
            token_id: CLOB token ID
            
        Returns:
            Order book with bids and asks
        """
        if not self.is_trading_enabled():
            # Fallback to public API
            return self._get_order_book_public(token_id)
        
        try:
            # Use CLOB client
            book = self.clob_client.get_order_book(token_id)
            return {
                "token_id": token_id,
                "bids": [[float(b.price), float(b.size)] for b in book.bids] if book.bids else [],
                "asks": [[float(a.price), float(a.size)] for a in book.asks] if book.asks else [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting order book: {e}")
            return self._get_order_book_public(token_id)
    
    def _get_order_book_public(self, token_id: str) -> Optional[Dict]:
        """Get order book using public API (fallback)"""
        try:
            response = self.session.get(
                f"{CLOB_API}/book/{token_id}",
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "token_id": token_id,
                    "bids": data.get("bids", []),
                    "asks": data.get("asks", []),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting public order book: {e}")
        return None
    
    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        order_type: str = "LIMIT"
    ) -> Optional[Order]:
        """
        Place an order on PolyMarket.
        
        Args:
            token_id: CLOB token ID
            side: BUY or SELL
            price: Price (0.01 to 0.99)
            size: Number of shares
            order_type: LIMIT or MARKET
            
        Returns:
            Order object if successful
        """
        if not self.is_trading_enabled():
            logger.error("Trading not enabled. Missing API credentials.")
            return None
        
        try:
            # Validate inputs
            if side not in ["BUY", "SELL"]:
                raise ValueError(f"Invalid side: {side}")
            
            if not 0.01 <= price <= 0.99:
                raise ValueError(f"Price must be between 0.01 and 0.99: {price}")
            
            if size <= 0:
                raise ValueError(f"Size must be positive: {size}")
            
            # Create order args
            order_args = OrderArgs(
                price=price,
                size=size,
                side=side.lower(),
                token_id=token_id
            )
            
            # Place order
            result = self.clob_client.create_order(order_args)
            
            if result and "orderID" in result:
                return Order(
                    id=result["orderID"],
                    market_id=token_id,
                    side=side,
                    outcome="YES" if "YES" in token_id else "NO",  # Simplified
                    price=price,
                    size=size,
                    status="OPEN",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    remaining_size=size
                )
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
        
        return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful
        """
        if not self.is_trading_enabled():
            logger.error("Trading not enabled")
            return False
        
        try:
            self.clob_client.cancel(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
        return False
    
    def cancel_all_orders(self) -> int:
        """
        Cancel all open orders.
        
        Returns:
            Number of orders cancelled
        """
        if not self.is_trading_enabled():
            logger.error("Trading not enabled")
            return 0
        
        try:
            cancelled = self.clob_client.cancel_all()
            logger.info(f"Cancelled {len(cancelled)} orders")
            return len(cancelled)
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
        return 0
    
    def get_open_orders(self) -> List[Order]:
        """
        Get all open orders.
        
        Returns:
            List of open orders
        """
        if not self.is_trading_enabled():
            return []
        
        try:
            orders = self.clob_client.get_open_orders()
            return [
                Order(
                    id=o.get("id", ""),
                    market_id=o.get("market", ""),
                    side=o.get("side", "").upper(),
                    outcome="YES",  # Determine from market
                    price=float(o.get("price", 0)),
                    size=float(o.get("size", 0)),
                    status="OPEN",
                    created_at=o.get("created_at", ""),
                    filled_size=float(o.get("takerAmount", 0)) - float(o.get("remaining", 0)),
                    remaining_size=float(o.get("remaining", 0))
                )
                for o in orders
            ]
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
        return []
    
    def get_portfolio(self) -> List[PortfolioPosition]:
        """
        Get current portfolio positions.
        
        Returns:
            List of positions
        """
        if not self.is_trading_enabled():
            return []
        
        try:
            # Get positions from CLOB
            positions = self.clob_client.get_positions()
            
            portfolio = []
            for pos in positions:
                # Get market info
                market = self.get_market(pos.get("conditionId", ""))
                question = market.get("question", "Unknown") if market else "Unknown"
                
                # Calculate P&L
                shares = float(pos.get("size", 0))
                avg_price = float(pos.get("avgPrice", 0))
                
                # Get current price
                token_id = pos.get("assetId", "")
                current_price = self.get_price_from_order_book(token_id) or avg_price
                
                value = shares * current_price
                cost = shares * avg_price
                pnl = value - cost
                pnl_percent = (pnl / cost * 100) if cost > 0 else 0
                
                portfolio.append(PortfolioPosition(
                    market_id=pos.get("conditionId", ""),
                    question=question,
                    outcome="YES" if pos.get("side") == "BUY" else "NO",
                    shares=shares,
                    avg_price=avg_price,
                    current_price=current_price,
                    value=value,
                    pnl=pnl,
                    pnl_percent=pnl_percent
                ))
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
        return []
    
    def get_price_from_order_book(self, token_id: str) -> Optional[float]:
        """Get best price from order book"""
        book = self.get_order_book(token_id)
        if book and book.get("bids"):
            # Best bid price
            return float(book["bids"][0][0])
        return None
    
    def get_balance(self) -> Dict[str, float]:
        """
        Get USDC balance on PolyMarket.
        
        Returns:
            Dict with cash and portfolio values
        """
        if not self.is_trading_enabled():
            return {"cash": 0.0, "portfolio": 0.0, "total": 0.0}
        
        try:
            # Get balance from CLOB
            balance = self.clob_client.get_balance()
            
            # Calculate portfolio value
            portfolio = self.get_portfolio()
            portfolio_value = sum(p.value for p in portfolio)
            
            return {
                "cash": float(balance.get("available", 0)),
                "portfolio": portfolio_value,
                "total": float(balance.get("total", 0)) + portfolio_value
            }
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
        
        return {"cash": 0.0, "portfolio": 0.0, "total": 0.0}
    
    def execute_arbitrage(self, market: BinaryMarket, max_position: float = 100.0) -> Optional[Order]:
        """
        Execute arbitrage trade on a market.
        
        Args:
            market: BinaryMarket with arbitrage opportunity
            max_position: Maximum position size in USD
            
        Returns:
            Order if executed
        """
        if not market.is_arbitrageable:
            logger.info(f"No arbitrage opportunity in {market.question[:50]}...")
            return None
        
        # Calculate position size
        # Buy equal amounts of YES and NO
        # Profit = $1 - (YES_price + NO_price)
        
        position_size = min(max_position, self.credentials.max_position_usd if self.credentials else 100)
        yes_amount = position_size / 2
        no_amount = position_size / 2
        
        logger.info(f"Executing arbitrage on {market.question[:50]}...")
        logger.info(f"  YES: ${market.yes_price:.4f} x {yes_amount:.2f}")
        logger.info(f"  NO:  ${market.no_price:.4f} x {no_amount:.2f}")
        logger.info(f"  Expected profit: {market.arbitrage_percent:.2f}%")
        
        # Place YES order
        yes_order = self.place_order(
            token_id=market.yes_token,
            side="BUY",
            price=market.yes_price,
            size=yes_amount / market.yes_price if market.yes_price > 0 else 0
        )
        
        # Place NO order
        no_order = self.place_order(
            token_id=market.no_token,
            side="BUY",
            price=market.no_price,
            size=no_amount / market.no_price if market.no_price > 0 else 0
        )
        
        if yes_order and no_order:
            logger.info("✅ Arbitrage executed successfully!")
        else:
            logger.error("❌ Failed to execute arbitrage")
            # Cancel any partial fills
            if yes_order:
                self.cancel_order(yes_order.id)
            if no_order:
                self.cancel_order(no_order.id)
        
        return yes_order or no_order


def get_polymarket_client_from_env() -> Optional[PolyMarketTradingClient]:
    """
    Create PolyMarket client from environment variables.
    
    Returns:
        Configured client or None if credentials missing
    """
    api_key = os.getenv("POLYMARKET_API_KEY")
    api_secret = os.getenv("POLYMARKET_API_SECRET")
    passphrase = os.getenv("POLYMARKET_PASSPHRASE")
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
    
    # Check if we have the minimum required credentials
    if not api_key or api_key == "your_polymarket_api_key_here":
        logger.info("PolyMarket API key not configured. Using read-only mode.")
        # Return client without trading
        return PolyMarketTradingClient()
    
    credentials = PolyMarketCredentials(
        api_key=api_key,
        api_secret=api_secret or "",
        passphrase=passphrase or "",
        private_key=private_key if private_key and private_key != "your_polymarket_polygon_private_key_here" else None
    )
    
    return PolyMarketTradingClient(credentials)


# Test function
if __name__ == "__main__":
    print("Testing PolyMarket Trading Client...")
    
    # Try to create client from env
    client = get_polymarket_client_from_env()
    
    print(f"\nTrading enabled: {client.is_trading_enabled()}")
    
    # Get markets
    print("\n📊 Fetching binary markets...")
    markets = client.get_binary_markets(min_liquidity=1000)
    print(f"Found {len(markets)} markets")
    
    # Show arbitrage opportunities
    print("\n🎯 Arbitrage Opportunities:")
    arbs = client.find_arbitrage_opportunities(min_spread=0.5)[:5]
    for arb in arbs:
        print(f"  {arb.question[:60]}...")
        print(f"    YES: ${arb.yes_price:.4f} | NO: ${arb.no_price:.4f}")
        print(f"    Combined: ${arb.combined_price:.4f} | Spread: {arb.arbitrage_percent:.2f}%")
        print()
    
    # If trading enabled, show balance
    if client.is_trading_enabled():
        print("\n💰 Balance:")
        balance = client.get_balance()
        print(f"  Cash: ${balance['cash']:.2f}")
        print(f"  Portfolio: ${balance['portfolio']:.2f}")
        print(f"  Total: ${balance['total']:.2f}")
