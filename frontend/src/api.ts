import axios from "axios";

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim();

// When RAW_BASE_URL is omitted or set to the sentinel value "proxy", fall back
// to a relative request so the Vite dev server proxy (or same-origin hosting)
// forwards calls to the backend.
const client = axios.create({
  baseURL: RAW_BASE_URL && RAW_BASE_URL !== "proxy" ? RAW_BASE_URL : ""
});

// Add request interceptor to include Clerk auth token
let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

client.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
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
  developer_message?: string | null;
}

export interface TranscriptionRecord {
  id: number;
  status: string;
  text: string | null;
  provider: string;
  provider_job_id: string | null;
  error: string | null;
  metadata: Record<string, unknown> | null;
  duration_ms: number | null;
  channel_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface SpeakerSegment {
  id: number;
  speaker_label: string | null;
  start_ms: number;
  end_ms: number;
  confidence: number | null;
  is_pj: boolean;
  channel_index: number | null;
  speaker_profile: string | null;
}

export interface SummaryRecord {
  id: number;
  model: string;
  text: string | null;
  status: string;
  updated_at: string;
}

export interface TodoRecord {
  id: number;
  title: string;
  due_hint: string | null;
  confidence: number | null;
  status: string;
  source_start_ms: number | null;
  source_end_ms: number | null;
  source_excerpt: string | null;
  ticktick_sync_status: string;
  ticktick_task_id: string | null;
  ticktick_synced_at: string | null;
  ticktick_sync_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface TagRecord {
  id: number;
  name: string;
  category: string;
  color: string;
  auto_generated: boolean;
  usage_count: number;
  created_at: string;
}

export interface SessionRecord {
  id: number;
  status: string;
  description: string | null;
  audio_path: string | null;
  last_error: string | null;
  last_transcribed_at: string | null;
  has_pj: boolean;
  todo_count: number;
  task_updates_count: number;
  processing_stages: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  transcriptions: TranscriptionRecord[];
  speaker_segments: SpeakerSegment[];
  summary: SummaryRecord | null;
  todos: TodoRecord[];
  tags: TagRecord[];
}

export async function uploadAudio(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("audio", file, file.name);

  const response = await client.post<UploadResponse>("/api/audio", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });

  return response.data;
}

export interface BulkUploadResult {
  success: boolean;
  file_name: string;
  session_id?: number;
  error?: string;
}

export interface BulkUploadResponse {
  total: number;
  successful: number;
  failed: number;
  results: BulkUploadResult[];
}

export async function uploadAudioBulk(files: File[]): Promise<BulkUploadResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file, file.name);
  });

  const response = await client.post<BulkUploadResponse>("/api/audio/bulk", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });

  return response.data;
}

export async function fetchSession(sessionId: number): Promise<SessionRecord> {
  const response = await client.get<SessionRecord>(`/api/sessions/${sessionId}`);
  return response.data;
}

export interface SessionFilterParams {
  has_pj?: boolean;
  speaker?: string;
  q?: string;
  from?: string;
  to?: string;
}

export async function fetchSessions(params: SessionFilterParams = {}): Promise<SessionRecord[]> {
  const response = await client.get<SessionRecord[]>("/api/sessions", { params });
  return response.data;
}

// TickTick Integration
export interface TickTickStatusResponse {
  connected: boolean;
  user_id: number;
  expires_at?: string;
  scope?: string;
  error?: string;
}

export interface TickTickProject {
  id: string;
  name: string;
}

export interface TickTickProjectsResponse {
  success: boolean;
  user_id: number;
  projects: TickTickProject[];
}

export async function getTickTickStatus(userId: number = 1): Promise<TickTickStatusResponse> {
  const response = await client.get<TickTickStatusResponse>(`/api/ticktick/status?user_id=${userId}`);
  return response.data;
}

export async function connectTickTick(userId: number = 1): Promise<void> {
  // This will redirect the browser to TickTick OAuth
  window.location.href = `/api/ticktick/connect?user_id=${userId}`;
}

export async function disconnectTickTick(userId: number = 1): Promise<void> {
  await client.post(`/api/ticktick/disconnect?user_id=${userId}`);
}

export async function getTickTickProjects(userId: number = 1): Promise<TickTickProjectsResponse> {
  const response = await client.get<TickTickProjectsResponse>(`/api/ticktick/projects?user_id=${userId}`);
  return response.data;
}

// Transcription Editing
export interface EditTranscriptionRequest {
  text: string;
  user_id?: number;
  notes?: string;
}

export interface EditTranscriptionResponse {
  id: number;
  text: string | null;
  status: string;
  edit_count: number;
  last_edited_at: string | null;
}

export async function editTranscription(
  transcriptionId: number,
  request: EditTranscriptionRequest
): Promise<EditTranscriptionResponse> {
  const response = await client.put<EditTranscriptionResponse>(
    `/api/transcriptions/${transcriptionId}`,
    request
  );
  return response.data;
}

export async function getTranscriptionHistory(transcriptionId: number): Promise<any[]> {
  const response = await client.get(`/api/transcriptions/${transcriptionId}/history`);
  return response.data;
}

// Task Management
export interface CreateTodoRequest {
  title: string;
  due_hint?: string;
  source_excerpt?: string;
}

export interface UpdateTodoRequest {
  title?: string;
  due_hint?: string;
  status?: string;
  source_excerpt?: string;
}

export async function createTodo(
  sessionId: number,
  request: CreateTodoRequest
): Promise<TodoRecord> {
  const response = await client.post<TodoRecord>(
    `/api/todos/sessions/${sessionId}/todos`,
    request
  );
  return response.data;
}

export async function updateTodo(
  todoId: number,
  request: UpdateTodoRequest
): Promise<TodoRecord> {
  const response = await client.put<TodoRecord>(`/api/todos/${todoId}`, request);
  return response.data;
}

export async function deleteTodo(todoId: number): Promise<void> {
  await client.delete(`/api/todos/${todoId}`);
}

export async function resyncTodo(todoId: number): Promise<{ message: string }> {
  const response = await client.post(`/api/todos/${todoId}/resync`);
  return response.data;
}

// Session Retry
export async function retrySession(sessionId: number): Promise<{ message: string; transcriptions_reset: number }> {
  const response = await client.post(`/api/sessions/${sessionId}/retry`);
  return response.data;
}

// Session Regenerate
export async function regenerateSession(sessionId: number): Promise<{ message: string; status: string }> {
  const response = await client.post(`/api/sessions/${sessionId}/regenerate`);
  return response.data;
}
