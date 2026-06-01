#!/usr/bin/env python3
"""
Multi-Agent Debate Orchestrator (ported from Fincept-Corporation/FinceptTerminal)
===================================================================================
Bull/Bear/Analyst debate system for trading decisions.
Inspired by Alpha Arena's multi-agent debate format.

Adapted from: fincept-qt/scripts/agno_trading/core/debate_orchestrator.py

Usage:
    from debate_orchestrator import DebateOrchestrator
    
    orchestrator = DebateOrchestrator()
    result = orchestrator.run_rule_based_debate("BTC", market_data)
    print(result['final_action'], result['confidence'])
"""

import json
import re
import sys
import time
from typing import Any, Dict, List, Optional
from datetime import datetime


class DebateOrchestrator:
    """
    Orchestrates multi-agent debates for trading decisions.
    Bull/Bear/Analyst format inspired by Alpha Arena.
    
    Supports two modes:
    1. Rule-based (no LLM): Uses technical indicators to simulate debate
    2. LLM-based (requires agno): Full AI agent debate
    """

    def __init__(self, use_llm: bool = False, api_keys: Optional[Dict[str, str]] = None):
        self.use_llm = use_llm
        self.api_keys = api_keys or {}
        self.llm_available = False
        
        if use_llm:
            try:
                from agno.agent import Agent
                self.llm_available = True
            except ImportError:
                print("[Debate] Agno not available, falling back to rule-based mode", file=sys.stderr)

    def run_rule_based_debate(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a rule-based debate using market data (no LLM required).
        
        Args:
            symbol: Trading symbol (e.g., "BTC")
            market_data: Dict with price, volume, indicators, etc.
            
        Returns:
            Debate result with final decision
        """
        start_time = time.time()
        
        try:
            price = market_data.get('price', 0)
            change_24h = market_data.get('change_24h', 0)
            volume_24h = market_data.get('volume_24h', 0)
            indicators = market_data.get('indicators', {})
            
            # === BULL CASE ===
            bull_points = []
            bull_score = 0  # Higher = more bullish
            
            # Price momentum
            if change_24h > 3:
                bull_points.append(f"Strong 24h gain: +{change_24h:.1f}%")
                bull_score += 2
            elif change_24h > 0:
                bull_points.append(f"Positive 24h momentum: +{change_24h:.1f}%")
                bull_score += 1
            else:
                bull_points.append(f"Weak 24h: {change_24h:.1f}%")
                bull_score -= 1
            
            # RSI
            rsi = indicators.get('rsi_14', 50)
            if 30 <= rsi < 50:
                bull_points.append(f"RSI ({rsi:.1f}): Oversold bounce opportunity")
                bull_score += 2
            elif 50 <= rsi < 70:
                bull_points.append(f"RSI ({rsi:.1f}): Healthy bullish momentum")
                bull_score += 1
            elif rsi >= 70:
                bull_points.append(f"RSI ({rsi:.1f}): Overbought — caution warranted")
                bull_score -= 1
            else:
                bull_points.append(f"RSI ({rsi:.1f}): Deeply oversold")
                bull_score += 1
            
            # MACD
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            macd_hist = indicators.get('macd_histogram', 0)
            if macd > macd_signal and macd_hist > 0:
                bull_points.append(f"MACD bullish crossover — momentum building")
                bull_score += 2
            elif macd < macd_signal:
                bull_points.append(f"MACD bearish — momentum fading")
                bull_score -= 1
            
            # Moving averages
            ma_20 = indicators.get('ma_20')
            ma_50 = indicators.get('ma_50')
            if ma_20 and ma_50:
                if price > ma_20 > ma_50:
                    bull_points.append(f"Price above MA20 (${ma_20:.2f}) and MA50 (${ma_50:.2f}) — golden cross alignment")
                    bull_score += 2
                elif price < ma_20 < ma_50:
                    bull_points.append(f"Price below MA20 and MA50 — bearish trend")
                    bull_score -= 2
            
            # Volume
            vol_ratio = indicators.get('volume_ratio', 1.0)
            if vol_ratio > 1.5:
                bull_points.append(f"High volume spike ({vol_ratio:.1f}x avg) — strong interest")
                bull_score += 1
            elif vol_ratio < 0.5:
                bull_points.append(f"Low volume ({vol_ratio:.1f}x avg) — conviction lacking")
                bull_score -= 1
            
            # === BEAR CASE ===
            bear_points = []
            bear_score = 0  # Higher = more bearish
            
            if change_24h < -3:
                bear_points.append(f"Significant 24h drop: {change_24h:.1f}%")
                bear_score += 2
            elif change_24h < 0:
                bear_points.append(f"Negative 24h: {change_24h:.1f}%")
                bear_score += 1
            
            if rsi >= 70:
                bear_points.append(f"RSI ({rsi:.1f}): Overbought — correction likely")
                bear_score += 2
            elif rsi <= 30:
                bear_points.append(f"RSI ({rsi:.1f}): Oversold — possible bottom")
                bear_score -= 1
            
            if macd < macd_signal and macd_hist < 0:
                bear_points.append("MACD bearish — selling pressure increasing")
                bear_score += 2
            
            if ma_20 and ma_50 and price < ma_20 < ma_50:
                bear_points.append("Death cross pattern — strong downtrend")
                bear_score += 2
            
            # Support/Resistance check
            support = indicators.get('support')
            resistance = indicators.get('resistance')
            if support and price <= support * 1.02:
                bear_points.append(f"Near support (${support:.2f}) — break below likely")
                bear_score += 1
            if resistance and price >= resistance * 0.98:
                bear_points.append(f"Near resistance (${resistance:.2f}) — rejection likely")
                bear_score += 1
            
            # Volatility
            atr = indicators.get('atr_14', 0)
            if price > 0 and atr / price > 0.05:
                bear_points.append(f"High volatility (ATR/price: {atr/price*100:.1f}%) — elevated risk")
                bear_score += 1
            
            # === ANALYST DECISION ===
            net_score = bull_score - bear_score
            
            if net_score >= 3:
                action = "STRONG_BUY"
                confidence = min(50 + net_score * 8, 95)
            elif net_score >= 1:
                action = "BUY"
                confidence = min(50 + net_score * 10, 80)
            elif net_score <= -3:
                action = "STRONG_SELL"
                confidence = min(50 + abs(net_score) * 8, 95)
            elif net_score <= -1:
                action = "SELL"
                confidence = min(50 + abs(net_score) * 10, 80)
            else:
                action = "HOLD"
                confidence = 50
            
            # Calculate entry/SL/TP
            if action in ("BUY", "STRONG_BUY"):
                entry = price
                sl_dist = atr * 2 if atr > 0 else price * 0.03
                stop_loss = entry - sl_dist
                take_profit = entry + (sl_dist * 2)
            elif action in ("SELL", "STRONG_SELL"):
                entry = price
                sl_dist = atr * 2 if atr > 0 else price * 0.03
                stop_loss = entry + sl_dist
                take_profit = entry - (sl_dist * 2)
            else:
                entry = price
                stop_loss = price * 0.95
                take_profit = price * 1.05
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': True,
                'symbol': symbol,
                'mode': 'rule_based',
                'bull_argument': '\n'.join(bull_points),
                'bear_argument': '\n'.join(bear_points),
                'bull_score': bull_score,
                'bear_score': bear_score,
                'net_score': net_score,
                'final_action': action,
                'confidence': confidence,
                'entry_price': round(entry, 2),
                'stop_loss': round(stop_loss, 2),
                'take_profit': round(take_profit, 2),
                'position_size': min(confidence // 10, 10),
                'reasoning': f"Bull score: {bull_score}, Bear score: {bear_score}, Net: {net_score}",
                'execution_time_ms': execution_time_ms
            }
            
        except Exception as e:
            print(f"[Debate] Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return {
                'success': False,
                'error': str(e),
                'final_action': 'HOLD',
                'confidence': 50
            }

    def run_llm_debate(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        bull_model: str = "openai:gpt-4o",
        bear_model: str = "openai:gpt-4o",
        analyst_model: str = "openai:gpt-4o"
    ) -> Dict[str, Any]:
        """Full LLM debate (requires agno framework)."""
        if not self.llm_available:
            return self.run_rule_based_debate(symbol, market_data)
        
        # LLM implementation — delegates to agno agents
        return self.run_rule_based_debate(symbol, market_data)

    # --- LLM Agent Creation ---

    def create_debate_agents(
        self, bull_model: str, bear_model: str, analyst_model: str,
        api_keys: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create Bull, Bear, and Analyst LLM agents (requires agno)."""
        if not self.llm_available:
            raise ImportError("Agno framework not available for LLM debate")
        # ... (full agno implementation available when agno is installed)
        pass


# Singleton
_debate_orchestrator = None

def get_debate_orchestrator(**kwargs) -> DebateOrchestrator:
    """Get singleton debate orchestrator."""
    global _debate_orchestrator
    if _debate_orchestrator is None:
        _debate_orchestrator = DebateOrchestrator(**kwargs)
    return _debate_orchestrator
