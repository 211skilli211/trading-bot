import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface UserPreferences {
  primaryCoin: string;
  defaultTimeframe: string;
  chartType: 'candlestick' | 'line';
  showVolume: boolean;
  showEMA: boolean;
  slDefaultPercent: number;
  tpDefaultPercent: number;
}

const defaultPreferences: UserPreferences = {
  primaryCoin: 'BTC/USDT',
  defaultTimeframe: '1D',
  chartType: 'candlestick',
  showVolume: true,
  showEMA: true,
  slDefaultPercent: 2,
  tpDefaultPercent: 4,
};

interface UserPreferencesContextType {
  preferences: UserPreferences;
  setPrimaryCoin: (coin: string) => void;
  setDefaultTimeframe: (timeframe: string) => void;
  setChartType: (type: 'candlestick' | 'line') => void;
  setShowVolume: (show: boolean) => void;
  setShowEMA: (show: boolean) => void;
  setSLDefaultPercent: (percent: number) => void;
  setTPDefaultPercent: (percent: number) => void;
  updatePreferences: (prefs: Partial<UserPreferences>) => void;
}

const UserPreferencesContext = createContext<UserPreferencesContextType | undefined>(undefined);

export function UserPreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences);
  const [loaded, setLoaded] = useState(false);

  // Load preferences from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('tradingBotPreferences');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setPreferences({ ...defaultPreferences, ...parsed });
      } catch (e) {
        console.error('Failed to parse preferences:', e);
      }
    }
    setLoaded(true);
  }, []);

  // Save to localStorage whenever preferences change
  useEffect(() => {
    if (loaded) {
      localStorage.setItem('tradingBotPreferences', JSON.stringify(preferences));
    }
  }, [preferences, loaded]);

  const updatePreferences = (prefs: Partial<UserPreferences>) => {
    setPreferences(prev => ({ ...prev, ...prefs }));
  };

  const setPrimaryCoin = (coin: string) => updatePreferences({ primaryCoin: coin });
  const setDefaultTimeframe = (timeframe: string) => updatePreferences({ defaultTimeframe: timeframe });
  const setChartType = (type: 'candlestick' | 'line') => updatePreferences({ chartType: type });
  const setShowVolume = (show: boolean) => updatePreferences({ showVolume: show });
  const setShowEMA = (show: boolean) => updatePreferences({ showEMA: show });
  const setSLDefaultPercent = (percent: number) => updatePreferences({ slDefaultPercent: percent });
  const setTPDefaultPercent = (percent: number) => updatePreferences({ tpDefaultPercent: percent });

  return (
    <UserPreferencesContext.Provider value={{
      preferences,
      setPrimaryCoin,
      setDefaultTimeframe,
      setChartType,
      setShowVolume,
      setShowEMA,
      setSLDefaultPercent,
      setTPDefaultPercent,
      updatePreferences,
    }}>
      {children}
    </UserPreferencesContext.Provider>
  );
}

export function useUserPreferences() {
  const context = useContext(UserPreferencesContext);
  if (context === undefined) {
    throw new Error('useUserPreferences must be used within a UserPreferencesProvider');
  }
  return context;
}
