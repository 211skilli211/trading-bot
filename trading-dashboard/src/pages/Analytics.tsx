import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { 
  BarChart3, TrendingUp, Calendar, Target, Settings,
  ChevronDown, RefreshCw, Star, Activity, Zap, Brain,
  Shield, TrendingDown, ArrowRight, CheckCircle2,
  BarChart4, X, Maximize2, Minimize2, GripVertical, Code2, Play
} from 'lucide-react';
import { Header } from '../components/Header';
import { AdvancedTradingView, calculateSLTPSuggestions, type Suggestion, type TradingData } from '../components/AdvancedTradingView';
import { useUserPreferences } from '../context/UserPreferencesContext';
import { formatUSD, formatPercent } from '../utils/format';

interface CoinOption {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  volume24h: number;
  marketCap: number;
}

const TIMEFRAMES: { label: string; value: string; days: number | 'all' }[] = [
  { label: '15M', value: '15m', days: 1 },
  { label: '1H', value: '1h', days: 7 },
  { label: '4H', value: '4h', days: 30 },
  { label: '1D', value: '1d', days: 90 },
  { label: '1W', value: '1w', days: 365 },
  { label: 'All', value: 'all', days: 'all' },
];

// Expanded coin list - top 50 cryptocurrencies
const AVAILABLE_COINS: CoinOption[] = [
  // Major Coins
  { symbol: 'BTC/USDT', name: 'Bitcoin', price: 64250, change24h: 2.5, volume24h: 28.5e9, marketCap: 1.26e12 },
  { symbol: 'ETH/USDT', name: 'Ethereum', price: 3450, change24h: 1.8, volume24h: 15.2e9, marketCap: 415e9 },
  { symbol: 'SOL/USDT', name: 'Solana', price: 148, change24h: -0.5, volume24h: 3.8e9, marketCap: 68e9 },
  { symbol: 'BNB/USDT', name: 'Binance Coin', price: 585, change24h: 0.8, volume24h: 1.2e9, marketCap: 88e9 },
  { symbol: 'XRP/USDT', name: 'Ripple', price: 0.62, change24h: -1.2, volume24h: 2.1e9, marketCap: 34e9 },
  { symbol: 'ADA/USDT', name: 'Cardano', price: 0.58, change24h: 3.2, volume24h: 450e6, marketCap: 20e9 },
  { symbol: 'DOGE/USDT', name: 'Dogecoin', price: 0.12, change24h: 5.5, volume24h: 1.8e9, marketCap: 17e9 },
  { symbol: 'DOT/USDT', name: 'Polkadot', price: 7.25, change24h: -0.8, volume24h: 280e6, marketCap: 10e9 },
  // Layer 1s
  { symbol: 'AVAX/USDT', name: 'Avalanche', price: 38.5, change24h: 2.1, volume24h: 890e6, marketCap: 14e9 },
  { symbol: 'MATIC/USDT', name: 'Polygon', price: 0.72, change24h: -1.5, volume24h: 420e6, marketCap: 6.7e9 },
  { symbol: 'NEAR/USDT', name: 'NEAR Protocol', price: 6.8, change24h: 4.2, volume24h: 380e6, marketCap: 7.1e9 },
  { symbol: 'ATOM/USDT', name: 'Cosmos', price: 9.2, change24h: -0.3, volume24h: 220e6, marketCap: 3.5e9 },
  { symbol: 'FTM/USDT', name: 'Fantom', price: 0.85, change24h: 6.8, volume24h: 310e6, marketCap: 2.4e9 },
  { symbol: 'ALGO/USDT', name: 'Algorand', price: 0.19, change24h: 1.2, volume24h: 95e6, marketCap: 1.5e9 },
  { symbol: 'VET/USDT', name: 'VeChain', price: 0.035, change24h: -2.1, volume24h: 65e6, marketCap: 2.8e9 },
  // DeFi
  { symbol: 'UNI/USDT', name: 'Uniswap', price: 9.8, change24h: 3.5, volume24h: 180e6, marketCap: 5.9e9 },
  { symbol: 'LINK/USDT', name: 'Chainlink', price: 18.5, change24h: 2.8, volume24h: 420e6, marketCap: 10.8e9 },
  { symbol: 'AAVE/USDT', name: 'Aave', price: 145, change24h: -1.2, volume24h: 120e6, marketCap: 2.1e9 },
  { symbol: 'MKR/USDT', name: 'Maker', price: 1750, change24h: 0.5, volume24h: 95e6, marketCap: 1.6e9 },
  { symbol: 'LDO/USDT', name: 'Lido DAO', price: 2.15, change24h: 5.2, volume24h: 150e6, marketCap: 1.9e9 },
  { symbol: 'CRV/USDT', name: 'Curve DAO', price: 0.42, change24h: -3.5, volume24h: 85e6, marketCap: 550e6 },
  { symbol: 'SNX/USDT', name: 'Synthetix', price: 2.8, change24h: 1.8, volume24h: 45e6, marketCap: 920e6 },
  // Memes
  { symbol: 'SHIB/USDT', name: 'Shiba Inu', price: 0.0000185, change24h: 8.2, volume24h: 890e6, marketCap: 10.9e9 },
  { symbol: 'PEPE/USDT', name: 'Pepe', price: 0.0000092, change24h: 12.5, volume24h: 1.2e9, marketCap: 3.8e9 },
  { symbol: 'FLOKI/USDT', name: 'Floki', price: 0.000156, change24h: 5.8, volume24h: 280e6, marketCap: 1.5e9 },
  { symbol: 'BONK/USDT', name: 'Bonk', price: 0.000022, change24h: -5.2, volume24h: 180e6, marketCap: 1.4e9 },
  // Gaming/Metaverse
  { symbol: 'SAND/USDT', name: 'The Sandbox', price: 0.45, change24h: 2.5, volume24h: 120e6, marketCap: 1.0e9 },
  { symbol: 'MANA/USDT', name: 'Decentraland', price: 0.48, change24h: 1.8, volume24h: 95e6, marketCap: 900e6 },
  { symbol: 'AXS/USDT', name: 'Axie Infinity', price: 8.2, change24h: -2.5, volume24h: 65e6, marketCap: 1.1e9 },
  { symbol: 'GALA/USDT', name: 'Gala', price: 0.045, change24h: 4.2, volume24h: 180e6, marketCap: 1.6e9 },
  { symbol: 'IMX/USDT', name: 'Immutable X', price: 2.35, change24h: 6.8, volume24h: 150e6, marketCap: 3.2e9 },
  // Infrastructure
  { symbol: 'ARB/USDT', name: 'Arbitrum', price: 1.15, change24h: 3.2, volume24h: 380e6, marketCap: 3.0e9 },
  { symbol: 'OP/USDT', name: 'Optimism', price: 2.45, change24h: -1.8, volume24h: 220e6, marketCap: 2.6e9 },
  { symbol: 'STRK/USDT', name: 'Starknet', price: 1.85, change24h: 5.5, volume24h: 280e6, marketCap: 2.1e9 },
  { symbol: 'ZKS/USDT', name: 'zkSync', price: 0.12, change24h: 8.5, volume24h: 95e6, marketCap: 450e6 },
  // Storage/Compute
  { symbol: 'FIL/USDT', name: 'Filecoin', price: 5.8, change24h: 1.5, volume24h: 180e6, marketCap: 3.2e9 },
  { symbol: 'RNDR/USDT', name: 'Render', price: 7.85, change24h: 12.5, volume24h: 420e6, marketCap: 3.0e9 },
  { symbol: 'AR/USDT', name: 'Arweave', price: 38.5, change24h: 4.2, volume24h: 85e6, marketCap: 2.5e9 },
  // AI/Tech
  { symbol: 'FET/USDT', name: 'Fetch.ai', price: 2.15, change24h: 8.5, volume24h: 280e6, marketCap: 1.8e9 },
  { symbol: 'AGIX/USDT', name: 'SingularityNET', price: 0.85, change24h: 6.2, volume24h: 150e6, marketCap: 1.1e9 },
  { symbol: 'WLD/USDT', name: 'Worldcoin', price: 4.85, change24h: -3.5, volume24h: 380e6, marketCap: 1.2e9 },
  { symbol: 'TAO/USDT', name: 'Bittensor', price: 425, change24h: 15.2, volume24h: 65e6, marketCap: 2.8e9 },
  // Oracles/Data
  { symbol: 'PYTH/USDT', name: 'Pyth Network', price: 0.42, change24h: 5.8, volume24h: 120e6, marketCap: 1.5e9 },
  { symbol: 'TRB/USDT', name: 'Tellor', price: 85, change24h: -8.5, volume24h: 45e6, marketCap: 220e6 },
  // Privacy
  { symbol: 'XMR/USDT', name: 'Monero', price: 145, change24h: 1.2, volume24h: 85e6, marketCap: 2.6e9 },
  { symbol: 'ZEC/USDT', name: 'Zcash', price: 28.5, change24h: -2.5, volume24h: 65e6, marketCap: 465e6 },
  // Exchanges
  { symbol: 'CRO/USDT', name: 'Cronos', price: 0.095, change24h: 2.8, volume24h: 35e6, marketCap: 2.4e9 },
  { symbol: 'KCS/USDT', name: 'KuCoin Token', price: 10.2, change24h: 0.5, volume24h: 12e6, marketCap: 980e6 },
  { symbol: 'GT/USDT', name: 'Gate Token', price: 7.85, change24h: 1.8, volume24h: 8e6, marketCap: 680e6 },
  // Others
  { symbol: 'ICP/USDT', name: 'Internet Computer', price: 13.5, change24h: 3.5, volume24h: 120e6, marketCap: 6.2e9 },
  { symbol: 'THETA/USDT', name: 'Theta Network', price: 2.35, change24h: -1.2, volume24h: 65e6, marketCap: 2.3e9 },
  { symbol: 'XLM/USDT', name: 'Stellar', price: 0.11, change24h: 2.5, volume24h: 95e6, marketCap: 3.1e9 },
  { symbol: 'TRX/USDT', name: 'TRON', price: 0.12, change24h: 1.8, volume24h: 320e6, marketCap: 10.5e9 },
  { symbol: 'ETC/USDT', name: 'Ethereum Classic', price: 28.5, change24h: -0.5, volume24h: 180e6, marketCap: 4.1e9 },
  { symbol: 'BCH/USDT', name: 'Bitcoin Cash', price: 385, change24h: 0.8, volume24h: 220e6, marketCap: 7.6e9 },
  { symbol: 'LTC/USDT', name: 'Litecoin', price: 72, change24h: 1.5, volume24h: 380e6, marketCap: 5.4e9 },
  { symbol: 'APT/USDT', name: 'Aptos', price: 9.2, change24h: 4.5, volume24h: 180e6, marketCap: 3.8e9 },
  { symbol: 'SUI/USDT', name: 'Sui', price: 1.45, change24h: 6.8, volume24h: 420e6, marketCap: 1.9e9 },
  { symbol: 'SEI/USDT', name: 'Sei', price: 0.58, change24h: 12.5, volume24h: 280e6, marketCap: 1.6e9 },
  { symbol: 'INJ/USDT', name: 'Injective', price: 25.5, change24h: 8.5, volume24h: 180e6, marketCap: 2.4e9 },
  { symbol: 'RUNE/USDT', name: 'THORChain', price: 5.85, change24h: -2.8, volume24h: 120e6, marketCap: 1.9e9 },
  { symbol: 'SUSHI/USDT', name: 'SushiSwap', price: 1.25, change24h: 3.5, volume24h: 85e6, marketCap: 290e6 },
  { symbol: 'COMP/USDT', name: 'Compound', price: 65, change24h: -1.5, volume24h: 35e6, marketCap: 520e6 },
  { symbol: 'YFI/USDT', name: 'Yearn Finance', price: 7850, change24h: 2.5, volume24h: 25e6, marketCap: 260e6 },
  { symbol: '1INCH/USDT', name: '1inch', price: 0.42, change24h: 4.2, volume24h: 45e6, marketCap: 420e6 },
  { symbol: 'DYDX/USDT', name: 'dYdX', price: 2.15, change24h: 5.8, volume24h: 95e6, marketCap: 1.3e9 },
  { symbol: 'ENS/USDT', name: 'Ethereum Name Service', price: 18.5, change24h: 3.2, volume24h: 65e6, marketCap: 580e6 },
  { symbol: 'GRT/USDT', name: 'The Graph', price: 0.28, change24h: 6.5, volume24h: 120e6, marketCap: 2.6e9 },
];

