"""
Polymarket Smart Money Module — Market Scanner
Discovers and tracks active markets from Polymarket.
"""
import requests
import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from config import config
from database import upsert_market, get_active_markets, log_scan

logger = logging.getLogger(__name__)


class MarketScanner:
    """Scans Polymarket for active markets and new listings."""
    
    def __init__(self):
        self.gamma_url = config.scanner.gamma_api_url
        self.clob_url = config.scanner.clob_api_url
        self.data_url = config.scanner.data_api_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PolymarketSmartMoney/1.0"
        })
    
    def fetch_markets(self, limit: int = None, active: bool = True, 
                      closed: bool = False) -> List[Dict]:
        """Fetch markets from Gamma API."""
        limit = limit or config.scanner.max_markets_per_scan
        markets = []
        offset = 0
        batch_size = 100
        
        while len(markets) < limit:
            try:
                resp = self.session.get(
                    f"{self.gamma_url}/markets",
                    params={
                        "active": str(active).lower(),
                        "closed": str(closed).lower(),
                        "limit": batch_size,
                        "offset": offset,
                        "order": "volume24hr",
                        "ascending": "false"
                    },
                    timeout=30
                )
                resp.raise_for_status()
                data = resp.json()
                
                if not data:
                    break
                
                for m in data:
                    market = self._parse_gamma_market(m)
                    if market:
                        markets.append(market)
                
                offset += batch_size
                if len(data) < batch_size:
                    break
                    
                time.sleep(0.5)  # rate limit courtesy
                
            except requests.RequestException as e:
                logger.error(f"Error fetching markets: {e}")
                break
        
        logger.info(f"Fetched {len(markets)} markets from Gamma API")
        return markets[:limit]
    
    def fetch_new_markets(self, hours: int = 24) -> List[Dict]:
        """Fetch markets created in the last N hours."""
        try:
            resp = self.session.get(
                f"{self.gamma_url}/markets",
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": 100,
                    "order": "createdAt",
                    "ascending": "false"
                },
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            
            cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
            new_markets = []
            
            for m in data:
                created = m.get("createdAt", m.get("created_at", ""))
                if created:
                    try:
                        ts = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                        if ts >= cutoff:
                            market = self._parse_gamma_market(m)
                            if market:
                                new_markets.append(market)
                    except (ValueError, TypeError):
                        continue
            
            logger.info(f"Found {len(new_markets)} new markets in last {hours}h")
            return new_markets
            
        except requests.RequestException as e:
            logger.error(f"Error fetching new markets: {e}")
            return []
    
    def fetch_market_trades(self, market_id: str, limit: int = 100) -> List[Dict]:
        """Fetch recent trades for a specific market from Data API."""
        try:
            resp = self.session.get(
                f"{self.data_url}/trades",
                params={
                    "market": market_id,
                    "limit": limit
                },
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching trades for {market_id}: {e}")
            return []
    
    def fetch_all_recent_trades(self, hours: int = 24) -> List[Dict]:
        """Fetch all recent trades across all markets."""
        try:
            resp = self.session.get(
                f"{self.data_url}/trades",
                params={
                    "limit": 1000,
                    "hours": hours
                },
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching recent trades: {e}")
            return []
    
    def scan_and_store(self) -> Dict[str, Any]:
        """Full scan: fetch markets and store in database."""
        start = time.time()
        
        # Fetch active markets
        markets = self.fetch_markets()
        stored = 0
        for m in markets:
            try:
                upsert_market(m)
                stored += 1
            except Exception as e:
                logger.warning(f"Error storing market {m.get('market_id')}: {e}")
        
        duration = time.time() - start
        log_scan("full", stored, 0, 0, duration)
        
        result = {
            "markets_found": len(markets),
            "markets_stored": stored,
            "duration_seconds": round(duration, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        logger.info(f"Scan complete: {result}")
        return result
    
    def _parse_gamma_market(self, raw: Dict) -> Optional[Dict]:
        """Parse a Gamma API market response into our schema."""
        try:
            market_id = raw.get("condition_id", raw.get("market_id", ""))
            if not market_id:
                return None
            
            # Parse outcome prices
            outcome_prices = []
            tokens = raw.get("tokens", [])
            for t in tokens:
                try:
                    outcome_prices.append(float(t.get("price", 0)))
                except (ValueError, TypeError):
                    outcome_prices.append(0.0)
            
            # Parse tags
            tags = raw.get("tags", [])
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except json.JSONDecodeError:
                    tags = [tags]
            
            return {
                "market_id": market_id,
                "question": raw.get("question", ""),
                "slug": raw.get("market_slug", ""),
                "volume": float(raw.get("volume", 0) or 0),
                "liquidity": float(raw.get("liquidityNum", raw.get("liquidity", 0)) or 0),
                "outcome_prices": outcome_prices,
                "created_at": raw.get("createdAt", raw.get("created_at", "")),
                "resolved": raw.get("closed", False),
                "outcome": raw.get("outcome", ""),
                "tags": tags
            }
        except Exception as e:
            logger.warning(f"Error parsing market: {e}")
            return None


# Convenience function
def run_scan() -> Dict[str, Any]:
    """Run a market scan and return results."""
    scanner = MarketScanner()
    return scanner.scan_and_store()
