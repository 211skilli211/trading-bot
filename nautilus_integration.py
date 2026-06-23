#!/usr/bin/env python3
"""
Nautilus Trader Integration — Phase 1 & 2
==========================================
Wraps existing strategy logic (regime detection, signal generation) 
into Nautilus Trader's framework for deterministic backtesting.

This module provides:
1. NautilusStrategy — wraps BaseStrategy into Nautilus Strategy class
2. NautilusDataAdapter — feeds market data into Nautilus engine
3. NautilusBacktestRunner — runs backtests with Nautilus BacktestEngine
4. NautilusLiveRunner — runs live/paper trading with Nautilus

Prerequisites (install when network allows):
    pip install nautilus_trader

Architecture:
    Existing Bot                  Nautilus Trader
    ───────────                   ──────────────
    RegimeDetector  ──────►  Strategy.on_tick / on_bar
    BaseStrategy    ──────►  Strategy.on_order_filled
    ccxt_connector  ──────►  CCXTExecutionAdapter
    backtester.py   ──────►  BacktestEngine
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# ─── Nautilus availability check ───────────────────────────────────────────────
NAUTILUS_AVAILABLE = False
try:
    import nautilus_trader
    NAUTILUS_AVAILABLE = True
    logger.info(f"[Nautilus] Version {nautilus_trader.__version__} available")
except ImportError:
    logger.info("[Nautilus] nautilus_trader not installed — integration scaffold ready, activate with: pip install nautilus_trader")


# ─── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class NautilusConfig:
    """Configuration for Nautilus Trader integration."""
    # Trading mode
    mode: str = "BACKTEST"  # BACKTEST, PAPER, LIVE
    
    # Instruments
    instruments: List[str] = None  # e.g., ["BTC/USDT", "ETH/USDT"]
    
    # Venue
    venue: str = "BINANCE"  # BINANCE, BYBIT, etc.
    
    # Data
    data_start: str = "2024-01-01"
    data_end: str = "2024-12-31"
    data_interval: str = "1m"  # 1m, 5m, 1h, 1d
    
    # Risk
    initial_capital: float = 10000.0
    max_position_pct: float = 0.02
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10
    
    # Strategy
    strategy_name: str = "regime_momentum"
    regime_config: Dict = None
    
    # Execution
    commission_pct: float = 0.001  # 0.1% per trade
    slippage_pct: float = 0.0005   # 0.05% slippage
    
    def __post_init__(self):
        if self.instruments is None:
            self.instruments = ["BTC/USDT", "ETH/USDT"]
        if self.regime_config is None:
            self.regime_config = {
                "usdt_dom_defensive": 8.5,
                "usdt_dom_risk_on": 7.0,
                "stable_supply_threshold": 150
            }


# ─── Strategy Adapter ──────────────────────────────────────────────────────────

class NautilusStrategyAdapter:
    """
    Wraps existing BaseStrategy into Nautilus Trader's Strategy class.
    
    This adapter bridges our existing strategy framework (RegimeDetector, 
    BaseStrategy, signal_generator) into Nautilus's event-driven architecture.
    
    Usage:
        adapter = NautilusStrategyAdapter(config, existing_strategy)
        # When Nautilus is available:
        # strategy = adapter.build_nautilus_strategy()
    """
    
    def __init__(self, config: NautilusConfig, existing_strategy=None):
        self.config = config
        self.existing_strategy = existing_strategy
        self.regime_detector = None
        
        # Import existing components
        try:
            from core.regime import RegimeDetector
            self.regime_detector = RegimeDetector(config.regime_config)
            logger.info("[Nautilus] RegimeDetector loaded")
        except ImportError as e:
            logger.warning(f"[Nautilus] Could not load RegimeDetector: {e}")
        
        # State
        self.current_regime = "NEUTRAL"
        self.signals_generated = 0
        self.trades_executed = 0
    
    def on_tick(self, tick):
        """
        Process a market tick — called by Nautilus on each price update.
        
        Maps to: RegimeDetector.detect_regime() + BaseStrategy.scan()
        """
        if not NAUTILUS_AVAILABLE:
            return
        
        # Detect regime
        if self.regime_detector:
            self.current_regime = self.regime_detector.detect_regime()
            regime_config = self.regime_detector.get_regime_config(self.current_regime)
            
            # Skip if defensive
            if regime_config.get('avoid_new_positions'):
                logger.debug(f"[Nautilus] Regime {self.current_regime}: skipping")
                return
        
        # Run existing strategy scan
        if self.existing_strategy:
            signals = self.existing_strategy.scan()
            for signal in signals:
                if signal.side != "hold" and signal.confidence > 0.7:
                    self._submit_order(signal)
    
    def on_bar(self, bar):
        """
        Process a completed bar/candlestick — called by Nautilus on each bar close.
        
        Maps to: signal_generator.generate_signal()
        """
        if not NAUTILUS_AVAILABLE:
            return
        
        # Bar-based strategy logic goes here
        # This is where SMA crossovers, momentum signals, etc. would be calculated
        pass
    
    def on_order_filled(self, order):
        """
        Process an order fill — called by Nautilus when an order is executed.
        
        Maps to: BaseStrategy.execute() + trade_database logging
        """
        if not NAUTILUS_AVAILABLE:
            return
        
        self.trades_executed += 1
        logger.info(f"[Nautilus] Order filled: {order}")
    
    def _submit_order(self, signal):
        """Submit an order to Nautilus execution engine."""
        if not NAUTILUS_AVAILABLE:
            return
        
        # This would use Nautilus's order submission API
        # from nautilus_trader.model import Order
        # order = Order(...)
        # self.submit_order(order)
        logger.info(f"[Nautilus] Would submit: {signal.side} {signal.symbol}")
        self.signals_generated += 1
    
    def build_nautilus_strategy(self):
        """
        Build a Nautilus Strategy class from this adapter.
        
        Returns a class that can be registered with Nautilus's BacktestEngine
        or LiveEngine.
        """
        if not NAUTILUS_AVAILABLE:
            logger.warning("[Nautilus] Cannot build strategy — nautilus_trader not installed")
            return None
        
        adapter = self  # Capture adapter instance
        
        # Nautilus Strategy class definition
        # This would use nautilus_trader.trading.strategy.Strategy as base
        class RegimeStrategy:
            """Nautilus strategy wrapping our regime-based approach."""
            
            def __init__(self, config):
                self.adapter = adapter
                self.config = config
            
            def on_start(self):
                logger.info("[Nautilus] Strategy started")
            
            def on_tick(self, tick):
                self.adapter.on_tick(tick)
            
            def on_bar(self, bar):
                self.adapter.on_bar(bar)
            
            def on_order_filled(self, order, trade):
                self.adapter.on_order_filled(order)
            
            def on_stop(self):
                logger.info(f"[Nautilus] Strategy stopped. Signals: {self.adapter.signals_generated}, Trades: {self.adapter.trades_executed}")
        
        return RegimeStrategy


# ─── Data Adapter ──────────────────────────────────────────────────────────────

class NautilusDataAdapter:
    """
    Feeds market data into Nautilus Trader.
    
    Supports:
    - Historical data from CCXT (for backtesting)
    - Live data from CCXT (for paper/live trading)
    - CSV/Parquet file import
    """
    
    def __init__(self, config: NautilusConfig):
        self.config = config
    
    def fetch_historical_data(self, symbol: str, start: str, end: str, interval: str = "1m") -> List[Dict]:
        """
        Fetch historical OHLCV data from CCXT.
        
        Returns data in format compatible with Nautilus's data catalog.
        """
        try:
            import ccxt
            exchange = ccxt.binance({'enableRateLimit': True})
            
            # Convert symbol format: "BTC/USDT" → "BTC/USDT"
            ohlcv = exchange.fetch_ohlcv(symbol, interval, since=exchange.parse8601(start + "T00:00:00Z"))
            
            data = []
            for candle in ohlcv:
                data.append({
                    'timestamp': candle[0],
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                })
            
            logger.info(f"[Nautilus] Fetched {len(data)} candles for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"[Nautilus] Error fetching data: {e}")
            return []
    
    def save_to_parquet(self, data: List[Dict], filename: str):
        """Save data to Parquet format for Nautilus backtesting."""
        try:
            import pandas as pd
            df = pd.DataFrame(data)
            df.to_parquet(filename)
            logger.info(f"[Nautilus] Saved {len(data)} rows to {filename}")
        except ImportError:
            logger.warning("[Nautilus] pandas not installed — saving as JSON")
            with open(filename.replace('.parquet', '.json'), 'w') as f:
                json.dump(data, f)
    
    def load_from_parquet(self, filename: str) -> List[Dict]:
        """Load data from Parquet file."""
        try:
            import pandas as pd
            df = pd.read_parquet(filename)
            return df.to_dict('records')
        except ImportError:
            logger.warning("[Nautilus] pandas not installed — loading from JSON")
            with open(filename.replace('.parquet', '.json'), 'r') as f:
                return json.load(f)


# ─── Backtest Runner ──────────────────────────────────────────────────────────

class NautilusBacktestRunner:
    """
    Runs backtests using Nautilus Trader's BacktestEngine.
    
    Key advantage: identical code path for backtest → live.
    The same strategy class runs in both modes.
    """
    
    def __init__(self, config: NautilusConfig):
        self.config = config
        self.data_adapter = NautilusDataAdapter(config)
        self.strategy_adapter = NautilusStrategyAdapter(config)
    
    def run_backtest(self, strategy_class=None) -> Dict[str, Any]:
        """
        Run a backtest.
        
        Args:
            strategy_class: Nautilus strategy class (if None, uses adapter's)
            
        Returns:
            Backtest results dict
        """
        if not NAUTILUS_AVAILABLE:
            logger.info("[Nautilus] Running scaffold backtest (nautilus_trader not installed)")
            return self._scaffold_backtest()
        
        # Full Nautilus backtest would go here:
        # from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
        # engine = BacktestEngine(config=BacktestEngineConfig())
        # engine.add_strategy(strategy_class)
        # engine.add_data(data)
        # engine.run()
        # return engine.get_results()
        
        return {"status": "nautilus_not_installed", "scaffold": True}
    
    def _scaffold_backtest(self) -> Dict[str, Any]:
        """
        Scaffold backtest using existing backtester.
        Provides same interface as Nautilus backtest.
        """
        logger.info("[Nautilus] Running scaffold backtest with existing engine")
        
        # Import existing backtester
        try:
            from backtester import Backtester
            from core.regime import RegimeDetector
            
            regime = RegimeDetector(self.config.regime_config)
            regime_config = regime.get_regime_config()
            
            results = {
                "mode": "SCAFFOLD",
                "initial_capital": self.config.initial_capital,
                "instruments": self.config.instruments,
                "regime": regime.current_regime if hasattr(regime, 'current_regime') else "NEUTRAL",
                "regime_config": regime_config,
                "status": "Install nautilus_trader for full backtesting",
                "install_command": "pip install nautilus_trader"
            }
            
            return results
            
        except ImportError as e:
            logger.error(f"[Nautilus] Could not load existing backtester: {e}")
            return {"status": "error", "message": str(e)}


# ─── Live Runner ───────────────────────────────────────────────────────────────

class NautilusLiveRunner:
    """
    Runs live/paper trading using Nautilus Trader's LiveEngine.
    
    Uses the same strategy class as backtest — just swap the engine.
    """
    
    def __init__(self, config: NautilusConfig):
        self.config = config
        self.strategy_adapter = NautilusStrategyAdapter(config)
        self.running = False
    
    def start(self, strategy_class=None, mode: str = "PAPER"):
        """
        Start live/paper trading.
        
        Args:
            strategy_class: Nautilus strategy class
            mode: "PAPER" or "LIVE"
        """
        if not NAUTILUS_AVAILABLE:
            logger.info(f"[Nautilus] Scaffold: would start {mode} trading")
            logger.info("[Nautilus] Install nautilus_trader to enable live trading")
            return
        
        self.running = True
        logger.info(f"[Nautilus] Starting {mode} trading...")
        
        # Full Nautilus live trading would go here:
        # from nautilus_trader.live import LiveEngine, LiveEngineConfig
        # engine = LiveEngine(config=LiveEngineConfig())
        # engine.add_strategy(strategy_class)
        # engine.add_venue(venue_config)
        # engine.run()
    
    def stop(self):
        """Stop live trading."""
        self.running = False
        logger.info("[Nautilus] Trading stopped")


# ─── Integration Status ────────────────────────────────────────────────────────

def get_integration_status() -> Dict[str, Any]:
    """Check Nautilus Trader integration status."""
    status = {
        "nautilus_installed": NAUTILUS_AVAILABLE,
        "components": {
            "NautilusStrategyAdapter": True,
            "NautilusDataAdapter": True,
            "NautilusBacktestRunner": True,
            "NautilusLiveRunner": True,
        },
        "existing_components": {
            "RegimeDetector": False,
            "BaseStrategy": False,
            "ccxt_connector": False,
            "backtester": False,
        },
        "next_steps": []
    }
    
    # Check existing components
    try:
        from core.regime import RegimeDetector
        status["existing_components"]["RegimeDetector"] = True
    except ImportError:
        status["next_steps"].append("Install core.regime.RegimeDetector")
    
    try:
        from strategies.strategy_template import BaseStrategy
        status["existing_components"]["BaseStrategy"] = True
    except ImportError:
        status["next_steps"].append("Install strategies.strategy_template.BaseStrategy")
    
    try:
        from ccxt_connector import CCXTConnector
        status["existing_components"]["ccxt_connector"] = True
    except ImportError:
        status["next_steps"].append("Install ccxt_connector.CCXTConnector")
    
    try:
        from backtester import Backtester
        status["existing_components"]["backtester"] = True
    except ImportError:
        status["next_steps"].append("Install backtester.Backtester")
    
    if not NAUTILUS_AVAILABLE:
        status["next_steps"].append("pip install nautilus_trader")
    
    return status


# ─── CLI Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    
    print("=" * 60)
    print("NAUTILUS TRADER INTEGRATION")
    print("=" * 60)
    
    # Check status
    status = get_integration_status()
    print(f"\nNautilus Installed: {'✅ YES' if status['nautilus_installed'] else '❌ NO (scaffold mode)'}")
    
    print("\nExisting Components:")
    for name, available in status["existing_components"].items():
        print(f"  {'✅' if available else '❌'} {name}")
    
    if status["next_steps"]:
        print("\nNext Steps:")
        for step in status["next_steps"]:
            print(f"  → {step}")
    
    # Test scaffold
    print("\n" + "-" * 60)
    print("SCAFFOLD BACKTEST TEST")
    print("-" * 60)
    
    config = NautilusConfig(
        mode="BACKTEST",
        instruments=["BTC/USDT", "ETH/USDT"],
        initial_capital=10000.0
    )
    
    runner = NautilusBacktestRunner(config)
    results = runner.run_backtest()
    
    print(f"\nResults: {json.dumps(results, indent=2, default=str)}")
    
    print("\n" + "=" * 60)
    print("Integration scaffold ready. Install nautilus_trader to activate.")
    print("=" * 60)
