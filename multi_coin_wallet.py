#!/usr/bin/env python3
"""
Multi-Coin Wallet Module
========================
Supports multiple blockchains:
- Solana (enabled by default)
- Ethereum (configurable)
- Bitcoin (configurable)
- Binance Smart Chain (configurable)

Provides unified interface for:
- Balance checking
- Transaction sending
- Address management
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import os


@dataclass
class TokenBalance:
    """Represents a token balance"""
    symbol: str
    balance: float
    decimals: int
    price_usd: Optional[float] = None
    
    @property
    def value_usd(self) -> float:
        if self.price_usd:
            return self.balance * self.price_usd
        return 0.0


@dataclass
class WalletInfo:
    """Wallet information for a specific chain"""
    chain: str
    address: Optional[str]
    connected: bool
    balances: List[TokenBalance]
    
    @property
    def total_value_usd(self) -> float:
        return sum(b.value_usd for b in self.balances)


class BaseWallet(ABC):
    """Abstract base class for all wallet implementations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)
    
    @abstractmethod
    def get_address(self) -> Optional[str]:
        """Get wallet address"""
        pass
    
    @abstractmethod
    def get_balances(self) -> List[TokenBalance]:
        """Get all token balances"""
        pass
    
    @abstractmethod
    def get_balance(self, token: str) -> float:
        """Get specific token balance"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if wallet is connected and ready"""
        pass
    
    @abstractmethod
    def send_transaction(self, to: str, amount: float, token: str) -> Optional[str]:
        """Send a transaction, returns tx hash or None"""
        pass


class SolanaWallet(BaseWallet):
    """Solana wallet implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.rpc_url = config.get("rpc_url", "https://api.mainnet-beta.solana.com")
        self._address = None
        self._load_wallet()
    
    def _load_wallet(self):
        """Load wallet from file"""
        try:
            if os.path.exists("solana_wallet_live.json"):
                with open("solana_wallet_live.json", "r") as f:
                    wallet_data = json.load(f)
                    self._address = wallet_data.get("public_key")
                    self._balance_sol = wallet_data.get("balance_sol", 0)
                    self._balance_usdc = wallet_data.get("balance_usdc", 0)
        except Exception as e:
            print(f"[SolanaWallet] Error loading wallet: {e}")
    
    def get_address(self) -> Optional[str]:
        return self._address
    
    def get_balances(self) -> List[TokenBalance]:
        balances = []
        if self._address:
            balances.append(TokenBalance("SOL", self._balance_sol, 9))
            balances.append(TokenBalance("USDC", self._balance_usdc, 6))
        return balances
    
    def get_balance(self, token: str) -> float:
        if token.upper() == "SOL":
            return self._balance_sol
        elif token.upper() == "USDC":
            return self._balance_usdc
        return 0.0
    
    def is_connected(self) -> bool:
        return self._address is not None
    
    def send_transaction(self, to: str, amount: float, token: str) -> Optional[str]:
        # This would integrate with solathon for actual transaction signing
        print(f"[SolanaWallet] Would send {amount} {token} to {to}")
        return None


class EthereumWallet(BaseWallet):
    """Ethereum/EVM wallet implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.rpc_url = config.get("rpc_url", "")
        self._address = config.get("address")
        self._private_key = config.get("private_key")
    
    def get_address(self) -> Optional[str]:
        return self._address
    
    def get_balances(self) -> List[TokenBalance]:
        # Would use web3.py to fetch real balances
        return [
            TokenBalance("ETH", 0.0, 18),
            TokenBalance("USDC", 0.0, 6),
        ]
    
    def get_balance(self, token: str) -> float:
        return 0.0  # Placeholder
    
    def is_connected(self) -> bool:
        return self._address is not None and self.rpc_url != ""
    
    def send_transaction(self, to: str, amount: float, token: str) -> Optional[str]:
        print(f"[EthereumWallet] Would send {amount} {token} to {to}")
        return None


