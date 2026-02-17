# 🚀 Trading Bot - Quick Start Guide

## Complete Setup (Choose Your Path)

### Path 1: Full Auto Solana (Proot Ubuntu) - RECOMMENDED

**For**: 20-50 USDT live trading with full automatic execution

```bash
# 1. In main Termux - run automated setup
chmod +x setup_proot.sh
./setup_proot.sh

# 2. Enter Ubuntu
proot-distro login ubuntu

# 3. Inside Ubuntu - activate environment
source ~/botenv/bin/activate
cd ~/trading-bot

# 4. Create .env file
nano .env
# Add: SOLANA_PRIVATE_KEY=your_key_here

# 5. Test
python solana_dex_full.py

# 6. Run bot
python trading_bot.py --mode paper --monitor 60
```

### Path 2: CEX Only (Main Termux)

**For**: Binance/Coinbase trading (no Solana)

```bash
# Install deps
pip install -r requirements.txt

# Create .env
cp .env.example .env
nano .env
# Add your Binance/Coinbase API keys

# Run
python trading_bot.py --mode paper --monitor 60
```

### Path 3: Hybrid (Main Termux + Manual Solana)

**For**: Detection on Termux, manual execution via web wallet

```bash
# Use solana_simple.py for quotes
python solana_simple.py

# When opportunity found, bot sends Telegram alert
# You click link and approve in Phantom/Trust Wallet
```

---

## 📋 Final Launch Checklist

### Pre-Launch (Do These First)

- [ ] Push code to GitHub
  ```bash
  git push origin main
  # OR manually upload files via GitHub web
  ```

- [ ] Choose your path above and complete setup

- [ ] Create Solana wallet (if using Path 1 or 3)
  ```bash
  # In Ubuntu (Path 1):
  python -c "from solathon import Keypair; kp = Keypair(); print(kp.public_key); print(kp.private_key)"
  
  # Or in main Termux (Path 3):
  python solana_simple.py  # generates wallet
  ```

- [ ] Fund wallet
  - Send 20-50 USDT (Solana network) to wallet address
  - Send 0.1 SOL for transaction fees
  - Verify on https://solscan.io

- [ ] Configure .env file
  ```bash
  SOLANA_PRIVATE_KEY=your_private_key_here
  SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
  TELEGRAM_BOT_TOKEN=your_token  # optional
  TELEGRAM_CHAT_ID=your_chat_id  # optional
  ```

### Testing Phase (24-48 hours)

- [ ] Run paper mode
  ```bash
  python trading_bot.py --mode paper --monitor 60
  ```

- [ ] Verify logs
  ```bash
  tail -f trading_bot.log
  ```

- [ ] Test alerts
  - Configure Telegram/Discord in config.json
  - Verify you receive notifications

- [ ] Check dashboard (optional)
  ```bash
  python trading_bot.py --dashboard --port 8080
  ```

### Live Trading (After Successful Testing)

- [ ] Small test first
  ```bash
  # Edit config.json - set small position size
  "risk": {
    "max_position_btc": 0.001,
    "capital_pct_per_trade": 0.02
  }
  
  # Run live with tiny amount
  python trading_bot.py --mode live --monitor 60
  ```

- [ ] Monitor first few trades closely

- [ ] Gradually increase position sizes after profits

### 24/7 Operation

- [ ] Enable auto-start
  ```bash
  # For Path 1 (Ubuntu):
  mkdir -p ~/.termux/boot
  cat > ~/.termux/boot/trading-bot << 'EOF'
  #!/data/data/com.termux/files/usr/bin/sh
  termux-wake-lock
  proot-distro login ubuntu -- bash -c "source ~/botenv/bin/activate && cd ~/trading-bot && python trading_bot.py --mode live --monitor 60 >> ~/bot.log 2>&1" &
  EOF
  chmod +x ~/.termux/boot/trading-bot
  ```

- [ ] Keep phone plugged in

- [ ] Disable battery optimization for Termux

---

## 🔧 Troubleshooting

### "solders not found" in Ubuntu
```bash
# Reinstall inside Ubuntu
source ~/botenv/bin/activate
pip install solders solathon --force-reinstall
```

### "No module named X"
```bash
pip install -r requirements.txt
```

### Push fails (network)
```bash
# Try multiple times
git push origin main

# Or manually upload via GitHub web interface:
# https://github.com/211skilli211/trading-bot/upload
```

### Bot stops when screen off
```bash
# Enable wake lock
termux-wake-lock

# Or add to .termux/boot/trading-bot
```

---

## 📊 Success Metrics

Track these to verify bot health:

| Metric | Target | Check Command |
|--------|--------|---------------|
| Win rate | >40% | Check logs |
| Sharpe ratio | >1.0 | Backtester |
| Max drawdown | <10% | Risk manager |
| Avg latency | <500ms | Execution logs |
| Uptime | >95% | sv status |

---

## 🎯 Next Steps

1. **Today**: Push code, choose path, setup environment
2. **Tomorrow**: Paper trading, verify alerts
3. **Day 3**: Small live test (5-10 USDT)
4. **Week 1**: Scale up if profitable
5. **Week 2**: Optimize parameters based on data

---

## 📞 Support

- GitHub: https://github.com/211skilli211/trading-bot
- Issues: Create GitHub issue for bugs
- Solscan: https://solscan.io (verify transactions)

---

**Ready to launch?** 🚀

Pick your path above and start with Step 1!
