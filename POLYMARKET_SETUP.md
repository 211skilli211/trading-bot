# PolyMarket Setup Guide

## Overview

PolyMarket is a decentralized prediction market platform on Polygon where you can trade YES/NO shares on real-world events. This guide will help you set up PolyMarket trading.

## Phone Environment — VERIFIED WORKING (2026-10-05)

Full pipeline verified **from the phone** (Python 3.8.10, PRoot userland):

- `clob.polymarket.com` + `gamma-api.polymarket.com` reachable ✅
- L2 API auth (HMAC headers with stored key/secret/passphrase) ✅ — `GET /data/orders` returned 0 open orders
- Wallet address derived from `POLYMARKET_PRIVATE_KEY`: `0xEd42...c9E6`
- EIP-712 order signing (keccak + secp256k1) produces valid 132-char signatures locally ✅
- `polymarket_check.py` — one-command verification (run: `python3 polymarket_check.py` from repo root)

**Credentials** live in `.env` (git-ignored, chmod 600): `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, `POLYMARKET_API_PASSPHRASE`, `POLYMARKET_PRIVATE_KEY`.

**Sizing note:** Polymarket markets carry a `minimum_order_size` (~5 shares).
This is the ONLY venue in our stack where a $10–35 bankroll can actually
trade (QCG's cheapest order needs $56.28 margin). Taker fees apply per
market category since 2026 (0 on geopolitics/zero_fees; 3–7% × p × (1−p)
otherwise — see the fee table in § "Trading Strategies").

### py-clob-client on Python 3.8 (install recipe)

`py-clob-client` declares `>=3.9.10` and its newest deps target py3.10 — but 0.34.6 installs and runs on 3.8.10 with this exact recipe (if the PRoot env loses `/usr/local`, redo in order):

```bash
pip install --ignore-requires-python --no-build-isolation \
  'cytoolz==0.12.1' 'bitarray==2.9.3' 'ckzg==2.1.7' 'coincurve==20.0.0' \
  'pydantic==2.10.6' 'pydantic-core==2.27.2' 'regex==2024.11.6' \
  'typing-extensions==4.13.2' 'annotated-types==0.6.0' \
  'eth-account==0.13.7' 'eth-utils==5.3.1' 'eth-typing==5.2.1' \
  'eth-abi==5.2.0' 'eth-keys==0.7.0' 'eth-rlp==2.2.0' 'eth-keyfile==0.8.1' \
  'rlp==4.1.0' 'hexbytes==1.3.1' 'eth-hash==0.7.1' \
  'h2==4.1.0' 'hpack==4.0.0' 'hyperframe==6.0.1' 'anyio==4.4.0' \
  py-clob-client
