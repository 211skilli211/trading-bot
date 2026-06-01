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
import { GlassCard, PageHeader, EmptyState } from '../components/ui/GlassCard';
import { api } from '../api/client';
import { Price, ArbitrageOpportunity } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';

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
  { symbol: 'BTC/USDT', name: 'Bitcoin', price: 64250, change24h: 2.5, volume24h: 28.5e9, marketCap: 1.26e12, chain: 'layer1' },
  { symbol: 'ETH/USDT', name: 'Ethereum', price: 3450, change24h: 1.8, volume24h: 15.2e9, marketCap: 415e9, chain: 'ethereum' },
  { symbol: 'SOL/USDT', name: 'Solana', price: 148, change24h: -0.5, volume24h: 3.8e9, marketCap: 68e9, chain: 'solana' },
  { symbol: 'BNB/USDT', name: 'Binance Coin', price: 585, change24h: 0.8, volume24h: 1.2e9, marketCap: 88e9, chain: 'binance' },
  { symbol: 'XRP/USDT', name: 'Ripple', price: 0.62, change24h: 1.2, volume24h: 1.8e9, marketCap: 34e9, chain: 'layer1' },
  { symbol: 'ADA/USDT', name: 'Cardano', price: 0.58, change24h: -1.5, volume24h: 420e6, marketCap: 20e9, chain: 'layer1' },
  { symbol: 'DOGE/USDT', name: 'Dogecoin', price: 0.12, change24h: 5.2, volume24h: 2.1e9, marketCap: 17e9, chain: 'meme' },
  { symbol: 'DOT/USDT', name: 'Polkadot', price: 7.25, change24h: 2.1, volume24h: 280e6, marketCap: 10e9, chain: 'layer1' },
  { symbol: 'AVAX/USDT', name: 'Avalanche', price: 38.5, change24h: 3.2, volume24h: 580e6, marketCap: 15e9, chain: 'layer1' },
  { symbol: 'MATIC/USDT', name: 'Polygon', price: 0.72, change24h: -0.8, volume24h: 380e6, marketCap: 7e9, chain: 'layer2' },
  { symbol: 'NEAR/USDT', name: 'NEAR Protocol', price: 6.8, change24h: 4.5, volume24h: 320e6, marketCap: 7e9, chain: 'layer1' },
  { symbol: 'ATOM/USDT', name: 'Cosmos', price: 9.2, change24h: 1.5, volume24h: 280e6, marketCap: 3.5e9, chain: 'layer1' },
  { symbol: 'FTM/USDT', name: 'Fantom', price: 0.85, change24h: -2.1, volume24h: 180e6, marketCap: 2.4e9, chain: 'layer1' },
  { symbol: 'UNI/USDT', name: 'Uniswap', price: 9.8, change24h: -1.2, volume24h: 180e6, marketCap: 5.9e9, chain: 'ethereum' },
  { symbol: 'AAVE/USDT', name: 'Aave', price: 105, change24h: 2.8, volume24h: 120e6, marketCap: 1.5e9, chain: 'ethereum' },
  { symbol: 'JTO/USDT', name: 'Jito', price: 3.2, change24h: 8.5, volume24h: 120e6, marketCap: 380e6, chain: 'solana' },
  { symbol: 'RAY/USDT', name: 'Raydium', price: 1.85, change24h: 5.2, volume24h: 45e6, marketCap: 480e6, chain: 'solana' },
  { symbol: 'BONK/USDT', name: 'Bonk', price: 0.000022, change24h: 12.5, volume24h: 280e6, marketCap: 1.4e9, chain: 'meme' },
  { symbol: 'WIF/USDT', name: 'Dogwifhat', price: 2.15, change24h: 15.8, volume24h: 420e6, marketCap: 2.1e9, chain: 'meme' },
];

