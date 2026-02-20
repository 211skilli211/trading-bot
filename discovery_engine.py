#!/usr/bin/env python3
"""
Discovery Engine - Arbitrage Opportunity Discovery

Integrates multiple data sources to find arbitrage opportunities:
1. PinkSale - Presale price discovery (presale vs DEX listing)
2. DEXScreener - DEX price data
3. CEX connectors - CEX price data

Usage:
    engine = DiscoveryEngine()
    
    # Full scan
    opportunities = engine.scan_all()
    
    # PinkSale only
    pinksale_opps = engine.scan_pinksale()
    
    # DEX-CEX only
    dex_cex_opps = engine.scan_dex_cex()
"""

import os
import sys
import json
import logging
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import scrapers
from scrapers.pinksale import PinkSaleScraper, TokenCandidate
from dexscreener_scanner import DEXScreenerScanner, ArbitrageOpportunity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class UnifiedOpportunity:
    """
    Unified arbitrage opportunity format.
    Combines data from all sources (PinkSale, DEXScreener, CEX).
    """
    # Identification
    opportunity_id: str
    source: str  # 'pinksale', 'dex_cex', 'dex_dex'
    symbol: str
    token_address: Optional[str] = None
    chain: str = 'unknown'
    
    # Price data
    buy_price: float = 0.0
    sell_price: float = 0.0
    spread_percent: float = 0.0
    
    # Venue info
    buy_venue: str = ""  # Exchange/DEX name
    sell_venue: str = ""  # Exchange/DEX name
    
    # Liquidity/volume
    buy_liquidity_usd: float = 0.0
    sell_liquidity_usd: float = 0.0
    volume_24h: float = 0.0
    
    # Profit estimation
    estimated_profit_percent: float = 0.0
    estimated_profit_usd: float = 0.0
    confidence_score: float = 0.0  # 0-100
    
    # Timing (for presale opportunities)
    presale_status: Optional[str] = None
    listing_time: Optional[datetime] = None
    time_sensitive: bool = False
    
    # Metadata
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate opportunity ID if not provided"""
        if not self.opportunity_id:
            hash_input = f"{self.source}:{self.symbol}:{self.buy_venue}:{self.sell_venue}:{self.discovered_at}"
            self.opportunity_id = hash(hash_input) % 10000000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'opportunity_id': self.opportunity_id,
            'source': self.source,
            'symbol': self.symbol,
            'token_address': self.token_address,
            'chain': self.chain,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'spread_percent': self.spread_percent,
            'buy_venue': self.buy_venue,
            'sell_venue': self.sell_venue,
            'buy_liquidity_usd': self.buy_liquidity_usd,
            'sell_liquidity_usd': self.sell_liquidity_usd,
            'volume_24h': self.volume_24h,
            'estimated_profit_percent': self.estimated_profit_percent,
            'estimated_profit_usd': self.estimated_profit_usd,
            'confidence_score': self.confidence_score,
            'presale_status': self.presale_status,
            'listing_time': self.listing_time.isoformat() if self.listing_time else None,
            'time_sensitive': self.time_sensitive,
            'discovered_at': self.discovered_at.isoformat(),
        }
    
    @property
    def is_pinksale_opportunity(self) -> bool:
        """Check if this is a PinkSale presale opportunity"""
        return self.source == 'pinksale'
    
    @property
    def profit_potential(self) -> str:
        """Get profit potential rating"""
        if self.estimated_profit_percent > 20:
            return "HIGH"
        elif self.estimated_profit_percent > 10:
            return "MEDIUM"
        elif self.estimated_profit_percent > 5:
            return "LOW"
        return "MINIMAL"


class DiscoveryEngine:
    """
    Main discovery engine that coordinates multiple scrapers and scanners.
    
    Features:
    - PinkSale presale monitoring
    - DEX-CEX price comparison
    - DEX-DEX arbitrage scanning
    - Opportunity scoring and ranking
    - Real-time alerts for time-sensitive opportunities
    
    Example:
        engine = DiscoveryEngine()
        
        # Scan all sources
        opportunities = engine.scan_all(min_spread_percent=5.0)
        
        # Get PinkSale watchlist
        watchlist = engine.get_pinksale_watchlist()
        
        # Subscribe to alerts
        engine.on_opportunity(lambda opp: print(f"New opportunity: {opp.symbol}"))
    """
    
    # Configuration
    DEFAULT_MIN_SPREAD = 3.0  # Minimum spread % to report
    DEFAULT_MIN_LIQUIDITY = 3000  # Minimum USD liquidity
    SCAN_INTERVAL = 60  # Seconds between scans
    
    def __init__(self,
                 min_spread_percent: float = DEFAULT_MIN_SPREAD,
                 min_liquidity_usd: float = DEFAULT_MIN_LIQUIDITY,
                 enable_pinksale: bool = True,
                 enable_dexscreener: bool = True):
        """
        Initialize the discovery engine.
        
        Args:
            min_spread_percent: Minimum price spread to consider an opportunity
            min_liquidity_usd: Minimum liquidity requirement
            enable_pinksale: Enable PinkSale scraper
            enable_dexscreener: Enable DEXScreener scanner
        """
        self.min_spread_percent = min_spread_percent
        self.min_liquidity_usd = min_liquidity_usd
        
        # Initialize scrapers
        self.pinksale_scraper: Optional[PinkSaleScraper] = None
        self.dexscreener_scanner: Optional[DEXScreenerScanner] = None
        
        if enable_pinksale:
            self.pinksale_scraper = PinkSaleScraper(rate_limit_delay=2.0)
            logger.info("[DiscoveryEngine] PinkSale scraper enabled")
        
        if enable_dexscreener:
            self.dexscreener_scanner = DEXScreenerScanner()
            logger.info("[DiscoveryEngine] DEXScreener scanner enabled")
        
        # Callbacks for real-time alerts
        self._opportunity_callbacks: List[Callable[[UnifiedOpportunity], None]] = []
        self._watchlist: List[UnifiedOpportunity] = []
        
        # Cache
        self._last_scan_results: List[UnifiedOpportunity] = []
        self._scan_count = 0
        
        logger.info("[DiscoveryEngine] Initialized")
    
    def on_opportunity(self, callback: Callable[[UnifiedOpportunity], None]):
        """
        Register a callback for new opportunities.
        
        Args:
            callback: Function to call when new opportunity is found
        """
        self._opportunity_callbacks.append(callback)
        logger.info(f"[DiscoveryEngine] Registered opportunity callback (total: {len(self._opportunity_callbacks)})")
    
    def _notify_opportunities(self, opportunities: List[UnifiedOpportunity]):
        """Notify all registered callbacks of new opportunities"""
        for opp in opportunities:
            for callback in self._opportunity_callbacks:
                try:
                    callback(opp)
                except Exception as e:
                    logger.error(f"[DiscoveryEngine] Callback error: {e}")
    
    def _token_candidate_to_opportunity(self, candidate: TokenCandidate) -> Optional[UnifiedOpportunity]:
        """
        Convert a PinkSale TokenCandidate to UnifiedOpportunity.
        
        Args:
            candidate: TokenCandidate from PinkSale scraper
            
        Returns:
            UnifiedOpportunity or None if not valid
        """
        if not candidate.token_address:
            return None
        
        # Calculate estimated profit (after estimated fees)
        estimated_fees = 1.0  # Estimate 1% total fees
        est_profit_pct = max(0, candidate.price_spread_percent - estimated_fees)
        
        # Calculate confidence score
        confidence = min(100, candidate.arbitrage_score)
        
        # Determine if time-sensitive
        time_sensitive = (
            candidate.presale_status.upper() == 'ACTIVE' and
            candidate.end_time is not None and
            (candidate.end_time - datetime.now(timezone.utc)).total_seconds() < 3600
        )
        
        return UnifiedOpportunity(
            opportunity_id=f"PS_{candidate.token_address[:8]}_{int(datetime.now(timezone.utc).timestamp())}",
            source='pinksale',
            symbol=candidate.symbol,
            token_address=candidate.token_address,
            chain=candidate.chain,
            buy_price=candidate.presale_price,
            sell_price=candidate.dex_price,
            spread_percent=candidate.price_spread_percent,
            buy_venue='PinkSale Presale',
            sell_venue='DEX Listing',
            buy_liquidity_usd=candidate.total_raised_usd,
            sell_liquidity_usd=candidate.dex_liquidity_usd,
            volume_24h=candidate.dex_volume_24h,
            estimated_profit_percent=est_profit_pct,
            estimated_profit_usd=candidate.total_raised_usd * (est_profit_pct / 100),
            confidence_score=confidence,
            presale_status=candidate.presale_status,
            listing_time=candidate.listing_time or candidate.end_time,
            time_sensitive=time_sensitive,
            raw_data=candidate.to_dict(),
        )
    
    def scan_pinksale(self, 
                      chains: Optional[List[str]] = None,
                      include_ended: bool = True) -> List[UnifiedOpportunity]:
        """
        Scan PinkSale for arbitrage opportunities.
        
        Args:
            chains: List of chains to scan (default: ['bsc', 'ethereum'])
            include_ended: Include finished presales that may list soon
            
        Returns:
            List of UnifiedOpportunity objects
        """
        if not self.pinksale_scraper:
            logger.warning("[DiscoveryEngine] PinkSale scraper not enabled")
            return []
        
        opportunities = []
        chains = chains or ['bsc', 'ethereum']
        
        logger.info(f"[DiscoveryEngine] Scanning PinkSale on chains: {chains}")
        
        for chain in chains:
            try:
                # Find opportunities on this chain
                candidates = self.pinksale_scraper.find_arbitrage_opportunities(
                    min_spread_percent=self.min_spread_percent,
                    min_liquidity_usd=self.min_liquidity_usd,
                    chain=chain
                )
                
                # Convert to unified format
                for candidate in candidates:
                    opp = self._token_candidate_to_opportunity(candidate)
                    if opp:
                        opportunities.append(opp)
                
                # Also get ended presales if requested
                if include_ended:
                    ended = self.pinksale_scraper.fetch_finished_presales(chain)
                    for candidate in ended:
                        if candidate.total_raised_usd >= self.min_liquidity_usd:
                            # These haven't listed yet - potential opportunity
                            opp = self._token_candidate_to_opportunity(candidate)
                            if opp:
                                opp.estimated_profit_percent = 0  # Unknown until listed
                                opp.confidence_score = 50  # Moderate confidence
                                opportunities.append(opp)
                
            except Exception as e:
                logger.error(f"[DiscoveryEngine] PinkSale scan error on {chain}: {e}")
        
        # Sort by confidence score
        opportunities.sort(key=lambda x: x.confidence_score, reverse=True)
        
        logger.info(f"[DiscoveryEngine] PinkSale scan complete: {len(opportunities)} opportunities")
        return opportunities
    
    def scan_dex_cex(self, symbols: Optional[List[str]] = None) -> List[UnifiedOpportunity]:
        """
        Scan for DEX-CEX arbitrage opportunities.
        
        Args:
            symbols: List of symbols to scan (default: major tokens)
            
        Returns:
            List of UnifiedOpportunity objects
        """
        if not self.dexscreener_scanner:
            logger.warning("[DiscoveryEngine] DEXScreener scanner not enabled")
            return []
        
        opportunities = []
        symbols = symbols or ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX']
        
        logger.info(f"[DiscoveryEngine] Scanning DEX-CEX for: {symbols}")
        
        try:
            # Get mock CEX prices (in production, fetch from real CEX APIs)
            # This is a placeholder - real implementation would use ccxt
            mock_cex_prices = self._fetch_cex_prices(symbols)
            
            # Scan with DEXScreener
            dex_opportunities = self.dexscreener_scanner.scan_arbitrage(symbols, mock_cex_prices)
            
            # Convert to unified format
            for dex_opp in dex_opportunities:
                if dex_opp.spread_percent >= self.min_spread_percent:
                    opp = UnifiedOpportunity(
                        opportunity_id=f"DC_{dex_opp.symbol}_{int(datetime.now(timezone.utc).timestamp())}",
                        source='dex_cex',
                        symbol=dex_opp.symbol,
                        buy_price=dex_opp.buy_price,
                        sell_price=dex_opp.sell_price,
                        spread_percent=dex_opp.spread_percent,
                        buy_venue=dex_opp.buy_exchange,
                        sell_venue=dex_opp.sell_exchange,
                        estimated_profit_percent=dex_opp.profit_potential,
                        confidence_score=80 if dex_opp.confidence == 'HIGH' else 50 if dex_opp.confidence == 'MEDIUM' else 30,
                        raw_data=dex_opp.to_dict(),
                    )
                    opportunities.append(opp)
            
        except Exception as e:
            logger.error(f"[DiscoveryEngine] DEX-CEX scan error: {e}")
        
        logger.info(f"[DiscoveryEngine] DEX-CEX scan complete: {len(opportunities)} opportunities")
        return opportunities
    
    def scan_solana(self) -> List[UnifiedOpportunity]:
        """
        Scan for Solana DEX-DEX arbitrage opportunities.
        
        Returns:
            List of UnifiedOpportunity objects
        """
        if not self.dexscreener_scanner:
            logger.warning("[DiscoveryEngine] DEXScreener scanner not enabled")
            return []
        
        opportunities = []
        
        logger.info("[DiscoveryEngine] Scanning Solana DEX-DEX...")
        
        try:
            sol_opps = self.dexscreener_scanner.get_solana_opportunities()
            
            for sol_opp in sol_opps:
                if sol_opp.spread_percent >= self.min_spread_percent:
                    opp = UnifiedOpportunity(
                        opportunity_id=f"SOL_{sol_opp.symbol}_{int(datetime.now(timezone.utc).timestamp())}",
                        source='dex_dex',
                        symbol=sol_opp.symbol,
                        chain='solana',
                        buy_price=sol_opp.buy_price,
                        sell_price=sol_opp.sell_price,
                        spread_percent=sol_opp.spread_percent,
                        buy_venue=sol_opp.buy_exchange,
                        sell_venue=sol_opp.sell_exchange,
                        estimated_profit_percent=sol_opp.profit_potential,
                        confidence_score=60,  # DEX-DEX is moderate confidence
                        raw_data=sol_opp.to_dict(),
                    )
                    opportunities.append(opp)
            
        except Exception as e:
            logger.error(f"[DiscoveryEngine] Solana scan error: {e}")
        
        logger.info(f"[DiscoveryEngine] Solana scan complete: {len(opportunities)} opportunities")
        return opportunities
    
    def scan_all(self, 
                 include_pinksale: bool = True,
                 include_dex_cex: bool = True,
                 include_solana: bool = True) -> List[UnifiedOpportunity]:
        """
        Run full scan across all enabled sources.
        
        Args:
            include_pinksale: Include PinkSale scanning
            include_dex_cex: Include DEX-CEX scanning
            include_solana: Include Solana DEX-DEX scanning
            
        Returns:
            Combined list of all opportunities sorted by profit potential
        """
        all_opportunities = []
        
        logger.info("=" * 80)
        logger.info("[DiscoveryEngine] Starting full scan...")
        logger.info("=" * 80)
        
        # 1. Scan PinkSale
        if include_pinksale and self.pinksale_scraper:
            pinksale_opps = self.scan_pinksale()
            all_opportunities.extend(pinksale_opps)
        
        # 2. Scan DEX-CEX
        if include_dex_cex and self.dexscreener_scanner:
            dex_cex_opps = self.scan_dex_cex()
            all_opportunities.extend(dex_cex_opps)
        
        # 3. Scan Solana
        if include_solana and self.dexscreener_scanner:
            solana_opps = self.scan_solana()
            all_opportunities.extend(solana_opps)
        
        # Sort by estimated profit
        all_opportunities.sort(key=lambda x: x.estimated_profit_percent, reverse=True)
        
        # Deduplicate by symbol+venue combination
        seen = set()
        unique_opportunities = []
        for opp in all_opportunities:
            key = f"{opp.symbol}:{opp.buy_venue}:{opp.sell_venue}"
            if key not in seen:
                seen.add(key)
                unique_opportunities.append(opp)
        
        self._last_scan_results = unique_opportunities
        self._scan_count += 1
        
        # Notify callbacks
        self._notify_opportunities(unique_opportunities)
        
        # Log summary
        logger.info("=" * 80)
        logger.info(f"[DiscoveryEngine] Scan #{self._scan_count} complete: {len(unique_opportunities)} total opportunities")
        logger.info("=" * 80)
        
        return unique_opportunities
    
    def get_pinksale_watchlist(self, hours: float = 12.0) -> List[UnifiedOpportunity]:
        """
        Get watchlist of PinkSale tokens about to list.
        
        Args:
            hours: Hours to look ahead
            
        Returns:
            List of opportunities sorted by listing time
        """
        if not self.pinksale_scraper:
            return []
        
        watchlist = []
        candidates = self.pinksale_scraper.get_watchlist(hours_until_listing=hours)
        
        for candidate in candidates:
            opp = self._token_candidate_to_opportunity(candidate)
            if opp:
                watchlist.append(opp)
        
        return watchlist
    
    def get_best_opportunities(self, 
                               min_confidence: float = 50.0,
                               limit: int = 10) -> List[UnifiedOpportunity]:
        """
        Get the best opportunities from last scan.
        
        Args:
            min_confidence: Minimum confidence score (0-100)
            limit: Maximum number to return
            
        Returns:
            Filtered and sorted opportunities
        """
        filtered = [
            opp for opp in self._last_scan_results
            if opp.confidence_score >= min_confidence
        ]
        return filtered[:limit]
    
    def get_opportunities_by_source(self, source: str) -> List[UnifiedOpportunity]:
        """Get opportunities from a specific source"""
        return [opp for opp in self._last_scan_results if opp.source == source]
    
    def get_opportunities_by_chain(self, chain: str) -> List[UnifiedOpportunity]:
        """Get opportunities for a specific blockchain"""
        return [opp for opp in self._last_scan_results if opp.chain.lower() == chain.lower()]
    
    def print_report(self, opportunities: Optional[List[UnifiedOpportunity]] = None):
        """
        Print a formatted report of opportunities.
        
        Args:
            opportunities: List to print (default: last scan results)
        """
        opps = opportunities or self._last_scan_results
        
        print("\n" + "=" * 100)
        print("🎯 ARBITRAGE DISCOVERY REPORT")
        print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 100)
        
        if not opps:
            print("\n📭 No opportunities found matching criteria.")
            print("=" * 100)
            return
        
        # Group by source
        by_source = {}
        for opp in opps:
            by_source.setdefault(opp.source, []).append(opp)
        
        # Print by category
        for source, source_opps in by_source.items():
            print(f"\n📊 {source.upper().replace('_', '-')} OPPORTUNITIES ({len(source_opps)} found)")
            print("-" * 100)
            
            for i, opp in enumerate(source_opps[:10], 1):
                # Confidence indicator
                if opp.confidence_score >= 80:
                    conf_emoji = "🟢"
                elif opp.confidence_score >= 50:
                    conf_emoji = "🟡"
                else:
                    conf_emoji = "🔴"
                
                # Time indicator for presales
                time_indicator = ""
                if opp.time_sensitive:
                    time_indicator = "⏰ URGENT "
                elif opp.listing_time:
                    time_until = (opp.listing_time - datetime.now(timezone.utc)).total_seconds() / 3600
                    if 0 < time_until < 24:
                        time_indicator = f"🕐 {time_until:.1f}h "
                
                print(f"\n{i}. {conf_emoji} {time_indicator}{opp.symbol}")
                print(f"   Chain: {opp.chain.upper()}")
                print(f"   Buy:  {opp.buy_venue:<25} @ ${opp.buy_price:,.6f}")
                print(f"   Sell: {opp.sell_venue:<25} @ ${opp.sell_price:,.6f}")
                print(f"   Spread: {opp.spread_percent:+.2f}% | Est. Profit: {opp.estimated_profit_percent:.2f}%")
                print(f"   Confidence: {opp.confidence_score:.0f}/100 | Volume 24h: ${opp.volume_24h:,.0f}")
                
                if opp.presale_status:
                    print(f"   Status: {opp.presale_status}")
        
        print("\n" + "=" * 100)
        print(f"📈 Total: {len(opps)} opportunities | Best: {opps[0].symbol if opps else 'N/A'}")
        print("=" * 100)
    
    def save_report(self, filepath: str, opportunities: Optional[List[UnifiedOpportunity]] = None):
        """
        Save opportunities to JSON file.
        
        Args:
            filepath: Path to save JSON
            opportunities: List to save (default: last scan results)
        """
        opps = opportunities or self._last_scan_results
        
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'scan_count': self._scan_count,
            'config': {
                'min_spread_percent': self.min_spread_percent,
                'min_liquidity_usd': self.min_liquidity_usd,
            },
            'opportunities': [opp.to_dict() for opp in opps],
            'summary': {
                'total': len(opps),
                'by_source': {},
                'by_chain': {},
            }
        }
        
        # Calculate summary
        for opp in opps:
            report['summary']['by_source'][opp.source] = report['summary']['by_source'].get(opp.source, 0) + 1
            report['summary']['by_chain'][opp.chain] = report['summary']['by_chain'].get(opp.chain, 0) + 1
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"[DiscoveryEngine] Report saved to {filepath}")
    
    def _fetch_cex_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Fetch CEX prices for symbols.
        Placeholder - real implementation would use ccxt.
        
        Returns:
            Dict mapping symbol to exchange prices
        """
        # This is a placeholder - in production, use ccxt to fetch real prices
        # For now, return empty dict to let DEXScreener scanner work with available data
        return {}