```

Why each pin (all verified 2026-10-05):
- `--ignore-requires-python` + `--no-build-isolation`: SDK declares py≥3.9.10; its pure-python sdists demand `setuptools>=77` (py≥3.9) in build isolation
- `ckzg==2.1.7`: last cp38/aarch64 wheel (2.1.8+ dropped 3.8)
- `coincurve==20.0.0`: cp38/aarch64 wheel + `>=3.8` (13.0.1 doesn't exist)
- `pydantic==2.10.6` / `pydantic-core==2.27.2`: last cp38 releases; newer pydantic-core is py3.9+ and builds via maturin (absent)
- `regex==2024.11.6`: last cp38 wheel; 2025+ sdists use PEP-639 license tables this setuptools can't parse
- `eth-*` 5.x/0.13.x generation: the 6.0/0.14 generation declares py≥3.10 and uses PEP-585 `collections.abc` generics at runtime (e.g. `Sequence[...]` in eth_typing)
- `eth-keyfile==0.8.1`: 0.9.x is py≥3.10, and eth-account 0.13.7 requires `<0.9.0`
- `h2==4.1.0` / `hpack==4.0.0`: hpack 4.1+ subclasses `tuple[bytes, bytes]` (PEP 585 runtime — 3.9+)
- `typing-extensions==4.13.2` / `annotated-types==0.6.0`: 4.16/0.8 use py3.9/3.10 stdlib internals (`_SpecialGenericAlias`, `types.EllipsisType`)
- `anyio==4.4.0`: 4.5+ imports `typing.TypeAlias` (py3.10)

**Code patch** (SDK ships py3.9+ annotations; ~2 min, idempotent): add `from __future__ import annotations` as first statement of every `.py` in `py_clob_client`, `py_order_utils`, `poly_eip712_structs`, `py_builder_signing_sdk` under `/usr/local/lib/python3.8/dist-packages/`. Safe: no `get_type_hints`/runtime annotation eval anywhere in those packages.

### 0.34.6 API deltas vs older SDKs

| Old | 0.34.6 |
|---|---|
| `ApiCredentials` | `ApiCreds` (in `clob_types`) |
| `client.address()` | `client.get_address()` |
| `OrderArgs(side="buy")` | `OrderArgs(side="BUY")` (uppercase string; `OrderType` enum is order *lifetime* GTC/FAK, not side) |
| `create_order` + manual post | `client.create_and_post_order(args)` → dict with `orderID`, `success` |
| `get_orders()` | same ✅, `cancel(id)` ✅, `cancel_all()` ✅ |

Repo code (`polymarket_trading.py`) is version-tolerant for all of the above.

## What You Need

### 1. Polymarket funding — pUSD era (verified on-chain 2026-10-05)

Since the pUSD migration Polymarket settles in **pUSD**
(`0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB`), not raw USDC. USDC in the
raw wallet is NOT tradable until wrapped to pUSD. Two layers:

**Layer 1 — get USDC into our wallet (you do this, no gas):**
Send USDC (native `0x3c499c542cEF5E3811E1192ce70d8cC03d5c3359` or
USDC.e `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` — both supported)
on **Polygon** to our wallet `0xEd42785Bb96799b957cB39D987553A9E8b71c9E6`
(derived from `POLYMARKET_PRIVATE_KEY`). Exchange / RedotPay / MetaMask
all work. Trace the tx on-chain: `python3 research/probe_tx.py <txhash>`
(traces any tx + dumps our wallet balances for all USDC variants + pUSD).

**Layer 2 — wrap to pUSD (the bot does this, ~$0.05 gas):**
1. Send **~0.3 POL** to the same address (few cents; any exchange that
   lists POL/MATIC on Polygon). The wallet needs gas for 3 tx.
2. `python3 trading_bot.py --polymarket-fund` — dry-run plan
   (shows USDC/pUSD/POL balances + the per-wallet bridge address).
3. `python3 trading_bot.py --polymarket-fund --yes` — sends:
   - USDC → Polymarket **bridge address** (per-wallet, from
     `POST bridge.polymarket.com/deposit`; Polymarket's relayer
     auto-wraps it to pUSD — *their* gas)
   - pUSD approve → standard CTF Exchange v2
   - pUSD approve → neg-risk CTF Exchange v2
4. `python3 trading_bot.py --polymarket-balance` → "pUSD cash: $X".

**Future top-ups:** send USDC *directly* to the bridge address (query it
with `--polymarket-fund` dry-run) — zero gas, relayer wraps it.

**Fallback if the bridge misbehaves:** `CollateralOnramp
0x93070a847efEf7F70739046A929D47a521F5B8ee .wrap(USDC, wallet, amount)`
(needs a prior USDC approve; 2 gas; docs list USDC.e as the asset —
native-USDC acceptance not confirmed, so the bridge is the default).
Unwrapping mirror: `CollateralOfframp
0x2957922Eb93258b93368531d39fAcCA3B4dC5854 .unwrap(...)`.

**Order signing (pUSD era):** CLOB moved to new exchange contracts with
the EIP-712 domain version "2" and a new 11-field Order struct; the old
SDK's `create_and_post_order` is rejected ("invalid order version").
Orders are signed locally by `pm_signer.py` (eth-account) and posted with
L2 HMAC — the executor (`polymarket_executor.py`) already uses this path.
The installed SDK carries the pUSD contract config via
`scripts/pusd_sdk_patch.py` (idempotent; re-run after any PRoot-overlay
reinstall, must print "PATCH OK").

**Safety notes:** dedicated wallet only, never main savings; the
executor caps spending at the declared bankroll
(`--polymarket-bankroll` / `POLYMARKET_BANKROLL`) and halts new entries
after a −$3 UTC-day realized loss (`--pm-daily-loss-cap`).
$10 is enough to start (5-share minimum orders, ~$5 typical endgame
entries).

### 2. PolyMarket API Credentials

For trading (placing/cancelling orders), you need CLOB API credentials.

**Steps to get API credentials:**
1. Go to https://polymarket.com/
2. Connect your wallet
3. Go to Settings or API section
4. Generate API Key, Secret, and Passphrase
5. Save these securely - they won't be shown again

### 3. Private Key (Optional but Recommended)

For programmatic withdrawals and advanced features, you may want to add your private key.

**⚠️ Security Warning:**
- Never share your private key
- Use a dedicated trading wallet with limited funds
- Consider using a hardware wallet

## Configuration

Add the following to your `.env` file:

```bash
# ============================================
# POLYMARKET (Binary Prediction Markets)
# ============================================

# Your Polygon wallet private key (for signing orders + pUSD funding)
# This wallet must have USDC on Polygon (wrapped to pUSD) for trading
POLYMARKET_PRIVATE_KEY=your_polymarket_polygon_private_key_here

