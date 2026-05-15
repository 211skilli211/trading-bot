"""
Polymarket Smart Money Module — Wallet Tracker
Monitors wallet activity and builds profiles for smart money detection.
"""
import requests
import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict

from config import config
from database import (
    get_db, upsert_wallet, insert_trade, get_wallet_trades,
    get_smart_wallets, get_active_markets, log_scan
)

logger = logging.getLogger(__name__)


class WalletTracker:
    """Tracks wallet activity on Polymarket."""
    
    def __init__(self):
        self.data_url = config.scanner.data_api_url
        self.gamma_url = config.scanner.gamma_api_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PolymarketSmartMoney/1.0"
        })
    
    def fetch_trades_for_market(self, market_id: str, limit: int = 500) -> List[Dict]:
        """Fetch all trades for a specific market."""
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
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
        except requests.RequestException as e:
            logger.error(f"Error fetching trades for market {market_id}: {e}")
            return []
    
    def fetch_all_trades(self, limit: int = 1000) -> List[Dict]:
        """Fetch recent trades across all markets."""
        try:
            resp = self.session.get(
                f"{self.data_url}/trades",
                params={"limit": limit},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
        except requests.RequestException as e:
            logger.error(f"Error fetching all trades: {e}")
            return []
    
    def fetch_wallet_history(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        """Fetch trade history for a specific wallet."""
        try:
            resp = self.session.get(
                f"{self.data_url}/trades",
                params={
                    "maker": wallet_address,
                    "limit": limit
                },
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
        except requests.RequestException as e:
            logger.error(f"Error fetching wallet history for {wallet_address}: {e}")
            return []
    
    def track_wallets_from_trades(self, trades: List[Dict]) -> Dict[str, Dict]:
        """Process trades and build wallet profiles."""
        wallets = defaultdict(lambda: {
            "trades": [],
            "total_volume": 0.0,
            "total_trades": 0,
            "markets": set(),
            "first_seen": None,
            "last_seen": None
        })
        
        for trade in trades:
            # Get wallet address (maker or taker)
            wallet = trade.get("maker", trade.get("taker", ""))
            if not wallet:
                continue
            
            # Parse trade data
            side = trade.get("side", "BUY")
            outcome = trade.get("outcome", "YES")
            price = float(trade.get("price", 0) or 0)
            size = float(trade.get("size", 0) or 0)
            usd_value = price * size
            timestamp = trade.get("timestamp", trade.get("created_at", ""))
            market_id = trade.get("market", trade.get("condition_id", ""))
            market_question = trade.get("question", "")
            tx_hash = trade.get("tx_hash", trade.get("transactionHash", ""))
            
            # Update wallet profile
            w = wallets[wallet]
            w["trades"].append(trade)
            w["total_volume"] += usd_value
            w["total_trades"] += 1
            w["markets"].add(market_id)
            
            if timestamp:
                if not w["first_seen"] or timestamp < w["first_seen"]:
                    w["first_seen"] = timestamp
                if not w["last_seen"] or timestamp > w["last_seen"]:
                    w["last_seen"] = timestamp
            
            # Store individual trade
            try:
                insert_trade(
                    wallet_address=wallet,
                    market_id=market_id,
                    side=side,
                    outcome=outcome,
                    price=price,
                    size=size,
                    usd_value=usd_value,
                    market_question=market_question,
                    tx_hash=tx_hash
                )
            except Exception as e:
                logger.warning(f"Error storing trade: {e}")
        
        return dict(wallets)
    
    def scan_high_volume_markets(self) -> Dict[str, Any]:
        """Scan high-volume markets for wallet activity."""
        start = time.time()
        
        # Get active markets with volume
        markets = get_active_markets(min_volume=config.scanner.min_volume_usd, limit=50)
        logger.info(f"Scanning {len(markets)} high-volume markets for wallet activity")
        
        all_wallets = {}
        total_trades = 0
        
        for market in markets:
            market_id = market["market_id"]
            trades = self.fetch_trades_for_market(market_id)
            
            if trades:
                wallets = self.track_wallets_from_trades(trades)
                for addr, profile in wallets.items():
                    if addr in all_wallets:
                        all_wallets[addr]["trades"].extend(profile["trades"])
                        all_wallets[addr]["total_volume"] += profile["total_volume"]
                        all_wallets[addr]["total_trades"] += profile["total_trades"]
                        all_wallets[addr]["markets"].update(profile["markets"])
                    else:
                        all_wallets[addr] = profile
                total_trades += len(trades)
            
            time.sleep(0.3)  # rate limit
        
        # Update wallet records in DB
        smart_count = 0
        for addr, profile in all_wallets.items():
            try:
                upsert_wallet(addr, {
                    "usd_value": profile["total_volume"],
                    "won": False  # will be updated by smart_money.py
                })
                if profile["total_volume"] >= config.smart_money.whale_min_total_volume:
                    smart_count += 1
            except Exception as e:
                logger.warning(f"Error updating wallet {addr}: {e}")
        
        duration = time.time() - start
        log_scan("wallet_scan", len(markets), len(all_wallets), 0, duration)
        
        result = {
            "markets_scanned": len(markets),
            "total_trades": total_trades,
            "unique_wallets": len(all_wallets),
            "smart_wallets": smart_count,
            "duration_seconds": round(duration, 2)
        }
        logger.info(f"Wallet scan complete: {result}")
        return result
    
    def get_wallet_profile(self, wallet_address: str) -> Optional[Dict]:
        """Get full profile for a wallet."""
        trades = get_wallet_trades(wallet_address, limit=1000)
        if not trades:
            return None
        
        total_volume = sum(t["usd_value"] for t in trades)
        markets = set(t["market_id"] for t in trades)
        
        return {
            "address": wallet_address,
            "total_trades": len(trades),
            "total_volume": total_volume,
            "avg_trade_size": total_volume / len(trades) if trades else 0,
            "markets_traded": len(markets),
            "first_trade": trades[-1]["timestamp"] if trades else None,
            "last_trade": trades[0]["timestamp"] if trades else None,
            "recent_trades": trades[:10]
        }
    
    def discover_smart_wallets(self) -> List[Dict]:
        """Discover potential smart money wallets from recent activity."""
        trades = self.fetch_all_trades(limit=1000)
        wallets = self.track_wallets_from_trades(trades)
        
        candidates = []
        for addr, profile in wallets.items():
            # Filter by minimum activity
            if profile["total_trades"] < 3:
                continue
            if profile["total_volume"] < config.smart_money.whale_min_total_volume:
                continue
            
            candidates.append({
                "address": addr,
                "total_trades": profile["total_trades"],
                "total_volume": profile["total_volume"],
                "avg_trade_size": profile["total_volume"] / profile["total_trades"],
                "markets_count": len(profile["markets"]),
                "first_seen": profile["first_seen"],
                "last_seen": profile["last_seen"]
            })
        
        # Sort by volume
        candidates.sort(key=lambda x: x["total_volume"], reverse=True)
        logger.info(f"Discovered {len(candidates)} smart money candidates")
        return candidates


def run_wallet_scan() -> Dict[str, Any]:
    """Run a wallet tracking scan."""
    tracker = WalletTracker()
    return tracker.scan_high_volume_markets()
