#!/usr/bin/env python3
"""
Scrapers Module for Trading Bot
===============================

Provides token discovery from multiple sources:
- PinkSale: Presale launchpad (BSC, ETH, Polygon, etc.)
- Pump.fun: New Solana token launches
- DEXScreener: Multi-chain DEX price data
- Birdeye: Solana token analytics (optional)
"""

# PinkSale scraper
from .pinksale import (
    PinkSaleScraper,
    TokenCandidate as PinkSaleToken,
    get_pinksale_scraper,
)

try:
    # PumpFun scraper (may not be available in all installations)
    from .pumpfun import (
        PumpFunScraper,
        PumpFunConfig,
        TokenCandidate as PumpFunToken,
        get_scraper as get_pumpfun_scraper,
        discover_new_tokens as discover_pumpfun_tokens,
        get_high_priority_tokens as get_pumpfun_migrating,
    )
    PUMPFUN_AVAILABLE = True
except ImportError:
    PUMPFUN_AVAILABLE = False

__all__ = [
    # PinkSale
    'PinkSaleScraper',
    'PinkSaleToken',
    'get_pinksale_scraper',
]

if PUMPFUN_AVAILABLE:
    __all__.extend([
        'PumpFunScraper',
        'PumpFunConfig',
        'PumpFunToken',
        'get_pumpfun_scraper',
        'discover_pumpfun_tokens',
        'get_pumpfun_migrating',
    ])