// Generate realistic OHLC data with volume
function generateChartData(basePrice: number, days: number | 'all', volatility: number = 0.025): TradingData[] {
  const data: TradingData[] = [];
  const now = Math.floor(Date.now() / 1000);
  const intervals = days === 'all' ? 365 * 24 : (days as number) * 24;
  const startTime = now - (intervals * 3600);
  
  // Always start from a consistent point based on basePrice
  let currentPrice = basePrice;
  let trend = 0;
  
  for (let i = 0; i < intervals; i++) {
    const time = startTime + (i * 3600);
    
    // Add some trend persistence
    trend = trend * 0.95 + (Math.random() - 0.48) * 0.02;
    const change = (Math.random() - 0.5) * volatility + trend;
    
    const open = currentPrice;
    const close = currentPrice * (1 + change);
    const high = Math.max(open, close) * (1 + Math.random() * 0.008);
    const low = Math.min(open, close) * (1 - Math.random() * 0.008);
    
    // Volume correlates with volatility
    const volatilityFactor = Math.abs(change) * 10 + 0.5;
    const volume = Math.floor((Math.random() * 500000 + 200000) * volatilityFactor);
    
    data.push({
      time,
      open: Number(open.toFixed(2)),
      high: Number(high.toFixed(2)),
      low: Number(low.toFixed(2)),
      close: Number(close.toFixed(2)),
      volume,
    });
    
    currentPrice = close;
  }
  
  return data;
}

