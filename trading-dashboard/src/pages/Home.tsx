import { useEffect, useState, useCallback } from 'react';
import { 
  TrendingUp, Wallet, Bell, Activity, Bot, 
  Zap, Users, LineChart, Sparkles, ChevronRight,
  Settings2, Coins, Beaker
} from 'lucide-react';
import { Header } from '../components/Header';
import { PositionCard } from '../components/PositionCard';
import { AlertBadge } from '../components/AlertBadge';
import { CryptoIcon } from '../components/CryptoIcon';
import { PortfolioChart } from '../components/PortfolioChart';
import { api } from '../api/client';
import { Portfolio, Price, Position, Alert, BotStatus, CurrencyBalance } from '../types';
import { formatUSD, formatCrypto, formatPercent, getCurrencyConfig } from '../utils/format';

export function Home() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [prices, setPrices] = useState<Price[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [tradingMode, setTradingMode] = useState<'PAPER' | 'LIVE'>('PAPER');
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [portfolioRes, pricesRes, positionsRes, alertsRes, botRes] = await Promise.allSettled([
        api.getPortfolio(),
        api.getPrices(),
        api.getPositions(),
        api.getAlerts(),
        api.getBotStatus(),
      ]);

      if (portfolioRes.status === 'fulfilled') {
        const data = portfolioRes.value;
        setPortfolio(data);
        // Always sync mode from backend response
        if (data.mode) {
          setTradingMode(data.mode);
        }
      }
      if (pricesRes.status === 'fulfilled') setPrices(pricesRes.value.slice(0, 3));
      if (positionsRes.status === 'fulfilled') setPositions(positionsRes.value.slice(0, 2));
      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value.slice(0, 3));
      if (botRes.status === 'fulfilled') setBotStatus(botRes.value);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading && !portfolio) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
        <span className="text-gray-400">Loading dashboard...</span>
      </div>
    );
  }

  const totalPnl = portfolio?.totalPnl || 0;
  const isLive = tradingMode === 'LIVE';

  // Use real currency data from API
  const currencyBalances: CurrencyBalance[] = portfolio?.currencies 
    ? Object.values(portfolio.currencies).filter(c => c.balance > 0)
    : [];

  const totalUsdValue = currencyBalances.reduce((sum, c) => sum + c.usdValue, 0);

  return (
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title="Dashboard" totalPnl={totalPnl} />
      
      <div className="p-4 space-y-6">
        {/* Mode Indicator - Read Only */}
        <div className={`p-4 rounded-xl border-2 ${
          isLive ? 'bg-green-500/10 border-green-500' : 'bg-yellow-500/10 border-yellow-500'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${isLive ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`}></div>
              <div>
                <span className={`font-bold text-lg ${isLive ? 'text-green-400' : 'text-yellow-400'}`}>
                  {isLive ? '🔴 LIVE TRADING' : '📊 PAPER TRADING'}
                </span>
                <p className="text-sm text-gray-400">
                  {isLive 
                    ? 'Real trades with real money on connected exchanges' 
                    : 'Practice with simulated $10,000 funds - no risk to real capital'}
                </p>
              </div>
            </div>
            <a 
              href="/settings"
              className="px-4 py-2 bg-dark-700 hover:bg-dark-600 rounded-lg text-sm transition-colors"
            >
              Change in Settings
            </a>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <a href="/zeroclaw" className="p-4 bg-dark-800 rounded-xl border border-dark-700 hover:border-blue-500 transition-colors">
            <div className="flex items-center gap-2 mb-1 text-blue-400">
              <Bot size={18} />
              <span className="text-xs font-semibold uppercase">ZeroClaw</span>
            </div>
            <div className="text-sm">AI Command Center</div>
          </a>

          <a href="/multi-agent" className="p-4 bg-dark-800 rounded-xl border border-dark-700 hover:border-purple-500 transition-colors">
            <div className="flex items-center gap-2 mb-1 text-purple-400">
              <Users size={18} />
              <span className="text-xs font-semibold uppercase">Agents</span>
            </div>
            <div className="text-sm">Multi-Agent Swarm</div>
          </a>

          <a href="/strategies" className="p-4 bg-dark-800 rounded-xl border border-dark-700 hover:border-orange-500 transition-colors">
            <div className="flex items-center gap-2 mb-1 text-orange-400">
              <Settings2 size={18} />
              <span className="text-xs font-semibold uppercase">Strategies</span>
            </div>
            <div className="text-sm">Manage Strategies</div>
          </a>

          <a href="/settings" className="p-4 bg-dark-800 rounded-xl border border-dark-700 hover:border-green-500 transition-colors">
            <div className="flex items-center gap-2 mb-1 text-green-400">
              <Zap size={18} />
              <span className="text-xs font-semibold uppercase">Settings</span>
            </div>
            <div className="text-sm">API Keys & Config</div>
          </a>
        </div>

        {/* Portfolio Analytics Charts */}
        <PortfolioChart />

        {/* Multi-Currency Portfolio Summary */}
        <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl p-5 text-white">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Wallet size={20} />
              <span className="text-sm opacity-80">Total Portfolio Value</span>
              {portfolio?.isPaper && (
                <span className="text-[10px] bg-yellow-400/30 px-2 py-0.5 rounded-full">
                  PAPER
                </span>
              )}
              {isLive && (
                <span className="text-[10px] bg-green-400/30 px-2 py-0.5 rounded-full">
                  LIVE
                </span>
              )}
            </div>
            <Activity size={20} className="opacity-60" />
          </div>
          
          <div className="text-3xl font-bold font-mono mb-2">
            {formatUSD(totalUsdValue)}
          </div>
          
          <div className={`flex items-center gap-1 ${totalPnl >= 0 ? 'text-green-300' : 'text-red-300'}`}>
            <TrendingUp size={16} />
            <span className="font-mono">{formatPercent(totalPnl)}</span>
            <span className="text-sm opacity-60 ml-1">all time</span>
          </div>
        </div>

        {/* Currency Holdings */}
        {currencyBalances.length > 0 && (
          <div className="bg-dark-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Coins size={18} className="text-blue-400" />
                Holdings
              </h2>
              <a href="/portfolio" className="text-sm text-blue-400">View All</a>
            </div>
            <div className="space-y-2">
              {currencyBalances.map((bal) => (
                <div key={bal.currency} className="flex items-center justify-between p-2 bg-dark-900/50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{getCurrencyConfig(bal.currency).flag}</span>
                    <span className="font-medium">{bal.currency}</span>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-sm">{formatCrypto(bal.balance, bal.currency)}</div>
                    <div className="text-xs text-gray-500">{formatUSD(bal.usdValue)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Prices */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Live Prices</h2>
            <a href="/prices" className="text-sm text-blue-400 flex items-center gap-1">
              View All <ChevronRight size={16} />
            </a>
          </div>
          <div className="grid gap-3">
            {prices.map((price) => (
              <a 
                key={`${price.exchange}-${price.symbol}`} 
                href={`/coin/${encodeURIComponent(price.symbol)}`}
                className="flex items-center justify-between p-4 bg-dark-800 rounded-xl border border-dark-700 hover:border-blue-500/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <CryptoIcon symbol={price.symbol} size={40} />
                  <div>
                    <div className="font-semibold">{price.symbol}</div>
                    <div className="text-xs text-gray-400">{price.exchange}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono font-semibold">{formatUSD(price.price)}</div>
                  <div className={`text-sm ${(price.change24h || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatPercent(price.change24h || 0)}
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>

        {/* Positions */}
        {positions.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold mb-3">Open Positions</h2>
            <div className="space-y-3">
              {positions.map((position) => (
                <PositionCard key={position.id} position={position} />
              ))}
            </div>
          </div>
        )}

        {/* Recent Alerts */}
        {alerts.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Bell size={18} />
                Alerts
              </h2>
              <a href="/alerts" className="text-sm text-blue-400">View All</a>
            </div>
            <div className="space-y-3">
              {alerts.map((alert) => (
                <AlertBadge key={alert.id} alert={alert} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
