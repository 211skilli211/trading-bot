# Trading Bot - Complete Setup Guide

## 🚀 Quick Start (Testnet/Devnet Only)

### Step 1: Access the Dashboard
Open your browser to:
```
http://localhost:8080
```

You should see the dashboard without "Internal Server Error"

### Step 2: Verify ZeroClaw AI
Check ZeroClaw status:
```bash
curl http://localhost:3000/health
```

Should show: `{"status":"ok", "paired":false}`

**Note:** `paired:false` is normal - pairing is only needed for remote Telegram/Discord access.

---

## 🔧 Testnet Configuration (Binance)

### 1. Create Binance Testnet Account
1. Go to: https://testnet.binance.vision/
2. Click "Generate HMAC_SHA256 Key"
3. Save your **API Key** and **Secret Key**

### 2. Configure Trading Bot
Edit `/root/trading-bot/.env`:
```bash
# Binance Testnet (NOT real money!)
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_SECRET_KEY=your_testnet_secret_here
BINANCE_TESTNET=true

# Trading Mode
TRADING_MODE=PAPER
```

### 3. Test Connection
```bash
cd /root/trading-bot
python3 -c "
import ccxt
exchange = ccxt.binance({
    'apiKey': 'your_testnet_api_key',
    'secret': 'your_testnet_secret',
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})
exchange.set_sandbox_mode(True)
print('Balance:', exchange.fetch_balance())
"
```

You should see testnet balances (free fake money).

---

## 🪐 Devnet Configuration (Solana)

### 1. Create Solana Devnet Wallet
```bash
# Install solana CLI if not present
curl --proto '=https' --tlsv1.2 -sSfL https://solana-install.solana.workers.dev | bash

# Create new wallet
solana-keygen new --outfile ~/.config/solana/devnet.json

# Set devnet cluster
solana config set --url devnet

# Get devnet SOL (free)
solana airdrop 2
```

### 2. Configure Solana DEX
Edit `/root/trading-bot/.env`:
```bash
# Solana Devnet
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_WALLET_FILE=solana_wallet.json
SOLANA_ENABLED=true
```

### 3. Test Jupiter Integration
```bash
curl -s 'https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=100000000&slippageBps=50'
```

Should return quote data.

---

## 🤖 ZeroClaw AI Integration

### Using ZeroClaw to Fix Errors

ZeroClaw can help debug and fix issues. Access it via:
- **Dashboard:** http://localhost:8080/zeroclaw
- **Command Line:** `cd /root/zeroclaw && ./target/release/zeroclaw agent`

### Common Commands

**Check System Status:**
```bash
curl http://localhost:3000/health | python3 -m json.tool
```

**View ZeroClaw Logs:**
```bash
tail -f /root/zeroclaw/zeroclaw.log
```

**Restart ZeroClaw:**
```bash
pkill -f "zeroclaw daemon"
cd /root/zeroclaw
./target/release/zeroclaw daemon &
```

**Get AI Predictions:**
```bash
curl http://localhost:8080/api/zeroclaw/predictions
```

---

## 🧪 Testing Checklist

### Before Adding Any Real Money:

1. **Dashboard Loads**
   - [ ] http://localhost:8080 shows dashboard
   - [ ] No 500 errors
   - [ ] All navigation links work

2. **Paper Trading Active**
   - [ ] Mode shows "PAPER" in top bar
   - [ ] Cannot switch to LIVE (button disabled)

3. **Testnet Connected**
   - [ ] Binance testnet API key configured
   - [ ] Balance shows test USDT/BTC
   - [ ] Prices updating from testnet

4. **Strategies Configured**
   - [ ] Visit /strategies page
   - [ ] Enable 1-2 strategies for testing
   - [ ] Set small position sizes ($10-50)

5. **ZeroClaw Working**
   - [ ] /zeroclaw page loads
   - [ ] Chat responds to queries
   - [ ] Charts display data
   - [ ] AI predictions generated

6. **Run Paper Trades**
   - [ ] Monitor for 24-48 hours
   - [ ] Check that trades are logged
   - [ ] Verify P&L calculations
   - [ ] Confirm no real money used

---

## 🆘 Troubleshooting

### "Internal Server Error" on Dashboard
```bash
# Check logs
tail -50 /root/trading-bot/dashboard.log

# Restart dashboard
pkill -f "python.*dashboard"
cd /root/trading-bot
python3 dashboard.py
```

### ZeroClaw Not Responding
```bash
# Check if running
ps aux | grep zeroclaw

# Check health
curl http://localhost:3000/health

# Restart
cd /root/zeroclaw
pkill -f "zeroclaw daemon"
./target/release/zeroclaw daemon &
```

### Database Errors
```bash
# Check database
sqlite3 /root/trading-bot/trades.db ".tables"

# Reset if needed (BACKUP FIRST!)
mv trades.db trades.db.backup
touch trades.db
```

### Port Already in Use
```bash
# Kill processes on port 8080
fuser -k 8080/tcp

# Or use different port
python3 dashboard.py --port 8081
```

---

## 🔐 Security Reminders

### NEVER DO THESE:
- ❌ Use mainnet API keys in testing
- ❌ Store real private keys in plain text
- ❌ Share your .env file
- ❌ Run with real money before 7-day paper test
- ❌ Disable stop losses
- ❌ Ignore error alerts

### ALWAYS DO THESE:
- ✅ Use testnet/devnet only for testing
- ✅ Encrypt API keys
- ✅ Set daily loss limits (recommend 5%)
- ✅ Enable all alerts
- ✅ Monitor first 48 hours closely
- ✅ Start with $100 max

---

## 📊 Going Live (After Successful Testing)

### ONLY after 7-day paper test:
1. Create mainnet API keys (small limits!)
2. Deposit $100-500 maximum
3. Set daily loss limit to 5%
4. Enable all safety features
5. Monitor 24/7 for first week
6. Scale up gradually only after proven success

---

## 🎯 Current Status

| Service | Status | URL |
|---------|--------|-----|
| Dashboard | ✅ Running | http://localhost:8080 |
| ZeroClaw AI | ✅ Running | http://localhost:3000 |
| Database | ✅ Ready | trades.db |
| Testnet | 🟡 Configure | See guide above |
| Devnet | 🟡 Configure | See guide above |

---

## 📞 Getting Help

1. **Dashboard Logs:** `/root/trading-bot/dashboard.log`
2. **ZeroClaw Logs:** `/root/zeroclaw/zeroclaw.log`
3. **GitHub:** https://github.com/211skilli211/trading-bot
4. **Test Checklist:** See TESTING_CHECKLIST.md

---

**Last Updated:** 2026-02-20
**Version:** 3.0 Enterprise
