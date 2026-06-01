# TRADING BOT WIRING AUDIT REPORT

**Date:** 2026-06-01
**Auditor:** OWL (automated)
**Scope:** All 16+ ported modules and their integration into `trading_bot.py`

---

## EXECUTIVE SUMMARY

The codebase contains **~80 Python files** across a modular architecture. `trading_bot.py` (1697 lines) serves as the main orchestrator. It imports the original/core modules properly but **completely misses all 16 newly-ported modules**. These new modules exist as standalone files with no wiring into the main bot, no integration tests, and several have cross-referencing import bugs. The new modules cannot be exercised through `trading_bot.py --test` because the test runner only invokes `pytest tests/`.

**Overall wiring health: ~35%** — core pipeline works, but the 16 new modules are disconnected orphans.

---

## 1. IMPORT CHAIN ANALYSIS

### What `trading_bot.py` Actually Imports (lines 46-157)

| Module | Import Line | Status |
|--------|------------|--------|
| `crypto_price_fetcher` | 47 | ✅ Core data layer — wired |
| `strategy_engine` | 53-54 | ✅ Arbitrage strategy — wired |
| `risk_manager` | 61 | ✅ Risk management — wired |
| `execution_layer` | 68 | ✅ Trade execution — wired |
| `exchange_connectors` | 76 | ✅ Optional — wired with fallback |
| `alerts` | 82 | ✅ Optional — wired with fallback |
| `dashboard` | 88 | ✅ Optional — wired with fallback |
| `solana_dex` | 95 | ✅ Optional — wired with fallback |
| `ml_predictions` | 103 | ✅ Optional — wired with fallback |
| `database` (OLD) | 110 | ✅ Used as `self.db` |
| `strategies.binary_arbitrage` | 117 | ✅ Wired |
| `strategies.sniper` | 123 | ✅ Wired |
| `trading_memory` | 131 | ✅ Wired |
| `news_fetcher` | 138 | ✅ Wired |
| `strategies.multi_agent` | 145 | ✅ Wired |
| `rl` | 153 | ✅ Wired (PPOAgent, etc.) |

### What's MISSING from `trading_bot.py` (all 16 ported modules)

| # | Module | File | Imported? | Used? |
|---|--------|------|-----------|-------|
| 1 | **strategy_interface** | `strategy_interface.py` | ❌ No | ❌ No |
| 2 | **strategies** (new) | `strategies.py` | ❌ No | ❌ No |
| 3 | **hyperopt_engine** | `hyperopt_engine.py` | ❌ No | ❌ No |
| 4 | **trade_database** | `trade_database.py` | ❌ No | ❌ No |
| 5 | **metrics** | `metrics.py` | ❌ No | ❌ No |
| 6 | **remote_control_api** | `remote_control_api.py` | ❌ No | ❌ No |
| 7 | **social_sentiment** | `social_sentiment.py` | ❌ No | ❌ No |
| 8 | **multi_strategy_orchestrator** | `multi_strategy_orchestrator.py` | ❌ No | ❌ No |
| 9 | **discord_notifier** | `discord_notifier.py` | ❌ No | ❌ No |
| 10 | **event_logger** | `event_logger.py` | ❌ No | ❌ No |
| 11 | **portfolio_optimizer** | `portfolio_optimizer.py` | ❌ No | ❌ No |
| 12 | **quantstats_analyzer** | `quantstats_analyzer.py` | ❌ No | ❌ No |
| 13 | **signal_generator** | `signal_generator.py` | ❌ No | ❌ No |
| 14 | **extended_indicators** | `extended_indicators.py` | ❌ No | ❌ No |
| 15 | **auto_trader_engine** | `auto_trader_engine.py` | ❌ No | ❌ No |
| 16 | **dynamic_config_manager** | `dynamic_config_manager.py` | ❌ No | ❌ No |

**Finding:** Zero of the 16 ported modules are imported or initialized in `trading_bot.py`.

---

