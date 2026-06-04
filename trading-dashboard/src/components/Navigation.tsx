import { useState, useMemo } from 'react';
import {
  Home, TrendingUp, Wallet, Bell, Settings,
  Bot, Users, Cpu, LineChart, Shield,
  FlaskConical, Target, X, Menu, Zap,
  BarChart3, Search, ChevronRight, Activity
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

/* ============================================================
   Navigation — Redesigned with anti-slop patterns
   - Rounded-square active indicator (not left-border accent)
   - Command palette for advanced pages
   - Bottom nav: 4 core + 1 overflow (not cramped)
   - Grouped sections with hierarchy
   ============================================================ */

interface NavItem {
  path: string;
  icon: typeof Home;
  label: string;
  section: 'core' | 'trading' | 'ai' | 'more';
}

const allNavItems: NavItem[] = [
  { path: '/', icon: Home, label: 'Dashboard', section: 'core' },
  { path: '/prices', icon: TrendingUp, label: 'Prices', section: 'core' },
  { path: '/portfolio', icon: Wallet, label: 'Portfolio', section: 'core' },
  { path: '/alerts', icon: Bell, label: 'Alerts', section: 'core' },
  // Trading
  { path: '/strategies', icon: Target, label: 'Strategies', section: 'trading' },
  { path: '/backtest', icon: FlaskConical, label: 'Backtest', section: 'trading' },
  { path: '/risk', icon: Shield, label: 'Risk', section: 'trading' },
  { path: '/analytics', icon: BarChart3, label: 'Analytics', section: 'trading' },
  // AI / Advanced
  { path: '/zeroclaw', icon: Bot, label: 'ZeroClaw', section: 'ai' },
  { path: '/multi-agent', icon: Users, label: 'Agents', section: 'ai' },
  { path: '/ml', icon: Cpu, label: 'ML & AI', section: 'ai' },
  { path: '/solana', icon: Zap, label: 'Solana', section: 'ai' },
  // More
  { path: '/settings', icon: Settings, label: 'Settings', section: 'more' },
];

const coreItems = allNavItems.filter(i => i.section === 'core');

export function Navigation() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const isActive = (path: string) => location.pathname === path;

  // Filter items for command palette search
  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return allNavItems;
    const q = searchQuery.toLowerCase();
    return allNavItems.filter(i =>
      i.label.toLowerCase().includes(q) || i.path.includes(q)
    );
  }, [searchQuery]);

  const renderNavItem = (item: NavItem, compact = false) => {
    const active = isActive(item.path);
    const Icon = item.icon;

    return (
      <Link
        key={item.path}
        to={item.path}
        onClick={() => setMobileMenuOpen(false)}
        className={[
          'group flex items-center transition-all',
          compact
            ? 'flex-col justify-center w-16 h-full gap-0.5'
            : 'gap-3 px-3 py-2.5 rounded-xl mx-1',
          active
            ? compact
              ? 'text-[#3B82F6]'
              : 'bg-[#0F4C75]/15 text-[#3B82F6]'
            : compact
              ? 'text-[#5a6a7e]'
              : 'text-[#5a6a7e] hover:text-[#e8ecf1] hover:bg-white/[0.03]',
        ].join(' ')}
      >
        <Icon
          size={compact ? 20 : 19}
          strokeWidth={active ? 2.5 : 1.8}
        />
        <span className={[
          'font-medium',
          compact ? 'text-[10px]' : 'text-[0.8rem]',
          active ? 'font-semibold' : '',
        ].join(' ')}>
          {item.label}
        </span>
      </Link>
    );
  };

  return (
    <>
      {/* ========== Mobile Bottom Navigation ========== */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden"
           style={{
             background: 'rgba(9, 13, 20, 0.92)',
             backdropFilter: 'blur(10px)',
             borderTop: '1px solid rgba(30, 50, 70, 0.3)',
           }}>
        <div className="flex justify-around items-center h-14">
          {coreItems.map(item => renderNavItem(item, true))}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="flex flex-col items-center justify-center w-16 h-full text-[#5a6a7e] hover:text-[#e8ecf1] transition-colors"
          >
            <Menu size={20} strokeWidth={1.8} />
            <span className="text-[10px] mt-0.5 font-medium">More</span>
          </button>
        </div>
        {/* Home indicator safe area */}
        <div className="safe-bottom" />
      </nav>

      {/* ========== Desktop Sidebar ========== */}
      <aside className="hidden lg:flex fixed left-0 top-0 h-full w-[224px] z-40 flex-col"
             style={{
               background: 'rgba(9, 13, 20, 0.95)',
               borderRight: '1px solid rgba(30, 50, 70, 0.25)',
             }}>
        {/* Logo */}
        <div className="px-4 pt-5 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#0F4C75]/20 flex items-center justify-center">
              <Activity size={18} className="text-[#3B82F6]" />
            </div>
            <span className="text-[1.15rem] font-bold tracking-tight text-[#e8ecf1]">
              ZeroClaw
            </span>
          </div>
        </div>

        {/* Search trigger */}
        <div className="px-3 mb-2">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[#5a6a7e] text-sm
                       bg-white/[0.03] hover:bg-white/[0.06] transition-colors"
          >
            <Search size={15} />
            <span>Search pages...</span>
            <span className="ml-auto text-xs opacity-40">⌘K</span>
          </button>
        </div>

        {/* Core nav */}
        <div className="px-2 mb-1">
          <div className="px-2 mb-1 text-[0.6rem] font-semibold text-[#3d4d60] uppercase tracking-wider">
            Overview
          </div>
          {allNavItems.filter(i => i.section === 'core').map(item => renderNavItem(item))}
        </div>

        {/* Trading */}
        <div className="px-2 mb-1 mt-3">
          <div className="px-2 mb-1 text-[0.6rem] font-semibold text-[#3d4d60] uppercase tracking-wider">
            Trading
          </div>
          {allNavItems.filter(i => i.section === 'trading').map(item => renderNavItem(item))}
        </div>

        {/* AI / Advanced */}
        <div className="px-2 mb-1 mt-3">
          <div className="px-2 mb-1 text-[0.6rem] font-semibold text-[#3d4d60] uppercase tracking-wider">
            Intelligence
          </div>
          {allNavItems.filter(i => i.section === 'ai').map(item => renderNavItem(item))}
        </div>

        {/* Settings at bottom */}
        <div className="mt-auto px-2 pb-4 pt-3">
          {allNavItems.filter(i => i.section === 'more').map(item => renderNavItem(item))}
        </div>
      </aside>

      {/* ========== Mobile Command Palette (Full-screen overlay) ========== */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-[100] flex flex-col lg:hidden animate-fade-in-up"
          style={{ background: 'rgba(9, 13, 20, 0.97)' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 pt-4 pb-2 safe-top">
            <h2 className="text-lg font-semibold text-[#e8ecf1]">Navigate</h2>
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="p-2 rounded-lg hover:bg-white/[0.06] text-[#5a6a7e] transition-colors"
            >
              <X size={22} />
            </button>
          </div>

          {/* Search */}
          <div className="px-4 py-2">
            <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl
                            bg-white/[0.04] border border-[rgba(30,50,70,0.3)]
                            focus-within:border-[#0F4C75]/40 transition-colors">
              <Search size={16} className="text-[#5a6a7e]" />
              <input
                autoFocus
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search pages..."
                className="flex-1 bg-transparent text-[#e8ecf1] text-sm outline-none placeholder:text-[#3d4d60]"
              />
            </div>
          </div>

          {/* Grouped items */}
          <div className="flex-1 overflow-y-auto no-scrollbar px-4 pb-20">
            {['core', 'trading', 'ai', 'more'].map(section => {
              const sectionItems = filteredItems.filter(i => i.section === section);
              if (sectionItems.length === 0) return null;
              const sectionLabel = {
                core: 'Overview',
                trading: 'Trading',
                ai: 'Intelligence',
                more: 'Settings',
              }[section];

              return (
                <div key={section} className="mb-4">
                  <div className="px-2 mb-1.5 text-[0.6rem] font-semibold text-[#3d4d60] uppercase tracking-wider">
                    {sectionLabel}
                  </div>
                  <div className="space-y-0.5">
                    {sectionItems.map(item => {
                      const active = isActive(item.path);
                      const Icon = item.icon;
                      return (
                        <Link
                          key={item.path}
                          to={item.path}
                          onClick={() => setMobileMenuOpen(false)}
                          className={[
                            'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors',
                            active
                              ? 'bg-[#0F4C75]/15 text-[#3B82F6]'
                              : 'text-[#5a6a7e] hover:text-[#e8ecf1] hover:bg-white/[0.03]',
                          ].join(' ')}
                        >
                          <Icon size={18} strokeWidth={active ? 2.5 : 1.8} />
                          <span className="text-sm font-medium">{item.label}</span>
                          <ChevronRight size={14} className="ml-auto opacity-30" />
                        </Link>
                      );
                    })}
                  </div>
                </div>
              );
            })}

            {filteredItems.length === 0 && (
              <div className="text-center py-12 text-[#5a6a7e]">
                <p className="text-sm">No pages match "{searchQuery}"</p>
              </div>
            )}
          </div>

          {/* Bottom safe area */}
          <div className="safe-bottom" />
        </div>
      )}
    </>
  );
}
