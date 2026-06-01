import { useEffect, useState } from 'react';
import { Header } from '../components/Header';
import { AlertBadge } from '../components/AlertBadge';
import { api } from '../api/client';
import { Alert } from '../types';
import { GlassCard, PageHeader, EmptyState, StatusBadge } from '../components/ui/GlassCard';
import { Bell, Check, CheckCheck, Filter } from 'lucide-react';

export function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAlerts() {
      try {
        const data = await api.getAlerts();
        setAlerts(data);
      } catch (error) {
        console.error('Failed to load alerts:', error);
      } finally {
        setLoading(false);
      }
    }
    loadAlerts();
  }, []);

  const filteredAlerts = filter === 'unread'
    ? alerts.filter(a => !a.read)
    : alerts;

  const unreadCount = alerts.filter(a => !a.read).length;

  const markAllRead = () => {
    setAlerts(alerts.map(a => ({ ...a, read: true })));
  };

  return (
    <div className="pb-20 lg:pb-6 lg:pl-[224px]">
      <Header title="Alerts" alertCount={unreadCount} />

      <div className="p-4 max-w-[960px] mx-auto">
        <PageHeader
          title="Alerts"
          subtitle={`${alerts.length} total · ${unreadCount} unread`}
          badge={unreadCount > 0 ? <StatusBadge status="alert" label={`${unreadCount} new`} /> : null}
          actions={
            unreadCount > 0 && (
              <button onClick={markAllRead} className="btn-ghost text-xs flex items-center gap-1.5">
                <CheckCheck size={14} />
                Mark all read
              </button>
            )
          }
        />

        {/* Filter tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setFilter('all')}
            className={[
              'px-4 py-2 rounded-xl text-sm font-medium transition-colors',
              filter === 'all'
                ? 'bg-[#0F4C75]/15 text-blue-400'
                : 'text-[#5a6a7e] hover:text-[#e8ecf1]',
            ].join(' ')}
          >
            All ({alerts.length})
          </button>
          <button
            onClick={() => setFilter('unread')}
            className={[
              'px-4 py-2 rounded-xl text-sm font-medium transition-colors',
              filter === 'unread'
                ? 'bg-[#0F4C75]/15 text-blue-400'
                : 'text-[#5a6a7e] hover:text-[#e8ecf1]',
            ].join(' ')}
          >
            Unread ({unreadCount})
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="space-y-3">
            <ShimmerCard lines={2} />
            <ShimmerCard lines={2} />
            <ShimmerCard lines={2} />
          </div>
        ) : filteredAlerts.length > 0 ? (
          <div className="space-y-2">
            {filteredAlerts.map((alert) => (
              <AlertBadge key={alert.id} alert={alert} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Bell size={32} />}
            title={filter === 'unread' ? 'All caught up' : 'No alerts yet'}
            description={filter === 'unread'
              ? 'No unread alerts — you\'re all set!'
              : 'Alerts will appear here when the bot detects events.'}
          />
        )}
      </div>
    </div>
  );
}

/* Inline shimmer helper for loading state */
function ShimmerCard({ lines }: { lines: number }) {
  return (
    <div className="glass-card p-4 space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="shimmer-text"
          style={{ width: `${70 + Math.random() * 30}%` }}
        />
      ))}
    </div>
  );
}
