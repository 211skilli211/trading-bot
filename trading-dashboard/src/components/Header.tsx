import { Menu, TrendingUp, TrendingDown, Bell, Bot, Circle } from 'lucide-react';
import { formatPercent } from '../utils/format';
import { StatusBadge } from '../components/ui/GlassCard';

interface HeaderProps {
  title: string;
  totalPnl?: number;
  alertCount?: number;
  isLive?: boolean;
}

export function Header({ title, totalPnl, alertCount, isLive }: HeaderProps) {
  return (
    <header
      className="sticky top-0 z-30 lg:z-40"
      style={{
        background: 'rgba(9, 13, 20, 0.9)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(30, 50, 70, 0.2)',
      }}
    >
      <div className="flex items-center justify-between px-4 h-12 lg:h-14">
        {/* Left: Title + Mode */}
        <div className="flex items-center gap-3">
          {/* Mobile menu trigger area — space for thumb */}
          <div className="lg:hidden w-8" />
          <h1 className="text-[0.95rem] font-semibold text-[#e8ecf1] tracking-tight">{title}</h1>
          {isLive !== undefined && (
            <StatusBadge status={isLive ? 'live' : 'paper'} />
          )}
        </div>

        {/* Right: P&L + Alert bell */}
        <div className="flex items-center gap-3">
          {totalPnl !== undefined && (
            <div className={`flex items-center gap-1 mono text-sm font-semibold ${totalPnl >= 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
              {totalPnl >= 0 ? <TrendingUp size={15} /> : <TrendingDown size={15} />}
              {formatPercent(totalPnl)}
            </div>
          )}
          {alertCount !== undefined && alertCount > 0 && (
            <button className="relative p-2 rounded-lg hover:bg-white/[0.04] transition-colors">
              <Bell size={18} className="text-[#5a6a7e]" />
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-[#EF476F] text-[#e8ecf1] text-[9px] font-bold flex items-center justify-center">
                {alertCount > 9 ? '9+' : alertCount}
              </span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
