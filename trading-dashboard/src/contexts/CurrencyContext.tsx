import { createContext, useContext, useState, type ReactNode } from 'react';
import type { Currency } from '../types';
import { DEFAULT_CURRENCY } from '../utils/format';

interface CurrencyContextType {
  currency: Currency;
  setCurrency: (currency: Currency) => void;
  displayCurrency: Currency;
}

const CurrencyContext = createContext<CurrencyContextType | undefined>(undefined);

const STORAGE_KEY = 'preferred-currency';

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<Currency>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY) as Currency;
      if (saved && ['USD', 'USDT', 'USDC', 'BTC', 'ETH', 'SOL', 'EUR', 'GBP'].includes(saved)) {
        return saved;
      }
    }
    return DEFAULT_CURRENCY;
  });

  const setCurrency = (newCurrency: Currency) => {
    setCurrencyState(newCurrency);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, newCurrency);
    }
  };

  // Display currency is always USD for now (can be made configurable)
  const displayCurrency = DEFAULT_CURRENCY;

  return (
    <CurrencyContext.Provider value={{ currency, setCurrency, displayCurrency }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  const context = useContext(CurrencyContext);
  if (context === undefined) {
    throw new Error('useCurrency must be used within a CurrencyProvider');
  }
  return context;
}