## 2. MODULE INTEGRATION STATUS

### 2.1 strategy_interface.py (452 lines)
- **Status:** Standalone, never imported
- **Contents:** `BaseStrategy` ABC, `StrategyRegistry`, `MultiTimeframeAggregator`, `compute_indicators()`
- **Depends on:** `numpy`, `pandas`
- **Required by:** `strategies.py`, `hyperopt_engine.py`, `multi_strategy_orchestrator.py`
- **Issue:** `StrategyRegistry` has `list()` method but `remote_control_api.py` line 342 calls `list_strategies()` which doesn't exist → **NameError at runtime**

### 2.2 strategies.py (564 lines)
- **Status:** Standalone, auto-registers via `register_all()` on import (line 564)
- **Contents:** 10 strategy classes (BollingerBandBreakout, MACDCrossover, IchimokuCloud, RSIMeanReversion, SMACrossover, MultiIndicatorConsensus, VolumeSpike, ATRBreakout, MomentumSurge, CEXArbitrageAdapter)
- **Depends on:** `strategy_interface` (line 27-30)
- **Issue:** `CEXArbitrageAdapter` at line 527 tries `from strategy_engine import TradeDecision` — but the actual class in `strategy_engine.py` is named differently (needs verification)

### 2.3 hyperopt_engine.py (411 lines)
- **Status:** Standalone, never wired
- **Depends on:** `strategy_interface.StrategyRegistry` (line 145-146)
- **Issues:**
  - Line 201: references `self.max_iteration` (typo — should be `self.max_iterations`)
  - Line 527: `_evaluate_params` creates strategy instance via `__new__` without `__init__`, then sets class attributes — strategies use indicator computation in `__init__` cascade that may fail

### 2.4 trade_database.py (473 lines)
- **Status:** Standalone, never wired
- **Issue:** `remote_control_api.py` line 329 calls `db.get_trades(limit=limit, offset=offset)` but `TradeDatabase` has no `get_trades()` method — it has `get_closed_trades()` and `get_open_trades()`. line 351 calls `db.get_analytics()` which also doesn't exist → **AttributeError at runtime**

### 2.5 metrics.py (312 lines)
- **Status:** Standalone, never wired
- **Contents:** `compute_advanced_metrics()`, `metrics_to_report()`, `walk_forward_optimization()`
- **Clean code**, no internal issues

### 2.6 remote_control_api.py (508 lines)
- **Status:** Standalone, has `__main__` block
- **Multiple runtime bugs:**
  - Line 342: `StrategyRegistry.list_strategies()` → should be `StrategyRegistry.list()`
  - Line 329: `db.get_trades(limit, offset)` → method doesn't exist on `TradeDatabase`
  - Line 345, 418: `db.open_trade(pair=, side=, ...)` → `TradeDatabase.open_trade()` signature is `(trade_id, pair, amount, open_rate, stake_amount, ...)` — incompatible call
  - Line 351: `db.get_analytics()` → doesn't exist on `TradeDatabase`

### 2.7 social_sentiment.py (453 lines)
- **Status:** Standalone, never wired
- **Has working `__main__` block** (lines 437-453)
- **Internal bug:** `RedditSentimentProvider.get_sentiment()` line 255: `score_val / 1000` may produce values outside -1..1 range before clamping — minor

### 2.8 multi_strategy_orchestrator.py (396 lines)
- **Status:** Standalone, never wired
- **Issues:**
  - Line 381: typo in `__main__` block — `"MultiIndicatorConsensuss"` (double 's')
  - Line 210: `if instance and hasattr(instance, 'generate_signal')` — strategies from `strategies.py` don't have `generate_signal()`, they have `analyze()` → strategies won't produce signals through this orchestrator

### 2.9 discord_notifier.py (257 lines)
- **Status:** Standalone, never wired
- **Clean code**, has working `__main__` block
- **Requires:** `DISCORD_WEBHOOK_URL` env var or prints helpful message

