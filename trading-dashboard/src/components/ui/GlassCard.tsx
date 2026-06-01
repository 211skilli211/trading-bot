/**
 * GlassCard — Primary container component
 * Caribbean dark glassmorphism with layered depth system.
 * 
 * Depth levels (Perception-First L2):
 *   default — standard card (most content)
 *   elevate — slightly raised (important metrics)
 *   sunken — inset (secondary info)
 *   float — floating overlay (modals, tooltips)
 * 
 * Variants:
 *   default — standard glass
 *   up — green sweep (profit/positive)
 *   down — red sweep (loss/negative)
 *   gold — gold accent (premium/important)
 *   alert — orange accent (warning)
 * 
 * Usage:
 *   <GlassCard>content</GlassCard>
 *   <GlassCard variant="up" elevate>profit metric</GlassCard>
 *   <GlassCard depth="sunken">secondary info</GlassCard>
 */

interface GlassCardProps {
  children: React.ReactNode;
  variant?: 'default' | 'up' | 'down' | 'gold' | 'alert';
  depth?: 'default' | 'elevate' | 'sunken' | 'float';
  padding?: 'sm' | 'md' | 'lg' | 'none';
  className?: string;
  onClick?: () => void;
  glow?: boolean;
}

const paddingMap = {
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-5 md:p-6',
  none: '',
};

const depthShadows = {
  default: '',
  elevate: 'shadow-[0_2px_4px_rgba(0,0,0,0.3),0_8px_24px_rgba(0,0,0,0.2),0_0_1px_rgba(15,76,117,0.1)]',
  sunken: 'shadow-[inset_0_1px_3px_rgba(0,0,0,0.3)] bg-[rgba(9,13,20,0.6)]',
  float: 'shadow-[0_4px_8px_rgba(0,0,0,0.4),0_16px_40px_rgba(0,0,0,0.3),0_0_1px_rgba(15,76,117,0.15)]',
};

const variantClasses = {
  default: '',
  up: 'card-up',
  down: 'card-down',
  gold: 'border-l-[3px] border-l-[#D4AF37]',
  alert: 'border-l-[3px] border-l-[#FF6B35]',
};

export function GlassCard({
  children,
  variant = 'default',
  depth = 'default',
  padding = 'md',
  className = '',
  onClick,
  glow = false,
}: GlassCardProps) {
  const baseClasses = [
    'glass-card',
    variantClasses[variant],
    depthShadows[depth],
    paddingMap[padding],
    glow ? 'animate-glow' : '',
    onClick ? 'cursor-pointer active:scale-[0.98]' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={baseClasses} onClick={onClick}>
      {children}
    </div>
  );
}

/* StatBlock — KPI display with proper hierarchy (Perception L1) */
interface StatBlockProps {
  label: string;
  value: string | number;
  change?: number;
  prefix?: string;
  suffix?: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'success' | 'danger' | 'gold';
  size?: 'sm' | 'md' | 'lg';
  sparkline?: number[];  // Simple sparkline data
}

const sizeMap = {
  sm: 'stat-number-sm',
  md: 'stat-number',
  lg: 'stat-number-lg',
};

export function StatBlock({
  label,
  value,
  change,
  prefix = '',
  suffix = '',
  icon,
  variant = 'default',
  size = 'md',
}: StatBlockProps) {
  const valueColor = {
    default: 'text-[#e8ecf1]',
    success: 'text-[#00C9A7]',
    danger: 'text-[#EF476F]',
    gold: 'text-[#D4AF37]',
  }[variant];

  return (
    <div className="flex flex-col gap-1.5">
      <span className="stat-label flex items-center gap-1.5">
        {icon && <span className="text-[#5a6a7e]">{icon}</span>}
        {label}
      </span>
      <span className={`${sizeMap[size]} ${valueColor}`}>
        {prefix}{typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value}{suffix}
      </span>
      {change !== undefined && (
        <span className={`font-mono text-xs font-semibold ${change >= 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
          {change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%
        </span>
      )}
    </div>
  );
}

/* ShimmerCard — Layout-matched skeleton loader (Interaction Design) */
export function ShimmerCard({
  height = 'h-24',
  lines,
}: {
  height?: string;
  lines?: number;
}) {
  if (lines) {
    return (
      <div className="glass-card p-4 space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="shimmer-text w-full"
            style={{
              width: `${70 + Math.random() * 30}%`,
              marginBottom: i === lines - 1 ? 0 : undefined,
            }}
          />
        ))}
      </div>
    );
  }
  return <div className={`shimmer shimmer-card ${height}`} />;
}

/* StatusBadge — Squared badges (Anti-slop: not pill-shaped) */
interface StatusBadgeProps {
  status: 'live' | 'paper' | 'strategy' | 'success' | 'alert';
  label?: string;
}

const badgeConfig = {
  live: { cls: 'badge-live text-white', defaultLabel: 'LIVE' },
  paper: { cls: 'badge-paper', defaultLabel: 'PAPER' },
  strategy: { cls: 'badge-strategy', defaultLabel: 'ACTIVE' },
  success: { cls: 'badge-success', defaultLabel: 'SUCCESS' },
  alert: { cls: 'badge-alert', defaultLabel: 'ALERT' },
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const config = badgeConfig[status];
  return (
    <span className={`badge ${config.cls}`}>
      {config.defaultLabel === 'LIVE' && (
        <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
      )}
      {label || config.defaultLabel}
    </span>
  );
}

/* Divider — Gradient separator */
export function Divider() {
  return <div className="divider" />;
}

/* PageHeader — Consistent page header with animation (Perception L1-L3) */
interface PageHeaderProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageHeader({ title, subtitle, badge, actions }: PageHeaderProps) {
  return (
    <div className="animate-fade-in-up flex flex-col gap-1.5 mb-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <h1 className="text-lg md:text-xl font-bold tracking-tight text-[#e8ecf1]">
            {title}
          </h1>
          {badge}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      {subtitle && (
        <p className="text-sm text-[#5a6a7e]">{subtitle}</p>
      )}
    </div>
  );
}

/* EmptyState — Composed empty state (not "nothing here") (Interaction Design) */
interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="glass-card p-8 flex flex-col items-center justify-center text-center gap-3 min-h-[180px]">
      <div className="text-[#3d4d60]">{icon}</div>
      <h3 className="text-[#e8ecf1] font-semibold text-[0.95rem]">{title}</h3>
      {description && <p className="text-[#5a6a7e] text-sm max-w-[260px]">{description}</p>}
      {action}
    </div>
  );
}

/* PriceTag — Formatted price with flash animation */
interface PriceTagProps {
  price: number;
  change?: number;
  size?: 'sm' | 'md' | 'lg';
  flash?: 'up' | 'down' | null;
}

export function PriceTag({ price, change, size = 'md', flash }: PriceTagProps) {
  return (
    <div className={[
      'inline-flex items-baseline gap-2',
      flash === 'up' ? 'price-flash-up' : '',
      flash === 'down' ? 'price-flash-down' : '',
    ].join(' ')}>
      <span className={[
        'mono font-bold',
        size === 'sm' ? 'text-sm' : size === 'md' ? 'text-lg' : 'text-2xl',
      ].join(' ')}>
        ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </span>
      {change !== undefined && (
        <span className={`mono text-xs font-semibold ${change >= 0 ? 'text-[#00C9A7]' : 'text-[#EF476F]'}`}>
          {change >= 0 ? '+' : ''}{change.toFixed(2)}%
        </span>
      )}
    </div>
  );
}
