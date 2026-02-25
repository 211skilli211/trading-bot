// Types for the trading dashboard

export type Currency = 'USD' | 'USDT' | 'USDC' | 'BTC' | 'ETH' | 'SOL' | 'EUR' | 'GBP';

export interface Price {
  symbol: string;
  price: number;
  change24h: number;
  volume24h: number;
  exchange: string;
  currency?: Currency;
  bid?: number;
  ask?: number;
  high24h?: number;
  low24h?: number;
}

export interface Position {
  id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  amount: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  currency?: Currency;
  isPaper?: boolean;
}

export interface Trade {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  amount: number;
  price: number;
  timestamp: string;
  pnl?: number;
  strategy: string;
  currency?: Currency;
  fee?: number;
  isPaper?: boolean;
}

export interface Portfolio {
  balance: number;
  equity: number;
  totalPnl: number;
  totalPnlPercent: number;
  positions: Position[];
  allocation: Allocation[];
  currencies?: Record<Currency, CurrencyBalance>;
  mode?: 'PAPER' | 'LIVE';
  walletConnected?: boolean;
  isPaper?: boolean;
  error?: string;
}

export interface CurrencyBalance {
  currency: Currency;
  balance: number;
  equity: number;
  available: number;
  locked: number;
  usdValue: number;
}

export interface Allocation {
  symbol: string;
  value: number;
  percent: number;
  currency?: Currency;
}

export interface Alert {
  id: string;
  type: 'price' | 'arbitrage' | 'system' | 'trade';
  severity: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

export interface ArbitrageOpportunity {
  symbol: string;
  buyExchange: string;
  sellExchange: string;
  buyPrice: number;
  sellPrice: number;
  spread: number;
  profitPercent: number;
  currency?: Currency;
}

export interface BotStatus {
  personal: {
    running: boolean;
    port: number;
    uptime: number;
  };
  trading: {
    running: boolean;
    port: number;
    uptime: number;
  };
}

export interface Strategy {
  id: string;
  name: string;
  enabled: boolean;
  description: string;
  risk: 'low' | 'medium' | 'high' | 'very_high';
  params: Record<string, any>;
  performance: {
    trades: number;
    wins: number;
    pnl: number;
  };
  supportedCurrencies?: Currency[];
}

export interface Agent {
  name: string;
  strategy?: string;
  strategy_type?: string;
  capital: number;
  risk?: string;
  risk_level?: string;
  status?: 'active' | 'paused' | 'stopped';
  pnl24h?: number;
  total_pnl?: number;
  trades24h?: number;
  total_trades?: number;
  winning_trades?: number;
  consecutive_losses?: number;
  kill_threshold?: number;
  max_position_pct?: number;
  created_at?: string;
  last_eval?: string;
  currency?: Currency;
}

export interface MultiAgentStatus {
  activeAgents?: number;
  totalAgents?: number;
  active_agents?: number;
  total_agents?: number;
  combinedPnl24h?: number;
  combined_pnl_24h?: number;
  consensusScore?: number;
  consensus_score?: number;
  signals24h?: number;
  signals_24h?: number;
  agents?: Agent[];
  data?: {
    active_agents?: number;
    total_agents?: number;
    agents?: Agent[];
  };
}

export interface ZeroClawStatus {
  personal: {
    running: boolean;
    port: number;
    status: string;
  };
  trading: {
    running: boolean;
    port: number;
    status: string;
  };
  activeSkills: number;
  mode: string;
  autonomousEnabled: boolean;
  currentRegime: string;
  decisionsToday: number;
  activeAdjustments: number;
}

export interface MLStatus {
  regime: string;
  regimeConfidence: number;
  agentCount: number;
  mlActive: boolean;
  predictions: MLPrediction[];
}

export interface MLPrediction {
  symbol: string;
  direction: 'up' | 'down' | 'neutral';
  signal?: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  timeframe: string;
  targetPrice?: number;
  stopLoss?: number;
  reasoning?: string;
}

export interface BacktestResult {
  strategy: string;
  startDate: string;
  endDate: string;
  initialBalance: number;
  finalBalance: number;
  totalReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  trades: number;
  winRate: number;
  currency?: Currency;
}

export interface SolanaToken {
  token: string;
  symbol: string;
  cexSymbol: string;
  decimals: number;
  price?: number;
  spread?: number;
}

export interface WalletStatus {
  connected: boolean;
  chain?: string;
  address?: string;
  balance?: number;
  currencies?: Record<Currency, number>;
}

export interface Config {
  bot: {
    mode: 'PAPER' | 'LIVE';
    monitor_interval: number;
    max_concurrent_trades: number;
    default_currency?: Currency;
  };
  strategies: Record<string, Strategy>;
  risk: {
    max_position_btc: number;
    stop_loss_pct: number;
    take_profit_pct: number;
    capital_pct_per_trade: number;
    max_total_exposure_pct: number;
    daily_loss_limit_pct: number;
    consecutive_loss_limit: number;
  };
  alerts: {
    enabled: boolean;
    telegram: { enabled: boolean; bot_token: string; chat_id: string };
    discord: { enabled: boolean; webhook_url: string };
    on_trade: boolean;
    on_stop_loss: boolean;
    on_daily_limit: boolean;
  };
  solana: {
    enabled: boolean;
    rpc_url: string;
    trade_amount_usd: number;
    pairs: SolanaToken[];
  };
}
