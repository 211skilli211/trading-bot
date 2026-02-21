#!/usr/bin/env python3
"""Log Analyzer Skill Handler"""
import sys
import os
import re
from datetime import datetime, timedelta

def analyze_log_file(filepath, limit=20):
    """Analyze a single log file"""
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        # Get recent lines
        recent = lines[-limit:]
        
        # Count patterns
        trades = len([l for l in lines if 'trade' in l.lower() or 'executed' in l.lower()])
        errors = len([l for l in lines if 'error' in l.lower() or 'exception' in l.lower()])
        alerts = len([l for l in lines if 'alert' in l.lower()])
        
        return {
            "filename": os.path.basename(filepath),
            "total_lines": len(lines),
            "trades": trades,
            "errors": errors,
            "alerts": alerts,
            "recent": recent
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("📋 ACTIVITY SUMMARY")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    log_files = [
        "/root/trading-bot/bot.log",
        "/root/trading-bot/dashboard.log",
        "/root/trading-bot/alerts.log"
    ]
    
    total_stats = {"trades": 0, "errors": 0, "alerts": 0}
    
    for log_file in log_files:
        result = analyze_log_file(log_file)
        if result and "error" not in result:
            print(f"📄 {result['filename']}:")
            print(f"   Total lines: {result['total_lines']}")
            print(f"   Trades: {result['trades']} | Errors: {result['errors']} | Alerts: {result['alerts']}")
            total_stats["trades"] += result['trades']
            total_stats["errors"] += result['errors']
            total_stats["alerts"] += result['alerts']
            print()
    
    print("📊 OVERALL ACTIVITY:")
    print(f"   🎯 Total Trades: {total_stats['trades']}")
    print(f"   ❌ Total Errors: {total_stats['errors']}")
    print(f"   🔔 Total Alerts: {total_stats['alerts']}")
    
    if total_stats['errors'] > 0:
        print()
        print("⚠️  Errors detected - run 'debugger' for details")
