# ZeroClaw AI & Strategy Agents - Complete Guide

## How ZeroClaw Works

### Current Status
```
✅ ZeroClaw Daemon: Running (PID 31133)
✅ Gateway: Port 3000 active
✅ Health: OK (57,788 seconds uptime)
⚠️  Paired: NO (Need pairing code to use AI chat)
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ZEROCLAW AI SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │  ZeroClaw Core   │      │  Python Trading  │                 │
│  │  (Rust)          │◄────►│  Bot (Flask)     │                 │
│  │                  │ HTTP │                  │                 │
│  │  ┌────────────┐  │ API  │  ┌────────────┐  │                 │
│  │  │  Gateway   │  │      │  │ Dashboard  │  │                 │
│  │  │  Port 3000 │  │      │  │  Port 8080 │  │                 │
│  │  └────────────┘  │      │  └────────────┘  │                 │
│  │                  │      │                  │                 │
│  │  ┌────────────┐  │      │  ┌────────────┐  │                 │
│  │  │  Skills    │  │      │  │ Strategies │  │                 │
│  │  │  • Price   │  │      │  │  • Arbitrage│ │                 │
│  │  │  • Scan    │  │      │  │  • Sniper   │ │                 │
│  │  │  • Trade   │  │      │  │  • Multi    │ │                 │
│  │  │  • Portfolio│ │      │  │     Agent   │ │                 │
│  │  └────────────┘  │      │  └────────────┘  │                 │
│  │                  │      │                  │                 │
│  │  ┌────────────┐  │      │  ┌────────────┐  │                 │
│  │  │  Memory    │  │      │  │  ML Pred   │  │                 │
│  │  │  SQLite    │  │      │  │  sklearn   │  │                 │
│  │  └────────────┘  │      │  └────────────┘  │                 │
│  │                  │      │                  │                 │
│  └──────────────────┘      └──────────────────┘                 │
│           │                           │                         │
│           └───────────┬───────────────┘                         │
│                       ▼                                         │
│          ┌─────────────────────────┐                            │
│          │   Shared Database       │                            │
│          │   trades.db             │                            │
│          └─────────────────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## ZeroClaw Skills (AI Agents)

### 1. Price-Check Skill
**Purpose:** Fetch cryptocurrency prices via AI

**Triggers:**
- "What's the price of BTC?"
- "Check SOL price"
- "How much is Ethereum?"

**How it works:**
1. User sends message to ZeroClaw (via Telegram or API)
2. AI parses the coin symbol
3. Skill fetches from CoinGecko/Binance
4. Returns formatted price

**Integration with ML:**
- Can combine with ML predictions: "BTC is $67k, ML predicts UP with 80% confidence"

### 2. Arbitrage-Scan Skill
**Purpose:** Find arbitrage opportunities

**Triggers:**
- "Scan for arbitrage"
- Heartbeat every 5 minutes (automatic)
- Manual button click

**How it works:**
1. Scans DEX vs CEX prices
2. Calculates spreads
3. Identifies opportunities >0.5%
4. Logs to shared database
5. Alerts via Telegram

**Integration with Strategies:**
- Uses same logic as `strategies/binary_arbitrage.py`
- Can trigger automatic execution with approval

### 3. Trade-Execute Skill
**Purpose:** Execute trades with AI oversight

**Triggers:**
- "Buy 100 SOL"
- "Sell half my BTC"

**How it works:**
1. AI parses intent
2. Calculates position size
3. Checks risk limits
4. **Requires approval** (supervised mode)
5. Executes via Python bot
6. Logs trade

### 4. Portfolio-Check Skill
**Purpose:** Analyze portfolio with AI insights

**Triggers:**
- "Show my portfolio"
- "How am I doing?"
- "Analyze my trades"

**How it works:**
1. Fetches positions from database
2. Calculates P&L
3. AI analyzes patterns
4. Suggests improvements
5. Identifies risks

## Strategy Agents (Python Side)

### Current Strategies

| Strategy | File | Purpose | ML Integration |
|----------|------|---------|----------------|
| **Arbitrage** | `strategies/binary_arbitrage.py` | Find YES/NO price discrepancies on PolyMarket | Can use ML for confidence scoring |
| **Sniper** | `strategies/sniper.py` | Quick momentum trades | Uses ML trend predictions |
| **Multi-Agent** | `strategies/multi_agent.py` | 6 competing agents, best performer wins | Each agent can use different ML models |

### How Strategies Work with ML

```
┌─────────────────────────────────────────┐
│         STRATEGY + ML FLOW              │
├─────────────────────────────────────────┤
│                                          │
│  1. Strategy scans for opportunities    │
│           ↓                              │
│  2. ML Predictor analyzes trend         │
│     • Direction (UP/DOWN/SIDEWAYS)      │
│     • Confidence score                  │
│     • Price prediction                  │
│           ↓                              │
│  3. Strategy combines signals           │
│     IF arbitrage_opportunity AND        │
│        ML_trend == "UP" AND             │
│        ML_confidence > 70%:             │
│           EXECUTE_TRADE                 │
│           ↓                              │
│  4. Risk Manager validates              │
│           ↓                              │
│  5. Execution Layer trades              │
│           ↓                              │
│  6. ZeroClaw logs to memory             │
│     • Trade details                     │
│     • ML prediction accuracy            │
│     • Strategy performance              │
└─────────────────────────────────────────┘
```

## Integration: Where Agents Should Work Together

### Current Separation (Suboptimal)
```
❌ ZeroClaw Skills    → Standalone AI responses
❌ Python Strategies  → Standalone execution
❌ ML Predictions     → Only in trading_bot.py
```

### Proposed Integration (Optimal)
```
✅ Unified Agent System

