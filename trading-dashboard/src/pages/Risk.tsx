import { useEffect, useState } from 'react';
import { 
  Shield, AlertTriangle, TrendingDown, Target,
  DollarSign, Percent, Activity, Save
} from 'lucide-react';
import { Header } from '../components/Header';
import { api } from '../api/client';

export function Risk() {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function loadConfig() {
    try {
      const data = await api.getConfig();
      setConfig(data);
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  }

  async function saveConfig() {
    setSaving(true);
    try {
      await api.updateConfig(config);
    } catch (error) {
      console.error('Failed to save config:', error);
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    loadConfig();
  }, []);

  if (loading) {
    return (
      <div className="pb-20 lg:pb-8 lg:pl-64">
        <Header title="Risk Management" />
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
        </div>
      </div>
    );
  }

  const riskParams = config?.risk || {};

  return (
    <div className="pb-20 lg:pb-8 lg:pl-64">
      <Header title="Risk Management" />
      
      <div className="p-4 space-y-6">
        {/* Warning */}
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-yellow-400 flex-shrink-0 mt-0.5" size={18} />
            <div className="text-sm text-gray-300">
              <p className="mb-1"><strong>Risk Management</strong></p>
              <p>These settings control the maximum risk exposure for all trading strategies. Incorrect settings may lead to significant losses.</p>
            </div>
          </div>
        </div>

        {/* Risk Parameters */}
        <div className="bg-dark-800 rounded-xl border border-dark-700 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="text-red-400" size={20} />
            <span className="font-semibold">Risk Parameters</span>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
              <div className="flex items-center gap-3">
                <Target size={18} className="text-blue-400" />
                <div>
                  <div className="font-medium">Max Position Size (BTC)</div>
                  <div className="text-sm text-gray-400">Maximum BTC per position</div>
                </div>
              </div>
              <input 
                type="number"
                value={riskParams.max_position_btc || 0.05}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, max_position_btc: parseFloat(e.target.value) }
                })}
                step={0.01}
                className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 w-24 text-right focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
              <div className="flex items-center gap-3">
                <TrendingDown size={18} className="text-red-400" />
                <div>
                  <div className="font-medium">Stop Loss (%)</div>
                  <div className="text-sm text-gray-400">Auto-close position at loss</div>
                </div>
              </div>
              <input 
                type="number"
                value={(riskParams.stop_loss_pct || 0.02) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, stop_loss_pct: parseFloat(e.target.value) / 100 }
                })}
                className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 w-24 text-right focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
              <div className="flex items-center gap-3">
                <TrendingDown size={18} className="text-green-400" />
                <div>
                  <div className="font-medium">Take Profit (%)</div>
                  <div className="text-sm text-gray-400">Auto-close position at profit</div>
                </div>
              </div>
              <input 
                type="number"
                value={(riskParams.take_profit_pct || 0.06) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, take_profit_pct: parseFloat(e.target.value) / 100 }
                })}
                className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 w-24 text-right focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
              <div className="flex items-center gap-3">
                <Percent size={18} className="text-yellow-400" />
                <div>
                  <div className="font-medium">Capital Per Trade (%)</div>
                  <div className="text-sm text-gray-400">Max capital allocation per trade</div>
                </div>
              </div>
              <input 
                type="number"
                value={(riskParams.capital_pct_per_trade || 0.0125) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, capital_pct_per_trade: parseFloat(e.target.value) / 100 }
                })}
                className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 w-24 text-right focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
              <div className="flex items-center gap-3">
                <Activity size={18} className="text-purple-400" />
                <div>
                  <div className="font-medium">Max Total Exposure (%)</div>
                  <div className="text-sm text-gray-400">Maximum portfolio exposure</div>
                </div>
              </div>
              <input 
                type="number"
                value={(riskParams.max_total_exposure_pct || 0.3) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, max_total_exposure_pct: parseFloat(e.target.value) / 100 }
                })}
                className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 w-24 text-right focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
              <div className="flex items-center gap-3">
                <DollarSign size={18} className="text-orange-400" />
                <div>
                  <div className="font-medium">Daily Loss Limit (%)</div>
                  <div className="text-sm text-gray-400">Circuit breaker threshold</div>
                </div>
              </div>
              <input 
                type="number"
                value={(riskParams.daily_loss_limit_pct || 0.05) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, daily_loss_limit_pct: parseFloat(e.target.value) / 100 }
                })}
                className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 w-24 text-right focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
              <div className="flex items-center gap-3">
                <AlertTriangle size={18} className="text-red-400" />
                <div>
                  <div className="font-medium">Consecutive Loss Limit</div>
                  <div className="text-sm text-gray-400">Pause after N losses</div>
                </div>
              </div>
              <input 
                type="number"
                value={riskParams.consecutive_loss_limit || 3}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, consecutive_loss_limit: parseInt(e.target.value) }
                })}
                className="bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 w-24 text-right focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          <button 
            onClick={saveConfig}
            disabled={saving}
            className="w-full mt-4 flex items-center justify-center gap-2 p-3 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? (
              <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Saving...</>
            ) : (
              <><Save size={18} /> Save Risk Settings</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
