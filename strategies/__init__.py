"""
Trading Strategies Module
======================
Contains all trading strategies and the multi-agent orchestrator.
"""

from .binary_arbitrage import BinaryArbitrageStrategy, ArbitrageOpportunity, ArbitrageTrade
from .sniper import SniperStrategy, SniperMarket, SniperTrade
from .multi_agent import MultiAgentSystem, Agent

__all__ = [
    # Binary Arbitrage
    "BinaryArbitrageStrategy",
    "ArbitrageOpportunity", 
    "ArbitrageTrade",
    # Sniper
    "SniperStrategy",
    "SniperMarket",
    "SniperTrade",
    # Multi-Agent
    "MultiAgentSystem",
    "Agent",
]

__version__ = "1.0.0"
