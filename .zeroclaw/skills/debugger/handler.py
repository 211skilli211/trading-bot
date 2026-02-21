#!/usr/bin/env python3
"""Debugger Skill Handler"""
import sys
import subprocess
import os
from datetime import datetime

def run_command(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()[:2000]  # Limit output
    except Exception as e:
        return f"Error: {str(e)}"

def check_logs():
    """Check recent logs for errors"""
    logs = []
    log_files = [
        "/root/trading-bot/bot.log",
        "/root/trading-bot/dashboard.log",
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            errors = run_command(f"grep -i 'error\\|exception\\|critical' {log_file} 2>/dev/null | tail -5")
            if errors:
                logs.append(f"📄 {os.path.basename(log_file)}:")
                logs.append(errors)
    
    return "\n".join(logs) if logs else "✅ No recent errors found"

def check_processes():
    """Check if processes are running"""
    processes = []
    
    # Check dashboard
    dashboard = run_command("pgrep -f 'python.*dashboard.py' | head -1")
    processes.append(f"Dashboard: {'✅ Running' if dashboard else '❌ Not running'}")
    
    # Check ZeroClaw
    zc_personal = run_command("pgrep -f 'zeroclaw.*3000' | head -1")
    zc_trading = run_command("pgrep -f 'zeroclaw.*3001' | head -1")
    processes.append(f"ZeroClaw Personal: {'✅ Running' if zc_personal else '❌ Not running'}")
    processes.append(f"ZeroClaw Trading: {'✅ Running' if zc_trading else '❌ Not running'}")
    
    return "\n".join(processes)

if __name__ == "__main__":
    print("🔍 DEBUG ANALYSIS")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    # Check processes
    print("🔧 PROCESS STATUS:")
    print(check_processes())
    print()
    
    # Check logs
    print("📋 RECENT ERRORS:")
    print(check_logs())
    print()
    
    # System check
    print("💻 SYSTEM CHECK:")
    disk = run_command("df -h / | tail -1 | awk '{print $5}'")
    if disk:
        disk_num = int(disk.replace('%', ''))
        disk_status = "✅" if disk_num < 80 else "⚠️" if disk_num < 90 else "❌"
        print(f"  {disk_status} Disk usage: {disk}")
    
    mem = run_command("free | grep Mem | awk '{printf \"%.0f\", $3/$2 * 100}'")
    if mem:
        mem_num = int(mem)
        mem_status = "✅" if mem_num < 70 else "⚠️" if mem_num < 85 else "❌"
        print(f"  {mem_status} Memory usage: {mem}%")
    
    print()
    print("💡 QUICK FIXES:")
    print("  1. If processes stopped: Restart with launch_bot.py")
    print("  2. If disk full: Clear logs with 'rm /root/trading-bot/*.log'")
    print("  3. If memory high: Restart the bot")
