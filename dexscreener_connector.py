#!/usr/bin/env python3
"""
DEXScreener Sniper - 2026 Best Practices Implementation
New pool sniper for Solana with intelligent scoring and safety features.
"""

import requests
import time
import json
from datetime import datetime, timezone, timedelta
from threading import Thread
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import os


@dataclass
class SniperOpportunity:
    """Represents a sniper opportunity with full metadata."""
    pair_address: str
    token_symbol: str
    token_mint: str
    quote_symbol: str
    dex: str
    liquidity_usd: float
    volume_5m: float
    volume_24h: float
    tx_count_5m: int
    fdv: float
    age_seconds: int
    score: int
    link: str
    price_usd: float
    price_change_5m: float


class DexScreenerSniper:
    """
    2026 Best-Practice DEXScreener Sniper
    
    Features:
    - Polls every 10s (respects ~300 req/min limit)
    - Client-side filtering (liquidity, FDV, age)
    - 0-100 scoring algorithm
    - Dry-run mode for testing
    - Async threading support
    - Birdeye integration ready
    """
    
    API_URL = "https://api.dexscreener.com/latest/dex/pairs/solana"
    
    def __init__(
        self,
        min_liquidity: float = 8000,
        max_fdv: float = 800000,
        min_score: int = 75,
        max_age_seconds: int = 300,
        dry_run: bool = True,
        poll_interval: int = 10
    ):
        """
        Initialize DEXScreener Sniper.
        
        Args:
            min_liquidity: Minimum liquidity in USD (default $8k)
            max_fdv: Maximum fully diluted valuation (default $800k)
            min_score: Minimum opportunity score to trigger (0-100)
            max_age_seconds: Maximum pool age to consider (default 5 min)
            dry_run: If True, only log opportunities without executing
            poll_interval: Seconds between API polls (default 10s)
        """
        self.min_liquidity = min_liquidity
        self.max_fdv = max_fdv
        self.min_score = min_score
        self.max_age_seconds = max_age_seconds
        self.dry_run = dry_run
        self.poll_interval = poll_interval
        
        self.seen_pairs = set()  # Avoid duplicates
        self.running = False
        self.callback: Optional[Callable] = None
        self.stats = {
            "polls": 0,
            "opportunities_found": 0,
            "executed": 0,
            "started_at": None
        }
        
        print(f"🔫 [DEXScreenerSniper] Initialized")
        print(f"   Min Liquidity: ${min_liquidity:,.0f}")
        print(f"   Max FDV: ${max_fdv:,.0f}")
        print(f"   Min Score: {min_score}/100")
        print(f"   Max Age: {max_age_seconds}s")
        print(f"   Poll Interval: {poll_interval}s")
        print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    def score_pair(self, pair: Dict) -> int:
        """
        2026 best-practice scoring algorithm (0-100).
        
        Scoring breakdown:
        - Liquidity: 30 points (min threshold)
        - 5m Volume: 25 points (activity indicator)
        - Transaction count: 20 points (engagement)
        - Freshness: 15 points (newer = better for sniping)
        - FDV: 10 points (avoid bloated tokens)
        """
        try:
            liquidity = pair.get("liquidity", {}).get("usd", 0) or 0
            volume_5m = pair.get("volume", {}).get("m5", 0) or 0
            volume_24h = pair.get("volume", {}).get("h24", 0) or 0
            buys_5m = pair.get("txns", {}).get("m5", {}).get("buys", 0) or 0
            sells_5m = pair.get("txns", {}).get("m5", {}).get("sells", 0) or 0
            tx_count = buys_5m + sells_5m
            fdv = pair.get("fdv") or 999999999
            
            created_at = pair.get("pairCreatedAt", 0)
            age_minutes = (time.time() * 1000 - created_at) / 60000 if created_at else 999
            
            score = 0
            
            # Liquidity score (0-30)
            if liquidity >= self.min_liquidity:
                score += 30
            elif liquidity >= self.min_liquidity * 0.5:
                score += 15
            
            # Volume score (0-25) - 5m volume indicates immediate interest
            if volume_5m > 10000:
                score += 25
            elif volume_5m > 5000:
                score += 20
            elif volume_5m > 1000:
                score += 10
            
            # Transaction count (0-20) - shows real activity
            if tx_count > 100:
                score += 20
            elif tx_count > 50:
                score += 15
            elif tx_count > 20:
                score += 10
            
            # Freshness (0-15) - newer pools have higher upside potential
            if age_minutes < 1:
                score += 15
            elif age_minutes < 3:
                score += 12
            elif age_minutes < 5:
                score += 8
            
            # FDV score (0-10) - avoid overvalued tokens
            if fdv <= self.max_fdv:
                score += 10
            elif fdv <= self.max_fdv * 2:
                score += 5
            
            # Bonus: Price momentum (up to 10 bonus points)
            price_change_5m = pair.get("priceChange", {}).get("m5", 0) or 0
            if 0 < price_change_5m < 50:  # Rising but not pumped
                score += 5
            
            return min(100, score)
        except Exception as e:
            print(f"[DEXScreener] Scoring error: {e}")
            return 0
    
    def fetch_new_pools(self) -> List[SniperOpportunity]:
        """
        Fetch and filter new pools from DEXScreener.
        Returns list of opportunities meeting criteria.
        """
        try:
            response = requests.get(self.API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            new_opps = []
            now = time.time() * 1000
            
            for pair in data.get("pairs", []):
                pair_addr = pair.get("pairAddress")
                if not pair_addr:
                    continue
                
                # Skip already seen
                if pair_addr in self.seen_pairs:
                    continue
                
                # Check age (< max_age_seconds)
                created_at = pair.get("pairCreatedAt")
                if not created_at:
                    continue
                age_ms = now - created_at
                if age_ms > self.max_age_seconds * 1000:
                    continue
                
                # Score the pair
                score = self.score_pair(pair)
                if score < self.min_score:
                    continue
                
                # Extract token info (prefer non-SOL as base for sniping)
                base = pair.get("baseToken", {})
                quote = pair.get("quoteToken", {})
                
                if base.get("symbol") == "SOL":
                    token_symbol = quote.get("symbol", "UNKNOWN")
                    token_mint = quote.get("address", "")
                    quote_symbol = "SOL"
                else:
                    token_symbol = base.get("symbol", "UNKNOWN")
                    token_mint = base.get("address", "")
                    quote_symbol = quote.get("symbol", "SOL")
                
                opp = SniperOpportunity(
                    pair_address=pair_addr,
                    token_symbol=token_symbol,
                    token_mint=token_mint,
                    quote_symbol=quote_symbol,
                    dex=pair.get("dexId", "unknown"),
                    liquidity_usd=pair.get("liquidity", {}).get("usd", 0) or 0,
                    volume_5m=pair.get("volume", {}).get("m5", 0) or 0,
                    volume_24h=pair.get("volume", {}).get("h24", 0) or 0,
                    tx_count_5m=(pair.get("txns", {}).get("m5", {}).get("buys", 0) or 0) + 
                               (pair.get("txns", {}).get("m5", {}).get("sells", 0) or 0),
                    fdv=pair.get("fdv") or 999999999,
                    age_seconds=int(age_ms / 1000),
                    score=score,
                    link=f"https://dexscreener.com/solana/{pair_addr}",
                    price_usd=float(pair.get("priceUsd", 0) or 0),
                    price_change_5m=pair.get("priceChange", {}).get("m5", 0) or 0
                )
                
                new_opps.append(opp)
                self.seen_pairs.add(pair_addr)
            
            # Sort by score descending
            new_opps.sort(key=lambda x: x.score, reverse=True)
            self.stats["polls"] += 1
            self.stats["opportunities_found"] += len(new_opps)
            
            return new_opps
            
        except requests.exceptions.Timeout:
            print("[DEXScreener] API timeout")
            return []
        except requests.exceptions.RequestException as e:
            print(f"[DEXScreener] API error: {e}")
            return []
        except Exception as e:
            print(f"[DEXScreener] Unexpected error: {e}")
            return []
    
    def start_monitoring(self, callback: Optional[Callable[[SniperOpportunity], None]] = None):
        """
        Start continuous monitoring in current thread.
        
        Args:
            callback: Function called for each opportunity found
        """
        self.running = True
        self.callback = callback
        self.stats["started_at"] = datetime.now(timezone.utc).isoformat()
        
        print(f"\n{'='*60}")
        print("🔫 DEXScreener Sniper STARTED")
        print(f"{'='*60}")
        print(f"Scanning for new Solana pools every {self.poll_interval}s...")
        print(f"Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                opps = self.fetch_new_pools()
                
                for opp in opps:
                    self._log_opportunity(opp)
                    
                    if callback and not self.dry_run:
                        try:
                            callback(opp)
                            self.stats["executed"] += 1
                        except Exception as e:
                            print(f"[DEXScreener] Callback error: {e}")
                
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n[DEXScreener] Stopping...")
        finally:
            self.running = False
            self.print_stats()
    
    def start_monitoring_threaded(self, callback: Optional[Callable[[SniperOpportunity], None]] = None) -> Thread:
        """
        Start monitoring in a background thread.
        
        Args:
            callback: Function called for each opportunity found
            
        Returns:
            Thread object (daemon)
        """
        self.callback = callback
        thread = Thread(target=self.start_monitoring, args=(callback,), daemon=True)
        thread.start()
        return thread
    
    def _log_opportunity(self, opp: SniperOpportunity):
        """Log opportunity details."""
        print(f"\n🚨 SNIPE CANDIDATE: {opp.token_symbol}/{opp.quote_symbol}")
        print(f"   Score: {opp.score}/100 | Age: {opp.age_seconds}s")
        print(f"   Liquidity: ${opp.liquidity_usd:,.0f} | FDV: ${opp.fdv:,.0f}")
        print(f"   5m Volume: ${opp.volume_5m:,.0f} | Txns: {opp.tx_count_5m}")
        print(f"   Price: ${opp.price_usd:.8f} ({opp.price_change_5m:+.1f}%)")
        print(f"   DEX: {opp.dex}")
        print(f"   Link: {opp.link}")
        
        if self.dry_run:
            print(f"   ⚠️  DRY RUN - No trade executed")
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        print("[DEXScreener] Sniper stopped")
    
    def print_stats(self):
        """Print run statistics."""
        print(f"\n{'='*60}")
        print("DEXScreener Sniper Stats")
        print(f"{'='*60}")
        print(f"Polls: {self.stats['polls']}")
        print(f"Opportunities: {self.stats['opportunities_found']}")
        print(f"Executed: {self.stats['executed']}")
        print(f"Started: {self.stats['started_at']}")
        print(f"Pairs tracked: {len(self.seen_pairs)}")
        print(f"{'='*60}\n")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stats as dictionary."""
        return {
            **self.stats,
            "running": self.running,
            "dry_run": self.dry_run,
            "seen_pairs_count": len(self.seen_pairs),
            "config": {
                "min_liquidity": self.min_liquidity,
                "max_fdv": self.max_fdv,
                "min_score": self.min_score,
                "poll_interval": self.poll_interval
            }
        }


# Integration helper for trading_bot.py
def create_sniper_integration(
    execution_layer,
    alerts_module=None,
    birdeye_connector=None,
    min_liquidity: float = 8000,
    min_score: int = 78,
    dry_run: bool = True
) -> DexScreenerSniper:
    """
    Create and configure sniper with trade execution callback.
    
    Args:
        execution_layer: ExecutionLayer instance for placing trades
        alerts_module: Optional alerts module for notifications
        birdeye_connector: Optional Birdeye connector for holder checks
        min_liquidity: Minimum liquidity threshold
        min_score: Minimum opportunity score
        dry_run: Start in dry-run mode
        
    Returns:
        Configured DexScreenerSniper instance
    """
    
    def execute_snipe(opp: SniperOpportunity):
        """Callback function for sniper opportunities."""
        print(f"\n🎯 EXECUTING SNIPE: {opp.token_symbol}")
        
        # Optional: Birdeye holder check
        if birdeye_connector and hasattr(birdeye_connector, 'get_token_info'):
            try:
                token_info = birdeye_connector.get_token_info(opp.token_mint)
                holders = token_info.get('holder_count', 0)
                if holders < 100:
                    print(f"   ⚠️  Low holders ({holders}) - skipping")
                    return
                print(f"   ✅ Holder check passed: {holders} holders")
            except Exception as e:
                print(f"   ⚠️  Holder check failed: {e}")
        
        # Calculate position size (max 10% of small balance)
        amount_usdt = min(5.0, 50.0 * 0.1)  # 5 USDT or 10% of $50
        
        print(f"   Position: ${amount_usdt:.2f} USDT")
        
        if dry_run:
            print(f"   ⚠️  DRY RUN - Would buy {opp.token_symbol}")
            return
        
        # Execute via Jupiter (requires solana_dex_full)
        try:
            from solana_dex_full import SolanaDEXFull, TOKENS
            
            dex = SolanaDEXFull()
            
            # Get Jupiter quote
            quote = dex.get_quote(
                TOKENS['USDT'],  # Input: USDT
                opp.token_mint,   # Output: target token
                int(amount_usdt * 1_000_000),  # Amount in micro-USDT
                slippage=100  # 1% slippage for fast execution
            )
            
            if not quote:
                print("   ❌ No Jupiter quote available")
                return
            
            # Execute swap
            sig = dex.execute_swap(quote, priority_fee=20000)
            
            if sig:
                msg = f"✅ SNIPED {opp.token_symbol} | Score {opp.score} | https://solscan.io/tx/{sig}"
                print(f"   {msg}")
                
                if alerts_module:
                    alerts_module.send(msg)
                    
                # Log to database if available
                if hasattr(execution_layer, 'log_snipe'):
                    execution_layer.log_snipe({
                        'token': opp.token_symbol,
                        'mint': opp.token_mint,
                        'amount': amount_usdt,
                        'score': opp.score,
                        'signature': sig,
                        'pair_link': opp.link
                    })
            else:
                print("   ❌ Swap failed")
                
        except Exception as e:
            print(f"   ❌ Snipe execution error: {e}")
    
    sniper = DexScreenerSniper(
        min_liquidity=min_liquidity,
        min_score=min_score,
        dry_run=dry_run,
        poll_interval=10
    )
    
    return sniper, execute_snipe


# Demo / Test
if __name__ == "__main__":
    print("=" * 60)
    print("DEXScreener Sniper - Test Mode")
    print("=" * 60)
    
    # Test 1: Create sniper in dry-run mode
    print("\n[Test 1] Initialize Sniper (Dry Run)")
    print("-" * 40)
    
    sniper = DexScreenerSniper(
        min_liquidity=8000,
        max_fdv=800000,
        min_score=75,
        dry_run=True
    )
    
    # Test 2: Single fetch
    print("\n[Test 2] Fetch New Pools")
    print("-" * 40)
    
    opps = sniper.fetch_new_pools()
    print(f"Found {len(opps)} opportunities meeting criteria")
    
    if opps:
        for opp in opps[:3]:
            print(f"\n  {opp.token_symbol} - Score: {opp.score}")
            print(f"  Liquidity: ${opp.liquidity_usd:,.0f}")
            print(f"  Age: {opp.age_seconds}s")
    
    # Test 3: Monitoring (10 seconds)
    print("\n[Test 3] 10-Second Monitor Test")
    print("-" * 40)
    print("Starting 10s test... (Ctrl+C to skip)")
    
    try:
        sniper.poll_interval = 5  # Faster for test
        sniper.start_monitoring(callback=lambda opp: print(f"Callback: {opp.token_symbol}"))
    except KeyboardInterrupt:
        pass
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("\nTo use in your bot:")
    print("  from dexscreener_connector import DexScreenerSniper")
    print("  sniper = DexScreenerSniper(dry_run=False)")
    print("  sniper.start_monitoring_threaded(callback=your_function)")
