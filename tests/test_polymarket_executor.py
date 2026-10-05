#!/usr/bin/env python3
"""Tests for polymarket_executor (guards, ledger, auto-execute, settlement
watch) and the alerts module-level helpers.

No network: PmTrader is replaced with stubs; ledger paths are redirected
to a temp dir via monkeypatch so the repo's data/ stays untouched.
"""

import json
import os
import time

import pytest

import polymarket_executor as px


# ---------------------------------------------------------------------------
# helpers / fixtures
# ---------------------------------------------------------------------------

OPPS = [
    {"id": "PM-01", "strategy": "endgame", "slug": "s1",
     "condition_id": "0x1", "question": "Will X?", "outcome": "Yes",
     "token_id": "T1", "price": 0.96, "shares": 5.0, "fee_rate": 0.04,
     "score": 90, "expected_profit_usd": 0.13, "edge_net": 0.002},
    {"id": "PM-02", "strategy": "smart_money", "slug": "s2",
     "condition_id": "0x2", "question": "Will Y?", "outcome": "No",
     "token_id": "T2", "price": 0.63, "shares": 5.0, "fee_rate": 0.03,
     "score": 80, "expected_profit_usd": 0.05, "edge_net": 0.01},
    {"id": "PM-03", "strategy": "binary_arb", "slug": "s3", "legs": [],
     "score": 99},
]


class StubTrader:
    def __init__(self, cash=20.0, asks=None):
        self.cash = cash
        self.asks = asks or {}

    def usdc_balance(self):
        return self.cash

    def positions(self):
        return []

    def best_ask(self, tok):
        return self.asks.get(tok, 0.99)

    def place_buy(self, token, price, size):
        self.last = (token, price, size)
        return {"success": True, "order_id": "oid-x", "status": "matched",
                "error": None}


@pytest.fixture
def tmp_ledger(monkeypatch, tmp_path):
    path = tmp_path / "pm_ledger.json"
    monkeypatch.setattr(px, "LEDGER_PATH", str(path))
    return str(path)


# ---------------------------------------------------------------------------
# ledger + P&L
# ---------------------------------------------------------------------------

def test_new_record_cost_and_fee(tmp_ledger):
    rec = px.new_record("endgame", OPPS[0], "oid-1")
    assert rec["cost_usd"] == 4.8
    assert rec["fee_usd_est"] == round(0.04 * 0.96 * 0.04 * 5, 4)
    assert rec["status"] == "open" and rec["order_id"] == "oid-1"


def test_settle_pnl_win_loss(tmp_ledger):
    base = {"shares": 5, "cost_usd": 4.8, "fee_usd_est": 0.0077}
    assert px.settle_pnl({**base, "resolution": "win"}) == \
        round(5 - 4.8 - 0.0077, 4)
    assert px.settle_pnl({**base, "resolution": "loss"}) == \
        round(-4.8 - 0.0077, 4)


def test_ledger_roundtrip_and_summary(tmp_ledger):
    led = px.load_ledger()
    assert led == {"records": []}
    rec = px.new_record("endgame", OPPS[0], "oid-1")
    led = px.add_record(led, rec)
    s = px.ledger_summary(led)
    assert s["open_count"] == 1 and s["open_cost"] == 4.8
    assert s["settled_count"] == 0 and s["realized_total"] == 0

    rec["status"] = "settled"
    rec["resolution"] = "win"
    rec["settled_pnl"] = px.settle_pnl(rec)
    rec["settle_ts"] = int(time.time())
    px.save_ledger(led)
    s2 = px.ledger_summary(px.load_ledger())
    assert s2["settled_count"] == 1 and s2["wins"] == 1
    assert s2["realized_today"] == round(rec["settled_pnl"], 2)
    # file permissions
    assert os.stat(tmp_ledger).st_mode & 0o077 == 0