const chainLabels: Record<string, { label: string; activeClass: string }> = {
  ethereum: { label: 'Ethereum', activeClass: 'bg-blue-500/15 text-blue-400' },
  solana: { label: 'Solana', activeClass: 'bg-blue-500/15 text-blue-400' },
  binance: { label: 'BNB Chain', activeClass: 'bg-[#D4AF37]/15 text-[#D4AF37]' },
  layer1: { label: 'Layer 1', activeClass: 'bg-[#00C9A7]/15 text-[#00C9A7]' },
  layer2: { label: 'Layer 2', activeClass: 'bg-[#00C9A7]/15 text-[#00C9A7]' },
  meme: { label: 'Meme', activeClass: 'bg-[#FF6B35]/15 text-[#FF6B35]' },
  defi: { label: 'DeFi', activeClass: 'bg-[#FF6B35]/15 text-[#FF6B35]' },
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
        if (pricesRes.status === 'fulfilled') setPrices(pricesRes.value);
        if (arbRes.status === 'fulfilled') setArbitrage(arbRes.value.filter((a: ArbitrageOpportunity) => a.profitPercent > 0));
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

  let filteredCoins = AVAILABLE_COINS.filter(coin => {
    const matchesSearch = coin.symbol.toLowerCase().includes(search.toLowerCase()) ||
                         coin.name.toLowerCase().includes(search.toLowerCase());
    const matchesChain = chainFilter === 'all' || coin.chain === chainFilter;
    const matchesFavorites = exchangeFilter !== 'favorites' || favorites.includes(coin.symbol);
    const matchesGainers = exchangeFilter !== 'gainers' || coin.change24h > 0;
    const matchesLosers = exchangeFilter !== 'losers' || coin.change24h < 0;
    return matchesSearch && matchesChain && matchesFavorites && matchesGainers && matchesLosers;
  });

  filteredCoins.sort((a, b) => {
    if (sortBy === 'volume') return b.volume24h - a.volume24h;
    if (sortBy === 'change') return b.change24h - a.change24h;
    if (sortBy === 'price') return b.price - a.price;
    return 0;
  });

  let filteredPrices = prices.filter(p => {
    const matchesSearch = p.symbol.toLowerCase().includes(search.toLowerCase());
    const matchesExchange = exchangeFilter === 'all' || p.exchange === exchangeFilter;
    const matchesFavorites = exchangeFilter !== 'favorites' || favorites.includes(p.symbol);
    const matchesGainers = exchangeFilter !== 'gainers' || (p.change24h || 0) > 0;
    const matchesLosers = exchangeFilter !== 'losers' || (p.change24h || 0) < 0;
    return matchesSearch && matchesExchange && matchesFavorites && matchesGainers && matchesLosers;
  });

  filteredPrices.sort((a, b) => {
    if (sortBy === 'volume') return (b.volume24h || 0) - (a.volume24h || 0);
    if (sortBy === 'change') return (b.change24h || 0) - (a.change24h || 0);
    if (sortBy === 'price') return (b.price || 0) - (a.price || 0);
    return 0;
  });

  const groupedPrices = filteredPrices.reduce((acc, price) => {
    if (!acc[price.symbol]) acc[price.symbol] = [];
    acc[price.symbol].push(price);
    return acc;
  }, {} as Record<string, Price[]>);

  const uniqueSymbols = Object.keys(groupedPrices);

  return (
    <div className="pb-20 lg:pb-6 lg:pl-[224px]">
      <Header title="Live Prices" />

      <div className="p-4 max-w-[1200px] mx-auto">
        <PageHeader
          title="Live Prices"
          subtitle={`${uniqueSymbols.length} markets · ${arbitrage.length} arb opportunities`}
        />

        {/* Search */}
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5a6a7e]" size={18} />
          <input
            type="text"
            placeholder="Search coins..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-glass w-full pl-10"
          />
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-2 flex-wrap mb-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={[
              'flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-colors',
              showFilters ? 'bg-[#0F4C75]/15 text-blue-400' : 'text-[#5a6a7e] hover:text-[#e8ecf1]',
            ].join(' ')}
          >
            <Filter size={15} />
            Filters
          </button>

          <select
            value={chainFilter}
            onChange={(e) => setChainFilter(e.target.value)}
            className="input-glass px-3 py-2 text-sm min-h-0"
          >
            <option value="all">All Chains</option>
            <option value="ethereum">Ethereum</option>
            <option value="solana">Solana</option>
            <option value="binance">BNB Chain</option>
            <option value="layer1">Layer 1</option>
            <option value="layer2">Layer 2</option>
            <option value="meme">Meme</option>
            <option value="defi">DeFi</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="input-glass px-3 py-2 text-sm min-h-0"
          >
            <option value="volume">Volume</option>
            <option value="change">Change</option>
            <option value="price">Price</option>
          </select>

          <div className="flex-1" />

          {/* View Toggle */}
          <div className="flex rounded-lg overflow-hidden border border-[rgba(30,50,70,0.3)]">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 transition-colors ${viewMode === 'grid' ? 'bg-[#0F4C75]/15 text-blue-400' : 'text-[#5a6a7e]'}`}
            >
              <Grid3X3 size={16} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 transition-colors ${viewMode === 'list' ? 'bg-[#0F4C75]/15 text-blue-400' : 'text-[#5a6a7e]'}`}
            >
              <List size={16} />
            </button>
          </div>
        </div>

        {/* Expanded Filters */}
        {showFilters && (
          <GlassCard padding="sm" className="mb-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-[#5a6a7e]">Show:</span>
              {[
                { key: 'favorites', label: 'Favorites', icon: Star },
                { key: 'gainers', label: 'Gainers', icon: TrendingUp },
                { key: 'losers', label: 'Losers', icon: TrendingDown },
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setExchangeFilter(exchangeFilter === key ? 'all' : key)}
                  className={[
                    'px-3 py-1 rounded-lg text-xs font-medium transition-colors',
                    exchangeFilter === key
                      ? 'bg-[#0F4C75]/15 text-blue-400'
                      : 'text-[#5a6a7e] hover:text-[#e8ecf1]',
                  ].join(' ')}
                >
                  <Icon size={11} className="inline mr-1" />
                  {label}
                </button>
              ))}
            </div>
          </GlassCard>
        )}

        {/* Chain Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 no-scrollbar mb-3">
          <span className="text-xs text-[#5a6a7e] whitespace-nowrap">Chain:</span>
          {Object.entries(chainLabels).map(([key, { label, activeClass }]) => (
            <button
              key={key}
              onClick={() => setChainFilter(chainFilter === key ? 'all' : key)}
              className={[
                'px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors',
                chainFilter === key ? activeClass : 'text-[#5a6a7e] hover:text-[#e8ecf1]',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('prices')}
            className={[
              'flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors',
              activeTab === 'prices'
                ? 'bg-[#0F4C75]/15 text-blue-400'
                : 'text-[#5a6a7e] hover:text-[#e8ecf1]',
            ].join(' ')}
          >
            <Layers size={15} className="inline mr-1.5" />
            Live Prices ({uniqueSymbols.length})
          </button>
          <button
            onClick={() => setActiveTab('arbitrage')}
            className={[
              'flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors',
              activeTab === 'arbitrage'
                ? 'bg-[#0F4C75]/15 text-blue-400'
                : 'text-[#5a6a7e] hover:text-[#e8ecf1]',
            ].join(' ')}
          >
            <Zap size={15} className="inline mr-1.5" />
            Arbitrage ({arbitrage.length})
          </button>
        </div>

        {/* Content */}
        {activeTab === 'prices' ? (
          viewMode === 'grid' ? (
            <div className="grid gap-3">
              {filteredPrices.map((price) => (
                <PriceCard key={`${price.exchange}-${price.symbol}`} price={price} />
              ))}
            </div>
          ) : (
            <GlassCard padding="none" className="overflow-hidden">
              {uniqueSymbols.map((symbol) => {
                const pricesForSymbol = groupedPrices[symbol];
                const mainPrice = pricesForSymbol[0];
                const isFavorite = favorites.includes(symbol);
                return (
                  <div
                    key={symbol}
                    onClick={() => navigate(`/coin/${encodeURIComponent(symbol)}`)}
                    className="flex items-center justify-between p-4 border-b border-[rgba(30,50,70,0.2)] last:border-0 hover:bg-white/[0.02] cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleFavorite(symbol); }}
                        className={isFavorite ? 'text-[#D4AF37]' : 'text-[#3d4d60]'}
                      >
                        <Star size={16} fill={isFavorite ? 'currentColor' : 'none'} />
                      </button>
                      <CryptoIcon symbol={symbol} size={36} />
                      <div>
                        <div className="font-semibold text-sm text-[#e8ecf1]">{symbol}</div>
                        <div className="text-xs text-[#5a6a7e]">
                          {pricesForSymbol.map(p => p.exchange).join(', ')}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="mono text-sm font-semibold text-[#e8ecf1]">{formatCurrency(mainPrice.price)}</div>
                      <div className={`mono text-xs ${(mainPrice.change24h || 0) >= 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
                        {formatPercent(mainPrice.change24h || 0)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </GlassCard>
          )
        ) : (
          <div className="space-y-3">
            {arbitrage.length > 0 ? (
              arbitrage.map((opp) => (
                <ArbitrageCard key={opp.symbol} opportunity={opp} />
              ))
            ) : (
              <EmptyState
                icon={<Zap size={32} />}
                title="No arbitrage opportunities"
                description="Check back in a few minutes — opportunities appear when price gaps emerge."
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
