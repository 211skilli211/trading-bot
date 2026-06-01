#!/usr/bin/env python3
"""
Agent Evolution System (ported from Fincept-Corporation/FinceptTerminal)
=========================================================================
Self-improving agents that learn from trading history.

Adapted from: fincept-qt/scripts/agno_trading/core/agent_evolution.py

Usage:
    from agent_evolution import AgentEvolution
    
    evo = AgentEvolution()
    should_evolve, reason = evo.should_evolve("agent_1", performance)
    if should_evolve:
        result = evo.evolve_agent("agent_1", "gpt-4o", instructions, reason)
"""

import json
import sys
import math
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from collections import Counter


class AgentEvolution:
    """
    Manages agent self-evolution through performance analysis.
    """

    def __init__(self):
        self.evolution_triggers = {
            'loss_streak': 3,
            'poor_win_rate': 0.40,
            'large_drawdown': 0.10,
            'consistent_wins': 5,
            'trades_milestone': 20
        }

    def should_evolve(self, agent_id: str, performance: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if agent should evolve based on performance.
        
        Returns:
            (should_evolve, trigger_reason)
        """
        if performance.get('consecutive_losses', 0) >= self.evolution_triggers['loss_streak']:
            return True, 'loss_streak'

        if performance.get('total_trades', 0) >= 10:
            win_rate = performance.get('win_rate', 100)
            if win_rate < self.evolution_triggers['poor_win_rate'] * 100:
                return True, 'poor_win_rate'

        if performance.get('current_drawdown', 0) >= self.evolution_triggers['large_drawdown']:
            return True, 'large_drawdown'

        if performance.get('total_trades', 0) > 0 and performance.get('total_trades', 0) % self.evolution_triggers['trades_milestone'] == 0:
            return True, 'trades_milestone'

        return False, None

    def analyze_patterns(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze trading patterns from history.
        
        Args:
            trades: List of trade dicts with keys: symbol, side, pnl, quantity, 
                    entry_price, exit_price, stop_loss, take_profit
                    
        Returns:
            Pattern analysis results
        """
        if not trades:
            return {'total_analyzed': 0, 'patterns': {}}

        winners = [t for t in trades if t.get('pnl', 0) > 0]
        losers = [t for t in trades if t.get('pnl', 0) < 0]

        analysis = {
            'total_analyzed': len(trades),
            'winners_count': len(winners),
            'losers_count': len(losers),
            'patterns': {}
        }

        # Best/worst symbols
        winning_symbols = Counter([t.get('symbol', 'unknown') for t in winners])
        losing_symbols = Counter([t.get('symbol', 'unknown') for t in losers])
        analysis['patterns']['best_symbols'] = [s for s, _ in winning_symbols.most_common(3)]
        analysis['patterns']['worst_symbols'] = [s for s, _ in losing_symbols.most_common(3)]

        # Best/worst sides
        winning_sides = Counter([t.get('side', 'buy') for t in winners])
        losing_sides = Counter([t.get('side', 'sell') for t in losers])
        analysis['patterns']['best_side'] = winning_sides.most_common(1)[0][0] if winning_sides else 'buy'
        analysis['patterns']['worst_side'] = losing_sides.most_common(1)[0][0] if losing_sides else None

        # Position sizing
        avg_win_size = sum(t.get('quantity', 0) * t.get('entry_price', 0) for t in winners) / len(winners) if winners else 0
        avg_loss_size = sum(t.get('quantity', 0) * t.get('entry_price', 0) for t in losers) / len(losers) if losers else 0

        analysis['patterns']['avg_winning_size'] = avg_win_size
        analysis['patterns']['avg_losing_size'] = avg_loss_size

        if avg_win_size < avg_loss_size * 0.75:
            analysis['patterns']['sizing_issue'] = 'winning_trades_too_small'
        elif avg_loss_size > avg_win_size * 1.5:
            analysis['patterns']['sizing_issue'] = 'losing_trades_too_large'
        else:
            analysis['patterns']['sizing_issue'] = None

        # SL hit rate
        trades_with_sl = [t for t in losers if t.get('stop_loss') is not None and t.get('exit_price')]
        if trades_with_sl:
            sl_hits = sum(1 for t in trades_with_sl 
                         if t['stop_loss'] and abs(t['exit_price'] - t['stop_loss']) / max(t['stop_loss'], 0.001) < 0.02)
            analysis['patterns']['stop_loss_hit_rate'] = sl_hits / len(losers) if losers else 0
        else:
            analysis['patterns']['stop_loss_hit_rate'] = 0

        # TP hit rate
        trades_with_tp = [t for t in winners if t.get('take_profit') is not None and t.get('exit_price')]
        if trades_with_tp:
            tp_hits = sum(1 for t in trades_with_tp
                         if t['take_profit'] and abs(t['exit_price'] - t['take_profit']) / max(t['take_profit'], 0.001) < 0.02)
            analysis['patterns']['take_profit_hit_rate'] = tp_hits / len(winners) if winners else 0
        else:
            analysis['patterns']['take_profit_hit_rate'] = 0

        return analysis

    def generate_new_instructions(
        self,
        current_instructions: List[str],
        patterns: Dict[str, Any],
        trigger: str
    ) -> List[str]:
        """
        Generate improved instructions based on analyzed patterns.
        """
        new_instructions = current_instructions.copy()
        learning_instructions = []

        if patterns.get('best_symbols'):
            learning_instructions.append(
                f"LEARNED: Better win rates with {', '.join(patterns['best_symbols'][:2])}. Favor these."
            )
        if patterns.get('worst_symbols'):
            learning_instructions.append(
                f"LEARNED: Poor performance with {', '.join(patterns['worst_symbols'][:2])}. Be cautious."
            )
        if patterns.get('best_side') and patterns.get('worst_side'):
            if patterns['best_side'] != patterns['worst_side']:
                learning_instructions.append(
                    f"LEARNED: {patterns['best_side'].upper()} trades outperform {patterns['worst_side'].upper()}."
                )

        sizing_issue = patterns.get('sizing_issue')
        if sizing_issue == 'winning_trades_too_small':
            learning_instructions.append("LEARNED: Winning trades are too small. Increase size on high-confidence setups.")
        elif sizing_issue == 'losing_trades_too_large':
            learning_instructions.append("LEARNED: Losing trades too large. Reduce position sizing.")

        sl_hit = patterns.get('stop_loss_hit_rate', 0)
        if sl_hit > 0.7:
            learning_instructions.append("LEARNED: Stop losses hit too often (70%+). Widen stops or improve entry timing.")
        elif sl_hit > 0 and sl_hit < 0.3:
            learning_instructions.append("LEARNED: Stop losses rarely hit. Risk management working well.")

        tp_hit = patterns.get('take_profit_hit_rate', 0)
        if tp_hit > 0.7:
            learning_instructions.append("LEARNED: Take profits hit consistently. Consider wider targets.")
        elif tp_hit > 0 and tp_hit < 0.3:
            learning_instructions.append("LEARNED: Take profits rarely hit. Consider trailing stops.")

        if trigger == 'loss_streak':
            learning_instructions.append("CAUTION: Losing streak active. Reduce position sizes 50% until 2 consecutive wins.")
        elif trigger == 'poor_win_rate':
            learning_instructions.append("STRATEGY SHIFT: Win rate below 40%. Focus on HIGH PROBABILITY setups only.")
        elif trigger == 'large_drawdown':
            learning_instructions.append("RISK ALERT: Drawdown over 10%. Review strategy before resuming.")

        return learning_instructions + new_instructions

    def evolve_agent(
        self,
        agent_id: str,
        current_instructions: List[str],
        trades: List[Dict[str, Any]],
        trigger: str
    ) -> Dict[str, Any]:
        """
        Evolve an agent based on performance.
        """
        try:
            patterns = self.analyze_patterns(trades)
            new_instructions = self.generate_new_instructions(
                current_instructions, patterns['patterns'], trigger
            )

            return {
                'success': True,
                'agent_id': agent_id,
                'trigger': trigger,
                'old_instructions': current_instructions,
                'new_instructions': new_instructions,
                'patterns': patterns,
                'timestamp': int(datetime.now().timestamp())
            }
        except Exception as e:
            print(f"[Evolution] Error: {e}", file=sys.stderr)
            return {'success': False, 'error': str(e)}


# Singleton
_agent_evolution = None

def get_agent_evolution() -> AgentEvolution:
    """Get singleton agent evolution system."""
    global _agent_evolution
    if _agent_evolution is None:
        _agent_evolution = AgentEvolution()
    return _agent_evolution