def test_ledger_summary_daily_window(tmp_ledger):
    now = int(time.time())
    old_ts = now - 200000  # not today (UTC)
    led = {"records": [
        {"status": "settled", "resolution": "loss", "settled_pnl": -9.9,
         "settle_ts": old_ts},
        {"status": "settled", "resolution": "win", "settled_pnl": 0.19,
         "settle_ts": now},
    ]}
    s = px.ledger_summary(led, now=now)
    assert s["realized_total"] == -9.71
    assert s["realized_today"] == 0.19
    assert s["wins"] == 1 and s["losses"] == 1


def test_corrupt_ledger_starts_fresh(tmp_ledger):
    with open(tmp_ledger, "w") as f:
        f.write("{not json")
    assert px.load_ledger() == {"records": []}


def test_parse_json_str():
    assert px._parse_json_str('["Yes", "No"]') == ["Yes", "No"]
    assert px._parse_json_str(["0.025", "0.975"]) == ["0.025", "0.975"]
    assert px._parse_json_str(None) == []
    assert px._parse_json_str("garbage") == []


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------

def test_check_entry_cash_ok():
    ok, why = px.check_entry(StubTrader(20.0), {"records": []}, 4.8, 3.0)
    assert ok and why == "ok"


def test_check_entry_insufficient_cash():
    ok, why = px.check_entry(StubTrader(4.5), {"records": []}, 4.8, 3.0)
    assert not ok and "insufficient USDC" in why


def test_check_entry_daily_loss_cap():
    led = {"records": [{
        **px.new_record("endgame", OPPS[0], "o"),
        "status": "settled", "resolution": "loss", "settled_pnl": -5.0,
        "settle_ts": int(time.time()),
    }]}
    ok, why = px.check_entry(StubTrader(20.0), led, 4.8, 3.0)
    assert not ok and "daily loss cap" in why


def test_check_entry_cap_zero_disables(tmp_ledger):
    led = {"records": [{
        **px.new_record("endgame", OPPS[0], "o"),
        "status": "settled", "resolution": "loss", "settled_pnl": -5.0,
        "settle_ts": int(time.time()),
    }]}
    ok, _ = px.check_entry(StubTrader(20.0), led, 4.8, 0.0)
    assert ok


def test_holding_token_via_ledger(tmp_ledger):
    led = px.add_record(px.load_ledger(),
                        px.new_record("endgame", OPPS[0], "o"))
    assert px.holding_token(StubTrader(), "T1")
    assert not px.holding_token(StubTrader(), "T9")


def test_holding_token_via_api():
    class T(StubTrader):
        def positions(self):
            return [{"asset": "T9", "size": 5.0}]
    assert px.holding_token(T(), "T9")


# ---------------------------------------------------------------------------
# auto_execute
# ---------------------------------------------------------------------------

def test_auto_execute_places_top_n(tmp_ledger):
    t = StubTrader(20.0, asks={"T1": 0.96, "T2": 0.63})
    res = px.auto_execute({"opportunities": [dict(o) for o in OPPS]}, t,
                          bankroll=10.0, types=("endgame", "smart_money"),
                          max_n=2)
    assert len(res["executed"]) == 2 and not res["skipped"]
    assert res["spent_this_run"] == round(4.8 + 3.15, 2)
    led = px.load_ledger()
    assert len(led["records"]) == 2
    assert led["records"][0]["order_id"] == "oid-x"
    assert led["records"][0]["status"] == "open"


def test_auto_execute_skips_multi_leg_arbs(tmp_ledger):
    t = StubTrader(20.0)
    res = px.auto_execute(
        {"opportunities": [dict(o) for o in OPPS]}, t, bankroll=10.0,
        max_n=5)
    ids = [s.get("id") for s in res["skipped"]] + \
          [e.get("id") for e in res["executed"]]
    assert "PM-03" not in ids  # arb with "legs" never auto-executed
    assert not px.load_ledger()["records"]


