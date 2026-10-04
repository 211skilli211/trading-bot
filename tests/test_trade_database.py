"""Regression tests for trade_database.TradeDatabase.

Covers the 2026-10-05 fix: a second `open_trade` method (simplified,
delegating to a non-existent `create_trade`) shadowed the real one in the
same class, breaking the manual-trade endpoint in remote_control_api.py.
"""

import inspect
import re

import pytest

from trade_database import TradeDatabase


@pytest.fixture
def db(tmp_path):
    return TradeDatabase(db_path=str(tmp_path / "trades.db"))


def test_open_trade_single_definition():
    """TradeDatabase must expose exactly one open_trade (no shadowing)."""
    methods = [n for n, _ in inspect.getmembers(
        TradeDatabase, predicate=inspect.isfunction) if n == "open_trade"]
    assert methods == ["open_trade"]
    sig = inspect.signature(TradeDatabase.open_trade)
    # the real signature — the shadowed simplified one is gone
    assert "stake_amount" in sig.parameters
    assert "entry_price" not in sig.parameters


def test_no_create_trade_reference_left():
    """The removed shadow delegated to a non-existent create_trade()."""
    src = inspect.getsource(TradeDatabase)
    assert "create_trade" not in src


def test_open_and_close_roundtrip(db):
    db.open_trade(
        trade_id="t-1", pair="ETHUSDT", amount=1.0, open_rate=2000.0,
        stake_amount=2000.0, direction="long", strategy="manual",
    )
    rows = db.get_trades(limit=10)
    assert len(rows) == 1
    assert rows[0]["trade_id"] == "t-1"
    assert rows[0]["state"] == "open"

    rec = db.close_trade(trade_id="t-1", close_rate=2200.0)
    assert rec is not None
    rows = db.get_trades(limit=10)
    assert rows[0]["state"] == "closed"
    assert rows[0]["profit_abs"] == pytest.approx(200.0)


def test_remote_control_manual_trade_uses_real_signature():
    """_handle_manual_trade must call open_trade with the full signature
    and no longer pass entry_price=0 through a simplified overload."""
    src = open("remote_control_api.py").read()
    assert "entry_price=0" not in src
    m = re.search(r"db\.open_trade\(([^)]*)\)", src, re.S)
    assert m is not None, "db.open_trade call not found"
    args = m.group(1)
    for kw in ("trade_id=", "pair=", "amount=", "open_rate=", "stake_amount="):
        assert kw in args, f"missing {kw} in open_trade call"
