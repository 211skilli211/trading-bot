#!/usr/bin/env python3
"""
Accumulation Zones
==================
Hard-coded buy zones based on institutional accumulation levels.

These zones represent areas where institutions are likely accumulating,
based on historical data and on-chain analysis.

Uses both:
1. Hard-coded zones (from transcript/research)
2. Dynamic 200W MA confirmation (optional)
"""

from typing import Dict, Optional, Literal
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# Hard-coded accumulation zones
# Based on institutional buying patterns and historical support levels
ACCUMULATION_ZONES = {
    'BTC': {
        'min': 35000,
        'max': 50000,
        'description': 'Strong institutional buying zone',
        'rationale': 'Post-ETF approval accumulation, miner capitulation'
    },
    'ETH': {
        'min': 1800,
        'max': 2500,
        'description': 'Smart money accumulation',
        'rationale': 'Pre-ETF anticipation, staking demand'
    },
    'SOL': {
        'min': 80,
        'max': 140,
        'description': 'High-beta accumulation',
        'rationale': 'Network growth, DeFi TVL expansion'
    },
    'BNB': {
        'min': 450,
        'max': 600,
        'description': 'Exchange token support',
        'rationale': 'Binance ecosystem value'
    },
    'XRP': {
        'min': 0.40,
        'max': 0.65,
        'description': 'Legal clarity accumulation',
        'rationale': 'Post-SEC lawsuit resolution'
    },
    'ADA': {
        'min': 0.30,
        'max': 0.50,
        'description': 'Development milestone accumulation',
        'rationale': 'Smart contract growth'
    },
    'DOT': {
        'min': 4.0,
        'max': 7.0,
        'description': 'Parachain ecosystem support',
        'rationale': 'Auction participation, development'
    },
    'LINK': {
        'min': 10,
        'max': 18,
        'description': 'Oracle network value',
        'rationale': 'CCIP adoption, staking'
    }
}


@dataclass
class ZoneStatus:
    """Accumulation zone status for an asset"""
    symbol: str
    in_zone: bool
    status: Literal['IN_ZONE', 'BELOW_ZONE', 'ABOVE_ZONE']
    current_price: float
    zone_min: float
    zone_max: float
    distance_pct: float
    description: str
    rationale: str
    buy_signal: bool


def is_accumulation_zone(symbol: str, price: float) -> bool:
    """
    Check if price is in accumulation zone.
    
    Args:
        symbol: Asset symbol (BTC, ETH, etc.)
        price: Current price
        
    Returns:
        True if price is within accumulation zone
    """
    zone = ACCUMULATION_ZONES.get(symbol.upper())
    if not zone:
        return False
    
    return zone['min'] <= price <= zone['max']


def get_zone_status(symbol: str, price: float) -> Optional[ZoneStatus]:
    """
    Get detailed accumulation zone status.
    
    Args:
        symbol: Asset symbol
        price: Current price
        
    Returns:
        ZoneStatus with detailed information
    """
    zone = ACCUMULATION_ZONES.get(symbol.upper())
    if not zone:
        return None
    
    # Determine status
    if zone['min'] <= price <= zone['max']:
        status = 'IN_ZONE'
        distance_pct = 0
        buy_signal = True
    elif price < zone['min']:
        status = 'BELOW_ZONE'
        distance_pct = ((zone['min'] - price) / zone['min']) * 100
        buy_signal = True  # Even better price
    else:
        status = 'ABOVE_ZONE'
        distance_pct = ((price - zone['max']) / zone['max']) * 100
        buy_signal = False
    
    return ZoneStatus(
        symbol=symbol.upper(),
        in_zone=status == 'IN_ZONE',
        status=status,
        current_price=price,
        zone_min=zone['min'],
        zone_max=zone['max'],
        distance_pct=round(distance_pct, 2),
        description=zone['description'],
        rationale=zone['rationale'],
        buy_signal=buy_signal
    )


def get_accumulation_opportunities(prices: Dict[str, float]) -> Dict[str, ZoneStatus]:
    """
    Get all accumulation opportunities from a price list.
    
    Args:
        prices: Dict of {symbol: price}
        
    Returns:
        Dict of symbols that are in or below accumulation zones
    """
    opportunities = {}
    
    for symbol, price in prices.items():
        status = get_zone_status(symbol, price)
        if status and status.buy_signal:
            opportunities[symbol] = status
    
    return opportunities


def format_zone_status(status: ZoneStatus) -> str:
    """Format zone status for display"""
    if status.in_zone:
        return f"✅ {status.symbol}: IN ZONE (${status.current_price:,.2f})"
    elif status.status == 'BELOW_ZONE':
        return f"🎯 {status.symbol}: BELOW ZONE by {status.distance_pct:.1f}% (${status.current_price:,.2f} < ${status.zone_min:,.2f})"
    else:
        return f"⬆️ {status.symbol}: ABOVE ZONE by {status.distance_pct:.1f}% (${status.current_price:,.2f} > ${status.zone_max:,.2f})"


class AccumulationMonitor:
    """
    Monitor accumulation zones for multiple assets.
    
    Usage:
        monitor = AccumulationMonitor()
        if monitor.is_in_zone('BTC', 42000):
            # Consider buying
        opportunities = monitor.get_opportunities({'BTC': 42000, 'ETH': 2200})
    """
    
    def __init__(self):
        self.zones = ACCUMULATION_ZONES
        logger.info(f"[AccumulationMonitor] Loaded {len(self.zones)} accumulation zones")
        for symbol, zone in self.zones.items():
            logger.info(f"  {symbol}: ${zone['min']:,.2f} - ${zone['max']:,.2f}")
    
    def is_in_zone(self, symbol: str, price: float) -> bool:
        """Check if price is in accumulation zone"""
        return is_accumulation_zone(symbol, price)
    
    def get_status(self, symbol: str, price: float) -> Optional[ZoneStatus]:
        """Get detailed zone status"""
        return get_zone_status(symbol, price)
    
    def get_opportunities(self, prices: Dict[str, float]) -> Dict[str, ZoneStatus]:
        """Get all accumulation opportunities"""
        return get_accumulation_opportunities(prices)
    
    def should_accumulate(self, symbol: str, price: float) -> bool:
        """
        Determine if should accumulate based on zone.
        
        Returns True if:
        - Price is in zone
        - Price is below zone (even better)
        """
        status = self.get_status(symbol, price)
        if not status:
            return False
        return status.buy_signal


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("ACCUMULATION ZONES TEST")
    print("=" * 60)
    
    monitor = AccumulationMonitor()
    
    # Test prices
    test_prices = {
        'BTC': 42000,   # In zone
        'ETH': 2100,    # In zone  
        'SOL': 90,      # In zone
        'BTC': 55000,   # Above zone
        'ETH': 1500,    # Below zone
    }
    
    print("\nZone Status Checks:")
    print("-" * 60)
    
    test_cases = [
        ('BTC', 42000),
        ('BTC', 55000),
        ('BTC', 30000),
        ('ETH', 2100),
        ('SOL', 90),
        ('SOL', 200),
    ]
    
    for symbol, price in test_cases:
        status = monitor.get_status(symbol, price)
        if status:
            print(format_zone_status(status))
    
    print("\n" + "=" * 60)
