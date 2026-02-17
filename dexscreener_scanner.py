#!/usr/bin/env python3
"""
DEXScreener Arbitrage Scanner
Finds price discrepancies between DEXs and CEXs
"""

import requests
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import time

@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    profit_potential: float
    timestamp: str
    confidence: str  # HIGH, MEDIUM, LOW
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'buy_exchange': self.buy_exchange,
            'sell_exchange': self.sell_exchange,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'spread_percent': self.spread_percent,
            'profit_potential': self.profit_potential,
            'timestamp': self.timestamp,
            'confidence': self.confidence
        }

class DEXScreenerScanner:
    """
    Scan DEXScreener for arbitrage opportunities
    """
    
    DEXSCREENER_API = "https://api.dexscreener.com/latest"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.last_scan = []
    
    def get_token_pairs(self, token_address: str) -> List[Dict]:
        """Get all DEX pairs for a token"""
        try:
            url = f"{self.DEXSCREENER_API}/dex/tokens/{token_address}"
            resp = self.session.get(url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get('pairs', [])
            return []
        except Exception as e:
            print(f"[DEXScreener] Error fetching pairs: {e}")
            return []
    
    def search_pairs(self, query: str) -> List[Dict]:
        """Search for trading pairs"""
        try:
            url = f"{self.DEXSCREENER_API}/dex/search"
            resp = self.session.get(url, params={'q': query}, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get('pairs', [])
            return []
        except Exception as e:
            print(f"[DEXScreener] Error searching: {e}")
            return []
    
    def scan_arbitrage(self, symbols: List[str], cex_prices: Dict[str, Dict]) -> List[ArbitrageOpportunity]:
        """
        Scan for arbitrage between DEXs and CEXs
        
        Args:
            symbols: List of symbols to scan (e.g., ['BTC', 'ETH', 'SOL'])
            cex_prices: Current CEX prices {symbol: {exchange: price}}
        
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        
        for symbol in symbols:
            try:
                # Search for this symbol on DEXs
                dex_pairs = self.search_pairs(f"{symbol} USDC")
                
                if not dex_pairs:
                    continue
                
                # Get best DEX price
                best_dex_buy = None
                best_dex_sell = None
                
                for pair in dex_pairs[:5]:  # Top 5 pairs
                    price = float(pair.get('priceUsd', 0))
                    dex = pair.get('dexId', 'Unknown')
                    volume = float(pair.get('volume', {}).get('h24', 0))
                    
                    # Skip low volume
                    if volume < 10000:  # Less than $10k volume
                        continue
                    
                    if price > 0:
                        if not best_dex_buy or price < best_dex_buy['price']:
                            best_dex_buy = {'price': price, 'dex': dex, 'pair': pair}
                        if not best_dex_sell or price > best_dex_sell['price']:
                            best_dex_sell = {'price': price, 'dex': dex, 'pair': pair}
                
                # Compare with CEX prices
                if symbol in cex_prices:
                    cex_data = cex_prices[symbol]
                    
                    for cex_name, cex_price in cex_data.items():
                        if cex_price <= 0:
                            continue
                        
                        # Opportunity 1: Buy on DEX, Sell on CEX
                        if best_dex_buy:
                            spread = (cex_price - best_dex_buy['price']) / best_dex_buy['price'] * 100
                            if spread > 0.3:  # Minimum 0.3% spread
                                opportunities.append(ArbitrageOpportunity(
                                    symbol=symbol,
                                    buy_exchange=f"{best_dex_buy['dex']} (DEX)",
                                    sell_exchange=cex_name,
                                    buy_price=best_dex_buy['price'],
                                    sell_price=cex_price,
                                    spread_percent=spread,
                                    profit_potential=spread - 0.2,  # Approximate after fees
                                    timestamp=datetime.now().isoformat(),
                                    confidence='HIGH' if spread > 1.0 else 'MEDIUM'
                                ))
                        
                        # Opportunity 2: Buy on CEX, Sell on DEX
                        if best_dex_sell:
                            spread = (best_dex_sell['price'] - cex_price) / cex_price * 100
                            if spread > 0.3:
                                opportunities.append(ArbitrageOpportunity(
                                    symbol=symbol,
                                    buy_exchange=cex_name,
                                    sell_exchange=f"{best_dex_sell['dex']} (DEX)",
                                    buy_price=cex_price,
                                    sell_price=best_dex_sell['price'],
                                    spread_percent=spread,
                                    profit_potential=spread - 0.2,
                                    timestamp=datetime.now().isoformat(),
                                    confidence='HIGH' if spread > 1.0 else 'MEDIUM'
                                ))
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"[DEXScreener] Error scanning {symbol}: {e}")
                continue
        
        # Sort by profit potential
        opportunities.sort(key=lambda x: x.profit_potential, reverse=True)
        self.last_scan = opportunities
        return opportunities
    
    def get_solana_opportunities(self) -> List[ArbitrageOpportunity]:
        """Get Solana DEX arbitrage opportunities"""
        opportunities = []
        
        try:
            # Scan top Solana pairs
            solana_tokens = [
                'SOL', 'BONK', 'JUP', 'RAY', 'ORCA', 
                'SAMO', 'MSOL', 'BSOL', 'JITO'
            ]
            
            for token in solana_tokens:
                pairs = self.search_pairs(f"{token} SOL")
                
                # Find price discrepancies between Raydium, Orca, Jupiter
                raydium_price = None
                orca_price = None
                
                for pair in pairs:
                    dex = pair.get('dexId', '').lower()
                    price = float(pair.get('priceUsd', 0))
                    
                    if price <= 0:
                        continue
                    
                    if 'raydium' in dex:
                        raydium_price = price
                    elif 'orca' in dex:
                        orca_price = price
                
                # Check for arb between DEXs
                if raydium_price and orca_price:
                    spread = abs(raydium_price - orca_price) / min(raydium_price, orca_price) * 100
                    if spread > 0.5:
                        opportunities.append(ArbitrageOpportunity(
                            symbol=f"{token}/SOL",
                            buy_exchange='Raydium' if raydium_price < orca_price else 'Orca',
                            sell_exchange='Orca' if raydium_price < orca_price else 'Raydium',
                            buy_price=min(raydium_price, orca_price),
                            sell_price=max(raydium_price, orca_price),
                            spread_percent=spread,
                            profit_potential=spread - 0.3,
                            timestamp=datetime.now().isoformat(),
                            confidence='MEDIUM'
                        ))
                
                time.sleep(0.3)
        
        except Exception as e:
            print(f"[DEXScreener] Solana scan error: {e}")
        
        return opportunities
    
    def print_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Pretty print opportunities"""
        if not opportunities:
            print("\n🔍 No arbitrage opportunities found.")
            return
        
        print("\n" + "=" * 80)
        print("🎯 ARBITRAGE OPPORTUNITIES FOUND")
        print("=" * 80)
        
        for i, opp in enumerate(opportunities[:10], 1):
            conf_emoji = "🟢" if opp.confidence == 'HIGH' else "🟡" if opp.confidence == 'MEDIUM' else "🔴"
            print(f"\n{i}. {conf_emoji} {opp.symbol}")
            print(f"   Buy:  {opp.buy_exchange:<20} @ ${opp.buy_price:,.4f}")
            print(f"   Sell: {opp.sell_exchange:<20} @ ${opp.sell_price:,.4f}")
            print(f"   Spread: {opp.spread_percent:.2f}% | Est. Profit: {opp.profit_potential:.2f}%")
            print(f"   Time: {opp.timestamp[11:19]}")
        
        print("\n" + "=" * 80)

# Global instance
_scanner = None

def get_scanner():
    global _scanner
    if _scanner is None:
        _scanner = DEXScreenerScanner()
    return _scanner

if __name__ == "__main__":
    scanner = DEXScreenerScanner()
    
    # Example: Scan with mock CEX prices
    mock_cex = {
        'SOL': {'Binance': 145.20, 'Kraken': 145.35},
        'BONK': {'Binance': 0.000012, 'Kraken': 0.0000118},
    }
    
    print("🔍 Scanning for arbitrage opportunities...")
    opps = scanner.scan_arbitrage(['SOL', 'BONK', 'JUP'], mock_cex)
    scanner.print_opportunities(opps)
