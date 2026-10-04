# cTrader Open API (QCG) — Phone-Side Setup

Direct control of your cTrader account (broker: **QCG**) from this phone —
no server hop. The connector speaks the official cTrader Open API:

```
OAuth URL:  https://id.ctrader.com/my/settings/openapi/grantingaccess  (?client_id&redirect_uri&scope&product=web)
Token:      https://openapi.ctrader.com/apps/token
Portal:     https://openapi.ctrader.com/apps   (app CRUD + redirect URIs + Playground)
Protobuf:   live.ctraderapi.com:5035   (or demo.ctraderapi.com:5035)  [TLS]
```

Verified on this phone:
- **2026-10-03**: both protobuf hosts reachable; full TLS + protobuf
  round-trip (Spotware `ctrader-open-api` 0.9.2, Python 3.8, Twisted 24.3.0,
  service-identity 24.2.0); fake credentials rejected cleanly with
  `CH_CLIENT_AUTH_FAILURE`.
- **2026-10-04**: full pipeline wired to the **live QCG account 47848046**
  ($10, 1:200, HEDGED): OAuth, account listing, balance, symbol specs, spot
  quotes, H1 bars, ExpectedMargin — all live-verified. Unit conventions and
  QCG contract sizes in §9/§10 below.

## 1. Dependencies (already installed on this phone)

```
pip install ctrader-open-api          # official Spotware SDK (py3.8 ok)
pip install "service-identity==24.2.0" # TLS verification; must be the
                                       # cryptography-42-compatible line
```

(`ctrader-open-api` pins `pyOpenSSL==24.1.0` + `protobuf==3.20.1`, which in
turn pins `cryptography` to 42.x. That's why service-identity must be 24.2.0,
not 26.1.0.)

> **PRoot gotcha:** the overlay can silently drop the SDK between sessions
> (pip metadata survives, the `.py` files vanish). Always verify at session
> start: `python3 -c "import ctrader_open_api"` — if it fails, the two pip
> installs above bring it back in ~30 s.

## 2. Create the API app (one-time, ~5 minutes)

The app portal is **openapi.ctrader.com** (a separate site from
my.ctrader.com — log in with the same cTrader ID):

1. Open **https://openapi.ctrader.com/apps** and log in with your cTrader ID.
2. **Add new app** → name it (e.g. `IBT`) → give a detailed description
   (improves approval speed) → **Save**.
