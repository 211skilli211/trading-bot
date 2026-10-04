#!/usr/bin/env python3
"""
Trading Bot Dashboard — v2 (2026-10-05)
========================================
Self-contained Flask dashboard for the trading bot. No build step, no CDN,
no external assets: a single dark UI page served from this module plus
read-only JSON APIs.

Data sources (all local, all real — no mocks):
  * trades.db           — main loop trade log (TradeDatabase schema)
  * trades_legacy.db    — legacy trade log (TradingDatabase schema)
  * data/paper_state.json   — live paper-trading lab slots
  * data/ctrader_credentials.json — cTrader account / park status (secrets never shown)
  * data/polymarket_last_scan.json — most recent Polymarket scanner run
  * Binance public API  — live prices (30s cache, degrades gracefully)
  * bot.pid             — bot process control (PID-file based; never pkill -f)

Run standalone:
    python3 dashboard.py            # http://localhost:7777  (PORT env overrides)

Run embedded in the bot:
    python3 trading_bot.py --dashboard          # dashboard-only mode
    config dashboard.enabled=true               # dashboard in a background thread

Programmatic (used by the bot loop):
    import dashboard
    dashboard.update_dashboard(prices=..., trades=..., positions=..., stats=...)
    dashboard.run_dashboard(port=7777)

Replaces the old 4.4k-line dashboard.py (duplicate routes, dead code after
return, mock ML/zeroclaw/multi-agent/arbitrage endpoints, broken template
routes, and pkill-based bot control) and the React app in trading-dashboard/.
"""

import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from flask import Flask, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:  # pragma: no cover
    FLASK_AVAILABLE = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = os.environ.get("BOT_DIR", os.path.abspath(os.path.dirname(__file__)))

DB_MAIN = os.path.join(BASE_DIR, "trades.db")
DB_LEGACY = os.path.join(BASE_DIR, "trades_legacy.db")
PAPER_STATE = os.path.join(BASE_DIR, "data", "paper_state.json")
CTRADER_CREDS = os.path.join(BASE_DIR, "data", "ctrader_credentials.json")
POLY_SCAN = os.path.join(BASE_DIR, "data", "polymarket_last_scan.json")
PID_FILE = os.path.join(BASE_DIR, "bot.pid")
BOT_LOG = os.path.join(BASE_DIR, "bot.log")

PRICE_TTL = 30  # seconds
WATCHLIST = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE"]

# Live-loop snapshot (populated by update_dashboard from the bot process)
LIVE = {"prices": None, "trades": None, "positions": None, "stats": None,
        "updated_ts": 0}


# ---------------------------------------------------------------------------
# Data readers
# ---------------------------------------------------------------------------

def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _row_dicts(rows, fields):
    out = []
    for r in rows:
        d = {}
        for f in fields:
            try:
                d[f] = r[f]
            except (IndexError, KeyError):
                d[f] = None
        out.append(d)
    return out


def main_trades(limit=50):
    """Recent trades from the main loop DB (TradeDatabase schema)."""
    if not os.path.exists(DB_MAIN):
        return []
    try:
        conn = _connect(DB_MAIN)
        rows = conn.execute(
            """SELECT pair, direction, amount, open_rate, close_rate,
                      profit_abs, state, strategy, open_date, close_date, trade_id
               FROM trades ORDER BY open_date DESC LIMIT ?""", (limit,)).fetchall()
        conn.close()
        return [
            {
                "time": r["open_date"] or "",
                "symbol": r["pair"] or "",
                "side": (r["direction"] or "").upper(),
                "entry": r["open_rate"],
                "exit": r["close_rate"],
                "size": r["amount"],
                "pnl": r["profit_abs"],
                "state": r["state"] or "",
                "strategy": r["strategy"] or "",
                "source": "bot",
            }
            for r in rows
        ]
    except Exception:
        return []


