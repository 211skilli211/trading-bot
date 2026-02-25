import { useState } from 'react';
import { 
  FlaskConical, Play, Calendar, DollarSign, 
  Target, TrendingUp, TrendingDown, Activity,
  BarChart3, Clock, Percent
} from 'lucide-react';
import { Header } from '../components/Header';
import { api } from '../api/client';
import { BacktestResult } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';

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
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title="Strategy Backtesting" />
      
      <div className="p-4 space-y-6">
        {/* Configuration */}
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Settings className="text-blue-400" size={20} />
            <span className="font-semibold">Backtest Configuration</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Strategy</label>
              <select 
                value={params.strategy}
                onChange={(e) => setParams({...params, strategy: e.target.value})}
                className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
              >
                {strategies.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Symbol</label>
              <select 
                value={params.symbol}
                onChange={(e) => setParams({...params, symbol: e.target.value})}
                className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
              >
                <option value="BTC/USDT">BTC/USDT</option>
                <option value="ETH/USDT">ETH/USDT</option>
                <option value="SOL/USDT">SOL/USDT</option>
                <option value="BNB/USDT">BNB/USDT</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Period (Days)</label>
              <input 
                type="number"
                value={params.days}
                onChange={(e) => setParams({...params, days: parseInt(e.target.value)})}
                min={7}
                max={365}
                className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Initial Balance ($)</label>
              <input 
                type="number"
                value={params.initialBalance}
                onChange={(e) => setParams({...params, initialBalance: parseInt(e.target.value)})}
                min={1000}
                step={1000}
                className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          <button 
            onClick={runBacktest}
            disabled={loading}
            className="w-full mt-4 flex items-center justify-center gap-2 p-3 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Running...</>
            ) : (
              <><Play size={18} /> Run Backtest</>
            )}
          </button>
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="text-green-400" size={20} />
              <span className="font-semibold">Backtest Results</span>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-dark-800 rounded-xl p-4 text-center">
                <div className="text-xs text-gray-400 mb-1">Total Return</div>
                <div className={`text-xl font-bold ${result.totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPercent(result.totalReturn)}
                </div>
              </div>

              <div className="bg-dark-800 rounded-xl p-4 text-center">
                <div className="text-xs text-gray-400 mb-1">Max Drawdown</div>
                <div className="text-xl font-bold text-red-400">
                  {formatPercent(-result.maxDrawdown)}
                </div>
              </div>

              <div className="bg-dark-800 rounded-xl p-4 text-center">
                <div className="text-xs text-gray-400 mb-1">Sharpe Ratio</div>
                <div className="text-xl font-bold text-blue-400">
                  {result.sharpeRatio.toFixed(2)}
                </div>
              </div>

              <div className="bg-dark-800 rounded-xl p-4 text-center">
                <div className="text-xs text-gray-400 mb-1">Win Rate</div>
                <div className="text-xl font-bold text-green-400">
                  {(result.winRate * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Detailed Stats */}
            <div className="bg-dark-800 rounded-xl border border-dark-700 p-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-400">Initial Balance</div>
                  <div className="font-mono">{formatCurrency(result.initialBalance)}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-400">Final Balance</div>
                  <div className={`font-mono ${result.finalBalance >= result.initialBalance ? 'text-green-400' : 'text-red-400'}`}>
                    {formatCurrency(result.finalBalance)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-400">Total Trades</div>
                  <div className="font-mono">{result.trades}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-400">Period</div>
                  <div className="font-mono">{result.startDate} to {result.endDate}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Info */}
        {!result && !loading && (
          <div className="text-center py-12 text-gray-400">
            <FlaskConical size={64} className="mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Run a Backtest</p>
            <p className="text-sm mt-1">Configure parameters and click Run to see historical performance</p>
          </div>
        )}
      </div>
    </div>
  );
}

import { Settings } from 'lucide-react';
