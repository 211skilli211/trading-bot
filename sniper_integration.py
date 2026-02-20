#!/usr/bin/env python3
"""
DEXScreener Sniper Integration for Trading Bot
Add this to your trading_bot.py to enable sniping
"""

from dexscreener_connector import DexScreenerSniper, create_sniper_integration
from threading import Thread
import os


class SniperIntegration:
    """Helper class to integrate sniper into trading bot."""
    
    def __init__(self, execution_layer, alerts_module=None, birdeye_connector=None):
        """
        Initialize sniper integration.
        
        Args:
            execution_layer: Your ExecutionLayer instance
            alerts_module: Optional alerts/telegram module
            birdeye_connector: Optional Birdeye connector for holder checks
        """
        self.execution_layer = execution_layer
        self.alerts = alerts_module
        self.birdeye = birdeye_connector
        self.sniper = None
        self.sniper_thread = None
        self.is_running = False
    
    def start(
        self,
        min_liquidity: float = 8000,
        min_score: int = 78,
        dry_run: bool = True
    ):
        """
        Start the sniper in background thread.
        
        Args:
            min_liquidity: Minimum pool liquidity in USD
            min_score: Minimum opportunity score (0-100)
            dry_run: If True, only log without executing trades
        """
        print("\n" + "="*60)
        print("🔫 Starting DEXScreener Sniper Integration")
        print("="*60)
        
        # Create sniper with callback
        self.sniper, execute_callback = create_sniper_integration(
            execution_layer=self.execution_layer,
            alerts_module=self.alerts,
            birdeye_connector=self.birdeye,
            min_liquidity=min_liquidity,
            min_score=min_score,
            dry_run=dry_run
        )
        
        # Start in background thread
        self.sniper_thread = Thread(
            target=self.sniper.start_monitoring,
            args=(execute_callback,),
            daemon=True
        )
        self.sniper_thread.start()
        self.is_running = True
        
        print(f"✅ Sniper running in {'DRY RUN' if dry_run else 'LIVE'} mode")
        print(f"   Min Liquidity: ${min_liquidity:,.0f}")
        print(f"   Min Score: {min_score}/100")
        print("="*60 + "\n")
    
    def stop(self):
        """Stop the sniper."""
        if self.sniper:
            self.sniper.stop()
            self.is_running = False
            print("[SniperIntegration] Sniper stopped")
    
    def get_stats(self):
        """Get sniper statistics."""
        if self.sniper:
            return self.sniper.get_stats()
        return {"running": False}


# Example usage for trading_bot.py:
"""
# In your TradingBot class __init__ or start method:

from sniper_integration import SniperIntegration

class TradingBot:
    def __init__(self):
        # ... your existing init ...
        self.execution_layer = ExecutionLayer(mode=ExecutionMode.PAPER)
        self.sniper_integration = None
    
    def start_sniper(self, dry_run=True):
        '''Start DEXScreener sniper.'''
        self.sniper_integration = SniperIntegration(
            execution_layer=self.execution_layer,
            alerts_module=self.alerts,  # if you have one
            birdeye_connector=self.birdeye  # if you have one
        )
        self.sniper_integration.start(
            min_liquidity=8000,
            min_score=78,
            dry_run=dry_run
        )
    
    def stop_sniper(self):
        '''Stop DEXScreener sniper.'''
        if self.sniper_integration:
            self.sniper_integration.stop()


# Then in your main:
bot = TradingBot()
bot.start_sniper(dry_run=True)  # Start in dry-run first!
# Let it run for a while, check logs
# Then: bot.start_sniper(dry_run=False) for live trading
"""


if __name__ == "__main__":
    print("=" * 60)
    print("Sniper Integration Helper")
    print("=" * 60)
    print("\nThis module provides helper classes to integrate")
    print("the DEXScreener sniper into your trading bot.")
    print("\nUsage in trading_bot.py:")
    print("-" * 40)
    print("""
from sniper_integration import SniperIntegration

# In your bot class:
self.sniper = SniperIntegration(execution_layer, alerts)
self.sniper.start(dry_run=True)  # Test first
    """)
    print("-" * 40)
