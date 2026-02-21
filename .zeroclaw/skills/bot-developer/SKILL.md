# Bot Developer Skill

## Purpose
Self-improvement capability - allows the bot to develop new features, fix bugs, and enhance itself.

## When to Use
- Add new trading strategies
- Create custom indicators
- Improve existing code
- Add new integrations
- Fix bugs automatically

## Safety Guardrails

### ✅ Safe Operations (Auto-Approved)
- Create new files in `/skills/`
- Add documentation
- Create tests
- Read-only analysis

### ⚠️ Requires Approval
- Modify existing working code
- Change configuration
- Install new packages
- Delete files
- Git commits

### ❌ Forbidden
- Modify core execution engine
- Change API credentials
- Access `.env` files
- Modify wallet/private keys
- Delete database

## Development Workflow

### 1. User Request
```
User: "Add a moving average crossover strategy"
```

### 2. Planning
Developer skill:
- Analyzes existing strategies
- Checks for similar implementations
- Plans the structure
- Shows plan to user

### 3. Implementation
Creates:
```
/root/trading-bot/strategies/ma_crossover.py
/root/trading-bot/strategies/ma_crossover_config.json
/tests/test_ma_crossover.py
```

### 4. Testing
- Syntax validation
- Unit tests (if available)
- Integration check
- Backtest simulation

### 5. Deployment
- User approves
- Code activated
- Monitoring begins

## Example Developments

### New Strategy: RSI Divergence
```python
# strategies/rsi_divergence.py
class RSIDivergenceStrategy:
    """Detect bullish/bearish RSI divergences"""
    
    def detect_divergence(self, prices, rsi):
        # Implementation...
        pass
```

### New Indicator: Volume Profile
```python
# indicators/volume_profile.py
def calculate_volume_profile(df, bins=24):
    """Calculate volume profile for support/resistance"""
    # Implementation...
    pass
```

### New Alert: Whale Watcher
```python
# alerts/whale_watcher.py
"""Monitor large wallet movements"""
```

## Version Control
All changes are:
1. Backed up before modification
2. Staged in git
3. Committed with descriptive message
4. Reversible if issues occur

## Learning from Development
The bot maintains:
- Development history
- Success/failure rates
- User preferences
- Code patterns that work

This creates a self-improving loop where the bot gets better at helping itself.