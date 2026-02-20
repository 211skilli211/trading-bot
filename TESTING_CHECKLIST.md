# Trading Bot - Pre-Funding Testing Checklist

## ⚠️ IMPORTANT: DO NOT ADD REAL MONEY UNTIL ALL TESTS PASS

This checklist ensures all bot features work correctly in **PAPER TRADING MODE** before any real funds are deposited.

---

## ✅ Phase 1: System Status

### ZeroClaw AI
- [ ] ZeroClaw daemon running (`curl http://localhost:3000/health`)
- [ ] ZeroClaw onboarded (`zeroclaw onboard` completed)
- [ ] AI status shows "Online" in dashboard
- [ ] Can chat with ZeroClaw via web interface

### Dashboard
- [ ] Dashboard loads without errors (`http://localhost:8080/`)
- [ ] All navigation links work
- [ ] No 500 Internal Server Errors on any page

### Database
- [ ] SQLite database accessible
- [ ] Can read/write trades
- [ ] Alert history functional

---

## ✅ Phase 2: Paper Trading Mode

### Configuration
- [ ] Mode set to **PAPER** in Config page
- [ ] Cannot switch to LIVE without wallet funded check
- [ ] Paper trading indicators visible on all pages

### Strategy Configuration
- [ ] Visit `/strategies` page
- [ ] Each strategy shows correct configuration
- [ ] Can toggle strategies on/off
- [ ] Can edit strategy parameters
- [ ] AI recommendations visible
- [ ] Changes persist after refresh

### Test Each Strategy in Paper Mode:
1. **Binary Arbitrage**
   - [ ] Monitors spread between exchanges
   - [ ] Logs opportunity detection
   - [ ] Simulates trades (no real money)

2. **15-Min Sniper**
   - [ ] Monitors 15m timeframe
   - [ ] Detects momentum breakouts
   - [ ] Paper trades executed

3. **Momentum Trader**
   - [ ] Moving average calculations working
   - [ ] Trend detection functional
   - [ ] Entry/exit signals generated

4. **Mean Reversion**
   - [ ] RSI calculations working
   - [ ] Overbought/oversold detection
   - [ ] Signals generated correctly

5. **Grid Trading**
   - [ ] Grid levels calculated
   - [ ] Buy/sell orders simulated
   - [ ] Range detection working

6. **Pairs Trading**
   - [ ] Correlation calculations
   - [ ] Z-score monitoring
   - [ ] Pair selection working

---

## ✅ Phase 3: Multi-Agent System

### Agent Status
- [ ] All 6 default agents visible
- [ ] ArbBot, SniperBot, ContrarianBot, MomentumBot, PairsBot, YOLOBot
- [ ] Status indicators show correctly
- [ ] P&L tracking working

### Consensus System
- [ ] Swarm consensus calculated
- [ ] Agent votes displayed
- [ ] Confidence scores shown
- [ ] Signal history logging

### Custom Agents
- [ ] Can create custom agent
- [ ] Natural language prompt accepted
- [ ] Skill file upload works
- [ ] Custom agent appears in list
- [ ] Can activate/deactivate custom agents

---

## ✅ Phase 4: Risk Management

### Position Limits
- [ ] Max position size enforced
- [ ] Exposure calculations correct
- [ ] Daily loss limits working

### Stop Loss / Take Profit
- [ ] SL/TP levels calculated correctly
- [ ] Triggers logged (not executed with real money in paper)
- [ ] Risk dashboard shows current exposure

### Circuit Breaker
- [ ] Failure detection working
- [ ] Auto-shutdown after threshold
- [ ] Recovery mechanism tested

---

## ✅ Phase 5: Alerts & Notifications

### Alert Generation
- [ ] Trade executed alerts
- [ ] Arbitrage opportunity alerts  
- [ ] Stop loss / take profit alerts
- [ ] Error alerts
- [ ] AI signal alerts

### Alert Management
- [ ] Mark as read works
- [ ] Delete alert works
- [ ] Clear all works
- [ ] Settings save correctly

---

## ✅ Phase 6: Exchange Connectivity (TESTNET ONLY)

