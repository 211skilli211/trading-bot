#!/usr/bin/env python3
"""
Interactive credential setup for 211Skilli Trading Bot
"""

import os
import re
import json
from getpass import getpass

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           🔐 EXCHANGE API CREDENTIALS SETUP                       ║
╠══════════════════════════════════════════════════════════════════╣
║  This script will help you configure your exchange API keys      ║
║  Required: At least 2 exchanges for arbitrage to work            ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    # Load current .env
    env_path = '.env'
    if not os.path.exists(env_path):
        print("❌ .env file not found. Creating from example...")
        if os.path.exists('.env.example'):
            with open('.env.example') as f:
                content = f.read()
        else:
            content = ""
    else:
        with open(env_path) as f:
            content = f.read()
    
    print("ℹ️  For each exchange, enter your API credentials.")
    print("   Leave blank to keep current value or skip.\n")
    
    exchanges = [
        ('BINANCE', 'Binance', False),
        ('COINBASE', 'Coinbase', False),
        ('KRAKEN', 'Kraken', True),
        ('BYBIT', 'Bybit', True),
        ('KUCOIN', 'KuCoin', True),
    ]
    
    updates = []
    
    for prefix, name, optional in exchanges:
        print(f"\n{'='*60}")
        print(f"📊 {name} {'(Optional)' if optional else '(Recommended)'}")
        print('='*60)
        
        # Get current values
        key_match = re.search(rf'{prefix}_API_KEY=(.+)', content)
        secret_match = re.search(rf'{prefix}_SECRET=(.+)', content)
        
        current_key = key_match.group(1) if key_match else 'not set'
        current_secret = secret_match.group(1) if secret_match else 'not set'
        
        print(f"Current API Key: {current_key[:10]}..." if len(current_key) > 10 else f"Current API Key: {current_key}")
        
        new_key = input(f"{name} API Key: ").strip()
        if new_key:
            new_secret = getpass(f"{name} Secret: ").strip()
            
            # Update content
            content = re.sub(rf'{prefix}_API_KEY=.*', f'{prefix}_API_KEY={new_key}', content)
            content = re.sub(rf'{prefix}_SECRET=.*', f'{prefix}_SECRET={new_secret}', content)
            updates.append(name)
            
            # Special handling for KuCoin passphrase
            if prefix == 'KUCOIN':
                passphrase = getpass("KuCoin Passphrase: ").strip()
                content = re.sub(r'KUCOIN_PASSPHRASE=.*', f'KUCOIN_PASSPHRASE={passphrase}', content)
    
    # Birdeye API
    print(f"\n{'='*60}")
    print("🔑 Birdeye API (For Solana DEX data)")
    print('='*60)
    print("Get free API key at: https://docs.birdeye.so/")
    print("Or press Enter to use demo key (rate limited)")
    
    birdeye_match = re.search(r'BIRDEYE_API_KEY=(.+)', content)
    current_birdeye = birdeye_match.group(1) if birdeye_match else 'not set'
    print(f"Current: {current_birdeye[:20]}..." if len(str(current_birdeye)) > 20 else f"Current: {current_birdeye}")
    
    new_birdeye = input("Birdeye API Key: ").strip()
    if new_birdeye:
        content = re.sub(r'BIRDEYE_API_KEY=.*', f'BIRDEYE_API_KEY={new_birdeye}', content)
        updates.append('Birdeye')
    elif 'BIRDEYE_API_KEY' not in content:
        # Add default demo key
        content += "\n# Birdeye API for Solana DEX data\nBIRDEYE_API_KEY=ce39d05c472e40898d05c472e408\n"
    
    # Save updated .env
    with open(env_path, 'w') as f:
        f.write(content)
    os.chmod(env_path, 0o600)
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    ✅ CREDENTIALS SAVED                           ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    if updates:
        print(f"Updated: {', '.join(updates)}")
    else:
        print("No changes made (using existing credentials)")
    
    # Summary
    print("\n📋 CURRENT CONFIGURATION:")
    print('-' * 60)
    
    for prefix, name, _ in exchanges:
        key_match = re.search(rf'{prefix}_API_KEY=(.+)', content)
        if key_match and not key_match.group(1).startswith('your_'):
            status = "✅ Configured"
        else:
            status = "❌ Not set"
        print(f"  {name:<12} {status}")
    
    print('-' * 60)
    
    # Verification option
    print("\n🧪 Test your credentials?")
    test = input("Test Binance connection now? (y/N): ").lower()
    if test == 'y':
        test_binance(content)

def test_binance(content):
    """Test Binance API connection"""
    try:
        import ccxt
        
        key_match = re.search(r'BINANCE_API_KEY=(.+)', content)
        secret_match = re.search(r'BINANCE_SECRET=(.+)', content)
        
        if not key_match or key_match.group(1).startswith('your_'):
            print("❌ Binance credentials not configured")
            return
        
        api_key = key_match.group(1)
        secret = secret_match.group(1)
        
        print("\n🔄 Testing Binance connection...")
        
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
        })
        
        # Test by fetching balance
        balance = exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        
        print(f"✅ Binance connected successfully!")
        print(f"   USDT Balance: {usdt_balance}")
        
    except Exception as e:
        print(f"❌ Binance connection failed: {e}")
        print("   Common causes:")
        print("   • Invalid API key/secret")
        print("   • IP not whitelisted")
        print("   • API key doesn't have trading permissions")
        print("   • System time is incorrect")

if __name__ == "__main__":
    main()
