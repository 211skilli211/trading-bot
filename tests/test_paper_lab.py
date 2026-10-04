#!/usr/bin/env python3
"""
Tests for the live paper-trading lab (paper_lab.py).

Covers:
- Closed-bar filtering (no lookahead on the in-progress candle)
- State init/resume semantics (flat adoption, carried position re-armed)
- run_slot: adoption, no-op re-run, new-bar processing, gap detection
- The core invariant: chunked replay == full replay (paper fills are
  exact backtest semantics — same step_bars engine)
- State persistence round-trip, dashboard, reset guards, error paths
"""

import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paper_lab
from paper_lab import (
    SLOTS,
    _resume_position,
    dashboard,
    filter_closed_bars,
    init_slot_state,
    load_state,
    run_all,
    run_slot,
    save_state,
)
from nautilus_integration import NautilusConfig, NautilusDataAdapter, get_strategy, step_bars

TF_4H_MS = 4 * 3_600_000


# ── helpers ───────────────────────────────────────────────────────────────────


def make_bars(n, start_px=100.0, step=3_600_000, t0=1_700_000_000_000):
    """Flat OHLC bars (±0.1 wicks)."""
    return [
        {"timestamp": t0 + i * step, "open": start_px, "high": start_px + 0.1,
         "low": start_px - 0.1, "close": start_px}
        for i in range(n)
    ]


def quiet_bars(n, start_px=100.0, t0=1_700_000_000_000):
    """Steady +0.1%/bar climb: strategy warms up, then fires long."""
    bars = []
    for i in range(n):
        c = start_px * (1.001 ** i)
        bars.append({
            "timestamp": t0 + i * TF_4H_MS,
            "open": c * 0.999, "high": c * 1.001,
            "low": c * 0.999, "close": c,
        })
    return bars


def slot4h(warmup_bars=200):
    return {"name": "t4h", "symbol": "ETH/USDT", "tf": "4h",
            "strategy": "regime_momentum",
            "strategy_config": {"lookback": 10, "momentum_threshold": 0.005,
                                "ema_fast": 50, "ema_slow": 100},
            "sl": 0.05, "tp": 0.10, "warmup_bars": warmup_bars}


def with_fetch(bars):
    """Context manager stubbing paper_lab.fetch_slot_bars."""
    class _Ctx:
        def __enter__(self):
            self.real = paper_lab.fetch_slot_bars
            paper_lab.fetch_slot_bars = lambda *a, **k: bars
            return self
        def __exit__(self, *exc):
            paper_lab.fetch_slot_bars = self.real
            return False
    return _Ctx()


SIM_4H = NautilusConfig(
    symbol="ETH/USDT", days=1, interval="4h",
    commission_pct=0.001, slippage_pct=0.0005,
    stop_loss_pct=0.05, take_profit_pct=0.10,
    strategy_name="regime_momentum",
    strategy_config={"lookback": 10, "momentum_threshold": 0.005,
                     "ema_fast": 50, "ema_slow": 100},
)


# ── filter_closed_bars ────────────────────────────────────────────────────────


def test_filter_drops_open_candle():
    bars = make_bars(3)
    now = bars[-1]["timestamp"] + 3_600_000 - 1  # last candle still open
    out = filter_closed_bars(bars, "1h", now_ms=now)
    assert [b["timestamp"] for b in out] == [bars[0]["timestamp"], bars[1]["timestamp"]]


def test_filter_keeps_just_closed_candle():
    bars = make_bars(3)
    now = bars[1]["timestamp"] + 3_600_000  # exactly the close instant
    out = filter_closed_bars(bars, "1h", now_ms=now)
    assert out[-1]["timestamp"] == bars[1]["timestamp"]
    assert len(out) == 2


# ── init / resume ─────────────────────────────────────────────────────────────


def test_init_state_flat_and_adopted():
    slot = SLOTS[0]
    bars = make_bars(5)
    st = init_slot_state(slot, bars, capital=5000.0)
    assert st["equity"] == 5000.0
    assert st["initial_capital"] == 5000.0
    assert st["position"] is None
    assert st["trades"] == []
    assert st["last_processed_ts"] == bars[-1]["timestamp"]
    assert st["runs"] == 0


