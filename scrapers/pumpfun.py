#!/usr/bin/env python3
"""
Pump.fun Scraper for Solana Token Discovery
============================================

Fetches newly created tokens from Pump.fun for early arbitrage detection.
Monitors bonding curve progress and detects imminent migrations to Raydium.

API Endpoints:
- /api/coins/for-you - New token feed
- /api/coins/king-of-the-hill - Trending tokens
- /api/coins/{mint} - Individual coin details

Bonding Curve:
- Tokens launch on Pump.fun with a bonding curve pricing model
- When market cap hits ~$69k (bonding curve ~100%), token migrates to Raydium
- Early discovery = arbitrage opportunities during/after migration
"""

import requests
import json
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TokenCandidate:
    """
    Represents a token discovered from Pump.fun.
    Used by the discovery engine for arbitrage analysis.
    """
    # Core identifiers
    mint_address: str
    name: str
    symbol: str
    
    # Metadata
    description: str = ""
    image_uri: str = ""
    creator_address: str = ""
    creation_time: Optional[datetime] = None
    
    # Market data
    usd_market_cap: float = 0.0
    sol_market_cap: float = 0.0
    price_usd: float = 0.0
    price_sol: float = 0.0
    
    # Bonding curve data
    bonding_curve_progress: float = 0.0  # 0-100%
    bonding_curve_address: str = ""
    is_nearing_migration: bool = False
    migration_threshold_usd: float = 69000.0  # ~$69k market cap
    
    # Source tracking
    source: str = "pumpfun"
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Raydium migration tracking
    is_migrated: bool = False
    raydium_pool: Optional[str] = None
    
    # Priority flag for discovery engine
    priority: str = "NORMAL"  # HIGH (nearing migration), NORMAL, LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        for key in ['creation_time', 'discovered_at', 'last_updated']:
            if data[key]:
                if isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
        return data
    
    @property
    def age_seconds(self) -> float:
        """Get token age in seconds since creation."""
        if not self.creation_time:
            return 0.0
        return (datetime.now(timezone.utc) - self.creation_time).total_seconds()
    
    @property
    def age_minutes(self) -> float:
        """Get token age in minutes."""
        return self.age_seconds / 60.0
    
    @property
    def migration_eta_minutes(self) -> Optional[float]:
        """Estimate minutes until migration based on bonding curve progress."""
        if self.bonding_curve_progress >= 100:
            return 0.0
        if self.bonding_curve_progress <= 0:
            return None
        # Rough estimate based on typical velocity
        # In reality, this depends on buy pressure
        remaining = 100 - self.bonding_curve_progress
        return remaining * 2  # Rough estimate: 2 min per %


@dataclass
class PumpFunConfig:
    """Configuration for Pump.fun scraper."""
    # Rate limiting
    min_request_interval: float = 1.0  # Minimum seconds between requests
    max_requests_per_minute: int = 30
    
    # Filtering
    max_token_age_minutes: int = 60  # Only tokens created within this window
    min_market_cap_usd: float = 1000  # Minimum $1k market cap
    max_market_cap_usd: float = 100000  # Maximum $100k (focus on early tokens)
    
    # Migration detection
    migration_alert_threshold: float = 85.0  # Alert when 85% to migration
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 2.0


