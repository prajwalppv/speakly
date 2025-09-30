import { useCallback, useMemo, useState } from "react";

import { UploadResponse, uploadAudio } from "../api";

type UploadState = "idle" | "uploading" | "success" | "error";

const DEFAULT_MESSAGE = "Select an audio file (WAV, MP3, M4A) to test the pipeline.";

export default function AudioUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [response, setResponse] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isUploading = state === "uploading";

  const helperMessage = useMemo(() => {
    if (state === "success" && response) {
      return `Audio received. Session #${response.session_id ?? "n/a"}.`;
    }

    if (state === "error" && error) {
      return error;
    }

    return DEFAULT_MESSAGE;
  }, [state, response, error]);

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] ?? null;
    setFile(selectedFile);
    setResponse(null);
    setError(null);
    setState("idle");
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
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Unable to upload audio right now.";
        setError(message);
        setState("error");
      }
    },
    [file]
  );

  return (
    <section className="card">
      <header className="card__header">
        <h2>Upload a sample</h2>
        <p>{helperMessage}</p>
      </header>
      <form onSubmit={handleSubmit} className="card__body" aria-live="polite">
        <label className="file-input">
          <span>Choose audio</span>
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
    </section>
  );
}