class BSCWallet(BaseWallet):
    """Binance Smart Chain wallet implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.rpc_url = config.get("rpc_url", "https://bsc-dataseed.binance.org")
        self._address = config.get("address")
    
    def get_address(self) -> Optional[str]:
        return self._address
    
    def get_balances(self) -> List[TokenBalance]:
        return [
            TokenBalance("BNB", 0.0, 18),
            TokenBalance("USDT", 0.0, 18),
        ]
    
    def get_balance(self, token: str) -> float:
        return 0.0
    
    def is_connected(self) -> bool:
        return self._address is not None
    
    def send_transaction(self, to: str, amount: float, token: str) -> Optional[str]:
        print(f"[BSCWallet] Would send {amount} {token} to {to}")
        return None


class MultiCoinWalletManager:
    """Manages multiple wallet connections"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.wallets: Dict[str, BaseWallet] = {}
        self._load_config()
        self._init_wallets()
    
    def _load_config(self):
        """Load wallet configuration"""
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                self.wallet_config = config.get("wallets", {})
        except:
            self.wallet_config = {
                "solana": {"enabled": True, "supported_tokens": ["SOL", "USDC", "USDT"]},
                "ethereum": {"enabled": False},
                "binance_smart_chain": {"enabled": False}
            }
    
    def _init_wallets(self):
        """Initialize enabled wallets"""
        for chain, config in self.wallet_config.items():
            if not config.get("enabled", False):
                continue
            
            try:
                if chain == "solana":
                    self.wallets[chain] = SolanaWallet(config)
                elif chain == "ethereum":
                    self.wallets[chain] = EthereumWallet(config)
                elif chain == "binance_smart_chain":
                    self.wallets[chain] = BSCWallet(config)
                print(f"[MultiCoinWallet] Initialized {chain} wallet")
            except Exception as e:
                print(f"[MultiCoinWallet] Failed to init {chain}: {e}")
    
    def get_wallet(self, chain: str) -> Optional[BaseWallet]:
        """Get a specific wallet by chain"""
        return self.wallets.get(chain)
    
    def get_all_balances(self) -> Dict[str, WalletInfo]:
        """Get balances for all connected wallets"""
        result = {}
        for chain, wallet in self.wallets.items():
            if wallet.is_connected():
                result[chain] = WalletInfo(
                    chain=chain,
                    address=wallet.get_address(),
                    connected=True,
                    balances=wallet.get_balances()
                )
        return result
    
    def is_funded(self, min_balance: float = 0.01) -> bool:
        """Check if any wallet has funds"""
        for wallet in self.wallets.values():
            if wallet.is_connected():
                for balance in wallet.get_balances():
                    if balance.balance > min_balance:
                        return True
        return False
    
    def get_primary_address(self) -> Optional[str]:
        """Get primary wallet address (Solana first)"""
        # Prefer Solana
        if "solana" in self.wallets:
            addr = self.wallets["solana"].get_address()
            if addr:
                return addr
        
        # Fall back to first available
        for wallet in self.wallets.values():
            addr = wallet.get_address()
            if addr:
                return addr
        
        return None
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get complete portfolio summary"""
        total_value = 0.0
        chain_summaries = {}
        
        for chain, wallet_info in self.get_all_balances().items():
            chain_value = wallet_info.total_value_usd
            total_value += chain_value
            chain_summaries[chain] = {
                "address": wallet_info.address[:20] + "..." if wallet_info.address else None,
                "tokens": [
                    {
                        "symbol": b.symbol,
                        "balance": round(b.balance, 6),
                        "value_usd": round(b.value_usd, 2)
                    }
                    for b in wallet_info.balances
                ],
                "total_usd": round(chain_value, 2)
            }
        
        return {
            "total_usd": round(total_value, 2),
            "chains": chain_summaries,
            "is_funded": total_value > 1.0
        }


def get_wallet_manager() -> MultiCoinWalletManager:
    """Get singleton wallet manager instance"""
    return MultiCoinWalletManager()


if __name__ == "__main__":
    print("Multi-Coin Wallet Module - Test Mode")
    print("=" * 60)
    
    manager = get_wallet_manager()
    
    print("\nConnected Wallets:")
    for chain, wallet in manager.wallets.items():
        status = "✅" if wallet.is_connected() else "❌"
        print(f"  {status} {chain.upper()}: {wallet.get_address() or 'Not connected'}")
    
    print("\nPortfolio Summary:")
    summary = manager.get_portfolio_summary()
    print(f"  Total Value: ${summary['total_usd']}")
    print(f"  Funded: {'Yes' if summary['is_funded'] else 'No'}")
    
    for chain, data in summary['chains'].items():
        print(f"\n  {chain.upper()}:")
        print(f"    Address: {data['address']}")
        for token in data['tokens']:
            print(f"    {token['symbol']}: {token['balance']} (${token['value_usd']})")
