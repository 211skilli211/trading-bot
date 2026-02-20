#!/usr/bin/env python3
"""
Health Monitor Module
Provides system health checks for the trading bot.
"""

import os
import sys
import sqlite3
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Try to import psutil, fallback to manual methods if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class HealthMonitor:
    """
    Monitors trading bot health including:
    - Exchange connectivity
    - Database accessibility
    - System resources (memory, disk)
    """
    
    def __init__(self, db_path: str = "trades.db"):
        """Initialize health monitor."""
        self.db_path = db_path
        self.checks = {}
        
    def check_exchange_connectivity(self) -> Dict[str, Any]:
        """
        Test connectivity to all configured exchanges.
        
        Returns:
            Dict with status and details for each exchange
        """
        results = {
            "name": "Exchange Connectivity",
            "status": "healthy",
            "exchanges": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # List of exchanges to check
        exchanges = [
            {"name": "Binance", "url": "https://api.binance.com/api/v3/ping", "timeout": 5},
            {"name": "Coinbase", "url": "https://api.coinbase.com/v2/exchange-rates?currency=BTC", "timeout": 5},
            {"name": "Kraken", "url": "https://api.kraken.com/0/public/SystemStatus", "timeout": 5},
            {"name": "Bybit", "url": "https://api.bybit.com/v5/market/time", "timeout": 5},
            {"name": "KuCoin", "url": "https://api.kucoin.com/api/v1/timestamp", "timeout": 5},
        ]
        
        any_unhealthy = False
        
        for exchange in exchanges:
            try:
                start_time = datetime.now()
                response = requests.get(exchange["url"], timeout=exchange["timeout"])
                latency = (datetime.now() - start_time).total_seconds() * 1000
                
                is_healthy = response.status_code == 200
                if not is_healthy:
                    any_unhealthy = True
                    
                results["exchanges"][exchange["name"]] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "latency_ms": round(latency, 2),
                    "status_code": response.status_code
                }
            except requests.exceptions.Timeout:
                any_unhealthy = True
                results["exchanges"][exchange["name"]] = {
                    "status": "unhealthy",
                    "error": "Timeout",
                    "latency_ms": None
                }
            except Exception as e:
                any_unhealthy = True
                results["exchanges"][exchange["name"]] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "latency_ms": None
                }
        
        if any_unhealthy:
            results["status"] = "degraded"
            
        return results
    
    def check_database(self) -> Dict[str, Any]:
        """
        Verify database is accessible and functioning.
        
        Returns:
            Dict with DB health status
        """
        result = {
            "name": "Database",
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Check if file exists
            if not os.path.exists(self.db_path):
                result["status"] = "unhealthy"
                result["error"] = "Database file not found"
                return result
            
            # Try to connect and query
            conn = sqlite3.connect(self.db_path, timeout=5)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            result["tables"] = tables
            
            # Get row counts
            counts = {}
            for table in ["trades", "positions", "price_history"]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                except:
                    counts[table] = 0
            result["row_counts"] = counts
            
            # Check DB size
            result["size_mb"] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
            
            conn.close()
            
        except sqlite3.Error as e:
            result["status"] = "unhealthy"
            result["error"] = f"SQLite error: {str(e)}"
        except Exception as e:
            result["status"] = "unhealthy"
            result["error"] = str(e)
            
        return result
    
    def _read_meminfo(self) -> Dict[str, int]:
        """Read memory info from /proc/meminfo (Linux fallback)."""
        mem_info = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    key, value = line.split(':')
                    mem_info[key.strip()] = int(value.split()[0]) * 1024  # Convert KB to bytes
        except:
            pass
        return mem_info
    
    def _read_statm(self, pid: int) -> Dict[str, int]:
        """Read process memory from /proc/PID/statm (Linux fallback)."""
        try:
            with open(f'/proc/{pid}/statm', 'r') as f:
                values = f.read().split()
                page_size = os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else 4096
                return {
                    'rss': int(values[1]) * page_size,
                    'vsize': int(values[0]) * page_size
                }
        except:
            return {'rss': 0, 'vsize': 0}
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """
        Monitor system RAM usage.
        
        Returns:
            Dict with memory statistics
        """
        result = {
            "name": "Memory Usage",
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            if PSUTIL_AVAILABLE:
                memory = psutil.virtual_memory()
                result["total_gb"] = round(memory.total / (1024**3), 2)
                result["available_gb"] = round(memory.available / (1024**3), 2)
                result["used_gb"] = round(memory.used / (1024**3), 2)
                result["percent_used"] = memory.percent
            else:
                # Fallback to reading /proc/meminfo
                mem_info = self._read_meminfo()
                total = mem_info.get('MemTotal', 0)
                free = mem_info.get('MemFree', 0)
                buffers = mem_info.get('Buffers', 0)
                cached = mem_info.get('Cached', 0)
                available = free + buffers + cached
                used = total - available
                
                result["total_gb"] = round(total / (1024**3), 2)
                result["available_gb"] = round(available / (1024**3), 2)
                result["used_gb"] = round(used / (1024**3), 2)
                result["percent_used"] = round((used / total) * 100, 1) if total > 0 else 0
            
            # Status thresholds
            if result["percent_used"] > 90:
                result["status"] = "critical"
            elif result["percent_used"] > 75:
                result["status"] = "warning"
            else:
                result["status"] = "healthy"
                
        except Exception as e:
            result["status"] = "unknown"
            result["error"] = str(e)
            
        return result
    
    def check_disk_space(self) -> Dict[str, Any]:
        """
        Check available disk space.
        
        Returns:
            Dict with disk usage statistics
        """
        result = {
            "name": "Disk Space",
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            db_dir = os.path.dirname(os.path.abspath(self.db_path)) or "."
            
            if PSUTIL_AVAILABLE:
                disk = psutil.disk_usage(db_dir)
                result["total_gb"] = round(disk.total / (1024**3), 2)
                result["free_gb"] = round(disk.free / (1024**3), 2)
                result["used_gb"] = round(disk.used / (1024**3), 2)
                result["percent_used"] = disk.percent
            else:
                # Fallback to using df command
                import subprocess
                stat = os.statvfs(db_dir)
                total = stat.f_blocks * stat.f_frsize
                free = stat.f_bavail * stat.f_frsize
                used = total - free
                
                result["total_gb"] = round(total / (1024**3), 2)
                result["free_gb"] = round(free / (1024**3), 2)
                result["used_gb"] = round(used / (1024**3), 2)
                result["percent_used"] = round((used / total) * 100, 1) if total > 0 else 0
            
            # Status thresholds
            if result["percent_used"] > 95:
                result["status"] = "critical"
            elif result["percent_used"] > 85:
                result["status"] = "warning"
            else:
                result["status"] = "healthy"
                
        except Exception as e:
            result["status"] = "unknown"
            result["error"] = str(e)
            
        return result
    
    def check_bot_process(self) -> Dict[str, Any]:
        """
        Check if the trading bot process is running.
        
        Returns:
            Dict with bot process status
        """
        result = {
            "name": "Bot Process",
            "status": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Check for PID file
            pid_file = "bot.pid"
            if os.path.exists(pid_file):
                with open(pid_file, "r") as f:
                    pid = int(f.read().strip())
                
                # Check if process exists
                if PSUTIL_AVAILABLE:
                    if psutil.pid_exists(pid):
                        proc = psutil.Process(pid)
                        result["status"] = "running"
                        result["pid"] = pid
                        result["name"] = proc.name()
                        result["cpu_percent"] = proc.cpu_percent(interval=0.1)
                        result["memory_mb"] = round(proc.memory_info().rss / (1024**2), 2)
                        result["uptime_seconds"] = int(datetime.now().timestamp() - proc.create_time())
                    else:
                        result["status"] = "stopped"
                        result["error"] = "PID file exists but process not found"
                else:
                    # Fallback: check if /proc/PID exists
                    if os.path.exists(f'/proc/{pid}'):
                        result["status"] = "running"
                        result["pid"] = pid
                        # Try to read process info
                        try:
                            with open(f'/proc/{pid}/stat', 'r') as f:
                                stat = f.read().split()
                                result["name"] = stat[1].strip('()') if len(stat) > 1 else "unknown"
                            # Get memory
                            mem = self._read_statm(pid)
                            result["memory_mb"] = round(mem['rss'] / (1024**2), 2)
                        except:
                            pass
                    else:
                        result["status"] = "stopped"
                        result["error"] = "PID file exists but process not found"
            else:
                result["status"] = "unknown"
                result["message"] = "No PID file found"
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            
        return result
    
    def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all health checks and return comprehensive report.
        
        Returns:
            Dict with overall status and all check results
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "healthy",
            "checks": {}
        }
        
        # Run all checks
        report["checks"]["exchanges"] = self.check_exchange_connectivity()
        report["checks"]["database"] = self.check_database()
        report["checks"]["memory"] = self.check_memory_usage()
        report["checks"]["disk"] = self.check_disk_space()
        report["checks"]["bot"] = self.check_bot_process()
        
        # Determine overall status
        statuses = []
        for check in report["checks"].values():
            statuses.append(check.get("status", "unknown"))
        
        if "critical" in statuses or "unhealthy" in statuses:
            report["status"] = "unhealthy"
        elif "warning" in statuses or "degraded" in statuses:
            report["status"] = "degraded"
        else:
            report["status"] = "healthy"
            
        return report
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a brief health summary for dashboard display.
        
        Returns:
            Dict with key health indicators
        """
        report = self.run_all_checks()
        
        summary = {
            "status": report["status"],
            "timestamp": report["timestamp"],
            "indicators": {}
        }
        
        # Exchange status - count healthy
        exchanges = report["checks"]["exchanges"].get("exchanges", {})
        healthy_exchanges = sum(1 for e in exchanges.values() if e.get("status") == "healthy")
        total_exchanges = len(exchanges)
        summary["indicators"]["exchanges"] = f"{healthy_exchanges}/{total_exchanges}"
        
        # Database status
        summary["indicators"]["database"] = report["checks"]["database"].get("status", "unknown")
        
        # Memory usage
        memory = report["checks"]["memory"]
        summary["indicators"]["memory"] = f"{memory.get('percent_used', 0)}%"
        
        # Disk usage
        disk = report["checks"]["disk"]
        summary["indicators"]["disk"] = f"{disk.get('percent_used', 0)}%"
        
        # Bot status
        summary["indicators"]["bot"] = report["checks"]["bot"].get("status", "unknown")
        
        return summary


# Simple CLI for testing
if __name__ == "__main__":
    print("Health Monitor - Test Mode")
    print("=" * 60)
    print(f"psutil available: {PSUTIL_AVAILABLE}")
    
    monitor = HealthMonitor()
    
    print("\n[Exchange Connectivity]")
    exchanges = monitor.check_exchange_connectivity()
    for name, status in exchanges.get("exchanges", {}).items():
        icon = "✅" if status.get("status") == "healthy" else "❌"
        latency = f"({status.get('latency_ms', 'N/A')}ms)" if status.get("latency_ms") else ""
        print(f"  {icon} {name}: {status.get('status')} {latency}")
    
    print("\n[Database]")
    db = monitor.check_database()
    icon = "✅" if db.get("status") == "healthy" else "❌"
    print(f"  {icon} Status: {db.get('status')}")
    print(f"     Size: {db.get('size_mb', 'N/A')} MB")
    print(f"     Tables: {', '.join(db.get('tables', []))}")
    
    print("\n[Memory Usage]")
    mem = monitor.check_memory_usage()
    icon = "✅" if mem.get("status") == "healthy" else ("⚠️" if mem.get("status") == "warning" else "❌")
    print(f"  {icon} Used: {mem.get('percent_used', 'N/A')}% ({mem.get('used_gb', 'N/A')}/{mem.get('total_gb', 'N/A')} GB)")
    
    print("\n[Disk Space]")
    disk = monitor.check_disk_space()
    icon = "✅" if disk.get("status") == "healthy" else ("⚠️" if disk.get("status") == "warning" else "❌")
    print(f"  {icon} Used: {disk.get('percent_used', 'N/A')}% ({disk.get('free_gb', 'N/A')} GB free)")
    
    print("\n[Bot Process]")
    bot = monitor.check_bot_process()
    icon = "✅" if bot.get("status") == "running" else "❌"
    print(f"  {icon} Status: {bot.get('status', 'unknown')}")
    if bot.get("pid"):
        print(f"     PID: {bot.get('pid')}")
        print(f"     Memory: {bot.get('memory_mb', 'N/A')} MB")
    
    print("\n" + "=" * 60)
    print("Full Report:")
    full = monitor.run_all_checks()
    print(f"  Overall Status: {full['status'].upper()}")