def test_resume_position_rearms_sltp():
    pos = {"side": "long", "entry": 100.0, "qty": 1.0, "notional": 100.0,
           "entry_ts": 1, "entry_idx": 42}
    out = _resume_position(pos)
    assert out["entry_idx"] == -1
    assert out["entry"] == 100.0
    assert out["qty"] == 1.0
    assert _resume_position(None) is None


# ── run_slot ──────────────────────────────────────────────────────────────────


def test_run_slot_first_run_adopts_flat():
    bars = quiet_bars(200)
    with with_fetch(bars):
        rep = run_slot(slot4h(), None, 10_000.0, "binance",
                       now_ms=bars[-1]["timestamp"] + TF_4H_MS)
    assert rep["adopted"] is True
    assert rep["new_bars"] == 0
    st = rep["state"]
    assert st["equity"] == 10_000.0
    assert st["position"] is None
    assert st["last_processed_ts"] == bars[-1]["timestamp"]
    assert st["runs"] == 0


def test_run_slot_no_new_bars_is_noop():
    bars = quiet_bars(200)
    st0 = init_slot_state(slot4h(), bars, 10_000.0)
    with with_fetch(bars):
        rep = run_slot(slot4h(), st0, 10_000.0, "binance",
                       now_ms=bars[-1]["timestamp"] + TF_4H_MS)
    assert rep["new_bars"] == 0
    assert rep["state"]["runs"] == 0


def test_run_slot_processes_only_new_bars():
    base = quiet_bars(200)
    extended = quiet_bars(205)  # same t0 -> seamless continuation
    st0 = init_slot_state(slot4h(warmup_bars=200), base, 10_000.0)

    with with_fetch(extended):
        rep = run_slot(slot4h(warmup_bars=200), st0, 10_000.0, "binance",
                       now_ms=extended[-1]["timestamp"] + TF_4H_MS)

    assert rep["adopted"] is False
    assert rep["new_bars"] == 5
    assert rep["gap"] is False
    assert rep["state"]["runs"] == 1
    assert rep["state"]["last_processed_ts"] == extended[-1]["timestamp"]
    # accounting identity: flat-basis equity == initial + sum(realized pnl)
    st = rep["state"]
    assert abs(st["equity"] - (10_000.0 + sum(t["pnl"] for t in st["trades"]))) < 1e-6
    # marked-to-market equity is consistent with the open position
    if st["position"]:
        p = st["position"]
        marked = st["equity"] + p["qty"] * (extended[-1]["close"] - p["entry"])
        assert marked > 0


def test_run_slot_gap_flagged_when_history_unavailable():
    bars = quiet_bars(200)
    st0 = init_slot_state(slot4h(), bars, 10_000.0)
    # state is OLDER than the fetched window start -> saved bars no longer
    # available: k == 0, progress made -> gap=True, whole fetch is "new"
    st0["last_processed_ts"] = bars[0]["timestamp"] - TF_4H_MS
    with with_fetch(bars):
        rep = run_slot(slot4h(), st0, 10_000.0, "binance",
                       now_ms=bars[-1]["timestamp"] + TF_4H_MS)
    assert rep["gap"] is True
    assert rep["new_bars"] == 200
    assert rep["state"]["last_processed_ts"] == bars[-1]["timestamp"]


def test_run_slot_no_data_reports_error():
    with with_fetch([]):
        rep = run_slot(slot4h(), None, 10_000.0, "binance")
    assert rep["error"] == "no market data"


# ── the core invariant: chunked replay == full replay ─────────────────────────


