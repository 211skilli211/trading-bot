"""
Arbitrage Scan Skill Handler
Scans for arbitrage opportunities across exchanges
"""
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from zeroclaw_venom.core.skill import SkillResult

@dataclass
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_pct: float
    profit_potential: float  # After fees
    volume_24h: float
    confidence: str  # HIGH, MEDIUM, LOW

def get_mock_prices(symbol: str) -> Dict[str, float]:
    """Get mock prices for different exchanges (replace with real API calls)"""
    base_prices = {
        "BTC-USD": 45000.0,
        "ETH-USD": 3200.0,
        "SOL-USD": 105.0,
        "ADA-USD": 0.55,
        "DOT-USD": 7.20,
    }
    base = base_prices.get(symbol, 100.0)
    
    return {
        "binance": base * (1 + (hash(symbol + "binance") % 10 - 5) / 1000),
        "coinbase": base * (1 + (hash(symbol + "coinbase") % 10 - 5) / 1000),
        "kraken": base * (1 + (hash(symbol + "kraken") % 10 - 5) / 1000),
        "bybit": base * (1 + (hash(symbol + "bybit") % 10 - 5) / 1000),
    }

def calculate_arbitrage(
    symbol: str, 
    prices: Dict[str, float],
    min_spread: float = 0.5
) -> List[ArbitrageOpportunity]:
    """Calculate arbitrage opportunities between exchanges"""
    opportunities = []
    exchanges = list(prices.keys())
    
    # Trading fees per exchange (approximate)
    fees = {
        "binance": 0.001,  # 0.1%
        "coinbase": 0.005,  # 0.5%
        "kraken": 0.0026,  # 0.26%
        "bybit": 0.001,  # 0.1%
    }
    
    # Mock 24h volumes
    volumes = {
        "BTC-USD": 25000000000,
        "ETH-USD": 15000000000,
        "SOL-USD": 2000000000,
        "ADA-USD": 500000000,
        "DOT-USD": 300000000,
    }
    
    for i, buy_ex in enumerate(exchanges):
        for sell_ex in exchanges[i+1:]:
            buy_price = prices[buy_ex]
            sell_price = prices[sell_ex]
            
            # Check if arbitrage exists (buy low, sell high)
            if sell_price > buy_price:
                spread = ((sell_price - buy_price) / buy_price) * 100
                
                if spread >= min_spread:
                    # Calculate profit after fees
                    total_fee = fees.get(buy_ex, 0.001) + fees.get(sell_ex, 0.001)
                    profit_after_fees = spread - (total_fee * 100)
                    
                    # Determine confidence based on spread and volume
                    volume = volumes.get(symbol, 1000000)
                    if spread > 2.0 and volume > 1000000000:
                        confidence = "HIGH"
                    elif spread > 1.0 and volume > 500000000:
                        confidence = "MEDIUM"
                    else:
                        confidence = "LOW"
                    
                    opportunities.append(ArbitrageOpportunity(
                        symbol=symbol,
                        buy_exchange=buy_ex,
                        sell_exchange=sell_ex,
                        buy_price=buy_price,
                        sell_price=sell_price,
                        spread_pct=spread,
                        profit_potential=profit_after_fees,
                        volume_24h=volume,
                        confidence=confidence
                    ))
    
    return sorted(opportunities, key=lambda x: x.spread_pct, reverse=True)

def handle(skill_input: Dict[str, Any], context: Any) -> SkillResult:
    """
    Scan for arbitrage opportunities across exchanges
    
    Expected skill_input:
    {
        "symbol": "BTC-USD",  # optional, scan specific symbol
        "min_spread": 0.5,    # optional, minimum spread % (default 0.5)
        "top_n": 5            # optional, number of opportunities to return
    }
    """
    symbol = skill_input.get("symbol")
    min_spread = skill_input.get("min_spread", 0.5)
    top_n = skill_input.get("top_n", 5)
    
    # Symbols to scan
    if symbol:
        symbols = [symbol.upper()]
    else:
        symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "DOT-USD"]
    
    all_opportunities: List[ArbitrageOpportunity] = []
    
    for sym in symbols:
        prices = get_mock_prices(sym)
        opportunities = calculate_arbitrage(sym, prices, min_spread)
        all_opportunities.extend(opportunities)
    
    # Sort by spread and take top N
    all_opportunities.sort(key=lambda x: x.spread_pct, reverse=True)
    top_opportunities = all_opportunities[:top_n]
    
    if not top_opportunities:
        return SkillResult(
            success=True,
            message=f"🔍 **Arbitrage Scan Complete**\n\nNo opportunities found with spread ≥ {min_spread}%.\n\n" +
                    "Markets appear to be efficiently priced across exchanges.",
            data={
                "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "symbols_scanned": symbols,
                "min_spread": min_spread,
                "opportunities_found": 0
            }
        )
    
    # Build response message
    lines = [
        f"🔍 **Arbitrage Opportunities Found**",
        f"",
        f"Scan Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Min Spread: {min_spread}%",
        f"Symbols Scanned: {', '.join(symbols)}",
        f"",
        f"**Top {len(top_opportunities)} Opportunities:**",
        f""
    ]
    
    for i, opp in enumerate(top_opportunities, 1):
        confidence_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(opp.confidence, "⚪")
        lines.append(
            f"{i}. **{opp.symbol}** {confidence_emoji}\n"
            f"   Buy on **{opp.buy_exchange.title()}** @ ${opp.buy_price:,.2f}\n"
            f"   Sell on **{opp.sell_exchange.title()}** @ ${opp.sell_price:,.2f}\n"
            f"   Spread: **{opp.spread_pct:.2f}%** | Net Profit: **{opp.profit_potential:.2f}%**\n"
            f"   24h Volume: ${opp.volume_24h:,.0f}"
        )
    
    lines.extend([
        f"",
        f"**Note:** Real execution requires sufficient balance on both exchanges.",
        f"Use `execute-trade` to perform arbitrage trades."
    ])
    
    # Convert to dict for data field
    opportunities_data = [
        {
            "symbol": opp.symbol,
            "buy_exchange": opp.buy_exchange,
            "sell_exchange": opp.sell_exchange,
            "buy_price": opp.buy_price,
            "sell_price": opp.sell_price,
            "spread_pct": opp.spread_pct,
            "profit_potential": opp.profit_potential,
            "volume_24h": opp.volume_24h,
            "confidence": opp.confidence
        }
        for opp in top_opportunities
    ]
    
    return SkillResult(
        success=True,
        message="\n".join(lines),
        data={
            "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "symbols_scanned": symbols,
            "min_spread": min_spread,
            "opportunities_found": len(all_opportunities),
            "opportunities": opportunities_data
        }
    )