# CLOB API credentials (L2 auth; scheme unchanged by the pUSD migration)
# Get at: polymarket.com -> Settings -> API
POLYMARKET_API_KEY=your_polymarket_api_key_here
POLYMARKET_API_SECRET=your_polymarket_api_secret_here   # base64
POLYMARKET_API_PASSPHRASE=your_polymarket_passphrase_here

# Polygon RPC fallbacks (pm_funding.py carries its own list; informational)
POLYGON_RPC_URL=https://polygon-bor-rpc.publicnode.com

# pUSD = settlement collateral (raw USDC does NOT trade until wrapped)
PUSD_POLYGON_ADDRESS=0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB
USDC_POLYGON_NATIVE=0x3c499c542cEF5E3811E1192ce70d8cC03d5c3359
USDC_POLYGON_BRIDGED=0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
```

## Trading Strategies (verified 2026-10-05)

Research + implementation live in:
- the global `polymarket` skill (`/root/.dsh/skills/polymarket/`) — the
  no-guesswork playbook (API facts, fees, strategies, CLI, error table)
- `polymarket_scanner.py` / `polymarket_strategies.py` in this repo

The four implemented strategies, in priority order:

1. **YES+NO binary arb** — ask(YES) + ask(NO) < $1 after taker fees on both
   legs. Locked profit at resolution; windows last seconds. Rare.
2. **Negative-risk set arb** — in a mutually-exclusive event group (gamma
   `negRisk` + `negRiskMarketID`), the sum of ALL outcomes' YES asks must be
   ~$1. If the full set's ask sum (after per-leg fees) is < $1, buy every
   outcome: exactly one pays $1. An outcome with no ask makes the set
   untradeable → skip (buying a partial set is a bet, not an arb).
3. **Endgame quick-win** — buy the near-certain favorite: ask ≥ 0.95 with
   ≤ 48h to resolution (≥ 0.97 with ≤ 24h), liquidity ≥ $2k, vol24h ≥ $5k,
   priced against a conservative prior (0.99 / 0.995). Small, fast,
   high-probability return — the workhorse for a small bankroll.
4. **Smart money** — copy large recent buys (≥ $500 by default) from
   data-api `/trades`, credentialed via wallet P&L from `/positions`.
   High-frequency wallets (>200 positions) are flagged "indicative only".

Sizing: quarter-Kelly on the edge, capped at 25% of bankroll per signal,
rounded up to the 5-share exchange minimum when below it. Bankroll comes
from `--polymarket-bankroll` or `$POLYMARKET_BANKROLL` (default $10).

### Fees (post-2025 model — NOT zero fees)

```
taker_fee = shares × feeRate × p × (1 − p)      (makers pay 0; redemption free)
```

feeRate per market category (gamma `feeType` field; the
`makerBaseFee`/`takerBaseFee` fields are a constant 1000 placeholder and are
NOT the rate):

| feeType | rate | notes |
|---|---|---|
| geopolitics / none / `zero_fees` | 0.00 | fee-free |
| `sports_fees_v2` | 0.03 | older sports markets |
| `politics_fees`, `tech_fees` | 0.04 | |
| `sports_fees_v3` | 0.05 | newer sports markets |
| `economics_fees`, `culture_fees`, `weather_fees` | 0.05 | |
| `crypto_fees_v2` | 0.07 | 5-min crypto up/down markets |
| unknown new type | 0.05 | conservative default in code |

At p = 0.5 the fee peaks (rate/4 of notional); it → 0 at extreme prices,
which is why endgame favorites still clear fees.

## Scanner & CLI (runs on the phone, no keys needed for scanning)

```bash
python3 trading_bot.py --polymarket-scan 20        # top 20 markets by 24h volume
python3 trading_bot.py --polymarket-opps          # full opportunity scan (~35s)
python3 trading_bot.py --polymarket-quickwins     # quick-wins only, sized
python3 trading_bot.py --polymarket-detail <market-slug-or-event-slug-or-0xID>
python3 trading_bot.py --polymarket-portfolio     # our positions + P&L
python3 trading_bot.py --polymarket-exec <slug> --pm-outcome "Yes" \
    --pm-shares 5 --pm-price 0.97 --yes           # place a limit BUY (--yes required)
python3 trading_bot.py --polymarket-bankroll 25   # sizing bankroll override
python3 polymarket_check.py                       # verify L2 credentials
```

Event slugs (e.g. `brazil-presidential-election`) render the whole negRisk
group with its all-YES ask sum. Minimum order: 5 shares.

## Execution loop (auto-execution + settlement tracking)

Closed-loop trading on top of the scanner — `polymarket_executor.py`:

```bash
# live pUSD cash + open orders + positions + realized-PnL ledger
python3 trading_bot.py --polymarket-balance

