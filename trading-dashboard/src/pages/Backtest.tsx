import { useState } from 'react';
import { 
  FlaskConical, Play, Calendar, DollarSign, 
  Target, TrendingUp, TrendingDown, Activity,
  BarChart3, Clock, Percent
} from 'lucide-react';
import { Header } from '../components/Header';
import { GlassCard, EmptyState } from '../components/ui/GlassCard';
import { api } from '../api/client';
import { BacktestResult } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';
import { ShimmerCard } from '../components/ui/GlassCard';

export function Backtest() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [params, setParams] = useState({
    strategy: 'arbitrage',
    days: 30,
    initialBalance: 10000,
    symbol: 'BTC/USDT',
  });

  async function runBacktest() {
    setLoading(true);
    try {
      const data = await api.runBacktest(params);
      setResult(data);
    } catch (error) {
      console.error('Failed to run backtest:', error);
    } finally {
      setLoading(false);
    }
  }

  const strategies = [
    { id: 'arbitrage', name: 'Binary Arbitrage', risk: 'low' },
    { id: 'sniper', name: '15-Min Sniper', risk: 'high' },
    { id: 'momentum', name: 'Momentum', risk: 'medium' },
    { id: 'contrarian', name: 'Contrarian', risk: 'medium' },
    { id: 'grid', name: 'Grid Trading', risk: 'low' },
    { id: 'breakout', name: 'Breakout', risk: 'high' },
  ];

  return (
    <div className="pb-20 lg:pb-6 lg:pl-[224px]">
      <Header title="Strategy Backtesting" />
      
      <div className="p-4 max-w-[960px] mx-auto space-y-6">
        {/* Configuration */}
        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <Settings className="text-[#3B82F6]" size={20} />
            <span className="font-semibold text-[#e8ecf1]">Backtest Configuration</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[#5a6a7e] mb-2">Strategy</label>
              <select
                value={params.strategy}
                onChange={(e) => setParams({...params, strategy: e.target.value})}
                className="input-glass w-full"
              >
                {strategies.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-[#5a6a7e] mb-2">Symbol</label>
              <select
                value={params.symbol}
                onChange={(e) => setParams({...params, symbol: e.target.value})}
                className="input-glass w-full"
              >
                <option value="BTC/USDT">BTC/USDT</option>
                <option value="ETH/USDT">ETH/USDT</option>
                <option value="SOL/USDT">SOL/USDT</option>
                <option value="BNB/USDT">BNB/USDT</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-[#5a6a7e] mb-2">Period (Days)</label>
              <input
                type="number"
                value={params.days}
                onChange={(e) => setParams({...params, days: parseInt(e.target.value)})}
                min={7}
                max={365}
                className="input-glass w-full"
              />
            </div>

            <div>
              <label className="block text-sm text-[#5a6a7e] mb-2">Initial Balance ($)</label>
              <input
                type="number"
                value={params.initialBalance}
                onChange={(e) => setParams({...params, initialBalance: parseInt(e.target.value)})}
                min={1000}
                step={1000}
                className="input-glass w-full"
              />
            </div>
          </div>

          <button
            onClick={runBacktest}
            disabled={loading}
            className="btn-primary w-full mt-4"
          >
            {loading ? (
              <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Running...</>
            ) : (
              <><Play size={18} /> Run Backtest</>
            )}
          </button>
        </GlassCard>

        {/* Results */}
        {result && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="text-[#00C9A7]" size={20} />
              <span className="font-semibold text-[#e8ecf1]">Backtest Results</span>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <GlassCard className="text-center">
                <div className="text-xs text-[#5a6a7e] mb-1">Total Return</div>
                <div className={`text-xl font-bold mono ${result.totalReturn >= 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
                  {formatPercent(result.totalReturn)}
                </div>
              </GlassCard>

              <GlassCard className="text-center">
                <div className="text-xs text-[#5a6a7e] mb-1">Max Drawdown</div>
                <div className="text-xl font-bold mono text-[#EF476F]">
                  {formatPercent(-result.maxDrawdown)}
                </div>
              </GlassCard>

              <GlassCard className="text-center">
                <div className="text-xs text-[#5a6a7e] mb-1">Sharpe Ratio</div>
                <div className="text-xl font-bold mono text-[#3B82F6]">
                  {result.sharpeRatio.toFixed(2)}
                </div>
              </GlassCard>

              <GlassCard className="text-center">
                <div className="text-xs text-[#5a6a7e] mb-1">Win Rate</div>
                <div className="text-xl font-bold mono text-[#00C9A7]">
                  {(result.winRate * 100).toFixed(1)}%
                </div>
              </GlassCard>
            </div>

            {/* Detailed Stats */}
            <GlassCard>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-[#5a6a7e]">Initial Balance</div>
                  <div className="mono text-[#e8ecf1]">{formatCurrency(result.initialBalance)}</div>
                </div>
                <div>
                  <div className="text-sm text-[#5a6a7e]">Final Balance</div>
                  <div className={`mono ${result.finalBalance >= result.initialBalance ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
                    {formatCurrency(result.finalBalance)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-[#5a6a7e]">Total Trades</div>
                  <div className="mono text-[#e8ecf1]">{result.trades}</div>
                </div>
                <div>
                  <div className="text-sm text-[#5a6a7e]">Period</div>
                  <div className="mono text-[#e8ecf1] text-xs">{result.startDate} to {result.endDate}</div>
                </div>
              </div>
            </GlassCard>
          </div>
        )}

        {/* Info */}
        {!result && !loading && (
          <EmptyState
            icon={<FlaskConical size={40} />}
            title="Run a Backtest"
            description="Configure parameters and click Run to see historical performance"
          />
        )}
      </div>
    </div>
  );
}
