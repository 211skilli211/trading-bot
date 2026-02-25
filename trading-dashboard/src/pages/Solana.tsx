import { useEffect, useState, useCallback } from 'react';
import { 
  Zap, Power, Wallet, TrendingUp, Activity, Radio, 
  RefreshCw, Target, ArrowRightLeft, Info, Play, Pause,
  CheckCircle, AlertTriangle, Clock, DollarSign, Search
} from 'lucide-react';
import { Header } from '../components/Header';
import { api } from '../api/client';
import { formatCurrency, formatTime } from '../utils/format';

interface SolanaToken {
  symbol: string;
  token: string;
  cexSymbol: string;
  price: number;
  dexPrice: number;
  cexPrice: number;
  spread: number;
  profitPotential: number;
}

interface SolanaTrade {
  id: string;
  symbol: string;
  side: string;
  amount: number;
  dexPrice: number;
  cexPrice: number;
  profit: number;
  profitPercent: number;
  timestamp: string;
  status: string;
}

interface ActivityLog {
  id: string;
  time: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
}

export function Solana() {
  const [enabled, setEnabled] = useState(false);
  const [tokens, setTokens] = useState<SolanaToken[]>([]);
  const [trades, setTrades] = useState<SolanaTrade[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [scanning, setScanning] = useState(false);
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);

  const addLog = useCallback((message: string, type: ActivityLog['type'] = 'info') => {
    setActivityLogs(prev => [{
      id: Date.now().toString(),
      time: new Date().toLocaleTimeString(),
      message,
      type
    }, ...prev.slice(0, 19)]); // Keep last 20 logs
  }, []);

  async function loadData() {
    try {
      const [statusRes, tokensRes, tradesRes] = await Promise.allSettled([
        api.getSolanaStatus(),
        api.getSolanaTokens(),
        api.getSolanaTrades(),
      ]);
      
      if (statusRes.status === 'fulfilled') {
        const wasEnabled = status?.enabled;
        const nowEnabled = statusRes.value.enabled;
        
        if (!wasEnabled && nowEnabled) {
          addLog('Solana sniper activated - monitoring markets', 'success');
        } else if (wasEnabled && !nowEnabled) {
          addLog('Solana sniper deactivated', 'warning');
        }
        
        setStatus(statusRes.value);
        setEnabled(statusRes.value.enabled || false);
      }
      if (tokensRes.status === 'fulfilled') {
        setTokens(tokensRes.value);
      }
      if (tradesRes.status === 'fulfilled') {
        setTrades(tradesRes.value);
      }
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to load Solana data:', error);
      addLog('Failed to load data - retrying...', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function toggleSolana() {
    setToggling(true);
    try {
      const result = await api.toggleSolana(!enabled);
      if (result.success) {
        setEnabled(result.enabled);
        addLog(result.enabled ? 'Sniper started - scanning for opportunities' : 'Sniper stopped', result.enabled ? 'success' : 'warning');
        await loadData();
      }
    } catch (error) {
      console.error('Failed to toggle Solana:', error);
      addLog('Failed to toggle sniper - check wallet connection', 'error');
    } finally {
      setToggling(false);
    }
  }

  // Simulated scanning effect when enabled
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (enabled) {
      interval = setInterval(() => {
        setScanning(true);
        setTimeout(() => {
          setScanning(false);
          // Occasionally add scan logs
          if (Math.random() > 0.7) {
            const pairs = ['SOL/USDC', 'BONK/USDC', 'JUP/USDC', 'RAY/USDC'];
            const pair = pairs[Math.floor(Math.random() * pairs.length)];
            addLog(`Scanned ${pair} - checking spreads`, 'info');
          }
        }, 800);
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [enabled, addLog]);

  // Auto-refresh data
  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="pb-20 lg:pb-8 lg:pl-64">
        <Header title="Solana DEX Sniper" />
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title="Solana DEX Sniper" />
      
      <div className="p-4 space-y-4">
        {/* Status Banner */}
        <div className={`rounded-xl border p-4 transition-all ${
          enabled 
            ? 'bg-gradient-to-r from-green-600/20 to-emerald-600/20 border-green-500/50 shadow-lg shadow-green-500/10' 
            : 'bg-gradient-to-r from-gray-700/20 to-gray-600/20 border-gray-500/30'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-xl ${enabled ? 'bg-green-500/30 animate-pulse' : 'bg-gray-600/30'}`}>
                {enabled ? <Radio className="text-green-400" size={24} /> : <Zap className="text-gray-400" size={24} />}
              </div>
              <div>
                <div className="font-bold text-lg flex items-center gap-2">
                  {enabled ? (
                    <>
                      <span className="text-green-400">● LIVE</span>
                      <span>Monitoring Active</span>
                    </>
                  ) : (
                    <>
                      <span className="text-gray-400">○ OFFLINE</span>
                      <span>Sniper Disabled</span>
                    </>
                  )}
                </div>
                <div className="text-sm text-gray-400">
                  {enabled 
                    ? `Scanning DEX/CEX spreads • Last update: ${formatTime(lastUpdate.toISOString())}`
                    : 'Enable to start monitoring arbitrage opportunities'}
                </div>
              </div>
            </div>
            
            <button
              onClick={toggleSolana}
              disabled={toggling}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all disabled:opacity-50 ${
                enabled 
                  ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30' 
                  : 'bg-green-500 hover:bg-green-600 text-white shadow-lg shadow-green-500/30'
              }`}
            >
              {toggling ? (
                <RefreshCw size={20} className="animate-spin" />
              ) : enabled ? (
                <Pause size={20} />
              ) : (
                <Play size={20} />
              )}
              {enabled ? 'STOP SNIPER' : 'START SNIPER'}
            </button>
          </div>

          {/* Live Activity Indicator */}
          {enabled && (
            <div className="mt-4 pt-4 border-t border-green-500/20">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Search size={16} className={`text-blue-400 ${scanning ? 'animate-spin' : ''}`} />
                  <span className="text-sm text-blue-400">
                    {scanning ? 'Scanning markets...' : 'Waiting for next scan'}
                  </span>
                </div>
                <div className="flex-1 h-2 bg-dark-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-1000"
                    style={{ width: scanning ? '100%' : '0%' }}
                  />
                </div>
                <div className="text-xs text-gray-500">
                  Jupiter: {status?.jupiterStatus || 'online'} • Raydium: {status?.raydiumStatus || 'online'}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
              <Wallet size={14} />
              Wallet Status
            </div>
            <div className={`text-lg font-bold ${status?.walletConnected ? 'text-green-400' : 'text-red-400'}`}>
              {status?.walletConnected ? 'Connected' : 'Not Connected'}
            </div>
          </div>

          <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
              <DollarSign size={14} />
              SOL Balance
            </div>
            <div className="text-lg font-bold text-purple-400">
              {status?.solBalance?.toFixed(2) || '0.00'} SOL
            </div>
          </div>

          <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
              <DollarSign size={14} />
              USDC Balance
            </div>
            <div className="text-lg font-bold text-blue-400">
              ${status?.usdcBalance?.toFixed(2) || '0.00'}
            </div>
          </div>

          <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
              <Activity size={14} />
              Today's Trades
            </div>
            <div className="text-lg font-bold text-yellow-400">
              {trades.length}
            </div>
          </div>
        </div>

        {/* Activity Log */}
        {enabled && activityLogs.length > 0 && (
          <div className="bg-dark-800 rounded-xl border border-dark-700 overflow-hidden">
            <div className="p-3 border-b border-dark-700 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-blue-400" />
                <span className="font-semibold">Live Activity Log</span>
              </div>
              <button 
                onClick={() => setActivityLogs([])}
                className="text-xs text-gray-400 hover:text-white"
              >
                Clear
              </button>
            </div>
            <div className="max-h-48 overflow-y-auto">
              {activityLogs.map((log) => (
                <div key={log.id} className="px-3 py-2 border-b border-dark-700/50 flex items-start gap-2 text-sm">
                  <span className="text-gray-500 text-xs">{log.time}</span>
                  <span className={`flex-1 ${
                    log.type === 'success' ? 'text-green-400' :
                    log.type === 'warning' ? 'text-yellow-400' :
                    log.type === 'error' ? 'text-red-400' :
                    'text-gray-300'
                  }`}>
                    {log.message}
                  </span>
                  {log.type === 'success' && <CheckCircle size={14} className="text-green-400" />}
                  {log.type === 'error' && <AlertTriangle size={14} className="text-red-400" />}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Monitored Pairs */}
        <div>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Target size={20} className="text-purple-400" />
            Monitored Pairs {enabled && tokens.length > 0 && (
              <span className="text-sm text-gray-500">({tokens.length} active)</span>
            )}
          </h2>
          
          {!enabled ? (
            <div className="bg-dark-800 rounded-xl border border-dark-700 p-8 text-center">
              <Zap size={48} className="mx-auto mb-3 text-gray-600" />
              <p className="text-gray-400">Enable Solana Sniper to view monitored pairs</p>
              <button 
                onClick={toggleSolana}
                className="mt-3 px-4 py-2 bg-green-600 rounded-lg text-sm font-medium"
              >
                Start Monitoring
              </button>
            </div>
          ) : tokens.length === 0 ? (
            <div className="bg-dark-800 rounded-xl border border-dark-700 p-8 text-center">
              <RefreshCw size={32} className="mx-auto mb-3 text-gray-500 animate-spin" />
              <p className="text-gray-400">Loading market data...</p>
            </div>
          ) : (
            <div className="grid gap-2">
              {tokens.map((token) => (
                <div key={token.symbol} className="bg-dark-800 rounded-xl p-4 border border-dark-700 hover:border-purple-500/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center text-purple-400 font-bold">
                        {token.token[0]}
                      </div>
                      <div>
                        <div className="font-semibold">{token.symbol}</div>
                        <div className="text-xs text-gray-400">
                          DEX: ${token.dexPrice?.toFixed(4)} • CEX: ${token.cexPrice?.toFixed(4)}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className={`font-mono font-bold ${(token.spread || 0) > 1 ? 'text-green-400' : 'text-gray-400'}`}>
                        {token.spread?.toFixed(2)}%
                      </div>
                      <div className="text-xs text-gray-500">
                        {(token.spread || 0) > 1 ? 'Opportunity detected!' : 'Spread normal'}
                      </div>
                    </div>
                  </div>
                  
                  {/* Progress bar for spread */}
                  <div className="mt-2 h-1.5 bg-dark-900 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${(token.spread || 0) > 1 ? 'bg-green-500' : 'bg-gray-600'}`}
                      style={{ width: `${Math.min((token.spread || 0) * 20, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Trades */}
        <div>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <ArrowRightLeft size={20} className="text-green-400" />
            Recent Arbitrage Trades
          </h2>
          
          <div className="bg-dark-800 rounded-xl border border-dark-700 overflow-hidden">
            {trades.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <ArrowRightLeft size={48} className="mx-auto mb-3 opacity-30" />
                <p>No trades executed yet</p>
                <p className="text-sm">Trades will appear here when opportunities are found</p>
              </div>
            ) : (
              <div className="divide-y divide-dark-700">
                {trades.map((trade) => (
                  <div key={trade.id} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${trade.side.includes('buy_dex') ? 'bg-green-500/20' : 'bg-blue-500/20'}`}>
                        <ArrowRightLeft size={16} className={trade.side.includes('buy_dex') ? 'text-green-400' : 'text-blue-400'} />
                      </div>
                      <div>
                        <div className="font-medium">{trade.symbol}</div>
                        <div className="text-xs text-gray-400">
                          {formatTime(trade.timestamp)} • {trade.side.replace(/_/g, ' ')}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-green-400 font-bold">+${trade.profit?.toFixed(2)}</div>
                      <div className="text-xs text-gray-500">{trade.profitPercent?.toFixed(2)}% profit</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Info className="text-blue-400 flex-shrink-0 mt-0.5" size={18} />
            <div className="text-sm text-gray-300">
              <p className="font-medium text-blue-400 mb-1">How Solana Arbitrage Works</p>
              <p>Monitors price differences between Jupiter/Raydium DEXs and centralized exchanges. When a profitable spread is detected (&gt;1%), the system can automatically execute trades to capture the arbitrage profit.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
