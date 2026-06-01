import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Wallet, TrendingUp, DollarSign, Coins, Beaker, AlertTriangle } from 'lucide-react';
import { Header } from '../components/Header';
import { PositionCard } from '../components/PositionCard';
import { GlassCard, StatBlock, ShimmerCard, PageHeader, EmptyState, StatusBadge } from '../components/ui/GlassCard';
import { api } from '../api/client';
import type { Portfolio as PortfolioType, Position, CurrencyBalance } from '../types';
import { formatCrypto, formatPercent, formatUSD, getChangeColor, getCurrencyConfig } from '../utils/format';

const COLORS = ['#0F4C75', '#00C9A7', '#D4AF37', '#FF6B35', '#3B82F6', '#EF476F', '#22c55e', '#8b5cf6'];

export function Portfolio() {
  const [portfolio, setPortfolio] = useState<PortfolioType | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'currencies' | 'allocation'>('overview');

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [portfolioRes, positionsRes] = await Promise.allSettled([
          api.getPortfolio(),
          api.getPositions(),
        ]);
        if (portfolioRes.status === 'fulfilled') setPortfolio(portfolioRes.value);
        if (positionsRes.status === 'fulfilled') setPositions(positionsRes.value);
      } catch (error) {
        console.error('Failed to load portfolio:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const currencyBalances: CurrencyBalance[] = portfolio?.currencies
    ? Object.values(portfolio.currencies).filter(c => c.balance > 0)
    : [];

  const totalUsdValue = currencyBalances.reduce((sum, c) => sum + c.usdValue, 0);
  const totalPnl = portfolio?.totalPnl || 0;
  const isPaper = portfolio?.isPaper ?? true;

  if (loading) {
    return (
      <div className="pb-20 lg:pb-6 lg:pl-[224px]">
        <Header title="Portfolio" />
        <div className="p-4 max-w-[1200px] mx-auto space-y-4">
          <ShimmerCard height="h-28" />
          <div className="grid grid-cols-2 gap-3">
            <ShimmerCard height="h-24" />
            <ShimmerCard height="h-24" />
          </div>
          <ShimmerCard height="h-48" lines={4} />
        </div>
      </div>
    );
  }

  return (
    <div className="pb-20 lg:pb-6 lg:pl-[224px]">
      <Header title="Portfolio" totalPnl={totalPnl} />

      <div className="p-4 max-w-[1200px] mx-auto">
        <PageHeader
          title="Portfolio"
          subtitle={`${currencyBalances.length} currencies · ${positions.length} positions`}
          badge={<StatusBadge status={isPaper ? 'paper' : 'live'} />}
        />

        {/* KPI Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <GlassCard variant={totalPnl >= 0 ? 'up' : 'down'} depth="elevate">
            <StatBlock label="Total Value" value={formatUSD(totalUsdValue)} icon={<Wallet size={14} />} size="lg" />
          </GlassCard>
          <GlassCard>
            <StatBlock label="Total P&L" value={`${totalPnl >= 0 ? '+' : ''}${formatUSD(totalPnl)}`}
              change={portfolio?.totalPnlPercent} icon={<TrendingUp size={14} />}
              variant={totalPnl >= 0 ? 'success' : 'danger'} />
          </GlassCard>
          <GlassCard>
            <StatBlock label="Equity" value={formatUSD(portfolio?.equity || 0)} icon={<DollarSign size={14} />} />
          </GlassCard>
          <GlassCard>
            <StatBlock label="Available" value={formatUSD(portfolio?.balance || 0)}
              icon={<Coins size={14} />} variant="gold" />
          </GlassCard>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-4 p-1 rounded-xl bg-white/[0.02]">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'currencies', label: 'Currencies' },
            { id: 'allocation', label: 'Allocation' },
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as typeof activeTab)}
              className={[
                'flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors',
                activeTab === id
                  ? 'bg-[#0F4C75]/15 text-blue-400'
                  : 'text-[#5a6a7e] hover:text-[#e8ecf1]',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {/* Paper/Live banner */}
            {isPaper && (
              <GlassCard variant="gold" padding="sm">
                <div className="flex items-center gap-3">
                  <Beaker size={18} className="text-[#D4AF37]" />
                  <div>
                    <span className="text-sm font-semibold text-[#D4AF37]">Paper Trading Mode</span>
                    <p className="text-xs text-[#5a6a7e]">Simulated environment — no real money at risk.</p>
                  </div>
                </div>
              </GlassCard>
            )}

            {/* Currency Holdings */}
            {currencyBalances.length > 0 ? (
              <GlassCard>
                <h3 className="text-sm font-semibold text-[#e8ecf1] mb-3 flex items-center gap-2">
                  <Coins size={15} className="text-blue-400" />
                  Holdings
                </h3>
                <div className="space-y-1">
                  {currencyBalances.slice(0, 5).map((bal) => (
                    <div key={bal.currency} className="flex items-center justify-between p-2.5 rounded-lg hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-center gap-2.5">
                        <span className="text-base">{getCurrencyConfig(bal.currency).flag}</span>
                        <div>
                          <div className="font-medium text-sm text-[#e8ecf1]">{bal.currency}</div>
                          <div className="text-xs text-[#5a6a7e]">{formatUSD(bal.usdValue)}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="mono text-sm text-[#e8ecf1]">{formatCrypto(bal.balance, bal.currency)}</div>
                        <div className="text-xs text-[#5a6a7e]">{((bal.usdValue / totalUsdValue) * 100).toFixed(1)}%</div>
                      </div>
                    </div>
                  ))}
                </div>
                {currencyBalances.length > 5 && (
                  <p className="text-center mt-3 text-xs text-[#5a6a7e]">
                    +{currencyBalances.length - 5} more currencies
                  </p>
                )}
              </GlassCard>
            ) : (
              <EmptyState
                icon={<Wallet size={32} />}
                title="No holdings yet"
                description="Connect an exchange or add paper trading funds to get started."
              />
            )}

            {/* P&L Card */}
            <GlassCard variant={totalPnl >= 0 ? 'up' : 'down'}>
              <StatBlock
                label="Total P&L"
                value={`${totalPnl >= 0 ? '+' : ''}${formatUSD(totalPnl)}`}
                change={portfolio?.totalPnlPercent}
                icon={<TrendingUp size={14} />}
                variant={totalPnl >= 0 ? 'success' : 'danger'}
                size="lg"
              />
            </GlassCard>
          </div>
        )}

        {/* Currencies Tab */}
        {activeTab === 'currencies' && (
          <GlassCard>
            <h3 className="text-sm font-semibold text-[#e8ecf1] mb-3">All Currencies</h3>
            {currencyBalances.length > 0 ? (
              <>
                <div className="space-y-1">
                  {currencyBalances.map((bal) => (
                    <div key={bal.currency} className="flex items-center justify-between p-3 rounded-lg hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-white/[0.04] flex items-center justify-center text-lg">
                          {getCurrencyConfig(bal.currency).flag}
                        </div>
                        <div>
                          <div className="font-medium text-sm text-[#e8ecf1]">{bal.currency}</div>
                          <div className="text-xs text-[#5a6a7e]">
                            {formatUSD(bal.usdValue)} · {((bal.usdValue / totalUsdValue) * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="mono text-sm text-[#e8ecf1]">{formatCrypto(bal.balance, bal.currency)}</div>
                        <div className="text-xs text-[#5a6a7e]">Avail: {formatCrypto(bal.available, bal.currency)}</div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-4 pt-3 border-t border-[rgba(30,50,70,0.2)]">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-[#e8ecf1]">Total Value</span>
                    <span className="mono text-lg font-bold text-[#e8ecf1]">{formatUSD(totalUsdValue)}</span>
                  </div>
                </div>
              </>
            ) : (
              <EmptyState
                icon={<Coins size={28} />}
                title="No currency data"
                description="Connect an exchange to see your holdings here."
              />
            )}
          </GlassCard>
        )}

        {/* Allocation Tab */}
        {activeTab === 'allocation' && (
          <GlassCard>
            <h3 className="text-sm font-semibold text-[#e8ecf1] mb-4">Portfolio Allocation</h3>
            {portfolio?.allocation && portfolio.allocation.length > 0 ? (
              <>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={portfolio.allocation}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="percent"
                      >
                        {portfolio.allocation.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: 'rgba(15, 22, 32, 0.95)',
                          border: '1px solid rgba(30, 50, 70, 0.4)',
                          borderRadius: '12px',
                          color: '#e8ecf1',
                          fontSize: '0.8rem',
                        }}
                        formatter={(value: number, _name: string, props: any) => [
                          `${value.toFixed(2)}% (${formatUSD(props.payload.value)})`,
                          props.payload.symbol,
                        ]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-4">
                  {portfolio.allocation.map((item, index) => (
                    <div key={item.symbol} className="flex items-center gap-2 text-xs p-2 rounded-lg bg-white/[0.02]">
                      <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                      <span className="font-medium text-[#e8ecf1]">{item.symbol}</span>
                      <span className="text-[#5a6a7e] ml-auto mono">{item.percent.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <EmptyState
                icon={<PieChart size={28} />}
                title="No allocation data"
                description="Add funds to see your portfolio allocation."
              />
            )}
          </GlassCard>
        )}

        {/* Positions */}
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-[#e8ecf1] mb-3 flex items-center gap-2">
            <TrendingUp size={15} className="text-[#D4AF37]" />
            Positions ({positions.length})
          </h3>
          {positions.length > 0 ? (
            <div className="space-y-2">
              {positions.map((position) => (
                <PositionCard key={position.id} position={position} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<TrendingUp size={28} />}
              title="No open positions"
              description="Start trading to see positions here."
            />
          )}
        </div>
      </div>
    </div>
  );
}
