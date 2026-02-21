# Trade Execution Skill

Execute trades on exchanges with proper validation and approval.

## When to Use

When user requests to:
- Execute a specific trade
- Buy/sell a token
- Place an order based on arbitrage opportunity

## Security Requirements

⚠️ **REQUIRES USER APPROVAL** - All trades must be confirmed

## Process

1. **Validate Request**
   - Check trading mode (paper/live)
   - Verify wallet connection
   - Validate symbol exists
   - Check sufficient balance

2. **Calculate Costs**
   ```
   trade_amount = requested_amount
   fees = exchange_fee + gas_fee
   slippage = estimated_slippage
   total_cost = trade_amount + fees + slippage_buffer
   ```

3. **Request Confirmation**
   - Show trade preview in Telegram
   - Wait for user approval (5 min timeout)
   - Require explicit "CONFIRM" response

4. **Execute Trade**
   - Call Python trading bot via shell
   - Record in database
   - Send confirmation

## Confirmation Format

```
⚠️ TRADE CONFIRMATION REQUIRED

Action: {BUY/SELL} {symbol}
Amount: {amount}
Price: ${price} (est.)
Fees: ${fees}
Total Cost: ${total}

Wallet Balance: ${balance}
Remaining After: ${remaining}

Mode: {PAPER/LIVE}
⚠️ {Paper = simulated | Live = REAL MONEY}

Reply within 5 minutes:
CONFIRM - Execute trade
CANCEL - Abort
```

## Post-Execution

```
✅ TRADE EXECUTED

Order ID: {order_id}
Status: {FILLED/PENDING}
Filled Price: ${price}
Amount: {amount}
Fees Paid: ${fees}
Net P&L: ${pnl}

View in dashboard: http://localhost:8080/trades
```
