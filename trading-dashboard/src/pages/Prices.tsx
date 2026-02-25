import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, Filter, Grid3X3, List, TrendingUp, TrendingDown,
  Star, Zap
} from 'lucide-react';
import { Header } from '../components/Header';
import { PriceCard } from '../components/PriceCard';
import { ArbitrageCard } from '../components/ArbitrageCard';
import { CryptoIcon } from '../components/CryptoIcon';
import { api } from '../api/client';
import { Price, ArbitrageOpportunity } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';

export function Prices() {
  const navigate = useNavigate();
  const [prices, setPrices] = useState<Price[]>([]);
  const [arbitrage, setArbitrage] = useState<ArbitrageOpportunity[]>([]);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'prices' | 'arbitrage'>('prices');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [exchangeFilter, setExchangeFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'volume' | 'change' | 'price'>('volume');
  const [favorites, setFavorites] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

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
            Prices ({uniqueSymbols.length})
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
