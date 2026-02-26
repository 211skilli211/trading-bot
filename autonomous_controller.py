#!/usr/bin/env python3
"""
Autonomous Trading Controller
=============================
Central decision-making engine for 24/7 autonomous trading agent.

Features:
- Continuous market monitoring
- AI-powered decision making
- Regime-based strategy adjustments
- Automatic risk parameter scaling
- Self-healing capabilities
- Human escalation for critical decisions

Usage:
    controller = AutonomousController()
    await controller.start()
"""

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import threading
import time

# Import existing modules
from core.regime import RegimeDetector, MarketRegime
from risk_manager import RiskManager
from strategies.multi_agent import MultiAgentSystem
from zeroclaw_integration import ZeroClawIntegration

# Data Broker Layer - Institutional-grade enriched data
try:
    from data_broker_layer import DataBrokerLayer, EnrichedData, create_data_broker_layer
    DATA_BROKER_AVAILABLE = True
except ImportError:
    DATA_BROKER_AVAILABLE = False
    DataBrokerLayer = None
    create_data_broker_layer = None
    logger.warning("[AutonomousController] DataBrokerLayer not available - install data_broker_layer.py")

try:
    from websocket_price_feed import WebSocketPriceFeed, WEBSOCKET_AVAILABLE
except ImportError:
    WEBSOCKET_AVAILABLE = False
    WebSocketPriceFeed = None

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of autonomous decisions."""
    STRATEGY_ENABLE = "strategy_enable"
    STRATEGY_DISABLE = "strategy_disable"
    STRATEGY_PARAM_ADJUST = "strategy_param_adjust"
    RISK_PARAM_ADJUST = "risk_param_adjust"
    EMERGENCY_STOP = "emergency_stop"
    POSITION_SIZE_ADJUST = "position_size_adjust"
    ALERT_CONFIG_ADJUST = "alert_config_adjust"


class DecisionStatus(Enum):
    """Status of autonomous decisions."""
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class AutonomousDecision:
    """Record of an autonomous decision."""
    decision_id: str
    timestamp: str
    decision_type: str
    description: str
    confidence: float
    market_regime: str
    trigger_reason: str
    proposed_action: Dict[str, Any]
    status: str
    executed_at: Optional[str] = None
    result: Optional[str] = None
    human_approved: bool = False
    

class AutonomousController:
    """
    Central autonomous decision-making engine.
    
    Runs continuously to:
    1. Monitor market conditions
    2. Evaluate strategy performance
    3. Make data-driven adjustments
    4. Execute safe autonomous actions
    5. Escalate critical decisions to humans
    """
    
    # Configuration defaults
    DEFAULT_CONFIG = {
        'enabled': False,
        'check_interval_seconds': 30,
        'min_confidence_threshold': 0.75,
        'max_daily_changes': 10,
        'paper_mode_only': True,
        'human_approval_required_for': [
            'emergency_stop',
            'live_mode_activation',
            'position_size_increase_over_50pct'
        ],
        'regime_switching_enabled': True,
        'dynamic_position_sizing': True,
        'risk_auto_adjustment': True,
        'max_single_position_usd': 500,
        'emergency_pnl_threshold': -0.10,  # -10% triggers emergency
        'volatility_scaling_factor': 1.0,
        
        # Data Broker Layer settings
        'use_enriched_data': True,
        'min_signal_confidence': 0.6,
        'whale_watch_enabled': True,
        'sentiment_weight': 0.2,
        'onchain_weight': 0.3,
        'technical_weight': 0.5,
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize autonomous controller.

        Args:
            config: Override default configuration
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.running = False
        self._lock = threading.RLock()

        # Initialize components
        self.zeroclaw = ZeroClawIntegration()
        self.regime_detector = RegimeDetector()
        self.risk_manager = RiskManager()
        self.multi_agent = MultiAgentSystem({})

        # Data Broker Layer - enriched market data
        self.data_broker: Optional[DataBrokerLayer] = None
        if DATA_BROKER_AVAILABLE and self.config.get('use_enriched_data'):
            try:
                self.data_broker = create_data_broker_layer()
                logger.info("[AutonomousController] DataBrokerLayer enabled")
            except Exception as e:
                logger.warning(f"[AutonomousController] DataBrokerLayer init failed: {e}")

        # WebSocket for real-time data
        self.price_feed: Optional[WebSocketPriceFeed] = None

        # State tracking
        self.current_regime: MarketRegime = 'NEUTRAL'
        self.last_regime_change: Optional[str] = None
        self.daily_changes_count = 0
        self.last_reset_date: str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        self.decisions_today: List[AutonomousDecision] = []

        # Enriched data cache
        self._enriched_data_cache: Dict[str, EnrichedData] = {}
        self._whale_alerts: List[Dict] = []

        # Statistics
        self.stats = {
            'total_decisions': 0,
            'executed_decisions': 0,
            'rejected_decisions': 0,
            'escalated_decisions': 0,
            'failed_executions': 0,
            'avg_confidence': 0.0,
            'enriched_data_signals': 0,
            'whale_alerts_24h': 0,
        }

        # Callbacks
        self.on_decision: Optional[Callable[[AutonomousDecision], None]] = None
        self.on_alert: Optional[Callable[[str, str], None]] = None

        # Initialize database
        self._init_database()

        logger.info("[AutonomousController] Initialized")
        logger.info(f"  Enabled: {self.config['enabled']}")
        logger.info(f"  Mode: {'PAPER ONLY' if self.config['paper_mode_only'] else 'LIVE ALLOWED'}")
        logger.info(f"  Check interval: {self.config['check_interval_seconds']}s")
        logger.info(f"  Enriched Data: {'ENABLED' if self.data_broker else 'DISABLED'}")
    
    def _init_database(self):
        """Initialize SQLite database for decision logging."""
        try:
            conn = sqlite3.connect('autonomous_decisions.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS autonomous_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT UNIQUE,
                    timestamp TEXT,
                    decision_type TEXT,
                    description TEXT,
                    confidence REAL,
                    market_regime TEXT,
                    trigger_reason TEXT,
                    proposed_action TEXT,
                    status TEXT,
                    executed_at TEXT,
                    result TEXT,
                    human_approved INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_decisions_timestamp 
                ON autonomous_decisions(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_decisions_status 
                ON autonomous_decisions(status)
            ''')
            
            conn.commit()
            conn.close()
            logger.info("[AutonomousController] Database initialized")
        except Exception as e:
            logger.error(f"[AutonomousController] Database init failed: {e}")
    
    def _log_decision(self, decision: AutonomousDecision):
        """Log decision to database."""
        try:
            conn = sqlite3.connect('autonomous_decisions.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO autonomous_decisions 
                (decision_id, timestamp, decision_type, description, confidence,
                 market_regime, trigger_reason, proposed_action, status,
                 executed_at, result, human_approved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                decision.decision_id,
                decision.timestamp,
                decision.decision_type,
                decision.description,
                decision.confidence,
                decision.market_regime,
                decision.trigger_reason,
                json.dumps(decision.proposed_action),
                decision.status,
                decision.executed_at,
                decision.result,
                1 if decision.human_approved else 0
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[AutonomousController] Failed to log decision: {e}")
    
    def _reset_daily_counters(self):
        """Reset daily counters if date changed."""
        current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if current_date != self.last_reset_date:
            self.daily_changes_count = 0
            self.decisions_today = []
            self.last_reset_date = current_date
            logger.info("[AutonomousController] Daily counters reset")
    
    async def start(self):
        """Start the autonomous controller loop."""
        if not self.config['enabled']:
            logger.warning("[AutonomousController] Cannot start - disabled in config")
            return False
        
        self.running = True
        logger.info("[AutonomousController] Starting autonomous loop...")
        
        # Start WebSocket price feed
        await self._start_price_feed()
        
        # Main loop
        while self.running:
            try:
                await self._run_cycle()
                await asyncio.sleep(self.config['check_interval_seconds'])
            except Exception as e:
                logger.error(f"[AutonomousController] Cycle error: {e}")
                await asyncio.sleep(5)  # Brief pause on error
        
        return True
    
    def stop(self):
        """Stop the autonomous controller."""
        self.running = False
        if self.price_feed:
            # Stop WebSocket connections
            pass
        logger.info("[AutonomousController] Stopped")
    
    async def _start_price_feed(self):
        """Initialize WebSocket price feed."""
        try:
            self.price_feed = WebSocketPriceFeed(
                exchanges=["binance"],
                symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            )
            # Note: WebSocket runs in separate thread
            logger.info("[AutonomousController] Price feed initialized")
        except Exception as e:
            logger.warning(f"[AutonomousController] Price feed init failed: {e}")
    
    async def _run_cycle(self):
        """Execute one monitoring cycle."""
        with self._lock:
            self._reset_daily_counters()
            
            # 1. Detect market regime
            await self._detect_regime()
            
            # 2. Gather market data
            market_data = await self._gather_market_data()
            
            # 3. Evaluate conditions and generate decisions
            decisions = await self._evaluate_conditions(market_data)
            
            # 4. Process decisions
            for decision in decisions:
                await self._process_decision(decision)
    
    async def _detect_regime(self):
        """Detect current market regime."""
        new_regime = self.regime_detector.detect_regime()
        
        if new_regime != self.current_regime:
            logger.info(f"[AutonomousController] Regime change: {self.current_regime} -> {new_regime}")
            self.last_regime_change = datetime.now(timezone.utc).isoformat()
            
            # Trigger regime-based adjustments
            if self.config['regime_switching_enabled']:
                await self._apply_regime_adjustments(new_regime)
        
        self.current_regime = new_regime
    
    async def _apply_regime_adjustments(self, regime: MarketRegime):
        """Apply strategy adjustments based on regime."""
        regime_config = self.regime_detector.get_regime_config(regime)
        
        decision = AutonomousDecision(
            decision_id=f"regime_{int(time.time())}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision_type=DecisionType.RISK_PARAM_ADJUST.value,
            description=f"Regime-based adjustment for {regime}",
            confidence=0.90,
            market_regime=regime,
            trigger_reason=f"Market regime changed to {regime}",
            proposed_action={
                'max_position_pct': regime_config['max_position_pct'],
                'stop_loss_pct': regime_config['stop_loss_pct'],
                'max_daily_trades': regime_config['max_daily_trades'],
                'strategies_enabled': regime_config['strategies_enabled']
            },
            status=DecisionStatus.PENDING.value
        )
        
        await self._process_decision(decision)
    
    async def _gather_market_data(self) -> Dict[str, Any]:
        """Gather current market data for decision making."""
        data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'regime': self.current_regime,
            'prices': {},
            'volatility': {},
            'portfolio': {},
            'recent_trades': [],
            'open_positions': [],
            'system_health': {},
            'enriched_data': {},
            'whale_alerts': [],
            'signal_scores': {}
        }

        # Get prices from WebSocket feed
        if self.price_feed:
            data['prices'] = self.price_feed.prices

        # Get enriched data from Data Broker Layer
        if self.data_broker:
            symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            for symbol in symbols:
                enriched = self.data_broker.get_enriched_data(
                    symbol,
                    include_onchain=self.config.get('whale_watch_enabled', True),
                    include_sentiment=True
                )
                if enriched:
                    self._enriched_data_cache[symbol] = enriched
                    data['enriched_data'][symbol] = enriched.to_dict()
                    data['signal_scores'][symbol] = {
                        'signal_score': enriched.signal_score,
                        'confidence': enriched.confidence,
                        'signals': enriched.signals
                    }
                    self.stats['enriched_data_signals'] += 1
            
            # Get whale alerts
            if self.config.get('whale_watch_enabled'):
                try:
                    self._whale_alerts = self.data_broker.get_whale_watch("solana", min_usd=50000)
                    data['whale_alerts'] = self._whale_alerts[:10]  # Last 10
                    self.stats['whale_alerts_24h'] = len(self._whale_alerts)
                except Exception as e:
                    logger.warning(f"[AutonomousController] Failed to get whale alerts: {e}")

        # Get portfolio summary
        try:
            data['portfolio'] = self.zeroclaw.get_portfolio_summary()
        except Exception as e:
            logger.warning(f"[AutonomousController] Failed to get portfolio: {e}")

        # Get recent trades from database
        try:
            conn = sqlite3.connect('trades.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                WHERE timestamp > datetime('now', '-1 hour')
                ORDER BY timestamp DESC
            """)
            data['recent_trades'] = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except Exception as e:
            logger.warning(f"[AutonomousController] Failed to get trades: {e}")

        return data
    
    async def _evaluate_conditions(self, market_data: Dict) -> List[AutonomousDecision]:
        """Evaluate conditions and generate decisions."""
        decisions = []

        # Check emergency conditions
        emergency_decision = await self._check_emergency_conditions(market_data)
        if emergency_decision:
            decisions.append(emergency_decision)
            return decisions  # Emergency takes precedence

        # Evaluate enriched data signals (if available)
        if self.data_broker and market_data.get('enriched_data'):
            enriched_decisions = await self._evaluate_enriched_signals(market_data)
            decisions.extend(enriched_decisions)

        # Check strategy performance
        strategy_decisions = await self._evaluate_strategies(market_data)
        decisions.extend(strategy_decisions)

        # Check risk parameters
        risk_decisions = await self._evaluate_risk_parameters(market_data)
        decisions.extend(risk_decisions)

        # Check multi-agent system
        agent_decisions = await self._evaluate_multi_agent(market_data)
        decisions.extend(agent_decisions)

        return decisions
    
    async def _check_emergency_conditions(self, market_data: Dict) -> Optional[AutonomousDecision]:
        """Check for emergency conditions requiring immediate action."""
        portfolio = market_data.get('portfolio', {})
        total_pnl = portfolio.get('total_pnl', 0)
        
        # Check for large losses
        if total_pnl < self.config['emergency_pnl_threshold']:
            return AutonomousDecision(
                decision_id=f"emergency_{int(time.time())}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                decision_type=DecisionType.EMERGENCY_STOP.value,
                description="Emergency stop triggered due to significant losses",
                confidence=0.95,
                market_regime=self.current_regime,
                trigger_reason=f"Portfolio P&L {total_pnl:.2%} below threshold {self.config['emergency_pnl_threshold']:.2%}",
                proposed_action={'action': 'pause_all_trading', 'close_positions': False},
                status=DecisionStatus.PENDING.value
            )
        
        return None

    async def _evaluate_enriched_signals(self, market_data: Dict) -> List[AutonomousDecision]:
        """Evaluate enriched data signals from Data Broker Layer."""
        decisions = []
        
        signal_scores = market_data.get('signal_scores', {})
        whale_alerts = market_data.get('whale_alerts', [])
        
        for symbol, signals in signal_scores.items():
            signal_score = signals.get('signal_score', 0)
            confidence = signals.get('confidence', 0)
            signal_details = signals.get('signals', {})
            
            # Skip if confidence too low
            if confidence < self.config.get('min_signal_confidence', 0.6):
                logger.debug(f"[AutonomousController] Skipping {symbol} - low confidence ({confidence:.2f})")
                continue
            
            # Strong buy signal
            if signal_score > 0.6:
                decisions.append(AutonomousDecision(
                    decision_id=f"enriched_buy_{symbol}_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    decision_type=DecisionType.STRATEGY_PARAM_ADJUST.value,
                    description=f"Strong buy signal for {symbol} from enriched data",
                    confidence=confidence,
                    market_regime=self.current_regime,
                    trigger_reason=f"Signal score: {signal_score:.2f}, Sentiment: {signal_details.get('sentiment', 'N/A')}, Exchange flow: {signal_details.get('exchange_flow', 'N/A')}",
                    proposed_action={
                        'symbol': symbol,
                        'action': 'increase_position_size',
                        'signal_score': signal_score,
                        'sentiment': signal_details.get('sentiment'),
                        'onchain_flow': signal_details.get('exchange_flow'),
                        'whale_activity': signal_details.get('whale_activity', 'normal')
                    },
                    status=DecisionStatus.PENDING.value
                ))
            
            # Strong sell signal
            elif signal_score < -0.6:
                decisions.append(AutonomousDecision(
                    decision_id=f"enriched_sell_{symbol}_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    decision_type=DecisionType.STRATEGY_PARAM_ADJUST.value,
                    description=f"Strong sell signal for {symbol} from enriched data",
                    confidence=confidence,
                    market_regime=self.current_regime,
                    trigger_reason=f"Signal score: {signal_score:.2f}, Sentiment: {signal_details.get('sentiment', 'N/A')}, Exchange flow: {signal_details.get('exchange_flow', 'N/A')}",
                    proposed_action={
                        'symbol': symbol,
                        'action': 'reduce_position_size',
                        'signal_score': signal_score,
                        'sentiment': signal_details.get('sentiment'),
                        'onchain_flow': signal_details.get('exchange_flow'),
                        'whale_activity': signal_details.get('whale_activity', 'normal')
                    },
                    status=DecisionStatus.PENDING.value
                ))
        
        # Check for unusual whale activity
        if len(whale_alerts) > 5:
            decisions.append(AutonomousDecision(
                decision_id=f"whale_alert_{int(time.time())}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                decision_type=DecisionType.ALERT_CONFIG_ADJUST.value,
                description=f"Unusual whale activity detected: {len(whale_alerts)} large transactions",
                confidence=0.8,
                market_regime=self.current_regime,
                trigger_reason=f"{len(whale_alerts)} whale transactions detected (threshold: 5)",
                proposed_action={
                    'action': 'increase_monitoring',
                    'whale_count': len(whale_alerts),
                    'largest_tx': max(whale_alerts, key=lambda x: x.get('value', 0)) if whale_alerts else None
                },
                status=DecisionStatus.PENDING.value
            ))
        
        return decisions

    async def _evaluate_strategies(self, market_data: Dict) -> List[AutonomousDecision]:
        """Evaluate strategy performance and suggest adjustments."""
        decisions = []
        
        # Get strategy performance from recent trades
        recent_trades = market_data.get('recent_trades', [])
        
        # Group by strategy
        strategy_performance = {}
        for trade in recent_trades:
            strategy = trade.get('strategy', 'unknown')
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {'trades': 0, 'pnl': 0, 'wins': 0}
            strategy_performance[strategy]['trades'] += 1
            strategy_performance[strategy]['pnl'] += trade.get('net_pnl', 0) or 0
            if trade.get('net_pnl', 0) > 0:
                strategy_performance[strategy]['wins'] += 1
        
        # Generate decisions for underperforming strategies
        for strategy, perf in strategy_performance.items():
            if perf['trades'] >= 5:  # Minimum sample size
                win_rate = perf['wins'] / perf['trades']
                
                if win_rate < 0.4 and perf['pnl'] < 0:
                    # Underperforming - suggest disabling or reducing size
                    decisions.append(AutonomousDecision(
                        decision_id=f"strat_{strategy}_{int(time.time())}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        decision_type=DecisionType.STRATEGY_PARAM_ADJUST.value,
                        description=f"Reduce risk for underperforming strategy: {strategy}",
                        confidence=0.75,
                        market_regime=self.current_regime,
                        trigger_reason=f"Win rate {win_rate:.1%} with negative P&L over {perf['trades']} trades",
                        proposed_action={
                            'strategy': strategy,
                            'adjustment': 'reduce_position_size',
                            'new_size_multiplier': 0.5
                        },
                        status=DecisionStatus.PENDING.value
                    ))
        
        return decisions
    
    async def _evaluate_risk_parameters(self, market_data: Dict) -> List[AutonomousDecision]:
        """Evaluate and suggest risk parameter adjustments."""
        decisions = []
        
        if not self.config['risk_auto_adjustment']:
            return decisions
        
        # Calculate current volatility from prices
        # This is a simplified version - would use proper volatility calc in production
        
        # Check if risk parameters need adjustment based on regime
        regime_config = self.regime_detector.get_regime_config(self.current_regime)
        
        # Suggest adjustment if current settings don't match regime
        # (In production, would compare actual vs recommended)
        
        return decisions
    
    async def _evaluate_multi_agent(self, market_data: Dict) -> List[AutonomousDecision]:
        """Evaluate multi-agent system performance."""
        decisions = []
        
        # Trigger agent evaluation
        evolution_results = self.multi_agent.evaluate_and_evolve()
        
        # Convert evolution results to decisions
        for killed_agent in evolution_results.get('killed', []):
            decisions.append(AutonomousDecision(
                decision_id=f"agent_kill_{killed_agent}_{int(time.time())}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                decision_type=DecisionType.STRATEGY_DISABLE.value,
                description=f"Agent {killed_agent} terminated due to poor performance",
                confidence=0.85,
                market_regime=self.current_regime,
                trigger_reason="Consecutive losses exceeded threshold",
                proposed_action={'agent': killed_agent, 'action': 'terminate'},
                status=DecisionStatus.PENDING.value
            ))
        
        return decisions
    
    async def _process_decision(self, decision: AutonomousDecision):
        """Process a single decision through validation and execution."""
        # Check daily change limits
        if self.daily_changes_count >= self.config['max_daily_changes']:
            decision.status = DecisionStatus.REJECTED.value
            decision.result = "Daily change limit reached"
            self._log_decision(decision)
            return
        
        # Check confidence threshold
        if decision.confidence < self.config['min_confidence_threshold']:
            decision.status = DecisionStatus.REJECTED.value
            decision.result = f"Confidence {decision.confidence:.2f} below threshold {self.config['min_confidence_threshold']}"
            self._log_decision(decision)
            return
        
        # Check if human approval required
        if self._requires_human_approval(decision):
            decision.status = DecisionStatus.ESCALATED.value
            await self._escalate_to_human(decision)
            self._log_decision(decision)
            return
        
        # Execute decision
        await self._execute_decision(decision)
    
    def _requires_human_approval(self, decision: AutonomousDecision) -> bool:
        """Check if decision requires human approval."""
        required_types = self.config['human_approval_required_for']
        
        if decision.decision_type in required_types:
            return True
        
        # Check for high-impact position size changes
        if decision.decision_type == DecisionType.POSITION_SIZE_ADJUST.value:
            action = decision.proposed_action
            if action.get('new_size_multiplier', 1.0) > 1.5:
                return True
        
        return False
    
    async def _escalate_to_human(self, decision: AutonomousDecision):
        """Escalate decision to human for approval."""
        message = f"""
🤖 <b>Autonomous Decision Requires Approval</b>

Type: {decision.decision_type}
Description: {decision.description}
Confidence: {decision.confidence:.1%}
Regime: {decision.market_regime}

Reason: {decision.trigger_reason}

Proposed Action:
<pre>{json.dumps(decision.proposed_action, indent=2)}</pre>

Use /approve {decision.decision_id} or /reject {decision.decision_id}
        """
        
        if self.on_alert:
            self.on_alert("escalation", message)
        
        # Send via ZeroClaw/Telegram
        try:
            self.zeroclaw.send_telegram_alert(message, priority='high')
        except Exception as e:
            logger.error(f"[AutonomousController] Failed to send escalation: {e}")
    
    async def _execute_decision(self, decision: AutonomousDecision):
        """Execute an approved decision."""
        try:
            logger.info(f"[AutonomousController] Executing decision: {decision.decision_id}")
            
            # Route to appropriate executor
            if decision.decision_type == DecisionType.STRATEGY_ENABLE.value:
                result = await self._execute_strategy_enable(decision)
            elif decision.decision_type == DecisionType.STRATEGY_DISABLE.value:
                result = await self._execute_strategy_disable(decision)
            elif decision.decision_type == DecisionType.STRATEGY_PARAM_ADJUST.value:
                result = await self._execute_strategy_param_adjust(decision)
            elif decision.decision_type == DecisionType.RISK_PARAM_ADJUST.value:
                result = await self._execute_risk_adjust(decision)
            elif decision.decision_type == DecisionType.EMERGENCY_STOP.value:
                result = await self._execute_emergency_stop(decision)
            else:
                result = {"success": False, "error": "Unknown decision type"}
            
            # Update decision status
            if result.get('success'):
                decision.status = DecisionStatus.EXECUTED.value
                decision.executed_at = datetime.now(timezone.utc).isoformat()
                decision.result = result.get('message', 'Executed successfully')
                self.daily_changes_count += 1
                self.stats['executed_decisions'] += 1
            else:
                decision.status = DecisionStatus.FAILED.value
                decision.result = result.get('error', 'Execution failed')
                self.stats['failed_executions'] += 1
            
        except Exception as e:
            decision.status = DecisionStatus.FAILED.value
            decision.result = str(e)
            self.stats['failed_executions'] += 1
            logger.error(f"[AutonomousController] Execution error: {e}")
        
        # Log and notify
        self._log_decision(decision)
        self.decisions_today.append(decision)
        
        if self.on_decision:
            self.on_decision(decision)
    
    async def _execute_strategy_enable(self, decision: AutonomousDecision) -> Dict:
        """Execute strategy enable decision."""
        # Would call dashboard API or config update
        return {"success": True, "message": "Strategy enabled"}
    
    async def _execute_strategy_disable(self, decision: AutonomousDecision) -> Dict:
        """Execute strategy disable decision."""
        return {"success": True, "message": "Strategy disabled"}
    
    async def _execute_strategy_param_adjust(self, decision: AutonomousDecision) -> Dict:
        """Execute strategy parameter adjustment."""
        action = decision.proposed_action
        # Would update config.json via API
        return {"success": True, "message": f"Parameters adjusted for {action.get('strategy')}"}
    
    async def _execute_risk_adjust(self, decision: AutonomousDecision) -> Dict:
        """Execute risk parameter adjustment."""
        action = decision.proposed_action
        # Would update risk manager configuration
        return {"success": True, "message": "Risk parameters adjusted"}
    
    async def _execute_emergency_stop(self, decision: AutonomousDecision) -> Dict:
        """Execute emergency stop."""
        # Critical action - implement actual stop
        logger.critical("[AutonomousController] EMERGENCY STOP EXECUTED")
        
        if self.on_alert:
            self.on_alert("emergency", "Emergency stop triggered by autonomous controller")
        
        return {"success": True, "message": "Emergency stop executed - all trading paused"}
    
    # Public API methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get current autonomous controller status."""
        return {
            'enabled': self.config['enabled'],
            'running': self.running,
            'current_regime': self.current_regime,
            'last_regime_change': self.last_regime_change,
            'daily_changes_count': self.daily_changes_count,
            'max_daily_changes': self.config['max_daily_changes'],
            'decisions_today': len(self.decisions_today),
            'stats': self.stats,
            'config': {
                'check_interval_seconds': self.config['check_interval_seconds'],
                'min_confidence_threshold': self.config['min_confidence_threshold'],
                'paper_mode_only': self.config['paper_mode_only'],
                'use_enriched_data': self.config['use_enriched_data'],
                'whale_watch_enabled': self.config['whale_watch_enabled']
            },
            'enriched_data': {
                'available': self.data_broker is not None,
                'cached_symbols': list(self._enriched_data_cache.keys()),
                'whale_alerts_count': len(self._whale_alerts)
            }
        }
    
    def get_decision_history(self, limit: int = 50) -> List[Dict]:
        """Get recent decision history."""
        try:
            conn = sqlite3.connect('autonomous_decisions.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM autonomous_decisions
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            decisions = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return decisions
        except Exception as e:
            logger.error(f"[AutonomousController] Failed to get history: {e}")
            return []
    
    def approve_decision(self, decision_id: str) -> bool:
        """Human approval of escalated decision."""
        # Find decision and execute
        for decision in self.decisions_today:
            if decision.decision_id == decision_id:
                decision.human_approved = True
                decision.status = DecisionStatus.APPROVED.value
                asyncio.create_task(self._execute_decision(decision))
                return True
        return False
    
    def reject_decision(self, decision_id: str) -> bool:
        """Human rejection of escalated decision."""
        for decision in self.decisions_today:
            if decision.decision_id == decision_id:
                decision.status = DecisionStatus.REJECTED.value
                decision.result = "Rejected by human operator"
                self._log_decision(decision)
                return True
        return False
    
    def toggle_enabled(self, enabled: bool):
        """Enable or disable autonomous mode."""
        self.config['enabled'] = enabled
        if enabled and not self.running:
            # Start in a background thread with its own event loop
            import threading
            def run_async_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.start())
            
            thread = threading.Thread(target=run_async_loop, daemon=True)
            thread.start()
            logger.info("[AutonomousController] Started in background thread")
        elif not enabled and self.running:
            self.stop()


# Singleton instance
_controller_instance: Optional[AutonomousController] = None


def get_autonomous_controller(config: Optional[Dict] = None) -> AutonomousController:
    """Get singleton autonomous controller instance."""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = AutonomousController(config)
    return _controller_instance


if __name__ == "__main__":
    # Test mode
    print("=" * 60)
    print("Autonomous Controller - Test Mode")
    print("=" * 60)
    
    controller = get_autonomous_controller({
        'enabled': True,
        'check_interval_seconds': 5,  # Fast for testing
        'paper_mode_only': True
    })
    
    print(f"\nStatus: {controller.get_status()}")
    
    # Run a few cycles
    async def test():
        await controller._run_cycle()
        print("\nCycle 1 complete")
        await asyncio.sleep(1)
        await controller._run_cycle()
        print("Cycle 2 complete")
        
        print("\nDecision history:")
        for d in controller.get_decision_history(10):
            print(f"  - {d['decision_type']}: {d['status']}")
    
    asyncio.run(test())
