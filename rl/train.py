#!/usr/bin/env python3
"""
RL Training Script
==================
Train a PPO agent on historical trading data.
Can be run standalone to train and save models.

Usage:
    python -m rl.train --data data/btc_prices.csv --episodes 100
    python -m rl.train --model models/ppo_agent.pkl --eval-only
"""

import argparse
import numpy as np
import pandas as pd
import os
import sys
import json
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from rl.environment import TradingEnvironment
    from rl.agent import PPOAgent, SimpleRLAgent
except ImportError:
    from environment import TradingEnvironment
    from agent import PPOAgent, SimpleRLAgent


def generate_sample_data(n_samples: int = 1000, trend: str = 'random') -> pd.DataFrame:
    """
    Generate sample OHLCV data for testing.
    
    Args:
        n_samples: Number of data points
        trend: 'up', 'down', 'random', or 'sideways'
        
    Returns:
        DataFrame with OHLCV data
    """
    np.random.seed(42)
    
    # Generate price series
    price = 50000.0  # Starting BTC price
    prices = [price]
    
    for i in range(n_samples - 1):
        if trend == 'up':
            change = np.random.normal(0.001, 0.01)
        elif trend == 'down':
            change = np.random.normal(-0.001, 0.01)
        elif trend == 'sideways':
            change = np.random.normal(0, 0.005)
        else:  # random
            change = np.random.normal(0, 0.02)
        
        price *= (1 + change)
        prices.append(price)
    
    prices = np.array(prices)
    
    # Generate OHLCV
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=n_samples, freq='1h'),
        'open': prices * (1 + np.random.normal(0, 0.001, n_samples)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.005, n_samples))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.005, n_samples))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Add technical indicators
    df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['ema_12'] = df['close'].ewm(span=12, adjust=False, min_periods=1).mean()
    
    # Simple RSI calculation
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / (loss + 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_26 = df['close'].ewm(span=26, adjust=False, min_periods=1).mean()
    df['macd'] = df['ema_12'] - ema_26
    
    return df


def load_data(filepath: str) -> pd.DataFrame:
    """
    Load price data from CSV file.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        DataFrame with OHLCV data
    """
    if not os.path.exists(filepath):
        print(f"Data file not found: {filepath}")
        print("Generating sample data instead...")
        return generate_sample_data()
    
    df = pd.read_csv(filepath)
    
    # Ensure required columns exist
    required = ['open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Add indicators if not present
    if 'sma_20' not in df.columns:
        df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
    if 'rsi' not in df.columns:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
    
    return df


def train_agent(
    data: pd.DataFrame,
    n_episodes: int = 100,
    max_steps: int = None,
    model_path: str = 'models/ppo_agent.pkl',
    agent_type: str = 'ppo',
    print_interval: int = 10,
    save_interval: int = 50
) -> Dict:
    """
    Train RL agent on price data.
    
    Args:
        data: DataFrame with OHLCV data
        n_episodes: Number of training episodes
        max_steps: Max steps per episode (None = full data)
        model_path: Where to save the trained model
        agent_type: 'ppo' or 'simple'
        print_interval: Print progress every N episodes
        save_interval: Save model every N episodes
        
    Returns:
        Training history dictionary
    """
    print("=" * 70)
    print("🤖 RL AGENT TRAINING")
    print("=" * 70)
    print(f"Agent Type: {agent_type.upper()}")
    print(f"Episodes: {n_episodes}")
    print(f"Data Points: {len(data)}")
    print(f"Model Path: {model_path}")
    print()
    
    # Create environment
    env = TradingEnvironment(
        data=data,
        initial_balance=10000.0,
        max_position=1.0,
        commission=0.001,
        window_size=20
    )
    
    # Create agent
    if agent_type == 'ppo':
        agent = PPOAgent(
            state_dim=env.state_dim,
            action_dim=env.action_dim,
            hidden_dims=[128, 64],
            learning_rate=0.0003,
            gamma=0.99,
            gae_lambda=0.95
        )
    else:
        agent = SimpleRLAgent(
            state_dim=env.state_dim,
            action_dim=env.action_dim,
            hidden_dim=64
        )
    
    # Try to load existing model
    if os.path.exists(model_path):
        print(f"Loading existing model from {model_path}")
        agent.load(model_path)
    
    # Training history
    history = {
        'episodes': [],
        'rewards': [],
        'pnl': [],
        'trades': [],
        'win_rates': []
    }
    
    best_pnl = -np.inf
    
    for episode in range(n_episodes):
        # Reset environment
        state = env.reset()
        episode_reward = 0
        steps = 0
        
        if max_steps is None:
            max_steps_episode = len(data) - env.window_size - 1
        else:
            max_steps_episode = max_steps
        
        # Run episode
        for step in range(max_steps_episode):
            # Select action
            if agent_type == 'ppo':
                action, log_prob, value = agent.select_action(state, training=True)
            else:
                action = agent.select_action(state, training=True)
                log_prob, value = 0, 0
            
            # Execute action
            next_state, reward, done, info = env.step(action)
            
            # Store experience
            if agent_type == 'ppo':
                agent.store_experience(state, action, reward, next_state, done, value, log_prob)
            else:
                agent.store_experience(state, action, reward, next_state, done)
            
            episode_reward += reward
            state = next_state
            steps += 1
            
            # Update agent periodically
            if agent_type == 'ppo' and len(agent.buffer) >= 64:
                agent.update(epochs=4, batch_size=32)
            
            if done:
                break
        
        # Final update with remaining experiences
        if agent_type == 'ppo' and len(agent.buffer) > 0:
            agent.update(epochs=4, batch_size=32)
        elif agent_type == 'simple' and len(agent.buffer) >= 32:
            agent.update(batch_size=32)
        
        # Get performance summary
        perf = env.get_performance_summary()
        
        # Record history
        history['episodes'].append(episode + 1)
        history['rewards'].append(episode_reward)
        history['pnl'].append(perf['total_pnl'])
        history['trades'].append(perf['total_trades'])
        history['win_rates'].append(perf['win_rate'])
        
        # Print progress
        if (episode + 1) % print_interval == 0:
            print(f"Episode {episode + 1}/{n_episodes} | "
                  f"Reward: {episode_reward:+.2f} | "
                  f"P&L: ${perf['total_pnl']:+.2f} | "
                  f"Trades: {perf['total_trades']} | "
                  f"Win Rate: {perf['win_rate']:.1%}")
        
        # Save best model
        if perf['total_pnl'] > best_pnl:
            best_pnl = perf['total_pnl']
            best_path = model_path.replace('.pkl', '_best.pkl')
            agent.save(best_path)
        
        # Save checkpoint
        if (episode + 1) % save_interval == 0:
            checkpoint_path = model_path.replace('.pkl', f'_ep{episode + 1}.pkl')
            agent.save(checkpoint_path)
    
    # Save final model
    agent.save(model_path)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 TRAINING SUMMARY")
    print("=" * 70)
    print(f"Total Episodes: {n_episodes}")
    print(f"Final Avg Reward: {np.mean(history['rewards'][-10:]):.2f}")
    print(f"Best P&L: ${best_pnl:+.2f}")
    print(f"Final Model: {model_path}")
    print(f"Best Model: {model_path.replace('.pkl', '_best.pkl')}")
    print("=" * 70)
    
    return history


def evaluate_agent(
    data: pd.DataFrame,
    model_path: str = 'models/ppo_agent.pkl',
    agent_type: str = 'ppo',
    n_episodes: int = 10,
    render: bool = False
) -> Dict:
    """
    Evaluate trained agent.
    
    Args:
        data: DataFrame with OHLCV data
        model_path: Path to trained model
        agent_type: 'ppo' or 'simple'
        n_episodes: Number of evaluation episodes
        render: Whether to render environment
        
    Returns:
        Evaluation metrics
    """
    print("=" * 70)
    print("🧪 AGENT EVALUATION")
    print("=" * 70)
    
    # Create environment
    env = TradingEnvironment(
        data=data,
        initial_balance=10000.0,
        max_position=1.0,
        commission=0.001,
        window_size=20
    )
    
    # Create and load agent
    if agent_type == 'ppo':
        agent = PPOAgent(
            state_dim=env.state_dim,
            action_dim=env.action_dim,
            hidden_dims=[128, 64]
        )
    else:
        agent = SimpleRLAgent(
            state_dim=env.state_dim,
            action_dim=env.action_dim
        )
    
    if not agent.load(model_path):
        print("Failed to load model. Using random agent.")
    
    # Run evaluation episodes
    all_rewards = []
    all_pnls = []
    all_trades = []
    all_win_rates = []
    
    for episode in range(n_episodes):
        state = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            if agent_type == 'ppo':
                action, _, _ = agent.select_action(state, training=False)
            else:
                action = agent.select_action(state, training=False)
            
            state, reward, done, info = env.step(action)
            episode_reward += reward
            
            if render:
                env.render()
        
        perf = env.get_performance_summary()
        all_rewards.append(episode_reward)
        all_pnls.append(perf['total_pnl'])
        all_trades.append(perf['total_trades'])
        all_win_rates.append(perf['win_rate'])
        
        print(f"Episode {episode + 1}: Reward={episode_reward:+.2f}, "
              f"P&L=${perf['total_pnl']:+.2f}, Trades={perf['total_trades']}, "
              f"Win Rate={perf['win_rate']:.1%}")
    
    # Summary statistics
    print("\n" + "=" * 70)
    print("📊 EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Episodes: {n_episodes}")
    print(f"Avg Reward: {np.mean(all_rewards):.2f} ± {np.std(all_rewards):.2f}")
    print(f"Avg P&L: ${np.mean(all_pnls):+.2f} ± ${np.std(all_pnls):.2f}")
    print(f"Avg Trades: {np.mean(all_trades):.1f}")
    print(f"Avg Win Rate: {np.mean(all_win_rates):.1%}")
    print("=" * 70)
    
    return {
        'rewards': all_rewards,
        'pnls': all_pnls,
        'trades': all_trades,
        'win_rates': all_win_rates
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Train or evaluate RL trading agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train on sample data
  python -m rl.train
  
  # Train on custom data
  python -m rl.train --data data/btc_prices.csv --episodes 200
  
  # Evaluate trained model
  python -m rl.train --model models/ppo_agent.pkl --eval-only
  
  # Use simple agent
  python -m rl.train --agent-type simple --episodes 100
"""
    )
    
    parser.add_argument(
        '--data',
        type=str,
        help='Path to CSV file with OHLCV data'
    )
    
    parser.add_argument(
        '--episodes',
        type=int,
        default=100,
        help='Number of training episodes (default: 100)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='trading-bot/models/ppo_agent.pkl',
        help='Path to save/load model (default: models/ppo_agent.pkl)'
    )
    
    parser.add_argument(
        '--agent-type',
        choices=['ppo', 'simple'],
        default='ppo',
        help='Type of agent to train (default: ppo)'
    )
    
    parser.add_argument(
        '--eval-only',
        action='store_true',
        help='Only evaluate, do not train'
    )
    
    parser.add_argument(
        '--eval-episodes',
        type=int,
        default=10,
        help='Number of evaluation episodes (default: 10)'
    )
    
    parser.add_argument(
        '--render',
        action='store_true',
        help='Render environment during evaluation'
    )
    
    args = parser.parse_args()
    
    # Load or generate data
    if args.data:
        data = load_data(args.data)
    else:
        print("No data file provided. Generating sample data...")
        data = generate_sample_data(n_samples=2000)
    
    if args.eval_only:
        # Only evaluate
        evaluate_agent(
            data=data,
            model_path=args.model,
            agent_type=args.agent_type,
            n_episodes=args.eval_episodes,
            render=args.render
        )
    else:
        # Train and optionally evaluate
        history = train_agent(
            data=data,
            n_episodes=args.episodes,
            model_path=args.model,
            agent_type=args.agent_type
        )
        
        # Quick evaluation
        print("\nRunning quick evaluation...")
        evaluate_agent(
            data=data,
            model_path=args.model,
            agent_type=args.agent_type,
            n_episodes=5,
            render=False
        )
        
        # Save training history
        history_path = args.model.replace('.pkl', '_history.json')
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"\nTraining history saved to {history_path}")


if __name__ == '__main__':
    main()
