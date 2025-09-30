# Speakly Phase 3 Design

## Goals

1. **Speaker intelligence** – add diarization plus PJ voice identification to every transcription. Persist speaker segments with timing, confidence, and PJ tagging for downstream search and analytics.
2. **Session intelligence** – enrich each session with LLM-generated artifacts:
   - concise summaries/highlights
   - actionable TODO extraction (description, due-hint, confidence, transcript span)
3. **Discovery & filtering** – expose new API queries (by speaker, PJ presence, date ranges, keywords, TODO status). Update the frontend so users can browse segments, summaries, and todos.
4. **Workflow automation** – ship optional services (Ollama, n8n) so Speakly can run entirely on self-hosted infrastructure and forward todos to external tools later.
5. **Operational polish** – migrate to FastAPI lifespan handlers, extend logging/metrics, and grow the test suite around the new behaviour.

## Architecture Overview

### Data Model Additions

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `speaker_profiles` | Catalog of known voices (e.g., PJ) | `name`, `description`, `embedding_path`, `is_primary` |
| `speaker_segments` | Per-transcription diarization output | `session_id`, `transcription_id`, `speaker_label`, `speaker_profile_id`, `start_ms`, `end_ms`, `confidence`, `is_pj` |
| `llm_runs` | Audit trail for every Ollama generation | `session_id`, `run_type` (`summary`, `todos`, `qa`), `model`, `prompt`, `response`, `status`, `started_at`, `completed_at`, `error` |
| `todos` | LLM-extracted actions | `session_id`, `llm_run_id`, `title`, `due_hint`, `confidence`, `status`, `source_start_ms`, `source_end_ms` |

Existing tables gain:
- `transcriptions`: add `duration_ms`, `channels`, `llm_summary_id` (optional FK to `llm_runs`).
- `sessions`: add `has_pj`, `summary_id` (FK), `todo_count` cache.

### Processing Flow

1. **Upload** (unchanged): we persist the audio file, create session + transcription rows, and submit to ElevenLabs with metadata + `webhook=true` + optional `webhook_id`.
2. **ElevenLabs Webhook** (enhanced):
   - Validate signature.
   - Parse diarization payload (`transcription.words` plus eventual diarization array once exposed).
   - Store/merge speaker segments; detect PJ matches via cosine similarity against `speaker_profiles` embedding (Phase 3 stub uses configurable threshold + stored embedding file path).
   - Mark session `has_pj` when at least one segment maps to PJ.
   - Kick off LLM jobs for summary & todos via background tasks.
3. **LLM Jobs**:
   - `ollama generate` with prompts under `backend/app/prompts/` for summary + todo extraction.
   - Store raw response in `llm_runs`, parse JSON payload for todos (schema enforced in code).
   - Persist todos; update session caches.
4. **Automation Hooks**:
   - Emit event (e.g., simple async queue) once TODOs are ready. n8n can poll `/api/sessions/:id/todos?status=pending` or we can add a `POST /api/hooks/todos` to push.

### Service Integrations

- **ElevenLabs:** continue using HTTP API. Diarization metadata currently lives inside `transcription.words`; if full diarization endpoint is separate we’ll accommodate once available.
- **Ollama:** run as a sidecar container (`ollama/ollama:latest`). Backend hits `http://ollama:11434/api/generate` with streaming disabled for now.
- **n8n:** optional container with SQLite volume that points at the same database (read-only via replica) or uses HTTP API to query Speakly.

### API Surface

| Endpoint | Notes |
|----------|-------|
| `GET /api/sessions` | Query params: `speaker=PJ`, `has_pj=true/false`, `from=`, `to=`, `q=` for transcript search. |
| `GET /api/sessions/{id}` | Include `speaker_segments`, `summary`, `todos`. |
| `GET /api/sessions/{id}/todos` | Optional `status` filter. |
| `POST /api/sessions/{id}/qa` | (Stretch) Fire an on-demand QA run via Ollama and return answer.

### Frontend Additions

- Session detail view gains:
  - speaker timeline (chips per segment) with PJ highlighting
  - summary card + refresh button
  - TODO list with due hints & transcript jump links
- Filters panel (left rail) for speaker/date/search.

### Configuration

New environment variables:
- `ELEVENLABS_DIARIZATION_ENABLED` (bool toggle)
- `PJ_PROFILE_PATH` (path to PJ sample embedding/audio)
- `OLLAMA_BASE_URL` (default `http://ollama:11434`)
- `OLLAMA_MODEL_SUMMARY`, `OLLAMA_MODEL_TODO`
- `TODO_CONFIDENCE_THRESHOLD`

Docker Compose additions:
- `ollama` service with persistent model volume
- `n8n` service (optional profile) linking to Speakly backend

### Testing Strategy

- Unit tests for diarization parser & PJ similarity scoring.
- Webhook integration test with diarization payload fixture.
- LLM prompt unit tests using deterministic mock responses.
- End-to-end test that simulates upload → webhook → summary/todo generation (mock Ollama).

## Next Steps

1. Schema migration & models (speaker/todo/llm tables + metadata columns).
2. Backend processing for diarization & PJ voice identification.
3. Ollama client + LLM job orchestration (summary + todo extraction).
4. API/filter enhancements and tests.
5. Frontend UI work.
6. Compose n8n + documentation.
