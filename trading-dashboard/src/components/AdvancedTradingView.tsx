import { useEffect, useRef, useState, useCallback } from 'react';
import { 
  createChart, 
  type IChartApi, 
  type ISeriesApi, 
  type CandlestickData, 
  type HistogramData,
  type LineData,
  type Time,
  LineStyle,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from 'lightweight-charts';
import { TrendingUp, TrendingDown, X } from 'lucide-react';

export interface TradingData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Suggestion {
  type: 'sl' | 'tp' | 'entry';
  price: number;
  confidence: number;
  reason: string;
  source: 'atr' | 'support_resistance' | 'risk_reward' | 'ai_prediction';
}

export interface PivotPoint {
  time: Time;
  pp: number;
  r1: number;
  r2: number;
  r3: number;
  s1: number;
  s2: number;
  s3: number;
}

interface AdvancedTradingViewProps {
  symbol: string;
  data: TradingData[];
  height?: number;
  onSLChange?: (price: number) => void;
  onTPChange?: (price: number) => void;
  stopLoss?: number;
  takeProfit?: number;
  suggestions?: Suggestion[];
  showVolume?: boolean;
  showEMA?: boolean;
  showBollinger?: boolean;
  showPivots?: boolean;
  isMobile?: boolean;
  onToggleVolume?: () => void;
  onToggleEMA?: () => void;
  onToggleBollinger?: () => void;
  onTogglePivots?: () => void;
  isFullscreen?: boolean;
  onExitFullscreen?: () => void;
}

// EMA with dynamic color based on price position
function calculateDynamicEMA(data: TradingData[], period: number): { time: Time; value: number; color: string }[] {
  const k = 2 / (period + 1);
  const emaData: { time: Time; value: number; color: string }[] = [];
  let ema = data[0]?.close || 0;
  
  data.forEach((candle) => {
    ema = candle.close * k + ema * (1 - k);
    // Green when price above EMA (bullish), Red when below (bearish)
    const color = candle.close >= ema ? '#22c55e' : '#ef4444';
    emaData.push({ time: candle.time as Time, value: ema, color });
  });
  
  return emaData;
}

// Calculate Pivot Points (works on any timeframe)
export function calculatePivotPoints(data: TradingData[]): PivotPoint[] {
  const pivots: PivotPoint[] = [];
  
  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1];
    const current = data[i];
    
    // Classic Pivot Point formula
    const pp = (prev.high + prev.low + prev.close) / 3;
    const r1 = (2 * pp) - prev.low;
    const r2 = pp + (prev.high - prev.low);
    const r3 = prev.high + 2 * (pp - prev.low);
    const s1 = (2 * pp) - prev.high;
    const s2 = pp - (prev.high - prev.low);
    const s3 = prev.low - 2 * (prev.high - pp);
    
    pivots.push({
      time: current.time as Time,
      pp,
      r1, r2, r3,
      s1, s2, s3
    });
  }
  
  return pivots;
}

// Technical Analysis Functions
function calculateATR(data: TradingData[], period: number = 14): number[] {
  const atr: number[] = [];
  let trSum = 0;
  
  for (let i = 0; i < data.length; i++) {
    const current = data[i];
    const prev = i > 0 ? data[i - 1] : current;
    
    const tr1 = current.high - current.low;
    const tr2 = Math.abs(current.high - prev.close);
    const tr3 = Math.abs(current.low - prev.close);
    const tr = Math.max(tr1, tr2, tr3);
    
    if (i < period) {
      trSum += tr;
      atr.push(trSum / (i + 1));
    } else {
      const prevATR = atr[i - 1];
      atr.push((prevATR * (period - 1) + tr) / period);
    }
  }
  
  return atr;
}

function calculateBollingerBands(data: TradingData[], period: number = 20, stdDev: number = 2) {
  const upper: { time: Time; value: number }[] = [];
  const middle: { time: Time; value: number }[] = [];
  const lower: { time: Time; value: number }[] = [];
  
  for (let i = period - 1; i < data.length; i++) {
    const slice = data.slice(i - period + 1, i + 1);
    const closes = slice.map(d => d.close);
    const sma = closes.reduce((a, b) => a + b, 0) / period;
    const variance = closes.reduce((a, b) => a + Math.pow(b - sma, 2), 0) / period;
    const std = Math.sqrt(variance);
    
    upper.push({ time: data[i].time as Time, value: sma + stdDev * std });
    middle.push({ time: data[i].time as Time, value: sma });
    lower.push({ time: data[i].time as Time, value: sma - stdDev * std });
  }
  
  return { upper, middle, lower };
}

