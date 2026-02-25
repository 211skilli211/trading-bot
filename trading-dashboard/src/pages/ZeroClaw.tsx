import { useEffect, useState, useRef } from 'react';
import { 
  Bot, Power, Activity, Settings, Shield, AlertTriangle,
  CheckCircle, Clock, TrendingUp, Brain, Zap, RefreshCw,
  Terminal, Play, Pause, ChevronDown, ChevronUp,
  AlertOctagon, BarChart3, History, Sparkles, Lock, Unlock,
  MessageSquare, Send, User, Loader2, Sparkle
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
  const [activeTab, setActiveTab] = useState<'overview' | 'decisions' | 'healing' | 'chat'>('overview');
  const [expandedDecision, setExpandedDecision] = useState<string | null>(null);
  
  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
      <div className="pb-20 lg:pb-8 lg:pl-64">
        <Header title="24/7 Autonomous Agent" />
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
        </div>
      </div>
    );
  }

  const pendingDecisions = decisions.filter(d => d.status === 'pending');
  const openIssues = issues.filter(i => i.status !== 'resolved');

  return (
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title="24/7 Autonomous Agent" />
      
      <div className="p-4 space-y-4">
        {/* Status Banner */}
        <div className={`rounded-xl border p-4 ${
          status?.enabled 
            ? 'bg-gradient-to-r from-green-600/20 to-emerald-600/20 border-green-500/50' 
            : 'bg-gradient-to-r from-gray-700/20 to-gray-600/20 border-gray-500/30'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-xl ${status?.enabled ? 'bg-green-500/30 animate-pulse' : 'bg-gray-600/30'}`}>
                <Brain size={24} className={status?.enabled ? 'text-green-400' : 'text-gray-400'} />
              </div>
              <div>
                <div className="font-bold text-lg flex items-center gap-2">
                  {status?.enabled ? (
                    <>
                      <span className="text-green-400">● AUTONOMOUS MODE ACTIVE</span>
                    </>
                  ) : (
                    <>
                      <span className="text-gray-400">○ STANDBY MODE</span>
                    </>
                  )}
                </div>
                <div className="text-sm text-gray-400">
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
                  ? 'bg-red-500 hover:bg-red-600 text-white' 
                  : 'bg-green-500 hover:bg-green-600 text-white'
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
          <div className="bg-dark-800 rounded-xl p-4 border border-green-500/30 text-center">
            <div className="text-2xl font-bold text-green-400">{status?.decisions_made || 0}</div>
            <div className="text-xs text-gray-400">Decisions Made</div>
          </div>
          <div className="bg-dark-800 rounded-xl p-4 border border-yellow-500/30 text-center">
            <div className="text-2xl font-bold text-yellow-400">{pendingDecisions.length}</div>
            <div className="text-xs text-gray-400">Pending Approval</div>
          </div>
          <div className="bg-dark-800 rounded-xl p-4 border border-blue-500/30 text-center">
            <div className="text-2xl font-bold text-blue-400">{status?.approval_rate || 0}%</div>
            <div className="text-xs text-gray-400">Approval Rate</div>
          </div>
          <div className="bg-dark-800 rounded-xl p-4 border border-red-500/30 text-center">
            <div className="text-2xl font-bold text-red-400">{openIssues.length}</div>
            <div className="text-xs text-gray-400">Active Issues</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 flex-wrap">
          {[
            { id: 'overview', label: 'Overview', icon: Activity },
            { id: 'decisions', label: `Decisions (${pendingDecisions.length})`, icon: Brain },
            { id: 'healing', label: `Self-Healing (${openIssues.length})`, icon: Shield },
            { id: 'chat', label: 'AI Chat', icon: MessageSquare },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === id 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-dark-800 text-gray-400 hover:text-white'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {/* System Health */}
            <div className="bg-dark-800 rounded-xl border border-dark-700 p-4">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Activity size={18} className="text-blue-400" />
                System Health
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-3 bg-dark-900 rounded-lg">
                  <div className="text-xs text-gray-400 mb-1">Health Score</div>
                  <div className={`text-xl font-bold ${(status?.health_score || 100) > 80 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {status?.health_score || 100}%
                  </div>
                </div>
                <div className="p-3 bg-dark-900 rounded-lg">
                  <div className="text-xs text-gray-400 mb-1">CPU Usage</div>
                  <div className="text-xl font-bold text-blue-400">{status?.cpu_usage || 0}%</div>
                </div>
                <div className="p-3 bg-dark-900 rounded-lg">
                  <div className="text-xs text-gray-400 mb-1">Memory</div>
                  <div className="text-xl font-bold text-purple-400">{status?.memory_usage || 0}%</div>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-dark-800 rounded-xl border border-dark-700 p-4">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <History size={18} className="text-green-400" />
                Recent Activity
              </h3>
              <div className="space-y-2">
                {decisions.slice(0, 5).map((decision) => (
                  <div key={decision.id} className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        decision.type === 'trade' ? 'bg-green-500/20 text-green-400' :
                        decision.type === 'config' ? 'bg-blue-500/20 text-blue-400' :
                        decision.type === 'risk' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {decision.type === 'trade' ? <TrendingUp size={16} /> :
                         decision.type === 'config' ? <Settings size={16} /> :
                         decision.type === 'risk' ? <AlertTriangle size={16} /> :
                         <AlertOctagon size={16} />}
                      </div>
                      <div>
                        <div className="font-medium">{decision.action}</div>
                        <div className="text-xs text-gray-400">{decision.symbol || decision.type}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-sm font-medium ${
                        decision.status === 'executed' ? 'text-green-400' :
                        decision.status === 'pending' ? 'text-yellow-400' :
                        decision.status === 'approved' ? 'text-blue-400' :
                        'text-red-400'
                      }`}>
                        {decision.status.toUpperCase()}
                      </div>
                      <div className="text-xs text-gray-500">{decision.confidence}% confidence</div>
                    </div>
                  </div>
                ))}
                {decisions.length === 0 && (
                  <div className="text-center py-8 text-gray-400">
                    <Sparkles size={48} className="mx-auto mb-2 opacity-30" />
                    <p>No decisions yet</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Decisions Tab */}
        {activeTab === 'decisions' && (
          <div className="space-y-3">
            {decisions.map((decision) => (
              <div key={decision.id} className="bg-dark-800 rounded-xl border border-dark-700 overflow-hidden">
                <div className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        decision.type === 'trade' ? 'bg-green-500/20 text-green-400' :
                        decision.type === 'config' ? 'bg-blue-500/20 text-blue-400' :
                        decision.type === 'risk' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {decision.type === 'trade' ? <TrendingUp size={18} /> :
                         decision.type === 'config' ? <Settings size={18} /> :
                         decision.type === 'risk' ? <AlertTriangle size={18} /> :
                         <AlertOctagon size={18} />}
                      </div>
                      <div>
                        <div className="font-semibold">{decision.action}</div>
                        <div className="text-sm text-gray-400">
                          {decision.symbol || decision.type} • {new Date(decision.timestamp).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        decision.status === 'executed' ? 'bg-green-500/20 text-green-400' :
                        decision.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                        decision.status === 'approved' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {decision.status}
                      </span>
                      <button
                        onClick={() => setExpandedDecision(expandedDecision === decision.id ? null : decision.id)}
                        className="p-1 text-gray-400 hover:text-white"
                      >
                        {expandedDecision === decision.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      </button>
                    </div>
                  </div>

                  {decision.status === 'pending' && (
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => approveDecision(decision.id)}
                        className="flex-1 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium flex items-center justify-center gap-1"
                      >
                        <CheckCircle size={14} />
                        Approve
                      </button>
                      <button
                        onClick={() => rejectDecision(decision.id)}
                        className="flex-1 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium flex items-center justify-center gap-1"
                      >
                        <AlertTriangle size={14} />
                        Reject
                      </button>
                    </div>
                  )}

                  {expandedDecision === decision.id && (
                    <div className="mt-3 pt-3 border-t border-dark-700">
                      <div className="text-sm text-gray-400 mb-2">AI Reasoning:</div>
                      <div className="text-sm bg-dark-900 rounded-lg p-3">{decision.reasoning}</div>
                      {decision.pnl !== undefined && (
                        <div className={`mt-2 text-sm ${decision.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          P&L: {decision.pnl >= 0 ? '+' : ''}{decision.pnl.toFixed(2)}%
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {decisions.length === 0 && (
              <div className="text-center py-12 text-gray-400 bg-dark-800 rounded-xl border border-dark-700">
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
              <div key={issue.id} className={`bg-dark-800 rounded-xl border p-4 ${
                issue.severity === 'critical' ? 'border-red-500/50' :
                issue.severity === 'high' ? 'border-orange-500/50' :
                issue.severity === 'medium' ? 'border-yellow-500/50' :
                'border-dark-700'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      issue.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                      issue.severity === 'high' ? 'bg-orange-500/20 text-orange-400' :
                      issue.severity === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-blue-500/20 text-blue-400'
                    }`}>
                      <Shield size={18} />
                    </div>
                    <div>
                      <div className="font-semibold">{issue.component}</div>
                      <div className="text-sm text-gray-400">{issue.issue}</div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      issue.status === 'resolved' ? 'bg-green-500/20 text-green-400' :
                      issue.status === 'remediating' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      {issue.status}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      issue.severity === 'critical' ? 'bg-red-500 text-white' :
                      issue.severity === 'high' ? 'bg-orange-500 text-white' :
                      issue.severity === 'medium' ? 'bg-yellow-500 text-black' :
                      'bg-blue-500 text-white'
                    }`}>
                      {issue.severity}
                    </span>
                  </div>
                </div>
                
                <div className="mt-2 text-xs text-gray-500">
                  Detected: {new Date(issue.detected_at).toLocaleString()}
                </div>
              </div>
            ))}
            
            {issues.length === 0 && (
              <div className="text-center py-12 text-gray-400 bg-dark-800 rounded-xl border border-dark-700">
                <CheckCircle size={48} className="mx-auto mb-3 text-green-400 opacity-50" />
                <p className="text-green-400 font-medium">All Systems Operational</p>
                <p className="text-sm">No healing issues detected</p>
              </div>
            )}
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="bg-dark-800 rounded-xl border border-dark-700 flex flex-col" style={{ height: '500px' }}>
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <Bot size={48} className="mx-auto mb-3 opacity-30" />
                  <p className="font-medium mb-2">Chat with ZeroClaw AI</p>
                  <p className="text-sm mb-4">Ask about market analysis, trading strategies, or bot status</p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {['Check portfolio status', 'Scan for arbitrage', 'Analyze BTC trend', 'What strategies are active?'].map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => { setInputMessage(suggestion); }}
                        className="px-3 py-1.5 bg-dark-700 hover:bg-dark-600 rounded-lg text-xs text-gray-300 transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`p-2 rounded-xl ${msg.role === 'user' ? 'bg-blue-600' : 'bg-green-600/20'}`}>
                      {msg.role === 'user' ? <User size={18} className="text-white" /> : <Bot size={18} className="text-green-400" />}
                    </div>
                    <div className={`max-w-[80%] p-3 rounded-xl ${
                      msg.role === 'user' 
                        ? 'bg-blue-600/20 text-blue-100' 
                        : 'bg-dark-700 text-gray-200'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      <span className="text-xs text-gray-500 mt-1 block">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))
              )}
              {chatLoading && (
                <div className="flex gap-3">
                  <div className="p-2 rounded-xl bg-green-600/20">
                    <Bot size={18} className="text-green-400" />
                  </div>
                  <div className="p-3 rounded-xl bg-dark-700 flex items-center gap-2">
                    <Loader2 size={16} className="animate-spin text-green-400" />
                    <span className="text-sm text-gray-400">ZeroClaw is thinking...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            
            {/* Chat Input */}
            <div className="p-4 border-t border-dark-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  placeholder="Ask ZeroClaw about markets, strategies, or bot status..."
                  className="flex-1 bg-dark-900 border border-dark-600 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={sendMessage}
                  disabled={chatLoading || !inputMessage.trim()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors"
                >
                  <Send size={18} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Info */}
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Terminal className="text-blue-400 flex-shrink-0 mt-0.5" size={18} />
            <div className="text-sm text-gray-300">
              <p className="font-medium text-blue-400 mb-1">24/7 Autonomous Agent</p>
              <p>The ZeroClaw AI operates continuously, making trading decisions, monitoring system health, and self-healing issues. It requires approval for high-risk decisions while handling routine operations automatically.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