@pytest.mark.parametrize("seed", [7, 1234, 20261004])
def test_chunked_replay_equals_full_replay(seed):
    """Paper semantics ARE backtest semantics: stepping a persisted state
    across new bars must land on exactly the same equity/trades as stepping
    one fresh state across the full tape."""
    adapter = NautilusDataAdapter(NautilusConfig())
    bars = adapter.generate_synthetic_bars(
        n_bars=480, start_price=3000.0, vol_per_bar=0.01,
        drift_per_bar=0.0001, seed=seed, interval_ms=TF_4H_MS,
    )
    assert len(bars) >= 100

    def full_run():
        state = {"equity": 10_000.0, "position": None, "trades": [], "fees_paid": 0.0}
        strat = get_strategy("regime_momentum", dict(SIM_4H.strategy_config))
        step_bars(state, strat, bars, SIM_4H)
        return state

    split = len(bars) // 2
    state = {"equity": 10_000.0, "position": None, "trades": [], "fees_paid": 0.0}
    strat = get_strategy("regime_momentum", dict(SIM_4H.strategy_config))
    step_bars(state, strat, bars[:split], SIM_4H)
    # paper-lab resume: carry the position with entry_idx=-1
    state["position"] = _resume_position(state.get("position"))
    step_bars(state, strat, bars[split:], SIM_4H)
    chunked = state

    full = full_run()
    assert abs(chunked["equity"] - full["equity"]) < 1e-9
    assert chunked["trades"] == full["trades"]
    assert abs(chunked["fees_paid"] - full["fees_paid"]) < 1e-9
    assert (chunked["position"] is None) == (full["position"] is None)


def test_chunked_split_mid_position_rearms_sltp():
    """A position opened on the LAST bar of the first chunk must have SL/TP
    active from the first bar of the second chunk (entry_idx=-1 re-arms it),
    matching the single-pass run exactly."""
    bars = make_bars(40, start_px=100.0, step=TF_4H_MS)

    class Scripted:
        """Fires a buy on the 20th bar consumed (0-based index 19)."""
        def __init__(self):
            self._n = 0
        def on_bar(self, bar):
            self._n += 1
            if self._n == 20:
                return {"action": "buy", "size_pct": 0.05}
            return None

    cfg = NautilusConfig(symbol="X", days=1, interval="1h",
                         commission_pct=0.0, slippage_pct=0.0,
                         stop_loss_pct=0.5, take_profit_pct=0.9)
    split = 20

    s1 = {"equity": 1000.0, "position": None, "trades": [], "fees_paid": 0.0}
    st1 = Scripted()
    step_bars(s1, st1, bars[:split], cfg)
    assert s1["position"] is not None
    assert s1["position"]["entry_idx"] == 19
    s1["position"] = _resume_position(s1["position"])

    s1b = {"equity": s1["equity"], "position": s1["position"],
           "trades": s1["trades"], "fees_paid": s1["fees_paid"]}
    step_bars(s1b, st1, bars[split:], cfg)

    stf = Scripted()
    sf = {"equity": 1000.0, "position": None, "trades": [], "fees_paid": 0.0}
    step_bars(sf, stf, bars, cfg)

    assert s1b["position"]["entry"] == sf["position"]["entry"]
    assert s1b["position"]["qty"] == sf["position"]["qty"]
    assert s1b["trades"] == sf["trades"]
    assert abs(s1b["equity"] - sf["equity"]) < 1e-9


# ── persistence + run_all + dashboard ─────────────────────────────────────────


@pytest.fixture
def tmp_state(monkeypatch, tmp_path):
    p = str(tmp_path / "paper_state.json")
    monkeypatch.setattr(paper_lab, "STATE_PATH", p)
    return p


def test_state_roundtrip(tmp_state):
    st = {"slots": {"a": {"equity": 1.0}}, "created_ts": 1}
    save_state(st)
    assert json.load(open(tmp_state))["slots"]["a"]["equity"] == 1.0
    assert load_state() == st
    assert not os.path.exists(tmp_state + ".tmp")


