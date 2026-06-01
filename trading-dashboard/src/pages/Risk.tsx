import { useEffect, useState } from 'react';
import { 
  Shield, AlertTriangle, TrendingDown, Target,
  DollarSign, Percent, Activity, Save
} from 'lucide-react';
import { Header } from '../components/Header';
import { GlassCard, ShimmerCard, PageHeader } from '../components/ui/GlassCard';
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
      <div className="pb-20 lg:pb-6 lg:pl-[224px]">
        <Header title="Risk Management" />
        <div className="flex items-center justify-center h-64">
          <ShimmerCard height="h-8" />
        </div>
      </div>
    );
  }

  const riskParams = config?.risk || {};

  return (
    <div className="pb-20 lg:pb-6 lg:pl-[224px]">
      <Header title="Risk Management" />

      <div className="p-4 max-w-[960px] mx-auto space-y-6">
        <PageHeader title="Risk Management" subtitle="Control maximum risk exposure for all trading strategies" />

        {/* Warning */}
        <GlassCard variant="gold" padding="sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-[#D4AF37] flex-shrink-0 mt-0.5" size={18} />
            <div className="text-sm text-[#e8ecf1]">
              <p className="font-semibold mb-1">Risk Management</p>
              <p className="text-[#5a6a7e]">These settings control the maximum risk exposure for all trading strategies. Incorrect settings may lead to significant losses.</p>
            </div>
          </div>
        </GlassCard>

        {/* Risk Parameters */}
        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <Shield className="text-[#EF476F]" size={20} />
            <span className="font-semibold text-[#e8ecf1]">Risk Parameters</span>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.03] transition-colors">
              <div className="flex items-center gap-3">
                <Target size={18} className="text-blue-400" />
                <div>
                  <div className="font-medium text-[#e8ecf1] text-sm">Max Position Size (BTC)</div>
                  <div className="text-xs text-[#5a6a7e]">Maximum BTC per position</div>
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
                className="input-glass w-24 text-right px-3 py-2"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.03] transition-colors">
              <div className="flex items-center gap-3">
                <TrendingDown size={18} className="text-[#EF476F]" />
                <div>
                  <div className="font-medium text-[#e8ecf1] text-sm">Stop Loss (%)</div>
                  <div className="text-xs text-[#5a6a7e]">Auto-close position at loss</div>
                </div>
              </div>
              <input
                type="number"
                value={(riskParams.stop_loss_pct || 0.02) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, stop_loss_pct: parseFloat(e.target.value) / 100 }
                })}
                className="input-glass w-24 text-right px-3 py-2"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.03] transition-colors">
              <div className="flex items-center gap-3">
                <TrendingDown size={18} className="text-[#00C9A7]" />
                <div>
                  <div className="font-medium text-[#e8ecf1] text-sm">Take Profit (%)</div>
                  <div className="text-xs text-[#5a6a7e]">Auto-close position at profit</div>
                </div>
              </div>
              <input
                type="number"
                value={(riskParams.take_profit_pct || 0.06) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, take_profit_pct: parseFloat(e.target.value) / 100 }
                })}
                className="input-glass w-24 text-right px-3 py-2"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.03] transition-colors">
              <div className="flex items-center gap-3">
                <Percent size={18} className="text-[#D4AF37]" />
                <div>
                  <div className="font-medium text-[#e8ecf1] text-sm">Capital Per Trade (%)</div>
                  <div className="text-xs text-[#5a6a7e]">Max capital allocation per trade</div>
                </div>
              </div>
              <input
                type="number"
                value={(riskParams.capital_pct_per_trade || 0.0125) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, capital_pct_per_trade: parseFloat(e.target.value) / 100 }
                })}
                className="input-glass w-24 text-right px-3 py-2"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.03] transition-colors">
              <div className="flex items-center gap-3">
                <Activity size={18} className="text-blue-400" />
                <div>
                  <div className="font-medium text-[#e8ecf1] text-sm">Max Total Exposure (%)</div>
                  <div className="text-xs text-[#5a6a7e]">Maximum portfolio exposure</div>
                </div>
              </div>
              <input
                type="number"
                value={(riskParams.max_total_exposure_pct || 0.3) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, max_total_exposure_pct: parseFloat(e.target.value) / 100 }
                })}
                className="input-glass w-24 text-right px-3 py-2"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.03] transition-colors">
              <div className="flex items-center gap-3">
                <DollarSign size={18} className="text-[#FF6B35]" />
                <div>
                  <div className="font-medium text-[#e8ecf1] text-sm">Daily Loss Limit (%)</div>
                  <div className="text-xs text-[#5a6a7e]">Circuit breaker threshold</div>
                </div>
              </div>
              <input
                type="number"
                value={(riskParams.daily_loss_limit_pct || 0.05) * 100}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, daily_loss_limit_pct: parseFloat(e.target.value) / 100 }
                })}
                className="input-glass w-24 text-right px-3 py-2"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.03] transition-colors">
              <div className="flex items-center gap-3">
                <AlertTriangle size={18} className="text-[#EF476F]" />
                <div>
                  <div className="font-medium text-[#e8ecf1] text-sm">Consecutive Loss Limit</div>
                  <div className="text-xs text-[#5a6a7e]">Pause after N losses</div>
                </div>
              </div>
              <input
                type="number"
                value={riskParams.consecutive_loss_limit || 3}
                onChange={(e) => setConfig({
                  ...config,
                  risk: { ...riskParams, consecutive_loss_limit: parseInt(e.target.value) }
                })}
                className="input-glass w-24 text-right px-3 py-2"
              />
            </div>
          </div>

          <button
            onClick={saveConfig}
            disabled={saving}
            className="btn-primary w-full mt-4"
          >
            {saving ? (
              <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Saving...</>
            ) : (
              <><Save size={18} /> Save Risk Settings</>
            )}
          </button>
        </GlassCard>
      </div>
    </div>
  );
}
