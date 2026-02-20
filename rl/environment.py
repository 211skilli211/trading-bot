#!/usr/bin/env python3
"""
Trading Environment for RL
==========================
Gym-style environment for training trading agents.

State Space:
- Price data (OHLCV)
- Technical indicators
- Account balance
- Open positions

Action Space:
- 0: HOLD
- 1: BUY
- 2: SELL
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class Trade:
    """Represents a trade"""
    entry_price: float
    entry_step: int
    side: str  # 'long' or 'short'
    size: float
    exit_price: float = 0.0
    exit_step: int = 0
    pnl: float = 0.0
    status: str = 'open'  # 'open' or 'closed'


class TradingEnvironment:
    """
    Trading environment for reinforcement learning.
    
    Follows OpenAI Gym interface:
    - reset(): Reset environment, return initial state
    - step(action): Execute action, return (state, reward, done, info)
    - render(): Visualize current state
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        initial_balance: float = 10000.0,
        max_position: float = 1.0,
        commission: float = 0.001,
        window_size: int = 20
    ):
        """
        Initialize trading environment.
        
        Args:
            data: DataFrame with OHLCV data
            initial_balance: Starting capital
            max_position: Maximum position size
            commission: Trading fee
            window_size: Number of past observations in state
        """
        self.data = data.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.max_position = max_position
        self.commission = commission
        self.window_size = window_size
        
        # State space
        self.n_features = 10  # OHLCV + indicators
        self.state_dim = self.n_features * window_size
        
        # Action space: 0=HOLD, 1=BUY, 2=SELL
        self.action_dim = 3
        
        # Episode tracking
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0.0  # Current position (-1 to 1)
        self.trades: List[Trade] = []
        self.current_trade: Trade = None
        
        # Performance tracking
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        
    def reset(self) -> np.ndarray:
        """Reset environment to initial state"""
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.position = 0.0
        self.trades = []
        self.current_trade = None
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        
        return self._get_state()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one trading step.
        
        Args:
            action: 0=HOLD, 1=BUY, 2=SELL
            
        Returns:
            state: New observation
            reward: Step reward
            done: Whether episode ended
            info: Additional info
        """
        # Get current price
        current_price = self.data.iloc[self.current_step]['close']
        
        # Execute action
        reward = 0.0
        
        if action == 1 and self.position <= 0:  # BUY
            if self.current_trade and self.current_trade.side == 'short':
                # Close short
                self._close_trade(current_price)
            
            # Open long
            self.current_trade = Trade(
                entry_price=current_price,
                entry_step=self.current_step,
                side='long',
                size=self.max_position
            )
            self.position = self.max_position
            
            # Commission cost
            reward -= self.commission * current_price
            
        elif action == 2 and self.position >= 0:  # SELL
            if self.current_trade and self.current_trade.side == 'long':
                # Close long
                self._close_trade(current_price)
            
            # Open short
            self.current_trade = Trade(
                entry_price=current_price,
                entry_step=self.current_step,
                side='short',
                size=self.max_position
            )
            self.position = -self.max_position
            
            # Commission cost
            reward -= self.commission * current_price
        
        # Calculate unrealized P&L
        unrealized_pnl = 0.0
        if self.current_trade and self.current_trade.status == 'open':
            if self.current_trade.side == 'long':
                unrealized_pnl = (current_price - self.current_trade.entry_price) * self.max_position
            else:
                unrealized_pnl = (self.current_trade.entry_price - current_price) * self.max_position
        
        # Reward is change in portfolio value
        portfolio_value = self.balance + unrealized_pnl
        reward += (portfolio_value - self.initial_balance) / self.initial_balance * 100
        
        # Move to next step
        self.current_step += 1
        
        # Check if done
        done = self.current_step >= len(self.data) - 1
        
        if done and self.current_trade and self.current_trade.status == 'open':
            # Close any open position
            self._close_trade(current_price)
        
        # Get new state
        state = self._get_state()
        
        info = {
            'step': self.current_step,
            'balance': self.balance,
            'position': self.position,
            'portfolio_value': portfolio_value,
            'unrealized_pnl': unrealized_pnl,
            'total_trades': self.total_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        }
        
        return state, reward, done, info
    
    def _get_state(self) -> np.ndarray:
        """Get current state observation"""
        # Get window of data
        start = max(0, self.current_step - self.window_size)
        end = self.current_step
        
        window_data = self.data.iloc[start:end]
        
        # Normalize features
        features = []
        
        for _, row in window_data.iterrows():
            # Price features (normalized by close)
            close = row['close']
            features.extend([
                row['open'] / close - 1,
                row['high'] / close - 1,
                row['low'] / close - 1,
                0.0,  # close / close - 1 = 0
                row['volume'] / (self.data['volume'].mean() + 1e-8),
            ])
            
            # Add technical indicators if available
            if 'rsi' in row:
                features.append(row['rsi'] / 100)
            else:
                features.append(0.5)
            
            if 'sma_20' in row:
                features.append(row['sma_20'] / close - 1)
            else:
                features.append(0.0)
            
            if 'ema_12' in row:
                features.append(row['ema_12'] / close - 1)
            else:
                features.append(0.0)
            
            if 'macd' in row:
                features.append(np.tanh(row['macd'] / close))
            else:
                features.append(0.0)
            
            # Position feature
            features.append(self.position)
        
        # Pad if necessary
        while len(features) < self.state_dim:
            features = [0.0] * self.n_features + features
        
        return np.array(features[-self.state_dim:], dtype=np.float32)
    
    def _close_trade(self, exit_price: float):
        """Close current trade"""
        if not self.current_trade or self.current_trade.status != 'open':
            return
        
        self.current_trade.exit_price = exit_price
        self.current_trade.exit_step = self.current_step
        
        # Calculate P&L
        if self.current_trade.side == 'long':
            pnl = (exit_price - self.current_trade.entry_price) * self.current_trade.size
        else:
            pnl = (self.current_trade.entry_price - exit_price) * self.current_trade.size
        
        pnl -= self.commission * exit_price  # Exit commission
        
        self.current_trade.pnl = pnl
        self.current_trade.status = 'closed'
        
        self.balance += pnl
        self.total_pnl += pnl
        self.total_trades += 1
        
        if pnl > 0:
            self.winning_trades += 1
        
        self.trades.append(self.current_trade)
        self.current_trade = None
        self.position = 0.0
    
    def render(self):
        """Render current state"""
        if len(self.data) > self.current_step:
            price = self.data.iloc[self.current_step]['close']
            print(f"Step: {self.current_step} | Price: ${price:.2f} | "
                  f"Balance: ${self.balance:.2f} | Position: {self.position:.2f} | "
                  f"Trades: {self.total_trades} | P&L: ${self.total_pnl:.2f}")
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.total_trades - self.winning_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            'total_pnl': self.total_pnl,
            'final_balance': self.balance,
            'return_pct': (self.balance - self.initial_balance) / self.initial_balance * 100
        }
