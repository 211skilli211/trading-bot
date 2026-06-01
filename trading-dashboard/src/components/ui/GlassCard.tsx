/**
 * GlassCard — Primary container component
 * Caribbean dark glassmorphism card with hover glow effects.
 * 
 * Usage:
 *   <GlassCard>content</GlassCard>
 *   <GlassCard variant="up">profit content</GlassCard>
 *   <GlassCard variant="down">loss content</GlassCard>
 *   <GlassCard padding="sm">compact card</GlassCard>
 */

interface GlassCardProps {
  children: React.ReactNode;
  variant?: 'default' | 'up' | 'down' | 'gold';
  padding?: 'sm' | 'md' | 'lg';
  className?: string;
  onClick?: () => void;
  glow?: boolean;
}

const paddingMap = {
  sm: 'p-3',
  md: 'p-4 md:p-5',
  lg: 'p-5 md:p-6',
};

const variantClasses = {
  default: '',
  up: 'card-up',
  down: 'card-down',
  gold: 'border-l-3 border-l-[#D4AF37]',
};

export function GlassCard({
  children,
  variant = 'default',
  padding = 'md',
  className = '',
  onClick,
  glow = false,
}: GlassCardProps) {
  const baseClasses = [
    'glass-card',
    variantClasses[variant],
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

/* StatBlock — KPI display for dashboard */
interface StatBlockProps {
  label: string;
  value: string | number;
  change?: number;
  prefix?: string;
  suffix?: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'success' | 'danger' | 'gold';
}

export function StatBlock({
  label,
  value,
  change,
  prefix = '',
  suffix = '',
  icon,
  variant = 'default',
}: StatBlockProps) {
  const valueColor = {
    default: 'text-[#F1F5F9]',
    success: 'text-[#00C9A7]',
    danger: 'text-[#EF476F]',
    gold: 'text-[#D4AF37]',
  }[variant];

  return (
    <div className="flex flex-col gap-1">
      <span className="stat-label flex items-center gap-1.5">
        {icon && <span className="text-[#64748B]">{icon}</span>}
        {label}
      </span>
      <span className={`stat-number ${valueColor}`}>
        {prefix}{typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value}{suffix}
      </span>
      {change !== undefined && (
        <span className={change >= 0 ? 'stat-change-up' : 'stat-change-down'}>
          {change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%
        </span>
      )}
    </div>
  );
}

/* ShimmerCard — Loading placeholder */
export function ShimmerCard({ height = 'h-24' }: { height?: string }) {
  return <div className={`shimmer ${height} rounded-xl`} />;
}

/* StatusBadge — Live/Paper/Strategy badges */
interface StatusBadgeProps {
  status: 'live' | 'paper' | 'strategy' | 'success' | 'alert';
  label?: string;
}

const badgeConfig = {
  live: { cls: 'badge-live text-white', defaultLabel: 'LIVE' },
  paper: { cls: 'badge-paper', defaultLabel: 'PAPER' },
  strategy: { cls: 'badge-strategy', defaultLabel: 'ACTIVE' },
  success: { cls: 'badge-success', defaultLabel: 'SUCCESS' },
  alert: { cls: 'badge bg-[#FF6B35] text-white', defaultLabel: 'ALERT' },
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const config = badgeConfig[status];
  return (
    <span className={`badge ${config.cls}`}>
      {config.defaultLabel === 'LIVE' && <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />}
      {label || config.defaultLabel}
    </span>
  );
}

/* Divider — Gradient separator */
export function Divider() {
  return <div className="divider" />;
}

/* PageHeader — Consistent page header with animation */
interface PageHeaderProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageHeader({ title, subtitle, badge, actions }: PageHeaderProps) {
  return (
    <div className="page-enter flex flex-col gap-2 mb-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg md:text-xl font-bold tracking-tight heading-glow">
            {title}
          </h1>
          {badge}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      {subtitle && (
        <p className="text-sm text-[#64748B]">{subtitle}</p>
      )}
    </div>
  );
}

/* EmptyState — When no data is available */
interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="glass-card p-8 flex flex-col items-center justify-center text-center gap-4 min-h-[200px]">
      <div className="text-[#64748B]">{icon}</div>
      <h3 className="text-[#F1F5F9] font-semibold text-base">{title}</h3>
      {description && <p className="text-[#64748B] text-sm max-w-sm">{description}</p>}
      {action}
    </div>
  );
}