### 2.10 event_logger.py (248 lines)
- **Status:** Standalone, never wired
- **Clean code**, has working `__main__` block
- **Global singleton pattern** via `get_logger()` — good design

### 2.11 portfolio_optimizer.py (380 lines)
- **Status:** Standalone, never wired
- **Depends on:** `scipy.optimize` (not in requirements.txt!)
- **Has working `__main__` block** (lines 356-380)

### 2.12 quantstats_analyzer.py (308 lines)
- **Status:** Standalone, never wired
- **Clean code**, uses only `numpy`, `pandas`
- **Has working `__main__` block** (lines 288-308)

### 2.13 signal_generator.py (314 lines)
- **Status:** Standalone, never wired
- **Bug in `__main__` (line 311):** prints `strength` instead of `s.strength` → **NameError**
- **Uses capitalized column names** (`Close`, `Volume`) unlike other modules that use lowercase — inconsistency

### 2.14 extended_indicators.py (383 lines)
- **Status:** Standalone, never wired
- **Depends on:** optional `talib`, optional `pandas`
- **Line 241:** References `pd.isna` without `import pandas as pd` in scope → **NameError in pandas fallback mode**
- **Has working `__main__` block** (lines 355-383)

### 2.15 auto_trader_engine.py (429 lines)
- **Status:** Standalone, never wired
- **Uses `asyncio`** internally but `start_sync()` wraps it in normal threads — mixed model
- **Has working `__main__` block** (lines 388-429)

### 2.16 dynamic_config_manager.py (696 lines)
- **Status:** Standalone, never wired
- **Depends on:** `core.regime.MarketRegime` (line 28) — imports correctly
- **Uses `async/await`** on `apply_regime_adjustments()` and `apply_volatility_scaling()` — requires async context to call
- **Missing `__main__` block** — no test entry point

---

## 3. CONFIGURATION MANAGEMENT

### 3.1 config.yaml (1842 lines)
- **Status:** Exists but is **broken**
- **Critical issue:** Contains deeply nested duplicate structures (lines 1-500 repeat `bot: config:` patterns recursively). YAML parses this but the duplicates create unpredictable behavior — later keys shadow earlier ones
- **Missing:** No references to any of the 16 new modules (no `hyperopt`, `remote_control`, `sentiment`, `discord`, `orchestrator` sections)

### 3.2 dynamic_config_manager.py
- Loads `config.json` by default (line 110), not `config.yaml`
- **No config.json exists** in the repo — falls back to hardcoded defaults (lines 183-205)
- The hardcoded defaults only include `strategies.arbitrage`, `strategies.sniper`, and `risk` — none of the new strategies
- **Safety bounds** (lines 61-69) only cover old parameters

### 3.3 Config Flow
```
config.yaml (broken, not loaded)
    ↓
config.json (doesn't exist)
    ↓
hardcoded defaults (lines 183-205 of dynamic_config_manager.py)
    ↓
trading_bot.py reads config.json (lines 1622-1626) — works, YAML not used
```

**Verdict:** Config management partially works for the old system. The new modules have no configuration pathway.

---

## 4. DATA FLOW ANALYSIS

### Core Pipeline (works):
```
crypto_price_fetcher.BinanceConnector.fetch_price()
    → strategy_engine.ArbitrageStrategy.analyze()
        → risk_manager.RiskManager.assess_trade()
            → execution_layer.ExecutionLayer.execute_trade()
                → database.TradingDatabase.save_trade()
                    → crypto_price_fetcher.AuditLogger.log()
```

This pipeline is **fully wired** and works end-to-end in `run_once()` (lines 1102-1394).

### New Module Data Flows (all broken/disconnected):

**price_fetcher → strategy_interface:** ❌ Not connected
- `strategy_interface.BaseStrategy.analyze()` expects OHLCV DataFrame
- `trading_bot.py` passes raw price dicts, not DataFrames

