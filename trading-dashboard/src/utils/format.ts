// Formatting utilities

import type { Currency } from '../types';

// Currency display configuration
export const CURRENCY_CONFIG: Record<Currency, { symbol: string; flag: string; decimals: number }> = {
  USD: { symbol: '$', flag: '🇺🇸', decimals: 2 },
  USDT: { symbol: '₮', flag: '💵', decimals: 2 },
  USDC: { symbol: '$', flag: '💲', decimals: 2 },
  BTC: { symbol: '₿', flag: '🔶', decimals: 8 },
  ETH: { symbol: 'Ξ', flag: '💠', decimals: 6 },
  SOL: { symbol: '◎', flag: '⚡', decimals: 9 },
  EUR: { symbol: '€', flag: '🇪🇺', decimals: 2 },
  GBP: { symbol: '£', flag: '🇬🇧', decimals: 2 },
};

// Default currency for the app
export const DEFAULT_CURRENCY: Currency = 'USD';

// Get currency config
export function getCurrencyConfig(currency: Currency) {
  return CURRENCY_CONFIG[currency] || CURRENCY_CONFIG.USD;
}

// Format currency with proper symbol and decimals
export function formatCurrency(value: number, currency: Currency = 'USD'): string {
  const config = getCurrencyConfig(currency);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency === 'USDT' || currency === 'USDC' ? 'USD' : currency,
    minimumFractionDigits: config.decimals,
    maximumFractionDigits: config.decimals,
  }).format(value);
}

// Format crypto with symbol prefix
export function formatCrypto(value: number, currency: Currency): string {
  const config = getCurrencyConfig(currency);
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: config.decimals,
    maximumFractionDigits: config.decimals,
  }).format(value);
  return `${config.symbol}${formatted}`;
}

// Format with adaptive decimals based on value magnitude
export function formatAdaptive(value: number, currency: Currency = 'USD'): string {
  const config = getCurrencyConfig(currency);
  const absValue = Math.abs(value);
  
  let decimals = config.decimals;
  if (absValue >= 10000) decimals = 0;
  else if (absValue >= 1) decimals = 2;
  else if (absValue >= 0.01) decimals = 4;
  else decimals = config.decimals;
  
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

// Format USD value (for showing USD equivalent)
export function formatUSD(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

// Format BTC value
export function formatBTC(value: number): string {
  return `₿${value.toFixed(8)}`;
}

// Format ETH value
export function formatETH(value: number): string {
  return `Ξ${value.toFixed(6)}`;
}

// Format SOL value
export function formatSOL(value: number): string {
  return `◎${value.toFixed(4)}`;
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatCompact(value: number): string {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
}

export function formatDate(timestamp: string): string {
  return new Date(timestamp).toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
  });
}

export function formatDateTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getChangeColor(value: number): string {
  if (value > 0) return 'text-trade-up';
  if (value < 0) return 'text-trade-down';
  return 'text-trade-neutral';
}

export function getChangeBg(value: number): string {
  if (value > 0) return 'bg-green-500/10';
  if (value < 0) return 'bg-red-500/10';
  return 'bg-gray-500/10';
}

// Format multi-currency balance display
export function formatMultiCurrencyBalance(
  balances: Record<Currency, number>,
  preferred: Currency = 'USD'
): string {
  const values = Object.entries(balances)
    .filter(([, amount]) => amount > 0)
    .sort((a, b) => {
      if (a[0] === preferred) return -1;
      if (b[0] === preferred) return 1;
      return 0;
    })
    .slice(0, 3); // Show top 3

  return values
    .map(([curr, amount]) => formatCrypto(amount, curr as Currency))
    .join(' | ');
}

// Get currency icon/name for UI
export function getCurrencyDisplay(currency: Currency): { name: string; icon: string; color: string } {
  const displays: Record<Currency, { name: string; icon: string; color: string }> = {
    USD: { name: 'US Dollar', icon: '$', color: 'text-green-400' },
    USDT: { name: 'Tether', icon: '₮', color: 'text-green-400' },
    USDC: { name: 'USD Coin', icon: '$', color: 'text-blue-400' },
    BTC: { name: 'Bitcoin', icon: '₿', color: 'text-orange-400' },
    ETH: { name: 'Ethereum', icon: 'Ξ', color: 'text-purple-400' },
    SOL: { name: 'Solana', icon: '◎', color: 'text-teal-400' },
    EUR: { name: 'Euro', icon: '€', color: 'text-blue-400' },
    GBP: { name: 'British Pound', icon: '£', color: 'text-purple-400' },
  };
  return displays[currency] || displays.USD;
}
