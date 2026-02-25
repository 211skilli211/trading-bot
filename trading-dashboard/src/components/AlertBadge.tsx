import { Alert } from '../types';
import { AlertTriangle, Info, CheckCircle } from 'lucide-react';

interface AlertBadgeProps {
  alert: Alert;
  onDismiss?: () => void;
}

const severityConfig = {
  error: { icon: AlertTriangle, color: 'text-red-400 bg-red-500/10 border-red-500/30' },
  warning: { icon: AlertTriangle, color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30' },
  info: { icon: Info, color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' },
  success: { icon: CheckCircle, color: 'text-green-400 bg-green-500/10 border-green-500/30' },
};

export function AlertBadge({ alert, onDismiss }: AlertBadgeProps) {
  const config = severityConfig[alert.severity] || severityConfig.info;
  const Icon = config.icon;
  
  return (
    <div className={`rounded-xl p-4 border ${config.color}`}>
      <div className="flex items-start gap-3">
        <Icon size={20} className="mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <h4 className="font-medium">{alert.title}</h4>
          <p className="text-sm mt-1 opacity-80">{alert.message}</p>
          <span className="text-xs opacity-60 mt-2 block">
            {new Date(alert.timestamp).toLocaleTimeString()}
          </span>
        </div>
        {onDismiss && (
          <button 
            onClick={onDismiss}
            className="text-xs opacity-60 hover:opacity-100"
          >
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}
