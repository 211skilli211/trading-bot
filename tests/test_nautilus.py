#!/usr/bin/env python3
"""
Tests for the Nautilus Trader integration.

Covers:
- P0 regressions (py3.8 import of core.regime, ccxt_connector import)
- Strategy registry + signal logic (regime momentum, Minervini/SEA, sniper, arb)
- Event-driven backtest engine (determinism, accounting identity, fees,
  stop-loss, take-profit, result fields)
- Data adapter (synthetic generator determinism, save/load round-trip,
  cache-based fetch)
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nautilus_integration as ni
import nautilus_strategies as ns
from nautilus_integration import (
    NautilusConfig,
    NautilusBacktestRunner,
    NautilusDataAdapter,
    get_integration_status,
    print_report,
)
from nautilus_strategies import (
    RegimeMomentumStrategy,
    MinerviniSeaStrategy,
    SniperStrategy,
    BinaryArbitrageStrategy,
    get_strategy,
    list_strategies,
)


# ─── helpers ─────────────────────────────────────────────────────────────────


def make_bars(closes, start_ts=1_700_000_000_000, interval_ms=3_600_000):
    """Build OHLCV bars from a list of close prices (o=h=l=c=close, vol=1)."""
    bars = []
    for i, c in enumerate(closes):
        bars.append({
            "timestamp": start_ts + i * interval_ms,
            "open": c, "high": c, "low": c, "close": c, "volume": 1000.0,
        })
    return bars


def uptrend_closes(n=300, start=100.0, end=170.0):
    return [start + (end - start) * i / (n - 1) for i in range(n)]


def downtrend_closes(n=300, start=170.0, end=100.0):
    return [start + (end - start) * i / (n - 1) for i in range(n)]


# ─── P0 regression: module imports on Python 3.8 ────────────────────────────


def test_core_regime_imports_py38():
    """core.regime must import on Python 3.8 (PEP 563 annotations)."""
    from core.regime import RegimeDetector  # noqa: F401
    assert True


def test_ccxt_connector_imports():
    """ccxt_connector must import despite ccxt version renames (gate/gateio)."""
    from ccxt_connector import CCXTConnector
    assert "binance" in CCXTConnector.EXCHANGE_MAP


def test_get_integration_status_shape():
    status = get_integration_status()
    for key in ("nautilus_installed", "python_version", "nautilus_installable",
                "ccxt_available", "components", "existing_components",
                "strategies", "next_steps"):
        assert key in status, f"missing status key: {key}"
    assert status["strategies"] == [
        "regime_momentum", "minervini_sea", "sniper", "binary_arbitrage"]
    # components are reported (availability depends on installed deps)
    for comp in ("RegimeDetector", "BaseStrategy", "CCXTConnector", "Backtester"):
        assert comp in status["existing_components"]
    assert status["existing_components"]["RegimeDetector"] is True
    assert status["existing_components"]["BaseStrategy"] is True


# ─── registry ────────────────────────────────────────────────────────────────


def test_registry_lists_four_strategies():
    assert len(list_strategies()) == 4
    assert set(list_strategies()) == {
        "regime_momentum", "minervini_sea", "sniper", "binary_arbitrage"}


def test_get_strategy_returns_instances():
    s1 = get_strategy("regime_momentum")
    s2 = get_strategy("minervini_sea")
    assert isinstance(s1, RegimeMomentumStrategy)
    assert isinstance(s2, MinerviniSeaStrategy)


def test_get_strategy_unknown_raises():
    with pytest.raises(ValueError):
        get_strategy("does_not_exist")


# ─── regime momentum ────────────────────────────────────────────────────────


def test_regime_momentum_buy_on_uptrend():
    strat = get_strategy("regime_momentum", {
        "regime": "NEUTRAL", "lookback": 20, "ema_fast": 5, "ema_slow": 10,
        "momentum_threshold": 0.01,
    })
    signals = []
    for bar in make_bars(uptrend_closes(80, start=100, end=130)):
        sig = strat.on_bar(bar)
        if sig:
            signals.append(sig)
    buys = [s for s in signals if s["action"] == "buy"]
    assert buys, "expected buy signals on a sustained uptrend"
    assert 0 < buys[0]["confidence"] <= 0.95
    assert "size_pct" in buys[0]


def test_regime_momentum_sell_on_downtrend():
    strat = get_strategy("regime_momentum", {
        "regime": "NEUTRAL", "lookback": 20, "ema_fast": 5, "ema_slow": 10,
        "momentum_threshold": 0.01,
    })
    signals = []
    for bar in make_bars(downtrend_closes(80, start=130, end=100)):
        sig = strat.on_bar(bar)
        if sig:
            signals.append(sig)
    sells = [s for s in signals if s["action"] == "sell"]
    assert sells, "expected sell signals on a sustained downtrend"


def test_regime_momentum_defensive_blocks_entries():
    strat = get_strategy("regime_momentum", {
        "regime": "DEFENSIVE", "lookback": 20, "ema_fast": 5, "ema_slow": 10,
        "momentum_threshold": 0.01,
    })
    actions = set()
    for bar in make_bars(uptrend_closes(80, start=100, end=130)):
        sig = strat.on_bar(bar)
        if sig:
            actions.add(sig["action"])
    assert "buy" not in actions, "DEFENSIVE regime must not emit entries"
    assert actions == {"close"}


def test_regime_momentum_no_signal_before_warmup():
    strat = get_strategy("regime_momentum", {
        "regime": "NEUTRAL", "lookback": 50, "ema_slow": 50,
    })
    for bar in make_bars(uptrend_closes(40, start=100, end=150))[:49]:
        assert strat.on_bar(bar) is None


# ─── Minervini / stage-2 ─────────────────────────────────────────────────────


def test_minervini_entry_on_uptrend():
    # 100 down bars (200 -> 100), then 200 up bars (100 -> 170):
    # at the end, 52w low ~100 (close > 130), 52w high ~170 (close >= 0.75*hi),
    # SMAs aligned after the sustained rally.
    closes = downtrend_closes(100, start=200.0, end=100.0) + \
        uptrend_closes(200, start=100.0, end=170.0)
    strat = get_strategy("minervini_sea")
    signals = []
    for bar in make_bars(closes, interval_ms=86_400_000):
        sig = strat.on_bar(bar)
        if sig:
            signals.append(sig)
    buys = [s for s in signals if s["action"] == "buy"]
    assert buys, "expected a Minervini stage-2 entry on the designed uptrend"
    assert all(buys[-1]["conditions"].values())


def test_minervini_flat_market_no_signals():
    strat = get_strategy("minervini_sea")
    n_signals = 0
    for _ in range(300):
        if strat.on_bar({"timestamp": 0, "open": 100, "high": 100,
                         "low": 100, "close": 100, "volume": 1}):
            n_signals += 1
    assert n_signals == 0


def test_minervini_exit_below_sma50():
    # Uptrend to 170 (triggers entries), then a crash to 130 (close < SMA50).
    closes = (downtrend_closes(100, start=200.0, end=100.0) +
              uptrend_closes(200, start=100.0, end=170.0) +
              downtrend_closes(60, start=170.0, end=130.0))
    strat = get_strategy("minervini_sea")
    saw_buy = False
    saw_close = False
    for bar in make_bars(closes, interval_ms=86_400_000):
        sig = strat.on_bar(bar)
        if sig and sig["action"] == "buy":
            saw_buy = True
        if sig and sig["action"] == "close":
            saw_close = True
    assert saw_buy, "expected an entry during the rally"
    assert saw_close, "expected a close (trend break) during the crash"


# ─── sniper ──────────────────────────────────────────────────────────────────


def test_sniper_spike_up_tick():
    strat = get_strategy("sniper", {"entry_threshold": 0.02})
    strat.on_tick({"timestamp": 1, "price": 100.0})
    sig = strat.on_tick({"timestamp": 2, "price": 103.0})  # +3%
    assert sig is not None
    assert sig["action"] == "buy"
    assert 0 < sig["confidence"] <= 0.9


def test_sniper_spike_down_tick():
    strat = get_strategy("sniper", {"entry_threshold": 0.02})
    strat.on_tick({"timestamp": 1, "price": 100.0})
    sig = strat.on_tick({"timestamp": 2, "price": 97.0})  # -3%
    assert sig is not None
    assert sig["action"] == "sell"


def test_sniper_small_move_no_signal():
    strat = get_strategy("sniper", {"entry_threshold": 0.02})
    strat.on_tick({"timestamp": 1, "price": 100.0})
    assert strat.on_tick({"timestamp": 2, "price": 100.5}) is None


def test_sniper_explicit_pct_field():
    strat = get_strategy("sniper", {"entry_threshold": 0.02})
    sig = strat.on_tick({"timestamp": 1, "price": 50.0, "price_change_pct": 0.05})
    assert sig is not None and sig["action"] == "buy"


# ─── binary arb ──────────────────────────────────────────────────────────────


def test_binary_arb_spread_detected():
    strat = get_strategy("binary_arbitrage", {"min_spread": 0.001})
    sig = strat.on_tick({
        "timestamp": 1,
        "venue_prices": {"BINANCE": 100.0, "BYBIT": 100.2},
    })
    assert sig is not None
    assert sig["action"] == "arbitrage"
    assert sig["spread"] == pytest.approx(0.002, abs=1e-6)


def test_binary_arb_below_threshold_no_signal():
    strat = get_strategy("binary_arbitrage", {"min_spread": 0.001})
    assert strat.on_tick({
        "timestamp": 1,
        "venue_prices": {"BINANCE": 100.0, "BYBIT": 100.05},
    }) is None


def test_binary_arb_single_venue_no_signal():
    strat = get_strategy("binary_arbitrage", {"min_spread": 0.001})
    assert strat.on_tick({"timestamp": 1, "venue_prices": {"BINANCE": 100.0}}) is None


# ─── backtest engine ─────────────────────────────────────────────────────────


def _default_bars(n=500, seed=42):
    adapter = NautilusDataAdapter(NautilusConfig())
    return adapter.generate_synthetic_bars(n_bars=n, seed=seed)


def test_backtest_result_fields():
    runner = NautilusBacktestRunner(NautilusConfig(interval="1h"))
    result = runner.run_backtest(bars=_default_bars())
    assert "error" not in result
    for key in ("engine", "strategy", "interval", "initial_capital",
                "final_equity", "total_return_pct", "bars", "start", "end",
                "total_trades", "win_rate_pct", "sharpe_ratio",
                "max_drawdown_pct", "fees_paid", "trades", "equity_curve"):
        assert key in result, f"missing result key: {key}"
    assert result["engine"] == "simulator"
    assert result["final_equity"] > 0
    assert len(result["equity_curve"]) == result["bars"] + 1


def test_backtest_deterministic():
    cfg = NautilusConfig(interval="1h")
    bars = _default_bars(seed=7)
    r1 = NautilusBacktestRunner(cfg).run_backtest(bars=bars)
    r2 = NautilusBacktestRunner(cfg).run_backtest(bars=bars)
    assert r1["final_equity"] == r2["final_equity"]
    assert r1["total_trades"] == r2["total_trades"]
    assert r1["trades"] == r2["trades"]


def test_backtest_accounting_identity():
    """final equity must equal initial + sum of net trade P&L."""
    cfg = NautilusConfig(interval="1h")
    result = NautilusBacktestRunner(cfg).run_backtest(bars=_default_bars())
    expected = result["initial_capital"] + sum(t["pnl"] for t in result["trades"])
    tol = 0.01 * max(1, len(result["trades"])) + 0.02
    assert abs(result["final_equity"] - expected) < tol


def test_backtest_fees_reduce_equity():
    bars = _default_bars(seed=11)
    no_fee = NautilusBacktestRunner(
        NautilusConfig(interval="1h", commission_pct=0.0, slippage_pct=0.0)
    ).run_backtest(bars=bars)
    with_fee = NautilusBacktestRunner(
        NautilusConfig(interval="1h", commission_pct=0.002, slippage_pct=0.0005)
    ).run_backtest(bars=bars)
    assert no_fee["total_trades"] > 0, "test bars must produce trades"
    assert with_fee["final_equity"] <= no_fee["final_equity"]
    assert with_fee["fees_paid"] > 0


def test_backtest_stop_loss_fires():
    # Uptrend (entry) then a -19% crash bar: SL (5%) must exit first.
    closes = [100 + 0.25 * i for i in range(60)]
    bars = make_bars(closes)
    bars.append({"timestamp": bars[-1]["timestamp"] + 3_600_000,
                 "open": closes[-1], "high": closes[-1] * 1.001,
                 "low": 94.0, "close": 95.0, "volume": 1000.0})
    strat = get_strategy("regime_momentum", {
        "regime": "NEUTRAL", "lookback": 20, "ema_fast": 5, "ema_slow": 10,
        "momentum_threshold": 0.01,
    })
    cfg = NautilusConfig(interval="1h", stop_loss_pct=0.05, take_profit_pct=0.5)
    result = NautilusBacktestRunner(cfg)._simulate(strat, "regime_momentum", bars)
    exits = [t for t in result["trades"] if t["exit_reason"] == "stop_loss"]
    assert exits, "expected a stop-loss exit on the crash bar"
    assert exits[0]["pnl"] < 0


def test_backtest_take_profit_fires():
    # Uptrend (entry) then a +13% spike bar: TP (10%) must exit.
    closes = [100 + 0.25 * i for i in range(60)]
    bars = make_bars(closes)
    bars.append({"timestamp": bars[-1]["timestamp"] + 3_600_000,
                 "open": closes[-1], "high": 130.0,
                 "low": closes[-1] * 0.999, "close": 129.0, "volume": 1000.0})
    strat = get_strategy("regime_momentum", {
        "regime": "NEUTRAL", "lookback": 20, "ema_fast": 5, "ema_slow": 10,
        "momentum_threshold": 0.01,
    })
    cfg = NautilusConfig(interval="1h", stop_loss_pct=0.5, take_profit_pct=0.10)
    result = NautilusBacktestRunner(cfg)._simulate(strat, "regime_momentum", bars)
    exits = [t for t in result["trades"] if t["exit_reason"] == "take_profit"]
    assert exits, "expected a take-profit exit on the spike bar"
    assert exits[0]["pnl"] > 0


def test_backtest_equity_curve_ends_flat():
    """No open position survives the backtest: the curve's final point is the
    flat (cash) equity, equal to the reported final equity."""
    bars = _default_bars(seed=3, n=200)
    result = NautilusBacktestRunner(NautilusConfig(interval="1h")).run_backtest(bars=bars)
    assert result["equity_curve"][-1] == pytest.approx(result["final_equity"], abs=0.01)
    valid_reasons = {"end_of_data", "stop_loss", "take_profit", "reversed", "signal_close"}
    for t in result["trades"]:
        assert t["exit_reason"] in valid_reasons


def test_print_report_runs():
    result = NautilusBacktestRunner(NautilusConfig(interval="1h")).run_backtest(
        bars=_default_bars())
    assert print_report(result) is None  # must not raise


def test_backtest_synthetic_fallback_when_no_data(tmp_path):
    cfg = NautilusConfig(symbol="BTC/USDT", days=2, interval="1h",
                         cache_dir=str(tmp_path))
    # Force empty fetch by pointing at a dead exchange id
    runner = NautilusBacktestRunner(cfg)
    result = runner.run_backtest(exchange_id="definitely_not_an_exchange")
    assert "error" not in result
    assert result["data_source"] == "synthetic"
    assert result["bars"] == 2 * ni.bars_per_day("1h")


# ─── data adapter ────────────────────────────────────────────────────────────


def test_synthetic_generator_deterministic():
    adapter = NautilusDataAdapter(NautilusConfig())
    a = adapter.generate_synthetic_bars(n_bars=100, seed=123, start_ts_ms=0)
    b = adapter.generate_synthetic_bars(n_bars=100, seed=123, start_ts_ms=0)
    c = adapter.generate_synthetic_bars(n_bars=100, seed=999, start_ts_ms=0)
    assert [x["close"] for x in a] == [x["close"] for x in b]
    assert [x["close"] for x in a] != [x["close"] for x in c]
    for bar in a:
        assert bar["low"] <= bar["open"] <= bar["high"] or bar["low"] <= bar["close"] <= bar["high"]
        assert bar["low"] <= min(bar["open"], bar["close"])
        assert bar["high"] >= max(bar["open"], bar["close"])
    assert a[0]["timestamp"] == 0
    assert a[1]["timestamp"] - a[0]["timestamp"] == 3_600_000


def test_adapter_save_load_roundtrip(tmp_path):
    adapter = NautilusDataAdapter(NautilusConfig())
    bars = adapter.generate_synthetic_bars(n_bars=50, seed=5, start_ts_ms=0)
    path = str(tmp_path / "bars.json")
    adapter.save_bars(bars, path)
    loaded = adapter.load_bars(path)
    assert len(loaded) == 50
    assert loaded[0]["close"] == bars[0]["close"]
    assert [b["timestamp"] for b in loaded] == [b["timestamp"] for b in bars]


def test_adapter_fetch_uses_cache(tmp_path, monkeypatch):
    """fetch_historical_data must return cached data without network calls."""
    cfg = NautilusConfig(symbol="BTC/USDT", days=30, interval="1h",
                         cache_dir=str(tmp_path))
    adapter = NautilusDataAdapter(cfg)
    # Pre-seed the cache file the adapter would read
    cached = adapter.generate_synthetic_bars(n_bars=10, seed=1, start_ts_ms=0)
    cache_file = os.path.join(str(tmp_path), "auto_BTC-USDT_30d_1h.json")
    with open(cache_file, "w") as f:
        json.dump(cached, f)

    def no_network(*a, **k):
        raise AssertionError("network should not be touched when cache exists")

    monkeypatch.setattr(adapter, "_fetch_via_ccxt", no_network)
    data = adapter.fetch_historical_data(exchange_id="auto")
    assert adapter.last_source == "cache"
    assert len(data) == 10
    assert data[0]["close"] == cached[0]["close"]


def test_adapter_fetch_no_exchange_returns_empty(tmp_path, monkeypatch):
    cfg = NautilusConfig(symbol="BTC/USDT", days=1, interval="1h",
                         cache_dir=str(tmp_path))
    adapter = NautilusDataAdapter(cfg)

    def no_data(*a, **k):
        return []

    monkeypatch.setattr(adapter, "_fetch_via_ccxt", no_data)
    assert adapter.fetch_historical_data(exchange_id="auto") == []
    assert adapter.last_source == "none"


if __name__ == "__main__":
    import pytest as _pt
    _pt.main([__file__, "-v"])
