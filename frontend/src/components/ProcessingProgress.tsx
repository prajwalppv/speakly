import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, Loader2, AlertCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProcessingStage {
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'error';
  timestamp: string | null;
  error?: string;
}

interface ProcessingStages {
  uploaded?: ProcessingStage;
  transcribing?: ProcessingStage;
  diarizing?: ProcessingStage;
  summarizing?: ProcessingStage;
  extracting_tasks?: ProcessingStage;
  syncing_tasks?: ProcessingStage;
}

interface ProcessingProgressProps {
  stages: ProcessingStages | null;
  sessionStatus: string;
}

interface StageInfo {
  key: keyof ProcessingStages;
  label: string;
  icon: string;
  estimatedSeconds: number;
}

const STAGES: StageInfo[] = [
  { key: 'uploaded', label: 'Upload Complete', icon: '📤', estimatedSeconds: 0 },
  { key: 'transcribing', label: 'Transcribing Audio', icon: '🎙️', estimatedSeconds: 120 },
  { key: 'diarizing', label: 'Identifying Speakers', icon: '👥', estimatedSeconds: 30 },
  { key: 'summarizing', label: 'Generating Summary', icon: '💡', estimatedSeconds: 15 },
  { key: 'extracting_tasks', label: 'Extracting Tasks', icon: '📋', estimatedSeconds: 10 },
  { key: 'syncing_tasks', label: 'Syncing to TickTick', icon: '🔄', estimatedSeconds: 5 },
];

const ProcessingProgress: React.FC<ProcessingProgressProps> = ({ stages, sessionStatus }) => {
  // Don't show if no stages data
  if (!stages) {
    return null;
  }

  const getCurrentStage = (): number => {
    for (let i = 0; i < STAGES.length; i++) {
      const stage = stages[STAGES[i].key];
      if (stage && (stage.status === 'in_progress' || stage.status === 'pending')) {
        return i;
      }
    }
    return STAGES.length;
  };

  const getTimeRemaining = (): string => {
    const currentIdx = getCurrentStage();
    let totalSeconds = 0;
    
    for (let i = currentIdx; i < STAGES.length; i++) {
      totalSeconds += STAGES[i].estimatedSeconds;
    }

    if (totalSeconds < 60) {
      return `~${totalSeconds}s`;
    }
    const minutes = Math.ceil(totalSeconds / 60);
    return `~${minutes} min`;
  };

  const getStageStatus = (stageKey: keyof ProcessingStages): 'pending' | 'in_progress' | 'completed' | 'failed' | 'error' => {
    const stage = stages[stageKey];
    return stage?.status || 'pending';
  };

  const currentStageIdx = getCurrentStage();
  const timeRemaining = getTimeRemaining();
  const isComplete = sessionStatus === 'completed';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-black/30 border border-bone-dim/20 rounded-lg p-4 space-y-4"
    >
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-display font-semibold text-bone flex items-center gap-2">
          {isComplete ? (
            <>
              <CheckCircle2 size={18} className="text-green" />
              Processing Complete!
            </>
          ) : (
            <>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              >
                <Loader2 size={18} className="text-blue" />
              </motion.div>
              Processing...
            </>
          )}
        </h4>
        {!isComplete && currentStageIdx < STAGES.length && (
          <span className="text-xs text-bone-dim flex items-center gap-1">
            <Clock size={12} />
            {timeRemaining} remaining
          </span>
        )}
      </div>

      <div className="space-y-3">
        {STAGES.map((stageInfo, idx) => {
          const status = getStageStatus(stageInfo.key);
          const isActive = idx === currentStageIdx;
          const stage = stages[stageInfo.key];

          return (
            <motion.div
              key={stageInfo.key}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="flex items-start gap-3"
            >
              <div className="flex flex-col items-center">
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-sm border-2 transition-all",
                  status === 'completed' && "bg-green/20 border-green text-green",
                  status === 'in_progress' && "bg-blue/20 border-blue text-blue",
                  status === 'error' && "bg-red-500/20 border-red-500 text-red-500",
                  status === 'pending' && "bg-bone-dim/10 border-bone-dim/30 text-bone-dim"
                )}>
                  {status === 'completed' && <CheckCircle2 size={16} />}
                  {status === 'in_progress' && (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    >
                      <Loader2 size={16} />
                    </motion.div>
                  )}
                  {status === 'error' && <AlertCircle size={16} />}
                  {status === 'pending' && <span>{stageInfo.icon}</span>}
                </div>
                {idx < STAGES.length - 1 && (
                  <div className={cn(
                    "w-0.5 h-6 mt-1 transition-colors",
                    status === 'completed' ? "bg-green/30" : "bg-bone-dim/20"
                  )} />
                )}
              </div>
              
              <div className="flex-1 pt-1">
                <div className={cn(
                  "text-sm font-medium transition-colors",
                  status === 'completed' && "text-green",
                  status === 'in_progress' && "text-blue",
                  status === 'error' && "text-red-500",
                  status === 'pending' && "text-bone-dim"
                )}>
                  {stageInfo.label}
                </div>
                
                {status === 'completed' && stage?.timestamp && (
                  <div className="text-xs text-bone-dim mt-0.5">
                    ✓ {new Date(stage.timestamp).toLocaleTimeString()}
                  </div>
                )}
                
                {status === 'in_progress' && (
                  <div className="text-xs text-blue mt-0.5 flex items-center gap-1">
                    In progress...
                  </div>
                )}
                
                {status === 'error' && stage?.error && (
                  <div className="text-xs text-red-500 mt-0.5 flex items-start gap-1">
                    <AlertCircle size={12} className="mt-0.5" />
                    {stage.error}
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
};

export default ProcessingProgress;
