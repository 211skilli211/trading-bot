#!/usr/bin/env python3
"""
Crypto Price Fetcher - Data Layer + Strategy Engine
Fetches BTC/USDT prices from Binance and Coinbase APIs.
Integrated with Strategy Engine for arbitrage decisions.
Part of the modular trading bot blueprint.
"""

import requests
import json
import time
import sys
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from strategy_engine import StrategyEngine, ArbitrageStrategy
    STRATEGY_ENGINE_AVAILABLE = True
except ImportError:
    STRATEGY_ENGINE_AVAILABLE = False
    print("Warning: StrategyEngine not available. Run in data-only mode.")

try:
    from risk_manager import RiskManager, RiskCheck
    RISK_MANAGER_AVAILABLE = True
except ImportError:
    RISK_MANAGER_AVAILABLE = False
    print("Warning: RiskManager not available. Trades will not be risk-checked.")


class ExchangeConnector:
    """Base class for exchange connectors."""
    
    def __init__(self, name: str):
        self.name = name
    
    def fetch_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch price for a symbol. Returns normalized data or None on error."""
        raise NotImplementedError


class BinanceConnector(ExchangeConnector):
    """Binance API connector."""
    
    API_BASE = "https://api.binance.com"
    
    def __init__(self):
        super().__init__("Binance")
    
    def fetch_price(self, symbol: str = "BTCUSDT") -> Optional[Dict[str, Any]]:
        """
        Fetch ticker price from Binance.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
        
        Returns:
            Normalized price data or None if request fails
        """
        try:
            endpoint = f"{self.API_BASE}/api/v3/ticker/24hr"
            params = {"symbol": symbol}
            
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                "exchange": self.name,
                "symbol": symbol,
                "price": float(data["lastPrice"]),
                "bid": float(data["bidPrice"]),
                "ask": float(data["askPrice"]),
                "volume_24h": float(data["volume"]),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "raw_response": data
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[Binance] Error fetching price: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"[Binance] Error parsing response: {e}")
            return None


class CoinbaseConnector(ExchangeConnector):
    """Coinbase API connector."""
    
    API_BASE = "https://api.exchange.coinbase.com"
    
    def __init__(self):
        super().__init__("Coinbase")
    
    def fetch_price(self, symbol: str = "BTC-USD") -> Optional[Dict[str, Any]]:
        """
        Fetch ticker price from Coinbase.
        
        Args:
            symbol: Trading pair (e.g., "BTC-USD")
        
        Returns:
            Normalized price data or None if request fails
        """
        try:
            # Coinbase uses different symbol format
            cb_symbol = symbol.replace("USDT", "-USD").replace("USDC", "-USD")
            
            endpoint = f"{self.API_BASE}/products/{cb_symbol}/ticker"
            
            response = requests.get(endpoint, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                "exchange": self.name,
                "symbol": cb_symbol,
                "price": float(data["price"]),
                "bid": float(data["bid"]),
                "ask": float(data["ask"]),
                "volume_24h": float(data["volume"]),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "raw_response": data
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[Coinbase] Error fetching price: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"[Coinbase] Error parsing response: {e}")
            return None


class SpreadCalculator:
    """Calculate price spreads between exchanges."""
    
    @staticmethod
    def calculate_spread(price1: Dict[str, Any], price2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate spread between two prices.
        
        Args:
            price1: Price data from exchange 1
            price2: Price data from exchange 2
        
        Returns:
            Spread analysis data
        """
        if not price1 or not price2:
            return {"error": "Missing price data"}
        
        p1 = price1["price"]
        p2 = price2["price"]
        
        # Calculate absolute and percentage spread
        spread_abs = abs(p1 - p2)
        spread_pct = (spread_abs / min(p1, p2)) * 100
        
        # Determine which exchange has higher price
        higher_exchange = price1["exchange"] if p1 > p2 else price2["exchange"]
        lower_exchange = price2["exchange"] if p1 > p2 else price1["exchange"]
        higher_price = max(p1, p2)
        lower_price = min(p1, p2)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "spread_absolute": round(spread_abs, 2),
            "spread_percentage": round(spread_pct, 4),
            "higher_exchange": higher_exchange,
            "higher_price": higher_price,
            "lower_exchange": lower_exchange,
            "lower_price": lower_price,
            "threshold_met": spread_pct > 0.5  # 0.5% threshold
        }