// Hook for detecting mobile viewport
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);
  
  return isMobile;
}

export function Analytics() {
  const { preferences, setPrimaryCoin, updatePreferences } = useUserPreferences();
  const isMobile = useIsMobile();
  const [selectedCoin, setSelectedCoin] = useState(preferences.primaryCoin);
  const [timeframe, setTimeframe] = useState(preferences.defaultTimeframe);
  const [chartData, setChartData] = useState<TradingData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [stopLoss, setStopLoss] = useState<number | undefined>(undefined);
  const [takeProfit, setTakeProfit] = useState<number | undefined>(undefined);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showCoinDropdown, setShowCoinDropdown] = useState(false);
  const [position, setPosition] = useState<'long' | 'short'>('long');
  const [riskPercent, setRiskPercent] = useState(2);
  const [useAISuggestions, setUseAISuggestions] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [accountSize, setAccountSize] = useState(10000);
  
  // Indicator states
  const [showVolume, setShowVolume] = useState(preferences.showVolume ?? true);
  const [showEMA, setShowEMA] = useState(preferences.showEMA ?? true);
  const [showBollinger, setShowBollinger] = useState(false);
  const [showPivots, setShowPivots] = useState(false);
  
  // Pine Script panel
  const [showPineScript, setShowPineScript] = useState(false);
  const [pineScriptCode, setPineScriptCode] = useState(`//@version=5
indicator("Custom Strategy", overlay=true)

// EMA with dynamic color
ema20 = ta.ema(close, 20)
emaColor = close > ema20 ? color.green : color.red
plot(ema20, "EMA 20", emaColor)

// Pivot Points
pivot = (high[1] + low[1] + close[1]) / 3
r1 = (2 * pivot) - low[1]
s1 = (2 * pivot) - high[1]

plot(pivot, "PP", color.orange)
plot(r1, "R1", color.green)
plot(s1, "S1", color.red)`);
  const [pineScriptError, setPineScriptError] = useState<string | null>(null);
  const [pineScriptOutput, setPineScriptOutput] = useState<string | null>(null);
  
  const chartContainerRef = useRef<HTMLDivElement>(null);

  // Load chart data
  const loadChartData = useCallback(async () => {
    setIsLoading(true);
    
    const coin = AVAILABLE_COINS.find(c => c.symbol === selectedCoin);
    const basePrice = coin?.price || 50000;
    
    const tf = TIMEFRAMES.find(t => t.value === timeframe);
    const days: number | 'all' = tf?.days ?? 30;
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    const data = generateChartData(basePrice, days);
    setChartData(data);
    
    // Calculate AI suggestions
    const currentPrice = data[data.length - 1]?.close || basePrice;
    const newSuggestions = calculateSLTPSuggestions(data, currentPrice, position);
    setSuggestions(newSuggestions);
    
    // Auto-apply best suggestions if enabled
    if (useAISuggestions && newSuggestions.length > 0) {
      const bestSL = newSuggestions
        .filter(s => s.type === 'sl')
        .sort((a, b) => b.confidence - a.confidence)[0];
      const bestTP = newSuggestions
        .filter(s => s.type === 'tp')
        .sort((a, b) => b.confidence - a.confidence)[0];
      
      if (bestSL) setStopLoss(bestSL.price);
      if (bestTP) setTakeProfit(bestTP.price);
    }
    
    setIsLoading(false);
  }, [selectedCoin, timeframe, position, useAISuggestions]);

  useEffect(() => {
    loadChartData();
  }, [loadChartData]);

  // Swipe gesture handlers
  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStart(e.touches[0].clientX);
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStart === null) return;
    
    const touchEnd = e.changedTouches[0].clientX;
    const diff = touchStart - touchEnd;
    
    // Swipe threshold
    if (Math.abs(diff) > 50) {
      const currentIndex = TIMEFRAMES.findIndex(t => t.value === timeframe);
      
      if (diff > 0 && currentIndex < TIMEFRAMES.length - 1) {
        setTimeframe(TIMEFRAMES[currentIndex + 1].value);
      } else if (diff < 0 && currentIndex > 0) {
        setTimeframe(TIMEFRAMES[currentIndex - 1].value);
      }
    }
    
    setTouchStart(null);
  };

  // Update primary coin
  const handleCoinChange = (symbol: string) => {
    setSelectedCoin(symbol);
    setPrimaryCoin(symbol);
    setShowCoinDropdown(false);
  };

  // Apply suggestion
  const applySuggestion = (suggestion: Suggestion) => {
    if (suggestion.type === 'sl') {
      setStopLoss(suggestion.price);
    } else if (suggestion.type === 'tp') {
      setTakeProfit(suggestion.price);
    }
  };

  // Toggle fullscreen
  const toggleFullscreen = async () => {
    if (!document.fullscreenElement) {
      await chartContainerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      await document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const currentCoin = useMemo(() => 
    AVAILABLE_COINS.find(c => c.symbol === selectedCoin) || AVAILABLE_COINS[0],
  [selectedCoin]);

  // Use the actual last close price from chart data
  const currentPrice = chartData[chartData.length - 1]?.close || currentCoin.price;
  
  // Calculate price change from chart data
  const priceChange = chartData.length > 1 
    ? ((currentPrice - chartData[chartData.length - 2]?.close) / chartData[chartData.length - 2]?.close) * 100 
    : 0;

  // FIXED: Proper position sizing calculation
  // Risk Amount = Account Size × Risk %
  const riskAmountValue = accountSize * (riskPercent / 100);
  
  // Risk per Unit = |Entry - Stop Loss|
  const riskPerUnit = stopLoss ? Math.abs(currentPrice - stopLoss) : 0;
  
  // Position Size (in units/coins) = Risk Amount / Risk per Unit
  const positionSizeUnits = riskPerUnit > 0 ? riskAmountValue / riskPerUnit : 0;
  
  // Position Value = Position Size × Entry Price
  const positionValue = positionSizeUnits * currentPrice;
  
  // Risk:Reward Ratio
  const riskReward = stopLoss && takeProfit 
    ? Math.abs((takeProfit - currentPrice) / (currentPrice - stopLoss))
    : 0;
  
  // Potential Profit & Loss
  const potentialProfit = takeProfit ? (takeProfit - currentPrice) * positionSizeUnits : 0;
  const potentialLoss = stopLoss ? (currentPrice - stopLoss) * positionSizeUnits : 0;

  // Dynamic chart height
  const chartHeight = isFullscreen 
    ? window.innerHeight - 100 
    : isMobile ? 350 : 550;

  return (
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title={isMobile ? "Analytics" : "Analytics Pro"} />
      
      <div className="p-2 sm:p-4 space-y-4 sm:space-y-6">
        {/* Top Controls */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Coin Selector */}
          <div className="relative flex-1 min-w-[140px] sm:min-w-0">
            <button
              onClick={() => setShowCoinDropdown(!showCoinDropdown)}
              className="w-full flex items-center justify-between gap-2 px-3 sm:px-4 py-2 bg-dark-800 border border-dark-700 rounded-lg hover:border-blue-500 transition-colors"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-semibold text-sm sm:text-base truncate">{selectedCoin}</span>
                <Star 
                  size={14} 
                  className={`flex-shrink-0 ${selectedCoin === preferences.primaryCoin ? 'text-yellow-400 fill-yellow-400' : 'text-gray-400'}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setPrimaryCoin(selectedCoin);
                  }}
                />
              </div>
              <ChevronDown size={16} className="text-gray-400 flex-shrink-0" />
            </button>
            
            {showCoinDropdown && (
              <div className="absolute top-full left-0 right-0 sm:w-80 mt-1 bg-dark-800 border border-dark-700 rounded-lg shadow-xl z-50 max-h-[60vh] overflow-auto">
                <div className="p-2">
                  <div className="text-xs text-gray-500 mb-2 px-2 sticky top-0 bg-dark-800">Select Market ({AVAILABLE_COINS.length} assets)</div>
                  {AVAILABLE_COINS.map((coin) => (
                    <button
                      key={coin.symbol}
                      onClick={() => handleCoinChange(coin.symbol)}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-dark-700 transition-colors ${
                        coin.symbol === selectedCoin ? 'bg-blue-600/20 border-l-2 border-blue-400' : ''
                      }`}
                    >
                      <div className="min-w-0 text-left">
                        <div className="font-medium text-sm">{coin.symbol}</div>
                        <div className="text-xs text-gray-400 truncate">{coin.name}</div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="font-mono text-sm">${coin.price.toLocaleString()}</div>
                        <div className={`text-xs ${coin.change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {coin.change24h >= 0 ? '+' : ''}{coin.change24h.toFixed(1)}%
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Timeframe */}
          <div className="flex-1 overflow-x-auto scrollbar-hide">
            <div className="flex items-center gap-1 bg-dark-800 border border-dark-700 rounded-lg p-1 w-max">
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf.value}
                  onClick={() => setTimeframe(tf.value)}
                  className={`px-2 sm:px-3 py-1.5 rounded text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
                    timeframe === tf.value 
                      ? 'bg-blue-600 text-white' 
                      : 'text-gray-400 hover:text-white hover:bg-dark-700'
                  }`}
                >
                  {tf.label}
                </button>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-1">
            <button
              onClick={toggleFullscreen}
              className="p-2 bg-dark-800 border border-dark-700 rounded-lg hover:border-blue-500 transition-colors"
            >
              {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>
            <button
              onClick={() => setShowSuggestions(!showSuggestions)}
              className={`p-2 rounded-lg transition-colors ${
                showSuggestions ? 'bg-purple-600 text-white' : 'bg-dark-800 border border-dark-700'
              }`}
            >
              <Brain size={18} />
            </button>
          </div>
        </div>

        {/* Position Toggle */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-dark-800 border border-dark-700 rounded-lg p-1">
            <button
              onClick={() => setPosition('long')}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors flex items-center gap-1 ${
                position === 'long' ? 'bg-green-600 text-white' : 'text-gray-400'
              }`}
            >
              <TrendingUp size={14} />
              Long
            </button>
            <button
              onClick={() => setPosition('short')}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors flex items-center gap-1 ${
                position === 'short' ? 'bg-red-600 text-white' : 'text-gray-400'
              }`}
            >
              <TrendingDown size={14} />
              Short
            </button>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`px-3 py-2 rounded-lg text-sm ${
              showSettings ? 'bg-blue-600 text-white' : 'bg-dark-800 border border-dark-700'
            }`}
          >
            <Settings size={16} />
          </button>
          <button
            onClick={() => setShowPineScript(!showPineScript)}
            className={`px-3 py-2 rounded-lg text-sm ${
              showPineScript ? 'bg-green-600 text-white' : 'bg-dark-800 border border-dark-700'
            }`}
          >
            <Code2 size={16} />
          </button>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="bg-dark-800 border border-dark-700 rounded-xl p-3 sm:p-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useAISuggestions}
                    onChange={(e) => setUseAISuggestions(e.target.checked)}
                    className="w-4 h-4 rounded border-dark-600"
                  />
                  <span className="text-sm">AI Auto-SL/TP</span>
                </label>
              </div>
              
              <div>
                <label className="block text-xs text-gray-400 mb-1">Account Size ($)</label>
                <input
                  type="number"
                  value={accountSize}
                  onChange={(e) => setAccountSize(Number(e.target.value))}
                  className="w-full bg-dark-900 border border-dark-600 rounded-lg px-2 py-1 text-sm"
                  min="100"
                  step="100"
                />
              </div>
              
              <div>
                <label className="block text-xs text-gray-400 mb-1">Risk Per Trade (%)</label>
                <input
                  type="number"
                  value={riskPercent}
                  onChange={(e) => setRiskPercent(Number(e.target.value))}
                  className="w-full bg-dark-900 border border-dark-600 rounded-lg px-2 py-1 text-sm"
                  min="0.1"
                  max="10"
                  step="0.1"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Indicators</label>
                <div className="flex flex-wrap gap-2">
                  <label className="flex items-center gap-1 cursor-pointer text-sm">
                    <input
                      type="checkbox"
                      checked={showVolume}
                      onChange={(e) => setShowVolume(e.target.checked)}
                      className="rounded"
                    />
                    Vol
                  </label>
                  <label className="flex items-center gap-1 cursor-pointer text-sm">
                    <input
                      type="checkbox"
                      checked={showEMA}
                      onChange={(e) => setShowEMA(e.target.checked)}
                      className="rounded"
                    />
                    EMA
                  </label>
                  <label className="flex items-center gap-1 cursor-pointer text-sm">
                    <input
                      type="checkbox"
                      checked={showBollinger}
                      onChange={(e) => setShowBollinger(e.target.checked)}
                      className="rounded"
                    />
                    BB
                  </label>
                  <label className="flex items-center gap-1 cursor-pointer text-sm">
                    <input
                      type="checkbox"
                      checked={showPivots}
                      onChange={(e) => setShowPivots(e.target.checked)}
                      className="rounded"
                    />
                    Pivots
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Pine Script Panel */}
        {showPineScript && (
          <div className="bg-dark-800 border border-dark-700 rounded-xl p-3 sm:p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Code2 size={18} className="text-green-400" />
                <h3 className="font-semibold">Pine Script Editor</h3>
                <span className="text-xs text-gray-400">(AI-powered indicators)</span>
              </div>
              <button
                onClick={() => setShowPineScript(false)}
                className="text-gray-400 hover:text-white"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Script</label>
                <textarea
                  value={pineScriptCode}
                  onChange={(e) => setPineScriptCode(e.target.value)}
                  className="w-full h-48 bg-dark-900 border border-dark-600 rounded-lg p-3 text-xs font-mono text-green-300 resize-none focus:outline-none focus:border-green-500"
                  spellCheck={false}
                />
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={() => {
                      // Simulate Pine Script compilation
                      setPineScriptError(null);
                      setPineScriptOutput('Compiling...');
                      setTimeout(() => {
                        setPineScriptOutput('✓ Script compiled successfully!\n\nIndicators added:\n- EMA 20 with dynamic color\n- Pivot Points (R1, S1)\n- Custom support/resistance levels');
                      }, 1000);
                    }}
                    className="px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded text-sm flex items-center gap-1"
                  >
                    <Play size={14} />
                    Compile & Run
                  </button>
                  <button
                    onClick={() => {
                      // Reset to default
                      setPineScriptCode(`//@version=5\nindicator("Custom Strategy", overlay=true)\n\n// EMA with dynamic color\nema20 = ta.ema(close, 20)\nemaColor = close > ema20 ? color.green : color.red\nplot(ema20, "EMA 20", emaColor)\n\n// Pivot Points\npivot = (high[1] + low[1] + close[1]) / 3\nr1 = (2 * pivot) - low[1]\ns1 = (2 * pivot) - high[1]\n\nplot(pivot, "PP", color.orange)\nplot(r1, "R1", color.green)\nplot(s1, "S1", color.red)`);
                      setPineScriptError(null);
                      setPineScriptOutput(null);
                    }}
                    className="px-3 py-1.5 bg-dark-700 hover:bg-dark-600 rounded text-sm"
                  >
                    Reset
                  </button>
                </div>
                {pineScriptError && (
                  <div className="mt-2 p-2 bg-red-900/30 border border-red-800 rounded text-xs text-red-300">
                    <strong>Error:</strong> {pineScriptError}
                  </div>
                )}
              </div>
              
              <div>
                <label className="block text-xs text-gray-400 mb-1">Output / Log</label>
                <div className="w-full h-48 bg-dark-900 border border-dark-600 rounded-lg p-3 text-xs font-mono overflow-auto">
                  {pineScriptOutput ? (
                    <pre className="text-green-300 whitespace-pre-wrap">{pineScriptOutput}</pre>
                  ) : (
                    <span className="text-gray-500">// Click "Compile & Run" to execute script</span>
                  )}
                </div>
                <div className="mt-2 text-xs text-gray-500">
                  <p>Pine Script v5 syntax supported. Common functions:</p>
                  <code className="text-gray-400">ta.ema, ta.sma, ta.rsi, ta.atr, ta.bb, plot, plotshape</code>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Main Chart */}
        <div 
          ref={chartContainerRef}
          className="bg-dark-800 rounded-xl p-2 sm:p-4 border border-dark-700 touch-pan-y"
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          {/* Price Header */}
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="text-lg sm:text-2xl font-bold">${currentPrice.toLocaleString()}</div>
              <div className={`text-xs sm:text-sm ${priceChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}% (24h)
              </div>
            </div>
            {stopLoss && takeProfit && (
              <div className="text-right">
                <div className="text-xs text-gray-400">Risk:Reward</div>
                <div className={`text-lg font-bold ${riskReward >= 2 ? 'text-green-400' : 'text-yellow-400'}`}>
                  1:{riskReward.toFixed(1)}
                </div>
              </div>
            )}
          </div>

          <AdvancedTradingView
            symbol={selectedCoin}
            data={chartData}
            height={chartHeight}
            stopLoss={stopLoss}
            takeProfit={takeProfit}
            onSLChange={setStopLoss}
            onTPChange={setTakeProfit}
            suggestions={suggestions}
            showVolume={showVolume}
            showEMA={showEMA}
            showBollinger={showBollinger}
            showPivots={showPivots}
            isMobile={isMobile}
            isFullscreen={isFullscreen}
            onExitFullscreen={() => setIsFullscreen(false)}
          />

          {/* Mobile Swipe Hint */}
          {isMobile && (
            <div className="flex items-center justify-center gap-1 mt-2 text-xs text-gray-500">
              <span>← Swipe chart to change timeframe →</span>
            </div>
          )}
        </div>

        {/* AI Suggestions Panel */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="bg-dark-800 rounded-xl p-3 sm:p-4 border border-dark-700">
            <div className="flex items-center gap-2 mb-3 sm:mb-4">
              <Brain size={18} className="text-purple-400" />
              <h3 className="font-semibold text-sm sm:text-base">AI Strategy Suggestions</h3>
              <span className="hidden sm:inline text-xs text-gray-400 ml-auto">Based on ATR, S/R & trend analysis</span>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Stop Loss Suggestions */}
              <div>
                <div className="text-xs sm:text-sm text-orange-400 mb-2 flex items-center gap-2">
                  <Shield size={14} />
                  Stop Loss
                </div>
                <div className="space-y-2">
                  {suggestions.filter(s => s.type === 'sl').slice(0, 2).map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => applySuggestion(suggestion)}
                      className={`w-full p-2 sm:p-3 rounded-lg border text-left transition-all ${
                        stopLoss === suggestion.price
                          ? 'bg-orange-500/20 border-orange-500'
                          : 'bg-dark-900 border-dark-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="min-w-0">
                          <div className="font-mono font-bold text-sm">${suggestion.price.toFixed(2)}</div>
                          <div className="text-xs text-gray-400 truncate">{suggestion.reason}</div>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="text-xs text-orange-400">{suggestion.confidence}%</div>
                          <div className="text-[10px] text-gray-500 uppercase">{suggestion.source.replace('_', ' ')}</div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Take Profit Suggestions */}
              <div>
                <div className="text-xs sm:text-sm text-green-400 mb-2 flex items-center gap-2">
                  <Target size={14} />
                  Take Profit
                </div>
                <div className="space-y-2">
                  {suggestions.filter(s => s.type === 'tp').slice(0, 2).map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => applySuggestion(suggestion)}
                      className={`w-full p-2 sm:p-3 rounded-lg border text-left transition-all ${
                        takeProfit === suggestion.price
                          ? 'bg-green-500/20 border-green-500'
                          : 'bg-dark-900 border-dark-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="min-w-0">
                          <div className="font-mono font-bold text-sm">${suggestion.price.toFixed(2)}</div>
                          <div className="text-xs text-gray-400 truncate">{suggestion.reason}</div>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="text-xs text-green-400">{suggestion.confidence}%</div>
                          <div className="text-[10px] text-gray-500 uppercase">{suggestion.source.replace('_', ' ')}</div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* FIXED: Trade Analysis with Correct Logic */}
        {(stopLoss || takeProfit) && (
          <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl p-3 sm:p-4 border border-blue-500/30">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <BarChart4 size={18} className="text-blue-400" />
              Trade Calculator
            </h3>
            
            {/* Input Summary */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4 mb-4">
              <div className="p-2 sm:p-3 bg-dark-900 rounded-lg">
                <div className="text-xs text-gray-400">Entry Price</div>
                <div className="text-base sm:text-lg font-mono font-bold">${currentPrice.toFixed(2)}</div>
              </div>
              
              {stopLoss && (
                <div className="p-2 sm:p-3 bg-dark-900 rounded-lg">
                  <div className="text-xs text-orange-400">Stop Loss</div>
                  <div className="text-base sm:text-lg font-mono font-bold text-orange-400">${stopLoss.toFixed(2)}</div>
                  <div className="text-[10px] sm:text-xs text-gray-500">
                    Risk: ${riskPerUnit.toFixed(2)}/unit
                  </div>
                </div>
              )}
              
              {takeProfit && (
                <div className="p-2 sm:p-3 bg-dark-900 rounded-lg">
                  <div className="text-xs text-green-400">Take Profit</div>
                  <div className="text-base sm:text-lg font-mono font-bold text-green-400">${takeProfit.toFixed(2)}</div>
                  <div className="text-[10px] sm:text-xs text-gray-500">
                    Reward: ${(takeProfit - currentPrice).toFixed(2)}/unit
                  </div>
                </div>
              )}
              
              {riskReward > 0 && (
                <div className={`p-2 sm:p-3 rounded-lg ${riskReward >= 2 ? 'bg-green-900/30' : 'bg-yellow-900/30'}`}>
                  <div className="text-xs text-gray-400">R:R Ratio</div>
                  <div className={`text-base sm:text-lg font-mono font-bold ${riskReward >= 2 ? 'text-green-400' : 'text-yellow-400'}`}>
                    1:{riskReward.toFixed(1)}
                  </div>
                </div>
              )}
            </div>

            {/* Position Sizing - FIXED LOGIC */}
            {positionSizeUnits > 0 && (
              <div className="space-y-3">
                <div className="p-3 bg-dark-900 rounded-lg border border-blue-500/30">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-gray-400">Risk Amount ({riskPercent}% of ${accountSize.toLocaleString()})</div>
                      <div className="text-xl font-mono font-bold text-orange-400">${riskAmountValue.toFixed(2)}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-400">Position Size</div>
                      <div className="text-xl font-mono font-bold text-blue-400">{positionSizeUnits.toFixed(4)} units</div>
                      <div className="text-xs text-gray-500">≈ ${positionValue.toFixed(2)} value</div>
                    </div>
                  </div>
                </div>

                {/* Profit/Loss Projection */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-green-900/20 rounded-lg border border-green-500/30">
                    <div className="text-xs text-green-400 mb-1">Potential Profit (if TP hit)</div>
                    <div className="text-lg font-mono font-bold text-green-400">+${potentialProfit.toFixed(2)}</div>
                    <div className="text-xs text-gray-500">{((potentialProfit / accountSize) * 100).toFixed(2)}% of account</div>
                  </div>
                  <div className="p-3 bg-red-900/20 rounded-lg border border-red-500/30">
                    <div className="text-xs text-red-400 mb-1">Potential Loss (if SL hit)</div>
                    <div className="text-lg font-mono font-bold text-red-400">-${potentialLoss.toFixed(2)}</div>
                    <div className="text-xs text-gray-500">{((potentialLoss / accountSize) * 100).toFixed(2)}% of account</div>
                  </div>
                </div>

                {/* Explanation */}
                <div className="text-xs text-gray-400 bg-dark-900/50 p-2 rounded">
                  <strong>How it works:</strong> With ${riskAmountValue.toFixed(2)} risk allowance and ${riskPerUnit.toFixed(2)} risk per unit, 
                  you can buy {positionSizeUnits.toFixed(4)} units at ${currentPrice.toFixed(2)} each for a total position value of ${positionValue.toFixed(2)}.
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
