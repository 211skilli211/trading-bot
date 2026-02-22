#!/usr/bin/env python3
"""
ZeroClaw Tool Executor
Bridge between ZeroClaw agent and trading tools
"""

import json
import sys
import os

# Add paths for imports
sys.path.insert(0, '/root/trading-bot/.zeroclaw')

class ToolExecutor:
    """Executes tools for ZeroClaw agent"""
    
    def __init__(self):
        self.tools = {
            "trading_engine": self._trading_engine,
            "arbitrage_scanner": self._arbitrage_scanner,
            "portfolio_manager": self._portfolio_manager,
            "price_fetcher": self._price_fetcher,
            "telegram_notifier": self._telegram_notifier,
            "multi_bot_controller": self._multi_bot_controller,
        }
    
    def execute(self, tool_name: str, params: dict) -> dict:
        """Execute a tool with parameters"""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            return self.tools[tool_name](params)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def _trading_engine(self, params: dict) -> dict:
        """Execute trading engine commands"""
        from trading_engine import TradingEngine
        
        engine = TradingEngine()
        action = params.get('action')
        
        if action == 'buy':
            return engine.execute_trade(
                symbol=params.get('symbol', 'BTC'),
                side='buy',
                amount=params.get('amount', 0.1),
                price=params.get('price'),
                order_type=params.get('order_type', 'market'),
                reason=params.get('reason', 'AI decision')
            )
        elif action == 'sell':
            return engine.execute_trade(
                symbol=params.get('symbol', 'BTC'),
                side='sell',
                amount=params.get('amount', 0.1),
                price=params.get('price'),
                order_type=params.get('order_type', 'market'),
                reason=params.get('reason', 'AI decision')
            )
        elif action == 'get_positions':
            return {"success": True, "positions": engine.get_positions()}
        elif action == 'get_balance':
            return {"success": True, "balance": engine.get_balance()}
        elif action == 'get_history':
            return {"success": True, "trades": engine.get_trade_history()}
        elif action == 'close_position':
            return engine.close_position(params.get('symbol', 'BTC'))
        elif action == 'set_mode':
            return engine.set_mode(params.get('mode', 'paper'))
        elif action == 'summary':
            return {"success": True, "portfolio": engine.get_portfolio_summary()}
        else:
            return {"error": f"Unknown trading action: {action}"}
    
    def _arbitrage_scanner(self, params: dict) -> dict:
        """Execute arbitrage scanner commands"""
        from arbitrage_engine import ArbitrageEngine
        
        engine = ArbitrageEngine()
        action = params.get('action')
        
        if action == 'scan':
            return {
                "success": True,
                "opportunities": engine.scan_arbitrage(
                    symbol=params.get('symbol'),
                    min_spread_pct=params.get('min_spread_pct', 0.3)
                )
            }
        elif action == 'execute':
            return engine.execute_arbitrage(
                symbol=params.get('symbol', 'BTC'),
                buy_exchange=params.get('buy_exchange', 'binance'),
                sell_exchange=params.get('sell_exchange', 'coinbase'),
                amount=params.get('amount', 0.01)
            )
        elif action == 'get_opportunities':
            return {
                "success": True,
                "opportunities": engine.get_opportunities(
                    hours=params.get('hours', 24)
                )
            }
        elif action == 'set_threshold':
            return engine.set_threshold(params.get('threshold', 0.3))
        elif action == 'stats':
            return {"success": True, "statistics": engine.get_statistics()}
        else:
            return {"error": f"Unknown arbitrage action: {action}"}
    
    def _portfolio_manager(self, params: dict) -> dict:
        """Execute portfolio manager commands"""
        from trading_engine import TradingEngine
        
        engine = TradingEngine()
        action = params.get('action')
        
        if action == 'get_portfolio':
            return {"success": True, "portfolio": engine.get_portfolio_summary()}
        elif action == 'get_pnl':
            balance = engine.get_balance()
            return {
                "success": True,
                "pnl": balance.get('total_pnl', 0),
                "pnl_pct": balance.get('pnl_pct', 0),
                "total_value": balance.get('total_value_usd', 0)
            }
        elif action == 'get_performance':
            trades = engine.get_trade_history(1000)
            winning = sum(1 for t in trades if t.get('pnl', 0) > 0)
            return {
                "success": True,
                "total_trades": len(trades),
                "winning_trades": winning,
                "win_rate": (winning / len(trades) * 100) if trades else 0
            }
        else:
            return {"error": f"Unknown portfolio action: {action}"}
    
    def _price_fetcher(self, params: dict) -> dict:
        """Execute price fetcher commands"""
        from trading_engine import TradingEngine
        
        engine = TradingEngine()
        action = params.get('action')
        
        if action == 'get_price':
            price = engine.get_price(params.get('symbol', 'BTC'))
            return {
                "success": True,
                "symbol": params.get('symbol', 'BTC'),
                "price": price,
                "timestamp": datetime.now().isoformat()
            }
        elif action == 'get_prices':
            symbols = params.get('symbols', ['BTC', 'ETH', 'SOL'])
            prices = {s: engine.get_price(s) for s in symbols}
            return {
                "success": True,
                "prices": prices,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"error": f"Unknown price action: {action}"}
    
    def _telegram_notifier(self, params: dict) -> dict:
        """Execute telegram notifier commands"""
        from telegram_notifier import TelegramNotifier
        
        notifier = TelegramNotifier()
        action = params.get('action')
        
        if action == 'send_message':
            return notifier.send_message(params.get('message', ''))
        elif action == 'send_alert':
            return notifier.send_alert(
                params.get('message', ''),
                params.get('level', 'info')
            )
        elif action == 'send_trade_notification':
            return notifier.send_trade_notification(params.get('trade_data', {}))
        elif action == 'set_alert':
            return notifier.set_alert(
                params.get('name', 'Alert'),
                params.get('condition', 'above'),
                params.get('symbol'),
                params.get('threshold')
            )
        else:
            return {"error": f"Unknown notification action: {action}"}
    
    def _multi_bot_controller(self, params: dict) -> dict:
        """Execute multi-bot controller commands"""
        from multi_bot_controller import MultiBotController
        
        controller = MultiBotController()
        action = params.get('action')
        
        if action == 'list_bots':
            return controller.get_bot_status()
        elif action == 'create_bot':
            return controller.create_bot(
                params.get('name', 'New Bot'),
                params.get('strategy', 'arbitrage'),
                params.get('symbols', ['BTC', 'ETH']),
                params.get('config', {})
            )
        elif action == 'start_bot':
            return controller.start_bot(params.get('bot_id'))
        elif action == 'stop_bot':
            return controller.stop_bot(params.get('bot_id'))
        elif action == 'delete_bot':
            return controller.delete_bot(params.get('bot_id'))
        elif action == 'get_status':
            return controller.get_bot_status(params.get('bot_id'))
        elif action == 'set_strategy':
            return controller.set_strategy(
                params.get('bot_id'),
                params.get('strategy', 'arbitrage'),
                params.get('parameters', {})
            )
        elif action == 'coordinate':
            return controller.coordinate_bots(
                params.get('coord_action', 'report')
            )
        else:
            return {"error": f"Unknown bot action: {action}"}


def main():
    """Main entry point for command line usage"""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: tool_executor.py <tool_name> [params_json]"}))
        sys.exit(1)
    
    tool_name = sys.argv[1]
    params = {}
    
    if len(sys.argv) > 2:
        try:
            params = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON parameters"}))
            sys.exit(1)
    
    executor = ToolExecutor()
    result = executor.execute(tool_name, params)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    from datetime import datetime
    main()
