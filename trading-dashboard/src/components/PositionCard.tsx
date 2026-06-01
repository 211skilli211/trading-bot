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
    <div className={`glass-card p-4 transition-colors ${
      isPaper ? 'border-l-[3px] border-l-[#D4AF37]' : ''
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-1.5 h-10 rounded-full ${
            position.side === 'LONG' ? 'bg-[#00C9A7]' : 'bg-[#EF476F]'
          }`} />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-sm text-[#e8ecf1]">{position.symbol}</h3>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/[0.04] text-[#5a6a7e]">
                {currency}
              </span>
              {isPaper && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#D4AF37]/10 text-[#D4AF37] flex items-center gap-0.5">
                  <Beaker size={9} />
                  PAPER
                </span>
              )}
            </div>
            <span className={`text-[11px] flex items-center gap-0.5 ${
              position.side === 'LONG' ? 'text-[#00C9A7]' : 'text-[#EF476F]'
            }`}>
              {position.side === 'LONG' ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
              {position.side}
            </span>
          </div>
        </div>

        <div className="text-right">
          <div className={`mono text-sm font-semibold ${getChangeColor(position.pnl)}`}>
            {formatUSD(position.pnl)}
          </div>
          <div className={`text-xs ${getChangeColor(position.pnlPercent)}`}>
            {formatPercent(position.pnlPercent)}
          </div>
        </div>
      </div>

      <div className="mt-2.5 grid grid-cols-3 gap-2 text-[11px]">
        <div>
          <span className="text-[#5a6a7e]">Amount</span>
          <div className="mono text-[#e8ecf1]">{formatCrypto(position.amount, currency)}</div>
        </div>
        <div>
          <span className="text-[#5a6a7e]">Entry</span>
          <div className="mono text-[#e8ecf1]">{formatUSD(position.entryPrice)}</div>
        </div>
        <div>
          <span className="text-[#5a6a7e]">Current</span>
          <div className="mono text-[#e8ecf1]">{formatUSD(position.currentPrice)}</div>
        </div>
      </div>
    </div>
  );
}