def test_auto_execute_dedupe(tmp_ledger):
    t = StubTrader(20.0, asks={"T1": 0.96, "T2": 0.63})
    report = {"opportunities": [dict(o) for o in OPPS[:2]]}
    px.auto_execute(report, t, bankroll=10.0, max_n=2)
    res2 = px.auto_execute(report, t, bankroll=10.0, max_n=2)
    assert not res2["executed"] and len(res2["skipped"]) == 2
    assert "already holding" in res2["skipped"][0]["reason"]


def test_auto_execute_requote_guard(tmp_ledger):
    class Up(StubTrader):
        def best_ask(self, tok):
            return 0.99 if tok == "T1" else 0.63
    res = px.auto_execute({"opportunities": [dict(OPPS[0])]}, Up(),
                          bankroll=10.0, max_n=1, dry_run=True)
    assert res["skipped"][0]["reason"].startswith("ask moved up")
    assert not px.load_ledger()["records"]


def test_auto_execute_dry_run_previews_with_cash_note(tmp_ledger):
    t = StubTrader(0.0, asks={"T2": 0.63})
    res = px.auto_execute({"opportunities": [dict(OPPS[1])]}, t,
                          bankroll=10.0, max_n=1, dry_run=True)
    assert len(res["executed"]) == 1
    rec = res["executed"][0]
    assert rec["dry_run"] and not rec["cash_ok"]
    assert "insufficient USDC" in rec["cash_note"]
    assert not px.load_ledger()["records"]


def test_auto_execute_dry_run_cash_ok(tmp_ledger):
    t = StubTrader(20.0, asks={"T2": 0.63})
    res = px.auto_execute({"opportunities": [dict(OPPS[1])]}, t,
                          bankroll=10.0, max_n=1, dry_run=True)
    assert res["executed"][0]["cash_ok"] and \
        res["executed"][0]["cash_note"] == ""


def test_auto_execute_halt_on_daily_cap(tmp_ledger):
    led = px.add_record(
        px.load_ledger(),
        {**px.new_record("endgame", OPPS[0], "o"),
         "status": "settled", "resolution": "loss", "settled_pnl": -5.0,
         "settle_ts": int(time.time())})
    t = StubTrader(20.0, asks={"T1": 0.96, "T2": 0.63})
    res = px.auto_execute({"opportunities": [dict(o) for o in OPPS[:2]]}, t,
                          bankroll=10.0, max_n=2, daily_loss_cap=3.0)
    assert res["halted"]
    # the pre-seeded settled record is the only record — nothing new placed
    assert len(px.load_ledger()["records"]) == 1


def test_auto_execute_order_rejection(tmp_ledger):
    class Fail(StubTrader):
        def __init__(self):
            super().__init__(asks={"T1": 0.96})

        def place_buy(self, *a, **k):
            return {"success": False, "order_id": None, "status": None,
                    "error": "not enough balance"}
    res = px.auto_execute({"opportunities": [dict(OPPS[0])]}, Fail(),
                          bankroll=10.0, max_n=1)
    assert not res["executed"]
    assert "order rejected" in res["skipped"][0]["reason"]
    assert not px.load_ledger()["records"]


def test_auto_execute_no_matching_opps(tmp_ledger):
    res = px.auto_execute({"opportunities": []}, StubTrader(), bankroll=10,
                          max_n=2)
    assert res["skipped"][0]["reason"].startswith("no matching")


# ---------------------------------------------------------------------------
# settlement watch
# ---------------------------------------------------------------------------

def test_watch_settlements_win_via_redeemable(tmp_ledger):
    led = px.add_record(px.load_ledger(),
                        px.new_record("endgame", OPPS[0], "oid-1"))

    class T(StubTrader):
        def positions(self):
            return [{"asset": "T1", "size": 5.0, "curPrice": 1.0,
                     "redeemable": True}]
    out = px.watch_settlements(T())
    assert out["settled"][0]["resolution"] == "win"
    assert out["settled"][0]["settled_pnl"] == \
        round(5 - 4.8 - 0.0077, 4)
    assert px.load_ledger()["records"][0]["status"] == "settled"


