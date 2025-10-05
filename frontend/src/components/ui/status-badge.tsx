import { motion } from 'framer-motion';
import { CheckCircle2, Clock, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type Status = 'completed' | 'processing' | 'pending' | 'error';

interface StatusBadgeProps {
  status: Status;
  label?: string;
  className?: string;
}

const statusConfig = {
  completed: {
    icon: CheckCircle2,
    color: 'text-green',
    bg: 'bg-green/10',
    border: 'border-green/30',
    label: 'Completed',
    animate: false,
  },
  processing: {
    icon: Loader2,
    color: 'text-blue',
    bg: 'bg-blue/10',
    border: 'border-blue/30',
    label: 'Processing',
    animate: true,
  },
  pending: {
    icon: Clock,
    color: 'text-gold',
    bg: 'bg-gold/10',
    border: 'border-gold/30',
    label: 'Pending',
    animate: false,
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-500',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    label: 'Error',
    animate: false,
  },
};

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;
  const displayLabel = label || config.label;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        'inline-flex items-center gap-2 px-3 py-1.5 rounded-full',
        'border text-sm font-medium',
        config.bg,
        config.border,
        config.color,
        className
      )}
    >
      {config.animate ? (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        >
          <Icon size={16} />
        </motion.div>
      ) : (
        <Icon size={16} />
      )}
      <span>{displayLabel}</span>
    </motion.div>
  );
}
