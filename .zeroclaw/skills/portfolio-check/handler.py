"""
Portfolio Check Skill Handler
Provides comprehensive portfolio analysis
"""
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from zeroclaw_venom.core.skill import SkillResult

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('trades.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_portfolio_summary() -> Dict[str, Any]:
    """Get portfolio summary from database"""
    conn = get_db_connection()
    try:
        # Get positions
        cursor = conn.execute('''
            SELECT symbol, side, amount, entry_price, current_price, pnl, pnl_percent, currency
            FROM positions WHERE status = 'open'
        ''')
        positions = [dict(row) for row in cursor.fetchall()]
        
        # Get recent trades
        cursor = conn.execute('''
            SELECT symbol, side, amount, price, timestamp, pnl, fee
            FROM trades ORDER BY timestamp DESC LIMIT 10
        ''')
        trades = [dict(row) for row in cursor.fetchall()]
        
        # Calculate metrics
        total_pnl = sum(p.get('pnl', 0) for p in positions)
        total_positions = len(positions)
        
        # Get trading mode
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            is_paper = config.get('bot', {}).get('mode', 'PAPER') == 'PAPER'
        except:
            is_paper = True
        
        return {
            "positions": positions,
            "recent_trades": trades,
            "total_open_positions": total_positions,
            "total_unrealized_pnl": total_pnl,
            "is_paper": is_paper,
            "mode": "PAPER" if is_paper else "LIVE"
        }
    finally:
        conn.close()

def get_paper_portfolio() -> Dict[str, Any]:
    """Get mock paper portfolio"""
    return {
        "balance": 10000.00,
        "equity": 10000.00,
        "totalPnl": 0.00,
        "totalPnlPercent": 0.00,
        "is_paper": True,
        "mode": "PAPER"
    }

def format_currency(value: float, symbol: str = "USD") -> str:
    """Format currency value"""
    if symbol == "USD":
        return f"${value:,.2f}"
    return f"{value:,.4f} {symbol}"

def handle(skill_input: Dict[str, Any], context: Any) -> SkillResult:
    """
    Check portfolio status and provide analysis
    
    Expected skill_input:
    {
        "detailed": false,  # optional, show detailed breakdown
        "currency": "USD"   # optional, filter by currency
    }
    """
    detailed = skill_input.get("detailed", False)
    filter_currency = skill_input.get("currency", "").upper()
    
    # Get portfolio data
    portfolio = get_portfolio_summary()
    
    mode_emoji = "📊" if portfolio["is_paper"] else "🔴"
    mode_label = portfolio["mode"]
    
    lines = [
        f"{mode_emoji} **Portfolio Overview** ({mode_label} Mode)",
        f"",
        f"**Open Positions:** {portfolio['total_open_positions']}",
        f"**Unrealized P&L:** {format_currency(portfolio['total_unrealized_pnl'])}",
        f""
    ]
    
    # Add positions breakdown
    if portfolio["positions"]:
        lines.append("**Current Positions:**")
        for pos in portfolio["positions"]:
            currency = pos.get("currency", "USD")
            if filter_currency and currency != filter_currency:
                continue
                
            pnl = pos.get("pnl", 0)
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            pnl_str = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
            
            lines.append(
                f"• **{pos['symbol']}** | {pos['side'].upper()}\n"
                f"  Amount: {pos['amount']:.4f} | Entry: ${pos['entry_price']:,.2f}\n"
                f"  Current: ${pos['current_price']:,.2f} | P&L: {pnl_emoji} ${pnl_str} ({pos.get('pnl_percent', 0):.2f}%)"
            )
        lines.append("")
    else:
        lines.append("*No open positions*\n")
    
    # Add recent trades
    if portfolio["recent_trades"]:
        lines.append("**Recent Trades:**")
        for trade in portfolio["recent_trades"][:5]:
            side_emoji = "🟢" if trade["side"] == "buy" else "🔴"
            lines.append(
                f"{side_emoji} {trade['side'].upper()} {trade['amount']:.4f} {trade['symbol']} "
                f"@ ${trade['price']:,.2f}"
            )
        lines.append("")
    
    # Add detailed analysis if requested
    if detailed:
        lines.append("**Portfolio Analysis:**")
        
        # Calculate allocation
        positions = portfolio["positions"]
        if positions:
            long_positions = [p for p in positions if p["side"] == "long"]
            short_positions = [p for p in positions if p["side"] == "short"]
            
            lines.append(f"• Long Positions: {len(long_positions)}")
            lines.append(f"• Short Positions: {len(short_positions)}")
            
            # Winners vs losers
            winners = [p for p in positions if p.get("pnl", 0) > 0]
            losers = [p for p in positions if p.get("pnl", 0) < 0]
            
            lines.append(f"• Winning Positions: {len(winners)} ({len(winners)/len(positions)*100:.1f}%)")
            lines.append(f"• Losing Positions: {len(losers)} ({len(losers)/len(positions)*100:.1f}%)")
            
            # Risk metrics
            if positions:
                avg_pnl = sum(p.get("pnl", 0) for p in positions) / len(positions)
                max_pnl = max(p.get("pnl", 0) for p in positions)
                min_pnl = min(p.get("pnl", 0) for p in positions)
                
                lines.append(f"• Average P&L per Position: ${avg_pnl:,.2f}")
                lines.append(f"• Best Position: +${max_pnl:,.2f}")
                lines.append(f"• Worst Position: ${min_pnl:,.2f}")
        
        lines.append("")
    
    # Add quick actions
    lines.extend([
        "**Quick Actions:**",
        "• `trade-execute` - Execute a new trade",
        "• `price-check` - Check current prices",
        "• `arbitrage-scan` - Find arbitrage opportunities"
    ])
    
    return SkillResult(
        success=True,
        message="\n".join(lines),
        data={
            "portfolio": portfolio,
            "mode": mode_label,
            "is_paper": portfolio["is_paper"],
            "timestamp": datetime.now().isoformat()
        }
    )
