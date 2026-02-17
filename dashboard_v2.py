#!/usr/bin/env python3
"""
Enhanced Dashboard with Performance Analytics
"""

from flask import Flask, render_template, jsonify, request
import json
import sqlite3
import os
from datetime import datetime, timedelta
from performance_analytics import get_analytics

app = Flask(__name__)

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect('trades.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_bot_data():
    """Get comprehensive bot data"""
    data = {
        "mode": "PAPER",
        "balance": 10000.0,
        "uptime": "Running",
        "prices": [],
        "positions": [],
        "trades": [],
        "analytics": {},
        "alerts": []
    }
    
    # Get analytics
    try:
        analytics = get_analytics()
        data['analytics'] = analytics.calculate_metrics(days=7)
        data['equity_curve'] = analytics.get_equity_curve(days=30)
    except Exception as e:
        data['analytics_error'] = str(e)
    
    # Get from database
    try:
        conn = get_db_connection()
        
        # Recent trades
        data['trades'] = [dict(row) for row in conn.execute(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 20"
        ).fetchall()]
        
        # Open positions
        data['positions'] = [dict(row) for row in conn.execute(
            "SELECT * FROM positions WHERE status='OPEN'"
        ).fetchall()]
        
        # Trade counts
        cursor = conn.execute("SELECT COUNT(*) FROM trades")
        data['total_trades'] = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM trades WHERE net_pnl > 0")
        data['winning_trades'] = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT SUM(net_pnl) FROM trades")
        result = cursor.fetchone()[0]
        data['total_pnl'] = result if result else 0.0
        
        conn.close()
    except Exception as e:
        data['db_error'] = str(e)
    
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            data['mode'] = config.get('bot', {}).get('mode', 'PAPER')
            data['config'] = config
    except:
        pass
    
    return data

@app.route('/')
def overview():
    """Main dashboard with analytics"""
    return render_template('dashboard_v2.html', data=get_bot_data())

@app.route('/analytics')
def analytics_page():
    """Detailed analytics page"""
    analytics = get_analytics()
    data = {
        'daily': analytics.calculate_metrics(days=1),
        'weekly': analytics.calculate_metrics(days=7),
        'monthly': analytics.calculate_metrics(days=30),
        'equity_curve': analytics.get_equity_curve(days=30)
    }
    return render_template('analytics.html', data=data)

@app.route('/api/stats')
def api_stats():
    """API endpoint for stats"""
    analytics = get_analytics()
    return jsonify(analytics.calculate_metrics(days=7))

@app.route('/api/equity')
def api_equity():
    """API endpoint for equity curve"""
    analytics = get_analytics()
    return jsonify(analytics.get_equity_curve(days=30))

@app.route('/api/recent_trades')
def api_recent_trades():
    """Get recent trades"""
    conn = get_db_connection()
    trades = [dict(row) for row in conn.execute(
        "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10"
    ).fetchall()]
    conn.close()
    return jsonify(trades)

if __name__ == '__main__':
    print("[Dashboard v2] Starting on http://0.0.0.0:8081")
    app.run(host='0.0.0.0', port=8081, debug=False)
