import { Alert } from '../types';
import { AlertTriangle, Info, CheckCircle, X } from 'lucide-react';

interface AlertBadgeProps {
  alert: Alert;
  onDismiss?: () => void;
}

const severityConfig = {
  error: { icon: AlertTriangle, cls: 'text-[#EF476F] bg-[#EF476F]/8 border-[#EF476F]/20' },
  warning: { icon: AlertTriangle, cls: 'text-[#D4AF37] bg-[#D4AF37]/8 border-[#D4AF37]/20' },
  info: { icon: Info, cls: 'text-[#3B82F6] bg-[#0F4C75]/8 border-[#0F4C75]/20' },
  success: { icon: CheckCircle, cls: 'text-[#00C9A7] bg-[#00C9A7]/8 border-[#00C9A7]/20' },
};

export function AlertBadge({ alert, onDismiss }: AlertBadgeProps) {
  const config = severityConfig[alert.severity] || severityConfig.info;
  const Icon = config.icon;

  return (
    <div className={`rounded-xl p-4 border ${config.cls} transition-colors`}>
      <div className="flex items-start gap-3">
        <Icon size={18} className="mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm text-[#e8ecf1]">{alert.title}</h4>
          <p className="text-xs mt-1 text-[#5a6a7e]">{alert.message}</p>
          <span className="text-[10px] text-[#3d4d60] mt-1.5 block">
            {new Date(alert.timestamp).toLocaleTimeString()}
          </span>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 rounded-md hover:bg-white/[0.04] text-[#5a6a7e] hover:text-[#e8ecf1] transition-colors"
          >
            <X size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
