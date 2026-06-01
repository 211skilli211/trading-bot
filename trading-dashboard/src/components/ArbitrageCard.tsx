import { ArbitrageOpportunity } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';
import { ArrowRight, Zap } from 'lucide-react';

interface ArbitrageCardProps {
  opportunity: ArbitrageOpportunity;
}

export function ArbitrageCard({ opportunity }: ArbitrageCardProps) {
  const isProfitable = opportunity.profitPercent > 0.3;
  
  return (
    <div className={`glass-card p-4 ${
      isProfitable ? 'border-l-[3px] border-l-[#00C9A7]' : ''
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-sm text-[#e8ecf1]">{opportunity.symbol}</h3>
          {isProfitable && <Zap size={14} className="text-[#D4AF37]" />}
        </div>
        <span className={`mono text-sm font-semibold ${
          isProfitable ? 'text-[#00C9A7]' : 'text-[#5a6a7e]'
        }`}>
          {formatPercent(opportunity.profitPercent)}
        </span>
      </div>

      <div className="mt-2.5 flex items-center justify-between text-xs">
        <div className="text-center">
          <div className="text-[10px] text-[#5a6a7e]">Buy</div>
          <div className="mono text-[#e8ecf1]">{opportunity.buyExchange}</div>
          <div className="mono text-[#00C9A7]">
            {formatCurrency(opportunity.buyPrice)}
          </div>
        </div>

        <ArrowRight className="text-[#3d4d60]" size={14} />

        <div className="text-center">
          <div className="text-[10px] text-[#5a6a7e]">Sell</div>
          <div className="mono text-[#e8ecf1]">{opportunity.sellExchange}</div>
          <div className="mono text-[#EF476F]">
            {formatCurrency(opportunity.sellPrice)}
          </div>
        </div>
      </div>

      {isProfitable && (
        <button className="btn-primary w-full mt-3 text-xs">
          Execute Arbitrage
        </button>
      )}
    </div>
  );
}
