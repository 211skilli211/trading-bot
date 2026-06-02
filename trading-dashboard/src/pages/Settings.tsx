import { useState, useEffect, useCallback } from 'react';
import {
  Settings2, Key, Shield, Save, CheckCircle, AlertTriangle,
  Beaker, Lock, Unlock, Eye, EyeOff, Wallet, Power,
  RefreshCw, ExternalLink, ArrowRight
} from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { useWalletModal } from '@solana/wallet-adapter-react-ui';
import { Header } from '../components/Header';
import { api, Credentials } from '../api/client';

interface Settings {
  notifications: boolean;
  autoRefresh: boolean;
  refreshInterval: number;
  riskPerTrade: number;
  maxPositions: number;
  autoTrading: boolean;
  minConfidence: number;
}

const defaultSettings: Settings = {
  notifications: true,
  autoRefresh: true,
  refreshInterval: 30,
  riskPerTrade: 2,
  maxPositions: 10,
  autoTrading: false,
  minConfidence: 75,
};

export function Settings() {
  const { publicKey, connected, disconnect } = useWallet();
  const { setVisible } = useWalletModal();
  
  const [settings, setSettings] = useState<Settings>(defaultSettings);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // API Credentials
  const [credentials, setCredentials] = useState<Credentials>({
    binanceApiKey: '',
    binanceSecret: '',
    coinbaseApiKey: '',
    coinbaseSecret: '',
    coinbasePassphrase: '',
  });
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [credentialsSaved, setCredentialsSaved] = useState(false);

  // Trading Mode
  const [tradingMode, setTradingMode] = useState<'PAPER' | 'LIVE'>('PAPER');
  const [modeLoading, setModeLoading] = useState(false);
  const [backendWalletConnected, setBackendWalletConnected] = useState(false);

  const loadSettings = useCallback(async () => {
    try {
      // Load trading mode and wallet status from backend
      const modeRes = await api.getPortfolio();
      if (modeRes.mode) {
        setTradingMode(modeRes.mode);
        setBackendWalletConnected(modeRes.walletConnected || false);
      }
      
      // Also check wallet status endpoint
      try {
        const walletRes = await api.getWalletStatus();
        if (walletRes.connected) {
          setBackendWalletConnected(true);
        }
      } catch (e) {
        // Ignore wallet status errors
      }

      // Load credentials (masked)
      const credRes = await api.getCredentials();
      if (credRes.success) {
        setCredentials({
          binanceApiKey: credRes.binanceApiKey || '',
          binanceSecret: credRes.binanceSecret ? '••••••••••••••••' : '',
          coinbaseApiKey: credRes.coinbaseApiKey || '',
          coinbaseSecret: credRes.coinbaseSecret ? '••••••••••••••••' : '',
          coinbasePassphrase: credRes.coinbasePassphrase ? '••••••••' : '',
        });
      }

      // Load user settings from localStorage
      const saved = localStorage.getItem('tradingBotSettings');
      if (saved) {
        setSettings({ ...defaultSettings, ...JSON.parse(saved) });
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Sync wallet with backend when connection changes
  useEffect(() => {
    if (connected && publicKey) {
      api.connectWallet(publicKey.toString()).then(() => {
        setBackendWalletConnected(true);
      }).catch(console.error);
    }
  }, [connected, publicKey]);

  const handleSave = () => {
    localStorage.setItem('tradingBotSettings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleToggleMode = async () => {
    if (modeLoading) return;
    
    setModeLoading(true);
    try {
      const result = await api.toggleTradingMode();
      if (result.success && result.mode) {
        setTradingMode(result.mode);
        const portfolio = await api.getPortfolio();
        setBackendWalletConnected(portfolio.walletConnected || false);
      }
    } catch (error) {
      console.error('Failed to toggle mode:', error);
    } finally {
      setModeLoading(false);
    }
  };

  const handleConnectWallet = () => {
    setVisible(true);
  };

  const handleDisconnectWallet = async () => {
    await disconnect();
    await api.disconnectWallet();
    setBackendWalletConnected(false);
  };

  const handleSaveCredentials = async () => {
    try {
      const credsToSave: Partial<Credentials> = {};
      if (credentials.binanceApiKey && !credentials.binanceApiKey.includes('•')) {
        credsToSave.binanceApiKey = credentials.binanceApiKey;
      }
      if (credentials.binanceSecret && !credentials.binanceSecret.includes('•')) {
        credsToSave.binanceSecret = credentials.binanceSecret;
      }
      if (credentials.coinbaseApiKey && !credentials.coinbaseApiKey.includes('•')) {
        credsToSave.coinbaseApiKey = credentials.coinbaseApiKey;
      }
      if (credentials.coinbaseSecret && !credentials.coinbaseSecret.includes('•')) {
        credsToSave.coinbaseSecret = credentials.coinbaseSecret;
      }
      if (credentials.coinbasePassphrase && !credentials.coinbasePassphrase.includes('•')) {
        credsToSave.coinbasePassphrase = credentials.coinbasePassphrase;
      }

      const result = await api.saveCredentials(credsToSave);
      if (result.success) {
        setCredentialsSaved(true);
        setTimeout(() => setCredentialsSaved(false), 2000);
      }
    } catch (error) {
      console.error('Failed to save credentials:', error);
    }
  };

  const toggleSecretVisibility = (key: string) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return (
      <div className="pb-20 lg:pb-8 lg:pl-[224px]">
        <Header title="Settings" />
        <div className="p-4">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3B82F6]"></div>
          </div>
        </div>
      </div>
    );
  }

  const isLive = tradingMode === 'LIVE';
  const walletConnected = connected && backendWalletConnected;

  return (
    <div className="pb-20 lg:pb-8 lg:pl-[224px]">
      <Header title="Settings" />
      
      <div className="p-4 space-y-6">
        {/* Trading Mode Section */}
        <section className="glass-card rounded-xl p-5 border border-[rgba(30,50,70,0.3)]">
          <div className="flex items-center gap-2 mb-4">
            <Power size={20} className="text-[#3B82F6]" />
            <h2 className="text-lg font-semibold">Trading Mode</h2>
          </div>
          
          <div className={`p-4 rounded-xl border-2 ${
            isLive ? 'bg-[#00C9A7]/10 border-[#00C9A7]' : 'bg-[#D4AF37]/10 border-[#D4AF37]'
          }`}>
            {/* Status Display */}
            <div className="mb-4">
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-3 h-3 rounded-full ${isLive ? 'bg-[#00C9A7] animate-pulse' : bg-[#D4AF37]}`}></div>
                <span className={`font-bold text-lg ${isLive ? 'text-[#00C9A7]' : 'text-[#D4AF37]'}`}>
                  {isLive ? '🔴 LIVE TRADING' : '📊 PAPER TRADING'}
                </span>
              </div>
              <p className="text-sm text-[#5a6a7e]">
                {isLive 
                  ? 'Real trades with real money on connected exchanges' 
                  : 'Practice with simulated $10,000 funds - no risk to real capital'}
              </p>
            </div>

            {/* Action Button */}
            <button
              onClick={handleToggleMode}
              disabled={modeLoading}
              className={`w-full py-3 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${
                isLive 
                  ? 'bg-[#D4AF37] hover:bg-yellow-600 text-black' 
                  : 'bg-[#00C9A7] hover:bg-[#00A88A] text-[#e8ecf1]
              } ${modeLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {modeLoading ? (
                <RefreshCw size={18} className="animate-spin" />
              ) : (
                <ArrowRight size={18} />
              )}
              {modeLoading ? 'SWITCHING...' : `SWITCH TO ${isLive ? 'PAPER TRADING' : 'LIVE TRADING'}`}
            </button>
          </div>
        </section>

        {/* Wallet Section */}
        <section className="glass-card rounded-xl p-5 border border-[rgba(30,50,70,0.3)]">
          <div className="flex items-center gap-2 mb-4">
            <Wallet size={20} className="text-[#D4AF37]" />
            <h2 className="text-lg font-semibold">Wallet Connection</h2>
          </div>
          
          <div className={`p-4 rounded-xl border ${walletConnected ? 'bg-[#00C9A7]/10 border-[#00C9A7]' : 'bg-[#EF476F]/10 border-[#EF476F]'}`}>
            {/* Status Display */}
            <div className="flex items-center gap-3 mb-4">
              <div className={`p-3 rounded-lg ${walletConnected ? 'bg-[#00C9A7]/20' : 'bg-[#EF476F]/20'}`}>
                {walletConnected ? (
                  <Unlock size={24} className="text-[#00C9A7]" />
                ) : (
                  <Lock size={24} className="text-[#EF476F]" />
                )}
              </div>
              <div>
                <div className="font-bold text-lg">
                  {walletConnected ? 'Wallet Connected' : 'Wallet Not Connected'}
                </div>
                <div className="text-sm text-[#5a6a7e]">
                  {walletConnected 
                    ? `${publicKey?.toString().slice(0, 6)}...${publicKey?.toString().slice(-4)}` 
                    : 'Connect Phantom or Solflare wallet for live trading'}
                </div>
              </div>
            </div>

            {/* Action Button */}
            {walletConnected ? (
              <button
                onClick={handleDisconnectWallet}
                className="w-full py-3 bg-[#D63D5E] hover:bg-red-700 rounded-lg font-semibold transition-all flex items-center justify-center gap-2"
              >
                <Lock size={18} />
                DISCONNECT WALLET
              </button>
            ) : (
              <button
                onClick={handleConnectWallet}
                className="w-full py-3 bg-[#0F4C75] hover:bg-[#1A5F8A] rounded-lg font-semibold transition-all flex items-center justify-center gap-2"
              >
                <Wallet size={18} />
                CONNECT WALLET
              </button>
            )}
          </div>
        </section>

        {/* API Credentials Section */}
        <section className="glass-card rounded-xl p-5 border border-[rgba(30,50,70,0.3)]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Key size={20} className="text-[#FF6B35]" />
              <h2 className="text-lg font-semibold">Exchange API Keys</h2>
            </div>
            <span className="text-xs text-[#3d4d60] bg-[#090d14] px-2 py-1 rounded">
              Required for LIVE trading
            </span>
          </div>

          <div className="space-y-4">
            {/* Binance */}
            <div className="p-4 bg-[#090d14] rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">🟡</span>
                <span className="font-semibold">Binance</span>
                <a 
                  href="https://www.binance.com/en/my/settings/api-management"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-auto text-xs text-[#3B82F6] flex items-center gap-1 hover:underline"
                >
                  Get API Keys <ExternalLink size={12} />
                </a>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-[#5a6a7e] mb-1">API Key</label>
                  <input
                    type="text"
                    value={credentials.binanceApiKey}
                    onChange={(e) => setCredentials(prev => ({ ...prev, binanceApiKey: e.target.value }))}
                    placeholder="Enter your Binance API Key"
                    className="w-full glass-card border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 text-sm focus:border-[#0F4C75] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#5a6a7e] mb-1">API Secret</label>
                  <div className="relative">
                    <input
                      type={showSecrets.binanceSecret ? 'text' : 'password'}
                      value={credentials.binanceSecret}
                      onChange={(e) => setCredentials(prev => ({ ...prev, binanceSecret: e.target.value }))}
                      placeholder="Enter your Binance API Secret"
                      className="w-full glass-card border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 pr-10 text-sm focus:border-[#0F4C75] focus:outline-none"
                    />
                    <button
                      onClick={() => toggleSecretVisibility('binanceSecret')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5a6a7e] hover:text-[#e8ecf1]"
                    >
                      {showSecrets.binanceSecret ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Coinbase */}
            <div className="p-4 bg-[#090d14] rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">🔵</span>
                <span className="font-semibold">Coinbase</span>
                <a 
                  href="https://www.coinbase.com/settings/api"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-auto text-xs text-[#3B82F6] flex items-center gap-1 hover:underline"
                >
                  Get API Keys <ExternalLink size={12} />
                </a>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-[#5a6a7e] mb-1">API Key</label>
                  <input
                    type="text"
                    value={credentials.coinbaseApiKey}
                    onChange={(e) => setCredentials(prev => ({ ...prev, coinbaseApiKey: e.target.value }))}
                    placeholder="Enter your Coinbase API Key"
                    className="w-full glass-card border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 text-sm focus:border-[#0F4C75] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#5a6a7e] mb-1">API Secret</label>
                  <div className="relative">
                    <input
                      type={showSecrets.coinbaseSecret ? 'text' : 'password'}
                      value={credentials.coinbaseSecret}
                      onChange={(e) => setCredentials(prev => ({ ...prev, coinbaseSecret: e.target.value }))}
                      placeholder="Enter your Coinbase API Secret"
                      className="w-full glass-card border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 pr-10 text-sm focus:border-[#0F4C75] focus:outline-none"
                    />
                    <button
                      onClick={() => toggleSecretVisibility('coinbaseSecret')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5a6a7e] hover:text-[#e8ecf1]"
                    >
                      {showSecrets.coinbaseSecret ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-[#5a6a7e] mb-1">Passphrase</label>
                  <input
                    type={showSecrets.coinbasePassphrase ? 'text' : 'password'}
                    value={credentials.coinbasePassphrase}
                    onChange={(e) => setCredentials(prev => ({ ...prev, coinbasePassphrase: e.target.value }))}
                    placeholder="Enter your Coinbase Passphrase"
                    className="w-full glass-card border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 text-sm focus:border-[#0F4C75] focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <button
              onClick={handleSaveCredentials}
              className="w-full py-3 bg-[#0F4C75] hover:bg-[#1A5F8A] rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              {credentialsSaved ? <CheckCircle size={18} className="text-[#00C9A7]" /> : <Save size={18} />}
              {credentialsSaved ? 'API Keys Saved!' : 'Save API Keys'}
            </button>
          </div>
        </section>

        {/* Auto Trading */}
        <section className="glass-card rounded-xl p-5 border border-[rgba(30,50,70,0.3)]">
          <div className="flex items-center gap-2 mb-4">
            <Settings2 size={20} className="text-pink-400" />
            <h2 className="text-lg font-semibold">Auto Trading</h2>
          </div>

          <div className="flex items-center justify-between p-4 bg-[#090d14] rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${settings.autoTrading ? 'bg-[#00C9A7]/20' : 'bg-[#151d28]'}`}>
                {settings.autoTrading ? <Unlock size={20} className="text-[#00C9A7]" /> : <Lock size={20} className="text-[#5a6a7e]" />}
              </div>
              <div>
                <div className="font-medium">Enable Auto Trading</div>
                <div className="text-xs text-[#5a6a7e]">
                  Automatically execute ML prediction trades
                </div>
              </div>
            </div>
            <button
              onClick={() => setSettings(prev => ({ ...prev, autoTrading: !prev.autoTrading }))}
              className={`w-14 h-7 rounded-full transition-colors relative ${
                settings.autoTrading ? 'bg-[#00C9A7] : 'bg-[#1a2332]'
              }`}
            >
              <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-transform ${
                settings.autoTrading ? 'translate-x-8' : 'translate-x-1'
              }`} />
            </button>
          </div>

          {settings.autoTrading && (
            <div className="mt-4 p-4 bg-[#090d14] rounded-lg">
              <label className="flex justify-between text-sm text-[#5a6a7e] mb-2">
                <span>Minimum Confidence</span>
                <span className="text-[#e8ecf1]">{settings.minConfidence}%</span>
              </label>
              <input
                type="range"
                min="50"
                max="95"
                value={settings.minConfidence}
                onChange={(e) => setSettings(prev => ({ ...prev, minConfidence: parseInt(e.target.value) }))}
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-xs text-[#3d4d60] mt-1">
                <span>50%</span>
                <span>95%</span>
              </div>
              
              <div className="mt-3 flex items-center gap-2 text-xs text-[#D4AF37] bg-[#D4AF37]/10 p-3 rounded">
                <AlertTriangle size={14} />
                <span>Requires connected wallet and exchange API keys</span>
              </div>
            </div>
          )}
        </section>

        {/* Risk Settings */}
        <section className="glass-card rounded-xl p-5 border border-[rgba(30,50,70,0.3)]">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={20} className="text-[#00C9A7]" />
            <h2 className="text-lg font-semibold">Risk Management</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="flex justify-between text-sm text-[#5a6a7e] mb-2">
                <span>Risk Per Trade (%)</span>
                <span className="text-[#e8ecf1]">{settings.riskPerTrade}%</span>
              </label>
              <input
                type="range"
                min="0.5"
                max="10"
                step="0.5"
                value={settings.riskPerTrade}
                onChange={(e) => setSettings(prev => ({ ...prev, riskPerTrade: parseFloat(e.target.value) }))}
                className="w-full accent-blue-500"
              />
            </div>

            <div>
              <label className="flex justify-between text-sm text-[#5a6a7e] mb-2">
                <span>Max Open Positions</span>
                <span className="text-[#e8ecf1]">{settings.maxPositions}</span>
              </label>
              <input
                type="range"
                min="1"
                max="50"
                value={settings.maxPositions}
                onChange={(e) => setSettings(prev => ({ ...prev, maxPositions: parseInt(e.target.value) }))}
                className="w-full accent-blue-500"
              />
            </div>
          </div>
        </section>

        {/* Appearance & Theme */}
        <section className="glass-card rounded-xl p-5 border border-[rgba(30,50,70,0.3)]">
          <div className="flex items-center gap-2 mb-4">
            <Settings2 size={20} className="text-[#D4AF37]" />
            <h2 className="text-lg font-semibold">Appearance</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-[#5a6a7e] mb-2">Theme</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => setSettings(prev => ({ ...prev, theme: 'dark' }))}
                  className={`p-3 rounded-lg border text-sm transition-colors ${
                    (settings as any).theme === 'dark' || !(settings as any).theme
                      ? 'bg-[#0F4C75] border-[#0F4C75] text-[#e8ecf1] 
                      : 'bg-[#090d14] border-[rgba(30,50,70,0.3)] text-[#5a6a7e] hover:border-[#3d4d60]'
                  }`}
                >
                  <div className="w-full h-4 bg-[#090d14] rounded mb-2" />
                  Dark
                </button>
                <button
                  onClick={() => setSettings(prev => ({ ...prev, theme: 'light' }))}
                  className={`p-3 rounded-lg border text-sm transition-colors ${
                    (settings as any).theme === 'light'
                      ? 'bg-[#0F4C75] border-[#0F4C75] text-[#e8ecf1] 
                      : 'bg-[#090d14] border-[rgba(30,50,70,0.3)] text-[#5a6a7e] hover:border-[#3d4d60]'
                  }`}
                >
                  <div className="w-full h-4 bg-[#e8ecf1] rounded mb-2" />
                  Light
                </button>
                <button
                  onClick={() => setSettings(prev => ({ ...prev, theme: 'system' }))}
                  className={`p-3 rounded-lg border text-sm transition-colors ${
                    (settings as any).theme === 'system'
                      ? 'bg-[#0F4C75] border-[#0F4C75] text-[#e8ecf1] 
                      : 'bg-[#090d14] border-[rgba(30,50,70,0.3)] text-[#5a6a7e] hover:border-[#3d4d60]'
                  }`}
                >
                  <div className="w-full h-4 bg-gradient-to-r from-gray-900 to-gray-100 rounded mb-2" />
                  System
                </button>
              </div>
            </div>

            <div>
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm">Compact Mode</span>
                <input
                  type="checkbox"
                  checked={(settings as any).compactMode || false}
                  onChange={(e) => setSettings(prev => ({ ...prev, compactMode: e.target.checked }))}
                  className="w-5 h-5 rounded accent-blue-500"
                />
              </label>
              <p className="text-xs text-[#3d4d60] mt-1">Reduce padding and font sizes for denser layout</p>
            </div>

            <div>
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm">Animations</span>
                <input
                  type="checkbox"
                  checked={(settings as any).animations !== false}
                  onChange={(e) => setSettings(prev => ({ ...prev, animations: e.target.checked }))}
                  className="w-5 h-5 rounded accent-blue-500"
                />
              </label>
              <p className="text-xs text-[#3d4d60] mt-1">Enable transition animations throughout the app</p>
            </div>
          </div>
        </section>

        {/* Notification Preferences */}
        <section className="glass-card rounded-xl p-5 border border-[rgba(30,50,70,0.3)]">
          <div className="flex items-center gap-2 mb-4">
            <RefreshCw size={20} className="text-[#D4AF37]" />
            <h2 className="text-lg font-semibold">Notifications</h2>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Trade Executions</div>
                <div className="text-sm text-[#5a6a7e]">Get notified when trades are opened/closed</div>
              </div>
              <input
                type="checkbox"
                checked={(settings as any).tradeNotifications !== false}
                onChange={(e) => setSettings(prev => ({ ...prev, tradeNotifications: e.target.checked }))}
                className="w-5 h-5 rounded accent-blue-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Price Alerts</div>
                <div className="text-sm text-[#5a6a7e]">Notify on significant price movements</div>
              </div>
              <input
                type="checkbox"
                checked={(settings as any).priceAlerts || false}
                onChange={(e) => setSettings(prev => ({ ...prev, priceAlerts: e.target.checked }))}
                className="w-5 h-5 rounded accent-blue-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Agent Decisions</div>
                <div className="text-sm text-[#5a6a7e]">Notify when AI agents make decisions</div>
              </div>
              <input
                type="checkbox"
                checked={(settings as any).agentNotifications !== false}
                onChange={(e) => setSettings(prev => ({ ...prev, agentNotifications: e.target.checked }))}
                className="w-5 h-5 rounded accent-blue-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Risk Alerts</div>
                <div className="text-sm text-[#5a6a7e]">Critical alerts for stop losses, liquidations</div>
              </div>
              <input
                type="checkbox"
                checked={(settings as any).riskAlerts !== false}
                onChange={(e) => setSettings(prev => ({ ...prev, riskAlerts: e.target.checked }))}
                className="w-5 h-5 rounded accent-blue-500"
              />
            </div>

            <div className="pt-3 border-t border-[rgba(30,50,70,0.3)]">
              <label className="block text-sm text-[#5a6a7e] mb-2">Notification Channels</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setSettings(prev => ({ ...prev, telegramEnabled: !(settings as any).telegramEnabled }))}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm border transition-colors ${
                    (settings as any).telegramEnabled
                      ? 'bg-[#0F4C75] border-[#0F4C75] text-[#e8ecf1]
                      : 'bg-[#090d14] border-[rgba(30,50,70,0.3)] text-[#5a6a7e] hover:border-[#3d4d60]'
                  }`}
                >
                  Telegram
                </button>
                <button
                  onClick={() => setSettings(prev => ({ ...prev, discordEnabled: !(settings as any).discordEnabled }))}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm border transition-colors ${
                    (settings as any).discordEnabled
                      ? 'bg-[#0F4C75] border-[#0F4C75] text-[#e8ecf1]
                      : 'bg-[#090d14] border-[rgba(30,50,70,0.3)] text-[#5a6a7e] hover:border-[#3d4d60]'
                  }`}
                >
                  Discord
                </button>
                <button
                  onClick={() => setSettings(prev => ({ ...prev, emailEnabled: !(settings as any).emailEnabled }))}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm border transition-colors ${
                    (settings as any).emailEnabled
                      ? 'bg-[#00C9A7] border-[#00C9A7] text-[#090d14]'
                      : 'bg-[#090d14] border-[rgba(30,50,70,0.3)] text-[#5a6a7e] hover:border-[#3d4d60]'
                  }`}
                >
                  Email
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Accessibility */}
        <section className="glass-card rounded-xl p-5 border border-[rgba(30,50,70,0.3)]">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={20} className="text-pink-400" />
            <h2 className="text-lg font-semibold">Accessibility</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm">High Contrast Mode</span>
                <input
                  type="checkbox"
                  checked={(settings as any).highContrast || false}
                  onChange={(e) => setSettings(prev => ({ ...prev, highContrast: e.target.checked }))}
                  className="w-5 h-5 rounded accent-blue-500"
                />
              </label>
              <p className="text-xs text-[#3d4d60] mt-1">Increase contrast for better visibility</p>
            </div>

            <div>
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm">Large Text</span>
                <input
                  type="checkbox"
                  checked={(settings as any).largeText || false}
                  onChange={(e) => setSettings(prev => ({ ...prev, largeText: e.target.checked }))}
                  className="w-5 h-5 rounded accent-blue-500"
                />
              </label>
              <p className="text-xs text-[#3d4d60] mt-1">Increase font sizes throughout the app</p>
            </div>

            <div>
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm">Reduce Motion</span>
                <input
                  type="checkbox"
                  checked={(settings as any).reduceMotion || false}
                  onChange={(e) => setSettings(prev => ({ ...prev, reduceMotion: e.target.checked }))}
                  className="w-5 h-5 rounded accent-blue-500"
                />
              </label>
              <p className="text-xs text-[#3d4d60] mt-1">Minimize animations and transitions</p>
            </div>

            <div>
              <label className="block text-sm text-[#5a6a7e] mb-2">Refresh Rate</label>
              <select
                value={settings.refreshInterval}
                onChange={(e) => setSettings(prev => ({ ...prev, refreshInterval: parseInt(e.target.value) }))}
                className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2 text-sm"
              >
                <option value={10}>10 seconds (High)</option>
                <option value={30}>30 seconds (Default)</option>
                <option value={60}>1 minute (Low)</option>
                <option value={300}>5 minutes (Minimal)</option>
              </select>
            </div>
          </div>
        </section>

        {/* Save Button */}
        <button
          onClick={handleSave}
          className="w-full py-3 bg-[#0F4C75] hover:bg-[#1A5F8A] rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors"
        >
          {saved ? <CheckCircle size={18} className="text-[#00C9A7]" /> : <Save size={18} />}
          {saved ? 'Settings Saved!' : 'Save Settings'}
        </button>

        {/* Version */}
        <div className="text-center text-xs text-[#3d4d60]">
          <div>Trading Bot v2.0.0</div>
          <div>ZeroClaw AI • Multi-Agent System</div>
        </div>
      </div>
    </div>
  );
}
