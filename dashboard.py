#!/usr/bin/env python3
"""
Professional Web Dashboard for Trading Bot
Modern dark UI with real-time updates
"""

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, jsonify, request
from threading import Thread
import time

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Global state
dashboard_data = {
    "mode": "paper",
    "balance": 10000.0,
    "uptime": "0h 0m",
    "cycle_count": 0,
    "total_pnl": 0.0,
    "win_rate": 0.0,
    "max_drawdown": 0.0,
    "exposure": 0.0,
    "total_trades": 0,
    "winning_trades": 0,
    "prices": [],
    "positions": [],
    "recent_trades": [],
    "chart_labels": [],
    "chart_data": []
}


def load_data_from_db():
    """Load trading data from SQLite database."""
    db_path = "trades.db"
    
    if not os.path.exists(db_path):
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get recent trades
        cursor.execute("""
            SELECT * FROM trades 
            ORDER BY timestamp DESC 
            LIMIT 20
        """)
        dashboard_data["recent_trades"] = [dict(row) for row in cursor.fetchall()]
        
        # Get open positions
        cursor.execute("""
            SELECT * FROM positions 
            WHERE status = 'OPEN'
            ORDER BY timestamp DESC
        """)
        dashboard_data["positions"] = [dict(row) for row in cursor.fetchall()]
        
        # Calculate stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(net_pnl) as total_pnl
            FROM trades
            WHERE timestamp > datetime('now', '-7 days')
        """)
        stats = cursor.fetchone()
        
        if stats:
            dashboard_data["total_trades"] = stats["total"] or 0
            dashboard_data["winning_trades"] = stats["wins"] or 0
            dashboard_data["total_pnl"] = stats["total_pnl"] or 0.0
            dashboard_data["win_rate"] = (
                (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
        
        # Calculate exposure
        exposure = sum(
            pos["quantity"] * pos["entry_price"] 
            for pos in dashboard_data["positions"]
        )
        dashboard_data["exposure"] = exposure
        
        conn.close()
        
    except Exception as e:
        print(f"[Dashboard] DB error: {e}")


def load_config():
    """Load bot configuration."""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            dashboard_data["mode"] = config.get("bot", {}).get("mode", "paper")
    except:
        pass


def generate_chart_data():
    """Generate sample chart data (replace with real data)."""
    labels = []
    data = []
    
    for i in range(7):
        date = datetime.now() - timedelta(days=6-i)
        labels.append(date.strftime("%m/%d"))
        # Simulate equity curve
        data.append(10000 + (i * 10) + (i * i * 2))
    
    dashboard_data["chart_labels"] = labels
    dashboard_data["chart_data"] = data


@app.route("/")
def index():
    """Main dashboard page."""
    load_data_from_db()
    load_config()
    generate_chart_data()
    
    return render_template(
        "index.html",
        data=dashboard_data,
        mode=dashboard_data["mode"],
        balance=dashboard_data["balance"],
        cycle_count=dashboard_data["cycle_count"],
        uptime=dashboard_data["uptime"],
        active_page="overview"
    )


@app.route("/prices")
def prices():
    """Live prices page."""
    return render_template(
        "index.html",
        data=dashboard_data,
        mode=dashboard_data["mode"],
        balance=dashboard_data["balance"],
        cycle_count=dashboard_data["cycle_count"],
        uptime=dashboard_data["uptime"],
        active_page="prices"
    )


@app.route("/positions")
def positions():
    """Open positions page."""
    load_data_from_db()
    return render_template(
        "index.html",
        data=dashboard_data,
        mode=dashboard_data["mode"],
        balance=dashboard_data["balance"],
        cycle_count=dashboard_data["cycle_count"],
        uptime=dashboard_data["uptime"],
        active_page="positions"
    )


@app.route("/trades")
def trades():
    """Trade history page."""
    load_data_from_db()
    return render_template(
        "index.html",
        data=dashboard_data,
        mode=dashboard_data["mode"],
        balance=dashboard_data["balance"],
        cycle_count=dashboard_data["cycle_count"],
        uptime=dashboard_data["uptime"],
        active_page="trades"
    )


@app.route("/solana")
def solana():
    """Solana DEX page."""
    return render_template(
        "index.html",
        data=dashboard_data,
        mode=dashboard_data["mode"],
        balance=dashboard_data["balance"],
        cycle_count=dashboard_data["cycle_count"],
        uptime=dashboard_data["uptime"],
        active_page="solana"
    )


@app.route("/config")
def config_page():
    """Configuration page."""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except:
        config = {}
    
    return render_template(
        "index.html",
        data=dashboard_data,
        config=config,
        mode=dashboard_data["mode"],
        balance=dashboard_data["balance"],
        cycle_count=dashboard_data["cycle_count"],
        uptime=dashboard_data["uptime"],
        active_page="config"
    )


@app.route("/alerts")
def alerts():
    """Alerts page."""
    return render_template(
        "index.html",
        data=dashboard_data,
        mode=dashboard_data["mode"],
        balance=dashboard_data["balance"],
        cycle_count=dashboard_data["cycle_count"],
        uptime=dashboard_data["uptime"],
        active_page="alerts"
    )


# API Endpoints
@app.route("/api/data")
def api_data():
    """JSON API for data."""
    load_data_from_db()
    return jsonify(dashboard_data)


@app.route("/api/config", methods=["POST"])
def api_config():
    """Update configuration."""
    try:
        new_config = request.json
        with open("config.json", "w") as f:
            json.dump(new_config, f, indent=2)
        return jsonify({"success": True, "message": "Config saved"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/manual_swap", methods=["POST"])
def api_manual_swap():
    """Execute manual swap."""
    try:
        data = request.json
        # This would integrate with your solana_dex_full.py
        # For now, just return success
        return jsonify({
            "success": True,
            "signature": "MANUAL_SWAP_TEST",
            "message": f"Swap executed: {data.get('amount')} tokens"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/test_alert", methods=["POST"])
def api_test_alert():
    """Send test alert."""
    return jsonify({"success": True, "message": "Test alert sent!"})


@app.route("/api/close_position/<position_id>", methods=["POST"])
def api_close_position(position_id):
    """Close a position."""
    try:
        # This would integrate with your risk_manager.py
        return jsonify({"success": True, "message": f"Position {position_id} closed"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def run_dashboard(host='0.0.0.0', port=8080):
    """Run the dashboard server."""
    print(f"[Dashboard] Starting professional UI on http://{host}:{port}")
    print(f"[Dashboard] Templates: templates/")
    print(f"[Dashboard] Static: static/css/, static/js/")
    app.run(host=host, port=port, debug=False, use_reloader=False)


def update_dashboard_data(prices=None, trades=None, positions=None, stats=None):
    """Update dashboard data from trading bot."""
    global dashboard_data
    
    if prices:
        dashboard_data["prices"] = prices
    if trades:
        dashboard_data["recent_trades"] = trades[-20:]
    if positions:
        dashboard_data["positions"] = positions
    if stats:
        dashboard_data.update(stats)
    
    dashboard_data["cycle_count"] += 1
    dashboard_data["uptime"] = f"{dashboard_data['cycle_count'] * 60 // 3600}h {(dashboard_data['cycle_count'] * 60 % 3600) // 60}m"


if __name__ == "__main__":
    run_dashboard()
