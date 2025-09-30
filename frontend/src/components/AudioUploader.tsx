import { useCallback, useEffect, useMemo, useState } from "react";

import { SessionRecord, UploadResponse, fetchSession, uploadAudio } from "../api";
import "./AudioUploader.css";

type UploadState = "idle" | "uploading" | "success" | "error";

const DEFAULT_MESSAGE = "Select an audio file (WAV, MP3, M4A) to test the pipeline.";

export default function AudioUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [response, setResponse] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<SessionRecord | null>(null);

  const isUploading = state === "uploading";

  const helperMessage = useMemo(() => {
    if (state === "error" && error) {
      return error;
    }

    if (session) {
      const transcription = session.transcriptions[0];
      if (transcription) {
        if (transcription.status === "completed" && transcription.text) {
          return "Transcription completed.";
        }
        if (transcription.status === "error") {
          return transcription.error ?? "Transcription failed.";
        }
        return `Transcription status: ${transcription.status}`;
      }
      return `Session status: ${session.status}`;
    }

    if (state === "success" && response) {
      return `Upload received. Session #${response.session_id ?? "n/a"}.`;
    }

    if (file) {
      return `Ready to upload ${file.name}`;
    }

    return DEFAULT_MESSAGE;
  }, [state, file, error, session]);

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] ?? null;
    setFile(selectedFile);
    setResponse(null);
    setError(null);
    setState("idle");
    setSession(null);
  }, []);

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      if (!file) {
        setError("Please choose an audio file before uploading.");
        setState("error");
        return;
      }

      setState("uploading");
      setError(null);

      try {
        const data = await uploadAudio(file);
        setResponse(data);
        setState("success");
        setSession(null);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Unable to upload audio right now.";
        setError(message);
        setState("error");
      }
    },
    [file]
  );

  useEffect(() => {
    if (!response?.session_id) {
      return;
    }

    let cancelled = false;
    let intervalId: number | null = null;

    const isTerminal = (status: string | undefined | null) =>
      !!status && ["completed", "error", "failed"].includes(status.toLowerCase());

    const poll = async () => {
      try {
        const data = await fetchSession(response.session_id!);
        if (cancelled) return;
        setSession(data);

        const transcriptionStatus = data.transcriptions[0]?.status;
        if (isTerminal(transcriptionStatus) || isTerminal(data.status)) {
          if (intervalId !== null) {
            window.clearInterval(intervalId);
            intervalId = null;
          }
        }
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : "Unable to retrieve session status.";
        setError(message);
      }
    };

    poll();
    intervalId = window.setInterval(poll, 2500);

    return () => {
      cancelled = true;
      if (intervalId !== null) {
        window.clearInterval(intervalId);
      }
    };
  }, [response?.session_id]);

  return (
    <section className="card">
      <header className="card__header">
        <h2>Upload a sample</h2>
        <p>{helperMessage}</p>
      </header>
      <form onSubmit={handleSubmit} className="card__body" aria-live="polite">
        <label className="file-input">
          <span className="file-input__label">{file ? file.name : "Choose audio"}</span>
          <input
            type="file"
            name="audio"
            accept="audio/*"
            onChange={handleFileChange}
            disabled={isUploading}
          />
        </label>
        <button type="submit" disabled={!file || isUploading}>
          {isUploading ? "Uploading..." : "Send to Speakly"}
        </button>
      </form>
      {response && (
        <dl className="card__meta">
          <div>
            <dt>Original file</dt>
            <dd>{response.file_name}</dd>
          </div>
          <div>
            <dt>Stored path</dt>
            <dd>{response.file_path}</dd>
          </div>
          <div>
            <dt>Received at</dt>
            <dd>{new Date(response.received_at).toLocaleString()}</dd>
          </div>
        </dl>
      )}
      {session && (
        <dl className="card__meta">
          <div>
            <dt>Session status</dt>
            <dd>{session.status}</dd>
          </div>
          {session.last_transcribed_at && (
            <div>
              <dt>Last transcribed</dt>
              <dd>{new Date(session.last_transcribed_at).toLocaleString()}</dd>
            </div>
          )}
          {session.transcriptions.length > 0 && (
            <>
              <div>
                <dt>Transcription status</dt>
                <dd>{session.transcriptions[0].status}</dd>
              </div>
              {session.transcriptions[0].text && (
                <div>
                  <dt>Transcript</dt>
                  <dd className="transcript-output">{session.transcriptions[0].text}</dd>
                </div>
              )}
              {session.transcriptions[0].error && (
                <div>
                  <dt>Error</dt>
                  <dd className="transcript-output transcript-output--error">
                    {session.transcriptions[0].error}
                  </dd>
                </div>
              )}
            </>
          )}
        </dl>
      )}
    </section>
  );
}
