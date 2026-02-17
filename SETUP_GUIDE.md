# 🚀 Trading Bot - Complete Setup Guide

## Overview
Professional-grade Solana trading bot with:
- **5 exchanges** via CCXT (100+ supported)
- **Solana DEX** via Jupiter (on-chain arbitrage)
- **Real-time WebSocket** feeds
- **SQLite database** for persistence
- **Backtesting** with Birdeye API
- **Advanced orders** (Limit, DCA)
- **24/7 operation** on Termux

---

## 📋 Prerequisites

- Android device with Termux
- 20-50 USDT on Solana (Trust Wallet or similar)
- GitHub account (for code backup)

---

## ⚡ Quick Start (5 minutes)

### 1. Clone and Setup
```bash
git clone https://github.com/211skilli211/trading-bot.git
cd trading-bot
chmod +x setup.sh
./setup.sh
```

### 2. Configure Environment
```bash
# Copy template
cp .env.example .env

# Edit with your keys
nano .env
```

### 3. Test Paper Trading
```bash
python trading_bot.py --mode paper --monitor 60
```

---

## 🔧 Detailed Setup

### Step 1: Install Dependencies

```bash
# Update Termux
pkg update && pkg upgrade

# Install Python and tools
pkg install python git

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Create Solana Wallet

```bash
# Generate new wallet
python3 << 'EOF'
from solders.keypair import Keypair
kp = Keypair()
print("="*60)
print("SAVE THESE SECURELY:")
print("="*60)
print(f"Address: {kp.pubkey()}")
print(f"Private Key: {kp.to_base58_string()}")
print("="*60)
EOF
```

**SAVE THE OUTPUT!** This is your bot's wallet.

### Step 3: Fund the Wallet

1. Copy the **Address** from Step 2
2. Open Trust Wallet
3. Send 20-50 USDT (Solana network) to that address
4. Also send 0.1 SOL for transaction fees
5. Verify on https://solscan.io

### Step 4: Configure Environment

Edit `.env`:

```bash
# Solana (REQUIRED)
SOLANA_PRIVATE_KEY=your_private_key_from_step_2
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Trading mode
TRADING_MODE=paper  # Change to 'live' when ready

# Optional: Alerts
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Step 5: Test Components

```bash
# Test Solana DEX
python solana_dex.py

# Test Birdeye backtester
python birdeye_connector.py

# Test WebSocket
python websocket_feeds.py

# Test database
python database.py

# Test Jupiter orders
python jupiter_orders.py
```

---

## 🎯 Usage Modes

### 1. Paper Trading (Testing)
```bash
python trading_bot.py --mode paper --monitor 60 --config config.json
```

### 2. Live Trading (Real Money)
```bash
# Edit .env first: TRADING_MODE=live
python trading_bot.py --mode live --monitor 60
```

### 3. Backtesting
```bash
python backtester.py --days 30 --strategy arbitrage
```

### 4. Web Dashboard
```bash
python trading_bot.py --dashboard --port 8080
# Access at http://localhost:8080
```

### 5. 24/7 Operation
```bash
# Enable auto-start
mkdir -p ~/.termux/boot
cp .termux/boot/trading-bot ~/.termux/boot/

# Or run manually with nohup
nohup python trading_bot.py --monitor 60 > bot.log 2>&1 &
```

---

## 📊 Strategies

### Arbitrage (Cross-Exchange)
```json
{
  "strategy": {
    "type": "arbitrage",
    "min_spread": 0.005,
    "fee_rate": 0.001
  }
}
```

### Triangular (Solana DEX)
```python
# USDC -> SOL -> BTC -> USDC
dex = SolanaDEX()
opportunities = dex.find_triangular_arbitrage('USDC', amount=20)
```

### DCA (Dollar Cost Average)
```python
# Buy $5 of SOL every 12 hours for 7 days
jup = JupiterOrders()
order = jup.create_dca_order(
    input_mint=USDC,
    output_mint=SOL,
    total_amount=50000000,  # 50 USDC
    number_of_orders=14,
    interval_seconds=43200  # 12 hours
)
```

### Limit Orders
```python
# Buy SOL when price drops to $65
limit = jup.create_limit_order(
    input_mint=USDC,
    output_mint=SOL,
    input_amount=10000000,  # 10 USDC
    target_price=65.0,
    wallet_address=YOUR_WALLET
)
```

---

## 🔒 Security Checklist

- [ ] Private keys in `.env` (never commit!)
- [ ] `.env` in `.gitignore`
- [ ] Wallet only holds trading funds (not main savings)
- [ ] Daily loss limits configured
- [ ] Alerts enabled for stop-losses
- [ ] API keys have withdrawal disabled

---

## 📈 Performance Monitoring

### Check Logs
```bash
# Real-time logs
tail -f trading_bot.log | python -m json.tool

# SQLite database
sqlite3 trades.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"
```

### Health Check
```bash
# View summary
python trading_bot.py  # single run with summary

# Check database stats
python -c "
from database import TradingDatabase
db = TradingDatabase()
print(db.get_performance_summary(days=7))
"
```

---

## 🆘 Troubleshooting

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Connection refused"
- Check internet connection
- Try different RPC URL in `.env`
- Check if Termux has network permission

### "Insufficient funds"
- Ensure wallet has SOL for fees (0.1 minimum)
- Verify USDT balance on Solana network (not Ethereum)

### Bot stops when screen off
```bash
# Enable wake lock
termux-wake-lock

# Or add to .termux/boot/trading-bot
```

---

## 🎯 7-Day Launch Plan

| Day | Task | Command |
|-----|------|---------|
| 1 | Setup & paper test | `python trading_bot.py --mode paper` |
| 2 | Run backtest | `python backtester.py` |
| 3 | Enable WebSocket | Update config, test speed |
| 4 | Test alerts | Configure Telegram/Discord |
| 5 | Small live test | 20 USDT, tiny positions |
| 6 | Monitor & adjust | Check dashboard, tweak params |
| 7 | Scale up | Increase position sizes |

---

## 🚀 Production Deployment

### 24/7 with Termux Services
```bash
# Install termux-services
pkg install termux-services

# Enable on boot
sv-enable trading-bot

# Start now
sv up trading-bot

# Check status
sv status trading-bot
```

### Dashboard Access
```bash
# Start dashboard
python trading_bot.py --dashboard

# Access from other devices on same network:
# http://YOUR_PHONE_IP:8080
```

---

## 💡 Pro Tips

1. **Start small**: 20 USDT first, scale after profits
2. **Monitor daily**: Check Telegram alerts
3. **Keep logs**: SQLite helps analyze performance
4. **Update regularly**: `git pull` for improvements
5. **Backup wallet**: Save private key in multiple secure places

---

## 📞 Support

- GitHub Issues: https://github.com/211skilli211/trading-bot/issues
- Solana Explorer: https://solscan.io
- Jupiter Docs: https://docs.jup.ag

---

**Ready to launch?** 🚀

Start with: `python trading_bot.py --mode paper --monitor 60`