def legacy_trades(limit=50):
    """Recent trades from the legacy DB (TradingDatabase schema)."""
    if not os.path.exists(DB_LEGACY):
        return []
    try:
        conn = _connect(DB_LEGACY)
        rows = conn.execute(
            """SELECT strategy, buy_exchange, buy_price, sell_price, quantity,
                      net_pnl, status, timestamp, trade_id
               FROM trades ORDER BY timestamp DESC LIMIT ?""", (limit,)).fetchall()
        conn.close()
        return [
            {
                "time": r["timestamp"] or "",
                "symbol": r["strategy"] or "",
                "side": (r["buy_exchange"] or "").upper(),
                "entry": r["buy_price"],
                "exit": r["sell_price"],
                "size": r["quantity"],
                "pnl": r["net_pnl"],
                "state": r["status"] or "",
                "strategy": r["strategy"] or "",
                "source": "legacy",
            }
            for r in rows
        ]
    except Exception:
        return []


def all_trades(limit=50):
    """Merged, newest-first trade feed across both DBs (best-effort sort)."""
    rows = main_trades(limit) + legacy_trades(limit)

    def key(r):
        t = str(r.get("time") or "")
        try:
            return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0

    rows.sort(key=key, reverse=True)
    return rows[:limit]


def trade_stats():
    """Aggregate stats across both trade DBs."""
    stats = {"trades": 0, "closed": 0, "wins": 0, "pnl": 0.0}
    try:
        if os.path.exists(DB_MAIN):
            conn = _connect(DB_MAIN)
            r = conn.execute(
                """SELECT COUNT(*) AS n,
                          COALESCE(SUM(CASE WHEN state NOT LIKE '%open%' THEN profit_abs END), 0) AS pnl,
                          SUM(CASE WHEN state NOT LIKE '%open%' AND profit_abs > 0 THEN 1 ELSE 0 END) AS wins,
                          SUM(CASE WHEN state NOT LIKE '%open%' THEN 1 ELSE 0 END) AS closed
                   FROM trades""").fetchone()
            stats["trades"] += int(r["n"] or 0)
            stats["pnl"] += float(r["pnl"] or 0)
            stats["wins"] += int(r["wins"] or 0)
            stats["closed"] += int(r["closed"] or 0)
            conn.close()
    except Exception:
        pass
    try:
        if os.path.exists(DB_LEGACY):
            conn = _connect(DB_LEGACY)
            r = conn.execute(
                """SELECT COUNT(*) AS n,
                          COALESCE(SUM(net_pnl), 0) AS pnl,
                          SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins
                   FROM trades WHERE net_pnl IS NOT NULL""").fetchone()
            stats["trades"] += int(r["n"] or 0)
            stats["closed"] += int(r["n"] or 0)
            stats["wins"] += int(r["wins"] or 0)
            stats["pnl"] += float(r["pnl"] or 0)
            conn.close()
    except Exception:
        pass
    stats["pnl"] = round(stats["pnl"], 2)
    stats["win_rate"] = round(100.0 * stats["wins"] / stats["closed"], 1) if stats["closed"] else 0.0
    return stats


