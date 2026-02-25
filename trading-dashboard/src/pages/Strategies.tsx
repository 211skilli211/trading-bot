import { useEffect, useState } from 'react';
import { 
  Target, ToggleLeft, ToggleRight, Settings, Info,
  TrendingUp, TrendingDown, Activity, Zap, Shield,
  ChevronDown, ChevronUp, Save, FileText, Code,
  Play, Pause, RefreshCw, AlertTriangle, CheckCircle,
  DollarSign, Clock, BarChart3, Sliders
} from 'lucide-react';
import { Header } from '../components/Header';
import { api } from '../api/client';

interface Strategy {
  id: string;
  name: string;
  description: string;
  prompt: string;
  enabled: boolean;
  risk: 'low' | 'medium' | 'high' | 'very_high';
  max_position_usd: number;
  check_interval_seconds: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  max_concurrent: number;
  params: Record<string, any>;
  performance?: {
    trades: number;
    wins: number;
    pnl: number;
  };
}

export function Strategies() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null);
  const [activeTab, setActiveTab] = useState<'params' | 'prompt'>('params');
  const [saving, setSaving] = useState(false);

  async function loadStrategies() {
    try {
      const data = await api.getStrategies();
      // Ensure each strategy has required fields
      const normalized = data.map((s: any) => ({
        ...s,
        description: s.description || '',
        prompt: s.prompt || '',
        performance: s.performance || { trades: 0, wins: 0, pnl: 0 }
      }));
      setStrategies(normalized);
    } catch (error) {
      console.error('Failed to load strategies:', error);
    } finally {
      setLoading(false);
    }
  }

  async function toggleStrategy(id: string) {
    try {
      const strategy = strategies.find(s => s.id === id);
      await api.toggleStrategy(id);
      // Optimistic update
      setStrategies(prev => prev.map(s => 
        s.id === id ? { ...s, enabled: !s.enabled } : s
      ));
      loadStrategies();
    } catch (error) {
      console.error('Failed to toggle strategy:', error);
    }
  }

  async function saveStrategy() {
    if (!editingStrategy) return;
    
    setSaving(true);
    try {
      await api.updateStrategy(editingStrategy.id, editingStrategy);
      setExpandedId(null);
      setEditingStrategy(null);
      loadStrategies();
    } catch (error) {
      console.error('Failed to update strategy:', error);
    } finally {
      setSaving(false);
    }
  }

  function startEditing(strategy: Strategy) {
    setEditingStrategy({ ...strategy });
    setExpandedId(strategy.id);
    setActiveTab('params');
  }

  function updateEditingField(field: string, value: any) {
    if (!editingStrategy) return;
    setEditingStrategy({ ...editingStrategy, [field]: value });
  }

  function updateEditingParam(key: string, value: any) {
    if (!editingStrategy) return;
    setEditingStrategy({
      ...editingStrategy,
      params: { ...editingStrategy.params, [key]: value }
    });
  }

  useEffect(() => {
    loadStrategies();
  }, []);

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'text-green-400 bg-green-500/20 border-green-500/30';
      case 'medium': return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30';
      case 'high': return 'text-orange-400 bg-orange-500/20 border-orange-500/30';
      case 'very_high': return 'text-red-400 bg-red-500/20 border-red-500/30';
      default: return 'text-gray-400 bg-gray-500/20 border-gray-500/30';
    }
  };

  const getStrategyIcon = (id: string) => {
    if (id.includes('arbitrage')) return <Activity size={20} />;
    if (id.includes('sniper')) return <Zap size={20} />;
    if (id.includes('momentum')) return <TrendingUp size={20} />;
    if (id.includes('reversion')) return <TrendingDown size={20} />;
    if (id.includes('grid')) return <Target size={20} />;
    if (id.includes('pairs')) return <BarChart3 size={20} />;
    return <Shield size={20} />;
  };

  if (loading) {
    return (
      <div className="pb-20 lg:pb-8 lg:pl-64">
        <Header title="Strategy Management" />
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
        </div>
      </div>
    );
  }

  const activeCount = strategies.filter(s => s.enabled).length;

  return (
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title="Strategy Management" />
      
      <div className="p-4 space-y-4">
        {/* Stats Overview */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-dark-800 rounded-xl p-4 border border-green-500/30 text-center">
            <div className="text-2xl font-bold text-green-400">{activeCount}</div>
            <div className="text-xs text-gray-400">Active Strategies</div>
          </div>
          <div className="bg-dark-800 rounded-xl p-4 border border-blue-500/30 text-center">
            <div className="text-2xl font-bold text-blue-400">{strategies.length}</div>
            <div className="text-xs text-gray-400">Total Strategies</div>
          </div>
          <div className="bg-dark-800 rounded-xl p-4 border border-purple-500/30 text-center">
            <div className="text-2xl font-bold text-purple-400">
              {strategies.reduce((sum, s) => sum + (s.performance?.pnl || 0), 0).toFixed(0)}
            </div>
            <div className="text-xs text-gray-400">Total P&L ($)</div>
          </div>
        </div>

        {/* Info Card */}
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Info className="text-blue-400 flex-shrink-0 mt-0.5" size={18} />
            <div className="text-sm text-gray-300">
              <p className="mb-1"><strong>Strategy Configuration</strong></p>
              <p>Enable/disable strategies and customize their parameters. Edit the strategy description and trading prompt to fine-tune how the AI executes trades. Each strategy has adjustable risk levels, position sizes, and technical parameters.</p>
            </div>
          </div>
        </div>

        {/* Strategy Cards */}
        {strategies.map((strategy) => {
          const isEditing = expandedId === strategy.id && editingStrategy;
          
          return (
            <div 
              key={strategy.id} 
              className={`bg-dark-800 rounded-xl border overflow-hidden transition-all ${
                strategy.enabled ? 'border-green-500/30' : 'border-dark-700'
              }`}
            >
              {/* Header */}
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${strategy.enabled ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-700 text-gray-400'}`}>
                      {getStrategyIcon(strategy.id)}
                    </div>
                    <div>
                      <div className="font-semibold">{strategy.name}</div>
                      <div className="text-sm text-gray-400 line-clamp-1">{strategy.description}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded text-xs border ${getRiskColor(strategy.risk)}`}>
                      {strategy.risk}
                    </span>
                    <button 
                      onClick={() => toggleStrategy(strategy.id)}
                      className={`transition-colors ${strategy.enabled ? 'text-green-400' : 'text-gray-600'}`}
                    >
                      {strategy.enabled ? <ToggleRight size={32} /> : <ToggleLeft size={32} />}
                    </button>
                  </div>
                </div>

                {/* Performance Stats */}
                <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-dark-700">
                  <div>
                    <div className="text-xs text-gray-400">Position Size</div>
                    <div className="font-mono text-sm">${strategy.max_position_usd}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Trades</div>
                    <div className="font-mono">{strategy.performance?.trades ?? 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Win Rate</div>
                    <div className={`font-mono ${((strategy.performance?.wins || 0) / ((strategy.performance?.trades || 0) > 0 ? strategy.performance!.trades : 1)) > 0.5 ? 'text-green-400' : 'text-yellow-400'}`}>
                      {(strategy.performance?.trades || 0) > 0 
                        ? (((strategy.performance?.wins || 0) / (strategy.performance?.trades || 1)) * 100).toFixed(0)
                        : 0}%
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">P&L</div>
                    <div className={`font-mono ${(strategy.performance?.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ${(strategy.performance?.pnl || 0).toFixed(0)}
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 mt-3">
                  <button 
                    onClick={() => isEditing ? setExpandedId(null) : startEditing(strategy)}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      isEditing 
                        ? 'bg-gray-700 text-gray-300' 
                        : 'bg-blue-600/20 text-blue-400 hover:bg-blue-600/30'
                    }`}
                  >
                    {isEditing ? <ChevronUp size={16} /> : <Settings size={16} />}
                    {isEditing ? 'Close' : 'Configure'}
                  </button>
                  
                  {strategy.enabled && (
                    <span className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-green-500/20 text-green-400">
                      <Play size={14} />
                      Active
                    </span>
                  )}
                </div>
              </div>

              {/* Expanded Editor */}
              {isEditing && editingStrategy && (
                <div className="px-4 pb-4 border-t border-dark-700">
                  {/* Tabs */}
                  <div className="flex gap-2 mt-4 mb-4">
                    <button
                      onClick={() => setActiveTab('params')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        activeTab === 'params' 
                          ? 'bg-blue-600 text-white' 
                          : 'bg-dark-700 text-gray-400 hover:text-white'
                      }`}
                    >
                      <Sliders size={16} className="inline mr-1" />
                      Parameters
                    </button>
                    <button
                      onClick={() => setActiveTab('prompt')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        activeTab === 'prompt' 
                          ? 'bg-blue-600 text-white' 
                          : 'bg-dark-700 text-gray-400 hover:text-white'
                      }`}
                    >
                      <Code size={16} className="inline mr-1" />
                      Strategy Prompt
                    </button>
                  </div>

                  {activeTab === 'params' ? (
                    <div className="space-y-4">
                      {/* Description */}
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Strategy Description</label>
                        <textarea
                          value={editingStrategy.description}
                          onChange={(e) => updateEditingField('description', e.target.value)}
                          rows={2}
                          className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none"
                        />
                      </div>

                      {/* Main Params */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Max Position ($)</label>
                          <input
                            type="number"
                            value={editingStrategy.max_position_usd}
                            onChange={(e) => updateEditingField('max_position_usd', parseFloat(e.target.value))}
                            className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Check Interval (sec)</label>
                          <input
                            type="number"
                            value={editingStrategy.check_interval_seconds}
                            onChange={(e) => updateEditingField('check_interval_seconds', parseInt(e.target.value))}
                            className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Stop Loss (%)</label>
                          <input
                            type="number"
                            step="0.01"
                            value={editingStrategy.stop_loss_pct}
                            onChange={(e) => updateEditingField('stop_loss_pct', parseFloat(e.target.value))}
                            className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Take Profit (%)</label>
                          <input
                            type="number"
                            step="0.01"
                            value={editingStrategy.take_profit_pct}
                            onChange={(e) => updateEditingField('take_profit_pct', parseFloat(e.target.value))}
                            className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Max Concurrent</label>
                          <input
                            type="number"
                            value={editingStrategy.max_concurrent}
                            onChange={(e) => updateEditingField('max_concurrent', parseInt(e.target.value))}
                            className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Risk Level</label>
                          <select
                            value={editingStrategy.risk}
                            onChange={(e) => updateEditingField('risk', e.target.value)}
                            className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
                          >
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="very_high">Very High</option>
                          </select>
                        </div>
                      </div>

                      {/* Strategy-specific Params */}
                      <div className="pt-4 border-t border-dark-700">
                        <h4 className="text-sm font-medium text-gray-400 mb-3">Strategy-Specific Parameters</h4>
                        <div className="grid grid-cols-2 gap-4">
                          {Object.entries(editingStrategy.params || {}).map(([key, value]) => (
                            <div key={key}>
                              <label className="block text-sm text-gray-400 mb-1 capitalize">
                                {key.replace(/_/g, ' ')}
                              </label>
                              <input
                                type={typeof value === 'number' ? 'number' : 'text'}
                                value={value as any}
                                onChange={(e) => updateEditingParam(key, typeof value === 'number' ? parseFloat(e.target.value) : e.target.value)}
                                className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 focus:border-blue-500 focus:outline-none"
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm text-gray-400 mb-1 flex items-center gap-2">
                          <Code size={14} />
                          Trading Prompt / Instructions
                        </label>
                        <p className="text-xs text-gray-500 mb-2">
                          Define how this strategy executes trades. The AI uses these instructions to make trading decisions.
                        </p>
                        <textarea
                          value={editingStrategy.prompt}
                          onChange={(e) => updateEditingField('prompt', e.target.value)}
                          rows={10}
                          className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none resize-none"
                          placeholder="Enter strategy trading instructions..."
                        />
                      </div>
                      
                      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <AlertTriangle size={16} className="text-blue-400 mt-0.5" />
                          <div className="text-xs text-gray-400">
                            <strong className="text-blue-400">Prompt Tips:</strong> Be specific about entry/exit conditions, indicators to use, and risk management rules. The AI interprets these instructions to execute trades.
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Save/Cancel Buttons */}
                  <div className="flex justify-end gap-2 pt-4 mt-4 border-t border-dark-700">
                    <button 
                      onClick={() => {
                        setExpandedId(null);
                        setEditingStrategy(null);
                      }}
                      className="px-4 py-2 text-gray-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button 
                      onClick={saveStrategy}
                      disabled={saving}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      {saving ? (
                        <RefreshCw size={16} className="animate-spin" />
                      ) : (
                        <Save size={16} />
                      )}
                      {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {strategies.length === 0 && (
          <div className="text-center py-12 text-gray-400 bg-dark-800 rounded-xl border border-dark-700">
            <Target size={48} className="mx-auto mb-4 opacity-50" />
            <p>No strategies configured</p>
          </div>
        )}
      </div>
    </div>
  );
}
