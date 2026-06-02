import { useEffect, useState } from 'react';
import { 
  Brain, RefreshCw, TrendingUp, TrendingDown, Minus, Activity,
  ChevronDown, ChevronUp, Calculator, DollarSign, Lightbulb,
  Target, Shield, AlertTriangle, BookOpen, BarChart3, Clock
} from 'lucide-react';
import { Header } from '../components/Header';
import { api } from '../api/client';
import { formatUSD } from '../utils/format';

interface MLPrediction {
  symbol: string;
  signal: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  current_price: number;
  target_price: number;
  stop_loss: number;
  timeframe: string;
  reasoning: string;
  indicators: {
    rsi: number;
    trend: string;
    momentum: number;
    support: number;
    resistance: number;
    volatility: number;
    volume_trend: string;
  };
  generated_at: string;
}

interface CalculatorInputs {
  investmentAmount: number;
  riskPercent: number;
}

export function ML() {
  const [predictions, setPredictions] = useState<MLPrediction[]>([]);
  const [marketSummary, setMarketSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showEducation, setShowEducation] = useState(true);
  
  const [calculator, setCalculator] = useState<CalculatorInputs>({
    investmentAmount: 500,
    riskPercent: 2,
  });

  async function loadPredictions() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/ml-predictions');
      const data = await res.json();
      
      if (data.success) {
        setPredictions(data.predictions);
        setMarketSummary(data.market_summary);
      } else {
        setError(data.error || 'Failed to load predictions');
      }
    } catch (e) {
      setError('Network error loading predictions');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPredictions();
    const interval = setInterval(loadPredictions, 60000);
    return () => clearInterval(interval);
  }, []);

  function calculatePosition(prediction: MLPrediction) {
    const entryPrice = prediction.current_price;
    const targetPrice = prediction.target_price;
    const stopLoss = prediction.stop_loss;
    
    const riskAmount = calculator.investmentAmount * (calculator.riskPercent / 100);
    const riskPerUnit = Math.abs(entryPrice - stopLoss);
    const positionSize = riskPerUnit > 0 ? riskAmount / riskPerUnit : 0;
    const positionValue = positionSize * entryPrice;
    const potentialProfit = positionSize * Math.abs(targetPrice - entryPrice);
    const potentialLoss = riskAmount;
    const riskReward = potentialLoss > 0 ? potentialProfit / potentialLoss : 0;
    
    return {
      positionSize: positionSize.toFixed(4),
      positionValue: positionValue.toFixed(2),
      potentialProfit: potentialProfit.toFixed(2),
      potentialLoss: potentialLoss.toFixed(2),
      riskReward: riskReward.toFixed(2),
      isViable: riskReward >= 1.5 && prediction.confidence >= 60,
    };
  }

  const getSignalColor = (signal: string) => {
    if (signal === 'BUY') return 'text-[#00C9A7] bg-[#00C9A7]/20 border-[#00C9A7]/30';
    if (signal === 'SELL') return 'text-[#EF476F] bg-[#EF476F]/20 border-[#EF476F]/30';
    return 'text-[#D4AF37] bg-[#D4AF37]/20 border-[#D4AF37]/30';
  };

  const getConfidenceColor = (conf: number) => {
    if (conf >= 75) return 'text-[#00C9A7]';
    if (conf >= 60) return 'text-[#D4AF37]';
    return 'text-[#EF476F]';
  };

  return (
    <div className="pb-20 lg:pb-8 lg:pl-[224px]">
      <Header title="AI Trading Signals" />
      
      <div className="p-4 space-y-4">
        {/* Education Panel */}
        {showEducation && (
          <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl border border-[#0F4C75]/30 p-4">
            <div className="flex items-start gap-3">
              <BookOpen size={24} className="text-[#3B82F6] flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-bold text-[#3B82F6] mb-2">How AI Predictions Work</h3>
                <div className="text-sm text-[#e8ecf1] space-y-1">
                  <p>• <strong>Technical Analysis:</strong> RSI, moving averages, momentum indicators</p>
                  <p>• <strong>Market Sentiment:</strong> Price trends, volatility, volume analysis</p>
                  <p>• <strong>Risk Management:</strong> Position sizing based on your investment amount</p>
                  <p>• <strong>Signal Confidence:</strong> Higher % = stronger prediction reliability</p>
                </div>
              </div>
              <button 
                onClick={() => setShowEducation(false)}
                className="ml-auto text-[#5a6a7e] hover:text-[#e8ecf1]"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Market Overview */}
        {marketSummary && (
          <div className="grid grid-cols-4 gap-2">
            <div className="glass-card rounded-xl p-3 text-center border border-[#00C9A7]/30">
              <div className="text-2xl font-bold text-[#00C9A7]">{marketSummary.bullish_signals}</div>
              <div className="text-xs text-[#5a6a7e]">Buy Signals</div>
            </div>
            <div className="glass-card rounded-xl p-3 text-center border border-[#EF476F]/30">
              <div className="text-2xl font-bold text-[#EF476F]">{marketSummary.bearish_signals}</div>
              <div className="text-xs text-[#5a6a7e]">Sell Signals</div>
            </div>
            <div className="glass-card rounded-xl p-3 text-center border border-[#D4AF37]/30">
              <div className="text-2xl font-bold text-[#D4AF37]">{marketSummary.avg_confidence}%</div>
              <div className="text-xs text-[#5a6a7e]">Avg Confidence</div>
            </div>
            <div className="glass-card rounded-xl p-3 text-center border border-[#0F4C75]/30">
              <div className="text-2xl font-bold text-[#3B82F6]">{predictions.length}</div>
              <div className="text-xs text-[#5a6a7e]">Assets Analyzed</div>
            </div>
          </div>
        )}

        {/* Calculator */}
        <div className="glass-card rounded-xl border border-[rgba(30,50,70,0.3)] p-4">
          <div className="flex items-center gap-2 mb-3">
            <Calculator size={20} className="text-[#3B82F6]" />
            <span className="font-bold">Your Investment Plan</span>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-[#5a6a7e] mb-1">How much do you want to invest? ($)</label>
              <div className="relative">
                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#3d4d60]" />
                <input
                  type="number"
                  value={calculator.investmentAmount}
                  onChange={(e) => setCalculator({...calculator, investmentAmount: Number(e.target.value)})}
                  className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg pl-8 pr-3 py-2"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-[#5a6a7e] mb-1">Risk per trade (%)</label>
              <input
                type="number"
                step="0.5"
                value={calculator.riskPercent}
                onChange={(e) => setCalculator({...calculator, riskPercent: Number(e.target.value)})}
                className="w-full bg-[#090d14] border border-[rgba(30,50,70,0.3)] rounded-lg px-3 py-2"
              />
              <div className="text-xs text-[#3d4d60] mt-1">
                You're risking ${(calculator.investmentAmount * calculator.riskPercent / 100).toFixed(2)} per trade
              </div>
            </div>
          </div>
        </div>

        {/* Loading/Error States */}
        {loading && predictions.length === 0 && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3B82F6]"></div>
            <span className="ml-3 text-[#5a6a7e]">Analyzing market data...</span>
          </div>
        )}
        
        {error && (
          <div className="bg-[#EF476F]/10 border border-[#EF476F]/30 rounded-xl p-4 text-center">
            <AlertTriangle size={24} className="mx-auto mb-2 text-[#EF476F]" />
            <p className="text-[#EF476F]">{error}</p>
            <button 
              onClick={loadPredictions}
              className="mt-2 px-4 py-2 bg-[#D63D5E] rounded-lg text-sm"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Predictions */}
        <div className="space-y-3">
          {predictions.map((pred) => {
            const calc = calculatePosition(pred);
            const isExpanded = expandedId === pred.symbol;
            
            return (
              <div key={pred.symbol} className={`glass-card rounded-xl border overflow-hidden ${getSignalColor(pred.signal)}`}>
                {/* Main Info */}
                <div className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${pred.signal === 'BUY' ? 'bg-[#00C9A7]/20' : pred.signal === 'SELL' ? 'bg-[#EF476F]/20' : 'bg-[#D4AF37]/20'}`}>
                        {pred.signal === 'BUY' ? <TrendingUp size={20} className="text-[#00C9A7]" /> : 
                         pred.signal === 'SELL' ? <TrendingDown size={20} className="text-[#EF476F]" /> : 
                         <Minus size={20} className="text-[#D4AF37]" />}
                      </div>
                      <div>
                        <div className="font-bold text-lg">{pred.symbol}</div>
                        <div className="text-xs text-[#5a6a7e]">Based on {pred.timeframe} analysis</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-xl">{pred.signal}</div>
                      <div className={`text-sm ${getConfidenceColor(pred.confidence)}`}>
                        {pred.confidence}% confidence
                      </div>
                    </div>
                  </div>

                  {/* Prices */}
                  <div className="grid grid-cols-3 gap-2 mt-3">
                    <div className="bg-[#090d14]/50 rounded-lg p-2 text-center">
                      <div className="text-xs text-[#3d4d60]">Current Price</div>
                      <div className="font-mono font-medium">{formatUSD(pred.current_price)}</div>
                    </div>
                    <div className="bg-[#00C9A7]/10 rounded-lg p-2 text-center">
                      <div className="text-xs text-[#00C9A7]">Target</div>
                      <div className="font-mono font-medium text-[#00C9A7]">{formatUSD(pred.target_price)}</div>
                    </div>
                    <div className="bg-[#EF476F]/10 rounded-lg p-2 text-center">
                      <div className="text-xs text-[#EF476F]">Stop Loss</div>
                      <div className="font-mono font-medium text-[#EF476F]">{formatUSD(pred.stop_loss)}</div>
                    </div>
                  </div>

                  {/* Your Position Analysis */}
                  <div className="mt-3 p-3 bg-[#090d14] rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Target size={16} className="text-[#3B82F6]" />
                      <span className="font-medium text-sm">Your Position Analysis</span>
                      {calc.isViable ? (
                        <span className="ml-auto px-2 py-0.5 bg-[#00C9A7] text-[#090d14] text-xs rounded-full">Viable Trade</span>
                      ) : (
                        <span className="ml-auto px-2 py-0.5 bg-[#D4AF37]/50 text-[#e8ecf1] text-xs rounded-full">High Risk</span>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-3 gap-2 text-center mb-2">
                      <div>
                        <div className="text-xs text-[#3d4d60]">Position Size</div>
                        <div className="font-mono">{calc.positionSize} units</div>
                      </div>
                      <div>
                        <div className="text-xs text-[#00C9A7]">Potential Profit</div>
                        <div className="font-mono text-[#00C9A7]">+${calc.potentialProfit}</div>
                      </div>
                      <div>
                        <div className="text-xs text-[#EF476F]">Max Loss</div>
                        <div className="font-mono text-[#EF476F]">-${calc.potentialLoss}</div>
                      </div>
                    </div>
                    
                    <div className="text-xs text-[#5a6a7e]">
                      Risk/Reward Ratio: <span className={Number(calc.riskReward) >= 2 ? 'text-[#00C9A7]' : 'text-[#D4AF37]'}>1:{calc.riskReward}</span>
                      <span className="ml-2 text-[#3d4d60]">(Recommended: 1:2 or higher)</span>
                    </div>
                  </div>

                  {/* Why This Signal? */}
                  <div className="mt-3 p-3 bg-[#0F4C75]/10 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Lightbulb size={16} className="text-[#D4AF37] mt-0.5" />
                      <div>
                        <div className="text-xs text-[#3B82F6] mb-1">Why this signal?</div>
                        <div className="text-sm">{pred.reasoning}</div>
                      </div>
                    </div>
                  </div>

                  {/* Expand Button */}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : pred.symbol)}
                    className="w-full mt-3 flex items-center justify-center gap-1 text-sm text-[#3B82F6] hover:text-[#3B82F6]/80"
                  >
                    {isExpanded ? 'Hide' : 'View'} Technical Details
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>

                {/* Technical Details */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-[rgba(30,50,70,0.3)]/50">
                    <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2">
                      <div className="p-2 bg-[#090d14] rounded text-center">
                        <div className="text-xs text-[#3d4d60]">RSI</div>
                        <div className={`font-mono ${pred.indicators.rsi < 30 ? 'text-[#00C9A7]' : pred.indicators.rsi > 70 ? 'text-[#EF476F]' : ''}`}>
                          {pred.indicators.rsi}
                        </div>
                        <div className="text-xs text-[#3d4d60]">
                          {pred.indicators.rsi < 30 ? 'Oversold' : pred.indicators.rsi > 70 ? 'Overbought' : 'Neutral'}
                        </div>
                      </div>
                      <div className="p-2 bg-[#090d14] rounded text-center">
                        <div className="text-xs text-[#3d4d60]">Trend</div>
                        <div className={`capitalize ${pred.indicators.trend === 'bullish' ? 'text-[#00C9A7]' : pred.indicators.trend === 'bearish' ? 'text-[#EF476F]' : ''}`}>
                          {pred.indicators.trend}
                        </div>
                      </div>
                      <div className="p-2 bg-[#090d14] rounded text-center">
                        <div className="text-xs text-[#3d4d60]">Support</div>
                        <div className="font-mono text-[#00C9A7]">{formatUSD(pred.indicators.support)}</div>
                      </div>
                      <div className="p-2 bg-[#090d14] rounded text-center">
                        <div className="text-xs text-[#3d4d60]">Resistance</div>
                        <div className="font-mono text-[#EF476F]">{formatUSD(pred.indicators.resistance)}</div>
                      </div>
                    </div>
                    
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <div className="p-2 bg-[#090d14] rounded text-center">
                        <div className="text-xs text-[#3d4d60]">Momentum</div>
                        <div className={`font-mono ${pred.indicators.momentum > 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
                          {pred.indicators.momentum > 0 ? '+' : ''}{pred.indicators.momentum.toFixed(2)}%
                        </div>
                      </div>
                      <div className="p-2 bg-[#090d14] rounded text-center">
                        <div className="text-xs text-[#3d4d60]">Volatility</div>
                        <div className="font-mono">{pred.indicators.volatility.toFixed(2)}%</div>
                      </div>
                    </div>

                    {/* Educational Tooltips */}
                    <div className="mt-3 text-xs text-[#3d4d60] space-y-1">
                      <p><strong>RSI (Relative Strength Index):</strong> Measures speed/change of price movements. Below 30 = oversold (potential buy), above 70 = overbought (potential sell).</p>
                      <p><strong>Support/Resistance:</strong> Price levels where the asset tends to stop falling (support) or rising (resistance).</p>
                      <p><strong>Momentum:</strong> Rate of price change. Positive = uptrend, negative = downtrend.</p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Refresh */}
        <button 
          onClick={loadPredictions}
          disabled={loading}
          className="w-full py-3 glass-card rounded-xl border border-[rgba(30,50,70,0.3)] flex items-center justify-center gap-2 text-[#5a6a7e] hover:text-[#e8ecf1] disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Analyzing...' : 'Refresh Analysis'}
        </button>
      </div>
    </div>
  );
}
