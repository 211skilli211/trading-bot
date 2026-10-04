#!/usr/bin/env python3
"""
Polymarket scanner — live opportunity discovery from public APIs.
=================================================================
Runs entirely on this phone's Python 3.8 + requests. No trading keys are
needed for scanning; only order execution (polymarket_trading.py) uses the
CLOB L2 credentials in .env.

Endpoints (all verified reachable from this phone, 2026-10-05):
    gamma  https://gamma-api.polymarket.com   markets / events (public)
    clob   https://clob.polymarket.com        POST /books batch order books
    data   https://data-api.polymarket.com    /trades /positions (public)

Detectors
--------
* binary_arb   — YES ask + NO ask < $1 (after taker fees on both legs).
* negrisk_arb  — multi-outcome event: sum of every outcome's YES ask
                 (after fees) < $1.  Requires ALL outcomes to have an ask —
                 an unpriced outcome means an incomplete set, which is a bet
                 not an arb.
* endgame      — "quick win": buy the near-certain favorite (ask >= 0.95,
                 <= 48h to resolution) at a conservative probability prior.
* smart_money  — large recent buys by wallets with demonstrated P&L
                 (data-api /trades + /positions).

Sizing uses polymarket_strategies.size_stake (quarter-Kelly, capped).
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

import polymarket_strategies as strat

logger = logging.getLogger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
DATA_API = "https://data-api.polymarket.com"

MIN_SHARES = strat.MIN_SHARES
DEFAULT_BANKROLL = 10.0


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _jarr(x) -> Optional[List[str]]:
    """Gamma encodes string arrays as JSON strings ('["Yes","No"]')."""
    if x is None:
        return None
    if isinstance(x, list):
        return [str(t) for t in x]
    try:
        v = json.loads(x)
        if isinstance(v, list):
            return [str(t) for t in v]
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def hours_to(end: Optional[datetime], now: Optional[datetime] = None) -> Optional[float]:
    if end is None:
        return None
    now = now or datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (end - now).total_seconds() / 3600.0


# --------------------------------------------------------------------------
# scanner
# --------------------------------------------------------------------------

class PolyScanner:
    """Scans Polymarket for liquid markets and tradable opportunities."""

    def __init__(self, bankroll: float = DEFAULT_BANKROLL, timeout: int = 30):
        self.bankroll = float(bankroll or DEFAULT_BANKROLL)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "clever-curie-bot/1.0"})
        self._books_cache: Dict[str, Dict] = {}

    # ---------------- data layer ----------------

    def parse_market(self, raw: Dict) -> Optional[Dict]:
        """Parse one gamma /markets row into a flat dict (or None)."""
        try:
            cond = raw.get("conditionId") or raw.get("condition_id")
            if not cond:
                return None
            outcomes = _jarr(raw.get("outcomes"))
            prices = _jarr(raw.get("outcomePrices"))
            tokens = _jarr(raw.get("clobTokenIds"))
            if not outcomes or not tokens:
                return None
            events = raw.get("events") or []
            ev = events[0] if isinstance(events, list) and events else {}
            fee_type = raw.get("feeType")
            m = {
                "condition_id": cond,
                "question": raw.get("question", ""),
                "slug": raw.get("slug", ""),
                "outcomes": outcomes,
                "prices": [float(p) for p in prices] if prices and prices[0] is not None else None,
                "token_ids": tokens,
                "best_bid": _f(raw.get("bestBid"), 0.0),
                "best_ask": _f(raw.get("bestAsk"), 0.0),
                "spread": _f(raw.get("spread"), 0.0),
                "volume24h": _f(raw.get("volume24hr"), 0.0),
                "volume": _f(raw.get("volumeNum") or raw.get("volume"), 0.0),
                "liquidity": _f(raw.get("liquidityNum") or raw.get("liquidity"), 0.0),
                "end": _parse_iso(raw.get("endDateIso") or raw.get("endDate")),
                "neg_risk": bool(raw.get("negRisk")),
                "neg_risk_market_id": raw.get("negRiskMarketID"),
                "event_slug": ev.get("slug") if isinstance(ev, dict) else None,
                "event_title": ev.get("title") if isinstance(ev, dict) else None,
                "fee_type": fee_type,
                "fees_enabled": bool(raw.get("feesEnabled", False)),
                "fee_rate": strat.fee_rate_for(fee_type, raw.get("feesEnabled", False)),
                "order_min_size": _f(raw.get("orderMinSize"), MIN_SHARES),
                "tick": _f(raw.get("orderPriceMinTickSize"), 0.01),
                "last_trade_price": _f(raw.get("lastTradePrice"), 0.0),
                "one_day_change": _f(raw.get("oneDayPriceChange"), 0.0),
                "closed": bool(raw.get("closed")),
                "active": bool(raw.get("active", True)),
            }
            # sanity: keep outcome/price/token counts aligned
            n = min(len(outcomes), len(tokens))
            if m["prices"]:
                n = min(n, len(m["prices"]))
            m["outcomes"] = outcomes[:n]
            m["token_ids"] = tokens[:n]
            if m["prices"]:
                m["prices"] = m["prices"][:n]
            return m
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("parse_market failed: %s", e)
            return None

    def fetch_markets(self, limit: int = 200, min_vol24h: float = 1000.0,
                      min_liquidity: float = 1000.0) -> List[Dict]:
        """Top active markets by 24h volume, liquid and open."""
        markets: List[Dict] = []
        offset = 0
        while len(markets) < limit:
            resp = self.session.get(
                f"{GAMMA_API}/markets",
                params={"active": "true", "closed": "false",
                        "order": "volume24hr", "ascending": "false",
                        "limit": 100, "offset": offset},
                timeout=self.timeout)
            resp.raise_for_status()
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                break
            for r in rows:
                m = self.parse_market(r)
                if m and m["volume24h"] >= min_vol24h and m["liquidity"] >= min_liquidity:
                    markets.append(m)
                if len(markets) >= limit:
                    break
            offset += 100
            if len(rows) < 100:
                break
            time.sleep(0.2)
        markets.sort(key=lambda m: m["volume24h"], reverse=True)
        return markets[:limit]

    def fetch_event_markets(self, event_slug: str) -> List[Dict]:
        """All markets in a (negative-risk) event group."""
        resp = self.session.get(f"{GAMMA_API}/events",
                                params={"slug": event_slug},
                                timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        out: List[Dict] = []
        for ev in data if isinstance(data, list) else []:
            for r in ev.get("markets", []) or []:
                m = self.parse_market(r)
                if m:
                    out.append(m)
        return out

    def fetch_books(self, token_ids: List[str]) -> Dict[str, Dict]:
        """Batch order books from the CLOB.  {token: {'bids':[[p,sz]...], 'asks':...}}

        bids sorted price-desc, asks price-asc (independent of server order).
        """
        books: Dict[str, Dict] = {}
        pending = [t for t in dict.fromkeys(token_ids) if t not in books]
        for i in range(0, len(pending), 25):
            chunk = pending[i:i + 25]
            try:
                resp = self.session.post(
                    f"{CLOB_API}/books",
                    json=[{"token_id": t} for t in chunk],
                    timeout=self.timeout)
                resp.raise_for_status()
                books.update(self._parse_books_payload(resp.json()))
            except requests.RequestException as e:
                logger.warning("books fetch failed: %s", e)
                time.sleep(0.3)
                continue
            time.sleep(0.15)
        return books

    def _parse_books_payload(self, payload) -> Dict[str, Dict]:
        out: Dict[str, Dict] = {}
        for b in payload:
            tok = b.get("asset_id")
            if not tok:
                continue
            bids = [(_f(x.get("price")), _f(x.get("size")))
                    for x in b.get("bids", []) or []]
            asks = [(_f(x.get("price")), _f(x.get("size")))
                    for x in b.get("asks", []) or []]
            bids = [bs for bs in bids if bs[0] > 0]
            asks = [asx for asx in asks if asx[0] > 0]
            bids.sort(key=lambda t: -t[0])
            asks.sort(key=lambda t: t[0])
            out[tok] = {"bids": bids, "asks": asks}
        return out

    # ---------------- book helpers ----------------

    @staticmethod
    def top_ask(book: Optional[Dict]) -> Optional[Tuple[float, float]]:
        """(price, size) of the best ask, or None."""
        if not book or not book.get("asks"):
            return None
        return book["asks"][0]

    @staticmethod
    def top_bid(book: Optional[Dict]) -> Optional[Tuple[float, float]]:
        if not book or not book.get("bids"):
            return None
        return book["bids"][0]

    @staticmethod
    def ask_depth_usd(book: Optional[Dict], within: float = 0.02) -> float:
        """USD notional available at/below best ask + `within` cents."""
        if not book or not book.get("asks"):
            return 0.0
        best = book["asks"][0][0]
        cap = best + within
        return sum(p * s for p, s in book["asks"] if p <= cap)

    @staticmethod
    def bid_depth_usd(book: Optional[Dict], within: float = 0.02) -> float:
        if not book or not book.get("bids"):
            return 0.0
        best = book["bids"][0][0]
        floor = best - within
        return sum(p * s for p, s in book["bids"] if p >= floor)

    # ---------------- detectors ----------------

    def detect_binary_arb(self, m: Dict, books: Dict[str, Dict],
                          min_edge: float = 0.005) -> Optional[Dict]:
        """YES ask + NO ask < $1 after taker fees on both legs."""
        if len(m["token_ids"]) != 2 or m["closed"]:
            return None
        yes_ask = self.top_ask(books.get(m["token_ids"][0]))
        no_ask = self.top_ask(books.get(m["token_ids"][1]))
        if not yes_ask or not no_ask:
            return None
        ay, an = yes_ask[0], no_ask[0]
        if not (0.0 < ay < 1.0 and 0.0 < an < 1.0):
            return None
        raw_sum = ay + an
        if raw_sum >= 1.0:
            return None
        fee = (strat.taker_fee_per_share(ay, m["fee_rate"])
               + strat.taker_fee_per_share(an, m["fee_rate"]))
        net = 1.0 - raw_sum - fee
        if net < min_edge:
            return None
        depth = min(self.ask_depth_usd(books.get(m["token_ids"][0])),
                    self.ask_depth_usd(books.get(m["token_ids"][1])))
        roi = net / raw_sum
        opp = self._base_opp(m, 0, "binary_arb", price=raw_sum,
                             p_est=1.0, edge_net=net, roi=roi,
                             depth_usd=depth)
        opp.update({
            "legs": [
                {"outcome": m["outcomes"][0], "price": ay,
                 "token_id": m["token_ids"][0]},
                {"outcome": m["outcomes"][1], "price": an,
                 "token_id": m["token_ids"][1]},
            ],
            "payout_per_set": 1.0,
            "rationale": (f"YES ask {ay:.3f} + NO ask {an:.3f} = {raw_sum:.3f} "
                          f"< $1.00; locked {net*100:.2f}%/set after fees "
                          f"(feeType={m['fee_type'] or 'free'})"),
        })
        return opp

    def detect_negrisk_arb(self, m: Dict, set_markets: List[Dict],
                           books: Dict[str, Dict],
                           min_edge: float = 0.005) -> Optional[Dict]:
        """All-outcome YES-ask set < $1 after per-leg fees.

        Every outcome in the group must have a live ask; if any outcome has
        no book the set is incomplete and buying the rest is a bet, not an
        arb.
        """
        if m["closed"] or not set_markets:
            return None
        legs: List[Dict] = []
        raw_sum = 0.0
        fee_sum = 0.0
        for sm in set_markets:
            if len(sm["token_ids"]) != 2:
                return None
            ask = self.top_ask(books.get(sm["token_ids"][0]))
            if not ask:
                return None
            p = ask[0]
            if not (0.0 < p < 1.0):
                return None
            legs.append({"outcome": sm["outcomes"][0], "question": sm["question"],
                         "price": p, "token_id": sm["token_ids"][0]})
            raw_sum += p
            fee_sum += strat.taker_fee_per_share(p, sm["fee_rate"])
        if raw_sum >= 1.0:
            return None
        net = 1.0 - raw_sum - fee_sum
        if net < min_edge:
            return None
        depths = [self.ask_depth_usd(books.get(l["token_id"])) for l in legs]
        depth = min(depths) if depths else 0.0
        roi = net / raw_sum
        opp = self._base_opp(m, 0, "negrisk_arb", price=raw_sum,
                             p_est=1.0, edge_net=net, roi=roi,
                             depth_usd=depth)
        opp.update({
            "legs": legs,
            "payout_per_set": 1.0,
            "n_outcomes": len(legs),
            "rationale": (f"{len(legs)}-outcome set: all-YES ask sum "
                          f"{raw_sum:.3f} < $1.00; locked {net*100:.2f}%/set "
                          f"after fees. Event: {m.get('event_title') or m['question']}"),
        })
        return opp

    def detect_endgame(self, m: Dict, books: Dict[str, Dict],
                       min_edge: float = 0.005, min_vol24h: float = 5000.0,
                       min_liquidity: float = 2000.0,
                       max_hours: float = 48.0,
                       now: Optional[datetime] = None) -> Optional[Dict]:
        """Quick win: buy the near-certain favorite before resolution."""
        if len(m["token_ids"]) != 2 or m["closed"]:
            return None
        if m["volume24h"] < min_vol24h or m["liquidity"] < min_liquidity:
            return None
        tte = hours_to(m["end"], now)
        if tte is None or tte > max_hours or tte < 0:
            return None
        best_side = -1
        best_ask = 0.0
        for i, tok in enumerate(m["token_ids"]):
            ask = self.top_ask(books.get(tok))
            if ask and ask[0] > best_ask:
                best_ask, best_side = ask[0], i
        if best_ask < 0.93:
            return None
        p_est = strat.endgame_prior(best_ask, tte)
        if p_est is None:
            return None
        fee = strat.taker_fee_per_share(best_ask, m["fee_rate"])
        edge_net = p_est - best_ask - fee
        if edge_net < min_edge:
            return None
        depth = self.ask_depth_usd(books.get(m["token_ids"][best_side]))
        roi = edge_net / best_ask
        opp = self._base_opp(m, best_side, "endgame", price=best_ask,
                             p_est=p_est, edge_net=edge_net, roi=roi,
                             depth_usd=depth, time_to_end_h=tte)
        opp["rationale"] = (
            f"favorite {m['outcomes'][best_side]!r} at ask {best_ask:.3f}, "
            f"{tte:.1f}h to resolution; conservative prior {p_est:.3f}; "
            f"net edge {edge_net*100:.2f}c/share after taker fee "
            f"({m['fee_type'] or 'free'}). {m['question']}")
        return opp

    def detect_smart_money(self, m: Dict, buys: Dict[Tuple[str, str, str], Dict],
                           min_edge: float = 0.001) -> Optional[Dict]:
        """Copy a large recent buy on THIS market by a credentialed wallet."""
        best: Optional[Dict] = None
        for (wallet, cond, outcome), agg in buys.items():
            if cond != m["condition_id"]:
                continue
            if agg["usd"] < agg.get("min_usd", 500):
                continue
            if best is None or agg["usd"] > best["usd"]:
                best = agg
        if best is None:
            return None
        # price = current ask for the bought outcome (our entry if we copy now)
        idx = None
        for i, o in enumerate(m["outcomes"]):
            if o.lower() == best["outcome"].lower():
                idx = i
                break
        if idx is None:
            return None
        books = self.fetch_books([m["token_ids"][idx]])
        ask = self.top_ask(books.get(m["token_ids"][idx]))
        if not ask:
            return None
        entry = ask[0]
        if not (0.01 < entry < 0.99):
            return None
        p_est = min(0.995, entry + best.get("copy_edge", 0.02))
        fee = strat.taker_fee_per_share(entry, m["fee_rate"])
        edge_net = p_est - entry - fee
        if edge_net < min_edge:
            return None
        depth = self.ask_depth_usd(books.get(m["token_ids"][idx]))
        tte = hours_to(m["end"])
        if tte is not None and tte < 0:
            return None  # settling: resolution disputes + locked capital
        roi = edge_net / entry
        opp = self._base_opp(m, idx, "smart_money", price=entry,
                            p_est=p_est, edge_net=edge_net, roi=roi,
                            depth_usd=depth, time_to_end_h=tte)
        pnl_txt = ""
        if best.get("wallet_pnl") is not None:
            n = best.get("wallet_pnl_n", 0)
            suffix = " — high-frequency wallet, indicative only" \
                if n > 200 else ""
            sign = "+" if best["wallet_pnl"] >= 0 else ""
            pnl_txt = (f", wallet P&L {sign}${abs(best['wallet_pnl']):,.0f} "
                       f"({n} positions){suffix}")
        opp["wallet"] = best["wallet"]
        opp["rationale"] = (
            f"wallet {best['wallet'][:10]}… bought "
            f"${best['usd']:,.0f} of {best['title'][:48]} ({best['outcome']}) "
            f"avg {best['avg_price']:.3f}, {best['minutes_ago']:.0f}m ago"
            f"{pnl_txt}. Entry now {entry:.3f}; copy-edge assumption "
            f"+{best.get('copy_edge', 0.02)*100:.0f}c.")
        return opp

    # ---------------- wallet P&L (data-api) ----------------

    def wallet_pnl(self, wallet: str) -> Optional[Tuple[float, int]]:
        """Total P&L (realized + cash) + position count for a wallet.

        Note: for high-frequency/market-maker wallets the open-position
        cashPnl dominates and the number is indicative only — callers should
        show the position count alongside it.
        """
        try:
            resp = self.session.get(
                f"{DATA_API}/positions",
                params={"user": wallet, "limit": 500},
                timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                return None
            total = 0.0
            for p in data:
                total += _f(p.get("realizedPnl")) + _f(p.get("cashPnl"))
            return total, len(data)
        except (requests.RequestException, ValueError) as e:
            logger.warning("wallet_pnl(%s) failed: %s", wallet, e)
            return None

    def fetch_recent_trades(self, limit: int = 1000) -> List[Dict]:
        try:
            resp = self.session.get(f"{DATA_API}/trades",
                                    params={"limit": limit},
                                    timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except requests.RequestException as e:
            logger.warning("fetch_recent_trades failed: %s", e)
            return []

    def aggregate_buys(self, trades: List[Dict], window_h: float = 2.0,
                       min_usd: float = 500.0, copy_edge: float = 0.02,
                       now: Optional[float] = None) -> Dict[Tuple[str, str, str], Dict]:
        """Aggregate large BUYs into {(wallet, conditionId, outcome): agg}."""
        now = now or time.time()
        cutoff = now - window_h * 3600
        agg: Dict[Tuple[str, str, str], Dict] = {}
        for t in trades:
            if t.get("side") != "BUY":
                continue
            ts = _f(t.get("timestamp"))
            if ts < cutoff:
                continue
            wallet = t.get("proxyWallet") or ""
            cond = t.get("conditionId") or ""
            outcome = t.get("outcome") or "?"
            if not (wallet and cond and outcome):
                continue
            size = _f(t.get("size"))
            price = _f(t.get("price"))
            usd = size * price
            if usd < min_usd:
                continue
            key = (wallet, cond, outcome)
            a = agg.setdefault(key, {"wallet": wallet, "conditionId": cond,
                                     "outcome": outcome, "title": t.get("title", ""),
                                     "usd": 0.0, "shares": 0.0, "cost": 0.0,
                                     "first_ts": ts, "last_ts": ts,
                                     "min_usd": min_usd, "copy_edge": copy_edge})
            a["usd"] += usd
            a["shares"] += size
            a["cost"] += usd
            a["first_ts"] = min(a["first_ts"], ts)
            a["last_ts"] = max(a["last_ts"], ts)
            if t.get("title"):
                a["title"] = t["title"]
        for a in agg.values():
            a["avg_price"] = (a["cost"] / a["shares"]) if a["shares"] else 0.0
            a["minutes_ago"] = (now - a["last_ts"]) / 60.0
        return agg

    # ---------------- internals ----------------

    def _base_opp(self, m: Dict, outcome_idx: int, strategy: str, price: float,
                  p_est: float, edge_net: float, roi: float,
                  depth_usd: float = 0.0,
                  time_to_end_h: Optional[float] = None) -> Dict:
        tte = time_to_end_h
        if tte is None:
            tte = hours_to(m["end"])
        sizing = strat.size_stake(self.bankroll, price, p_est, cap_pct=0.25)
        score = strat.score_signal(
            strategy, roi=roi, edge_net=edge_net, price=price,
            time_to_end_h=tte, depth_usd=depth_usd,
            liquidity=m["liquidity"], volume24h=m["volume24h"],
            spread=m["spread"])
        return {
            "strategy": strategy,
            "question": m["question"],
            "slug": m["slug"],
            "condition_id": m["condition_id"],
            "outcome_idx": outcome_idx,
            "outcome": m["outcomes"][outcome_idx] if outcome_idx < len(m["outcomes"]) else "?",
            "token_id": m["token_ids"][outcome_idx] if outcome_idx < len(m["token_ids"]) else "",
            "price": round(price, 4),
            "p_est": round(p_est, 4),
            "edge_net": round(edge_net, 4),
            "fee_rate": m["fee_rate"],
            "fee_type": m["fee_type"],
            "fee_per_share": round(strat.taker_fee_per_share(price, m["fee_rate"]), 5),
            "roi": round(roi, 4),
            "time_to_end_h": round(tte, 2) if tte is not None else None,
            "volume24h": m["volume24h"],
            "liquidity": m["liquidity"],
            "spread": m["spread"],
            "depth_usd": round(depth_usd, 2),
            "score": score,
            "bankroll": self.bankroll,
            "stake_usd": sizing["stake_usd"],
            "shares": sizing["shares"],
            "below_min": sizing["below_min"],
            "min_stake_usd": strat.min_stake_for_min_shares(price),
            "expected_profit_usd": round(edge_net * sizing["shares"], 2) if sizing["shares"] else 0.0,
        }

    # ---------------- orchestration ----------------

    def scan(self, limit: int = 200, min_edge: float = 0.005,
             nr_groups: int = 10, smart_window_h: float = 2.0,
             smart_min_usd: float = 500.0,
             now: Optional[datetime] = None) -> Dict:
        t0 = time.time()
        now = now or datetime.now(timezone.utc)
        markets = self.fetch_markets(limit=limit)
        logger.info("scanned %d markets", len(markets))

        # books for every token of every market (25 per request)
        all_tokens = [t for m in markets for t in m["token_ids"]]
        books = self.fetch_books(all_tokens)

        opps: List[Dict] = []
        for m in markets:
            for det, kwargs in (
                (self.detect_binary_arb, {"books": books, "min_edge": min_edge}),
                (self.detect_endgame, {"books": books, "min_edge": min_edge, "now": now}),
            ):
                try:
                    o = det(m, **kwargs)
                    if o:
                        opps.append(o)
                except Exception as e:  # pragma: no cover - defensive
                    logger.warning("%s(%s) failed: %s", det.__name__, m["slug"], e)

        # negative-risk sets: one representative market per group + full group
        seen_groups: Dict[str, Dict] = {}
        for m in markets:
            if m["neg_risk"] and m["event_slug"] and m["neg_risk_market_id"]:
                seen_groups.setdefault(m["neg_risk_market_id"], m)
        nr_checked = 0
        for g_id, rep in seen_groups.items():
            if nr_checked >= nr_groups:
                break
            try:
                group = self.fetch_event_markets(rep["event_slug"])
            except requests.RequestException as e:
                logger.warning("event fetch %s failed: %s", rep["event_slug"], e)
                continue
            if not group:
                continue
            nr_checked += 1
            group_tokens = [t for sm in group for t in sm["token_ids"]]
            gbooks = {k: v for k, v in books.items() if k in set(group_tokens)}
            gbooks.update(self.fetch_books(
                [t for t in group_tokens if t not in books]))
            try:
                o = self.detect_negrisk_arb(rep, group, gbooks, min_edge=min_edge)
                if o:
                    opps.append(o)
            except Exception as e:  # pragma: no cover
                logger.warning("negrisk detect failed: %s", e)

        # smart money: large recent buys, enriched with our scanned markets
        trades = self.fetch_recent_trades(limit=1000)
        buys = self.aggregate_buys(trades, window_h=smart_window_h,
                                   min_usd=smart_min_usd)
        sm_seen_wallets = set()
        sm_count = 0
        by_cond = {m["condition_id"]: m for m in markets}
        for key, agg in sorted(buys.items(), key=lambda kv: -kv[1]["usd"]):
            m = by_cond.get(key[1])
            if m is None:
                continue
            if sm_count >= 5:
                break
            try:
                if key[0] not in sm_seen_wallets:
                    sm_seen_wallets.add(key[0])
                    pnl = self.wallet_pnl(key[0])
                    if pnl is not None:
                        agg["wallet_pnl"], agg["wallet_pnl_n"] = pnl
                    time.sleep(0.1)
                o = self.detect_smart_money(m, {key: agg})
                if o:
                    opps.append(o)
                    sm_count += 1
            except Exception as e:  # pragma: no cover
                logger.warning("smart_money detect failed: %s", e)

        opps.sort(key=lambda o: -o["score"])
        for i, o in enumerate(opps):
            o["id"] = f"PM-{i + 1:02d}"

        return {
            "ts": now.isoformat(),
            "bankroll": self.bankroll,
            "markets": markets,
            "opportunities": opps,
            "stats": {
                "markets_scanned": len(markets),
                "books_fetched": len(books),
                "nr_groups_checked": nr_checked,
                "recent_trades": len(trades),
                "whale_buys": len(buys),
                "duration_s": round(time.time() - t0, 1),
            },
        }

    # ---------------- detail view ----------------

    def market_detail(self, slug_or_condition: str,
                      min_edge: float = 0.005) -> Dict:
        """Full detail for one market (or event group): books, fees, arbs."""
        ref = slug_or_condition
        raw = None
        if ref.startswith("0x") and len(ref) > 40:
            resp = self.session.get(f"{GAMMA_API}/markets/{ref}",
                                   timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()
        else:
            resp = self.session.get(f"{GAMMA_API}/markets",
                                    params={"slug": ref},
                                    timeout=self.timeout)
            resp.raise_for_status()
            rows = resp.json()
            raw = rows[0] if isinstance(rows, list) and rows else None
            if not raw:
                # maybe it's an *event* slug (a negRisk group)
                try:
                    evs = self.session.get(f"{GAMMA_API}/events",
                                           params={"slug": ref},
                                           timeout=self.timeout).json()
                except requests.RequestException:
                    evs = []
                if isinstance(evs, list) and evs:
                    return self.event_detail(evs[0], min_edge=min_edge)
        if not raw:
            raise ValueError(f"market or event not found: {ref}")
        m = self.parse_market(raw)
        if not m:
            raise ValueError(f"could not parse market: {ref}")
        books = self.fetch_books(m["token_ids"])
        out: Dict = {
            "market": m,
            "books": {
                m["outcomes"][i]: {
                    "best_bid": self.top_bid(books.get(t)),
                    "best_ask": self.top_ask(books.get(t)),
                    "bid_depth_usd": round(self.bid_depth_usd(books.get(t)), 2),
                    "ask_depth_usd": round(self.ask_depth_usd(books.get(t)), 2),
                    "levels": {"bids": books.get(t, {}).get("bids", [])[:5],
                               "asks": books.get(t, {}).get("asks", [])[:5]},
                } for i, t in enumerate(m["token_ids"])
            },
            "binary_arb": self.detect_binary_arb(m, books, min_edge=min_edge),
            "endgame": self.detect_endgame(m, books, min_edge=min_edge),
            "fee_rate": m["fee_rate"],
            "min_order_usd": strat.min_stake_for_min_shares(
                m["prices"][0] if m["prices"] else 0.5),
        }
        if m["neg_risk"] and m["event_slug"]:
            try:
                group = self.fetch_event_markets(m["event_slug"])
                out["neg_risk_group"] = self._negrisk_group_summary(
                    m, group, books, min_edge)
            except requests.RequestException as e:
                logger.warning("NR group summary failed: %s", e)
        return out

    def event_detail(self, event: Dict, min_edge: float = 0.005) -> Dict:
        """Detail view for an event (negRisk group)."""
        markets = [m for m in (self.parse_market(r)
                               for r in event.get("markets", []) or [])
                   if m]
        yes_tokens = [m["token_ids"][0] for m in markets
                      if len(m["token_ids"]) >= 1]
        books = self.fetch_books(yes_tokens)
        out: Dict = {
            "type": "event",
            "event_title": event.get("title", ""),
            "event_slug": event.get("slug", ""),
            "neg_risk": bool(event.get("negRisk")),
            "markets": markets,
            "negrisk_arb": None,
            "yes_sum": None,
        }
        if markets:
            rep = markets[0]
            out["negrisk_arb"] = self.detect_negrisk_arb(
                rep, markets, {k: v for k, v in books.items()
                                if k in set(yes_tokens)},
                min_edge=min_edge)
            s = 0.0
            any_priced = False
            for m in markets:
                ask = self.top_ask(books.get(m["token_ids"][0]))
                if ask:
                    s += ask[0]
                    any_priced = True
            out["yes_sum"] = round(s, 4) if any_priced else None
        return out

    def _negrisk_group_summary(self, rep: Dict, group: List[Dict],
                               books: Dict[str, Dict],
                               min_edge: float = 0.005) -> Dict:
        yes_tokens = [m["token_ids"][0] for m in group
                      if len(m["token_ids"]) >= 1]
        gbooks = {k: v for k, v in books.items() if k in set(yes_tokens)}
        gbooks.update(self.fetch_books([t for t in yes_tokens
                                        if t not in books]))
        s = 0.0
        priced = 0
        for m in group:
            ask = self.top_ask(gbooks.get(m["token_ids"][0]))
            if ask:
                s += ask[0]
                priced += 1
        return {
            "event_title": rep.get("event_title"),
            "n_outcomes": len(group),
            "priced_outcomes": priced,
            "yes_ask_sum": round(s, 4),
            "negrisk_arb": self.detect_negrisk_arb(rep, group, gbooks,
                                                   min_edge=min_edge),
        }


# --------------------------------------------------------------------------
# human-readable formatting
# --------------------------------------------------------------------------

def _fmt_money(x: float) -> str:
    if abs(x) >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if abs(x) >= 10_000:
        return f"${x/1000:.0f}k"
    return f"${x:,.0f}"


def format_market_table(markets: List[Dict], n: int = 20) -> str:
    lines = ["┌─ top markets by 24h volume " + "─" * 40]
    lines.append(f"│ {'Q':<44} {'YES':>6} {'VOL24h':>9} {'LIQ':>8} {'FEE':>4} {'ENDS':>9}")
    for m in markets[:n]:
        yes = m["prices"][0] if m["prices"] else None
        yes_txt = f"{yes:>6.3f}" if yes is not None else "     —"
        tte = hours_to(m["end"])
        if m.get("closed"):
            ends = "settled"
        elif tte is None:
            ends = "?"
        elif tte >= 0:
            ends = f"{tte:.0f}h"
        else:
            ends = "settling"  # end date passed, resolution pending
        fee = "0%" if m["fee_rate"] == 0 else f"{m['fee_rate']*100:.0f}%"
        lines.append(
            f"│ {m['question'][:44]:<44} {yes_txt} "
            f"{_fmt_money(m['volume24h']):>9} {_fmt_money(m['liquidity']):>8} "
            f"{fee:>4} {ends:>9}")
    lines.append("└" + "─" * 80)
    return "\n".join(lines)


def format_opportunities(report: Dict, n: int = 15) -> str:
    opps = report.get("opportunities", [])
    if not opps:
        return ("No opportunities right now — that's normal: arbs close in "
                "seconds and endgame picks depend on the tape. Re-run "
                "--polymarket-opps any time; it's free.")
    lines = [f"🎯 {len(opps)} opportunity(ies), bankroll ${report['bankroll']:.2f}:"]
    for o in opps[:n]:
        tte = (f", ends in {o['time_to_end_h']:.0f}h"
               if o.get("time_to_end_h") else "")
        lines.append(
            f"\n{o.get('id', '?')} [{o['strategy'].upper()}] "
            f"score {o['score']:.0f}/100 | {o['question'][:64]}")
        if "legs" in o:
            legs = ", ".join(f"{l['outcome'][:14]}@{l['price']:.3f}"
                             for l in o["legs"][:6])
            more = f" (+{len(o['legs'])-6} more)" if len(o["legs"]) > 6 else ""
            lines.append(f"   legs: {legs}{more}")
        else:
            lines.append(
                f"   buy {o['outcome']!r} @ {o['price']:.3f} "
                f"(est prob {o['p_est']:.3f}, net edge {o['edge_net']*100:.2f}c/share"
                f", fee {o['fee_per_share']*100:.3f}c/share{tte})")
        lines.append(
            f"   sizing: ${o['stake_usd']:.2f} = {o['shares']:.2f} shares"
            f"{' (raised to exchange min 5 shares)' if o.get('below_min') else ''}"
            f"  → expected ${o['expected_profit_usd']:.2f}"
            f"  [min order ${o['min_stake_usd']:.2f}]")
        lines.append(f"   {o['rationale']}")
    return "\n".join(lines)


def format_detail(d: Dict) -> str:
    if d.get("type") == "event":
        return format_event_detail(d)
    m = d["market"]
    lines = [
        f"📊 {m['question']}",
        f"   slug={m['slug']}  ends={m['end']}",
        f"   vol24h={_fmt_money(m['volume24h'])}  liq={_fmt_money(m['liquidity'])} "
        f"spread={m['spread']:.3f}  feeType={m['fee_type'] or 'free'} "
        f"(rate {m['fee_rate']:.0%})  min order={m['order_min_size']} shares",
        f"   negRisk={m['neg_risk']}  event={m.get('event_title') or '-'}",
    ]
    for outcome, b in d["books"].items():
        bid = b["best_bid"] or (0, 0)
        ask = b["best_ask"] or (0, 0)
        lines.append(
            f"   {outcome}: bid {bid[0]:.3f} (depth {b['bid_depth_usd']:.0f}) "
            f"| ask {ask[0]:.3f} (depth {b['ask_depth_usd']:.0f})")
    if d.get("binary_arb"):
        lines.append(f"   ✅ binary arb: {d['binary_arb']['rationale']}")
    else:
        lines.append("   binary arb: none")
    if d.get("endgame"):
        lines.append(f"   ✅ endgame quick-win: {d['endgame']['rationale']}")
    else:
        lines.append("   endgame: not a quick win right now")
    grp = d.get("neg_risk_group")
    if grp:
        lines.append(
            f"   negRisk group: {grp['n_outcomes']} outcomes "
            f"({grp['priced_outcomes']} priced), YES-ask sum "
            f"{grp['yes_ask_sum']:.3f}")
        if grp.get("negrisk_arb"):
            lines.append(f"   ✅ {grp['negrisk_arb']['rationale']}")
        else:
            lines.append("   negRisk arb: none")
    return "\n".join(lines)


def format_event_detail(d: Dict) -> str:
    lines = [
        f"📊 EVENT: {d.get('event_title') or d.get('event_slug')}"
        f"  (negRisk={d.get('neg_risk')}, {len(d.get('markets', []))} outcomes)"
    ]
    if d.get("yes_sum") is not None:
        arb = d.get("negrisk_arb")
        lines.append(
            f"   sum of all-YES asks: ${d['yes_sum']:.3f} "
            f"{'→ ✅ SET ARB ' + arb['rationale'] if arb else '→ no arb (>= $1.00)'}")
    for m in d.get("markets", []):
        p = m["prices"][0] if m.get("prices") else None
        price_txt = f"{p:>7.3f}" if p is not None else "      —"
        lines.append(
            f"   {m['question'][:56]:<56} {price_txt}  "
            f"vol24h {_fmt_money(m['volume24h']):>8}")
    return "\n".join(lines)
