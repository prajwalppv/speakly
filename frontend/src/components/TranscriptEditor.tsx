import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Edit2, Save, X, History, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface TranscriptEditorProps {
  transcriptionId: number;
  initialText: string;
  onSave: (text: string, notes?: string) => Promise<void>;
  onCancel?: () => void;
  renderActions?: (actions: {
    handleEdit: (e: React.MouseEvent) => void;
    loadHistory: (e: React.MouseEvent) => Promise<void>;
    loadingHistory: boolean;
  }) => React.ReactNode;
}

const TranscriptEditor: React.FC<TranscriptEditorProps> = ({
  transcriptionId,
  initialText,
  onSave,
  onCancel,
  renderActions,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [text, setText] = useState(initialText);
  const [notes, setNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [editHistory, setEditHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card collapse
    setText(initialText);
    setIsEditing(true);
  };

  const handleSave = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card collapse
    setIsSaving(true);
    try {
      await onSave(text, notes || undefined);
      setIsEditing(false);
      setNotes("");
    } catch (error) {
      alert("Failed to save changes. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card collapse
    setText(initialText);
    setNotes("");
    setIsEditing(false);
    if (onCancel) {
      onCancel();
    }
  };

  const loadHistory = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card collapse
    setLoadingHistory(true);
    try {
      const response = await fetch(
        `/api/transcriptions/${transcriptionId}/history`,
      );
      const data = await response.json();
      setEditHistory(data);
      setShowHistory(true);
    } catch (error) {
      // Failed to load history - will show empty state
    } finally {
      setLoadingHistory(false);
    }
  };

  const hasChanges = text !== initialText;

  if (isEditing) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-black/50 border border-gold/30 rounded-lg p-4 space-y-4"
      >
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-display font-semibold text-bone flex items-center gap-2">
            <Edit2 size={16} className="text-gold" />
            Editing Transcript
          </h4>
          <div className="flex gap-2">
            <motion.button
              className="px-3 py-1.5 border border-bone-dim text-bone-dim rounded-lg text-sm font-medium hover:bg-white/5 transition-colors disabled:opacity-50"
              onClick={handleCancel}
              disabled={isSaving}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Cancel
            </motion.button>
            <motion.button
              className={cn(
                "px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-all",
                hasChanges && !isSaving
                  ? "bg-gradient-green text-black shadow-lg hover:shadow-green/50"
                  : "bg-black-soft text-bone-dim cursor-not-allowed",
              )}
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              whileHover={hasChanges && !isSaving ? { scale: 1.05 } : {}}
              whileTap={hasChanges && !isSaving ? { scale: 0.95 } : {}}
            >
              {isSaving ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  >
                    <Save size={16} />
                  </motion.div>
                  Saving...
                </>
              ) : (
                <>
                  <Save size={16} />
                  Save Changes
                </>
              )}
            </motion.button>
          </div>
        </div>

        <textarea
          className="w-full bg-black border border-gold/20 rounded-lg p-3 text-bone font-mono text-sm resize-y min-h-[300px] focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          onFocus={(e) => e.stopPropagation()}
          placeholder="Edit transcript text..."
          rows={15}
          autoFocus
        />

        <div className="space-y-2">
          <label
            htmlFor="edit-notes"
            className="text-sm font-medium text-bone-dim"
          >
            Notes (optional):
          </label>
          <input
            id="edit-notes"
            type="text"
            className="w-full bg-black border border-gold/20 rounded-lg px-3 py-2 text-bone text-sm focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
            placeholder="e.g., Fixed speaker names, corrected technical terms"
          />
        </div>

        <AnimatePresence>
          {hasChanges && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="text-sm text-gold flex items-center gap-2"
            >
              💡 Your changes will be saved to the edit history
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  }

  return (
    <div className="space-y-3">
      {renderActions &&
        renderActions({ handleEdit, loadHistory, loadingHistory })}

      <div className="bg-black/30 border border-bone-dim/20 rounded-lg p-4">
        <p className="text-bone text-sm whitespace-pre-wrap">
          {initialText || (
            <span className="text-bone-dim italic">
              No transcription available
            </span>
          )}
        </p>
      </div>

      <AnimatePresence>
        {showHistory && editHistory.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-black/30 border border-gold/20 rounded-lg p-4 space-y-3"
          >
            <h5 className="text-sm font-display font-semibold text-gold flex items-center gap-2">
              <History size={16} />
              Edit History ({editHistory.length})
            </h5>
            <div className="space-y-2">
              {editHistory.map((edit, idx) => (
                <motion.div
                  key={edit.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="bg-black/50 border border-bone-dim/20 rounded-lg p-3 space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-bone-dim">
                      {new Date(edit.created_at).toLocaleString()}
                    </span>
                    <span className="px-2 py-0.5 bg-gold/20 text-gold rounded-full font-medium">
                      {edit.edit_type}
                    </span>
                  </div>
                  {edit.notes && (
                    <div className="text-sm text-bone flex items-start gap-2">
                      <span>💬</span>
                      <span>{edit.notes}</span>
                    </div>
                  )}
                  {idx < editHistory.length - 1 && (
                    <details className="group">
                      <summary className="text-sm text-blue cursor-pointer hover:text-blue-bright flex items-center gap-1">
                        <ChevronDown
                          size={14}
                          className="group-open:rotate-180 transition-transform"
                        />
                        View changes
                      </summary>
                      <div className="mt-2 space-y-2 text-xs">
                        <div className="bg-red-500/10 border border-red-500/20 rounded p-2">
                          <strong className="text-red-500">Before:</strong>
                          <pre className="text-bone-dim mt-1 whitespace-pre-wrap">
                            {edit.previous_text.substring(0, 200)}...
                          </pre>
                        </div>
                        <div className="bg-green/10 border border-green/20 rounded p-2">
                          <strong className="text-green">After:</strong>
                          <pre className="text-bone-dim mt-1 whitespace-pre-wrap">
                            {edit.new_text.substring(0, 200)}...
                          </pre>
                        </div>
                      </div>
                    </details>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default TranscriptEditor;
