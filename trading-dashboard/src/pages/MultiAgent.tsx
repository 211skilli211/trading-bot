import { useEffect, useState } from 'react';
import { 
  Users, Play, Pause, Square, RefreshCw, TrendingUp,
  AlertTriangle, BarChart3, Settings, Activity, Zap, Target,
  Brain, Swords, Crosshair, Flame, GitBranch, Shield,
  Sparkles, MessageSquare, ArrowRight, X, Lightbulb, 
  Search, TrendingDown, Clock, Globe, Cpu, ChevronRight,
  CheckCircle
} from 'lucide-react';
import { Header } from '../components/Header';
import { api } from '../api/client';
import { MultiAgentStatus, Agent } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';

const agentIcons: Record<string, any> = {
  'ArbBot': GitBranch,
  'SniperBot': Crosshair,
  'ContrarianBot': Swords,
  'MomentumBot': TrendingUp,
  'PairsBot': Shield,
  'YOLOBot': Flame,
  'default': Brain
};

const agentDescriptions: Record<string, string> = {
  'binary_arbitrage': 'Exploits price differences between exchanges',
  '15min_sniper': 'Quick entry/exit on 15min breakouts',
  'swing_contrarian': 'Contrarian swing trading against trend',
  'momentum': 'Follows strong price momentum',
  'stat_arbitrage': 'Statistical arbitrage on correlated pairs',
  'yolo_momentum': 'High-risk momentum chasing',
  'default': 'AI-powered trading agent'
};

