import { useEffect, useState, useCallback } from 'react';
import {
  TrendingUp, Wallet, Bell, Activity, Bot,
  Zap, Users, LineChart, Sparkles, ChevronRight,
  Settings2, Coins
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { Header } from '../components/Header';
import { PositionCard } from '../components/PositionCard';
import { AlertBadge } from '../components/AlertBadge';
import { CryptoIcon } from '../components/CryptoIcon';
import { PortfolioChart } from '../components/PortfolioChart';
import { GlassCard, StatBlock, ShimmerCard, StatusBadge, PageHeader, EmptyState, PriceTag } from '../components/ui/GlassCard';
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
        if (data.mode) setTradingMode(data.mode);
      }
      if (pricesRes.status === 'fulfilled') setPrices(pricesRes.value.slice(0, 4));
      if (positionsRes.status === 'fulfilled') setPositions(positionsRes.value.slice(0, 3));
      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value.slice(0, 4));
      if (botRes.status === 'fulfilled') setBotStatus(botRes.value);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading && !portfolio) {
    return (
      <div className="flex flex-col gap-4 p-4 pb-24 lg:pb-8 lg:pl-[236px]">
        {/* Skeleton header */}
        <div className="flex items-center justify-between mb-5">
          <ShimmerCard height="h-8" />
          <ShimmerCard height="h-6" />
        </div>
        {/* Skeleton stats grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[1,2,3,4].map(i => <ShimmerCard key={i} height="h-20" />)}
        </div>
        {/* Skeleton chart */}
        <ShimmerCard height="h-48" />
        {/* Skeleton portfolio */}
        <ShimmerCard height="h-32" lines={3} />
        {/* Skeleton prices */}
        <ShimmerCard height="h-40" lines={4} />
      </div>
    );
  }

  const totalPnl = portfolio?.totalPnl || 0;
  const isLive = tradingMode === 'LIVE';

  const currencyBalances: CurrencyBalance[] = portfolio?.currencies
    ? Object.values(portfolio.currencies).filter(c => c.balance > 0)
    : [];

  const totalUsdValue = currencyBalances.reduce((sum, c) => sum + c.usdValue, 0);

  return (
    <div className="pb-20 lg:pb-6 lg:pl-[224px]">
      <Header title="Dashboard" totalPnl={totalPnl} />

      <div className="p-4 max-w-[1440px] mx-auto">

        {/* ========== Row 1: Status + KPI Grid (Perception L0 — clear hierarchy) ========== */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
          {/* Portfolio value — primary metric, spans 2 cols on desktop */}
          <GlassCard
            className="col-span-2 lg:col-span-2"
            variant={totalPnl >= 0 ? 'up' : 'down'}
            depth="elevate"
          >
            <StatBlock
              label="Portfolio Value"
              value={formatUSD(totalUsdValue)}
              change={totalPnl}
              icon={<Wallet size={14} />}
              variant={totalPnl >= 0 ? 'success' : 'danger'}
              size="lg"
            />
          </GlassCard>

          {/* P&L */}
          <GlassCard>
            <StatBlock
              label="Total P&L"
              value={`${totalPnl >= 0 ? '+' : ''}${formatPercent(totalPnl)}`}
              icon={<TrendingUp size={14} />}
              variant={totalPnl >= 0 ? 'success' : 'danger'}
            />
          </GlassCard>

          {/* Mode badge */}
          <GlassCard className="flex items-center justify-center">
            <StatusBadge status={isLive ? 'live' : 'paper'} />
          </GlassCard>

          {/* Active positions count */}
          <GlassCard>
            <StatBlock
              label="Positions"
              value={positions.length}
              icon={<Activity size={14} />}
              variant={positions.length > 0 ? 'default' : 'success'}
            />
          </GlassCard>
        </div>

        {/* ========== Row 2: Quick Navigation (Anti-slop: varied visual interest, not 4 equal cards) ========== */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <Link to="/zeroclaw" className="glass-card p-4 flex flex-col gap-2 group hover:border-blue-500/20">
            <div className="flex items-center justify-between">
              <Bot size={20} className="text-blue-400" />
              <ChevronRight size={16} className="text-[#3d4d60] group-hover:text-blue-400 transition-colors" />
            </div>
            <span className="text-sm font-semibold text-[#e8ecf1]">ZeroClaw AI</span>
            <span className="text-xs text-[#5a6a7e]">Command center</span>
          </Link>

          <Link to="/multi-agent" className="glass-card p-4 flex flex-col gap-2 group hover:border-blue-500/20">
            <div className="flex items-center justify-between">
              <Users size={20} className="text-[#3B82F6]" />
              <ChevronRight size={16} className="text-[#3d4d60] group-hover:text-blue-400 transition-colors" />
            </div>
            <span className="text-sm font-semibold text-[#e8ecf1]">Agents</span>
            <span className="text-xs text-[#5a6a7e]">Multi-agent swarm</span>
          </Link>

          <Link to="/strategies" className="glass-card p-4 flex flex-col gap-2 group hover:border-blue-500/20">
            <div className="flex items-center justify-between">
              <Settings2 size={20} className="text-[#FF6B35]" />
              <ChevronRight size={16} className="text-[#3d4d60] group-hover:text-blue-400 transition-colors" />
            </div>
            <span className="text-sm font-semibold text-[#e8ecf1]">Strategies</span>
            <span className="text-xs text-[#5a6a7e]">Manage strategies</span>
          </Link>

          <Link to="/settings" className="glass-card p-4 flex flex-col gap-2 group hover:border-blue-500/20">
            <div className="flex items-center justify-between">
              <LineChart size={20} className="text-[#D4AF37]" />
              <ChevronRight size={16} className="text-[#3d4d60] group-hover:text-blue-400 transition-colors" />
            </div>
            <span className="text-sm font-semibold text-[#e8ecf1]">Analytics</span>
            <span className="text-xs text-[#5a6a7e]">Performance data</span>
          </Link>
        </div>

        {/* ========== Row 3: Chart (Portfolio Analytics) ========== */}
        <div className="mb-4">
          <PortfolioChart />
        </div>

        {/* ========== Row 4: Two-column layout (Layout: asymmetry, not centered) ========== */}
        <div className="grid lg:grid-cols-5 gap-4">

          {/* Left: Holdings + Prices (3 cols) */}
          <div className="lg:col-span-3 space-y-4">
            {/* Holdings */}
            {currencyBalances.length > 0 ? (
              <GlassCard>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-[#e8ecf1] flex items-center gap-2">
                    <Coins size={16} className="text-blue-400" />
                    Holdings
                  </h2>
                  <Link to="/portfolio" className="btn-link text-xs">View All</Link>
                </div>
                <div className="space-y-1.5">
                  {currencyBalances.map((bal) => (
                    <div key={bal.currency} className="flex items-center justify-between p-2.5 rounded-lg hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-center gap-2.5">
                        <span className="text-base">{getCurrencyConfig(bal.currency).flag}</span>
                        <span className="font-medium text-sm text-[#e8ecf1]">{bal.currency}</span>
                      </div>
                      <div className="text-right">
                        <div className="mono text-sm text-[#e8ecf1]">{formatCrypto(bal.balance, bal.currency)}</div>
                        <div className="mono text-xs text-[#5a6a7e]">{formatUSD(bal.usdValue)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </GlassCard>
            ) : (
              <EmptyState
                icon={<Wallet size={32} />}
                title="No holdings yet"
                description="Connect an exchange or add paper trading funds to get started."
                action={<Link to="/settings" className="btn-primary text-xs">Configure Exchanges</Link>}
              />
            )}

            {/* Live Prices */}
            {prices.length > 0 && (
              <GlassCard>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-[#e8ecf1]">Live Prices</h2>
                  <Link to="/prices" className="btn-link text-xs flex items-center gap-0.5">
                    View All <ChevronRight size={14} />
                  </Link>
                </div>
                <div className="space-y-1.5">
                  {prices.map((price) => (
                    <Link
                      key={`${price.exchange}-${price.symbol}`}
                      to={`/coin/${encodeURIComponent(price.symbol)}`}
                      className="flex items-center justify-between p-2.5 rounded-lg hover:bg-white/[0.02] transition-colors"
                    >
                      <div className="flex items-center gap-2.5">
                        <CryptoIcon symbol={price.symbol} size={32} />
                        <div>
                          <div className="font-semibold text-sm text-[#e8ecf1]">{price.symbol}</div>
                          <div className="text-xs text-[#5a6a7e]">{price.exchange}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="mono text-sm font-semibold text-[#e8ecf1]">{formatUSD(price.price)}</div>
                        <div className={`mono text-xs ${(price.change24h || 0) >= 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
                          {formatPercent(price.change24h || 0)}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </GlassCard>
            )}
          </div>

          {/* Right: Positions + Alerts sidebar (2 cols) */}
          <div className="lg:col-span-2 space-y-4">
            {/* Positions */}
            {positions.length > 0 ? (
              <GlassCard>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-[#e8ecf1] flex items-center gap-2">
                    <Activity size={16} className="text-[#D4AF37]" />
                    Open Positions
                  </h2>
                  <StatusBadge status={isLive ? 'live' : 'paper'} label={positions.length.toString()} />
                </div>
                <div className="space-y-2">
                  {positions.map((position) => (
                    <PositionCard key={position.id} position={position} />
                  ))}
                </div>
              </GlassCard>
            ) : (
              <EmptyState
                icon={<Activity size={28} />}
                title="No open positions"
                description={isLive ? "Waiting for trade signals..." : "Paper trading — no active positions yet."}
              />
            )}

            {/* Alerts */}
            {alerts.length > 0 && (
              <GlassCard>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-[#e8ecf1] flex items-center gap-2">
                    <Bell size={16} className="text-[#FF6B35]" />
                    Recent Alerts
                    <span className="badge badge-alert">{alerts.length}</span>
                  </h2>
                  <Link to="/alerts" className="btn-link text-xs">View All</Link>
                </div>
                <div className="space-y-2">
                  {alerts.map((alert) => (
                    <AlertBadge key={alert.id} alert={alert} />
                  ))}
                </div>
              </GlassCard>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
