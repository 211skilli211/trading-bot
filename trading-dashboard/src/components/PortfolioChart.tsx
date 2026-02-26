import { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { TrendingUp, TrendingDown, Activity, PieChart, BarChart3, LineChart } from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface PortfolioData {
  equity: number[];
  labels: string[];
  trades: { win: number; loss: number };
  byStrategy: Record<string, number>;
  dailyPnL: number[];
}

export function PortfolioChart() {
  const [activeChart, setActiveChart] = useState<'equity' | 'trades' | 'strategy' | 'daily'>('equity');
  const [data, setData] = useState<PortfolioData>({
    equity: [],
    labels: [],
    trades: { win: 0, loss: 0 },
    byStrategy: {},
    dailyPnL: [],
  });

  useEffect(() => {
    // Generate realistic portfolio data
    const days = 30;
    const equity: number[] = [10000];
    const labels: string[] = [];
    const dailyPnL: number[] = [];
    
    for (let i = 0; i < days; i++) {
      const date = new Date();
      date.setDate(date.getDate() - (days - i));
      labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
      
      const change = (Math.random() - 0.45) * 200;
      dailyPnL.push(change);
      equity.push(equity[equity.length - 1] + change);
    }

    setData({
      equity,
      labels,
      trades: { win: 42, loss: 18 },
      byStrategy: {
        'Arbitrage': 3250,
        'Sniper': 2100,
        'Momentum': 1850,
        'Contrarian': 1200,
        'Grid': 800,
      },
      dailyPnL,
    });
  }, []);

  const equityChartData = {
    labels: data.labels,
    datasets: [
      {
        label: 'Portfolio Value',
        data: data.equity,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
      },
    ],
  };

  const tradeChartData = {
    labels: ['Winning Trades', 'Losing Trades'],
    datasets: [
      {
        data: [data.trades.win, data.trades.loss],
        backgroundColor: ['#22c55e', '#ef4444'],
        borderWidth: 0,
      },
    ],
  };

  const strategyChartData = {
    labels: Object.keys(data.byStrategy),
    datasets: [
      {
        label: 'P&L by Strategy',
        data: Object.values(data.byStrategy),
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(168, 85, 247, 0.8)',
          'rgba(34, 197, 94, 0.8)',
          'rgba(245, 158, 11, 0.8)',
          'rgba(239, 68, 68, 0.8)',
        ],
        borderWidth: 0,
      },
    ],
  };

  const dailyPnLData = {
    labels: data.labels,
    datasets: [
      {
        label: 'Daily P&L',
        data: data.dailyPnL,
        backgroundColor: data.dailyPnL.map(v => v >= 0 ? '#22c55e' : '#ef4444'),
        borderWidth: 0,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: {
          color: '#94a3b8',
          usePointStyle: true,
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
        ticks: {
          color: '#94a3b8',
        },
      },
      y: {
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
        ticks: {
          color: '#94a3b8',
        },
      },
    },
  };

  const totalReturn = ((data.equity[data.equity.length - 1] - 10000) / 10000 * 100).toFixed(2);
  const winRate = (data.trades.win / (data.trades.win + data.trades.loss) * 100).toFixed(1);

  return (
    <div className="bg-dark-800 rounded-xl border border-dark-700 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <Activity size={18} className="text-blue-400" />
          Portfolio Analytics
        </h3>
        
        {/* Chart Toggle */}
        <div className="flex bg-dark-900 rounded-lg p-1">
          <button
            onClick={() => setActiveChart('equity')}
            className={`px-3 py-1.5 rounded text-sm flex items-center gap-1 transition-colors ${
              activeChart === 'equity' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            <LineChart size={14} />
            Equity
          </button>
          <button
            onClick={() => setActiveChart('trades')}
            className={`px-3 py-1.5 rounded text-sm flex items-center gap-1 transition-colors ${
              activeChart === 'trades' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            <PieChart size={14} />
            Win Rate
          </button>
          <button
            onClick={() => setActiveChart('strategy')}
            className={`px-3 py-1.5 rounded text-sm flex items-center gap-1 transition-colors ${
              activeChart === 'strategy' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            <BarChart3 size={14} />
            Strategy
          </button>
          <button
            onClick={() => setActiveChart('daily')}
            className={`px-3 py-1.5 rounded text-sm flex items-center gap-1 transition-colors ${
              activeChart === 'daily' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            <Activity size={14} />
            Daily
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-dark-900 rounded-lg p-3 text-center">
          <div className={`text-2xl font-bold ${parseFloat(totalReturn) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {parseFloat(totalReturn) >= 0 ? '+' : ''}{totalReturn}%
          </div>
          <div className="text-xs text-gray-400">30-Day Return</div>
        </div>
        <div className="bg-dark-900 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-blue-400">{winRate}%</div>
          <div className="text-xs text-gray-400">Win Rate</div>
        </div>
        <div className="bg-dark-900 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-purple-400">
            ${(data.equity[data.equity.length - 1] - 10000).toFixed(0)}
          </div>
          <div className="text-xs text-gray-400">Total P&L</div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        {activeChart === 'equity' && (
          <Line data={equityChartData} options={chartOptions} />
        )}
        {activeChart === 'trades' && (
          <div className="flex items-center justify-center h-full">
            <div className="w-48">
              <Doughnut 
                data={tradeChartData} 
                options={{
                  ...chartOptions,
                  plugins: { ...chartOptions.plugins, legend: { position: 'bottom' } },
                }} 
              />
            </div>
          </div>
        )}
        {activeChart === 'strategy' && (
          <Bar data={strategyChartData} options={chartOptions} />
        )}
        {activeChart === 'daily' && (
          <Bar data={dailyPnLData} options={{...chartOptions, plugins: { ...chartOptions.plugins, legend: { display: false }}}} />
        )}
      </div>
    </div>
  );
}
