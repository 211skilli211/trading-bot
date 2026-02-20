#!/usr/bin/env python3
"""
Pump.fun Integration Example
============================

Demonstrates how to use the Pump.fun scraper for token discovery
and arbitrage opportunity detection.

Usage:
    python pumpfun_integration.py --scan          # Scan for new tokens
    python pumpfun_integration.py --migrations    # Find tokens nearing migration
    python pumpfun_integration.py --arbitrage     # Find arbitrage opportunities
    python pumpfun_integration.py --monitor       # Continuous monitoring
"""

import argparse
import time
import json
from datetime import datetime, timezone
from typing import List

# Import Pump.fun scraper
try:
    from scrapers.pumpfun import (
        PumpFunScraper, 
        PumpFunConfig, 
        TokenCandidate,
        get_scraper,
        discover_new_tokens,
        get_high_priority_tokens
    )
    PUMPFUN_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Pump.fun scraper: {e}")
    PUMPFUN_AVAILABLE = False

# Import DEXScreener for price comparison
try:
    from dexscreener_scanner import DEXScreenerScanner
    DEXSCREENER_AVAILABLE = True
except ImportError:
    DEXSCREENER_AVAILABLE = False


def print_token(token: TokenCandidate, verbose: bool = False):
    """Pretty print token information."""
    print(f"\n  {'='*60}")
    print(f"  🪙 {token.symbol} ({token.name[:40]})")
    print(f"  {'='*60}")
    print(f"  Mint: {token.mint_address}")
    print(f"  Market Cap: ${token.usd_market_cap:,.2f}")
    print(f"  Price: ${token.price_usd:.12f}")
    print(f"  Bonding Curve: {token.bonding_curve_progress:.1f}%")
    
    if token.is_nearing_migration:
        eta = token.migration_eta_minutes
        eta_str = f"~{eta:.0f} min" if eta else "soon"
        print(f"  🚨 MIGRATION IMMINENT! ({eta_str})")
    
    if token.creation_time:
        age_mins = token.age_minutes
        age_str = f"{age_mins:.1f} minutes" if age_mins < 60 else f"{age_mins/60:.1f} hours"
        print(f"  Age: {age_str}")
    
    if token.creator_address:
        print(f"  Creator: {token.creator_address[:20]}...")
    
    if verbose:
        if token.description:
            print(f"  Description: {token.description[:100]}...")
        print(f"  Priority: {token.priority}")
        print(f"  Migrated: {'Yes' if token.is_migrated else 'No'}")
        if token.raydium_pool:
            print(f"  Raydium Pool: {token.raydium_pool}")


def scan_new_tokens(limit: int = 20, verbose: bool = False):
    """Scan for new tokens on Pump.fun."""
    print("=" * 70)
    print("🔍 SCANNING PUMP.FUN FOR NEW TOKENS")
    print("=" * 70)
    
    scraper = get_scraper()
    tokens = scraper.get_new_tokens(limit=limit)
    
    print(f"\n✅ Found {len(tokens)} new tokens")
    
    for token in tokens:
        print_token(token, verbose=verbose)
    
    # Summary
    migrating = [t for t in tokens if t.is_nearing_migration]
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY: {len(tokens)} tokens, {len(migrating)} nearing migration")
    print(f"{'='*70}")
    
    return tokens


def find_migrating_tokens():
    """Find tokens that are about to migrate to Raydium."""
    print("=" * 70)
    print("🚀 FINDING TOKENS NEARING MIGRATION")
    print("=" * 70)
    
    scraper = get_scraper()
    tokens = scraper.get_migrating_tokens()
    
    print(f"\n✅ Found {len(tokens)} tokens nearing migration\n")
    
    for i, token in enumerate(tokens, 1):
        print(f"{i}. 🚨 {token.symbol}")
        print(f"   Market Cap: ${token.usd_market_cap:,.2f}")
        print(f"   Bonding Progress: {token.bonding_curve_progress:.1f}%")
        print(f"   Estimated Migration: ~{token.migration_eta_minutes or '?':.0f} min")
        print()
    
    return tokens