// AI SL/TP Calculator
export function calculateSLTPSuggestions(
  data: TradingData[],
  currentPrice: number,
  position: 'long' | 'short' = 'long'
): Suggestion[] {
  if (data.length < 20) return [];
  
  const suggestions: Suggestion[] = [];
  
  // 1. ATR-Based Stop Loss
  const atrValues = calculateATR(data, 14);
  const currentATR = atrValues[atrValues.length - 1];
  
  suggestions.push({
    type: 'sl',
    price: currentPrice - (currentATR * 2),
    confidence: 85,
    reason: `ATR-based stop (14-period ATR: ${currentATR.toFixed(2)})`,
    source: 'atr',
  });
  
  // 2. Support/Resistance Based
  const recentLows = data.slice(-20).map(d => d.low);
  const recentHighs = data.slice(-20).map(d => d.high);
  const support = Math.min(...recentLows);
  const resistance = Math.max(...recentHighs);
  
  if (position === 'long') {
    suggestions.push({
      type: 'sl',
      price: support * 0.995,
      confidence: 78,
      reason: `Support level at ${support.toFixed(2)}`,
      source: 'support_resistance',
    });
    suggestions.push({
      type: 'tp',
      price: resistance * 1.02,
      confidence: 72,
      reason: `Resistance target at ${resistance.toFixed(2)}`,
      source: 'support_resistance',
    });
  }
  
  // 3. Risk:Reward Optimized (1:2 R:R)
  const riskAmount = currentPrice - (support * 0.995);
  const optimalTP = currentPrice + (riskAmount * 2);
  
  suggestions.push({
    type: 'tp',
    price: optimalTP,
    confidence: 90,
    reason: 'Optimal 1:2 Risk:Reward ratio',
    source: 'risk_reward',
  });
  
  return suggestions;
}

