#!/usr/bin/env python3
"""
Real-time Arbitrage Opportunity Finder - Production Ready
"""

import json
import os
from datetime import datetime
from typing import Dict, List
import ccxt

from dexscreener_scanner import get_scanner

class ArbitrageFinder:
    """Find and display all arbitrage opportunities"""
    
    def __init__(self):
        self.scanner = get_scanner()
        self.exchanges = {}
        self.load_exchanges()
    
    def load_exchanges(self):
        """Load exchange APIs"""
        with open('.env') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ[key] = val
        
        try:
            self.exchanges['binance'] = ccxt.binance({
                'apiKey': os.getenv('BINANCE_API_KEY'),
                'secret': os.getenv('BINANCE_SECRET'),
                'enableRateLimit': True,
            })
        except:
            pass
        
        try:
            self.exchanges['kraken'] = ccxt.kraken({
                'apiKey': os.getenv('KRAKEN_API_KEY'),
                'secret': os.getenv('KRAKEN_SECRET'),
                'enableRateLimit': True,
            })
        except:
            pass
    
    def get_cex_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get current prices from all CEXs"""
        prices = {}
        
        for symbol in symbols:
            prices[symbol] = {}
            
            for name, exchange in self.exchanges.items():
                try:
                    ticker = exchange.fetch_ticker(f"{symbol}/USDT")
                    prices[symbol][name] = ticker['last']
                except:
                    try:
                        ticker = exchange.fetch_ticker(f"{symbol}/USD")
                        prices[symbol][name] = ticker['last']
                    except:
                        pass
        
        return prices
    
    def find_cex_arbitrage(self, symbols: List[str]) -> List[Dict]:
        """Find CEX-to-CEX arbitrage opportunities"""
        opportunities = []
        prices = self.get_cex_prices(symbols)
        
        for symbol, exchange_prices in prices.items():
            if len(exchange_prices) < 2:
                continue
            
            min_ex = min(exchange_prices.items(), key=lambda x: x[1])
            max_ex = max(exchange_prices.items(), key=lambda x: x[1])
            
            spread = (max_ex[1] - min_ex[1]) / min_ex[1] * 100
            
            # Filter: minimum 0.15%, maximum 5% (filter out bad data)
            if 0.15 <= spread <= 5.0:
                opportunities.append({
                    'type': 'CEX-CEX',
                    'symbol': symbol,
                    'buy_exchange': min_ex[0].upper(),
                    'sell_exchange': max_ex[0].upper(),
                    'buy_price': min_ex[1],
                    'sell_price': max_ex[1],
                    'spread_percent': spread,
                    'profit_after_fees': max(0, spread - 0.15),
                    'action': f"BUY on {min_ex[0].upper()} → SELL on {max_ex[0].upper()}"
                })
        
        return sorted(opportunities, key=lambda x: x['spread_percent'], reverse=True)
    
    def print_report(self):
        """Print comprehensive arbitrage report"""
        symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA']
        
        print("\n🔍 Scanning CEX prices...")
        cex_opps = self.find_cex_arbitrage(symbols)
        
        print("\n" + "=" * 80)
        print("💰 LIVE ARBITRAGE OPPORTUNITIES")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        print("\n📊 CEX-TO-CEX OPPORTUNITIES:")
        print("-" * 80)
        
        if cex_opps:
            for opp in cex_opps:
                print(f"\n🟢 {opp['symbol']}")
                print(f"   {opp['action']}")
                print(f"   Buy:  ${opp['buy_price']:,.2f}")
                print(f"   Sell: ${opp['sell_price']:,.2f}")
                print(f"   Spread: {opp['spread_percent']:.3f}% | Net: {opp['profit_after_fees']:.3f}%")
        else:
            print("\n   No profitable opportunities (spreads < 0.15%)")
            print("   Tip: Market is efficient right now, try again in a few minutes")
        
        print("\n" + "=" * 80)
        print(f"📈 Total opportunities: {len(cex_opps)}")
        print("=" * 80)

if __name__ == "__main__":
    finder = ArbitrageFinder()
    finder.print_report()
