import { useState } from 'react';

interface CryptoIconProps {
  symbol: string;
  size?: number;
  className?: string;
}

// Map common symbols to CoinGecko IDs for images
const symbolMap: Record<string, string> = {
  'BTC': 'bitcoin',
  'ETH': 'ethereum',
  'SOL': 'solana',
  'BNB': 'binancecoin',
  'ADA': 'cardano',
  'XRP': 'ripple',
  'DOT': 'polkadot',
  'DOGE': 'dogecoin',
  'AVAX': 'avalanche-2',
  'LINK': 'chainlink',
  'MATIC': 'matic-network',
  'LTC': 'litecoin',
  'UNI': 'uniswap',
  'ATOM': 'cosmos',
  'ETC': 'ethereum-classic',
  'XLM': 'stellar',
  'ALGO': 'algorand',
  'VET': 'vechain',
  'FIL': 'filecoin',
  'TRX': 'tron',
  'NEAR': 'near',
  'AAVE': 'aave',
  'SUSHI': 'sushi',
  'COMP': 'compound-governance-token',
  'MKR': 'maker',
  'YFI': 'yearn-finance',
  'SNX': 'havven',
  'CRV': 'curve-dao-token',
  '1INCH': '1inch',
  'GRT': 'the-graph',
  'BAT': 'basic-attention-token',
  'ENJ': 'enjincoin',
  'MANA': 'decentraland',
  'SAND': 'the-sandbox',
  'AXS': 'axie-infinity',
  'CHZ': 'chiliz',
  'HOT': 'holotoken',
  'BTT': 'bittorrent',
  'SHIB': 'shiba-inu',
  'TON': 'the-open-network',
  'APT': 'aptos',
  'SUI': 'sui',
  'BCH': 'bitcoin-cash',
  'USDT': 'tether',
  'USDC': 'usd-coin',
  'DAI': 'dai',
  'BUSD': 'binance-usd',
};

// Color schemes for fallback
const colorSchemes: Record<string, string> = {
  'BTC': '#F7931A',
  'ETH': '#627EEA',
  'SOL': '#14F195',
  'BNB': '#F3BA2F',
  'ADA': '#0033AD',
  'XRP': '#23292F',
  'DOT': '#E6007A',
  'DOGE': '#C2A633',
  'AVAX': '#E84142',
  'LINK': '#2A5ADA',
  'MATIC': '#8247E5',
  'LTC': '#BFBBBB',
  'UNI': '#FF007A',
  'ATOM': '#2E3148',
  'ETC': '#328332',
  'XLM': '#080808',
  'ALGO': '#000000',
  'VET': '#15BDFF',
  'FIL': '#0090FF',
  'TRX': '#FF060A',
  'NEAR': '#000000',
  'AAVE': '#B6509E',
  'SUSHI': '#FA52A0',
  'COMP': '#00D395',
  'MKR': '#1AAB9B',
  'YFI': '#006AE3',
  'SNX': '#00D1FF',
  'CRV': '#FF4040',
  '1INCH': '#1C324F',
  'GRT': '#6747ED',
  'BAT': '#FF5000',
  'ENJ': '#624DBF',
  'MANA': '#FF2D55',
  'SAND': '#00AEEF',
  'AXS': '#0055D5',
  'CHZ': '#EF4123',
  'HOT': '#AC443C',
  'BTT': '#000000',
  'SHIB': '#E8E8E8',
  'TON': '#0088CC',
  'APT': '#000000',
  'SUI': '#4DA2FF',
  'BCH': '#8DC351',
  'USDT': '#26A17B',
  'USDC': '#2775CA',
  'DAI': '#F5AC37',
  'BUSD': '#F0B90B',
};

export function CryptoIcon({ symbol, size = 32, className = '' }: CryptoIconProps) {
  const [error, setError] = useState(false);
  
  // Extract base symbol (e.g., "BTC" from "BTC/USDT")
  const baseSymbol = symbol.split('/')[0];
  const coinId = symbolMap[baseSymbol];
  const bgColor = colorSchemes[baseSymbol] || '#3B82F6';
  
  if (error || !coinId) {
    // Fallback to colored circle with letter
    return (
      <div
        className={`rounded-full flex items-center justify-center font-bold text-white ${className}`}
        style={{ 
          width: size, 
          height: size, 
          backgroundColor: bgColor,
          fontSize: size * 0.4
        }}
      >
        {baseSymbol.slice(0, 2)}
      </div>
    );
  }
  
  return (
    <img
      src={`https://assets.coincap.io/assets/icons/${baseSymbol.toLowerCase()}@2x.png`}
      alt={baseSymbol}
      className={`rounded-full ${className}`}
      style={{ width: size, height: size, objectFit: 'cover' }}
      onError={() => setError(true)}
    />
  );
}
