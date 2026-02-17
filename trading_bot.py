#!/usr/bin/env python3
"""
Trading Bot - Complete End-to-End Orchestrator
===============================================

A modular, ethical trading bot that implements:
1. Data Layer       - Fetch prices from exchanges
2. Strategy Engine  - Arbitrage logic and signal generation
3. Risk Manager     - Position limits and stop-loss rules
4. Execution Layer  - Paper/live trade execution

Usage:
    python trading_bot.py --mode paper              # Single run, paper mode
    python trading_bot.py --mode paper --monitor 60 # Continuous monitoring
    python trading_bot.py --mode live               # Live trading (requires API keys)
    python trading_bot.py --test                    # Run all module tests

Configuration:
    Create a .env file with your API keys for live trading:
    BINANCE_API_KEY=your_key
    BINANCE_SECRET=your_secret
    COINBASE_API_KEY=your_key
    COINBASE_SECRET=your_secret
"""

import argparse
import json
import time
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Import our modules
try:
    from crypto_price_fetcher import BinanceConnector, CoinbaseConnector, AuditLogger
    DATA_LAYER_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Data Layer: {e}")
    DATA_LAYER_AVAILABLE = False

try:
    from strategy_engine import ArbitrageStrategy
    STRATEGY_LAYER_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Strategy Engine: {e}")
    STRATEGY_LAYER_AVAILABLE = False

try:
    from risk_manager import RiskManager
    RISK_LAYER_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Risk Manager: {e}")
    RISK_LAYER_AVAILABLE = False

try:
    from execution_layer import ExecutionLayer, ExecutionMode
    EXECUTION_LAYER_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Execution Layer: {e}")
    EXECUTION_LAYER_AVAILABLE = False

# Optional modules
try:
    from exchange_connectors import MultiExchangeConnector
    MULTI_EXCHANGE_AVAILABLE = True
except ImportError:
    MULTI_EXCHANGE_AVAILABLE = False

try:
    from alerts import AlertManager
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False

try:
    import dashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False