# DRY RUN first (no --yes): scan + show what WOULD be bought
python3 trading_bot.py --polymarket-auto 2

# real execution of the top-N single-leg signals (endgame + smart_money default)
python3 trading_bot.py --polymarket-auto 2 --yes

# one settlement pass: match open ledger bets against live market state,
# mark settled, record realized P&L, fire alerts
python3 trading_bot.py --polymarket-watch
```

Rules enforced by the executor (all in code; tested in
`tests/test_polymarket_executor.py`):

- **Single-leg only** — multi-leg arbs are never auto-executed (leg risk).
- **Cash guard** — reads live L2 pUSD cash; refuses entries the wallet can't
  pay (dry runs annotate instead of skip).
- **Bankroll cap** — cost ≤ `--polymarket-bankroll` / `POLYMARKET_BANKROLL`.
- **Daily loss cap** — realized P&L ≤ −`--pm-daily-loss-cap` (default $3)
  for the UTC day → no new entries until tomorrow.
- **Quote guard** — re-quotes the book at order time; skips if the ask moved
  >2¢ against the signal (stale-tape protection).
- **Ledger** — every entry/exit appended to `data/pm_ledger.json`
  (git-ignored); `--polymarket-watch` settles it against live state.
- **Telegram** — fill/settle/stop events go to the configured bot
  (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`; test with `--telegram-test`).

Resident mode (paper lab + Polymarket settlement in one loop):

```bash
python3 trading_bot.py --watch 300     # cycle every 300s; Ctrl-C stops cleanly
```

## API Endpoints (actual Polymarket, all reachable from this phone)

```
Gamma (public, no auth):
  GET https://gamma-api.polymarket.com/markets?active=true&closed=false
      &order=volume24hr&ascending=false&limit=100&offset=0
  GET https://gamma-api.polymarket.com/markets?slug=<market-slug>
  GET https://gamma-api.polymarket.com/markets/<0xConditionId>
  GET https://gamma-api.polymarket.com/events?slug=<event-slug>
CLOB (public):
  POST https://clob.polymarket.com/books   # body: [{"token_id": "..."}, ...]
  GET  https://clob.polymarket.com/price?token_id=...&side=buy
Data-API (public):
  GET https://data-api.polymarket.com/trades?limit=1000
  GET https://data-api.polymarket.com/positions?user=0xWALLET&limit=500
```

Key gamma market fields: `outcomes`/`outcomePrices`/`clobTokenIds` (JSON
strings), `bestBid`/`bestAsk`/`spread` (first outcome only), `volume24hr`,
`liquidityNum`, `endDateIso`, `negRisk` + `negRiskMarketID` +
`events[0].slug`, `feeType` + `feesEnabled`, `orderMinSize` (= 5 shares),
`orderPriceMinTickSize`.

## Testing

Test your configuration:

```bash
cd /workspace/clever-curie
python3 polymarket_check.py                        # L2 credentials + wallet
python3 trading_bot.py --polymarket-scan 10        # public data (no keys)
python3 trading_bot.py --polymarket-balance        # L2: cash, orders, ledger
```

## Troubleshooting

### "Trading not enabled" error
- Check that POLYMARKET_API_KEY is set correctly in .env
- Ensure the key is not the placeholder "your_polymarket_api_key_here"

### "pUSD cash: $0.00" / "Insufficient balance"
- USDC in the raw wallet is NOT tradable (pUSD era): run
  `--polymarket-fund --yes` (needs ~0.3 POL gas) to wrap via the bridge
- USDC on the wrong network (Ethereum mainnet) is invisible to Polymarket —
  must be Polygon; trace any deposit with `python3 research/probe_tx.py <hash>`
- "POL balance < 0.05" warning: send ~0.3 POL to the wallet first
- Dry-run `--polymarket-auto` annotations ("no cash") are the guard, not an error

### Orders not filling
- PolyMarket has low liquidity on some markets
- Try markets with higher volume (> $10,000 daily)
- Adjust your price to be closer to the current market price

### API errors
- Verify your API credentials are correct
- Check that your API key hasn't expired
- Ensure you have internet connectivity to clob.polymarket.com

## Risk Warning

⚠️ **Prediction markets involve risk:**
- Markets can resolve unexpectedly
- Liquidity may be low on some markets
- Oracle failures can affect resolution
- Only trade with funds you can afford to lose

## Resources

- PolyMarket: https://polymarket.com
- Documentation: https://docs.polymarket.com/
- CLOB API: https://docs.polymarket.com/#clob-api
- Polygon Bridge: https://portal.polygon.technology/bridge
