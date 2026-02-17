#!/usr/bin/env python3
"""
Import trades from JSON log to database
"""

import json
import sqlite3
from datetime import datetime

def import_from_log():
    log_file = "trading_bot.log"
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("[Import] No log file found")
        return 0
    
    conn = sqlite3.connect('trades.db')
    cursor = conn.cursor()
    
    imported = 0
    for line in lines:
        try:
            entry = json.loads(line.strip())
            
            # Only import trade entries
            if entry.get('type') == 'TRADE' or entry.get('type') == 'TRADE_EXECUTED':
                data = entry.get('data', {})
                
                cursor.execute('''
                    INSERT OR IGNORE INTO trades 
                    (trade_id, timestamp, symbol, side, exchange, entry_price, 
                     quantity, pnl, fees, net_pnl, status, mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('trade_id', f"IMPORT_{imported}"),
                    entry.get('timestamp'),
                    data.get('symbol', 'BTCUSDT'),
                    data.get('side'),
                    data.get('exchange'),
                    data.get('entry_price'),
                    data.get('quantity'),
                    data.get('pnl'),
                    data.get('fees', 0),
                    data.get('net_pnl'),
                    data.get('status', 'CLOSED'),
                    data.get('mode', 'PAPER')
                ))
                imported += 1
                
        except json.JSONDecodeError:
            continue
        except Exception as e:
            print(f"[Import] Error: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"[Import] Imported {imported} trades from log")
    return imported

if __name__ == "__main__":
    import_from_log()
