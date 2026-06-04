import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, TrendingUp, TrendingDown, Clock, 
  DollarSign, BarChart3, Activity, Globe,
  ChevronDown, Star, Share2
} from 'lucide-react';
import { Header } from '../components/Header';
import { CryptoIcon } from '../components/CryptoIcon';
import { api } from '../api/client';
import { Price } from '../types';
import { formatCurrency, formatPercent, formatNumber } from '../utils/format';
import { 
import { ShimmerCard } from '../components/ui/GlassCard';
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, AreaChart, Area 
} from 'recharts';

type TimeRange = '1h' | '24h' | '1w' | '1m' | '1y' | 'all';

interface ChartData {
  time: string;
  price: number;
  volume: number;
}

export function CoinDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const [price, setPrice] = useState<Price | null>(null);
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [loading, setLoading] = useState(true);
  const [favorite, setFavorite] = useState(false);

  // Generate mock historical data based on current price
  function generateChartData(basePrice: number, range: TimeRange): ChartData[] {
    const data: ChartData[] = [];
    const now = new Date();
    let points = 50;
    let interval = 60 * 60 * 1000; // 1 hour default
    
    switch (range) {
      case '1h': points = 60; interval = 60 * 1000; break; // 1 minute
      case '24h': points = 24; interval = 60 * 60 * 1000; break; // 1 hour
      case '1w': points = 7; interval = 24 * 60 * 60 * 1000; break; // 1 day
      case '1m': points = 30; interval = 24 * 60 * 60 * 1000; break; // 1 day
      case '1y': points = 12; interval = 30 * 24 * 60 * 60 * 1000; break; // 1 month
      case 'all': points = 20; interval = 180 * 24 * 60 * 60 * 1000; break; // 6 months
    }
    
    let currentPrice = basePrice;
    for (let i = points; i >= 0; i--) {
      const time = new Date(now.getTime() - i * interval);
      // Random walk
      const change = (Math.random() - 0.48) * currentPrice * 0.02;
      currentPrice += change;
      
      data.push({
        time: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        price: currentPrice,
        volume: Math.random() * 1000000
      });
    }
    return data;
  }

  useEffect(() => {
    async function loadData() {
      if (!symbol) return;
      
      try {
        const prices = await api.getPrices();
        const coinPrice = prices.find((p: Price) => p.symbol === symbol);
        if (coinPrice) {
          setPrice(coinPrice);
          setChartData(generateChartData(coinPrice.price, timeRange));
        }
        
        // Check favorites
        const saved = localStorage.getItem('favoriteCoins');
        if (saved) {
          setFavorite(JSON.parse(saved).includes(symbol));
        }
      } catch (error) {
        console.error('Failed to load coin data:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [symbol]);

  useEffect(() => {
    if (price) {
      setChartData(generateChartData(price.price, timeRange));
    }
  }, [timeRange, price]);

  const toggleFavorite = () => {
    const saved = localStorage.getItem('favoriteCoins');
    const favorites = saved ? JSON.parse(saved) : [];
    
    const newFavorites = favorite
      ? favorites.filter((s: string) => s !== symbol)
      : [...favorites, symbol];
    
    localStorage.setItem('favoriteCoins', JSON.stringify(newFavorites));
    setFavorite(!favorite);
  };

  if (loading) {
    return (
      <div className="pb-20 lg:pb-8 lg:pl-[224px]">
        <Header title="Coin Details" />
        <ShimmerCard height="h-64" />
      </div>
    );
  }

  if (!price) {
    return (
      <div className="pb-20 lg:pb-8 lg:pl-[224px]">
        <Header title="Coin Not Found" />
        <div className="flex flex-col items-center justify-center h-64 text-[#5a6a7e]">
          <p>Coin not found</p>
          <button 
            onClick={() => navigate('/prices')}
            className="mt-4 text-[#3B82F6] hover:underline"
          >
            Back to Prices
          </button>
        </div>
      </div>
    );
  }

  const priceChange = price.change24h || 0;
  const isPositive = priceChange >= 0;
  const baseSymbol = symbol?.split('/')[0] || '';
  const quoteSymbol = symbol?.split('/')[1] || 'USDT';

  return (
    <div className="pb-20 lg:pb-8 lg:pl-[224px]">
      <div className="sticky top-0 z-40 bg-[#090d14]/98 border-b border-[rgba(30,50,70,0.3)]">
        <div className="flex items-center justify-between px-4 h-14">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => navigate(-1)}
              className="p-2 -ml-2 rounded-lg hover:glass-card"
            >
              <ArrowLeft size={24} />
            </button>
            <CryptoIcon symbol={symbol || ''} size={32} />
            <div>
              <h1 className="font-semibold">{baseSymbol}</h1>
              <span className="text-xs text-[#5a6a7e]">{symbol}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={toggleFavorite}
              className={`p-2 rounded-lg hover:glass-card ${favorite ? 'text-[#D4AF37]' : 'text-[#5a6a7e]'}`}
            >
              <Star size={20} fill={favorite ? 'currentColor' : 'none'} />
            </button>
            <button className="p-2 rounded-lg hover:glass-card text-[#5a6a7e]">
              <Share2 size={20} />
            </button>
          </div>
        </div>
      </div>
      
      <div className="p-4 space-y-6">
        {/* Price Header */}
        <div className="text-center py-4">
          <div className="text-4xl font-bold font-mono">
            {formatCurrency(price.price)}
          </div>
          <div className={`flex items-center justify-center gap-2 mt-2 ${isPositive ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
            {isPositive ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
            <span className="font-mono text-lg">{formatPercent(priceChange)}</span>
            <span className="text-[#5a6a7e] text-sm">(24h)</span>
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="flex gap-1 glass-card rounded-xl p-1">
          {(['1h', '24h', '1w', '1m', '1y', 'all'] as TimeRange[]).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                timeRange === range 
                  ? 'bg-[#0F4C75] text-[#e8ecf1] 
                  : 'text-[#5a6a7e] hover:text-[#e8ecf1]
              }`}
            >
              {range === '1h' && '1H'}
              {range === '24h' && '24H'}
              {range === '1w' && '1W'}
              {range === '1m' && '1M'}
              {range === '1y' && '1Y'}
              {range === 'all' && 'All'}
            </button>
          ))}
        </div>

        {/* Chart */}
        <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-4">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={isPositive ? '#22c55e' : '#ef4444'} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={isPositive ? '#22c55e' : '#ef4444'} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis 
                  dataKey="time" 
                  stroke="#64748b" 
                  fontSize={12}
                  tickLine={false}
                />
                <YAxis 
                  stroke="#64748b" 
                  fontSize={12}
                  tickLine={false}
                  domain={['auto', 'auto']}
                  tickFormatter={(value) => `$${value.toLocaleString()}`}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: '1px solid #334155',
                    borderRadius: '8px'
                  }}
                  formatter={(value: number) => [formatCurrency(value), 'Price']}
                />
                <Area 
                  type="monotone" 
                  dataKey="price" 
                  stroke={isPositive ? '#22c55e' : '#ef4444'} 
                  fillOpacity={1} 
                  fill="url(#colorPrice)" 
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="glass-card rounded-xl p-4">
            <div className="flex items-center gap-2 text-[#5a6a7e] mb-1">
              <BarChart3 size={16} />
              <span className="text-sm">Volume (24h)</span>
            </div>
            <div className="font-mono font-semibold">
              ${formatNumber((price.volume24h || 0) / 1e9)}B
            </div>
          </div>

          <div className="glass-card rounded-xl p-4">
            <div className="flex items-center gap-2 text-[#5a6a7e] mb-1">
              <Activity size={16} />
              <span className="text-sm">High / Low</span>
            </div>
            <div className="font-mono font-semibold text-sm">
              <span className="text-[#00C9A7]">${formatNumber(price.price * 1.02)}</span>
              <span className="text-[#3d4d60] mx-1">/</span>
              <span className="text-[#EF476F]">${formatNumber(price.price * 0.98)}</span>
            </div>
          </div>

          <div className="glass-card rounded-xl p-4">
            <div className="flex items-center gap-2 text-[#5a6a7e] mb-1">
              <Globe size={16} />
              <span className="text-sm">Exchange</span>
            </div>
            <div className="font-semibold">{price.exchange}</div>
          </div>

          <div className="glass-card rounded-xl p-4">
            <div className="flex items-center gap-2 text-[#5a6a7e] mb-1">
              <Clock size={16} />
              <span className="text-sm">Updated</span>
            </div>
            <div className="font-mono text-sm">Just now</div>
          </div>
        </div>

        {/* Trading Actions */}
        <div className="grid grid-cols-2 gap-3">
          <button 
            className="flex items-center justify-center gap-2 p-4 bg-[#00A88A] rounded-xl hover:bg-green-700 transition-colors"
          >
            <TrendingUp size={20} />
            <span className="font-semibold">Buy {baseSymbol}</span>
          </button>
          <button 
            className="flex items-center justify-center gap-2 p-4 bg-[#D63D5E] rounded-xl hover:bg-red-700 transition-colors"
          >
            <TrendingDown size={20} />
            <span className="font-semibold">Sell {baseSymbol}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
