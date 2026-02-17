#!/usr/bin/env python3
"""
Safely switch trading bot to LIVE mode
"""

import json
import os
from datetime import datetime

def check_requirements():
    """Check if ready for live trading"""
    issues = []
    warnings = []
    
    print("🔍 CHECKING LIVE MODE REQUIREMENTS...")
    print("=" * 60)
    
    # 1. Check wallet funding
    print("\n1. Checking Solana wallet...")
    try:
        with open('solana_wallet_live.json') as f:
            wallet = json.load(f)
        print(f"   ✅ Wallet: {wallet['public_key'][:25]}...")
        warnings.append("Wallet created but funding status unknown - verify on solscan.io")
    except:
        issues.append("Solana wallet not created - run setup first")
    
    # 2. Check exchange balances
    print("\n2. Checking exchange balances...")
    try:
        with open('.env') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ[key] = val
        
        import ccxt
        
        try:
            ex = ccxt.binance({
                'apiKey': os.getenv('BINANCE_API_KEY'),
                'secret': os.getenv('BINANCE_SECRET'),
                'enableRateLimit': True,
            })
            bal = ex.fetch_balance()
            usdt = bal.get('USDT', {}).get('free', 0)
            print(f"   ✅ Binance: ${usdt} USDT")
            if usdt < 100:
                warnings.append(f"Low Binance balance: ${usdt} - recommend $500+")
        except Exception as e:
            issues.append(f"Binance connection failed: {e}")
    except:
        pass
    
    # 3. Check config
    print("\n3. Checking configuration...")
    try:
        with open('config.json') as f:
            cfg = json.load(f)
        current_mode = cfg.get('bot', {}).get('mode', 'PAPER')
        print(f"   Current mode: {current_mode}")
        if current_mode == 'LIVE':
            warnings.append("Bot is already in LIVE mode!")
    except:
        issues.append("config.json not found")
    
    # Report
    print("\n" + "=" * 60)
    print("📋 CHECK RESULTS:")
    print("=" * 60)
    
    if issues:
        print("\n❌ CRITICAL ISSUES (Must fix before live):")
        for issue in issues:
            print(f"   • {issue}")
    
    if warnings:
        print("\n⚠️  WARNINGS (Recommend fixing):")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not issues and not warnings:
        print("\n✅ All checks passed! Ready for live trading.")
    
    return len(issues) == 0

def switch_mode(mode='LIVE'):
    """Switch trading mode"""
    print(f"\n🔄 Switching to {mode} mode...")
    
    try:
        with open('config.json', 'r') as f:
            cfg = json.load(f)
        
        cfg['bot']['mode'] = mode
        cfg['bot']['switched_at'] = datetime.now().isoformat()
        
        with open('config.json', 'w') as f:
            json.dump(cfg, f, indent=2)
        
        print(f"✅ Successfully switched to {mode} mode!")
        print(f"   Config saved to config.json")
        print(f"   Timestamp: {cfg['bot']['switched_at']}")
        
        # Backup
        with open(f'config_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(cfg, f, indent=2)
        print(f"   Backup created")
        
        return True
        
    except Exception as e:
        print(f"❌ Error switching mode: {e}")
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           🚀 LIVE MODE SWITCHER                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  ⚠️  WARNING: This will enable REAL trades with REAL money!       ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    # Check requirements
    ready = check_requirements()
    
    if not ready:
        print("\n❌ Cannot switch to live mode - fix critical issues first")
        return
    
    print("\n" + "=" * 60)
    print("🔄 LIVE MODE SWITCH OPTIONS:")
    print("=" * 60)
    print("""
1. FULL LIVE (All exchanges + Solana)
   → Real trades everywhere
   
2. CEX-ONLY LIVE (Binance/Kraken only)
   → Real CEX trades, paper Solana
   
3. SOLANA-ONLY LIVE (Jupiter DEX only)
   → Real Solana swaps, paper CEX
   
4. CANCEL - Stay in paper mode
""")
    
    choice = input("Select option (1-4): ").strip()
    
    if choice == '1':
        confirm = input("\n⚠️  FULL LIVE MODE - Type 'LIVE' to confirm: ")
        if confirm == 'LIVE':
            switch_mode('LIVE')
            print("\n✅ BOT IS NOW IN FULL LIVE MODE!")
            print("   Restart bot to apply changes: Ctrl+C, then ~/start-bot.sh")
        else:
            print("\n❌ Cancelled - confirmation mismatch")
    
    elif choice == '2':
        confirm = input("\n⚠️  CEX-ONLY LIVE - Type 'CEX' to confirm: ")
        if confirm == 'CEX':
            switch_mode('LIVE_CEX')
            print("\n✅ BOT IS IN CEX-ONLY LIVE MODE!")
            print("   Solana will remain in paper mode")
        else:
            print("\n❌ Cancelled")
    
    elif choice == '3':
        confirm = input("\n⚠️  SOLANA-ONLY LIVE - Type 'SOL' to confirm: ")
        if confirm == 'SOL':
            switch_mode('LIVE_SOLANA')
            print("\n✅ BOT IS IN SOLANA-ONLY LIVE MODE!")
            print("   CEX will remain in paper mode")
        else:
            print("\n❌ Cancelled")
    
    elif choice == '4':
        print("\n✅ Cancelled - staying in paper mode")
    
    else:
        print("\n❌ Invalid option")

if __name__ == "__main__":
    main()
