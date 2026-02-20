#!/usr/bin/env python3
"""
Live Trading Implementation for Execution Layer
===============================================
Actual exchange integration using CCXT for:
- Binance
- Coinbase
- Kraken
- Bybit
- KuCoin

Also supports Solana DEX via Jupiter.
"""

import os
import json
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# CCXT import with fallback
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("[LiveTrading] CCXT not available. Install: pip install ccxt")


@dataclass
class LiveExecutionResult:
    """Result of a live trade execution"""
    success: bool
    order_id: Optional[str]
    filled_price: Optional[float]
    filled_amount: Optional[float]
    fee: Optional[float]
    error: Optional[str]
    timestamp: str
    raw_response: Optional[Dict] = None


class CEXTrader:
    """Centralized Exchange Trading via CCXT"""
    
    EXCHANGE_MAP = {
        "binance": "binance",
        "coinbase": "coinbase",
        "kraken": "kraken",
        "bybit": "bybit",
        "kucoin": "kucoin",
    }
    
    def __init__(self):
        self.exchanges: Dict[str, Any] = {}
        self._init_exchanges()
    
    def _init_exchanges(self):
        """Initialize exchange connections from environment/config"""
        if not CCXT_AVAILABLE:
            return
        
        # Binance
        binance_key = os.getenv("BINANCE_API_KEY")
        binance_secret = os.getenv("BINANCE_SECRET")
        if binance_key and binance_secret:
            try:
                self.exchanges["binance"] = ccxt.binance({
                    "apiKey": binance_key,
                    "secret": binance_secret,
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"}
                })
                logger.info("[CEXTrader] Binance initialized")
            except Exception as e:
                logger.error(f"[CEXTrader] Binance init error: {e}")
        
        # Coinbase
        coinbase_key = os.getenv("COINBASE_API_KEY")
        coinbase_secret = os.getenv("COINBASE_SECRET")
        if coinbase_key and coinbase_secret:
            try:
                self.exchanges["coinbase"] = ccxt.coinbase({
                    "apiKey": coinbase_key,
                    "secret": coinbase_secret,
                    "enableRateLimit": True,
                })
                logger.info("[CEXTrader] Coinbase initialized")
            except Exception as e:
                logger.error(f"[CEXTrader] Coinbase init error: {e}")
        
        # Kraken
        kraken_key = os.getenv("KRAKEN_API_KEY")
        kraken_secret = os.getenv("KRAKEN_SECRET")
        if kraken_key and kraken_secret:
            try:
                self.exchanges["kraken"] = ccxt.kraken({
                    "apiKey": kraken_key,
                    "secret": kraken_secret,
                    "enableRateLimit": True,
                })
                logger.info("[CEXTrader] Kraken initialized")
            except Exception as e:
                logger.error(f"[CEXTrader] Kraken init error: {e}")
    
    def _normalize_symbol(self, symbol: str, exchange: str) -> str:
        """Normalize symbol for exchange"""
        # Convert BTC/USDT to exchange-specific format
        symbol = symbol.replace("-", "/").upper()
        return symbol
    
    def execute_market_buy(
        self,
        exchange: str,
        symbol: str,
        amount_usd: float,
        dry_run: bool = False
    ) -> LiveExecutionResult:
        """
        Execute a market buy order.
        
        Args:
            exchange: Exchange name (binance, coinbase, etc.)
            symbol: Trading pair (BTC/USDT)
            amount_usd: Amount in USD to spend
            dry_run: If True, don't actually execute
            
        Returns:
            Execution result
        """
        if not CCXT_AVAILABLE:
            return LiveExecutionResult(
                success=False,
                order_id=None,
                filled_price=None,
                filled_amount=None,
                fee=None,
                error="CCXT not available",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        ex = self.exchanges.get(exchange.lower())
        if not ex:
            return LiveExecutionResult(
                success=False,
                order_id=None,
                filled_price=None,
                filled_amount=None,
                fee=None,
                error=f"Exchange {exchange} not configured",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        symbol = self._normalize_symbol(symbol, exchange)
        
        if dry_run:
            return LiveExecutionResult(
                success=True,
                order_id="DRY_RUN",
                filled_price=None,
                filled_amount=amount_usd,
                fee=0,
                error=None,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        try:
            # Get current price to calculate amount
            ticker = ex.fetch_ticker(symbol)
            price = ticker["last"]
            amount = amount_usd / price
            
            # Execute market order
            order = ex.create_market_buy_order(symbol, amount)
            
            return LiveExecutionResult(
                success=True,
                order_id=order.get("id"),
                filled_price=order.get("average", order.get("price", price)),
                filled_amount=order.get("filled", amount),
                fee=order.get("fee", {}).get("cost") if order.get("fee") else None,
                error=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
                raw_response=order
            )
            
        except Exception as e:
            logger.error(f"[CEXTrader] Buy error: {e}")
            return LiveExecutionResult(
                success=False,
                order_id=None,
                filled_price=None,
                filled_amount=None,
                fee=None,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    def execute_market_sell(
        self,
        exchange: str,
        symbol: str,
        amount: float,
        dry_run: bool = False
    ) -> LiveExecutionResult:
        """Execute a market sell order"""
        if not CCXT_AVAILABLE:
            return LiveExecutionResult(
                success=False,
                order_id=None,
                filled_price=None,
                filled_amount=None,
                fee=None,
                error="CCXT not available",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        ex = self.exchanges.get(exchange.lower())
        if not ex:
            return LiveExecutionResult(
                success=False,
                order_id=None,
                filled_price=None,
                filled_amount=None,
                fee=None,
                error=f"Exchange {exchange} not configured",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        symbol = self._normalize_symbol(symbol, exchange)
        
        if dry_run:
            return LiveExecutionResult(
                success=True,
                order_id="DRY_RUN",
                filled_price=None,
                filled_amount=amount,
                fee=0,
                error=None,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        try:
            order = ex.create_market_sell_order(symbol, amount)
            
            return LiveExecutionResult(
                success=True,
                order_id=order.get("id"),
                filled_price=order.get("average", order.get("price")),
                filled_amount=order.get("filled", amount),
                fee=order.get("fee", {}).get("cost") if order.get("fee") else None,
                error=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
                raw_response=order
            )
            
        except Exception as e:
            logger.error(f"[CEXTrader] Sell error: {e}")
            return LiveExecutionResult(
                success=False,
                order_id=None,
                filled_price=None,
                filled_amount=None,
                fee=None,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    def get_balance(self, exchange: str, currency: str = "USDT") -> float:
        """Get balance for a currency on an exchange"""
        if not CCXT_AVAILABLE:
            return 0.0
        
        ex = self.exchanges.get(exchange.lower())
        if not ex:
            return 0.0
        
        try:
            balance = ex.fetch_balance()
            return balance.get(currency, {}).get("free", 0.0)
        except Exception as e:
            logger.error(f"[CEXTrader] Balance error: {e}")
            return 0.0


class DEXTrader:
    """Decentralized Exchange Trading (Solana via Jupiter)"""
    
    def __init__(self):
        self.wallet_loaded = os.path.exists("solana_wallet_live.json")
        self.private_key = os.getenv("SOLANA_PRIVATE_KEY")
    
    def execute_swap(
        self,
        input_token: str,
        output_token: str,
        amount: float,
        slippage_bps: int = 50,
        dry_run: bool = False
    ) -> LiveExecutionResult:
        """
        Execute a swap on Jupiter DEX.
        
        Args:
            input_token: Input token mint (or symbol)
            output_token: Output token mint (or symbol)
            amount: Amount to swap
            slippage_bps: Slippage tolerance in basis points
            dry_run: If True, don't actually execute
            
        Returns:
            Execution result
        """
        if not self.wallet_loaded or not self.private_key:
            return LiveExecutionResult(
                success=False,
                order_id=None,
                filled_price=None,
                filled_amount=None,
                fee=None,
                error="Solana wallet not configured",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        try:
            # Import here to avoid dependency issues
            from solana_dex import SolanaDEX
            
            dex = SolanaDEX(private_key=self.private_key)
            
            if dry_run:
                return LiveExecutionResult(
                    success=True,
                    order_id="DRY_RUN",
                    filled_price=None,
                    filled_amount=amount,
                    fee=0.001,  # ~0.1% Jupiter fee
                    error=None,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
            
            # Get quote
            quote = dex.get_quote(input_token, output_token, amount, slippage_bps)
            if not quote:
                return LiveExecutionResult(
                    success=False,
                    order_id=None,
                    filled_price=None,
                    filled_amount=None,
                    fee=None,
                    error="Could not get swap quote",
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
            
            # Execute swap
            tx_signature = dex.execute_swap(quote)
            
            if tx_signature:
                return LiveExecutionResult(
                    success=True,
                    order_id=tx_signature,
                    filled_price=None,
                    filled_amount=quote.out_amount if hasattr(quote, 'out_amount') else amount,
                    fee=0.0005,  # Solana fee
                    error=None,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
            else:
                return LiveExecutionResult(
                    success=False,
                    order_id=None,
                    filled_price=None,
                    filled_amount=None,
                    fee=None,
                    error="Swap execution failed",
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
                
        except Exception as e:
            logger.error(f"[DEXTrader] Swap error: {e}")
            return LiveExecutionResult(
                success=False,
                order_id=None,
                filled_price=None,
                filled_amount=None,
                fee=None,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )


class LiveTradingExecutor:
    """
    Main executor for live trading.
    Routes to CEX or DEX based on trade type.
    """
    
    def __init__(self):
        self.cex = CEXTrader()
        self.dex = DEXTrader()
        self.dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    
    def execute_cex_arbitrage(
        self,
        buy_exchange: str,
        sell_exchange: str,
        symbol: str,
        amount_usd: float,
        expected_profit: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a CEX arbitrage trade.
        
        Returns:
            (success, execution_details)
        """
        logger.info(f"[LiveTrading] Executing CEX arbitrage: {buy_exchange} -> {sell_exchange}")
        
        # Execute buy
        buy_result = self.cex.execute_market_buy(
            buy_exchange, symbol, amount_usd, dry_run=self.dry_run
        )
        
        if not buy_result.success:
            logger.error(f"[LiveTrading] Buy failed: {buy_result.error}")
            return False, {"error": f"Buy failed: {buy_result.error}"}
        
        # Calculate amount to sell
        amount_to_sell = buy_result.filled_amount or (amount_usd / buy_result.filled_price)
        
        # Execute sell
        sell_result = self.cex.execute_market_sell(
            sell_exchange, symbol, amount_to_sell, dry_run=self.dry_run
        )
        
        if not sell_result.success:
            logger.error(f"[LiveTrading] Sell failed: {sell_result.error}")
            return False, {"error": f"Sell failed: {sell_result.error}", "buy_order": buy_result}
        
        # Calculate actual profit
        buy_cost = amount_usd
        sell_revenue = sell_result.filled_amount * sell_result.filled_price
        actual_profit = sell_revenue - buy_cost
        
        return True, {
            "buy_order": buy_result,
            "sell_order": sell_result,
            "expected_profit": expected_profit,
            "actual_profit": actual_profit,
            "dry_run": self.dry_run
        }
    
    def execute_dex_swap(
        self,
        from_token: str,
        to_token: str,
        amount: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a DEX swap.
        
        Returns:
            (success, execution_details)
        """
        logger.info(f"[LiveTrading] Executing DEX swap: {from_token} -> {to_token}")
        
        result = self.dex.execute_swap(
            from_token, to_token, amount, dry_run=self.dry_run
        )
        
        return result.success, {
            "order": result,
            "dry_run": self.dry_run
        }
    
    def check_funding(self, exchange: str, min_balance: float = 10.0) -> bool:
        """Check if exchange has sufficient funding"""
        balance = self.cex.get_balance(exchange, "USDT")
        return balance >= min_balance


def get_live_executor() -> LiveTradingExecutor:
    """Get singleton live trading executor"""
    return LiveTradingExecutor()


if __name__ == "__main__":
    print("Live Trading Implementation - Test Mode")
    print("=" * 60)
    
    executor = get_live_executor()
    
    print(f"\nCEX Exchanges Configured: {list(executor.cex.exchanges.keys())}")
    print(f"DEX Wallet Loaded: {executor.dex.wallet_loaded}")
    print(f"Dry Run Mode: {executor.dry_run}")
    
    if executor.cex.exchanges:
        print("\nTesting balance check...")
        for ex in executor.cex.exchanges:
            balance = executor.cex.get_balance(ex)
            print(f"  {ex}: {balance} USDT")
    
    print("\nTo enable live trading:")
    print("  1. Set API keys as environment variables:")
    print("     BINANCE_API_KEY, BINANCE_SECRET")
    print("  2. Set SOLANA_PRIVATE_KEY for DEX trading")
    print("  3. Set DRY_RUN=false to execute real trades")
