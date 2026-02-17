#!/usr/bin/env python3
"""
Web Dashboard - Real-time Trading Bot Monitor
Simple web interface to view trades, positions, and performance
"""

import json
import os
from datetime import datetime, timezone
from flask import Flask, render_template_string, jsonify
from threading import Thread
import time

app = Flask(__name__)

# Global state (in production, use a proper database)
dashboard_state = {
    "prices": [],
    "trades": [],
    "positions": [],
    "stats": {
        "total_cycles": 0,
        "successful_trades": 0,
        "total_pnl": 0.0,
        "daily_pnl": 0.0,
        "avg_latency": 0.0
    },
    "last_update": None
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Bot Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-card h3 {
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
        }
        .positive { color: #4ade80; }
        .negative { color: #f87171; }
        .neutral { color: #fbbf24; }
        .section {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .section h2 {
            margin-bottom: 15px;
            font-size: 1.3em;
            border-bottom: 2px solid rgba(255,255,255,0.2);
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th {
            font-weight: 600;
            opacity: 0.8;
        }
        tr:hover {
            background: rgba(255,255,255,0.05);
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .badge-success { background: #4ade80; color: #000; }
        .badge-warning { background: #fbbf24; color: #000; }
        .badge-danger { background: #f87171; color: #000; }
        .price-ticker {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 15px;
        }
        .price-item {
            text-align: center;
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            min-width: 150px;
        }
        .price-item h4 {
            opacity: 0.8;
            margin-bottom: 5px;
        }
        .price-item .price {
            font-size: 1.5em;
            font-weight: bold;
        }
        .status-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0,0,0,0.8);
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-online { background: #4ade80; }
        .status-offline { background: #f87171; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .updating {
            animation: pulse 1s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Trading Bot Dashboard</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Cycles</h3>
                <div class="value neutral">{{ stats.total_cycles }}</div>
            </div>
            <div class="stat-card">
                <h3>Successful Trades</h3>
                <div class="value positive">{{ stats.successful_trades }}</div>
            </div>
            <div class="stat-card">
                <h3>Total P&L</h3>
                <div class="value {% if stats.total_pnl >= 0 %}positive{% else %}negative{% endif %}">
                    ${{ "%.2f"|format(stats.total_pnl) }}
                </div>
            </div>
            <div class="stat-card">
                <h3>Daily P&L</h3>
                <div class="value {% if stats.daily_pnl >= 0 %}positive{% else %}negative{% endif %}">
                    ${{ "%.2f"|format(stats.daily_pnl) }}
                </div>
            </div>
            <div class="stat-card">
                <h3>Avg Latency</h3>
                <div class="value neutral">{{ "%.1f"|format(stats.avg_latency) }}ms</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Live Prices</h2>
            <div class="price-ticker">
                {% for price in prices %}
                <div class="price-item">
                    <h4>{{ price.exchange }}</h4>
                    <div class="price">${{ "%.2f"|format(price.price) }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="section">
            <h2>💼 Open Positions</h2>
            {% if positions %}
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Exchange</th>
                        <th>Side</th>
                        <th>Entry Price</th>
                        <th>Quantity</th>
                        <th>Stop Loss</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody>
                    {% for pos in positions %}
                    <tr>
                        <td>{{ pos.position_id }}</td>
                        <td>{{ pos.exchange }}</td>
                        <td>{{ pos.side }}</td>
                        <td>${{ "%.2f"|format(pos.entry_price) }}</td>
                        <td>{{ "%.4f"|format(pos.quantity) }} BTC</td>
                        <td>${{ "%.2f"|format(pos.stop_loss_price) }}</td>
                        <td class="{% if pos.unrealized_pnl >= 0 %}positive{% else %}negative{% endif %}">
                            ${{ "%.2f"|format(pos.unrealized_pnl) }}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p style="opacity: 0.7; text-align: center; padding: 20px;">No open positions</p>
            {% endif %}
        </div>
        
        <div class="section">
            <h2>📝 Recent Trades</h2>
            {% if trades %}
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Time</th>
                        <th>Mode</th>
                        <th>Status</th>
                        <th>Buy</th>
                        <th>Sell</th>
                        <th>Quantity</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody>
                    {% for trade in trades %}
                    <tr>
                        <td>{{ trade.trade_id }}</td>
                        <td>{{ trade.timestamp[:19] }}</td>
                        <td>{{ trade.mode }}</td>
                        <td>
                            <span class="badge badge-{% if trade.status == 'FILLED' %}success{% elif trade.status == 'REJECTED' %}danger{% else %}warning{% endif %}">
                                {{ trade.status }}
                            </span>
                        </td>
                        <td>{{ trade.buy_exchange }}</td>
                        <td>{{ trade.sell_exchange }}</td>
                        <td>{{ "%.4f"|format(trade.quantity) }} BTC</td>
                        <td class="{% if trade.net_pnl and trade.net_pnl >= 0 %}positive{% else %}negative{% endif %}">
                            ${{ "%.2f"|format(trade.net_pnl or 0) }}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p style="opacity: 0.7; text-align: center; padding: 20px;">No trades yet</p>
            {% endif %}
        </div>
    </div>
    
    <div class="status-bar">
        <div>
            <span class="status-indicator status-online"></span>
            <span>Bot Online</span>
        </div>
        <div>
            Last Update: {{ last_update or 'Never' }}
        </div>
    </div>
    
    <script>
        // Auto-refresh every 5 seconds
        setInterval(() => {
            location.reload();
        }, 5000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template_string(HTML_TEMPLATE, **dashboard_state)


@app.route('/api/data')
def api_data():
    """API endpoint for JSON data."""
    return jsonify(dashboard_state)


def update_dashboard(prices=None, trades=None, positions=None, stats=None):
    """Update dashboard state from trading bot."""
    global dashboard_state
    
    if prices:
        dashboard_state["prices"] = prices
    if trades:
        dashboard_state["trades"] = trades[-20:]  # Keep last 20
    if positions:
        dashboard_state["positions"] = positions
    if stats:
        dashboard_state["stats"].update(stats)
    
    dashboard_state["last_update"] = datetime.now(timezone.utc).isoformat()


def run_dashboard(host='0.0.0.0', port=8080):
    """Run the dashboard server."""
    print(f"[Dashboard] Starting server on http://{host}:{port}")
    print(f"[Dashboard] Open your browser to view the dashboard")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Test mode - populate with sample data
    print("Dashboard - Test Mode")
    print("=" * 60)
    
    # Sample data
    update_dashboard(
        prices=[
            {"exchange": "Binance", "price": 68890.50},
            {"exchange": "Coinbase", "price": 68860.25},
            {"exchange": "Kraken", "price": 68875.00}
        ],
        trades=[
            {
                "trade_id": "TRADE_0001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": "PAPER",
                "status": "FILLED",
                "buy_exchange": "Binance",
                "sell_exchange": "Coinbase",
                "quantity": 0.01,
                "net_pnl": 12.50
            }
        ],
        positions=[
            {
                "position_id": "POS_0001",
                "exchange": "Binance",
                "side": "LONG",
                "entry_price": 68000,
                "quantity": 0.0074,
                "stop_loss_price": 66640,
                "unrealized_pnl": 65.80
            }
        ],
        stats={
            "total_cycles": 42,
            "successful_trades": 3,
            "total_pnl": 45.30,
            "daily_pnl": 12.50,
            "avg_latency": 245.5
        }
    )
    
    print("\nStarting dashboard server...")
    print("Open http://localhost:8080 in your browser\n")
    run_dashboard()
