#!/usr/bin/env python3
"""
Confidence Scorer (ported from Fincept-Corporation/FinceptTerminal)
====================================================================
Calculate 0-1 confidence scores for trading signals.

Adapted from: fincept-qt/scripts/agno_trading/utils/confidence_scorer.py

Usage:
    from confidence_scorer import ConfidenceScorer
    
    result = ConfidenceScorer.calculate_comprehensive_confidence(
        indicator_alignment=0.8,
        trend_strength=0.7,
        volume_confirmation=0.6,
        risk_reward_ratio=2.5
    )
    print(result['confidence'], result['rating'])
"""

from typing import Dict, Optional


class ConfidenceScorer:
    """Calculate confidence scores (0.0 to 1.0) for trading signals."""

    @staticmethod
    def calculate(
        indicator_alignment: float = 0.5,
        trend_strength: float = 0.5,
        volume_confirmation: float = 0.5,
        risk_reward_ratio: float = 2.0,
        volatility_factor: float = 0.5,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """Calculate overall confidence score."""
        if weights is None:
            weights = {
                'indicators': 0.30,
                'trend': 0.25,
                'volume': 0.20,
                'risk_reward': 0.15,
                'volatility': 0.10
            }

        rr_normalized = min(risk_reward_ratio / 3.0, 1.0)
        volatility_score = 1.0 - volatility_factor

        confidence = (
            indicator_alignment * weights['indicators'] +
            trend_strength * weights['trend'] +
            volume_confirmation * weights['volume'] +
            rr_normalized * weights['risk_reward'] +
            volatility_score * weights['volatility']
        )
        confidence = max(0.0, min(1.0, confidence))

        return {
            "confidence": round(confidence, 3),
            "breakdown": {
                "indicator_alignment": round(indicator_alignment, 2),
                "trend_strength": round(trend_strength, 2),
                "volume_confirmation": round(volume_confirmation, 2),
                "risk_reward_score": round(rr_normalized, 2),
                "volatility_score": round(volatility_score, 2)
            },
            "rating": ConfidenceScorer._rating(confidence)
        }

    @staticmethod
    def indicator_alignment(indicators: Dict[str, str]) -> float:
        """How many indicators agree (0-1)."""
        if not indicators:
            return 0.5
        signals = list(indicators.values())
        buy_count = sum(1 for s in signals if s in ('buy', 'bullish'))
        sell_count = sum(1 for s in signals if s in ('sell', 'bearish'))
        return max(buy_count, sell_count) / len(signals) if signals else 0.5

    @staticmethod
    def trend_strength(price: float, ma_20: float, ma_50: float, ma_200: Optional[float] = None) -> float:
        """Trend strength from moving average alignment (0-1)."""
        if price > ma_20 > ma_50:
            score = 0.6
        elif price < ma_20 < ma_50:
            score = 0.6
        else:
            score = 0.3

        if ma_200:
            if (price > ma_20 > ma_50 > ma_200) or (price < ma_20 < ma_50 < ma_200):
                score = 1.0
        return score

    @staticmethod
    def volume_confirmation(current_vol: float, avg_vol: float, threshold: float = 1.2) -> float:
        """Volume confirmation score (0-1)."""
        if avg_vol == 0:
            return 0.5
        ratio = current_vol / avg_vol
        if ratio >= threshold:
            return min(ratio / 2.0, 1.0)
        return 0.3

    @staticmethod
    def adjust_for_market(base: float, condition: str) -> float:
        """Adjust confidence based on market conditions."""
        multipliers = {
            'trending': 1.1, 'ranging': 0.9,
            'volatile': 0.85, 'calm': 1.0,
        }
        return max(0.0, min(1.0, base * multipliers.get(condition, 1.0)))

    @staticmethod
    def recommend(confidence: float, min_threshold: float = 0.6) -> str:
        """Recommend action based on confidence."""
        if confidence >= 0.8:
            return "STRONG_EXECUTE"
        elif confidence >= 0.7:
            return "EXECUTE"
        elif confidence >= min_threshold:
            return "EXECUTE_WITH_CAUTION"
        return "SKIP"

    @staticmethod
    def _rating(confidence: float) -> str:
        if confidence >= 0.8: return "Very High"
        elif confidence >= 0.7: return "High"
        elif confidence >= 0.6: return "Medium"
        elif confidence >= 0.5: return "Low"
        return "Very Low"
