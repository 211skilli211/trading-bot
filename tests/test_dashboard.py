"""Tests for dashboard.py v2 — the self-contained bot dashboard.

All tests are offline: data files are created in tmp_path and module path
constants are monkeypatched; the price cache is pre-seeded or requests is
disabled so no network call ever happens.
"""

import json
import os
import time

import pytest

import dashboard


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point every dashboard data path at an empty temp dir."""
    monkeypatch.setattr(dashboard, "DB_MAIN", str(tmp_path / "trades.db"))
    monkeypatch.setattr(dashboard, "DB_LEGACY", str(tmp_path / "trades_legacy.db"))
    monkeypatch.setattr(dashboard, "PAPER_STATE", str(tmp_path / "paper_state.json"))
    monkeypatch.setattr(dashboard, "CTRADER_CREDS", str(tmp_path / "ctrader_credentials.json"))
    monkeypatch.setattr(dashboard, "POLY_SCAN", str(tmp_path / "polymarket_last_scan.json"))
    monkeypatch.setattr(dashboard, "PID_FILE", str(tmp_path / "bot.pid"))
    monkeypatch.setattr(dashboard, "BOT_LOG", str(tmp_path / "bot.log"))
    dashboard.LIVE.clear()
    return tmp_path


@pytest.fixture
def client(sandbox):
    assert dashboard.FLASK_AVAILABLE, "flask must be installed"
    dashboard.app.config["TESTING"] = True
    with dashboard.app.test_client() as c:
        yield c


def seed_trade_db(tmp_path):
    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "trades.db"))
    conn.executescript(
        """
        CREATE TABLE trades (
            trade_id TEXT PRIMARY KEY, pair TEXT NOT NULL,
            exchange TEXT NOT NULL DEFAULT 'binance',
            direction TEXT NOT NULL DEFAULT 'long',
            amount REAL NOT NULL, open_rate REAL NOT NULL, close_rate REAL,
            stake_amount REAL NOT NULL, profit_abs REAL, profit_ratio REAL,
            open_date TEXT NOT NULL, close_date TEXT,
            state TEXT NOT NULL DEFAULT 'open',
            stop_loss REAL, take_profit REAL,
            strategy TEXT DEFAULT 'manual', timeframe TEXT DEFAULT '15m',
            orders TEXT DEFAULT '[]', tags TEXT DEFAULT '[]',
            fees_open REAL DEFAULT 0.0, fees_close REAL DEFAULT 0.0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        INSERT INTO trades (trade_id, pair, direction, amount, open_rate,
            close_rate, stake_amount, profit_abs, open_date, close_date,
            state, created_at, updated_at)
            VALUES ('t1', 'ETHUSDT', 'long', 0.5, 3000, 3100, 1500, 50,
                    '2026-10-01T00:00:00', '2026-10-02T00:00:00', 'closed',
                    '2026-10-01T00:00:00', '2026-10-02T00:00:00'),
                   ('t2', 'BTCUSDT', 'short', 0.1, 85000, NULL, 8500, NULL,
                    '2026-10-03T00:00:00', NULL, 'open',
                    '2026-10-03T00:00:00', '2026-10-03T00:00:00');
        """
    )
    conn.close()


def seed_legacy_db(tmp_path):
    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "trades_legacy.db"))
    conn.executescript(
        """
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, trade_id TEXT UNIQUE,
            timestamp TEXT, mode TEXT, strategy TEXT, buy_exchange TEXT,
            sell_exchange TEXT, buy_price REAL, sell_price REAL,
            quantity REAL, spread_pct REAL, fees_paid REAL, net_pnl REAL,
            latency_ms REAL, status TEXT, raw_data TEXT);
        INSERT INTO trades (trade_id, timestamp, strategy, buy_exchange,
            buy_price, sell_price, quantity, net_pnl, status)
            VALUES ('x1', '2026-09-30T00:00:00', 'BTCARBITRAGE', 'binance',
                    84000, 84100, 0.01, 1.0, 'closed');
        """
    )
    conn.close()


# ---------------------------------------------------------------------------
# Health + UI
# ---------------------------------------------------------------------------

def test_healthz(client):
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_index_serves_self_contained_ui(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["Content-Type"]
    html = r.get_data(as_text=True)
    assert "Trading Bot" in html
    # no external assets (offline-safe)
    assert 'src="http' not in html and "href=\"http" not in html
    assert "cdn" not in html.lower().replace("blend", "")


# ---------------------------------------------------------------------------
# Data readers
# ---------------------------------------------------------------------------

def test_trades_merge_both_dbs(client, sandbox):
    seed_trade_db(sandbox)
    seed_legacy_db(sandbox)
    r = client.get("/api/trades")
    assert r.status_code == 200
    body = r.get_json()
    assert len(body["trades"]) == 3
    sources = {t["source"] for t in body["trades"]}
    assert sources == {"bot", "legacy"}
    # newest first: the 10-03 open trade leads
    assert body["trades"][0]["time"].startswith("2026-10-03")
    # stats cover both DBs
    assert body["stats"]["trades"] == 3
    assert body["stats"]["closed"] == 2
    assert abs(body["stats"]["pnl"] - 51.0) < 1e-6


def test_missing_dbs_are_fine(client):
    r = client.get("/api/overview")
    assert r.status_code == 200
    body = r.get_json()
    assert body["trade_stats"]["trades"] == 0
    assert body["trades"] == []


def test_paper_state_parse(client, sandbox):
    state = {
        "created_ts": 1791131418711,
        "slots": {
            "eth-1d": {
                "equity": 10123.45, "initial_capital": 10000.0,
                "position": {"symbol": "ETHUSDT", "side": "long"},
                "trades": [1, 2, 3], "fees_paid": 7.5,
                "last_processed_ts": int(time.time()), "runs": 4,
            },
            "eth-4h": {
                "equity": 9950.0, "initial_capital": 10000.0,
                "position": None, "trades": [], "fees_paid": 0.0,
                "last_processed_ts": None, "runs": 1,
            },
        },
    }
    with open(dashboard.PAPER_STATE, "w") as f:
        json.dump(state, f)
    r = client.get("/api/paper")
    assert r.status_code == 200
    slots = {s["name"]: s for s in r.get_json()["slots"]}
    assert slots["eth-1d"]["open_position"] is True
    assert slots["eth-1d"]["pnl"] == 123.45
    assert slots["eth-4h"]["open_position"] is False
    assert slots["eth-4h"]["pnl_pct"] == -0.5


def test_ctrader_status_never_leaks_secrets(client, sandbox):
    token = "SECRETTOKEN-abc123"
    creds = {
        "client_id": "32782_xxx", "client_secret": "SdtP0z-secret",
        "redirect_uri": "https://my.ctrader.com",
        "access_token": token, "refresh_token": "REFTOKEN-xyz",
        "access_token_expires_at": int(time.time()) + 3 * 86400,
        "host": "live", "account_id": "47848046",
        "live_parked": True, "live_parked_at": int(time.time()) - 3600,
        "account_id_demo": "49028696",
    }
    with open(dashboard.CTRADER_CREDS, "w") as f:
        json.dump(creds, f)
    r = client.get("/api/ctrader")
    assert r.status_code == 200
    body = r.get_json()
    assert body["live_account"] == "47848046"
    assert body["demo_account"] == "49028696"
    assert body["parked"] is True
    assert body["token_days_left"] == 2
    payload = r.get_data(as_text=True)
    assert token not in payload
    assert "SdtP0z-secret" not in payload
    assert "REFTOKEN-xyz" not in payload


def test_ctrader_status_absent(client):
    assert client.get("/api/ctrader").get_json() == {}


def test_polymarket_status_sorted_by_expected(client, sandbox):
    scan = {
        "ts": int(time.time()), "scan_secs": 35.2, "bankroll": 10.0,
        "count": 3,
        "opportunities": [
            {"id": "PM-1", "strategy": "endgame", "market": "A", "expected": 0.05},
            {"id": "PM-2", "strategy": "smart_money", "market": "B", "expected": 0.9},
            {"id": "PM-3", "strategy": "binary_arb", "market": "C", "expected": 0.1},
        ],
    }
    with open(dashboard.POLY_SCAN, "w") as f:
        json.dump(scan, f)
    r = client.get("/api/polymarket")
    assert r.status_code == 200
    body = r.get_json()
    assert body["count"] == 3
    assert [o["id"] for o in body["top"]] == ["PM-2", "PM-3", "PM-1"]


# ---------------------------------------------------------------------------
# Live-loop snapshot (update_dashboard)
# ---------------------------------------------------------------------------

def test_update_dashboard_feeds_overview(client):
    dashboard.update_dashboard(stats={"total_cycles": 42, "total_pnl": 1.25})
    r = client.get("/api/overview")
    body = r.get_json()
    assert body["bot"]["live"] is True
    assert body["bot"]["live_stats"]["total_cycles"] == 42


def test_update_dashboard_noop_ok(client):
    dashboard.update_dashboard()  # all None → must not raise
    assert client.get("/api/healthz").status_code == 200


# ---------------------------------------------------------------------------
# Bot control (no real process is spawned)
# ---------------------------------------------------------------------------

def test_is_bot_running_no_pidfile(client, sandbox):
    assert dashboard.is_bot_running() is False


def test_is_bot_running_stale_pidfile_cleaned(client, sandbox):
    with open(dashboard.PID_FILE, "w") as f:
        json.dump({"pid": 999999999, "mode": "paper"}, f)
    assert dashboard.is_bot_running() is False
    assert not os.path.exists(dashboard.PID_FILE)


def test_stop_bot_without_pidfile(client):
    body = client.post("/api/bot/stop").get_json()
    assert body["stopped"] is False
    assert "PID" in body["message"]


# ---------------------------------------------------------------------------
# Prices: offline behavior
# ---------------------------------------------------------------------------

def test_prices_serve_fresh_cache_without_network(client):
    now = time.time()
    dashboard._price_cache.update({
        "ts": now,
        "data": {
            "watch": [{"symbol": "BTC", "price": 85000.0, "change": 1.2, "volume": 1e9}],
            "gainers": [], "losers": [],
        },
        "error": None,
    })
    r = client.get("/api/prices")
    assert r.status_code == 200
    body = r.get_json()
    assert body["data"]["watch"][0]["symbol"] == "BTC"
    assert body["error"] is None


def test_prices_degrade_gracefully_when_requests_missing(client, monkeypatch):
    monkeypatch.setattr(dashboard, "requests", None)
    dashboard._price_cache.update({"ts": 0.0, "data": None, "error": None})
    r = client.get("/api/overview")
    assert r.status_code == 200
    assert r.get_json()["prices"]["watch"] is None
