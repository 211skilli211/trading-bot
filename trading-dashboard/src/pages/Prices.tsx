import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, Filter, Grid3X3, List, TrendingUp, TrendingDown,
  Star, Zap, ChevronDown, Layers, Globe
} from 'lucide-react';
import { Header } from '../components/Header';
import { PriceCard } from '../components/PriceCard';
import { ArbitrageCard } from '../components/ArbitrageCard';
import { CryptoIcon } from '../components/CryptoIcon';
import { api } from '../api/client';
import { Price, ArbitrageOpportunity } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';

// Unified coin list from Analytics
interface CoinOption {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  volume24h: number;
  marketCap: number;
  chain: 'ethereum' | 'solana' | 'binance' | 'layer1' | 'layer2' | 'meme' | 'defi';
}

const AVAILABLE_COINS: CoinOption[] = [
  // Major Coins
  { symbol: 'BTC/USDT', name: 'Bitcoin', price: 64250, change24h: 2.5, volume24h: 28.5e9, marketCap: 1.26e12, chain: 'layer1' },
  { symbol: 'ETH/USDT', name: 'Ethereum', price: 3450, change24h: 1.8, volume24h: 15.2e9, marketCap: 415e9, chain: 'ethereum' },
  { symbol: 'SOL/USDT', name: 'Solana', price: 148, change24h: -0.5, volume24h: 3.8e9, marketCap: 68e9, chain: 'solana' },
  { symbol: 'BNB/USDT', name: 'Binance Coin', price: 585, change24h: 0.8, volume24h: 1.2e9, marketCap: 88e9, chain: 'binance' },
  { symbol: 'XRP/USDT', name: 'Ripple', price: 0.62, change24h: 1.2, volume24h: 1.8e9, marketCap: 34e9, chain: 'layer1' },
  { symbol: 'ADA/USDT', name: 'Cardano', price: 0.58, change24h: -1.5, volume24h: 420e6, marketCap: 20e9, chain: 'layer1' },
  { symbol: 'DOGE/USDT', name: 'Dogecoin', price: 0.12, change24h: 5.2, volume24h: 2.1e9, marketCap: 17e9, chain: 'meme' },
  { symbol: 'DOT/USDT', name: 'Polkadot', price: 7.25, change24h: 2.1, volume24h: 280e6, marketCap: 10e9, chain: 'layer1' },
  // Layer 1s
  { symbol: 'AVAX/USDT', name: 'Avalanche', price: 38.5, change24h: 3.2, volume24h: 580e6, marketCap: 15e9, chain: 'layer1' },
  { symbol: 'MATIC/USDT', name: 'Polygon', price: 0.72, change24h: -0.8, volume24h: 380e6, marketCap: 7e9, chain: 'layer2' },
  { symbol: 'NEAR/USDT', name: 'NEAR Protocol', price: 6.8, change24h: 4.5, volume24h: 320e6, marketCap: 7e9, chain: 'layer1' },
  { symbol: 'ATOM/USDT', name: 'Cosmos', price: 9.2, change24h: 1.5, volume24h: 280e6, marketCap: 3.5e9, chain: 'layer1' },
  { symbol: 'FTM/USDT', name: 'Fantom', price: 0.85, change24h: -2.1, volume24h: 180e6, marketCap: 2.4e9, chain: 'layer1' },
  { symbol: 'ALGO/USDT', name: 'Algorand', price: 0.19, change24h: 0.5, volume24h: 95e6, marketCap: 1.6e9, chain: 'layer1' },
  { symbol: 'VET/USDT', name: 'VeChain', price: 0.035, change24h: 1.2, volume24h: 85e6, marketCap: 2.8e9, chain: 'layer1' },
  // DeFi
  { symbol: 'UNI/USDT', name: 'Uniswap', price: 9.8, change24h: -1.2, volume24h: 180e6, marketCap: 5.9e9, chain: 'ethereum' },
  { symbol: 'AAVE/USDT', name: 'Aave', price: 105, change24h: 2.8, volume24h: 120e6, marketCap: 1.5e9, chain: 'ethereum' },
  { symbol: 'MKR/USDT', name: 'Maker', price: 1680, change24h: 0.5, volume24h: 95e6, marketCap: 1.5e9, chain: 'ethereum' },
  { symbol: 'CRV/USDT', name: 'Curve', price: 0.42, change24h: -3.5, volume24h: 85e6, marketCap: 550e6, chain: 'ethereum' },
  { symbol: 'SUSHI/USDT', name: 'SushiSwap', price: 1.25, change24h: 3.5, volume24h: 85e6, marketCap: 290e6, chain: 'ethereum' },
  { symbol: 'COMP/USDT', name: 'Compound', price: 65, change24h: -1.5, volume24h: 35e6, marketCap: 520e6, chain: 'ethereum' },
  // Solana Ecosystem
  { symbol: 'JTO/USDT', name: 'Jito', price: 3.2, change24h: 8.5, volume24h: 120e6, marketCap: 380e6, chain: 'solana' },
  { symbol: 'RAY/USDT', name: 'Raydium', price: 1.85, change24h: 5.2, volume24h: 45e6, marketCap: 480e6, chain: 'solana' },
  { symbol: 'BONK/USDT', name: 'Bonk', price: 0.000022, change24h: 12.5, volume24h: 280e6, marketCap: 1.4e9, chain: 'meme' },
  { symbol: 'WIF/USDT', name: 'Dogwifhat', price: 2.15, change24h: 15.8, volume24h: 420e6, marketCap: 2.1e9, chain: 'meme' },
];

