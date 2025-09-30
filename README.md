# Speakly Phase 3

Phase 3 turns Speakly into a speaker-aware, action-oriented assistant. The backend is a FastAPI service backed by SQLite, ElevenLabs for transcription + diarization, and optional Ollama + n8n sidecars. The frontend (React + Vite) now visualises speakers, summaries, and TODOs.

## Highlights

- ElevenLabs webhook pipeline with diarization + PJ voice tagging and advanced metadata
- LLM-powered summaries and actionable TODO extraction (via Ollama, with graceful fallbacks)
- Rich filtering (`/api/sessions?speaker=PJ&has_pj=true&q=sync`) and session details including speaker timelines
- Frontend dashboard to upload audio, browse sessions, review summaries, and manage todos
- Optional n8n automation profile ready to sync todos with external task managers

## Prerequisites

- Docker Desktop / Engine 24+
- Docker Compose v2
- ElevenLabs account + Speech-to-Text webhook configured (point to `https://<your-ngrok>/api/webhooks/elevenlabs`)
- (Optional) Ollama for local LLM generation

## Environment

Edit `.env` to supply credentials and toggles:

```
SPEAKLY_ENVIRONMENT=prod
SPEAKLY_LOG_LEVEL=INFO
ELEVENLABS_API_KEY=...
ELEVENLABS_WEBHOOK_SECRET=...
ELEVENLABS_WEBHOOK_ID=             # optional explicit webhook id
ELEVENLABS_DIARIZATION_ENABLED=true
PJ_PROFILE_NAME=PJ
PJ_VOICE_TAGS=pj,patrick
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL_SUMMARY=llama3
OLLAMA_MODEL_TODO=llama3
TODO_CONFIDENCE_THRESHOLD=0.35
SPEAKLY_DEVELOPER_MODE=false
```

## Running the stack

### Core services (backend + frontend)

```bash
docker compose up --build backend frontend
```

- Backend: `http://localhost:8000`
  - `POST /api/audio` – upload audio (multipart)
  - `POST /api/webhooks/elevenlabs` – ElevenLabs callback
  - `GET /api/sessions` – list with filters (`has_pj`, `speaker`, `q`, `from`, `to`)
  - `GET /api/sessions/{id}` – full session details (speaker segments, summary, todos)
- Frontend: `http://localhost:5173`
  - Upload samples
  - Browse session list with filters
  - Review summaries, TODOs, and diarization timeline

### Enable Ollama (LLM summaries + todos)

```bash
docker compose up --build backend frontend --profile llm
```

The backend targets `OLLAMA_BASE_URL` (defaults to `http://ollama:11434`). Make sure the required models are pulled inside the container, for example:

```bash
docker compose exec ollama ollama pull llama3
```

If Ollama is unavailable the backend falls back to lightweight heuristics and marks LLM runs as `error`.

### Optional n8n automation

```bash
docker compose up --build backend frontend --profile n8n
```

n8n UI: `http://localhost:5678` (basic auth defaults to `admin/changeme`). Use Speakly APIs to poll for new todos and dispatch them to external task tools.

## Testing

Backend tests (pytest) run inside the Docker image:

```bash
docker compose run --rm --profile test backend-tests
```

## Notes

- ElevenLabs metadata is persisted with each transcription. Diarization is toggled via `ELEVENLABS_DIARIZATION_ENABLED`.
- Default PJ speaker profile is auto-created; adjust `PJ_PROFILE_NAME`/`PJ_VOICE_TAGS` to match your tags or provide custom logic in `speaker_profiles` table.
- Speaker segments, summaries, and TODOs are all exposed via the session APIs for easy integration with external services.
- Set `SPEAKLY_DEVELOPER_MODE=true` to bubble backend errors and debug messages directly into API responses and the UI during development.
- Logs live at `backend/logs/speakly.log` (JSON). Update `SPEAKLY_LOG_LEVEL` for more detail.

## Phase 3 follow-up ideas

- Wire TODO webhook to TickTick or other task managers via n8n
- Add real voice embedding comparison for PJ identification
- Streaming LLM responses & user-triggered Q&A endpoints
