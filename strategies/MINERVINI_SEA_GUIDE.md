# Minervini SEA (Specific Entry Point Analysis) Strategy

## Overview

This is a complete implementation of Mark Minervini's legendary momentum trading strategy, based on his books "Trade Like a Stock Market Wizard" and "Think and Trade Like a Champion".

## Performance Expectations

From the source material:
- **Win Rate**: 30-40% (yes, most trades lose!)
- **Average Annual Return**: 220% over 5 years
- **Total Return**: 33,500% over 5 years (Minervini's actual performance)
- **US Investing Championship**: 334.8% return in 2021

**Key Insight**: The strategy makes money through asymmetric reward/risk. Winners are 3x to 10x larger than losers.

## Core Philosophy

1. **Only trade in Stage 2 uptrends** (wind at your back)
2. **Buy high, sell higher** (not value investing)
3. **Volatility Contraction Pattern (VCP)** for precise entries
4. **Cut losses quickly** (7-8% stop loss)
5. **Let winners run** (trailing stops)

## The Four Stages

Every stock goes through four predictable stages:

```
Stage 1: Neglect Phase (sideways)     - AVOID
Stage 2: Advancing Phase (uptrend)    - ✅ TRADE HERE
Stage 3: Topping Phase (distribution) - AVOID  
Stage 4: Declining Phase (downtrend)  - AVOID
```

## Strategy Components

### 1. Trend Template (Stage 2 Filter)

Eliminates ~90% of stocks. All must be true:

| Criteria | Rule |
|----------|------|
| Price vs MAs | Close > 150-day SMA AND > 200-day SMA |
| MA Alignment | 150-day SMA > 200-day SMA |
| Trend Direction | 200-day SMA rising for 4+ months |
| Distance from Highs | Within 25% of 52-week high |
| Relative Strength | RS rating ≥ 70 (preferably 80-90) |

### 2. Volatility Contraction Pattern (VCP)

The "coiled spring" setup before explosive moves:

```
Price
  │    ╲       (First contraction: ~20-28%)
  │     ╲___
  │         ╲    (Second: ~12-16%)
  │          ╲__
  │              ╲   (Third: ≤6-8%)
  │               ╲__
  │                   ╲____ (Tight pivot, volume dries up)
  │                        ╲_____ 📈 BREAKOUT
  └──────────────────────────────────→ Time
```

**Key Characteristics:**
- 3+ contractions of decreasing magnitude
- Volume dries up during consolidation
- Tightest action near the highs (pivot point)
- Breakout on volume surge (40-50% above average)

### 3. Entry Rules

1. Trend Template passes
2. Valid VCP detected  
3. Price breaks above VCP pivot
4. Volume ≥ 40-50% above 50-day average
5. Enter at market or on pullback to pivot

### 4. Position Sizing (1-2% Risk Rule)

```
Max Risk = Account Size × Risk %
         = $100,000 × 1%
         = $1,000

Risk per Share = Entry Price - Stop Loss
               = $50 - $46
               = $4

Position Size = Max Risk / Risk per Share
              = $1,000 / $4
              = 250 shares
```

### 5. Exit Rules

**Initial Stop Loss:**
- Place just below VCP low (typically 7-8% from entry)
- Hard stop - never move it down

**Trailing Stop:**
- Activate when profit reaches 2.5x initial risk
- Move to breakeven + 2% profit
- Continue trailing at logical support levels

**Hard Exits:**
- Close below 200-day SMA
- Trend template no longer valid
- Trailing stop hit

## Configuration Parameters

```python
config = {
    # Account Settings
    "account_size": 100000,          # Total account value
    "risk_per_trade": 1.0,           # Risk % per trade (1-2%)
    "max_position_usd": 10000,       # Max $ per position
    
    # Trend Template
    "min_rs_rating": 70,             # Minimum RS rating
    "max_distance_from_52wh": 0.25,  # Max 25% from highs
    
    # VCP Detection
    "vcp_min_contractions": 2,       # Minimum contractions
    "vcp_max_total_depth": 0.30,     # Max 30% total depth
    "vcp_min_tightness_score": 60,   # Min tightness (0-100)
    
    # Entry/Exit
    "volume_surge_ratio": 1.4,       # 40% volume surge required
    "initial_stop_pct": 0.07,        # 7% initial stop
    "trailing_stop_activation": 2.5  # Activate at 2.5x profit
}
```

## File Structure

```
strategies/
├── minervini_sea.py              # Main strategy class
├── minervini_sea_example.py      # Usage examples
└── MINERVINI_SEA_GUIDE.md        # This guide
```

## Usage Examples

### Basic Usage

```python
from strategies.minervini_sea import MinerviniSEAStrategy
import pandas as pd

# Configuration
config = {
    "name": "Minervini_SEA",
    "account_size": 100000,
    "risk_per_trade": 1.0,
    "max_position_usd": 10000
}

# Initialize
strategy = MinerviniSEAStrategy(config)

# Load data (dict of symbol -> DataFrame)
data = {
    "AAPL": aapl_df,
    "MSFT": msft_df,
    # ...
}

# Scan for signals
signals = strategy.scan(data)

# Execute signals
for signal in signals:
    if signal.side == "buy":
        trade = strategy.execute(signal, mode="PAPER")
        print(f"Entered {trade.symbol} at ${trade.entry_price}")
```

### With Backtrader

```python
import backtrader as bt
from strategies.minervini_sea import MinerviniSEAStrategy

class MinerviniBTStrategy(bt.Strategy):
    def __init__(self):
        self.sea = MinerviniSEAStrategy(config)
    
    def next(self):
        # Convert backtrader data to pandas
        df = self.get_data_as_df()
        
        # Check for signals
        signals = self.sea.scan({self.data._name: df})
        
        for signal in signals:
            if signal.side == "buy":
                self.buy()
            elif signal.side == "sell":
                self.sell()
```

### With Existing Bot

```python
from strategies.minervini_sea import MinerviniSEAStrategyAdapter

# In trading_bot.py, add to strategy registry:
STRATEGIES = {
    "minervini_sea": MinerviniSEAStrategyAdapter,
    # ... other strategies
}
```

## Testing

Run the example file:

```bash
cd /root/trading-bot/strategies
python3 minervini_sea_example.py
```

This will:
1. Run a simple backtest with sample data
2. Show bot integration example
3. Test with real data (if yfinance available)

## Assumptions & Limitations

### VCP Detection

The VCP (Volatility Contraction Pattern) is inherently visual. The algorithmic detection uses:
- Swing high/low analysis
- Contraction depth measurement
- Volume analysis
- Tightness scoring

**⚠️ IMPORTANT**: Always visually verify VCP patterns on charts before trading. The algorithm is a screening tool, not a replacement for chart analysis.

### Relative Strength

RS rating is calculated as:
```
RS = (Stock 12M Return / SPY 12M Return) × 100
```

If no benchmark provided, uses percentile rank approximation.

### Data Requirements

- Minimum 1 year of daily data (252 bars)
- OHLCV columns required
- Clean data (no gaps preferred)

## Expected Results

Based on Minervini's methodology:

| Metric | Expected |
|--------|----------|
| Win Rate | 30-40% |
| Avg Winner | +20% to +100% |
| Avg Loser | -7% to -8% |
| Profit Factor | 2.0+ |
| Max Drawdown | 15-25% |
| Annual Return | 50-200%+ |

## Risk Management

### Position Sizing
- Never risk more than 1-2% per trade
- Position size = Risk $ / (Entry - Stop)
- Maximum position: 10-20% of account

### Portfolio Heat
- Maximum 6-8 open positions
- Stop trading after 3 consecutive losses
- Reduce size during drawdowns

### Market Regime
- Only trade when SPY > 200-day SMA
- Reduce exposure in choppy markets
- Full exposure in strong uptrends

## Psychological Requirements

Minervini emphasizes these mental disciplines:

1. **Comfort buying highs** - Fight the instinct to "get a bargain"
2. **Cut losses quickly** - No hope, no prayer, just rules
3. **Let winners run** - Don't take small profits
4. **Accept 60-70% losers** - Focus on expectancy, not win rate
5. **Patience** - Wait for perfect setups

## Further Reading

**Books by Mark Minervini:**
- "Trade Like a Stock Market Wizard" (essential)
- "Think and Trade Like a Champion"
- "Mindset Secrets for Winning"

**Resources:**
- Minervini Private Access (MPA) - Trading education platform
- Twitter: @markminervini
- YouTube interviews and presentations

## Disclaimer

⚠️ **WARNING**: This is an aggressive momentum strategy with significant risk:
- Expect 60-70% of trades to lose money
- Requires strict discipline and emotional control
- Past performance (Minervini's results) does not guarantee future results
- Always paper trade extensively before using real money
- Never risk more than you can afford to lose

## Support

For questions or issues:
1. Check the example file: `minervini_sea_example.py`
2. Review Minervini's books for methodology details
3. Test with paper trading first

---

**Version**: 1.0.0  
**Author**: Trading Bot System  
**License**: MIT