# Singleton instance
_engine: Optional[DiscoveryEngine] = None


def get_discovery_engine() -> DiscoveryEngine:
    """Get singleton instance of DiscoveryEngine"""
    global _engine
    if _engine is None:
        _engine = DiscoveryEngine()
    return _engine


if __name__ == "__main__":
    # Test the discovery engine
    print("=" * 100)
    print("🚀 DISCOVERY ENGINE - TEST MODE")
    print("=" * 100)
    
    # Initialize
    engine = DiscoveryEngine(
        min_spread_percent=3.0,
        min_liquidity_usd=5000,
        enable_pinksale=True,
        enable_dexscreener=True,
    )
    
    # Register callback
    def on_opp(opp):
        print(f"\n🔔 NEW OPPORTUNITY: {opp.symbol} ({opp.spread_percent:+.2f}% spread)")
    
    engine.on_opportunity(on_opp)
    
    # Run scans
    print("\n[TEST 1] Scanning PinkSale...")
    pinksale_opps = engine.scan_pinksale(chains=['bsc'])
    print(f"Found {len(pinksale_opps)} PinkSale opportunities")
    
    print("\n[TEST 2] Scanning Solana...")
    solana_opps = engine.scan_solana()
    print(f"Found {len(solana_opps)} Solana opportunities")
    
    print("\n[TEST 3] Full scan...")
    all_opps = engine.scan_all()
    
    # Print report
    engine.print_report(all_opps)
    
    # Save report
    report_path = "discovery_report.json"
    engine.save_report(report_path, all_opps)
    print(f"\n📄 Report saved to: {report_path}")
    
    print("\n" + "=" * 100)
    print("✅ Discovery Engine tests completed")
    print("=" * 100)
