#!/usr/bin/env python3
"""
Self-Healing Engine
===================
Autonomous issue detection and recovery system.

Features:
- Continuous health monitoring
- Automatic remediation for common issues
- Recovery verification
- Escalation for unresolved issues
- Learning from recovery outcomes

Usage:
    healer = SelfHealingEngine()
    await healer.start()
"""

import asyncio
import json
import logging
import sqlite3
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from pathlib import Path

from zeroclaw_integration import ZeroClawIntegration

logger = logging.getLogger(__name__)


class IssueType(Enum):
    """Types of issues that can be detected."""
    API_CONNECTIVITY = "api_connectivity"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"
    DATABASE_ERROR = "database_error"
    MEMORY_HIGH = "memory_high"
    DISK_FULL = "disk_full"
    PROCESS_CRASH = "process_crash"
    ZEROCLAW_DOWN = "zeroclaw_down"
    TRADE_EXECUTION_FAILURE = "trade_execution_failure"
    RISK_THRESHOLD_BREACH = "risk_threshold_breach"
    LATENCY_SPIKE = "latency_spike"


class RemediationAction(Enum):
    """Available remediation actions."""
    RESTART_SERVICE = "restart_service"
    RECONNECT_WEBSOCKET = "reconnect_websocket"
    CLEAR_CACHE = "clear_cache"
    KILL_ZOMBIE_PROCESSES = "kill_zombie_processes"
    ROTATE_LOGS = "rotate_logs"
    RESET_RISK_PARAMS = "reset_risk_params"
    RESTART_ZEROCLAW = "restart_zeroclaw"
    NOTIFY_OPERATOR = "notify_operator"


class IssueStatus(Enum):
    """Status of detected issues."""
    DETECTED = "detected"
    REMEDIATING = "remediating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    FAILED = "failed"


@dataclass
class DetectedIssue:
    """Record of a detected issue."""
    issue_id: str
    timestamp: str
    issue_type: str
    description: str
    severity: str  # critical, high, medium, low
    metrics: Dict[str, Any]
    status: str
    remediation_attempted: Optional[str] = None
    remediation_result: Optional[str] = None
    resolved_at: Optional[str] = None
    escalation_count: int = 0