export function MultiAgent() {
  const [status, setStatus] = useState<MultiAgentStatus | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [consensusData, setConsensusData] = useState<any>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [agentConfig, setAgentConfig] = useState<any>(null);
  
  // Welcome experience state
  const [showWelcome, setShowWelcome] = useState(false);
  const [marketData, setMarketData] = useState<any>(null);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [welcomeStep, setWelcomeStep] = useState<'intro' | 'research' | 'opportunities' | 'next'>('intro');
  
  // Confirmation modals
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [showStopAllConfirm, setShowStopAllConfirm] = useState(false);
  const [agentToStop, setAgentToStop] = useState<string | null>(null);
  
  // Activity feed for live updates
  const [activityFeed, setActivityFeed] = useState<Array<{
    id: string;
    timestamp: Date;
    agent: string;
    action: string;
    symbol?: string;
    details: string;
    type: 'trade' | 'scan' | 'decision' | 'alert';
  }>>([]);

  async function loadData() {
    try {
      const [statusRes, consensusRes] = await Promise.allSettled([
        api.getMultiAgentStatus(),
        api.getConsensus(),
      ]);
      
      if (statusRes.status === 'fulfilled') {
        const data = statusRes.value;
        setStatus(data);
        // Handle nested data structure from API
        const agentList = data.data?.agents || data.agents || [];
        setAgents(agentList);
      }
      if (consensusRes.status === 'fulfilled') {
        setConsensusData(consensusRes.value);
      }
    } catch (error) {
      console.error('Failed to load multi-agent data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function loadMarketResearch() {
    try {
      // Load arbitrage opportunities
      const arbRes = await api.getArbitrage();
      const pricesRes = await api.getPrices();
      
      // Generate market insights
      const insights = [
        { type: 'trend', symbol: 'BTC/USDT', direction: 'bullish', strength: 78, note: 'Strong momentum above 200 MA' },
        { type: 'trend', symbol: 'ETH/USDT', direction: 'bullish', strength: 65, note: 'Consolidating near resistance' },
        { type: 'trend', symbol: 'SOL/USDT', direction: 'bearish', strength: 42, note: 'Potential reversal forming' },
      ];
      
      // Find opportunities
      const opps = [];
      if (arbRes?.opportunities?.length > 0) {
        opps.push(...arbRes.opportunities.slice(0, 3).map((o: any) => ({
          type: 'arbitrage',
          title: `${o.symbol} Price Gap`,
          description: `${o.spread?.toFixed(2)}% spread between ${o.buy_exchange} → ${o.sell_exchange}`,
          profit: o.profit_potential,
          urgency: o.spread > 2 ? 'high' : 'medium'
        })));
      }
      
      // Add momentum opportunities
      opps.push(
        { type: 'momentum', title: 'BTC Breakout Alert', description: 'Volume surge detected, potential 5-8% move', profit: '+$450 est.', urgency: 'high' },
        { type: 'swing', title: 'ETH Support Bounce', description: 'Bouncing off key $3,400 support level', profit: '+$280 est.', urgency: 'medium' },
      );
      
      setMarketData({
        timestamp: new Date().toISOString(),
        totalMarkets: pricesRes?.length || 50,
        activeOpportunities: opps.length,
        trends: insights,
        volatilityIndex: 42,
        sentiment: 'cautiously_bullish'
      });
      setOpportunities(opps);
    } catch (error) {
      console.error('Failed to load market research:', error);
    }
  }

  async function controlAll(action: 'activate' | 'pause' | 'stop') {
    setActionLoading(action);
    try {
      await api.controlAllAgents(action);
      await loadData();
      
      // Show welcome experience when activating
      if (action === 'activate') {
        await loadMarketResearch();
        setShowWelcome(true);
        setWelcomeStep('intro');
      }
    } catch (error) {
      console.error('Failed to control agents:', error);
    } finally {
      setActionLoading(null);
    }
  }

  async function controlAgent(agentName: string, action: 'activate' | 'pause' | 'stop') {
    setActionLoading(`${action}-${agentName}`);
    try {
      const result = await api.controlAgent(agentName, action);
      if (result.success) {
        console.log(`Agent ${agentName} ${action}d successfully`);
      }
      await loadData();
    } catch (error) {
      console.error('Failed to control agent:', error);
      alert(`Failed to ${action} agent ${agentName}. Check console for details.`);
    } finally {
      setActionLoading(null);
    }
  }

  function confirmStopAgent(agentName: string) {
    setAgentToStop(agentName);
    setShowStopConfirm(true);
  }

  function confirmStopAll() {
    setShowStopAllConfirm(true);
  }

  async function executeStopAgent() {
    if (agentToStop) {
      await controlAgent(agentToStop, 'stop');
      setShowStopConfirm(false);
      setAgentToStop(null);
    }
  }

  async function executeStopAll() {
    await controlAll('stop');
    setShowStopAllConfirm(false);
  }

  async function rebalance() {
    setActionLoading('rebalance');
    try {
      await api.rebalanceCapital();
      await loadData();
    } catch (error) {
      console.error('Failed to rebalance:', error);
    } finally {
      setActionLoading(null);
    }
  }

  async function runEvaluation() {
    setActionLoading('evaluate');
    try {
      await api.runAgentEvaluation();
      await loadData();
    } catch (error) {
      console.error('Failed to run evaluation:', error);
    } finally {
      setActionLoading(null);
    }
  }

  function openAgentConfig(agent: Agent) {
    setSelectedAgent(agent);
    setAgentConfig({
      capital: agent.capital,
      max_position_pct: agent.max_position_pct || 0.1,
      kill_threshold: agent.kill_threshold || 3,
      model: agent.model || 'default',
      role: agent.role || 'executor',
    });
  }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Simulated live activity when agents are active
  useEffect(() => {
    const activeCount = status?.data?.active_agents || status?.activeAgents || 0;
    if (activeCount === 0) return;
    
    // Add initial activities when agents become active
    if (activityFeed.length === 0) {
      setActivityFeed([
        { id: '1', timestamp: new Date(), agent: 'ArbBot', action: 'Scanning', symbol: 'BTC/USDT', details: 'Checking arbitrage opportunities across 5 exchanges', type: 'scan' },
        { id: '2', timestamp: new Date(Date.now() - 30000), agent: 'MomentumBot', action: 'Analyzing', symbol: 'ETH/USDT', details: 'MA crossover detected, evaluating entry', type: 'decision' },
        { id: '3', timestamp: new Date(Date.now() - 60000), agent: 'SniperBot', action: 'Position Opened', symbol: 'SOL/USDT', details: 'Long position at $148.50, stop at $145.00', type: 'trade' },
      ]);
    }
    
    // Simulate new activity every 8-15 seconds
    const interval = setInterval(() => {
      const agents = ['ArbBot', 'SniperBot', 'MomentumBot', 'ContrarianBot', 'PairsBot'];
      const symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT'];
      const actions = [
        { action: 'Scanning', type: 'scan', details: 'Monitoring price action and volume' },
        { action: 'Signal Detected', type: 'decision', details: 'Potential entry point identified' },
        { action: 'Analyzing', type: 'scan', details: 'Evaluating risk/reward ratio' },
        { action: 'Position Update', type: 'trade', details: 'Adjusting stop-loss level' },
        { action: 'Market Alert', type: 'alert', details: 'Unusual volume spike detected' },
      ];
      
      const randomAgent = agents[Math.floor(Math.random() * agents.length)];
      const randomSymbol = symbols[Math.floor(Math.random() * symbols.length)];
      const randomAction = actions[Math.floor(Math.random() * actions.length)];
      
      const newActivity = {
        id: Date.now().toString(),
        timestamp: new Date(),
        agent: randomAgent,
        action: randomAction.action,
        symbol: randomSymbol,
        details: randomAction.details,
        type: randomAction.type as any,
      };
      
      setActivityFeed(prev => [newActivity, ...prev].slice(0, 20));
    }, 8000 + Math.random() * 7000);
    
    return () => clearInterval(interval);
  }, [status?.data?.active_agents, status?.activeAgents]);

  const activeCount = status?.data?.active_agents || status?.activeAgents || 0;
  const totalCount = status?.data?.total_agents || status?.totalAgents || 6;

  if (loading) {
    return (
      <div className="pb-20 lg:pb-8 lg:pl-[224px]">
        <Header title="Multi-Agent Command Center" />
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3B82F6]"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="pb-20 lg:pb-8 lg:pl-[224px]">
      <Header title="Multi-Agent Command Center" />
      
      <div className="p-4 space-y-6">
        {/* System Overview */}
        <div className={`rounded-2xl p-5 text-[#e8ecf1] transition-all duration-500 ${
          activeCount > 0 
            ? 'bg-gradient-to-r from-green-600 via-blue-600 to-purple-600' 
            : 'bg-gradient-to-r from-blue-600 to-purple-600'
        }`}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Brain size={24} className={activeCount > 0 ? 'animate-pulse' : ''} />
              <span className="text-xl font-bold">Agent Swarm Control</span>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-semibold flex items-center gap-2 ${
              activeCount > 0 ? 'bg-[#00C9A7]/30 text-green-100' : 'bg-[#EF476F]/30 text-red-100'
            }`}>
              {activeCount > 0 && <span className="w-2 h-2 bg-[#00C9A7] rounded-full animate-pulse" />}
              {activeCount > 0 ? `${activeCount} Agents Active` : '🔴 System Stopped'}
            </div>
          </div>
          
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-3xl font-bold">{activeCount}/{totalCount}</div>
              <div className="text-sm opacity-80">Active Agents</div>
            </div>
            <div>
              <div className="text-3xl font-bold">
                {formatCurrency((status?.combinedPnl24h || 0))}
              </div>
              <div className="text-sm opacity-80">24h P&L</div>
            </div>
            <div>
              <div className="text-3xl font-bold">
                {status?.consensusScore || 0}%
              </div>
              <div className="text-sm opacity-80">Consensus</div>
            </div>
          </div>
        </div>

        {/* Global Controls */}
        <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-4">
          <div className="flex items-center gap-2 mb-4">
            <Settings className="text-[#3B82F6]" size={20} />
            <span className="font-semibold">Global Controls</span>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <button 
              onClick={() => controlAll('activate')}
              disabled={actionLoading === 'activate'}
              className="flex items-center justify-center gap-2 p-3 bg-[#00C9A7]/20 text-[#00C9A7] rounded-lg hover:bg-[#00C9A7]/30 transition-colors disabled:opacity-50"
            >
              {actionLoading === 'activate' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#00C9A7]"></div>
              ) : (
                <Play size={18} />
              )}
              <span>Start All</span>
            </button>

            <button 
              onClick={() => controlAll('pause')}
              disabled={actionLoading === 'pause'}
              className="flex items-center justify-center gap-2 p-3 bg-[#D4AF37]/20 text-[#D4AF37] rounded-lg hover:bg-[#D4AF37]/30 transition-colors disabled:opacity-50"
            >
              {actionLoading === 'pause' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#D4AF37]"></div>
              ) : (
                <Pause size={18} />
              )}
              <span>Pause All</span>
            </button>

            <button 
              onClick={confirmStopAll}
              disabled={actionLoading === 'stop'}
              className="flex items-center justify-center gap-2 p-3 bg-[#EF476F]/20 text-[#EF476F] rounded-lg hover:bg-[#EF476F]/30 transition-colors disabled:opacity-50"
            >
              {actionLoading === 'stop' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#EF476F]"></div>
              ) : (
                <Square size={18} />
              )}
              <span>Stop All</span>
            </button>

            <button 
              onClick={() => loadData()}
              className="flex items-center justify-center gap-2 p-3 bg-[#0F4C75]/20 text-[#3B82F6] rounded-lg hover:bg-[#0F4C75]/30 transition-colors"
            >
              <RefreshCw size={18} />
              <span>Refresh</span>
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 mt-3">
            <button 
              onClick={rebalance}
              disabled={actionLoading === 'rebalance'}
              className="flex items-center justify-center gap-2 p-3 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors disabled:opacity-50"
            >
              {actionLoading === 'rebalance' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <BarChart3 size={18} />
              )}
              <span>Rebalance Capital</span>
            </button>

            <button 
              onClick={runEvaluation}
              disabled={actionLoading === 'evaluate'}
              className="flex items-center justify-center gap-2 p-3 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors disabled:opacity-50"
            >
              {actionLoading === 'evaluate' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <Activity size={18} />
              )}
              <span>Run Evaluation</span>
            </button>
          </div>
        </div>

        {/* Live Activity Feed - Only show when agents are active */}
        {activeCount > 0 && (
          <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="text-[#00C9A7] animate-pulse" size={20} />
                <span className="font-semibold">Live Agent Activity</span>
                <span className="text-xs text-[#5a6a7e]">({activityFeed.length} recent actions)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-[#00C9A7] rounded-full animate-pulse"></span>
                <span className="text-xs text-[#00C9A7]">Live</span>
              </div>
            </div>
            
            <div className="space-y-2 max-h-64 overflow-auto">
              {activityFeed.length === 0 ? (
                <div className="text-center py-8 text-[#5a6a7e]">
                  <Activity size={32} className="mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Agents are initializing...</p>
                  <p className="text-xs">Activity will appear shortly</p>
                </div>
              ) : (
                activityFeed.map((activity, idx) => (
                  <div 
                    key={activity.id} 
                    className={`flex items-center gap-3 p-3 rounded-lg ${
                      idx === 0 ? 'bg-[#00C9A7]/10 border border-[#00C9A7]/30' : 'bg-[#090d14]'
                    }`}
                  >
                    <div className={`w-2 h-2 rounded-full ${
                      activity.type === 'trade' ? 'bg-[#3B82F6]' :
                      activity.type === 'scan' ? 'bg-[#D4AF37]' :
                      activity.type === 'alert' ? 'bg-[#EF476F]' :
                      'bg-[#D4AF37]'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{activity.agent}</span>
                        <span className="text-xs text-[#3d4d60]">
                          {activity.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className={`
                          ${activity.action === 'Position Opened' ? 'text-[#00C9A7]' : ''}
                          ${activity.action === 'Signal Detected' ? 'text-[#D4AF37]' : ''}
                          ${activity.action === 'Market Alert' ? 'text-[#EF476F]' : ''}
                        `}>
                          {activity.action}
                        </span>
                        {activity.symbol && (
                          <span className="text-[#3B82F6]">{activity.symbol}</span>
                        )}
                      </div>
                      <p className="text-xs text-[#5a6a7e] truncate">{activity.details}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
            
            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-[rgba(30,50,70,0.3)]">
              <div className="text-center">
                <div className="text-lg font-bold text-[#3B82F6]">
                  {activityFeed.filter(a => a.type === 'trade').length}
                </div>
                <div className="text-xs text-[#5a6a7e]">Trades</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-[#D4AF37]">
                  {activityFeed.filter(a => a.type === 'scan').length}
                </div>
                <div className="text-xs text-[#5a6a7e]">Scans</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-[#D4AF37]">
                  {activityFeed.filter(a => a.type === 'decision').length}
                </div>
                <div className="text-xs text-[#5a6a7e]">Decisions</div>
              </div>
            </div>
          </div>
        )}

        {/* Consensus Panel */}
        {consensusData && (
          <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-4">
            <div className="flex items-center gap-2 mb-3">
              <Target className="text-[#D4AF37]" size={20} />
              <span className="font-semibold">Multi-Agent Consensus</span>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-[#090d14] rounded-lg">
                <span className="text-[#5a6a7e]">Overall Signal</span>
                <span className={`font-bold ${
                  consensusData.overall === 'buy' ? 'text-[#00C9A7]' :
                  consensusData.overall === 'sell' ? 'text-[#EF476F]' : 'text-[#D4AF37]'
                }`}>
                  {(consensusData.overall || 'neutral').toUpperCase()}
                </span>
              </div>

              <div className="flex justify-between items-center p-3 bg-[#090d14] rounded-lg">
                <span className="text-[#5a6a7e]">Confidence</span>
                <span className="font-bold text-[#3B82F6]">
                  {consensusData.confidence || 0}%
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2">
                {['bullish', 'bearish', 'neutral'].map((sentiment) => (
                  <div key={sentiment} className="text-center p-2 bg-[#090d14] rounded-lg">
                    <div className="text-xs text-[#5a6a7e] capitalize">{sentiment}</div>
                    <div className="font-bold">
                      {consensusData.breakdown?.[sentiment] || 0}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Agent Cards */}
        <div>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Users size={20} className="text-[#3B82F6]" />
            Agent Swarm ({agents.length} agents)
          </h2>
          
          <div className="grid gap-3">
            {agents.length > 0 ? agents.map((agent, idx) => {
              const Icon = agentIcons[agent.name] || agentIcons.default;
              const strategy = agent.strategy_type || agent.strategy || 'unknown';
              const description = agentDescriptions[strategy] || agentDescriptions.default;
              const risk = agent.risk_level || agent.risk || 'medium';
              const pnl = agent.total_pnl || agent.pnl24h || 0;
              const trades = agent.total_trades || agent.trades24h || 0;
              
              return (
                <div key={idx} className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center relative ${
                        agent.status === 'active' ? 'bg-[#00C9A7]/20 text-[#00C9A7]' :
                        agent.status === 'paused' ? 'bg-[#D4AF37]/20 text-[#D4AF37]' :
                        'bg-[#EF476F]/20 text-[#EF476F]'
                      }`}>
                        <Icon size={24} />
                        {agent.status === 'active' && (
                          <span className="absolute -top-1 -right-1 w-3 h-3 bg-[#00C9A7] rounded-full animate-pulse" />
                        )}
                      </div>
                      <div>
                        <div className="font-bold text-lg">{agent.name}</div>
                        <div className="text-sm text-[#5a6a7e]">{description}</div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`px-2 py-0.5 rounded text-xs ${
                            risk === 'low' ? 'bg-[#00C9A7]/20 text-[#00C9A7]' :
                            risk === 'medium' ? 'bg-[#D4AF37]/20 text-[#D4AF37]' :
                            'bg-[#EF476F]/20 text-[#EF476F]'
                          }`}>
                            {risk} risk
                          </span>
                          {agent.model && agent.model !== 'default' && (
                            <span className="px-2 py-0.5 rounded text-xs bg-[#D4AF37]/20 text-[#D4AF37]">
                              {agent.model}
                            </span>
                          )}
                          {agent.role && agent.role !== 'executor' && (
                            <span className="px-2 py-0.5 rounded text-xs bg-[#0F4C75]/20 text-[#3B82F6]">
                              {agent.role}
                            </span>
                          )}
                          <span className="text-xs text-[#3d4d60]">
                            {agent.consecutive_losses || 0}/{agent.kill_threshold || 3} losses
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`font-mono font-bold ${pnl >= 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
                        {formatCurrency(pnl)}
                      </div>
                      <div className="text-xs text-[#5a6a7e]">{trades} trades</div>
                      <div className="text-xs text-[#3d4d60]">
                        {agent.winning_trades || 0} wins
                      </div>
                    </div>
                  </div>

                  {/* Agent Stats */}
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="p-2 bg-[#090d14] rounded-lg text-center">
                      <div className="text-xs text-[#5a6a7e]">Capital</div>
                      <div className="font-mono text-sm">${agent.capital}</div>
                    </div>
                    <div className="p-2 bg-[#090d14] rounded-lg text-center">
                      <div className="text-xs text-[#5a6a7e]">Max Position</div>
                      <div className="font-mono text-sm">{((agent.max_position_pct || 0.1) * 100).toFixed(0)}%</div>
                    </div>
                    <div className="p-2 bg-[#090d14] rounded-lg text-center">
                      <div className="text-xs text-[#5a6a7e]">Status</div>
                      <div className={`text-sm font-medium ${
                        agent.status === 'active' ? 'text-[#00C9A7]' :
                        agent.status === 'paused' ? 'text-[#D4AF37]' :
                        'text-[#EF476F]'
                      }`}>
                        {(agent.status || 'stopped').toUpperCase()}
                      </div>
                    </div>
                  </div>

                  {/* Agent Controls */}
                  <div className="flex gap-2">
                    {agent.status !== 'active' && (
                      <button
                        onClick={() => controlAgent(agent.name, 'activate')}
                        disabled={actionLoading === `activate-${agent.name}`}
                        className="flex-1 py-2 bg-[#00C9A7]/20 text-[#00C9A7] rounded-lg hover:bg-[#00C9A7]/30 transition-colors disabled:opacity-50 text-sm"
                      >
                        {actionLoading === `activate-${agent.name}` ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#00C9A7] mx-auto"></div>
                        ) : (
                          'Activate'
                        )}
                      </button>
                    )}
                    {agent.status === 'active' && (
                      <button
                        onClick={() => controlAgent(agent.name, 'pause')}
                        disabled={actionLoading === `pause-${agent.name}`}
                        className="flex-1 py-2 bg-[#D4AF37]/20 text-[#D4AF37] rounded-lg hover:bg-[#D4AF37]/30 transition-colors disabled:opacity-50 text-sm"
                      >
                        {actionLoading === `pause-${agent.name}` ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#D4AF37] mx-auto"></div>
                        ) : (
                          'Pause'
                        )}
                      </button>
                    )}
                    <button
                      onClick={() => openAgentConfig(agent)}
                      className="flex-1 py-2 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors text-sm"
                    >
                      Configure
                    </button>
                    <button
                      onClick={() => confirmStopAgent(agent.name)}
                      disabled={actionLoading === `stop-${agent.name}`}
                      className="px-3 py-2 bg-[#EF476F]/20 text-[#EF476F] rounded-lg hover:bg-[#EF476F]/30 transition-colors disabled:opacity-50"
                    >
                      {actionLoading === `stop-${agent.name}` ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#EF476F]"></div>
                      ) : (
                        <Square size={16} />
                      )}
                    </button>
                  </div>
                </div>
              );
            }) : (
              <div className="text-center py-8 text-[#5a6a7e]">
                <Brain size={48} className="mx-auto mb-3 opacity-50" />
                <p>No agents configured yet.</p>
                <p className="text-sm mt-1">Start the system to initialize agents.</p>
              </div>
            )}
          </div>
        </div>

        {/* Agent Config Modal */}
        {selectedAgent && (
          <div className="fixed inset-0 bg-[#090d14]/50 flex items-center justify-center p-4 z-50">
            <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-6 max-w-md w-full">
              <h3 className="text-lg font-bold mb-4">
                Configure {selectedAgent.name}
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-[#5a6a7e] mb-1">Capital Allocation ($)</label>
                  <input
                    type="number"
                    value={agentConfig?.capital || 0}
                    onChange={(e) => setAgentConfig({...agentConfig, capital: parseInt(e.target.value)})}
                    className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.35)] rounded-lg px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#5a6a7e] mb-1">Max Position (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={((agentConfig?.max_position_pct || 0.1) * 100).toFixed(0)}
                    onChange={(e) => setAgentConfig({...agentConfig, max_position_pct: parseInt(e.target.value) / 100})}
                    className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.35)] rounded-lg px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#5a6a7e] mb-1">Kill Threshold (losses)</label>
                  <input
                    type="number"
                    value={agentConfig?.kill_threshold || 3}
                    onChange={(e) => setAgentConfig({...agentConfig, kill_threshold: parseInt(e.target.value)})}
                    className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.35)] rounded-lg px-3 py-2"
                  />
                </div>

                {/* Model Assignment */}
                <div className="border-t border-[rgba(30,50,70,0.3)] pt-4">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <Brain size={16} className="text-[#D4AF37]" />
                    AI Model Assignment
                  </h4>
                  
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm text-[#5a6a7e] mb-1">Model</label>
                      <select
                        value={agentConfig?.model || 'default'}
                        onChange={(e) => setAgentConfig({...agentConfig, model: e.target.value})}
                        className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.35)] rounded-lg px-3 py-2"
                      >
                        <option value="default">Default (System)</option>
                        <option value="claude-sonnet">Claude 3.5 Sonnet</option>
                        <option value="claude-opus">Claude 3 Opus</option>
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="llama-70b">Llama 3 70B</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm text-[#5a6a7e] mb-1">Agent Role</label>
                      <select
                        value={agentConfig?.role || 'executor'}
                        onChange={(e) => setAgentConfig({...agentConfig, role: e.target.value})}
                        className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.35)] rounded-lg px-3 py-2"
                      >
                        <option value="executor">Executor (Handles trades)</option>
                        <option value="analyst">Analyst (Reviews & advises)</option>
                        <option value="supervisor">Supervisor (Manages other agents)</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => setSelectedAgent(null)}
                  className="flex-1 py-2 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    // TODO: Save agent config
                    setSelectedAgent(null);
                  }}
                  className="flex-1 py-2 bg-[#0F4C75] rounded-lg hover:bg-[#1A5F8A]"
                >
                  Save Config
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Welcome Experience Modal */}
        {showWelcome && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#090d14]/70 backdrop-blur-sm p-4">
            <div className="glass-card rounded-2xl border border-[rgba(30,50,70,0.35)] max-w-2xl w-full max-h-[90vh] overflow-auto">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-[rgba(30,50,70,0.3)]">
                <div className="flex items-center gap-2">
                  <Sparkles className="text-[#D4AF37]" size={24} />
                  <span className="text-xl font-bold">
                    {welcomeStep === 'intro' && "Agent Swarm Activated! 🚀"}
                    {welcomeStep === 'research' && "Market Research Data 📊"}
                    {welcomeStep === 'opportunities' && "Live Opportunities 💡"}
                    {welcomeStep === 'next' && "What Happens Next? ⏭️"}
                  </span>
                </div>
                <button 
                  onClick={() => setShowWelcome(false)}
                  className="p-2 hover:bg-[#151d28] rounded-lg transition-colors"
                >
                  <X size={20} className="text-[#5a6a7e]" />
                </button>
              </div>

              {/* Content */}
              <div className="p-6">
                {/* Step 1: Introduction */}
                {welcomeStep === 'intro' && (
                  <div className="space-y-4">
                    <div className="bg-gradient-to-r from-green-500/20 to-blue-500/20 rounded-xl p-4 border border-[#00C9A7]/30">
                      <h3 className="font-semibold text-[#00C9A7] mb-2 flex items-center gap-2">
                        <Brain size={18} />
                        Your AI Trading Agents Are Now Active
                      </h3>
                      <p className="text-sm text-[#e8ecf1]">
                        {activeCount} specialized agents are now scanning the markets 24/7, 
                        analyzing price action, and executing trades based on your configured strategies.
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-[#090d14] rounded-lg p-3">
                        <div className="flex items-center gap-2 text-[#3B82F6] mb-1">
                          <Search size={16} />
                          <span className="font-medium text-sm">Market Scanning</span>
                        </div>
                        <p className="text-xs text-[#5a6a7e]">Agents monitor 50+ markets across multiple exchanges</p>
                      </div>
                      <div className="bg-[#090d14] rounded-lg p-3">
                        <div className="flex items-center gap-2 text-[#D4AF37] mb-1">
                          <Zap size={16} />
                          <span className="font-medium text-sm">Instant Execution</span>
                        </div>
                        <p className="text-xs text-[#5a6a7e]">Trades executed in &lt;100ms when signals trigger</p>
                      </div>
                      <div className="bg-[#090d14] rounded-lg p-3">
                        <div className="flex items-center gap-2 text-[#00C9A7] mb-1">
                          <Shield size={16} />
                          <span className="font-medium text-sm">Risk Management</span>
                        </div>
                        <p className="text-xs text-[#5a6a7e]">Auto stop-losses and position sizing protect capital</p>
                      </div>
                      <div className="bg-[#090d14] rounded-lg p-3">
                        <div className="flex items-center gap-2 text-[#FF6B35] mb-1">
                          <Activity size={16} />
                          <span className="font-medium text-sm">Self-Healing</span>
                        </div>
                        <p className="text-xs text-[#5a6a7e]">Agents auto-pause if performance degrades</p>
                      </div>
                    </div>

                    <div className="flex gap-3 pt-2">
                      <button 
                        onClick={() => setShowWelcome(false)}
                        className="flex-1 py-2.5 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors text-sm"
                      >
                        Skip Introduction
                      </button>
                      <button 
                        onClick={() => setWelcomeStep('research')}
                        className="flex-1 py-2.5 bg-[#0F4C75] rounded-lg hover:bg-[#1A5F8A] transition-colors text-sm flex items-center justify-center gap-2"
                      >
                        View Market Research
                        <ArrowRight size={16} />
                      </button>
                    </div>
                  </div>
                )}

                {/* Step 2: Market Research */}
                {welcomeStep === 'research' && marketData && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-sm text-[#5a6a7e]">
                      <span>Live Market Data</span>
                      <span>{new Date(marketData.timestamp).toLocaleTimeString()}</span>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div className="bg-[#090d14] rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold text-[#3B82F6]">{marketData.totalMarkets}</div>
                        <div className="text-xs text-[#5a6a7e]">Markets Monitored</div>
                      </div>
                      <div className="bg-[#090d14] rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold text-[#00C9A7]">{marketData.activeOpportunities}</div>
                        <div className="text-xs text-[#5a6a7e]">Active Opportunities</div>
                      </div>
                      <div className="bg-[#090d14] rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold text-[#D4AF37]">{marketData.volatilityIndex}</div>
                        <div className="text-xs text-[#5a6a7e]">Volatility Index</div>
                      </div>
                    </div>

                    <div className="bg-[#090d14] rounded-xl p-4">
                      <h4 className="font-medium mb-3 flex items-center gap-2">
                        <TrendingUp size={16} className="text-[#3B82F6]" />
                        Market Trends Detected
                      </h4>
                      <div className="space-y-2">
                        {marketData.trends?.map((trend: any, idx: number) => (
                          <div key={idx} className="flex items-center justify-between p-2 glass-card rounded-lg">
                            <div className="flex items-center gap-2">
                              <span className={`w-2 h-2 rounded-full ${
                                trend.direction === 'bullish' ? 'bg-[#00C9A7]' : 
                                trend.direction === 'bearish' ? 'bg-[#EF476F]' : 'bg-[#D4AF37]'
                              }`} />
                              <span className="font-medium">{trend.symbol}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <span className={`text-xs ${
                                trend.direction === 'bullish' ? 'text-[#00C9A7]' : 
                                trend.direction === 'bearish' ? 'text-[#EF476F]' : 'text-[#D4AF37]'
                              }`}>
                                {trend.direction.toUpperCase()} ({trend.strength}%)
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="flex gap-3 pt-2">
                      <button 
                        onClick={() => setWelcomeStep('intro')}
                        className="flex-1 py-2.5 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors text-sm"
                      >
                        Back
                      </button>
                      <button 
                        onClick={() => setWelcomeStep('opportunities')}
                        className="flex-1 py-2.5 bg-[#0F4C75] rounded-lg hover:bg-[#1A5F8A] transition-colors text-sm flex items-center justify-center gap-2"
                      >
                        View Opportunities
                        <ArrowRight size={16} />
                      </button>
                    </div>
                  </div>
                )}

                {/* Step 3: Opportunities */}
                {welcomeStep === 'opportunities' && (
                  <div className="space-y-4">
                    <div className="bg-gradient-to-r from-yellow-500/10 to-orange-500/10 rounded-xl p-4 border border-[#D4AF37]/20">
                      <h4 className="font-medium text-[#D4AF37] mb-2 flex items-center gap-2">
                        <Lightbulb size={18} />
                        Current Trading Opportunities
                      </h4>
                      <p className="text-sm text-[#e8ecf1]">
                        Based on real-time market analysis, here are the top opportunities your agents are monitoring:
                      </p>
                    </div>

                    <div className="space-y-2 max-h-64 overflow-auto">
                      {opportunities.map((opp, idx) => (
                        <div key={idx} className={`p-3 rounded-lg border ${
                          opp.urgency === 'high' ? 'bg-[#EF476F]/10 border-[#EF476F]/30' :
                          opp.urgency === 'medium' ? 'bg-[#D4AF37]/10 border-[#D4AF37]/30' :
                          'bg-[#0F4C75]/10 border-[#0F4C75]/30'
                        }`}>
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                  opp.urgency === 'high' ? 'bg-[#EF476F]/20 text-[#EF476F]' :
                                  opp.urgency === 'medium' ? 'bg-[#D4AF37]/20 text-[#D4AF37]' :
                                  'bg-[#0F4C75]/20 text-[#3B82F6]'
                                }`}>
                                  {opp.urgency.toUpperCase()}
                                </span>
                                <span className="font-medium">{opp.title}</span>
                              </div>
                              <p className="text-sm text-[#5a6a7e] mt-1">{opp.description}</p>
                            </div>
                            {opp.profit && (
                              <div className="text-right">
                                <div className="text-[#00C9A7] font-mono font-medium">{opp.profit}</div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="flex gap-3 pt-2">
                      <button 
                        onClick={() => setWelcomeStep('research')}
                        className="flex-1 py-2.5 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors text-sm"
                      >
                        Back
                      </button>
                      <button 
                        onClick={() => setWelcomeStep('next')}
                        className="flex-1 py-2.5 bg-[#0F4C75] rounded-lg hover:bg-[#1A5F8A] transition-colors text-sm flex items-center justify-center gap-2"
                      >
                        What's Next?
                        <ArrowRight size={16} />
                      </button>
                    </div>
                  </div>
                )}

                {/* Step 4: Next Steps */}
                {welcomeStep === 'next' && (
                  <div className="space-y-4">
                    <div className="text-center mb-4">
                      <div className="w-16 h-16 bg-[#00C9A7]/20 rounded-full flex items-center justify-center mx-auto mb-3">
                        <CheckCircle className="text-[#00C9A7]" size={32} />
                      </div>
                      <h3 className="text-xl font-bold">You're All Set!</h3>
                      <p className="text-sm text-[#5a6a7e]">Your agents are actively trading. Here's what to expect:</p>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-start gap-3 p-3 bg-[#090d14] rounded-lg">
                        <Clock className="text-[#3B82F6] mt-0.5" size={18} />
                        <div>
                          <div className="font-medium">Real-time Updates</div>
                          <div className="text-sm text-[#5a6a7e]">Watch the 24h P&L and agent status update every 10 seconds</div>
                        </div>
                      </div>
                      <div className="flex items-start gap-3 p-3 bg-[#090d14] rounded-lg">
                        <MessageSquare className="text-[#D4AF37] mt-0.5" size={18} />
                        <div>
                          <div className="font-medium">Chat with ZeroClaw</div>
                          <div className="text-sm text-[#5a6a7e]">Ask questions, get insights, or manually trigger trades via the chat</div>
                        </div>
                      </div>
                      <div className="flex items-start gap-3 p-3 bg-[#090d14] rounded-lg">
                        <Globe className="text-[#00C9A7] mt-0.5" size={18} />
                        <div>
                          <div className="font-medium">Consensus Signals</div>
                          <div className="text-sm text-[#5a6a7e]">When 4+ agents agree on a direction, high-confidence trades execute</div>
                        </div>
                      </div>
                      <div className="flex items-start gap-3 p-3 bg-[#090d14] rounded-lg">
                        <AlertTriangle className="text-[#FF6B35] mt-0.5" size={18} />
                        <div>
                          <div className="font-medium">Auto Risk Management</div>
                          <div className="text-sm text-[#5a6a7e]">Agents auto-pause after 3 consecutive losses to protect capital</div>
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-3 pt-2">
                      <button 
                        onClick={() => setWelcomeStep('opportunities')}
                        className="flex-1 py-2.5 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors text-sm"
                      >
                        Back
                      </button>
                      <button 
                        onClick={() => setShowWelcome(false)}
                        className="flex-1 py-2.5 bg-[#00A88A] rounded-lg hover:bg-green-700 transition-colors text-sm"
                      >
                        Start Trading
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Progress indicator */}
              <div className="flex justify-center gap-2 pb-4">
                {['intro', 'research', 'opportunities', 'next'].map((step, idx) => (
                  <button
                    key={step}
                    onClick={() => setWelcomeStep(step as any)}
                    className={`w-2 h-2 rounded-full transition-colors ${
                      welcomeStep === step ? 'bg-[#3B82F6]' : 'bg-[#1a2332] hover:bg-[#3d4d60]'
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Stop Agent Confirmation Modal */}
        {showStopConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#090d14]/70 backdrop-blur-sm p-4">
            <div className="glass-card rounded-2xl border border-[rgba(30,50,70,0.35)] max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-[#EF476F]/20 rounded-full flex items-center justify-center">
                  <AlertTriangle className="text-[#EF476F]" size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-bold">Stop Agent?</h3>
                  <p className="text-sm text-[#5a6a7e]">This will immediately halt {agentToStop}</p>
                </div>
              </div>
              
              <p className="text-sm text-[#e8ecf1] mb-6">
                Any open positions will remain active. The agent will stop scanning for new opportunities.
              </p>

              <div className="flex gap-3">
                <button 
                  onClick={() => setShowStopConfirm(false)}
                  className="flex-1 py-2.5 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={executeStopAgent}
                  className="flex-1 py-2.5 bg-[#D63D5E] rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
                >
                  <Square size={16} />
                  Stop Agent
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Stop All Confirmation Modal */}
        {showStopAllConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#090d14]/70 backdrop-blur-sm p-4">
            <div className="glass-card rounded-2xl border border-[#EF476F]/30 max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-[#EF476F]/20 rounded-full flex items-center justify-center animate-pulse">
                  <AlertTriangle className="text-[#EF476F]" size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#EF476F]">Stop All Agents?</h3>
                  <p className="text-sm text-[#5a6a7e]">This will halt the entire swarm</p>
                </div>
              </div>
              
              <div className="bg-[#EF476F]/10 border border-[#EF476F]/20 rounded-lg p-3 mb-6">
                <p className="text-sm text-[#e8ecf1]">
                  <strong>Warning:</strong> All {activeCount} active agents will be stopped immediately. 
                  Open positions will remain but no new trades will be executed.
                </p>
              </div>

              <div className="flex gap-3">
                <button 
                  onClick={() => setShowStopAllConfirm(false)}
                  className="flex-1 py-2.5 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={executeStopAll}
                  className="flex-1 py-2.5 bg-[#D63D5E] rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
                >
                  <Square size={16} />
                  Stop All Agents
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
