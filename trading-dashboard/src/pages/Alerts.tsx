import { useEffect, useState } from 'react';
import { Header } from '../components/Header';
import { AlertBadge } from '../components/AlertBadge';
import { api } from '../api/client';
import { Alert } from '../types';
import { Bell, Check } from 'lucide-react';

export function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  useEffect(() => {
    async function loadAlerts() {
      try {
        const data = await api.getAlerts();
        setAlerts(data);
      } catch (error) {
        console.error('Failed to load alerts:', error);
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
    <div className="pb-20">
      <Header title="Alerts" />
      
      <div className="p-4 space-y-4">
        {/* Filter Tabs */}
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                filter === 'all' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-dark-800 text-gray-400'
              }`}
            >
              All ({alerts.length})
            </button>
            <button
              onClick={() => setFilter('unread')}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                filter === 'unread' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-dark-800 text-gray-400'
              }`}
            >
              Unread ({unreadCount})
            </button>
          </div>
          
          {unreadCount > 0 && (
            <button 
              onClick={markAllRead}
              className="flex items-center gap-1 text-sm text-blue-400"
            >
              <Check size={16} />
              Mark all read
            </button>
          )}
        </div>

        {/* Alerts List */}
        {filteredAlerts.length > 0 ? (
          <div className="space-y-3">
            {filteredAlerts.map((alert) => (
              <AlertBadge 
                key={alert.id} 
                alert={alert}
                onDismiss={() => setAlerts(alerts.filter(a => a.id !== alert.id))}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <Bell size={48} className="mx-auto mb-4 text-gray-600" />
            <p className="text-gray-400">No alerts</p>
            <p className="text-sm text-gray-500 mt-1">
              {filter === 'unread' ? 'All caught up!' : 'Alerts will appear here'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