**strategy_interface → hyperopt_engine:** ❌ Not connected
- `HyperoptEngine` correctly imports from `StrategyRegistry`, but registry is never populated in `trading_bot.py`

**execution → trade_database:** ❌ Not connected
- `database.py` (old `TradingDatabase`) is used instead of new `trade_database.py`
- Old DB uses `save_trade()`, new DB uses `open_trade()`/`close_trade()` — different API

**sentiment → strategy:** ❌ Not connected
- `SentimentEngine` output is never fed into any strategy or signal pipeline

**signal_generator → any consumer:** ❌ Not connected
- `SignalGenerator.generate_all()` produces `TradeSignal` objects that nothing consumes

**orchestrator → strategies:** ❌ Partially connected
- `StrategyOrchestrator.register_strategy()` tries to import strategies by hardcoded names (lines 145-155), but the call interface mismatch (`generate_signal` vs `analyze`) breaks execution

**metrics → dashboard/reporting:** ❌ Not connected
- `compute_advanced_metrics()` is never called with trade results

**event_logger → any system:** ❌ Not connected
- Global singleton is never instantiated or used

**auto_trader_engine → main loop:** ❌ Not connected
- `AutoTrader.start_sync()` is a complete alternative event loop, never started

---

## 5. MISSING WIRING — WHAT NEEDS TO BE GLUED

### Critical (blocks any new module usage):

1. **`trading_bot.py` needs import block** for all 16 modules (after line 98, before the `@dataclass` block)
2. **`trading_bot.py._init_layers()` needs new sections** to initialize:
   - `StrategyOrchestrator` with registered strategies
   - `TradeDatabase` (new) alongside or replacing old `TradingDatabase`
   - `DiscordNotifier` (if webhook configured)
   - `EventLogger` (as primary logger)
   - `SentimentEngine` (wrapping `news_fetcher`)
   - `AutoTraderEngine` (as execution alternative)
   - `RemoteControlApi` (background thread)
   - `DynamicConfigManager` (for runtime parameter adjustment)
3. **`trading_bot.py.run_once()` needs integration points**:
   - After Step 1: feed data to `SignalGenerator` and `ExtendedIndicators`
   - After Step 2: feed sentiment from `SentimentEngine` into decision
   - After Step 4: record trades in new `TradeDatabase`
   - After Step 5: send alerts via `DiscordNotifier`
   - Step 7: replace `self.logger.log()` with `EventLogger.log()`
4. **`trading_bot.py` argparse** needs new flags:
   - `--optimize` (run hyperopt)
   - `--sentiment` (enable sentiment analysis)
   - `--remote-api` (start REST API)
   - `--auto-trader` (use auto-trader engine)
   - `--discord` (enable Discord alerts)

### Important (data flow bugs):

5. **`signal_generator.py`** uses `df["Close"]` (capitalized) but `crypto_price_fetcher` returns lowercase keys — mismatch
6. **`trade_database.py`** needs its schema created by `trading_bot.py.__init__()` or `_init_layers()`
7. **`config.yaml`** needs to be de-duplicated and extended with new module configs
8. **`dynamic_config_manager.py`** default config needs new strategy parameters

### Minor (code bugs in new modules):

9. **`remote_control_api.py:342`** — `StrategyRegistry.list_strategies()` → `StrategyRegistry.list()`
10. **`remote_control_api.py:329`** — `db.get_trades(limit, offset)` → needs new method on `TradeDatabase`
11. **`remote_control_api.py:351`** — `db.get_analytics()` → doesn't exist
12. **`hyperopt_engine.py:201`** — `self.max_iteration` → `self.max_iterations`
13. **`extended_indicators.py:241`** — `pd.isna()` → `np.isnan()` or `import pandas as pd`
14. **`signal_generator.py:311`** — `strength` → `s.strength`
15. **`multi_strategy_orchestrator.py:381`** — `"MultiIndicatorConsensuss"` → `"MultiIndicatorConsensus"`
16. **`multi_strategy_orchestrator.py:210`** — checks `hasattr(instance, 'generate_signal')` but strategies use `analyze()`

