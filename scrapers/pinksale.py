#!/usr/bin/env python3
"""
PinkSale Finance Scraper for Arbitrage Discovery

Fetches active and finished presales from PinkSale to identify
arbitrage opportunities between presale prices and DEX listing prices.

PinkSale URLs:
- https://www.pinksale.finance/launchpads
- https://www.pinksale.finance/launchpad/ethereum (Ethereum chain)
- https://www.pinksale.finance/launchpad/bsc (BSC chain - primary)
- https://www.pinksale.finance/launchpad/polygon
- https://www.pinksale.finance/launchpad/arbitrum
- https://www.pinksale.finance/launchpad/base

Note: PinkSale uses JavaScript to render presale data dynamically.
For production use, consider using Selenium/Playwright for full JS rendering.
This implementation uses requests with fallback to API endpoints if available.
"""

import re
import time
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional, Callable, Any
from urllib.parse import urljoin, urlparse
import hashlib

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TokenCandidate:
    """
    Represents a token discovered from PinkSale presale.
    Used for arbitrage opportunity detection.
    """
    # Identification
    token_address: str
    symbol: str
    name: str
    chain: str  # bsc, ethereum, polygon, etc.
    
    # Presale Info
    presale_address: str = ""
    presale_price: float = 0.0  # Price per token in USD
    presale_status: str = ""  # ACTIVE, ENDED, UPCOMING, CANCELLED
    
    # Liquidity / Raise Info
    total_raised_usd: float = 0.0
    liquidity_percent: float = 0.0  # % of raised funds going to LP
    soft_cap: float = 0.0
    hard_cap: float = 0.0
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    listing_time: Optional[datetime] = None  # When token lists on DEX
    
    # DEX Info (for comparison)
    dex_price: float = 0.0  # Current price on DEX (if listed)
    dex_liquidity_usd: float = 0.0
    dex_volume_24h: float = 0.0
    
    # Calculated fields
    price_spread_percent: float = 0.0  # (dex_price - presale_price) / presale_price * 100
    arbitrage_score: float = 0.0  # Higher = better opportunity
    
    # Metadata
    source_url: str = ""
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate derived fields after initialization"""
        self._calculate_arbitrage_score()
    
    def _calculate_arbitrage_score(self):
        """
        Calculate an arbitrage opportunity score based on multiple factors:
        - Price spread (higher is better)
        - Liquidity (higher is better)
        - Time to listing (sooner is better for active presales)
        """
        score = 0.0
        
        # Price spread factor (primary)
        if self.price_spread_percent > 0:
            score += min(self.price_spread_percent * 10, 500)  # Cap at 500
        
        # Liquidity factor
        if self.total_raised_usd > 0:
            liquidity_score = min(self.total_raised_usd / 10000, 100)  # $100k = 100 points
            score += liquidity_score
        
        # Time urgency factor (for active presales ending soon)
        if self.end_time and self.presale_status.upper() == 'ACTIVE':
            time_remaining = (self.end_time - datetime.now(timezone.utc)).total_seconds()
            if 0 < time_remaining < 3600:  # Less than 1 hour
                score += 50  # Urgency bonus
        
        self.arbitrage_score = round(score, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'token_address': self.token_address,
            'symbol': self.symbol,
            'name': self.name,
            'chain': self.chain,
            'presale_address': self.presale_address,
            'presale_price': self.presale_price,
            'presale_status': self.presale_status,
            'total_raised_usd': self.total_raised_usd,
            'liquidity_percent': self.liquidity_percent,
            'soft_cap': self.soft_cap,
            'hard_cap': self.hard_cap,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'listing_time': self.listing_time.isoformat() if self.listing_time else None,
            'dex_price': self.dex_price,
            'dex_liquidity_usd': self.dex_liquidity_usd,
            'dex_volume_24h': self.dex_volume_24h,
            'price_spread_percent': self.price_spread_percent,
            'arbitrage_score': self.arbitrage_score,
            'source_url': self.source_url,
            'discovered_at': self.discovered_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
        }
    
    @property
    def is_listed(self) -> bool:
        """Check if token is already listed on DEX"""
        return self.dex_price > 0 and self.dex_liquidity_usd > 0
    
    @property
    def is_opportunity(self) -> bool:
        """Check if this represents a valid arbitrage opportunity"""
        return (
            self.price_spread_percent > 5.0  # Minimum 5% spread
            and self.total_raised_usd > 5000  # Minimum liquidity
            and self.presale_status.upper() in ['ACTIVE', 'ENDED', 'UPCOMING']
        )


class PinkSaleScraper:
    """
    Scraper for PinkSale Finance launchpad data.
    
    Fetches presale information for arbitrage discovery.
    Supports multiple chains: BSC (primary), Ethereum, Polygon, Arbitrum, Base.
    
    Usage:
        scraper = PinkSaleScraper()
        
        # Fetch all active presales on BSC
        candidates = scraper.fetch_active_presales(chain='bsc')
        
        # Fetch finished presales about to list
        ending_soon = scraper.fetch_ending_soon(hours=2)
        
        # Compare with DEX prices
        scraper.enrich_with_dex_prices(candidates)
    """
    
    # PinkSale base URLs
    BASE_URL = "https://www.pinksale.finance"
    LAUNCHPADS_URL = "https://www.pinksale.finance/launchpads/all"
    
    # Chain-specific URLs
    CHAIN_URLS = {
        'ethereum': "https://www.pinksale.finance/launchpads/ethereum",
        'bsc': "https://www.pinksale.finance/launchpads/bsc",
        'polygon': "https://www.pinksale.finance/launchpads/polygon",
        'arbitrum': "https://www.pinksale.finance/launchpads/arbitrum",
        'base': "https://www.pinksale.finance/launchpads/base",
        'avalanche': "https://www.pinksale.finance/launchpads/avalanche",
        'fantom': "https://www.pinksale.finance/launchpads/fantom",
    }
    
    # Alternative: Direct API endpoints (these may change)
    # PinkSale uses GraphQL or internal APIs that can be discovered via browser dev tools
    API_BASE = "https://api.pinksale.finance/api/v1"
    
    # GraphQL endpoint (may require authentication)
    GRAPHQL_URL = "https://www.pinksale.finance/api/graphql"
    
    # Rate limiting config
    REQUEST_DELAY = 2.0  # Seconds between requests
    MAX_RETRIES = 3
    RETRY_DELAY = 5.0
    
    # Supported chains
    SUPPORTED_CHAINS = ['bsc', 'ethereum', 'polygon', 'arbitrum', 'base', 'avalanche', 'fantom']
    
    def __init__(self, 
                 rate_limit_delay: float = 2.0,
                 max_retries: int = 3,
                 use_js_renderer: bool = False):
        """
        Initialize the PinkSale scraper.
        
        Args:
            rate_limit_delay: Seconds to wait between requests
            max_retries: Number of retries for failed requests
            use_js_renderer: Whether to use Selenium for JS rendering (slower but more reliable)
        """
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.use_js_renderer = use_js_renderer
        self.last_request_time = 0
        
        # Setup session with retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Cache for discovered tokens
        self._cache: Dict[str, TokenCandidate] = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info(f"[PinkSaleScraper] Initialized (rate_limit={rate_limit_delay}s, max_retries={max_retries})")
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"[PinkSaleScraper] Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _fetch_page(self, url: str, params: Optional[Dict] = None) -> Optional[str]:
        """
        Fetch a page with rate limiting and retries.
        
        Args:
            url: URL to fetch
            params: Optional query parameters
            
        Returns:
            HTML content or None if failed
        """
        self._rate_limit()
        
        try:
            logger.info(f"[PinkSaleScraper] Fetching: {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"[PinkSaleScraper] Error fetching {url}: {e}")
            return None
    
    def _extract_json_from_script(self, html: str, pattern: str) -> Optional[Dict]:
        """
        Extract JSON data embedded in script tags.
        PinkSale often embeds data in window.__INITIAL_STATE__ or similar.
        """
        try:
            # Look for common patterns
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.__DATA__\s*=\s*({.+?});',
                r'"presales":\s*(\[.+?\])',
                r'"launchpads":\s*(\[.+?\])',
            ]
            
            for p in patterns:
                match = re.search(p, html, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    return data
        except (json.JSONDecodeError, AttributeError) as e:
            logger.debug(f"[PinkSaleScraper] Could not extract JSON: {e}")
        
        return None
    
    def _parse_token_address(self, text: str) -> Optional[str]:
        """
        Extract Ethereum-style address from text.
        Matches 0x followed by 40 hex characters.
        """
        pattern = r'0x[a-fA-F0-9]{40}'
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    def _parse_amount(self, text: str) -> float:
        """
        Parse monetary amount from text.
        Handles formats like: $1,234.56, 1.5 ETH, 1000 USDT
        """
        if not text:
            return 0.0
        
        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[$,\s]', '', text.strip())
        
        # Extract number
        match = re.search(r'[\d,]+\.?\d*', cleaned)
        if match:
            try:
                return float(match.group(0).replace(',', ''))
            except ValueError:
                pass
        
        return 0.0
    
    def _parse_percentage(self, text: str) -> float:
        """Parse percentage value from text"""
        if not text:
            return 0.0
        
        match = re.search(r'(\d+\.?\d*)\s*%', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        return 0.0
    
    def _parse_datetime(self, text: str) -> Optional[datetime]:
        """
        Parse datetime from various formats.
        Handles ISO format, relative times, etc.
        """
        if not text:
            return None
        
        try:
            # Try ISO format
            return datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        try:
            # Try common formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%d/%m/%Y %H:%M:%S',
                '%m/%d/%Y %H:%M:%S',
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(text.strip(), fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        except Exception:
            pass
        
        return None
    
    def fetch_active_presales(self, chain: str = 'bsc', limit: int = 50) -> List[TokenCandidate]:
        """
        Fetch active presales from PinkSale.
        
        Note: PinkSale uses Cloudflare protection which may block simple requests.
        For production use, consider:
        1. Using a headless browser (Selenium/Playwright)
        2. Using a proxy service
        3. Using the GraphQL API with proper authentication
        
        Args:
            chain: Blockchain to fetch from (bsc, ethereum, polygon, etc.)
            limit: Maximum number of presales to fetch
            
        Returns:
            List of TokenCandidate objects
        """
        candidates = []
        
        if chain not in self.SUPPORTED_CHAINS:
            logger.warning(f"[PinkSaleScraper] Unsupported chain: {chain}")
            return candidates
        
        # Try GraphQL API first
        candidates = self._fetch_via_graphql(chain, status='ACTIVE', limit=limit)
        
        if candidates:
            logger.info(f"[PinkSaleScraper] Found {len(candidates)} presales via GraphQL")
            return candidates
        
        # Fallback to HTML scraping
        url = self.CHAIN_URLS.get(chain, self.LAUNCHPADS_URL)
        html = self._fetch_page(url)
        
        if not html:
            logger.warning(f"[PinkSaleScraper] Failed to fetch presales for {chain}")
            return candidates
        
        # Check for Cloudflare challenge
        if 'challenge-platform' in html or 'cf-browser-verification' in html:
            logger.warning("[PinkSaleScraper] Cloudflare challenge detected. "
                          "Consider using Selenium/Playwright for this site.")
            return candidates
        
        # Try to extract JSON data first
        data = self._extract_json_from_script(html, "")
        
        if data:
            # Parse from JSON structure
            candidates = self._parse_from_json(data, chain)
        else:
            # Fallback to HTML parsing
            candidates = self._parse_from_html(html, chain)
        
        # Filter to active presales only
        active = [c for c in candidates if c.presale_status.upper() == 'ACTIVE']
        
        logger.info(f"[PinkSaleScraper] Found {len(active)} active presales on {chain}")
        return active[:limit]
    
    def _fetch_via_graphql(self, chain: str, status: str = 'ACTIVE', limit: int = 50) -> List[TokenCandidate]:
        """
        Fetch presales via PinkSale's GraphQL API.
        This is often more reliable than HTML scraping.
        """
        candidates = []
        
        # GraphQL query for presales
        # Note: This query structure may need to be updated based on actual API
        query = {
            "operationName": "GetLaunchpads",
            "variables": {
                "chain": chain.upper(),
                "status": status,
                "limit": limit,
                "offset": 0
            },
            "query": """
                query GetLaunchpads($chain: String, $status: String, $limit: Int, $offset: Int) {
                    launchpads(chain: $chain, status: $status, limit: $limit, offset: $offset) {
                        id
                        tokenAddress
                        tokenName
                        tokenSymbol
                        presaleAddress
                        status
                        totalRaised
                        softCap
                        hardCap
                        liquidityPercent
                        startTime
                        endTime
                        chain
                    }
                }
            """
        }
        
        try:
            self._rate_limit()
            response = self.session.post(
                self.GRAPHQL_URL,
                json=query,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                launchpads = data.get('data', {}).get('launchpads', [])
                
                for item in launchpads:
                    candidate = self._item_to_candidate(item, chain)
                    if candidate:
                        candidates.append(candidate)
            
        except Exception as e:
            logger.debug(f"[PinkSaleScraper] GraphQL fetch failed: {e}")
        
        return candidates
    
    def fetch_finished_presales(self, chain: str = 'bsc', limit: int = 50) -> List[TokenCandidate]:
        """
        Fetch finished/ended presales that may be about to list on DEX.
        
        Args:
            chain: Blockchain to fetch from
            limit: Maximum number of presales to fetch
            
        Returns:
            List of TokenCandidate objects
        """
        candidates = []
        
        # Fetch and parse similar to active presales
        url = self.CHAIN_URLS.get(chain, self.LAUNCHPADS_URL)
        html = self._fetch_page(url)
        
        if html:
            candidates = self._parse_from_html(html, chain)
            # Filter to ended presales
            finished = [c for c in candidates if c.presale_status.upper() in ['ENDED', 'FINISHED']]
            return finished[:limit]
        
        return candidates
    
    def fetch_ending_soon(self, hours: float = 2.0, chain: str = 'bsc') -> List[TokenCandidate]:
        """
        Fetch presales ending within specified hours.
        These are prime arbitrage candidates as they may list soon.
        
        Args:
            hours: Number of hours to look ahead
            chain: Blockchain to fetch from
            
        Returns:
            List of TokenCandidate objects ending soon
        """
        all_presales = self.fetch_active_presales(chain)
        now = datetime.now(timezone.utc)
        
        ending_soon = []
        for candidate in all_presales:
            if candidate.end_time:
                time_until_end = (candidate.end_time - now).total_seconds() / 3600
                if 0 < time_until_end <= hours:
                    ending_soon.append(candidate)
        
        # Sort by end time (soonest first)
        ending_soon.sort(key=lambda x: x.end_time or datetime.max.replace(tzinfo=timezone.utc))
        
        logger.info(f"[PinkSaleScraper] Found {len(ending_soon)} presales ending within {hours}h")
        return ending_soon
    
    def fetch_presale_details(self, presale_url: str) -> Optional[TokenCandidate]:
        """
        Fetch detailed information for a specific presale.
        
        Args:
            presale_url: Full URL to the presale page
            
        Returns:
            TokenCandidate with full details or None
        """
        html = self._fetch_page(presale_url)
        if not html:
            return None
        
        # Parse detailed information
        # This would extract: vesting schedule, team info, audit status, etc.
        
        # Extract chain from URL
        chain = 'bsc'
        for c in self.SUPPORTED_CHAINS:
            if c in presale_url:
                chain = c
                break
        
        candidates = self._parse_from_html(html, chain)
        if candidates:
            candidate = candidates[0]
            candidate.source_url = presale_url
            return candidate
        
        return None
    
    def _parse_from_json(self, data: Dict, chain: str) -> List[TokenCandidate]:
        """
        Parse TokenCandidates from JSON structure.
        PinkSale sometimes embeds data in window.__INITIAL_STATE__
        """
        candidates = []
        
        # Try different possible structures
        presales = data.get('presales', []) or data.get('launchpads', []) or data.get('data', [])
        
        if isinstance(presales, dict):
            # Handle nested structure
            presales = presales.get('list', []) or presales.get('items', [])
        
        for item in presales:
            try:
                candidate = self._item_to_candidate(item, chain)
                if candidate:
                    candidates.append(candidate)
            except Exception as e:
                logger.debug(f"[PinkSaleScraper] Error parsing item: {e}")
                continue
        
        return candidates
    
    def _parse_from_html(self, html: str, chain: str) -> List[TokenCandidate]:
        """
        Parse TokenCandidates from HTML using regex patterns.
        Fallback when JSON extraction fails.
        """
        candidates = []
        
        try:
            # Check for Cloudflare
            if 'challenge-platform' in html or 'cf-browser-verification' in html:
                logger.warning("[PinkSaleScraper] Cloudflare protection active - cannot parse HTML")
                return candidates
            
            # Look for presale cards/containers
            # PinkSale uses various class names over time
            presale_patterns = [
                r'<a[^>]*href="(/launchpad/[^"]+)"[^>]*>.*?<\/a>',  # Launchpad links
                r'data-presale-address="(0x[a-fA-F0-9]{40})"',  # Presale addresses
                r'data-token-address="(0x[a-fA-F0-9]{40})"',  # Token addresses
            ]
            
            # Find all presale URLs
            presale_urls = re.findall(r'href="(/launchpad/0x[a-fA-F0-9]{40})"', html)
            presale_urls = list(set(presale_urls))  # Deduplicate
            
            logger.info(f"[PinkSaleScraper] Found {len(presale_urls)} presale URLs in HTML")
            
            for url_path in presale_urls[:20]:  # Limit to 20 for rate limiting
                full_url = urljoin(self.BASE_URL, url_path)
                
                # Extract token address from URL
                token_address = self._parse_token_address(url_path)
                
                if token_address:
                    candidate = TokenCandidate(
                        token_address=token_address,
                        symbol="UNKNOWN",  # Would need to fetch details
                        name="Unknown Token",
                        chain=chain,
                        presale_address=token_address,
                        source_url=full_url,
                    )
                    candidates.append(candidate)
        
        except Exception as e:
            logger.error(f"[PinkSaleScraper] HTML parsing error: {e}")
        
        return candidates
    
    def _item_to_candidate(self, item: Dict, chain: str) -> Optional[TokenCandidate]:
        """Convert a JSON item to TokenCandidate"""
        try:
            # Extract fields with flexible key names
            token_address = (
                item.get('tokenAddress') or 
                item.get('token_address') or 
                item.get('token') or 
                ''
            )
            
            if not token_address or not token_address.startswith('0x'):
                return None
            
            presale_address = (
                item.get('presaleAddress') or 
                item.get('address') or 
                item.get('id') or 
                token_address
            )
            
            # Parse status
            status = (
                item.get('status') or 
                item.get('state') or 
                item.get('presaleStatus') or 
                'UNKNOWN'
            ).upper()
            
            # Parse amounts
            total_raised = self._parse_amount(str(item.get('totalRaised', item.get('total_raised', 0))))
            soft_cap = self._parse_amount(str(item.get('softCap', item.get('soft_cap', 0))))
            hard_cap = self._parse_amount(str(item.get('hardCap', item.get('hard_cap', 0))))
            
            # Parse price
            presale_price = 0.0
            if 'presalePrice' in item:
                presale_price = float(item['presalePrice'])
            elif 'price' in item:
                presale_price = float(item['price'])
            elif 'rate' in item and total_raised > 0:
                # Calculate from rate
                presale_price = 1.0 / float(item['rate'])
            
            # Parse times
            start_time = self._parse_datetime(str(item.get('startTime', item.get('start_time', ''))))
            end_time = self._parse_datetime(str(item.get('endTime', item.get('end_time', ''))))
            
            # Parse liquidity percentage
            liquidity_pct = self._parse_percentage(str(item.get('liquidity', item.get('liquidityPercent', 0))))
            
            # Build candidate
            candidate = TokenCandidate(
                token_address=token_address,
                symbol=item.get('symbol', item.get('tokenSymbol', 'UNKNOWN')),
                name=item.get('name', item.get('tokenName', 'Unknown Token')),
                chain=chain,
                presale_address=presale_address,
                presale_price=presale_price,
                presale_status=status,
                total_raised_usd=total_raised,
                liquidity_percent=liquidity_pct,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
                start_time=start_time,
                end_time=end_time,
                source_url=urljoin(self.BASE_URL, f"/launchpad/{presale_address}"),
                raw_data=item,
            )
            
            return candidate
            
        except Exception as e:
            logger.debug(f"[PinkSaleScraper] Error converting item: {e}")
            return None
    
    def enrich_with_dex_prices(self, 
                               candidates: List[TokenCandidate],
                               price_fetcher: Optional[Callable[[str, str], Dict]] = None) -> List[TokenCandidate]:
        """
        Enrich candidates with current DEX prices.
        
        Args:
            candidates: List of TokenCandidates to enrich
            price_fetcher: Optional custom price fetcher function(token_address, chain) -> price_data
            
        Returns:
            Updated list of candidates with DEX prices
        """
        enriched = []
        
        for candidate in candidates:
            try:
                if price_fetcher:
                    # Use custom fetcher
                    price_data = price_fetcher(candidate.token_address, candidate.chain)
                else:
                    # Use default DEXScreener integration
                    price_data = self._fetch_dexscreener_price(candidate.token_address, candidate.chain)
                
                if price_data:
                    candidate.dex_price = price_data.get('priceUsd', 0)
                    candidate.dex_liquidity_usd = price_data.get('liquidity', {}).get('usd', 0)
                    candidate.dex_volume_24h = price_data.get('volume', {}).get('h24', 0)
                    
                    # Calculate spread
                    if candidate.presale_price > 0 and candidate.dex_price > 0:
                        candidate.price_spread_percent = (
                            (candidate.dex_price - candidate.presale_price) / candidate.presale_price * 100
                        )
                    
                    candidate.last_updated = datetime.now(timezone.utc)
                    candidate._calculate_arbitrage_score()
                
                enriched.append(candidate)
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"[PinkSaleScraper] Error enriching {candidate.symbol}: {e}")
                enriched.append(candidate)
        
        return enriched
    
    def _fetch_dexscreener_price(self, token_address: str, chain: str) -> Optional[Dict]:
        """
        Fetch price from DEXScreener API.
        
        Args:
            token_address: Token contract address
            chain: Blockchain name
            
        Returns:
            Price data dict or None
        """
        try:
            # Map chain names
            chain_map = {
                'bsc': 'bsc',
                'ethereum': 'ethereum',
                'polygon': 'polygon',
                'arbitrum': 'arbitrum',
                'base': 'base',
                'avalanche': 'avalanche',
                'fantom': 'fantom',
            }
            
            dex_chain = chain_map.get(chain, chain)
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                
                if pairs:
                    # Find best pair by liquidity
                    best_pair = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                    return best_pair
            
            return None
            
        except Exception as e:
            logger.debug(f"[PinkSaleScraper] DEXScreener fetch error: {e}")
            return None
    
    def find_arbitrage_opportunities(self, 
                                      min_spread_percent: float = 5.0,
                                      min_liquidity_usd: float = 5000,
                                      chain: str = 'bsc') -> List[TokenCandidate]:
        """
        Find presale-DEX arbitrage opportunities.
        
        This is the main method for discovering arbitrage opportunities.
        
        Args:
            min_spread_percent: Minimum price spread percentage to consider
            min_liquidity_usd: Minimum liquidity requirement
            chain: Blockchain to scan
            
        Returns:
            List of TokenCandidate opportunities sorted by arbitrage score
        """
        opportunities = []
        
        logger.info(f"[PinkSaleScraper] Scanning for arbitrage opportunities on {chain}...")
        
        # 1. Fetch active presales
        active = self.fetch_active_presales(chain)
        
        # 2. Fetch finished presales about to list
        finished = self.fetch_finished_presales(chain)
        
        # Combine and deduplicate
        all_candidates = {c.token_address: c for c in active + finished}
        candidates = list(all_candidates.values())
        
        logger.info(f"[PinkSaleScraper] Analyzing {len(candidates)} unique presales")
        
        # 3. Enrich with DEX prices
        enriched = self.enrich_with_dex_prices(candidates)
        
        # 4. Filter for opportunities
        for candidate in enriched:
            # Check if already listed with good spread
            if candidate.is_listed:
                if candidate.price_spread_percent >= min_spread_percent:
                    opportunities.append(candidate)
            else:
                # Not listed yet - check if it's about to list (high potential)
                if (candidate.presale_status.upper() == 'ENDED' and 
                    candidate.total_raised_usd >= min_liquidity_usd):
                    # Mark as potential opportunity
                    candidate.arbitrage_score = candidate.total_raised_usd / 1000  # Liquidity score
                    opportunities.append(candidate)
        
        # Sort by arbitrage score (descending)
        opportunities.sort(key=lambda x: x.arbitrage_score, reverse=True)
        
        logger.info(f"[PinkSaleScraper] Found {len(opportunities)} arbitrage opportunities")
        
        return opportunities
    
    def get_watchlist(self, hours_until_listing: float = 24.0) -> List[TokenCandidate]:
        """
        Get a watchlist of tokens that will list within specified hours.
        Useful for preparing to execute trades when listing happens.
        
        Args:
            hours_until_listing: Hours to look ahead
            
        Returns:
            List of TokenCandidates sorted by listing time
        """
        watchlist = []
        
        for chain in ['bsc', 'ethereum']:  # Primary chains
            ending = self.fetch_ending_soon(hours=hours_until_listing, chain=chain)
            
            for candidate in ending:
                # Estimate listing time (usually within 1 hour after presale ends)
                if candidate.end_time:
                    candidate.listing_time = candidate.end_time
                watchlist.append(candidate)
        
        # Sort by estimated listing time
        watchlist.sort(key=lambda x: x.listing_time or datetime.max.replace(tzinfo=timezone.utc))
        
        return watchlist
    
    def fetch_with_selenium(self, url: str, wait_for: str = "body", timeout: int = 30) -> Optional[str]:
        """
        Fetch page using Selenium (for Cloudflare-protected sites).
        
        Note: Requires selenium and webdriver to be installed.
        
        Args:
            url: URL to fetch
            wait_for: CSS selector to wait for
            timeout: Page load timeout
            
        Returns:
            HTML content or None
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument(f'--user-agent={self.session.headers["User-Agent"]}')
            
            # Create driver
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(timeout)
            
            try:
                driver.get(url)
                # Wait for element to ensure page is loaded
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                )
                return driver.page_source
            finally:
                driver.quit()
                
        except ImportError:
            logger.error("[PinkSaleScraper] Selenium not installed. Run: pip install selenium")
            return None
        except Exception as e:
            logger.error(f"[PinkSaleScraper] Selenium error: {e}")
            return None
    
    def fetch_from_alternative_sources(self, chain: str = 'bsc') -> List[TokenCandidate]:
        """
        Fetch presale data from alternative sources when PinkSale is blocked.
        
        Alternative sources:
        - DexTools trending (for newly listed tokens)
        - CoinGecko recently added
        - Defined.fi API (if available)
        
        Args:
            chain: Blockchain to filter by
            
        Returns:
            List of TokenCandidate objects
        """
        candidates = []
        
        # Try CoinGecko recently added
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 100,
                'page': 1,
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                coins = response.json()
                
                for coin in coins:
                    platforms = coin.get('platforms', {})
                    
                    # Find address for requested chain
                    address = None
                    if chain == 'ethereum' and platforms.get('ethereum'):
                        address = platforms['ethereum']
                    elif chain == 'bsc' and platforms.get('binance-smart-chain'):
                        address = platforms['binance-smart-chain']
                    elif chain == 'polygon' and platforms.get('polygon-pos'):
                        address = platforms['polygon-pos']
                    elif chain == 'arbitrum' and platforms.get('arbitrum-one'):
                        address = platforms['arbitrum-one']
                    
                    if address:
                        candidate = TokenCandidate(
                            token_address=address,
                            symbol=coin.get('symbol', 'UNKNOWN').upper(),
                            name=coin.get('name', 'Unknown'),
                            chain=chain,
                            dex_price=coin.get('current_price', 0),
                            dex_volume_24h=coin.get('total_volume', 0),
                            source_url=f"https://www.coingecko.com/en/coins/{coin.get('id')}",
                        )
                        candidates.append(candidate)
                        
        except Exception as e:
            logger.debug(f"[PinkSaleScraper] CoinGecko fetch error: {e}")
        
        logger.info(f"[PinkSaleScraper] Found {len(candidates)} tokens from alternative sources")
        return candidates
    
    def get_presale_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current presales across all chains.
        
        Returns:
            Dict with statistics
        """
        stats = {
            'total_active': 0,
            'total_ended': 0,
            'total_raised_usd': 0.0,
            'by_chain': {},
            'top_opportunities': [],
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        for chain in ['bsc', 'ethereum']:
            active = self.fetch_active_presales(chain)
            ended = self.fetch_finished_presales(chain)
            
            stats['by_chain'][chain] = {
                'active': len(active),
                'ended': len(ended),
                'total_raised': sum(c.total_raised_usd for c in active + ended),
            }
            
            stats['total_active'] += len(active)
            stats['total_ended'] += len(ended)
            stats['total_raised_usd'] += stats['by_chain'][chain]['total_raised']
            
            # Find opportunities
            opportunities = self.find_arbitrage_opportunities(chain=chain)
            stats['top_opportunities'].extend([
                {
                    'symbol': o.symbol,
                    'chain': o.chain,
                    'spread_percent': o.price_spread_percent,
                    'arbitrage_score': o.arbitrage_score,
                }
                for o in opportunities[:5]
            ])
        
        return stats


# Convenience function for quick usage
def get_pinksale_scraper() -> PinkSaleScraper:
    """Get a singleton instance of PinkSaleScraper"""
    return PinkSaleScraper()


if __name__ == "__main__":
    # Test the scraper
    print("=" * 80)
    print("🚀 PinkSale Scraper - Test Mode")
    print("=" * 80)
    
    scraper = PinkSaleScraper(rate_limit_delay=1.0)
    
    # Test 1: Fetch active presales on BSC
    print("\n[TEST 1] Fetching active BSC presales...")
    print("Note: PinkSale uses Cloudflare protection which may block direct requests.")
    print("For production use, consider using Selenium or alternative data sources.")
    print()
    
    active = scraper.fetch_active_presales('bsc', limit=10)
    print(f"Found {len(active)} active presales")
    
    for c in active[:3]:
        print(f"  - {c.symbol} ({c.name}) | Raised: ${c.total_raised_usd:,.0f}")
    
    if not active:
        print("  (No presales found - Cloudflare may be blocking requests)")
    
    # Test 2: Fetch from alternative sources
    print("\n[TEST 2] Fetching from alternative sources (CoinGecko)...")
    alt_candidates = scraper.fetch_from_alternative_sources('bsc')
    print(f"Found {len(alt_candidates)} tokens from alternative sources")
    
    for c in alt_candidates[:5]:
        print(f"  - {c.symbol} ({c.name}) | Price: ${c.dex_price:,.6f}")
    
    # Test 3: Fetch ending soon
    print("\n[TEST 3] Fetching presales ending within 6 hours...")
    ending = scraper.fetch_ending_soon(hours=6, chain='bsc')
    print(f"Found {len(ending)} presales ending soon")
    
    # Test 4: Find arbitrage opportunities
    print("\n[TEST 4] Finding arbitrage opportunities...")
    opportunities = scraper.find_arbitrage_opportunities(
        min_spread_percent=5.0,
        min_liquidity_usd=5000,
        chain='bsc'
    )
    print(f"Found {len(opportunities)} opportunities")
    
    for opp in opportunities[:5]:
        status_emoji = "🟢" if opp.is_listed else "⏳"
        print(f"  {status_emoji} {opp.symbol}: {opp.price_spread_percent:+.1f}% spread | "
              f"Score: {opp.arbitrage_score:.0f}")
    
    # Test 5: Enrich with DEX prices
    if alt_candidates:
        print("\n[TEST 5] Enriching candidates with DEX prices...")
        enriched = scraper.enrich_with_dex_prices(alt_candidates[:5])
        for e in enriched[:3]:
            print(f"  - {e.symbol}: ${e.dex_price:,.6f} | Liquidity: ${e.dex_liquidity_usd:,.0f}")
    
    # Test 6: Get watchlist
    print("\n[TEST 6] Generating watchlist for next 12 hours...")
    watchlist = scraper.get_watchlist(hours_until_listing=12.0)
    print(f"Watchlist: {len(watchlist)} tokens")
    
    for w in watchlist[:3]:
        time_str = w.end_time.strftime('%H:%M') if w.end_time else 'Unknown'
        print(f"  - {w.symbol} ends at {time_str} UTC")
    
    print("\n" + "=" * 80)
    print("✅ PinkSale Scraper tests completed")
    print("=" * 80)
    print("\nNotes:")
    print("- PinkSale uses Cloudflare protection which blocks simple HTTP requests")
    print("- For production deployment, use Selenium/Playwright or GraphQL API")
    print("- Alternative data sources (CoinGecko) are available as fallback")
    print("- DEXScreener integration works for price comparison once addresses are known")
    print("=" * 80)
