#!/usr/bin/env python3
"""
Minervini SEA Strategy - Usage Examples
=======================================

This file demonstrates how to use the MinerviniSEAStrategy with:
1. Backtrader (backtesting framework)
2. VectorBT (vectorized backtesting)
3. Simple pandas loop (minimal dependencies)
4. Live trading integration with existing bot
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import logging

# Import the strategy
from minervini_sea import MinerviniSEAStrategy, SEASignal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# EXAMPLE 1: Simple Pandas Loop (Minimal Dependencies)
# =============================================================================

def example_pandas_loop():
    """
    Example using a simple pandas loop for backtesting.
    
    This is the most straightforward way to test the strategy
    with minimal dependencies.
    """
    print("=" * 70)
    print("EXAMPLE 1: Simple Pandas Loop Backtest")
    print("=" * 70)
    
    # Generate sample data (in real usage, load from yfinance or CSV)
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    np.random.seed(42)
    
    # Create a simulated stock with Stage 2 uptrend and VCP pattern
    price = 100
    prices = []
    for i in range(len(dates)):
        # Simulate Stage 2 uptrend with occasional consolidations
        if i < 100:
            # Stage 1 - basing
            change = np.random.normal(0.0005, 0.015)
        elif i < 200:
            # Stage 2 - strong uptrend
            change = np.random.normal(0.002, 0.02)
        elif i < 220:
            # VCP consolidation (tightening range)
            volatility = 0.02 - (i - 200) * 0.0005  # Decreasing volatility
            change = np.random.normal(0, volatility)
        else:
            # Breakout and continuation
            change = np.random.normal(0.003, 0.025)
        
        price *= (1 + change)
        prices.append(price)
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, len(dates))
    })
    df.set_index('date', inplace=True)
    
    # Create benchmark (simulated SPY)
    spy_prices = [100 * (1.0003 ** i) * (1 + np.random.normal(0, 0.008)) 
                  for i in range(len(dates))]
    spy_df = pd.DataFrame({
        'date': dates,
        'close': spy_prices,
        'open': spy_prices,
        'high': spy_prices,
        'low': spy_prices,
        'volume': np.random.randint(10000000, 50000000, len(dates))
    })
    spy_df.set_index('date', inplace=True)
    
    # Initialize strategy
    config = {
        "name": "SEA_Backtest",
        "account_size": 100000,
        "risk_per_trade": 1.0,
        "max_position_usd": 10000,
        "min_rs_rating": 70
    }
    
    strategy = MinerviniSEAStrategy(config)
    
    # Walk-forward analysis
    print("\nRunning walk-forward analysis...")
    print("-" * 70)
    
    for i in range(252, len(df)):
        # Get data up to current point
        current_data = df.iloc[:i]
        current_spy = spy_df.iloc[:i]
        
        # Create data dict
        data = {"TEST": current_data}
        
        # Scan for signals
        signals = strategy.scan(data, current_spy)
        
        # Execute signals
        for signal in signals:
            if signal.side == "buy":
                print(f"\n📅 {current_data.index[-1].strftime('%Y-%m-%d')}")
                print(f"🚀 BUY SIGNAL: {signal.symbol}")
                print(f"   Entry: ${signal.entry_price:.2f}")
                print(f"   Stop: ${signal.stop_loss:.2f} ({(signal.stop_loss/signal.entry_price-1)*100:.1f}%)")
                print(f"   Shares: {signal.position_size}")
                print(f"   Risk: ${signal.risk_per_share * signal.position_size:.2f}")
                print(f"   Confidence: {signal.confidence:.1%}")
                print(f"   Reason: {signal.reason}")
                
                strategy.execute(signal, mode="PAPER")
                
            elif signal.side == "sell":
                print(f"\n📅 {current_data.index[-1].strftime('%Y-%m-%d')}")
                print(f"🔴 SELL SIGNAL: {signal.symbol}")
                print(f"   Exit: ${signal.exit_price:.2f}")
                print(f"   Reason: {signal.reason}")
                
                strategy.execute(signal, mode="PAPER")
    
    # Print final stats
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)
    stats = strategy.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")


# =============================================================================
# EXAMPLE 2: Integration with Existing Trading Bot
# =============================================================================

class MinerviniSEAStrategyAdapter:
    """
    Adapter to integrate Minervini SEA with the existing trading bot architecture.
    
    This wraps the MinerviniSEAStrategy to conform to the BaseStrategy interface
    used by the trading bot.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.sea_strategy = MinerviniSEAStrategy(config)
        self.name = config.get("name", "Minervini_SEA")
    
    def scan(self, market_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Scan markets for signals (compatible with bot interface)
        
        Args:
            market_data: Dict of symbol -> DataFrame
            
        Returns:
            List of signal dictionaries
        """
        # Get benchmark (SPY) if available
        benchmark = market_data.get("SPY")
        
        # Run SEA strategy scan
        signals = self.sea_strategy.scan(market_data, benchmark)
        
        # Convert to bot-compatible format
        bot_signals = []
        for signal in signals:
            bot_signals.append({
                "timestamp": signal.timestamp,
                "symbol": signal.symbol,
                "side": signal.side,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "metadata": signal.metadata
            })
        
        return bot_signals
    
    def execute(self, signal: Dict, mode: str = "PAPER") -> Dict:
        """Execute a signal"""
        # Convert dict back to SEASignal
        sea_signal = SEASignal(**signal)
        
        # Execute via SEA strategy
        trade = self.sea_strategy.execute(sea_signal, mode)
        
        if trade:
            return {
                "trade_id": trade.trade_id,
                "status": "EXECUTED",
                "symbol": trade.symbol,
                "side": trade.side,
                "shares": trade.shares,
                "entry_price": trade.entry_price,
                "stop_loss": trade.stop_loss
            }
        return {"status": "FAILED"}
    
    def get_stats(self) -> Dict:
        """Get strategy statistics"""
        return self.sea_strategy.get_stats()


def example_bot_integration():
    """Example of integrating with the existing bot"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Bot Integration")
    print("=" * 70)
    
    config = {
        "name": "Minervini_SEA",
        "enabled": True,
        "account_size": 100000,
        "risk_per_trade": 1.0,
        "max_position_usd": 10000,
        "scan_interval_seconds": 300  # 5 minutes
    }
    
    adapter = MinerviniSEAStrategyAdapter(config)
    
    print(f"\nStrategy '{adapter.name}' initialized")
    print(f"Adapter ready for bot integration")
    print(f"\nTo add to bot:")
    print(f"  1. Import: from strategies.minervini_sea import MinerviniSEAStrategyAdapter")
    print(f"  2. Create: strategy = MinerviniSEAStrategyAdapter(config)")
    print(f"  3. Add to: trading_bot.py strategy registry")


