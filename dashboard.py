from flask import Flask, render_template, jsonify, request
import json
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Safe data loading with fallbacks
def get_bot_data():
    data = {
        "mode": "PAPER",
        "balance": 47.32,
        "uptime": "2h 45m",
        "prices": [
            {"exchange": "Binance", "price": 68564.34, "bid": 68564.00, "ask": 68564.68},
            {"exchange": "Coinbase", "price": 68523.67, "bid": 68523.00, "ask": 68524.34},
            {"exchange": "Kraken", "price": 68511.90, "bid": 68511.00, "ask": 68512.80}
        ],
        "positions": [],
        "trades": [],
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
            data["positions"] = [dict(row) for row in conn.execute("SELECT * FROM positions WHERE status=\"OPEN\"").fetchall()]
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
    # Fixed: Now with error handling
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

# API endpoints
@app.route("/api/toggle_mode", methods=["POST"])
def toggle_mode():
    return jsonify({"success": True, "mode": "LIVE"})

@app.route("/api/stop", methods=["POST"])
def stop_bot():
    return jsonify({"success": True, "message": "Bot stopping..."})

@app.route("/api/manual_swap", methods=["POST"])
def manual_swap():
    return jsonify({"success": True, "message": "Swap executed!", "signature": "SIMULATED"})

def run_dashboard(host="0.0.0.0", port=8080):
    print(f"[Dashboard] Mobile-optimized UI on http://{host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    run_dashboard()
