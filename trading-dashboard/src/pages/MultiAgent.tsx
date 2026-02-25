import { useEffect, useState } from 'react';
import { 
  Users, Play, Pause, Square, RefreshCw, TrendingUp,
  AlertTriangle, BarChart3, Settings, Activity, Zap, Target,
  Brain, Swords, Crosshair, Flame, GitBranch, Shield
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

  async function controlAll(action: 'activate' | 'pause' | 'stop') {
    setActionLoading(action);
    try {
      await api.controlAllAgents(action);
      await loadData();
    } catch (error) {
      console.error('Failed to control agents:', error);
    } finally {
      setActionLoading(null);
    }
  }

  async function controlAgent(agentName: string, action: 'activate' | 'pause' | 'stop') {
    setActionLoading(`${action}-${agentName}`);
    try {
      // TODO: Add individual agent control endpoint
      console.log(`Controlling agent ${agentName}: ${action}`);
      await loadData();
    } catch (error) {
      console.error('Failed to control agent:', error);
    } finally {
      setActionLoading(null);
    }
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
    });
  }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const activeCount = status?.data?.active_agents || status?.activeAgents || 0;
  const totalCount = status?.data?.total_agents || status?.totalAgents || 6;

  if (loading) {
    return (
      <div className="pb-20 lg:pb-8 lg:pl-64">
        <Header title="Multi-Agent Command Center" />
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title="Multi-Agent Command Center" />
      
      <div className="p-4 space-y-6">
        {/* System Overview */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-5 text-white">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Brain size={24} />
              <span className="text-xl font-bold">Agent Swarm Control</span>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
              activeCount > 0 ? 'bg-green-400/30 text-green-100' : 'bg-red-400/30 text-red-100'
            }`}>
              {activeCount > 0 ? `🟢 ${activeCount} Active` : '🔴 System Stopped'}
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
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Settings className="text-blue-400" size={20} />
            <span className="font-semibold">Global Controls</span>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <button 
              onClick={() => controlAll('activate')}
              disabled={actionLoading === 'activate'}
              className="flex items-center justify-center gap-2 p-3 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors disabled:opacity-50"
            >
              {actionLoading === 'activate' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-400"></div>
              ) : (
                <Play size={18} />
              )}
              <span>Start All</span>
            </button>

            <button 
              onClick={() => controlAll('pause')}
              disabled={actionLoading === 'pause'}
              className="flex items-center justify-center gap-2 p-3 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition-colors disabled:opacity-50"
            >
              {actionLoading === 'pause' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-400"></div>
              ) : (
                <Pause size={18} />
              )}
              <span>Pause All</span>
            </button>

            <button 
              onClick={() => controlAll('stop')}
              disabled={actionLoading === 'stop'}
              className="flex items-center justify-center gap-2 p-3 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors disabled:opacity-50"
            >
              {actionLoading === 'stop' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-400"></div>
              ) : (
                <Square size={18} />
              )}
              <span>Stop All</span>
            </button>

            <button 
              onClick={() => loadData()}
              className="flex items-center justify-center gap-2 p-3 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors"
            >
              <RefreshCw size={18} />
              <span>Refresh</span>
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 mt-3">
            <button 
              onClick={rebalance}
              disabled={actionLoading === 'rebalance'}
              className="flex items-center justify-center gap-2 p-3 bg-dark-700 rounded-lg hover:bg-dark-600 transition-colors disabled:opacity-50"
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
              className="flex items-center justify-center gap-2 p-3 bg-dark-700 rounded-lg hover:bg-dark-600 transition-colors disabled:opacity-50"
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

        {/* Consensus Panel */}
        {consensusData && (
          <div className="bg-dark-800 rounded-xl border border-dark-700 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Target className="text-purple-400" size={20} />
              <span className="font-semibold">Multi-Agent Consensus</span>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-dark-900 rounded-lg">
                <span className="text-gray-400">Overall Signal</span>
                <span className={`font-bold ${
                  consensusData.overall === 'buy' ? 'text-green-400' :
                  consensusData.overall === 'sell' ? 'text-red-400' : 'text-yellow-400'
                }`}>
                  {(consensusData.overall || 'neutral').toUpperCase()}
                </span>
              </div>

              <div className="flex justify-between items-center p-3 bg-dark-900 rounded-lg">
                <span className="text-gray-400">Confidence</span>
                <span className="font-bold text-blue-400">
                  {consensusData.confidence || 0}%
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2">
                {['bullish', 'bearish', 'neutral'].map((sentiment) => (
                  <div key={sentiment} className="text-center p-2 bg-dark-900 rounded-lg">
                    <div className="text-xs text-gray-400 capitalize">{sentiment}</div>
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
            <Users size={20} className="text-blue-400" />
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
                <div key={idx} className="bg-dark-800 rounded-xl border border-dark-700 p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                        agent.status === 'active' ? 'bg-green-500/20 text-green-400' :
                        agent.status === 'paused' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        <Icon size={24} />
                      </div>
                      <div>
                        <div className="font-bold text-lg">{agent.name}</div>
                        <div className="text-sm text-gray-400">{description}</div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`px-2 py-0.5 rounded text-xs ${
                            risk === 'low' ? 'bg-green-500/20 text-green-400' :
                            risk === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                            'bg-red-500/20 text-red-400'
                          }`}>
                            {risk} risk
                          </span>
                          <span className="text-xs text-gray-500">
                            {agent.consecutive_losses || 0}/{agent.kill_threshold || 3} losses
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`font-mono font-bold ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(pnl)}
                      </div>
                      <div className="text-xs text-gray-400">{trades} trades</div>
                      <div className="text-xs text-gray-500">
                        {agent.winning_trades || 0} wins
                      </div>
                    </div>
                  </div>

                  {/* Agent Stats */}
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="p-2 bg-dark-900 rounded-lg text-center">
                      <div className="text-xs text-gray-400">Capital</div>
                      <div className="font-mono text-sm">${agent.capital}</div>
                    </div>
                    <div className="p-2 bg-dark-900 rounded-lg text-center">
                      <div className="text-xs text-gray-400">Max Position</div>
                      <div className="font-mono text-sm">{((agent.max_position_pct || 0.1) * 100).toFixed(0)}%</div>
                    </div>
                    <div className="p-2 bg-dark-900 rounded-lg text-center">
                      <div className="text-xs text-gray-400">Status</div>
                      <div className={`text-sm font-medium ${
                        agent.status === 'active' ? 'text-green-400' :
                        agent.status === 'paused' ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>
                        {(agent.status || 'stopped').toUpperCase()}
                      </div>
                    </div>
                  </div>

                  {/* Agent Controls */}
                  <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                      <button 
                        onClick={() => controlAgent(agent.name, 'activate')}
                        disabled={actionLoading === `activate-${agent.name}`}
                        className="flex items-center gap-1 px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors disabled:opacity-50 text-sm"
                      >
                        {actionLoading === `activate-${agent.name}` ? (
                          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-green-400"></div>
                        ) : (
                          <Play size={14} />
                        )}
                        Start
                      </button>
                      <button 
                        onClick={() => controlAgent(agent.name, 'pause')}
                        disabled={actionLoading === `pause-${agent.name}`}
                        className="flex items-center gap-1 px-3 py-1.5 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition-colors disabled:opacity-50 text-sm"
                      >
                        {actionLoading === `pause-${agent.name}` ? (
                          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-yellow-400"></div>
                        ) : (
                          <Pause size={14} />
                        )}
                        Pause
                      </button>
                      <button 
                        onClick={() => controlAgent(agent.name, 'stop')}
                        disabled={actionLoading === `stop-${agent.name}`}
                        className="flex items-center gap-1 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors disabled:opacity-50 text-sm"
                      >
                        {actionLoading === `stop-${agent.name}` ? (
                          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-red-400"></div>
                        ) : (
                          <Square size={14} />
                        )}
                        Stop
                      </button>
                    </div>
                    
                    <button 
                      onClick={() => openAgentConfig(agent)}
                      className="p-2 rounded-lg hover:bg-dark-700 text-gray-400"
                      title="Configure Agent"
                    >
                      <Settings size={16} />
                    </button>
                  </div>
                </div>
              );
            }) : (
              <div className="text-center py-8 text-gray-400 bg-dark-800 rounded-xl border border-dark-700">
                <Users size={48} className="mx-auto mb-2 opacity-50" />
                <p>No agents configured</p>
              </div>
            )}
          </div>
        </div>

        {/* Agent Config Modal */}
        {selectedAgent && agentConfig && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80">
            <div className="bg-dark-800 rounded-xl border border-dark-700 p-5 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold">Configure {selectedAgent.name}</h3>
                <button 
                  onClick={() => setSelectedAgent(null)}
                  className="p-2 rounded-lg hover:bg-dark-700"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Capital Allocation ($)</label>
                  <input
                    type="number"
                    value={agentConfig.capital}
                    onChange={(e) => setAgentConfig({...agentConfig, capital: parseInt(e.target.value)})}
                    className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2"
                  />
                </div>
                
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Max Position %</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="1"
                    value={agentConfig.max_position_pct}
                    onChange={(e) => setAgentConfig({...agentConfig, max_position_pct: parseFloat(e.target.value)})}
                    className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2"
                  />
                </div>
                
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Kill Threshold (consecutive losses)</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={agentConfig.kill_threshold}
                    onChange={(e) => setAgentConfig({...agentConfig, kill_threshold: parseInt(e.target.value)})}
                    className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2"
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-5">
                <button 
                  onClick={() => setSelectedAgent(null)}
                  className="flex-1 py-2 bg-dark-700 rounded-lg hover:bg-dark-600"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    // TODO: Save agent config
                    setSelectedAgent(null);
                  }}
                  className="flex-1 py-2 bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Save Config
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
