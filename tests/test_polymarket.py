"""Tests for the Polymarket strategy engine + scanner detectors.

All tests are offline: synthetic gamma/CLOB payloads, no network.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest

import polymarket_scanner as psc
import polymarket_strategies as strat

NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# fee model
# ---------------------------------------------------------------------------

def test_fee_rate_by_type():
    assert strat.fee_rate_for("zero_fees") == 0.0
    assert strat.fee_rate_for(None) == 0.0
    assert strat.fee_rate_for("politics_fees") == 0.04
    assert strat.fee_rate_for("crypto_fees_v2") == 0.07
    # fees disabled -> always free
    assert strat.fee_rate_for("politics_fees", fees_enabled=False) == 0.0
    # unknown new category -> conservative default, never assume free
    assert strat.fee_rate_for("brand_new_category") == strat.DEFAULT_FEE_RATE


def test_taker_fee_math():
    # fee = shares x rate x p x (1-p)
    assert strat.taker_fee_per_share(0.5, 0.04) == pytest.approx(0.01)
    assert strat.taker_fee_total(100, 0.5, 0.04) == pytest.approx(1.0)
    # outside (0,1) -> no fee
    assert strat.taker_fee_total(100, 0.0, 0.04) == 0.0
    assert strat.taker_fee_total(100, 1.0, 0.04) == 0.0
    # fee curve peaks at p=0.5
    assert strat.taker_fee_per_share(0.5, 0.05) > strat.taker_fee_per_share(0.9, 0.05)


# ---------------------------------------------------------------------------
# kelly sizing
# ---------------------------------------------------------------------------

def test_kelly_no_edge():
    assert strat.kelly_fraction(0.5, 0.5) == 0.0
    assert strat.kelly_fraction(0.5, 0.4) == 0.0
    assert strat.kelly_fraction(0.0, 0.9) == 0.0


def test_kelly_formula():
    # f* = (p - c) / (1 - c); quarter Kelly
    assert strat.kelly_fraction(0.5, 0.55) == pytest.approx(0.025)
    assert strat.kelly_fraction(0.97, 0.995) == pytest.approx(0.025 / 0.03 * 0.25, rel=1e-4)


def test_size_stake_basic():
    r = strat.size_stake(100, 0.5, 0.55)
    assert r["ok"]
    assert r["stake_usd"] == pytest.approx(2.5)     # 100 * 0.025
    assert r["shares"] == pytest.approx(5.0)


def test_size_stake_capped():
    # raw quarter kelly 0.225 < cap 0.25 -> exact
    r = strat.size_stake(100, 0.90, 0.99, cap_pct=0.25)
    assert r["stake_usd"] == pytest.approx(22.5)
    # max_stake_usd binds first
    r2 = strat.size_stake(100, 0.90, 0.99, max_stake_usd=10.0)
    assert r2["stake_usd"] == pytest.approx(10.0)


def test_size_stake_no_edge_or_bad_input():
    assert not strat.size_stake(100, 0.5, 0.5)["ok"]
    assert not strat.size_stake(0, 0.5, 0.6)["ok"]
    assert not strat.size_stake(100, 1.2, 0.9)["ok"]


def test_size_stake_below_min_raises_to_exchange_minimum():
    # $10 bankroll, tiny stake -> fewer than 5 shares -> report min-size version
    r = strat.size_stake(10, 0.97, 0.995)
    assert r["ok"] and r["below_min"]
    assert r["shares"] == 5.0
    assert r["stake_usd"] == pytest.approx(4.85)


def test_min_stake_helper():
    assert strat.min_stake_for_min_shares(0.97) == 4.85
    assert strat.min_stake_for_min_shares(0.02) == 0.10


# ---------------------------------------------------------------------------
# endgame priors
# ---------------------------------------------------------------------------

def test_endgame_prior_tiers():
    assert strat.endgame_prior(0.98, 10) == 0.995      # strong tier
    assert strat.endgame_prior(0.96, 30) == 0.99       # weaker tier
    assert strat.endgame_prior(0.98, 30) == 0.99       # >24h drops to weaker tier
    assert strat.endgame_prior(0.94, 30) is None       # below 0.95
    assert strat.endgame_prior(0.99, 100) is None      # too far out
    assert strat.endgame_prior(0.99, None) is None


# ---------------------------------------------------------------------------
# book helpers
# ---------------------------------------------------------------------------

def _book(bids=None, asks=None):
    return {"bids": bids or [], "asks": asks or []}


def test_top_ask_bid():
    s = psc.PolyScanner()
    book = _book(bids=[(0.49, 100), (0.48, 50)],
                 asks=[(0.52, 80), (0.55, 300)])
    assert s.top_ask(book) == (0.52, 80)
    assert s.top_bid(book) == (0.49, 100)
    assert s.top_ask(None) is None
    assert s.top_ask(_book()) is None


def test_ask_depth():
    s = psc.PolyScanner()
    book = _book(asks=[(0.52, 100), (0.53, 200), (0.60, 1000)])
    # within 2c of touch: 100*0.52 + 200*0.53
    assert s.ask_depth_usd(book, within=0.02) == pytest.approx(158.0)
    assert s.ask_depth_usd(None) == 0.0


def test_parse_books_payload_sorts_and_casts():
    s = psc.PolyScanner()
    payload = [{
        "asset_id": "T1",
        "bids": [{"price": "0.40", "size": "10"}, {"price": "0.50", "size": "20"}],
        "asks": [{"price": "0.60", "size": "5"}, {"price": "0.55", "size": "7"}],
    }]
    out = s._parse_books_payload(payload)
    assert out["T1"]["bids"] == [(0.5, 20.0), (0.4, 10.0)]
    assert out["T1"]["asks"] == [(0.55, 7.0), (0.6, 5.0)]


# ---------------------------------------------------------------------------
# gamma parsing
# ---------------------------------------------------------------------------

def _raw_market(**over):
    raw = {
        "conditionId": "0xabc", "question": "Q?", "slug": "q-slug",
        "outcomes": '["Yes", "No"]', "outcomePrices": '["0.4", "0.6"]',
        "clobTokenIds": '["111", "222"]',
        "bestBid": 0.39, "bestAsk": 0.41, "spread": 0.02,
        "volume24hr": 12345.0, "liquidityNum": 999.0,
        "endDateIso": "2099-01-01T00:00:00Z",
        "negRisk": False, "negRiskMarketID": None,
        "feeType": "zero_fees", "feesEnabled": True,
        "orderMinSize": 5, "orderPriceMinTickSize": 0.01,
        "events": [{"slug": "ev-slug", "title": "Ev Title"}],
        "lastTradePrice": 0.4, "oneDayPriceChange": 0.01,
        "closed": False, "active": True,
    }
    raw.update(over)
    return raw


def test_parse_market_gamma_shape():
    s = psc.PolyScanner()
    m = s.parse_market(_raw_market())
    assert m["condition_id"] == "0xabc"
    assert m["outcomes"] == ["Yes", "No"]
    assert m["prices"] == [0.4, 0.6]
    assert m["token_ids"] == ["111", "222"]
    assert m["fee_rate"] == 0.0
    assert m["event_slug"] == "ev-slug"
    assert m["end"] is not None
    assert s.parse_market({}) is None


def test_parse_market_aligns_short_arrays():
    s = psc.PolyScanner()
    m = s.parse_market(_raw_market(outcomePrices='["0.4"]'))
    # a short price array truncates every array to the same length
    assert m["prices"] == [0.4]
    assert len(m["outcomes"]) == 1
    assert len(m["token_ids"]) == 1


def test_hours_to():
    assert psc.hours_to(None) is None
    dt = NOW + timedelta(hours=12)
    assert psc.hours_to(dt, NOW) == pytest.approx(12.0)
    assert psc.hours_to(NOW - timedelta(hours=1), NOW) == pytest.approx(-1.0)
    # naive datetimes are tolerated
    naive_end = datetime(2026, 10, 4, 15, 0, 0)
    assert psc.hours_to(naive_end, NOW) == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# binary arb
# ---------------------------------------------------------------------------

def _mk(s, **over):
    return s.parse_market(_raw_market(**over))


def test_binary_arb_positive():
    s = psc.PolyScanner(bankroll=100)
    m = _mk(s)
    books = {m["token_ids"][0]: _book(asks=[(0.48, 500)]),
             m["token_ids"][1]: _book(asks=[(0.50, 500)])}
    o = s.detect_binary_arb(m, books, min_edge=0.005)
    assert o is not None
    assert o["edge_net"] == pytest.approx(0.02)
    assert o["p_est"] == 1.0
    assert o["roi"] == pytest.approx(0.02 / 0.98, abs=1e-4)  # rounded to 4dp
    assert o["legs"][0] == {"outcome": "Yes", "price": 0.48,
                            "token_id": m["token_ids"][0]}
    assert o["depth_usd"] == pytest.approx(500 * 0.48)


def test_binary_arb_killed_by_fees():
    s = psc.PolyScanner(bankroll=100)
    m = _mk(s, feeType="politics_fees")
    assert m["fee_rate"] == 0.04
    books = {m["token_ids"][0]: _book(asks=[(0.48, 500)]),
             m["token_ids"][1]: _book(asks=[(0.50, 500)])}
    # raw edge 2c, but fees ~0.01 + ~0.00998 -> net ~0.00002 < 0.005
    assert s.detect_binary_arb(m, books, min_edge=0.005) is None
    # ...but a 4c raw edge survives fees
    books2 = {m["token_ids"][0]: _book(asks=[(0.46, 500)]),
              m["token_ids"][1]: _book(asks=[(0.50, 500)])}
    o = s.detect_binary_arb(m, books2, min_edge=0.005)
    assert o is not None
    assert o["edge_net"] < 0.04  # fees shaved off some of the 4c


def test_binary_arb_sum_over_one_or_missing_side():
    s = psc.PolyScanner(bankroll=100)
    m = _mk(s)
    books = {m["token_ids"][0]: _book(asks=[(0.60, 500)]),
             m["token_ids"][1]: _book(asks=[(0.40, 500)])}
    assert s.detect_binary_arb(m, books) is None
    books = {m["token_ids"][0]: _book(asks=[(0.40, 500)])}
    assert s.detect_binary_arb(m, books) is None


# ---------------------------------------------------------------------------
# negative-risk arb
# ---------------------------------------------------------------------------

def test_negrisk_arb_positive():
    s = psc.PolyScanner(bankroll=100)
    rep = _mk(s)
    group = [rep,
             _mk(s, conditionId="0xb1", outcomes='["A2", "No2"]',
                 clobTokenIds='["333", "444"]'),
             _mk(s, conditionId="0xb2", outcomes='["A3", "No3"]',
                 clobTokenIds='["555", "666"]')]
    books = {
        "111": _book(asks=[(0.30, 100)]),
        "333": _book(asks=[(0.30, 100)]),
        "555": _book(asks=[(0.30, 100)]),
    }
    o = s.detect_negrisk_arb(rep, group, books, min_edge=0.005)
    assert o is not None
    assert o["n_outcomes"] == 3
    assert o["edge_net"] == pytest.approx(0.10)
    assert o["rationale"].startswith("3-outcome set")


def test_negrisk_incomplete_set_is_not_an_arb():
    s = psc.PolyScanner(bankroll=100)
    rep = _mk(s)
    group = [rep,
             _mk(s, conditionId="0xb1", outcomes='["A2", "No2"]',
                 clobTokenIds='["333", "444"]')]
    # second outcome has no ask -> buying the first alone is a bet
    books = {"111": _book(asks=[(0.20, 100)])}
    assert s.detect_negrisk_arb(rep, group, books) is None


# ---------------------------------------------------------------------------
# endgame quick-win
# ---------------------------------------------------------------------------

def _endgame_raw(hours_to_end, ask_yes, ask_no, vol=20_000.0, liq=10_000.0,
                 **over):
    end = NOW + timedelta(hours=hours_to_end)
    return _raw_market(
        endDateIso=end.isoformat().replace("+00:00", "Z"),
        volume24hr=vol, liquidityNum=liq, **over)


def test_endgame_quick_win():
    s = psc.PolyScanner(bankroll=10)
    m = s.parse_market(_endgame_raw(12, 0.97, 0.03))
    books = {m["token_ids"][0]: _book(asks=[(0.97, 2000)]),
             m["token_ids"][1]: _book(asks=[(0.03, 2000)])}
    o = s.detect_endgame(m, books, min_edge=0.005, now=NOW)
    assert o is not None
    assert o["outcome"] == "Yes"
    assert o["p_est"] == 0.995
    assert o["edge_net"] == pytest.approx(0.995 - 0.97)  # zero fees
    assert o["time_to_end_h"] == pytest.approx(12.0)
    assert o["strategy"] == "endgame"
    assert o["shares"] >= 5
    assert o["expected_profit_usd"] > 0
    assert o["score"] > 0


def test_endgame_rejected_variants():
    s = psc.PolyScanner(bankroll=10)
    books_factory = lambda y, n: {  # noqa: E731
        "tokY": _book(asks=[(y, 1000)]), "tokN": _book(asks=[(n, 1000)])}

    # too far out
    m = s.parse_market(_endgame_raw(100, 0.97, 0.03,
                                    clobTokenIds='["tokY","tokN"]'))
    assert s.detect_endgame(m, books_factory(0.97, 0.03), now=NOW) is None

    # favorite not strong enough (0.94 < 0.95 tier floor)
    m = s.parse_market(_endgame_raw(12, 0.94, 0.06,
                                    clobTokenIds='["tokY","tokN"]'))
    assert s.detect_endgame(m, books_factory(0.94, 0.06), now=NOW) is None

    # illiquid / low volume
    m = s.parse_market(_endgame_raw(12, 0.97, 0.03, vol=100.0,
                                    clobTokenIds='["tokY","tokN"]'))
    assert s.detect_endgame(m, books_factory(0.97, 0.03), now=NOW) is None

    # fees + tight edge kill a marginal signal
    m = s.parse_market(_endgame_raw(12, 0.97, 0.03, feeType="crypto_fees_v2",
                                    clobTokenIds='["tokY","tokN"]'))
    # fee = 0.07*0.97*0.03 = 0.00204; edge = 0.025 - 0.00204 = 0.023 -> still in
    assert s.detect_endgame(m, books_factory(0.97, 0.03), now=NOW,
                            min_edge=0.005) is not None
    # raise the bar beyond the edge -> out
    assert s.detect_endgame(m, books_factory(0.97, 0.03), now=NOW,
                            min_edge=0.03) is None


# ---------------------------------------------------------------------------
# smart money
# ---------------------------------------------------------------------------

def test_aggregate_buys_filters_and_sums():
    s = psc.PolyScanner()
    now = 1_000_000.0
    trades = [
        {"side": "BUY", "proxyWallet": "0xA", "conditionId": "0xC",
         "outcome": "Yes", "size": 100, "price": 0.5,
         "timestamp": now - 60, "title": "M1"},
        {"side": "BUY", "proxyWallet": "0xA", "conditionId": "0xC",
         "outcome": "Yes", "size": 200, "price": 0.6,
         "timestamp": now - 30, "title": "M1"},
        {"side": "SELL", "proxyWallet": "0xA", "conditionId": "0xC",
         "outcome": "Yes", "size": 500, "price": 0.5,
         "timestamp": now - 10, "title": "M1"},          # sell excluded
        {"side": "BUY", "proxyWallet": "0xB", "conditionId": "0xC",
         "outcome": "Yes", "size": 10, "price": 0.5,     # $5 < min_usd
         "timestamp": now - 10, "title": "M1"},
        {"side": "BUY", "proxyWallet": "0xB", "conditionId": "0xC",
         "outcome": "No", "size": 1000, "price": 0.5,
         "timestamp": now - 3 * 3600, "title": "M1"},    # outside window
    ]
    agg = s.aggregate_buys(trades, window_h=2.0, min_usd=50.0, now=now)
    assert len(agg) == 1
    a = agg[("0xA", "0xC", "Yes")]
    assert a["usd"] == pytest.approx(100 * 0.5 + 200 * 0.6)
    assert a["shares"] == pytest.approx(300)
    assert a["avg_price"] == pytest.approx((50 + 120) / 300)
    assert a["minutes_ago"] == pytest.approx(0.5)


def test_smart_money_signal():
    s = psc.PolyScanner(bankroll=100)
    m = s.parse_market(_endgame_raw(40, 0.50, 0.50,
                                    clobTokenIds='["tokY","tokN"]'))
    now = time.time()
    agg = {("0xWALLET", m["condition_id"], "Yes"): {
        "wallet": "0xWALLET", "conditionId": m["condition_id"],
        "outcome": "Yes", "title": "Will Thing happen?", "usd": 2500.0,
        "shares": 4000.0, "cost": 2000.0, "first_ts": now - 900,
        "last_ts": now - 60, "avg_price": 0.5, "minutes_ago": 1.0,
        "min_usd": 500.0, "copy_edge": 0.02,
        "wallet_pnl": 5234.5, "wallet_pnl_n": 37}}
    books = {"tokY": _book(asks=[(0.50, 5000)]),
             "tokN": _book(asks=[(0.50, 5000)])}
    s.fetch_books = lambda tokens: {t: books[t] for t in tokens}
    o = s.detect_smart_money(m, agg)
    assert o is not None
    assert o["strategy"] == "smart_money"
    assert o["wallet"] == "0xWALLET"
    assert o["outcome"] == "Yes"
    assert o["price"] == 0.5
    assert o["p_est"] == pytest.approx(0.52)
    assert o["edge_net"] == pytest.approx(0.02)
    assert "2,500" in o["rationale"]
    assert "wallet P&L +$5,234 (37 positions)" in o["rationale"]
    # high-frequency wallets get flagged as indicative only
    key = ("0xWALLET", m["condition_id"], "Yes")
    o2 = s.detect_smart_money(m, {key: dict(agg[key], wallet_pnl_n=900)})
    assert "indicative only" in o2["rationale"]


def test_smart_money_skips_settling_markets():
    s = psc.PolyScanner(bankroll=100)
    m = s.parse_market(_endgame_raw(-24, 0.50, 0.50,
                                    clobTokenIds='["tokY","tokN"]'))
    now = time.time()
    agg = {("0xWALLET", m["condition_id"], "Yes"): {
        "wallet": "0xWALLET", "conditionId": m["condition_id"],
        "outcome": "Yes", "title": "T?", "usd": 2500.0, "shares": 4000.0,
        "cost": 2000.0, "first_ts": now - 900, "last_ts": now - 60,
        "avg_price": 0.5, "minutes_ago": 1.0, "min_usd": 500.0,
        "copy_edge": 0.02}}
    books = {"tokY": _book(asks=[(0.50, 5000)]),
             "tokN": _book(asks=[(0.50, 5000)])}
    s.fetch_books = lambda tokens: {t: books[t] for t in tokens}
    assert s.detect_smart_money(m, agg) is None


def test_smart_money_rejects_crowded_or_far_entry():
    s = psc.PolyScanner(bankroll=100)
    m = s.parse_market(_endgame_raw(40, 0.50, 0.50,
                                    clobTokenIds='["tokY","tokN"]'))
    now = time.time()
    agg = {("0xWALLET", m["condition_id"], "Yes"): {
        "wallet": "0xWALLET", "conditionId": m["condition_id"],
        "outcome": "Yes", "title": "T?", "usd": 2500.0, "shares": 4000.0,
        "cost": 2000.0, "first_ts": now - 900, "last_ts": now - 60,
        "avg_price": 0.5, "minutes_ago": 1.0, "min_usd": 500.0,
        "copy_edge": 0.0005}}  # sub-half-cent copy edge
    books = {"tokY": _book(asks=[(0.50, 5000)]),
             "tokN": _book(asks=[(0.50, 5000)])}
    s.fetch_books = lambda tokens: {t: books[t] for t in tokens}
    assert s.detect_smart_money(m, agg) is None
    # no matching outcome in the market
    agg2 = dict(agg)
    key = ("0xWALLET", m["condition_id"], "Maybe")
    agg2[key] = dict(list(agg.values())[0], outcome="Maybe")
    del agg2[("0xWALLET", m["condition_id"], "Yes")]
    assert s.detect_smart_money(m, agg2) is None


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def test_score_signal_bounds_and_monotonic():
    low = strat.score_signal(
        "endgame", roi=0.01, edge_net=0.01, price=0.97,
        time_to_end_h=40, depth_usd=50, liquidity=2000,
        volume24h=6000, spread=0.02)
    high = strat.score_signal(
        "endgame", roi=0.05, edge_net=0.05, price=0.95,
        time_to_end_h=5, depth_usd=500, liquidity=50_000,
        volume24h=200_000, spread=0.001)
    assert 0.0 <= low <= 100.0
    assert high > low
    assert high == pytest.approx(min(100.0, high))


def test_score_signal_arb_dominates():
    arb = strat.score_signal(
        "binary_arb", roi=0.01, edge_net=0.01, price=0.99,
        depth_usd=100, time_to_end_h=30)
    directional = strat.score_signal(
        "endgame", roi=0.01, edge_net=0.01, price=0.97,
        depth_usd=100, time_to_end_h=30)
    assert arb > directional


# ---------------------------------------------------------------------------
# formatting (smoke)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# detail views (mocked HTTP)
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _fake_session(routes, books_payload):
    class FS:
        def get(self, url, params=None, **kw):
            for pat, fn in routes:
                if pat in url:
                    return _FakeResp(fn(url, params))
            raise AssertionError(f"unrouted GET {url}")

        def post(self, url, json=None, **kw):
            return _FakeResp(books_payload)

    return FS()


def test_market_detail_market_slug():
    s = psc.PolyScanner(bankroll=10)
    raw = _raw_market()
    books = [
        {"asset_id": "111",
         "bids": [{"price": "0.39", "size": "100"}],
         "asks": [{"price": "0.41", "size": "50"}]},
        {"asset_id": "222",
         "bids": [{"price": "0.58", "size": "100"}],
         "asks": [{"price": "0.60", "size": "50"}]},
    ]
    s.session = _fake_session(
        [("markets", lambda u, p: [raw] if p and p.get("slug") == "q-slug"
          else [])], books)
    d = s.market_detail("q-slug")
    assert d["market"]["slug"] == "q-slug"
    assert d["books"]["Yes"]["best_ask"] == (0.41, 50.0)
    assert d["books"]["No"]["best_ask"] == (0.60, 50.0)
    assert d["binary_arb"] is None      # 0.41 + 0.60 > 1
    assert d["endgame"] is None
    assert "Q?" in psc.format_detail(d)


def test_market_detail_event_slug_falls_back_to_event():
    s = psc.PolyScanner(bankroll=100)
    a = _raw_market()
    b = _raw_market(conditionId="0xb1", question="B?", slug="b-slug",
                    outcomes='["B1", "NoB"]',
                    clobTokenIds='["333", "444"]')
    event = {"title": "Grp", "slug": "grp-slug", "negRisk": True,
             "markets": [a, b]}
    books = [
        {"asset_id": "111", "bids": [],
         "asks": [{"price": "0.30", "size": "10"}]},
        {"asset_id": "333", "bids": [],
         "asks": [{"price": "0.30", "size": "10"}]},
    ]
    s.session = _fake_session(
        [("events", lambda u, p: [event]),
         ("markets", lambda u, p: [])], books)
    d = s.market_detail("grp-slug")
    assert d["type"] == "event"
    assert d["event_title"] == "Grp"
    assert d["yes_sum"] == pytest.approx(0.60)
    assert d["negrisk_arb"] is not None
    assert d["negrisk_arb"]["edge_net"] == pytest.approx(0.40, abs=1e-6)
    assert "SET ARB" in psc.format_event_detail(d)


def test_market_detail_not_found_raises():
    s = psc.PolyScanner()
    s.session = _fake_session(
        [("events", lambda u, p: []), ("markets", lambda u, p: [])], [])
    with pytest.raises(ValueError, match="not found"):
        s.market_detail("nope-slug")


def test_format_functions_smoke():
    s = psc.PolyScanner(bankroll=10)
    m = s.parse_market(_endgame_raw(12, 0.97, 0.03))
    table = psc.format_market_table([m], 5)
    assert "top markets" in table and "Q?" in table
    opp = s.detect_endgame(m, {m["token_ids"][0]: _book(asks=[(0.97, 2000)]),
                               m["token_ids"][1]: _book(asks=[(0.03, 2000)])},
                           now=NOW)
    report = {"bankroll": 10.0, "opportunities": [opp], "markets": [m]}
    text = psc.format_opportunities(report)
    assert "ENDGAME" in text and "sizing" in text
    empty = psc.format_opportunities({"bankroll": 10.0, "opportunities": []})
    assert "No opportunities" in empty
