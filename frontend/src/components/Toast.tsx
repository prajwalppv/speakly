import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastProps {
  message: string;
  type: ToastType;
  duration?: number;
  onClose: () => void;
}

const toastConfig = {
  success: {
    icon: CheckCircle2,
    bg: 'bg-green/20',
    border: 'border-green',
    text: 'text-green',
  },
  error: {
    icon: XCircle,
    bg: 'bg-red-500/20',
    border: 'border-red-500',
    text: 'text-red-500',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-gold/20',
    border: 'border-gold',
    text: 'text-gold',
  },
  info: {
    icon: Info,
    bg: 'bg-blue/20',
    border: 'border-blue',
    text: 'text-blue',
  },
};

const Toast: React.FC<ToastProps> = ({ message, type, duration = 3000, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const config = toastConfig[type];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: -50, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      className={cn(
        'fixed top-4 right-4 z-50',
        'flex items-center gap-3 p-4 rounded-lg',
        'border-2 backdrop-blur-xl',
        'shadow-2xl min-w-[300px] max-w-md',
        config.bg,
        config.border
      )}
    >
      <Icon size={24} className={config.text} />
      <div className="flex-1 text-bone font-medium">{message}</div>
      <motion.button
        onClick={onClose}
        className={cn('p-1 rounded-full hover:bg-white/10 transition-colors', config.text)}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
      >
        <X size={18} />
      </motion.button>
    </motion.div>
  );
};

export default Toast;
