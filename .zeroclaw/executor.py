#!/usr/bin/env python3
"""
ZeroClaw Skill Executor with Messenger Agent Formatting
Routes commands and formats responses beautifully
"""
import sys
import subprocess
import os
import json

SKILL_DIR = "/root/trading-bot/.zeroclaw/skills"
MESSENGER = "/root/trading-bot/.zeroclaw/skills/messenger-agent/handler.py"

def format_with_messenger(format_type, data):
    """Format data using messenger agent"""
    try:
        result = subprocess.run(
            ["python3", MESSENGER, format_type, json.dumps(data)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None

def run_skill(skill_name, command):
    """Execute a skill handler"""
    handler_path = os.path.join(SKILL_DIR, skill_name, "handler.py")
    
    if not os.path.exists(handler_path):
        return f"⚠️ Skill '{skill_name}' not available"
    
    try:
        result = subprocess.run(
            ["python3", handler_path, command],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"⚠️ Error: {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return "⏱️ Request timed out"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def route_command(command):
    """Route command to appropriate skill with formatting"""
    command_lower = command.lower()
    
    # Price Check
    if any(word in command_lower for word in ["price", "worth", "cost", "check btc", "check eth"]):
        output = run_skill("price-check", command)
        return output
    
    # System Diagnostic
    elif any(word in command_lower for word in ["status", "health", "diagnose", "system"]):
        output = run_skill("system-diagnostic", command)
        return output
    
    # Performance Monitor
    elif any(word in command_lower for word in ["performance", "pnl", "profit", "stats", "how am i"]):
        output = run_skill("performance-monitor", command)
        return output
    
    # Debugger
    elif any(word in command_lower for word in ["debug", "error", "wrong", "fix"]):
        output = run_skill("debugger", command)
        return output
    
    # Log Analyzer
    elif any(word in command_lower for word in ["logs", "activity", "history", "what happened"]):
        output = run_skill("log-analyzer", command)
        return output
    
    # BTC/ETH shorthand
    elif "btc" in command_lower or "bitcoin" in command_lower:
        return run_skill("price-check", "price of BTC")
    elif "eth" in command_lower or "ethereum" in command_lower:
        return run_skill("price-check", "price of ETH")
    
    # Help
    elif any(word in command_lower for word in ["help", "commands", "what can you do"]):
        return show_help()
    
    # Default
    else:
        return f"🤖 I can help with:\n\n💰 Price: \"BTC price\"\n🔍 Status: \"System status\"\n📊 Stats: \"Performance\"\n\nType 'help' for more!"

def show_help():
    """Show available commands"""
    return """🤖 *TRADING BOT COMMANDS*

💰 *PRICE CHECKS:*
• "BTC price" or "Bitcoin"
• "ETH price" or "Ethereum"
• "Price of SOL"

🔍 *DIAGNOSTICS:*
• "System status"
• "Health check"
• "Debug error"

📊 *ANALYSIS:*
• "Performance"
• "Trading stats"
• "How am I doing?"

⚡ *QUICK:*
Just type "BTC" for Bitcoin price!

What would you like to check?"""

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = sys.stdin.read().strip()
    
    if command:
        response = route_command(command)
        print(response)
    else:
        print("🤖 Hi! I'm your trading assistant.\n\nTry: 'BTC price' or 'System status'")

if __name__ == "__main__":
    main()
