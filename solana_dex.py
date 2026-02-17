#!/usr/bin/env python3
"""
Solana DEX Trading Module - Full Auto Execution
Uses solathon (pure Python, no Rust/solders)
Jupiter V6 API for swaps and quotes
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
    SOLATHON_AVAILABLE = True
except ImportError:
    SOLATHON_AVAILABLE = False
    print("[SolanaDEX] Warning: solathon not installed. Run: pip install solathon")


# Jupiter API endpoints
JUPITER_QUOTE = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP = "https://quote-api.jup.ag/v6/swap"

# Token mint addresses (Solana mainnet)
TOKENS = {
    'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    'USDT': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',
    'SOL': 'So11111111111111111111111111111111111111112',
    'BTC': '3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmLJ',
    'ETH': '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs',
    'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
}


@dataclass
class SwapRoute:
    """Jupiter swap route."""
    input_mint: str
    output_mint: str
    in_amount: int
    out_amount: int
    price_impact_pct: float
    route_plan: List[Dict]
    other_amount_threshold: int
    swap_mode: str
    slippage_bps: int


@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity."""
    timestamp: str
    path: List[str]
    symbols: List[str]
    input_amount: float
    expected_output: float
    profit_pct: float
    price_impact: float
    viable: bool


class SolanaDEX:
    """
    Solana DEX Trading with Jupiter + solathon.
    Full auto execution - no manual approval needed.
    """
    
    def __init__(self, rpc_url: Optional[str] = None, private_key: Optional[str] = None):
        """
        Initialize Solana DEX connector.
        
        Args:
            rpc_url: Solana RPC endpoint
            private_key: Base58 private key (or from env SOLANA_PRIVATE_KEY)
        """
        if not SOLATHON_AVAILABLE:
            raise RuntimeError("solathon not installed. Run: pip install solathon")
        
        # Initialize RPC client
        self.rpc_url = rpc_url or os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        self.client = Client(self.rpc_url)
        
        # Load keypair
        key_str = private_key or os.getenv('SOLANA_PRIVATE_KEY')
        if key_str:
            try:
                self.keypair = Keypair.from_base58_string(key_str)
                self.wallet_address = str(self.keypair.public_key)
                print(f"[SolanaDEX] Wallet loaded: {self.wallet_address}")
            except Exception as e:
                print(f"[SolanaDEX] Error loading key: {e}")
                self.keypair = None
                self.wallet_address = None
        else:
            print("[SolanaDEX] No private key - read-only mode")
            self.keypair = None
            self.wallet_address = None
        
        # Stats
        self.total_swaps = 0
        self.successful_swaps = 0
        self.total_fees_sol = 0.0
        
        print(f"[SolanaDEX] RPC: {self.rpc_url[:50]}...")
    
    def get_balance(self, token: str = 'SOL') -> Optional[float]:
        """Get wallet balance."""
        if not self.wallet_address:
            return None
        
        try:
            if token == 'SOL':
                balance = self.client.get_balance(self.keypair.public_key)
                return balance / 1e9 if balance else 0.0
            else:
                # SPL token balance would need token account lookup
                return 0.0
        except Exception as e:
            print(f"[SolanaDEX] Balance error: {e}")
            return None
    
    def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50
    ) -> Optional[SwapRoute]:
        """
        Get Jupiter swap quote.
        
        Args:
            input_mint: Input token mint
            output_mint: Output token mint
            amount: Amount in smallest unit
            slippage_bps: Slippage tolerance (50 = 0.5%)
        
        Returns:
            SwapRoute or None
        """
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": slippage_bps,
                "onlyDirectRoutes": False,
                "asLegacyTransaction": False
            }
            
            response = requests.get(JUPITER_QUOTE, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                print(f"[SolanaDEX] Quote error: {data['error']}")
                return None
            
            return SwapRoute(
                input_mint=data['inputMint'],
                output_mint=data['outputMint'],
                in_amount=int(data['inAmount']),
                out_amount=int(data['outAmount']),
                price_impact_pct=float(data.get('priceImpactPct', 0)),
                route_plan=data.get('routePlan', []),
                other_amount_threshold=int(data['otherAmountThreshold']),
                swap_mode=data.get('swapMode', 'ExactIn'),
                slippage_bps=slippage_bps
            )
            
        except Exception as e:
            print(f"[SolanaDEX] Quote failed: {e}")
            return None
    
    def execute_swap(
        self,
        route: SwapRoute,
        priority_fee_lamports: int = 10000,
        dry_run: bool = False
    ) -> Optional[str]:
        """
        Execute Jupiter swap with full auto signing.
        
        Args:
            route: SwapRoute from get_quote
            priority_fee_lamports: Priority fee for faster execution
            dry_run: If True, don't actually send transaction
        
        Returns:
            Transaction signature or None
        """
        if not self.keypair:
            print("[SolanaDEX] Cannot execute: no private key")
            return None
        
        if dry_run:
            print("[SolanaDEX] DRY RUN - Transaction not sent")
            return f"DRY_RUN_{self.total_swaps:04d}"
        
        try:
            # Build swap transaction
            payload = {
                "quoteResponse": {
                    "inputMint": route.input_mint,
                    "outputMint": route.output_mint,
                    "inAmount": str(route.in_amount),
                    "outAmount": str(route.out_amount),
                    "otherAmountThreshold": str(route.other_amount_threshold),
                    "swapMode": route.swap_mode,
                    "slippageBps": route.slippage_bps,
                    "platformFee": None,
                    "priceImpactPct": str(route.price_impact_pct),
                    "routePlan": route.route_plan,
                    "contextSlot": 0,
                    "timeTaken": 0
                },
                "userPublicKey": self.wallet_address,
                "wrapAndUnwrapSol": True,
                "computeUnitPriceMicroLamports": priority_fee_lamports,
                "dynamicComputeUnitLimit": True
            }
            
            print(f"[SolanaDEX] Building transaction...")
            response = requests.post(JUPITER_SWAP, json=payload, timeout=30)
            response.raise_for_status()
            swap_data = response.json()
            
            if 'error' in swap_data:
                print(f"[SolanaDEX] Swap error: {swap_data['error']}")
                return None
            
            # Decode and sign transaction
            raw_tx = base64.b64decode(swap_data['swapTransaction'])
            
            # Sign with solathon
            tx = Transaction.from_bytes(raw_tx)
            signed_tx = tx.sign([self.keypair])
            
            # Send transaction
            print(f"[SolanaDEX] Sending transaction...")
            signature = self.client.send_transaction(
                signed_tx,
                commitment=Commitment.FINALIZED
            )
            
            self.total_swaps += 1
            self.successful_swaps += 1
            
            print(f"[SolanaDEX] ✅ Swap executed!")
            print(f"  Signature: {signature}")
            print(f"  Explorer: https://solscan.io/tx/{signature}")
            
            return signature
            
        except Exception as e:
            print(f"[SolanaDEX] Execution failed: {e}")
            return None
    
    def find_triangular_arbitrage(
        self,
        start_token: str = 'USDC',
        amount: float = 20.0
    ) -> List[ArbitrageOpportunity]:
        """
        Find triangular arbitrage opportunities.
        Example: USDC -> SOL -> BTC -> USDC
        """
        if start_token not in TOKENS:
            print(f"[SolanaDEX] Unknown token: {start_token}")
            return []
        
        opportunities = []
        start_mint = TOKENS[start_token]
        decimals = 6 if start_token in ['USDC', 'USDT'] else 9
        amount_raw = int(amount * (10 ** decimals))
        
        print(f"[SolanaDEX] Scanning for triangular arb with {amount} {start_token}...")
        
        # Test common paths
        paths = [
            ['USDC', 'SOL', 'USDC'],
            ['USDC', 'BTC', 'USDC'],
            ['USDC', 'ETH', 'USDC'],
            ['USDC', 'BONK', 'USDC'],
            ['USDT', 'SOL', 'USDT'],
            ['USDT', 'BTC', 'USDT'],
        ]
        
        for path_symbols in paths:
            if path_symbols[0] != start_token:
                continue
            
            mint1 = TOKENS[path_symbols[0]]
            mint2 = TOKENS[path_symbols[1]]
            mint3 = TOKENS[path_symbols[2]]
            
            # Step 1
            quote1 = self.get_quote(mint1, mint2, amount_raw)
            if not quote1:
                continue
            
            # Step 2
            quote2 = self.get_quote(mint2, mint3, quote1.out_amount)
            if not quote2:
                continue
            
            # Calculate profit
            output_decimals = 6 if path_symbols[2] in ['USDC', 'USDT'] else 9
            final_amount = quote2.out_amount / (10 ** output_decimals)
            profit = final_amount - amount
            profit_pct = (profit / amount) * 100
            
            # Check viability (account for fees ~0.3% total)
            viable = profit_pct > 0.5
            
            opp = ArbitrageOpportunity(
                timestamp=datetime.now(timezone.utc).isoformat(),
                path=[mint1, mint2, mint3],
                symbols=path_symbols,
                input_amount=amount,
                expected_output=final_amount,
                profit_pct=profit_pct,
                price_impact=max(quote1.price_impact_pct, quote2.price_impact_pct),
                viable=viable
            )
            
            opportunities.append(opp)
            
            status = "✅ VIABLE" if viable else "❌"
            print(f"  {path_symbols[0]} -> {path_symbols[1]} -> {path_symbols[2]}: "
                  f"{profit_pct:+.3f}% {status}")
        
        return sorted(opportunities, key=lambda x: x.profit_pct, reverse=True)
    
    def print_summary(self):
        """Print trading summary."""
        print("\n" + "=" * 60)
        print("SOLANA DEX TRADING SUMMARY")
        print("=" * 60)
        print(f"Wallet: {self.wallet_address or 'Not connected'}")
        
        if self.wallet_address:
            balance = self.get_balance('SOL')
            if balance is not None:
                print(f"SOL Balance: {balance:.4f} SOL")
        
        print(f"Total Swaps: {self.total_swaps}")
        print(f"Successful: {self.successful_swaps}")
        print(f"Total Fees: {self.total_fees_sol:.4f} SOL")
        print("=" * 60)


if __name__ == "__main__":
    print("Solana DEX Module - Test Mode (solathon)")
    print("=" * 60)
    
    if not SOLATHON_AVAILABLE:
        print("\n❌ solathon not installed")
        print("Run: pip install solathon")
        exit(1)
    
    # Initialize without key (read-only)
    dex = SolanaDEX()
    
    # Test balance
    print("\n[Test 1] Check Balance")
    balance = dex.get_balance('SOL')
    if balance is not None:
        print(f"  Balance: {balance:.4f} SOL")
    
    # Test quote
    print("\n[Test 2] Get Quote: USDC -> SOL")
    quote = dex.get_quote(
        TOKENS['USDC'],
        TOKENS['SOL'],
        amount=10_000_000,  # 10 USDC
        slippage_bps=50
    )
    if quote:
        print(f"  Input: {quote.in_amount / 1e6} USDC")
        print(f"  Output: {quote.out_amount / 1e9:.6f} SOL")
        print(f"  Price Impact: {quote.price_impact_pct:.4f}%")
    
    # Test triangular arb
    print("\n[Test 3] Triangular Arbitrage Scan")
    opportunities = dex.find_triangular_arbitrage('USDC', amount=20.0)
    
    if opportunities:
        print(f"\n  Found {len(opportunities)} paths:")
        for opp in opportunities:
            print(f"    {' -> '.join(opp.symbols)}: {opp.profit_pct:+.3f}%")
    
    dex.print_summary()
