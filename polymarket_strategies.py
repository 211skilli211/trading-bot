#!/usr/bin/env python3
"""
Polymarket strategy engine — fee model, Kelly sizing, signal scoring.
======================================================================
Pure functions only (no I/O): everything here is unit-testable offline on
this phone's Python 3.8. The scanner (polymarket_scanner.py) feeds market
data in; this module decides what is worth buying and how much.

Fee model
---------
Official formula (docs.polymarket.com/trading/fees, verified 2026-10-05):

    fee_usd = shares x feeRate x p x (1 - p)        (taker only, at match time)

Makers pay zero (and earn rebates); redemption is free. feeRate is set per
market *category* (the gamma field ``feeType``); the gamma fields
``makerBaseFee``/``takerBaseFee`` are a constant placeholder (1000) and are
NOT the rate. Rates below were verified against the 2026 schedule published
in Polymarket docs + multiple independent fee calculators:

    geopolitics / None      0.00   (fee-free category)
    zero_fees               0.00
    politics_fees           0.04
    tech_fees               0.04
    sports_fees_v2          0.03   (older sports markets)
    sports_fees_v3          0.05
    crypto_fees_v2          0.07
    economics_fees          0.05
    culture_fees            0.05
    weather_fees            0.05

Unknown/new fee types get a conservative default (0.05) — never assume free.

Sizing
------
Quarter-Kelly on the binary edge, with hard caps so a $10-35 bankroll can
never be blown by one signal:

    raw kelly fraction  = (p - c) / (1 - c)      [p = est. win prob, c = cost]
    stake = bankroll x min(raw x 0.25, cap_pct)
    shares = stake / c,  capped by max_stake_usd, floored by exchange min (5)

Strategy notes (research 2026-10-05, see references in the `polymarket`
skill and POLYMARKET_SETUP.md §9):
  * binary_arb / negrisk_arb — resolution-arithmetic locks (YES+NO < $1, or
    all-YES set < $1). Risk-free if fully filled; windows are seconds.
  * endgame — "quick win": buy the near-certain favorite (ask >= 0.93,
    <= 48h to resolution) for a small, fast, high-probability return.
  * smart_money — copy large buys by wallets with demonstrated P&L.
"""

from typing import Dict, Optional

# --------------------------------------------------------------------------
# Fee model
# --------------------------------------------------------------------------

FEE_RATES = {
    None: 0.0,
    "zero_fees": 0.0,
    "politics_fees": 0.04,
    "tech_fees": 0.04,
    "sports_fees_v2": 0.03,
    "sports_fees_v3": 0.05,
    "crypto_fees_v2": 0.07,
    "economics_fees": 0.05,
    "culture_fees": 0.05,
    "weather_fees": 0.05,
}

#: Conservative default for unknown fee types (never assume zero).
DEFAULT_FEE_RATE = 0.05


def fee_rate_for(fee_type: Optional[str], fees_enabled: bool = True) -> float:
    """Taker fee rate for a market, from its gamma fee fields."""
    if not fees_enabled:
        return 0.0
    if fee_type is None:
        return 0.0
    return FEE_RATES.get(fee_type, DEFAULT_FEE_RATE)


def taker_fee_per_share(price: float, fee_rate: float) -> float:
    """Taker fee (USD) charged for one share at `price`."""
    if fee_rate <= 0 or not (0.0 < price < 1.0):
        return 0.0
    return fee_rate * price * (1.0 - price)


def taker_fee_total(shares: float, price: float, fee_rate: float) -> float:
    """Taker fee (USD) for `shares` at `price`."""
    return taker_fee_per_share(price, fee_rate) * max(0.0, shares)


# --------------------------------------------------------------------------
# Kelly sizing
# --------------------------------------------------------------------------

MIN_SHARES = 5.0  # Polymarket minimum order size (shares)


def kelly_fraction(price: float, p_est: float, fraction: float = 0.25) -> float:
    """Kelly bankroll fraction for buying a binary at `price` with edge.

    Buying at cost c pays (1 - c) on a win, so b = (1-c)/c and
    f* = (b*p - q)/b = (p - c) / (1 - c).  Returns the *fractional* Kelly
    (quarter by default).  Never negative — no edge means no bet.
    """
    if not (0.0 < price < 1.0):
        return 0.0
    p_est = min(1.0 - 1e-9, max(0.0, p_est))
    raw = (p_est - price) / (1.0 - price)
    return max(0.0, raw * fraction)


