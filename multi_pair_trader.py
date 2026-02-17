#!/usr/bin/env python3
"""
Multi-Pair Trading Integration
Trade multiple cryptocurrencies simultaneously
"""

import json
import os
from typing import List, Dict
from datetime import datetime
import ccxt

class MultiPairTrader:
    """Manage trading across multiple pairs"""
    
    def __init__(self):
        self.pairs = []
        self.exchanges = {}
        self.load_config()
        self.load_exchanges()
    
    def load_config(self):
        """Load multi-pair configuration"""
        try:
            with open('multi_pair_config.json') as f:
                config = json.load(f)
                self.pairs = config.get('trading_pairs', [])
                self.solana_pairs = config.get('solana_pairs', [])
        except:
            # Default config
            self.pairs = [
                {'symbol': 'BTC/USDT', 'enabled': True, 'min_spread': 0.15},
                {'symbol': 'ETH/USDT', 'enabled': True, 'min_spread': 0.12},
                {'symbol': 'SOL/USDT', 'enabled': True, 'min_spread': 0.18},
            ]
    
    def load_exchanges(self):
        """Load exchange connections"""
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
    
    def get_all_prices(self) -> Dict[str, Dict]:
        """Get prices for all enabled pairs"""
        prices = {}
        
        for pair_config in self.pairs:
            if not pair_config.get('enabled', False):
                continue
            
            symbol = pair_config['symbol']
            prices[symbol] = {}
            
            for name, exchange in self.exchanges.items():
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    prices[symbol][name] = {
                        'bid': ticker['bid'],
                        'ask': ticker['ask'],
                        'last': ticker['last']
                    }
                except:
                    pass
        
        return prices
    
    def scan_all_pairs(self) -> List[Dict]:
        """Scan all pairs for arbitrage"""
        opportunities = []
        prices = self.get_all_prices()
        
        for symbol, pair_config in zip(prices.keys(), self.pairs):
            exchange_prices = prices[symbol]
            
            if len(exchange_prices) < 2:
                continue
            
            # Find best buy and sell
            buy_ex = min(exchange_prices.items(), key=lambda x: x[1]['ask'])
            sell_ex = max(exchange_prices.items(), key=lambda x: x[1]['bid'])
            
            spread = (sell_ex[1]['bid'] - buy_ex[1]['ask']) / buy_ex[1]['ask'] * 100
            min_spread = pair_config.get('min_spread', 0.15)
            
            if spread >= min_spread:
                opportunities.append({
                    'symbol': symbol,
                    'buy_exchange': buy_ex[0].upper(),
                    'sell_exchange': sell_ex[0].upper(),
                    'buy_price': buy_ex[1]['ask'],
                    'sell_price': sell_ex[1]['bid'],
                    'spread': spread,
                    'min_required': min_spread,
                    'timestamp': datetime.now().isoformat()
                })
        
        return sorted(opportunities, key=lambda x: x['spread'], reverse=True)
    
    def print_status(self):
        """Print multi-pair trading status"""
        print("\n" + "=" * 70)
        print("📊 MULTI-PAIR TRADING STATUS")
        print("=" * 70)
        
        print("\nEnabled Pairs:")
        for pair in self.pairs:
            status = "🟢" if pair.get('enabled') else "🔴"
            print(f"   {status} {pair['symbol']:<12} Min Spread: {pair['min_spread']}%")
        
        print("\nScanning for opportunities...")
        opps = self.scan_all_pairs()
        
        if opps:
            print(f"\n🎯 {len(opps)} opportunities found:")
            for opp in opps:
                print(f"\n   {opp['symbol']}")
                print(f"   Buy:  {opp['buy_exchange']:<10} @ ${opp['buy_price']:,.2f}")
                print(f"   Sell: {opp['sell_exchange']:<10} @ ${opp['sell_price']:,.2f}")
                print(f"   Spread: {opp['spread']:.3f}%")
        else:
            print("\n   No opportunities above minimum spread thresholds")
        
        print("\n" + "=" * 70)

if __name__ == "__main__":
    trader = MultiPairTrader()
    trader.print_status()