---

## 6. ENTRY POINT & TEST ANALYSIS

### `python3 trading_bot.py --test`
- **Runs:** `subprocess.run(["python", "-m", "pytest", "tests/", "-v"])` (line 1497-1499)
- **Test files found:**
  - `tests/test_strategy.py` — Tests `StrategyEngine.evaluate()`, imports correctly
  - `tests/test_execution_layer.py` — Tests execution layer
  - `tests/test_risk.py` — Tests risk manager
  - `tests/test_websocket_feed.py` — Tests websocket feed
- **NOT tested by pytest:** Any of the 16 new modules
- **Result:** Core tests likely pass. New modules are untested.

### Module `__main__` blocks:

| Module | Has `__main__` | Works standalone? |
|--------|---------------|-------------------|
| strategy_interface.py | ❌ No | N/A |
| strategies.py | ❌ No | Auto-registers on import |
| hyperopt_engine.py | ❌ No | N/A |
| trade_database.py | ❌ No | N/A |
| metrics.py | ❌ No | N/A |
| remote_control_api.py | ✅ Yes | ✅ Starts HTTP server |
| social_sentiment.py | ✅ Yes | ✅ Works with API keys |
| multi_strategy_orchestrator.py | ✅ Yes | ✅ Works (minor typo) |
| discord_notifier.py | ✅ Yes | ✅ Works with webhook |
| event_logger.py | ✅ Yes | ✅ Works |
| portfolio_optimizer.py | ✅ Yes | ✅ Works with scipy |
| quantstats_analyzer.py | ✅ Yes | ✅ Works |
| signal_generator.py | ✅ Yes | ❌ NameError on line 311 |
| extended_indicators.py | ✅ Yes | ⚠️ May fail in pandas-only mode |
| auto_trader_engine.py | ✅ Yes | ✅ Works |
| dynamic_config_manager.py | ❌ No | N/A |

---

## 7. DEPENDENCIES (`requirements.txt`)

### Currently listed:
```
requests>=2.31.0
python-dotenv>=1.0.0
flask>=3.0.0
PyJWT>=2.8.0
numpy>=1.26.0
pandas>=2.1.0
scikit-learn>=1.3.0
# solathon>=0.3.0  (commented out)
# ta-lib>=0.4.0    (commented out)
```

### Missing (required by ported modules):
```
scipy>=1.11.0          # portfolio_optimizer.py, hyperopt_engine.py (line 204, 216, etc.)
PyYAML>=6.0            # config.yaml parsing (not directly used yet)
python-telegram-bot    # telegram_alerts.py (separate file, not in requirements)
```

### Analysis:
- `scipy` is the most critical missing dependency — `portfolio_optimizer.py` imports `scipy.optimize` at runtime in every optimization method
- `PyJWT` is listed but the fallback HMAC auth works without it
- `flask` is listed but only used by `dashboard.py`
- No dependency for `talib` (correctly commented — requires system library)

---

## 8. DATABASE SCHEMA CONFLICTS

Two database systems co-exist:

| | Old (`database.py`) | New (`trade_database.py`) |
|---|---|---|
| **File** | `trades.db` | `trades.db` (same path!) |
| **Schema** | Simple `trades` table with JSON raw_data | Full ORM-style with `TradeRecord`, `pair_locks`, `bot_state` tables |
| **API** | `save_trade()`, `save_price()`, `get_performance_summary()` | `open_trade()`, `close_trade()`, `get_performance_summary()`, `export_csv()` |
| **Indexes** | Basic | Optimized (pair, state, strategy, date) |

**Critical Issue:** Both use `trades.db` — running both will cause schema conflicts or data loss.

---

## 9. RISK OF CIRCULAR DEPENDENCIES

Detected potential circular imports:

