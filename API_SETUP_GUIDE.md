# 🔐 Exchange API Credentials Setup Guide

## Required for CEX Arbitrage

You need API keys from at least 2 exchanges for arbitrage to work.

---

## 📊 EXCHANGE 1: BINANCE (Recommended)

### Step 1: Create API Key
1. Go to: https://www.binance.com/en/my/settings/api-management
2. Click "Create API" → "System-generated"
3. Complete security verification (2FA/SMS)

### Step 2: Configure API Permissions
```
☑️ Enable Reading (required for prices)
☑️ Enable Spot & Margin Trading (required for trades)
☐ Enable Withdrawals (keep OFF for security)
☑️ Restrict access to trusted IPs only (recommended)
```

### Step 3: IP Whitelist (IMPORTANT)
Add your phone's IP address:
```bash
# In Termux, get your IP:
curl ifconfig.me
```

### Step 4: Copy to .env
```
BINANCE_API_KEY=your_actual_key_here
BINANCE_SECRET=your_actual_secret_here
```

⚠️ **Binance requires KYC verification for API access**

---

## 📊 EXCHANGE 2: COINBASE / COINBASE PRO

### Option A: Coinbase Advanced Trade (Recommended)
1. Go to: https://portal.cdp.coinbase.com/access/api
2. Click "Create API Key"
3. Select permissions:
   - `wallet:accounts:read`
   - `wallet:buys:create`
   - `wallet:sells:create`

### Option B: Coinbase Pro (Legacy)
1. Go to: https://pro.coinbase.com/profile/api
2. Create new API key
3. Permissions: View, Trade

### Copy to .env
```
COINBASE_API_KEY=your_actual_key_here
COINBASE_SECRET=your_actual_secret_here
```

---

## 📊 EXCHANGE 3: KRAKEN (Optional but good)

1. Go to: https://www.kraken.com/u/security/api
2. Click "Generate New Key"
3. Permissions needed:
   - Query Funds
   - Query Open Orders & Trades
   - Query Closed Orders & Trades
   - Create & Modify Orders

### Copy to .env
```
KRAKEN_API_KEY=your_actual_key_here
KRAKEN_SECRET=your_actual_secret_here
```

---

## 📊 EXCHANGE 4: BYBIT (Optional)

1. Go to: https://www.bybit.com/app/user/api-management
2. Create API Key
3. Select "System-generated"
4. Permissions: Read, Trade

### Copy to .env
```
BYBIT_API_KEY=your_actual_key_here
BYBIT_SECRET=your_actual_secret_here
```

---

## 📊 EXCHANGE 5: KUCOIN (Optional)

1. Go to: https://www.kucoin.com/account/api
2. Create API
3. Permissions: General, Trade
4. **Note:** KuCoin requires a passphrase

### Copy to .env
```
KUCOIN_API_KEY=your_actual_key_here
KUCOIN_SECRET=your_actual_secret_here
KUCOIN_PASSPHRASE=your_passphrase_here
```

---

## 🔑 BIRDEYE API (For Solana DEX Data)

1. Go to: https://docs.birdeye.so/docs/getting-started
2. Or use public endpoint (rate limited):
   ```
   BIRDEYE_API_KEY=ce39d05c472e40898d05c472e408
   ```
   (This is a demo key - get your own for production)

---

## 🚀 QUICK SETUP SCRIPT

After getting your API keys, run this in Ubuntu proot:

```bash
cd ~/trading-bot
source ~/botenv/bin/activate
python3 << 'PYCODE'
import os

print("Enter your API credentials:")
print("(Leave blank to skip)")
print()

# Collect credentials
creds = {}

creds['BINANCE_API_KEY'] = input("Binance API Key: ").strip()
creds['BINANCE_SECRET'] = input("Binance Secret: ").strip()

creds['COINBASE_API_KEY'] = input("Coinbase API Key: ").strip()
creds['COINBASE_SECRET'] = input("Coinbase Secret: ").strip()

creds['KRAKEN_API_KEY'] = input("Kraken API Key (optional): ").strip()
creds['KRAKEN_SECRET'] = input("Kraken Secret (optional): ").strip()

# Read current .env
with open('.env', 'r') as f:
    content = f.read()

# Update each credential
for key, value in creds.items():
    if value:
        import re
        pattern = rf'{key}=.*'
        replacement = f'{key}={value}'
        content = re.sub(pattern, replacement, content)
        print(f"✅ Updated {key}")

# Write back
with open('.env', 'w') as f:
    f.write(content)

print()
print("✅ All credentials saved to .env")
PYCODE
```

---

## ⚠️ SECURITY BEST PRACTICES

1. **Never share your .env file**
2. **Enable IP restrictions** on all exchange APIs
3. **Disable withdrawals** on API keys (trade-only)
4. **Use 2FA** on all exchange accounts
5. **Regularly rotate** API keys (every 90 days)
6. **Monitor API usage** for unauthorized access

---

## ✅ VERIFICATION

After setting up credentials, test them:

```bash
# In Ubuntu proot
cd ~/trading-bot
source ~/botenv/bin/activate

# Test Binance connection
python3 -c "
import ccxt
import os
from dotenv import load_dotenv
load_dotenv()

exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET'),
    'enableRateLimit': True,
})

try:
    balance = exchange.fetch_balance()
    print(f'✅ Binance connected! Balance: {balance[\"USDT\"][\"free\"]} USDT')
except Exception as e:
    print(f'❌ Binance error: {e}')
"
```

---

## 📞 NEED HELP?

If you get API errors:
1. Check IP whitelist includes your current IP
2. Verify API permissions include "Trading"
3. Ensure account is KYC verified (Binance)
4. Check if API key is still valid (not expired)
5. Verify system time is correct (important for signatures)
