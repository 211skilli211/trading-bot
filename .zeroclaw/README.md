# ZeroClaw AI Trading System

A comprehensive AI-controlled trading system powered by ZeroClaw agent with OpenRouter LLM integration.

## Architecture

```
User → Dashboard → AI Agent → Tool Executor → Trading Engine
                   ↓
            OpenRouter LLM (arcee-ai/trinity-large-preview:free)
                   ↓
            Tool Results → Natural Language Response
```

## Components

### 1. AI Agent (`ai_agent.py`)
- **Purpose**: Natural language interface for trading operations
- **Model**: OpenRouter with arcee-ai/trinity-large-preview:free
- **Features**:
  - Intent detection for trading commands
  - Tool execution and result formatting
  - Conversation history tracking
  - Natural language responses

### 2. Trading Engine (`trading_engine.py`)
- **Purpose**: Execute trades and manage positions
- **Mode**: Paper trading (practice mode)
- **Features**:
  - Buy/sell orders (market/limit)
  - Position tracking
  - Balance management
  - Trade history with P&L
  - SQLite database storage

### 3. Arbitrage Engine (`arbitrage_engine.py`)
- **Purpose**: Scan and execute arbitrage opportunities
- **Exchanges**: CoinGecko, Binance, Coinbase, KuCoin, OKX
- **Features**:
  - Real-time price scanning
  - Spread detection (default 0.3% threshold)
  - Profit calculation
  - Opportunity tracking

### 4. Multi-Bot Controller (`multi_bot_controller.py`)
- **Purpose**: Coordinate multiple trading bots
- **Strategies**: Arbitrage, Momentum, Mean Reversion, Grid, DCA
- **Features**:
  - Bot creation/management
  - Start/stop control
  - Strategy assignment
  - Bot coordination (start_all, stop_all, report)

### 5. Telegram Notifier (`telegram_notifier.py`)
- **Purpose**: Send notifications and alerts
- **Features**:
  - Trade notifications
  - Price alerts
  - Arbitrage alerts
  - Bot status updates
  - Alert management

### 6. Tool Executor (`tool_executor.py`)
- **Purpose**: Bridge between AI agent and tools
- **Tools**:
  - trading_engine
  - arbitrage_scanner
  - portfolio_manager
  - price_fetcher
  - telegram_notifier
  - multi_bot_controller

## Dashboard API Endpoints

### Trading API
```
POST /api/trading/execute       - Execute trade (buy/sell)
GET  /api/trading/positions     - Get open positions
GET  /api/trading/balance       - Get account balance
GET  /api/trading/history       - Get trade history
GET  /api/trading/portfolio     - Get full portfolio summary
```

### Arbitrage API
```
GET /api/arbitrage/scan         - Scan for opportunities
GET /api/arbitrage/stats        - Get arbitrage statistics
```

### Bot Control API
```
GET    /api/bots/list           - List all bots
POST   /api/bots/create         - Create new bot
POST   /api/bots/<id>/start     - Start a bot
POST   /api/bots/<id>/stop      - Stop a bot
POST   /api/bots/coordinate     - Coordinate all bots
```

### AI Agent API
```
POST /api/zeroclaw/chat         - AI chat with tool integration
POST /api/ai/tools              - Direct tool execution
```

### Notifications API
```
POST /api/notifications/send    - Send Telegram notification
```

## Usage Examples

### AI Chat Commands
```bash
# Buy cryptocurrency
curl -X POST http://localhost:8080/api/zeroclaw/chat \
  -d '{"message":"Buy 0.01 BTC"}'

# Check price
curl -X POST http://localhost:8080/api/zeroclaw/chat \
  -d '{"message":"What is ETH price?"}'

# View portfolio
curl -X POST http://localhost:8080/api/zeroclaw/chat \
  -d '{"message":"Show my portfolio"}'

# Scan arbitrage
curl -X POST http://localhost:8080/api/zeroclaw/chat \
  -d '{"message":"Find arbitrage opportunities"}'

# List bots
curl -X POST http://localhost:8080/api/zeroclaw/chat \
  -d '{"message":"Show my trading bots"}'
```