const chainLabels: Record<string, { label: string; color: string }> = {
  ethereum: { label: 'Ethereum', color: 'bg-blue-500/20 text-blue-400' },
  solana: { label: 'Solana', color: 'bg-purple-500/20 text-purple-400' },
  binance: { label: 'BNB Chain', color: 'bg-yellow-500/20 text-yellow-400' },
  layer1: { label: 'Layer 1', color: 'bg-green-500/20 text-green-400' },
  layer2: { label: 'Layer 2', color: 'bg-cyan-500/20 text-cyan-400' },
  meme: { label: 'Meme', color: 'bg-pink-500/20 text-pink-400' },
  defi: { label: 'DeFi', color: 'bg-orange-500/20 text-orange-400' },
};

export function Prices() {
  const navigate = useNavigate();
  const [prices, setPrices] = useState<Price[]>([]);
  const [arbitrage, setArbitrage] = useState<ArbitrageOpportunity[]>([]);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'prices' | 'arbitrage'>('prices');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [exchangeFilter, setExchangeFilter] = useState<string>('all');
  const [chainFilter, setChainFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'volume' | 'change' | 'price'>('volume');
  const [favorites, setFavorites] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [showCoinDropdown, setShowCoinDropdown] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('favoriteCoins');
    if (saved) setFavorites(JSON.parse(saved));
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const [pricesRes, arbRes] = await Promise.allSettled([
          api.getPrices(),
          api.getArbitrage(),
        ]);
        
        if (pricesRes.status === 'fulfilled') {
          setPrices(pricesRes.value);
        }
        if (arbRes.status === 'fulfilled') {
          setArbitrage(arbRes.value.filter((a: ArbitrageOpportunity) => a.profitPercent > 0));
        }
      } catch (error) {
        console.error('Failed to load prices:', error);
      }
    }
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const toggleFavorite = (symbol: string) => {
    const newFavs = favorites.includes(symbol)
      ? favorites.filter(s => s !== symbol)
      : [...favorites, symbol];
    setFavorites(newFavs);
    localStorage.setItem('favoriteCoins', JSON.stringify(newFavs));
  };

  const exchanges = Array.from(new Set(prices.map(p => p.exchange)));

  // Filter coins from unified list
  let filteredCoins = AVAILABLE_COINS.filter(coin => {
    const matchesSearch = coin.symbol.toLowerCase().includes(search.toLowerCase()) ||
                         coin.name.toLowerCase().includes(search.toLowerCase());
    const matchesChain = chainFilter === 'all' || coin.chain === chainFilter;
    const matchesFavorites = exchangeFilter !== 'favorites' || favorites.includes(coin.symbol);
    const matchesGainers = exchangeFilter !== 'gainers' || coin.change24h > 0;
    const matchesLosers = exchangeFilter !== 'losers' || coin.change24h < 0;
    return matchesSearch && matchesChain && matchesFavorites && matchesGainers && matchesLosers;
  });

  // Sort coins
  filteredCoins.sort((a, b) => {
    if (sortBy === 'volume') return b.volume24h - a.volume24h;
    if (sortBy === 'change') return b.change24h - a.change24h;
    if (sortBy === 'price') return b.price - a.price;
    return 0;
  });

  // Legacy price filtering (keep for compatibility)
  let filteredPrices = prices.filter(p => {
    const matchesSearch = p.symbol.toLowerCase().includes(search.toLowerCase());
    const matchesExchange = exchangeFilter === 'all' || p.exchange === exchangeFilter;
    const matchesFavorites = exchangeFilter !== 'favorites' || favorites.includes(p.symbol);
    const matchesGainers = exchangeFilter !== 'gainers' || (p.change24h || 0) > 0;
    const matchesLosers = exchangeFilter !== 'losers' || (p.change24h || 0) < 0;
    return matchesSearch && matchesExchange && matchesFavorites && matchesGainers && matchesLosers;
  });

  // Sort prices
  filteredPrices.sort((a, b) => {
    if (sortBy === 'volume') return (b.volume24h || 0) - (a.volume24h || 0);
    if (sortBy === 'change') return (b.change24h || 0) - (a.change24h || 0);
    if (sortBy === 'price') return (b.price || 0) - (a.price || 0);
    return 0;
  });

  // Group by symbol for list view
  const groupedPrices = filteredPrices.reduce((acc, price) => {
    if (!acc[price.symbol]) acc[price.symbol] = [];
    acc[price.symbol].push(price);
    return acc;
  }, {} as Record<string, Price[]>);

  const uniqueSymbols = Object.keys(groupedPrices);

  return (
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title="Live Prices" />
      
      <div className="p-4 space-y-4">
        {/* Search & Filters */}
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input
              type="text"
              placeholder="Search coins..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-dark-800 border border-dark-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Filter Bar */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                showFilters ? 'bg-blue-600 text-white' : 'bg-dark-800 text-gray-400'
              }`}
            >
              <Filter size={16} />
              Filters
            </button>

            <select
              value={exchangeFilter}
              onChange={(e) => setExchangeFilter(e.target.value)}
              className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="all">All Exchanges</option>
              {exchanges.map(ex => (
                <option key={ex} value={ex}>{ex}</option>
              ))}
            </select>

            <select
              value={chainFilter}
              onChange={(e) => setChainFilter(e.target.value)}
              className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="all">All Chains</option>
              <option value="ethereum">Ethereum</option>
              <option value="solana">Solana</option>
              <option value="binance">BNB Chain</option>
              <option value="layer1">Layer 1</option>
              <option value="layer2">Layer 2</option>
              <option value="meme">Meme Coins</option>
              <option value="defi">DeFi</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="volume">Sort by Volume</option>
              <option value="change">Sort by Change</option>
              <option value="price">Sort by Price</option>
            </select>

            <div className="flex-1"></div>

            {/* View Toggle */}
            <div className="flex bg-dark-800 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded ${viewMode === 'grid' ? 'bg-blue-600 text-white' : 'text-gray-400'}`}
              >
                <Grid3X3 size={18} />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded ${viewMode === 'list' ? 'bg-blue-600 text-white' : 'text-gray-400'}`}
              >
                <List size={18} />
              </button>
            </div>
          </div>

          {/* Expanded Filters */}
          {showFilters && (
            <div className="bg-dark-800 rounded-xl p-3 space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm text-gray-400">Show:</span>
                <button 
                  onClick={() => setExchangeFilter(exchangeFilter === 'favorites' ? 'all' : 'favorites')}
                  className={`px-3 py-1 rounded-full text-sm ${exchangeFilter === 'favorites' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-dark-700 text-gray-400'}`}
                >
                  <Star size={12} className="inline mr-1" />
                  Favorites
                </button>
                <button 
                  onClick={() => setExchangeFilter(exchangeFilter === 'gainers' ? 'all' : 'gainers')}
                  className={`px-3 py-1 rounded-full text-sm ${exchangeFilter === 'gainers' ? 'bg-green-500/20 text-green-400' : 'bg-dark-700 text-gray-400'}`}
                >
                  <TrendingUp size={12} className="inline mr-1" />
                  Gainers
                </button>
                <button 
                  onClick={() => setExchangeFilter(exchangeFilter === 'losers' ? 'all' : 'losers')}
                  className={`px-3 py-1 rounded-full text-sm ${exchangeFilter === 'losers' ? 'bg-red-500/20 text-red-400' : 'bg-dark-700 text-gray-400'}`}
                >
                  <TrendingDown size={12} className="inline mr-1" />
                  Losers
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Unified Coin List Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowCoinDropdown(!showCoinDropdown)}
            className="w-full flex items-center justify-between gap-2 px-4 py-3 bg-dark-800 border border-dark-700 rounded-xl hover:border-blue-500 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Globe className="text-blue-400" size={20} />
              <div className="text-left">
                <div className="font-semibold">Unified Market List</div>
                <div className="text-xs text-gray-400">{filteredCoins.length} assets available</div>
              </div>
            </div>
            <ChevronDown className={`text-gray-400 transition-transform ${showCoinDropdown ? 'rotate-180' : ''}`} size={20} />
          </button>
          
          {showCoinDropdown && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-dark-800 border border-dark-700 rounded-xl shadow-xl z-50 max-h-[60vh] overflow-auto">
              <div className="p-3">
                <div className="text-xs text-gray-500 mb-2 px-2 sticky top-0 bg-dark-800">Select Market ({filteredCoins.length} assets)</div>
                {filteredCoins.map((coin) => (
                  <button
                    key={coin.symbol}
                    onClick={() => {
                      navigate(`/coin/${encodeURIComponent(coin.symbol)}`);
                      setShowCoinDropdown(false);
                    }}
                    className="w-full flex items-center justify-between p-2 hover:bg-dark-700 rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <CryptoIcon symbol={coin.symbol} size={32} />
                      <div className="text-left">
                        <div className="font-medium">{coin.symbol}</div>
                        <div className="text-xs text-gray-400">{coin.name}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono">${coin.price.toLocaleString()}</div>
                      <div className={`text-xs ${coin.change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {coin.change24h >= 0 ? '+' : ''}{coin.change24h.toFixed(2)}%
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Chain Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
          <span className="text-sm text-gray-400 whitespace-nowrap">Filter by:</span>
          {Object.entries(chainLabels).map(([key, { label, color }]) => (
            <button
              key={key}
              onClick={() => setChainFilter(chainFilter === key ? 'all' : key)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                chainFilter === key ? color : 'bg-dark-800 text-gray-400 border border-dark-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('prices')}
            className={`flex-1 py-2 rounded-xl font-medium transition-colors ${
              activeTab === 'prices' 
                ? 'bg-blue-600 text-white' 
                : 'bg-dark-800 text-gray-400'
            }`}
          >
            <Layers size={16} className="inline mr-1" />
            Live Prices ({uniqueSymbols.length})
          </button>
          <button
            onClick={() => setActiveTab('arbitrage')}
            className={`flex-1 py-2 rounded-xl font-medium transition-colors ${
              activeTab === 'arbitrage' 
                ? 'bg-blue-600 text-white' 
                : 'bg-dark-800 text-gray-400'
            }`}
          >
            <Zap size={16} className="inline mr-1" />
            Arbitrage ({arbitrage.length})
          </button>
        </div>

        {/* Content */}
        {activeTab === 'prices' ? (
          viewMode === 'grid' ? (
            <div className="grid gap-3">
              {filteredPrices.map((price) => (
                <PriceCard 
                  key={`${price.exchange}-${price.symbol}`} 
                  price={price}
                />
              ))}
            </div>
          ) : (
            <div className="bg-dark-800 rounded-xl border border-dark-700 overflow-hidden">
              {uniqueSymbols.map((symbol) => {
                const pricesForSymbol = groupedPrices[symbol];
                const mainPrice = pricesForSymbol[0];
                const isFavorite = favorites.includes(symbol);
                return (
                  <div 
                    key={symbol} 
                    onClick={() => navigate(`/coin/${encodeURIComponent(symbol)}`)}
                    className="flex items-center justify-between p-4 border-b border-dark-700 last:border-0 hover:bg-dark-700/50 cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleFavorite(symbol);
                        }}
                        className={isFavorite ? 'text-yellow-400' : 'text-gray-600'}
                      >
                        <Star size={18} fill={isFavorite ? 'currentColor' : 'none'} />
                      </button>
                      <CryptoIcon symbol={symbol} size={40} />
                      <div>
                        <div className="font-semibold">{symbol}</div>
                        <div className="text-xs text-gray-400">
                          {pricesForSymbol.map(p => p.exchange).join(', ')}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono">{formatCurrency(mainPrice.price)}</div>
                      <div className={`text-sm ${(mainPrice.change24h || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPercent(mainPrice.change24h || 0)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )
        ) : (
          <div className="space-y-3">
            {arbitrage.length > 0 ? (
              arbitrage.map((opp) => (
                <ArbitrageCard key={opp.symbol} opportunity={opp} />
              ))
            ) : (
              <div className="text-center py-12 text-gray-400">
                <Filter size={48} className="mx-auto mb-4 opacity-50" />
                <p>No arbitrage opportunities found</p>
                <p className="text-sm mt-1">Check back in a few minutes</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
