"""
RL Agent Module
===============
Reinforcement Learning for trading decisions.

Components:
- environment.py: Trading environment (Gym-style)
- agent.py: PPO agent implementation
- train.py: Training script
- evaluate.py: Evaluation script
"""

try:
    from .environment import TradingEnvironment
    from .agent import PPOAgent
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False

__all__ = ['TradingEnvironment', 'PPOAgent', 'RL_AVAILABLE']
