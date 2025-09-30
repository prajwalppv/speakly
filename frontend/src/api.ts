import axios from "axios";

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim();

// When RAW_BASE_URL is omitted or set to the sentinel value "proxy", fall back
// to a relative request so the Vite dev server proxy (or same-origin hosting)
// forwards calls to the backend.
const client = axios.create({
  baseURL: RAW_BASE_URL && RAW_BASE_URL !== "proxy" ? RAW_BASE_URL : ""
});

export interface UploadResponse {
  status: string;
  file_name: string;
  file_path: string;
  session_id?: number | null;
  received_at: string;
  session_status: string;
  transcription_id?: number | null;
  transcription_status?: string | null;
}

export interface TranscriptionRecord {
  id: number;
  status: string;
  text: string | null;
  provider: string;
  provider_job_id: string | null;
  error: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface SessionRecord {
  id: number;
  status: string;
  audio_path: string | null;
  last_error: string | null;
  last_transcribed_at: string | null;
  created_at: string;
  updated_at: string;
  transcriptions: TranscriptionRecord[];
}

export async function uploadAudio(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("audio", file, file.name);

  const response = await client.post<UploadResponse>("/api/audio", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });

  return response.data;
}

export async function fetchSession(sessionId: number): Promise<SessionRecord> {
  const response = await client.get<SessionRecord>(`/api/sessions/${sessionId}`);
  return response.data;
}