class AuditLogger:
    """Log all price data and decisions for transparency."""
    
    def __init__(self, log_file: str = "trading_bot.log"):
        self.log_file = log_file
    
    def log(self, data: Dict[str, Any], log_type: str = "INFO"):
        """Log data to file with timestamp."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "type": log_type,
            "data": data
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def log_price_data(self, prices: list, spread: Dict[str, Any]):
        """Log price comparison data."""
        self.log({
            "prices": prices,
            "spread_analysis": spread
        }, "PRICE_CHECK")


def fetch_prices(use_strategy: bool = True) -> Optional[Dict[str, Any]]:
    """
    Main function to fetch and display prices from both exchanges.
    
    Args:
        use_strategy: If True, run strategy engine analysis
    
    Returns:
        Analysis results if strategy is used, None otherwise
    """
    
    print("=" * 60)
    print("Crypto Price Fetcher - Data Layer + Strategy Engine")
    print("Fetching BTC/USDT prices from Binance and Coinbase")
    print("=" * 60)
    print()
    
    # Initialize connectors
    binance = BinanceConnector()
    coinbase = CoinbaseConnector()
    logger = AuditLogger("price_log.jsonl")
    
    # Initialize strategy engine if available
    strategy_result = None
    if use_strategy and STRATEGY_ENGINE_AVAILABLE:
        strategy = ArbitrageStrategy(config={
            'fee_rate': 0.001,      # 0.1% trading fee
            'slippage': 0.0005,      # 0.05% slippage estimate
            'min_spread': 0.002,     # 0.2% minimum spread
            'paper_trading': True    # Safety: paper trading only
        })
        print("[StrategyEngine] Arbitrage logic enabled (PAPER TRADING MODE)")
        print()
    
    # Fetch prices
    print("[1] Fetching from Binance...")
    binance_data = binance.fetch_price("BTCUSDT")
    
    print("[2] Fetching from Coinbase...")
    coinbase_data = coinbase.fetch_price("BTC-USD")
    
    print()
    
    # Display results
    prices: List[Dict[str, Any]] = []
    
    if binance_data:
        print(f"✓ Binance BTC/USDT:")
        print(f"  Price: ${binance_data['price']:,.2f}")
        print(f"  Bid:   ${binance_data['bid']:,.2f}")
        print(f"  Ask:   ${binance_data['ask']:,.2f}")
        print(f"  24h Volume: {binance_data['volume_24h']:,.4f} BTC")
        prices.append(binance_data)
    else:
        print("✗ Failed to fetch from Binance")
    
    print()
    
    if coinbase_data:
        print(f"✓ Coinbase BTC/USD:")
        print(f"  Price: ${coinbase_data['price']:,.2f}")
        print(f"  Bid:   ${coinbase_data['bid']:,.2f}")
        print(f"  Ask:   ${coinbase_data['ask']:,.2f}")
        print(f"  24h Volume: {coinbase_data['volume_24h']:,.4f} BTC")
        prices.append(coinbase_data)
    else:
        print("✗ Failed to fetch from Coinbase")
    
    print()
    print("-" * 60)
    
    # Calculate and display spread
    if len(prices) == 2:
        spread = SpreadCalculator.calculate_spread(binance_data, coinbase_data)
        
        print("Spread Analysis:")
        print(f"  Absolute Spread: ${spread['spread_absolute']:,.2f}")
        print(f"  Percentage Spread: {spread['spread_percentage']:.4f}%")
        print(f"  Higher Price: {spread['higher_exchange']} at ${spread['higher_price']:,.2f}")
        print(f"  Lower Price:  {spread['lower_exchange']} at ${spread['lower_price']:,.2f}")
        print()
        
        # Strategy Engine Analysis
        if use_strategy and STRATEGY_ENGINE_AVAILABLE:
            print("📊 STRATEGY ENGINE ANALYSIS")
            print("-" * 40)
            
            strategy_result = strategy.analyze(prices)
            signal = strategy_result['signal']
            
            # Display signal
            decision_icon = "🟢" if signal['decision'] == "TRADE" else "🔴"
            print(f"\n{decision_icon} Strategy: {signal['decision']}")
            print(f"   Reason: {signal['reason']}")
            print(f"   Confidence: {signal['confidence']}")
            print(f"   Spread: {signal['spread_pct']:.4%}")
            print(f"   Threshold: {signal['threshold_pct']:.4%}")
            
            if signal['expected_profit_pct']:
                print(f"   Expected Profit: {signal['expected_profit_pct']:.4%}")
            
            # Display paper portfolio summary
            portfolio = strategy_result['paper_portfolio']
            if portfolio['total_trades'] > 0:
                print(f"\n📈 Paper Portfolio:")
                print(f"   Total Trades: {portfolio['total_trades']}")
                print(f"   Expected P&L: ${portfolio['total_expected_profit']:,.2f}")
            
            # Risk Management Check
            if RISK_MANAGER_AVAILABLE and signal['decision'] == "TRADE":
                print("\n🛡️  RISK MANAGEMENT CHECK")
                print("-" * 40)
                
                # Initialize risk manager if not exists (using default config)
                if not hasattr(fetch_prices, 'risk_manager'):
                    fetch_prices.risk_manager = RiskManager(
                        max_position_btc=0.05,
                        stop_loss_pct=0.02,
                        capital_pct_per_trade=0.05,
                        initial_balance=10000.0
                    )
                
                rm = fetch_prices.risk_manager
                
                # Check stop-losses on existing positions first
                current_prices = {
                    p['exchange']: p['price'] for p in prices
                }
                closed_positions = rm.check_stop_losses(current_prices)
                
                # Assess new trade
                risk_check = rm.assess_trade(signal, signal['buy_price'])
                
                risk_icon = "🟢" if risk_check.decision in ["APPROVE", "MODIFY"] else "🔴"
                print(f"\n{risk_icon} Risk Decision: {risk_check.decision}")
                print(f"   Reason: {risk_check.reason}")
                print(f"   Allocation: ${risk_check.allocation_usd:,.2f}")
                print(f"   Position Size: {risk_check.position_size_btc:.4f} BTC")
                print(f"   Stop-Loss: ${risk_check.stop_loss_price:,.2f}" if risk_check.stop_loss_price else "")
                print(f"   Risk Level: {risk_check.risk_level}")
                print(f"   Current Exposure: ${risk_check.current_exposure:,.2f}")
                
                # Log risk decision
                logger.log({
                    "signal": signal,
                    "risk_check": risk_check.__dict__ if hasattr(risk_check, '__dict__') else risk_check
                }, "RISK_DECISION")
                
                # Show closed positions from stop-loss
                if closed_positions:
                    print(f"\n🚨 Stop-Loss Triggered: {len(closed_positions)} position(s) closed")
            
            # Log strategy decision
            logger.log(strategy_result, "STRATEGY_DECISION")
            
        elif spread['threshold_met']:
            print(f"⚠️  THRESHOLD MET: Spread > 0.5% ({spread['spread_percentage']:.4f}%)")
            print("   Potential arbitrage opportunity detected!")
        else:
            print(f"ℹ️  Threshold not met (need > 0.5%, got {spread['spread_percentage']:.4f}%)")
        
        # Log the data
        logger.log_price_data(prices, spread)
        print()
        print(f"✓ Data logged to price_log.jsonl")
    else:
        print("⚠️  Cannot calculate spread - missing data from one or more exchanges")
    
    print("-" * 60)
    
    return strategy_result


def continuous_monitoring(interval: int = 30, use_strategy: bool = True):
    """
    Continuously monitor prices at specified interval.
    
    Args:
        interval: Seconds between checks (default: 30)
        use_strategy: If True, use strategy engine
    """
    print("Starting continuous monitoring...")
    print(f"Checking every {interval} seconds. Press Ctrl+C to stop.\n")
    
    # Initialize risk manager for monitoring session
    if use_strategy and RISK_MANAGER_AVAILABLE:
        fetch_prices.risk_manager = RiskManager(
            max_position_btc=0.05,
            stop_loss_pct=0.02,
            capital_pct_per_trade=0.05,
            initial_balance=10000.0
        )
    
    try:
        while True:
            fetch_prices(use_strategy=use_strategy)
            
            print(f"\nNext check in {interval} seconds...\n")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        
        # Print final summaries
        if use_strategy and STRATEGY_ENGINE_AVAILABLE:
            print("\n" + "=" * 60)
            print("FINAL PAPER TRADING SUMMARY")
            print("=" * 60)
        
        if RISK_MANAGER_AVAILABLE and hasattr(fetch_prices, 'risk_manager'):
            fetch_prices.risk_manager.print_summary()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Price Fetcher with Strategy Engine')
    parser.add_argument('--monitor', type=int, metavar='SECONDS',
                        help='Enable continuous monitoring with specified interval')
    parser.add_argument('--no-strategy', action='store_true',
                        help='Disable strategy engine (data only)')
    parser.add_argument('--test-strategy', action='store_true',
                        help='Test strategy engine standalone')
    
    args = parser.parse_args()
    
    if args.test_strategy:
        # Run strategy engine tests
        print("Running Strategy Engine tests...")
        os.system(f"python {os.path.join(os.path.dirname(__file__), 'strategy_engine.py')}")
    elif args.monitor:
        # Continuous monitoring mode
        continuous_monitoring(args.monitor, use_strategy=not args.no_strategy)
    else:
        # Single fetch mode
        fetch_prices(use_strategy=not args.no_strategy)
        print("\nTips:")
        print("  --monitor [seconds]  Continuous monitoring")
        print("  --no-strategy        Data only, no strategy")
        print("  --test-strategy      Run strategy engine tests")
        print("\nExample: python crypto_price_fetcher.py --monitor 60")
