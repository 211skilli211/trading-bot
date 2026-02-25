import { Routes, Route } from 'react-router-dom';
import { Navigation } from './components/Navigation';
import { Home } from './pages/Home';
import { Prices } from './pages/Prices';
import { Portfolio } from './pages/Portfolio';
import { Alerts } from './pages/Alerts';
import { Settings } from './pages/Settings';
import { ZeroClaw } from './pages/ZeroClaw';
import { MultiAgent } from './pages/MultiAgent';
import { Strategies } from './pages/Strategies';
import { ML } from './pages/ML';
import { Solana } from './pages/Solana';
import { Backtest } from './pages/Backtest';
import { Risk } from './pages/Risk';
import { Analytics } from './pages/Analytics';
import { CoinDetail } from './pages/CoinDetail';
import { UserPreferencesProvider } from './context/UserPreferencesContext';

function App() {
  return (
    <UserPreferencesProvider>
      <div className="min-h-screen bg-dark-900 text-white">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/prices" element={<Prices />} />
          <Route path="/coin/:symbol" element={<CoinDetail />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/zeroclaw" element={<ZeroClaw />} />
          <Route path="/multi-agent" element={<MultiAgent />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/ml" element={<ML />} />
          <Route path="/solana" element={<Solana />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/analytics" element={<Analytics />} />
        </Routes>
        <Navigation />
      </div>
    </UserPreferencesProvider>
  );
}

export default App;
