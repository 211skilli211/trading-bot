# 🤖 Modular Trading Bot

A transparent, ethical, and modular trading bot built in Python. Designed with safety-first principles, comprehensive audit logging, and clean separation of concerns.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      TRADING BOT SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │  DATA LAYER │───→│   STRATEGY  │───→│    RISK     │        │
│   │             │    │   ENGINE    │    │  MANAGER    │        │
│   │ • Binance   │    │             │    │             │        │
│   │ • Coinbase  │    │ • Arbitrage │    │ • Position  │        │
│   │ • Logging   │    │ • Analysis  │    │   Limits    │        │
│   │             │    │ • Signals   │    │ • Stop-Loss │        │
│   └─────────────┘    └─────────────┘    └──────┬──────┘        │
│                                                  │              │
│                                                  ▼              │
│                                          ┌─────────────┐        │
│                                          │  EXECUTION  │        │
│                                          │   LAYER     │        │
│                                          │             │        │
│                                          │ • Paper Mode│        │
│                                          │ • Live Mode │        │
│                                          │ • Latency   │        │
│                                          └──────┬──────┘        │
│                                                  │              │
│                                                  ▼              │
│                                          ┌─────────────┐        │
│                                          │  AUDIT LOG  │        │
│                                          │  (JSONL)    │        │
│                                          └─────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

| File | Purpose | Lines |
|------|---------|-------|
| `trading_bot.py` | Main orchestrator - ties all layers together | ~400 |
| `crypto_price_fetcher.py` | Data Layer - exchange connectors | ~350 |
| `strategy_engine.py` | Strategy Engine - arbitrage logic | ~400 |
| `risk_manager.py` | Risk Manager - safety controls | ~550 |
| `execution_layer.py` | Execution Layer - order placement | ~550 |

## Quick Start

### 1. Single Run (Paper Mode)
```bash
python trading_bot.py --mode paper
```

### 2. Continuous Monitoring
```bash
python trading_bot.py --mode paper --monitor 60
```

### 3. Run All Tests
```bash
python trading_bot.py --test
```

## Usage Examples

### Basic Usage
```bash
# Single execution (paper mode)
python trading_bot.py

# Custom log file
python trading_bot.py --log my_trades.log

# Continuous monitoring every 30 seconds
python trading_bot.py --monitor 30
```

### Configuration File
Create `config.json`:
```json
{
  "strategy": {
    "fee_rate": 0.001,
    "slippage": 0.0005,
    "min_spread": 0.002
  },
  "risk": {
    "max_position_btc": 0.05,
    "stop_loss_pct": 0.02,
    "capital_pct_per_trade": 0.05,
    "initial_balance": 10000
  }
}
```

Run with config:
```bash
python trading_bot.py --config config.json
```

### Live Trading (⚠️ Use with Caution)
```bash
# Set environment variables
export BINANCE_API_KEY="your_key"
export BINANCE_SECRET="your_secret"
export COINBASE_API_KEY="your_key"
export COINBASE_SECRET="your_secret"

# Run in live mode
python trading_bot.py --mode live
```

## System Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Fetch Prices│────→│   Strategy  │────→│    Risk     │────→│  Execute    │
│             │     │   Signal    │     │   Check     │     │   Trade     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   trading_bot.log   │
                        │   (JSON Lines)      │
                        └─────────────────────┘
```

## Module Details

### 1. Data Layer (`crypto_price_fetcher.py`)
- **BinanceConnector**: Fetches BTC/USDT via REST API
- **CoinbaseConnector**: Fetches BTC/USD via REST API
- **AuditLogger**: Structured JSONL logging
- **SpreadCalculator**: Basic spread analysis

### 2. Strategy Engine (`strategy_engine.py`)
- **ArbitrageStrategy**: Main strategy wrapper
- **StrategyEngine**: Spread analysis & signal generation
- **PaperTrade**: Simulated trade tracking
- **TradeSignal**: Structured signal output

**Threshold Calculation:**
```
Total Cost = (fee_rate × 2) + (slippage × 2) + min_spread
Default: 0.3% + 0.2% = 0.5% minimum spread required
```

### 3. Risk Manager (`risk_manager.py`)
- **Position Limits**: Max 0.05 BTC per trade (configurable)
- **Stop-Loss**: Automatic exit at 2% loss
- **Capital Allocation**: Risk 5% of balance per trade
- **Exposure Limits**: Max 30% in open positions
- **Daily Loss Limit**: Halt trading after 5% daily loss

### 4. Execution Layer (`execution_layer.py`)
- **Paper Mode**: Simulates trades, tracks P&L
- **Live Mode**: Placeholder for real API calls
- **Retry Logic**: Exponential backoff for failures
- **Latency Tracking**: Signal → Execution timing

## Sample Output

```
======================================================================
🤖 TRADING BOT - End-to-End Orchestrator
======================================================================
✅ Data Layer initialized
✅ Strategy Engine initialized
✅ Risk Manager initialized
✅ Execution Layer initialized

📊 Configuration:
   Mode: PAPER
   Log File: trading_bot.log

======================================================================
🔄 TRADING CYCLE #1
======================================================================

