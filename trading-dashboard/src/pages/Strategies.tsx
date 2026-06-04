import { useEffect, useState } from 'react';
import { 
  Target, ToggleLeft, ToggleRight, Settings, Info,
  TrendingUp, TrendingDown, Activity, Zap, Shield,
  ChevronDown, ChevronUp, Save, FileText, Code,
  Play, Pause, RefreshCw, AlertTriangle, CheckCircle,
  DollarSign, Clock, BarChart3, Sliders
} from 'lucide-react';
import { Header } from '../components/Header';
import { ShimmerCard } from '../components/ui/GlassCard';
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
      if (!strategy) return;
      const newEnabled = !strategy.enabled;
      await api.toggleStrategy(id, newEnabled);
      // Optimistic update
      setStrategies(prev => prev.map(s => 
        s.id === id ? { ...s, enabled: newEnabled } : s
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
      case 'low': return 'text-[#00C9A7] bg-[#00C9A7]/20 border-[#00C9A7]/30';
      case 'medium': return 'text-[#D4AF37] bg-[#D4AF37]/20 border-[#D4AF37]/30';
      case 'high': return 'text-[#FF6B35] bg-[#FF6B35]/20 border-[#FF6B35]/30';
      case 'very_high': return 'text-[#EF476F] bg-[#EF476F]/20 border-[#EF476F]/30';
      default: return 'text-[#5a6a7e] bg-[#3d4d60]/20 border-[#3d4d60]/30';
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
      <div className="pb-20 lg:pb-8 lg:pl-[224px]">
        <Header title="Strategy Management" />
        <div className="p-4">
          <ShimmerCard />
        </div>
      </div>
    );
  }

  const activeCount = strategies.filter(s => s.enabled).length;

  return (
    <div className="pb-20 lg:pb-8 lg:pl-[224px]">
      <Header title="Strategy Management" />
      
      <div className="p-4 space-y-4">
        {/* Stats Overview */}
        <div className="grid grid-cols-3 gap-3">
          <div className="glass-card rounded-xl p-4 border border-[#00C9A7]/30 text-center">
            <div className="text-2xl font-bold text-[#00C9A7]">{activeCount}</div>
            <div className="text-xs text-[#5a6a7e]">Active Strategies</div>
          </div>
          <div className="glass-card rounded-xl p-4 border border-[#0F4C75]/30 text-center">
            <div className="text-2xl font-bold text-[#3B82F6]">{strategies.length}</div>
            <div className="text-xs text-[#5a6a7e]">Total Strategies</div>
          </div>
          <div className="glass-card rounded-xl p-4 border border-[#D4AF37]/30 text-center">
            <div className="text-2xl font-bold text-[#D4AF37]">
              {strategies.reduce((sum, s) => sum + (s.performance?.pnl || 0), 0).toFixed(0)}
            </div>
            <div className="text-xs text-[#5a6a7e]">Total P&L ($)</div>
          </div>
        </div>

        {/* Info Card */}
        <div className="bg-[#0F4C75]/10 border border-[#0F4C75]/30 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Info className="text-[#3B82F6] flex-shrink-0 mt-0.5" size={18} />
            <div className="text-sm text-[#e8ecf1]">
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
              className={`glass-card rounded-xl border overflow-hidden transition-all ${
                strategy.enabled ? 'border-[#00C9A7]/30' : 'border-[rgba(30,50,70,0.3)]'
              }`}
            >
              {/* Header */}
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${strategy.enabled ? 'bg-[#0F4C75]/20 text-[#3B82F6]' : 'bg-[#151d28] text-[#5a6a7e]'}`}>
                      {getStrategyIcon(strategy.id)}
                    </div>
                    <div>
                      <div className="font-semibold">{strategy.name}</div>
                      <div className="text-sm text-[#5a6a7e] line-clamp-1">{strategy.description}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded text-xs border ${getRiskColor(strategy.risk)}`}>
                      {strategy.risk}
                    </span>
                    <button 
                      onClick={() => toggleStrategy(strategy.id)}
                      className={`transition-colors ${strategy.enabled ? 'text-[#00C9A7]' : 'text-[#3d4d60]'}`}
                    >
                      {strategy.enabled ? <ToggleRight size={32} /> : <ToggleLeft size={32} />}
                    </button>
                  </div>
                </div>

                {/* Performance Stats */}
                <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-[rgba(30,50,70,0.3)]">
                  <div>
                    <div className="text-xs text-[#5a6a7e]">Position Size</div>
                    <div className="font-mono text-sm">${strategy.max_position_usd}</div>
                  </div>
                  <div>
                    <div className="text-xs text-[#5a6a7e]">Trades</div>
                    <div className="font-mono">{strategy.performance?.trades ?? 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-[#5a6a7e]">Win Rate</div>
                    <div className={`font-mono ${((strategy.performance?.wins || 0) / ((strategy.performance?.trades || 0) > 0 ? strategy.performance!.trades : 1)) > 0.5 ? 'text-[#00C9A7]' : 'text-[#D4AF37]'}`}>
                      {(strategy.performance?.trades || 0) > 0 
                        ? (((strategy.performance?.wins || 0) / (strategy.performance?.trades || 1)) * 100).toFixed(0)
                        : 0}%
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-[#5a6a7e]">P&L</div>
                    <div className={`font-mono ${(strategy.performance?.pnl || 0) >= 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
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
                        ? 'bg-[#151d28] text-[#e8ecf1]' 
                        : 'bg-[#0F4C75]/20 text-[#3B82F6] hover:bg-[#0F4C75]/30'
                    }`}
                  >
                    {isEditing ? <ChevronUp size={16} /> : <Settings size={16} />}
                    {isEditing ? 'Close' : 'Configure'}
                  </button>
                  
                  {strategy.enabled && (
                    <span className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-[#00C9A7]/20 text-[#00C9A7]">
                      <Play size={14} />
                      Active
                    </span>
                  )}
                </div>
              </div>

              {/* Expanded Editor */}
              {isEditing && editingStrategy && (
                <div className="px-4 pb-4 border-t border-[rgba(30,50,70,0.3)]">
                  {/* Tabs */}
                  <div className="flex gap-2 mt-4 mb-4">
                    <button
                      onClick={() => setActiveTab('params')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        activeTab === 'params' 
                          ? 'bg-[#0F4C75] text-[#e8ecf1] 
                          : 'bg-[#151d28] text-[#5a6a7e] hover:text-[#e8ecf1]
                      }`}
                    >
                      <Sliders size={16} className="inline mr-1" />
                      Parameters
                    </button>
                    <button
                      onClick={() => setActiveTab('prompt')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        activeTab === 'prompt' 
                          ? 'bg-[#0F4C75] text-[#e8ecf1] 
                          : 'bg-[#151d28] text-[#5a6a7e] hover:text-[#e8ecf1]
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
                        <label className="block text-sm text-[#5a6a7e] mb-1">Strategy Description</label>
                        <textarea
                          value={editingStrategy.description}
                          onChange={(e) => updateEditingField('description', e.target.value)}
                          rows={2}
                          className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 text-sm focus:border-[#0F4C75] focus:outline-none resize-none"
                        />
                      </div>

                      {/* Main Params */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-[#5a6a7e] mb-1">Max Position ($)</label>
                          <input
                            type="number"
                            value={editingStrategy.max_position_usd}
                            onChange={(e) => updateEditingField('max_position_usd', parseFloat(e.target.value))}
                            className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 focus:border-[#0F4C75] focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-[#5a6a7e] mb-1">Check Interval (sec)</label>
                          <input
                            type="number"
                            value={editingStrategy.check_interval_seconds}
                            onChange={(e) => updateEditingField('check_interval_seconds', parseInt(e.target.value))}
                            className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 focus:border-[#0F4C75] focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-[#5a6a7e] mb-1">Stop Loss (%)</label>
                          <input
                            type="number"
                            step="0.01"
                            value={editingStrategy.stop_loss_pct}
                            onChange={(e) => updateEditingField('stop_loss_pct', parseFloat(e.target.value))}
                            className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 focus:border-[#0F4C75] focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-[#5a6a7e] mb-1">Take Profit (%)</label>
                          <input
                            type="number"
                            step="0.01"
                            value={editingStrategy.take_profit_pct}
                            onChange={(e) => updateEditingField('take_profit_pct', parseFloat(e.target.value))}
                            className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 focus:border-[#0F4C75] focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-[#5a6a7e] mb-1">Max Concurrent</label>
                          <input
                            type="number"
                            value={editingStrategy.max_concurrent}
                            onChange={(e) => updateEditingField('max_concurrent', parseInt(e.target.value))}
                            className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 focus:border-[#0F4C75] focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-[#5a6a7e] mb-1">Risk Level</label>
                          <select
                            value={editingStrategy.risk}
                            onChange={(e) => updateEditingField('risk', e.target.value)}
                            className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 focus:border-[#0F4C75] focus:outline-none"
                          >
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="very_high">Very High</option>
                          </select>
                        </div>
                      </div>

                      {/* Strategy-specific Params */}
                      <div className="pt-4 border-t border-[rgba(30,50,70,0.3)]">
                        <h4 className="text-sm font-medium text-[#5a6a7e] mb-3">Strategy-Specific Parameters</h4>
                        <div className="grid grid-cols-2 gap-4">
                          {Object.entries(editingStrategy.params || {}).map(([key, value]) => (
                            <div key={key}>
                              <label className="block text-sm text-[#5a6a7e] mb-1 capitalize">
                                {key.replace(/_/g, ' ')}
                              </label>
                              <input
                                type={typeof value === 'number' ? 'number' : 'text'}
                                value={value as any}
                                onChange={(e) => updateEditingParam(key, typeof value === 'number' ? parseFloat(e.target.value) : e.target.value)}
                                className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 focus:border-[#0F4C75] focus:outline-none"
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm text-[#5a6a7e] mb-1 flex items-center gap-2">
                          <Code size={14} />
                          Trading Prompt / Instructions
                        </label>
                        <p className="text-xs text-[#3d4d60] mb-2">
                          Define how this strategy executes trades. The AI uses these instructions to make trading decisions.
                        </p>
                        <textarea
                          value={editingStrategy.prompt}
                          onChange={(e) => updateEditingField('prompt', e.target.value)}
                          rows={10}
                          className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 text-sm font-mono focus:border-[#0F4C75] focus:outline-none resize-none"
                          placeholder="Enter strategy trading instructions..."
                        />
                      </div>
                      
                      <div className="bg-[#0F4C75]/10 border border-[#0F4C75]/30 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <AlertTriangle size={16} className="text-[#3B82F6] mt-0.5" />
                          <div className="text-xs text-[#5a6a7e]">
                            <strong className="text-[#3B82F6]">Prompt Tips:</strong> Be specific about entry/exit conditions, indicators to use, and risk management rules. The AI interprets these instructions to execute trades.
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Save/Cancel Buttons */}
                  <div className="flex justify-end gap-2 pt-4 mt-4 border-t border-[rgba(30,50,70,0.3)]">
                    <button 
                      onClick={() => {
                        setExpandedId(null);
                        setEditingStrategy(null);
                      }}
                      className="px-4 py-2 text-[#5a6a7e] hover:text-[#e8ecf1]"
                    >
                      Cancel
                    </button>
                    <button 
                      onClick={saveStrategy}
                      disabled={saving}
                      className="flex items-center gap-2 px-4 py-2 bg-[#0F4C75] rounded-lg hover:bg-[#1A5F8A] disabled:opacity-50"
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
          <div className="text-center py-12 text-[#5a6a7e] glass-card rounded-xl border border-[rgba(30,50,70,0.3)]">
            <Target size={48} className="mx-auto mb-4 opacity-50" />
            <p>No strategies configured</p>
          </div>
        )}
      </div>
    </div>
  );
}