def test_watch_settlements_loss_market_closed(tmp_ledger):
    led = px.add_record(px.load_ledger(),
                        px.new_record("smart_money", OPPS[1], "oid-2"))

    class T(StubTrader):
        def market_by_slug(self, slug):
            return {"closed": True, "outcomes": '["Yes", "No"]',
                    "outcomePrices": '["1", "0"]'}
    out = px.watch_settlements(T())
    assert out["settled"][0]["resolution"] == "loss"
    fee = round(0.03 * 0.63 * 0.37 * 5, 4)
    assert out["settled"][0]["settled_pnl"] == round(-3.15 - fee, 4)


def test_watch_settlements_win_price_one(tmp_ledger):
    led = px.add_record(px.load_ledger(),
                        px.new_record("endgame", OPPS[0], "oid-1"))

    class T(StubTrader):
        def positions(self):
            return [{"asset": "T1", "size": 5.0, "curPrice": 1.0}]
        def market_by_slug(self, slug):
            return {"closed": True, "outcomes": '["Yes", "No"]',
                    "outcomePrices": '["1", "0"]'}
    out = px.watch_settlements(T())
    assert out["settled"][0]["resolution"] == "win"


def test_watch_settlements_still_open(tmp_ledger):
    opp9 = dict(OPPS[0], slug="s9", token_id="T9")
    led = px.add_record(px.load_ledger(),
                        px.new_record("endgame", opp9, "oid-3"))

    class T(StubTrader):
        def positions(self):
            return [{"asset": "T9", "size": 5.0, "curPrice": 0.9}]
        def market_by_slug(self, slug):
            return {"closed": False}
    out = px.watch_settlements(T())
    assert out["still_open"] == 1 and not out["settled"]
    assert px.load_ledger()["records"][0]["status"] == "open"


def test_watch_settlements_no_open_bets(tmp_ledger):
    out = px.watch_settlements(StubTrader())
    assert out == {"settled": [], "still_open": 0, "errors": []}


def test_watch_settlements_position_gone_market_open(tmp_ledger):
    opp9 = dict(OPPS[0], slug="s9", token_id="T9")
    led = px.add_record(px.load_ledger(),
                        px.new_record("endgame", opp9, "oid-3"))

    class T(StubTrader):
        def positions(self):
            return []
        def market_by_slug(self, slug):
            return {"closed": False}
    out = px.watch_settlements(T())
    assert out["still_open"] == 1 and not out["settled"]


def test_watch_settlements_missing_outcome_no_guess(tmp_ledger):
    """If our outcome isn't in the gamma list, don't guess the price."""
    opp9 = dict(OPPS[0], slug="s9", token_id="T9", outcome="Maybe")
    led = px.add_record(px.load_ledger(),
                        px.new_record("endgame", opp9, "oid-3"))

    class T(StubTrader):
        def positions(self):
            return []
        def market_by_slug(self, slug):
            return {"closed": True, "outcomes": '["Yes", "No"]',
                    "outcomePrices": '["1", "0"]'}
    out = px.watch_settlements(T())
    assert out["still_open"] == 1 and not out["settled"]


# ---------------------------------------------------------------------------
# PmTrader auth surface (no network beyond constructor key derivation, which
# is local)
# ---------------------------------------------------------------------------

