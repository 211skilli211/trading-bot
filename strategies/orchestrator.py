#!/usr/bin/env python3
"""
Trading Bot Orchestrator
======================
Main entry point that runs all strategies and the multi-agent system.

Usage:
    python orchestrator.py                    # Run all strategies
    python orchestrator.py --strategy arb    # Run only arbitrage
    python orchestrator.py --paper           # Paper trading mode
    python orchestrator.py --live            # Live trading mode
"""

import argparse
import json
import logging
import signal
import sys
import time
import os
from datetime import datetime, timezone
from typing import Dict, Optional

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategies
from strategies.binary_arbitrage import BinaryArbitrageStrategy
from strategies.sniper import SniperStrategy
from strategies.multi_agent import MultiAgentSystem

# Import memory and alerts
from trading_memory import TradingMemory
from alerts import AlertManager

# Live trading execution
try:
    from execution_layer_live import CEXTrader, ExecutionMode as LiveExecutionMode
    LIVE_TRADING_AVAILABLE = True
except ImportError:
    LIVE_TRADING_AVAILABLE = False

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    """
    Main orchestrator that coordinates all trading strategies.
    
    Features:
    - Runs multiple strategies in parallel
    - Manages shared memory
    - Handles alerts
    - Circuit breaker logic
    """
    
    def __init__(self, config_path: str = "config.json", mode: str = "PAPER"):
        self.mode = mode
        self.running = False
        
        # Load config
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Initialize components
        self.memory = TradingMemory()
        self.alert_manager = AlertManager(self.config.get("alerts", {}))
        
        # Initialize strategies
        self.strategies = {}
        self._init_strategies()
        
        # Multi-agent system
        self.multi_agent = MultiAgentSystem(
            self.config.get("multi_agent", {})
        )
        
        # Stats
        self.start_time = datetime.now(timezone.utc)
        self.total_trades = 0
        
        logger.info(f"[Orchestrator] Initialized in {mode} mode")
    
    def _init_strategies(self):
        """Initialize all trading strategies"""
        
        # Binary Arbitrage
        arb_config = self.config.get("binary_arb", {
            "min_spread_pct": 1.0,
            "max_position_usd": 10,
            "max_concurrent_arbs": 3,
            "check_interval_seconds": 30
        })
        self.strategies["binary_arbitrage"] = BinaryArbitrageStrategy(arb_config)
        
        # Sniper
        sniper_config = self.config.get("sniper", {
            "momentum_threshold": 0.10,
            "max_position_usd": 5,
            "entry_window_seconds": 60,
            "max_concurrent_trades": 3
        })
        self.strategies["sniper"] = SniperStrategy(sniper_config)
        
        logger.info(f"[Orchestrator] Initialized {len(self.strategies)} strategies")
    
    def run_strategy(self, strategy_name: str, iterations: Optional[int] = None):
        """Run a specific strategy"""
        if strategy_name not in self.strategies:
            logger.error(f"Unknown strategy: {strategy_name}")
            return
        
        strategy = self.strategies[strategy_name]
        logger.info(f"[Orchestrator] Running {strategy_name}...")
        
        if hasattr(strategy, 'run'):
            strategy.run(mode=self.mode, iterations=iterations)
    
    def scan_all(self) -> Dict:
        """Scan all strategies for opportunities"""
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": self.mode,
            "opportunities": {}
        }
        
        # Scan each strategy
        for name, strategy in self.strategies.items():
            try:
                # Check for different scan method names
                scan_method = None
                if hasattr(strategy, 'scan'):
                    scan_method = strategy.scan
                elif hasattr(strategy, 'scan_markets'):
                    scan_method = strategy.scan_markets
                
                if scan_method:
                    opportunities = scan_method()
                    # Handle different return types
                    if isinstance(opportunities, list):
                        results["opportunities"][name] = {
                            "count": len(opportunities),
                            "data": [o.to_dict() if hasattr(o, 'to_dict') else o for o in opportunities]
                        }
                    else:
                        results["opportunities"][name] = {
                            "count": 0,
                            "data": [],
                            "info": str(opportunities)
                        }
                else:
                    results["opportunities"][name] = {"info": "No scan method available"}
            except Exception as e:
                logger.error(f"Error scanning {name}: {e}")
                results["opportunities"][name] = {"error": str(e)}
        
        return results
    
    def get_stats(self) -> Dict:
        """Get overall statistics"""
        stats = {
            "mode": self.mode,
            "uptime_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "total_trades": self.total_trades,
            "strategies": {},
            "memory": self.memory.get_stats(),
            "multi_agent": self.multi_agent.get_dashboard_data()
        }
        
        # Get strategy stats
        for name, strategy in self.strategies.items():
            if hasattr(strategy, 'get_stats'):
                stats["strategies"][name] = strategy.get_stats()
        
        return stats
    
    def stop(self):
        """Stop all strategies"""
        logger.info("[Orchestrator] Stopping...")
        self.running = False
        
        # Log final stats
        stats = self.get_stats()
        logger.info(f"[Orchestrator] Final stats: {json.dumps(stats, indent=2)}")
        
        # Save to memory
        self.memory.log_trade(
            strategy="general",
            pnl=0,
            notes=f"Bot stopped after {stats['uptime_seconds']:.0f} seconds",
            metadata={"stats": stats}
        )
    
    def execute_live(self, strategy_name: str, signal: Dict) -> Dict:
        """
        Execute a trade in live mode.
        
        Args:
            strategy_name: Name of the strategy generating the signal
            signal: Trade signal dict with buy_exchange, sell_exchange, amount, etc.
        
        Returns:
            Execution result
        """
        if not LIVE_TRADING_AVAILABLE:
            return {"success": False, "error": "Live trading not available"}
        
        if self.mode != "LIVE":
            return {"success": False, "error": "Not in LIVE mode"}
        
        try:
            # Initialize trader
            trader = CEXTrader()
            
            # Execute the trade
            result = trader.execute_order(
                exchange=signal.get("exchange", "binance"),
                side=signal.get("side", "BUY"),
                symbol=signal.get("symbol", "BTC/USDT"),
                amount=signal.get("amount", 0.001),
                price=signal.get("price")
            )
            
            # Log to memory
            self.memory.log_trade(
                strategy=strategy_name,
                pnl=result.get("filled_amount", 0) * (result.get("filled_price", 0) - signal.get("price", 0)),
                notes=f"Live trade: {signal.get('side')} {signal.get('symbol')}",
                metadata=result
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Live execution error: {e}")
            return {"success": False, "error": str(e)}


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Trading Bot Orchestrator")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--mode", choices=["PAPER", "LIVE"], default="PAPER", 
                       help="Trading mode")
    parser.add_argument("--strategy", help="Run specific strategy only")
    parser.add_argument("--iterations", type=int, help="Number of iterations (for testing)")
    parser.add_argument("--scan-only", action="store_true", help="Scan once and exit")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create orchestrator
    orchestrator = TradingOrchestrator(config_path=args.config, mode=args.mode)
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run
    if args.scan_only:
        # Single scan and display
        results = orchestrator.scan_all()
        print(json.dumps(results, indent=2))
    elif args.strategy:
        # Run specific strategy
        orchestrator.run_strategy(args.strategy, args.iterations)
    else:
        # Run all (continuous)
        logger.info("[Orchestrator] Starting continuous mode...")
        orchestrator.running = True
        
        while orchestrator.running:
            # Scan for opportunities
            results = orchestrator.scan_all()
            
            # Log opportunities
            total_opps = sum(
                opp.get("count", 0) 
                for opp in results.get("opportunities", {}).values()
            )
            
            if total_opps > 0:
                logger.info(f"[Orchestrator] Found {total_opps} opportunities")
            
            # Sleep between scans
            time.sleep(60)
        
        orchestrator.stop()


if __name__ == "__main__":
    main()
