#!/usr/bin/env python3
"""
ZeroClaw AI Agent with Tool Integration
AI-powered trading assistant with direct tool control
"""

import json
import os
import subprocess
import requests
from typing import List, Dict, Any, Callable
from datetime import datetime

class ToolRegistry:
    """Registry of available tools for the AI agent"""
    
    def __init__(self):
        self.tools: Dict[str, Dict] = {
            "trading_engine": {
                "description": "Execute trades, manage positions, check balance",
                "actions": ["buy", "sell", "get_positions", "get_balance", "get_history", "close_position", "set_mode", "summary"]
            },
            "arbitrage_scanner": {
                "description": "Scan for arbitrage opportunities across exchanges",
                "actions": ["scan", "execute", "get_opportunities", "set_threshold", "stats"]
            },
            "portfolio_manager": {
                "description": "Manage portfolio, track P&L, analyze performance",
                "actions": ["get_portfolio", "get_pnl", "get_performance", "rebalance", "set_allocation"]
            },
            "price_fetcher": {
                "description": "Fetch real-time prices from multiple exchanges",
                "actions": ["get_price", "get_prices", "get_history", "subscribe", "unsubscribe"]
            },
            "telegram_notifier": {
                "description": "Send notifications and alerts via Telegram",
                "actions": ["send_message", "send_alert", "send_trade_notification", "set_alert"]
            },
            "multi_bot_controller": {
                "description": "Coordinate multiple trading bots and strategies",
                "actions": ["list_bots", "create_bot", "start_bot", "stop_bot", "delete_bot", "get_status", "set_strategy", "coordinate"]
            }
        }
    
    def get_tool_description(self) -> str:
        """Get formatted tool descriptions"""
        lines = ["AVAILABLE TOOLS:"]
        for name, info in self.tools.items():
            lines.append(f"  {name}: {info['description']}")
            lines.append(f"    Actions: {', '.join(info['actions'])}")
        return "\n".join(lines)
    
    def is_valid_tool(self, tool: str, action: str) -> bool:
        """Check if tool and action are valid"""
        if tool not in self.tools:
            return False
        return action in self.tools[tool]["actions"]