3. Wait for the app status to become **active** (new apps with the trading
   scope can take up to 1–3 days to clear cTrader's review; often faster).
4. **Add a redirect URI** — a *separate step* (this is the one everyone
   misses, including us at first): app row → **Edit** → scroll to
   **Redirect URIs** → add `https://my.ctrader.com` → **Save**.
   (The first/default URI is a pre-filled *playground* placeholder and does
   **not** work for real authorisation.)
5. Copy the **Client ID** and **Client Secret** (row → **Credentials** →
   **View**).

> Note: if QCG already provides API-app credentials for their clients, use
> those instead and skip creation.

## 3. Store the app credentials

Put them in `.env` (git-ignored; also add to `secure_key_loader.py` if you
prefer encrypted storage):

```ini
CTRADER_CLIENT_ID=<client id>
CTRADER_CLIENT_SECRET=<client secret>
CTRADER_REDIRECT_URI=https://my.ctrader.com
```

Check at any time:

```bash
python3 trading_bot.py --ctrader-status
```

It reports SDK health, endpoint reachability, what's missing, and the next
step.

## 4. Authenticate (on the phone)

Two paths — pick one:

**Path A — standard OAuth (recommended, uses the registered redirect URI)**

```bash
# a) print the authorization URL
python3 trading_bot.py --ctrader-auth
# b) open that URL in your phone's browser, log in, tap Allow access
# c) you land on a URL ending in ?code=<AUTH_CODE>  (even if the page
#    errors, the code is in the address bar)
# d) exchange it — the code expires after ~1 minute, paste it quickly:
python3 trading_bot.py --ctrader-auth --ctrader-auth-code <AUTH_CODE>
```

If the consent page says *"Provided application does not contain provided
URI"*, the app has no matching redirect URI registered — go back to
§2 step 4 (Edit → Redirect URIs → add `https://my.ctrader.com` → Save),
then re-run `--ctrader-auth`.

**Path B — Playground (no redirect URI needed, tokens on one screen)**

1. **https://openapi.ctrader.com/apps** → your app row → **Playground** button.
2. Scope: **trading** → **Get token**.
3. The page shows `accessToken` + `refreshToken` for your cTID — copy both:

```bash
python3 trading_bot.py --ctrader-import <ACCESS_TOKEN> <REFRESH_TOKEN>
```

Tokens are saved to `data/ctrader_credentials.json` (chmod 600, git-ignored):
`access_token`, `refresh_token`, expiry. The connector auto-refreshes the
access token before each session (refresh works with client credentials
only — no redirect URI involved); force it anytime with `--ctrader-refresh`.
Access tokens live ~30 days; refresh tokens are valid indefinitely until you
re-authorise.

## 5. Select your account

```bash
python3 trading_bot.py --ctrader-accounts      # list linked accounts
python3 trading_bot.py --ctrader-account <id>  # set the default
```

(You should see your funded $10 live account here. Use `--ctrader-demo` on
any command to force the demo host instead.)

## 6. Try it

```bash
python3 trading_bot.py --ctrader-info          # balance / equity / positions
python3 trading_bot.py --ctrader-positions     # open positions + pending orders
python3 trading_bot.py --ctrader-quote EURUSD,GBPUSD,XAUUSD
python3 trading_bot.py --ctrader-bars EURUSD --ctrader-period H1 --ctrader-count 100
python3 trading_bot.py --ctrader-deals 20
```

## 7. Trading

```bash
# demo account — no confirmation needed
python3 trading_bot.py --ctrader-buy EURUSD --ctrader-lots 1 --ctrader-demo

# LIVE account — requires explicit --yes (the bot refuses otherwise)
python3 trading_bot.py --ctrader-buy EURUSD --ctrader-lots 1 \
    --ctrader-sl 1.1150 --ctrader-tp 1.1350 --yes

python3 trading_bot.py --ctrader-cancel <ORDER_ID>
python3 trading_bot.py --ctrader-close <POSITION_ID> [--close-lots 0.5]
```

(Lots are converted to raw volume via the symbol's contract — on QCG,
`--ctrader-lots 1` for EURUSD = 100,000 raw units = 10,000 EUR. See §10.)

Every order runs a **local preflight before anything is sent**: volume is
checked against the symbol's min/step/max, then ExpectedMargin + balance +
used margin are fetched and the order is refused with
`INSUFFICIENT_MARGIN` if the account can't carry it. (With the $10 live
account every order is refused here by design — that's the floor working,
not a bug.)

Orders are confirmed through cTrader's execution events (the API has no
order-response message); the command prints `ORDER_ACCEPTED` /
`ORDER_FILLED` / `ORDER_REJECTED` from the watch window. No confirmation in
the window ⇒ verify with `--ctrader-orders` / `--ctrader-positions`.

## 8. Demo account

- The Open API **cannot create accounts** (the protocol only has
  AccountAuth / GetAccountList / AccountLogout). Create the demo in QCG's
  platform: my.ctrader.com (cTrader web terminal) or the cTrader mobile app →
  **Open demo account** (instant, virtual $10,000).
