#!/usr/bin/env python3
"""
Trading Orchestrator Skill Handler
Routes incoming commands to appropriate skill handlers
"""
import sys
import subprocess
import os

SKILL_DIR = "/root/trading-bot/.zeroclaw/skills"

def route_command(command):
    """Route command to appropriate skill handler"""
    command_lower = command.lower()
    
    if any(word in command_lower for word in ["price", "check", "worth", "cost"]):
        return run_skill("price-check", command)
    
    elif any(word in command_lower for word in ["status", "health", "diagnose", "check system"]):
        return run_skill("system-diagnostic", command)
    
    elif any(word in command_lower for word in ["performance", "pnl", "profit", "stats", "how am i"]):
        return run_skill("performance-monitor", command)
    
    elif any(word in command_lower for word in ["debug", "error", "wrong", "fix", "trace"]):
        return run_skill("debugger", command)
    
    elif any(word in command_lower for word in ["logs", "activity", "history", "what happened"]):
        return run_skill("log-analyzer", command)
    
    elif any(word in command_lower for word in ["arbitrage", "spread", "opportunity"]):
        return run_skill("arbitrage-scan", command)
    
    elif any(word in command_lower for word in ["help", "commands", "what can you do"]):
        return show_help()
    
    else:
        return show_help()

def run_skill(skill_name, command):
    """Execute a skill handler"""
    handler_path = os.path.join(SKILL_DIR, skill_name, "handler.py")
    
    if not os.path.exists(handler_path):
        return f"⚠️  Skill '{skill_name}' not fully implemented yet"
    
    try:
        result = subprocess.run(
            ["python3", handler_path, command],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout.strip()
        if output:
            return output
        else:
            return f"⚠️  Skill '{skill_name}' returned no output"
    except subprocess.TimeoutExpired:
        return "⏱️  Skill timed out (30s)"
    except Exception as e:
        return f"❌ Error executing skill: {str(e)}"

def show_help():
    """Show available commands"""
    return """📊 TRADING COMMANDS:

• "price of BTC" - Check crypto prices
• "check price ETH" - Get ETH price
• "status" - System health check
• "performance" - Trading stats
• "help" - Show this menu

💡 Try sending a price check command!"""

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = sys.stdin.read().strip()
    
    if command:
        response = route_command(command)
        print(response)
    else:
        print(show_help())
