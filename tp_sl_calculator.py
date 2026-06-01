#!/usr/bin/env python3
"""
TP/SL Calculator (ported from Fincept-Corporation/FinceptTerminal)
====================================================================
Dynamic Take Profit and Stop Loss calculation based on volatility.

Adapted from: fincept-qt/scripts/agno_trading/utils/tp_sl_calculator.py

Usage:
    from tp_sl_calculator import TPSLCalculator
    
    result = TPSLCalculator.calculate_dynamic_tp_sl(
        entry_price=50000, direction='long', volatility=1500
    )
    print(result)
"""

from typing import Dict, List


class TPSLCalculator:
    """Calculate dynamic TP/SL levels."""

    @staticmethod
    def calculate_dynamic_tp_sl(
        entry_price: float,
        direction: str,
        volatility: float,
        risk_reward_ratio: float = 2.0,
        atr_multiplier: float = 2.0
    ) -> Dict:
        sl_distance = volatility * atr_multiplier
        if direction.lower() == 'long':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * risk_reward_ratio)
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * risk_reward_ratio)

        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "sl_distance": round(sl_distance, 2),
            "tp_distance": round(sl_distance * risk_reward_ratio, 2),
            "risk_reward_ratio": risk_reward_ratio
        }

    @staticmethod
    def calculate_from_percentage(
        entry_price: float,
        direction: str,
        sl_percent: float = 2.0,
        tp_percent: float = 5.0
    ) -> Dict:
        sl_amount = entry_price * (sl_percent / 100)
        tp_amount = entry_price * (tp_percent / 100)

        if direction.lower() == 'long':
            stop_loss = entry_price - sl_amount
            take_profit = entry_price + tp_amount
        else:
            stop_loss = entry_price + sl_amount
            take_profit = entry_price - tp_amount

        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "sl_percent": sl_percent,
            "tp_percent": tp_percent,
            "risk_reward_ratio": tp_percent / sl_percent if sl_percent > 0 else 0
        }

    @staticmethod
    def trailing_stop(
        entry_price: float,
        current_price: float,
        direction: str,
        trail_percent: float = 1.0
    ) -> float:
        if direction.lower() == 'long':
            trailing = current_price * (1 - trail_percent / 100)
            original = entry_price * (1 - trail_percent / 100)
            return max(trailing, original)
        else:
            trailing = current_price * (1 + trail_percent / 100)
            original = entry_price * (1 + trail_percent / 100)
            return min(trailing, original)

    @staticmethod
    def estimate_volatility(prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return prices[-1] * 0.02 if prices else 0

        ranges = []
        for i in range(max(0, len(prices) - period), len(prices)):
            if i > 0:
                ranges.append(abs(prices[i] - prices[i - 1]))
        return sum(ranges) / len(ranges) if ranges else 0

    @staticmethod
    def validate(
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
        min_rr: float = 1.5
    ) -> Dict:
        errors = []
        warnings = []

        if direction.lower() == 'long':
            if stop_loss >= entry_price:
                errors.append("SL must be below entry for long")
            if take_profit <= entry_price:
                errors.append("TP must be above entry for long")
            if stop_loss < entry_price and take_profit > entry_price:
                rr = (take_profit - entry_price) / max(entry_price - stop_loss, 0.001)
                if rr < min_rr:
                    warnings.append(f"R:R {rr:.2f} below minimum {min_rr}")
        else:
            if stop_loss <= entry_price:
                errors.append("SL must be above entry for short")
            if take_profit >= entry_price:
                errors.append("TP must be below entry for short")
            if stop_loss > entry_price and take_profit < entry_price:
                rr = (entry_price - take_profit) / max(stop_loss - entry_price, 0.001)
                if rr < min_rr:
                    warnings.append(f"R:R {rr:.2f} below minimum {min_rr}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
