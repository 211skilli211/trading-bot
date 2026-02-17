#!/usr/bin/env python3
"""
Full Auto Solana DEX - Proot/Ubuntu Version
Uses solathon for complete transaction signing
Requires: proot-distro Ubuntu with solders/solathon installed
"""

import os
import base64
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    from solathon import Client, Keypair, Transaction
    from solathon.core.types import Commitment
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    print("[SolanaDEX] solathon not installed. Run: pip install solathon")
    print("[SolanaDEX] Or use solana_simple.py for basic functionality")


# Constants
JUPITER_QUOTE = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP = "https://quote-api.jup.ag/v6/swap"

TOKENS = {
    'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    'USDT': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',
    'SOL': 'So11111111111111111111111111111111111111112',
    'BTC': '3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmLJ',
    'ETH': '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs',
    'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
}


class SolanaDEXFull:
    """
    Full automatic Solana DEX trading.
    Works inside proot-distro Ubuntu with solathon.
    """
    
    def __init__(self, rpc_url: Optional[str] = None):
        """Initialize with optional custom RPC."""
        if not SOLANA_AVAILABLE:
            raise RuntimeError("solathon not available")
        
        self.rpc_url = rpc_url or os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        self.client = Client(self.rpc_url)
        
        # Load keypair
        priv_key = os.getenv('SOLANA_PRIVATE_KEY')
        if priv_key:
            self.keypair = Keypair.from_base58_string(priv_key)
            self.wallet = str(self.keypair.public_key)
            print(f"[SolanaDEX] Wallet: {self.wallet[:20]}...")
        else:
            self.keypair = None
            self.wallet = None
            print("[SolanaDEX] No key - read only")
        
        self.swaps = 0
    
    def get_balance(self) -> Optional[float]:
        """Get SOL balance."""
        if not self.wallet:
            return None
        try:
            bal = self.client.get_balance(self.keypair.public_key)
            return bal / 1e9 if bal else 0.0
        except Exception as e:
            print(f"[SolanaDEX] Balance error: {e}")
            return None
    
    def get_quote(self, input_mint: str, output_mint: str, amount: int, slippage: int = 50) -> Optional[Dict]:
        """Get Jupiter quote."""
        try:
            r = requests.get(JUPITER_QUOTE, params={
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": slippage
            }, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[SolanaDEX] Quote error: {e}")
            return None
    
    def execute_swap(self, quote: Dict, priority_fee: int = 15000, dry_run: bool = False) -> Optional[str]:
        """
        Execute swap with full auto signing.
        
        Args:
            quote: Jupiter quote response
            priority_fee: Priority fee in micro-lamports
            dry_run: If True, don't send transaction
        
        Returns:
            Transaction signature
        """
        if not self.keypair:
            print("[SolanaDEX] No keypair")
            return None
        
        if dry_run:
            print("[SolanaDEX] DRY RUN")
            return "DRY_RUN"
        
        try:
            # Build swap transaction
            payload = {
                "quoteResponse": quote,
                "userPublicKey": self.wallet,
                "wrapAndUnwrapSol": True,
                "computeUnitPriceMicroLamports": priority_fee
            }
            
            r = requests.post(JUPITER_SWAP, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            # Decode transaction
            raw_tx = base64.b64decode(data["swapTransaction"])
            
            # Sign with solathon
            tx = Transaction.from_bytes(raw_tx)
            signed = tx.sign([self.keypair])
            
            # Send
            sig = self.client.send_transaction(signed, commitment=Commitment.FINALIZED)
            
            self.swaps += 1
            print(f"[SolanaDEX] ✅ Swap: {sig[:20]}...")
            print(f"[SolanaDEX] Explorer: https://solscan.io/tx/{sig}")
            
            return sig
            
        except Exception as e:
            print(f"[SolanaDEX] Swap failed: {e}")
            return None
    
    def find_arbitrage(self, start: str = 'USDC', amount: float = 20.0) -> List[Dict]:
        """Find triangular arbitrage."""
        if start not in TOKENS:
            return []
        
        opportunities = []
        start_mint = TOKENS[start]
        decimals = 6 if start in ['USDC', 'USDT'] else 9
        amount_raw = int(amount * (10 ** decimals))
        
        paths = [
            ['USDC', 'SOL', 'USDC'],
            ['USDC', 'BTC', 'USDC'],
            ['USDT', 'SOL', 'USDT'],
        ]
        
        for path in paths:
            if path[0] != start:
                continue
            
            q1 = self.get_quote(TOKENS[path[0]], TOKENS[path[1]], amount_raw)
            if not q1:
                continue
            
            q2 = self.get_quote(TOKENS[path[1]], TOKENS[path[2]], int(q1['outAmount']))
            if not q2:
                continue
            
            out_decimals = 6 if path[2] in ['USDC', 'USDT'] else 9
            final = int(q2['outAmount']) / (10 ** out_decimals)
            profit = final - amount
            profit_pct = (profit / amount) * 100
            
            opportunities.append({
                'path': path,
                'input': amount,
                'output': final,
                'profit': profit,
                'profit_pct': profit_pct,
                'viable': profit_pct > 0.5
            })
        
        return sorted(opportunities, key=lambda x: x['profit_pct'], reverse=True)


if __name__ == "__main__":
    print("Solana DEX Full Auto - Test")
    print("=" * 50)
    
    if not SOLANA_AVAILABLE:
        print("❌ solathon not installed")
        exit(1)
    
    dex = SolanaDEXFull()
    
    # Test balance
    bal = dex.get_balance()
    if bal is not None:
        print(f"Balance: {bal:.4f} SOL")
    
    # Test quote
    quote = dex.get_quote(TOKENS['USDC'], TOKENS['SOL'], 10_000_000)
    if quote:
        print(f"Quote: {int(quote['outAmount']) / 1e9:.6f} SOL for 10 USDC")
    
    print("\n✅ Ready for full auto trading!")
