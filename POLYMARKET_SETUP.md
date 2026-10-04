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

### 1. Polygon Wallet with USDC

PolyMarket trades using USDC on the Polygon network.

**Steps:**
1. Get a wallet that supports Polygon (MetaMask, Rainbow, etc.)
2. Add Polygon network to your wallet:
   - Network Name: Polygon Mainnet
   - RPC URL: https://polygon-rpc.com
   - Chain ID: 137
   - Currency Symbol: MATIC
   - Block Explorer: https://polygonscan.com

3. Bridge USDC from Ethereum to Polygon:
   - Use the official bridge: https://portal.polygon.technology/bridge
   - Or use a third-party bridge like Hop Exchange, Stargate, or Bungee
   - You need USDC on Polygon to trade (minimum $10-20 recommended)

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

# Your Polygon wallet private key (for signing transactions)
# This wallet must have USDC on Polygon network for trading
POLYMARKET_PRIVATE_KEY=your_polymarket_polygon_private_key_here

# CLOB API credentials (for order book access)
# Get API key at: https://docs.polymarket.com/#authentication
POLYMARKET_API_KEY=your_polymarket_api_key_here
POLYMARKET_API_SECRET=your_polymarket_api_secret_here
POLYMARKET_PASSPHRASE=your_polymarket_passphrase_here

# Polygon RPC endpoint
POLYGON_RPC_URL=https://polygon-rpc.com

# USDC token address on Polygon (don't change this)
USDC_POLYGON_ADDRESS=0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
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
cd /root/trading-bot
python3 polymarket_client.py
```

This will fetch markets and show arbitrage opportunities.

## Troubleshooting

### "Trading not enabled" error
- Check that POLYMARKET_API_KEY is set correctly in .env
- Ensure the key is not the placeholder "your_polymarket_api_key_here"

### "Insufficient balance" error
- Make sure you have USDC on Polygon (not Ethereum mainnet)
- Check your balance at https://polymarket.com/portfolio

### Orders not filling
- PolyMarket has low liquidity on some markets
- Try markets with higher volume (> $10,000 daily)
- Adjust your price to be closer to the current market price

### API errors
- Verify your API credentials are correct
- Check that your API key hasn't expired
- Ensure you have internet connectivity to clob.polymarket.com

## Fees

- Trading Fee: 2% per trade (taken from profit)
- Gas Fees: Minimal on Polygon (~$0.01-0.10 per transaction)

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
