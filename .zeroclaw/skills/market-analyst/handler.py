"""
Market Analyst Skill Handler
Provides market analysis and insights
"""
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from zeroclaw_venom.core.skill import SkillResult

def get_price_data(symbol: str, days: int = 7) -> List[Dict]:
    """Get historical price data (mock implementation)"""
    # In real implementation, fetch from database or API
    base_prices = {
        "BTC-USD": 45000, "ETH-USD": 3200, "SOL-USD": 105,
        "ADA-USD": 0.55, "DOT-USD": 7.20, "XRP-USD": 0.62
    }
    base = base_prices.get(symbol, 100)
    
    import random
    data = []
    for i in range(days):
        change = random.uniform(-0.05, 0.05)
        price = base * (1 + change)
        data.append({
            "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
            "price": price,
            "volume": random.uniform(1000000, 10000000)
        })
        base = price
    
    return list(reversed(data))

def calculate_ma(prices: List[float], period: int) -> List[float]:
    """Calculate moving average"""
    ma = []
    for i in range(len(prices)):
        if i < period - 1:
            ma.append(None)
        else:
            ma.append(sum(prices[i-period+1:i+1]) / period)
    return ma

def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI"""
    if len(prices) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_trend(data: List[Dict]) -> Dict[str, Any]:
    """Analyze price trend"""
    prices = [d["price"] for d in data]
    volumes = [d["volume"] for d in data]
    
    # Calculate moving averages
    ma7 = calculate_ma(prices, 7)
    ma20 = calculate_ma(prices, min(20, len(prices)))
    
    # Current values
    current_price = prices[-1]
    current_ma7 = ma7[-1] if ma7[-1] else current_price
    current_ma20 = ma20[-1] if ma20[-1] else current_price
    
    # Trend determination
    if current_price > current_ma7 > current_ma20:
        trend = "BULLISH"
        trend_strength = "STRONG" if current_price > current_ma7 * 1.05 else "MODERATE"
    elif current_price < current_ma7 < current_ma20:
        trend = "BEARISH"
        trend_strength = "STRONG" if current_price < current_ma7 * 0.95 else "MODERATE"
    else:
        trend = "NEUTRAL"
        trend_strength = "CONSOLIDATING"
    
    # Price change
    price_change = ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] else 0
    
    # Volume trend
    avg_volume = sum(volumes) / len(volumes)
    recent_volume = sum(volumes[-3:]) / 3
    volume_trend = "INCREASING" if recent_volume > avg_volume * 1.1 else "DECREASING" if recent_volume < avg_volume * 0.9 else "STABLE"
    
    return {
        "trend": trend,
        "trend_strength": trend_strength,
        "price_change_pct": price_change,
        "current_price": current_price,
        "support": min(prices),
        "resistance": max(prices),
        "rsi": calculate_rsi(prices),
        "volume_trend": volume_trend,
        "ma7": current_ma7,
        "ma20": current_ma20
    }

def handle(skill_input: Dict[str, Any], context: Any) -> SkillResult:
    """
    Analyze market conditions for a symbol
    
    Expected skill_input:
    {
        "symbol": "BTC-USD",
        "days": 14  # Analysis period
    }
    """
    symbol = skill_input.get("symbol", "BTC-USD").upper()
    days = skill_input.get("days", 14)
    
    # Get data and analyze
    data = get_price_data(symbol, days)
    analysis = analyze_trend(data)
    
    # Build response
    trend_emoji = {
        "BULLISH": "🟢",
        "BEARISH": "🔴",
        "NEUTRAL": "⚪"
    }.get(analysis["trend"], "⚪")
    
    # RSI interpretation
    rsi = analysis["rsi"]
    if rsi > 70:
        rsi_signal = "OVERBOUGHT"
        rsi_emoji = "🔴"
    elif rsi < 30:
        rsi_signal = "OVERSOLD"
        rsi_emoji = "🟢"
    else:
        rsi_signal = "NEUTRAL"
        rsi_emoji = "⚪"
    
    lines = [
        f"📊 **Market Analysis: {symbol}**",
        f"",
        f"**Current Price:** ${analysis['current_price']:,.2f}",
        f"**{days}D Change:** {analysis['price_change_pct']:+.2f}%",
        f"",
        f"**Trend Analysis:**",
        f"{trend_emoji} Direction: {analysis['trend']} ({analysis['trend_strength']})",
        f"📈 Support: ${analysis['support']:,.2f}",
        f"📉 Resistance: ${analysis['resistance']:,.2f}",
        f"",
        f"**Technical Indicators:**",
        f"{rsi_emoji} RSI (14): {rsi:.1f} ({rsi_signal})",
        f"📊 MA7: ${analysis['ma7']:,.2f}" if analysis['ma7'] else "",
        f"📊 MA20: ${analysis['ma20']:,.2f}" if analysis['ma20'] else "",
        f"",
        f"**Volume:**",
        f"📊 Trend: {analysis['volume_trend']}",
        f""
    ]
    
    # Trading recommendation
    lines.append("**Trading Recommendation:**")
    
    if analysis["trend"] == "BULLISH" and rsi < 70:
        lines.append("🟢 **BUY** - Uptrend with room to grow")
    elif analysis["trend"] == "BEARISH" and rsi > 30:
        lines.append("🔴 **SELL/SHORT** - Downtrend likely to continue")
    elif rsi > 70:
        lines.append("🟡 **WAIT** - Overbought conditions, expect pullback")
    elif rsi < 30:
        lines.append("🟢 **BUY** - Oversold, potential bounce")
    else:
        lines.append("🟡 **HOLD** - Neutral conditions, wait for clearer signal")
    
    lines.extend([
        f"",
        f"**Key Levels:**",
        f"• Entry: Around ${analysis['current_price']*0.995:,.2f}",
        f"• Stop Loss: Below ${analysis['support']*0.99:,.2f}",
        f"• Take Profit: Above ${analysis['resistance']*0.99:,.2f}"
    ])
    
    return SkillResult(
        success=True,
        message="\n".join(filter(None, lines)),
        data={
            "symbol": symbol,
            "analysis_period_days": days,
            "current_price": analysis["current_price"],
            "trend": analysis["trend"],
            "trend_strength": analysis["trend_strength"],
            "rsi": rsi,
            "rsi_signal": rsi_signal,
            "support": analysis["support"],
            "resistance": analysis["resistance"],
            "recommendation": lines[-4] if "BUY" in lines[-4] or "SELL" in lines[-4] or "WAIT" in lines[-4] or "HOLD" in lines[-4] else "NEUTRAL"
        }
    )
