"""
Config Optimizer Skill Handler
Analyzes and suggests configuration improvements
"""
import json
import sqlite3
from typing import Dict, Any, List
from datetime import datetime, timedelta
from zeroclaw_venom.core.skill import SkillResult

def get_recent_performance(days: int = 7) -> Dict[str, Any]:
    """Get recent trading performance"""
    conn = sqlite3.connect('trades.db')
    conn.row_factory = sqlite3.Row
    
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = conn.execute('''
            SELECT COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                   SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                   SUM(pnl) as total_pnl,
                   AVG(pnl) as avg_pnl
            FROM trades WHERE timestamp > ?
        ''', (cutoff,))
        
        row = cursor.fetchone()
        return {
            "total_trades": row[0] or 0,
            "winning_trades": row[1] or 0,
            "losing_trades": row[2] or 0,
            "total_pnl": row[3] or 0,
            "avg_pnl": row[4] or 0
        }
    finally:
        conn.close()

def load_config() -> Dict[str, Any]:
    """Load current configuration"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except:
        return {"bot": {"mode": "PAPER"}}

def analyze_config(config: Dict, performance: Dict) -> List[Dict[str, Any]]:
    """Analyze configuration and generate recommendations"""
    recommendations = []
    
    bot_config = config.get("bot", {})
    risk_config = config.get("risk", {})
    
    # Check trading mode
    if bot_config.get("mode") == "PAPER" and performance["total_trades"] > 20:
        win_rate = performance["winning_trades"] / performance["total_trades"] if performance["total_trades"] > 0 else 0
        if win_rate > 0.55:
            recommendations.append({
                "category": "Mode",
                "priority": "MEDIUM",
                "current": "PAPER",
                "suggested": "LIVE",
                "reason": f"Win rate of {win_rate*100:.1f}% over {performance['total_trades']} trades suggests readiness for live trading",
                "impact": "Start trading with real funds"
            })
    
    # Check position sizing
    max_pos = risk_config.get("max_position_size", 0.1)
    if performance["total_trades"] > 10:
        avg_pnl = performance["avg_pnl"]
        if avg_pnl > 0 and max_pos < 0.15:
            recommendations.append({
                "category": "Position Sizing",
                "priority": "LOW",
                "current": f"{max_pos*100:.0f}%",
                "suggested": "15%",
                "reason": "Positive average P&L suggests room for larger positions",
                "impact": "Increase potential returns"
            })
        elif avg_pnl < 0 and max_pos > 0.05:
            recommendations.append({
                "category": "Position Sizing",
                "priority": "HIGH",
                "current": f"{max_pos*100:.0f}%",
                "suggested": "5%",
                "reason": "Negative average P&L - reduce risk exposure",
                "impact": "Limit potential losses"
            })
    
    # Check stop loss
    stop_loss = risk_config.get("stop_loss_pct", 0.02)
    if stop_loss > 0.05:
        recommendations.append({
            "category": "Risk Management",
            "priority": "HIGH",
            "current": f"{stop_loss*100:.0f}%",
            "suggested": "2-3%",
            "reason": "Stop loss too wide increases downside risk",
            "impact": "Tighter risk control"
        })
    
    # Check take profit
    take_profit = risk_config.get("take_profit_pct", 0.05)
    if take_profit < stop_loss * 1.5:
        recommendations.append({
            "category": "Risk Management",
            "priority": "MEDIUM",
            "current": f"{take_profit*100:.0f}%",
            "suggested": f"{stop_loss*150:.0f}%",
            "reason": "Risk/reward ratio should be at least 1:1.5",
            "impact": "Better risk-adjusted returns"
        })
    
    # Check scan interval
    scan_interval = bot_config.get("scan_interval", 300)
    if scan_interval < 60:
        recommendations.append({
            "category": "Performance",
            "priority": "LOW",
            "current": f"{scan_interval}s",
            "suggested": "60s",
            "reason": "Very frequent scanning may cause rate limiting",
            "impact": "Avoid API rate limits"
        })
    
    return recommendations

def handle(skill_input: Dict[str, Any], context: Any) -> SkillResult:
    """
    Analyze configuration and suggest optimizations
    
    Expected skill_input:
    {
        "days": 7  # Number of days to analyze performance
    }
    """
    days = skill_input.get("days", 7)
    
    # Load data
    config = load_config()
    performance = get_recent_performance(days)
    recommendations = analyze_config(config, performance)
    
    # Build response
    lines = [
        f"⚙️ **Configuration Analysis**",
        f"",
        f"Analysis Period: Last {days} days",
        f"Total Trades: {performance['total_trades']}",
        f"Win Rate: {performance['winning_trades']/performance['total_trades']*100:.1f}%" if performance['total_trades'] > 0 else "Win Rate: N/A",
        f"Total P&L: ${performance['total_pnl']:,.2f}",
        f""
    ]
    
    if recommendations:
        lines.append(f"**Recommendations ({len(recommendations)} found):**\n")
        
        # Sort by priority
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        for i, rec in enumerate(recommendations, 1):
            emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(rec["priority"], "⚪")
            lines.append(
                f"{i}. {emoji} **{rec['category']}** ({rec['priority']} priority)\n"
                f"   Current: {rec['current']} → Suggested: {rec['suggested']}\n"
                f"   Reason: {rec['reason']}\n"
                f"   Impact: {rec['impact']}"
            )
        
        lines.extend([
            f"",
            f"**To apply changes:**",
            f"1. Edit `config.json` manually, or",
            f"2. Use the Settings page in the dashboard"
        ])
    else:
        lines.append("✅ **No configuration issues detected.**")
        lines.append(f"Your current settings appear optimal for recent performance.")
    
    return SkillResult(
        success=True,
        message="\n".join(lines),
        data={
            "analysis_period_days": days,
            "performance": performance,
            "recommendations": recommendations,
            "current_config": config
        }
    )
