import { useCallback, useEffect, useMemo, useState } from "react";

import {
  SessionRecord,
  UploadResponse,
  fetchSession,
  fetchSessions,
  uploadAudio,
} from "../api";
import "./AudioUploader.css";

type UploadState = "idle" | "uploading" | "success" | "error";

type SessionFilters = {
  speaker: string;
  hasPj: boolean;
  q: string;
};

const DEFAULT_MESSAGE = "Select an audio file (WAV, MP3, M4A) to test the pipeline.";

function formatDuration(ms: number | null): string {
  if (!ms) return "";
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export default function AudioUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [response, setResponse] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [filters, setFilters] = useState<SessionFilters>({ speaker: "", hasPj: false, q: "" });
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);

  const isUploading = state === "uploading";

  const helperMessage = useMemo(() => {
    if (state === "error" && error) {
      return error;
    }

    if (session) {
      const transcription = session.transcriptions[0];
      if (transcription) {
        if (session.summary?.text && transcription.status === "completed") {
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
      if (response.developer_message) {
        return `${response.developer_message} (session #${response.session_id ?? "n/a"})`;
      }
      return `Upload received. Session #${response.session_id ?? "n/a"}.`;
    }

    if (file) {
      return `Ready to upload ${file.name}`;
    }

    return DEFAULT_MESSAGE;
  }, [state, file, error, session, response]);

  const loadSessions = useCallback(
    async (activeFilters: SessionFilters) => {
      setSessionsLoading(true);
      try {
        const payload = await fetchSessions({
          q: activeFilters.q || undefined,
          speaker: activeFilters.speaker || undefined,
          has_pj: activeFilters.hasPj ? true : undefined,
        });
        setSessions(payload);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to load sessions.";
        setError(message);
      } finally {
        setSessionsLoading(false);
      }
    },
    []
  );

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
        if (data.session_id) {
          setSelectedSessionId(data.session_id);
        }
        loadSessions(filters);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Unable to upload audio right now.";
        setError(message);
        setState("error");
      }
    },
    [file, filters, loadSessions]
  );

  useEffect(() => {
    loadSessions(filters);
  }, [filters, loadSessions]);

  useEffect(() => {
    if (!selectedSessionId) {
      return;
    }

    let cancelled = false;
    const load = async () => {
      try {
        const data = await fetchSession(selectedSessionId);
        if (!cancelled) {
          setSession(data);
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error ? err.message : "Unable to retrieve session.";
          setError(message);
        }
      }
    };

    load();
    const intervalId = window.setInterval(load, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [selectedSessionId, response?.session_status]);

  const handleSelectSession = useCallback((sessionId: number) => {
    setSelectedSessionId(sessionId);
  }, []);

  return (
    <div className="layout">
      <main className="layout__content">
        <header className="layout__header">
          <h1>Speakly: Phase 3 Preview</h1>
          <p>
            Upload an audio file or pick an existing session to see diarization, PJ detection,
            summaries, and actionable TODOs generated via the Ollama pipeline.
          </p>
        </header>

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
              {response.developer_message && (
                <div>
                  <dt>Developer</dt>
                  <dd className="developer-note">{response.developer_message}</dd>
                </div>
              )}
            </dl>
          )}
        </section>

        {session && (
          <section className="card session-detail">
            <header className="card__header">
              <h2>Session #{session.id}</h2>
              <p>
                Status: <strong>{session.status}</strong>{" "}
                {session.has_pj ? "• PJ detected" : ""}
              </p>
            </header>
            <div className="session-detail__grid">
              <div className="session-detail__column">
                <h3>Summary</h3>
                <p className="session-detail__summary">
                  {session.summary?.text ?? "Waiting for summarisation."}
                </p>
                <h3>Todos ({session.todo_count})</h3>
                {session.todos.length === 0 ? (
                  <p className="session-detail__empty">No todos yet.</p>
                ) : (
                  <ul className="session-todo-list">
                    {session.todos.map((todo) => (
                      <li key={todo.id}>
                        <div>
                          <span className="todo-title">{todo.title}</span>
                          {todo.due_hint && <small> – {todo.due_hint}</small>}
                        </div>
                        {todo.source_excerpt && (
                          <blockquote>{todo.source_excerpt}</blockquote>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="session-detail__column">
                <h3>Speakers</h3>
                {session.speaker_segments.length === 0 ? (
                  <p className="session-detail__empty">No diarization data.</p>
                ) : (
                  <ul className="speaker-list">
                    {session.speaker_segments.map((segment) => (
                      <li key={segment.id} className={segment.is_pj ? "speaker-list__item--pj" : ""}>
                        <span className="speaker-label">
                          {segment.speaker_profile || segment.speaker_label || "Speaker"}
                        </span>
                        <span className="speaker-timing">
                          {formatDuration(segment.start_ms)} – {formatDuration(segment.end_ms)}
                        </span>
                        {segment.is_pj && <span className="speaker-tag">PJ</span>}
                      </li>
                    ))}
                  </ul>
                )}
                <h3>Transcriptions</h3>
                <ul className="transcription-list">
                  {session.transcriptions.map((transcription) => (
                    <li key={transcription.id}>
                      <div className="transcription-list__header">
                        <span>{transcription.provider}</span>
                        <span className={`status status--${transcription.status}`}>
                          {transcription.status}
                        </span>
                      </div>
                      <p>{transcription.text ?? "Awaiting transcript."}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        )}
      </main>

      <aside className="layout__sidebar">
        <section className="card">
          <header className="card__header">
            <h2>Browse Sessions</h2>
            <p>Filter by speaker, keyword, or PJ presence.</p>
          </header>
          <div className="filters">
            <label>
              <span>Search</span>
              <input
                type="search"
                value={filters.q}
                placeholder="Search transcript text..."
                onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))}
              />
            </label>
            <label>
              <span>Speaker</span>
              <input
                type="search"
                value={filters.speaker}
                placeholder="Speaker label or name"
                onChange={(event) =>
                  setFilters((prev) => ({ ...prev, speaker: event.target.value }))
                }
              />
            </label>
            <label className="filter-checkbox">
              <input
                type="checkbox"
                checked={filters.hasPj}
                onChange={(event) =>
                  setFilters((prev) => ({ ...prev, hasPj: event.target.checked }))
                }
              />
              <span>Only sessions with PJ</span>
            </label>
          </div>
          <div className="session-list" aria-busy={sessionsLoading}>
            {sessionsLoading && <p>Loading sessions…</p>}
            {!sessionsLoading && sessions.length === 0 && <p>No sessions yet.</p>}
            {!sessionsLoading && sessions.length > 0 && (
              <ul>
                {sessions.map((item) => (
                  <li
                    key={item.id}
                    className={selectedSessionId === item.id ? "session-list__item active" : "session-list__item"}
                  >
                    <button type="button" onClick={() => handleSelectSession(item.id)}>
                      <div className="session-list__title">
                        Session #{item.id}
                        {item.has_pj ? <span className="speaker-tag">PJ</span> : null}
                      </div>
                      <div className="session-list__meta">
                        <span>{new Date(item.created_at).toLocaleString()}</span>
                        <span>{item.status}</span>
                        <span>{item.todo_count} todos</span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </aside>
    </div>
  );
}