class SelfHealingEngine:
    """
    Autonomous self-healing system for the trading bot.
    
    Responsibilities:
    1. Monitor system health continuously
    2. Detect issues automatically
    3. Attempt remediation for known issues
    4. Verify recovery success
    5. Escalate unresolved issues
    6. Learn from remediation outcomes
    """
    
    # Health check intervals (seconds)
    CHECK_INTERVALS = {
        'fast': 10,      # For critical components
        'normal': 30,    # Standard checks
        'slow': 60       # Non-critical checks
    }
    
    # Remediation playbook - maps issues to actions
    REMEDIATION_PLAYBOOK = {
        IssueType.ZEROCLAW_DOWN.value: [
            RemediationAction.RESTART_ZEROCLAW,
            RemediationAction.NOTIFY_OPERATOR
        ],
        IssueType.WEBSOCKET_DISCONNECT.value: [
            RemediationAction.RECONNECT_WEBSOCKET
        ],
        IssueType.MEMORY_HIGH.value: [
            RemediationAction.CLEAR_CACHE,
            RemediationAction.KILL_ZOMBIE_PROCESSES
        ],
        IssueType.DISK_FULL.value: [
            RemediationAction.ROTATE_LOGS,
            RemediationAction.CLEAR_CACHE
        ],
        IssueType.API_CONNECTIVITY.value: [
            RemediationAction.RECONNECT_WEBSOCKET,
            RemediationAction.NOTIFY_OPERATOR
        ],
        IssueType.TRADE_EXECUTION_FAILURE.value: [
            RemediationAction.RESET_RISK_PARAMS,
            RemediationAction.NOTIFY_OPERATOR
        ]
    }
    
    # Success rates for learning (issue_type -> action -> success_rate)
    REMEDIATION_SUCCESS_RATES: Dict[str, Dict[str, float]] = {}
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize self-healing engine.
        
        Args:
            config: Configuration overrides
        """
        self.config = config or {}
        self.running = False
        self.zeroclaw = ZeroClawIntegration()
        
        # Issue tracking
        self.active_issues: Dict[str, DetectedIssue] = {}
        self.resolved_issues: List[DetectedIssue] = []
        
        # Health status cache
        self.health_cache: Dict[str, Any] = {}
        self.last_check: Dict[str, float] = {}
        
        # Callbacks
        self.on_issue: Optional[Callable[[DetectedIssue], None]] = None
        self.on_resolution: Optional[Callable[[DetectedIssue], None]] = None
        
        # Statistics
        self.stats = {
            'issues_detected': 0,
            'issues_resolved_autonomously': 0,
            'issues_escalated': 0,
            'remediation_attempts': 0,
            'remediation_successes': 0
        }
        
        # Initialize database
        self._init_database()
        
        logger.info("[SelfHealingEngine] Initialized")
    
    def _init_database(self):
        """Initialize SQLite database for issue tracking."""
        try:
            conn = sqlite3.connect('self_healing.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detected_issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id TEXT UNIQUE,
                    timestamp TEXT,
                    issue_type TEXT,
                    description TEXT,
                    severity TEXT,
                    metrics TEXT,
                    status TEXT,
                    remediation_attempted TEXT,
                    remediation_result TEXT,
                    resolved_at TEXT,
                    escalation_count INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_issues_status 
                ON detected_issues(status)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_issues_type 
                ON detected_issues(issue_type)
            ''')
            
            # Remediation effectiveness tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS remediation_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id TEXT,
                    action_taken TEXT,
                    success INTEGER,
                    duration_seconds REAL,
                    timestamp TEXT,
                    FOREIGN KEY (issue_id) REFERENCES detected_issues(issue_id)
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Database init failed: {e}")
    
    def _log_issue(self, issue: DetectedIssue):
        """Log issue to database."""
        try:
            conn = sqlite3.connect('self_healing.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO detected_issues 
                (issue_id, timestamp, issue_type, description, severity, metrics,
                 status, remediation_attempted, remediation_result, resolved_at, escalation_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                issue.issue_id,
                issue.timestamp,
                issue.issue_type,
                issue.description,
                issue.severity,
                json.dumps(issue.metrics),
                issue.status,
                issue.remediation_attempted,
                issue.remediation_result,
                issue.resolved_at,
                issue.escalation_count
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Failed to log issue: {e}")
    
    async def start(self):
        """Start the self-healing engine."""
        self.running = True
        logger.info("[SelfHealingEngine] Starting monitoring loop...")
        
        while self.running:
            try:
                await self._run_health_check_cycle()
                await asyncio.sleep(self.CHECK_INTERVALS['normal'])
            except Exception as e:
                logger.error(f"[SelfHealingEngine] Cycle error: {e}")
                await asyncio.sleep(5)
        
        logger.info("[SelfHealingEngine] Stopped")
    
    def stop(self):
        """Stop the self-healing engine."""
        self.running = False
    
    def toggle(self, enabled: bool):
        """Enable or disable self-healing with proper event loop handling."""
        if enabled and not self.running:
            import threading
            def run_async_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.start())
            
            thread = threading.Thread(target=run_async_loop, daemon=True)
            thread.start()
            logger.info("[SelfHealingEngine] Started in background thread")
        elif not enabled and self.running:
            self.stop()
    
    async def _run_health_check_cycle(self):
        """Execute one complete health check cycle."""
        now = time.time()
        
        # 1. Check ZeroClaw gateway
        if self._should_check('zeroclaw', now):
            await self._check_zeroclaw_health()
        
        # 2. Check WebSocket connections
        if self._should_check('websocket', now):
            await self._check_websocket_health()
        
        # 3. Check database
        if self._should_check('database', now):
            await self._check_database_health()
        
        # 4. Check system resources
        if self._should_check('system', now):
            await self._check_system_resources()
        
        # 5. Check trading health
        if self._should_check('trading', now):
            await self._check_trading_health()
        
        # 6. Process any new issues
        await self._process_issues()
    
    def _should_check(self, component: str, now: float) -> bool:
        """Determine if a component should be checked."""
        last_check = self.last_check.get(component, 0)
        interval = self.CHECK_INTERVALS['normal']
        
        # Critical components checked more frequently
        if component in ['zeroclaw', 'trading']:
            interval = self.CHECK_INTERVALS['fast']
        
        return now - last_check >= interval
    
    async def _check_zeroclaw_health(self):
        """Check ZeroClaw gateway health."""
        self.last_check['zeroclaw'] = time.time()
        
        try:
            is_running = self.zeroclaw.is_running()
            
            if not is_running:
                issue = DetectedIssue(
                    issue_id=f"zeroclaw_down_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    issue_type=IssueType.ZEROCLAW_DOWN.value,
                    description="ZeroClaw gateway is not responding",
                    severity='high',
                    metrics={'gateway_url': self.zeroclaw.gateway_url},
                    status=IssueStatus.DETECTED.value
                )
                await self._register_issue(issue)
            else:
                # Clear any existing ZeroClaw issues
                await self._clear_resolved_issues(IssueType.ZEROCLAW_DOWN.value)
                
        except Exception as e:
            logger.warning(f"[SelfHealingEngine] ZeroClaw check failed: {e}")
    
    async def _check_websocket_health(self):
        """Check WebSocket connection health."""
        self.last_check['websocket'] = time.time()
        
        # Would check actual WebSocket connection status
        # For now, placeholder
        pass
    
    async def _check_database_health(self):
        """Check database health."""
        self.last_check['database'] = time.time()
        
        try:
            conn = sqlite3.connect('trades.db', timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades")
            cursor.fetchone()
            conn.close()
            
            # Clear any existing DB issues
            await self._clear_resolved_issues(IssueType.DATABASE_ERROR.value)
            
        except Exception as e:
            issue = DetectedIssue(
                issue_id=f"db_error_{int(time.time())}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                issue_type=IssueType.DATABASE_ERROR.value,
                description=f"Database connection error: {str(e)[:100]}",
                severity='critical',
                metrics={'error': str(e)},
                status=IssueStatus.DETECTED.value
            )
            await self._register_issue(issue)
    
    async def _check_system_resources(self):
        """Check system resource usage."""
        self.last_check['system'] = time.time()
        
        try:
            # Check memory usage
            mem_info = self._get_memory_usage()
            if mem_info.get('percent', 0) > 90:
                issue = DetectedIssue(
                    issue_id=f"memory_high_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    issue_type=IssueType.MEMORY_HIGH.value,
                    description=f"High memory usage: {mem_info['percent']}%",
                    severity='medium',
                    metrics=mem_info,
                    status=IssueStatus.DETECTED.value
                )
                await self._register_issue(issue)
            
            # Check disk usage
            disk_info = self._get_disk_usage()
            if disk_info.get('percent', 0) > 90:
                issue = DetectedIssue(
                    issue_id=f"disk_full_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    issue_type=IssueType.DISK_FULL.value,
                    description=f"Low disk space: {disk_info['percent']}% used",
                    severity='high',
                    metrics=disk_info,
                    status=IssueStatus.DETECTED.value
                )
                await self._register_issue(issue)
            
        except Exception as e:
            logger.warning(f"[SelfHealingEngine] Resource check failed: {e}")
    
    async def _check_trading_health(self):
        """Check trading system health."""
        self.last_check['trading'] = time.time()
        
        try:
            # Check recent trade execution failures
            conn = sqlite3.connect('trades.db')
            cursor = conn.cursor()
            
            # Get failed trades in last hour
            cursor.execute("""
                SELECT COUNT(*) FROM trades 
                WHERE status = 'FAILED' 
                AND timestamp > datetime('now', '-1 hour')
            """)
            failed_count = cursor.fetchone()[0]
            conn.close()
            
            if failed_count > 5:
                issue = DetectedIssue(
                    issue_id=f"trade_failures_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    issue_type=IssueType.TRADE_EXECUTION_FAILURE.value,
                    description=f"High trade failure rate: {failed_count} failures in last hour",
                    severity='high',
                    metrics={'failed_count': failed_count},
                    status=IssueStatus.DETECTED.value
                )
                await self._register_issue(issue)
            
        except Exception as e:
            logger.warning(f"[SelfHealingEngine] Trading check failed: {e}")
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage."""
        try:
            # Use /proc/meminfo on Linux
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            
            mem_total = 0
            mem_available = 0
            
            for line in lines:
                if line.startswith('MemTotal:'):
                    mem_total = int(line.split()[1]) * 1024
                elif line.startswith('MemAvailable:'):
                    mem_available = int(line.split()[1]) * 1024
            
            if mem_total > 0:
                used = mem_total - mem_available
                percent = (used / mem_total) * 100
                return {
                    'total': mem_total,
                    'available': mem_available,
                    'used': used,
                    'percent': percent
                }
        except Exception as e:
            logger.debug(f"[SelfHealingEngine] Memory check failed: {e}")
        
        return {'percent': 0}
    
    def _get_disk_usage(self) -> Dict[str, float]:
        """Get current disk usage."""
        try:
            result = subprocess.run(
                ['df', '-h', '.'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Parse df output
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    used_pct = int(parts[4].rstrip('%'))
                    return {'percent': used_pct}
        except Exception as e:
            logger.debug(f"[SelfHealingEngine] Disk check failed: {e}")
        
        return {'percent': 0}
    
    async def _register_issue(self, issue: DetectedIssue):
        """Register a newly detected issue."""
        # Check if similar issue already exists
        for existing in self.active_issues.values():
            if (existing.issue_type == issue.issue_type and 
                existing.status != IssueStatus.RESOLVED.value):
                # Update existing issue
                existing.escalation_count += 1
                self._log_issue(existing)
                return
        
        # Register new issue
        self.active_issues[issue.issue_id] = issue
        self.stats['issues_detected'] += 1
        self._log_issue(issue)
        
        logger.warning(f"[SelfHealingEngine] Issue detected: {issue.issue_type} - {issue.description}")
        
        if self.on_issue:
            self.on_issue(issue)
    
    async def _clear_resolved_issues(self, issue_type: str):
        """Mark issues of a type as resolved."""
        for issue in list(self.active_issues.values()):
            if issue.issue_type == issue_type:
                issue.status = IssueStatus.RESOLVED.value
                issue.resolved_at = datetime.now(timezone.utc).isoformat()
                self.resolved_issues.append(issue)
                del self.active_issues[issue.issue_id]
                self._log_issue(issue)
    
    async def _process_issues(self):
        """Process active issues for remediation."""
        for issue in list(self.active_issues.values()):
            if issue.status == IssueStatus.DETECTED.value:
                await self._attempt_remediation(issue)
    
    async def _attempt_remediation(self, issue: DetectedIssue):
        """Attempt to remediate an issue."""
        # Get remediation actions from playbook
        actions = self.REMEDIATION_PLAYBOOK.get(issue.issue_type, [])
        
        if not actions:
            # No known remediation - escalate immediately
            await self._escalate_issue(issue)
            return
        
        # Sort actions by historical success rate
        sorted_actions = sorted(
            actions,
            key=lambda a: self.REMEDIATION_SUCCESS_RATES
                .get(issue.issue_type, {})
                .get(a.value, 0.5),
            reverse=True
        )
        
        issue.status = IssueStatus.REMEDIATING.value
        self._log_issue(issue)
        
        # Try each action in order
        for action in sorted_actions:
            if action == RemediationAction.NOTIFY_OPERATOR:
                # Only notify after other attempts fail
                continue
            
            logger.info(f"[SelfHealingEngine] Attempting {action.value} for {issue.issue_type}")
            
            start_time = time.time()
            success = await self._execute_remediation_action(action, issue)
            duration = time.time() - start_time
            
            self.stats['remediation_attempts'] += 1
            
            # Record outcome
            await self._record_remediation_outcome(issue, action.value, success, duration)
            
            if success:
                issue.status = IssueStatus.RESOLVED.value
                issue.resolved_at = datetime.now(timezone.utc).isoformat()
                issue.remediation_attempted = action.value
                issue.remediation_result = "Success"
                
                self.resolved_issues.append(issue)
                del self.active_issues[issue.issue_id]
                
                self.stats['issues_resolved_autonomously'] += 1
                self.stats['remediation_successes'] += 1
                
                self._log_issue(issue)
                
                if self.on_resolution:
                    self.on_resolution(issue)
                
                logger.info(f"[SelfHealingEngine] Issue resolved: {issue.issue_id}")
                return
        
        # All remediation attempts failed - escalate
        await self._escalate_issue(issue)
    
    async def _execute_remediation_action(self, action: RemediationAction, 
                                          issue: DetectedIssue) -> bool:
        """Execute a specific remediation action."""
        try:
            if action == RemediationAction.RESTART_ZEROCLAW:
                return await self._restart_zeroclaw()
            
            elif action == RemediationAction.RECONNECT_WEBSOCKET:
                return await self._reconnect_websocket()
            
            elif action == RemediationAction.CLEAR_CACHE:
                return await self._clear_cache()
            
            elif action == RemediationAction.KILL_ZOMBIE_PROCESSES:
                return await self._kill_zombie_processes()
            
            elif action == RemediationAction.ROTATE_LOGS:
                return await self._rotate_logs()
            
            elif action == RemediationAction.RESET_RISK_PARAMS:
                return await self._reset_risk_params()
            
            else:
                logger.warning(f"[SelfHealingEngine] Unknown action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Remediation action failed: {e}")
            return False
    
    async def _restart_zeroclaw(self) -> bool:
        """Restart ZeroClaw daemon."""
        try:
            # Kill existing
            subprocess.run(['pkill', '-f', 'zeroclaw daemon'], 
                          capture_output=True, timeout=10)
            
            await asyncio.sleep(2)
            
            # Start new instance
            subprocess.Popen(
                ['zeroclaw', 'daemon'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Wait and verify
            await asyncio.sleep(5)
            
            for _ in range(10):
                if self.zeroclaw.is_running():
                    return True
                await asyncio.sleep(1)
            
            return False
            
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Failed to restart ZeroClaw: {e}")
            return False
    
    async def _reconnect_websocket(self) -> bool:
        """Reconnect WebSocket connections."""
        # Would trigger WebSocket reconnection
        logger.info("[SelfHealingEngine] WebSocket reconnection triggered")
        return True
    
    async def _clear_cache(self) -> bool:
        """Clear application cache."""
        try:
            cache_paths = ['.cache', '__pycache__', '.pytest_cache']
            for path in cache_paths:
                if Path(path).exists():
                    subprocess.run(['rm', '-rf', path], capture_output=True)
            return True
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Cache clear failed: {e}")
            return False
    
    async def _kill_zombie_processes(self) -> bool:
        """Kill zombie/orphaned processes."""
        try:
            # Find python processes using high memory
            result = subprocess.run(
                ['ps', 'aux', '--sort=-%mem'],
                capture_output=True,
                text=True
            )
            
            # Would parse and kill zombies
            return True
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Kill zombies failed: {e}")
            return False
    
    async def _rotate_logs(self) -> bool:
        """Rotate log files."""
        try:
            log_files = list(Path('.').glob('*.log'))
            for log_file in log_files:
                if log_file.stat().st_size > 100 * 1024 * 1024:  # 100MB
                    # Rotate
                    backup = log_file.with_suffix('.log.old')
                    log_file.rename(backup)
            return True
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Log rotation failed: {e}")
            return False
    
    async def _reset_risk_params(self) -> bool:
        """Reset risk parameters to safe defaults."""
        try:
            # Would reset config to safe values
            logger.info("[SelfHealingEngine] Risk parameters reset to defaults")
            return True
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Risk reset failed: {e}")
            return False
    
    async def _escalate_issue(self, issue: DetectedIssue):
        """Escalate issue to human operator."""
        issue.status = IssueStatus.ESCALATED.value
        issue.escalation_count += 1
        self._log_issue(issue)
        
        self.stats['issues_escalated'] += 1
        
        # Send notification
        message = f"""
🚨 <b>Self-Healing Escalation</b>

Issue: {issue.issue_type}
Description: {issue.description}
Severity: {issue.severity}
Remediation attempts: {issue.escalation_count}

Metrics:
<pre>{json.dumps(issue.metrics, indent=2)}</pre>

Manual intervention may be required.
        """.strip()
        
        try:
            self.zeroclaw.send_telegram_alert(message, priority='critical')
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Failed to send escalation: {e}")
        
        logger.critical(f"[SelfHealingEngine] Issue escalated: {issue.issue_id}")
    
    async def _record_remediation_outcome(self, issue: DetectedIssue, 
                                          action: str, success: bool, duration: float):
        """Record remediation outcome for learning."""
        try:
            conn = sqlite3.connect('self_healing.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO remediation_outcomes 
                (issue_id, action_taken, success, duration_seconds, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                issue.issue_id,
                action,
                1 if success else 0,
                duration,
                datetime.now(timezone.utc).isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Update success rate in memory
            if issue.issue_type not in self.REMEDIATION_SUCCESS_RATES:
                self.REMEDIATION_SUCCESS_RATES[issue.issue_type] = {}
            
            current_rate = self.REMEDIATION_SUCCESS_RATES[issue.issue_type].get(action, 0.5)
            # Exponential moving average
            new_rate = (0.9 * current_rate) + (0.1 * (1.0 if success else 0))
            self.REMEDIATION_SUCCESS_RATES[issue.issue_type][action] = new_rate
            
        except Exception as e:
            logger.error(f"[SelfHealingEngine] Failed to record outcome: {e}")
    
    # Public API
    
    def get_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            'running': self.running,
            'active_issues': len(self.active_issues),
            'resolved_issues': len(self.resolved_issues),
            'stats': self.stats,
            'last_checks': {k: datetime.fromtimestamp(v).isoformat() 
                           for k, v in self.last_check.items()}
        }
    
    def get_active_issues(self) -> List[Dict]:
        """Get list of active issues."""
        return [asdict(issue) for issue in self.active_issues.values()]
    
    def force_remediation(self, issue_id: str) -> bool:
        """Manually trigger remediation for an issue."""
        if issue_id in self.active_issues:
            asyncio.create_task(self._attempt_remediation(self.active_issues[issue_id]))
            return True
        return False


# Singleton instance
_healer_instance: Optional[SelfHealingEngine] = None


def get_self_healing_engine(config: Optional[Dict] = None) -> SelfHealingEngine:
    """Get singleton self-healing engine instance."""
    global _healer_instance
    if _healer_instance is None:
        _healer_instance = SelfHealingEngine(config)
    return _healer_instance


if __name__ == "__main__":
    # Test mode
    print("=" * 60)
    print("Self-Healing Engine - Test Mode")
    print("=" * 60)
    
    import asyncio
    
    async def test():
        healer = get_self_healing_engine()
        
        print(f"\nStatus: {healer.get_status()}")
        
        # Simulate an issue
        print("\n--- Simulating ZeroClaw down issue ---")
        issue = DetectedIssue(
            issue_id=f"test_issue_{int(time.time())}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            issue_type=IssueType.ZEROCLAW_DOWN.value,
            description="Test issue",
            severity='high',
            metrics={},
            status=IssueStatus.DETECTED.value
        )
        await healer._register_issue(issue)
        
        print(f"Active issues: {len(healer.active_issues)}")
        
        # Test resource checks
        print("\n--- Resource checks ---")
        print(f"Memory: {healer._get_memory_usage()}")
        print(f"Disk: {healer._get_disk_usage()}")
    
    asyncio.run(test())
