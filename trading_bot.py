#!/usr/bin/env python3
"""
Trading Bot - Complete End-to-End Orchestrator with Solana DEX Integration
============================================================================

A modular, ethical trading bot that implements:
1. Data Layer       - Fetch prices from exchanges (CEX + Solana DEX)
2. Strategy Engine  - Arbitrage logic and signal generation
3. Risk Manager     - Position limits and stop-loss rules
4. Execution Layer  - Paper/live trade execution

Features:
- CEX Arbitrage: Binance, Coinbase, etc.
- DEX Arbitrage: Jupiter (Solana) vs CEX
- Parallel scanning with threading
- Unified risk management and alerting

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
    SOLANA_PRIVATE_KEY=your_solana_key  # For DEX trading
"""

import argparse
import json
import time
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from threading import Thread, Event
from dataclasses import dataclass

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

# Solana DEX Integration
try:
    from solana_dex import SolanaDEX, TOKENS
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    print("[TradingBot] Note: Solana DEX module not available")

# ML Predictions Integration
try:
    from ml_predictions import MLPredictionSystem
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("[TradingBot] Note: ML Predictions not available")

try:
    from database import TradingDatabase
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Strategy modules
try:
    from strategies.binary_arbitrage import BinaryArbitrageStrategy
    BINARY_ARB_AVAILABLE = True
except ImportError as e:
    BINARY_ARB_AVAILABLE = False
    print(f"[TradingBot] Note: Binary Arbitrage not available: {e}")

try:
    from strategies.sniper import SniperStrategy
    SNIPER_AVAILABLE = True
except ImportError as e:
    SNIPER_AVAILABLE = False
    print(f"[TradingBot] Note: Sniper Strategy not available: {e}")

try:
    from trading_memory import TradingMemory
    MEMORY_AVAILABLE = True
except ImportError as e:
    MEMORY_AVAILABLE = False
    print(f"[TradingBot] Note: Trading Memory not available: {e}")

try:
    from news_fetcher import CryptoNewsFetcher
    NEWS_AVAILABLE = True
except ImportError as e:
    NEWS_AVAILABLE = False
    print(f"[TradingBot] Note: News Fetcher not available: {e}")

try:
    from strategies.multi_agent import MultiAgentSystem
    MULTI_AGENT_AVAILABLE = True
except ImportError as e:
    MULTI_AGENT_AVAILABLE = False
    print(f"[TradingBot] Note: Multi-Agent not available: {e}")

# RL Agent Integration
try:
    from rl import PPOAgent, TradingEnvironment, RL_AVAILABLE
    from rl.agent import SimpleRLAgent
except ImportError as e:
    RL_AVAILABLE = False
    print(f"[TradingBot] Note: RL Agent not available: {e}")


@dataclass
class SolanaArbitrageResult:
    """Result of a Solana DEX arbitrage check."""
    timestamp: str
    token_pair: str
    dex_price: float
    cex_price: float
    spread_pct: float
    viable: bool
    action: str
    details: Dict[str, Any]