def paper_state():
    """Paper-trading lab slots (data/paper_state.json)."""
    try:
        with open(PAPER_STATE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    slots = []
    for name, s in (data.get("slots") or {}).items():
        init = float(s.get("initial_capital") or 10000.0)
        equity = float(s.get("equity") or init)
        pos = s.get("position") or {}
        trades = s.get("trades") or []
        slots.append({
            "name": name,
            "equity": round(equity, 2),
            "initial": init,
            "pnl": round(equity - init, 2),
            "pnl_pct": round(100.0 * (equity - init) / init, 3) if init else 0.0,
            "open_position": bool(pos),
            "position_symbol": pos.get("symbol") or pos.get("pair") or "",
            "side": (pos.get("side") or "").upper(),
            "trades": len(trades),
            "fees": round(float(s.get("fees_paid") or 0.0), 2),
            "runs": int(s.get("runs") or 0),
            "last_bar_ts": s.get("last_processed_ts"),
        })
    return {"slots": slots, "created_ts": data.get("created_ts")}


def ctrader_status():
    """cTrader account / park status. Secrets are never included."""
    try:
        with open(CTRADER_CREDS) as f:
            c = json.load(f)
    except (OSError, ValueError):
        return None
    out = {
        "configured": bool(c.get("access_token")),
        "live_account": c.get("account_id"),
        "demo_account": c.get("account_id_demo"),
        "parked": bool(c.get("live_parked")),
        "parked_at": c.get("live_parked_at"),
        "token_days_left": None,
    }
    exp = c.get("access_token_expires_at")
    if exp:
        out["token_days_left"] = max(0, int((exp - time.time()) // 86400))
    return out


def polymarket_status():
    """Most recent scanner run (data/polymarket_last_scan.json)."""
    try:
        with open(POLY_SCAN) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    opps = sorted(data.get("opportunities") or [],
                  key=lambda o: float(o.get("expected") or 0.0), reverse=True)
    return {
        "ts": data.get("ts"),
        "scan_secs": data.get("scan_secs"),
        "bankroll": data.get("bankroll"),
        "count": data.get("count"),
        "top": opps[:5],
    }


# ---------------------------------------------------------------------------
# Prices (Binance public API, cached)
# ---------------------------------------------------------------------------

_price_cache = {"ts": 0.0, "data": None, "error": None}


def fetch_prices():
    """Watchlist + top movers from Binance. Cached 30s; degrades to cache/[] on error."""
    now = time.time()
    if _price_cache["data"] and now - _price_cache["ts"] < PRICE_TTL:
        return _price_cache
    if requests is None:
        return _price_cache
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=6)
        if resp.status_code != 200:
            raise RuntimeError("Binance HTTP %s" % resp.status_code)
        tickers = resp.json()
        tmap = {t["symbol"].replace("USDT", ""): t for t in tickers
                if t.get("symbol", "").endswith("USDT")}

        def fmt(base):
            t = tmap.get(base)
            if not t:
                return None
            return {
                "symbol": base,
                "price": float(t["lastPrice"]),
                "change": float(t["priceChangePercent"]),
                "volume": float(t.get("quoteVolume") or t.get("volume") or 0),
            }

        watch = [p for p in (fmt(b) for b in WATCHLIST) if p]
        others = [p for p in tmap.values()
                  if p["symbol"].replace("USDT", "") not in WATCHLIST
                  and float(p.get("quoteVolume") or 0) > 1_000_000]
        gainers = sorted(others, key=lambda t: float(t["priceChangePercent"]), reverse=True)[:6]
        losers = sorted(others, key=lambda t: float(t["priceChangePercent"]))[:6]

        _price_cache.update({
            "ts": now,
            "data": {
                "watch": watch,
                "gainers": [fmt(t["symbol"].replace("USDT", "")) or t for t in gainers],
                "losers": [fmt(t["symbol"].replace("USDT", "")) or t for t in losers],
            },
            "error": None,
        })
    except Exception as e:
        _price_cache["error"] = str(e)[:120]
    return _price_cache


# ---------------------------------------------------------------------------
# Bot control (PID-file based — never pkill/pgrep on command text)
# ---------------------------------------------------------------------------

def is_bot_running():
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
        return False


def start_bot(mode="paper"):
    if is_bot_running():
        return {"started": False, "message": "Bot already running"}
    proc = subprocess.Popen(
        [sys.executable, "trading_bot.py", "--mode", mode, "--monitor", "60"],
        cwd=BASE_DIR,
        stdout=open(BOT_LOG, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    with open(PID_FILE, "w") as f:
        json.dump({"pid": proc.pid, "mode": mode, "started_at": int(time.time())}, f)
    return {"started": True, "pid": proc.pid, "mode": mode}


def stop_bot():
    pid = None
    try:
        with open(PID_FILE) as f:
            pid = int(json.load(f).get("pid", 0))
    except (OSError, ValueError):
        pass
    if not pid:
        return {"stopped": False, "message": "No bot PID on file (not running here)"}
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError:
        return {"stopped": False, "message": "Not permitted to signal PID %d" % pid}
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
    return {"stopped": True, "pid": pid}


# ---------------------------------------------------------------------------
# Programmatic API (used by trading_bot.py)
# ---------------------------------------------------------------------------

def update_dashboard(prices=None, trades=None, positions=None, stats=None):
    """Store a live snapshot from the bot loop for the dashboard to display."""
    if prices is not None:
        LIVE["prices"] = prices
    if trades is not None:
        LIVE["trades"] = trades
    if positions is not None:
        LIVE["positions"] = positions
    if stats is not None:
        LIVE["stats"] = stats
    LIVE["updated_ts"] = int(time.time())


def run_dashboard(port=7777, host="0.0.0.0"):
    """Run the dashboard server (blocking)."""
    if not FLASK_AVAILABLE:
        print("❌ Dashboard unavailable: flask is not installed (pip install flask)")
        return
    print("=" * 60)
    print("🌐 Trading Dashboard v2")
    print("   URL: http://localhost:%d" % port)
    print("   Data: %s" % BASE_DIR)
    print("=" * 60)
    app.run(host=host, port=port, debug=False, threaded=True)


# ---------------------------------------------------------------------------
# Flask app + API
# ---------------------------------------------------------------------------

app = Flask(__name__)


@app.route("/api/healthz")
def api_healthz():
    return jsonify({"status": "ok", "ts": int(time.time())})


@app.route("/api/overview")
def api_overview():
    prices = fetch_prices()
    live_stats = LIVE.get("stats")
    return jsonify({
        "bot": {
            "running": is_bot_running(),
            "live": bool(LIVE.get("updated_ts")),
            "live_updated_ts": LIVE.get("updated_ts"),
            "live_stats": live_stats,
        },
        "trade_stats": trade_stats(),
        "paper": paper_state(),
        "ctrader": ctrader_status(),
        "polymarket": polymarket_status(),
        "prices": {
            "watch": prices["data"]["watch"] if prices["data"] else None,
            "gainers": prices["data"]["gainers"] if prices["data"] else [],
            "losers": prices["data"]["losers"] if prices["data"] else [],
            "error": prices["error"],
        },
        "trades": all_trades(20),
    })


@app.route("/api/trades")
def api_trades():
    limit = min(int(request.args.get("limit", 50)), 500)
    return jsonify({"trades": all_trades(limit), "stats": trade_stats()})


@app.route("/api/paper")
def api_paper():
    return jsonify(paper_state() or {"slots": []})


@app.route("/api/ctrader")
def api_ctrader():
    return jsonify(ctrader_status() or {})


@app.route("/api/polymarket")
def api_polymarket():
    return jsonify(polymarket_status() or {})


@app.route("/api/prices")
def api_prices():
    p = fetch_prices()
    return jsonify({"data": p["data"], "error": p["error"], "ts": int(p["ts"])})


@app.route("/api/bot/start", methods=["POST"])
def api_bot_start():
    return jsonify(start_bot(request.form.get("mode", "paper")))


@app.route("/api/bot/stop", methods=["POST"])
def api_bot_stop():
    return jsonify(stop_bot())


# ---------------------------------------------------------------------------
# UI (single self-contained page — dark, responsive, no external assets)
# ---------------------------------------------------------------------------

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0b0f17">
<title>Trading Bot</title>
<style>
:root{
  --bg:#0b0f17;--panel:#111827;--panel2:#0f1522;--line:#1f2a3d;
  --txt:#e5e9f0;--dim:#8b98ad;--green:#22c55e;--red:#ef4444;
  --amber:#f59e0b;--blue:#38bdf8;--violet:#a78bfa;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:14px/1.5 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;padding:16px}
h1{font-size:18px;font-weight:650;letter-spacing:.2px}
header{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:14px}
.pill{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);
  background:var(--panel);border-radius:999px;padding:4px 12px;font-size:12px;color:var(--dim)}
.pill b{color:var(--txt);font-weight:600}
.dot{width:8px;height:8px;border-radius:50%;background:var(--dim)}
.dot.on{background:var(--green);box-shadow:0 0 8px var(--green)}
.dot.off{background:var(--red)}
.dot.warn{background:var(--amber)}
.grid{display:grid;gap:12px}
.g3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.g2{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.card h2{font-size:12px;text-transform:uppercase;letter-spacing:.8px;color:var(--dim);margin-bottom:10px}
.row{display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid var(--panel2)}
.row:last-child{border-bottom:none}
.row .k{color:var(--dim)}
.muted{color:var(--dim);font-size:12px}
.pos{color:var(--green)} .neg{color:var(--red)} .amb{color:var(--amber)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--dim);font-weight:500;text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
td{padding:6px 8px;border-bottom:1px solid var(--panel2)}
tr:hover td{background:var(--panel2)}
.tag{display:inline-block;padding:1px 7px;border-radius:6px;font-size:11px;background:var(--panel2);border:1px solid var(--line);color:var(--dim)}
.btn{border:1px solid var(--line);background:var(--panel2);color:var(--txt);border-radius:8px;padding:6px 14px;cursor:pointer;font-size:13px}
.btn:hover{border-color:var(--dim)}
.btn.danger{border-color:#7f1d1d;color:#fca5a5}
.stats{display:flex;flex-wrap:wrap;gap:12px}
.stat{flex:1;min-width:120px;background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px}
.stat .v{font-size:18px;font-weight:650}
.stat .l{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
footer{margin-top:14px;color:var(--dim);font-size:12px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.section{margin-bottom:12px}
@media (max-width:600px){body{padding:10px}.stat{min-width:45%}}
</style>
</head>
<body>
<header>
  <h1>⚡ Trading Bot</h1>
  <span class="pill" id="pill-bot"><span class="dot" id="dot-bot"></span><b>bot</b> <span id="bot-state">…</span></span>
  <span class="pill" id="pill-ct"><span class="dot" id="dot-ct"></span>cTrader <span id="ct-state">…</span></span>
  <span class="pill" id="pill-pm">Polymarket <span id="pm-state">…</span></span>
  <span style="flex:1"></span>
  <button class="btn" id="btn-start">Start bot</button>
  <button class="btn danger" id="btn-stop">Stop</button>
</header>

<div class="section">
  <div class="stats" id="stats-strip"></div>
</div>

<div class="grid g3 section">
  <div class="card">
    <h2>Paper lab (live bars, real signals)</h2>
    <div id="paper">Loading…</div>
  </div>
  <div class="card">
    <h2>cTrader / QCG</h2>
    <div id="ctrader">Loading…</div>
  </div>
  <div class="card">
    <h2>Polymarket — last scan</h2>
    <div id="polymarket">Loading…</div>
  </div>
</div>

<div class="grid g2 section">
  <div class="card">
    <h2>Watchlist</h2>
    <div id="watch"><table><thead><tr><th>Symbol</th><th>Price</th><th>24h</th></tr></thead><tbody></tbody></table></div>
  </div>
  <div class="card">
    <h2>Movers</h2>
    <div id="movers"><table><thead><tr><th>Symbol</th><th>Price</th><th>24h</th><th></th></tr></thead><tbody></tbody></table></div>
  </div>
</div>

<div class="card section">
  <h2>Recent trades <span class="muted" id="trades-meta"></span></h2>
  <table>
    <thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>Entry</th><th>Exit</th><th>PnL</th><th>State</th><th>Source</th></tr></thead>
    <tbody id="trades"></tbody>
  </table>
</div>

<footer>
  <span id="updated">—</span>
  <span>auto-refresh 15s · sources: trades.db · trades_legacy.db · data/*.json · Binance</span>
</footer>

<script>
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function money(v,d){if(v==null||isNaN(v))return '—';v=Number(v);return '$'+v.toLocaleString(undefined,{minimumFractionDigits:d==null?2:d,maximumFractionDigits:d==null?2:d})}
function num(v,d){if(v==null||isNaN(v))return '—';return Number(v).toLocaleString(undefined,{maximumFractionDigits:d==null?2:d})}
function cls(v){return v>0?'pos':(v<0?'neg':'')}
function pct(v){if(v==null||isNaN(v))return '—';return (v>0?'+':'')+v.toFixed(2)+'%'}
function ago(ts){if(!ts)return '—';if(ts>1e12)ts=ts/1000;var s=Math.floor(Date.now()/1000-ts);if(s<0)return 'soon';if(s<90)return s+'s ago';if(s<5400)return Math.floor(s/60)+'m ago';if(s<129600)return Math.floor(s/3600)+'h ago';return Math.floor(s/86400)+'d ago'}

async function load(){
  let d;
  try{ d = await (await fetch('/api/overview')).json(); }catch(e){ document.getElementById('updated').textContent='offline: '+e.message; return }
  render(d);
}

function render(d){
  // bot pill
  var b=d.bot||{};
  document.getElementById('dot-bot').className='dot '+(b.running?'on':'off');
  document.getElementById('bot-state').textContent=b.running?'running':'stopped';
  // cTrader pill
  var ct=d.ctrader||{};
  document.getElementById('dot-ct').className='dot '+(ct.parked?'warn':(ct.configured?'on':'off'));
  document.getElementById('ct-state').textContent=ct.parked?'parked':(ct.configured?'linked':'no creds');
  // pm pill
  var pm=d.polymarket||{};
  document.getElementById('pm-state').textContent=pm.count!=null?('last scan '+ago(pm.ts)):'no scan yet';

  // stats strip
  var s=d.trade_stats||{}, paper=d.paper||{}, paperPnl=0, paperEq=0, paperInit=0;
  (paper.slots||[]).forEach(function(x){paperPnl+=x.pnl;paperEq+=x.equity;paperInit+=x.initial});
  document.getElementById('stats-strip').innerHTML=[
    ['Trades',String(s.trades||0)],
    ['Win rate',s.win_rate!=null?s.win_rate+'%':'—'],
    ['Bot PnL',money(s.pnl)],
    ['Paper equity',money(paperEq,0)],
    ['Paper PnL',(paperPnl>0?'+':'')+money(paperPnl).slice(1)],
    ['Paper return',paperInit?pct(100*(paperEq-paperInit)/paperInit):'—'],
  ].map(function(x){return '<div class="stat"><div class="v">'+x[1]+'</div><div class="l">'+x[0]+'</div></div>'}).join('');

  // paper slots
  var pp='';
  (paper.slots||[]).forEach(function(x){
    pp+='<div class="row"><span class="k">'+esc(x.name)+' <span class="tag">'+(x.open_position?(esc(x.side)+' '+esc(x.position_symbol)):'flat')+'</span></span>'
      +'<span><b>'+money(x.equity)+'</b> <span class="'+cls(x.pnl)+'">'+(x.pnl>=0?'+':'')+num(x.pnl)+' ('+pct(x.pnl_pct)+')</span></span></div>'
      +'<div class="row"><span class="muted">trades '+x.trades+' · fees '+money(x.fees)+' · runs '+x.runs+' · last bar '+ago(x.last_bar_ts)+'</span></div>';
  });
  document.getElementById('paper').innerHTML=pp||'<span class="muted">no paper state yet — run: python3 trading_bot.py --paper-run</span>';

  // ctrader
  var c='';
  if(ct.configured){
    c+='<div class="row"><span class="k">Live account</span><span><b>'+esc(ct.live_account||'—')+'</b> '+(ct.parked?'<span class="tag amb">PARKED</span>':'<span class="tag">active</span>')+'</span></div>';
    c+='<div class="row"><span class="k">Demo account</span><span><b>'+esc(ct.demo_account||'—')+'</b></span></div>';
    c+='<div class="row"><span class="k">Token</span><span>'+ (ct.token_days_left!=null?ct.token_days_left+' days left':'—') +'</span></div>';
    if(ct.parked) c+='<div class="muted" style="margin-top:8px">🔒 Live order placement is refused until <code>--ctrader-unpark</code>. Parked '+ago(ct.parked_at)+'</div>';
  } else c='<span class="muted">no cTrader credentials (data/ctrader_credentials.json)</span>';
  document.getElementById('ctrader').innerHTML=c;

  // polymarket
  var m='';
  if(pm.top&&pm.top.length){
    m+='<div class="muted" style="margin-bottom:8px">scan '+ago(pm.ts)+' · '+(pm.scan_secs||'—')+'s · bankroll $'+(pm.bankroll||'—')+' · '+pm.count+' opps</div>';
    pm.top.forEach(function(o){
      m+='<div class="row"><span class="k">'+esc(o.type||'')+'</span><span class="'+cls(o.expected||0)+'">'+esc(o.market||'')+' → '+(o.expected>0?'+':'')+num(o.expected)+'</span></div>';
    });
  } else m='<span class="muted">no scan cached yet — run: python3 trading_bot.py --polymarket-scan</span>';
  document.getElementById('polymarket').innerHTML=m;

  // prices
  var p=d.prices||{};
  var wt='';
  (p.watch||[]).forEach(function(x){
    wt+='<tr><td><b>'+esc(x.symbol)+'</b></td><td>'+money(x.price, x.price<1?4:2)+'</td><td class="'+cls(x.change)+'">'+pct(x.change)+'</td></tr>';
  });
  document.querySelector('#watch tbody').innerHTML=wt||'<tr><td colspan="3" class="muted">prices unavailable: '+esc(p.error||'')+'</td></tr>';
  var mv='';
  (p.gainers||[]).forEach(function(x){mv+='<tr><td>'+esc(x.symbol)+'</td><td>'+money(x.price, x.price<1?4:2)+'</td><td class="pos">'+pct(x.change)+'</td><td class="tag">gain</td></tr>'});
  (p.losers||[]).forEach(function(x){mv+='<tr><td>'+esc(x.symbol)+'</td><td>'+money(x.price, x.price<1?4:2)+'</td><td class="neg">'+pct(x.change)+'</td><td class="tag">loss</td></tr>'});
  document.querySelector('#movers tbody').innerHTML=mv||'<tr><td colspan="4" class="muted">no data</td></tr>';

  // trades
  var tt='';
  (d.trades||[]).forEach(function(t){
    tt+='<tr><td class="muted">'+esc((t.time||'').slice(0,16))+'</td><td><b>'+esc(t.symbol)+'</b></td><td>'+esc(t.side||'—')+'</td><td>'+num(t.entry,4)+'</td><td>'+num(t.exit,4)+'</td><td class="'+cls(t.pnl)+'">'+(t.pnl!=null?((t.pnl>0?'+':'')+num(t.pnl)):'—')+'</td><td><span class="tag">'+esc(t.state)+'</span></td><td class="muted">'+esc(t.source)+'</td></tr>';
  });
  document.getElementById('trades').innerHTML=tt||'<tr><td colspan="8" class="muted">no trades recorded yet</td></tr>';
  document.getElementById('trades-meta').textContent='';
  document.getElementById('updated').textContent='updated '+new Date().toLocaleTimeString();
}

document.getElementById('btn-start').onclick=function(){fetch('/api/bot/start',{method:'POST'}).then(load)};
document.getElementById('btn-stop').onclick=function(){if(confirm('Stop the bot process?'))fetch('/api/bot/stop',{method:'POST'}).then(load)};
load();
setInterval(load,15000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    from flask import Response
    return Response(PAGE, mimetype="text/html")


if __name__ == "__main__":
    if not FLASK_AVAILABLE:
        print("❌ Dashboard unavailable: flask is not installed (pip install flask)")
        sys.exit(1)
    run_dashboard(port=int(os.environ.get("PORT", "7777")))
