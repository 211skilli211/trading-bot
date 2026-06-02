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
      <div className="pb-20 lg:pb-8 lg:pl-[224px]">
        <Header title="Solana DEX Sniper" />
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#D4AF37]"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="pb-20 lg:pb-8 lg:pl-[224px]">
      <Header title="Solana DEX Sniper" />
      
      <div className="p-4 space-y-4">
        {/* Status Banner */}
        <div className={`rounded-xl border p-4 transition-all ${
          enabled 
            ? 'bg-gradient-to-r from-green-600/20 to-emerald-600/20 border-[#00C9A7]/50 shadow-lg shadow-green-500/10' 
            : 'bg-gradient-to-r from-[#151d28] to-[#1a2332] border-[rgba(30,50,70,0.3)]'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-xl ${enabled ? 'bg-[#00C9A7]/30 animate-pulse' : 'bg-[#3d4d60]/30'}`}>
                {enabled ? <Radio className="text-[#00C9A7]" size={24} /> : <Zap className="text-[#5a6a7e]" size={24} />}
              </div>
              <div>
                <div className="font-bold text-lg flex items-center gap-2">
                  {enabled ? (
                    <>
                      <span className="text-[#00C9A7]">● LIVE</span>
                      <span>Monitoring Active</span>
                    </>
                  ) : (
                    <>
                      <span className="text-[#5a6a7e]">○ OFFLINE</span>
                      <span>Sniper Disabled</span>
                    </>
                  )}
                </div>
                <div className="text-sm text-[#5a6a7e]">
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
                  ? 'bg-[#EF476F] hover:bg-[#D63D5E] text-[#e8ecf1] shadow-lg shadow-red-500/30' 
                  : 'bg-[#00C9A7] hover:bg-[#00A88A] text-[#e8ecf1] shadow-lg shadow-green-500/30'
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
            <div className="mt-4 pt-4 border-t border-[#00C9A7]/20">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Search size={16} className={`text-[#3B82F6] ${scanning ? 'animate-spin' : ''}`} />
                  <span className="text-sm text-[#3B82F6]">
                    {scanning ? 'Scanning markets...' : 'Waiting for next scan'}
                  </span>
                </div>
                <div className="flex-1 h-2 bg-[#090d14] rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-1000"
                    style={{ width: scanning ? '100%' : '0%' }}
                  />
                </div>
                <div className="text-xs text-[#3d4d60]">
                  Jupiter: {status?.jupiterStatus || 'online'} • Raydium: {status?.raydiumStatus || 'online'}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="glass-card rounded-xl p-4 border border-[rgba(30,50,70,0.3)]">
            <div className="flex items-center gap-2 text-[#5a6a7e] text-xs mb-1">
              <Wallet size={14} />
              Wallet Status
            </div>
            <div className={`text-lg font-bold ${status?.walletConnected ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
              {status?.walletConnected ? 'Connected' : 'Not Connected'}
            </div>
          </div>

          <div className="glass-card rounded-xl p-4 border border-[rgba(30,50,70,0.3)]">
            <div className="flex items-center gap-2 text-[#5a6a7e] text-xs mb-1">
              <DollarSign size={14} />
              SOL Balance
            </div>
            <div className="text-lg font-bold text-[#D4AF37]">
              {status?.solBalance?.toFixed(2) || '0.00'} SOL
            </div>
          </div>

          <div className="glass-card rounded-xl p-4 border border-[rgba(30,50,70,0.3)]">
            <div className="flex items-center gap-2 text-[#5a6a7e] text-xs mb-1">
              <DollarSign size={14} />
              USDC Balance
            </div>
            <div className="text-lg font-bold text-[#3B82F6]">
              ${status?.usdcBalance?.toFixed(2) || '0.00'}
            </div>
          </div>

          <div className="glass-card rounded-xl p-4 border border-[rgba(30,50,70,0.3)]">
            <div className="flex items-center gap-2 text-[#5a6a7e] text-xs mb-1">
              <Activity size={14} />
              Today's Trades
            </div>
            <div className="text-lg font-bold text-[#D4AF37]">
              {trades.length}
            </div>
          </div>
        </div>

        {/* Activity Log */}
        {enabled && activityLogs.length > 0 && (
          <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] overflow-hidden">
            <div className="p-3 border-b border-[rgba(30,50,70,0.3)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-[#3B82F6]" />
                <span className="font-semibold">Live Activity Log</span>
              </div>
              <button 
                onClick={() => setActivityLogs([])}
                className="text-xs text-[#5a6a7e] hover:text-[#e8ecf1]"
              >
                Clear
              </button>
            </div>
            <div className="max-h-48 overflow-y-auto">
              {activityLogs.map((log) => (
                <div key={log.id} className="px-3 py-2 border-b border-[rgba(30,50,70,0.3)]/50 flex items-start gap-2 text-sm">
                  <span className="text-[#3d4d60] text-xs">{log.time}</span>
                  <span className={`flex-1 ${
                    log.type === 'success' ? 'text-[#00C9A7]' :
                    log.type === 'warning' ? 'text-[#D4AF37]' :
                    log.type === 'error' ? 'text-[#EF476F]' :
                    'text-[#e8ecf1]'
                  }`}>
                    {log.message}
                  </span>
                  {log.type === 'success' && <CheckCircle size={14} className="text-[#00C9A7]" />}
                  {log.type === 'error' && <AlertTriangle size={14} className="text-[#EF476F]" />}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Monitored Pairs */}
        <div>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Target size={20} className="text-[#D4AF37]" />
            Monitored Pairs {enabled && tokens.length > 0 && (
              <span className="text-sm text-[#3d4d60]">({tokens.length} active)</span>
            )}
          </h2>
          
          {!enabled ? (
            <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-8 text-center">
              <Zap size={48} className="mx-auto mb-3 text-[#3d4d60]" />
              <p className="text-[#5a6a7e]">Enable Solana Sniper to view monitored pairs</p>
              <button 
                onClick={toggleSolana}
                className="mt-3 px-4 py-2 bg-[#00A88A] rounded-lg text-sm font-medium"
              >
                Start Monitoring
              </button>
            </div>
          ) : tokens.length === 0 ? (
            <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-8 text-center">
              <RefreshCw size={32} className="mx-auto mb-3 text-[#3d4d60] animate-spin" />
              <p className="text-[#5a6a7e]">Loading market data...</p>
            </div>
          ) : (
            <div className="grid gap-2">
              {tokens.map((token) => (
                <div key={token.symbol} className="glass-card rounded-xl p-4 border border-[rgba(30,50,70,0.3)] hover:border-[#D4AF37]/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-[#D4AF37]/20 rounded-lg flex items-center justify-center text-[#D4AF37] font-bold">
                        {token.token[0]}
                      </div>
                      <div>
                        <div className="font-semibold">{token.symbol}</div>
                        <div className="text-xs text-[#5a6a7e]">
                          DEX: ${token.dexPrice?.toFixed(4)} • CEX: ${token.cexPrice?.toFixed(4)}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className={`font-mono font-bold ${(token.spread || 0) > 1 ? 'text-[#00C9A7]' : 'text-[#5a6a7e]'}`}>
                        {token.spread?.toFixed(2)}%
                      </div>
                      <div className="text-xs text-[#3d4d60]">
                        {(token.spread || 0) > 1 ? 'Opportunity detected!' : 'Spread normal'}
                      </div>
                    </div>
                  </div>
                  
                  {/* Progress bar for spread */}
                  <div className="mt-2 h-1.5 bg-[#090d14] rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${(token.spread || 0) > 1 ? 'bg-[#00C9A7] : 'bg-[#3d4d60]'}`}
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
            <ArrowRightLeft size={20} className="text-[#00C9A7]" />
            Recent Arbitrage Trades
          </h2>
          
          <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] overflow-hidden">
            {trades.length === 0 ? (
              <div className="p-8 text-center text-[#5a6a7e]">
                <ArrowRightLeft size={48} className="mx-auto mb-3 opacity-30" />
                <p>No trades executed yet</p>
                <p className="text-sm">Trades will appear here when opportunities are found</p>
              </div>
            ) : (
              <div className="divide-y divide-dark-700">
                {trades.map((trade) => (
                  <div key={trade.id} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${trade.side.includes('buy_dex') ? 'bg-[#00C9A7]/20' : 'bg-[#0F4C75]/20'}`}>
                        <ArrowRightLeft size={16} className={trade.side.includes('buy_dex') ? 'text-[#00C9A7]' : 'text-[#3B82F6]'} />
                      </div>
                      <div>
                        <div className="font-medium">{trade.symbol}</div>
                        <div className="text-xs text-[#5a6a7e]">
                          {formatTime(trade.timestamp)} • {trade.side.replace(/_/g, ' ')}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[#00C9A7] font-bold">+${trade.profit?.toFixed(2)}</div>
                      <div className="text-xs text-[#3d4d60]">{trade.profitPercent?.toFixed(2)}% profit</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="bg-[#0F4C75]/10 border border-[#0F4C75]/30 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Info className="text-[#3B82F6] flex-shrink-0 mt-0.5" size={18} />
            <div className="text-sm text-[#e8ecf1]">
              <p className="font-medium text-[#3B82F6] mb-1">How Solana Arbitrage Works</p>
              <p>Monitors price differences between Jupiter/Raydium DEXs and centralized exchanges. When a profitable spread is detected (&gt;1%), the system can automatically execute trades to capture the arbitrage profit.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
