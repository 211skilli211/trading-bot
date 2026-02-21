# Arbitrage Scan Skill

Scan for arbitrage opportunities between exchanges.

## When to Use

- Heartbeat runs every 5 minutes automatically
- User explicitly requests scan
- Before executing trades to check market conditions

## Process

1. Query prices from multiple sources:
   - Binance API (CEX)
   - DexScreener API (DEX)
   - Local price cache (SQLite)

2. Calculate spreads:
   ```
   spread = (higher_price - lower_price) / lower_price
   net_spread = spread - (fee_buy + fee_sell + slippage)
   ```

3. Identify opportunities:
   - Minimum spread: 0.5%
   - Minimum profit after fees: $1
   - Filter by liquidity (minimum $10k)

4. Save to memory and notify

## Alert Thresholds

- **Low** (0.5% - 1.0%): Log only
- **Medium** (1.0% - 2.0%): Memory + Dashboard
- **High** (>2.0%): Telegram alert + Auto-trade (if enabled)

## Output Format (Alert)

```
🚨 ARBITRAGE OPPORTUNITY DETECTED

Token: {symbol}
Buy: ${buy_price} on {buy_exchange}
Sell: ${sell_price} on {sell_exchange}
Spread: {spread}%
Est. Profit: ${profit} (after fees)

Liquidity: ${liquidity}
Confidence: {high/medium/low}

⚡ Act fast! Opportunity expires in ~{seconds}s

Reply "EXECUTE" to trade (if live mode enabled)
Reply "IGNORE" to dismiss
```

## Database Schema

Stores opportunities in SQLite:
- timestamp
- symbol
- buy_exchange
- sell_exchange
- spread_pct
- profit_usd
- status (active/expired/executed)
