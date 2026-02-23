#!/usr/bin/env python3
"""
Dynamic Configuration Manager
=============================
Self-adjusting trading configuration based on market conditions.

Features:
- Regime-based parameter adjustments
- Volatility-scaled position sizing
- Performance feedback loop
- Safety bounds enforcement
- Rollback capability

Usage:
    manager = DynamicConfigManager()
    await manager.apply_regime_adjustments('DEFENSIVE')
"""

import json
import logging
import sqlite3
from copy import deepcopy
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from core.regime import MarketRegime

logger = logging.getLogger(__name__)


@dataclass
class ConfigChange:
    """Record of a configuration change."""
    change_id: str
    timestamp: str
    regime: str
    trigger: str
    original_value: Any
    new_value: Any
    parameter_path: str  # e.g., "strategies.arbitrage.max_position_usd"
    rolled_back: bool = False
    rollback_timestamp: Optional[str] = None


class DynamicConfigManager:
    """
    Manages dynamic configuration adjustments for the trading bot.
    
    Responsibilities:
    1. Load and validate configuration
    2. Apply regime-based adjustments
    3. Scale parameters based on volatility
    4. Learn from performance feedback
    5. Enforce safety bounds
    6. Support rollback of changes
    """
    
    # Default safety bounds
    SAFETY_BOUNDS = {
        'strategies.*.max_position_usd': {'min': 10, 'max': 1000},
        'strategies.*.stop_loss_pct': {'min': 0.005, 'max': 0.20},
        'strategies.*.take_profit_pct': {'min': 0.01, 'max': 0.50},
        'strategies.*.check_interval_seconds': {'min': 5, 'max': 3600},
        'risk.max_position_btc': {'min': 0.001, 'max': 1.0},
        'risk.capital_pct_per_trade': {'min': 0.01, 'max': 0.50},
        'risk.stop_loss_pct': {'min': 0.005, 'max': 0.20},
    }
    
    # Regime-based multipliers
    REGIME_MULTIPLIERS = {
        'DEFENSIVE': {
            'position_size': 0.5,
            'stop_loss': 0.8,
            'take_profit': 0.7,
            'check_interval': 2.0,  # Slower checks
            'max_concurrent': 0.5,
            'capital_allocation': 0.5,
            'description': 'Risk-off, tight controls'
        },
        'NEUTRAL': {
            'position_size': 1.0,
            'stop_loss': 1.0,
            'take_profit': 1.0,
            'check_interval': 1.0,
            'max_concurrent': 1.0,
            'capital_allocation': 1.0,
            'description': 'Balanced configuration'
        },
        'RISK_ON': {
            'position_size': 1.5,
            'stop_loss': 1.2,
            'take_profit': 1.5,
            'check_interval': 0.8,  # Faster checks
            'max_concurrent': 1.5,
            'capital_allocation': 1.3,
            'description': 'Expanded opportunities'
        }
    }
    
    # Volatility scaling factors (based on ATR or similar)
    VOLATILITY_THRESHOLDS = {
        'low': {'atr_pct': 0.02, 'multiplier': 1.2},      # < 2% ATR
        'normal': {'atr_pct': 0.05, 'multiplier': 1.0},   # 2-5% ATR
        'high': {'atr_pct': 0.10, 'multiplier': 0.7},     # 5-10% ATR
        'extreme': {'atr_pct': float('inf'), 'multiplier': 0.4}  # > 10% ATR
    }
    
    def __init__(self, config_path: str = 'config.json'):
        """
        Initialize dynamic config manager.
        
        Args:
            config_path: Path to main configuration file
        """
        self.config_path = Path(config_path)
        self.backup_dir = Path('config_backups')
        self.backup_dir.mkdir(exist_ok=True)
        
        # Load current configuration
        self.current_config = self._load_config()
        self.original_config = deepcopy(self.current_config)
        
        # Change history
        self.changes: List[ConfigChange] = []
        self.current_regime: Optional[str] = None
        
        # Performance tracking
        self.performance_history: Dict[str, List[Dict]] = {}
        
        # Initialize database
        self._init_database()
        
        logger.info("[DynamicConfigManager] Initialized")
    
    def _init_database(self):
        """Initialize SQLite database for change tracking."""
        try:
            conn = sqlite3.connect('config_changes.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    change_id TEXT UNIQUE,
                    timestamp TEXT,
                    regime TEXT,
                    trigger TEXT,
                    original_value TEXT,
                    new_value TEXT,
                    parameter_path TEXT,
                    rolled_back INTEGER,
                    rollback_timestamp TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    change_id TEXT,
                    timestamp TEXT,
                    metric_name TEXT,
                    metric_value REAL,
                    FOREIGN KEY (change_id) REFERENCES config_changes(change_id)
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[DynamicConfigManager] Database init failed: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[DynamicConfigManager] Failed to load config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'strategies': {
                'arbitrage': {
                    'enabled': True,
                    'max_position_usd': 100,
                    'stop_loss_pct': 0.02,
                    'take_profit_pct': 0.06
                },
                'sniper': {
                    'enabled': True,
                    'max_position_usd': 50,
                    'stop_loss_pct': 0.03,
                    'take_profit_pct': 0.09
                }
            },
            'risk': {
                'max_position_btc': 0.05,
                'stop_loss_pct': 0.02,
                'capital_pct_per_trade': 0.05
            }
        }
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"[DynamicConfigManager] Failed to save config: {e}")
            raise
    
    def _backup_config(self):
        """Create backup of current configuration."""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"config_backup_{timestamp}.json"
        
        try:
            with open(backup_path, 'w') as f:
                json.dump(self.current_config, f, indent=2)
            logger.info(f"[DynamicConfigManager] Config backed up to {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"[DynamicConfigManager] Backup failed: {e}")
            return None
    
    def _enforce_safety_bounds(self, parameter_path: str, value: Any) -> Any:
        """
        Enforce safety bounds on parameter values.
        
        Args:
            parameter_path: Path to parameter (e.g., 'strategies.arbitrage.max_position_usd')
            value: Proposed new value
            
        Returns:
            Value clamped to safety bounds
        """
        # Find matching bound pattern
        for pattern, bounds in self.SAFETY_BOUNDS.items():
            # Convert pattern to simple matching (handle wildcards)
            pattern_parts = pattern.split('.')
            path_parts = parameter_path.split('.')
            
            if len(pattern_parts) != len(path_parts):
                continue
            
            match = True
            for p_part, path_part in zip(pattern_parts, path_parts):
                if p_part != '*' and p_part != path_part:
                    match = False
                    break
            
            if match:
                min_val = bounds['min']
                max_val = bounds['max']
                
                if isinstance(value, (int, float)):
                    clamped = max(min_val, min(max_val, value))
                    if clamped != value:
                        logger.warning(
                            f"[DynamicConfigManager] {parameter_path} clamped: "
                            f"{value} -> {clamped} (bounds: {min_val}-{max_val})"
                        )
                    return clamped
        
        return value
    
    def _apply_multipliers(self, base_value: float, multipliers: List[float]) -> float:
        """Apply multiple multipliers to a base value."""
        result = base_value
        for m in multipliers:
            result *= m
        return result
    
    def _set_nested_value(self, config: Dict, path: str, value: Any):
        """Set a nested dictionary value by path."""
        parts = path.split('.')
        current = config
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    def _get_nested_value(self, config: Dict, path: str) -> Any:
        """Get a nested dictionary value by path."""
        parts = path.split('.')
        current = config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    async def apply_regime_adjustments(self, regime: MarketRegime) -> List[ConfigChange]:
        """
        Apply all configuration adjustments for a market regime.
        
        Args:
            regime: Current market regime (DEFENSIVE, NEUTRAL, RISK_ON)
            
        Returns:
            List of changes made
        """
        if regime == self.current_regime:
            return []
        
        logger.info(f"[DynamicConfigManager] Applying regime adjustments for {regime}")
        
        multipliers = self.REGIME_MULTIPLIERS.get(regime, self.REGIME_MULTIPLIERS['NEUTRAL'])
        changes = []
        
        # Backup current config
        self._backup_config()
        
        # Apply to all strategies
        strategies = self.current_config.get('strategies', {})
        for strategy_name, strategy_config in strategies.items():
            # Adjust position sizes
            if 'max_position_usd' in strategy_config:
                original = strategy_config['max_position_usd']
                new_value = original * multipliers['position_size']
                new_value = self._enforce_safety_bounds(
                    f'strategies.{strategy_name}.max_position_usd', 
                    new_value
                )
                
                change = await self._apply_change(
                    regime=regime,
                    trigger='regime_change',
                    parameter_path=f'strategies.{strategy_name}.max_position_usd',
                    new_value=new_value,
                    original_value=original
                )
                changes.append(change)
            
            # Adjust stop losses
            if 'stop_loss_pct' in strategy_config:
                original = strategy_config['stop_loss_pct']
                new_value = original * multipliers['stop_loss']
                new_value = self._enforce_safety_bounds(
                    f'strategies.{strategy_name}.stop_loss_pct',
                    new_value
                )
                
                change = await self._apply_change(
                    regime=regime,
                    trigger='regime_change',
                    parameter_path=f'strategies.{strategy_name}.stop_loss_pct',
                    new_value=new_value,
                    original_value=original
                )
                changes.append(change)
            
            # Adjust take profits
            if 'take_profit_pct' in strategy_config:
                original = strategy_config['take_profit_pct']
                new_value = original * multipliers['take_profit']
                new_value = self._enforce_safety_bounds(
                    f'strategies.{strategy_name}.take_profit_pct',
                    new_value
                )
                
                change = await self._apply_change(
                    regime=regime,
                    trigger='regime_change',
                    parameter_path=f'strategies.{strategy_name}.take_profit_pct',
                    new_value=new_value,
                    original_value=original
                )
                changes.append(change)
            
            # Adjust check intervals
            if 'check_interval_seconds' in strategy_config:
                original = strategy_config['check_interval_seconds']
                new_value = int(original * multipliers['check_interval'])
                new_value = self._enforce_safety_bounds(
                    f'strategies.{strategy_name}.check_interval_seconds',
                    new_value
                )
                
                change = await self._apply_change(
                    regime=regime,
                    trigger='regime_change',
                    parameter_path=f'strategies.{strategy_name}.check_interval_seconds',
                    new_value=new_value,
                    original_value=original
                )
                changes.append(change)
        
        # Apply to risk parameters
        risk_config = self.current_config.get('risk', {})
        if 'capital_pct_per_trade' in risk_config:
            original = risk_config['capital_pct_per_trade']
            new_value = original * multipliers['capital_allocation']
            new_value = self._enforce_safety_bounds('risk.capital_pct_per_trade', new_value)
            
            change = await self._apply_change(
                regime=regime,
                trigger='regime_change',
                parameter_path='risk.capital_pct_per_trade',
                new_value=new_value,
                original_value=original
            )
            changes.append(change)
        
        self.current_regime = regime
        
        # Save updated config
        self._save_config(self.current_config)
        
        logger.info(f"[DynamicConfigManager] Applied {len(changes)} regime adjustments")
        return changes
    
    async def apply_volatility_scaling(self, volatility_level: str) -> List[ConfigChange]:
        """
        Scale position sizes based on volatility level.
        
        Args:
            volatility_level: 'low', 'normal', 'high', or 'extreme'
            
        Returns:
            List of changes made
        """
        vol_config = self.VOLATILITY_THRESHOLDS.get(volatility_level)
        if not vol_config:
            logger.warning(f"[DynamicConfigManager] Unknown volatility level: {volatility_level}")
            return []
        
        multiplier = vol_config['multiplier']
        logger.info(f"[DynamicConfigManager] Applying volatility scaling: {volatility_level} "
                   f"(multiplier: {multiplier})")
        
        changes = []
        
        # Apply to all strategy position sizes
        strategies = self.current_config.get('strategies', {})
        for strategy_name, strategy_config in strategies.items():
            if 'max_position_usd' in strategy_config:
                original = strategy_config['max_position_usd']
                new_value = original * multiplier
                new_value = self._enforce_safety_bounds(
                    f'strategies.{strategy_name}.max_position_usd',
                    new_value
                )
                
                change = await self._apply_change(
                    regime=self.current_regime or 'NEUTRAL',
                    trigger=f'volatility_{volatility_level}',
                    parameter_path=f'strategies.{strategy_name}.max_position_usd',
                    new_value=new_value,
                    original_value=original
                )
                changes.append(change)
        
        self._save_config(self.current_config)
        return changes
    
    async def _apply_change(self, regime: str, trigger: str, parameter_path: str,
                           new_value: Any, original_value: Any) -> ConfigChange:
        """Apply a single configuration change."""
        change_id = f"{parameter_path.replace('.', '_')}_{int(datetime.now().timestamp())}"
        
        change = ConfigChange(
            change_id=change_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            regime=regime,
            trigger=trigger,
            original_value=original_value,
            new_value=new_value,
            parameter_path=parameter_path
        )
        
        # Apply to current config
        self._set_nested_value(self.current_config, parameter_path, new_value)
        
        # Store change
        self.changes.append(change)
        
        # Log to database
        try:
            conn = sqlite3.connect('config_changes.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO config_changes 
                (change_id, timestamp, regime, trigger, original_value, new_value, parameter_path, rolled_back)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                change_id,
                change.timestamp,
                regime,
                trigger,
                json.dumps(original_value),
                json.dumps(new_value),
                parameter_path
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[DynamicConfigManager] Failed to log change: {e}")
        
        logger.info(f"[DynamicConfigManager] Applied change: {parameter_path} = {new_value}")
        return change
    
    def rollback_change(self, change_id: str) -> bool:
        """
        Rollback a specific configuration change.
        
        Args:
            change_id: ID of change to rollback
            
        Returns:
            True if successful
        """
        # Find the change
        change = None
        for c in self.changes:
            if c.change_id == change_id:
                change = c
                break
        
        if not change:
            logger.error(f"[DynamicConfigManager] Change not found: {change_id}")
            return False
        
        # Restore original value
        self._set_nested_value(self.current_config, change.parameter_path, change.original_value)
        
        # Mark as rolled back
        change.rolled_back = True
        change.rollback_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Update database
        try:
            conn = sqlite3.connect('config_changes.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE config_changes 
                SET rolled_back = 1, rollback_timestamp = ?
                WHERE change_id = ?
            ''', (change.rollback_timestamp, change_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[DynamicConfigManager] Failed to update rollback: {e}")
        
        # Save config
        self._save_config(self.current_config)
        
        logger.info(f"[DynamicConfigManager] Rolled back change: {change_id}")
        return True
    
    def rollback_all_regime_changes(self, regime: str) -> int:
        """Rollback all changes made for a specific regime."""
        count = 0
        for change in reversed(self.changes):
            if change.regime == regime and not change.rolled_back:
                if self.rollback_change(change.change_id):
                    count += 1
        return count
    
    def record_performance_feedback(self, change_id: str, metric_name: str, metric_value: float):
        """
        Record performance feedback for a configuration change.
        
        This enables learning from which adjustments worked best.
        """
        try:
            conn = sqlite3.connect('config_changes.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO performance_feedback (change_id, timestamp, metric_name, metric_value)
                VALUES (?, ?, ?, ?)
            ''', (
                change_id,
                datetime.now(timezone.utc).isoformat(),
                metric_name,
                metric_value
            ))
            conn.commit()
            conn.close()
            
            # Store in memory for quick access
            if change_id not in self.performance_history:
                self.performance_history[change_id] = []
            self.performance_history[change_id].append({
                'metric': metric_name,
                'value': metric_value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"[DynamicConfigManager] Failed to record feedback: {e}")
    
    def get_change_history(self, limit: int = 50) -> List[Dict]:
        """Get history of configuration changes."""
        try:
            conn = sqlite3.connect('config_changes.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM config_changes
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            changes = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return changes
        except Exception as e:
            logger.error(f"[DynamicConfigManager] Failed to get history: {e}")
            return []
    
    def get_effective_config(self) -> Dict[str, Any]:
        """Get current effective configuration."""
        return deepcopy(self.current_config)
    
    def get_adjustment_summary(self) -> Dict[str, Any]:
        """Get summary of current adjustments."""
        active_changes = [c for c in self.changes if not c.rolled_back]
        
        return {
            'current_regime': self.current_regime,
            'total_changes_made': len(self.changes),
            'active_adjustments': len(active_changes),
            'changes_by_regime': {},
            'recent_changes': [
                {
                    'parameter': c.parameter_path,
                    'regime': c.regime,
                    'trigger': c.trigger,
                    'new_value': c.new_value
                }
                for c in self.changes[-10:]
            ]
        }


# Singleton instance
_manager_instance: Optional[DynamicConfigManager] = None


def get_dynamic_config_manager(config_path: str = 'config.json') -> DynamicConfigManager:
    """Get singleton dynamic config manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DynamicConfigManager(config_path)
    return _manager_instance


if __name__ == "__main__":
    # Test mode
    print("=" * 60)
    print("Dynamic Config Manager - Test Mode")
    print("=" * 60)
    
    import asyncio
    
    async def test():
        manager = get_dynamic_config_manager()
        
        print(f"\nInitial config:")
        print(json.dumps(manager.get_effective_config(), indent=2))
        
        # Test regime adjustment
        print("\n--- Testing DEFENSIVE regime ---")
        changes = await manager.apply_regime_adjustments('DEFENSIVE')
        print(f"Made {len(changes)} changes")
        
        for c in changes[:3]:
            print(f"  {c.parameter_path}: {c.original_value} -> {c.new_value}")
        
        # Test volatility scaling
        print("\n--- Testing HIGH volatility scaling ---")
        changes = await manager.apply_volatility_scaling('high')
        print(f"Made {len(changes)} changes")
        
        # Get summary
        print("\n--- Adjustment Summary ---")
        print(json.dumps(manager.get_adjustment_summary(), indent=2))
        
        # Get history
        print("\n--- Change History ---")
        history = manager.get_change_history(10)
        for h in history[:3]:
            print(f"  {h['parameter_path']}: {h['trigger']}")
    
    asyncio.run(test())