class TradingBot:
    """
    Complete Trading Bot Orchestrator.
    
    Coordinates all four layers:
    - Fetches market data
    - Generates trade signals
    - Validates risk limits
    - Executes trades
    - Logs everything for audit
    """
    
    def __init__(
        self,
        mode: str = "paper",
        log_file: str = "trading_bot.log",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Trading Bot.
        
        Args:
            mode: 'paper' or 'live' trading mode
            log_file: Path to log file
            config: Custom configuration dictionary
        """
        print("=" * 70)
        print("🤖 TRADING BOT - End-to-End Orchestrator")
        print("=" * 70)
        
        self.mode = mode
        self.log_file = log_file
        self.config = config or {}
        
        # Initialize logger
        self.logger = AuditLogger(log_file)
        
        # Initialize layers
        self._init_layers()
        
        # Statistics
        self.run_count = 0
        self.start_time = datetime.now(timezone.utc)
        
        print(f"\n📊 Configuration:")
        print(f"   Mode: {mode.upper()}")
        print(f"   Log File: {log_file}")
        print(f"   Start Time: {self.start_time.isoformat()}")
    
    def _init_layers(self):
        """Initialize all trading layers."""
        
        # Data Layer
        if DATA_LAYER_AVAILABLE:
            self.binance = BinanceConnector()
            self.coinbase = CoinbaseConnector()
            print("✅ Data Layer initialized")
            
            # Additional exchanges
            if MULTI_EXCHANGE_AVAILABLE:
                exchange_config = self.config.get('exchanges', {})
                self.multi_exchange = MultiExchangeConnector({
                    "exchanges": exchange_config
                })
                print("✅ Multi-Exchange connectors initialized")
            else:
                self.multi_exchange = None
        else:
            raise RuntimeError("Data Layer not available")
        
        # Strategy Layer
        if STRATEGY_LAYER_AVAILABLE:
            strategy_config = self.config.get('strategy', {})
            self.strategy = ArbitrageStrategy(config={
                'fee_rate': strategy_config.get('fee_rate', 0.001),
                'slippage': strategy_config.get('slippage', 0.0005),
                'min_spread': strategy_config.get('min_spread', 0.002),
                'paper_trading': True  # Always true in strategy layer
            })
            print("✅ Strategy Engine initialized")
        else:
            raise RuntimeError("Strategy Engine not available")
        
        # Risk Layer
        if RISK_LAYER_AVAILABLE:
            risk_config = self.config.get('risk', {})
            self.risk_manager = RiskManager(
                max_position_btc=risk_config.get('max_position_btc', 0.05),
                stop_loss_pct=risk_config.get('stop_loss_pct', 0.02),
                take_profit_pct=risk_config.get('take_profit_pct'),
                capital_pct_per_trade=risk_config.get('capital_pct_per_trade', 0.05),
                max_total_exposure_pct=risk_config.get('max_total_exposure_pct', 0.30),
                initial_balance=risk_config.get('initial_balance', 10000.0),
                daily_loss_limit_pct=risk_config.get('daily_loss_limit_pct', 0.05)
            )
            print("✅ Risk Manager initialized")
        else:
            raise RuntimeError("Risk Manager not available")
        
        # Execution Layer
        if EXECUTION_LAYER_AVAILABLE:
            execution_mode = ExecutionMode.PAPER if self.mode == "paper" else ExecutionMode.LIVE
            exec_config = self.config.get('execution', {})
            
            # Load API keys from environment for live mode
            binance_key = os.getenv('BINANCE_API_KEY')
            binance_secret = os.getenv('BINANCE_SECRET')
            coinbase_key = os.getenv('COINBASE_API_KEY')
            coinbase_secret = os.getenv('COINBASE_SECRET')
            
            self.executor = ExecutionLayer(
                mode=execution_mode,
                max_retries=exec_config.get('max_retries', 3),
                retry_delay=exec_config.get('retry_delay', 1.0),
                binance_api_key=binance_key,
                binance_secret=binance_secret,
                coinbase_api_key=coinbase_key,
                coinbase_secret=coinbase_secret
            )
            print("✅ Execution Layer initialized")
        else:
            raise RuntimeError("Execution Layer not available")
        
        # Alert Manager (optional)
        if ALERTS_AVAILABLE:
            alert_config = self.config.get('alerts', {})
            self.alerts = AlertManager(alert_config)
            print("✅ Alert Manager initialized")
        else:
            self.alerts = None
        
        print()
    
    def run_once(self) -> Dict[str, Any]:
        """
        Execute one complete trading cycle.
        
        Returns:
            Complete execution record
        """
        self.run_count += 1
        cycle_start = time.time()
        
        print(f"\n{'='*70}")
        print(f"🔄 TRADING CYCLE #{self.run_count}")
        print(f"{'='*70}")
        
        result = {
            "cycle": self.run_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": self.mode,
            "status": "INITIATED"
        }
        
        # =====================================================================
        # STEP 1: DATA LAYER - Fetch Prices
        # =====================================================================
        print("\n📡 STEP 1: Fetching Market Data...")
        
        prices = []
        
        binance_data = self.binance.fetch_price("BTCUSDT")
        if binance_data:
            print(f"   ✓ Binance: ${binance_data['price']:,.2f}")
            prices.append(binance_data)
        else:
            print(f"   ✗ Binance: Failed")
        
        coinbase_data = self.coinbase.fetch_price("BTC-USD")
        if coinbase_data:
            print(f"   ✓ Coinbase: ${coinbase_data['price']:,.2f}")
            prices.append(coinbase_data)
        else:
            print(f"   ✗ Coinbase: Failed")
        
        # Fetch from additional exchanges if available
        if self.multi_exchange:
            additional_prices = self.multi_exchange.fetch_all_prices()
            for price_data in additional_prices:
                print(f"   ✓ {price_data['exchange']}: ${price_data['price']:,.2f}")
                prices.append(price_data)
        
        if len(prices) < 2:
            result["status"] = "FAILED"
            result["error"] = "Could not fetch prices from enough exchanges"
            print(f"\n❌ ERROR: {result['error']}")
            
            # Send error alert
            if self.alerts:
                self.alerts.send_error_alert(f"Price fetch failed: {result['error']}")
            
            return result
        
        result["prices"] = prices
        
        # =====================================================================
        # STEP 2: STRATEGY ENGINE - Generate Signal
        # =====================================================================
        print("\n🧠 STEP 2: Strategy Engine Analysis...")
        
        strategy_start = time.time()
        strategy_result = self.strategy.analyze(prices)
        signal = strategy_result['signal']
        
        print(f"   Decision: {signal['decision']}")
        print(f"   Reason: {signal['reason']}")
        print(f"   Spread: {signal['spread_pct']:.4%}")
        
        result["strategy"] = strategy_result
        
        # =====================================================================
        # STEP 3: RISK MANAGEMENT - Validate Trade
        # =====================================================================
        print("\n🛡️  STEP 3: Risk Management Check...")
        
        # Check stop-losses on existing positions first
        current_prices = {p['exchange']: p['price'] for p in prices}
        closed_positions = self.risk_manager.check_stop_losses(current_prices)
        
        if closed_positions:
            print(f"   🚨 {len(closed_positions)} position(s) closed by stop-loss")
        
        # Assess new trade
        if signal['decision'] == "TRADE":
            buy_price = signal.get('buy_price', 0)
            risk_check = self.risk_manager.assess_trade(signal, buy_price)
            
            print(f"   Decision: {risk_check.decision}")
            print(f"   Reason: {risk_check.reason}")
            print(f"   Position Size: {risk_check.position_size_btc:.4f} BTC")
            print(f"   Risk Level: {risk_check.risk_level}")
            
            result["risk"] = risk_check.__dict__ if hasattr(risk_check, '__dict__') else risk_check
        else:
            print("   ⏭️  Skipped (no trade signal)")
            result["risk"] = {"decision": "HOLD", "reason": "No trade signal"}
        
        # =====================================================================
        # STEP 4: EXECUTION LAYER - Execute Trade
        # =====================================================================
        print("\n🚀 STEP 4: Execution Layer...")
        
        if signal['decision'] == "TRADE":
            risk_data = result["risk"]
            execution = self.executor.execute_trade(
                strategy_signal=signal,
                risk_result=risk_data,
                signal_timestamp=strategy_start
            )
            
            print(f"   Status: {execution.status}")
            print(f"   Mode: {execution.mode}")
            
            if execution.net_pnl is not None:
                print(f"   Net P&L: ${execution.net_pnl:,.2f}")
            
            print(f"   Latency: {execution.total_latency_ms:.1f}ms")
            
            result["execution"] = execution.__dict__ if hasattr(execution, '__dict__') else execution
            result["status"] = execution.status
        else:
            print("   ⏭️  Skipped (no trade signal)")
            result["execution"] = None
            result["status"] = "NO_TRADE"
        
        # =====================================================================
        # STEP 5: ALERTS - Send notifications
        # =====================================================================
        if self.alerts:
            alert_config = self.config.get('alerts', {})
            
            # Trade alert
            if alert_config.get('on_trade', True) and result.get('execution'):
                self.alerts.send_trade_alert(result['execution'])
            
            # Stop-loss alert
            if alert_config.get('on_stop_loss', True) and closed_positions:
                for pos in closed_positions:
                    self.alerts.send_stop_loss_alert(pos.__dict__ if hasattr(pos, '__dict__') else pos)
            
            # Daily limit alert
            risk_summary = self.risk_manager.get_portfolio_summary()
            if alert_config.get('on_daily_limit', True) and risk_summary.get('trading_halted'):
                self.alerts.send_daily_limit_alert(
                    risk_summary['daily_pnl'],
                    self.config.get('risk', {}).get('daily_loss_limit_pct', 0.05)
                )
        
        # =====================================================================
        # STEP 6: DASHBOARD - Update real-time view
        # =====================================================================
        if DASHBOARD_AVAILABLE:
            try:
                dashboard.update_dashboard(
                    prices=result.get('prices', []),
                    trades=[e.__dict__ if hasattr(e, '__dict__') else e for e in self.executor.executions[-10:]],
                    positions=[p.__dict__ if hasattr(p, '__dict__') else p for p in self.risk_manager.positions if p.status == "OPEN"],
                    stats={
                        "total_cycles": self.run_count,
                        "successful_trades": self.executor.successful_executions,
                        "total_pnl": sum(e.net_pnl or 0 for e in self.executor.executions),
                        "daily_pnl": risk_summary.get('daily_pnl', 0),
                        "avg_latency": self.executor.avg_latency_ms
                    }
                )
            except Exception as e:
                print(f"   Dashboard update error: {e}")
        
        # =====================================================================
        # STEP 7: LOGGING - Audit Trail
        # =====================================================================
        cycle_end = time.time()
        result["cycle_time_ms"] = round((cycle_end - cycle_start) * 1000, 2)
        
        self.logger.log(result, "TRADE_CYCLE")
        
        print(f"\n📝 Cycle logged to {self.log_file}")
        print(f"⏱️  Total Cycle Time: {result['cycle_time_ms']:.1f}ms")
        print(f"{'='*70}")
        
        return result
    
    def run_monitor(self, interval: int = 60):
        """
        Run continuous monitoring.
        
        Args:
            interval: Seconds between cycles
        """
        print(f"\n🔁 Starting continuous monitoring...")
        print(f"   Interval: {interval} seconds")
        print(f"   Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.run_once()
                
                print(f"\n⏳ Sleeping for {interval} seconds...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            self.print_summary()
    
    def print_summary(self):
        """Print complete trading session summary."""
        print("\n" + "=" * 70)
        print("📊 TRADING SESSION SUMMARY")
        print("=" * 70)
        
        duration = datetime.now(timezone.utc) - self.start_time
        
        print(f"\nSession Info:")
        print(f"   Mode: {self.mode.upper()}")
        print(f"   Cycles Run: {self.run_count}")
        print(f"   Duration: {duration}")
        print(f"   Start Time: {self.start_time.isoformat()}")
        
        # Strategy Summary
        if STRATEGY_LAYER_AVAILABLE:
            portfolio = self.strategy.engine.get_paper_portfolio_summary()
            print(f"\nStrategy Engine:")
            print(f"   Paper Trades: {portfolio['total_trades']}")
            print(f"   Expected P&L: ${portfolio['total_expected_profit']:,.2f}")
        
        # Risk Summary
        if RISK_LAYER_AVAILABLE:
            risk_summary = self.risk_manager.get_portfolio_summary()
            print(f"\nRisk Manager:")
            print(f"   Open Positions: {risk_summary['open_positions']}")
            print(f"   Total Exposure: ${risk_summary['total_exposure_usd']:,.2f}")
            print(f"   Daily P&L: ${risk_summary['daily_pnl']:+,.2f}")
            print(f"   Trades Approved: {risk_summary['trades_approved']}")
            print(f"   Trades Rejected: {risk_summary['trades_rejected']}")
            if risk_summary['trading_halted']:
                print(f"   ⚠️  TRADING HALTED - Daily loss limit exceeded")
        
        # Execution Summary
        if EXECUTION_LAYER_AVAILABLE:
            exec_summary = self.executor.get_summary()
            print(f"\nExecution Layer:")
            print(f"   Total Executions: {exec_summary['total_executions']}")
            print(f"   Success Rate: {exec_summary['success_rate']:.1f}%")
            print(f"   Avg Latency: {exec_summary['avg_latency_ms']:.1f}ms")
        
        print("\n" + "=" * 70)


def run_tests():
    """Run all module tests using pytest."""
    print("\n" + "=" * 70)
    print("🧪 RUNNING ALL MODULE TESTS")
    print("=" * 70)
    
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-v"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("ERRORS:", result.stderr)
    
    print("\n" + "=" * 70)
    print("✅ Test run completed")
    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Trading Bot - End-to-End Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trading_bot.py --mode paper                    # Single run, paper mode
  python trading_bot.py --mode paper --monitor 60       # Continuous monitoring
  python trading_bot.py --test                          # Run module tests
  
Environment Variables for Live Trading:
  BINANCE_API_KEY, BINANCE_SECRET
  COINBASE_API_KEY, COINBASE_SECRET
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['paper', 'live'],
        default='paper',
        help='Trading mode: paper (simulation) or live (real trades)'
    )
    
    parser.add_argument(
        '--monitor',
        type=int,
        metavar='SECONDS',
        help='Enable continuous monitoring with specified interval'
    )
    
    parser.add_argument(
        '--log',
        default='trading_bot.log',
        help='Log file path (default: trading_bot.log)'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run all module tests'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='JSON config file for custom settings'
    )
    
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Start web dashboard'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Dashboard port (default: 8080)'
    )
    
    args = parser.parse_args()
    
    # Run tests if requested
    if args.test:
        run_tests()
        return
    
    # Start dashboard only mode
    if args.dashboard:
        if DASHBOARD_AVAILABLE:
            print("🌐 Starting Dashboard Server...")
            print(f"   URL: http://localhost:{args.port}")
            print(f"   Use --port to change port\n")
            dashboard.run_dashboard(port=args.port)
        else:
            print("❌ Dashboard not available. Install flask: pip install flask")
            sys.exit(1)
        return
    
    # Load config if provided
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    elif os.path.exists('config.json'):
        # Use default config.json if it exists
        with open('config.json', 'r') as f:
            config = json.load(f)
            print("📄 Loaded config.json")
    
    # Start dashboard in background if enabled in config
    dashboard_thread = None
    if DASHBOARD_AVAILABLE and config.get('dashboard', {}).get('enabled', False):
        dashboard_port = config.get('dashboard', {}).get('port', 8080)
        print(f"🌐 Starting Dashboard on port {dashboard_port}...")
        dashboard_thread = Thread(target=dashboard.run_dashboard, kwargs={'port': dashboard_port}, daemon=True)
        dashboard_thread.start()
    
    # Initialize and run bot
    try:
        bot = TradingBot(
            mode=args.mode,
            log_file=args.log,
            config=config
        )
        
        if args.monitor:
            bot.run_monitor(args.monitor)
        else:
            bot.run_once()
            bot.print_summary()
            
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
