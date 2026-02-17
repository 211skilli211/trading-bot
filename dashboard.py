from flask import Flask, render_template, jsonify, request
import json
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Global variable to store latest data from trading bot
_latest_data = {
    'prices': [],
    'trades': [],
    'positions': [],
    'balance': 10000.0,
    'timestamp': None
}

def update_dashboard(prices=None, trades=None, positions=None, balance=None):
    """Update dashboard data from trading bot - called by trading_bot.py"""
    global _latest_data
    if prices is not None:
        _latest_data['prices'] = prices
    if trades is not None:
        _latest_data['trades'] = trades[-20:] if len(trades) > 20 else trades  # Keep last 20
    if positions is not None:
        _latest_data['positions'] = positions
    if balance is not None:
        _latest_data['balance'] = balance
    _latest_data['timestamp'] = datetime.now().isoformat()
    return True

def get_latest_data():
    """Get latest dashboard data"""
    return _latest_data

# Safe data loading with fallbacks
def get_bot_data():
    data = {
        "mode": "PAPER",
        "balance": _latest_data.get('balance', 10000.0),
        "uptime": "Running",
        "prices": _latest_data.get('prices', []),
        "positions": _latest_data.get('positions', []),
        "trades": _latest_data.get('trades', []),
        "alerts": [],
        "config": {},
        "solana_address": "Not connected",
        "sol_balance": 0.0,
        "usdt_balance": 0.0
    }
    
    # Try to load from database (graceful if does not exist)
    try:
        if os.path.exists("trades.db"):
            conn = sqlite3.connect("trades.db")
            conn.row_factory = sqlite3.Row
            data["trades"] = [dict(row) for row in conn.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 50").fetchall()]
            data["positions"] = [dict(row) for row in conn.execute("SELECT * FROM positions WHERE status='OPEN'").fetchall()]
            conn.close()
    except Exception as e:
        print(f"[Dashboard] DB warning: {e}")
        data["trades"] = []
        data["positions"] = []
    
    # Try to load config
    try:
        with open("config.json", "r") as f:
            data["config"] = json.load(f)
            data["mode"] = data["config"].get("bot", {}).get("mode", "PAPER")
    except:
        data["config"] = {"bot": {"mode": "PAPER"}, "strategy": {"min_spread": 0.5}}
    
    # Try to load Solana wallet
    try:
        if os.path.exists("solana_wallet_live.json"):
            with open("solana_wallet_live.json") as f:
                wallet = json.load(f)
                data["solana_address"] = wallet.get("public_key", "Not connected")[:20] + "..."
    except:
        pass
    
    return data

@app.route("/")
def index():
    return render_template("index.html", data=get_bot_data())

@app.route("/prices")
def prices():
    return render_template("prices.html", data=get_bot_data())

@app.route("/positions")
def positions():
    return render_template("positions.html", data=get_bot_data())

@app.route("/trades")
def trades():
    return render_template("trades.html", data=get_bot_data())

@app.route("/solana")
def solana():
    return render_template("solana.html", data=get_bot_data())

@app.route("/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        try:
            with open("config.json", "w") as f:
                json.dump(request.json, f, indent=2)
            return jsonify({"success": True, "message": "Config saved!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    return render_template("config.html", data=get_bot_data())

@app.route("/alerts")
def alerts():
    return render_template("alerts.html", data=get_bot_data())

@app.route("/api/data")
def api_data():
    """API endpoint for live data updates"""
    return jsonify(get_bot_data())

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
    return jsonify({"success": True, "message": "Stop signal sent (implement in trading loop)"})

@app.route("/api/manual_swap", methods=["POST"])
def manual_swap():
    data = request.json
    return jsonify({"success": True, "message": f"Manual swap requested: {data}"})

def run_dashboard(host="0.0.0.0", port=8080):
    print(f"[Dashboard] Mobile-optimized UI on http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == "__main__":
    run_dashboard()


@app.route("/dashboard_v2")
def dashboard_v2():
    """New unified dashboard"""
    return render_template("dashboard_v2.html", data=get_bot_data())
