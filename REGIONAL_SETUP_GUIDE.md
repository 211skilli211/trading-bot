# 🌍 Regional Setup Guide (Coinbase Unavailable)

## Your IP Address: 199.21.164.56
*(This may change if you switch networks)*

---

## ✅ BINANCE SETUP (Your Primary Exchange)

### Step 1: API Permissions
```
☑️ Enable Reading
☑️ Enable Spot & Margin Trading
☐ Enable Margin Loan, Repay & Transfer
☐ Permits Universal Transfer  
☐ Enable Withdrawals (KEEP OFF FOR SECURITY)
☐ Enable Symbol Whitelist (optional)
```

### Step 2: IP Restrictions
```
☑️ Restricted (Recommended)
IP Address: 199.21.164.56
```

⚠️ **IMPORTANT**: Since you're on mobile, your IP may change when switching between WiFi and mobile data. You may need to update this in Binance if you get "Invalid IP" errors.

---

## ✅ KRAKEN SETUP (Your Secondary Exchange)

### API Permissions
```
Funds:
  ☑️ Query

Orders and Trades:
  ☑️ Query open orders & trades
  ☑️ Query closed orders & trades
  ☑️ Create & modify orders
  ☑️ Cancel & close orders

WebSocket Interface:
  ☑️ Allow WebSocket connections
```

---

## 🔄 ALTERNATIVE EXCHANGES (Recommended)

### Bybit (Best Coinbase Alternative)
- **URL**: https://www.bybit.com/app/user/api-management
- **Availability**: Most countries
- **Permissions**: Read + Trade (no withdrawals)
- **IP Restriction**: Recommended

### KuCoin (Good Backup)
- **URL**: https://www.kucoin.com/account/api
- **Availability**: Global
- **Permissions**: General + Trade
- **Note**: Requires passphrase in addition to key/secret

---

## 📊 RECOMMENDED COMBINATIONS

### Minimum (Start here):
- ✅ Binance
- ✅ Kraken

### Better (Add Bybit):
- ✅ Binance
- ✅ Kraken
- ✅ Bybit

### Optimal (All 4):
- ✅ Binance
- ✅ Kraken
- ✅ Bybit
- ✅ KuCoin

More exchanges = more arbitrage opportunities!

---

## ⚠️ MOBILE IP CONSIDERATIONS

Since you're running on Android/Termux:

1. **Static IP Option**: Use your home WiFi (IP rarely changes)
2. **Mobile Data**: IP changes frequently - you'll need to update Binance
3. **Solution**: Get API keys for all 3-4 exchanges, then use the ones that work with your current IP

---

## 🚀 QUICK START

After getting your keys:

```bash
proot-distro login ubuntu
cd ~/trading-bot
python setup_credentials.py
```

Enter:
- Binance API Key + Secret
- Kraken API Key + Secret
- Bybit API Key + Secret (optional but recommended)
