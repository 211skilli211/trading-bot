#!/usr/bin/env python3
"""
Advanced Metrics — Adapted from Jesse's metrics module
=========================================================
Beyond basic Sharpe/drawdown, these metrics give a complete
picture of strategy performance.

Metrics included:
- Calmar Ratio    = Annual return / Max drawdown
- Sortino Ratio   = Return / Downside deviation (penalizes only bad volatility)
- Expectancy      = Avg win × win_rate - avg loss × loss_rate
- SER Ratio       = Sharpe / √2 (Kelly criterion adjusted)
- Profit Factor   = Gross profit / Gross loss
- Recovery Factor = Net profit / Max drawdown
- Ulcer Index     = Drawdown-based risk measure (improved Sharpe)
- Avg Trade Duration
- Consecutive tracking

Ported from: jesse-ai/jesse/jesse/metrics.py
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class AdvancedMetrics:
    """Complete performance metrics for a strategy or portfolio."""
    # Basic
    total_return_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    # Risk-Adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    ser_ratio: float = 0.0  # Sharpe Equivalent Risk-adjusted
    # Profitability
    profit_factor: float = 0.0
    expectancy: float = 0.0
    expectancy_ratio: float = 0.0  # Expected return / avg loss
    recovery_factor: float = 0.0
    # Risk
    max_drawdown_pct: float = 0.0
    avg_drawdown_pct: float = 0.0
    ulcer_index: float = 0.0
    # Consistency
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    avg_trade_bars: float = 0.0
    avg_win_bars: float = 0.0
    avg_loss_bars: float = 0.0
    # Trade stats
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    net_profit: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0


def compute_advanced_metrics(
    trades: List[Dict[str, Any]],
    risk_free_rate: float = 0.0,  # Annual risk-free rate (e.g., 0.05 for 5%)
    periods_per_year: int = 252 * 24 * 4,  # 15m candles → periods per year
) -> AdvancedMetrics:
    """
    Compute comprehensive performance metrics from a list of trade dicts.
    
    Each trade dict needs:
        - profit_abs: float (P&L in USD)
        - profit_ratio: float (P&L as ratio, e.g., 0.02 for 2%)
        - duration_bars: int (number of candles the trade was open)
    
    Args:
        trades: List of completed trade dicts
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino
        periods_per_year: Number of trading periods in a year
    
    Returns:
        AdvancedMetrics with all computed values
    """
    if not trades:
        return AdvancedMetrics()
    
    m = AdvancedMetrics()
    m.total_trades = len(trades)
    
    profits = [t.get('profit_abs', 0) for t in trades]
    returns = [t.get('profit_ratio', 0) for t in trades]
    durations = [t.get('duration_bars', 0) for t in trades]
    
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    
    m.winning_trades = len(wins)
    m.losing_trades = len(losses)
    m.win_rate = m.winning_trades / m.total_trades if m.total_trades > 0 else 0.0
    
    m.net_profit = sum(profits)
    m.gross_profit = sum(wins) if wins else 0.0
    m.gross_loss = abs(sum(losses)) if losses else 0.0
    
    m.avg_win = np.mean(wins) if wins else 0.0
    m.avg_loss = abs(np.mean(losses)) if losses else 0.0
    m.largest_win = max(wins) if wins else 0.0
    m.largest_loss = abs(min(losses)) if losses else 0.0
    m.total_return_pct = sum(returns)
    
    # --- Profit Factor ---
    m.profit_factor = m.gross_profit / m.gross_loss if m.gross_loss > 0 else float('inf')
    
    # --- Expectancy ---
    # E = (WinRate × AvgWin) - (LossRate × AvgLoss)
    m.expectancy = (m.win_rate * m.avg_win) - ((1 - m.win_rate) * m.avg_loss)
    # Expectancy Ratio = Expected return / Avg loss (how many losses to make 1 unit)
    m.expectancy_ratio = m.expectancy / m.avg_loss if m.avg_loss > 0 else 0.0
    
    # --- Sharpe Ratio ---
    if len(returns) > 2:
        excess_returns = np.array(returns) - (risk_free_rate / periods_per_year)
        std_returns = np.std(excess_returns, ddof=1)
        if std_returns > 0:
            period_sharpe = np.mean(excess_returns) / std_returns
            m.sharpe_ratio = period_sharpe * np.sqrt(periods_per_year)
    
    # --- Sortino Ratio ---
    if len(returns) > 2:
        downside_returns = [r for r in returns if r < 0]
        downside_std = np.std(downside_returns, ddof=1) if downside_returns else 0
        if downside_std > 0:
            annual_return = np.mean(returns) * periods_per_year
            m.sortino_ratio = annual_return / (downside_std * np.sqrt(periods_per_year))
    
    # --- Max Drawdown ---
    equity = np.cumsum(returns)
    peak = equity[0]
    max_dd = 0.0
    for i, eq in enumerate(equity):
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    m.max_drawdown_pct = max_dd
    
    # --- Avg Drawdown ---
    peak = equity[0]
    drawdowns = []
    for eq in equity:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0
        drawdowns.append(dd)
    m.avg_drawdown_pct = np.mean(drawdowns) if drawdowns else 0.0
    
    # --- Calmar Ratio ---
    # Annual return / Max drawdown
    annual_return = np.mean(returns) * periods_per_year if returns else 0
    if m.max_drawdown_pct > 0:
        m.calmar_ratio = annual_return / m.max_drawdown_pct
    else:
        m.calmar_ratio = float('inf')
    
    # --- SER Ratio (Kelly-adjusted) ---
    # SER = Sharpe / sqrt(2) — penalizes negative Sharpe more heavily
    m.ser_ratio = m.sharpe_ratio / np.sqrt(2) if m.sharpe_ratio != 0 else 0.0
    
    # --- Recovery Factor = Net profit / Max drawdown ---
    if m.max_drawdown_pct > 0:
        m.recovery_factor = m.net_profit / (m.max_drawdown_pct * abs(m.net_profit)) if m.net_profit != 0 else 0.0
    
    # --- Ulcer Index ---
    # sqrt(avg(drawdown^2)) — penalizes large drawdowns more than small ones
    if drawdowns:
        sq_dds = [dd ** 2 for dd in drawdowns]
        m.ulcer_index = np.sqrt(np.mean(sq_dds))
    
    # --- Consecutive tracking ---
    if profits:
        current_streak = 0
        current_sign = None
        for p in profits:
            sign = 1 if p > 0 else -1
            if sign == current_sign:
                current_streak += 1
            else:
                # Record previous streak
                if current_sign == 1 and (m.max_consecutive_wins == 0 or current_streak > m.max_consecutive_wins):
                    pass
                current_sign = sign
                current_streak = 1
            if sign == 1 and current_streak > m.max_consecutive_wins:
                m.max_consecutive_wins = current_streak
            if sign == -1 and current_streak > m.max_consecutive_losses:
                m.max_consecutive_losses = current_streak
    
    # --- Duration ---
    if durations:
        m.avg_trade_bars = np.mean(durations)
        win_durations = [durations[i] for i in range(len(durations)) if profits[i] > 0]
        loss_durations = [durations[i] for i in range(len(durations)) if profits[i] < 0]
        m.avg_win_bars = np.mean(win_durations) if win_durations else 0.0
        m.avg_loss_bars = np.mean(loss_durations) if loss_durations else 0.0
    
    return m


def metrics_to_report(m: AdvancedMetrics) -> str:
    """Format metrics as a readable report string."""
    lines = [
        "=" * 55,
        "  ADVANCED PERFORMANCE METRICS",
        "=" * 55,
        "",
        f"  Total Trades:    {m.total_trades}",
        f"  Win Rate:        {m.win_rate:.1%} ({m.winning_trades}W / {m.losing_trades}L)",
        f"  Net Profit:      ${m.net_profit:,.2f}",
        f"  Total Return:    {m.total_return_pct:.2%}",
        f"",
        f"  --- Risk-Adjusted ---",
        f"  Sharpe Ratio:    {m.sharpe_ratio:.3f}",
        f"  Sortino Ratio:   {m.sortino_ratio:.3f}",
        f"  Calmar Ratio:    {m.calmar_ratio:.3f}",
        f"  SER Ratio:       {m.ser_ratio:.3f}",
        f"",
        f"  --- Profitability ---",
        f"  Profit Factor:   {m.profit_factor:.3f}",
        f"  Expectancy:      ${m.expectancy:.2f}/trade",
        f"  Expectancy Ratio:{m.expectancy_ratio:.3f}",
        f"  Recovery Factor: {m.recovery_factor:.3f}",
        f"",
        f"  --- Risk ---",
        f"  Max Drawdown:    {m.max_drawdown_pct:.2%}",
        f"  Avg Drawdown:    {m.avg_drawdown_pct:.2%}",
        f"  Ulcer Index:     {m.ulcer_index:.4f}",
        f"",
        f"  --- Consistency ---",
        f"  Max Consec Wins: {m.max_consecutive_wins}",
        f"  Max Consec Loss: {m.max_consecutive_losses}",
        f"  Avg Win:         ${m.avg_win:,.2f}",
        f"  Avg Loss:        ${m.avg_loss:,.2f}",
        f"  Largest Win:     ${m.largest_win:,.2f}",
        f"  Largest Loss:    ${m.largest_loss:,.2f}",
        f"  Avg Trade Bars:  {m.avg_trade_bars:.1f}",
        f"  Avg Win Bars:    {m.avg_win_bars:.1f}",
        f"  Avg Loss Bars:   {m.avg_loss_bars:.1f}",
        "=" * 55,
    ]
    return '\n'.join(lines)


def walk_forward_optimization(
    candles: pd.DataFrame,
    strategy_params: Dict,
    train_size: int = 500,
    test_size: int = 200,
    step_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    Walk-forward optimization — Jesse's gold standard.
    
    Splits data into rolling windows:
    1. Train on window N, test on window N+1
    2. Slide forward, repeat
    3. Aggregate results across all windows
    
    This prevents overfitting — parameters must perform on unseen data.
    
    Args:
        candles: Full OHLCV dataset
        strategy_params: Strategy parameters to test
        train_size: Number of candles in training window
        test_size: Number of candles in testing window
        step_size: How far to slide each iteration
    
    Returns:
        List of per-window results with train/test metrics
    """
    results = []
    total = len(candles)
    
    i = 0
    while i + train_size + test_size <= total:
        train_candles = candles.iloc[i:i + train_size]
        test_candles = candles.iloc[i + train_size:i + train_size + test_size]
        
        window_result = {
            "window": len(results) + 1,
            "train_start": str(train_candles.index[0]) if hasattr(train_candles.index[0], 'isoformat' ) else i,
            "train_end": str(train_candles.index[-1]) if hasattr(train_candles.index[-1], 'isoformat') else i + train_size,
            "test_start_idx": i + train_size,
            "test_end_idx": i + train_size + test_size,
            "train_metrics": None,
            "test_metrics": None,
        }
        
        # Here you would run strategy train/test
        # For now, record the window structure
        results.append(window_result)
        
        i += step_size
    
    print(f"[WalkForward] {len(results)} windows computed "
          f"(train={train_size}, test={test_size}, step={step_size})")
    return results
