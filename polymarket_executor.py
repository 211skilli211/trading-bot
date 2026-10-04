#!/usr/bin/env python3
"""
Polymarket live-execution loop.

Closes the loop the scanner leaves open:
  - PmTrader      — L2-authenticated CLOB wrapper (USDC balance, open orders,
                    positions, order placement) on py-clob-client 0.34.6.
  - Ledger        — data/pm_ledger.json: every executed bet, its cost/fees,
                    and its settlement outcome (realized P&L).
  - Guards        — actual-cash check (never order more USDC than we hold),
                    daily loss cap (halt entries for the day),
                    position dedupe (never stack a second entry on a token
                    we already hold).
  - auto_execute  — take the top-N scanner opportunities (single-leg only)
                    and place limit BUYs, recording each in the ledger.
  - watch_settlements — follow open bets to resolution via gamma + data-api,
                    mark them settled, compute realized P&L, alert.

Fees: Polymarket taker fee = shares × fee_rate × p × (1-p), charged on the
winning side at settlement for fee-charging markets. The ledger records the
taker fee estimated at entry; settlement P&L is `shares×1 − cost − fee` on a
win, `−cost − fee` on a loss.

Safety:
  - No order is ever placed by these functions unless the caller explicitly
    did (CLI requires --yes upstream).
  - Every L2 call is wrapped: a bad/expired credential surfaces as a clean
    error, never a half-executed state.
  - Multi-leg arbitrage opportunities are NEVER auto-executed (legging risk:
    one leg fills, the other doesn't). Single-leg signals only.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import (ApiCreds, OrderArgs,
                                           BalanceAllowanceParams,
                                           AssetType)
    CLOB_AVAILABLE = True
except ImportError:
    CLOB_AVAILABLE = False

logger = logging.getLogger(__name__)

CLOB_HOST = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
CHAIN_ID = 137  # Polygon

LEDGER_PATH = os.path.join("data", "pm_ledger.json")
USDC_DECIMALS = 6
CASH_BUFFER_USD = 0.10  # keep a dust buffer so fee rounding never rejections


# ---------------------------------------------------------------------------
# Trader
# ---------------------------------------------------------------------------

class ClobAuthError(Exception):
    """L2 credentials missing/invalid."""


class PmTrader:
    """Thin, defensive wrapper over the 0.34.6 CLOB client."""

    def __init__(self, host: str = CLOB_HOST, chain_id: int = CHAIN_ID):
        if not CLOB_AVAILABLE:
            raise RuntimeError(
                "py-clob-client not installed — see POLYMARKET_SETUP.md / "
                "references/setup-recipe.md")
        self.host = host
        self.chain_id = chain_id
        self.key = os.environ.get("POLYMARKET_PRIVATE_KEY", "").strip()
        self.api_key = os.environ.get("POLYMARKET_API_KEY", "").strip()
        self.api_secret = os.environ.get("POLYMARKET_API_SECRET", "").strip()
        self.api_passphrase = os.environ.get(
            "POLYMARKET_API_PASSPHRASE", "").strip()
        placeholders = ("", "your_polymarket_polygon_private_key_here")
        if self.key in placeholders:
            raise ClobAuthError(
                "POLYMARKET_PRIVATE_KEY missing in .env — cannot trade")
        self._client = ClobClient(host, key=self.key, chain_id=chain_id)
        self.wallet: str = self._client.get_address()
        self._l2 = None  # lazy

    # ---- L2 session ----

    def _l2c(self):
        """L2-authenticated client (lazy; raises ClobAuthError if bad)."""
        if self._l2 is not None:
            return self._l2
        if not (self.api_key and self.api_secret and self.api_passphrase):
            raise ClobAuthError(
                "POLYMARKET_API_KEY/SECRET/PASSPHRASE missing in .env")
        try:
            c = ClobClient(self.host, key=self.key, chain_id=self.chain_id)
            c.set_api_creds(ApiCreds(api_key=self.api_key,
                                     api_secret=self.api_secret,
                                     api_passphrase=self.api_passphrase))
            # touch a private endpoint so failures surface now, not later
            c.get_orders()
            self._l2 = c
            return c
        except ClobAuthError:
            raise
        except Exception as e:
            raise ClobAuthError(
                "L2 auth failed ({}: {}) — run `python3 polymarket_check.py`".
                format(type(e).__name__, str(e)[:160]))

    # ---- read API ----

    def usdc_balance(self) -> float:
        """USDC cash available on Polymarket, in USD."""
        c = self._l2c()
        try:
            res = c.get_balance_allowance(
                BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
        except Exception as e:
            raise ClobAuthError(
                "balance fetch failed ({}: {})".format(
                    type(e).__name__, str(e)[:160]))
        raw = res.get("balance", "0") if isinstance(res, dict) else "0"
        try:
            return float(raw) / (10 ** USDC_DECIMALS)
        except (TypeError, ValueError):
            return 0.0

    def open_orders(self) -> List[Dict]:
        try:
            return self._l2c().get_orders() or []
        except ClobAuthError:
            raise
        except Exception:
            return []

    def order_status(self, order_id: str) -> Optional[Dict]:
        try:
            return self._l2c().get_order(order_id)
        except Exception:
            return None

    def positions(self) -> List[Dict]:
        """Our positions from the public data-api (no L2 needed)."""
        try:
            r = requests.get(
                f"{DATA_API}/positions",
                params={"user": self.wallet, "limit": 500}, timeout=30)
            if r.status_code == 200:
                return r.json() or []
        except requests.RequestException:
            pass
        return []

    # ---- write API ----

    def place_buy(self, token_id: str, price: float,
                  size: float) -> Dict:
        """Place a limit BUY. Returns {success, order_id, status, error}."""
        c = self._l2c()
        try:
            args = OrderArgs(price=price, size=size,
                             side="BUY", token_id=token_id)
            res = c.create_and_post_order(args)
        except Exception as e:
            return {"success": False, "order_id": None, "status": None,
                    "error": "{}: {}".format(type(e).__name__,
                                             str(e)[:200])}
        res = res or {}
        ok = bool(res.get("success"))
        return {
            "success": ok,
            "order_id": res.get("orderID"),
            "status": res.get("status"),
            "error": None if ok else str(
                res.get("errorMsg") or res.get("status") or res)[:200],
        }

    # ---- market state (public gamma) ----

    def market_by_slug(self, slug: str) -> Optional[Dict]:
        try:
            r = requests.get(f"{GAMMA_API}/markets",
                             params={"slug": slug}, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return data[0] if data else None
                if isinstance(data, dict):
                    return data
        except (requests.RequestException, ValueError):
            pass
        return None

    def best_ask(self, token_id: str) -> Optional[float]:
        try:
            r = requests.get(f"{self.host}/book/{token_id}", timeout=30)
            if r.status_code == 200:
                asks = (r.json() or {}).get("asks") or []
                if asks:
                    return min(float(a.get("price")) for a in asks
                               if a.get("price"))
        except (requests.RequestException, ValueError, TypeError):
            pass
        return None


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

def load_ledger() -> Dict:
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH) as f:
                data = json.load(f)
            if isinstance(data, dict) and "records" in data:
                return data
        except (ValueError, OSError):
            logger.warning("ledger corrupt — starting fresh")
    return {"records": []}


def save_ledger(ledger: Dict) -> None:
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    tmp = LEDGER_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(ledger, f, indent=2)
    os.replace(tmp, LEDGER_PATH)
    try:
        os.chmod(LEDGER_PATH, 0o600)
    except OSError:
        pass


def add_record(ledger: Dict, rec: Dict) -> Dict:
    """Append a record, persist, and return the (updated) ledger."""
    ledger["records"].append(rec)
    save_ledger(ledger)
    return ledger


def new_record(strategy: str, opp: Dict, order_id: str) -> Dict:
    return {
        "id": "pm-{}-{}".format(int(time.time()),
                                os.urandom(3).hex()),
        "ts": int(time.time()),
        "strategy": strategy,
        "slug": opp.get("slug", ""),
        "condition_id": opp.get("condition_id", ""),
        "question": opp.get("question", ""),
        "outcome": opp.get("outcome", ""),
        "token_id": opp.get("token_id", ""),
        "shares": float(opp.get("shares", 0)),
        "price": float(opp.get("price", 0)),
        "cost_usd": round(float(opp.get("price", 0)) *
                          float(opp.get("shares", 0)), 4),
        "fee_usd_est": round(float(opp.get("fee_rate", 0.0)) *
                             float(opp.get("price", 0)) *
                             (1 - float(opp.get("price", 0))) *
                             float(opp.get("shares", 0)), 4),
        "expected_profit_usd": float(opp.get("expected_profit_usd", 0)),
        "order_id": order_id,
        "status": "open",
        "resolution": None,
        "settled_pnl": None,
        "settle_ts": None,
    }


def ledger_summary(ledger: Dict, now: Optional[int] = None) -> Dict:
    now = now or int(time.time())
    day_start = (now // 86400) * 86400  # UTC midnight (epoch is UTC)
    open_recs = [r for r in ledger["records"] if r.get("status") == "open"]
    settled = [r for r in ledger["records"]
               if r.get("status") == "settled"]
    daily = sum(r.get("settled_pnl", 0) or 0 for r in settled
                if (r.get("settle_ts") or 0) >= day_start)
    return {
        "open_count": len(open_recs),
        "open_cost": round(sum(r.get("cost_usd", 0) or 0 for r in open_recs),
                           2),
        "settled_count": len(settled),
        "wins": sum(1 for r in settled
                    if r.get("resolution") == "win"),
        "losses": sum(1 for r in settled
                      if r.get("resolution") == "loss"),
        "realized_total": round(sum(r.get("settled_pnl", 0) or 0
                                    for r in settled), 2),
        "realized_today": round(daily, 2),
    }


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def holding_token(trader: PmTrader, token_id: str) -> bool:
    """True if we already hold this outcome token (API first, ledger fallback)."""
    try:
        for p in trader.positions():
            if p.get("asset") == token_id and float(
                    p.get("size", 0) or 0) > 0:
                return True
    except Exception:
        pass
    ledger = load_ledger()
    return any(r.get("token_id") == token_id and r.get("status") == "open"
               for r in ledger["records"])


def check_entry(trader: PmTrader, ledger: Dict, cost_usd: float,
                daily_loss_cap: float) -> Tuple[bool, str]:
    """All pre-flight guards for one entry. Returns (ok, reason)."""
    if daily_loss_cap > 0:
        daily = ledger_summary(ledger)["realized_today"]
        if daily <= -abs(daily_loss_cap):
            return False, (
                "daily loss cap hit (today ${:.2f}, cap ${:.2f}) — "
                "entries paused until next UTC day".format(daily,
                                                          daily_loss_cap))
    try:
        cash = trader.usdc_balance()
    except ClobAuthError as e:
        return False, str(e)
    if cash < cost_usd + CASH_BUFFER_USD:
        return False, (
            "insufficient USDC: have ${:.2f}, need ${:.2f} (+${:.2f} buffer)"
            .format(cash, cost_usd, CASH_BUFFER_USD))
    return True, "ok"


# ---------------------------------------------------------------------------
# Auto-execute
# ---------------------------------------------------------------------------

def auto_execute(report: Dict, trader: PmTrader, bankroll: float,
                 types: Tuple[str, ...] = ("endgame", "smart_money"),
                 max_n: int = 2, daily_loss_cap: float = 3.0,
                 dry_run: bool = False) -> Dict:
    """Execute the top-N single-leg opportunities from a scanner report.

    Returns {"executed": [...], "skipped": [...], "halted": bool,
             "cash_before": float}
    """
    import alerts
    ledger = load_ledger()
    opps = [o for o in report.get("opportunities", [])
            if o.get("strategy") in types and "legs" not in o]
    opps.sort(key=lambda o: o.get("score", 0), reverse=True)

    results = {"executed": [], "skipped": [], "halted": False,
               "cash_before": None}
    if not opps:
        results["skipped"].append(
            {"reason": "no matching opportunities "
                       "(types={})".format(",".join(types))})
        return results

    try:
        results["cash_before"] = trader.usdc_balance()
    except ClobAuthError as e:
        results["skipped"].append({"reason": str(e)})
        results["halted"] = True
        return results

    spent_this_run = 0.0
    for o in opps[: max(1, max_n)]:
        token = o.get("token_id", "")
        if not token:
            results["skipped"].append(
                {"id": o.get("id"), "reason": "no token_id"})
            continue
        if holding_token(trader, token):
            results["skipped"].append(
                {"id": o.get("id"),
                 "reason": "already holding this outcome"})
            continue
        # Re-quote: reject if the ask moved up > 2¢ since the scan
        try:
            ask = trader.best_ask(token)
        except Exception:
            ask = None
        price = o.get("price", 0.0)
        if ask and ask > price + 0.02:
            results["skipped"].append(
                {"id": o.get("id"),
                 "reason": "ask moved up: scan {:.3f} → now {:.3f}"
                           .format(price, ask)})
            continue
        shares = float(o.get("shares", 0))
        if shares < 5:
            results["skipped"].append(
                {"id": o.get("id"),
                 "reason": "sized below 5-share minimum"})
            continue
        cost = round(price * shares, 4)
        ok, reason = check_entry(trader, ledger, cost, daily_loss_cap)
        if dry_run:
            # A dry run previews strategy intent; the cash/cap check is
            # reported (not enforced) so a $0 wallet still sees the plan.
            results["executed"].append(
                {"id": o.get("id"), "strategy": o.get("strategy"),
                 "question": o.get("question"),
                 "outcome": o.get("outcome"), "shares": shares,
                 "price": price, "cost_usd": cost, "dry_run": True,
                 "cash_ok": ok,
                 "cash_note": "" if ok else reason})
            continue
        if not ok:
            if "daily loss cap" in reason:
                results["halted"] = True
                results["skipped"].append(
                    {"id": o.get("id"), "reason": reason})
                alerts.notify("⛔ Polymarket auto-run halted", reason)
                break
            results["skipped"].append(
                {"id": o.get("id"), "reason": reason})
            continue

        res = trader.place_buy(token, price, shares)
        if res.get("success"):
            rec = new_record(o.get("strategy", "?"), o, res.get("order_id"))
            rec["exec_result"] = res.get("status")
            add_record(ledger, rec)
            spent_this_run += cost
            results["executed"].append(rec)
            alerts.notify(
                "🟢 Polymarket BUY filled path open",
                "{id} {strategy} — {q}\nBuy {out} {sh:g} @ {pr:.3f} "
                "(${cost:.2f})\norder {oid}\nedge {edge}/share, "
                "expected +${exp:g}".format(
                    id=o.get("id", "?"), strategy=o.get("strategy"),
                    q=str(o.get("question", ""))[:80],
                    out=o.get("outcome"), sh=shares, pr=price,
                    cost=cost, oid=res.get("order_id"),
                    edge=o.get("edge_net", 0),
                    exp=o.get("expected_profit_usd", 0)))
        else:
            results["skipped"].append(
                {"id": o.get("id"), "reason": "order rejected: "
                                               + str(res.get("error"))})

    results["spent_this_run"] = round(spent_this_run, 2)
    return results


# ---------------------------------------------------------------------------
# Settlement watch
# ---------------------------------------------------------------------------

def _parse_json_str(x) -> List[str]:
    if isinstance(x, list):
        return [str(v) for v in x]
    if isinstance(x, str):
        try:
            v = json.loads(x)
            return [str(i) for i in v] if isinstance(v, list) else []
        except ValueError:
            return []
    return []


def settle_pnl(rec: Dict) -> float:
    """Net realized P&L for a settled record (fees estimated at entry)."""
    shares = rec.get("shares", 0) or 0
    cost = rec.get("cost_usd", 0) or 0
    fee = rec.get("fee_usd_est", 0) or 0
    if rec.get("resolution") == "win":
        return round(shares * 1.0 - cost - fee, 4)
    return round(-cost - fee, 4)


def watch_settlements(trader: PmTrader,
                      ledger: Optional[Dict] = None) -> Dict:
    """One pass: check every open ledger record against live market state.

    Resolution detection:
      1. data-api position `redeemable` → we won (shares redeemable at $1).
      2. gamma market `closed` + outcome price ≈1 for our side → win;
         ≈0 → loss.
    Returns {"settled": [...], "still_open": int, "errors": [...]}.
    """
    import alerts
    ledger = ledger or load_ledger()
    open_recs = [r for r in ledger["records"]
                 if r.get("status") == "open"]
    if not open_recs:
        return {"settled": [], "still_open": 0, "errors": []}

    try:
        pos_by_token = {str(p.get("asset")): p
                        for p in trader.positions()}
    except Exception as e:
        return {"settled": [], "still_open": len(open_recs),
                "errors": ["positions fetch: " + str(e)[:120]]}

    settled, errors = [], []
    for rec in open_recs:
        token = rec.get("token_id", "")
        outcome = str(rec.get("outcome", ""))
        pos = pos_by_token.get(token)
        resolution = None
        if pos:
            if pos.get("redeemable"):
                resolution = "win"
            else:
                closed, out_price = _market_state(trader, rec)
                cur = _fsafe(pos.get("curPrice"))
                price = out_price if out_price is not None else cur
                if closed and price is not None:
                    if price >= 0.9:
                        resolution = "win"
                    elif price <= 0.1:
                        resolution = "loss"
        else:
            closed, out_price = _market_state(trader, rec)
            if closed and out_price is not None:
                resolution = "win" if out_price >= 0.9 else "loss"
            else:
                # Position gone, market not confirmed closed — data lag.
                continue

        if resolution is None:
            # Position still there but market not confirmed closed.
            continue

        rec["status"] = "settled"
        rec["resolution"] = resolution
        rec["settled_pnl"] = settle_pnl(rec)
        rec["settle_ts"] = int(time.time())
        settled.append(rec)
        emoji = "✅" if resolution == "win" else "❌"
        alerts.notify(
            "{} Polymarket settled — ${:g} net".format(
                "WIN" if resolution == "win" else "LOSS",
                rec["settled_pnl"]),
            "{emoji} {q}\n{out} {sh:g} sh @ {pr:.3f} → "
            "{res} (net ${pnl:+.2f} incl. est. fees)\n"
            "{note}".format(
                emoji=emoji, q=str(rec.get("question", ""))[:80],
                out=rec.get("outcome"), sh=rec.get("shares", 0),
                pr=rec.get("price", 0), res=resolution.upper(),
                pnl=rec["settled_pnl"],
                note="Position is REDEEMABLE — redeem in Polymarket UI "
                     "(free) to release the USDC."
                     if (resolution == "win" and pos and
                         pos.get("redeemable"))
                     else ""))
    if settled:
        save_ledger(ledger)
    still = len(open_recs) - len(settled)
    return {"settled": settled, "still_open": still, "errors": errors}


def _fsafe(x) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _market_state(trader: PmTrader, rec: Dict):
    """(closed, price_of_our_outcome) from gamma for the record's slug."""
    m = trader.market_by_slug(rec.get("slug", ""))
    if not m:
        return False, None
    closed = bool(m.get("closed"))
    if not closed:
        return False, None
    outcomes = _parse_json_str(m.get("outcomes"))
    prices = _parse_json_str(m.get("outcomePrices"))
    outcome = str(rec.get("outcome", ""))
    if outcome in outcomes:
        i = outcomes.index(outcome)
    else:
        # fallback: match by condition + our token if prices align
        i = None
    if i is None and len(prices) >= 2:
        # binary: if we have exactly two outcomes and ours is missing,
        # unknown → don't guess
        return closed, None
    if i is not None and i < len(prices):
        p = _fsafe(prices[i])
        return closed, p
    return closed, None


