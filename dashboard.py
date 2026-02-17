from flask import Flask, render_template, jsonify, request
import json, sqlite3, os
from datetime import datetime
from threading import Thread

app = Flask(__name__, template_folder='templates', static_folder='static')

# Global sniper instance (initialized on first use)
sniper_instance = None
sniper_thread = None

def get_bot_data():
    """Get bot data with safe fallbacks"""
    data = {
        "mode": "PAPER",
        "balance": 47.32,
        "uptime": "3h 12m",
        "prices": {"Binance": 68564.34, "Coinbase": 68523.67, "Kraken": 68511.90},
        "spread": 0.076,
        "positions": [],
        "trades": [],
        "alerts": [],
        "config": {},
        "solana_balance": 20.45,
        "usdt_balance": 47.32,
        "kpis": {
            "pnl": "+0.00",
            "winrate": "0%",
            "exposure": "0%"
        }
    }
    
    # Try to load from database
    try:
        if os.path.exists("trades.db"):
            conn = sqlite3.connect("trades.db")
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT timestamp, action, amount, price, pnl, status "
                "FROM trades ORDER BY timestamp DESC LIMIT 50"
            ).fetchall()
            data["trades"] = [tuple(row) for row in rows]
            
            # Load positions
            pos_rows = conn.execute(
                "SELECT * FROM positions WHERE status='OPEN'"
            ).fetchall()
            data["positions"] = [dict(row) for row in pos_rows]
            conn.close()
    except Exception as e:
        print(f"[Dashboard] DB warning: {e}")
    
    # Try to load config
    try:
        with open("config.json", "r") as f:
            cfg = json.load(f)
            data["config"] = cfg
            data["mode"] = cfg.get("bot", {}).get("mode", "PAPER")
    except Exception as e:
        data["config"] = {
            "bot": {"mode": "PAPER"},
            "strategy": {"min_spread": 0.1}
        }
    
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
            return jsonify({"status": "saved", "message": "Config saved!"})
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)})
    return render_template("config.html", data=get_bot_data())

@app.route("/alerts")
def alerts():
    return render_template("alerts.html", data=get_bot_data())

# API endpoints
@app.route("/api/set_mode", methods=["POST"])
def set_mode():
    try:
        req = request.get_json()
        mode = req.get("mode", "PAPER")
        
        # Load current config
        cfg = {}
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                cfg = json.load(f)
        
        # Update mode
        if "bot" not in cfg:
            cfg["bot"] = {}
        cfg["bot"]["mode"] = mode
        
        with open("config.json", "w") as f:
            json.dump(cfg, f, indent=2)
        
        return jsonify({"status": "ok", "mode": mode})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/api/stop", methods=["POST"])
def stop_bot():
    # Signal file for bot to check
    try:
        with open("bot.stop", "w") as f:
            f.write("stop")
        return jsonify({"status": "ok", "message": "Bot stopping..."})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/api/manual_swap", methods=["POST"])
def manual_swap():
    try:
        req = request.get_json()
        input_token = req.get("input", "USDT")
        output_token = req.get("output", "SOL")
        amount = req.get("amount", 10)
        
        # Here you would integrate with your Jupiter swap code
        return jsonify({
            "status": "pending",
            "message": f"Swap {amount} {input_token} → {output_token} queued",
            "input": input_token,
            "output": output_token,
            "amount": amount
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/api/status")
def api_status():
    return jsonify(get_bot_data())

# DEXScreener Sniper API endpoints
@app.route("/api/sniper/start", methods=["POST"])
def sniper_start():
    global sniper_instance, sniper_thread
    
    try:
        req = request.get_json() or {}
        
        # Import sniper module
        try:
            from dexscreener_connector import DexScreenerSniper
        except ImportError as e:
            return jsonify({"status": "error", "error": f"DEXScreener module not available: {e}"})
        
        # Stop existing sniper if running
        if sniper_instance and sniper_instance.running:
            sniper_instance.stop()
        
        # Create new sniper instance
        sniper_instance = DexScreenerSniper(
            min_liquidity=req.get("min_liquidity", 8000),
            min_score=req.get("min_score", 75),
            dry_run=req.get("dry_run", True),
            poll_interval=10
        )
        
        # Start in background thread
        sniper_thread = Thread(target=sniper_instance.start_monitoring, daemon=True)
        sniper_thread.start()
        
        mode = "DRY RUN" if req.get("dry_run", True) else "LIVE"
        return jsonify({
            "status": "ok",
            "message": f"Sniper started in {mode} mode",
            "config": {
                "min_liquidity": sniper_instance.min_liquidity,
                "min_score": sniper_instance.min_score,
                "dry_run": sniper_instance.dry_run
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/api/sniper/stop", methods=["POST"])
def sniper_stop():
    global sniper_instance
    
    try:
        if sniper_instance:
            sniper_instance.stop()
            return jsonify({"status": "ok", "message": "Sniper stopped"})
        else:
            return jsonify({"status": "ok", "message": "Sniper was not running"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/api/sniper/status")
def sniper_status():
    global sniper_instance
    
    try:
        if sniper_instance:
            stats = sniper_instance.get_stats()
            return jsonify({
                "status": "ok",
                "running": stats.get("running", False),
                "stats": stats
            })
        else:
            return jsonify({
                "status": "ok",
                "running": False,
                "message": "Sniper not initialized"
            })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

def run_dashboard(host="0.0.0.0", port=8080):
    print(f"[Dashboard] Mobile-optimized UI on http://{host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    run_dashboard()
