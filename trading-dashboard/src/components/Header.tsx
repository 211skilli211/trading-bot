import { Menu, TrendingUp, TrendingDown } from 'lucide-react';
import { formatPercent } from '../utils/format';

interface HeaderProps {
  title: string;
  totalPnl?: number;
}

export function Header({ title, totalPnl }: HeaderProps) {
  return (
    <header className="hidden lg:block sticky top-0 z-40 bg-dark-900/95 backdrop-blur border-b border-dark-700">
      <div className="flex items-center justify-between px-4 h-14">
        <div className="flex items-center gap-3">
          <button className="p-2 -ml-2 rounded-lg hover:bg-dark-800">
            <Menu size={24} />
          </button>
          <h1 className="text-lg font-semibold">{title}</h1>
        </div>
        
        {totalPnl !== undefined && (
          <div className={`flex items-center gap-1 ${totalPnl >= 0 ? 'text-trade-up' : 'text-trade-down'}`}>
            {totalPnl >= 0 ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
            <span className="font-mono font-medium">
              {formatPercent(totalPnl)}
            </span>
          </div>
        )}
      </div>
    </header>
  );
}
