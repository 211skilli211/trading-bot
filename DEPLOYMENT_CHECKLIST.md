# Trading Bot Deployment Checklist
# ==================================

## Render Account
- User: 211skilli211
- Render API key: (REDACTED — stored in ~/.hermes/.env)

## Services to Deploy
1. **trading-bot** (web) — REST API at /api/v1/* endpoints
2. **trading-bot-worker** (worker) — Paper trading loop every 30s
3. **daily-summary** (cron) — Daily report at 9AM UTC

## Required Credentials (ALL MISSING — need from user)

### Exchange API Keys (pick one or more):
- [ ] BINANCE_API_KEY — Your Binance API key
- [ ] BINANCE_SECRET — Your Binance API secret
- [ ] KRAKEN_API_KEY — Your Kraken API key
- [ ] KRAKEN_SECRET — Your Kraken API secret
- [ ] COINBASE_API_KEY — Coinbase API key (optional)
- [ ] COINBASE_SECRET — Coinbase API secret (optional)

### Solana:
- [ ] SOLANA_PRIVATE_KEY — Base58 private key for DEX trading (optional, paper mode works without)

### Notifications:
- [ ] DISCORD_WEBHOOK_URL — Discord webhook for trade alerts
- [ ] TELEGRAM_BOT_TOKEN — Telegram bot token for alerts
- [ ] TELEGRAM_CHAT_ID — Telegram chat ID for alerts

### Data Sources:
- [ ] LUNARCRUSH_API_KEY — Social sentiment data
- [ ] NEWS_API_KEY — News articles for sentiment
- [ ] TWITTER_BEARER_TOKEN — Twitter API for sentiment

## Deployment Steps
1. User provides credentials (or subset to start)
2. Create Render env var group via API: `render apis create-env-var-group`
3. Set each env var via API or Render dashboard
4. Trigger deploy: main branch auto-deploys on push
5. Verify: curl https://trading-bot.onrender.com/api/v1/status

## Notes
- Bot runs in PAPER mode by default (no real money at risk)
- Start with Binance only (most liquid, best API)
- Notifications optional (bot works without them)
- Solana optional (CEX arbitrage works without it)
- Free plan: 750 hours/month, sleeps after 15min inactivity
