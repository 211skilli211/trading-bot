const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';

export interface OrderRequest {
  symbol: string;
  side: 'BUY' | 'SELL';
  amount: number;
  price?: number;
  orderType?: 'market' | 'limit';
  exchange?: string;
}

export interface Credentials {
  binanceApiKey?: string;
  binanceSecret?: string;
  coinbaseApiKey?: string;
  coinbaseSecret?: string;
  coinbasePassphrase?: string;
}

// Helper to handle fetch with credentials
async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}`);
  }
  
  return response.json();
}

export const api = {
  // Portfolio
  getPortfolio: () => fetchWithAuth(`${API_BASE}/api/portfolio`),
  getPositions: () => fetchWithAuth(`${API_BASE}/api/positions`),
  getPrices: () => fetchWithAuth(`${API_BASE}/api/prices`),
  getAlerts: () => fetchWithAuth(`${API_BASE}/api/alerts`),
  getBotStatus: () => fetchWithAuth(`${API_BASE}/api/bot/status`),
  
  // Trading Mode
  toggleTradingMode: () => fetchWithAuth(`${API_BASE}/api/toggle_mode`, { method: 'POST' }),
  
  // ZeroClaw
  getZeroClawStatus: () => fetchWithAuth(`${API_BASE}/api/zeroclaw/status`),
  getZeroClawSessions: () => fetchWithAuth(`${API_BASE}/api/zeroclaw/sessions`),
  createZeroClawSession: (message: string, threadId?: string) => 
    fetchWithAuth(`${API_BASE}/api/zeroclaw/session`, {
      method: 'POST',
      body: JSON.stringify({ message, thread_id: threadId }),
    }),
  getZeroClawSession: (sessionId: string) => 
    fetchWithAuth(`${API_BASE}/api/zeroclaw/session/${sessionId}`),
  submitUserResponse: (sessionId: string, response: string) => 
    fetchWithAuth(`${API_BASE}/api/zeroclaw/session/${sessionId}/response`, {
      method: 'POST',
      body: JSON.stringify({ response }),
    }),
  
  // Multi-Agent
  getMultiAgentHistory: () => fetchWithAuth(`${API_BASE}/api/multi-agent/history`),
  getMultiAgentStatus: () => fetchWithAuth(`${API_BASE}/api/multi-agent/status`),
  activateMultiAgentSwarm: () => 
    fetchWithAuth(`${API_BASE}/api/multi-agent/activate`, { method: 'POST' }),
  
  // ML Predictions
  getMLPredictions: () => fetchWithAuth(`${API_BASE}/api/ml-predictions`),
  
  // Trade Execution
  placeOrder: (data: OrderRequest) => 
    fetchWithAuth(`${API_BASE}/api/orders`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  executeMLTrade: (prediction: { symbol: string; signal: string; confidence: number }) => 
    fetchWithAuth(`${API_BASE}/api/trading/execute-ml`, {
      method: 'POST',
      body: JSON.stringify(prediction),
    }),
  
  // Credentials
  getCredentials: () => fetchWithAuth(`${API_BASE}/api/credentials`),
  saveCredentials: (creds: Partial<Credentials>) => 
    fetchWithAuth(`${API_BASE}/api/credentials`, {
      method: 'POST',
      body: JSON.stringify(creds),
    }),
  
  // Strategies
  getStrategies: () => fetchWithAuth(`${API_BASE}/api/strategies`),
  updateStrategy: (id: string, data: any) => 
    fetchWithAuth(`${API_BASE}/api/strategies/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  // Coin Details
  getCoinDetails: (symbol: string) => 
    fetchWithAuth(`${API_BASE}/api/coins/${encodeURIComponent(symbol)}`),
  
  // Wallet
  getWalletStatus: () => fetchWithAuth(`${API_BASE}/api/wallet/status`),
  connectWallet: (publicKey: string) => 
    fetchWithAuth(`${API_BASE}/api/wallet/connect`, {
      method: 'POST',
      body: JSON.stringify({ 
        address: publicKey,
        chain: 'solana',
        provider: 'phantom'
      }),
    }),
  disconnectWallet: () => 
    fetchWithAuth(`${API_BASE}/api/wallet/disconnect`, { method: 'POST' }),
  
  // Backtest
  runBacktest: (params: { strategy: string; days: number; symbol: string; initialBalance?: number }) => 
    fetchWithAuth(`${API_BASE}/api/backtest`, {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  
  // ML
  getMLStatus: () => fetchWithAuth(`${API_BASE}/api/ml/status`),
  
  // Multi-Agent extra
  getConsensus: () => fetchWithAuth(`${API_BASE}/api/multi-agent/consensus`),
  controlAllAgents: (action: 'start' | 'stop' | 'activate' | 'pause') => 
    fetchWithAuth(`${API_BASE}/api/multi-agent/control`, {
      method: 'POST',
      body: JSON.stringify({ action: action === 'activate' ? 'start' : action === 'pause' ? 'stop' : action }),
    }),
  rebalanceCapital: () => 
    fetchWithAuth(`${API_BASE}/api/multi-agent/rebalance`, { method: 'POST' }),
  runAgentEvaluation: () => 
    fetchWithAuth(`${API_BASE}/api/multi-agent/evaluate`, { method: 'POST' }),
  
  // Prices/Arbitrage
  getArbitrage: () => fetchWithAuth(`${API_BASE}/api/arbitrage`),
  
  // Config
  getConfig: () => fetchWithAuth(`${API_BASE}/api/config`),
  updateConfig: (config: any) => 
    fetchWithAuth(`${API_BASE}/api/config`, {
      method: 'POST',
      body: JSON.stringify(config),
    }),
  
  // Solana
  getSolanaStatus: () => fetchWithAuth(`${API_BASE}/api/solana/status`),
  getSolanaTokens: () => fetchWithAuth(`${API_BASE}/api/solana/tokens`),
  getSolanaTrades: () => fetchWithAuth(`${API_BASE}/api/solana/trades`),
  toggleSolana: (enabled?: boolean) => 
    fetchWithAuth(`${API_BASE}/api/solana/toggle`, { 
      method: 'POST',
      body: JSON.stringify({ enabled }),
    }),
  
  // Strategies
  toggleStrategy: (id: string) => 
    fetchWithAuth(`${API_BASE}/api/strategies/${id}/toggle`, { method: 'POST' }),
  
  // ZeroClaw extra
  toggleAutonomous: (enabled?: boolean) => 
    fetchWithAuth(`${API_BASE}/api/autonomous/toggle`, { 
      method: 'POST',
      body: JSON.stringify({ enabled }),
    }),
  chatWithZeroClaw: (message: string) => 
    fetchWithAuth(`${API_BASE}/api/zeroclaw/chat`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
};
