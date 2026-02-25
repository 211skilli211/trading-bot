"""
Trade Execute Skill Handler
Executes trades with user approval flow
"""
import json
from typing import Dict, Any, Optional
from zeroclaw_venom.core.skill import SkillResult
from execution_layer import ExecutionLayer, ExecutionMode
from dataclasses import asdict

def handle(skill_input: Dict[str, Any], context: Any) -> SkillResult:
    """
    Execute a trade with user approval
    
    Expected skill_input:
    {
        "symbol": "BTC-USD",
        "side": "BUY" or "SELL",
        "amount": 0.1,
        "price": 45000.0,  # optional, for limit orders
        "order_type": "market" or "limit",
        "exchange": "binance",  # optional
        "reasoning": "String explaining the trade rationale"
    }
    """
    session = context.session
    
    # Check if we're in confirmation flow
    if session.pending_step == "trade_confirm":
        return _handle_confirmation(skill_input, context)
    
    # Validate required fields
    required = ["symbol", "side", "amount"]
    missing = [f for f in required if f not in skill_input]
    if missing:
        return SkillResult(
            success=False,
            message=f"Missing required fields: {', '.join(missing)}",
            data={"missing_fields": missing}
        )
    
    symbol = skill_input["symbol"]
    side = skill_input["side"].upper()
    amount = float(skill_input["amount"])
    price = skill_input.get("price")
    order_type = skill_input.get("order_type", "market").lower()
    exchange = skill_input.get("exchange")
    reasoning = skill_input.get("reasoning", "No reasoning provided")
    
    # Validate side
    if side not in ["BUY", "SELL"]:
        return SkillResult(
            success=False,
            message=f"Invalid side: {side}. Must be BUY or SELL",
            data={}
        )
    
    # Get trading mode
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        is_paper = config.get('bot', {}).get('mode', 'PAPER') == 'PAPER'
    except:
        is_paper = True
    
    mode = ExecutionMode.PAPER if is_paper else ExecutionMode.LIVE
    mode_label = "📊 PAPER" if is_paper else "🔴 LIVE"
    
    # Build confirmation preview
    preview = {
        "symbol": symbol,
        "side": side,
        "amount": amount,
        "order_type": order_type.upper(),
        "mode": mode_label,
        "exchange": exchange or "Best available",
        "reasoning": reasoning
    }
    
    if price:
        preview["price"] = price
        preview["estimated_total"] = amount * price
    else:
        preview["estimated_total"] = "Market price (will be determined at execution)"
    
    # Calculate estimated fees (0.1% for most exchanges)
    if price:
        estimated_fee = amount * price * 0.001
        preview["estimated_fee"] = f"${estimated_fee:.2f}"
    
    # Store trade details in session for confirmation
    session.set_step_data("trade_details", {
        "symbol": symbol,
        "side": side,
        "amount": amount,
        "price": price,
        "order_type": order_type,
        "exchange": exchange
    })
    session.pending_step = "trade_confirm"
    
    return SkillResult(
        success=True,
        message=f"**Trade Preview ({mode_label})**\n\nPlease review and confirm this trade:\n\n" +
                f"**{side}** {amount} {symbol}\n" +
                f"Type: {order_type.upper()}\n" +
                f"Exchange: {exchange or 'Best available'}\n" +
                (f"Price: ${price:,.2f}\n" if price else "Price: Market\n") +
                (f"Est. Fee: {preview.get('estimated_fee', 'N/A')}\n" if 'estimated_fee' in preview else "") +
                f"\nReasoning: {reasoning}\n\n" +
                f"Reply **CONFIRM** to execute or **CANCEL** to abort.",
        data={"preview": preview, "requires_user_response": True},
        requires_user_response=True
    )

def _handle_confirmation(skill_input: Dict[str, Any], context: Any) -> SkillResult:
    """Handle user confirmation response"""
    session = context.session
    response = skill_input.get("user_response", "").upper().strip()
    trade_details = session.get_step_data("trade_details")
    
    if not trade_details:
        session.pending_step = None
        return SkillResult(
            success=False,
            message="Trade session expired. Please start over.",
            data={}
        )
    
    if response == "CANCEL":
        session.pending_step = None
        session.set_step_data("trade_details", None)
        return SkillResult(
            success=False,
            message="❌ Trade cancelled by user.",
            data={"cancelled": True}
        )
    
    if response != "CONFIRM":
        return SkillResult(
            success=False,
            message="Please reply **CONFIRM** to execute the trade or **CANCEL** to abort.",
            data={"requires_user_response": True},
            requires_user_response=True
        )
    
    # Execute the trade
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        is_paper = config.get('bot', {}).get('mode', 'PAPER') == 'PAPER'
        
        # Get API credentials from config
        binance_creds = config.get('binance', {})
        coinbase_creds = config.get('coinbase', {})
        
        mode = ExecutionMode.PAPER if is_paper else ExecutionMode.LIVE
        
        executor = ExecutionLayer(
            mode=mode,
            binance_api_key=binance_creds.get('api_key'),
            binance_api_secret=binance_creds.get('api_secret'),
            coinbase_api_key=coinbase_creds.get('api_key'),
            coinbase_api_secret=coinbase_creds.get('api_secret'),
            coinbase_passphrase=coinbase_creds.get('passphrase')
        )
        
        # Create trade signal
        from execution_layer import TradeSignal, RiskParameters
        
        signal = TradeSignal(
            symbol=trade_details["symbol"],
            direction="LONG" if trade_details["side"] == "BUY" else "SHORT",
            confidence=1.0,
            order_type=trade_details["order_type"].upper(),
            price=trade_details.get("price"),
            reason="ZeroClaw user-approved trade"
        )
        
        risk = RiskParameters(
            max_position_size=trade_details["amount"],
            max_risk_per_trade=0.1,
            stop_loss_pct=0.02,
            take_profit_pct=0.05
        )
        
        import time
        execution = executor.execute_trade(
            signal=signal,
            risk_params=risk,
            timestamp=int(time.time())
        )
        
        # Clear session
        session.pending_step = None
        session.set_step_data("trade_details", None)
        
        if execution.status.value == "EXECUTED":
            mode_label = "📊 PAPER" if is_paper else "🔴 LIVE"
            return SkillResult(
                success=True,
                message=f"✅ **Trade Executed** ({mode_label})\n\n" +
                        f"Order ID: `{execution.order_id}`\n" +
                        f"Symbol: {execution.symbol}\n" +
                        f"Side: {execution.direction}\n" +
                        f"Amount: {execution.amount}\n" +
                        (f"Price: ${execution.execution_price:,.2f}\n" if execution.execution_price else "") +
                        (f"Fee: ${execution.fees:,.4f}\n" if execution.fees else "") +
                        f"Status: {execution.status.value}\n" +
                        f"Time: {execution.timestamp}",
                data={"execution": asdict(execution)}
            )
        else:
            return SkillResult(
                success=False,
                message=f"❌ **Trade Failed**\n\nStatus: {execution.status.value}\n" +
                        f"Error: {execution.error_message or 'Unknown error'}",
                data={"execution": asdict(execution)}
            )
            
    except Exception as e:
        session.pending_step = None
        session.set_step_data("trade_details", None)
        return SkillResult(
            success=False,
            message=f"❌ **Trade Execution Failed**\n\nError: {str(e)}",
            data={"error": str(e)}
        )
