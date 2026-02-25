import { useState } from 'react';
import { 
  Home, TrendingUp, Wallet, Bell, Settings, 
  Bot, Users, Cpu, LineChart, Shield, 
  FlaskConical, Target, X, Menu, Zap,
  Sparkles, BarChart3
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const mainNavItems = [
  { path: '/', icon: Home, label: 'Dashboard' },
  { path: '/prices', icon: TrendingUp, label: 'Prices' },
  { path: '/portfolio', icon: Wallet, label: 'Portfolio' },
  { path: '/alerts', icon: Bell, label: 'Alerts' },
];

const advancedNavItems = [
  { path: '/zeroclaw', icon: Bot, label: 'ZeroClaw AI' },
  { path: '/multi-agent', icon: Users, label: 'Multi-Agent' },
  { path: '/strategies', icon: Target, label: 'Strategies' },
  { path: '/ml', icon: Cpu, label: 'ML & AI' },
  { path: '/solana', icon: Zap, label: 'Sol Sniper' },
  { path: '/backtest', icon: FlaskConical, label: 'Backtest' },
  { path: '/risk', icon: Shield, label: 'Risk Mgmt' },
  { path: '/analytics', icon: BarChart3, label: 'Analytics' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export function Navigation() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  const isActive = (path: string) => location.pathname === path;

  return (
    <>
      {/* Mobile Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-dark-800 border-t border-dark-700 safe-area-pb z-40 lg:hidden">
        <div className="flex justify-around items-center h-16">
          {mainNavItems.map(({ path, icon: Icon, label }) => (
            <Link
              key={path}
              to={path}
              className={`flex flex-col items-center justify-center w-16 h-full ${
                isActive(path) ? 'text-blue-400' : 'text-gray-400'
              }`}
            >
              <Icon size={22} strokeWidth={isActive(path) ? 2.5 : 2} />
              <span className="text-[10px] mt-0.5">{label}</span>
            </Link>
          ))}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="flex flex-col items-center justify-center w-16 h-full text-gray-400"
          >
            <Menu size={22} />
            <span className="text-[10px] mt-0.5">More</span>
          </button>
        </div>
      </nav>

      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex fixed left-0 top-0 h-full w-64 bg-dark-800 border-r border-dark-700 z-40 flex-col">
        <div className="p-4 border-b border-dark-700">
          <div className="flex items-center gap-2">
            <Sparkles className="text-blue-400" size={24} />
            <span className="text-xl font-bold">ZeroClaw</span>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto py-4">
          <div className="px-3 mb-2 text-xs font-semibold text-gray-500 uppercase">Main</div>
          {mainNavItems.map(({ path, icon: Icon, label }) => (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-4 py-3 mx-2 rounded-lg transition-colors ${
                isActive(path) 
                  ? 'bg-blue-600/20 text-blue-400 border-l-2 border-blue-400' 
                  : 'text-gray-400 hover:bg-dark-700 hover:text-white'
              }`}
            >
              <Icon size={20} />
              <span>{label}</span>
            </Link>
          ))}
          
          <div className="px-3 mt-6 mb-2 text-xs font-semibold text-gray-500 uppercase">Advanced</div>
          {advancedNavItems.map(({ path, icon: Icon, label }) => (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-4 py-3 mx-2 rounded-lg transition-colors ${
                isActive(path) 
                  ? 'bg-blue-600/20 text-blue-400 border-l-2 border-blue-400' 
                  : 'text-gray-400 hover:bg-dark-700 hover:text-white'
              }`}
            >
              <Icon size={20} />
              <span>{label}</span>
            </Link>
          ))}
        </div>
      </aside>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="absolute right-0 top-0 h-full w-72 bg-dark-800 shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-dark-700">
              <span className="text-lg font-bold">Menu</span>
              <button 
                onClick={() => setMobileMenuOpen(false)}
                className="p-2 rounded-lg hover:bg-dark-700"
              >
                <X size={24} />
              </button>
            </div>
            
            <div className="overflow-y-auto h-[calc(100%-70px)]">
              <div className="p-2">
                <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase">Main</div>
                {[...mainNavItems, ...advancedNavItems].map(({ path, icon: Icon, label }) => (
                  <Link
                    key={path}
                    to={path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive(path) 
                        ? 'bg-blue-600/20 text-blue-400' 
                        : 'text-gray-400 hover:bg-dark-700'
                    }`}
                  >
                    <Icon size={20} />
                    <span>{label}</span>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
