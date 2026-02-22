#!/usr/bin/env python3
"""
Multi-Agent Orchestrator for ZeroClaw
Coordinates multiple specialized agents to complete complex tasks
"""

import json
import subprocess
import sys
from typing import Dict, List, Any

class MultiAgentOrchestrator:
    def __init__(self, config_path: str = "/tmp/trading_zeroclaw/.zeroclaw/multi-agent.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.agents = {a['id']: a for a in self.config['agents']}
    
    def route_task(self, message: str) -> Dict[str, Any]:
        """Route a task to the appropriate agent(s)"""
        message_lower = message.lower()
        
        # Determine which agent(s) should handle this
        assigned_agents = []
        
        if any(kw in message_lower for kw in ['price', 'btc', 'eth', 'sol', 'cost']):
            assigned_agents.append(self.agents.get('price-analyst'))
        
        if any(kw in message_lower for kw in ['arbitrage', 'spread', 'difference']):
            assigned_agents.append(self.agents.get('arbitrage-hunter'))
        
        if any(kw in message_lower for kw in ['portfolio', 'position', 'holding', 'pnl']):
            assigned_agents.append(self.agents.get('portfolio-manager'))
        
        if any(kw in message_lower for kw in ['status', 'health', 'error', 'debug']):
            assigned_agents.append(self.agents.get('system-monitor'))
        
        # Default to price analyst
        if not assigned_agents:
            assigned_agents = [self.agents.get('price-analyst')]
        
        return {
            'primary_agent': assigned_agents[0],
            'supporting_agents': assigned_agents[1:] if len(assigned_agents) > 1 else [],
            'coordination_mode': self.config['coordination']['mode']
        }
    
    def execute_with_agent(self, agent: Dict, message: str) -> str:
        """Execute a task using a specific agent's skills"""
        skills = agent.get('skills', [])
        
        # Map to telegram handler commands
        results = []
        for skill in skills[:2]:  # Use top 2 relevant skills
            try:
                result = self._execute_skill(skill, message)
                if result:
                    results.append(result)
            except Exception as e:
                results.append(f"⚠️ {skill}: {str(e)}")
        
        return "\n\n".join(results) if results else f"Agent {agent['name']} processed your request."
    
    def _execute_skill(self, skill: str, message: str) -> str:
        """Execute a specific skill"""
        # Use the telegram handler
        handler_path = "/tmp/trading_zeroclaw/.zeroclaw/telegram_handler.sh"
        
        proc = subprocess.run(
            ['bash', handler_path],
            input=json.dumps({"message": message, "user_id": "multi_agent"}),
            capture_output=True,
            text=True,
            env={"HOME": "/tmp/trading_zeroclaw"},
            timeout=30
        )
        
        return proc.stdout.strip() if proc.returncode == 0 else proc.stderr.strip()
    
    def process(self, message: str) -> Dict[str, Any]:
        """Process a message through the multi-agent system"""
        routing = self.route_task(message)
        primary = routing['primary_agent']
        supporting = routing['supporting_agents']
        
        # Execute with primary agent
        primary_result = self.execute_with_agent(primary, message)
        
        # Get supporting insights
        supporting_results = []
        for agent in supporting:
            result = self.execute_with_agent(agent, message)
            if result and result != primary_result:
                supporting_results.append({
                    'agent': agent['name'],
                    'result': result
                })
        
        return {
            'success': True,
            'primary_agent': primary['name'],
            'primary_result': primary_result,
            'supporting_insights': supporting_results,
            'coordination_mode': routing['coordination_mode']
        }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        orchestrator = MultiAgentOrchestrator()
        result = orchestrator.process(message)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: multi_agent_orchestrator.py <message>")
        print("Example: multi_agent_orchestrator.py 'check btc price and arbitrage'")