class ZeroClawAIAgent:
    """AI Agent with tool integration for trading operations"""
    
    def __init__(self):
        self.config = self._load_config()
        self.provider = self.config.get('default_provider', 'openrouter')
        self.model = self.config.get('default_model', 'openrouter/openrouter/auto')
        self.api_key = os.getenv('OPENROUTER_API_KEY', self.config.get('api_key', ''))
        self.tools = ToolRegistry()
        self.conversation_history: List[Dict] = []
    
    def _load_config(self) -> Dict:
        """Load ZeroClaw config"""
        try:
            config = {}
            with open('/sdcard/zeroclaw-workspace/trading-bot/.zeroclaw/config.toml', 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, val = line.split('=', 1)
                        config[key.strip()] = val.strip().strip('"')
            return config
        except:
            return {
                'default_provider': 'openrouter',
                'default_model': 'openrouter/openrouter/auto',
            }
    
    def _execute_tool(self, tool: str, params: Dict) -> Dict:
        """Execute a tool via subprocess"""
        try:
            cmd = [
                'python3', '/sdcard/zeroclaw-workspace/trading-bot/.zeroclaw/tool_executor.py',
                tool, json.dumps(params)
            ]
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr[:200]}
                
        except subprocess.TimeoutExpired:
            return {"error": "Tool execution timed out"}
        except Exception as e:
            return {"error": str(e)}
    
    def _call_llm_with_tools(self, messages: List[Dict], tools_context: str) -> Dict:
        """Call LLM with tool awareness"""
        try:
            if not self.api_key or len(self.api_key) < 20:
                return {
                    "response": "⚠️ OpenRouter API key not configured.\n\nTo enable AI features:\n1. Get API key from https://openrouter.ai\n2. Set OPENROUTER_API_KEY environment variable\n3. Or add api_key to ~/.zeroclaw/config.toml",
                    "tool_calls": [],
                    "error": "API_KEY_MISSING"
                }
            
            # Enhance system prompt with tool info
            if messages and messages[0].get('role') == 'system':
                messages[0]['content'] += f"\n\n{tools_context}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "ZeroClaw Trading Dashboard",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1500
            }
            
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=data, timeout=60
            )
            
            if resp.status_code == 200:
                result = resp.json()
                content = result['choices'][0]['message']['content']
                
                # Parse tool calls from response (simple parsing)
                tool_calls = self._extract_tool_calls(content)
                
                return {
                    "response": content,
                    "tool_calls": tool_calls
                }
            else:
                return {"response": "", "tool_calls": []}
                
        except Exception as e:
            return {"response": "", "tool_calls": [], "error": str(e)}
    
    def _extract_tool_calls(self, content: str) -> List[Dict]:
        """Extract tool calls from AI response"""
        tool_calls = []
        
        # Look for patterns like: [TOOL:trading_engine:buy:symbol=BTC:amount=0.1]
        import re
        pattern = r'\[TOOL:(\w+):(\w+)(?::([^\]]+))?\]'
        matches = re.findall(pattern, content)
        
        for match in matches:
            tool, action, params_str = match
            params = {}
            if params_str:
                for param in params_str.split(':'):
                    if '=' in param:
                        k, v = param.split('=', 1)
                        params[k] = v
            
            tool_calls.append({
                "tool": tool,
                "action": action,
                "params": params
            })
        
        return tool_calls
    
    def _get_tool_results(self, tool_calls: List[Dict]) -> str:
        """Execute tool calls and format results"""
        results = []
        
        for call in tool_calls:
            tool = call.get('tool')
            action = call.get('action')
            params = call.get('params', {})
            params['action'] = action
            
            result = self._execute_tool(tool, params)
            results.append(f"Tool: {tool}.{action}\nResult: {json.dumps(result, indent=2)[:500]}")
        
        return "\n\n".join(results) if results else ""
    
    def _detect_and_execute_intent(self, message: str) -> tuple:
        """Detect user intent and execute appropriate tools"""
        msg_lower = message.lower()
        
        # Trading intent
        if any(kw in msg_lower for kw in ['buy', 'sell', 'trade', 'execute', 'order']):
            # Extract symbol and amount
            symbol = 'BTC'
            for s in ['eth', 'sol', 'ada', 'xrp', 'doge', 'bnb']:
                if s in msg_lower:
                    symbol = s.upper()
            
            # Default amounts
            amount = 0.1
            if 'btc' in msg_lower:
                amount = 0.01
            
            action = 'buy' if 'buy' in msg_lower else 'sell'
            
            result = self._execute_tool('trading_engine', {
                'action': action,
                'symbol': symbol,
                'amount': amount,
                'reason': f'User request: {message}'
            })
            
            return ('trading_engine', result)
        
        # Price check intent
        if any(kw in msg_lower for kw in ['price', 'cost', 'worth', 'value']):
            symbol = 'BTC'
            for s in ['eth', 'sol', 'ada', 'xrp', 'doge', 'bnb', 'btc', 'bitcoin']:
                if s in msg_lower:
                    symbol = s.upper() if s != 'bitcoin' else 'BTC'
            
            result = self._execute_tool('price_fetcher', {
                'action': 'get_price',
                'symbol': symbol
            })
            
            return ('price_fetcher', result)
        
        # Portfolio intent
        if any(kw in msg_lower for kw in ['portfolio', 'balance', 'holding', 'position', 'pnl']):
            result = self._execute_tool('portfolio_manager', {'action': 'get_portfolio'})
            return ('portfolio_manager', result)
        
        # Arbitrage intent
        if any(kw in msg_lower for kw in ['arbitrage', 'spread', 'opportunity']):
            result = self._execute_tool('arbitrage_scanner', {
                'action': 'scan',
                'min_spread_pct': 0.3
            })
            return ('arbitrage_scanner', result)
        
        # Bot control intent
        if any(kw in msg_lower for kw in ['bot', 'strategy', 'automation']):
            result = self._execute_tool('multi_bot_controller', {'action': 'list_bots'})
            return ('multi_bot_controller', result)
        
        return (None, None)
    
    def chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Process a chat message with AI and tools"""
        
        if conversation_history is None:
            conversation_history = []
        
        # Detect intent and execute tool
        tool_used, tool_result = self._detect_and_execute_intent(message)
        
        # Build system prompt
        system_prompt = f"""You are ZeroClaw AI, an advanced crypto trading assistant.

{self.tools.get_tool_description()}

CURRENT MODE: Paper Trading (Practice mode - no real funds at risk)

When the user asks for trading operations:
1. Use the appropriate tool to get real data
2. Provide clear, actionable responses
3. Always mention that we're in paper trading mode
4. Include relevant numbers and statistics

