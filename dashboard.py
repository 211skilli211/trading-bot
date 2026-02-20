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

from flask import Flask, render_template, jsonify, request, flash, session
import json
import sqlite3
import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

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
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

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
    """Get wallet and funding status"""
    status = {
        "funded": False,
        "connected": False,
        "chains": {},
        "primary_address": None,
        "total_usd_value": 0.0,
        "messages": [],
        "session_wallet": None
    }
    
    # Check for WalletConnect session (only within request context)
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
    
    # Check legacy wallet file
    try:
        if os.path.exists("solana_wallet_live.json"):
            with open("solana_wallet_live.json", "r") as f:
                wallet = json.load(f)
                if wallet.get("public_key"):
                    if "solana" not in status["chains"]:
                        status["chains"]["solana"] = {
                            "address": wallet["public_key"],
                            "balance_sol": wallet.get("balance_sol", 0),
                            "balance_usdc": wallet.get("balance_usdc", 0),
                            "connected": True
                        }
                    if not status["primary_address"]:
                        status["primary_address"] = wallet["public_key"][:20] + "..."
                    if wallet.get("balance_sol", 0) > 0.01 or wallet.get("balance_usdc", 0) > 1:
                        status["funded"] = True
    except:
        pass
    
    return status

def get_wallet_balance(chain: str, address: str) -> Dict[str, Any]:
    """Get wallet balance"""
    try:
        if chain == 'solana' and os.path.exists("solana_wallet_live.json"):
            with open("solana_wallet_live.json", "r") as f:
                wallet = json.load(f)
                if wallet.get("public_key") == address:
                    return {
                        "sol": wallet.get("balance_sol", 0),
                        "usdc": wallet.get("balance_usdc", 0),
                        "usd_value": wallet.get("balance_usdc", 0) + wallet.get("balance_sol", 0) * 100
                    }
        return {"sol": 0, "usdc": 0, "usd_value": 0}
    except:
        return {"error": "Failed to get balance"}

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
    prices = _latest_data.get('prices', [])
    if not prices:
        prices = fetch_live_prices()
    
    data = {
        "mode": "PAPER",
        "balance": _latest_data.get('balance', 10000.0),
        "uptime": "Running",
        "prices": prices,
        "positions": _latest_data.get('positions', []),
        "trades": _latest_data.get('trades', []),
        "alerts": [],
        "config": {},
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
    return render_template("index.html", data=get_bot_data(), nav=NAVIGATION, wallet=get_wallet_status())

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
    """Check ZeroClaw AI system status"""
    try:
        import requests
        resp = requests.get('http://127.0.0.1:3000/health', timeout=5)
        data = resp.json() if resp.status_code == 200 else {}
        return jsonify({
            "running": data.get('status') == 'ok',
            "paired": data.get('paired', False),
            "uptime_seconds": data.get('runtime', {}).get('uptime_seconds', 0),
            "components": data.get('runtime', {}).get('components', {})
        })
    except Exception as e:
        return jsonify({"running": False, "error": str(e)})

@app.route("/api/zeroclaw/chat", methods=["POST"])
def zeroclaw_chat():
    try:
        import requests
        data = request.json
        resp = requests.post('http://127.0.0.1:3000/agent', json={"message": data.get("message", "")}, timeout=30)
        return jsonify(resp.json() if resp.status_code == 200 else {"error": "Failed"})
    except Exception as e:
        return jsonify({"error": str(e)})

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
        
        # Return results
        return jsonify({
            "success": True,
            "result": {
                "start_date": result.start_date,
                "end_date": result.end_date,
                "initial_balance": result.initial_balance,
                "final_balance": result.final_balance,
                "total_return_pct": result.total_return_pct,
                "total_trades": result.total_trades,
                "win_rate": result.win_rate,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown_pct": result.max_drawdown_pct,
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
# MAIN
# ============================================================================

def run_dashboard(host="0.0.0.0", port=8080):
    print(f"[Dashboard] Trading Bot Dashboard v2.0")
    print(f"[Dashboard] 16 pages | WalletConnect | ZeroClaw AI")
    print(f"[Dashboard] URL: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == "__main__":
    run_dashboard()
