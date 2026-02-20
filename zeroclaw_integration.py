#!/usr/bin/env python3
"""
ZeroClaw Integration Bridge
============================
Connects the Python trading bot with ZeroClaw AI infrastructure.

Features:
- AI-powered predictions via ZeroClaw
- Telegram channel integration
- Shared SQLite memory
- Heartbeat task coordination
- Gateway API communication
"""

import requests
import sqlite3
import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ZeroClawIntegration:
    """
    Bridge between ZeroClaw AI and Python trading bot.
    
    ZeroClaw handles: AI, Telegram, memory, security
    Python bot handles: Price APIs, CCXT execution, dashboard
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize ZeroClaw integration.
        
        Args:
            config: Configuration dict with zeroclaw settings
        """
        self.config = config or self._load_config()
        
        # Gateway settings
        self.gateway_url = self.config.get('zeroclaw_gateway', 'http://127.0.0.1:3000')
        self.pairing_token = self.config.get('zeroclaw_pairing_token')
        
        # Database (shared with ZeroClaw)
        self.db_path = self.config.get('database', 'trades.db')
        
        # HTTP session
        self.session = requests.Session()
        if self.pairing_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.pairing_token}',
                'Content-Type': 'application/json'
            })
        
        # State
        self._available = None
        
        logger.info(f"[ZeroClaw] Initialized with gateway: {self.gateway_url}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('zeroclaw', {})
        except Exception as e:
            logger.warning(f"[ZeroClaw] Could not load config: {e}")
            return {}
    
    # =====================================================================
    # Connection & Health
    # =====================================================================
    
    def is_running(self) -> bool:
        """Check if ZeroClaw gateway is accessible"""
        if self._available is not None:
            return self._available
        
        try:
            resp = self.session.get(f'{self.gateway_url}/status', timeout=5)
            self._available = resp.status_code == 200
            return self._available
        except Exception as e:
            logger.debug(f"[ZeroClaw] Not running: {e}")
            self._available = False
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed ZeroClaw status"""
        if not self.is_running():
            return {
                'running': False,
                'error': 'ZeroClaw daemon not running',
                'help': 'Run: zeroclaw daemon'
            }
        
        try:
            resp = self.session.get(f'{self.gateway_url}/status', timeout=5)
            if resp.status_code == 200:
                return {'running': True, **resp.json()}
            else:
                return {'running': False, 'error': f'Status code: {resp.status_code}'}
        except Exception as e:
            return {'running': False, 'error': str(e)}
    
    # =====================================================================
    # AI Communication
    # =====================================================================
    
    def ask_ai(self, message: str, context: Optional[str] = None) -> str:
        """
        Send message to ZeroClaw AI and get response.
        
        Args:
            message: User query
            context: Optional context for the AI
            
        Returns:
            AI response text
        """
        if not self.is_running():
            return "ZeroClaw is not running. Start it with: zeroclaw daemon"
        
        try:
            payload = {'message': message}
            if context:
                payload['context'] = context
            
            resp = self.session.post(
                f'{self.gateway_url}/agent',
                json=payload,
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get('response', 'No response from AI')
            else:
                return f"Error: {resp.status_code} - {resp.text[:200]}"
                
        except Exception as e:
            logger.error(f"[ZeroClaw] AI request failed: {e}")
            return f"Error: {str(e)}"
    
    def trigger_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a ZeroClaw skill.
        
        Args:
            skill_name: Name of the skill to trigger
            params: Parameters for the skill
            
        Returns:
            Skill execution result
        """
        if not self.is_running():
            return {'error': 'ZeroClaw not running'}
        
        try:
            resp = self.session.post(
                f'{self.gateway_url}/skills/{skill_name}/trigger',
                json=params,
                timeout=60
            )
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {'error': f'HTTP {resp.status_code}', 'details': resp.text[:500]}
                
        except Exception as e:
            logger.error(f"[ZeroClaw] Skill trigger failed: {e}")
            return {'error': str(e)}
    
    # =====================================================================
    # Memory Operations
    # =====================================================================
    
    def save_to_memory(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Save data to ZeroClaw memory.
        
        Args:
            key: Memory key
            data: Data to store
            
        Returns:
            True if successful
        """
        if not self.is_running():
            return False
        
        try:
            resp = self.session.post(
                f'{self.gateway_url}/memory/store',
                json={'key': key, 'data': data},
                timeout=10
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[ZeroClaw] Memory save failed: {e}")
            return False
    
    def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search ZeroClaw memory.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of memory entries
        """
        if not self.is_running():
            return []
        
        try:
            resp = self.session.get(
                f'{self.gateway_url}/memory/search',
                params={'query': query, 'limit': limit},
                timeout=10
            )
            
            if resp.status_code == 200:
                return resp.json().get('results', [])
            return []
            
        except Exception as e:
            logger.error(f"[ZeroClaw] Memory search failed: {e}")
            return []
    
    def get_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get arbitrage opportunities from memory"""
        return self.search_memory('arbitrage opportunity', limit)
    
    # =====================================================================
    # Trading Bot Integration
    # =====================================================================
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get basic stats
            stats = {
                'total_trades': cursor.execute("SELECT COUNT(*) FROM trades").fetchone()[0],
                'total_pnl': cursor.execute("SELECT SUM(net_pnl) FROM trades").fetchone()[0] or 0,
                'winning_trades': cursor.execute("SELECT COUNT(*) FROM trades WHERE net_pnl > 0").fetchone()[0],
                'open_positions': cursor.execute("SELECT COUNT(*) FROM positions WHERE status='OPEN'").fetchone()[0],
            }
            
            # Calculate win rate
            if stats['total_trades'] > 0:
                stats['win_rate'] = stats['winning_trades'] / stats['total_trades'] * 100
            else:
                stats['win_rate'] = 0
            
            # Get recent trades
            recent_trades = cursor.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 5"
            ).fetchall()
            stats['recent_trades'] = [dict(row) for row in recent_trades]
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"[ZeroClaw] Portfolio fetch failed: {e}")
            return {'error': str(e)}
    
    def store_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        Store trade in shared SQLite database.
        
        Args:
            trade_data: Trade execution data
            
        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO trades (
                    timestamp, mode, strategy, buy_exchange, sell_exchange,
                    buy_price, sell_price, quantity, spread_pct, fees_paid,
                    net_pnl, latency_ms, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                trade_data.get('mode', 'PAPER'),
                trade_data.get('strategy', 'arbitrage'),
                trade_data.get('buy_exchange'),
                trade_data.get('sell_exchange'),
                trade_data.get('buy_price'),
                trade_data.get('sell_price'),
                trade_data.get('quantity'),
                trade_data.get('spread_pct'),
                trade_data.get('fees_paid'),
                trade_data.get('net_pnl'),
                trade_data.get('latency_ms'),
                trade_data.get('status', 'FILLED')
            ))
            
            conn.commit()
            conn.close()
            
            # Also save to ZeroClaw memory for AI context
            self.save_to_memory(f"trade_{trade_data.get('trade_id')}", trade_data)
            
            return True
            
        except Exception as e:
            logger.error(f"[ZeroClaw] Trade store failed: {e}")
            return False
    
    # =====================================================================
    # Telegram Integration
    # =====================================================================
    
    def send_telegram_alert(self, message: str, priority: str = 'normal') -> bool:
        """
        Send alert via ZeroClaw Telegram channel.
        
        Args:
            message: Alert message
            priority: Alert priority (low, normal, high)
            
        Returns:
            True if successful
        """
        if not self.is_running():
            logger.warning("[ZeroClaw] Cannot send Telegram alert - not running")
            return False
        
        try:
            # Send to ZeroClaw agent with alert prefix
            response = self.ask_ai(f"TELEGRAM_ALERT [{priority.upper()}]: {message}")
            return 'error' not in response.lower()
            
        except Exception as e:
            logger.error(f"[ZeroClaw] Telegram alert failed: {e}")
            return False
    
    # =====================================================================
    # Price & Opportunity APIs
    # =====================================================================
    
    def get_price_prediction(self, symbol: str) -> Dict[str, Any]:
        """
        Get AI price prediction from ZeroClaw.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Prediction data with confidence
        """
        query = f"""
        Analyze {symbol} price movement based on:
        1. Recent price action (last 24h)
        2. Market sentiment
        3. Technical indicators
        4. Similar historical patterns
        
        Provide prediction in JSON format:
        {{
            "direction": "up/down/sideways",
            "confidence": 0-100,
            "timeframe": "1h/4h/24h",
            "reasoning": "brief explanation"
        }}
        """
        
        response = self.ask_ai(query)
        
        # Try to parse JSON from response
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except:
            pass
        
        return {
            'direction': 'unknown',
            'confidence': 0,
            'reasoning': response[:200]
        }
    
    def scan_arbitrage(self) -> List[Dict[str, Any]]:
        """Trigger arbitrage scan skill"""
        result = self.trigger_skill('arbitrage-scan', {'manual': True})
        return result.get('opportunities', [])
    
    # =====================================================================
    # Utility Methods
    # =====================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive ZeroClaw statistics"""
        if not self.is_running():
            return {'running': False}
        
        try:
            resp = self.session.get(f'{self.gateway_url}/stats', timeout=5)
            if resp.status_code == 200:
                return {'running': True, **resp.json()}
            return {'running': False, 'error': f'Status {resp.status_code}'}
        except Exception as e:
            return {'running': False, 'error': str(e)}


def get_zeroclaw(config: Optional[Dict] = None) -> ZeroClawIntegration:
    """Get singleton ZeroClaw integration instance"""
    return ZeroClawIntegration(config)


if __name__ == "__main__":
    print("ZeroClaw Integration - Test Mode")
    print("=" * 60)
    
    zc = get_zeroclaw()
    
    print(f"\nGateway URL: {zc.gateway_url}")
    print(f"Pairing Token: {'✅ Set' if zc.pairing_token else '❌ Not set'}")
    print(f"Database: {zc.db_path}")
    
    print(f"\nZeroClaw Status: ", end="")
    if zc.is_running():
        print("✅ Running")
        
        # Test AI
        print("\nTesting AI...")
        response = zc.ask_ai("What is arbitrage trading? Keep it brief.")
        print(f"AI Response: {response[:200]}...")
        
        # Test portfolio
        print("\nFetching portfolio...")
        portfolio = zc.get_portfolio_summary()
        print(f"Portfolio: {portfolio}")
        
    else:
        print("❌ Not running")
        print("\nTo start ZeroClaw:")
        print("  zeroclaw daemon")
        print("\nTo configure:")
        print("  Edit ~/.zeroclaw/config.toml")