If executing a trade, show:
- What was traded
- At what price
- Total cost/proceeds
- Current balance after trade
"""
        
        # Add tool result to context
        tool_context = ""
        if tool_result:
            if tool_result.get('success'):
                tool_context = f"\n\nTOOL RESULT ({tool_used}):\n{json.dumps(tool_result, indent=2)[:800]}"
            else:
                tool_context = f"\n\nTOOL ERROR ({tool_used}): {tool_result.get('error', 'Unknown error')}"
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
            {"role": "user", "content": message + tool_context}
        ]
        
        # Call LLM
        llm_result = self._call_llm_with_tools(messages, self.tools.get_tool_description())
        
        ai_response = llm_result.get('response', '').strip()
        
        # If LLM response is empty, use tool result directly
        if not ai_response and tool_result:
            if tool_used == 'trading_engine' and tool_result.get('success'):
                trade = tool_result
                ai_response = f"✅ Trade executed!\n\n**{trade.get('side', '').upper()} {trade.get('symbol')}**\nAmount: {trade.get('amount')}\nPrice: ${trade.get('price', 0):,.2f}\nTotal: ${trade.get('total', 0):,.2f}\nFees: ${trade.get('fees', 0):,.4f}\nMode: {trade.get('mode', 'unknown').upper()}\nID: `{trade.get('trade_id', 'N/A')}`"
            
            elif tool_used == 'price_fetcher' and tool_result.get('success'):
                price_data = tool_result
                ai_response = f"📊 **{price_data.get('symbol')} Price**: ${price_data.get('price', 0):,.2f}\n\nData fetched from multiple exchanges in real-time."
            
            elif tool_used == 'portfolio_manager' and tool_result.get('success'):
                portfolio = tool_result.get('portfolio', {})
                balance = portfolio.get('balance', {})
                ai_response = f"💼 **Portfolio Summary**\n\nTotal Value: ${balance.get('total_value_usd', 0):,.2f}\nPnL: ${balance.get('total_pnl', 0):,.2f} ({balance.get('pnl_pct', 0):+.2f}%)\nOpen Positions: {portfolio.get('metrics', {}).get('open_positions', 0)}\nTotal Trades: {portfolio.get('metrics', {}).get('total_trades', 0)}"
            
            elif tool_used == 'arbitrage_scanner':
                opportunities = tool_result.get('opportunities', [])
                if opportunities:
                    ai_response = f"🔍 Found {len(opportunities)} arbitrage opportunities:\n\n"
                    for opp in opportunities[:3]:
                        ai_response += f"• **{opp.get('symbol')}**: Buy on {opp.get('buy_exchange')} @ ${opp.get('buy_price', 0):,.2f}, Sell on {opp.get('sell_exchange')} @ ${opp.get('sell_price', 0):,.2f}\n  Spread: {opp.get('spread_pct', 0):.2f}% | Est. Profit: ${opp.get('profit_potential', 0):,.2f}\n\n"
                else:
                    ai_response = "🔍 No arbitrage opportunities found with current spread threshold (0.3%). The market is efficiently priced across exchanges."
            
            elif tool_used == 'multi_bot_controller':
                summary = tool_result.get('summary', {})
                ai_response = f"🤖 **Bot Status**\n\nTotal Bots: {summary.get('total', 0)}\nRunning: {summary.get('running', 0)}\nStopped: {summary.get('stopped', 0)}\n\nUse 'create bot' to start a new automated trading strategy."
            
            else:
                ai_response = "I processed your request. How else can I help you with your trading?"
        
        # Clean up response (remove tool call markers)
        ai_response = self._clean_response(ai_response)
        
        return {
            "success": True,
            "response": ai_response,
            "tool_used": tool_used,
            "tool_result": tool_result,
            "model": self.model,
            "provider": self.provider,
            "timestamp": datetime.now().isoformat()
        }
    
    def _clean_response(self, text: str) -> str:
        """Clean up AI response by removing tool markers"""
        import re
        # Remove [TOOL:...] markers
        text = re.sub(r'\[TOOL:[^\]]+\]', '', text)
        # Remove [TOOL_RESULT...] markers
        text = re.sub(r'\[TOOL_RESULT[^\]]*\]', '', text)
        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def main():
    import sys
    
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        agent = ZeroClawAIAgent()
        result = agent.chat(message)
        print(json.dumps(result, indent=2))
    else:
        agent = ZeroClawAIAgent()
        history = []
        
        print("🤖 ZeroClaw AI Trading Agent")
        print("Type 'quit' to exit, 'help' for commands")
        print("-" * 50)
        
        while True:
            try:
                message = input("\nYou: ").strip()
                if message.lower() in ['quit', 'exit']:
                    break
                if message.lower() == 'help':
                    print("\nCommands:")
                    print("  buy BTC 0.01    - Buy Bitcoin")
                    print("  sell ETH 0.5    - Sell Ethereum")
                    print("  price SOL       - Check Solana price")
                    print("  portfolio       - View portfolio")
                    print("  arbitrage       - Scan for opportunities")
                    print("  bots            - List trading bots")
                    continue
                if not message:
                    continue
                
                result = agent.chat(message, history)
                print(f"\n🤖 {result['response']}")
                
                if result.get('tool_used'):
                    print(f"\n[Tool used: {result['tool_used']}]")
                
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": result['response']})
                
                if len(history) > 10:
                    history = history[-10:]
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break


if __name__ == "__main__":
    main()
