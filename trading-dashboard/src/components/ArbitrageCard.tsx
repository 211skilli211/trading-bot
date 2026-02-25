import { ArbitrageOpportunity } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';
import { ArrowRight, Zap } from 'lucide-react';

interface ArbitrageCardProps {
  opportunity: ArbitrageOpportunity;
}

export function ArbitrageCard({ opportunity }: ArbitrageCardProps) {
  const isProfitable = opportunity.profitPercent > 0.3;
  
  return (
    <div className={`rounded-xl p-4 border ${
      isProfitable 
        ? 'bg-green-500/10 border-green-500/30' 
        : 'bg-dark-800 border-dark-700'
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold">{opportunity.symbol}</h3>
          {isProfitable && <Zap size={16} className="text-yellow-400" />}
        </div>
        <span className={`font-mono font-medium ${
          isProfitable ? 'text-green-400' : 'text-gray-400'
        }`}>
          {formatPercent(opportunity.profitPercent)}
        </span>
      </div>
      
      <div className="mt-3 flex items-center justify-between text-sm">
        <div className="text-center">
          <div className="text-xs text-gray-400">Buy</div>
          <div className="font-mono">{opportunity.buyExchange}</div>
          <div className="font-mono text-green-400">
            {formatCurrency(opportunity.buyPrice)}
          </div>
        </div>
        
        <ArrowRight className="text-gray-500" />
        
        <div className="text-center">
          <div className="text-xs text-gray-400">Sell</div>
          <div className="font-mono">{opportunity.sellExchange}</div>
          <div className="font-mono text-red-400">
            {formatCurrency(opportunity.sellPrice)}
          </div>
        </div>
      </div>
      
      {isProfitable && (
        <button className="mt-3 w-full py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors">
          Execute Arbitrage
        </button>
      )}
    </div>
  );
}
