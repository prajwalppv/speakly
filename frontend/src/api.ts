import axios from "axios";

const DEFAULT_BASE_URL = "http://localhost:8000";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL
});

export interface UploadResponse {
  status: string;
  file_name: string;
  file_path: string;
  session_id?: number | null;
  received_at: string;
}

export async function uploadAudio(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("audio", file, file.name);

  const response = await client.post<UploadResponse>("/api/audio", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });

  return response.data;
}
