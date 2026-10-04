# Finviz + Invo — research & trade-copying assessment

**Date:** 2026-10-05 · **Status:** research complete, nothing wired yet (decision pending)
Verified live from this phone where noted.

## TL;DR

| Tool | Verdict | Role in our stack |
|---|---|---|
| **Finviz** | Good **manual** research UI (reachable from phone, no API) | Human-in-the-loop layer: screen stocks, spot momentum/news/insider, then trade QCG equities through cTrader. NOT a bot data source (no public API; scraping = ToS gray + brittle). |
| **Invo** | Real copy-trading platform (crypto perps on Hyperliquid) | Optional **signal/copy layer**. Either use natively in-app (zero code) or tap its feed for signals we execute ourselves. Auth-gated reverse-engineered API = breakage risk; 1–10 s signal delay; Invo-routed fills pay a 0.35% builder fee. |
| **Better/faster research source** | **Yahoo chart API** (key-free, verified from phone) | The bot-native layer: same price/volume data finviz displays, via `query1.finance.yahoo.com`, no account, no key. Feeds a QCG-equni universe screener when we build one. |

## 1. Finviz — facts

- `finviz.com` reachable from the phone (HTTP 200, ~0.85 s). Free tier covers screener,
  heatmaps, news, watchlists; Elite (paid, ~$39/mo) adds alerts/insider depth —
  not justified at our bankroll.
- **No public/official API.** Access patterns:
  - manual browser use (fine — it's a research UI, not a data pipeline)
  - scraping `screener.ashx` HTML (fragile; anti-bot walls; ToS gray) — rejected
  - third-party scrapers (Apify actors, `pyfinviz`-style libs) — paid/fragile — rejected
- What finviz gives us that nothing else does well in one screen: sector heatmaps,
  relative-strength views, earnings/insider overlays, "Stage Analysis" options.
  Those are **discretionary research** — which is exactly where a human on a phone
  browser fits, not where a bot should scrape.

## 2. Programmatic research alternatives (bot-native)

Verified from this phone (2026-10-05):

| Source | Auth | Limits | Use |
|---|---|---|---|
| **Yahoo chart API** ✅ verified | none | unofficial; be gentle (1 req/s) | OHLCV bars any US ticker/ETF/index: `GET https://query1.finance.yahoo.com/v8/finance/chart/<SYMBOL>?range=1y&interval=1d` (plain `requests` + any UA). This is the fastest finviz replacement for *data*. |
| Finnhub | free key, 60 calls/min | fundamentals + company news + basic screener | if we want fundamentals filters without finviz |
| FMP (Financial Modeling Prep) | free key, ~250 calls/day | screener + fundamentals | same |
| EODHD | trial | EOD + intraday, "finviz alternative" per their own docs | same, paid after trial |
| yfinance (pip) | none | wraps Yahoo; py3.8-compatible versions exist but pinning pain — the raw endpoint above needs no dependency | skip until we need it |

**Recommendation:** build the research layer on the raw Yahoo endpoint (zero deps,
zero keys) + our own screener logic (momentum / relative-strength / volume filters
matching the Minervini SEA + regime-momentum templates we already have). Finviz
stays the human UI for cross-checking. When QCG live funding lands and the
equity sleeve makes sense, the screener outputs a QCG-tradable universe; the
strategy engine already runs on any OHLCV bars.

## 3. Invo — facts

- **Invo** (invoapp.com, Involio Inc.) = social-trading app, US market. Traders
  post *verified* real trades; followers copy positions. Execution venue:
  **Hyperliquid perps** (BTC/ETH/SOL/DOGE/XRP …, up to 40×).
- Official copy flow: in-app — follow traders, tap copy, funds sit in the
  Invo/Hyperlinked wallet. No public API, no broker integration.
- **Open-source copy stack exists:** `github.com/AKCodez/invo-copy-trader`
  (MIT, Node/TS) — reverse-engineered `api.invoapp.com` REST surface:
  - auth: `INVO_REFRESH_TOKEN` (JWT, ~350-day TTL) extracted from the app's
    encrypted local storage (AES-GCM decrypt of `FlutterSecureStorage` entry);
    agent key (~90-day) from IndexedDB; auto-refresh of 10-min access tokens.
  - discovery: `POST /v1_0/trending/get_portfolios_pl` (rank top traders by
    win-rate, P&L, W/L, liquidity)
  - signals: `POST /v1_0/posts/get_feed` — followed traders' verified trade
    posts carry ticker, direction, leverage, entry/exit price (1–10 s delay
    after execution — fine for copy trading, not for HFT)
  - execution: **direct on Hyperliquid** via HL SDK (IOC orders; Invo-routed
    orders pay a 0.35% builder fee — executing direct on HL avoids that)
  - risks called out by the project itself: RE API may change/break any time;
    credential re-extraction on expiry; platform ToS.
- **API is auth-gated** (verified from phone: unauthenticated POST →
  `{"status":"error","message":"Missing authorization header"}`).

### Options for us, ranked

1. **Native in-app copying (no code, now):** user opens Invo, funds its
   Hyperliquid wallet, follows vetted traders in-app. Pros: zero fragility,
   real-time, platform-managed. Cons: capital locked in Invo/HL, builder fee
   on Invo-routed fills, US app/account required. *Decision needed from user.*
2. **Signal tap (our code, later):** poll the RE feed for followed traders →
   route signals through our Telegram alerts → we execute on a venue we
   control (Hyperliquid direct or ccxt spot). Reuses our `alerts.py` + sizing
   discipline. Fragility = the RE API; build only after #1 proves the
   trader-selection process is worth copying.
3. **Polymarket smart-money copy (already built, now):** the copy layer we
   fully control — `--polymarket-auto` copies ≥$500 whale buys on the same
   venue with quarter-Kelly sizing. This is the "invo-class" feature for
   prediction markets, already shipped.

## 4. Fit with current state

- QCG live account: **parked, $10** (can't trade until funded; floor $56.28
  min-order margin @ 1:20).
- cTrader demo: **static book** (QCG demo cluster doesn't fill orders).
- Paper lab: running (ETH 1d + 4h regime-momentum, cross-validated configs).
- Polymarket: live loop running (executor + watch + alerts, needs USDC).
- So: finviz research feeds the *future* QCG equity sleeve; Invo is optional
  crypto-perp copy; the revenue-now path remains Polymarket + paper lab.

## 5. Actions

- [ ] User decision: open Invo account + fund HL wallet for native copy? (opt 1)
- [ ] User decision: fund Polymarket wallet `0xEd42…c9E6` (USDC on Polygon)
- [ ] When QCG funded: build Yahoo-API stock screener → QCG universe (this file
      is the data-source spec)
- [ ] Optional later: Invo feed signal tap (only after native copy proves out)
