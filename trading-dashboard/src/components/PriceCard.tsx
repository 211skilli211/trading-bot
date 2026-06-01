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
      className="glass-card p-4 active:scale-[0.98] transition-all cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CryptoIcon symbol={price.symbol} size={36} />
          <div>
            <h3 className="font-semibold text-sm text-[#e8ecf1]">{price.symbol}</h3>
            <span className="text-[11px] text-[#5a6a7e]">{price.exchange}</span>
          </div>
        </div>
        <div className={`flex items-center gap-1 mono text-sm ${getChangeColor(price.change24h || 0)}`}>
          {isUp ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
          {formatPercent(price.change24h || 0)}
        </div>
      </div>

      <div className="mt-2.5 flex items-end justify-between">
        <div>
          <span className="text-xl font-bold mono text-[#e8ecf1]">
            {formatCurrency(price.price || 0)}
          </span>
        </div>

        <div className="text-[11px] text-[#5a6a7e] text-right mono">
          <div>Vol: {volume >= 1e9 ? (volume / 1e9).toFixed(2) + 'B' : volume >= 1e6 ? (volume / 1e6).toFixed(2) + 'M' : volume.toFixed(2)}</div>
          {price.bid && price.ask && (
            <div className="mt-0.5">
              Bid: {formatCurrency(price.bid)} / Ask: {formatCurrency(price.ask)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