# ---------------------------------------------------------------------------
# Balance / status report
# ---------------------------------------------------------------------------

def balance_report(trader: PmTrader) -> str:
    lines = []
    lines.append("💰 Polymarket — wallet " + trader.wallet)
    try:
        cash = trader.usdc_balance()
        lines.append("   USDC cash: ${:.4f}".format(cash))
    except ClobAuthError as e:
        lines.append("   USDC cash: ❌ " + str(e))
        cash = 0.0

    try:
        orders = trader.open_orders()
    except ClobAuthError:
        orders = []
    lines.append("   open orders: {}".format(len(orders)))
    for o in orders[:5]:
        lines.append("     • {} {} {} @ {} (id {})".format(
            o.get("side", "?"), o.get("size", "?"),
            o.get("price", "?"),
            (o.get("market") or "")[:24],
            str(o.get("id", ""))[:12]))

    pos = trader.positions()
    tot_val = 0.0
    for p in pos:
        tot_val += float(p.get("currentValue", 0) or 0)
    lines.append("   positions: {} (value ${:.2f})".format(
        len(pos), tot_val))
    for p in pos[:10]:
        mark = " ⚑redeemable" if p.get("redeemable") else ""
        lines.append("     • {} {} {} sh @ {} → {}${:.2f}{}".format(
            str(p.get("title", "?"))[:44],
            str(p.get("outcome", "?"))[:10],
            p.get("size", "?"), p.get("avgPrice", "?"),
            "PnL ", float(p.get("cashPnl", 0) or 0) +
            float(p.get("realizedPnl", 0) or 0), mark))

    led = load_ledger()
    s = ledger_summary(led)
    lines.append("   ledger: {} open (${:.2f}), {} settled "
                 "({}W/{}L), realized ${:+.2f}, today ${:+.2f}".format(
                     s["open_count"], s["open_cost"], s["settled_count"],
                     s["wins"], s["losses"], s["realized_total"],
                     s["realized_today"]))
    return "\n".join(lines)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