def test_pmtrader_requires_key(monkeypatch):
    monkeypatch.delenv("POLYMARKET_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("POLYMARKET_API_KEY", "k")
    with pytest.raises(px.ClobAuthError):
        px.PmTrader()


def test_balance_report_renders(tmp_ledger, monkeypatch):
    """balance_report must render wallet/cash/ledger without crashing, and
    must not raise on an auth-failing trader (reports the error instead)."""
    class Good(StubTrader):
        wallet = "0xabc"
        def open_orders(self):
            return []

    class Bad(Good):
        def usdc_balance(self):
            raise px.ClobAuthError("l2 down")

    out = px.balance_report(Good())
    assert "0xabc" in out and "pUSD cash: $20.0000" in out and \
        "ledger:" in out
    out_bad = px.balance_report(Bad())
    assert "pUSD cash: ❌" in out_bad


# ---------------------------------------------------------------------------
# place_buy — pUSD-era v2 signing path
# ---------------------------------------------------------------------------

_TEST_KEY = "0x" + "11" * 31 + "22"
_TEST_WALLET = "0x7d931fd3f5a12c18Cd77f9Cb90ff58E677dF9479"
_TEST_SECRET_B64 = "c2VjcmV0c2VjcmV0c2VjcmV0"  # b"secretsecretsecret"


def _mk_trader(monkeypatch):
    """Real PmTrader on a throwaway key; no network (L2 calls are lazy)."""
    monkeypatch.setenv("POLYMARKET_PRIVATE_KEY", _TEST_KEY)
    monkeypatch.setenv("POLYMARKET_API_KEY", "k")
    monkeypatch.setenv("POLYMARKET_API_SECRET", _TEST_SECRET_B64)
    monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "p")
    return px.PmTrader()


def test_place_buy_uses_v2_signer(monkeypatch):
    """place_buy must sign via pm_signer (EIP-712 v2) and POST /order with
    L2 headers — not the dead v1 SDK path."""
    calls = {}

    def fake_fetch_book(token_id, host=None, timeout=20):
        calls["book"] = token_id
        return {"tick_size": "0.01", "min_order_size": "5",
                "neg_risk": True, "bids": [], "asks": []}

    def fake_sign(key, token_id, maker, taker, side, neg_risk=False,
                  salt=None):
        calls["sign"] = (token_id, maker, taker, side, neg_risk, key)
        return "0xsig", {"tokenId": str(token_id), "makerAmount": str(maker),
                         "takerAmount": str(taker)}

    def fake_post(api_key, api_secret, api_passphrase, address, body,
                  order_type="GTC", host=None, defer_exec=False,
                  timeout=25):
        calls["post"] = (api_key, address, order_type)
        return {"success": True, "orderID": "0xord", "status": "live"}

    monkeypatch.setattr(px.pm_signer, "fetch_book", fake_fetch_book)
    monkeypatch.setattr(px.pm_signer, "sign_eoa_order", fake_sign)
    monkeypatch.setattr(px.pm_signer, "post_order", fake_post)

    t = _mk_trader(monkeypatch)
    res = t.place_buy("TOK1", 0.52, 10)
    assert res == {"success": True, "order_id": "0xord",
                   "status": "live", "error": None}
    # limit BUY @0.52 ×10 -> maker 5.20 USD, taker 10 shares; signed with
    # our key against the NEG-RISK exchange (book says neg_risk)
    assert calls["sign"] == ("TOK1", 5200000, 10000000, "BUY", True,
                             _TEST_KEY)
    assert calls["post"][2] == "GTC"
    assert calls["post"][1] == _TEST_WALLET


def test_place_buy_missing_l2_creds_raises(monkeypatch):
    t = _mk_trader(monkeypatch)
    t.api_key = ""
    with pytest.raises(px.ClobAuthError):
        t.place_buy("TOK1", 0.52, 10)


def test_place_buy_min_size_guard(monkeypatch):
    monkeypatch.setattr(
        px.pm_signer, "fetch_book",
        lambda *a, **k: {"tick_size": "0.01", "min_order_size": "5",
                         "neg_risk": False, "bids": [], "asks": []})
    t = _mk_trader(monkeypatch)
    res = t.place_buy("TOK1", 0.52, 3)
    assert res["success"] is False
    assert "minimum" in res["error"]


# ---------------------------------------------------------------------------
# pm_signer unit tests (pure, no network)
# ---------------------------------------------------------------------------