- QCG routes `demo.ctraderapi.com` to the **same cluster** as live (verified:
  the demo host's account list returns the live account `isLive:true`). Once
  the demo account exists it shows up in `--ctrader-accounts` as `DEMO`:

```bash
python3 trading_bot.py --ctrader-accounts            # new id, marked DEMO
python3 trading_bot.py --ctrader-account <DEMO_ID> --ctrader-demo
python3 trading_bot.py --ctrader-info --ctrader-demo # balance $10,000 virtual
```

- **Never** mix environments: a LIVE account id on the demo host (or vice
  versa) fails with `CANT_ROUTE_REQUEST`.

## 9. QCG account & symbol facts (verified live 2026-10-04)

- Live account **47848046** (traderLogin 8008440), HEDGED, **1:200**
  (`leverageInCents=2000` ÷ 10; confirmed by ExpectedMargin: notional =
  margin × 200).
- Reference prices that day: BTC $84.8k · ETH $2,693 · BCH $315.8 · EURUSD
  1.1251 · XAU $4,142.7 · US30 51,163.
- Forex (EURUSD/XAU/US30) is **closed weekends** — spot events return the
  last session quote (stale timestamp). Crypto (BTC/ETH/BCH) trades 24/7.

| Symbol | 1.0 lot (raw units) | Min order | Min margin (USD) |
|--------|--------------------:|----------:|-----------------:|
| EURUSD / EURGBP | 100,000 u = 10,000 EUR | 1 lot | **$56.28** |
| XAUUSD | 100 u = 10 oz | 1 lot | $207.21 |
| BTCUSD | 10 u = **1 BTC** | 1 lot | $424.20 |
| ETHUSD | 1,000 u = 100 ETH | 1 lot | $1,347.73 |
| BCHUSD | 1,000 u = 100 BCH | 10 lots (=1,000 BCH) | $1,590.75 |
| US30 | 100 u = 10 index u | 1 lot | $2,558.33 |

## 10. Unit conventions (IMPORTANT — protocol constants, not per-symbol)

Verified against the official `OpenApiMessages.proto` **and** live QCG data.
Getting these wrong produces silently-off prices or rejected orders.

| Quantity | On the wire | In the CLI |
|----------|-------------|------------|
| spot / bar price | fixed-point int64 = **price × 100000** ("1/100000 of a price unit"). The symbol's `digits` field is **display precision only** — do NOT scale by it (BTC is off by ~100x otherwise). | float price |
| bar deltas | `Trendbar.low` absolute; `open/high/close = low + delta{Open,High,Close}` (all 1e5) | float |
| order/position/execution prices | **plain `double`** (NOT fixed-point): `limitPrice`, `stopLoss`, `takeProfit`, `executionPrice` | float price |
| relative SL/TP | int64 in 1/100000 of a price (1e5 scale) | — |
| volume | int64 raw units. **QCG: 1.0 lot = lotSize/100 raw units** (generic sample convention is 1 lot = 100). Must satisfy per-symbol `minVolume`/`stepVolume`/`maxVolume`. | lots (float) via `volume_for_symbol(lots, spec)` |
| money | int64, smallest currency unit (USD = cents) | dollars (`/10**moneyDigits`) |
| time | int64 ms since epoch (bars: `utcTimestampInMinutes` = minutes) | UTC |

Helpers: `price_raw(price)` / `price_float(raw)` (1e5, **no digits arg**),
`volume_for_symbol(lots, spec)`, `check_volume(spec, raw)`,
`money_float(raw, digits)`, `lots_display(raw, spec)`.

## 11. How much to fund for live trading (from §9 margins)

| Balance | Minimum orders you can place |
|---------|------------------------------|
| $10–$100 | **Nothing** — below every min margin ($10 account is a read-only demo of the wiring) |
| $300 | EURUSD/EURGBP only (56.28 = 19% of equity) |
| $500 | EURUSD + XAUUSD |
| $1,000 | + BTCUSD (min order = 1 BTC, 42% margin) |
| $2,000 | comfortable FX; BTC at ~21% margin |
| $5,000 | + ETHUSD, BCHUSD |
| $15,000 | + US30 (full range) |

**Recommendation:** $500 is the hard floor; **$1,000–$2,000** to start on
FX + BTC; **$5,000+** if you want ETH/gold/BCH. Keep used margin well under
~25% of equity, size SLs off the symbols' `slDistance`, and do the first
trades on the QCG demo account (§8) before funding live.

## Command reference

| Flag | Effect |
|------|--------|
| `--ctrader-status` | SDK / endpoints / credentials / next steps |
| `--ctrader-auth [--ctrader-auth-code CODE]` | OAuth URL or code exchange |
| `--ctrader-import ACCESS REFRESH` | Import tokens from the portal Playground |
| `--ctrader-refresh` | Force access-token refresh |
| `--ctrader-accounts` | List linked trading accounts |
| `--ctrader-account ID` | Set default account |
| `--ctrader-info` | Balance / equity / unrealized PnL / positions |
| `--ctrader-positions` | Open positions + pending orders |
| `--ctrader-orders` | Pending orders |
| `--ctrader-deals [N]` | Last N deals (default 20, 30-day window) |
| `--ctrader-symbols` | Enabled symbol table |
| `--ctrader-quote SYM[,SYM…]` | Live spot quotes (`--ctrader-wait N` s) |
| `--ctrader-bars SYM --ctrader-period H1 --ctrader-count N` | Historical bars |
| `--ctrader-buy / --ctrader-sell SYM --ctrader-lots N [--ctrader-sl P --ctrader-tp P --ctrader-comment C]` | Market order (live ⇒ `--yes`) |
| `--ctrader-cancel ORDER_ID` | Cancel pending order |
| `--ctrader-close POSITION_ID [--close-lots V]` | Close (part of) a position |
| `--ctrader-demo` | Force demo host for the command |

## Troubleshooting

| Error | Meaning / fix |
|-------|---------------|
| *"application does not contain provided URI"* | The requested redirect URI isn't registered on the app — app Edit → Redirect URIs → add it → Save (or use Path B, `--ctrader-import`) |
| `CH_CLIENT_AUTH_FAILURE` | Wrong/rotated Client ID or Secret — re-copy from the Open API portal |
| `CH_ACCESS_TOKEN_EXPIRED` / auth errors | Run `--ctrader-refresh`; if no refresh token, redo `--ctrader-auth` |
| `CH_ACCOUNT_NOT_FOUND` / account errors | Wrong account id — `--ctrader-accounts` |
| `SYMBOL_NOT_FOUND` | Symbol name differs on this broker (e.g. `EURUSD.c`) — `--ctrader-symbols` |
| `CONNECT_TIMEOUT` | Network drop — check connectivity, retry |
| `CANT_ROUTE_REQUEST` | Account-auth for an account that doesn't exist in this environment — usually a LIVE id on the demo host or vice-versa. List accounts on the matching host and set the right id (§8). |
| `ACCESS_DENIED` on code exchange | Auth code expired (>~60 s) or already used — re-authorize and paste faster, or use Playground import (Path B) |
| `TRADING_BAD_VOLUME` | Raw volume not a multiple of `stepVolume` / below `minVolume` — use the QCG contract size (§10); `--ctrader-lots` is converted via `volume_for_symbol` |
| `INSUFFICIENT_MARGIN` (local preflight) | Order's expected margin exceeds free margin — add funds or reduce size (§11) |
| prices look off by ~100x | Scaled by `10**digits` instead of the protocol 1e5 scale — use `price_float(raw)` (§10) |
| `import ctrader_open_api` fails mid-project | PRoot overlay dropped the SDK — re-run the two pip installs in §1 |
| order rejected at placement | Look at the `ORDER_REJECTED` execution event / `--ctrader-orders`; often min-volume, SL/TP too close to price, or symbol session closed |

## Security notes

- `data/ctrader_credentials.json` holds the OAuth tokens — it is chmod 600
  and git-ignored. Treat it like an API key; rotate the app secret if you
  suspect exposure.
- Live orders require `--yes` by design. The demo host is the safe
  playground: every command accepts `--ctrader-demo`.
- The Open API app scope is all-or-nothing per app; create a second app
  with read-only scope if you want a monitoring-only credential.