# =============================================================================
# EXAMPLE 3: Using with Real Data (yfinance)
# =============================================================================

def example_with_yfinance():
    """Example using real market data from yfinance"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Real Data with yfinance")
    print("=" * 70)
    
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Install with: pip install yfinance")
        return
    
    # Download data
    print("\nDownloading data...")
    symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "META"]
    spy = yf.download("SPY", period="2y", interval="1d", progress=False)
    
    data = {}
    for symbol in symbols:
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if not df.empty:
            # Flatten column names if multi-index
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            # Rename to lowercase
            df.columns = [c.lower() for c in df.columns]
            data[symbol] = df
            print(f"  {symbol}: {len(df)} bars")
    
    # Prepare SPY
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)
    spy.columns = [c.lower() for c in spy.columns]
    
    # Initialize strategy
    config = {
        "name": "SEA_RealData",
        "account_size": 100000,
        "risk_per_trade": 1.0,
        "max_position_usd": 10000,
        "min_rs_rating": 70
    }
    
    strategy = MinerviniSEAStrategy(config)
    
    # Scan
    print("\nScanning for setups...")
    print("-" * 70)
    
    signals = strategy.scan(data, spy)
    
    if signals:
        print(f"\nFound {len(signals)} signals:")
        for signal in signals:
            print(f"\n🎯 {signal.symbol}")
            print(f"   Side: {signal.side.upper()}")
            print(f"   Entry: ${signal.entry_price:.2f}")
            print(f"   Stop: ${signal.stop_loss:.2f}")
            print(f"   Confidence: {signal.confidence:.1%}")
            if signal.trend_template:
                print(f"   RS Rating: {signal.trend_template.rs_rating:.0f}")
    else:
        print("\nNo signals found in current data.")
        print("This is normal - Minervini's criteria are strict and valid setups are rare.")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    # Run examples
    print("\n" + "=" * 70)
    print("MINERVINI SEA STRATEGY - USAGE EXAMPLES")
    print("=" * 70)
    
    # Example 1: Simple pandas loop
    example_pandas_loop()
    
    # Example 2: Bot integration
    example_bot_integration()
    
    # Example 3: Real data (optional - requires yfinance)
    try:
        example_with_yfinance()
    except Exception as e:
        print(f"\nReal data example skipped: {e}")
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
