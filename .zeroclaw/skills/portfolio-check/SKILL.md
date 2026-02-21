# Portfolio Check Skill

Display comprehensive portfolio and trading performance.

## When to Use

When user asks about:
- Portfolio status
- Open positions
- Trading performance
- Account balance
- Recent trades

## Data Sources

1. SQLite database (trades.db)
2. ZeroClaw memory
3. Wallet balance API

## Metrics Calculated

- Total P&L (realized + unrealized)
- Win rate
- Average trade duration
- Sharpe ratio
- Max drawdown
- Current exposure

## Output Format

```
💼 PORTFOLIO SUMMARY

Total Value: ${total_value}
Available Balance: ${balance}
Open Positions: {count}

Performance (24h):
- Trades: {count}
- P&L: ${pnl} ({pnl_pct}%)
- Win Rate: {win_rate}%

Performance (All Time):
- Total Trades: {count}
- Total P&L: ${total_pnl}
- Best Trade: ${best_trade}
- Worst Trade: ${worst_trade}

Open Positions:
{symbol} | {entry_price} | {current_price} | {pnl} | {size}

Recent Trades:
{time} | {symbol} | {side} | {price} | {pnl}

View full dashboard: http://localhost:8080
```

## Commands Supported

- "portfolio" - Full summary
- "positions" - Open positions only
- "trades today" - Today's trades
- "performance" - All-time stats
