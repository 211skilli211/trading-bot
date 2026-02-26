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
      <div className="pb-20 lg:pb-8 lg:pl-64">
        <Header title="Settings" />
        <div className="p-4">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
          </div>
        </div>
      </div>
    );
  }

  const isLive = tradingMode === 'LIVE';
  const walletConnected = connected && backendWalletConnected;

  return (
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title="Settings" />
      
      <div className="p-4 space-y-6">
        {/* Trading Mode Section */}
        <section className="bg-dark-800 rounded-xl p-5 border border-dark-700">
          <div className="flex items-center gap-2 mb-4">
            <Power size={20} className="text-blue-400" />
            <h2 className="text-lg font-semibold">Trading Mode</h2>
          </div>
          
          <div className={`p-4 rounded-xl border-2 ${
            isLive ? 'bg-green-500/10 border-green-500' : 'bg-yellow-500/10 border-yellow-500'
          }`}>
            {/* Status Display */}
            <div className="mb-4">
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-3 h-3 rounded-full ${isLive ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`}></div>
                <span className={`font-bold text-lg ${isLive ? 'text-green-400' : 'text-yellow-400'}`}>
                  {isLive ? '🔴 LIVE TRADING' : '📊 PAPER TRADING'}
                </span>
              </div>
              <p className="text-sm text-gray-400">
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
                  ? 'bg-yellow-500 hover:bg-yellow-600 text-black' 
                  : 'bg-green-500 hover:bg-green-600 text-white'
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
        <section className="bg-dark-800 rounded-xl p-5 border border-dark-700">
          <div className="flex items-center gap-2 mb-4">
            <Wallet size={20} className="text-purple-400" />
            <h2 className="text-lg font-semibold">Wallet Connection</h2>
          </div>
          
          <div className={`p-4 rounded-xl border ${walletConnected ? 'bg-green-500/10 border-green-500' : 'bg-red-500/10 border-red-500'}`}>
            {/* Status Display */}
            <div className="flex items-center gap-3 mb-4">
              <div className={`p-3 rounded-lg ${walletConnected ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                {walletConnected ? (
                  <Unlock size={24} className="text-green-400" />
                ) : (
                  <Lock size={24} className="text-red-400" />
                )}
              </div>
              <div>
                <div className="font-bold text-lg">
                  {walletConnected ? 'Wallet Connected' : 'Wallet Not Connected'}
                </div>
                <div className="text-sm text-gray-400">
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
                className="w-full py-3 bg-red-600 hover:bg-red-700 rounded-lg font-semibold transition-all flex items-center justify-center gap-2"
              >
                <Lock size={18} />
                DISCONNECT WALLET
              </button>
            ) : (
              <button
                onClick={handleConnectWallet}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-all flex items-center justify-center gap-2"
              >
                <Wallet size={18} />
                CONNECT WALLET
              </button>
            )}
          </div>
        </section>

        {/* API Credentials Section */}
        <section className="bg-dark-800 rounded-xl p-5 border border-dark-700">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Key size={20} className="text-orange-400" />
              <h2 className="text-lg font-semibold">Exchange API Keys</h2>
            </div>
            <span className="text-xs text-gray-500 bg-dark-900 px-2 py-1 rounded">
              Required for LIVE trading
            </span>
          </div>

          <div className="space-y-4">
            {/* Binance */}
            <div className="p-4 bg-dark-900 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">🟡</span>
                <span className="font-semibold">Binance</span>
                <a 
                  href="https://www.binance.com/en/my/settings/api-management"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-auto text-xs text-blue-400 flex items-center gap-1 hover:underline"
                >
                  Get API Keys <ExternalLink size={12} />
                </a>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">API Key</label>
                  <input
                    type="text"
                    value={credentials.binanceApiKey}
                    onChange={(e) => setCredentials(prev => ({ ...prev, binanceApiKey: e.target.value }))}
                    placeholder="Enter your Binance API Key"
                    className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">API Secret</label>
                  <div className="relative">
                    <input
                      type={showSecrets.binanceSecret ? 'text' : 'password'}
                      value={credentials.binanceSecret}
                      onChange={(e) => setCredentials(prev => ({ ...prev, binanceSecret: e.target.value }))}
                      placeholder="Enter your Binance API Secret"
                      className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 pr-10 text-sm focus:border-blue-500 focus:outline-none"
                    />
                    <button
                      onClick={() => toggleSecretVisibility('binanceSecret')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                    >
                      {showSecrets.binanceSecret ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Coinbase */}
            <div className="p-4 bg-dark-900 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">🔵</span>
                <span className="font-semibold">Coinbase</span>
                <a 
                  href="https://www.coinbase.com/settings/api"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-auto text-xs text-blue-400 flex items-center gap-1 hover:underline"
                >
                  Get API Keys <ExternalLink size={12} />
                </a>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">API Key</label>
                  <input
                    type="text"
                    value={credentials.coinbaseApiKey}
                    onChange={(e) => setCredentials(prev => ({ ...prev, coinbaseApiKey: e.target.value }))}
                    placeholder="Enter your Coinbase API Key"
                    className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">API Secret</label>
                  <div className="relative">
                    <input
                      type={showSecrets.coinbaseSecret ? 'text' : 'password'}
                      value={credentials.coinbaseSecret}
                      onChange={(e) => setCredentials(prev => ({ ...prev, coinbaseSecret: e.target.value }))}
                      placeholder="Enter your Coinbase API Secret"
                      className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 pr-10 text-sm focus:border-blue-500 focus:outline-none"
                    />
                    <button
                      onClick={() => toggleSecretVisibility('coinbaseSecret')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                    >
                      {showSecrets.coinbaseSecret ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Passphrase</label>
                  <input
                    type={showSecrets.coinbasePassphrase ? 'text' : 'password'}
                    value={credentials.coinbasePassphrase}
                    onChange={(e) => setCredentials(prev => ({ ...prev, coinbasePassphrase: e.target.value }))}
                    placeholder="Enter your Coinbase Passphrase"
                    className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <button
              onClick={handleSaveCredentials}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              {credentialsSaved ? <CheckCircle size={18} className="text-green-400" /> : <Save size={18} />}
              {credentialsSaved ? 'API Keys Saved!' : 'Save API Keys'}
            </button>
          </div>
        </section>

        {/* Auto Trading */}
        <section className="bg-dark-800 rounded-xl p-5 border border-dark-700">
          <div className="flex items-center gap-2 mb-4">
            <Settings2 size={20} className="text-pink-400" />
            <h2 className="text-lg font-semibold">Auto Trading</h2>
          </div>

          <div className="flex items-center justify-between p-4 bg-dark-900 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${settings.autoTrading ? 'bg-green-500/20' : 'bg-gray-700'}`}>
                {settings.autoTrading ? <Unlock size={20} className="text-green-400" /> : <Lock size={20} className="text-gray-400" />}
              </div>
              <div>
                <div className="font-medium">Enable Auto Trading</div>
                <div className="text-xs text-gray-400">
                  Automatically execute ML prediction trades
                </div>
              </div>
            </div>
            <button
              onClick={() => setSettings(prev => ({ ...prev, autoTrading: !prev.autoTrading }))}
              className={`w-14 h-7 rounded-full transition-colors relative ${
                settings.autoTrading ? 'bg-green-500' : 'bg-gray-600'
              }`}
            >
              <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-transform ${
                settings.autoTrading ? 'translate-x-8' : 'translate-x-1'
              }`} />
            </button>
          </div>

          {settings.autoTrading && (
            <div className="mt-4 p-4 bg-dark-900 rounded-lg">
              <label className="flex justify-between text-sm text-gray-400 mb-2">
                <span>Minimum Confidence</span>
                <span className="text-white">{settings.minConfidence}%</span>
              </label>
              <input
                type="range"
                min="50"
                max="95"
                value={settings.minConfidence}
                onChange={(e) => setSettings(prev => ({ ...prev, minConfidence: parseInt(e.target.value) }))}
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>50%</span>
                <span>95%</span>
              </div>
              
              <div className="mt-3 flex items-center gap-2 text-xs text-yellow-400 bg-yellow-500/10 p-3 rounded">
                <AlertTriangle size={14} />
                <span>Requires connected wallet and exchange API keys</span>
              </div>
            </div>
          )}
        </section>

        {/* Risk Settings */}
        <section className="bg-dark-800 rounded-xl p-5 border border-dark-700">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={20} className="text-green-400" />
            <h2 className="text-lg font-semibold">Risk Management</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="flex justify-between text-sm text-gray-400 mb-2">
                <span>Risk Per Trade (%)</span>
                <span className="text-white">{settings.riskPerTrade}%</span>
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
              <label className="flex justify-between text-sm text-gray-400 mb-2">
                <span>Max Open Positions</span>
                <span className="text-white">{settings.maxPositions}</span>
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
        <section className="bg-dark-800 rounded-xl p-5 border border-dark-700">
          <div className="flex items-center gap-2 mb-4">
            <Settings2 size={20} className="text-purple-400" />
            <h2 className="text-lg font-semibold">Appearance</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Theme</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => setSettings(prev => ({ ...prev, theme: 'dark' }))}
                  className={`p-3 rounded-lg border text-sm transition-colors ${
                    (settings as any).theme === 'dark' || !(settings as any).theme
                      ? 'bg-blue-600 border-blue-500 text-white' 
                      : 'bg-dark-900 border-dark-700 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  <div className="w-full h-4 bg-gray-900 rounded mb-2" />
                  Dark
                </button>
                <button
                  onClick={() => setSettings(prev => ({ ...prev, theme: 'light' }))}
                  className={`p-3 rounded-lg border text-sm transition-colors ${
                    (settings as any).theme === 'light'
                      ? 'bg-blue-600 border-blue-500 text-white' 
                      : 'bg-dark-900 border-dark-700 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  <div className="w-full h-4 bg-gray-100 rounded mb-2" />
                  Light
                </button>
                <button
                  onClick={() => setSettings(prev => ({ ...prev, theme: 'system' }))}
                  className={`p-3 rounded-lg border text-sm transition-colors ${
                    (settings as any).theme === 'system'
                      ? 'bg-blue-600 border-blue-500 text-white' 
                      : 'bg-dark-900 border-dark-700 text-gray-400 hover:border-gray-500'
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
              <p className="text-xs text-gray-500 mt-1">Reduce padding and font sizes for denser layout</p>
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
              <p className="text-xs text-gray-500 mt-1">Enable transition animations throughout the app</p>
            </div>
          </div>
        </section>

        {/* Notification Preferences */}
        <section className="bg-dark-800 rounded-xl p-5 border border-dark-700">
          <div className="flex items-center gap-2 mb-4">
            <RefreshCw size={20} className="text-yellow-400" />
            <h2 className="text-lg font-semibold">Notifications</h2>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Trade Executions</div>
                <div className="text-sm text-gray-400">Get notified when trades are opened/closed</div>
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
                <div className="text-sm text-gray-400">Notify on significant price movements</div>
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
                <div className="text-sm text-gray-400">Notify when AI agents make decisions</div>
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
                <div className="text-sm text-gray-400">Critical alerts for stop losses, liquidations</div>
              </div>
              <input
                type="checkbox"
                checked={(settings as any).riskAlerts !== false}
                onChange={(e) => setSettings(prev => ({ ...prev, riskAlerts: e.target.checked }))}
                className="w-5 h-5 rounded accent-blue-500"
              />
            </div>

            <div className="pt-3 border-t border-dark-700">
              <label className="block text-sm text-gray-400 mb-2">Notification Channels</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setSettings(prev => ({ ...prev, telegramEnabled: !(settings as any).telegramEnabled }))}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm border transition-colors ${
                    (settings as any).telegramEnabled
                      ? 'bg-blue-600 border-blue-500 text-white'
                      : 'bg-dark-900 border-dark-700 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  Telegram
                </button>
                <button
                  onClick={() => setSettings(prev => ({ ...prev, discordEnabled: !(settings as any).discordEnabled }))}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm border transition-colors ${
                    (settings as any).discordEnabled
                      ? 'bg-indigo-600 border-indigo-500 text-white'
                      : 'bg-dark-900 border-dark-700 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  Discord
                </button>
                <button
                  onClick={() => setSettings(prev => ({ ...prev, emailEnabled: !(settings as any).emailEnabled }))}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm border transition-colors ${
                    (settings as any).emailEnabled
                      ? 'bg-green-600 border-green-500 text-white'
                      : 'bg-dark-900 border-dark-700 text-gray-400 hover:border-gray-500'
                  }`}
                >
                  Email
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Accessibility */}
        <section className="bg-dark-800 rounded-xl p-5 border border-dark-700">
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
              <p className="text-xs text-gray-500 mt-1">Increase contrast for better visibility</p>
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
              <p className="text-xs text-gray-500 mt-1">Increase font sizes throughout the app</p>
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
              <p className="text-xs text-gray-500 mt-1">Minimize animations and transitions</p>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Refresh Rate</label>
              <select
                value={settings.refreshInterval}
                onChange={(e) => setSettings(prev => ({ ...prev, refreshInterval: parseInt(e.target.value) }))}
                className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-sm"
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
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors"
        >
          {saved ? <CheckCircle size={18} className="text-green-400" /> : <Save size={18} />}
          {saved ? 'Settings Saved!' : 'Save Settings'}
        </button>

        {/* Version */}
        <div className="text-center text-xs text-gray-600">
          <div>Trading Bot v2.0.0</div>
          <div>ZeroClaw AI • Multi-Agent System</div>
        </div>
      </div>
    </div>
  );
}
