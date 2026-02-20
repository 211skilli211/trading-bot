# Add this to dashboard.py

# Global variable to store latest data
_latest_data = {
    'prices': [],
    'trades': [],
    'positions': [],
    'balance': 10000.0,
    'timestamp': None
}

def update_dashboard(prices=None, trades=None, positions=None, balance=None):
    """Update dashboard data from trading bot"""
    global _latest_data
    if prices:
        _latest_data['prices'] = prices
    if trades:
        _latest_data['trades'] = trades
    if positions:
        _latest_data['positions'] = positions
    if balance:
        _latest_data['balance'] = balance
    _latest_data['timestamp'] = datetime.now().isoformat()
    return True

def get_latest_data():
    """Get latest dashboard data"""
    return _latest_data

# Modify get_bot_data to use latest data
def get_bot_data():
    """Get bot data with latest updates from trading loop"""
    data = {
        "mode": "PAPER",
        "balance": _latest_data.get('balance', 10000.0),
        "uptime": "Running",
        "prices": _latest_data.get('prices', []),
        "positions": _latest_data.get('positions', []),
        "trades": _latest_data.get('trades', []),
        "alerts": []
    }
    
    # Try to load from database
    try:
        if os.path.exists("trades.db"):
            conn = sqlite3.connect("trades.db")
            conn.row_factory = sqlite3.Row
            
            # Get recent trades
            data["trades"] = [dict(row) for row in conn.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10"
            ).fetchall()]
            
            # Get open positions
            data["positions"] = [dict(row) for row in conn.execute(
                "SELECT * FROM positions WHERE status='OPEN'"
            ).fetchall()]
            
            conn.close()
    except Exception as e:
        print(f"[Dashboard] DB warning: {e}")
    
    # Try to load config
    try:
        with open("config.json", "r") as f:
            cfg = json.load(f)
            data["mode"] = cfg.get("bot", {}).get("mode", "PAPER")
    except:
        pass
    
    return data