class PumpFunScraper:
    """
    Scraper for Pump.fun token discovery.
    
    Fetches new tokens, monitors bonding curves, and detects
    imminent migrations to Raydium for arbitrage opportunities.
    """
    
    # Pump.fun API endpoints
    BASE_URL = "https://pump.fun"
    API_BASE = "https://pump.fun/api"
    
    # Alternative data sources
    ALTERNATIVE_APIS = {
        'pumpportal': 'https://api.pumpportal.fun',
        'gmgn': 'https://api.gmgn.ai',
    }
    
    ENDPOINTS = {
        'for_you': '/coins/for-you',
        'king_of_hill': '/coins/king-of-the-hill',
        'coin_details': '/coins/{}',  # Format with mint address
        'profiles_for_you': '/profiles/for-you',
        'profiles_following': '/profiles/following',
    }
    
    def __init__(self, config: Optional[PumpFunConfig] = None, use_alternative: bool = False):
        """
        Initialize Pump.fun scraper.
        
        Args:
            config: PumpFunConfig instance or None for defaults
            use_alternative: Use alternative API if pump.fun is blocked
        """
        self.config = config or PumpFunConfig()
        self.use_alternative = use_alternative
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://pump.fun/',
            'Origin': 'https://pump.fun',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'no-cache',
        })
        
        # Rate limiting state
        self.last_request_time: Optional[float] = None
        self.request_count = 0
        self.request_window_start = time.time()
        
        # Tracking state
        self.seen_tokens: Dict[str, datetime] = {}  # mint -> first_seen
        self.token_cache: Dict[str, TokenCandidate] = {}
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'tokens_discovered': 0,
            'migrations_detected': 0,
        }
        
        logger.info("[PumpFunScraper] Initialized")
        logger.info(f"  Rate limit: {self.config.max_requests_per_minute}/min")
        logger.info(f"  Migration threshold: {self.config.migration_alert_threshold}%")
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        now = time.time()
        
        # Reset counter if window has passed
        if now - self.request_window_start >= 60:
            self.request_count = 0
            self.request_window_start = now
        
        # Check per-minute limit
        if self.request_count >= self.config.max_requests_per_minute:
            sleep_time = 60 - (now - self.request_window_start) + 1
            logger.warning(f"[PumpFunScraper] Rate limit reached, sleeping {sleep_time:.1f}s")
            time.sleep(max(sleep_time, 0))
            self.request_count = 0
            self.request_window_start = time.time()
        
        # Apply minimum interval
        if self.last_request_time:
            elapsed = now - self.last_request_time
            if elapsed < self.config.min_request_interval:
                sleep_time = self.config.min_request_interval - elapsed
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, retries: int = 0) -> Optional[Dict]:
        """
        Make a rate-limited request to Pump.fun API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            retries: Current retry count
            
        Returns:
            JSON response data or None on failure
        """
        # Ensure proper URL construction
        if endpoint.startswith('http'):
            url = endpoint
        else:
            # Remove leading slash if present to avoid double slashes
            endpoint = endpoint.lstrip('/')
            url = f"{self.API_BASE}/{endpoint}"
        
        self._rate_limit()
        
        try:
            self.stats['total_requests'] += 1
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                self.stats['successful_requests'] += 1
                return response.json()
            elif response.status_code == 429:
                logger.warning(f"[PumpFunScraper] Rate limited (429), backing off...")
                if retries < self.config.max_retries:
                    time.sleep(self.config.retry_delay * (retries + 1))
                    return self._make_request(endpoint, params, retries + 1)
            else:
                logger.error(f"[PumpFunScraper] HTTP {response.status_code}: {url}")
                self.stats['failed_requests'] += 1
                
        except requests.exceptions.Timeout:
            logger.error(f"[PumpFunScraper] Timeout: {url}")
            if retries < self.config.max_retries:
                time.sleep(self.config.retry_delay)
                return self._make_request(endpoint, params, retries + 1)
        except requests.exceptions.RequestException as e:
            logger.error(f"[PumpFunScraper] Request error: {e}")
            self.stats['failed_requests'] += 1
        except json.JSONDecodeError as e:
            logger.error(f"[PumpFunScraper] JSON decode error: {e}")
            self.stats['failed_requests'] += 1
        
        return None
    
    def _parse_token_data(self, data: Dict) -> Optional[TokenCandidate]:
        """
        Parse raw API token data into TokenCandidate.
        
        Args:
            data: Raw token data from API
            
        Returns:
            TokenCandidate or None if invalid
        """
        try:
            mint = data.get('mint')
            if not mint:
                return None
            
            # Parse creation time if available
            creation_time = None
            if 'created_timestamp' in data:
                try:
                    ts = data['created_timestamp']
                    if isinstance(ts, (int, float)):
                        creation_time = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                except (ValueError, TypeError):
                    pass
            
            # Calculate bonding curve progress
            market_cap = float(data.get('usd_market_cap', 0) or 0)
            bonding_progress = min((market_cap / 69000) * 100, 100) if market_cap > 0 else 0
            
            # Determine priority
            priority = "NORMAL"
            is_nearing = bonding_progress >= self.config.migration_alert_threshold
            if is_nearing:
                priority = "HIGH"
            elif bonding_progress < 10:
                priority = "LOW"
            
            token = TokenCandidate(
                mint_address=mint,
                name=data.get('name', 'Unknown'),
                symbol=data.get('symbol', 'UNKNOWN'),
                description=data.get('description', ''),
                image_uri=data.get('image_uri', ''),
                creator_address=data.get('creator', ''),
                creation_time=creation_time,
                usd_market_cap=market_cap,
                sol_market_cap=float(data.get('market_cap', 0) or 0),
                price_usd=float(data.get('usd_price', 0) or 0),
                price_sol=float(data.get('price', 0) or 0),
                bonding_curve_progress=bonding_progress,
                bonding_curve_address=data.get('bonding_curve', ''),
                is_nearing_migration=is_nearing,
                is_migrated=data.get('is_migrated', False),
                raydium_pool=data.get('raydium_pool', None),
                priority=priority,
            )
            
            return token
            
        except Exception as e:
            logger.error(f"[PumpFunScraper] Error parsing token data: {e}")
            return None
    
    def _fetch_from_dexscreener(self, limit: int = 50) -> List[TokenCandidate]:
        """
        Fetch Pump.fun tokens from DexScreener API as alternative source.
        DexScreener provides comprehensive DEX data including Pump.fun tokens.
        """
        tokens = []
        
        try:
            # Use DexScreener's token profiles API for Pump.fun tokens
            url = "https://api.dexscreener.com/token-profiles/latest/v1"
            
            self._rate_limit()
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                profiles = data if isinstance(data, list) else data.get('profiles', [])
                
                for profile in profiles[:limit]:
                    token = self._parse_dexscreener_profile(profile)
                    if token:
                        tokens.append(token)
                        
        except Exception as e:
            logger.debug(f"[PumpFunScraper] DexScreener fetch error: {e}")
        
        return tokens
    
    def _parse_dexscreener_profile(self, data: Dict) -> Optional[TokenCandidate]:
        """Parse DexScreener token profile into TokenCandidate."""
        try:
            token_address = data.get('tokenAddress')
            if not token_address:
                return None
            
            # Check if it's a Pump.fun token
            links = data.get('links', [])
            is_pumpfun = any(
                'pump.fun' in str(link.get('url', '')).lower() 
                for link in links
            )
            
            # Get description
            description = data.get('description', '')
            
            # Try to get price data from DexScreener
            price_usd = 0.0
            market_cap = 0.0
            
            # Parse creation time if available in description
            creation_time = None
            
            # Calculate bonding curve progress from market cap
            bonding_progress = min((market_cap / 69000) * 100, 100) if market_cap > 0 else 0
            
            is_nearing = bonding_progress >= self.config.migration_alert_threshold
            priority = "HIGH" if is_nearing else "NORMAL"
            
            return TokenCandidate(
                mint_address=token_address,
                name=data.get('name', 'Unknown'),
                symbol=data.get('symbol', 'UNKNOWN'),
                description=description,
                image_uri=data.get('icon', ''),
                creation_time=creation_time,
                usd_market_cap=market_cap,
                price_usd=price_usd,
                bonding_curve_progress=bonding_progress,
                is_nearing_migration=is_nearing,
                priority=priority,
            )
        except Exception as e:
            logger.debug(f"[PumpFunScraper] Error parsing DexScreener profile: {e}")
            return None
    
    def _fetch_solana_tokens(self, limit: int = 50) -> List[TokenCandidate]:
        """
        Fetch recently created Solana tokens.
        Uses DexScreener's token pairs API to find new Pump.fun tokens.
        """
        tokens = []
        
        try:
            # Get latest Solana pairs from DexScreener
            url = "https://api.dexscreener.com/latest/dex/search"
            params = {'q': 'solana pump'}
            
            self._rate_limit()
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                
                # Filter for Pump.fun pairs
                seen_mints = set()
                for pair in pairs:
                    dex_id = pair.get('dexId', '').lower()
                    
                    # Check if it's a Pump.fun pair
                    if 'pump' in dex_id or self._is_pumpfun_pair(pair):
                        base_token = pair.get('baseToken', {})
                        mint = base_token.get('address')
                        
                        if mint and mint not in seen_mints:
                            seen_mints.add(mint)
                            token = self._parse_pair_to_token(pair)
                            if token:
                                tokens.append(token)
                                
                                if len(tokens) >= limit:
                                    break
                                    
        except Exception as e:
            logger.debug(f"[PumpFunScraper] Solana tokens fetch error: {e}")
        
        return tokens
    
    def _is_pumpfun_pair(self, pair: Dict) -> bool:
        """Check if a pair is from Pump.fun based on various indicators."""
        # Check DEX ID
        dex_id = pair.get('dexId', '').lower()
        if 'pump' in dex_id:
            return True
        
        # Check pair address patterns
        pair_address = pair.get('pairAddress', '').lower()
        if 'pump' in pair_address:
            return True
        
        # Check labels
        labels = pair.get('labels', [])
        if any('pump' in str(label).lower() for label in labels):
            return True
        
        return False
    
    def _parse_pair_to_token(self, pair: Dict) -> Optional[TokenCandidate]:
        """Parse DexScreener pair data into TokenCandidate."""
        try:
            base_token = pair.get('baseToken', {})
            mint = base_token.get('address')
            if not mint:
                return None
            
            # Get market data
            price_usd = float(pair.get('priceUsd', 0) or 0)
            market_cap = float(pair.get('marketCap', 0) or pair.get('fdv', 0) or 0)
            
            # If no market cap, estimate from price and typical supply
            if market_cap == 0 and price_usd > 0:
                # Pump.fun tokens typically have 1B supply
                market_cap = price_usd * 1_000_000_000
            
            # Calculate bonding curve progress
            bonding_progress = min((market_cap / 69000) * 100, 100) if market_cap > 0 else 0
            
            # Check liquidity for additional context
            liquidity = pair.get('liquidity', {})
            liquidity_usd = float(liquidity.get('usd', 0) or 0)
            
            # Determine migration status
            dex_id = pair.get('dexId', '').lower()
            is_migrated = 'raydium' in dex_id or 'orca' in dex_id
            
            is_nearing = bonding_progress >= self.config.migration_alert_threshold
            priority = "HIGH" if is_nearing else "NORMAL"
            
            # Get volume info
            volume = pair.get('volume', {})
            volume_24h = float(volume.get('h24', 0) or 0)
            
            return TokenCandidate(
                mint_address=mint,
                name=base_token.get('name', 'Unknown'),
                symbol=base_token.get('symbol', 'UNKNOWN'),
                usd_market_cap=market_cap,
                price_usd=price_usd,
                bonding_curve_progress=bonding_progress,
                is_nearing_migration=is_nearing,
                is_migrated=is_migrated,
                raydium_pool=pair.get('pairAddress') if is_migrated else None,
                priority=priority,
            )
        except Exception as e:
            logger.debug(f"[PumpFunScraper] Error parsing pair: {e}")
            return None
    
    def get_new_tokens(self, limit: int = 50, include_nsfw: bool = False) -> List[TokenCandidate]:
        """
        Fetch newly created tokens from Pump.fun.
        Tries official API first, falls back to alternative sources.
        
        Args:
            limit: Maximum number of tokens to fetch
            include_nsfw: Whether to include NSFW content
            
        Returns:
            List of TokenCandidate objects
        """
        tokens = []
        
        # Try official Pump.fun API first
        if not self.use_alternative:
            offset = 0
            batch_size = min(limit, 50)
            
            while len(tokens) < limit:
                params = {
                    'offset': offset,
                    'limit': batch_size,
                    'includeNsfw': 'true' if include_nsfw else 'false'
                }
                
                data = self._make_request(self.ENDPOINTS['for_you'], params)
                
                if data:
                    items = data if isinstance(data, list) else data.get('coins', [])
                    
                    for item in items:
                        token = self._parse_token_data(item)
                        if token and self._filter_token(token):
                            if token.mint_address not in self.seen_tokens:
                                self.seen_tokens[token.mint_address] = datetime.now(timezone.utc)
                                self.stats['tokens_discovered'] += 1
                            
                            self.token_cache[token.mint_address] = token
                            tokens.append(token)
                            
                            if len(tokens) >= limit:
                                break
                    
                    offset += batch_size
                    if len(items) < batch_size:
                        break
                else:
                    # API failed, mark for alternative
                    logger.warning("[PumpFunScraper] Official API failed, trying alternative sources...")
                    self.use_alternative = True
                    break
        
        # Fall back to alternative sources
        if not tokens and self.use_alternative:
            logger.info("[PumpFunScraper] Using alternative data source (DexScreener)")
            
            # Try multiple methods
            tokens = self._fetch_solana_tokens(limit=limit)
            
            if not tokens:
                tokens = self._fetch_from_dexscreener(limit=limit)
            
            # Filter and cache
            filtered = []
            for token in tokens:
                if self._filter_token(token):
                    if token.mint_address not in self.seen_tokens:
                        self.seen_tokens[token.mint_address] = datetime.now(timezone.utc)
                        self.stats['tokens_discovered'] += 1
                        logger.info(f"[PumpFunScraper] New token: {token.symbol} (${token.usd_market_cap:,.0f} mcap)")
                    
                    self.token_cache[token.mint_address] = token
                    filtered.append(token)
            
            tokens = filtered
        
        return tokens[:limit]
    
    def get_trending_tokens(self, limit: int = 20) -> List[TokenCandidate]:
        """
        Fetch trending/king of the hill tokens.
        
        Args:
            limit: Maximum number of tokens to fetch
            
        Returns:
            List of TokenCandidate objects
        """
        tokens = []
        
        params = {
            'includeNsfw': 'false',
            'limit': limit
        }
        
        data = self._make_request(self.ENDPOINTS['king_of_hill'], params)
        if not data:
            return tokens
        
        items = data if isinstance(data, list) else data.get('coins', [])
        
        for item in items:
            token = self._parse_token_data(item)
            if token and self._filter_token(token):
                tokens.append(token)
                self.token_cache[token.mint_address] = token
        
        return tokens
    
    def get_token_details(self, mint_address: str) -> Optional[TokenCandidate]:
        """
        Fetch detailed information for a specific token.
        
        Args:
            mint_address: Token mint address
            
        Returns:
            TokenCandidate or None if not found
        """
        endpoint = self.ENDPOINTS['coin_details'].format(mint_address)
        data = self._make_request(endpoint)
        
        if data:
            token = self._parse_token_data(data)
            if token:
                self.token_cache[mint_address] = token
            return token
        
        return None
    
    def _filter_token(self, token: TokenCandidate) -> bool:
        """
        Apply filters to determine if token should be included.
        
        Args:
            token: TokenCandidate to evaluate
            
        Returns:
            True if token passes filters
        """
        # Age filter
        if token.creation_time:
            age_minutes = token.age_minutes
            if age_minutes > self.config.max_token_age_minutes:
                return False
        
        # Market cap filters
        if token.usd_market_cap < self.config.min_market_cap_usd:
            return False
        if token.usd_market_cap > self.config.max_market_cap_usd:
            return False
        
        return True
    
    def get_migrating_tokens(self) -> List[TokenCandidate]:
        """
        Get tokens nearing migration to Raydium (high priority).
        
        Returns:
            List of tokens with bonding curve >= threshold
        """
        # Refresh token data
        all_tokens = self.get_new_tokens(limit=100)
        
        migrating = [
            t for t in all_tokens
            if t.is_nearing_migration or t.bonding_curve_progress >= self.config.migration_alert_threshold
        ]
        
        # Sort by bonding curve progress (highest first)
        migrating.sort(key=lambda x: x.bonding_curve_progress, reverse=True)
        
        if migrating:
            logger.info(f"[PumpFunScraper] Found {len(migrating)} tokens nearing migration")
        
        return migrating
    
    def check_migration_status(self, token: TokenCandidate) -> bool:
        """
        Check if a token has migrated to Raydium.
        
        Args:
            token: TokenCandidate to check
            
        Returns:
            True if token has migrated
        """
        updated = self.get_token_details(token.mint_address)
        if updated:
            token.is_migrated = updated.is_migrated
            token.raydium_pool = updated.raydium_pool
            token.last_updated = datetime.now(timezone.utc)
            
            if token.is_migrated and not updated.is_migrated:
                self.stats['migrations_detected'] += 1
                logger.info(f"[PumpFunScraper] 🚀 Token migrated: {token.symbol}")
        
        return token.is_migrated
    
    def scan_for_arbitrage_opportunities(self) -> List[TokenCandidate]:
        """
        Scan for tokens with potential arbitrage opportunities.
        Focuses on:
        1. Newly created tokens (< 5 min old)
        2. Tokens nearing migration (high volatility)
        3. Recently migrated tokens (price discovery on Raydium)
        
        Returns:
            List of TokenCandidate sorted by priority
        """
        opportunities = []
        
        # Get new tokens
        new_tokens = self.get_new_tokens(limit=50)
        
        for token in new_tokens:
            # High priority: nearing migration
            if token.is_nearing_migration:
                token.priority = "HIGH"
                opportunities.append(token)
            # Medium priority: very new tokens
            elif token.age_minutes < 5:
                token.priority = "MEDIUM"
                opportunities.append(token)
            # Low priority: recently migrated
            elif token.is_migrated and token.age_minutes < 30:
                token.priority = "MEDIUM"
                opportunities.append(token)
        
        # Sort by priority and bonding curve progress
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        opportunities.sort(key=lambda x: (priority_order.get(x.priority, 3), -x.bonding_curve_progress))
        
        return opportunities
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics."""
        return {
            **self.stats,
            'cached_tokens': len(self.token_cache),
            'seen_tokens': len(self.seen_tokens),
        }
    
    def clear_cache(self, max_age_hours: int = 24):
        """
        Clear old tokens from cache.
        
        Args:
            max_age_hours: Remove tokens older than this
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        old_mints = [
            mint for mint, seen_time in self.seen_tokens.items()
            if seen_time < cutoff
        ]
        
        for mint in old_mints:
            del self.seen_tokens[mint]
            if mint in self.token_cache:
                del self.token_cache[mint]
        
        if old_mints:
            logger.info(f"[PumpFunScraper] Cleared {len(old_mints)} old tokens from cache")


