# Price Check Skill

Fetch cryptocurrency prices from multiple sources.

## When to Use

When user asks about any cryptocurrency price, market data, or token value.

## Data Sources

1. **DexScreener API** - Real-time DEX prices
2. **CoinGecko API** - Market data and historical prices
3. **Local Database** - Cached prices from trading bot

## Process

1. Extract token symbol from user query
2. Query DexScreener API for current price
3. Query local SQLite database for recent trades
4. Format comprehensive price report
5. Save to memory for tracking

## Example Queries

- "What's the price of Bitcoin?"
- "Check SOL price"
- "How much is ETH worth?"

## Output Format

```
💰 {SYMBOL} Price Report

Current Price: ${price}
24h Change: {change}%
24h Volume: ${volume}
Liquidity: ${liquidity}

Trading Bot Data:
- Last trade: ${last_trade_price}
- Positions: {open_positions}
- P&L: ${pnl}

Source: DexScreener / Trading Bot
Updated: {timestamp}
```
