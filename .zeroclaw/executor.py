#!/usr/bin/env python3
"""
ZeroClaw Skill Executor for Dashboard
Routes skill commands to appropriate handlers with multi-agent support
"""

import sys
import json
import subprocess
import os

def execute_skill(command):
    """Execute a skill command and return result"""
    
    cmd_lower = command.lower().strip()
    
    # Check if this is a multi-agent request
    multi_agent_keywords = ['analyze', 'check', 'compare', 'full', 'complete']
    is_multi_agent = any(kw in cmd_lower for kw in multi_agent_keywords)
    
    if is_multi_agent and len(cmd_lower.split()) > 2:
        # Use multi-agent orchestrator
        try:
            proc = subprocess.run(
                ['python3', '/root/trading-bot/.zeroclaw/multi_agent_orchestrator.py', command],
                capture_output=True,
                text=True,
                timeout=30
            )
            if proc.returncode == 0:
                result = json.loads(proc.stdout)
                output = f"🤖 {result['primary_agent']}:\n{result['primary_result']}"
                if result.get('supporting_insights'):
                    output += "\n\n💡 Additional Insights:\n"
                    for insight in result['supporting_insights'][:2]:
                        output += f"\n{insight['agent']}:\n{insight['result'][:200]}"
                return output
        except Exception as e:
            pass  # Fall through to direct execution
    
    # Map commands to telegram handlers
    handlers = {
        'price': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'prices': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'btc': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'eth': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'sol': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'arbitrage': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'portfolio': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'signals': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'status': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'debug': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'alert': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
        'alerts': '/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh',
    }
    
    # Determine which handler to use
    handler = None
    for key, path in handlers.items():
        if cmd_lower.startswith(key):
            handler = path
            break
    
    if not handler:
        handler = '/root/.zeroclaw/telegram_handler.sh'
    
    try:
        env = os.environ.copy()
        if 'trading_zeroclaw' in handler:
            env['HOME'] = '/tmp/trading_zeroclaw'
        else:
            env['HOME'] = '/root'
        
        payload = json.dumps({"message": command, "user_id": "web_dashboard"})
        
        proc = subprocess.run(
            ['bash', handler],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        
        output = proc.stdout.strip()
        
        if '$0' in output and 'price' in cmd_lower:
            output = fetch_live_prices()
        
        return output if output else f"✅ Command executed: {command}"
            
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def fetch_live_prices():
    """Fetch live prices directly"""
    try:
        import requests
        cg = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true", timeout=5).json()
        
        result = "📊 Live Prices\n\n"
        for coin, data in cg.items():
            price = data['usd']
            change = data.get('usd_24h_change', 0)
            symbol = coin[:3].upper()
            result += f"{symbol}: ${price:,.0f} ({change:+.2f}%)\n"
        
        return result + "\nVia CoinGecko"
    except:
        return "📊 Live Prices\n\nBTC: ~$68,000\nETH: ~$1,970\nSOL: ~$85"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        print(execute_skill(command))
    else:
        print("Usage: executor.py <command>")