def test_run_all_persists_both_slots(tmp_state, monkeypatch):
    bars_a = quiet_bars(150)
    bars_b = quiet_bars(150)
    for b in bars_b:
        b["timestamp"] += 1

    def fake_fetch(slot, last_ts_ms=0, exchange="binance", now_ms=None):
        return bars_a if slot["name"] == SLOTS[0]["name"] else bars_b

    monkeypatch.setattr(paper_lab, "fetch_slot_bars", fake_fetch)
    out = run_all(capital=10_000.0)
    st = load_state()
    assert set(st["slots"].keys()) == {s["name"] for s in SLOTS}
    for name in st["slots"]:
        assert st["slots"][name]["equity"] == 10_000.0
        assert st["slots"][name]["position"] is None
    assert len(out["reports"]) == 2
    assert all(r["adopted"] for r in out["reports"])


def test_dashboard_renders(tmp_state):
    st = {
        "created_ts": 1,
        "slots": {
            SLOTS[0]["name"]: {
                "equity": 10_123.45, "initial_capital": 10_000.0,
                "position": {"side": "long", "entry": 3200.0, "qty": 0.015,
                             "notional": 48.0, "entry_ts": 1, "entry_idx": -1},
                "trades": [{"side": "long", "entry": 3100.0, "exit": 3200.0,
                            "qty": 0.01, "pnl": 1.0, "fees": 0.02,
                            "entry_ts": 1, "exit_ts": 2,
                            "exit_reason": "take_profit"}],
                "fees_paid": 0.5, "last_processed_ts": 1_790_000_000_000,
            },
        },
    }
    txt = dashboard(st)
    assert SLOTS[0]["name"] in txt
    assert "LONG" in txt
    assert "equity 10,123.45" in txt
    assert "take_profit" in txt
    assert "(paper: simulated fills" in txt
    assert f'[{SLOTS[1]["name"]}]' in txt
    assert "not started" in txt


def test_dashboard_reports_new_bars(tmp_state):
    st = {
        "created_ts": 1,
        "slots": {
            SLOTS[0]["name"]: {"equity": 10_000.0, "position": None, "trades": [],
                               "last_processed_ts": 1},
        },
    }
    txt = dashboard(st, reports=[{"slot": SLOTS[0]["name"], "new_bars": 3,
                                  "new_trades": []}])
    assert "just processed 3 new closed bars" in txt


def test_dashboard_gap_warning(tmp_state):
    st = {"created_ts": 1, "slots": {
        SLOTS[0]["name"]: {"equity": 10_000.0, "position": None, "trades": [],
                           "last_processed_ts": 1}}}
    txt = dashboard(st, reports=[{"slot": SLOTS[0]["name"], "new_bars": 3,
                                  "gap": True, "new_trades": []}])
    assert "history gap" in txt


# ── reset guards + CLI ────────────────────────────────────────────────────────


def test_reset_refused_without_yes(tmp_state):
    st = {"slots": {"a": {"equity": 1.0}}, "created_ts": 1}
    save_state(st)
    rc = paper_lab.cmd_reset(capital=10_000.0, yes=False)
    assert rc == 1
    assert load_state() == st  # untouched


def test_reset_without_yes_on_fresh_state_ok(tmp_state, monkeypatch, capsys):
    monkeypatch.setattr(paper_lab, "fetch_slot_bars",
                        lambda *a, **k: quiet_bars(150))
    rc = paper_lab.cmd_reset(capital=7_500.0, yes=False)
    assert rc == 0
    st = load_state()
    assert all(s["equity"] == 7_500.0 for s in st["slots"].values())
    assert "reset" in capsys.readouterr().out.lower()


def test_main_status_no_state_returns_1(tmp_state, capsys):
    rc = paper_lab.main(["--status"])
    assert rc == 1
    assert "No paper state yet" in capsys.readouterr().out


def test_main_status_shows_dashboard(tmp_state, capsys):
    save_state({"created_ts": 1, "slots": {
        SLOTS[0]["name"]: {"equity": 10_000.0, "position": None, "trades": [],
                           "last_processed_ts": 1}}})
    rc = paper_lab.main(["--status"])
    assert rc == 0
    assert "PAPER LAB" in capsys.readouterr().out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