def find_arbitrage_opportunities():
    """Find arbitrage opportunities between Pump.fun and Raydium."""
    print("=" * 70)
    print("💰 FINDING ARBITRAGE OPPORTUNITIES")
    print("=" * 70)
    
    if not DEXSCREENER_AVAILABLE:
        print("❌ DEXScreener not available for price comparison")
        return []
    
    scraper = get_scraper()
    dex = DEXScreenerScanner()
    
    # Get tokens nearing migration (high volatility = arbitrage potential)
    tokens = scraper.get_new_tokens(limit=30)
    opportunities = []
    
    print(f"\nAnalyzing {len(tokens)} tokens for price discrepancies...\n")
    
    for token in tokens:
        # Skip tokens without proper market data
        if token.usd_market_cap < 1000:
            continue
        
        # Get DEX prices
        pairs = dex.get_token_pairs(token.mint_address)
        
        pump_price = token.price_usd
        raydium_price = None
        
        for pair in pairs:
            dex_name = pair.get('dexId', '').lower()
            price = float(pair.get('priceUsd', 0))
            
            if 'raydium' in dex_name and price > 0:
                raydium_price = price
                break
        
        # Check for arbitrage
        if pump_price > 0 and raydium_price and raydium_price > 0:
            spread = abs(raydium_price - pump_price) / min(pump_price, raydium_price) * 100
            
            if spread > 1.0:  # 1% minimum spread
                opportunities.append({
                    'token': token,
                    'pump_price': pump_price,
                    'raydium_price': raydium_price,
                    'spread_pct': spread
                })
                
                print(f"💰 {token.symbol}")
                print(f"   Pump.fun:  ${pump_price:.12f}")
                print(f"   Raydium:   ${raydium_price:.12f}")
                print(f"   Spread:    {spread:.2f}%")
                print()
    
    # Sort by spread
    opportunities.sort(key=lambda x: x['spread_pct'], reverse=True)
    
    print(f"{'='*70}")
    print(f"📊 Found {len(opportunities)} arbitrage opportunities")
    print(f"{'='*70}")
    
    return opportunities


def continuous_monitor(interval: int = 30):
    """Continuously monitor Pump.fun for new opportunities."""
    print("=" * 70)
    print("🔔 CONTINUOUS MONITORING MODE")
    print(f"⏱️  Check interval: {interval} seconds")
    print("=" * 70)
    print("\nPress Ctrl+C to stop\n")
    
    scraper = get_scraper()
    seen_tokens = set()
    
    try:
        while True:
            timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"[{timestamp}] Scanning...", end=' ')
            
            tokens = scraper.get_new_tokens(limit=20)
            new_tokens = [t for t in tokens if t.mint_address not in seen_tokens]
            
            # Update seen tokens
            for t in tokens:
                seen_tokens.add(t.mint_address)
            
            migrating = [t for t in new_tokens if t.is_nearing_migration]
            
            if new_tokens:
                print(f"🆕 {len(new_tokens)} new, {len(migrating)} migrating")
                
                for token in migrating:
                    print(f"  🚨 {token.symbol} nearing migration! ({token.bonding_curve_progress:.1f}%)")
            else:
                print("No new tokens")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped by user")
        print(f"Total unique tokens seen: {len(seen_tokens)}")


def export_tokens(filepath: str, limit: int = 100):
    """Export token data to JSON file."""
    print(f"Exporting {limit} tokens to {filepath}...")
    
    scraper = get_scraper()
    tokens = scraper.get_new_tokens(limit=limit)
    
    data = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'count': len(tokens),
        'tokens': [t.to_dict() for t in tokens]
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"✅ Exported {len(tokens)} tokens to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description='Pump.fun Token Discovery and Arbitrage Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pumpfun_integration.py --scan --limit 50
  python pumpfun_integration.py --migrations
  python pumpfun_integration.py --arbitrage
  python pumpfun_integration.py --monitor --interval 60
  python pumpfun_integration.py --export tokens.json
        """
    )
    
    parser.add_argument('--scan', action='store_true',
                        help='Scan for new tokens')
    parser.add_argument('--migrations', action='store_true',
                        help='Find tokens nearing migration')
    parser.add_argument('--arbitrage', action='store_true',
                        help='Find arbitrage opportunities')
    parser.add_argument('--monitor', action='store_true',
                        help='Continuous monitoring mode')
    parser.add_argument('--export', type=str, metavar='FILE',
                        help='Export tokens to JSON file')
    parser.add_argument('--limit', type=int, default=20,
                        help='Maximum tokens to fetch (default: 20)')
    parser.add_argument('--interval', type=int, default=30,
                        help='Monitoring interval in seconds (default: 30)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    
    args = parser.parse_args()
    
    if not PUMPFUN_AVAILABLE:
        print("❌ Pump.fun scraper not available. Please check your installation.")
        return
    
    # Default to scan if no action specified
    if not any([args.scan, args.migrations, args.arbitrage, args.monitor, args.export]):
        args.scan = True
    
    if args.scan:
        scan_new_tokens(limit=args.limit, verbose=args.verbose)
    
    if args.migrations:
        find_migrating_tokens()
    
    if args.arbitrage:
        find_arbitrage_opportunities()
    
    if args.monitor:
        continuous_monitor(interval=args.interval)
    
    if args.export:
        export_tokens(args.export, limit=args.limit)


if __name__ == "__main__":
    main()
