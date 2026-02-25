import { useEffect, useState } from 'react';
import { useWallet, useConnection } from '@solana/wallet-adapter-react';
import { PublicKey } from '@solana/web3.js';

export interface TokenBalance {
  symbol: string;
  name: string;
  mint: string;
  balance: number;
  decimals: number;
  usdValue?: number;
  logoURI?: string;
}

// Common Solana tokens
const KNOWN_TOKENS: Record<string, { symbol: string; name: string; decimals: number; logoURI: string }> = {
  'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': {
    symbol: 'USDC',
    name: 'USD Coin',
    decimals: 6,
    logoURI: 'https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/logo.png'
  },
  'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB': {
    symbol: 'USDT',
    name: 'Tether',
    decimals: 6,
    logoURI: 'https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB/logo.svg'
  },
  'So11111111111111111111111111111111111111112': {
    symbol: 'SOL',
    name: 'Solana',
    decimals: 9,
    logoURI: 'https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png'
  },
  'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263': {
    symbol: 'BONK',
    name: 'Bonk',
    decimals: 5,
    logoURI: 'https://arweave.net/hQiPZOsRZXGXBJd_82PhVdlM_hACsT_q6wqh5nbdhxw'
  },
  '7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARo': {
    symbol: 'stSOL',
    name: 'Lido Staked SOL',
    decimals: 9,
    logoURI: 'https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARo/logo.png'
  },
  'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So': {
    symbol: 'mSOL',
    name: 'Marinade Staked SOL',
    decimals: 9,
    logoURI: 'https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So/logo.png'
  },
  'J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn': {
    symbol: 'JitoSOL',
    name: 'Jito Staked SOL',
    decimals: 9,
    logoURI: 'https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn/logo.png'
  },
};

export function useWalletTokens() {
  const { connection } = useConnection();
  const { publicKey, connected } = useWallet();
  const [tokens, setTokens] = useState<TokenBalance[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalValue, setTotalValue] = useState(0);

  useEffect(() => {
    if (!connected || !publicKey || !connection) {
      setTokens([]);
      setTotalValue(0);
      return;
    }

    const fetchTokens = async () => {
      setLoading(true);
      try {
        // Get SOL balance
        const solBalance = await connection.getBalance(publicKey);
        const solToken: TokenBalance = {
          symbol: 'SOL',
          name: 'Solana',
          mint: 'So11111111111111111111111111111111111111112',
          balance: solBalance / 1e9,
          decimals: 9,
          logoURI: KNOWN_TOKENS['So11111111111111111111111111111111111111112'].logoURI,
        };

        // Get all token accounts
        const tokenAccounts = await connection.getParsedTokenAccountsByOwner(
          publicKey,
          { programId: new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA') }
        );

        const tokenBalances: TokenBalance[] = [solToken];

        // Parse token accounts
        for (const { account } of tokenAccounts.value) {
          const parsedInfo = account.data.parsed.info;
          const mint = parsedInfo.mint;
          const balance = parsedInfo.tokenAmount.uiAmount;
          const decimals = parsedInfo.tokenAmount.decimals;

          if (balance > 0) {
            const knownToken = KNOWN_TOKENS[mint];
            if (knownToken) {
              tokenBalances.push({
                symbol: knownToken.symbol,
                name: knownToken.name,
                mint,
                balance,
                decimals,
                logoURI: knownToken.logoURI,
              });
            } else {
              // Unknown token - add with minimal info
              tokenBalances.push({
                symbol: mint.slice(0, 4) + '...',
                name: 'Unknown Token',
                mint,
                balance,
                decimals,
              });
            }
          }
        }

        // Sort by balance (descending)
        tokenBalances.sort((a, b) => b.balance - a.balance);

        setTokens(tokenBalances);
        
        // Calculate total value (mock prices for now)
        const mockPrices: Record<string, number> = {
          'SOL': 145,
          'USDC': 1,
          'USDT': 1,
          'BONK': 0.00001,
          'stSOL': 155,
          'mSOL': 160,
          'JitoSOL': 158,
        };

        const total = tokenBalances.reduce((sum, token) => {
          const price = mockPrices[token.symbol] || 0;
          return sum + (token.balance * price);
        }, 0);
        
        setTotalValue(total);
      } catch (error) {
        console.error('Failed to fetch tokens:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTokens();
    const interval = setInterval(fetchTokens, 15000); // Refresh every 15s
    return () => clearInterval(interval);
  }, [connected, publicKey, connection]);

  return { tokens, loading, totalValue };
}