1. `strategy_interface.py` ← `strategies.py` ← `hyperopt_engine.py` → `strategy_interface.py` ✅ OK (hyperopt imports registry only)
2. `trading_bot.py` → `crypto_price_fetcher.py` → `strategy_engine.py` → `risk_manager.py` ✅ OK (no back-imports)
3. `multi_strategy_orchestrator.py` line 145-155: `from strategies import BollingerBandBreakout` → `strategies.py` line 27: `from strategy_interface import ...` → No cycle ⚠️ But if `strategy_interface` tried to import from `strategies`, it would cycle
4. `dynamic_config_manager.py` line 28: `from core.regime import MarketRegime` → `core/regime.py` doesn't import back ✅ OK

**No actual circular dependencies found**, but the `multi_strategy_orchestrator.py` hardcoded strategy imports are fragile.

---

## 10. PRIORITIZED FIX LIST

### P0 — Critical (must fix before any new module can be used):

1. Add import block for all 16 modules in `trading_bot.py` (after line 98)
2. Add initialization calls in `_init_layers()` or a new `_init_advanced_modules()` method
3. Fix `signal_generator.py:311` — `strength` → `s.strength`
4. Fix `extended_indicators.py:241` — `pd.isna()` → `np.isnan()`
5. Add `scipy>=1.11.0` to `requirements.txt`
6. Fix `config.yaml` — remove nested duplicate structure

### P1 — Important (fix for correct operation):

7. Fix `remote_control_api.py:342` — `list_strategies()` → `list()`
8. Add `get_trades()` method to `trade_database.py` (or fix all callers to use `get_closed_trades()`)
9. Add `get_analytics()` method to `trade_database.py`
10. Fix `hyperopt_engine.py:201` — `max_iteration` → `max_iterations`
11. Fix `trade_database.py` vs `database.py` schema conflict — pick one
12. Fix `multi_strategy_orchestrator.py:210` — `generate_signal` → `analyze`
13. Fix `multi_strategy_orchestrator.py:381` — typo in strategy name

### P2 — Enhancement (improves integration):

14. Add command-line flags to `trading_bot.py` for `--optimize`, `--sentiment`, `--remote-api`, `--discord`
15. Wire `EventLogger` as primary logger instead of `AuditLogger`
16. Wire `DiscordNotifier` into alert pipeline (after `AlertManager`)
17. Wire `SentimentEngine` output into `run_once()` Step 2 (strategy analysis)
18. Add `DynamicConfigManager` to `trading_bot.py.__init__()` and apply regime adjustments
19. Resolve `config.yaml` vs `config.json` confusion — pick one format
20. Add integration tests for the 16 new modules in `tests/`

---

## APPENDIX: FILE INVENTORY

```
trading_bot.py              1697 lines  Main orchestrator
strategy_interface.py        452 lines  BaseStrategy + Registry [NOT WIRED]
strategies.py                564 lines  10 strategies [NOT WIRED]
hyperopt_engine.py           411 lines  Parameter optimizer [NOT WIRED]
trade_database.py            473 lines  Enhanced trade DB [NOT WIRED]
metrics.py                   312 lines  Advanced metrics [NOT WIRED]
remote_control_api.py        508 lines  REST API [NOT WIRED]
social_sentiment.py          453 lines  Sentiment engine [NOT WIRED]
multi_strategy_orchestrator.py 396 lines Strategy orchestrator [NOT WIRED]
discord_notifier.py          257 lines  Discord alerts [NOT WIRED]
event_logger.py              248 lines  Structured logging [NOT WIRED]
portfolio_optimizer.py       380 lines  Portfolio optimization [NOT WIRED]
quantstats_analyzer.py       308 lines  Quant analysis [NOT WIRED]
signal_generator.py          314 lines  Signal generation [NOT WIRED]
extended_indicators.py       383 lines  Tech indicators [NOT WIRED]
auto_trader_engine.py        429 lines  Autonomous trader [NOT WIRED]
dynamic_config_manager.py    696 lines  Config management [NOT WIRED]
```
