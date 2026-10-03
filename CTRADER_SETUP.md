# cTrader Open API (QCG) — Phone-Side Setup

Direct control of your cTrader account (broker: **QCG**) from this phone —
no server hop. The connector speaks the official cTrader Open API:

```
OAuth:      https://openapi.ctrader.com/apps/{auth,token}
Protobuf:   live.ctraderapi.com:5035   (or demo.ctraderapi.com:5035)  [TLS]
```

Verified on this phone (2026-10-03):
- `live.ctraderapi.com:5035` and `demo.ctraderapi.com:5035` both reachable
- Full TLS + protobuf round-trip works (Spotware `ctrader-open-api` 0.9.2,
  Python 3.8, Twisted 24.3.0, service-identity 24.2.0)
- The server correctly rejects fake app credentials with
  `CH_CLIENT_AUTH_FAILURE` — with your real app credentials the same
  pipeline authenticates and trades.

## 1. Dependencies (already installed on this phone)

```
pip install ctrader-open-api          # official Spotware SDK (py3.8 ok)
pip install "service-identity==24.2.0" # TLS verification; must be the
                                       # cryptography-42-compatible line
```

(`ctrader-open-api` pins `pyOpenSSL==24.1.0` + `protobuf==3.20.1`, which in
turn pins `cryptography` to 42.x. That's why service-identity must be 24.2.0,
not 26.1.0.)

## 2. Create the API app (one-time, ~5 minutes)

1. Log in at **my.ctrader.com** with your QCG account (webtrader).
2. Open **Settings → Apps & API** (or the developer portal at
   api.ctrader.com) → **API Apps** → create a new app.
3. Name it e.g. `clever-curie`, set the redirect URI to
   `https://my.ctrader.com`, and grant the scope
   **“Account info and trading”** (you need both: read *and* trade).
4. Copy the **Client ID** and **Client Secret**.

> Note: newly created apps requesting the *trading* scope may go through a
> short cTrader review (up to 1–3 business days) before they can authorize.
> If QCG already provides API-app credentials for their clients, use those
> instead and skip creation.

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

## 4. Authenticate (OAuth, on the phone)

```bash
# a) print the authorization URL
python3 trading_bot.py --ctrader-auth
# b) open that URL in your phone's browser, log in, authorize
# c) you land on a URL ending in ?code=<AUTH_CODE>  (even if the page 404s,
#    the code is in the address bar)
# d) exchange it:
python3 trading_bot.py --ctrader-auth --ctrader-auth-code <AUTH_CODE>
```

Tokens are saved to `data/ctrader_credentials.json` (chmod 600, git-ignored):
`access_token`, `refresh_token`, expiry. The connector auto-refreshes the
access token before each session; force it anytime with `--ctrader-refresh`.

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
python3 trading_bot.py --ctrader-buy EURUSD --ctrader-lots 0.01 --ctrader-demo

# LIVE account — requires explicit --yes (the bot refuses otherwise)
python3 trading_bot.py --ctrader-buy EURUSD --ctrader-lots 0.01 \
    --ctrader-sl 1.0750 --ctrader-tp 1.0950 --yes

python3 trading_bot.py --ctrader-cancel <ORDER_ID>
python3 trading_bot.py --ctrader-close <POSITION_ID> [--close-lots 0.5]
```

Orders are confirmed through cTrader's execution events (the API has no
order-response message); the command prints `ORDER_ACCEPTED` /
`ORDER_FILLED` / `ORDER_REJECTED` from the watch window. No confirmation in
the window ⇒ verify with `--ctrader-orders` / `--ctrader-positions`.

## Unit conventions (important)

| Quantity  | On the wire                                    | In the CLI            |
|-----------|------------------------------------------------|-----------------------|
| volume    | int64, **1 lot = 100** (0.01-lot granularity)  | lots (float)          |
| spot px   | fixed-point int64, `price * 10^digits`         | float price           |
| bar px    | `Trendbar.low` absolute; `open/high/close = low + delta{Open,High,Close}` | float |
| money     | int64 in smallest currency unit (USD cents)    | dollars               |
| time      | int64 ms since epoch (bars: minutes)           | UTC timestamps        |

`--ctrader-lots 0.01` sends `volume=1`. Symbol min/step volume come from the
account's symbol table — check `--ctrader-symbols` if a size is rejected.

## Command reference

| Flag | Effect |
|------|--------|
| `--ctrader-status` | SDK / endpoints / credentials / next steps |
| `--ctrader-auth [--ctrader-auth-code CODE]` | OAuth URL or code exchange |
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
| `CH_CLIENT_AUTH_FAILURE` | Wrong/rotated Client ID or Secret — re-copy from Apps & API |
| `CH_ACCESS_TOKEN_EXPIRED` / auth errors | Run `--ctrader-refresh`; if no refresh token, redo `--ctrader-auth` |
| `CH_ACCOUNT_NOT_FOUND` / account errors | Wrong account id — `--ctrader-accounts` |
| `SYMBOL_NOT_FOUND` | Symbol name differs on this broker (e.g. `EURUSD.c`) — `--ctrader-symbols` |
| `CONNECT_TIMEOUT` | Network drop — check connectivity, retry |
| order rejected at placement | Look at the `ORDER_REJECTED` execution event / `--ctrader-orders`; often min-volume, SL/TP too close to price, or symbol session closed |

## Security notes

- `data/ctrader_credentials.json` holds the OAuth tokens — it is chmod 600
  and git-ignored. Treat it like an API key; rotate the app secret if you
  suspect exposure.
- Live orders require `--yes` by design. The demo host is the safe
  playground: every command accepts `--ctrader-demo`.
- The Open API app scope is all-or-nothing per app; create a second app
  with read-only scope if you want a monitoring-only credential.
