import { useEffect, useState, useRef } from 'react';
import { 
  Bot, Power, Activity, Settings, Shield, AlertTriangle,
  CheckCircle, Clock, TrendingUp, Brain, Zap, RefreshCw,
  Terminal, Play, Pause, ChevronDown, ChevronUp,
  AlertOctagon, BarChart3, History, Sparkles, Lock, Unlock,
  MessageSquare, Send, User, Loader2, Sparkle, X
} from 'lucide-react';
import { Header } from '../components/Header';
import { api } from '../api/client';

interface AutonomousStatus {
  enabled: boolean;
  mode: string;
  uptime_hours: number;
  decisions_made: number;
  pending_decisions: number;
  approval_rate: number;
  last_decision: string;
  health_score: number;
  cpu_usage: number;
  memory_usage: number;
}

interface Decision {
  id: string;
  timestamp: string;
  type: 'trade' | 'config' | 'risk' | 'alert';
  symbol?: string;
  action: string;
  confidence: number;
  status: 'pending' | 'approved' | 'rejected' | 'executed';
  reasoning: string;
  pnl?: number;
}

interface HealingIssue {
  id: string;
  component: string;
  issue: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  detected_at: string;
  status: 'open' | 'remediating' | 'resolved';
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export function ZeroClaw() {
  const [status, setStatus] = useState<AutonomousStatus | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [issues, setIssues] = useState<HealingIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'decisions' | 'healing'>('overview');
  const [expandedDecision, setExpandedDecision] = useState<string | null>(null);
  
  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Settings state
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    model: 'anthropic/claude-3.5-sonnet',
    tools: {
      portfolio: true,
      arbitrage: true,
      charting: true,
      risk: true,
    },
    permissions: {
      autoTrade: false,
      requireApproval: true,
      maxPositionSize: 1000,
    },
    mcp: {
      enabled: false,
      protocol: 'standard',
    },
  });

  async function loadData() {
    try {
      // Load autonomous status
      const statusRes = await fetch('/api/autonomous/status');
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        if (statusData.success) {
          setStatus(statusData.data);
        }
      }

      // Load decisions
      const decisionsRes = await fetch('/api/autonomous/decisions?limit=20');
      if (decisionsRes.ok) {
        const decisionsData = await decisionsRes.json();
        if (decisionsData.success) {
          setDecisions(decisionsData.decisions || []);
        }
      }

      // Load healing issues
      const issuesRes = await fetch('/api/healing/issues');
      if (issuesRes.ok) {
        const issuesData = await issuesRes.json();
        if (issuesData.success) {
          setIssues(issuesData.issues || []);
        }
      }
    } catch (error) {
      console.error('Failed to load autonomous data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function toggleAutonomous() {
    setToggling(true);
    try {
      const result = await api.toggleAutonomous(!status?.enabled);
      if (result.success) {
        loadData();
      }
    } catch (error) {
      console.error('Failed to toggle autonomous:', error);
    } finally {
      setToggling(false);
    }
  }

  // Chat functions
  async function sendMessage() {
    if (!inputMessage.trim() || chatLoading) return;
    
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setChatLoading(true);
    
    try {
      const result = await api.chatWithZeroClaw(userMsg.content);
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.response || result.message || 'No response',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setChatLoading(false);
    }
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function approveDecision(decisionId: string) {
    try {
      await fetch(`/api/autonomous/decisions/${decisionId}/approve`, { method: 'POST' });
      loadData();
    } catch (error) {
      console.error('Failed to approve decision:', error);
    }
  }

  async function rejectDecision(decisionId: string) {
    try {
      await fetch(`/api/autonomous/decisions/${decisionId}/reject`, { method: 'POST' });
      loadData();
    } catch (error) {
      console.error('Failed to reject decision:', error);
    }
  }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="pb-20 lg:pb-8 lg:pl-[224px]">
        <Header title="24/7 Autonomous Agent" />
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3B82F6]"></div>
        </div>
      </div>
    );
  }

  const pendingDecisions = decisions.filter(d => d.status === 'pending');
  const openIssues = issues.filter(i => i.status !== 'resolved');

  return (
    <div className="pb-20 lg:pb-8 lg:pl-[224px]">
      <Header title="24/7 Autonomous Agent" />
      
      <div className="p-4 space-y-4">
        {/* Status Banner */}
        <div className={`rounded-xl border p-4 ${
          status?.enabled 
            ? 'bg-gradient-to-r from-green-600/20 to-emerald-600/20 border-[#00C9A7]/50' 
            : 'bg-gradient-to-r from-[#151d28] to-[#1a2332] border-[rgba(30,50,70,0.3)]'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-xl ${status?.enabled ? 'bg-[#00C9A7]/30 animate-pulse' : 'bg-[#3d4d60]/30'}`}>
                <Brain size={24} className={status?.enabled ? 'text-[#00C9A7]' : 'text-[#5a6a7e]'} />
              </div>
              <div>
                <div className="font-bold text-lg flex items-center gap-2">
                  {status?.enabled ? (
                    <>
                      <span className="text-[#00C9A7]">● AUTONOMOUS MODE ACTIVE</span>
                    </>
                  ) : (
                    <>
                      <span className="text-[#5a6a7e]">○ STANDBY MODE</span>
                    </>
                  )}
                </div>
                <div className="text-sm text-[#5a6a7e]">
                  {status?.enabled 
                    ? `AI making decisions for ${status.uptime_hours?.toFixed(1) || 0} hours • Health: ${status.health_score || 100}%`
                    : 'Enable to start 24/7 autonomous trading'}
                </div>
              </div>
            </div>
            
            <button
              onClick={toggleAutonomous}
              disabled={toggling}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all disabled:opacity-50 ${
                status?.enabled 
                  ? 'bg-[#EF476F] hover:bg-[#D63D5E] text-[#e8ecf1] 
                  : 'bg-[#00C9A7] hover:bg-[#00A88A] text-[#e8ecf1]
              }`}
            >
              {toggling ? (
                <RefreshCw size={20} className="animate-spin" />
              ) : status?.enabled ? (
                <Pause size={20} />
              ) : (
                <Play size={20} />
              )}
              {status?.enabled ? 'STOP AGENT' : 'START AGENT'}
            </button>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-4 gap-3">
          <div className="glass-card rounded-xl p-4 border border-[#00C9A7]/30 text-center">
            <div className="text-2xl font-bold text-[#00C9A7]">{status?.decisions_made || 0}</div>
            <div className="text-xs text-[#5a6a7e]">Decisions Made</div>
          </div>
          <div className="glass-card rounded-xl p-4 border border-[#D4AF37]/30 text-center">
            <div className="text-2xl font-bold text-[#D4AF37]">{pendingDecisions.length}</div>
            <div className="text-xs text-[#5a6a7e]">Pending Approval</div>
          </div>
          <div className="glass-card rounded-xl p-4 border border-[#0F4C75]/30 text-center">
            <div className="text-2xl font-bold text-[#3B82F6]">{status?.approval_rate || 0}%</div>
            <div className="text-xs text-[#5a6a7e]">Approval Rate</div>
          </div>
          <div className="glass-card rounded-xl p-4 border border-[#EF476F]/30 text-center">
            <div className="text-2xl font-bold text-[#EF476F]">{openIssues.length}</div>
            <div className="text-xs text-[#5a6a7e]">Active Issues</div>
          </div>
        </div>

        {/* Tabs & Settings */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex gap-2 flex-wrap">
            {[
              { id: 'overview', label: 'Overview', icon: Activity },
              { id: 'decisions', label: `Decisions (${pendingDecisions.length})`, icon: Brain },
              { id: 'healing', label: `Self-Healing (${openIssues.length})`, icon: Shield },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === id 
                  ? 'bg-[#0F4C75] text-[#e8ecf1] 
                  : 'glass-card text-[#5a6a7e] hover:text-[#e8ecf1]
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
          </div>
          
          {/* Settings Button */}
          <button
            onClick={() => setShowSettings(true)}
            className="flex items-center gap-2 px-4 py-2 glass-card hover:bg-[#151d28] text-[#5a6a7e] hover:text-[#e8ecf1] rounded-lg font-medium transition-colors"
          >
            <Settings size={16} />
            Settings
          </button>
        </div>

        {/* Overview Tab with Chat */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {/* System Health */}
            <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-4">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Activity size={18} className="text-[#3B82F6]" />
                System Health
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-3 bg-[#090d14] rounded-lg">
                  <div className="text-xs text-[#5a6a7e] mb-1">Health Score</div>
                  <div className={`text-xl font-bold ${(status?.health_score || 100) > 80 ? 'text-[#00C9A7]' : 'text-[#D4AF37]'}`}>
                    {status?.health_score || 100}%
                  </div>
                </div>
                <div className="p-3 bg-[#090d14] rounded-lg">
                  <div className="text-xs text-[#5a6a7e] mb-1">CPU Usage</div>
                  <div className="text-xl font-bold text-[#3B82F6]">{status?.cpu_usage || 0}%</div>
                </div>
                <div className="p-3 bg-[#090d14] rounded-lg">
                  <div className="text-xs text-[#5a6a7e] mb-1">Memory</div>
                  <div className="text-xl font-bold text-[#D4AF37]">{status?.memory_usage || 0}%</div>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-4">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <History size={18} className="text-[#00C9A7]" />
                Recent Activity
              </h3>
              <div className="space-y-2">
                {decisions.slice(0, 5).map((decision) => (
                  <div key={decision.id} className="flex items-center justify-between p-3 bg-[#090d14] rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        decision.type === 'trade' ? 'bg-[#00C9A7]/20 text-[#00C9A7]' :
                        decision.type === 'config' ? 'bg-[#0F4C75]/20 text-[#3B82F6]' :
                        decision.type === 'risk' ? 'bg-[#EF476F]/20 text-[#EF476F]' :
                        'bg-[#D4AF37]/20 text-[#D4AF37]'
                      }`}>
                        {decision.type === 'trade' ? <TrendingUp size={16} /> :
                         decision.type === 'config' ? <Settings size={16} /> :
                         decision.type === 'risk' ? <AlertTriangle size={16} /> :
                         <AlertOctagon size={16} />}
                      </div>
                      <div>
                        <div className="font-medium">{decision.action}</div>
                        <div className="text-xs text-[#5a6a7e]">{decision.symbol || decision.type}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-sm font-medium ${
                        decision.status === 'executed' ? 'text-[#00C9A7]' :
                        decision.status === 'pending' ? 'text-[#D4AF37]' :
                        decision.status === 'approved' ? 'text-[#3B82F6]' :
                        'text-[#EF476F]'
                      }`}>
                        {decision.status.toUpperCase()}
                      </div>
                      <div className="text-xs text-[#3d4d60]">{decision.confidence}% confidence</div>
                    </div>
                  </div>
                ))}
                {decisions.length === 0 && (
                  <div className="text-center py-8 text-[#5a6a7e]">
                    <Sparkles size={48} className="mx-auto mb-2 opacity-30" />
                    <p>No decisions yet</p>
                  </div>
                )}
              </div>
            </div>

            {/* AI Chat - Now on Overview Screen */}
            <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] overflow-hidden">
              <div className="p-4 border-b border-[rgba(30,50,70,0.3)] flex items-center justify-between">
                <h3 className="font-semibold flex items-center gap-2">
                  <MessageSquare size={18} className="text-[#00C9A7]" />
                  AI Chat Assistant
                </h3>
                <span className="text-xs text-[#5a6a7e]">Ask about markets, strategies, or status</span>
              </div>
              
              {/* Chat Messages */}
              <div className="h-64 overflow-y-auto p-4 space-y-4 bg-[#090d14]/50">
                {messages.length === 0 ? (
                  <div className="text-center py-8 text-[#5a6a7e]">
                    <Bot size={40} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm mb-3">Chat with ZeroClaw AI</p>
                    <div className="flex flex-wrap gap-2 justify-center">
                      {['Check portfolio status', 'Scan for arbitrage', 'Analyze BTC trend', 'What strategies are active?'].map((suggestion) => (
                        <button
                          key={suggestion}
                          onClick={() => { setInputMessage(suggestion); }}
                          className="px-3 py-1.5 bg-[#151d28] hover:bg-[#1a2332] rounded-lg text-xs text-[#e8ecf1] transition-colors"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                      <div className={`p-2 rounded-xl ${msg.role === 'user' ? 'bg-[#0F4C75]' : 'bg-[#00A88A]/20'}`}>
                        {msg.role === 'user' ? <User size={16} className="text-[#e8ecf1]" /> : <Bot size={16} className="text-[#00C9A7]" />}
                      </div>
                      <div className={`max-w-[80%] p-3 rounded-xl text-sm ${
                        msg.role === 'user' 
                          ? 'bg-[#0F4C75]/20 text-blue-100' 
                          : 'bg-[#151d28] text-[#e8ecf1]'
                      }`}>
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        <span className="text-xs text-[#3d4d60] mt-1 block">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))
                )}
                {chatLoading && (
                  <div className="flex gap-3">
                    <div className="p-2 rounded-xl bg-[#00A88A]/20">
                      <Bot size={16} className="text-[#00C9A7]" />
                    </div>
                    <div className="p-3 rounded-xl bg-[#151d28] flex items-center gap-2">
                      <Loader2 size={14} className="animate-spin text-[#00C9A7]" />
                      <span className="text-xs text-[#5a6a7e]">ZeroClaw is thinking...</span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
              
              {/* Chat Input */}
              <div className="p-4 border-t border-[rgba(30,50,70,0.3)]">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Ask ZeroClaw about markets, strategies, or bot status..."
                    className="flex-1 bg-[#090d14] border border-[rgba(30,50,70,0.35)] rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-[#0F4C75]"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={chatLoading || !inputMessage.trim()}
                    className="px-4 py-2 bg-[#0F4C75] hover:bg-[#1A5F8A] disabled:opacity-50 rounded-lg transition-colors"
                  >
                    <Send size={18} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Decisions Tab -->
        {activeTab === 'decisions' && (
          <div className="space-y-3">
            {decisions.map((decision) => (
              <div key={decision.id} className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] overflow-hidden">
                <div className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        decision.type === 'trade' ? 'bg-[#00C9A7]/20 text-[#00C9A7]' :
                        decision.type === 'config' ? 'bg-[#0F4C75]/20 text-[#3B82F6]' :
                        decision.type === 'risk' ? 'bg-[#EF476F]/20 text-[#EF476F]' :
                        'bg-[#D4AF37]/20 text-[#D4AF37]'
                      }`}>
                        {decision.type === 'trade' ? <TrendingUp size={18} /> :
                         decision.type === 'config' ? <Settings size={18} /> :
                         decision.type === 'risk' ? <AlertTriangle size={18} /> :
                         <AlertOctagon size={18} />}
                      </div>
                      <div>
                        <div className="font-semibold">{decision.action}</div>
                        <div className="text-sm text-[#5a6a7e]">
                          {decision.symbol || decision.type} • {new Date(decision.timestamp).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        decision.status === 'executed' ? 'bg-[#00C9A7]/20 text-[#00C9A7]' :
                        decision.status === 'pending' ? 'bg-[#D4AF37]/20 text-[#D4AF37]' :
                        decision.status === 'approved' ? 'bg-[#0F4C75]/20 text-[#3B82F6]' :
                        'bg-[#EF476F]/20 text-[#EF476F]'
                      }`}>
                        {decision.status}
                      </span>
                      <button
                        onClick={() => setExpandedDecision(expandedDecision === decision.id ? null : decision.id)}
                        className="p-1 text-[#5a6a7e] hover:text-[#e8ecf1]"
                      >
                        {expandedDecision === decision.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      </button>
                    </div>
                  </div>

                  {decision.status === 'pending' && (
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => approveDecision(decision.id)}
                        className="flex-1 py-2 bg-[#00A88A] hover:bg-green-700 rounded-lg text-sm font-medium flex items-center justify-center gap-1"
                      >
                        <CheckCircle size={14} />
                        Approve
                      </button>
                      <button
                        onClick={() => rejectDecision(decision.id)}
                        className="flex-1 py-2 bg-[#D63D5E] hover:bg-red-700 rounded-lg text-sm font-medium flex items-center justify-center gap-1"
                      >
                        <AlertTriangle size={14} />
                        Reject
                      </button>
                    </div>
                  )}

                  {expandedDecision === decision.id && (
                    <div className="mt-3 pt-3 border-t border-[rgba(30,50,70,0.3)]">
                      <div className="text-sm text-[#5a6a7e] mb-2">AI Reasoning:</div>
                      <div className="text-sm bg-[#090d14] rounded-lg p-3">{decision.reasoning}</div>
                      {decision.pnl !== undefined && (
                        <div className={`mt-2 text-sm ${decision.pnl >= 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
                          P&L: {decision.pnl >= 0 ? '+' : ''}{decision.pnl.toFixed(2)}%
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {decisions.length === 0 && (
              <div className="text-center py-12 text-[#5a6a7e] glass-card rounded-xl border border-[rgba(30,50,70,0.3)]">
                <Brain size={48} className="mx-auto mb-3 opacity-30" />
                <p>No decisions recorded yet</p>
                <p className="text-sm">Enable autonomous mode to start making decisions</p>
              </div>
            )}
          </div>
        )}

        {/* Healing Tab */}
        {activeTab === 'healing' && (
          <div className="space-y-3">
            {issues.map((issue) => (
              <div key={issue.id} className={`glass-card rounded-xl border p-4 ${
                issue.severity === 'critical' ? 'border-[#EF476F]/50' :
                issue.severity === 'high' ? 'border-[#FF6B35]/50' :
                issue.severity === 'medium' ? 'border-[#D4AF37]/50' :
                'border-[rgba(30,50,70,0.3)]'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      issue.severity === 'critical' ? 'bg-[#EF476F]/20 text-[#EF476F]' :
                      issue.severity === 'high' ? 'bg-[#FF6B35]/20 text-[#FF6B35]' :
                      issue.severity === 'medium' ? 'bg-[#D4AF37]/20 text-[#D4AF37]' :
                      'bg-[#0F4C75]/20 text-[#3B82F6]'
                    }`}>
                      <Shield size={18} />
                    </div>
                    <div>
                      <div className="font-semibold">{issue.component}</div>
                      <div className="text-sm text-[#5a6a7e]">{issue.issue}</div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      issue.status === 'resolved' ? 'bg-[#00C9A7]/20 text-[#00C9A7]' :
                      issue.status === 'remediating' ? 'bg-[#0F4C75]/20 text-[#3B82F6]' :
                      'bg-[#EF476F]/20 text-[#EF476F]'
                    }`}>
                      {issue.status}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      issue.severity === 'critical' ? 'bg-[#EF476F] text-[#e8ecf1] :
                      issue.severity === 'high' ? 'bg-[#FF6B35] text-[#e8ecf1] :
                      issue.severity === 'medium' ? 'bg-[#D4AF37] text-black' :
                      'bg-[#0F4C75] text-[#e8ecf1]
                    }`}>
                      {issue.severity}
                    </span>
                  </div>
                </div>
                
                <div className="mt-2 text-xs text-[#3d4d60]">
                  Detected: {new Date(issue.detected_at).toLocaleString()}
                </div>
              </div>
            ))}
            
            {issues.length === 0 && (
              <div className="text-center py-12 text-[#5a6a7e] glass-card rounded-xl border border-[rgba(30,50,70,0.3)]">
                <CheckCircle size={48} className="mx-auto mb-3 text-[#00C9A7] opacity-50" />
                <p className="text-[#00C9A7] font-medium">All Systems Operational</p>
                <p className="text-sm">No healing issues detected</p>
              </div>
            )}
          </div>
        )}

        {/* Settings Modal */}
        {showSettings && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#090d14]/70 backdrop-blur-sm p-4">
            <div className="glass-card rounded-2xl border border-[rgba(30,50,70,0.35)] max-w-2xl w-full max-h-[90vh] overflow-auto">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-[rgba(30,50,70,0.3)]">
                <div className="flex items-center gap-2">
                  <Settings className="text-[#3B82F6]" size={24} />
                  <span className="text-xl font-bold">ZeroClaw Settings</span>
                </div>
                <button 
                  onClick={() => setShowSettings(false)}
                  className="p-2 hover:bg-[#151d28] rounded-lg transition-colors"
                >
                  <X size={20} className="text-[#5a6a7e]" />
                </button>
              </div>

              <div className="p-6 space-y-6">
                {/* Model Selection */}
                <div className="bg-[#090d14] rounded-xl p-4">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <Brain size={18} className="text-[#D4AF37]" />
                    AI Model
                  </h3>
                  <select
                    value={settings.model}
                    onChange={(e) => setSettings({...settings, model: e.target.value})}
                    className="w-full glass-card border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet (Recommended)</option>
                    <option value="anthropic/claude-3-opus">Claude 3 Opus (Most Capable)</option>
                    <option value="openai/gpt-4o">GPT-4o (OpenAI)</option>
                    <option value="google/gemini-pro">Gemini Pro (Google)</option>
                    <option value="meta-llama/llama-3-70b">Llama 3 70B (Meta)</option>
                  </select>
                  <p className="text-xs text-[#5a6a7e] mt-2">
                    Select the AI model that powers ZeroClaw's decision making. More capable models may have higher latency.
                  </p>
                </div>

                {/* Tools */}
                <div className="bg-[#090d14] rounded-xl p-4">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <Zap size={18} className="text-[#D4AF37]" />
                    Assistant Tools
                  </h3>
                  <div className="space-y-3">
                    {[
                      { key: 'portfolio', label: 'Portfolio Analysis', desc: 'Analyze portfolio performance and suggest rebalancing' },
                      { key: 'arbitrage', label: 'Arbitrage Scanner', desc: 'Scan for price discrepancies across exchanges' },
                      { key: 'charting', label: 'Technical Analysis', desc: 'Chart patterns and indicator analysis' },
                      { key: 'risk', label: 'Risk Manager', desc: 'Monitor and manage trading risks' },
                    ].map(({ key, label, desc }) => (
                      <label key={key} className="flex items-start gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.tools[key as keyof typeof settings.tools]}
                          onChange={(e) => setSettings({
                            ...settings,
                            tools: { ...settings.tools, [key]: e.target.checked }
                          })}
                          className="mt-1 w-4 h-4 rounded border-[rgba(30,50,70,0.35)]"
                        />
                        <div>
                          <div className="font-medium text-sm">{label}</div>
                          <div className="text-xs text-[#5a6a7e]">{desc}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Permissions */}
                <div className="bg-[#090d14] rounded-xl p-4">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <Shield size={18} className="text-[#00C9A7]" />
                    Controls & Permissions
                  </h3>
                  <div className="space-y-4">
                    <label className="flex items-start gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.permissions.autoTrade}
                        onChange={(e) => setSettings({
                          ...settings,
                          permissions: { ...settings.permissions, autoTrade: e.target.checked }
                        })}
                        className="mt-1 w-4 h-4 rounded border-[rgba(30,50,70,0.35)]"
                      />
                      <div>
                        <div className="font-medium text-sm">Auto-Trading</div>
                        <div className="text-xs text-[#5a6a7e]">Allow ZeroClaw to execute trades automatically without approval</div>
                      </div>
                    </label>
                    
                    <label className="flex items-start gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.permissions.requireApproval}
                        onChange={(e) => setSettings({
                          ...settings,
                          permissions: { ...settings.permissions, requireApproval: e.target.checked }
                        })}
                        className="mt-1 w-4 h-4 rounded border-[rgba(30,50,70,0.35)]"
                      />
                      <div>
                        <div className="font-medium text-sm">Require Approval</div>
                        <div className="text-xs text-[#5a6a7e]">Require manual approval for trades above $100</div>
                      </div>
                    </label>

                    <div>
                      <label className="block text-sm font-medium mb-2">Max Position Size ($)</label>
                      <input
                        type="number"
                        value={settings.permissions.maxPositionSize}
                        onChange={(e) => setSettings({
                          ...settings,
                          permissions: { ...settings.permissions, maxPositionSize: parseInt(e.target.value) }
                        })}
                        className="w-full glass-card border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                  </div>
                </div>

                {/* MCP */}
                <div className="bg-[#090d14] rounded-xl p-4">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <Activity size={18} className="text-[#3B82F6]" />
                    MCP (Multi-Control Protocol)
                  </h3>
                  <div className="space-y-3">
                    <label className="flex items-start gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.mcp.enabled}
                        onChange={(e) => setSettings({
                          ...settings,
                          mcp: { ...settings.mcp, enabled: e.target.checked }
                        })}
                        className="mt-1 w-4 h-4 rounded border-[rgba(30,50,70,0.35)]"
                      />
                      <div>
                        <div className="font-medium text-sm">Enable MCP</div>
                        <div className="text-xs text-[#5a6a7e]">Allow external systems to control ZeroClaw via API</div>
                      </div>
                    </label>
                    
                    {settings.mcp.enabled && (
                      <select
                        value={settings.mcp.protocol}
                        onChange={(e) => setSettings({
                          ...settings,
                          mcp: { ...settings.mcp, protocol: e.target.value }
                        })}
                        className="w-full glass-card border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 text-sm"
                      >
                        <option value="standard">Standard Protocol</option>
                        <option value="extended">Extended Protocol (More commands)</option>
                        <option value="restricted">Restricted (Read-only)</option>
                      </select>
                    )}
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="flex gap-3 p-4 border-t border-[rgba(30,50,70,0.3)]">
                <button 
                  onClick={() => setShowSettings(false)}
                  className="flex-1 py-2.5 bg-[#151d28] rounded-lg hover:bg-[#1a2332] transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    // TODO: Save settings to backend
                    setShowSettings(false);
                  }}
                  className="flex-1 py-2.5 bg-[#0F4C75] rounded-lg hover:bg-[#1A5F8A] transition-colors"
                >
                  Save Settings
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Info */}
        <div className="bg-[#0F4C75]/10 border border-[#0F4C75]/30 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Terminal className="text-[#3B82F6] flex-shrink-0 mt-0.5" size={18} />
            <div className="text-sm text-[#e8ecf1]">
              <p className="font-medium text-[#3B82F6] mb-1">24/7 Autonomous Agent</p>
              <p>The ZeroClaw AI operates continuously, making trading decisions, monitoring system health, and self-healing issues. It requires approval for high-risk decisions while handling routine operations automatically.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
