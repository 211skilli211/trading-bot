#!/usr/bin/env python3
"""
Backtester Module
Test strategies on historical data before risking real money.

Features:
- Download historical OHLCV data via CCXT
- Replay strategy on past data
- Calculate Sharpe ratio, max drawdown, win rate
- Optimize parameters
"""

import json
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from decimal import Decimal

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    print("[Backtester] Warning: CCXT not installed")


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    max_consecutive_losses: int
    trades: List[Dict]


class Backtester:
    """
    Strategy backtesting engine.
    
    Usage:
        bt = Backtester('binance', 'BTC/USDT')
        data = bt.fetch_data(days=30)
        result = bt.run_strategy(data, fee_rate=0.001)
        bt.print_report(result)
    """
    
    def __init__(self, exchange_id: str = 'binance', symbol: str = 'BTC/USDT'):
        """
        Initialize backtester.
        
        Args:
            exchange_id: Exchange to fetch data from
            symbol: Trading pair
        """
        if not CCXT_AVAILABLE:
            raise RuntimeError("CCXT required for backtesting")
        
        self.exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True})
        self.symbol = symbol
        self.exchange_id = exchange_id
        
        print(f"[Backtester] Initialized: {exchange_id} {symbol}")
    
    def fetch_data(self, days: int = 30, timeframe: str = '1h') -> List[List]:
        """
        Fetch historical OHLCV data.
        
        Args:
            days: Number of days to fetch
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        
        Returns:
            List of [timestamp, open, high, low, close, volume]
        """
        print(f"[Backtester] Fetching {days} days of {timeframe} data...")
        
        since = self.exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
        
        all_data = []
        while since < self.exchange.milliseconds():
            try:
                data = self.exchange.fetch_ohlcv(self.symbol, timeframe, since, limit=1000)
                if not data:
                    break
                all_data.extend(data)
                since = data[-1][0] + 1
                print(f"  Fetched {len(data)} candles...")
            except Exception as e:
                print(f"  Error: {e}")
                break
        
        print(f"[Backtester] Total candles: {len(all_data)}")
        return all_data
    
    def run_arbitrage_backtest(
        self,
        data1: List[List],
        data2: List[List],
        fee_rate: float = 0.001,
        min_spread: float = 0.005,
        initial_balance: float = 10000.0
    ) -> BacktestResult:
        """
        Run arbitrage backtest between two datasets (simulating two exchanges).
        
        Args:
            data1: OHLCV from exchange 1
            data2: OHLCV from exchange 2
            fee_rate: Trading fee per side
            min_spread: Minimum spread to trade
            initial_balance: Starting capital
        
        Returns:
            BacktestResult with statistics
        """
        balance = initial_balance
        trades = []
        equity_curve = [balance]
        
        # Align data by timestamp
        min_len = min(len(data1), len(data2))
        
        for i in range(min_len):
            candle1 = data1[i]
            candle2 = data2[i]
            
            price1 = candle1[4]  # Close price
            price2 = candle2[4]
            timestamp = candle1[0]
            
            # Calculate spread
            spread = abs(price1 - price2) / min(price1, price2)
            
            # Check for trade opportunity
            threshold = (fee_rate * 2) + min_spread
            
            if spread > threshold:
                # Determine buy/sell
                if price1 < price2:
                    buy_price, sell_price = price1, price2
                    buy_ex, sell_ex = "Exchange1", "Exchange2"
                else:
                    buy_price, sell_price = price2, price1
                    buy_ex, sell_ex = "Exchange2", "Exchange1"
                
                # Calculate trade size (5% of balance)
                trade_size = balance * 0.05 / buy_price
                
                # Calculate P&L
                buy_cost = trade_size * buy_price * (1 + fee_rate)
                sell_revenue = trade_size * sell_price * (1 - fee_rate)
                profit = sell_revenue - (trade_size * buy_price)
                
                balance += profit
                
                trades.append({
                    'timestamp': timestamp,
                    'buy_exchange': buy_ex,
                    'sell_exchange': sell_ex,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'size': trade_size,
                    'spread': spread,
                    'profit': profit,
                    'balance': balance
                })
            
            equity_curve.append(balance)
        
        # Calculate statistics
        profits = [t['profit'] for t in trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]
        
        # Sharpe ratio (simplified)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(365 * 24)
        else:
            sharpe = 0.0
        
        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            max_dd = max(max_dd, dd)
        
        return BacktestResult(
            start_date=datetime.fromtimestamp(data1[0][0]/1000, timezone.utc).isoformat(),
            end_date=datetime.fromtimestamp(data1[-1][0]/1000, timezone.utc).isoformat(),
            initial_balance=initial_balance,
            final_balance=balance,
            total_return_pct=(balance - initial_balance) / initial_balance * 100,
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=len(wins) / len(trades) * 100 if trades else 0,
            avg_profit=np.mean(wins) if wins else 0,
            avg_loss=np.mean(losses) if losses else 0,
            profit_factor=abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd * 100,
            max_consecutive_losses=0,  # TODO: calculate
            trades=trades
        )
    
    def print_report(self, result: BacktestResult):
        """Print formatted backtest report."""
        print("\n" + "=" * 70)
        print("📊 BACKTEST REPORT")
        print("=" * 70)
        print(f"Period: {result.start_date[:10]} to {result.end_date[:10]}")
        print(f"Initial Balance: ${result.initial_balance:,.2f}")
        print(f"Final Balance: ${result.final_balance:,.2f}")
        print(f"Total Return: {result.total_return_pct:+.2f}%")
        print()
        print("Trade Statistics:")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Win Rate: {result.win_rate:.1f}%")
        print(f"  Winning: {result.winning_trades}")
        print(f"  Losing: {result.losing_trades}")
        print(f"  Avg Profit: ${result.avg_profit:,.2f}")
        print(f"  Avg Loss: ${result.avg_loss:,.2f}")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
        print()
        print("Risk Metrics:")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%")
        print("=" * 70)


if __name__ == "__main__":
    print("Backtester - Test Mode")
    print("=" * 70)
    
    if not CCXT_AVAILABLE:
        print("\n❌ CCXT not installed. Run: pip install ccxt")
        exit(1)
    
    # Create backtester
    bt = Backtester('binance', 'BTC/USDT')
    
    # Fetch data
    print("\n[1] Fetching historical data...")
    data = bt.fetch_data(days=7, timeframe='1h')
    
    if len(data) < 100:
        print("Not enough data for backtest")
        exit(1)
    
    # Split data to simulate two exchanges (with slight price differences)
    print("\n[2] Running arbitrage backtest...")
    
    # Simulate second exchange with 0.1% price offset
    data2 = [[c[0], c[1]*1.001, c[2]*1.001, c[3]*1.001, c[4]*1.001, c[5]] for c in data]
    
    result = bt.run_arbitrage_backtest(
        data1=data,
        data2=data2,
        fee_rate=0.001,
        min_spread=0.002,
        initial_balance=10000
    )
    
    # Print report
    bt.print_report(result)
    
    # Show sample trades
    if result.trades:
        print("\nSample Trades:")
        for t in result.trades[:3]:
            print(f"  {t['buy_exchange']} @ ${t['buy_price']:,.2f} -> "
                  f"{t['sell_exchange']} @ ${t['sell_price']:,.2f} = "
                  f"${t['profit']:+.2f}")