### Direct Trading
```bash
# Execute trade
curl -X POST http://localhost:8080/api/trading/execute \
  -d '{"action":"buy","symbol":"BTC","amount":0.01}'

# Check balance
curl http://localhost:8080/api/trading/balance

# Get positions
curl http://localhost:8080/api/trading/positions
```

### Bot Management
```bash
# Create bot
curl -X POST http://localhost:8080/api/bots/create \
  -d '{"name":"Arbitrage Bot 1","strategy":"arbitrage","symbols":["BTC","ETH"]}'

# Start all bots
curl -X POST http://localhost:8080/api/bots/coordinate \
  -d '{"action":"start_all"}'

# Get bot report
curl -X POST http://localhost:8080/api/bots/coordinate \
  -d '{"action":"report"}'
```

## Configuration

### ZeroClaw Config (`config.toml`)
- **Provider**: OpenRouter
- **Model**: arcee-ai/trinity-large-preview:free
- **Mode**: Supervised (requires approval for medium/high risk)
- **Trading**: Paper mode (practice)
- **Tools**: 6 trading tools enabled

### Trading Parameters
- **Initial Balance**: $10,000 USDT
- **Trading Mode**: Paper (simulated)
- **Fee Rate**: 0.1% per trade
- **Min Arbitrage Spread**: 0.3%

## Data Storage

### SQLite Databases
- `trading.db` - Trades, positions, balance
- `arbitrage.db` - Opportunities, executions
- `bots.db` - Bot configurations, logs
- `notifications.db` - Alert history

### File Locations
```
/tmp/trading_zeroclaw/.zeroclaw/
├── trading.db
├── arbitrage.db
├── bots.db
├── notifications.db
├── workspace/portfolio/
├── logs/
└── config.toml
```

## Security

### Paper Trading Mode
- All trades are simulated
- No real funds at risk
- Perfect for testing strategies

### Required Approvals
- Medium risk commands require approval
- High risk commands blocked by default
- Trading mode can be set per request

### API Key Storage
- OpenRouter API key in environment
- Telegram bot token in config
- Encrypted secrets support

## Telegram Integration

### Bot Commands
```
/price <symbol>     - Check price
/buy <symbol> <amt> - Buy crypto
/sell <symbol> <amt>- Sell crypto
/portfolio          - View portfolio
/arbitrage          - Scan opportunities
/bots               - List bots
/status             - System status
```

### Notifications
- Trade executions
- Price alerts
- Arbitrage opportunities
- Bot status changes

## Monitoring

### Dashboard Metrics
- Portfolio value & P&L
- Open positions
- Recent trades
- Bot status
- Arbitrage opportunities

### Logs
- `/tmp/trading_zeroclaw/.zeroclaw/logs/`
- Trade execution logs
- Bot activity logs
- Error logs

## Future Enhancements

### Planned Features
1. Live trading mode (with API keys)
2. More exchanges integration
3. Advanced charting
4. Backtesting engine
5. Machine learning signals
6. Copy trading
7. Social trading features

### Strategy Ideas
1. Momentum trading
2. Grid trading
3. DCA (Dollar Cost Averaging)
4. Mean reversion
5. Breakout trading
6. News-based trading

## Support

### Troubleshooting
1. Check ZeroClaw daemon is running
2. Verify OpenRouter API key
3. Check Telegram bot token
4. Review logs for errors

### Logs Location
```bash
# Dashboard logs
tail -f /tmp/dashboard.log

# ZeroClaw logs
tail -f /tmp/trading_zeroclaw/.zeroclaw/zeroclaw.log

# Trading engine logs
tail -f /tmp/trading_zeroclaw/.zeroclaw/logs/trading.log
```

## License

MIT License - For educational and personal use.

**Warning**: Cryptocurrency trading involves significant risk. Always use paper trading mode to practice before risking real funds.