📡 STEP 1: Fetching Market Data...
   ✓ Binance: $68,638.77
   ✓ Coinbase: $68,601.18

🧠 STEP 2: Strategy Engine Analysis...
   Decision: TRADE
   Reason: Spread 1.47% > 0.5% threshold
   Spread: 1.4706%

🛡️  STEP 3: Risk Management Check...
   Decision: APPROVE
   Reason: Trade approved: 0.0074 BTC @ $68,000.00
   Position Size: 0.0074 BTC
   Risk Level: LOW

🚀 STEP 4: Execution Layer...
📊 PAPER TRADE EXECUTED: TRADE_0001
   Buy:  0.0074 BTC on Binance @ $68,011.05
   Sell: 0.0074 BTC on Coinbase @ $68,988.79
   Fees: $1.01
   Net P&L: $6.22
   Latency: 253.1ms

📝 Cycle logged to trading_bot.log
⏱️  Total Cycle Time: 1100.2ms
```

## Audit Logging

All activities are logged to JSONL files:

```json
{
  "timestamp": "2026-02-16T22:56:54.483192+00:00Z",
  "type": "TRADE_CYCLE",
  "data": {
    "cycle": 1,
    "mode": "paper",
    "prices": [...],
    "strategy": {...},
    "risk": {...},
    "execution": {...}
  }
}
```

Log types:
- `PRICE_CHECK` - Raw price data
- `STRATEGY_DECISION` - Strategy signals
- `RISK_DECISION` - Risk assessments
- `TRADE_CYCLE` - Complete cycle records

## Safety Features

1. **Paper Mode Default**: All trades are simulated by default
2. **Daily Loss Limits**: Trading halts after 5% daily loss
3. **Position Limits**: Caps exposure per trade
4. **Stop-Loss**: Automatic position closure
5. **Comprehensive Logging**: Full audit trail
6. **No Hardcoded Keys**: API keys via environment only

## Security Checklist

Before enabling live trading:

- [ ] Tested thoroughly in paper mode
- [ ] API keys stored securely (environment variables)
- [ ] Withdrawal permissions disabled on API keys
- [ ] IP whitelisting enabled on exchanges
- [ ] Small position sizes configured
- [ ] Daily loss limits set appropriately
- [ ] Monitoring and alerting in place

## Testing Individual Modules

```bash
# Test Strategy Engine
python strategy_engine.py

# Test Risk Manager
python risk_manager.py

# Test Execution Layer
python execution_layer.py

# Test all modules
python trading_bot.py --test
```

## Future Enhancements

- [ ] WebSocket feeds for lower latency
- [ ] Multi-pair arbitrage (triangular)
- [ ] More exchanges (Kraken, Bybit, etc.)
- [ ] Machine learning signal enhancement
- [ ] Web dashboard for monitoring
- [ ] Telegram/Discord alerts
- [ ] Database storage for analytics

## License

MIT License - Use at your own risk. Trading cryptocurrencies carries significant risk of loss.

## Disclaimer

This software is for educational purposes only. Cryptocurrency trading involves substantial risk. Always:
- Start with paper trading
- Use funds you can afford to lose
- Consult with financial advisors
- Understand the risks before trading


---

## 🆕 New Features (February 2026)

### Enhanced Execution Layer V2
- **Partial Fill Handling**: Automatic retry for unfilled order portions
- **Arbitrage Reconciliation**: Recovers from failed trade legs, closes orphaned positions
- **Enhanced Monitoring**: Real-time trade status tracking
- **Background Worker**: Automatic reconciliation queue processing

### WebSocket Price Feeds
- **Low Latency**: Real-time price data from Binance and Coinbase
- **Order Book Depth**: Track market depth for accurate slippage calculation
- **Automatic Reconnection**: Exponential backoff for connection failures
- **Arbitrage Detection**: Real-time opportunity scanning

### Solana DEX Enhanced
- **MEV Protection**: Jito bundle submission for front-running protection
- **Dynamic Priority Fees**: Automatic fee adjustment based on network congestion
- **Transaction Simulation**: Pre-execution validation to prevent failures
- **Slippage Protection**: Configurable bounds with price impact checking

### Testing & CI/CD
- **Comprehensive Test Suite**: pytest coverage for all major components
- **GitHub Actions**: Automated testing, linting, security scanning
- **Docker Support**: Containerized deployment with docker-compose
- **Security Scanning**: Bandit and Safety integration

### Mobile-Optimized UI
- **Responsive Design**: Mobile-first approach with bottom navigation
- **Touch Gestures**: Pull-to-refresh, swipe navigation, touch feedback
- **Floating Action Button**: Quick access to common actions
- **Optimized Controls**: 44px minimum touch targets

### Files Added
```
execution_layer_v2.py       # Enhanced execution with reconciliation
websocket_price_feed.py     # Low-latency price feeds
solana_dex_enhanced.py      # MEV-protected DEX trading
tests/                      # Comprehensive test suite
.github/workflows/ci.yml    # CI/CD pipeline
Dockerfile                  # Container build
docker-compose.yml          # Full stack deployment
static/css/mobile.css       # Mobile styles
static/js/mobile.js         # Mobile interactions
```

See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for detailed documentation.
