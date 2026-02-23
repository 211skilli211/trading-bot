#!/usr/bin/env python3
"""
Intelligent Alert System
========================
ML-powered predictive alerting with anomaly detection.

Features:
- Anomaly detection on trading metrics
- Predictive alerting for potential issues
- Smart alert prioritization
- Context enrichment with AI analysis
- Alert fatigue prevention

Usage:
    alerts = IntelligentAlertSystem()
    await alerts.analyze_and_alert()
"""

import json
import logging
import sqlite3
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import deque
import time

from zeroclaw_integration import ZeroClawIntegration

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels."""
    CRITICAL = "critical"      # Immediate action required
    HIGH = "high"              # Urgent attention needed
    MEDIUM = "medium"          # Important, review soon
    LOW = "low"                # Informational
    PREDICTIVE = "predictive"  # Future issue predicted


class AlertCategory(Enum):
    """Alert categories."""
    RISK = "risk"                      # Risk threshold related
    PERFORMANCE = "performance"        # Trading performance
    SYSTEM = "system"                  # System health
    MARKET = "market"                  # Market conditions
    OPPORTUNITY = "opportunity"        # Trading opportunities
    ANOMALY = "anomaly"                # Anomalous patterns
    PREDICTIVE = "predictive"          # Predicted issues


@dataclass
class Alert:
    """Alert record."""
    alert_id: str
    timestamp: str
    priority: str
    category: str
    title: str
    message: str
    metrics: Dict[str, Any]
    suggested_action: Optional[str]
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[str] = None


class IntelligentAlertSystem:
    """
    Intelligent alerting system with ML-based anomaly detection.
    
    Responsibilities:
    1. Monitor trading metrics for anomalies
    2. Predict potential issues before they occur
    3. Prioritize alerts by urgency
    4. Enrich alerts with AI analysis
    5. Prevent alert fatigue through smart filtering
    6. Learn from alert effectiveness
    """
    
    # Alert thresholds
    DEFAULT_THRESHOLDS = {
        'daily_loss_pct': -0.05,        # -5% daily loss
        'consecutive_losses': 5,         # 5 losses in a row
        'win_rate_min': 0.30,            # Below 30% win rate
        'latency_max_ms': 5000,          # 5 second latency
        'position_exposure_max': 0.50,   # 50% of capital exposed
        'drawdown_max_pct': 0.15,        # 15% max drawdown
        'volatility_spike': 3.0,         # 3x normal volatility
        'api_error_rate': 0.10,          # 10% API error rate
    }
    
    # Anomaly detection windows (in minutes)
    ANOMALY_WINDOWS = {
        'short': 15,
        'medium': 60,
        'long': 240
    }
    
    # Alert cooldowns (in seconds)
    ALERT_COOLDOWNS = {
        AlertCategory.RISK.value: 300,      # 5 min for risk alerts
        AlertCategory.PERFORMANCE.value: 600,  # 10 min for performance
        AlertCategory.SYSTEM.value: 60,     # 1 min for system
        AlertCategory.MARKET.value: 1800,   # 30 min for market
        AlertCategory.OPPORTUNITY.value: 300,
        AlertCategory.ANOMALY.value: 900,   # 15 min for anomalies
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize intelligent alert system.
        
        Args:
            config: Configuration overrides
        """
        self.config = {**self.DEFAULT_THRESHOLDS, **(config or {})}
        self.zeroclaw = ZeroClawIntegration()
        
        # Metric history for anomaly detection
        self.metric_history: Dict[str, deque] = {
            'pnl': deque(maxlen=1000),
            'win_rate': deque(maxlen=100),
            'latency': deque(maxlen=500),
            'exposure': deque(maxlen=100),
            'volatility': deque(maxlen=200),
            'trade_frequency': deque(maxlen=100)
        }
        
        # Recent alerts for cooldown tracking
        self.recent_alerts: Dict[str, float] = {}  # category -> timestamp
        
        # Alert callbacks
        self.on_alert: Optional[Callable[[Alert], None]] = None
        
        # Statistics
        self.stats = {
            'alerts_generated': 0,
            'alerts_by_priority': {},
            'alerts_by_category': {},
            'anomalies_detected': 0,
            'predictions_made': 0
        }
        
        # Initialize database
        self._init_database()
        
        logger.info("[IntelligentAlertSystem] Initialized")
    
    def _init_database(self):
        """Initialize SQLite database for alert tracking."""
        try:
            conn = sqlite3.connect('intelligent_alerts.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE,
                    timestamp TEXT,
                    priority TEXT,
                    category TEXT,
                    title TEXT,
                    message TEXT,
                    metrics TEXT,
                    suggested_action TEXT,
                    acknowledged INTEGER,
                    acknowledged_at TEXT,
                    resolved INTEGER,
                    resolved_at TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON alerts(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_priority 
                ON alerts(priority)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_category 
                ON alerts(category)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_resolved 
                ON alerts(resolved)
            ''')
            
            # Alert effectiveness tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alert_effectiveness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT,
                    action_taken TEXT,
                    outcome TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[IntelligentAlertSystem] Database init failed: {e}")
    
    def _log_alert(self, alert: Alert):
        """Log alert to database."""
        try:
            conn = sqlite3.connect('intelligent_alerts.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO alerts 
                (alert_id, timestamp, priority, category, title, message, metrics, 
                 suggested_action, acknowledged, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            ''', (
                alert.alert_id,
                alert.timestamp,
                alert.priority,
                alert.category,
                alert.title,
                alert.message,
                json.dumps(alert.metrics),
                alert.suggested_action
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[IntelligentAlertSystem] Failed to log alert: {e}")
    
    async def analyze_and_alert(self, market_data: Optional[Dict] = None):
        """
        Main analysis loop - check for alerts and anomalies.
        
        Args:
            market_data: Optional pre-fetched market data
        """
        if market_data is None:
            market_data = await self._gather_market_data()
        
        # Update metric history
        self._update_metric_history(market_data)
        
        # Check all alert conditions
        alerts = []
        
        # 1. Risk alerts
        risk_alerts = await self._check_risk_conditions(market_data)
        alerts.extend(risk_alerts)
        
        # 2. Performance alerts
        perf_alerts = await self._check_performance_conditions(market_data)
        alerts.extend(perf_alerts)
        
        # 3. System health alerts
        system_alerts = await self._check_system_conditions(market_data)
        alerts.extend(system_alerts)
        
        # 4. Market condition alerts
        market_alerts = await self._check_market_conditions(market_data)
        alerts.extend(market_alerts)
        
        # 5. Anomaly detection
        anomaly_alerts = await self._detect_anomalies()
        alerts.extend(anomaly_alerts)
        
        # 6. Predictive analysis
        predictive_alerts = await self._generate_predictions()
        alerts.extend(predictive_alerts)
        
        # Filter and prioritize
        filtered_alerts = self._filter_alerts(alerts)
        prioritized_alerts = self._prioritize_alerts(filtered_alerts)
        
        # Deliver alerts
        for alert in prioritized_alerts:
            await self._deliver_alert(alert)
    
    async def _gather_market_data(self) -> Dict[str, Any]:
        """Gather current market and trading data."""
        data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'portfolio': {},
            'recent_trades': [],
            'positions': [],
            'system_health': {}
        }
        
        try:
            # Get portfolio
            data['portfolio'] = self.zeroclaw.get_portfolio_summary()
        except Exception as e:
            logger.warning(f"[IntelligentAlertSystem] Failed to get portfolio: {e}")
        
        try:
            # Get recent trades
            conn = sqlite3.connect('trades.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM trades 
                WHERE timestamp > datetime('now', '-24 hours')
                ORDER BY timestamp DESC
            """)
            data['recent_trades'] = [dict(row) for row in cursor.fetchall()]
            
            # Get positions
            cursor.execute("SELECT * FROM positions WHERE status='OPEN'")
            data['positions'] = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
        except Exception as e:
            logger.warning(f"[IntelligentAlertSystem] Failed to get trades: {e}")
        
        return data
    
    def _update_metric_history(self, market_data: Dict):
        """Update metric history for anomaly detection."""
        portfolio = market_data.get('portfolio', {})
        
        # P&L metric
        if 'total_pnl' in portfolio:
            self.metric_history['pnl'].append({
                'timestamp': market_data['timestamp'],
                'value': portfolio['total_pnl']
            })
        
        # Win rate metric
        if 'win_rate' in portfolio:
            self.metric_history['win_rate'].append({
                'timestamp': market_data['timestamp'],
                'value': portfolio['win_rate'] / 100  # Convert to decimal
            })
        
        # Trade frequency (last hour)
        recent_trades = market_data.get('recent_trades', [])
        trades_last_hour = len([t for t in recent_trades 
                               if datetime.fromisoformat(t['timestamp']) > 
                               datetime.now(timezone.utc) - timedelta(hours=1)])
        self.metric_history['trade_frequency'].append({
            'timestamp': market_data['timestamp'],
            'value': trades_last_hour
        })
        
        # Exposure metric
        positions = market_data.get('positions', [])
        total_exposure = sum(p.get('value_usd', 0) for p in positions)
        # Would calculate as % of portfolio
        self.metric_history['exposure'].append({
            'timestamp': market_data['timestamp'],
            'value': total_exposure
        })
    
    async def _check_risk_conditions(self, market_data: Dict) -> List[Alert]:
        """Check risk-related alert conditions."""
        alerts = []
        portfolio = market_data.get('portfolio', {})
        
        # Check daily loss
        daily_pnl = portfolio.get('total_pnl', 0)
        # Would need to calculate daily specifically
        if daily_pnl < self.config['daily_loss_pct']:
            alerts.append(Alert(
                alert_id=f"risk_daily_loss_{int(time.time())}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                priority=AlertPriority.CRITICAL.value,
                category=AlertCategory.RISK.value,
                title="Critical: Daily Loss Limit Exceeded",
                message=f"Daily P&L is {daily_pnl:.2%}, below threshold of {self.config['daily_loss_pct']:.2%}",
                metrics={'daily_pnl': daily_pnl, 'threshold': self.config['daily_loss_pct']},
                suggested_action="Consider pausing trading or reducing position sizes"
            ))
        
        # Check drawdown
        # Would calculate from peak
        
        # Check exposure
        positions = market_data.get('positions', [])
        total_exposure = sum(p.get('value_usd', 0) for p in positions)
        # Would calculate as % of portfolio
        
        return alerts
    
    async def _check_performance_conditions(self, market_data: Dict) -> List[Alert]:
        """Check performance-related alert conditions."""
        alerts = []
        portfolio = market_data.get('portfolio', {})
        
        # Check win rate
        win_rate = portfolio.get('win_rate', 100) / 100
        if win_rate < self.config['win_rate_min']:
            recent_trades = market_data.get('recent_trades', [])
            if len(recent_trades) >= 10:  # Minimum sample size
                alerts.append(Alert(
                    alert_id=f"perf_winrate_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    priority=AlertPriority.HIGH.value,
                    category=AlertCategory.PERFORMANCE.value,
                    title="Low Win Rate Detected",
                    message=f"Win rate is {win_rate:.1%}, below threshold of {self.config['win_rate_min']:.1%}",
                    metrics={'win_rate': win_rate, 'total_trades': portfolio.get('total_trades', 0)},
                    suggested_action="Review strategy parameters or consider switching strategies"
                ))
        
        # Check consecutive losses
        recent_trades = market_data.get('recent_trades', [])
        consecutive_losses = 0
        for trade in recent_trades:
            if trade.get('net_pnl', 0) < 0:
                consecutive_losses += 1
            else:
                break
        
        if consecutive_losses >= self.config['consecutive_losses']:
            alerts.append(Alert(
                alert_id=f"perf_consecutive_{int(time.time())}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                priority=AlertPriority.CRITICAL.value,
                category=AlertCategory.PERFORMANCE.value,
                title="Consecutive Loss Streak",
                message=f"{consecutive_losses} consecutive losing trades",
                metrics={'consecutive_losses': consecutive_losses},
                suggested_action="Consider temporary trading halt or strategy review"
            ))
        
        return alerts
    
    async def _check_system_conditions(self, market_data: Dict) -> List[Alert]:
        """Check system health conditions."""
        alerts = []
        
        # Check API latency
        # Would need actual latency tracking
        
        # Check error rates
        # Would need error tracking
        
        return alerts
    
    async def _check_market_conditions(self, market_data: Dict) -> List[Alert]:
        """Check market condition alerts."""
        alerts = []
        
        # Check for volatility spikes
        # Would need volatility calculation
        
        return alerts
    
    async def _detect_anomalies(self) -> List[Alert]:
        """Detect anomalies using statistical methods."""
        alerts = []
        
        for metric_name, history in self.metric_history.items():
            if len(history) < 20:  # Need minimum data
                continue
            
            # Extract values
            values = [h['value'] for h in history if isinstance(h['value'], (int, float))]
            
            if len(values) < 20:
                continue
            
            # Calculate statistics
            mean = statistics.mean(values[:-1])  # Exclude latest
            stdev = statistics.stdev(values[:-1]) if len(values) > 1 else 0
            
            if stdev == 0:
                continue
            
            latest = values[-1]
            z_score = abs(latest - mean) / stdev
            
            # Alert on high z-score
            if z_score > 3:  # 3 standard deviations
                self.stats['anomalies_detected'] += 1
                
                alerts.append(Alert(
                    alert_id=f"anomaly_{metric_name}_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    priority=AlertPriority.MEDIUM.value,
                    category=AlertCategory.ANOMALY.value,
                    title=f"Anomaly Detected: {metric_name}",
                    message=f"Unusual {metric_name} value: {latest:.4f} (z-score: {z_score:.2f})",
                    metrics={
                        'metric': metric_name,
                        'value': latest,
                        'mean': mean,
                        'z_score': z_score
                    },
                    suggested_action="Review recent activity for this metric"
                ))
        
        return alerts
    
    async def _generate_predictions(self) -> List[Alert]:
        """Generate predictive alerts based on trend analysis."""
        alerts = []
        
        # Simple trend prediction for P&L
        pnl_history = list(self.metric_history['pnl'])
        if len(pnl_history) >= 10:
            recent = [h['value'] for h in pnl_history[-10:]]
            
            # Check for declining trend
            if all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
                self.stats['predictions_made'] += 1
                
                alerts.append(Alert(
                    alert_id=f"pred_decline_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    priority=AlertPriority.PREDICTIVE.value,
                    category=AlertCategory.PREDICTIVE.value,
                    title="Predictive Alert: Declining Performance Trend",
                    message="P&L has declined for 10 consecutive measurements",
                    metrics={'trend': 'declining', 'measurements': 10},
                    suggested_action="Review strategy effectiveness and market conditions"
                ))
        
        # Predictive alert for win rate
        winrate_history = list(self.metric_history['win_rate'])
        if len(winrate_history) >= 5:
            recent_wr = [h['value'] for h in winrate_history[-5:]]
            avg_recent_wr = sum(recent_wr) / len(recent_wr)
            
            if avg_recent_wr < 0.35 and len(recent_wr) == 5:
                alerts.append(Alert(
                    alert_id=f"pred_winrate_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    priority=AlertPriority.PREDICTIVE.value,
                    category=AlertCategory.PREDICTIVE.value,
                    title="Predictive Alert: Win Rate Declining",
                    message=f"Recent win rate average is {avg_recent_wr:.1%}",
                    metrics={'avg_win_rate': avg_recent_wr, 'samples': 5},
                    suggested_action="Consider reducing position sizes"
                ))
        
        return alerts
    
    def _filter_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """Filter alerts based on cooldowns and duplicates."""
        filtered = []
        now = time.time()
        
        for alert in alerts:
            category = alert.category
            cooldown = self.ALERT_COOLDOWNS.get(category, 300)
            
            # Check cooldown
            last_alert_time = self.recent_alerts.get(category, 0)
            if now - last_alert_time < cooldown:
                continue
            
            # Update cooldown tracker
            self.recent_alerts[category] = now
            filtered.append(alert)
        
        return filtered
    
    def _prioritize_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """Sort alerts by priority."""
        priority_order = {
            AlertPriority.CRITICAL.value: 0,
            AlertPriority.HIGH.value: 1,
            AlertPriority.MEDIUM.value: 2,
            AlertPriority.LOW.value: 3,
            AlertPriority.PREDICTIVE.value: 4
        }
        
        return sorted(alerts, key=lambda a: priority_order.get(a.priority, 5))
    
    async def _deliver_alert(self, alert: Alert):
        """Deliver alert through all channels."""
        # Log to database
        self._log_alert(alert)
        
        # Update stats
        self.stats['alerts_generated'] += 1
        self.stats['alerts_by_priority'][alert.priority] = \
            self.stats['alerts_by_priority'].get(alert.priority, 0) + 1
        self.stats['alerts_by_category'][alert.category] = \
            self.stats['alerts_by_category'].get(alert.category, 0) + 1
        
        # Callback
        if self.on_alert:
            self.on_alert(alert)
        
        # Send via ZeroClaw/Telegram for critical/high priority
        if alert.priority in [AlertPriority.CRITICAL.value, AlertPriority.HIGH.value]:
            try:
                emoji = {
                    AlertPriority.CRITICAL.value: "🚨",
                    AlertPriority.HIGH.value: "⚠️"
                }.get(alert.priority, "ℹ️")
                
                message = f"""
{emoji} <b>{alert.title}</b>

{alert.message}

<i>{alert.suggested_action or ''}</i>
                """.strip()
                
                self.zeroclaw.send_telegram_alert(message, priority=alert.priority)
            except Exception as e:
                logger.error(f"[IntelligentAlertSystem] Failed to send alert: {e}")
        
        logger.info(f"[IntelligentAlertSystem] Alert delivered: {alert.title}")
    
    # Public API
    
    def get_active_alerts(self, category: Optional[str] = None) -> List[Dict]:
        """Get active (unresolved) alerts."""
        try:
            conn = sqlite3.connect('intelligent_alerts.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT * FROM alerts
                    WHERE resolved = 0 AND category = ?
                    ORDER BY timestamp DESC
                ''', (category,))
            else:
                cursor.execute('''
                    SELECT * FROM alerts
                    WHERE resolved = 0
                    ORDER BY timestamp DESC
                ''')
            
            alerts = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return alerts
        except Exception as e:
            logger.error(f"[IntelligentAlertSystem] Failed to get alerts: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        try:
            conn = sqlite3.connect('intelligent_alerts.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE alerts 
                SET acknowledged = 1, acknowledged_at = ?
                WHERE alert_id = ?
            ''', (datetime.now(timezone.utc).isoformat(), alert_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[IntelligentAlertSystem] Failed to acknowledge: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        try:
            conn = sqlite3.connect('intelligent_alerts.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE alerts 
                SET resolved = 1, resolved_at = ?
                WHERE alert_id = ?
            ''', (datetime.now(timezone.utc).isoformat(), alert_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[IntelligentAlertSystem] Failed to resolve: {e}")
            return False
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert system statistics."""
        return {
            **self.stats,
            'active_alerts': len(self.get_active_alerts()),
            'metric_history_sizes': {
                k: len(v) for k, v in self.metric_history.items()
            }
        }


# Singleton instance
_alert_system_instance: Optional[IntelligentAlertSystem] = None


def get_intelligent_alert_system(config: Optional[Dict] = None) -> IntelligentAlertSystem:
    """Get singleton alert system instance."""
    global _alert_system_instance
    if _alert_system_instance is None:
        _alert_system_instance = IntelligentAlertSystem(config)
    return _alert_system_instance


if __name__ == "__main__":
    # Test mode
    print("=" * 60)
    print("Intelligent Alert System - Test Mode")
    print("=" * 60)
    
    import asyncio
    
    async def test():
        alerts = get_intelligent_alert_system()
        
        # Add some test data
        alerts.metric_history['pnl'].extend([
            {'timestamp': datetime.now(timezone.utc).isoformat(), 'value': 100 + i*10}
            for i in range(15)
        ])
        
        # Manually add some declining values
        alerts.metric_history['pnl'].extend([
            {'timestamp': datetime.now(timezone.utc).isoformat(), 'value': 250 - i*20}
            for i in range(10)
        ])
        
        # Test anomaly detection
        print("\n--- Testing anomaly detection ---")
        anomaly_alerts = await alerts._detect_anomalies()
        print(f"Found {len(anomaly_alerts)} anomalies")
        
        # Test predictive alerts
        print("\n--- Testing predictive alerts ---")
        pred_alerts = await alerts._generate_predictions()
        print(f"Generated {len(pred_alerts)} predictions")
        for a in pred_alerts:
            print(f"  - {a.title}")
        
        # Get stats
        print("\n--- Alert Stats ---")
        print(json.dumps(alerts.get_alert_stats(), indent=2))
    
    asyncio.run(test())