# Convenience functions for direct usage
_scraper_instance: Optional[PumpFunScraper] = None


def get_scraper(config: Optional[PumpFunConfig] = None) -> PumpFunScraper:
    """Get global scraper instance."""
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = PumpFunScraper(config)
    return _scraper_instance


def discover_new_tokens(limit: int = 20) -> List[TokenCandidate]:
    """
    Quick function to discover new tokens.
    
    Args:
        limit: Maximum tokens to return
        
    Returns:
        List of TokenCandidate
    """
    scraper = get_scraper()
    return scraper.get_new_tokens(limit=limit)


def get_high_priority_tokens() -> List[TokenCandidate]:
    """
    Get tokens nearing migration (high arbitrage potential).
    
    Returns:
        List of high priority TokenCandidate
    """
    scraper = get_scraper()
    return scraper.get_migrating_tokens()


if __name__ == "__main__":
    # Test mode
    print("=" * 70)
    print("🎯 Pump.fun Scraper - Test Mode")
    print("=" * 70)
    
    scraper = PumpFunScraper()
    
    # Test 1: Fetch new tokens
    print("\n[Test 1] Fetching new tokens...")
    new_tokens = scraper.get_new_tokens(limit=10)
    print(f"  Found {len(new_tokens)} new tokens")
    
    for token in new_tokens[:5]:
        age_str = f"{token.age_minutes:.1f}m" if token.creation_time else "unknown"
        print(f"  • {token.symbol} ({token.name[:20]}...)")
        print(f"    MCap: ${token.usd_market_cap:,.0f} | Bonding: {token.bonding_curve_progress:.1f}% | Age: {age_str}")
        if token.is_nearing_migration:
            print(f"    ⚠️  NEARING MIGRATION!")
    
    # Test 2: Fetch trending tokens
    print("\n[Test 2] Fetching trending tokens...")
    trending = scraper.get_trending_tokens(limit=5)
    print(f"  Found {len(trending)} trending tokens")
    
    # Test 3: Get high priority tokens
    print("\n[Test 3] Scanning for migration opportunities...")
    migrating = scraper.get_migrating_tokens()
    print(f"  Found {len(migrating)} tokens nearing migration")
    
    # Test 4: Stats
    print("\n[Test 4] Scraper statistics:")
    stats = scraper.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Pump.fun scraper tests completed")
    print("=" * 70)
