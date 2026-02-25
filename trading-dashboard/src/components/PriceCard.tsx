import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Price } from '../types';
import { CryptoIcon } from './CryptoIcon';
import { formatCurrency, formatPercent, getChangeColor } from '../utils/format';

interface PriceCardProps {
  price: Price;
  onClick?: () => void;
}

export function PriceCard({ price, onClick }: PriceCardProps) {
  const navigate = useNavigate();
  const isUp = (price.change24h || 0) >= 0;
  const volume = price.volume24h || 0;
  
  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      navigate(`/coin/${encodeURIComponent(price.symbol)}`);
    }
  };
  
  return (
    <div 
      onClick={handleClick}
      className="bg-dark-800 rounded-xl p-4 border border-dark-700 active:scale-[0.98] transition-transform cursor-pointer hover:border-blue-500/50"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CryptoIcon symbol={price.symbol} size={40} />
          <div>
            <h3 className="font-semibold text-lg">{price.symbol}</h3>
            <span className="text-xs text-gray-400">{price.exchange}</span>
          </div>
        </div>
        <div className={`flex items-center gap-1 ${getChangeColor(price.change24h || 0)}`}>
          {isUp ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
          <span className="font-mono">{formatPercent(price.change24h || 0)}</span>
        </div>
      </div>
      
      <div className="mt-3 flex items-end justify-between">
        <div>
          <span className="text-2xl font-bold font-mono">
            {formatCurrency(price.price || 0)}
          </span>
        </div>
        
        <div className="text-xs text-gray-400 text-right">
          <div>Vol: {volume >= 1e9 ? (volume / 1e9).toFixed(2) + 'B' : volume >= 1e6 ? (volume / 1e6).toFixed(2) + 'M' : volume.toFixed(2)}</div>
          {price.bid && price.ask && (
            <div className="mt-1">
              Bid: {formatCurrency(price.bid)} / Ask: {formatCurrency(price.ask)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
