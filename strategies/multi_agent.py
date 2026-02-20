#!/usr/bin/env python3
"""
Multi-Agent Trading System
=========================
Orchestrates multiple trading agents with performance-based evolution.

Features:
- Run 6 trading agents in parallel
- Monitor performance daily
- Kill bottom 20% after 3 consecutive losses
- Replace with new agents
- Scale top 20% with increased capital
"""

import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class Agent:
    """Trading agent with strategy"""
    name: str
    strategy_type: str
    capital: float
    risk_level: str  # low, medium, high, very_high
    status: str = "active"  # active, paused, killed
    consecutive_losses: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0
    kill_threshold: int = 3
    max_position_pct: float = 0.10
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_eval: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    def to_dict(self) -> Dict:
        return asdict(self)


class MultiAgentSystem:
    """
    Multi-Agent Trading System
    
    Process:
    1. Initialize 6 agents with different strategies
    2. Run all agents in parallel
    3. Monitor performance daily
    4. Kill bottom 20% after 3 consecutive losses
    5. Replace with new agents
    6. Scale top 20% with increased capital
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # System parameters
        self.kill_threshold_losses = config.get("kill_threshold_losses", 3)
        self.kill_percentage = config.get("kill_percentage", 0.20)  # Bottom 20%
        self.scale_winners_pct = config.get("scale_winners_pct", 0.25)  # Scale up 25%
        self.rebalance_frequency_hours = config.get("rebalance_frequency_hours", 24)
        
        # Initialize agents
        self.agents: List[Agent] = []
        self._init_agents()
        
        # History
        self.history: List[Dict] = []
        
        # Database
        self._init_database()
        
        logger.info(f"[MultiAgent] Initialized with {len(self.agents)} agents")
    
    def _init_agents(self):
        """Initialize default agent roster"""
        agent_configs = [
            {"name": "ArbBot", "strategy": "binary_arbitrage", "capital": 50, "risk": "low"},
            {"name": "SniperBot", "strategy": "15min_sniper", "capital": 50, "risk": "medium"},
            {"name": "ContrarianBot", "strategy": "contrarian", "capital": 25, "risk": "medium"},
            {"name": "MomentumBot", "strategy": "momentum", "capital": 25, "risk": "medium"},
            {"name": "PairsBot", "strategy": "pairs_trading", "capital": 25, "risk": "low"},
            {"name": "YOLOBot", "strategy": "high_risk", "capital": 10, "risk": "very_high"},
        ]
        
        for cfg in agent_configs:
            self.agents.append(Agent(
                name=cfg["name"],
                strategy_type=cfg["strategy"],
                capital=cfg["capital"],
                risk_level=cfg["risk"],
                kill_threshold=self.kill_threshold_losses if cfg["risk"] != "very_high" else 2
            ))
    
    def _init_database(self):
        """Initialize database"""
        conn = sqlite3.connect("trades.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS multi_agent_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                agent_name TEXT,
                details TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def get_agent(self, name: str) -> Optional[Agent]:
        """Get agent by name"""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None
    
    def update_agent_stats(self, agent_name: str, trade_pnl: float, is_win: bool):
        """Update agent statistics after a trade"""
        agent = self.get_agent(agent_name)
        if not agent:
            return
        
        agent.total_trades += 1
        agent.total_pnl += trade_pnl
        
        if is_win:
            agent.winning_trades += 1
            agent.consecutive_losses = 0  # Reset on win
        else:
            agent.consecutive_losses += 1
        
        agent.last_eval = datetime.now(timezone.utc).isoformat()
    
    def evaluate_and_evolve(self) -> Dict:
        """
        Daily evaluation - kill losers, scale winners
        
        Process:
        1. Calculate performance metrics for each agent
        2. Sort by performance
        3. Kill bottom 20% with > 3 consecutive losses
        4. Scale top 20% winners
        5. Log evolution
        """
        results = {
            "killed": [],
            "scaled_up": [],
            "kept": []
        }
        
        # Sort agents by P&L
        sorted_agents = sorted(self.agents, key=lambda a: a.total_pnl, reverse=True)
        
        # Calculate kill count (bottom 20%)
        kill_count = max(1, int(len(self.agents) * self.kill_percentage))
        scale_count = max(1, int(len(self.agents) * self.scale_winners_pct))
        
        # Track who to kill (bottom performers with consecutive losses)
        to_kill = []
        for agent in sorted_agents[-kill_count:]:
            if agent.consecutive_losses >= agent.kill_threshold:
                to_kill.append(agent)
        
        # Kill agents
        for agent in to_kill:
            agent.status = "killed"
            results["killed"].append(agent.name)
            self._log_event("kill", agent.name, f"Consecutive losses: {agent.consecutive_losses}")
            logger.warning(f"[MultiAgent] ❌ {agent.name} KILLED after {agent.consecutive_losses} losses")
            
            # Replace with new agent
            new_agent = self._create_replacement_agent(agent.strategy_type)
            self.agents.append(new_agent)
            self._log_event("spawn", new_agent.name, f"Replaced {agent.name}")
        
        # Scale winners (top performers)
        for agent in sorted_agents[:scale_count]:
            if agent.status == "active" and agent.total_pnl > 0 and agent.win_rate > 60:
                old_capital = agent.capital
                agent.capital *= (1 + self.scale_winners_pct)
                agent.max_position_pct *= (1 + self.scale_winners_pct)
                results["scaled_up"].append({
                    "name": agent.name,
                    "old_capital": old_capital,
                    "new_capital": agent.capital
                })
                self._log_event("scale", agent.name, f"Capital: {old_capital} → {agent.capital}")
                logger.info(f"[MultiAgent] ✅ {agent.name} SCALED UP +{self.scale_winners_pct*100}%")
        
        # Log survivors
        for agent in self.agents:
            if agent.status == "active" and agent.name not in results["killed"]:
                results["kept"].append(agent.name)
        
        # Save history
        self.history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "agent_stats": [a.to_dict() for a in self.agents]
        })
        
        return results
    
    def _create_replacement_agent(self, strategy_type: str) -> Agent:
        """Create a new agent to replace a killed one"""
        import random
        
        names = ["NovaBot", "PulseBot", "ApexBot", "ZenBot", "FluxBot", "NovaBot2"]
        taken_names = [a.name for a in self.agents]
        available_names = [n for n in names if n not in taken_names]
        
        name = random.choice(available_names) if available_names else f"Bot_{int(time.time())}"
        
        return Agent(
            name=name,
            strategy_type=strategy_type,
            capital=20,  # Start with smaller capital
            risk_level="medium",
            kill_threshold=self.kill_threshold_losses
        )
    
    def _log_event(self, event_type: str, agent_name: str, details: str):
        """Log evolution event to database"""
        try:
            conn = sqlite3.connect("trades.db")
            conn.execute("""
                INSERT INTO multi_agent_history (timestamp, event_type, agent_name, details)
                VALUES (?, ?, ?, ?)
            """, (datetime.now(timezone.utc).isoformat(), event_type, agent_name, details))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[MultiAgent] Log error: {e}")
    
    def get_dashboard_data(self) -> Dict:
        """Get data for dashboard"""
        return {
            "total_agents": len(self.agents),
            "active_agents": sum(1 for a in self.agents if a.status == "active"),
            "killed_agents": sum(1 for a in self.agents if a.status == "killed"),
            "total_capital": sum(a.capital for a in self.agents),
            "total_pnl": sum(a.total_pnl for a in self.agents),
            "best_performer": max(self.agents, key=lambda a: a.total_pnl).name if self.agents else None,
            "worst_performer": min(self.agents, key=lambda a: a.total_pnl).name if self.agents else None,
            "agents": [a.to_dict() for a in self.agents]
        }
    
    def run_evaluation_cycle(self):
        """Run a single evaluation cycle"""
        logger.info("[MultiAgent] Running evaluation cycle...")
        
        # In production, this would fetch real stats from each strategy
        # For now, simulate with current state
        
        results = self.evaluate_and_evolve()
        
        logger.info(f"[MultiAgent] Evaluation complete: {results}")
        return results


# CLI for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    config = {
        "kill_threshold_losses": 3,
        "kill_percentage": 0.20,
        "scale_winners_pct": 0.25,
        "rebalance_frequency_hours": 24
    }
    
    system = MultiAgentSystem(config)
    
    print("\n" + "="*60)
    print("MULTI-AGENT TRADING SYSTEM")
    print("="*60)
    
    # Show initial state
    data = system.get_dashboard_data()
    print(f"\nTotal Agents: {data['total_agents']}")
    print(f"Active: {data['active_agents']} | Killed: {data['killed_agents']}")
    print(f"Total Capital: ${data['total_capital']:.2f}")
    print(f"Total P&L: ${data['total_pnl']:.2f}")
    
    print("\n📊 Agent Performance:")
    print("-" * 60)
    for agent in data["agents"]:
        status_icon = "✅" if agent["status"] == "active" else "❌"
        print(f"{status_icon} {agent['name']:15} | ${agent['capital']:6.2f} | P&L: ${agent['total_pnl']:+6.2f} | Win: {agent['win_rate']:5.1f}% | Risk: {agent['risk_level']}")
    
    print("\n" + "="*60)