def size_stake(
    bankroll: float,
    price: float,
    p_est: float,
    cap_pct: float = 0.25,
    max_stake_usd: Optional[float] = None,
    min_shares: float = MIN_SHARES,
) -> Dict:
    """Quarter-Kelly stake for one binary signal.

    Returns a dict with: stake_usd, shares, ok, reason, below_min.
    ``ok`` is False when the bankroll or math says "don't bet";
    ``below_min`` is True when the computed stake buys fewer shares than the
    exchange minimum (the signal is still valid — the caller decides).
    """
    if bankroll <= 0:
        return {"stake_usd": 0.0, "shares": 0.0, "ok": False,
                "reason": "bankroll <= 0", "below_min": False}
    if not (0.0 < price < 1.0):
        return {"stake_usd": 0.0, "shares": 0.0, "ok": False,
                "reason": "price out of (0,1)", "below_min": False}
    if p_est <= price:
        return {"stake_usd": 0.0, "shares": 0.0, "ok": False,
                "reason": "no edge (p_est <= price)", "below_min": False}

    frac = min(kelly_fraction(price, p_est), cap_pct)
    stake = bankroll * frac
    if max_stake_usd is not None:
        stake = min(stake, max_stake_usd)
    shares = round(stake / price, 2) if stake > 0 else 0.0
    below_min = shares < min_shares
    if below_min:
        # Report the minimum-sized version too, so the UI can show what a
        # $5-risk entry would look like.
        shares = round(min_shares, 2)
        stake = round(shares * price, 2)
    return {"stake_usd": round(stake, 2), "shares": shares, "ok": True,
            "reason": "ok", "below_min": below_min}


# --------------------------------------------------------------------------
# Signal scoring
# --------------------------------------------------------------------------

#: Higher = structurally safer / more valuable per unit of risk.
STRATEGY_PRIORITY = {
    "binary_arb": 100.0,
    "negrisk_arb": 100.0,
    "endgame": 70.0,
    "smart_money": 55.0,
    "momentum": 40.0,
}

#: ROI scaling per strategy for the profit component (roi_pct -> 100).
PROFIT_SCALE = {
    "binary_arb": 100.0,   # 1% edge on a locked arb is already great
    "negrisk_arb": 100.0,
    "endgame": 25.0,       # 4% net on a quick win is strong
    "smart_money": 30.0,
    "momentum": 33.0,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def score_signal(
    strategy: str,
    roi: float,
    edge_net: float,
    price: float,
    time_to_end_h: Optional[float] = None,
    depth_usd: float = 0.0,
    liquidity: float = 0.0,
    volume24h: float = 0.0,
    spread: float = 0.0,
) -> float:
    """Composite 0-100 signal score (weights per casatrick's 2026 bot study).

        score = 0.30*profit + 0.25*confidence + 0.20*priority
              + 0.15*urgency + 0.10*risk_reward
    """
    roi_pct = max(0.0, roi) * 100.0
    scale = PROFIT_SCALE.get(strategy, 30.0)
    profit = _clamp(roi_pct * scale)

    conf = _clamp(depth_usd / 3.0)          # $300 book depth nearby => 100
    if liquidity > 10_000:
        conf = _clamp(conf + 10)
    if volume24h > 50_000:
        conf = _clamp(conf + 10)
    if 0 < spread <= 0.01:
        conf = _clamp(conf + 10)

    prio = STRATEGY_PRIORITY.get(strategy, 40.0)

    if strategy in ("binary_arb", "negrisk_arb"):
        urgency = 100.0                      # acts now or the window closes
    elif time_to_end_h is None:
        urgency = 50.0
    else:
        urgency = _clamp(100.0 * (1.0 - time_to_end_h / 48.0))

    if strategy in ("binary_arb", "negrisk_arb"):
        risk_reward = 100.0                  # locked at resolution if filled
    else:
        risk_reward = _clamp((edge_net / max(price, 1e-6)) * 300.0)

    return round(
        0.30 * profit + 0.25 * conf + 0.20 * prio + 0.15 * urgency
        + 0.10 * risk_reward, 2)


# --------------------------------------------------------------------------
# Quick-win heuristics (endgame markets)
# --------------------------------------------------------------------------

#: Conservative probability priors for "effectively decided" favorites.
#: These are deliberately pessimistic: we only act when the ask is cheap
#: enough relative to even this shrunk estimate.
ENDGAME_PRIORS = (
    # (min ask, max hours to end, prior probability)
    (0.97, 24.0, 0.995),
    (0.95, 48.0, 0.99),
)


def endgame_prior(ask: float, time_to_end_h: Optional[float]) -> Optional[float]:
    """Conservative win-probability estimate for a near-decided favorite,
    or None when the market isn't endgame-ish enough to bet."""
    if time_to_end_h is None or time_to_end_h < 0:
        return None
    for min_ask, max_h, prior in ENDGAME_PRIORS:
        if ask >= min_ask and time_to_end_h <= max_h:
            return prior
    return None


def min_stake_for_min_shares(price: float, min_shares: float = MIN_SHARES) -> float:
    """Cheapest stake (USD) that satisfies the exchange minimum size."""
    return round(min_shares * price, 2)
