# PolyMarket Setup Guide

## Overview

PolyMarket is a decentralized prediction market platform on Polygon where you can trade YES/NO shares on real-world events. This guide will help you set up PolyMarket trading.

## What You Need

### 1. Polygon Wallet with USDC

PolyMarket trades using USDC on the Polygon network.

**Steps:**
1. Get a wallet that supports Polygon (MetaMask, Rainbow, etc.)
2. Add Polygon network to your wallet:
   - Network Name: Polygon Mainnet
   - RPC URL: https://polygon-rpc.com
   - Chain ID: 137
   - Currency Symbol: MATIC
   - Block Explorer: https://polygonscan.com

3. Bridge USDC from Ethereum to Polygon:
   - Use the official bridge: https://portal.polygon.technology/bridge
   - Or use a third-party bridge like Hop Exchange, Stargate, or Bungee
   - You need USDC on Polygon to trade (minimum $10-20 recommended)

### 2. PolyMarket API Credentials

For trading (placing/cancelling orders), you need CLOB API credentials.

**Steps to get API credentials:**
1. Go to https://polymarket.com/
2. Connect your wallet
3. Go to Settings or API section
4. Generate API Key, Secret, and Passphrase
5. Save these securely - they won't be shown again

### 3. Private Key (Optional but Recommended)

For programmatic withdrawals and advanced features, you may want to add your private key.

**⚠️ Security Warning:**
- Never share your private key
- Use a dedicated trading wallet with limited funds
- Consider using a hardware wallet

## Configuration

Add the following to your `.env` file:

```bash
# ============================================
# POLYMARKET (Binary Prediction Markets)
# ============================================

# Your Polygon wallet private key (for signing transactions)
# This wallet must have USDC on Polygon network for trading
POLYMARKET_PRIVATE_KEY=your_polymarket_polygon_private_key_here

# CLOB API credentials (for order book access)
# Get API key at: https://docs.polymarket.com/#authentication
POLYMARKET_API_KEY=your_polymarket_api_key_here
POLYMARKET_API_SECRET=your_polymarket_api_secret_here
POLYMARKET_PASSPHRASE=your_polymarket_passphrase_here

# Polygon RPC endpoint
POLYGON_RPC_URL=https://polygon-rpc.com

# USDC token address on Polygon (don't change this)
USDC_POLYGON_ADDRESS=0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
```

## Trading Strategies

### 1. Binary Arbitrage

**How it works:**
- Buy both YES and NO when their combined price < $1.00
- Guaranteed profit = $1.00 - (YES_price + NO_price)
- Example: YES @ $0.49 + NO @ $0.48 = $0.97 → $0.03 profit

**Requirements:**
- USDC on Polygon
- API credentials for order placement

### 2. Market Making

Place bids on both sides of the spread to earn the difference.

### 3. Trend Following

Buy shares in markets where you have strong conviction about the outcome.

## API Endpoints

The bot provides these PolyMarket endpoints:

### Public Endpoints (No API Key Required)

```
GET /api/polymarket/markets              # List all markets
GET /api/polymarket/market/<id>          # Get specific market
GET /api/polymarket/trending             # Trending markets
GET /api/polymarket/arbitrage            # Arbitrage opportunities
GET /api/polymarket/orderbook/<token_id> # Order book for token
```

### Trading Endpoints (API Key Required)

```
GET  /api/polymarket/status              # Trading status & balance
GET  /api/polymarket/orders              # List open orders
POST /api/polymarket/orders              # Place order
DELETE /api/polymarket/orders/<id>       # Cancel order
GET  /api/polymarket/portfolio           # Portfolio positions
```

## Testing

Test your configuration:

```bash
cd /root/trading-bot
python3 polymarket_client.py
```

This will fetch markets and show arbitrage opportunities.

## Troubleshooting

### "Trading not enabled" error
- Check that POLYMARKET_API_KEY is set correctly in .env
- Ensure the key is not the placeholder "your_polymarket_api_key_here"

### "Insufficient balance" error
- Make sure you have USDC on Polygon (not Ethereum mainnet)
- Check your balance at https://polymarket.com/portfolio

### Orders not filling
- PolyMarket has low liquidity on some markets
- Try markets with higher volume (> $10,000 daily)
- Adjust your price to be closer to the current market price

### API errors
- Verify your API credentials are correct
- Check that your API key hasn't expired
- Ensure you have internet connectivity to clob.polymarket.com

## Fees

- Trading Fee: 2% per trade (taken from profit)
- Gas Fees: Minimal on Polygon (~$0.01-0.10 per transaction)

## Risk Warning

⚠️ **Prediction markets involve risk:**
- Markets can resolve unexpectedly
- Liquidity may be low on some markets
- Oracle failures can affect resolution
- Only trade with funds you can afford to lose

## Resources

- PolyMarket: https://polymarket.com
- Documentation: https://docs.polymarket.com/
- CLOB API: https://docs.polymarket.com/#clob-api
- Polygon Bridge: https://portal.polygon.technology/bridge
