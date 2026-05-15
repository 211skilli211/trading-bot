"""
Polymarket Smart Money Module — Smart Money Scoring Engine
Scores wallets based on whale activity, win rate, and early positioning.
"""
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from config import config
from database import (
    get_db, get_smart_wallets, get_active_markets, get_wallet_trades,
    insert_signal, upsert_wallet
)

logger = logging.getLogger(__name__)


class SmartMoneyScorer:
    """Scores wallets and generates smart money signals."""
    
    def __init__(self):
        self.whale_min_trade = config.smart_money.whale_min_trade_size
        self.whale_min_volume = config.smart_money.whale_min_total_volume
        self.win_rate_min_trades = config.smart_money.win_rate_min_trades
        self.win_rate_threshold = config.smart_money.win_rate_threshold
        self.early_bird_max_age = config.smart_money.early_bird_max_age_hours
        self.early_bird_min_trade = config.smart_money.early_bird_min_trade_size
    
    def score_all_wallets(self) -> List[Dict]:
        """Score all tracked wallets and return ranked list."""
        conn = get_db()
        wallets = conn.execute("SELECT * FROM wallets WHERE total_trades >= 3").fetchall()
        conn.close()
        
        scored = []
        for w in wallets:
            wallet = dict(w)
            score, strategies = self._calculate_score(wallet)
            wallet["smart_money_score"] = score
            wallet["strategies"] = strategies
            wallet["is_smart"] = 1 if score >= 50 else 0
            scored.append(wallet)
            
            # Update wallet score in DB
            conn = get_db()
            conn.execute("""
                UPDATE wallets SET smart_money_score = ?, is_smart = ?, strategy = ?
                WHERE address = ?
            """, (score, wallet["is_smart"], ",".join(strategies), wallet["address"]))
            conn.commit()
            conn.close()
        
        scored.sort(key=lambda x: x["smart_money_score"], reverse=True)
        return scored
    
    def generate_signals(self) -> List[Dict]:
        """Generate smart money signals from recent activity."""
        signals = []
        
        # Get smart wallets
        smart_wallets = get_smart_wallets(min_score=50, limit=100)
        
        for wallet in smart_wallets:
            addr = wallet["address"]
            recent_trades = get_wallet_trades(addr, limit=20)
            
            for trade in recent_trades:
                # Check if this trade is a signal
                signal = self._evaluate_trade_signal(wallet, trade)
                if signal:
                    signal_id = insert_signal(
                        wallet_address=addr,
                        market_id=trade["market_id"],
                        strategy=signal["strategy"],
                        score=signal["score"],
                        details=signal["details"],
                        market_question=trade.get("market_question", "")
                    )
                    signal["id"] = signal_id
                    signals.append(signal)
        
        logger.info(f"Generated {len(signals)} smart money signals")
        return signals
    
    def _calculate_score(self, wallet: Dict) -> tuple:
        """Calculate composite smart money score (0-100)."""
        scores = {}
        
        # Whale score (0-100)
        volume = wallet.get("total_volume", 0)
        avg_trade = wallet.get("avg_trade_size", 0)
        if volume >= self.whale_min_volume:
            scores["whale"] = min(100, (volume / self.whale_min_volume) * 50)
        elif avg_trade >= self.whale_min_trade:
            scores["whale"] = min(60, (avg_trade / self.whale_min_trade) * 30)
        else:
            scores["whale"] = 0
        
        # Win rate score (0-100)
        total_trades = wallet.get("total_trades", 0)
        win_rate = wallet.get("win_rate", 0)
        if total_trades >= self.win_rate_min_trades and win_rate >= self.win_rate_threshold:
            scores["win_rate"] = min(100, (win_rate / self.win_rate_threshold) * 70)
        elif total_trades >= 10 and win_rate >= 0.6:
            scores["win_rate"] = 40
        else:
            scores["win_rate"] = 0
        
        # Early bird score (0-100) — based on trade patterns
        # This is calculated per-trade in _evaluate_trade_signal
        scores["early_bird"] = self._estimate_early_bird_score(wallet)
        
        # Weighted composite
        composite = (
            scores["whale"] * config.smart_money.weight_whale +
            scores["win_rate"] * config.smart_money.weight_win_rate +
            scores["early_bird"] * config.smart_money.weight_early_bird
        )
        
        strategies = [k for k, v in scores.items() if v > 30]
        if not strategies:
            strategies = ["none"]
        
        return round(composite, 2), strategies
    
    def _estimate_early_bird_score(self, wallet: Dict) -> float:
        """Estimate early bird tendency from wallet's trade history."""
        trades = get_wallet_trades(wallet["address"], limit=50)
        if not trades:
            return 0
        
        early_count = 0
        for trade in trades:
            # Check if trade was early in market's life
            # This is a heuristic — we'd need market creation time for accuracy
            timestamp = trade.get("timestamp", "")
            if timestamp:
                try:
                    trade_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    # If we can determine market age at time of trade, score it
                    # For now, use a simple heuristic
                    early_count += 1
                except (ValueError, TypeError):
                    continue
        
        if early_count > 10:
            return 60
        elif early_count > 5:
            return 30
        return 0
    
    def _evaluate_trade_signal(self, wallet: Dict, trade: Dict) -> Optional[Dict]:
        """Evaluate if a specific trade is a smart money signal."""
        signals = []
        usd_value = trade.get("usd_value", 0)
        
        # Whale signal
        if usd_value >= self.whale_min_trade:
            signals.append({
                "strategy": "whale",
                "score": min(100, (usd_value / self.whale_min_trade) * 50),
                "details": {
                    "trade_value": usd_value,
                    "threshold": self.whale_min_trade,
                    "side": trade.get("side"),
                    "outcome": trade.get("outcome"),
                    "price": trade.get("price")
                }
            })
        
        # Win rate signal
        if (wallet.get("win_rate", 0) >= self.win_rate_threshold and 
            wallet.get("total_trades", 0) >= self.win_rate_min_trades):
            signals.append({
                "strategy": "win_rate",
                "score": min(100, (wallet["win_rate"] / self.win_rate_threshold) * 70),
                "details": {
                    "wallet_win_rate": wallet["win_rate"],
                    "wallet_total_trades": wallet["total_trades"],
                    "side": trade.get("side"),
                    "outcome": trade.get("outcome")
                }
            })
        
        # Early bird signal
        market_id = trade.get("market_id", "")
        if market_id:
            market_age_hours = self._get_market_age_hours(market_id)
            if market_age_hours is not None and market_age_hours <= self.early_bird_max_age:
                if usd_value >= self.early_bird_min_trade:
                    signals.append({
                        "strategy": "early_bird",
                        "score": min(100, (1 - market_age_hours / self.early_bird_max_age) * 80),
                        "details": {
                            "market_age_hours": market_age_hours,
                            "trade_value": usd_value,
                            "side": trade.get("side"),
                            "outcome": trade.get("outcome")
                        }
                    })
        
        # Return highest scoring signal
        if signals:
            return max(signals, key=lambda x: x["score"])
        return None
    
    def _get_market_age_hours(self, market_id: str) -> Optional[float]:
        """Get market age in hours."""
        conn = get_db()
        row = conn.execute(
            "SELECT created_at FROM markets WHERE market_id = ?", (market_id,)
        ).fetchone()
        conn.close()
        
        if row and row["created_at"]:
            try:
                created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                return (now - created).total_seconds() / 3600
            except (ValueError, TypeError):
                pass
        return None
    
    def get_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Get top smart money wallets."""
        scored = self.score_all_wallets()
        return scored[:limit]


def run_scoring() -> Dict[str, Any]:
    """Run smart money scoring and generate signals."""
    scorer = SmartMoneyScorer()
    
    # Score all wallets
    leaderboard = scorer.get_leaderboard()
    
    # Generate signals
    signals = scorer.generate_signals()
    
    return {
        "wallets_scored": len(leaderboard),
        "signals_generated": len(signals),
        "top_wallets": leaderboard[:5],
        "top_signals": signals[:5]
    }
