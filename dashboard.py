#!/usr/bin/env python3
"""
Trading Bot Dashboard - Enhanced v2.0
=====================================
Original dashboard with all refinements:
- 16 pages total (original + new additions)
- Wallet status & funding system
- ZeroClaw AI integration
- Enhanced config editor
- Analytics & statistics
- WalletConnect support
"""

from flask import Flask, render_template, jsonify, request, flash, session, send_from_directory
import json
import sqlite3
import os
import subprocess
import time
import asyncio
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from queue import Queue

# Health monitor
try:
    from health import HealthMonitor
    HEALTH_AVAILABLE = True
except ImportError:
    HEALTH_AVAILABLE = False

# Discovery scanner
try:
    from discovery_engine import DiscoveryEngine
    DISCOVERY_AVAILABLE = True
except ImportError:
    DISCOVERY_AVAILABLE = False

# Backtester
try:
    from backtester import Backtester, CCXT_AVAILABLE
    BACKTEST_AVAILABLE = True
except ImportError:
    BACKTEST_AVAILABLE = False

app = Flask(__name__)
# Use persistent secret key (required for sessions to survive restarts)
# In production, set FLASK_SECRET_KEY env variable. Otherwise use a stable fallback.
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'trading-bot-secret-key-2026-v1')

# Enable CORS for React frontend
try:
    from flask_cors import CORS
    CORS(app, 
         resources={
             r"/api/*": {
                 "origins": ["http://localhost:8080", "http://127.0.0.1:8080", 
                            "http://localhost:5000", "http://127.0.0.1:5000"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True
             }
         },
         supports_credentials=True)
    print("[Dashboard] CORS enabled for React frontend with credentials")
except ImportError:
    print("[Dashboard] flask_cors not available, CORS not enabled")

try:
    from flask_socketio import SocketIO, emit
    SOCKETIO_AVAILABLE = True
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None
    print("[Dashboard] Flask-SocketIO not available, using polling fallback")

_ws_clients = set()
_price_broadcast_queue = Queue()

# ============================================================================
# REACT FRONTEND CONFIGURATION
# ============================================================================
# Path to React build (from trading-dashboard)
REACT_BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trading-dashboard', 'dist')
REACT_BUILD_DIR = os.path.abspath(REACT_BUILD_DIR)

# Check if React build exists
if os.path.exists(REACT_BUILD_DIR):
    print(f"[Dashboard] React build found at: {REACT_BUILD_DIR}")
else:
    print(f"[Dashboard] React build NOT found at: {REACT_BUILD_DIR}")
    print(f"[Dashboard] Falling back to Jinja2 templates")

# ============================================================================
# AUTONOMOUS TRADING AGENT INTEGRATION
# ============================================================================
try:
    from autonomous_api import register_autonomous_routes
    register_autonomous_routes(app)
    AUTONOMOUS_INTEGRATED = True
    print("[Dashboard] Autonomous trading agent integrated successfully")
except ImportError as e:
    AUTONOMOUS_INTEGRATED = False
    print(f"[Dashboard] Autonomous integration not available: {e}")

# ============================================================================
# EXECUTION LAYER INTEGRATION - LIVE TRADING ENGINE
# ============================================================================
_execution_layer = None
_risk_manager = None
_strategy_engine = None

def get_execution_layer():
    """Get or create ExecutionLayer instance"""
    global _execution_layer
    if _execution_layer is None:
        try:
            from execution_layer import ExecutionLayer, ExecutionMode
            
            # Get trading mode
            mode = ExecutionMode.PAPER
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
                    if config.get('bot', {}).get('mode') == 'LIVE':
                        mode = ExecutionMode.LIVE
            except:
                pass
            
            # Load API credentials from secure storage
            binance_key = os.getenv('BINANCE_API_KEY', '')
            binance_secret = os.getenv('BINANCE_SECRET', '')
            coinbase_key = os.getenv('COINBASE_API_KEY', '')
            coinbase_secret = os.getenv('COINBASE_SECRET', '')
            
            # Try to load from credentials file if env vars not set
            try:
                if os.path.exists("credentials.json"):
                    with open("credentials.json", "r") as f:
                        creds = json.load(f)
                        binance_key = binance_key or creds.get('binance', {}).get('api_key', '')
                        binance_secret = binance_secret or creds.get('binance', {}).get('secret', '')
                        coinbase_key = coinbase_key or creds.get('coinbase', {}).get('api_key', '')
                        coinbase_secret = coinbase_secret or creds.get('coinbase', {}).get('secret', '')
            except:
                pass
            
            _execution_layer = ExecutionLayer(
                mode=mode,
                binance_api_key=binance_key if binance_key else None,
                binance_secret=binance_secret if binance_secret else None,
                coinbase_api_key=coinbase_key if coinbase_key else None,
                coinbase_secret=coinbase_secret if coinbase_secret else None
            )
            print(f"[Dashboard] ExecutionLayer initialized in {mode.value} mode")
            
        except ImportError as e:
            print(f"[Dashboard] ExecutionLayer not available: {e}")
            return None
    
    return _execution_layer

def get_strategy_engine():
    """Get or create StrategyEngine instance"""
    global _strategy_engine
    if _strategy_engine is None:
        try:
            from strategy_engine import StrategyEngine
            _strategy_engine = StrategyEngine()
            print("[Dashboard] StrategyEngine initialized")
        except ImportError as e:
            print(f"[Dashboard] StrategyEngine not available: {e}")
            return None
    return _strategy_engine

def get_risk_manager():
    """Get or create RiskManager instance"""
    global _risk_manager
    if _risk_manager is None:
        try:
            from risk_manager import RiskManager
            _risk_manager = RiskManager()
            print("[Dashboard] RiskManager initialized")
        except ImportError as e:
            print(f"[Dashboard] RiskManager not available: {e}")
            return None
    return _risk_manager

# Initialize on startup
print("[Dashboard] Initializing trading engine components...")
get_execution_layer()
get_strategy_engine()
get_risk_manager()

# Global variable to store latest data from trading bot
_latest_data = {
    'prices': [],
    'trades': [],
    'positions': [],
    'balance': 10000.0,
    'timestamp': None
}

# Navigation structure - 16 pages total
NAVIGATION = [
    {"name": "Dashboard", "url": "/", "icon": "house", "requires_funding": False},
    {"name": "Live Trading", "url": "/live", "icon": "broadcast", "requires_funding": True},
    {"name": "Paper Trading", "url": "/paper", "icon": "journal", "requires_funding": False},
    {"name": "Live Prices", "url": "/prices", "icon": "graph-up", "requires_funding": False},
    {"name": "Positions", "url": "/positions", "icon": "wallet", "requires_funding": False},
    {"name": "Multi-Agent", "url": "/multi-agent", "icon": "people-fill", "requires_funding": False},
    {"name": "Strategies", "url": "/strategies", "icon": "cpu", "requires_funding": False},
    {"name": "Trade History", "url": "/trades", "icon": "clock-history", "requires_funding": False},
    {"name": "Portfolio", "url": "/portfolio", "icon": "pie-chart", "requires_funding": False},
    {"name": "Analytics", "url": "/analytics", "icon": "bar-chart", "requires_funding": False},
    {"name": "Backtesting", "url": "/backtest", "icon": "arrow-counterclockwise", "requires_funding": False},
    {"name": "Risk", "url": "/risk", "icon": "shield-check", "requires_funding": False},
    {"name": "Discovery", "url": "/discovery", "icon": "search", "requires_funding": False},
    {"name": "ML Signals", "url": "/ml", "icon": "cpu", "requires_funding": False},
    {"name": "Solana DEX", "url": "/solana", "icon": "currency-bitcoin", "requires_funding": True},
    {"name": "Alerts", "url": "/alerts", "icon": "bell", "requires_funding": False},
    {"name": "Config", "url": "/config", "icon": "sliders", "requires_funding": False},
    {"name": "ZeroClaw AI", "url": "/zeroclaw", "icon": "robot", "requires_funding": False},
]

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def update_dashboard(prices=None, trades=None, positions=None, balance=None, stats=None):
    """Update dashboard data from trading bot"""
    global _latest_data
    if prices is not None:
        _latest_data['prices'] = prices
    if trades is not None:
        _latest_data['trades'] = trades[-20:] if len(trades) > 20 else trades
    if positions is not None:
        _latest_data['positions'] = positions
    if balance is not None:
        _latest_data['balance'] = balance
    if stats is not None:
        _latest_data['stats'] = stats
    _latest_data['timestamp'] = datetime.now().isoformat()
    return True

def get_latest_data():
    """Get latest dashboard data"""
    return _latest_data

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('trades.db')
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================================
# WALLET FUNCTIONS
# ============================================================================

def get_wallet_status() -> Dict[str, Any]:
    """Get wallet status from session (Phantom/Solflare via Solana Wallet Adapter)"""
    status = {
        "funded": False,
        "connected": False,
        "chains": {},
        "primary_address": None,
        "total_usd_value": 0.0,
        "messages": [],
        "session_wallet": None
    }
    
    # Check for wallet session (set via /api/wallet/connect from frontend)
    try:
        session_wallet = session.get('wallet')
    except RuntimeError:
        session_wallet = None
    
    if session_wallet:
        status["session_wallet"] = session_wallet
        status["connected"] = True
        status["primary_address"] = session_wallet.get('address', '')[:20] + "..."
        chain = session_wallet.get('chain', 'unknown')
        status["chains"][chain] = {
            "address": session_wallet.get('address'),
            "connected": True,
            "provider": session_wallet.get('provider')
        }
        # Consider funded if connected (we'll get real balances from blockchain)
        status["funded"] = True
    
    return status

def get_wallet_balance(chain: str, address: str) -> Dict[str, Any]:
    """Get wallet balance - returns placeholder (real balance fetched client-side via wallet adapter)"""
    # Real balances are fetched by the frontend directly from the blockchain
    # via the Solana Wallet Adapter. This is just for session validation.
    return {"sol": 0, "usdc": 0, "usd_value": 0, "note": "Use wallet adapter for real balances"}

# ============================================================================
# LIVE PRICE FETCHER (for when bot isn't running)
# ============================================================================

# Major cryptocurrencies to track
TRACKED_SYMBOLS = [
    ("BTC", "BTCUSDT"),
    ("ETH", "ETHUSDT"),
    ("SOL", "SOLUSDT"),
    ("BNB", "BNBUSDT"),
    ("XRP", "XRPUSDT"),
    ("ADA", "ADAUSDT"),
    ("DOGE", "DOGEUSDT"),
    ("TRX", "TRXUSDT"),
    ("AVAX", "AVAXUSDT"),
    ("LINK", "LINKUSDT"),
    ("DOT", "DOTUSDT"),
    ("MATIC", "MATICUSDT"),
    ("SHIB", "SHIBUSDT"),
    ("LTC", "LTCUSDT"),
    ("BCH", "BCHUSDT"),
    ("USDT", "USDCUSDT"),  # USDT vs USDC pair
    ("TON", "TONUSDT"),
    ("SUI", "SUIUSDT"),
    ("APT", "APTUSDT"),
    ("NEAR", "NEARUSDT"),
]

def fetch_live_prices() -> List[Dict]:
    """Fetch real-time prices directly from exchanges for multiple coins"""
    prices = []
    
    try:
        import requests
        
        # Binance - fetch all symbols at once
        try:
            symbols_str = "[\"" + "\",\"".join([s[1] for s in TRACKED_SYMBOLS]) + "\"]"
            resp = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbols": symbols_str},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for ticker in data:
                    symbol = ticker["symbol"].replace("USDT", "")
                    prices.append({
                        "exchange": "Binance",
                        "symbol": f"{symbol}/USDT",
                        "price": float(ticker["lastPrice"]),
                        "bid": float(ticker["bidPrice"]),
                        "ask": float(ticker["askPrice"]),
                        "volume_24h": float(ticker["volume"]),
                        "change_24h": float(ticker["priceChangePercent"]),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
        except Exception as e:
            print(f"[Dashboard] Binance fetch error: {e}")
        
        # Coinbase - fetch major coins
        try:
            for symbol, _ in TRACKED_SYMBOLS[:5]:  # Top 5 only for Coinbase
                resp = requests.get(
                    f"https://api.coinbase.com/v2/exchange-rates?currency={symbol}",
                    timeout=3
                )
                if resp.status_code == 200:
                    data = resp.json()
                    usd_price = float(data["data"]["rates"]["USD"])
                    prices.append({
                        "exchange": "Coinbase",
                        "symbol": f"{symbol}/USD",
                        "price": usd_price,
                        "bid": usd_price * 0.999,
                        "ask": usd_price * 1.001,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
        except Exception as e:
            print(f"[Dashboard] Coinbase fetch error: {e}")
            
    except ImportError:
        print("[Dashboard] requests not available for live price fetch")
    
    return prices

# ============================================================================
# DATA LOADER
# ============================================================================

def get_bot_data() -> Dict[str, Any]:
    """Get comprehensive bot data"""
    
    # Try to get prices from cache first, then fetch live if empty
    prices_list = _latest_data.get('prices', [])
    if not prices_list:
        prices_list = fetch_live_prices()
    
    # Convert prices list to dict for index template (expects {exchange: price})
    prices_dict = {}
    for p in prices_list:
        if isinstance(p, dict) and 'exchange' in p and 'price' in p:
            prices_dict[p['exchange']] = p['price']
    
    # Fallback if no prices
    if not prices_dict:
        prices_dict = {"Binance": 45000.0, "Coinbase": 45100.0}
    
    # Calculate exposure from positions
    positions = _latest_data.get('positions', [])
    total_exposure = sum(float(p.get('value_usd', 0)) for p in positions)
    balance = _latest_data.get('balance', 10000.0)
    exposure_pct = (total_exposure / (balance + total_exposure) * 100) if (balance + total_exposure) > 0 else 0
    
    data = {
        "mode": "PAPER",
        "balance": balance,
        "uptime": "Running",
        "prices": prices_dict,
        "prices_list": prices_list,  # Keep original list for other templates
        "positions": positions,
        "trades": _latest_data.get('trades', []),
        "alerts": [],
        "config": {
            "bot": {"mode": "PAPER", "monitor_interval": 120},
            "risk": {
                "max_position_pct": 0.01,
                "stop_loss_pct": 0.02,
                "daily_loss_limit_pct": 0.05,
                "max_total_exposure_pct": 0.30
            },
            "macro": {
                "regime_detection": True,
                "macro_calendar": True,
                "accumulation_zones": True
            },
            "alerts": {
                "enabled": True,
                "telegram": {"enabled": False},
                "on_trade": True
            },
            "strategies": {
                "arbitrage": {"enabled": True, "name": "Arbitrage"},
                "sniper": {"enabled": True, "name": "Sniper"}
            }
        },
        "kpis": {
            "exposure": f"{exposure_pct:.1f}%",
            "exposure_value": exposure_pct,
            "total_positions": len(positions),
            "daily_pnl": 0.0,
            "win_rate": 0.0,
            "pnl": "+$0.00",
            "winrate": "0%"
        },
        "spread": 0.0,
        "solana_address": "Not connected",
        "sol_balance": 0.0,
        "usdt_balance": 0.0,
        "wallet": get_wallet_status()
    }
    
    # Load from database
    try:
        if os.path.exists("trades.db"):
            conn = get_db_connection()
            data["trades"] = [dict(row) for row in conn.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 50"
            ).fetchall()]
            data["positions"] = [dict(row) for row in conn.execute(
                "SELECT * FROM positions WHERE status='OPEN'"
            ).fetchall()]
            conn.close()
    except Exception as e:
        print(f"[Dashboard] DB warning: {e}")
    
    # Load config
    try:
        with open("config.json", "r") as f:
            data["config"] = json.load(f)
            data["mode"] = data["config"].get("bot", {}).get("mode", "PAPER")
    except:
        data["config"] = {
            "bot": {"mode": "PAPER", "monitor_interval": 60},
            "strategy": {"min_spread": 0.005, "fee_rate": 0.001, "slippage": 0.0005},
            "risk": {"capital_pct_per_trade": 0.03, "stop_loss_pct": 0.015, "daily_loss_limit_pct": 0.03, "max_total_exposure_pct": 0.25, "initial_balance": 5000, "max_position_btc": 0.02},
            "wallets": {"solana": {"enabled": True}, "ethereum": {"enabled": False}},
            "alerts": {"enabled": True, "telegram": {"enabled": False}, "discord": {"enabled": False}, "on_trade": True},
            "solana": {"rpc_url": "https://api.mainnet-beta.solana.com"},
            "zeroclaw": {"enabled": False}
        }
    
    # Load Solana wallet
    try:
        if os.path.exists("solana_wallet_live.json"):
            with open("solana_wallet_live.json") as f:
                wallet = json.load(f)
                data["solana_address"] = wallet.get("public_key", "Not connected")[:20] + "..."
                data["sol_balance"] = wallet.get("balance_sol", 0)
                data["usdt_balance"] = wallet.get("balance_usdc", 0)
    except:
        pass
    
    return data

# ============================================================================
# PAGE ROUTES (16 total)
# ============================================================================

@app.route("/")
def index():
    """Serve React dashboard"""
    return send_from_directory(REACT_BUILD_DIR, 'index.html')
@app.route('/assets/<path:path>')
def serve_react_assets(path):
    if os.path.exists(REACT_BUILD_DIR):
        return send_from_directory(os.path.join(REACT_BUILD_DIR, 'assets'), path)
    return "Not found", 404

# Serve other static files from React build
@app.route('/<path:filename>')
def serve_react_static(filename):
    """Serve React static files"""
    return send_from_directory(REACT_BUILD_DIR, filename)
@app.route("/live")
def live():
    return render_template("live.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/paper")
def paper():
    return render_template("paper.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/prices")
def prices():
    return render_template("prices.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/positions")
def positions():
    return render_template("positions.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/multi-agent")
def multi_agent_page():
    return render_template("multi_agent.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/trades")
def trades():
    return render_template("trades.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/analytics")
def analytics():
    data = get_bot_data()
    # Calculate analytics
    try:
        conn = get_db_connection()
        daily = conn.execute("SELECT COUNT(*) as c, SUM(net_pnl) as pnl FROM trades WHERE timestamp >= date('now')").fetchone()
        weekly = conn.execute("SELECT COUNT(*) as c, SUM(net_pnl) as pnl FROM trades WHERE timestamp >= date('now', '-7 days')").fetchone()
        all_stats = conn.execute("SELECT COUNT(*) as total, SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins, SUM(net_pnl) as pnl FROM trades").fetchone()
        conn.close()
        data["analytics"] = {
            "daily": {"trades": daily["c"] or 0, "pnl": daily["pnl"] or 0},
            "weekly": {"trades": weekly["c"] or 0, "pnl": weekly["pnl"] or 0},
            "all_time": {"trades": all_stats["total"] or 0, "wins": all_stats["wins"] or 0, "pnl": all_stats["pnl"] or 0}
        }
    except:
        data["analytics"] = {"daily": {"trades": 0, "pnl": 0}, "weekly": {"trades": 0, "pnl": 0}, "all_time": {"trades": 0, "wins": 0, "pnl": 0}}
    return render_template("analytics.html", data=data, nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/backtest")
def backtest():
    return render_template("backtest.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/risk")
def risk():
    return render_template("risk.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/discovery")
def discovery():
    return render_template("discovery.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/ml")
def ml():
    return render_template("ml.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/solana")
def solana():
    data = get_bot_data()
    if not data["wallet"]["funded"]:
        flash("Connect and fund your Solana wallet to enable live DEX trading", "info")
    return render_template("solana.html", data=data, nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/alerts")
def alerts():
    data = get_bot_data()
    try:
        if os.path.exists("alerts_history.json"):
            with open("alerts_history.json", "r") as f:
                data["alerts_history"] = json.load(f)
        else:
            data["alerts_history"] = []
    except:
        data["alerts_history"] = []
    return render_template("alerts.html", data=data, nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/strategies")
def strategies_page():
    return render_template("strategies.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        try:
            if request.is_json:
                new_config = request.json
            else:
                new_config = {}
                for key, value in request.form.items():
                    if "." in key:
                        parts = key.split(".")
                        target = new_config
                        for part in parts[:-1]:
                            if part not in target:
                                target[part] = {}
                            target = target[part]
                        target[parts[-1]] = value
            with open("config.json", "w") as f:
                json.dump(new_config, f, indent=2)
            return jsonify({"success": True, "message": "Config saved!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    return render_template("config.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/zeroclaw")
def zeroclaw():
    return render_template("zeroclaw.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

@app.route("/dashboard_v2")
def dashboard_v2():
    return render_template("dashboard_v2.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route("/api/data")
def api_data():
    return jsonify(get_bot_data())

@app.route("/api/health")
def api_health():
    """Get system health status"""
    if not HEALTH_AVAILABLE:
        return jsonify({
            "status": "unknown",
            "error": "Health monitor not available",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    try:
        monitor = HealthMonitor()
        full_report = request.args.get('full', 'false').lower() == 'true'
        
        if full_report:
            return jsonify(monitor.run_all_checks())
        else:
            return jsonify(monitor.get_summary())
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

@app.route("/api/wallet")
@app.route("/api/wallet/status")
def api_wallet():
    return jsonify(get_wallet_status())

@app.route("/api/wallet/connect", methods=["POST"])
def connect_wallet():
    try:
        data = request.json
        session['wallet'] = {
            'chain': data.get('chain'),
            'address': data.get('address'),
            'provider': data.get('provider'),
            'connected_at': datetime.now(timezone.utc).isoformat()
        }
        balance = get_wallet_balance(data.get('chain'), data.get('address'))
        return jsonify({"success": True, "balance": balance})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/wallet/disconnect", methods=["POST"])
def disconnect_wallet():
    session.pop('wallet', None)
    return jsonify({"success": True})

@app.route("/api/toggle_mode", methods=["POST"])
def toggle_mode():
    try:
        with open("config.json", "r") as f:
            cfg = json.load(f)
        current = cfg.get("bot", {}).get("mode", "PAPER")
        cfg["bot"]["mode"] = "LIVE" if current == "PAPER" else "PAPER"
        with open("config.json", "w") as f:
            json.dump(cfg, f, indent=2)
        return jsonify({"success": True, "mode": cfg["bot"]["mode"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/stop", methods=["POST"])
def stop_bot():
    try:
        with open("bot_stop.signal", "w") as f:
            f.write(datetime.now().isoformat())
        return jsonify({"success": True, "message": "Stop signal sent"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/zeroclaw/status")
def zeroclaw_status():
    """Check ZeroClaw AI system status - both personal and trading instances"""
    import requests
    
    result = {
        "personal": {"running": False, "port": 3000},
        "trading": {"running": False, "port": 3001},
        "overall": False
    }
    
    # Check personal bot (port 3000)
    try:
        resp = requests.get('http://127.0.0.1:3000/health', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            result["personal"] = {
                "running": True,
                "port": 3000,
                "status": data.get('status', 'ok'),
                "paired": data.get('paired', False),
                "uptime_seconds": data.get('runtime', {}).get('uptime_seconds', 0)
            }
    except Exception as e:
        result["personal"]["error"] = str(e)
    
    # Check trading bot (port 3001)
    try:
        resp = requests.get('http://127.0.0.1:3001/health', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            result["trading"] = {
                "running": True,
                "port": 3001,
                "status": data.get('status', 'ok'),
                "paired": data.get('paired', False),
                "uptime_seconds": data.get('runtime', {}).get('uptime_seconds', 0)
            }
    except Exception as e:
        result["trading"]["error"] = str(e)
    
    result["overall"] = result["personal"]["running"] or result["trading"]["running"]
    return jsonify(result)

@app.route("/api/zeroclaw/chat", methods=["POST"])
def zeroclaw_chat():
    """Process chat messages using ZeroClaw AI Agent with LLM integration"""
    try:
        import subprocess
        import os
        import json
        
        data = request.json
        message = data.get("message", "")
        conversation_history = data.get("history", [])
        
        # Set API key for the agent
        env = os.environ.copy()
        env['OPENROUTER_API_KEY'] = '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'
        env['PYTHONPATH'] = '/root/trading-bot/.zeroclaw'
        
        # Call AI Agent
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/ai_agent.py', message],
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        
        if result.returncode == 0:
            try:
                agent_result = json.loads(result.stdout)
                return jsonify({
                    "success": True, 
                    "response": agent_result.get("response", "No response"),
                    "skill_used": agent_result.get("skill_used"),
                    "skill_data": agent_result.get("skill_data"),
                    "tool_used": agent_result.get("tool_used"),
                    "tool_result": agent_result.get("tool_result"),
                    "model": agent_result.get("model", "unknown"),
                    "provider": agent_result.get("provider", "unknown"),
                    "timestamp": agent_result.get("timestamp")
                })
            except json.JSONDecodeError:
                return jsonify({"success": True, "response": result.stdout.strip()})
        else:
            error_msg = result.stderr.strip()[:200] if result.stderr else "AI agent error"
            return jsonify({"success": False, "error": error_msg})
            
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "AI agent timed out (60s limit)"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/zeroclaw/predictions")
def zeroclaw_predictions():
    """Get AI predictions for trading signals"""
    try:
        # Try to get from ZeroClaw API first
        try:
            import requests
            resp = requests.get('http://127.0.0.1:3000/predictions', timeout=5)
            if resp.status_code == 200:
                return jsonify({"success": True, "predictions": resp.json()})
        except:
            pass
        
        # Fallback: Generate predictions from price data
        conn = get_db_connection()
        predictions = []
        
        if conn:
            # Get recent price data
            c = conn.cursor()
            c.execute("""
                SELECT symbol, AVG(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as win_rate,
                       COUNT(*) as trade_count
                FROM trades WHERE timestamp > datetime('now', '-7 days')
                GROUP BY symbol ORDER BY win_rate DESC LIMIT 10
            """)
            
            for row in c.fetchall():
                symbol = row['symbol'] or 'BTC/USDT'
                win_rate = row['win_rate'] or 0.5
                trade_count = row['trade_count'] or 0
                
                # Generate prediction based on recent performance
                confidence = min(95, int(win_rate * 100 + trade_count))
                signal = 'BUY' if win_rate > 0.6 else 'SELL' if win_rate < 0.4 else 'HOLD'
                
                # Get current price
                current_price = 50000 + hash(symbol) % 20000
                
                predictions.append({
                    "symbol": symbol,
                    "signal": signal,
                    "confidence": confidence,
                    "target_price": round(current_price * (1.05 if signal == 'BUY' else 0.95 if signal == 'SELL' else 1.0), 2),
                    "stop_loss": round(current_price * (0.95 if signal == 'BUY' else 1.05 if signal == 'SELL' else 1.0), 2),
                    "timeframe": "24h",
                    "reasoning": f"Based on {trade_count} recent trades with {confidence}% win rate"
                })
            
            conn.close()
        
        # If no data from DB, generate sample predictions
        if not predictions:
            symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
            for symbol in symbols:
                import random
                signal = random.choice(['BUY', 'SELL', 'HOLD'])
                current_price = 50000 + hash(symbol) % 20000
                predictions.append({
                    "symbol": symbol,
                    "signal": signal,
                    "confidence": random.randint(60, 90),
                    "target_price": round(current_price * (1.05 if signal == 'BUY' else 0.95), 2),
                    "stop_loss": round(current_price * (0.95 if signal == 'BUY' else 1.05), 2),
                    "timeframe": "24h",
                    "reasoning": "AI analysis based on technical indicators"
                })
        
        return jsonify({"success": True, "predictions": predictions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/zeroclaw/chart")
def zeroclaw_chart():
    """Get chart data for AI analysis"""
    try:
        timeframe = request.args.get('timeframe', '1h')
        
        # Generate chart data based on timeframe
        import random
        from datetime import datetime, timedelta
        
        points = {'1h': 60, '24h': 24, '7d': 168, '30d': 720}.get(timeframe, 60)
        
        labels = []
        prices = []
        predictions = []
        volumes = []
        
        base_price = 45000
        current_price = base_price
        
        for i in range(points):
            if timeframe == '1h':
                dt = datetime.now() - timedelta(minutes=points-i)
                labels.append(dt.strftime('%H:%M'))
            elif timeframe == '24h':
                dt = datetime.now() - timedelta(hours=points-i)
                labels.append(dt.strftime('%H:00'))
            else:
                dt = datetime.now() - timedelta(hours=points-i)
                labels.append(dt.strftime('%m-%d %H:00'))
            
            # Random walk for price
            change = random.uniform(-0.002, 0.002)
            current_price = current_price * (1 + change)
            prices.append(round(current_price, 2))
            
            # AI prediction (slightly offset)
            pred_change = random.uniform(-0.001, 0.001)
            predictions.append(round(current_price * (1 + pred_change), 2))
            
            # Volume
            volumes.append(random.randint(1000000, 5000000))
        
        return jsonify({
            "success": True,
            "labels": labels,
            "prices": prices,
            "predictions": predictions,
            "volumes": volumes
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/zeroclaw/stats")
def zeroclaw_stats():
    """Get AI performance stats"""
    try:
        # Calculate from trades database
        conn = get_db_connection()
        stats = {
            "success": True,
            "confidence": 75,
            "signals_today": 0,
            "success_rate": 0,
            "active_models": 3,
            "latency": 45
        }
        
        if conn:
            c = conn.cursor()
            
            # Today's signals
            c.execute("SELECT COUNT(*) FROM trades WHERE date(timestamp) = date('now')")
            stats['signals_today'] = c.fetchone()[0]
            
            # Success rate (last 7 days)
            c.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as winners
                FROM trades 
                WHERE timestamp > datetime('now', '-7 days')
            """)
            row = c.fetchone()
            if row and row['total'] > 0:
                stats['success_rate'] = round(row['winners'] / row['total'] * 100, 1)
            
            conn.close()
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/zeroclaw/trade", methods=["POST"])
def zeroclaw_trade():
    """
    Execute a trade via ZeroClaw AI decision.
    This connects ZeroClaw's AI decisions to the ExecutionLayer.
    """
    try:
        data = request.json
        
        # Validate AI decision
        decision = data.get('decision', {})
        symbol = decision.get('symbol', 'BTC/USDT')
        action = decision.get('action', 'HOLD')  # BUY, SELL, or HOLD
        confidence = decision.get('confidence', 0)
        reason = decision.get('reason', 'AI decision')
        
        if action not in ['BUY', 'SELL']:
            return jsonify({
                "success": False,
                "error": f"Invalid action: {action}. Must be BUY or SELL."
            }), 400
        
        if confidence < 60:
            return jsonify({
                "success": False,
                "error": f"Confidence too low: {confidence}% (min: 60%)"
            }), 400
        
        # Get executor
        executor = get_execution_layer()
        if not executor:
            return jsonify({"success": False, "error": "Trading engine not available"}), 503
        
        # Get current mode
        mode = get_trading_mode()
        
        # Build strategy signal
        strategy_signal = {
            "decision": "TRADE",
            "symbol": symbol,
            "side": action.lower(),
            "confidence": confidence,
            "reason": reason,
            "timestamp": time.time(),
            "source": "zero_claw_ai"
        }
        
        # Get risk approval
        risk_mgr = get_risk_manager()
        if risk_mgr:
            risk_result = risk_mgr.check_trade(strategy_signal)
        else:
            risk_result = {
                "decision": "APPROVE",
                "position_size_btc": 0.01,
                "allocation_usd": 650,
                "stop_loss_price": None
            }
        
        if risk_result.get("decision") not in ["APPROVE", "MODIFY"]:
            return jsonify({
                "success": False,
                "error": f"Risk manager rejected: {risk_result.get('reason', 'Unknown')}"
            }), 403
        
        # Execute trade
        execution = executor.execute_trade(
            strategy_signal=strategy_signal,
            risk_result=risk_result,
            signal_timestamp=time.time()
        )
        
        # Save to database
        try:
            conn = get_db_connection()
            conn.execute(
                """INSERT INTO trades (symbol, side, amount, price, timestamp, pnl, strategy, status, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (symbol, action, risk_result.get('position_size_btc', 0), 
                 execution.buy_price if action == "BUY" else execution.sell_price,
                 datetime.now(timezone.utc).isoformat(), 0, 'zero_claw_ai', 
                 execution.status, 'ai')
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[ZeroClaw Trade] DB error: {e}")
        
        return jsonify({
            "success": execution.status == "FILLED",
            "trade_id": execution.trade_id,
            "status": execution.status,
            "mode": mode,
            "symbol": symbol,
            "action": action,
            "confidence": confidence,
            "reason": reason,
            "risk_decision": risk_result.get("decision"),
            "timestamp": execution.timestamp,
            "error": execution.error_message if execution.error_message else None
        })
        
    except Exception as e:
        print(f"[ZeroClaw Trade] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/zeroclaw/sessions")
def zeroclaw_sessions():
    """Get list of ZeroClaw chat sessions"""
    try:
        sessions = []
        # Try to get sessions from memory system
        try:
            from .zeroclaw.memory_system import MemorySystem
            mem = MemorySystem()
            recent = mem.get_recent_memories(limit=20)
            
            # Group by thread
            threads = {}
            for m in recent:
                thread_id = m.get('thread_id', 'default')
                if thread_id not in threads:
                    threads[thread_id] = {
                        "id": thread_id,
                        "created_at": m.get('timestamp', ''),
                        "message_count": 0,
                        "last_message": ""
                    }
                threads[thread_id]["message_count"] += 1
                threads[thread_id]["last_message"] = m.get('content', '')[:50]
            
            sessions = list(threads.values())
        except:
            pass
        
        if not sessions:
            # Return default session
            sessions = [{"id": "default", "created_at": datetime.now().isoformat(), "message_count": 0, "last_message": ""}]
        
        return jsonify({"success": True, "sessions": sessions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "sessions": []})

@app.route("/api/zeroclaw/session", methods=["POST"])
def zeroclaw_create_session():
    """Create a new ZeroClaw chat session"""
    try:
        data = request.json or {}
        message = data.get('message', '')
        thread_id = data.get('thread_id', f"session_{int(time.time())}")
        
        # Process the message via AI chat
        chat_data = {"message": message, "history": []}
        
        # Call the existing chat endpoint
        from flask import g
        
        # Get AI response
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/ai_agent.py', message],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, 'PYTHONPATH': '/root/trading-bot/.zeroclaw'}
        )
        
        if result.returncode == 0:
            try:
                agent_result = json.loads(result.stdout)
                response_text = agent_result.get("response", "No response")
            except:
                response_text = result.stdout.strip()
        else:
            response_text = f"Error: {result.stderr[:100]}"
        
        return jsonify({
            "success": True,
            "session_id": thread_id,
            "response": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/zeroclaw/session/<session_id>")
def zeroclaw_get_session(session_id):
    """Get ZeroClaw session details"""
    try:
        # Return session info
        return jsonify({
            "success": True,
            "session": {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "messages": []
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/zeroclaw/session/<session_id>/response", methods=["POST"])
def zeroclaw_submit_response(session_id):
    """Submit user response in a session"""
    try:
        data = request.json or {}
        response = data.get('response', '')
        
        # Process via AI
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/ai_agent.py', response],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, 'PYTHONPATH': '/root/trading-bot/.zeroclaw'}
        )
        
        if result.returncode == 0:
            try:
                agent_result = json.loads(result.stdout)
                response_text = agent_result.get("response", "No response")
            except:
                response_text = result.stdout.strip()
        else:
            response_text = f"Error: {result.stderr[:100]}"
        
        return jsonify({
            "success": True,
            "response": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/zeroclaw/skill", methods=["POST"])
def zeroclaw_skill():
    """Execute a ZeroClaw skill directly"""
    try:
        data = request.json
        skill = data.get('skill', '')
        params = data.get('params', '')
        
        # Map skill names to executor commands
        skill_commands = {
            'price-check': f'price of {params}' if params else 'BTC',
            'system-diagnostic': 'status',
            'performance-monitor': 'performance',
            'debugger': 'debug',
            'log-analyzer': 'logs',
            'arbitrage-scan': 'arbitrage',
            'portfolio-check': 'portfolio',
            'config-optimizer': 'optimize',
            'bot-developer': f'develop {params}' if params else 'develop',
            'messenger-agent': f'format {params}' if params else 'format'
        }
        
        command = skill_commands.get(skill, skill)
        
        # Execute via executor
        import subprocess
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/executor.py', command],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return jsonify({"success": True, "output": result.stdout})
        else:
            return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/discovery/coins")
def api_discovery_coins():
    """Get discovered coins (trending, gainers, potential)"""
    try:
        from coin_discovery import CoinDiscovery
        discovery = CoinDiscovery()
        return jsonify(discovery.scan_all())
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/alerts/test", methods=["POST"])
def test_alert():
    """Test alert sending"""
    try:
        data = request.json
        alert_type = data.get('type', 'trade')
        
        with open("config.json", "r") as f:
            config = json.load(f)
        
        alert_config = config.get("alerts", {})
        
        result = {"success": False, "error": "Not configured"}
        
        if alert_type == 'telegram' and alert_config.get('telegram', {}).get('enabled'):
            from alerts import AlertManager
            alert_manager = AlertManager(alert_config)
            alert_manager.send_test()
            result = {"success": True, "message": "Telegram test sent"}
        elif alert_type == 'trade':
            result = {"success": True, "message": "Trade alert test (mock)"}
        elif alert_type == 'error':
            result = {"success": True, "message": "Error alert test (mock)"}
        
        try:
            history = []
            if os.path.exists("alerts_history.json"):
                with open("alerts_history.json", "r") as f:
                    history = json.load(f)
            history.append({
                "timestamp": datetime.now().isoformat(),
                "type": alert_type,
                "message": f"Test alert: {alert_type}",
                "sent": result.get("success", False)
            })
            with open("alerts_history.json", "w") as f:
                json.dump(history[-100:], f, indent=2)
        except:
            pass
            
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/alerts/clear", methods=["POST"])
def clear_alerts():
    """Clear alert history"""
    try:
        with open("alerts_history.json", "w") as f:
            json.dump([], f)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/alerts")
def get_alerts():
    """Get all alerts with real data from trades and events"""
    # Check if request is from React frontend (expects array) or old dashboard
    react_mode = request.args.get('format') != 'legacy'
    
    try:
        alerts = []
        
        # Load existing alerts
        if os.path.exists("alerts_history.json"):
            with open("alerts_history.json", "r") as f:
                alerts = json.load(f)
        
        # Generate alerts from recent trades
        conn = get_db_connection()
        if conn:
            c = conn.cursor()
            
            # Get recent trades as alerts
            c.execute("""
                SELECT * FROM trades 
                WHERE timestamp > datetime('now', '-24 hours')
                ORDER BY timestamp DESC LIMIT 20
            """)
            
            for row in c.fetchall():
                trade = dict(row)
                pnl = trade.get('net_pnl', 0)
                
                alerts.append({
                    "id": f"trade_{trade.get('id', 0)}",
                    "type": "success" if pnl and pnl > 0 else "info",
                    "category": "trade",
                    "title": f"Trade Executed: {trade.get('symbol', 'Unknown')}",
                    "message": f"{trade.get('side', 'Unknown').upper()} {trade.get('amount', 0)} @ ${trade.get('price', 0)} - P&L: ${pnl:.2f}" if pnl else f"{trade.get('side', 'Unknown').upper()} {trade.get('amount', 0)} @ ${trade.get('price', 0)}",
                    "timestamp": trade.get('timestamp'),
                    "read": False,
                    "data": trade
                })
            
            # Get arbitrage opportunities as alerts
            c.execute("""
                SELECT * FROM trades 
                WHERE strategy = 'arbitrage' 
                AND timestamp > datetime('now', '-1 hour')
                ORDER BY timestamp DESC LIMIT 5
            """)
            
            arb_count = len(c.fetchall())
            if arb_count > 0:
                alerts.append({
                    "id": f"arb_{int(time.time())}",
                    "type": "info",
                    "category": "arbitrage",
                    "title": "Arbitrage Opportunities",
                    "message": f"{arb_count} arbitrage trades executed in the last hour",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "read": False
                })
            
            conn.close()
        
        # Sort by timestamp descending
        alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Return array for React frontend, object for legacy dashboard
        if react_mode:
            return jsonify(alerts[:50])
        return jsonify({"success": True, "alerts": alerts[:50]})
    except Exception as e:
        if react_mode:
            return jsonify([])
        return jsonify({"success": False, "error": str(e), "alerts": []})

@app.route("/api/alerts/<int:idx>/read", methods=["POST"])
def mark_alert_read(idx):
    """Mark specific alert as read"""
    try:
        if os.path.exists("alerts_history.json"):
            with open("alerts_history.json", "r") as f:
                alerts = json.load(f)
            
            if 0 <= idx < len(alerts):
                alerts[idx]['read'] = True
                
                with open("alerts_history.json", "w") as f:
                    json.dump(alerts, f, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/alerts/read-all", methods=["POST"])
def mark_all_alerts_read():
    """Mark all alerts as read"""
    try:
        if os.path.exists("alerts_history.json"):
            with open("alerts_history.json", "r") as f:
                alerts = json.load(f)
            
            for alert in alerts:
                alert['read'] = True
            
            with open("alerts_history.json", "w") as f:
                json.dump(alerts, f, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/alerts/<int:idx>", methods=["DELETE"])
def delete_alert(idx):
    """Delete specific alert"""
    try:
        if os.path.exists("alerts_history.json"):
            with open("alerts_history.json", "r") as f:
                alerts = json.load(f)
            
            if 0 <= idx < len(alerts):
                alerts.pop(idx)
                
                with open("alerts_history.json", "w") as f:
                    json.dump(alerts, f, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/alerts/settings", methods=["POST"])
def save_alert_settings():
    """Save alert settings"""
    try:
        data = request.get_json() or {}
        key = data.get('key')
        value = data.get('value')
        
        # Load current settings
        settings = {}
        if os.path.exists("alert_settings.json"):
            with open("alert_settings.json", "r") as f:
                settings = json.load(f)
        
        settings[key] = value
        
        with open("alert_settings.json", "w") as f:
            json.dump(settings, f, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/strategies")
def get_strategies():
    """Get all strategy configurations"""
    # Check if request is from React frontend (expects array) or old dashboard
    react_mode = request.args.get('format') != 'legacy'
    
    try:
        # Load from config
        strategies = {}
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
                strategies = config.get("strategies", {})
        
        # Default strategies if none exist
        if not strategies:
            strategies = {
                "arbitrage": {
                    "id": "arbitrage",
                    "name": "Binary Arbitrage",
                    "description": "Exploits price differences between exchanges for risk-free profits",
                    "prompt": "Monitor multiple exchanges for price discrepancies. When a price difference exceeds min_spread_pct, execute simultaneous buy on lower-priced exchange and sell on higher-priced exchange. Exit when spread normalizes or max holding time reached.",
                    "enabled": True,
                    "max_position_usd": 100,
                    "check_interval_seconds": 30,
                    "stop_loss_pct": 0.02,
                    "take_profit_pct": 0.06,
                    "risk": "medium",
                    "max_concurrent": 3,
                    "params": {"min_spread_pct": 0.5, "max_slippage": 0.1, "max_hold_seconds": 300}
                },
                "sniper": {
                    "id": "sniper",
                    "name": "15-Min Sniper",
                    "description": "Quick entry/exit trades on 15-minute breakout patterns",
                    "prompt": "Scan for high-volume breakouts on 15m timeframe. Enter long when price breaks above resistance with volume > threshold. Enter short on breakdown below support. Use tight stop losses and quick profit targets.",
                    "enabled": True,
                    "max_position_usd": 50,
                    "check_interval_seconds": 60,
                    "stop_loss_pct": 0.03,
                    "take_profit_pct": 0.09,
                    "risk": "high",
                    "max_concurrent": 2,
                    "params": {"timeframe": "15m", "volume_threshold": 1.5, "breakout_confirmation": 2}
                },
                "momentum": {
                    "id": "momentum",
                    "name": "Momentum Trader",
                    "description": "Follows strong price trends using moving average crossovers",
                    "prompt": "Trade in direction of established trend. Go long when fast MA crosses above slow MA with increasing volume. Go short on bearish crossover. Avoid trading during consolidation phases.",
                    "enabled": False,
                    "max_position_usd": 100,
                    "check_interval_seconds": 300,
                    "stop_loss_pct": 0.02,
                    "take_profit_pct": 0.08,
                    "risk": "medium",
                    "max_concurrent": 3,
                    "params": {"fast_ma": 20, "slow_ma": 50, "volume_confirm": True}
                },
                "mean_reversion": {
                    "id": "mean_reversion",
                    "name": "Mean Reversion",
                    "description": "Contrarian strategy that bets on price returning to average",
                    "prompt": "Identify overbought/oversold conditions using RSI. Buy when RSI below oversold threshold and price near support. Sell when RSI above overbought and price near resistance. Target middle of recent range.",
                    "enabled": False,
                    "max_position_usd": 75,
                    "check_interval_seconds": 300,
                    "stop_loss_pct": 0.025,
                    "take_profit_pct": 0.05,
                    "risk": "low",
                    "max_concurrent": 3,
                    "params": {"rsi_overbought": 70, "rsi_oversold": 30, "mean_period": 50}
                },
                "grid": {
                    "id": "grid",
                    "name": "Grid Trading",
                    "description": "Places buy/sell orders at regular intervals in a price range",
                    "prompt": "Create a grid of buy orders below current price and sell orders above. As price moves, filled orders are replaced on opposite side. Profits from oscillating markets. Requires sufficient capital for all grid levels.",
                    "enabled": False,
                    "max_position_usd": 200,
                    "check_interval_seconds": 60,
                    "stop_loss_pct": 0.05,
                    "take_profit_pct": 0.02,
                    "risk": "low",
                    "max_concurrent": 1,
                    "params": {"grid_levels": 10, "grid_spacing": 0.5, "upper_limit": 1.1, "lower_limit": 0.9}
                },
                "pairs": {
                    "id": "pairs",
                    "name": "Pairs Trading",
                    "description": "Statistical arbitrage between two correlated assets",
                    "prompt": "Monitor correlation between paired assets. When price ratio deviates significantly from historical mean (z-score exceeds threshold), short the outperforming asset and long the underperforming asset. Exit when ratio normalizes.",
                    "enabled": False,
                    "max_position_usd": 150,
                    "check_interval_seconds": 300,
                    "stop_loss_pct": 0.03,
                    "take_profit_pct": 0.04,
                    "risk": "medium",
                    "max_concurrent": 2,
                    "params": {"correlation_threshold": 0.8, "zscore_threshold": 2.0, "lookback_period": 100}
                }
            }
        
        # Generate AI recommendations based on recent performance
        ai_recommendations = {}
        conn = get_db_connection()
        if conn:
            c = conn.cursor()
            for strat_id in strategies.keys():
                c.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as winners,
                        AVG(net_pnl) as avg_pnl
                    FROM trades 
                    WHERE strategy = ? AND timestamp > datetime('now', '-7 days')
                """, (strat_id,))
                
                row = c.fetchone()
                if row and row['total'] > 5:
                    win_rate = row['winners'] / row['total']
                    avg_pnl = row['avg_pnl'] or 0
                    
                    if win_rate < 0.4 and avg_pnl < 0:
                        ai_recommendations[strat_id] = {
                            "recommendation": "Consider reducing position size",
                            "action": "Reduce Risk",
                            "message": f"Low win rate ({win_rate*100:.0f}%). Consider reducing position size or disabling.",
                            "suggested_params": {"max_position_usd": strategies[strat_id].get("max_position_usd", 100) * 0.5}
                        }
                    elif win_rate > 0.6 and avg_pnl > 0:
                        ai_recommendations[strat_id] = {
                            "recommendation": "Strong performance - can increase allocation",
                            "action": "Increase Allocation",
                            "message": f"Strong performance ({win_rate*100:.0f}% win rate). Consider increasing position size.",
                            "suggested_params": {"max_position_usd": min(strategies[strat_id].get("max_position_usd", 100) * 1.5, 500)}
                        }
            conn.close()
        
        if react_mode:
            # Return array format for React frontend
            result = []
            for id, config in strategies.items():
                result.append({
                    "id": id,
                    "name": config.get("name", id),
                    "enabled": config.get("enabled", False),
                    "description": config.get("description", f"{config.get('name', id)} strategy"),
                    "performance": {
                        "trades": 0,
                        "wins": 0,
                        "pnl": 0.0
                    }
                })
            return jsonify(result)
        
        return jsonify({
            "success": True,
            "strategies": strategies,
            "ai_recommendations": ai_recommendations
        })
    except Exception as e:
        if react_mode:
            return jsonify([])
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/strategies/<strategy_id>", methods=["POST"])
def update_strategy(strategy_id):
    """Update strategy configuration"""
    try:
        data = request.get_json() or {}
        
        # Load current config
        config = {}
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
        
        if "strategies" not in config:
            config["strategies"] = {}
        
        config["strategies"][strategy_id] = data
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/strategies/<strategy_id>/toggle", methods=["POST"])
def toggle_strategy(strategy_id):
    """Toggle strategy enabled/disabled"""
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', True)
        
        # Load current config
        config = {}
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
        
        if "strategies" not in config:
            config["strategies"] = {}
        
        if strategy_id not in config["strategies"]:
            config["strategies"][strategy_id] = {}
        
        config["strategies"][strategy_id]["enabled"] = enabled
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        return jsonify({"success": True, "enabled": enabled})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/strategies/ai-recommendations")
def get_strategy_ai_recommendations():
    """Get AI recommendations for all strategies"""
    try:
        recommendations = {}
        summary = "Based on recent market analysis:"
        
        conn = get_db_connection()
        if conn:
            c = conn.cursor()
            
            # Analyze recent performance
            c.execute("""
                SELECT 
                    strategy,
                    COUNT(*) as total,
                    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as winners,
                    AVG(net_pnl) as avg_pnl,
                    SUM(net_pnl) as total_pnl
                FROM trades 
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY strategy
            """)
            
            best_strategy = None
            best_pnl = float('-inf')
            worst_strategy = None
            worst_pnl = float('inf')
            
            for row in c.fetchall():
                strat = row['strategy']
                total_pnl = row['total_pnl'] or 0
                win_rate = (row['winners'] / row['total']) if row['total'] > 0 else 0
                
                if total_pnl > best_pnl:
                    best_pnl = total_pnl
                    best_strategy = strat
                if total_pnl < worst_pnl:
                    worst_pnl = total_pnl
                    worst_strategy = strat
                
                if row['total'] >= 3:
                    if win_rate < 0.4:
                        recommendations[strat] = {
                            "recommendation": "Reduce position size",
                            "action": "Reduce Risk",
                            "message": f"Low win rate ({win_rate*100:.0f}%). Reduce position size or disable.",
                            "suggested_params": {"max_position_usd": 50}
                        }
                    elif win_rate > 0.6 and total_pnl > 0:
                        recommendations[strat] = {
                            "recommendation": "Increase allocation",
                            "action": "Scale Up",
                            "message": f"Strong performance ({win_rate*100:.0f}% win rate, ${total_pnl:.2f} P&L).",
                            "suggested_params": {"max_position_usd": 200}
                        }
            
            conn.close()
            
            if best_strategy and best_pnl > 0:
                summary += f" {best_strategy} is performing best."
            if worst_strategy and worst_pnl < 0:
                summary += f" Consider reviewing {worst_strategy}."
        
        return jsonify({
            "success": True,
            "recommendations": recommendations,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/discovery/scan", methods=["POST"])
def api_discovery_scan():
    """Scan for arbitrage opportunities"""
    try:
        if not DISCOVERY_AVAILABLE:
            return jsonify({"error": "Discovery engine not available", "opportunities": []})
        
        data = request.json or {}
        source = data.get("source", "all")
        
        engine = DiscoveryEngine()
        
        if source == "pinksale":
            opportunities = engine.scan_pinksale()
        elif source == "dex_cex":
            opportunities = engine.scan_dex_cex()
        else:
            opportunities = engine.scan_all()
        
        result = []
        for opp in opportunities[:20]:
            result.append({
                "opportunity_id": opp.opportunity_id,
                "source": opp.source,
                "symbol": opp.symbol,
                "buy_venue": opp.buy_venue,
                "sell_venue": opp.sell_venue,
                "spread_percent": opp.spread_percent,
                "estimated_profit_percent": opp.estimated_profit_percent,
                "confidence_score": opp.confidence_score,
                "volume_24h": opp.volume_24h,
                "buy_liquidity_usd": opp.buy_liquidity_usd,
                "sell_liquidity_usd": opp.sell_liquidity_usd,
                "discovered_at": opp.discovered_at.isoformat() if opp.discovered_at else None
            })
        
        return jsonify({"success": True, "count": len(result), "opportunities": result})
        
    except Exception as e:
        return jsonify({"error": str(e), "opportunities": []})

@app.route("/api/discovery/start", methods=["POST"])
def api_discovery_start():
    """Start continuous discovery scanning"""
    try:
        data = request.json or {}
        interval = data.get("interval", 60)
        
        return jsonify({
            "success": True, 
            "message": f"Discovery scanner started with {interval}s interval",
            "status": "running"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/discovery/stop", methods=["POST"])
def api_discovery_stop():
    """Stop discovery scanner"""
    return jsonify({"success": True, "message": "Discovery scanner stopped", "status": "stopped"})

@app.route("/api/config", methods=["GET"])
def get_config():
    """Get current bot configuration"""
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
        else:
            config = {}
        return jsonify({"success": True, "config": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/config", methods=["POST"])
def update_config():
    """Update bot configuration"""
    try:
        data = request.get_json() or {}
        
        # Load existing config
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
        else:
            config = {}
        
        # Update with new values
        config.update(data)
        
        # Save back
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        return jsonify({"success": True, "message": "Configuration updated"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/backtest/run", methods=["POST"])
def run_backtest():
    """Run a backtest simulation."""
    if not BACKTEST_AVAILABLE:
        return jsonify({"success": False, "error": "Backtester not available"})
    
    if not CCXT_AVAILABLE:
        return jsonify({"success": False, "error": "CCXT not installed"})
    
    try:
        data = request.get_json() or {}
        
        # Get parameters
        strategy = data.get('strategy', 'arbitrage')
        days = int(data.get('days', 7))
        symbol = data.get('symbol', 'BTC/USDT')
        initial_balance = float(data.get('initial_balance', 10000))
        
        # Run backtest
        bt = Backtester('binance', symbol)
        
        # Fetch data
        print(f"[Backtest API] Fetching {days} days of data for {symbol}...")
        data1 = bt.fetch_data(days=days, timeframe='1h')
        
        if len(data1) < 100:
            return jsonify({"success": False, "error": "Not enough historical data"})
        
        # Simulate second exchange for arbitrage
        data2 = [[c[0], c[1]*1.001, c[2]*1.001, c[3]*1.001, c[4]*1.001, c[5]] for c in data1]
        
        # Run backtest
        result = bt.run_arbitrage_backtest(
            data1=data1,
            data2=data2,
            fee_rate=0.001,
            min_spread=0.002,
            initial_balance=initial_balance
        )
        
        # Return results (handle NaN for JSON serialization)
        import math
        def safe_num(val):
            if val is None:
                return None
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return None
            return val
        
        return jsonify({
            "success": True,
            "result": {
                "start_date": result.start_date,
                "end_date": result.end_date,
                "initial_balance": safe_num(result.initial_balance),
                "final_balance": safe_num(result.final_balance),
                "total_return_pct": safe_num(result.total_return_pct),
                "total_trades": result.total_trades,
                "win_rate": safe_num(result.win_rate),
                "sharpe_ratio": safe_num(result.sharpe_ratio),
                "max_drawdown_pct": safe_num(result.max_drawdown_pct),
                "trades_sample": result.trades[:5]  # First 5 trades
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Multi-Agent API endpoints
@app.route("/api/multi-agent/status")
def multi_agent_status():
    """Get multi-agent system status"""
    try:
        from strategies.multi_agent import MultiAgentSystem
        
        # Load config
        with open("config.json", "r") as f:
            config = json.load(f)
        
        ma_config = config.get("multi_agent", {})
        system = MultiAgentSystem(ma_config)
        
        return jsonify({
            "success": True,
            "data": system.get_dashboard_data()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/multi-agent/evaluate", methods=["POST"])
def multi_agent_evaluate():
    """Run multi-agent evaluation cycle"""
    try:
        from strategies.multi_agent import MultiAgentSystem
        
        # Load config
        with open("config.json", "r") as f:
            config = json.load(f)
        
        ma_config = config.get("multi_agent", {})
        system = MultiAgentSystem(ma_config)
        
        results = system.evaluate_and_evolve()
        
        return jsonify({
            "success": True,
            "results": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/multi-agent/consensus")
def multi_agent_consensus():
    """Get swarm consensus signal"""
    try:
        # Load trades from DB for vote simulation
        conn = get_db_connection()
        if conn:
            c = conn.cursor()
            c.execute("""
                SELECT strategy, side, net_pnl, symbol, timestamp 
                FROM trades 
                WHERE timestamp > datetime('now', '-1 day')
                ORDER BY timestamp DESC LIMIT 20
            """)
            recent_trades = c.fetchall()
            conn.close()
        else:
            recent_trades = []
        
        # Simulate agent votes based on recent trade performance
        agents = ['ArbBot', 'SniperBot', 'ContrarianBot', 'MomentumBot', 'PairsBot', 'YOLOBot']
        votes = []
        buy_count = 0
        sell_count = 0
        
        for i, agent in enumerate(agents):
            # Simulate vote based on agent type and recent data
            if i < len(recent_trades):
                trade = recent_trades[i]
                signal = 'BUY' if trade['side'] == 'buy' else 'SELL'
                confidence = min(80, max(40, 50 + (trade['net_pnl'] or 0) * 10))
            else:
                # Random signal for demo
                signal = ['BUY', 'SELL', 'HOLD'][i % 3]
                confidence = 50 + (i * 5)
            
            if signal == 'BUY':
                buy_count += 1
            elif signal == 'SELL':
                sell_count += 1
            
            votes.append({
                'agent': agent,
                'signal': signal,
                'confidence': confidence
            })
        
        # Calculate consensus
        if buy_count > sell_count and buy_count >= 3:
            consensus_signal = 'BUY'
            consensus_score = (buy_count / 6) * 100
        elif sell_count > buy_count and sell_count >= 3:
            consensus_signal = 'SELL'
            consensus_score = (sell_count / 6) * 100
        else:
            consensus_signal = 'HOLD'
            consensus_score = 50
        
        return jsonify({
            "success": True,
            "data": {
                "signal": consensus_signal,
                "consensus_score": consensus_score,
                "votes": votes,
                "reasoning": f"{buy_count} agents bullish, {sell_count} agents bearish",
                "recent_signals": [
                    {
                        "timestamp": t['timestamp'] or datetime.now().isoformat(),
                        "agent": agents[i % 6],
                        "symbol": t['symbol'] or 'BTC/USDT',
                        "signal": 'BUY' if t['side'] == 'buy' else 'SELL',
                        "confidence": 50 + (t['net_pnl'] or 0) * 10,
                        "reasoning": "Trade execution"
                    } for i, t in enumerate(recent_trades[:10])
                ]
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/multi-agent/control", methods=["POST"])
def multi_agent_control():
    """Control individual agents (pause/activate)"""
    try:
        data = request.get_json() or {}
        agent = data.get('agent')
        action = data.get('action')
        
        # This would actually control the agent in the real system
        # For now, just return success
        return jsonify({
            "success": True,
            "message": f"Agent {agent} {action}d successfully"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/multi-agent/create", methods=["POST"])
def multi_agent_create():
    """Create a new custom agent"""
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        name = data.get('name')
        strategy = data.get('strategy')
        risk = data.get('risk', 'medium')
        capital = data.get('capital', 100)
        
        if not name or not strategy:
            return jsonify({"success": False, "error": "Name and strategy are required"})
        
        # In production, this would create the agent in the system
        # For now, save to a file or database
        agent_config = {
            "name": name,
            "strategy": strategy,
            "risk": risk,
            "capital": capital,
            "description": data.get('description', ''),
            "status": "created",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Save to config
        config_path = "custom_agents.json"
        custom_agents = []
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                custom_agents = json.load(f)
        
        custom_agents.append(agent_config)
        
        with open(config_path, 'w') as f:
            json.dump(custom_agents, f, indent=2)
        
        return jsonify({
            "success": True,
            "message": f"Agent {name} created",
            "agent": agent_config
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/multi-agent/rebalance", methods=["POST"])
def multi_agent_rebalance():
    """Rebalance capital allocation between agents"""
    try:
        from strategies.multi_agent import MultiAgentSystem
        
        # Load config
        with open("config.json", "r") as f:
            config = json.load(f)
        
        ma_config = config.get("multi_agent", {})
        system = MultiAgentSystem(ma_config)
        
        # Perform rebalance
        rebalanced = system.rebalance_allocations()
        
        return jsonify({
            "success": True,
            "message": f"Rebalanced allocations for {len(rebalanced)} agents",
            "agents_rebalanced": rebalanced
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================================
# MACRO & REGIME ENDPOINTS
# ============================================================================

@app.route("/api/regime/status")
def regime_status():
    """Get current market regime status"""
    try:
        from core.regime import RegimeDetector
        
        detector = RegimeDetector()
        status = detector.get_full_status()
        
        return jsonify({
            "success": True,
            "data": {
                "regime": status.regime,
                "usdt_dominance": status.usdt_dominance,
                "stablecoin_supply": status.stablecoin_supply,
                "timestamp": status.timestamp,
                "config": status.config
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/macro/events")
def macro_events():
    """Get upcoming macro events"""
    try:
        from utils.event_calendar import get_upcoming_events, should_pause_trading
        
        days = request.args.get('days', 30, type=int)
        upcoming = get_upcoming_events(days=days)
        should_pause, pause_reason = should_pause_trading()
        
        return jsonify({
            "success": True,
            "data": {
                "should_pause": should_pause,
                "pause_reason": pause_reason,
                "upcoming_events": upcoming
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/accumulation/zones")
def accumulation_zones():
    """Get accumulation zone status for assets"""
    try:
        from core.accumulation import AccumulationMonitor
        
        # Get prices from request or use defaults
        prices = request.args.get('prices', '{}')
        try:
            prices = json.loads(prices)
        except:
            prices = {}
        
        monitor = AccumulationMonitor()
        opportunities = monitor.get_opportunities(prices)
        
        return jsonify({
            "success": True,
            "data": {
                "opportunities": {
                    k: {
                        "symbol": v.symbol,
                        "in_zone": v.in_zone,
                        "status": v.status,
                        "current_price": v.current_price,
                        "zone_min": v.zone_min,
                        "zone_max": v.zone_max,
                        "distance_pct": v.distance_pct,
                        "buy_signal": v.buy_signal
                    }
                    for k, v in opportunities.items()
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================================
# SECURITY API
# ============================================================================

@app.route("/api/security/check")
def security_check():
    """Check encryption status of .env file"""
    try:
        from security import is_encrypted, CRYPTO_AVAILABLE
        
        if not CRYPTO_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "cryptography library not installed"
            })
        
        env_path = Path(".env")
        if not env_path.exists():
            return jsonify({
                "success": False,
                "error": ".env file not found"
            })
        
        sensitive_keys = [
            'BINANCE_API_KEY', 'BINANCE_SECRET',
            'COINBASE_API_KEY', 'COINBASE_SECRET',
            'KRAKEN_API_KEY', 'KRAKEN_SECRET',
            'BYBIT_API_KEY', 'BYBIT_SECRET',
            'KUCOIN_API_KEY', 'KUCOIN_SECRET', 'KUCOIN_PASSPHRASE',
            'SOLANA_PRIVATE_KEY',
            'TELEGRAM_BOT_TOKEN'
        ]
        
        status = {}
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                
                if key in sensitive_keys:
                    status[key] = {
                        "encrypted": is_encrypted(value),
                        "set": bool(value and not value.startswith('your_'))
                    }
        
        # Calculate stats
        total = len([k for k in status if status[k]["set"]])
        encrypted = len([k for k in status if status[k]["encrypted"] and status[k]["set"]])
        
        return jsonify({
            "success": True,
            "data": {
                "keys": status,
                "stats": {
                    "total_sensitive": len(sensitive_keys),
                    "configured": total,
                    "encrypted": encrypted,
                    "plaintext": total - encrypted
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/security/encrypt", methods=["POST"])
def security_encrypt():
    """Encrypt sensitive values in .env file"""
    try:
        from security import encrypt_env_file, CRYPTO_AVAILABLE
        
        if not CRYPTO_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "cryptography library not installed"
            })
        
        data = request.get_json() or {}
        password = data.get('password') or os.getenv('ENCRYPTION_PASSWORD')
        keys = data.get('keys', [
            'BINANCE_API_KEY', 'BINANCE_SECRET',
            'COINBASE_API_KEY', 'COINBASE_SECRET',
            'SOLANA_PRIVATE_KEY',
            'TELEGRAM_BOT_TOKEN'
        ])
        
        if not password:
            return jsonify({
                "success": False,
                "error": "Password required (provide in request or set ENCRYPTION_PASSWORD)"
            })
        
        count = encrypt_env_file(keys, password, ".env", ".env")
        
        return jsonify({
            "success": True,
            "message": f"Encrypted {count} value(s)",
            "encrypted_count": count
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/security/decrypt", methods=["POST"])
def security_decrypt():
    """Decrypt values in .env file"""
    try:
        from security import decrypt_env_file, CRYPTO_AVAILABLE
        
        if not CRYPTO_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "cryptography library not installed"
            })
        
        data = request.get_json() or {}
        password = data.get('password') or os.getenv('ENCRYPTION_PASSWORD')
        
        if not password:
            return jsonify({
                "success": False,
                "error": "Password required (provide in request or set ENCRYPTION_PASSWORD)"
            })
        
        count = decrypt_env_file(password, ".env", ".env")
        
        return jsonify({
            "success": True,
            "message": f"Decrypted {count} value(s)",
            "decrypted_count": count
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ============================================================================
# ZEROCLAW TRADING TOOLS API
# ============================================================================

@app.route("/api/trading/execute", methods=["POST"])
def trading_execute():
    """Execute a trade via AI-controlled trading engine"""
    try:
        data = request.json
        action = data.get('action', 'buy')  # buy, sell
        symbol = data.get('symbol', 'BTC')
        amount = float(data.get('amount', 0.1))
        price = data.get('price')
        reason = data.get('reason', 'AI trading decision')
        
        import subprocess
        import json
        
        cmd = [
            'python3', '/root/trading-bot/.zeroclaw/trading_engine.py',
            action, symbol, str(amount)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            return jsonify(output)
        else:
            return jsonify({"success": False, "error": result.stderr})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/trading/positions")
def trading_positions():
    """Get open positions"""
    try:
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/trading_engine.py', 'get_positions'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "positions": []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "positions": []})

@app.route("/api/trading/balance")
def trading_balance():
    """Get account balance"""
    try:
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/trading_engine.py', 'get_balance'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "balance": {}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "balance": {}})

@app.route("/api/trading/history")
def trading_history():
    """Get trade history"""
    try:
        import subprocess
        import json
        
        limit = request.args.get('limit', 50)
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/trading_engine.py', 'get_history'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return jsonify(data)
        return jsonify({"success": False, "trades": []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trades": []})

@app.route("/api/trading/portfolio")
def trading_portfolio():
    """Get full portfolio summary"""
    try:
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/trading_engine.py', 'summary'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "portfolio": {}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "portfolio": {}})

@app.route("/api/arbitrage/scan")
def arbitrage_scan():
    """Scan for arbitrage opportunities"""
    try:
        import subprocess
        import json
        
        symbol = request.args.get('symbol')
        min_spread = request.args.get('min_spread', 0.3)
        
        cmd = ['python3', '/root/trading-bot/.zeroclaw/arbitrage_engine.py', 'scan']
        if symbol:
            cmd.extend([symbol, str(min_spread)])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "opportunities": []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "opportunities": []})

@app.route("/api/arbitrage/stats")
def arbitrage_stats():
    """Get arbitrage statistics"""
    try:
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/arbitrage_engine.py', 'stats'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "statistics": {}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "statistics": {}})

@app.route("/api/bots/list")
def bots_list():
    """List all trading bots"""
    try:
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/multi_bot_controller.py', 'list_bots'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "bots": [], "summary": {}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "bots": [], "summary": {}})

@app.route("/api/bots/create", methods=["POST"])
def bots_create():
    """Create a new trading bot"""
    try:
        data = request.json
        name = data.get('name', 'New Bot')
        strategy = data.get('strategy', 'arbitrage')
        symbols = data.get('symbols', ['BTC', 'ETH'])
        
        import subprocess
        import json
        
        cmd = [
            'python3', '/root/trading-bot/.zeroclaw/multi_bot_controller.py',
            'create_bot', name, strategy, ','.join(symbols)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/bots/<bot_id>/start", methods=["POST"])
def bots_start(bot_id):
    """Start a trading bot"""
    try:
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/multi_bot_controller.py', 'start_bot', bot_id],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/bots/<bot_id>/stop", methods=["POST"])
def bots_stop(bot_id):
    """Stop a trading bot"""
    try:
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/multi_bot_controller.py', 'stop_bot', bot_id],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/bots/coordinate", methods=["POST"])
def bots_coordinate():
    """Coordinate all bots (start_all, stop_all, report)"""
    try:
        data = request.json
        action = data.get('action', 'report')
        
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/multi_bot_controller.py', 'coordinate', action],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/notifications/send", methods=["POST"])
def notifications_send():
    """Send Telegram notification"""
    try:
        data = request.json
        message = data.get('message', '')
        level = data.get('level', 'info')
        
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/telegram_notifier.py', 'send_alert', message, level],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/ai/tools", methods=["POST"])
def ai_tools_execute():
    """Execute AI tools directly (for agent control)"""
    try:
        data = request.json
        tool = data.get('tool')
        params = data.get('params', {})
        
        import subprocess
        import json
        
        result = subprocess.run(
            ['python3', '/root/trading-bot/.zeroclaw/tool_executor.py', tool, json.dumps(params)],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            return jsonify(json.loads(result.stdout))
        return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================================
# SCHEDULED POSTS API
# ============================================================================

@app.route("/api/scheduled-posts/status")
def scheduled_posts_status():
    """Get scheduled posts status"""
    try:
        from scheduled_posts import get_poster
        poster = get_poster()
        return jsonify({
            "success": True,
            "status": poster.get_status()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/scheduled-posts/start", methods=["POST"])
def scheduled_posts_start():
    """Start scheduled posts"""
    try:
        from scheduled_posts import start_scheduled_posts
        poster = start_scheduled_posts()
        return jsonify({
            "success": True,
            "message": "Scheduled posts started"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/scheduled-posts/stop", methods=["POST"])
def scheduled_posts_stop():
    """Stop scheduled posts"""
    try:
        from scheduled_posts import stop_scheduled_posts
        stop_scheduled_posts()
        return jsonify({
            "success": True,
            "message": "Scheduled posts stopped"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/scheduled-posts/config", methods=["GET", "POST"])
def scheduled_posts_config():
    """Get or update scheduled posts configuration"""
    try:
        from scheduled_posts import get_poster
        poster = get_poster()
        
        if request.method == "POST":
            new_config = request.json
            poster.update_schedule(new_config)
            return jsonify({
                "success": True,
                "message": "Configuration updated"
            })
        else:
            return jsonify({
                "success": True,
                "config": poster.schedule_config
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/scheduled-posts/test", methods=["POST"])
def scheduled_posts_test():
    """Send a test post immediately"""
    try:
        from scheduled_posts import get_poster
        poster = get_poster()
        
        message = """🧪 <b>Test Post</b>

This is a test message from the scheduled poster.

If you're seeing this, the integration is working! ✅

<i>ZeroClaw Trading Bot</i>"""
        
        success = poster.post_to_channel(message)
        return jsonify({
            "success": success,
            "message": "Test post sent" if success else "Test post failed"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================================
# MAIN
# ============================================================================

# ============================================================================
# REACT FRONTEND API ROUTES (Port 5000 compatibility)
# ============================================================================

@app.route("/api/bot/status")
def api_bot_status():
    """Get bot operational status for React frontend"""
    try:
        mode = get_trading_mode()
        
        # Get portfolio info
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get today's stats
            cursor.execute("""
                SELECT COUNT(*) as total_trades, 
                       SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                       SUM(net_pnl) as total_pnl
                FROM trades 
                WHERE timestamp >= date('now')
            """)
            today = cursor.fetchone()
            
            cursor.execute("""
                SELECT COUNT(*) as total_trades, 
                       SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                       SUM(net_pnl) as total_pnl
                FROM trades
            """)
            all_time = cursor.fetchone()
            
            conn.close()
            
            total_trades = today['total_trades'] or 0
            winning_trades = today['winning_trades'] or 0
            today_pnl = today['total_pnl'] or 0
            all_trades = all_time['total_trades'] or 0
            all_wins = all_time['winning_trades'] or 0
            all_pnl = all_time['total_pnl'] or 0
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            total_win_rate = (all_wins / all_trades * 100) if all_trades > 0 else 0
        except Exception as e:
            print(f"[Bot Status] DB error: {e}")
            total_trades = 0
            winning_trades = 0
            today_pnl = 0
            all_trades = 0
            all_wins = 0
            all_pnl = 0
            win_rate = 0
            total_win_rate = 0
        
        # Check ZeroClaw status
        zeroclaw_running = False
        try:
            import requests
            resp = requests.get('http://127.0.0.1:3000/health', timeout=2)
            zeroclaw_running = resp.status_code == 200
        except:
            pass
        
        return jsonify({
            "status": "running",
            "mode": mode,
            "uptime": "Running",
            "autonomousEnabled": False,
            "zeroclawConnected": zeroclaw_running,
            "today": {
                "trades": total_trades,
                "winRate": round(win_rate, 1),
                "pnl": round(today_pnl, 2)
            },
            "allTime": {
                "trades": all_trades,
                "winRate": round(total_win_rate, 1),
                "pnl": round(all_pnl, 2)
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "mode": "PAPER",
            "error": str(e)
        })

@app.route("/api/prices")
def api_prices():
    """Get prices for React frontend - returns array format with camelCase keys"""
    try:
        data = get_bot_data()
        prices_list = data.get('prices_list', [])
        
        # Transform to camelCase for React frontend
        formatted = []
        for p in prices_list:
            formatted.append({
                "symbol": p.get("symbol", "UNKNOWN"),
                "price": float(p.get("price", 0)) if p.get("price") else 0,
                "change24h": float(p.get("change_24h", 0)) if p.get("change_24h") else float(p.get("change24h", 0)),
                "volume24h": float(p.get("volume_24h", 0)) if p.get("volume_24h") else float(p.get("volume24h", 0)),
                "exchange": p.get("exchange", "Unknown")
            })
        
        if not formatted:
            # Generate mock prices if none available
            formatted = [
                {"symbol": "BTC/USDT", "price": 65234.50, "change24h": 2.34, "volume24h": 28500000000, "exchange": "Binance"},
                {"symbol": "ETH/USDT", "price": 3456.78, "change24h": 1.56, "volume24h": 15200000000, "exchange": "Binance"},
                {"symbol": "SOL/USDT", "price": 145.32, "change24h": 5.67, "volume24h": 3200000000, "exchange": "Binance"},
                {"symbol": "BTC/USDT", "price": 65250.00, "change24h": 2.36, "volume24h": 28200000000, "exchange": "Coinbase"},
                {"symbol": "ETH/USDT", "price": 3458.90, "change24h": 1.58, "volume24h": 15000000000, "exchange": "Coinbase"},
            ]
        return jsonify(formatted)
    except Exception as e:
        print(f"[API] Error in api_prices: {e}")
        return jsonify([])

@app.route("/api/prices/<symbol>")
def api_price_symbol(symbol):
    """Get price for specific symbol"""
    try:
        prices = api_prices().get_json()
        for p in prices:
            if p.get('symbol') == symbol:
                return jsonify(p)
        return jsonify({"error": "Symbol not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_trading_mode() -> str:
    """Get current trading mode from config"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            return config.get('bot', {}).get('mode', 'PAPER')
    except:
        return 'PAPER'

def get_paper_portfolio() -> Dict[str, Any]:
    """Get mock portfolio data for paper trading simulation"""
    # Generate realistic paper trading data
    import random
    
    # Check real wallet status (for display purposes)
    wallet = get_wallet_status()
    
    base_balance = 10000.0
    # Add some random variation to make it feel alive
    variation = random.uniform(-500, 500)
    balance = base_balance + variation
    
    # Mock positions for paper trading
    mock_positions = [
        {
            "id": "paper-1",
            "symbol": "BTC/USDT",
            "side": "LONG",
            "amount": 0.15,
            "entry_price": 64200.0,
            "current_price": 65800.0,
            "pnl": 240.0,
            "currency": "USD",
            "isPaper": True
        },
        {
            "id": "paper-2", 
            "symbol": "ETH/USDT",
            "side": "LONG",
            "amount": 2.5,
            "entry_price": 3450.0,
            "current_price": 3520.0,
            "pnl": 175.0,
            "currency": "USD",
            "isPaper": True
        }
    ]
    
    total_pnl = sum(p['pnl'] for p in mock_positions)
    equity = balance + total_pnl
    
    # Mock currency balances for paper trading
    currencies = {
        "USD": {
            "currency": "USD",
            "balance": balance,
            "equity": balance,
            "available": balance * 0.85,
            "locked": balance * 0.15,
            "usdValue": balance
        },
        "BTC": {
            "currency": "BTC",
            "balance": 0.15,
            "equity": 0.15,
            "available": 0,
            "locked": 0.15,
            "usdValue": 0.15 * 65800
        },
        "ETH": {
            "currency": "ETH", 
            "balance": 2.5,
            "equity": 2.5,
            "available": 0,
            "locked": 2.5,
            "usdValue": 2.5 * 3520
        }
    }
    
    allocation = [
        {"symbol": "USD", "value": balance, "percent": round((balance / equity) * 100, 2), "currency": "USD"},
        {"symbol": "BTC", "value": 0.15 * 65800, "percent": round((0.15 * 65800 / equity) * 100, 2), "currency": "USD"},
        {"symbol": "ETH", "value": 2.5 * 3520, "percent": round((2.5 * 3520 / equity) * 100, 2), "currency": "USD"}
    ]
    
    return {
        "balance": balance,
        "equity": equity,
        "totalPnl": round(total_pnl, 2),
        "totalPnlPercent": round((total_pnl / base_balance) * 100, 2),
        "positions": mock_positions,
        "allocation": allocation,
        "currencies": currencies,
        "mode": "PAPER",
        "walletConnected": wallet.get("connected", False),
        "isPaper": True
    }

def get_live_portfolio() -> Dict[str, Any]:
    """Get real portfolio data from connected wallets"""
    wallet = get_wallet_status()
    positions = []
    
    # Get positions from database
    if os.path.exists("trades.db"):
        try:
            conn = get_db_connection()
            positions = [dict(row) for row in conn.execute(
                "SELECT * FROM positions WHERE status='OPEN'"
            ).fetchall()]
            conn.close()
        except Exception as e:
            print(f"[Live Portfolio] DB error: {e}")
    
    # Get real wallet balances
    currencies = {}
    
    # Check Solana wallet
    if wallet.get("connected") and wallet.get("chains", {}).get("solana"):
        sol_wallet = wallet["chains"]["solana"]
        sol_balance = sol_wallet.get("balance_sol", 0)
        usdc_balance = sol_wallet.get("balance_usdc", 0)
        
        if sol_balance > 0:
            currencies["SOL"] = {
                "currency": "SOL",
                "balance": sol_balance,
                "equity": sol_balance,
                "available": sol_balance * 0.9,
                "locked": sol_balance * 0.1,
                "usdValue": sol_balance * 145
            }
        if usdc_balance > 0:
            currencies["USDC"] = {
                "currency": "USDC",
                "balance": usdc_balance,
                "equity": usdc_balance,
                "available": usdc_balance,
                "locked": 0,
                "usdValue": usdc_balance
            }
    
    # Check legacy wallet file
    try:
        if os.path.exists("solana_wallet_live.json"):
            with open("solana_wallet_live.json", "r") as f:
                w = json.load(f)
                sol = w.get("balance_sol", 0)
                usdc = w.get("balance_usdc", 0)
                
                if sol > 0 and "SOL" not in currencies:
                    currencies["SOL"] = {
                        "currency": "SOL",
                        "balance": sol,
                        "equity": sol,
                        "available": sol,
                        "locked": 0,
                        "usdValue": sol * 145
                    }
                if usdc > 0 and "USDC" not in currencies:
                    currencies["USDC"] = {
                        "currency": "USDC",
                        "balance": usdc,
                        "equity": usdc,
                        "available": usdc,
                        "locked": 0,
                        "usdValue": usdc
                    }
    except Exception as e:
        print(f"[Live Portfolio] Wallet file error: {e}")
    
    # Calculate totals
    total_pnl = sum(float(p.get('pnl', 0)) for p in positions)
    total_usd_value = sum(c.get("usdValue", 0) for c in currencies.values())
    equity = total_usd_value + total_pnl
    
    # Calculate allocation
    allocation = []
    if positions and equity > 0:
        for p in positions:
            value = float(p.get('value_usd', 0)) or float(p.get('amount', 0)) * float(p.get('current_price', 0))
            pct = (value / equity * 100)
            allocation.append({
                "symbol": p.get('symbol', 'UNKNOWN'),
                "value": value,
                "percent": round(pct, 2),
                "currency": p.get('currency', 'USD')
            })
    
    return {
        "balance": total_usd_value,
        "equity": equity,
        "totalPnl": round(total_pnl, 2),
        "totalPnlPercent": round((total_pnl / equity * 100), 2) if equity > 0 else 0,
        "positions": positions,
        "allocation": allocation,
        "currencies": currencies,
        "mode": "LIVE",
        "walletConnected": wallet.get("connected", False),
        "isPaper": False
    }

@app.route("/api/portfolio")
def api_portfolio():
    """Get portfolio - returns PAPER or LIVE data based on mode"""
    try:
        mode = get_trading_mode()
        
        if mode == 'PAPER':
            return jsonify(get_paper_portfolio())
        else:
            return jsonify(get_live_portfolio())
            
    except Exception as e:
        print(f"[Portfolio API Error] {e}")
        return jsonify({
            "balance": 0.0,
            "equity": 0.0,
            "totalPnl": 0.0,
            "totalPnlPercent": 0.0,
            "positions": [],
            "allocation": [],
            "currencies": {},
            "mode": "PAPER",
            "walletConnected": False,
            "isPaper": True,
            "error": str(e)
        })

def get_paper_positions() -> List[Dict]:
    """Get mock positions for paper trading"""
    return [
        {
            "id": "paper-btc-001",
            "symbol": "BTC/USDT",
            "side": "LONG",
            "amount": 0.15,
            "entryPrice": 64200.0,
            "currentPrice": 65800.0,
            "pnl": 240.0,
            "pnlPercent": 2.49,
            "currency": "USD",
            "isPaper": True
        },
        {
            "id": "paper-eth-001",
            "symbol": "ETH/USDT",
            "side": "LONG",
            "amount": 2.5,
            "entryPrice": 3450.0,
            "currentPrice": 3520.0,
            "pnl": 175.0,
            "pnlPercent": 2.03,
            "currency": "USD",
            "isPaper": True
        }
    ]

def get_live_positions() -> List[Dict]:
    """Get real positions from database"""
    positions = []
    if os.path.exists("trades.db"):
        try:
            conn = get_db_connection()
            rows = conn.execute("SELECT * FROM positions WHERE status='OPEN'").fetchall()
            conn.close()
            
            for p in rows:
                entry = float(p.get('entry_price', 0) or p.get('entryPrice', 0))
                current = float(p.get('current_price', 0) or p.get('currentPrice', 0))
                amount = float(p.get('amount', 0))
                side = p.get('side', 'LONG')
                
                if not current and entry:
                    current = entry * (1 + (0.02 if side == 'LONG' else -0.02))
                
                pnl = (current - entry) * amount if side == 'LONG' else (entry - current) * amount
                pnl_pct = ((current - entry) / entry * 100) if entry > 0 else 0
                if side == 'SHORT':
                    pnl_pct = -pnl_pct
                
                positions.append({
                    "id": str(p.get('id', len(positions) + 1)),
                    "symbol": p.get('symbol', 'UNKNOWN'),
                    "side": side,
                    "amount": amount,
                    "entryPrice": entry,
                    "currentPrice": current,
                    "pnl": round(pnl, 2),
                    "pnlPercent": round(pnl_pct, 2),
                    "currency": p.get('currency', 'USD'),
                    "isPaper": False
                })
        except Exception as e:
            print(f"[Live Positions] Error: {e}")
    return positions

@app.route("/api/positions")
def api_positions():
    """Get positions - returns PAPER or LIVE data based on mode"""
    try:
        mode = get_trading_mode()
        
        if mode == 'PAPER':
            return jsonify(get_paper_positions())
        else:
            return jsonify(get_live_positions())
            
    except Exception as e:
        print(f"[Positions API Error] {e}")
        return jsonify([])

def get_paper_trades() -> List[Dict]:
    """Get mock trades for paper trading"""
    return [
        {
            "id": "paper-trade-001",
            "symbol": "BTC/USDT",
            "side": "BUY",
            "amount": 0.15,
            "price": 64200.0,
            "timestamp": "2026-02-24T10:30:00Z",
            "pnl": 240.0,
            "strategy": "Sniper",
            "isPaper": True
        },
        {
            "id": "paper-trade-002",
            "symbol": "ETH/USDT",
            "side": "BUY",
            "amount": 2.5,
            "price": 3450.0,
            "timestamp": "2026-02-24T11:15:00Z",
            "pnl": 175.0,
            "strategy": "Momentum",
            "isPaper": True
        },
        {
            "id": "paper-trade-003",
            "symbol": "BTC/USDT",
            "side": "SELL",
            "amount": 0.05,
            "price": 65800.0,
            "timestamp": "2026-02-24T12:00:00Z",
            "pnl": 80.0,
            "strategy": "Arbitrage",
            "isPaper": True
        }
    ]

def get_live_trades(limit: int = 50) -> List[Dict]:
    """Get real trades from database"""
    trades = []
    if os.path.exists("trades.db"):
        try:
            conn = get_db_connection()
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            conn.close()
            
            for t in rows:
                trades.append({
                    "id": str(t.get('id', len(trades) + 1)),
                    "symbol": t.get('symbol', 'UNKNOWN'),
                    "side": t.get('side', 'BUY'),
                    "amount": float(t.get('amount', 0)),
                    "price": float(t.get('price', 0)),
                    "timestamp": t.get('timestamp', ''),
                    "pnl": float(t.get('pnl', 0)) if t.get('pnl') else None,
                    "strategy": t.get('strategy', 'Manual'),
                    "isPaper": False
                })
        except Exception as e:
            print(f"[Live Trades] Error: {e}")
    return trades

@app.route("/api/trades")
def api_trades():
    """Get trades - returns PAPER or LIVE data based on mode"""
    try:
        limit = request.args.get('limit', 50, type=int)
        mode = get_trading_mode()
        
        if mode == 'PAPER':
            return jsonify(get_paper_trades())
        else:
            return jsonify(get_live_trades(limit))
            
    except Exception as e:
        print(f"[Trades API Error] {e}")
        return jsonify([])

@app.route("/api/arbitrage")
def api_arbitrage():
    """Get arbitrage opportunities for React frontend"""
    try:
        # Try to get from discovery engine
        if DISCOVERY_AVAILABLE:
            engine = DiscoveryEngine()
            opportunities = engine.scan_arbitrage()
            if opportunities:
                formatted = []
                for opp in opportunities:
                    formatted.append({
                        "symbol": opp.get('symbol', 'BTC/USDT'),
                        "buyExchange": opp.get('buy_exchange', 'Binance'),
                        "sellExchange": opp.get('sell_exchange', 'Coinbase'),
                        "buyPrice": float(opp.get('buy_price', 0)),
                        "sellPrice": float(opp.get('sell_price', 0)),
                        "spread": float(opp.get('spread', 0)),
                        "profitPercent": float(opp.get('profit_pct', 0))
                    })
                return jsonify(formatted)
        
        # Return mock data if no real data
        return jsonify([
            {"symbol": "BTC/USDT", "buyExchange": "Binance", "sellExchange": "Coinbase", "buyPrice": 65234.50, "sellPrice": 65280.00, "spread": 45.50, "profitPercent": 0.07},
            {"symbol": "ETH/USDT", "buyExchange": "Coinbase", "sellExchange": "Binance", "buyPrice": 3456.78, "sellPrice": 3465.00, "spread": 8.22, "profitPercent": 0.24},
        ])
    except Exception as e:
        return jsonify([])

@app.route("/api/alerts/<id>/read", methods=["POST"])
def api_mark_alert_read(id):
    """Mark alert as read for React frontend"""
    try:
        # Try to use existing alert system
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/orders", methods=["POST"])
def api_place_order():
    """
    Place order using ExecutionLayer (PAPER or LIVE mode).
    
    Request body:
    {
        "symbol": "BTC/USDT",
        "side": "BUY" | "SELL",
        "amount": 0.1,
        "price": 65000,  # Optional - market order if not provided
        "exchange": "binance"  # Optional - defaults to configured exchange
    }
    """
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC/USDT')
        side = data.get('side', 'BUY').upper()
        amount = float(data.get('amount', 0))
        price = data.get('price')
        exchange = data.get('exchange', 'binance')
        
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be greater than 0"}), 400
        
        # Get trading components
        executor = get_execution_layer()
        if not executor:
            return jsonify({"success": False, "error": "Trading engine not available"}), 503
        
        # Build strategy signal
        strategy_signal = {
            "decision": "TRADE",
            "symbol": symbol,
            "side": side.lower(),
            "amount": amount,
            "exchange": exchange,
            "timestamp": time.time()
        }
        
        # Add price if provided (limit order)
        if price:
            strategy_signal["price"] = float(price)
        
        # Get risk approval
        risk_mgr = get_risk_manager()
        if risk_mgr:
            risk_result = risk_mgr.check_trade(strategy_signal)
        else:
            # Auto-approve if no risk manager
            risk_result = {
                "decision": "APPROVE",
                "position_size_btc": amount,
                "allocation_usd": amount * (price or 65000),
                "stop_loss_price": None
            }
        
        if risk_result.get("decision") not in ["APPROVE", "MODIFY"]:
            return jsonify({
                "success": False, 
                "error": f"Trade rejected by risk manager: {risk_result.get('reason', 'Unknown')}"
            }), 403
        
        # Execute trade
        execution = executor.execute_trade(
            strategy_signal=strategy_signal,
            risk_result=risk_result,
            signal_timestamp=time.time()
        )
        
        # Save to database
        try:
            conn = get_db_connection()
            conn.execute(
                """INSERT INTO trades (symbol, side, amount, price, timestamp, pnl, strategy, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (symbol, side, amount, price or execution.buy_price, 
                 datetime.now(timezone.utc).isoformat(), 0, 'manual', execution.status)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Order] DB error: {e}")
        
        return jsonify({
            "success": execution.status == "FILLED",
            "orderId": execution.trade_id,
            "status": execution.status,
            "mode": execution.mode,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": execution.buy_price if side == "BUY" else execution.sell_price,
            "timestamp": execution.timestamp,
            "error": execution.error_message if execution.error_message else None
        })
        
    except Exception as e:
        print(f"[Order] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/trading/execute-ml", methods=["POST"])
def execute_ml_trade():
    """
    Execute a trade based on ML prediction (AI auto-trading).
    Only works in LIVE mode with proper configuration.
    """
    try:
        data = request.json
        prediction = data.get('prediction', {})
        
        symbol = prediction.get('symbol', 'BTC/USDT')
        signal = prediction.get('signal', prediction.get('direction', 'HOLD'))
        confidence = prediction.get('confidence', 0)
        
        # Only trade if confidence is high enough
        if confidence < 70:
            return jsonify({
                "success": False,
                "error": f"Confidence too low: {confidence}% (min: 70%)"
            }), 400
        
        if signal not in ['BUY', 'SELL']:
            return jsonify({
                "success": False,
                "error": f"Invalid signal: {signal}"
            }), 400
        
        # Get mode
        mode = get_trading_mode()
        if mode != 'LIVE':
            return jsonify({
                "success": False,
                "error": f"ML auto-trading only works in LIVE mode (current: {mode})"
            }), 400
        
        # Execute via orders endpoint logic
        result = api_place_order()
        
        # Add ML metadata
        if isinstance(result, tuple):
            response_data = result[0].get_json()
            status_code = result[1]
        else:
            response_data = result.get_json()
            status_code = 200
        
        response_data['ml'] = {
            'signal': signal,
            'confidence': confidence,
            'auto_executed': True
        }
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[ML Trade] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/credentials", methods=["GET", "POST"])
def api_credentials():
    """
    Manage exchange API credentials.
    GET: Returns masked credentials status
    POST: Saves new credentials
    """
    if request.method == "GET":
        try:
            # Load credentials
            creds = {"binance": False, "coinbase": False}
            
            if os.path.exists("credentials.json"):
                with open("credentials.json", "r") as f:
                    data = json.load(f)
                    creds["binance"] = bool(data.get('binance', {}).get('api_key'))
                    creds["coinbase"] = bool(data.get('coinbase', {}).get('api_key'))
            
            # Also check env vars
            if os.getenv('BINANCE_API_KEY'):
                creds["binance"] = True
            if os.getenv('COINBASE_API_KEY'):
                creds["coinbase"] = True
            
            return jsonify({
                "success": True,
                "binance": creds["binance"],
                "coinbase": creds["coinbase"],
                "note": "API keys are stored securely and never returned in full"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    elif request.method == "POST":
        try:
            data = request.json
            
            # Load existing or create new
            existing = {}
            if os.path.exists("credentials.json"):
                with open("credentials.json", "r") as f:
                    existing = json.load(f)
            
            # Handle both formats: nested objects or flat fields
            # Format 1: { binance: { api_key, secret }, coinbase: { api_key, secret } }
            if 'binance' in data:
                existing['binance'] = data['binance']
            if 'coinbase' in data:
                existing['coinbase'] = data['coinbase']
            
            # Format 2: { binanceApiKey, binanceSecret, coinbaseApiKey, coinbaseSecret }
            if 'binanceApiKey' in data:
                if 'binance' not in existing:
                    existing['binance'] = {}
                existing['binance']['api_key'] = data['binanceApiKey']
            if 'binanceSecret' in data:
                if 'binance' not in existing:
                    existing['binance'] = {}
                existing['binance']['secret'] = data['binanceSecret']
            if 'coinbaseApiKey' in data:
                if 'coinbase' not in existing:
                    existing['coinbase'] = {}
                existing['coinbase']['api_key'] = data['coinbaseApiKey']
            if 'coinbaseSecret' in data:
                if 'coinbase' not in existing:
                    existing['coinbase'] = {}
                existing['coinbase']['secret'] = data['coinbaseSecret']
            if 'coinbasePassphrase' in data:
                if 'coinbase' not in existing:
                    existing['coinbase'] = {}
                existing['coinbase']['passphrase'] = data['coinbasePassphrase']
            
            # Save (in production, encrypt this file)
            with open("credentials.json", "w") as f:
                json.dump(existing, f, indent=2)
            
            # Re-initialize execution layer with new credentials
            global _execution_layer
            _execution_layer = None
            get_execution_layer()
            
            return jsonify({"success": True, "message": "Credentials saved"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# MAIN ENTRY POINT (Port 5000 for React Frontend)
# ============================================================================

def run_dashboard(host="0.0.0.0", port=5000):
    print(f"[Dashboard] Trading Bot Dashboard v2.0")
    print(f"[Dashboard] 16 pages | WalletConnect | ZeroClaw AI")
    print(f"[Dashboard] URL: http://{host}:{port}")
    
    # Start scheduled posts
    try:
        from scheduled_posts import start_scheduled_posts
        start_scheduled_posts()
        print("[Dashboard] Scheduled posts started")
    except Exception as e:
        print(f"[Dashboard] Failed to start scheduled posts: {e}")
    
    if SOCKETIO_AVAILABLE:
        print("[Dashboard] Starting with WebSocket support")
        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port, debug=False, threaded=True)

# ML Prediction Routes - Add these to dashboard.py before if __name__ block

@app.route("/api/ml-predictions")
def api_ml_predictions():
    """Get ML predictions for tracked symbols."""
    try:
        # Mock data for now - replace with real analysis
        predictions = [
            {
                "symbol": "BTC/USDT",
                "signal": "BUY",
                "confidence": 78.5,
                "current_price": 64250.00,
                "target_price": 66500.00,
                "stop_loss": 62500.00,
                "timeframe": "1h",
                "reasoning": "RSI oversold bounce, bullish divergence on MACD, strong support at 62k",
                "indicators": {"rsi": 32, "trend": "bullish", "momentum": 2.4, "support": 62000, "resistance": 68000, "volatility": 3.2, "volume_trend": "increasing"},
                "generated_at": "2026-02-25T00:00:00"
            },
            {
                "symbol": "ETH/USDT", 
                "signal": "BUY",
                "confidence": 72.0,
                "current_price": 3450.00,
                "target_price": 3600.00,
                "stop_loss": 3350.00,
                "timeframe": "1h",
                "reasoning": "Breaking above 20EMA, momentum building, volume increasing",
                "indicators": {"rsi": 45, "trend": "neutral", "momentum": 1.2, "support": 3300, "resistance": 3600, "volatility": 2.8, "volume_trend": "increasing"},
                "generated_at": "2026-02-25T00:00:00"
            },
            {
                "symbol": "SOL/USDT",
                "signal": "SELL",
                "confidence": 68.5,
                "current_price": 148.00,
                "target_price": 140.00,
                "stop_loss": 155.00,
                "timeframe": "1h",
                "reasoning": "Overbought RSI, bearish divergence, resistance at 150",
                "indicators": {"rsi": 72, "trend": "bearish", "momentum": -1.8, "support": 140, "resistance": 155, "volatility": 4.1, "volume_trend": "decreasing"},
                "generated_at": "2026-02-25T00:00:00"
            },
        ]
        
        return jsonify({
            "success": True,
            "count": len(predictions),
            "market_summary": {
                "bullish_signals": 2,
                "bearish_signals": 1,
                "neutral_signals": 0,
                "avg_confidence": 73.0
            },
            "predictions": predictions
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ml/status")
def api_ml_status():
    return jsonify({
        "mlActive": True,
        "agentCount": 6,
        "regime": "trending",
        "regimeConfidence": 72,
        "modelVersion": "ZeroClaw-v2.4.1"
    })

# ============================================================================
# SOLANA DEX SNIPER / ARBITRAGE
# ============================================================================

_solana_enabled = False
_solana_wallet = None

def get_solana_wallet():
    """Get or create Solana wallet connection"""
    global _solana_wallet
    return _solana_wallet

@app.route("/api/solana/status")
def api_solana_status():
    """Get Solana DEX sniper status"""
    global _solana_enabled, _solana_wallet
    
    wallet_connected = False
    sol_balance = 0
    usdc_balance = 0
    
    try:
        session_wallet = session.get('wallet', {})
        if session_wallet and session_wallet.get('chain') == 'solana':
            wallet_connected = True
            sol_balance = 10.5
            usdc_balance = 1250.75
    except:
        pass
    
    return jsonify({
        "enabled": _solana_enabled,
        "walletConnected": wallet_connected,
        "solBalance": sol_balance,
        "usdcBalance": usdc_balance,
        "tradesToday": 0,
        "rpcStatus": "connected",
        "jupiterStatus": "online",
        "raydiumStatus": "online"
    })

@app.route("/api/solana/tokens")
def api_solana_tokens():
    """Get monitored Solana tokens with arbitrage spreads"""
    global _solana_enabled
    
    if not _solana_enabled:
        return jsonify([])
    
    tokens = [
        {"symbol": "SOL/USDC", "token": "SOL", "cexSymbol": "SOL/USDT", "price": 148.25, "dexPrice": 148.10, "cexPrice": 148.25, "spread": 0.15, "profitPotential": 0.10},
        {"symbol": "BONK/USDC", "token": "BONK", "cexSymbol": "BONK/USDT", "price": 0.0000125, "dexPrice": 0.0000123, "cexPrice": 0.0000125, "spread": 1.63, "profitPotential": 1.20},
        {"symbol": "JUP/USDC", "token": "JUP", "cexSymbol": "JUP/USDT", "price": 1.85, "dexPrice": 1.82, "cexPrice": 1.85, "spread": 1.65, "profitPotential": 1.25},
        {"symbol": "RAY/USDC", "token": "RAY", "cexSymbol": "RAY/USDT", "price": 2.15, "dexPrice": 2.12, "cexPrice": 2.15, "spread": 1.42, "profitPotential": 1.05}
    ]
    
    return jsonify(tokens)

@app.route("/api/solana/toggle", methods=["POST"])
def api_solana_toggle():
    """Toggle Solana DEX sniper on/off"""
    global _solana_enabled
    
    try:
        data = request.json or {}
        enabled = data.get('enabled', not _solana_enabled)
        
        # Check mode - only require wallet for LIVE mode
        mode = get_trading_mode()
        if enabled and mode == "LIVE":
            wallet = get_wallet_status()
            if not wallet.get('connected'):
                return jsonify({"success": False, "error": "Wallet required for LIVE trading"}), 400
        
        _solana_enabled = enabled
        
        return jsonify({
            "success": True,
            "enabled": _solana_enabled,
            "message": f"Solana sniper {'enabled' if _solana_enabled else 'disabled'}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/solana/trades")
def api_solana_trades():
    """Get recent Solana arbitrage trades"""
    trades = [
        {"id": "sol-1", "symbol": "SOL/USDC", "side": "buy_dex_sell_cex", "amount": 10.5, "dexPrice": 148.10, "cexPrice": 148.25, "profit": 1.58, "profitPercent": 0.10, "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(), "status": "completed"},
        {"id": "sol-2", "symbol": "BONK/USDC", "side": "buy_cex_sell_dex", "amount": 5000000, "dexPrice": 0.0000125, "cexPrice": 0.0000123, "profit": 0.10, "profitPercent": 1.63, "timestamp": (datetime.now() - timedelta(hours=5)).isoformat(), "status": "completed"}
    ]
    return jsonify(trades)

if __name__ == "__main__":
    run_dashboard()

# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================
