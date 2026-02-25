import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Wallet, TrendingUp, DollarSign, Bitcoin, Coins, Link2, Beaker, AlertTriangle } from 'lucide-react';
import { Header } from '../components/Header';
import { PositionCard } from '../components/PositionCard';
import { api } from '../api/client';
import type { Portfolio as PortfolioType, Position, CurrencyBalance } from '../types';
import { 
  formatCrypto,
  formatPercent, 
  formatUSD,
  getChangeColor,
  getCurrencyConfig,
} from '../utils/format';


const COLORS = ['#3b82f6', '#22c55e', '#ef4444', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

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
        
        if (portfolioRes.status === 'fulfilled') {
          setPortfolio(portfolioRes.value);
        }
        if (positionsRes.status === 'fulfilled') {
          setPositions(positionsRes.value);
        }
      } catch (error) {
        console.error('Failed to load portfolio:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Use real currency data from API, fallback to empty array
  const currencyBalances: CurrencyBalance[] = portfolio?.currencies 
    ? Object.values(portfolio.currencies).filter(c => c.balance > 0)
    : [];

  const totalUsdValue = currencyBalances.reduce((sum, c) => sum + c.usdValue, 0);

  if (loading) {
    return (
      <div className="pb-20">
        <Header title="Portfolio" />
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
          <span className="text-gray-400">Loading portfolio...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="pb-20">
      <Header title="Portfolio" />
      
      <div className="p-4 space-y-6">
        {/* Tab Navigation */}
        <div className="flex bg-dark-800 rounded-lg p-1">
          {[
            { id: 'overview', label: 'Overview', icon: Wallet },
            { id: 'currencies', label: 'Currencies', icon: Coins },
            { id: 'allocation', label: 'Allocation', icon: PieChart },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as typeof activeTab)}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                activeTab === id
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* Paper Trading Indicator */}
        {portfolio?.isPaper && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <Beaker className="w-5 h-5 text-yellow-400" />
              </div>
              <div>
                <div className="font-semibold text-yellow-400">Paper Trading Mode</div>
                <div className="text-xs text-gray-400">
                  Simulated environment with $10,000 mock funds. No real money at risk.
                </div>
              </div>
            </div>
            <div className="text-xs text-yellow-400 bg-yellow-500/20 px-3 py-1 rounded-full">
              PRACTICE MODE
            </div>
          </div>
        )}

        {/* Live Mode - Wallet Required */}
        {portfolio?.mode === 'LIVE' && !portfolio?.walletConnected && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-500/20 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <div className="font-semibold text-red-400">Wallet Required for Live Trading</div>
                <div className="text-xs text-gray-400">
                  Connect a wallet to access your real portfolio
                </div>
              </div>
            </div>
            <a 
              href="/settings"
              className="px-4 py-2 bg-red-600 rounded-lg text-sm hover:bg-red-700 transition-colors"
            >
              Connect Wallet
            </a>
          </div>
        )}

        {/* Connect Wallet CTA (for live mode when no funds) */}
        {!portfolio?.isPaper && !portfolio?.walletConnected && portfolio?.balance === 0 && (
          <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl p-6 border border-blue-500/30 text-center">
            <Wallet className="w-12 h-12 mx-auto mb-3 text-blue-400" />
            <h3 className="text-lg font-semibold mb-2">Connect Your Wallet</h3>
            <p className="text-gray-400 text-sm mb-4">
              Connect your wallet to view your portfolio balances and start trading
            </p>
            <a 
              href="/settings"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Link2 className="w-4 h-4" />
              Connect Wallet
            </a>
          </div>
        )}

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <>
            {/* Balance Cards */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-dark-800 rounded-xl p-4">
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  <TrendingUp className="w-3 h-3" />
                  Total Equity
                </div>
                <div className="text-xl font-bold font-mono">
                  {formatUSD(portfolio?.equity || 0)}
                </div>
                {currencyBalances.find(c => c.currency === 'BTC') && (
                  <div className="text-xs text-gray-500 mt-1">
                    {formatCrypto(currencyBalances.find(c => c.currency === 'BTC')?.equity || 0, 'BTC')} BTC
                  </div>
                )}
              </div>
              <div className="bg-dark-800 rounded-xl p-4">
                <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                  <DollarSign className="w-3 h-3" />
                  Available
                </div>
                <div className="text-xl font-bold font-mono">
                  {formatUSD(portfolio?.balance || 0)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {currencyBalances.length} {currencyBalances.length === 1 ? 'currency' : 'currencies'}
                </div>
              </div>
            </div>

            {/* Multi-Currency Summary */}
            {currencyBalances.length > 0 && (
              <div className="bg-dark-800 rounded-xl p-4">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Coins className="w-4 h-4 text-blue-400" />
                  Balances
                </h3>
                <div className="space-y-2">
                  {currencyBalances.slice(0, 4).map((bal) => (
                    <div key={bal.currency} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{getCurrencyConfig(bal.currency).flag}</span>
                        <div>
                          <div className="font-medium">{bal.currency}</div>
                          <div className="text-xs text-gray-500">
                            {formatUSD(bal.usdValue)}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-mono font-medium">
                          {formatCrypto(bal.balance, bal.currency)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {((bal.usdValue / totalUsdValue) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                {currencyBalances.length > 4 && (
                  <div className="text-center mt-3 text-xs text-gray-500">
                    +{currencyBalances.length - 4} more currencies
                  </div>
                )}
              </div>
            )}

            {/* PnL */}
            <div className={`rounded-xl p-4 border ${
              (portfolio?.totalPnl || 0) >= 0 
                ? 'bg-green-500/10 border-green-500/30' 
                : 'bg-red-500/10 border-red-500/30'
            }`}>
              <div className="text-xs opacity-80 mb-1">Total P&L</div>
              <div className={`text-2xl font-bold font-mono ${
                getChangeColor(portfolio?.totalPnl || 0)
              }`}>
                {formatUSD(portfolio?.totalPnl || 0)}
                <span className="text-sm ml-2">
                  {formatPercent(portfolio?.totalPnlPercent || 0)}
                </span>
              </div>
            </div>
          </>
        )}

        {/* Currencies Tab */}
        {activeTab === 'currencies' && (
          <div className="bg-dark-800 rounded-xl p-4">
            <h3 className="font-semibold mb-4">All Currencies</h3>
            {currencyBalances.length > 0 ? (
              <>
                <div className="space-y-3">
                  {currencyBalances.map((bal) => (
                    <div key={bal.currency} className="flex items-center justify-between p-3 bg-dark-900/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-dark-700 flex items-center justify-center text-xl">
                          {getCurrencyConfig(bal.currency).flag}
                        </div>
                        <div>
                          <div className="font-medium">{bal.currency}</div>
                          <div className="text-xs text-gray-500">
                            {formatUSD(bal.usdValue)} • {((bal.usdValue / totalUsdValue) * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-mono font-medium">
                          {formatCrypto(bal.balance, bal.currency)}
                        </div>
                        <div className="text-xs text-gray-500">
                          Avail: {formatCrypto(bal.available, bal.currency)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* Total */}
                <div className="mt-4 pt-4 border-t border-white/10">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Total Value</span>
                    <span className="font-mono font-bold text-lg">{formatUSD(totalUsdValue)}</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-gray-500">
                No currency data available
              </div>
            )}
          </div>
        )}

        {/* Allocation Tab */}
        {activeTab === 'allocation' && portfolio?.allocation && portfolio.allocation.length > 0 && (
          <div className="bg-dark-800 rounded-xl p-4">
            <h3 className="font-semibold mb-4">Portfolio Allocation</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={portfolio.allocation}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="percent"
                  >
                    {portfolio.allocation.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: '1px solid #334155',
                      borderRadius: '8px'
                    }}
                    formatter={(value: number, _name: string, props: any) => [
                      `${value.toFixed(2)}% (${formatUSD(props.payload.value)})`,
                      props.payload.symbol
                    ]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-4">
              {portfolio.allocation.map((item, index) => (
                <div key={item.symbol} className="flex items-center gap-2 text-xs p-2 bg-dark-900/50 rounded">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="font-medium">{item.symbol}</span>
                  <span className="text-gray-400 ml-auto">{item.percent.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Positions */}
        <div>
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Bitcoin className="w-4 h-4 text-orange-400" />
            Positions ({positions.length})
          </h3>
          <div className="space-y-3">
            {positions.length > 0 ? (
              positions.map((position) => (
                <PositionCard key={position.id} position={position} />
              ))
            ) : (
              <div className="text-center py-8 bg-dark-800 rounded-xl">
                <div className="text-gray-500">No open positions</div>
                <div className="text-xs text-gray-600 mt-1">Start trading to see positions here</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
