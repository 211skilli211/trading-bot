import { Position } from '../types';
import { formatUSD, formatCrypto, formatPercent, getChangeColor } from '../utils/format';
import { TrendingUp, TrendingDown, Beaker } from 'lucide-react';

interface PositionCardProps {
  position: Position;
}

export function PositionCard({ position }: PositionCardProps) {
  const currency = position.currency || 'USD';
  const isPaper = position.isPaper;
  
  return (
    <div className={`bg-dark-800 rounded-xl p-4 border transition-colors ${
      isPaper ? 'border-yellow-500/30 hover:border-yellow-500/50' : 'border-dark-700 hover:border-blue-500/30'
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-2 h-12 rounded-full ${
            position.side === 'LONG' ? 'bg-trade-up' : 'bg-trade-down'
          }`} />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold">{position.symbol}</h3>
              <span className="text-xs px-2 py-0.5 bg-dark-900 rounded text-gray-400">
                {currency}
              </span>
              {isPaper && (
                <span className="text-[10px] px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 rounded flex items-center gap-1">
                  <Beaker size={10} />
                  PAPER
                </span>
              )}
            </div>
            <span className={`text-xs flex items-center gap-1 ${
              position.side === 'LONG' ? 'text-trade-up' : 'text-trade-down'
            }`}>
              {position.side === 'LONG' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {position.side}
            </span>
          </div>
        </div>
        
        <div className="text-right">
          <div className={`font-mono font-medium ${getChangeColor(position.pnl)}`}>
            {formatUSD(position.pnl)}
          </div>
          <div className={`text-xs ${getChangeColor(position.pnlPercent)}`}>
            {formatPercent(position.pnlPercent)}
          </div>
        </div>
      </div>
      
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <div>
          <span className="text-gray-400">Amount</span>
          <div className="font-mono">{formatCrypto(position.amount, currency)}</div>
        </div>
        <div>
          <span className="text-gray-400">Entry</span>
          <div className="font-mono">{formatUSD(position.entryPrice)}</div>
        </div>
        <div>
          <span className="text-gray-400">Current</span>
          <div className="font-mono">{formatUSD(position.currentPrice)}</div>
        </div>
      </div>
    </div>
  );
}