def test_signer_amount_encoding_docs_examples():
    import pm_signer as S
    book = {"tick_size": "0.01", "min_order_size": "5"}
    # docs: limit BUY 10 shares @ 0.52
    assert S.encode_amounts(book, "BUY", 0.52, 10) == (5200000, 10000000)
    # docs: limit SELL 10 shares @ 0.52
    assert S.encode_amounts(book, "SELL", 0.52, 10) == (10000000, 5200000)
    # docs: market BUY $10 @ max 0.52 -> 19.2308 shares
    assert S.market_buy_amounts(book, 10.0, 0.52) == (10000000, 19230800)
    # tick 0.1: price 1dp / size 2dp
    book1 = {"tick_size": "0.1", "min_order_size": "5"}
    assert S.encode_amounts(book1, "BUY", 0.9, 11) == (9900000, 11000000)


def test_signer_eip712_v2_recovery():
    """Signed digest must recover to the EOA, and the neg-risk domain must
    differ from the standard one."""
    import pm_signer as S
    from eth_account import Account
    from eth_account.messages import hash_eip712_message, hash_domain
    from Crypto.Hash import keccak

    sig, body = S.sign_eoa_order(_TEST_KEY, "123456789012345678901",
                                 5200000, 10000000, "BUY", salt=479249096354)
    domain = dict(S.DOMAIN_BASE, verifyingContract=S.EXCHANGE_STANDARD)
    msg = {"salt": 479249096354, "maker": _TEST_WALLET,
           "signer": _TEST_WALLET, "tokenId": 123456789012345678901,
           "makerAmount": 5200000, "takerAmount": 10000000, "side": 0,
           "signatureType": 0, "timestamp": int(body["timestamp"]),
           "metadata": S.Z32, "builder": S.Z32}
    k = keccak.new(digest_bits=256)
    k.update(b"\x19\x01" + hash_domain(domain)
             + bytes(hash_eip712_message(S.ORDER_TYPES, msg)))
    b = bytes.fromhex(sig[2:])
    assert Account._recover_hash(k.digest(), (b[64], b[:32], b[32:64])) \
        .lower() == _TEST_WALLET.lower()
    sig_n, _ = S.sign_eoa_order(_TEST_KEY, "123456789012345678901",
                                5200000, 10000000, "BUY", neg_risk=True,
                                salt=479249096354)
    assert sig_n != sig
    # domain must be v2 with the new standard exchange
    assert S.DOMAIN_BASE["version"] == "2"
    assert S.EXCHANGE_STANDARD.lower() == \
        "0xe111180000d2663c0091e4f400237545b87b996b"


def test_signer_l2_hmac():
    import base64, hashlib, hmac as h
    import pm_signer as S
    body_s = '{"deferExec": false, "order": {}, "orderType": "GTC", "owner": "K"}'
    hh = S.l2_headers("K", _TEST_SECRET_B64, "P", "0xabc", "POST",
                      "/order", body_s)
    ts = hh["POLY_TIMESTAMP"]
    expect = base64.urlsafe_b64encode(
        h.new(b"secretsecretsecret",
              (ts + "POST" + "/order" + body_s).encode(),
              hashlib.sha256).digest()).decode()
    assert hh["POLY_SIGNATURE"] == expect
    assert hh["POLY_API_KEY"] == "K" and hh["POLY_PASSPHRASE"] == "P"


# ---------------------------------------------------------------------------
# alerts module-level helpers
# ---------------------------------------------------------------------------

def test_alerts_noop_when_unconfigured(monkeypatch):
    import alerts
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert not alerts.telegram_configured()
    assert alerts.send_telegram("x") is None
    assert alerts.notify("t", "b") is None
    assert "TELEGRAM_BOT_TOKEN" in alerts.test_telegram()


def test_alerts_rejects_placeholders(monkeypatch):
    import alerts
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert not alerts.telegram_configured()
