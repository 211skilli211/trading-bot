# Nautilus Trader — Integration Research for Trading Bot

## What is Nautilus Trader?
Production-grade open-source algorithmic trading engine. Core written in Rust with Python bindings. 
Designed for multi-venue trading: crypto, equities, forex, derivatives, options.

**URL:** https://github.com/nautechsystems/nautilus_trader
**Website:** https://nautilustrader.io
**License:** MIT

## Key Characteristics
- **Rust core** → nanosecond resolution, memory-safe, low-latency
- **Python API** → strategy development in Python
- **Event-driven** → deterministic replay, identical backtest/live behavior
- **Multi-asset** → spot, futures, derivatives, options in one engine
- **Multi-venue** → trade across exchanges from single engine
- **25,000+ tests** → unit, integration, acceptance, property-based, simulation

## Architecture
```
┌─────────────────────────────────────────────────┐
│                  Strategy Layer                  │
│              (Python strategies)                 │
├─────────────────────────────────────────────────┤
│              Nautilus Trader Core                │
│         (Rust — event-driven engine)             │
├──────────┬──────────┬──────────┬────────────────┤
│ Portfolio │  Risk    │Execution │   Data/Market  │
│  Manager  │ Manager  │  Layer   │    Adapter     │
└──────────┴──────────┴──────────┴────────────────┘
```

## Current Trading Bot vs Nautilus Trader

### Current (custom)
| Component | File | Lines |
|-----------|------|-------|
| Execution | `execution_layer.py`, `execution_layer_v2.py` | ~1200 |
| Data | `data_broker_layer.py`, `crypto_price_fetcher.py` | ~800 |
| Strategy | `autonomous_controller.py`, `core/regime.py` | ~600 |
| Backtesting | `backtester.py` | ~400 |
| Connectors | `ccxt_connector.py`, `jupiter_orders.py` | ~500 |
| Alerts | `intelligent_alerts.py`, `alerts.py` | ~300 |
| **Total** | | **~3800** |

### With Nautilus Trader
| Component | Approach |
|-----------|----------|
| Execution | Native (Rust) — drop replacement |
| Data | Native adapters — drop replacement |
| Strategy | Python — port logic to Nautilus strategy class |
| Backtesting | Native event-driven backtester |
| Connectors | Use Nautilus CCXT adapter |
| Risk | Native risk manager |

## Platform Constraint (verified 2026-10-03)

`nautilus_trader` wheels require **Python 3.11+** (PyPI publishes cp311/cp312
wheels only; latest line targets 3.12–3.14). This phone runs **Python 3.8.10**,
so the Rust core can only be installed on the **server (Render)**.

The integration is designed around this:

| Runs where | What runs | How |
|------------|-----------|-----|
| Phone (py3.8) | Strategy logic + event-driven backtest | pure Python, `nautilus_strategies.py` + `nautilus_integration.py` simulator |
| Server (py3.11+) | Full Rust engine | `pip install nautilus_trader`, same strategy classes via `NautilusStrategyAdapter.build_nautilus_strategy()` |

Backtest-to-live parity is preserved by construction: the strategies are
engine-agnostic, deterministic classes fed bar-by-bar; the Rust engine only
adds venue adapters and the matching core.

## Integration Plan (with status)

### Phase 1: Install & Explore — ✅ DONE (phone side)
- `pip install numpy ccxt pandas pytest requests` works on-device (aarch64 wheels)
- `pip install nautilus_trader` → **server only** (py3.11+)

### Phase 2: Port Strategy Logic — ✅ DONE
Implemented as engine-agnostic classes in `nautilus_strategies.py`:
- `RegimeMomentumStrategy` — momentum over rolling window + EMA trend filter,
  regime-gated (DEFENSIVE blocks entries, sizes from regime table)
- `MinerviniSeaStrategy` — full 6-condition stage-2 template on a 252-bar window,
  SMA50 break exit
- `SniperStrategy` — rapid-move entries on tick/bar deltas
- `BinaryArbitrageStrategy` — cross-venue spread detection

### Phase 3: Replace Execution Layer — ⏳ server
- Wire Nautilus `CCXTExecutionAdapter` on Render
- `NautilusStrategyAdapter.build_nautilus_strategy()` returns a real
  `Strategy` subclass when installed (callback signatures to verify against
  the installed version)

### Phase 4: Backtesting — ✅ DONE (simulator) / ⏳ (Rust engine)
`NautilusBacktestRunner` runs a deterministic event-driven simulator:
long/short, regime-gated sizing, commission, slippage, stop-loss,
take-profit. Data via `NautilusDataAdapter` (ccxt with
binance→kraken→coinbase fallback + USDT→USD quote fallback, JSON cache,
seeded synthetic generator for offline tests).

Run:
```bash
python3 nautilus_integration.py                  # status + offline demo
python3 nautilus_integration.py --real-data      # real exchange data
python3 trading_bot.py --nautilus-backtest --nautilus-strategy regime_momentum
python3 trading_bot.py --nautilus-status         # integration status
```

### Phase 5: Live Trading — ⏳ server
- Same strategy code, different execution adapter
- Paper trading first via Nautilus `PaperExchange`
- Risk management via Nautilus `RiskEngine`

## Migration Effort Estimate
| Phase | Effort | Risk |
|-------|--------|------|
| Install & test | 2-4 hours | Low |
| Port strategy | 1-2 days | Medium |
| Replace execution | 1 day | Medium |
| Backtesting setup | 1 day | Low |
| Live deployment | 1 day | High |
| **Total** | **~1 week** | |

## Recommendation
**Proceed with Phase 1-2** as a parallel implementation. Keep current bot running while
developing the Nautilus version. The key benefit is deterministic backtesting — our current
`backtester.py` doesn't guarantee the same behavior in live trading.

## Current Status (2026-10-03)

| Item | Status |
|------|--------|
| Strategy classes (4) | ✅ Real, deterministic, engine-agnostic |
| Event-driven backtest simulator | ✅ Working (fees, slippage, SL/TP, reverse, sizing) |
| Data adapter (ccxt + cache + synthetic) | ✅ Working — verified on real Binance 1h data |
| CLI wiring (`trading_bot.py`) | ✅ `--nautilus-backtest`, `--nautilus-status`, `--nautilus-*` |
| Tests | ✅ `tests/test_nautilus.py` — 31 tests, full suite 63 passed |
| P0 fixes found along the way | ✅ `core/regime.py` py3.8 annotation crash; `ccxt_connector.py` `ccxt.gateio` import crash |
| Rust engine on phone | ❌ Impossible (py3.8 < 3.11) — server only |
| Rust engine on server | ⏳ Phase 3/5 |

## Alternatives Considered
- **Freqtrade**: Crypto-only, simpler, 380+ contributors → good for crypto-only
- **VectorBT**: Ultra-fast backtesting, no execution layer → backtesting only
- **QuantConnect LEAN**: Cloud-dependent, C# core → not ideal for our setup
- **Nautilus**: Rust core, Python API, multi-venue, open-source → best fit

## Key Advantages for Our Use Case
1. **Backtest-to-live parity** — identical code runs in both environments
2. **Multi-venue readiness** → ready to add equities/forex when needed
3. **Rust performance** → can handle high-frequency data without Python GIL issues
4. **Professional risk management** → built-in position sizing, drawdown limits
5. **No vendor lock-in** — self-hosted, full control
