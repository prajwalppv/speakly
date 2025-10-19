import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Mic2, Square } from "lucide-react";
import { cn } from "@/lib/utils";

type RecorderStatus = "idle" | "recording" | "recorded";

interface AudioRecorderProps {
  onRecordingComplete: (file: File) => void;
  onCancel?: () => void;
  className?: string;
}

const formatSeconds = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const secs = (seconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
};

const resolveFileExtension = (mimeType: string) => {
  if (mimeType.includes("audio/mpeg")) return "mp3";
  if (mimeType.includes("audio/ogg")) return "ogg";
  if (mimeType.includes("audio/mp4")) return "m4a";
  if (mimeType.includes("audio/wav")) return "wav";
  if (mimeType.includes("audio/x-wav")) return "wav";
  if (mimeType.includes("audio/webm")) return "webm";
  return "webm";
};

export default function AudioRecorder({
  onRecordingComplete,
  onCancel,
  className,
}: AudioRecorderProps) {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [activeMimeType, setActiveMimeType] = useState("audio/webm");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const recordedBlobRef = useRef<Blob | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  const supportsRecording = useMemo(() => {
    if (typeof navigator === "undefined") {
      return false;
    }
    const hasMediaDevices =
      !!navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === "function";
    return hasMediaDevices && typeof MediaRecorder !== "undefined";
  }, []);

  const cleanupStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startTimer = useCallback(() => {
    stopTimer();
    setElapsedSeconds(0);
    timerRef.current = window.setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
  }, [stopTimer]);

  const setPreview = useCallback((url: string | null) => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    if (url) {
      previewUrlRef.current = url;
    }
    setPreviewUrl(url);
  }, []);

  const resetState = useCallback(() => {
    stopTimer();
    cleanupStream();
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    recordedBlobRef.current = null;
    setPreview(null);
    setElapsedSeconds(0);
    setStatus("idle");
    setError(null);
  }, [cleanupStream, setPreview, stopTimer]);

  useEffect(() => {
    return () => {
      stopTimer();
      cleanupStream();
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }
    };
  }, [cleanupStream, stopTimer]);

  const startRecording = useCallback(async () => {
    if (!supportsRecording) {
      setError("Your browser doesn't support in-app recording.");
      return;
    }

    setError(null);
    setPreview(null);
    recordedBlobRef.current = null;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const preferredMimeTypes = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ];

      let selectedMimeType = "";
      for (const candidate of preferredMimeTypes) {
        try {
          if (!selectedMimeType && MediaRecorder.isTypeSupported(candidate)) {
            selectedMimeType = candidate;
          }
        } catch {
          // Some browsers throw for unsupported types
        }
      }

      const recorder = selectedMimeType
        ? new MediaRecorder(stream, { mimeType: selectedMimeType })
        : new MediaRecorder(stream);

      mediaRecorderRef.current = recorder;
      const effectiveMimeType =
        recorder.mimeType || selectedMimeType || "audio/webm";
      setActiveMimeType(effectiveMimeType);
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        stopTimer();
        cleanupStream();

        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || effectiveMimeType,
        });
        recordedBlobRef.current = blob;
        setPreview(URL.createObjectURL(blob));
        setActiveMimeType(blob.type || effectiveMimeType);
        setStatus("recorded");
      };

      recorder.start();
      startTimer();
      setStatus("recording");
    } catch (err) {
      cleanupStream();
      stopTimer();
      const message =
        err instanceof Error
          ? err.message
          : "We couldn't access the microphone.";
      setError(message);
      setStatus("idle");
    }
  }, [cleanupStream, setPreview, startTimer, stopTimer, supportsRecording]);

  const stopRecording = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const handleUseRecording = useCallback(() => {
    const blob = recordedBlobRef.current;
    if (!blob) {
      setError("Recording not ready yet. Please try again.");
      return;
    }

    const mimeType = blob.type || activeMimeType || "audio/webm";
    const extension = resolveFileExtension(mimeType);
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const fileName = `speakly-recording-${timestamp}.${extension}`;
    const file = new File([blob], fileName, { type: mimeType });

    onRecordingComplete(file);
    resetState();
    if (onCancel) {
      onCancel();
    }
  }, [activeMimeType, onCancel, onRecordingComplete, resetState]);

  const handleCancel = useCallback(() => {
    resetState();
    if (onCancel) {
      onCancel();
    }
  }, [onCancel, resetState]);

  return (
    <div
      className={cn(
        "border border-gold/20 rounded-lg bg-black-soft/80 p-4 space-y-4",
        className,
      )}
    >
      {!supportsRecording && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-900/20 border border-red-900/40 rounded-md px-3 py-2">
          <AlertCircle size={16} />
          <span>Your browser doesn't support recording audio directly.</span>
        </div>
      )}

      {supportsRecording && (
        <>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 text-sm text-red-400 bg-red-900/20 border border-red-900/40 rounded-md px-3 py-2"
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </motion.div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-12 w-12 items-center justify-center rounded-full border-2",
                  status === "recording"
                    ? "border-red-500/60 bg-red-500/20 text-red-300"
                    : "border-gold/60 bg-gold/10 text-gold",
                )}
              >
                {status === "recording" ? (
                  <Square size={22} />
                ) : (
                  <Mic2 size={24} />
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-bone">
                  {status === "recording"
                    ? "Recording in progress"
                    : status === "recorded"
                      ? "Recording ready"
                      : "Ready to capture"}
                </p>
                <p className="text-xs text-bone-dim">
                  {status === "recording"
                    ? "Speak naturally—we’re capturing every word."
                    : status === "recorded"
                      ? "Preview your clip or record again."
                      : "Your mic stays private and secure."}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {status !== "recording" && (
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  onClick={startRecording}
                  className={cn(
                    "px-4 py-2 rounded-lg font-medium transition-all",
                    status === "recorded"
                      ? "border border-gold text-gold hover:bg-gold hover:text-black"
                      : "bg-gradient-blue text-bone shadow hover:shadow-blue/40",
                  )}
                  disabled={!supportsRecording}
                >
                  {status === "recorded" ? "Record Again" : "Start Recording"}
                </motion.button>
              )}
              {status === "recording" && (
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  onClick={stopRecording}
                  className="px-4 py-2 rounded-lg font-medium bg-red-600 text-white shadow hover:bg-red-500"
                >
                  Stop
                </motion.button>
              )}
              <motion.button
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                onClick={handleCancel}
                className="px-4 py-2 rounded-lg font-medium border border-gold/40 text-bone-dim hover:text-bone hover:border-gold/80"
              >
                Close
              </motion.button>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border border-gold/10 rounded-lg px-4 py-3 bg-black/40">
            <div className="flex items-center gap-2 text-sm text-bone-dim">
              <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
              <span>
                {status === "recording" ? "Listening..." : "Standing by"}
              </span>
            </div>
            <div className="text-sm font-mono text-bone">
              {formatSeconds(elapsedSeconds)}
            </div>
            <div className="text-xs uppercase tracking-wide text-bone-dim">
              {activeMimeType.replace("audio/", "")}
            </div>
          </div>

          <AnimatePresence mode="wait">
            {previewUrl && status === "recorded" && (
              <motion.div
                key="preview"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 6 }}
                className="space-y-3 rounded-lg border border-gold/20 bg-black/40 p-4"
              >
                <div className="flex items-center gap-2 text-bone">
                  <CheckCircle2 size={18} className="text-green" />
                  <span className="text-sm font-medium">
                    Preview your voice note
                  </span>
                </div>
                <audio controls src={previewUrl} className="w-full" />
                <div className="flex flex-wrap gap-3">
                  <motion.button
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.96 }}
                    onClick={handleUseRecording}
                    className="flex-1 min-w-[140px] px-4 py-2 rounded-lg font-medium bg-gradient-blue text-bone shadow hover:shadow-blue/40"
                  >
                    Add To Upload Queue
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.96 }}
                    onClick={resetState}
                    className="flex-1 min-w-[140px] px-4 py-2 rounded-lg font-medium border border-gold text-gold hover:bg-gold hover:text-black"
                  >
                    Retake
                  </motion.button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}