### Binance Testnet
- [ ] API key configured for TESTNET
- [ ] Connection test passes
- [ ] Price data received
- [ ] **NO REAL MONEY AT RISK**

### Paper Trading Simulation
- [ ] Orders simulated, not sent to exchange
- [ ] P&L calculated from simulated fills
- [ ] Latency measured
- [ ] Slippage estimated

---

## ✅ Phase 7: Solana DEX (Devnet ONLY)

### Jupiter Integration
- [ ] Connected to Jupiter API
- [ ] Quote fetching works
- [ ] **Using DEVNET, not mainnet**
- [ ] No real SOL at risk

### Transaction Simulation
- [ ] All transactions simulated first
- [ ] Priority fees calculated
- [ ] Slippage protection active
- [ ] No real transactions without explicit confirmation

---

## ✅ Phase 8: ZeroClaw AI Features

### Chart Analysis
- [ ] Price charts loading
- [ ] Timeframe switching (1H/24H/7D/30D)
- [ ] AI predictions displayed
- [ ] Indicators working (SMA, RSI, Volume)

### Predictions
- [ ] AI generates buy/sell signals
- [ ] Confidence scores shown
- [ ] Target prices estimated
- [ ] Stop loss recommendations

### Chat Interface
- [ ] Can ask about prices
- [ ] Can request market analysis
- [ ] Can get portfolio insights
- [ ] Can create custom strategies via chat

---

## ✅ Phase 9: Backtesting

### Historical Testing
- [ ] Can run backtest on each strategy
- [ ] Results show returns, win rate, sharpe ratio
- [ ] Different timeframes testable
- [ ] Multiple symbols supported

### Paper Trade Results
- [ ] 7-day paper trading history visible
- [ ] P&L tracked correctly
- [ ] Win/loss ratio calculated
- [ ] No real money lost in testing

---

## ✅ Phase 10: Security Checks

### API Key Security
- [ ] Keys encrypted at rest
- [ ] No keys in logs
- [ ] Keys not exposed in UI
- [ ] Secure key rotation possible

### Access Control
- [ ] Dashboard password protected (if configured)
- [ ] No unauthorized access
- [ ] Session management working

---

## 🚫 LIVE TRADING CHECKLIST (Only After All Above Pass)

### Before Going Live:
- [ ] Minimum $100 in exchange account (start small!)
- [ ] Verified withdrawal works
- [ ] Tested with $1 trade first
- [ ] Stop losses configured
- [ ] Daily loss limit set (recommend 5% max)
- [ ] Alerts configured for all events
- [ ] Can monitor 24/7 or have auto-shutdown

### Emergency Procedures Tested:
 [ ] Emergency stop button works
- [ ] Can close all positions quickly
- [ ] Can disable all strategies instantly
- [ ] Can switch back to paper mode

---

## 📊 Expected Paper Trading Results (7 Days)

Before going live, you should see:
- **Minimum 50 paper trades** executed
- **Win rate tracked** (aim for >50%)
- **P&L calculated** (positive or negative, just need data)
- **All strategies tested** at least once
- **No system crashes** for 7 days

---

## 📝 Current Test Status

Last Updated: 2026-02-20

| Component | Status | Notes |
|-----------|--------|-------|
| ZeroClaw AI | 🟡 Running | Onboarded, needs pairing |
| Dashboard | 🟢 Operational | All pages functional |
| Paper Trading | 🟢 Ready | Mode enforced |
| Multi-Agent | 🟢 Ready | 6 agents active |
| Risk Mgmt | 🟢 Ready | Limits configured |
| Alerts | 🟢 Ready | Real data from DB |
| Strategies | 🟢 Ready | AI recommendations active |
| Solana DEX | 🟡 Devnet | Ready for testing |

---

## 🎯 NEXT STEPS

1. **Run 7-day paper trading test**
2. **Document all results**
3. **Tune strategy parameters based on results**
4. **Only then consider small live test ($10-50)**
5. **Gradually increase after proven success**

---

**REMEMBER: Never risk money you can't afford to lose!**
