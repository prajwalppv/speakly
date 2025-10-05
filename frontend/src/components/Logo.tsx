import { Mic2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface LogoProps {
  size?: 'small' | 'medium' | 'large';
  showText?: boolean;
  className?: string;
}

export default function Logo({ size = 'medium', showText = true, className }: LogoProps) {
  const sizeMap = {
    small: { icon: 20, text: 'text-base' },
    medium: { icon: 28, text: 'text-xl' },
    large: { icon: 40, text: 'text-3xl' },
  };

  const currentSize = sizeMap[size];

  return (
    <motion.div
      className={cn('flex items-center gap-3', className)}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      <motion.div
        className="relative flex items-center justify-center"
        whileHover={{ scale: 1.1, rotate: 5 }}
        whileTap={{ scale: 0.95 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      >
        <motion.div
          className="absolute inset-0 bg-gradient-gold rounded-full blur-md opacity-50"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.5, 0.3, 0.5],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <div className="relative z-10 flex items-center justify-center p-2 rounded-full bg-black-soft border-2 border-gold">
          <Mic2 size={currentSize.icon} className="text-gold" strokeWidth={2.5} />
        </div>
      </motion.div>
      {showText && (
        <motion.span
          className={cn(
            'font-display font-bold bg-gradient-gold bg-clip-text text-transparent',
            currentSize.text
          )}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: 'easeOut' }}
        >
          Speakly
        </motion.span>
      )}
    </motion.div>
  );
}