┌─────────────────────────────────────────────────────┐
│           UNIFIED AI/ML/STRATEGY LAYER              │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────┐ │
│  │  ZeroClaw   │◄──►│  ML Models  │◄──►│Strategies│ │
│  │  AI Brain   │    │  sklearn    │    │  Engine  │ │
│  └─────────────┘    └─────────────┘    └─────────┘ │
│         │                   │                │      │
│         └───────────────────┴────────────────┘      │
│                         │                          │
│                    ┌─────────┐                     │
│                    │  Bot    │                     │
│                    │ Decision│                     │
│                    │ Engine  │                     │
│                    └─────────┘                     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## How to Integrate Everything into ML Section

### Option 1: ML Dashboard Shows All Agents
```
/ML Page Should Show:
├── ML Predictions (current)
│   ├── BTC: UP 80% → $71k
│   └── ETH: DOWN 65% → $1.8k
├── ZeroClaw AI Insights
│   └── "BTC showing bullish divergence, consider long"
├── Strategy Agent Status
│   ├── Arbitrage: 0 opportunities
│   ├── Sniper: Watching 3 pairs
│   └── Multi-Agent: Agent #5 leading
└── Combined Signals
    └── HIGH CONFIDENCE: BTC Arbitrage + ML UP + Sniper Trigger
```

### Option 2: Agents Feed Into ML
```python
# In trading_bot.py, enhance ML step:

# 1. Get ML prediction
ml_signal = ml_predictor.predict('BTC/USDT')

# 2. Get ZeroClaw AI insight
zc_insight = zeroclaw.get_ai_analysis('BTC/USDT')

# 3. Get Strategy signals
arb_signal = binary_arbitrage.scan()
sniper_signal = sniper.scan_markets()

# 4. Combine all signals
combined_score = combine_signals(
    ml=ml_signal,
    ai=zc_insight,
    arb=arb_signal,
    sniper=sniper_signal
)

# 5. Execute if confidence high enough
if combined_score.confidence > 80:
    execute_trade(combined_score)
```

## Implementation Plan

### Step 1: Fix ZeroClaw Pairing
```bash
# Get pairing code
zeroclaw daemon
# (Look for: "Pairing code: XXXXXX")

# Pair the bot
curl -X POST http://127.0.0.1:3000/pair \
  -d '{"code": "XXXXXX", "name": "trading-bot"}'
```

### Step 2: Create Unified Agent API
```python
# new file: unified_agents.py

class UnifiedAgentSystem:
    """
    Combines:
    - ZeroClaw AI (natural language, memory)
    - ML Predictions (technical analysis)
    - Strategies (execution logic)
    """
    
    def get_comprehensive_signal(self, symbol):
        # Get all inputs
        ml = self.ml.predict(symbol)
        ai = self.zeroclaw.analyze(symbol)
        strategies = self.strategy_engine.scan(symbol)
        
        # Combine
        return self.ensemble.combine(ml, ai, strategies)
```

### Step 3: Update ML Dashboard
```javascript
// In ml.html, add sections:
- ML Predictions (existing)
- ZeroClaw AI Insights (new)
- Strategy Agent Status (new)
- Combined Signal Score (new)
```

## Current Limitations

| Issue | Status | Solution |
|-------|--------|----------|
| ZeroClaw not paired | 🔴 | Get pairing code |
| Agents siloed | 🟡 | Create unified API |
| ML only in bot | 🟡 | Expose to dashboard |
| No agent visualization | 🟡 | Add to ML page |

## Quick Test

```bash
# 1. Check ZeroClaw
curl http://127.0.0.1:3000/health

# 2. Check ML
curl http://127.0.0.1:8080/api/data | jq '.stats.ml_prediction'

# 3. Check Strategies
python -c "from strategies.orchestrator import TradingOrchestrator; o=TradingOrchestrator(); print(o.scan_all())"
```

## Summary

**ZeroClaw** = AI Brain (NLP, memory, Telegram)
**ML Predictions** = Technical Analysis (sklearn, indicators)
**Strategies** = Execution Logic (arbitrage, sniper, multi-agent)

**Integration Goal:** All three should feed into a unified decision engine, displayed on the ML dashboard.
