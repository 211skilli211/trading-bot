#!/usr/bin/env python3
"""System Diagnostic Skill Handler"""
import sys
import subprocess
import json
from datetime import datetime

def check_health(endpoint, name):
    """Check if service is healthy"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", endpoint],
            capture_output=True, text=True, timeout=5
        )
        status_code = result.stdout.strip()
        if status_code == "200":
            return f"✅ {name}: Healthy"
        else:
            return f"❌ {name}: Error {status_code}"
    except Exception as e:
        return f"❌ {name}: {str(e)}"

def run_command(cmd):
    """Run shell command safely"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except:
        return "N/A"

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    print(f"🔍 SYSTEM DIAGNOSTIC REPORT")
    print(f"⏰ {timestamp}")
    print()
    
    # Check ZeroClaw instances
    print("🧠 ZEROCLAW INSTANCES:")
    print(check_health("http://localhost:3000/health", "Personal (3000)"))
    print(check_health("http://localhost:3001/health", "Trading (3001)"))
    print()
    
    # Check Dashboard
    print("🖥️  DASHBOARD:")
    print(check_health("http://localhost:8080/", "Web Interface"))
    print()
    
    # System resources
    print("💾 SYSTEM RESOURCES:")
    
    # Disk usage
    disk = run_command("df -h /root/trading-bot 2>/dev/null | tail -1 | awk '{print $5}'")
    if disk:
        print(f"  Disk Usage: {disk}")
    
    # Memory
    mem = run_command("free -h 2>/dev/null | grep Mem | awk '{print $3 \"/\" $2}'")
    if mem:
        print(f"  Memory Used: {mem}")
    
    # Load average
    load = run_command("uptime | awk -F'load average:' '{print $2}'")
    if load:
        print(f"  Load Average:{load}")
    
    print()
    
    # Running processes
    print("🔧 ACTIVE PROCESSES:")
    processes = run_command("ps aux | grep -E 'zeroclaw|python.*dashboard' | grep -v grep | wc -l")
    if processes and processes != "0":
        print(f"  ✅ {processes} trading processes running")
    else:
        print(f"  ⚠️  No trading processes detected")
    
    print()
    print("📊 Overall: Check individual components above")
