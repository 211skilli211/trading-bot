#!/usr/bin/env python3
"""
WebSocket Real-Time Feeds for Solana
Ultra-fast price updates via Solana RPC WebSocket
"""

import asyncio
import websockets
import json
from typing import Callable, Optional
from datetime import datetime, timezone


class SolanaWebSocket:
    """
    Solana WebSocket connection for real-time updates.
    Subscribes to Jupiter swaps, Raydium pools, and account changes.
    """
    
    JUPITER_PROGRAM_ID = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
    RAYDIUM_AMM_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    
    def __init__(self, rpc_url: str = "wss://api.mainnet-beta.solana.com"):
        """
        Initialize WebSocket connection.
        
        Args:
            rpc_url: Solana WebSocket endpoint (use Helius/QuickNode for faster)
        """
        self.rpc_url = rpc_url
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.subscriptions = {}
        self.callbacks = {}
        self.running = False
        
        print(f"[WebSocket] Initialized: {rpc_url[:50]}...")
    
    async def connect(self):
        """Establish WebSocket connection."""
        try:
            self.ws = await websockets.connect(self.rpc_url)
            print("[WebSocket] Connected!")
            return True
        except Exception as e:
            print(f"[WebSocket] Connection failed: {e}")
            return False
    
    async def subscribe_jupiter_swaps(self, callback: Callable):
        """Subscribe to Jupiter swap transactions."""
        subscription = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [self.JUPITER_PROGRAM_ID]},
                {"commitment": "confirmed"}
            ]
        }
        
        await self.ws.send(json.dumps(subscription))
        self.callbacks['jupiter'] = callback
        print("[WebSocket] Subscribed to Jupiter swaps")
    
    async def subscribe_price_updates(self, token_address: str, callback: Callable):
        """Subscribe to token account changes (price updates)."""
        subscription = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "accountSubscribe",
            "params": [
                token_address,
                {"commitment": "confirmed", "encoding": "base64"}
            ]
        }
        
        await self.ws.send(json.dumps(subscription))
        self.callbacks[f'price_{token_address}'] = callback
        print(f"[WebSocket] Subscribed to price updates: {token_address[:20]}...")
    
    async def listen(self):
        """Main listen loop."""
        self.running = True
        
        while self.running:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                # Handle subscription responses
                if 'result' in data:
                    sub_id = data.get('result')
                    if 'id' in data:
                        self.subscriptions[data['id']] = sub_id
                    continue
                
                # Handle notifications
                if 'method' in data and data['method'] == 'logsNotification':
                    if 'jupiter' in self.callbacks:
                        await self.callbacks['jupiter'](data['params']['result'])
                
                if 'method' in data and data['method'] == 'accountNotification':
                    sub_id = data['params']['subscription']
                    for key, callback in self.callbacks.items():
                        if key.startswith('price_'):
                            await callback(data['params']['result'])
                
            except websockets.exceptions.ConnectionClosed:
                print("[WebSocket] Connection closed, reconnecting...")
                await asyncio.sleep(5)
                await self.connect()
            except Exception as e:
                print(f"[WebSocket] Error: {e}")
                await asyncio.sleep(1)
    
    async def close(self):
        """Close WebSocket connection."""
        self.running = False
        if self.ws:
            await self.ws.close()
            print("[WebSocket] Disconnected")


class PriceAggregator:
    """
    Aggregates prices from multiple WebSocket sources.
    Maintains order book state for arbitrage detection.
    """
    
    def __init__(self):
        self.prices = {}
        self.order_books = {}
        self.last_update = {}
    
    async def handle_jupiter_swap(self, log_data: dict):
        """Process Jupiter swap log."""
        # Extract swap info from logs
        logs = log_data.get('value', {}).get('logs', [])
        
        for log in logs:
            if 'Swap' in log:
                timestamp = datetime.now(timezone.utc).isoformat()
                print(f"[PriceAgg] Jupiter swap detected at {timestamp}")
                # Parse swap details and update prices
                break
    
    async def handle_price_update(self, account_data: dict):
        """Process token account update."""
        # Update price cache
        pass
    
    def get_best_price(self, token: str, side: str = 'buy') -> Optional[float]:
        """Get best available price across DEXs."""
        if token in self.prices:
            return self.prices[token].get(side)
        return None


if __name__ == "__main__":
    print("WebSocket Feeds - Test Mode")
    print("=" * 60)
    
    async def test_websocket():
        ws = SolanaWebSocket()
        
        if await ws.connect():
            aggregator = PriceAggregator()
            
            # Subscribe to Jupiter
            await ws.subscribe_jupiter_swaps(aggregator.handle_jupiter_swap)
            
            print("\nListening for 30 seconds...")
            print("(Ctrl+C to stop)\n")
            
            # Listen for 30 seconds
            try:
                await asyncio.wait_for(ws.listen(), timeout=30)
            except asyncio.TimeoutError:
                print("\nTest complete")
            finally:
                await ws.close()
    
    # Run test
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\nStopped by user")