class TradingBot:
    """
    Complete Trading Bot Orchestrator.
    
    Coordinates all four layers:
    - Fetches market data from CEX and DEX
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
        print("   With Solana DEX Integration")
        print("=" * 70)
        
        # Handle case where config is passed as first argument
        if isinstance(mode, dict):
            config = mode
            mode = config.get('bot', {}).get('mode', 'paper') if config else 'paper'
        
        self.mode = mode
        self.log_file = log_file
        self.config = config or {}
        
        # Initialize logger
        self.logger = AuditLogger(log_file)
        
        # Initialize database
        if DATABASE_AVAILABLE:
            self.db = TradingDatabase()
        else:
            self.db = None
        
        # Initialize layers
        self._init_layers()
        
        # Initialize Solana DEX
        self._init_solana()
        
        # Statistics
        self.run_count = 0
        self.start_time = datetime.now(timezone.utc)
        
        # Threading control
        self._stop_event = Event()
        self._solana_thread = None
        self._cex_thread = None
        
        print(f"\n📊 Configuration:")
        print(f"   Mode: {mode.upper()}")
        print(f"   Log File: {log_file}")
        print(f"   Start Time: {self.start_time.isoformat()}")
        
        # Solana stats
        self.solana_scan_count = 0
        self.solana_opportunities_found = 0
        self.solana_trades_executed = 0
    
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
            kraken_key = os.getenv('KRAKEN_API_KEY')
            kraken_secret = os.getenv('KRAKEN_SECRET')
            
            self.executor = ExecutionLayer(
                mode=execution_mode,
                max_retries=exec_config.get('max_retries', 3),
                retry_delay=exec_config.get('retry_delay', 1.0),
                binance_api_key=binance_key,
                binance_secret=binance_secret,
                coinbase_api_key=coinbase_key,
                coinbase_secret=coinbase_secret,
                kraken_api_key=kraken_key,
                kraken_secret=kraken_secret
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
        
        # ML Predictions (optional)
        if ML_AVAILABLE:
            self.ml_predictor = MLPredictionSystem()
            print("✅ ML Predictions initialized")
        else:
            self.ml_predictor = None
        
        # Strategy Modules
        self._init_strategies()
        
        # Trading Memory (optional)
        if MEMORY_AVAILABLE:
            self.memory = TradingMemory()
            print("✅ Trading Memory initialized")
        else:
            self.memory = None
        
        # News Fetcher (optional)
        self.news_fetcher = None
        if NEWS_AVAILABLE:
            try:
                self.news_fetcher = CryptoNewsFetcher()
                print("✅ News Fetcher initialized")
            except Exception as e:
                print(f"⚠️  News Fetcher init failed: {e}")
        else:
            print("ℹ️  News Fetcher: Module not available")
        
        # Multi-Agent System (optional)
        self.multi_agent = None
        if MULTI_AGENT_AVAILABLE:
            try:
                ma_config = self.config.get('multi_agent', {})
                self.multi_agent = MultiAgentSystem(ma_config)
                print("✅ Multi-Agent System initialized")
                print(f"   Agents: {len(self.multi_agent.agents)}")
            except Exception as e:
                print(f"⚠️  Multi-Agent init failed: {e}")
        else:
            print("ℹ️  Multi-Agent: Module not available")
        
        print()
    
    def _init_solana(self):
        """Initialize Solana DEX connector."""
        self.solana_enabled = self.config.get('solana', {}).get('enabled', False)
        
        if not self.solana_enabled:
            print("ℹ️  Solana DEX: Disabled in config")
            self.solana_dex = None
            return
        
        if not SOLANA_AVAILABLE:
            print("⚠️  Solana DEX: Module not available (pip install solathon)")
            self.solana_dex = None
            self.solana_enabled = False
            return
        
        try:
            solana_config = self.config.get('solana', {})
            rpc_url = solana_config.get('rpc_url') or os.getenv('SOLANA_RPC_URL')
            
            # Try to load private key from environment first, then from wallet file
            private_key = os.getenv('SOLANA_PRIVATE_KEY')
            
            if not private_key:
                # Try loading from wallet file
                wallet_file = solana_config.get('wallet_file', 'solana_wallet_live.json')
                if os.path.exists(wallet_file):
                    try:
                        with open(wallet_file, 'r') as f:
                            wallet_data = json.load(f)
                            private_key = wallet_data.get('private_key')
                            print(f"[SolanaDEX] Loaded wallet from {wallet_file}")
                    except Exception as e:
                        print(f"[SolanaDEX] Could not load wallet file: {e}")
            
            self.solana_dex = SolanaDEX(rpc_url=rpc_url, private_key=private_key)
            
            # Check if wallet is loaded (for live trading)
            if self.mode == "live" and not self.solana_dex.keypair:
                print("⚠️  Solana DEX: Wallet not loaded - falling back to paper mode for DEX")
            
            print("✅ Solana DEX initialized")
            print(f"   RPC: {self.solana_dex.rpc_url[:50]}...")
            print(f"   Wallet: {self.solana_dex.wallet_address or 'Not connected (read-only)'}")
            
            # Trading pairs to scan
            self.solana_pairs = solana_config.get('pairs', [
                {'token': 'SOL', 'symbol': 'SOL/USDC', 'cex_symbol': 'SOLUSDT', 'decimals': 9},
                {'token': 'BTC', 'symbol': 'BTC/USDC', 'cex_symbol': 'BTCUSDT', 'decimals': 8},
                {'token': 'ETH', 'symbol': 'ETH/USDC', 'cex_symbol': 'ETHUSDT', 'decimals': 8},
            ])
            
            # Arbitrage thresholds
            self.solana_min_spread = solana_config.get('min_spread', 0.005)  # 0.5%
            self.solana_trade_amount_usd = solana_config.get('trade_amount_usd', 50)
            
        except Exception as e:
            print(f"❌ Solana DEX initialization failed: {e}")
            self.solana_dex = None
            self.solana_enabled = False
    
    def _init_strategies(self):
        """Initialize strategy modules."""
        print("\n📊 Initializing Strategies...")
        
        # Binary Arbitrage Strategy (PolyMarket)
        self.binary_arb = None
        if BINARY_ARB_AVAILABLE:
            try:
                arb_config = self.config.get('strategies', {}).get('binary_arbitrage', {})
                self.binary_arb = BinaryArbitrageStrategy(arb_config)
                print("✅ Binary Arbitrage Strategy initialized")
            except Exception as e:
                print(f"⚠️  Binary Arbitrage init failed: {e}")
        else:
            print("ℹ️  Binary Arbitrage: Module not available")
        
        # Sniper Strategy (PolyMarket)
        self.sniper = None
        if SNIPER_AVAILABLE:
            try:
                sniper_config = self.config.get('strategies', {}).get('sniper', {})
                self.sniper = SniperStrategy(sniper_config)
                print("✅ Sniper Strategy initialized")
            except Exception as e:
                print(f"⚠️  Sniper init failed: {e}")
        else:
            print("ℹ️  Sniper: Module not available")
        
        # RL Agent
        self._init_rl_agent()
    
    def _init_rl_agent(self):
        """Initialize RL agent."""
        self.rl_agent = None
        self.rl_env = None
        self.rl_available = False
        
        if not RL_AVAILABLE:
            print("ℹ️  RL Agent: Module not available")
            return
        
        try:
            rl_config = self.config.get('rl', {})
            
            if not rl_config.get('enabled', False):
                print("ℹ️  RL Agent: Disabled in config")
                return
            
            # Determine agent type
            agent_type = rl_config.get('agent_type', 'ppo')
            model_path = rl_config.get('model_path', 'models/ppo_agent.pkl')
            
            # State and action dimensions for trading
            window_size = rl_config.get('window_size', 20)
            state_dim = 10 * window_size  # Features * window
            action_dim = 3  # HOLD, BUY, SELL
            
            # Create agent
            if agent_type == 'ppo':
                self.rl_agent = PPOAgent(
                    state_dim=state_dim,
                    action_dim=action_dim,
                    hidden_dims=rl_config.get('hidden_dims', [128, 64]),
                    learning_rate=rl_config.get('learning_rate', 0.0003),
                    gamma=rl_config.get('gamma', 0.99)
                )
            else:
                self.rl_agent = SimpleRLAgent(
                    state_dim=state_dim,
                    action_dim=action_dim,
                    hidden_dim=rl_config.get('hidden_dim', 64)
                )
            
            # Try to load existing model
            if os.path.exists(model_path):
                if self.rl_agent.load(model_path):
                    print(f"✅ RL Agent loaded from {model_path}")
                else:
                    print(f"⚠️  RL Agent: Could not load model, using fresh agent")
            else:
                print(f"ℹ️  RL Agent: No existing model at {model_path}")
            
            self.rl_available = True
            print(f"✅ RL Agent initialized ({agent_type})")
            print(f"   State dim: {state_dim}, Action dim: {action_dim}")
            
        except Exception as e:
            print(f"⚠️  RL Agent init failed: {e}")
            self.rl_agent = None
    
    def get_rl_signal(self, market_data: Dict) -> Optional[Dict]:
        """
        Get trading signal from RL agent.
        
        Args:
            market_data: Dictionary with price data
            
        Returns:
            Signal dictionary or None if RL not available
        """
        if not self.rl_available or not self.rl_agent:
            return None
        
        try:
            # Convert market data to state format
            # This is a simplified version - in production you'd want
            # proper state construction from market_data
            state = self._market_data_to_state(market_data)
            
            # Get action from agent
            if hasattr(self.rl_agent, 'select_action'):
                if isinstance(self.rl_agent, PPOAgent):
                    action, log_prob, value = self.rl_agent.select_action(state, training=False)
                else:
                    action = self.rl_agent.select_action(state, training=False)
            else:
                return None
            
            # Map action to signal
            action_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
            signal = {
                'source': 'rl_agent',
                'action': action_map.get(action, 'HOLD'),
                'action_code': action,
                'confidence': 1.0,  # Could be derived from action probabilities
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return signal
            
        except Exception as e:
            print(f"[RL] Error getting signal: {e}")
            return None
    
    def _market_data_to_state(self, market_data: Dict) -> np.ndarray:
        """Convert market data to RL state format."""
        # This is a simplified placeholder
        # In production, construct proper state from price history
        window_size = self.config.get('rl', {}).get('window_size', 20)
        state_dim = 10 * window_size
        
        # Return zero state as placeholder
        # Real implementation would use historical data
        return np.zeros(state_dim, dtype=np.float32)
    
    def train_rl_agent(
        self, 
        data: pd.DataFrame = None, 
        episodes: int = 100,
        save_path: str = None
    ) -> Dict:
        """
        Train RL agent on historical data.
        
        Args:
            data: DataFrame with OHLCV data (None = fetch from exchanges)
            episodes: Number of training episodes
            save_path: Where to save the trained model
            
        Returns:
            Training results
        """
        if not RL_AVAILABLE:
            return {"error": "RL module not available"}
        
        print("\n" + "="*60)
        print("🤖 RL AGENT TRAINING")
        print("="*60)
        
        try:
            # Import training function
            from rl.train import train_agent, generate_sample_data
            
            # Generate or use provided data
            if data is None:
                print("Generating sample training data...")
                data = generate_sample_data(n_samples=2000)
            
            # Determine save path
            if save_path is None:
                save_path = self.config.get('rl', {}).get('model_path', 'models/ppo_agent.pkl')
            
            # Run training
            agent_type = self.config.get('rl', {}).get('agent_type', 'ppo')
            history = train_agent(
                data=data,
                n_episodes=episodes,
                model_path=save_path,
                agent_type=agent_type,
                print_interval=max(1, episodes // 10)
            )
            
            # Reload the trained model
            if self.rl_agent and os.path.exists(save_path):
                self.rl_agent.load(save_path)
            
            print("\n✅ Training complete!")
            return {
                "status": "success",
                "episodes": episodes,
                "final_reward": np.mean(history['rewards'][-10:]) if history['rewards'] else 0,
                "model_path": save_path
            }
            
        except Exception as e:
            print(f"❌ Training failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def run_binary_arbitrage_scan(self) -> Dict:
        """Run a single binary arbitrage scan."""
        if not self.binary_arb:
            return {"error": "Binary Arbitrage not available"}
        
        print("\n" + "="*60)
        print("🔍 BINARY ARBITRAGE SCAN")
        print("="*60)
        
        opportunities = self.binary_arb.scan()
        
        if opportunities:
            print(f"🎯 Found {len(opportunities)} opportunities")
            # Execute top opportunity in paper mode
            if self.mode == "paper":
                for opp in opportunities[:1]:  # Just execute the best one
                    trade = self.binary_arb.execute(opp, mode="PAPER")
                    print(f"📄 Paper trade executed: {trade.trade_id}")
        else:
            print("No arbitrage opportunities found")
        
        return self.binary_arb.get_stats()
    
    def run_sniper_scan(self) -> Dict:
        """Run a single sniper scan."""
        if not self.sniper:
            return {"error": "Sniper not available"}
        
        print("\n" + "="*60)
        print("🔍 SNIPER SCAN")
        print("="*60)
        
        opportunities = self.sniper.scan_markets()
        
        if opportunities:
            print(f"🎯 Found {len(opportunities)} sniper signals")
            for market in opportunities:
                if self.mode == "paper":
                    trade = self.sniper.execute(market, market.recommended_side, mode="PAPER")
                    print(f"📄 Paper trade executed: {trade.trade_id} ({market.recommended_side})")
        else:
            print("No sniper opportunities found")
        
        return self.sniper.get_stats()
    
    def run_multi_agent_evaluation(self) -> Dict:
        """
        Run multi-agent system evaluation cycle.
        
        Evaluates all agents, kills losers, scales winners.
        """
        if not self.multi_agent:
            return {"error": "Multi-Agent system not available"}
        
        print("\n" + "="*60)
        print("🤖 MULTI-AGENT EVALUATION")
        print("="*60)
        
        # Show current state
        dashboard_data = self.multi_agent.get_dashboard_data()
        print(f"\n📊 Current State:")
        print(f"   Total Agents: {dashboard_data['total_agents']}")
        print(f"   Active: {dashboard_data['active_agents']} | Killed: {dashboard_data['killed_agents']}")
        print(f"   Total Capital: ${dashboard_data['total_capital']:.2f}")
        print(f"   Total P&L: ${dashboard_data['total_pnl']:+.2f}")
        
        print("\n📈 Agent Performance:")
        for agent in dashboard_data["agents"]:
            status_icon = "✅" if agent["status"] == "active" else "❌"
            print(f"   {status_icon} {agent['name']:15} | ${agent['capital']:6.2f} | P&L: ${agent['total_pnl']:+6.2f} | Win: {agent['win_rate']:5.1f}%")
        
        # Run evaluation
        results = self.multi_agent.evaluate_and_evolve()
        
        print(f"\n🔄 Evolution Results:")
        if results["killed"]:
            print(f"   ❌ Killed: {', '.join(results['killed'])}")
        if results["scaled_up"]:
            for scale_info in results["scaled_up"]:
                print(f"   ✅ Scaled Up: {scale_info['name']} (${scale_info['old_capital']:.2f} → ${scale_info['new_capital']:.2f})")
        if not results["killed"] and not results["scaled_up"]:
            print("   ℹ️  No changes (evaluation period)")
        
        return results
    
    def get_multi_agent_status(self) -> Dict:
        """Get current multi-agent system status."""
        if not self.multi_agent:
            return {"error": "Multi-Agent system not available"}
        return self.multi_agent.get_dashboard_data()
    
    def fetch_news_analysis(self, keywords: List[str] = None) -> Dict:
        """
        Fetch and analyze news sentiment.
        
        Args:
            keywords: List of keywords to filter by (e.g., ['BTC', 'Bitcoin'])
            
        Returns:
            Dict with articles and sentiment summary
        """
        if not self.news_fetcher:
            return {"error": "News fetcher not available"}
        
        print("\n" + "="*60)
        print("📰 NEWS ANALYSIS")
        print("="*60)
        
        # Fetch news
        articles = self.news_fetcher.fetch_all(keywords=keywords, limit=30)
        
        if not articles:
            print("No news articles found")
            return {"articles": [], "sentiment": 0, "bias": "neutral"}
        
        # Calculate sentiment
        sentiments = [a.get('sentiment', 0) for a in articles]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # Categorize articles
        bullish = [a for a in articles if a.get('sentiment', 0) > 0.3]
        bearish = [a for a in articles if a.get('sentiment', 0) < -0.3]
        neutral = [a for a in articles if -0.3 <= a.get('sentiment', 0) <= 0.3]
        
        print(f"📊 Sentiment Analysis:")
        print(f"   Articles fetched: {len(articles)}")
        print(f"   Average sentiment: {avg_sentiment:+.2f} ({'bullish' if avg_sentiment > 0.1 else 'bearish' if avg_sentiment < -0.1 else 'neutral'})")
        print(f"   Bullish articles: {len(bullish)}")
        print(f"   Bearish articles: {len(bearish)}")
        print(f"   Neutral articles: {len(neutral)}")
        
        # Store in memory
        if self.memory:
            for article in articles[:5]:  # Store top 5
                self.memory.add_news([{
                    "title": article["title"],
                    "source": article["source"],
                    "sentiment": article.get("sentiment", 0),
                    "bias": article.get("bias", "center"),
                    "keywords": article.get("keywords", [])
                }])
        
        return {
            "articles": articles[:10],  # Return top 10
            "sentiment": avg_sentiment,
            "bullish_count": len(bullish),
            "bearish_count": len(bearish),
            "neutral_count": len(neutral),
            "bias": "bullish" if avg_sentiment > 0.1 else "bearish" if avg_sentiment < -0.1 else "neutral"
        }
    
    def scan_solana_arbitrage(self) -> List[SolanaArbitrageResult]:
        """
        Scan for arbitrage opportunities between Solana DEX (Jupiter) and CEX (Binance).
        
        This method can be run in a separate thread for parallel scanning.
        
        Returns:
            List of SolanaArbitrageResult objects
        """
        if not self.solana_enabled or not self.solana_dex:
            return []
        
        results = []
        self.solana_scan_count += 1
        
        print(f"\n{'='*70}")
        print(f"🔍 SOLANA DEX SCAN #{self.solana_scan_count}")
        print(f"{'='*70}")
        
        for pair_config in self.solana_pairs:
            try:
                result = self._check_single_pair_arbitrage(pair_config)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"[SolanaScanner] Error checking {pair_config['symbol']}: {e}")
                continue
        
        return results
    
    def _check_single_pair_arbitrage(self, pair_config: Dict[str, Any]) -> Optional[SolanaArbitrageResult]:
        """
        Check arbitrage for a single trading pair.
        
        Args:
            pair_config: Pair configuration with token, symbol, cex_symbol
            
        Returns:
            SolanaArbitrageResult if check completed, None otherwise
        """
        token = pair_config['token']
        symbol = pair_config['symbol']
        cex_symbol = pair_config['cex_symbol']
        decimals = pair_config['decimals']
        
        # Get Jupiter (DEX) price via quote
        trade_amount_usd = self.solana_trade_amount_usd
        usdc_amount = int(trade_amount_usd * 1_000_000)  # USDC has 6 decimals
        
        token_mint = TOKENS.get(token)
        usdc_mint = TOKENS['USDC']
        
        if not token_mint:
            return None
        
        # Get Jupiter quote: USDC -> Token
        jupiter_quote = self.solana_dex.get_quote(
            input_mint=usdc_mint,
            output_mint=token_mint,
            amount=usdc_amount,
            slippage_bps=50
        )
        
        if not jupiter_quote:
            print(f"   {symbol}: Could not get Jupiter quote")
            return None
        
        # Calculate DEX price (USDC per token)
        tokens_received = jupiter_quote.out_amount / (10 ** decimals)
        dex_price = trade_amount_usd / tokens_received if tokens_received > 0 else 0
        
        # Get Binance (CEX) price
        cex_data = self.binance.fetch_price(cex_symbol)
        if not cex_data:
            print(f"   {symbol}: Could not get CEX price")
            return None
        
        cex_price = cex_data['price']
        
        # Calculate spread: (DEX - CEX) / CEX
        price_diff = dex_price - cex_price
        spread_pct = abs(price_diff) / cex_price if cex_price > 0 else 0
        
        # Determine if opportunity exists
        viable = spread_pct >= self.solana_min_spread
        
        if viable:
            self.solana_opportunities_found += 1
            direction = "DEX→CEX" if dex_price > cex_price else "CEX→DEX"
            print(f"   🎯 {symbol}: Spread {spread_pct:.4%} ({direction})")
            print(f"      DEX (Jupiter): ${dex_price:,.2f}")
            print(f"      CEX (Binance): ${cex_price:,.2f}")
        else:
            print(f"   {symbol}: Spread {spread_pct:.4%} (below threshold)")
        
        result = SolanaArbitrageResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            token_pair=symbol,
            dex_price=dex_price,
            cex_price=cex_price,
            spread_pct=spread_pct,
            viable=viable,
            action="EXECUTE" if viable else "HOLD",
            details={
                'jupiter_quote': {
                    'in_amount': jupiter_quote.in_amount,
                    'out_amount': jupiter_quote.out_amount,
                    'price_impact': jupiter_quote.price_impact_pct,
                },
                'cex_data': cex_data,
                'trade_amount_usd': trade_amount_usd
            }
        )
        
        # Execute if viable and risk check passes
        if viable:
            self._execute_solana_arbitrage(result, pair_config, jupiter_quote)
        
        return result
    
    def _execute_solana_arbitrage(
        self, 
        opportunity: SolanaArbitrageResult, 
        pair_config: Dict[str, Any],
        jupiter_quote: Any
    ):
        """
        Execute Solana arbitrage trade if risk check passes.
        
        Args:
            opportunity: The arbitrage opportunity
            pair_config: Pair configuration
            jupiter_quote: Jupiter swap route
        """
        print(f"\n🚀 EXECUTING SOLANA ARBITRAGE: {opportunity.token_pair}")
        
        # Risk check
        trade_signal = {
            'decision': 'TRADE',
            'buy_exchange': 'Jupiter' if opportunity.dex_price < opportunity.cex_price else 'Binance',
            'sell_exchange': 'Binance' if opportunity.dex_price < opportunity.cex_price else 'Jupiter',
            'buy_price': min(opportunity.dex_price, opportunity.cex_price),
            'sell_price': max(opportunity.dex_price, opportunity.cex_price),
            'spread_pct': opportunity.spread_pct,
            'type': 'SOLANA_ARB'
        }
        
        risk_check = self.risk_manager.assess_trade(
            trade_signal,
            current_price=opportunity.cex_price
        )
        
        print(f"   Risk Decision: {risk_check.decision}")
        print(f"   Risk Reason: {risk_check.reason}")
        
        if risk_check.decision not in ['APPROVE', 'MODIFY']:
            print(f"   ❌ Trade rejected by risk manager")
            opportunity.action = "RISK_REJECTED"
            return
        
        # Execute based on mode
        if self.mode == "paper":
            # Simulate the swap
            print(f"   📄 PAPER TRADE - Simulating Jupiter swap")
            tx_signature = f"PAPER_{self.solana_trades_executed:04d}_{int(time.time())}"
            execution_status = "FILLED"
            
            # Calculate simulated P&L
            position_size = risk_check.position_size_btc
            expected_profit = position_size * opportunity.cex_price * opportunity.spread_pct
            
            print(f"   Simulated Profit: ${expected_profit:.2f}")
            
        else:
            # Live execution
            if not self.solana_dex.keypair:
                print(f"   ❌ Cannot execute: No Solana wallet loaded")
                opportunity.action = "NO_WALLET"
                return
            
            print(f"   💸 LIVE TRADE - Executing Jupiter swap...")
            tx_signature = self.solana_dex.execute_swap(
                route=jupiter_quote,
                priority_fee_lamports=10000,
                dry_run=False
            )
            execution_status = "FILLED" if tx_signature else "FAILED"
        
        if execution_status == "FILLED":
            self.solana_trades_executed += 1
            opportunity.action = "EXECUTED"
            
            # Log to database
            trade_record = {
                'trade_id': f"SOL_{self.solana_trades_executed:04d}",
                'timestamp': opportunity.timestamp,
                'mode': self.mode,
                'strategy': 'solana_arbitrage',
                'buy_exchange': trade_signal['buy_exchange'],
                'sell_exchange': trade_signal['sell_exchange'],
                'buy_price': trade_signal['buy_price'],
                'sell_price': trade_signal['sell_price'],
                'quantity': risk_check.position_size_btc,
                'spread_pct': opportunity.spread_pct,
                'fees_paid': trade_amount_usd * 0.0035,  # Approx 0.35% fees on Solana
                'net_pnl': expected_profit if self.mode == "paper" else 0,  # Real P&L calculated later
                'latency_ms': 0,
                'status': execution_status,
                'raw_data': json.dumps({
                    'solana_tx': tx_signature,
                    'opportunity': opportunity.__dict__,
                    'risk_check': risk_check.__dict__ if hasattr(risk_check, '__dict__') else risk_check
                })
            }
            
            if self.db:
                self.db.save_trade(trade_record)
                print(f"   💾 Trade saved to database")
            
            # Log to memory
            if self.memory:
                pnl = expected_profit if self.mode == "paper" else 0
                self.memory.log_trade(
                    strategy="solana_arbitrage",
                    pnl=pnl,
                    notes=f"Solana DEX arbitrage: {opportunity.spread_pct:.2%} spread",
                    metadata={
                        "token": pair_config['token'],
                        "spread_pct": opportunity.spread_pct,
                        "mode": self.mode
                    }
                )
            
            # Send alert
            if self.alerts:
                self.alerts.send_trade_alert(trade_record)
            
            print(f"   ✅ Trade executed successfully!")
            if tx_signature and not tx_signature.startswith("PAPER_"):
                print(f"   Transaction: https://solscan.io/tx/{tx_signature}")
        else:
            opportunity.action = "FAILED"
            print(f"   ❌ Trade execution failed")
    
    def _run_solana_scanner(self, interval: int = 30):
        """
        Run Solana scanner in a loop (intended for threading).
        
        Args:
            interval: Seconds between scans
        """
        print(f"[SolanaScanner] Starting scanner thread (interval: {interval}s)")
        
        while not self._stop_event.is_set():
            try:
                self.scan_solana_arbitrage()
            except Exception as e:
                print(f"[SolanaScanner] Error in scan: {e}")
            
            # Wait for interval or until stopped
            self._stop_event.wait(interval)
        
        print("[SolanaScanner] Scanner thread stopped")
    
    def scan_multi_exchange_arbitrage(self, symbol: str = 'BTC/USDT', min_spread_pct: float = 0.002) -> List[Dict[str, Any]]:
        """
        Scan for arbitrage opportunities between multiple CEX exchanges.
        
        Args:
            symbol: Trading pair to scan (e.g., 'BTC/USDT', 'ETH/USDT')
            min_spread_pct: Minimum spread percentage to consider
            
        Returns:
            List of arbitrage opportunities
        """
        print(f"\n{'='*70}")
        print(f"🔍 MULTI-EXCHANGE ARBITRAGE SCAN: {symbol}")
        print(f"{'='*70}")
        
        if not EXECUTION_LAYER_AVAILABLE:
            print("  ❌ Execution Layer not available")
            return []
        
        # Check balances across exchanges
        print("\n💰 Checking Exchange Balances...")
        balances = self.executor.get_all_balances('USDT')
        for exchange_name, balance in balances['exchanges'].items():
            if 'error' not in balance:
                print(f"   {exchange_name.upper()}: ${balance.get('free', 0):,.2f} USDT available")
        print(f"   Total Available: ${balances.get('total_free', 0):,.2f} USDT")
        
        # Find arbitrage opportunities
        opportunities = self.executor.find_arbitrage_opportunities(symbol, min_spread_pct)
        
        if opportunities:
            print(f"\n🎯 Found {len(opportunities)} arbitrage opportunity(s):")
            for i, opp in enumerate(opportunities[:5], 1):
                print(f"\n   {i}. Buy on {opp['buy_exchange'].upper()} @ ${opp['buy_price']:,.2f}")
                print(f"      Sell on {opp['sell_exchange'].upper()} @ ${opp['sell_price']:,.2f}")
                print(f"      Spread: {opp['spread_pct']:.4%} (${opp['spread']:,.2f})")
        else:
            print(f"\nℹ️  No arbitrage opportunities found (min spread: {min_spread_pct:.4%})")
        
        return opportunities
    
    def run_once(self) -> Dict[str, Any]:
        """
        Execute one complete trading cycle (CEX arbitrage).
        
        Returns:
            Complete execution record
        """
        self.run_count += 1
        cycle_start = time.time()
        
        print(f"\n{'='*70}")
        print(f"🔄 CEX TRADING CYCLE #{self.run_count}")
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
            if self.db:
                self.db.save_price('binance', 'BTC/USDT', binance_data)
        else:
            print(f"   ✗ Binance: Failed")
        
        coinbase_data = self.coinbase.fetch_price("BTC-USD")
        if coinbase_data:
            print(f"   ✓ Coinbase: ${coinbase_data['price']:,.2f}")
            prices.append(coinbase_data)
            if self.db:
                self.db.save_price('coinbase', 'BTC/USD', coinbase_data)
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
        
        # ML Prediction Enhancement
        if self.ml_predictor:
            try:
                print("\n   🤖 ML Prediction Analysis...")
                # Get BTC prediction for trend confirmation
                btc_pred = self.ml_predictor.predict('BTC/USDT', '4h')
                print(f"      BTC Trend: {btc_pred.direction} ({btc_pred.confidence:.0f}% confidence)")
                print(f"      Predicted: ${btc_pred.price_now:,.0f} → ${btc_pred.price_predicted:,.0f}")
                
                # Enhance signal with ML insight
                if signal['decision'] == 'TRADE':
                    # If arbitrage signal says BUY on exchange with lower price
                    # but ML predicts DOWN trend, reduce confidence
                    if btc_pred.direction == 'DOWN' and btc_pred.confidence > 70:
                        print(f"      ⚠️  CAUTION: ML predicts downward trend")
                        signal['ml_insight'] = f"DOWN trend {btc_pred.confidence:.0f}% confidence"
                    elif btc_pred.direction == 'UP' and btc_pred.confidence > 70:
                        print(f"      ✅ CONFIRMED: ML supports upward trend")
                        signal['ml_insight'] = f"UP trend {btc_pred.confidence:.0f}% confidence"
                
                result["ml_prediction"] = {
                    "symbol": btc_pred.symbol,
                    "direction": btc_pred.direction,
                    "confidence": btc_pred.confidence,
                    "price_now": btc_pred.price_now,
                    "price_predicted": btc_pred.price_predicted
                }
            except Exception as e:
                print(f"      ML analysis skipped: {e}")
        
        # RL Agent Signal
        if self.rl_available and self.rl_agent:
            try:
                print("\n   🧠 RL Agent Analysis...")
                
                # Prepare market data for RL
                market_data = {
                    'prices': prices,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                rl_signal = self.get_rl_signal(market_data)
                if rl_signal:
                    action_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
                    action_name = action_map.get(rl_signal['action_code'], 'HOLD')
                    print(f"      RL Signal: {action_name}")
                    
                    # Store RL signal in result
                    result["rl_signal"] = rl_signal
                    
                    # Optionally modify signal based on RL (configurable)
                    rl_config = self.config.get('rl', {})
                    if rl_config.get('use_for_execution', False) and rl_signal['action'] != 'HOLD':
                        # RL can override strategy decision if configured
                        print(f"      RL overriding strategy decision")
                        signal['decision'] = 'TRADE'
                        signal['rl_override'] = True
                        signal['rl_action'] = rl_signal['action']
            except Exception as e:
                print(f"      RL analysis skipped: {e}")
        
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
            
            # Save to database
            if self.db and execution.status == "FILLED":
                trade_record = {
                    'trade_id': execution.trade_id,
                    'timestamp': execution.timestamp,
                    'mode': execution.mode,
                    'strategy': 'cex_arbitrage',
                    'buy_exchange': execution.buy_exchange,
                    'sell_exchange': execution.sell_exchange,
                    'buy_price': execution.buy_price,
                    'sell_price': execution.sell_price,
                    'quantity': execution.quantity,
                    'spread_pct': signal.get('spread_pct', 0),
                    'fees_paid': execution.fees_paid,
                    'net_pnl': execution.net_pnl,
                    'latency_ms': execution.total_latency_ms,
                    'status': execution.status,
                    'raw_data': json.dumps(result)
                }
                self.db.save_trade(trade_record)
                
                # Log to memory
                if self.memory:
                    self.memory.log_trade(
                        strategy="cex_arbitrage",
                        pnl=execution.net_pnl or 0,
                        notes=f"CEX arbitrage: {execution.buy_exchange} -> {execution.sell_exchange}",
                        metadata={
                            "spread_pct": signal.get('spread_pct', 0),
                            "mode": execution.mode,
                            "latency_ms": execution.total_latency_ms
                        }
                    )
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
                exec_data = result['execution']
                if isinstance(exec_data, dict) and exec_data.get('status') == "FILLED":
                    self.alerts.send_trade_alert(exec_data)
            
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
                risk_summary = self.risk_manager.get_portfolio_summary()
                dashboard.update_dashboard(
                    prices=result.get('prices', []),
                    trades=[e.__dict__ if hasattr(e, '__dict__') else e for e in self.executor.executions[-10:]],
                    positions=[p.__dict__ if hasattr(p, '__dict__') else p for p in self.risk_manager.positions if p.status == "OPEN"],
                    stats={
                        "total_cycles": self.run_count,
                        "successful_trades": self.executor.successful_executions,
                        "total_pnl": sum(e.net_pnl or 0 for e in self.executor.executions),
                        "daily_pnl": risk_summary.get('daily_pnl', 0),
                        "avg_latency": self.executor.avg_latency_ms,
                        "solana_scans": self.solana_scan_count,
                        "solana_opportunities": self.solana_opportunities_found,
                        "solana_trades": self.solana_trades_executed
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
    
    def run_monitor(self, interval: int = 60, solana_interval: int = 30):
        """
        Run continuous monitoring with both CEX and Solana DEX scanning.
        
        Args:
            interval: Seconds between CEX cycles
            solana_interval: Seconds between Solana DEX scans
        """
        print(f"\n🔁 Starting continuous monitoring...")
        print(f"   CEX Interval: {interval} seconds")
        print(f"   Solana Interval: {solana_interval} seconds")
        print(f"   Press Ctrl+C to stop\n")
        
        # Start Solana scanner in background thread if enabled
        if self.solana_enabled and self.solana_dex:
            self._solana_thread = Thread(
                target=self._run_solana_scanner,
                args=(solana_interval,),
                daemon=True
            )
            self._solana_thread.start()
            print("   Solana DEX scanner started in background\n")
        
        try:
            while True:
                self.run_once()
                
                print(f"\n⏳ Sleeping for {interval} seconds...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            self._stop_event.set()
            self.print_summary()
    
    def print_summary(self):
        """Print complete trading session summary."""
        print("\n" + "=" * 70)
        print("📊 TRADING SESSION SUMMARY")
        print("=" * 70)
        
        duration = datetime.now(timezone.utc) - self.start_time
        
        print(f"\nSession Info:")
        print(f"   Mode: {self.mode.upper()}")
        print(f"   CEX Cycles Run: {self.run_count}")
        print(f"   Duration: {duration}")
        print(f"   Start Time: {self.start_time.isoformat()}")
        
        # Solana Summary
        if self.solana_enabled:
            print(f"\nSolana DEX:")
            print(f"   Scans Completed: {self.solana_scan_count}")
            print(f"   Opportunities Found: {self.solana_opportunities_found}")
            print(f"   Trades Executed: {self.solana_trades_executed}")
        
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
        
        # Database Summary
        if self.db:
            perf_summary = self.db.get_performance_summary(days=1)
            if perf_summary.get('total_trades', 0) > 0:
                print(f"\nDatabase (Last 24h):")
                print(f"   Total Trades: {perf_summary['total_trades']}")
                print(f"   Total P&L: ${perf_summary.get('total_pnl', 0):+,.2f}")
                print(f"   Win Rate: {perf_summary.get('win_rate', 0):.1f}%")
        
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
        description='Trading Bot - End-to-End Orchestrator with Solana DEX',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trading_bot.py --mode paper                    # Single run, paper mode
  python trading_bot.py --mode paper --monitor 60       # Continuous monitoring
  python trading_bot.py --mode live --monitor 60        # Live trading
  python trading_bot.py --test                          # Run module tests
  
Environment Variables for Live Trading:
  BINANCE_API_KEY, BINANCE_SECRET
  COINBASE_API_KEY, COINBASE_SECRET
  SOLANA_PRIVATE_KEY (for DEX trading)
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
        '--solana-interval',
        type=int,
        default=30,
        metavar='SECONDS',
        help='Solana DEX scan interval in seconds (default: 30)'
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
    
    parser.add_argument(
        '--train-rl',
        type=int,
        metavar='EPISODES',
        help='Train RL agent for specified number of episodes'
    )
    
    parser.add_argument(
        '--rl-model',
        type=str,
        default='models/ppo_agent.pkl',
        help='Path to RL model file (default: models/ppo_agent.pkl)'
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
    
    # Handle RL training mode
    if args.train_rl:
        print("=" * 70)
        print("🤖 RL AGENT TRAINING MODE")
        print("=" * 70)
        
        try:
            bot = TradingBot(
                mode='paper',
                log_file=args.log,
                config=config
            )
            
            # Run training
            result = bot.train_rl_agent(
                episodes=args.train_rl,
                save_path=args.rl_model
            )
            
            if 'error' in result:
                print(f"❌ Training failed: {result['error']}")
                sys.exit(1)
            else:
                print("\n✅ Training completed successfully!")
                sys.exit(0)
                
        except Exception as e:
            print(f"\n❌ Fatal Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        return
    
    # Initialize and run bot
    try:
        bot = TradingBot(
            mode=args.mode,
            log_file=args.log,
            config=config
        )
        
        if args.monitor:
            bot.run_monitor(args.monitor, solana_interval=args.solana_interval)
        else:
            # Run one CEX cycle and one Solana scan
            bot.run_once()
            if bot.solana_enabled:
                print("\n" + "=" * 70)
                print("🔍 Running Solana DEX scan...")
                print("=" * 70)
                bot.scan_solana_arbitrage()
            bot.print_summary()
            
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
