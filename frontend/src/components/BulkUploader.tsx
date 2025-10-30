import { useCallback, useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  uploadAudioBulk,
  SessionRecord,
  fetchSession,
  editTranscription,
  regenerateSession,
  deleteSession,
} from "../api";
import TranscriptEditor from "./TranscriptEditor";
import TaskManager from "./TaskManager";
import AudioRecorder from "./AudioRecorder";
import Toast, { ToastType } from "./Toast";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Upload,
  X,
  CheckCircle2,
  AlertCircle,
  Clock,
  Mic2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  RefreshCw,
  Eye,
  Trash2,
  Loader2,
  Check,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadProgress {
  fileName: string;
  status: "pending" | "uploading" | "success" | "error";
  sessionId?: number;
  error?: string;
  session?: SessionRecord;
}

const fileSignature = (file: File) =>
  `${file.name}-${file.size}-${file.lastModified}`;

const TERMINAL_SESSION_STATUSES: Array<SessionRecord["status"]> = [
  "completed",
  "completed_with_warnings",
  "error",
  "awaiting_review",
  "rejected",
];

export default function BulkUploader({
  onUploadComplete,
}: {
  onUploadComplete?: () => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<UploadProgress[]>([]);
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());
  const [toast, setToast] = useState<{
    message: string;
    type: ToastType;
  } | null>(null);
  const [showRecorder, setShowRecorder] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<number | null>(
    null,
  );

  const showToast = useCallback((message: string, type: ToastType) => {
    setToast({ message, type });
  }, []);

  const addFiles = useCallback(
    (incomingFiles: File[]) => {
      if (incomingFiles.length === 0) return;

      const existingSignatures = new Set(files.map(fileSignature));
      const freshFiles = incomingFiles.filter(
        (file) => !existingSignatures.has(fileSignature(file)),
      );

      if (freshFiles.length === 0) {
        showToast("Those files are already queued for upload.", "info");
        return;
      }

      if (freshFiles.length < incomingFiles.length) {
        showToast("Skipped files that were already in your queue.", "info");
      }

      setFiles((prev) => [...prev, ...freshFiles]);
      setProgress((prev) => [
        ...prev,
        ...freshFiles.map((f) => ({
          fileName: f.name,
          status: "pending" as const,
        })),
      ]);
    },
    [files, showToast],
  );

  const resetFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const refreshSession = async (sessionId: number) => {
    try {
      const updatedSession = await fetchSession(sessionId);
      setProgress((prev) =>
        prev.map((item) =>
          item.sessionId === sessionId
            ? { ...item, session: updatedSession }
            : item,
        ),
      );
    } catch (error) {
      // Silently fail refresh
    }
  };

  const handleTranscriptSave = async (
    transcriptionId: number,
    text: string,
    notes: string | null,
  ) => {
    try {
      await editTranscription(transcriptionId, {
        text,
        notes: notes || undefined,
      });
      // Find which session this transcription belongs to and refresh it
      const item = progress.find((p) =>
        p.session?.transcriptions.some((t) => t.id === transcriptionId),
      );
      if (item?.sessionId) {
        await refreshSession(item.sessionId);
      }
      showToast("Transcript saved successfully", "success");
    } catch (error) {
      showToast("Failed to save transcript", "error");
      throw error;
    }
  };

  const handleRegenerate = async (e: React.MouseEvent, sessionId: number) => {
    e.stopPropagation(); // Prevent card collapse

    if (
      !confirm(
        "This will regenerate the summary and tasks from the current transcript. Continue?",
      )
    ) {
      return;
    }

    try {
      await regenerateSession(sessionId);
      showToast("Regenerating summary and tasks...", "info");

      // Poll for updates every 3 seconds for up to 30 seconds
      for (let i = 0; i < 10; i++) {
        await new Promise((resolve) => setTimeout(resolve, 3000));
        await refreshSession(sessionId);
      }

      showToast("Regeneration complete!", "success");
    } catch (error) {
      showToast("Failed to regenerate", "error");
    }
  };

  const handleDeleteSessionRecord = async (sessionId: number) => {
    if (deletingSessionId === sessionId) {
      return;
    }
    if (!confirm("Delete this recording permanently? This cannot be undone.")) {
      return;
    }

    setDeletingSessionId(sessionId);
    try {
      await deleteSession(sessionId);
      setProgress((prev) =>
        prev.filter((item) => item.sessionId !== sessionId),
      );
      showToast("Recording deleted.", "success");
    } catch (error) {
      showToast("Failed to delete recording.", "error");
    } finally {
      setDeletingSessionId(null);
    }
  };

  // Load full session data after upload (includes processing_stages)
  useEffect(() => {
    const loadSessionData = async () => {
      for (const item of progress) {
        if (item.sessionId && item.status === "success") {
          try {
            const sessionData = await fetchSession(item.sessionId);
            setProgress((prev) =>
              prev.map((p) =>
                p.sessionId === item.sessionId
                  ? { ...p, session: sessionData }
                  : p,
              ),
            );
          } catch (error) {
            // Silently fail session load - will retry on next poll
          }
        }
      }
    };

    // Initial load
    loadSessionData();

    // Smart polling: only poll sessions that are still processing
    const hasProcessing = progress.some(
      (p) => p.session && !TERMINAL_SESSION_STATUSES.includes(p.session.status),
    );

    if (!hasProcessing) {
      // No processing sessions - stop polling
      return;
    }

    // Poll every 2 seconds while processing (faster for better UX)
    const interval = setInterval(loadSessionData, 2000);
    return () => clearInterval(interval);
  }, [
    progress
      .map((p) => `${p.sessionId}:${p.session?.status || "none"}`)
      .join(","),
  ]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
      resetFileInput();
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    const filesToUpload = [...files];

    setUploading(true);
    setFiles([]);
    resetFileInput();

    // Mark items currently in-flight as uploading and clear stale errors
    setProgress((prev) =>
      prev.map((p) =>
        p.status === "pending" || p.status === "uploading"
          ? { ...p, status: "uploading" as const, error: undefined }
          : p,
      ),
    );

    try {
      const response = await uploadAudioBulk(filesToUpload);

      // Update progress with results
      const updatedProgress = response.results.map((result) => ({
        fileName: result.file_name,
        status: result.success ? ("success" as const) : ("error" as const),
        sessionId: result.session_id,
        error: result.error,
      }));

      setProgress(updatedProgress);

      // Keep results visible - don't auto-clear!
      // User needs to review what happened
      if (onUploadComplete) {
        onUploadComplete();
      }
    } catch (error) {
      setProgress((prev) =>
        prev.map((p) =>
          p.status === "pending" || p.status === "uploading"
            ? {
                ...p,
                status: "error" as const,
                error: "Upload failed",
              }
            : p,
        ),
      );
    } finally {
      setUploading(false);
    }
  };

  const handleClear = () => {
    setFiles([]);
    setProgress([]);
    resetFileInput();
  };

  const handleUploadMore = () => {
    // Reset for new upload
    setFiles([]);
    setProgress([]);
    resetFileInput();
  };

  const hasResults = progress.length > 0 && !uploading;
  const canUploadMore =
    hasResults &&
    progress.some((p) => p.status === "success" || p.status === "error");

  const toggleCard = (sessionId: number) => {
    setExpandedCards((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sessionId)) {
        newSet.delete(sessionId);
      } else {
        newSet.add(sessionId);
      }
      return newSet;
    });
  };

  const generateTitle = (session?: SessionRecord): string => {
    // Use LLM-generated title if available
    if (session?.description) {
      return session.description;
    }

    // Show processing while waiting for title
    if (session?.transcriptions?.[0]?.text) {
      return "Generating title...";
    }

    return "Processing...";
  };

  // Poll for session updates (only for sessions still processing)
  useEffect(() => {
    if (progress.length === 0) return;

    // Only poll sessions that are uploaded but still processing
    const sessionIds = progress
      .filter(
        (p) =>
          p.sessionId &&
          p.status === "success" &&
          p.session &&
          !TERMINAL_SESSION_STATUSES.includes(p.session.status),
      )
      .map((p) => p.sessionId!);

    if (sessionIds.length === 0) {
      // All sessions completed - stop polling
      return;
    }

    const pollSessions = async () => {
      const updates = await Promise.all(
        sessionIds.map(async (id) => {
          try {
            const session = await fetchSession(id);
            return { sessionId: id, session };
          } catch (error) {
            // Session fetch failed, will be retried
            return null;
          }
        }),
      );

      setProgress((prev) =>
        prev.map((p) => {
          if (!p.sessionId) return p;
          const update = updates.find((u) => u?.sessionId === p.sessionId);
          if (update?.session) {
            return { ...p, session: update.session };
          }
          return p;
        }),
      );
    };

    const sessionIdsKey = progress
      .map((p) => p.sessionId)
      .filter(Boolean)
      .join(",");
    if (!sessionIdsKey) return; // No sessions to poll

    // Poll immediately
    pollSessions();

    // Then poll every 3 seconds
    const interval = setInterval(pollSessions, 3000);

    return () => clearInterval(interval);
  }, [
    progress
      .map((p) => `${p.sessionId}:${p.session?.status || "none"}`)
      .join(","),
  ]);

  const handleRecordingComplete = useCallback(
    (file: File) => {
      addFiles([file]);
      showToast("Recording added to your upload list.", "success");
    },
    [addFiles, showToast],
  );

  return (
    <div className="w-full max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Main Upload Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative bg-gradient-to-br from-black-soft to-black border-2 border-gold rounded-xl p-8 shadow-2xl overflow-hidden"
      >
        {/* Animated background glow */}
        <motion.div
          className="absolute inset-0 bg-gradient-gold opacity-5"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.05, 0.1, 0.05],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        <div className="relative z-10">
          {/* Header */}
          <div className="flex items-center gap-3 mb-2">
            <motion.div
              whileHover={{ scale: 1.1, rotate: 5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <Mic2 size={28} className="text-gold" strokeWidth={2.5} />
            </motion.div>
            <h2 className="text-2xl font-display font-bold bg-gradient-gold bg-clip-text text-transparent">
              Upload Audio
            </h2>
          </div>
          <p className="text-bone-dim text-sm mb-6">
            Drop your audio files here or click to browse • Up to 50 files at
            once
          </p>

          {/* Upload Zone */}
          <motion.div whileHover={{ scale: 1.01 }} className="mb-6">
            <input
              type="file"
              id="bulk-file-input"
              ref={fileInputRef}
              multiple
              accept="audio/*"
              onChange={handleFileSelect}
              className="hidden"
              disabled={uploading}
            />
            <label
              htmlFor="bulk-file-input"
              className={cn(
                "flex flex-col items-center justify-center",
                "border-2 border-dashed border-gold rounded-lg p-12",
                "transition-all duration-300 cursor-pointer",
                "hover:border-gold-bright hover:bg-gold/5",
                uploading && "opacity-50 cursor-not-allowed",
              )}
            >
              <AnimatePresence mode="wait">
                {files.length === 0 ? (
                  <motion.div
                    key="empty"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="flex flex-col items-center gap-4"
                  >
                    <motion.div
                      animate={{ y: [0, -10, 0] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      <Upload
                        size={48}
                        className="text-gold"
                        strokeWidth={1.5}
                      />
                    </motion.div>
                    <span className="text-lg font-medium text-bone">
                      Click to select files or drag & drop
                    </span>
                    <span className="text-sm text-bone-dim">
                      MP3, WAV, M4A, and more (max 50 files)
                    </span>
                  </motion.div>
                ) : (
                  <motion.div
                    key="selected"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="flex flex-col items-center gap-3"
                  >
                    <span className="text-4xl">📎</span>
                    <span className="text-lg font-medium text-bone">
                      {files.length} file{files.length > 1 ? "s" : ""} selected
                    </span>
                    <span className="text-sm text-bone-dim">
                      Click to change selection
                    </span>
                  </motion.div>
                )}
              </AnimatePresence>
            </label>
          </motion.div>

          {/* Optional in-browser recorder */}
          <div className="space-y-3">
            <motion.button
              whileHover={{ scale: uploading ? 1 : 1.03 }}
              whileTap={{ scale: uploading ? 1 : 0.97 }}
              onClick={() => setShowRecorder((prev) => !prev)}
              disabled={uploading}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all",
                "border border-gold text-gold hover:bg-gold hover:text-black",
                uploading &&
                  "opacity-50 cursor-not-allowed hover:bg-transparent hover:text-gold",
              )}
            >
              <Mic2 size={18} />
              {showRecorder ? "Hide Recorder" : "Record a Voice Note"}
            </motion.button>
            <AnimatePresence>
              {showRecorder && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                >
                  <AudioRecorder
                    onRecordingComplete={handleRecordingComplete}
                    onCancel={() => setShowRecorder(false)}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 justify-end">
            <AnimatePresence>
              {files.length > 0 && !uploading && (
                <motion.button
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  onClick={handleClear}
                  className="px-4 py-2 border-2 border-gold text-gold rounded-lg font-medium hover:bg-gold hover:text-black transition-all"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Clear Selection
                </motion.button>
              )}
              {canUploadMore && (
                <motion.button
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  onClick={handleUploadMore}
                  className="px-4 py-2 border-2 border-gold text-gold rounded-lg font-medium hover:bg-gold hover:text-black transition-all"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Upload More Files
                </motion.button>
              )}
            </AnimatePresence>
            <motion.button
              onClick={handleUpload}
              disabled={files.length === 0 || uploading}
              className={cn(
                "px-6 py-2 bg-gradient-blue text-bone rounded-lg font-medium",
                "shadow-lg hover:shadow-blue/50 transition-all",
                "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none",
              )}
              whileHover={files.length > 0 && !uploading ? { scale: 1.05 } : {}}
              whileTap={files.length > 0 && !uploading ? { scale: 0.95 } : {}}
            >
              {uploading ? (
                <span className="flex items-center gap-2">
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  >
                    <Sparkles size={18} />
                  </motion.span>
                  Uploading...
                </span>
              ) : (
                `Process ${files.length} file${files.length !== 1 ? "s" : ""}`
              )}
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Upload Results - Individual Cards Below */}
      <AnimatePresence>
        {progress.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <h3 className="text-lg font-display font-semibold text-bone flex items-center gap-2">
              <span>📊</span>
              Upload Results (
              {progress.filter((p) => p.status === "success").length} of{" "}
              {progress.length} successful)
            </h3>
            <div className="space-y-3">
              {progress.map((item, index) => {
                const isExpanded = item.sessionId
                  ? expandedCards.has(item.sessionId)
                  : false;
                const smartTitle = generateTitle(item.session);
                const hasTranscription =
                  !!item.session?.transcriptions?.[0]?.text;
                const hasSummary = !!item.session?.summary?.text;
                const hasTodos = (item.session?.todos?.length ?? 0) > 0;
                const isProcessing = item.session?.status === "processing";
                const extractionStatus = (
                  item.session?.processing_stages?.extracting_tasks?.status ||
                  ""
                )
                  .toString()
                  .toLowerCase();
                const extractionInProgress =
                  !hasTodos &&
                  hasTranscription &&
                  (["pending", "in_progress"].includes(extractionStatus) ||
                    (!extractionStatus &&
                      ["processing", "pending"].includes(
                        (item.session?.status || "").toLowerCase(),
                      )));
                const extractionFailed =
                  hasTranscription && extractionStatus === "failed";
                const showNoTasksDetected =
                  hasTranscription &&
                  !hasTodos &&
                  !extractionInProgress &&
                  !extractionFailed;

                return (
                  <motion.div
                    key={item.sessionId || `upload-${item.fileName}-${index}`}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.1 }}
                    className={cn(
                      "bg-gradient-to-br from-black-soft to-black border-2 rounded-lg overflow-hidden transition-all",
                      item.status === "success" && "border-green/30",
                      item.status === "error" && "border-red-500/30",
                      item.status === "uploading" && "border-blue/30",
                      item.status === "pending" && "border-gold/30",
                      item.sessionId &&
                        "cursor-pointer hover:shadow-lg hover:shadow-gold/20",
                    )}
                    onClick={() => item.sessionId && toggleCard(item.sessionId)}
                    whileHover={item.sessionId ? { scale: 1.01 } : {}}
                  >
                    <div className="p-4 flex items-center gap-4">
                      <span className="text-3xl">
                        {item.status === "pending" && "⏱️"}
                        {item.status === "uploading" && "⏳"}
                        {item.status === "error" && "❌"}
                        {item.status === "success" &&
                          item.session?.status === "completed" &&
                          "✅"}
                        {item.status === "success" &&
                          item.session?.status === "processing" &&
                          "⏳"}
                        {item.status === "success" &&
                          item.session?.status === "error" &&
                          "❌"}
                        {item.status === "success" && !item.session && "⏳"}
                      </span>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-display font-semibold text-bone truncate">
                          {smartTitle}
                        </h4>
                        <p className="text-sm text-bone-dim truncate">
                          {item.fileName}
                        </p>
                        <span
                          className={cn(
                            "text-xs font-medium inline-block mt-1",
                            item.status === "success" &&
                              item.session?.status === "completed" &&
                              "text-green",
                            item.status === "success" &&
                              item.session?.status === "processing" &&
                              "text-blue",
                            item.status === "error" && "text-red-500",
                            item.status === "pending" && "text-gold",
                          )}
                        >
                          {item.status === "pending" && "Waiting..."}
                          {item.status === "uploading" && "Uploading..."}
                          {item.status === "error" && "Upload Failed"}
                          {item.status === "success" &&
                            item.session?.status === "completed" &&
                            "✅ Complete"}
                          {item.status === "success" &&
                            item.session?.status === "processing" &&
                            "⏳ Processing..."}
                          {item.status === "success" &&
                            item.session?.status === "error" &&
                            "❌ Error"}
                          {item.status === "success" &&
                            !item.session &&
                            "⏳ Starting..."}
                        </span>
                      </div>
                      {item.sessionId && (
                        <motion.span
                          className="text-gold text-xl"
                          animate={{ rotate: isExpanded ? 90 : 0 }}
                        >
                          ▶
                        </motion.span>
                      )}
                    </div>
                    {item.sessionId && isExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="border-t border-gold/20 bg-black/30 p-4 space-y-4"
                      >
                        <div className="flex items-center gap-2 text-sm">
                          <span className="text-bone-dim">Session ID:</span>
                          <span className="text-gold font-mono">
                            #{item.sessionId}
                          </span>
                        </div>

                        {/* Session Status */}
                        {item.session && (
                          <div className="flex items-center gap-2">
                            <span
                              className={cn(
                                "px-3 py-1 rounded-full text-sm font-medium",
                                item.session.status === "completed" &&
                                  "bg-green/20 text-green border border-green/30",
                                item.session.status ===
                                  "completed_with_warnings" &&
                                  "bg-amber-500/20 text-amber-100 border border-amber-500/30",
                                item.session.status === "processing" &&
                                  "bg-blue/20 text-blue border border-blue/30",
                                item.session.status === "awaiting_review" &&
                                  "bg-amber-500/20 text-amber-100 border border-amber-400/30",
                                item.session.status === "rejected" &&
                                  "bg-purple-500/20 text-purple-100 border border-purple-400/30",
                                item.session.status === "error" &&
                                  "bg-red-500/20 text-red-500 border border-red-500/30",
                              )}
                            >
                              {item.session.status === "completed" && "✅"}
                              {item.session.status ===
                                "completed_with_warnings" && "⚠️"}
                              {item.session.status === "processing" && "⏳"}
                              {item.session.status === "awaiting_review" &&
                                "👀"}
                              {item.session.status === "rejected" && "🚫"}
                              {item.session.status === "error" && "❌"}{" "}
                              {item.session.status.replace(/_/g, " ")}
                            </span>
                            <motion.button
                              onClick={(e) => {
                                e.stopPropagation();
                                if (item.sessionId) {
                                  handleDeleteSessionRecord(item.sessionId);
                                }
                              }}
                              disabled={deletingSessionId === item.sessionId}
                              className={cn(
                                "px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 border border-red-500/40 bg-red-500/10 text-red-200 hover:bg-red-500/20 transition-all",
                                deletingSessionId === item.sessionId &&
                                  "opacity-60 cursor-wait",
                              )}
                              whileHover={
                                deletingSessionId === item.sessionId
                                  ? {}
                                  : { scale: 1.05 }
                              }
                              whileTap={
                                deletingSessionId === item.sessionId
                                  ? {}
                                  : { scale: 0.95 }
                              }
                            >
                              {deletingSessionId === item.sessionId ? (
                                <Loader2 size={12} className="animate-spin" />
                              ) : (
                                <Trash2 size={12} />
                              )}
                              Delete
                            </motion.button>
                          </div>
                        )}

                        {/* Processing Progress - Show status */}
                        {item.session &&
                          item.session.status === "processing" && (
                            <div className="flex items-center gap-2 text-blue text-sm">
                              <Clock size={16} />
                              <span>Processing your audio...</span>
                            </div>
                          )}
                        {item.session &&
                          item.session.status === "awaiting_review" && (
                            <div className="flex items-center gap-2 text-amber-200 text-sm">
                              <Eye size={16} />
                              <span>
                                Waiting for you to review and approve this
                                recording.
                              </span>
                            </div>
                          )}

                        {/* Transcription */}
                        <div className="space-y-2">
                          <h5 className="text-sm font-display font-semibold text-bone flex items-center gap-2">
                            <span>📝</span> Transcription
                          </h5>
                          {hasTranscription &&
                          item.session &&
                          item.session.transcriptions?.[0] ? (
                            <TranscriptEditor
                              transcriptionId={
                                item.session.transcriptions[0].id
                              }
                              initialText={
                                item.session.transcriptions[0].text || ""
                              }
                              onSave={(text: string, notes?: string) =>
                                handleTranscriptSave(
                                  item.session!.transcriptions[0].id,
                                  text,
                                  notes || null,
                                )
                              }
                            />
                          ) : (
                            <div className="flex items-center gap-2 text-sm text-bone-dim">
                              <Clock size={16} />
                              <span>Transcribing audio...</span>
                            </div>
                          )}
                        </div>

                        {/* Summary */}
                        <div className="space-y-2">
                          <h5 className="text-sm font-display font-semibold text-bone flex items-center gap-2">
                            <span>✨</span> AI Summary
                          </h5>
                          {hasSummary && item.session?.summary?.text ? (
                            <div className="prose prose-sm prose-invert max-w-none bg-black/50 p-3 rounded-lg border border-green/20">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {item.session.summary.text}
                              </ReactMarkdown>
                            </div>
                          ) : hasTranscription ? (
                            <div className="flex items-center gap-2 text-sm text-bone-dim">
                              <Clock size={16} />
                              <span>Generating summary...</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2 text-sm text-bone-dim">
                              <Clock size={16} />
                              <span>Waiting for transcription...</span>
                            </div>
                          )}
                        </div>

                        {/* TODOs */}
                        <div className="space-y-2">
                          <h5 className="text-sm font-display font-semibold text-bone flex items-center gap-2">
                            <span>✅</span> Tasks
                          </h5>
                          {hasTodos ? (
                            <TaskManager
                              sessionId={item.sessionId!}
                              todos={item.session?.todos || []}
                              onUpdate={() => refreshSession(item.sessionId!)}
                            />
                          ) : extractionInProgress ? (
                            <div className="flex items-center gap-2 text-sm text-bone-dim">
                              <Clock size={16} />
                              <span>Extracting tasks...</span>
                            </div>
                          ) : extractionFailed ? (
                            <div className="flex items-center gap-2 text-sm text-red-400">
                              <AlertCircle size={16} />
                              <span>Task extraction failed.</span>
                            </div>
                          ) : showNoTasksDetected ? (
                            <div className="flex items-center gap-2 text-sm text-bone-dim">
                              <Check size={16} />
                              <span>No tasks detected in this recording.</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2 text-sm text-bone-dim">
                              <Clock size={16} />
                              <span>Waiting for transcription...</span>
                            </div>
                          )}
                        </div>

                        {/* Regenerate Button */}
                        {hasTranscription && (
                          <motion.div
                            className="pt-2 space-y-2"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                          >
                            <motion.button
                              className="w-full px-4 py-2 bg-gradient-blue text-bone rounded-lg font-medium hover:shadow-lg hover:shadow-blue/50 transition-all flex items-center justify-center gap-2"
                              onClick={(e) =>
                                handleRegenerate(e, item.sessionId!)
                              }
                              disabled={!item.sessionId}
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                            >
                              <RefreshCw size={18} />
                              Regenerate Summary & Tasks
                            </motion.button>
                            <p className="text-xs text-bone-dim text-center">
                              💡 Use this after editing the transcript to get
                              fresh AI insights
                            </p>
                          </motion.div>
                        )}
                      </motion.div>
                    )}
                    {item.error && (
                      <div className="px-4 pb-4 flex items-center gap-2 text-red-500">
                        <span>⚠️</span>
                        <span className="text-sm">{item.error}</span>
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toast Notifications */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