export function AdvancedTradingView({
  symbol,
  data,
  height = 600,
  onSLChange,
  onTPChange,
  stopLoss,
  takeProfit,
  suggestions = [],
  showVolume = true,
  showEMA = true,
  showBollinger = false,
  showPivots = false,
  isMobile = false,
  onToggleVolume,
  onToggleEMA,
  onToggleBollinger,
  onTogglePivots,
  isFullscreen = false,
  onExitFullscreen,
}: AdvancedTradingViewProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const emaSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const bollingerUpperRef = useRef<ISeriesApi<'Line'> | null>(null);
  const bollingerLowerRef = useRef<ISeriesApi<'Line'> | null>(null);
  const slLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  const tpLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  // Pivot point refs
  const pivotPPRef = useRef<ISeriesApi<'Line'> | null>(null);
  const pivotR1Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const pivotR2Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const pivotS1Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const pivotS2Ref = useRef<ISeriesApi<'Line'> | null>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [emaData, setEmaData] = useState<{ time: Time; value: number; color: string }[]>([]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current || chartRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#3b82f6',
          labelBackgroundColor: '#3b82f6',
        },
        horzLine: {
          color: '#3b82f6',
          labelBackgroundColor: '#3b82f6',
        },
      },
      rightPriceScale: {
        borderColor: '#1e293b',
      },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: {
        vertTouchDrag: false,
      },
    });

    chartRef.current = chart;

    // Main candlestick series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });
    candlestickSeriesRef.current = candlestickSeries;

    // Volume series
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#3b82f6',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
      visible: false,
    });
    volumeSeriesRef.current = volumeSeries;

    // Dynamic EMA series - color changes based on price position
    const emaSeries = chart.addSeries(LineSeries, {
      color: '#22c55e', // Default, will be updated
      lineWidth: 2,
      title: 'EMA 20',
    });
    emaSeriesRef.current = emaSeries;

    // Bollinger Bands
    const bbUpper = chart.addSeries(LineSeries, {
      color: '#06b6d4',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: 'BB Upper',
    });
    bollingerUpperRef.current = bbUpper;

    const bbLower = chart.addSeries(LineSeries, {
      color: '#06b6d4',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: 'BB Lower',
    });
    bollingerLowerRef.current = bbLower;

    // Pivot Points
    const pivotPP = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      title: 'PP',
    });
    pivotPPRef.current = pivotPP;

    const pivotR1 = chart.addSeries(LineSeries, {
      color: '#22c55e',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      title: 'R1',
    });
    pivotR1Ref.current = pivotR1;

    const pivotR2 = chart.addSeries(LineSeries, {
      color: '#16a34a',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      title: 'R2',
    });
    pivotR2Ref.current = pivotR2;

    const pivotS1 = chart.addSeries(LineSeries, {
      color: '#ef4444',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      title: 'S1',
    });
    pivotS1Ref.current = pivotS1;

    const pivotS2 = chart.addSeries(LineSeries, {
      color: '#dc2626',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      title: 'S2',
    });
    pivotS2Ref.current = pivotS2;

    // SL/TP lines
    if (onSLChange) {
      const slSeries = chart.addSeries(LineSeries, {
        color: '#f97316',
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        title: 'SL',
        lastValueVisible: true,
      });
      slLineRef.current = slSeries;
    }

    if (onTPChange) {
      const tpSeries = chart.addSeries(LineSeries, {
        color: '#22c55e',
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        title: 'TP',
        lastValueVisible: true,
      });
      tpLineRef.current = tpSeries;
    }

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: height,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [height, onSLChange, onTPChange]);

  // Update data
  useEffect(() => {
    if (!data.length || !candlestickSeriesRef.current) return;

    const candleData: CandlestickData<Time>[] = data.map(d => ({
      time: d.time as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candlestickSeriesRef.current.setData(candleData);

    // Volume
    if (volumeSeriesRef.current) {
      const volumeData: HistogramData<Time>[] = data.map(d => ({
        time: d.time as Time,
        value: d.volume,
        color: d.close >= d.open ? '#22c55e60' : '#ef444460',
      }));
      volumeSeriesRef.current.setData(volumeData);
      volumeSeriesRef.current.applyOptions({ visible: showVolume });
    }

    // Dynamic EMA with color based on price position
    if (emaSeriesRef.current) {
      const dynamicEMA = calculateDynamicEMA(data, 20);
      setEmaData(dynamicEMA);
      
      // Set the line color based on latest position
      const lastPoint = dynamicEMA[dynamicEMA.length - 1];
      const emaColor = lastPoint?.color || '#22c55e';
      emaSeriesRef.current.applyOptions({ color: emaColor });
      
      // Set the data
      emaSeriesRef.current.setData(dynamicEMA.map(d => ({ time: d.time, value: d.value })));
      emaSeriesRef.current.applyOptions({ visible: showEMA });
    }

    // Bollinger Bands
    if (bollingerUpperRef.current && bollingerLowerRef.current) {
      const { upper, lower } = calculateBollingerBands(data);
      bollingerUpperRef.current.setData(upper);
      bollingerLowerRef.current.setData(lower);
      bollingerUpperRef.current.applyOptions({ visible: showBollinger });
      bollingerLowerRef.current.applyOptions({ visible: showBollinger });
    }

    // Pivot Points
    if (pivotPPRef.current && data.length > 1) {
      const pivots = calculatePivotPoints(data);
      
      if (pivotPPRef.current) {
        pivotPPRef.current.setData(pivots.map(p => ({ time: p.time, value: p.pp })));
        pivotPPRef.current.applyOptions({ visible: showPivots });
      }
      if (pivotR1Ref.current) {
        pivotR1Ref.current.setData(pivots.map(p => ({ time: p.time, value: p.r1 })));
        pivotR1Ref.current.applyOptions({ visible: showPivots });
      }
      if (pivotR2Ref.current) {
        pivotR2Ref.current.setData(pivots.map(p => ({ time: p.time, value: p.r2 })));
        pivotR2Ref.current.applyOptions({ visible: showPivots });
      }
      if (pivotS1Ref.current) {
        pivotS1Ref.current.setData(pivots.map(p => ({ time: p.time, value: p.s1 })));
        pivotS1Ref.current.applyOptions({ visible: showPivots });
      }
      if (pivotS2Ref.current) {
        pivotS2Ref.current.setData(pivots.map(p => ({ time: p.time, value: p.s2 })));
        pivotS2Ref.current.applyOptions({ visible: showPivots });
      }
    }

    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }

    setIsLoading(false);
  }, [data, showVolume, showEMA, showBollinger, showPivots]);

  // Update SL/TP lines
  useEffect(() => {
    if (slLineRef.current && stopLoss && data.length) {
      const lineData: LineData<Time>[] = data.map(d => ({
        time: d.time as Time,
        value: stopLoss,
      }));
      slLineRef.current.setData(lineData);
    }
  }, [stopLoss, data]);

  useEffect(() => {
    if (tpLineRef.current && takeProfit && data.length) {
      const lineData: LineData<Time>[] = data.map(d => ({
        time: d.time as Time,
        value: takeProfit,
      }));
      tpLineRef.current.setData(lineData);
    }
  }, [takeProfit, data]);

  const currentPrice = data[data.length - 1]?.close || 0;
  const currentEMAValue = emaData[emaData.length - 1]?.value || 0;
  const isAboveEMA = currentPrice >= currentEMAValue;

  return (
    <div className="w-full">
      {/* Fullscreen Exit Button */}
      {isFullscreen && onExitFullscreen && (
        <div className="absolute top-4 right-4 z-50">
          <button
            onClick={onExitFullscreen}
            className="p-2 bg-dark-800 border border-dark-600 rounded-lg hover:bg-dark-700 shadow-lg flex items-center gap-2"
          >
            <X size={20} />
            <span className="text-sm">Exit Fullscreen</span>
          </button>
        </div>
      )}

      {/* Indicator Toggle Buttons - only show if callbacks provided */}
      {(onToggleVolume || onToggleEMA || onToggleBollinger || onTogglePivots) && (
        <div className="flex flex-wrap gap-2 mb-3">
          {onToggleVolume && (
            <button
              onClick={onToggleVolume}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                showVolume
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
                  : 'bg-dark-800 text-gray-400 border border-dark-700'
              }`}
            >
              Volume
            </button>
          )}
          {onToggleEMA && (
            <button
              onClick={onToggleEMA}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                showEMA
                  ? (isAboveEMA ? 'bg-green-500/20 text-green-400 border border-green-500/50' : 'bg-red-500/20 text-red-400 border border-red-500/50')
                  : 'bg-dark-800 text-gray-400 border border-dark-700'
              }`}
            >
              EMA {showEMA && (isAboveEMA ? '(Bullish)' : '(Bearish)')}
            </button>
          )}
          {onToggleBollinger && (
            <button
              onClick={onToggleBollinger}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                showBollinger
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                  : 'bg-dark-800 text-gray-400 border border-dark-700'
              }`}
            >
              Bollinger
            </button>
          )}
          {onTogglePivots && (
            <button
              onClick={onTogglePivots}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                showPivots
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/50'
                  : 'bg-dark-800 text-gray-400 border border-dark-700'
              }`}
            >
              Pivots (H1)
            </button>
          )}
        </div>
      )}

      {/* Chart */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-900/50 z-10">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full rounded-xl overflow-hidden" style={{ height }} />
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-3 text-xs text-gray-400 flex-wrap">
        {showEMA && (
          <div className="flex items-center gap-1">
            <div className={`w-3 h-0.5 ${isAboveEMA ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span>EMA 20 ({isAboveEMA ? 'Above' : 'Below'})</span>
          </div>
        )}
        {showBollinger && (
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-cyan-500 border-dashed"></div>
            <span>BB (20, 2)</span>
          </div>
        )}
        {showPivots && (
          <>
            <div className="flex items-center gap-1">
              <div className="w-3 h-0.5 bg-amber-500"></div>
              <span>PP</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-0.5 bg-green-500"></div>
              <span>R1/R2</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-0.5 bg-red-500"></div>
              <span>S1/S2</span>
            </div>
          </>
        )}
        {stopLoss && (
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-orange-500"></div>
            <span>SL</span>
          </div>
        )}
        {takeProfit && (
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-green-500"></div>
            <span>TP</span>
          </div>
        )}
      </div>
    </div>
  );
}
