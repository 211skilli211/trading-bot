#!/usr/bin/env python3
"""
Check all credentials and bot readiness
"""

import os
import re
import json
from datetime import datetime

def check_env():
    """Load and check .env file"""
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    return env_vars

def is_configured(value):
    """Check if a value is properly configured"""
    if not value:
        return False
    if value.startswith('your_'):
        return False
    if value == '***':
        return False
    return True

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           🔐 CREDENTIAL STATUS CHECK                              ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    env = check_env()
    
    # Check exchanges
    exchanges = [
        ('BINANCE', 'Binance'),
        ('COINBASE', 'Coinbase'),
        ('KRAKEN', 'Kraken'),
        ('BYBIT', 'Bybit'),
        ('KUCOIN', 'KuCoin'),
    ]
    
    print("📊 EXCHANGE API CREDENTIALS:")
    print('-' * 60)
    
    configured_exchanges = []
    missing_exchanges = []
    
    for prefix, name in exchanges:
        key = env.get(f'{prefix}_API_KEY', '')
        secret = env.get(f'{prefix}_SECRET', '')
        
        if is_configured(key) and is_configured(secret):
            configured_exchanges.append(name)
            print(f"  ✅ {name:<12} Configured")
        else:
            missing_exchanges.append(name)
            print(f"  ❌ {name:<12} Not configured")
    
    print('-' * 60)
    print(f"Configured: {len(configured_exchanges)}/5 exchanges")
    
    # Check Solana
    print("\n🔑 SOLANA DEX CREDENTIALS:")
    print('-' * 60)
    
    sol_key = env.get('SOLANA_PRIVATE_KEY', '')
    sol_rpc = env.get('SOLANA_RPC_URL', '')
    
    if is_configured(sol_key):
        print(f"  ✅ Private Key  Configured ({sol_key[:15]}...)")
    else:
        print(f"  ❌ Private Key  Not configured")
    
    if is_configured(sol_rpc):
        print(f"  ✅ RPC URL     {sol_rpc[:40]}...")
    else:
        print(f"  ❌ RPC URL     Not configured")
    
    # Check wallet file
    if os.path.exists('solana_wallet_live.json'):
        with open('solana_wallet_live.json') as f:
            wallet = json.load(f)
        print(f"  ✅ Wallet File  {wallet['public_key'][:30]}...")
    else:
        print(f"  ❌ Wallet File  Not found")
    
    print('-' * 60)
    
    # Check Telegram
    print("\n📱 TELEGRAM ALERTS:")
    print('-' * 60)
    
    tg_token = env.get('TELEGRAM_BOT_TOKEN', '')
    tg_chat = env.get('TELEGRAM_CHAT_ID', '')
    
    if is_configured(tg_token) and is_configured(tg_chat):
        print(f"  ✅ Configured")
    else:
        print(f"  ❌ Not configured (optional)")
    
    print('-' * 60)
    
    # Check Birdeye
    print("\n🔍 BIRDEYE API (Solana DEX Data):")
    print('-' * 60)
    
    birdeye = env.get('BIRDEYE_API_KEY', '')
    if is_configured(birdeye):
        print(f"  ✅ Configured")
    else:
        print(f"  ⚠️  Using demo key (rate limited)")
    
    
    # Check Jupiter (optional - works without key)
    print("\n🪐 JUPITER DEX (Solana Swaps):")
    print('-' * 60)
    print("  ✅ Public API - No key required for basic swaps")
    print("  ✅ Quote API: https://quote-api.jup.ag/v6")
    jupiter_key = env.get('JUPITER_API_KEY', '')
    if is_configured(jupiter_key):
        print(f"  ✅ Premium key configured (optional)")
    else:
        print(f"  ℹ️  Using free public API (sufficient for most trading)")
    print('-' * 60)

    # Overall readiness
    print("\n" + "="*60)
    print("📋 BOT READINESS SUMMARY:")
    print('='*60)
    
    ready_for_paper = len(configured_exchanges) >= 0  # Paper needs no keys
    ready_for_live_cex = len(configured_exchanges) >= 2
    ready_for_solana = is_configured(sol_key) and is_configured(sol_rpc)
    
    print(f"\n  📝 Paper Trading:     {'✅ Ready' if ready_for_paper else '❌ Not ready'}")
    print(f"  💱 CEX Live Trading:  {'✅ Ready' if ready_for_live_cex else '❌ Need 2+ exchanges'}")
    print(f"  💎 Solana DEX:        {'✅ Ready' if ready_for_solana else '❌ Need wallet funding'}")
    
    # Recommendations
    print("\n" + "="*60)
    print("📢 RECOMMENDATIONS:")
    print('='*60)
    
    if len(configured_exchanges) < 2:
        print("\n1️⃣  To enable CEX arbitrage:")
        print("   → Run: python setup_credentials.py")
        print("   → Get API keys from Binance + Coinbase (minimum)")
    
    if not ready_for_solana:
        print("\n2️⃣  To enable Solana DEX trading:")
        print("   → Fund wallet: 6QqkyDZj62L7uvNvAeHNd1bs8PkbVJzGU1ZHiEeV57rS")
        print("   → Send 20 USDT (SPL) + 0.1 SOL")
        print("   → Verify: https://solscan.io/account/6QqkyDZj62L7uvNvAeHNd1bs8PkbVJzGU1ZHiEeV57rS")
    
    if not is_configured(tg_token):
        print("\n3️⃣  To enable Telegram alerts:")
        print("   → Run: python setup_telegram.py")
        print("   → Message @BotFather to create a bot")
    
    print("\n" + "="*60)
    print(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

if __name__ == "__main__":
    main()
