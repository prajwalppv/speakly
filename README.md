# Speakly Phase 2

Phase 2 extends the initial "hello pipeline" with ElevenLabs Scribe transcription hooks, session history, and a richer UI loop. The backend is a FastAPI application with SQLite storage and JSON logging, and the frontend is a React + Vite interface for uploading sample audio and tracking transcription progress. Both services are containerised so the entire stack can be run and tested with Docker Compose.

## Prerequisites

- Docker Desktop or Docker Engine 24+
- Docker Compose v2 (usually bundled with Docker Desktop)

## Usage

### Boot the stack

```bash
docker compose up --build backend frontend
```

- Backend API: `http://localhost:8000` (`POST /api/audio`)
- Frontend UI: `http://localhost:5173`

- The frontend issues uploads to the backend and shows the JSON response. Uploaded files are stored under `backend/storage/audio` on the host for inspection.
- Query session history with `GET /api/sessions` or a specific record with `GET /api/sessions/{id}`.
- Webhook callback endpoint: `POST /api/webhooks/elevenlabs`.

### Configure ElevenLabs (optional)

Set the following environment variables before starting the stack to forward uploads to ElevenLabs Scribe STT:

| Variable | Purpose |
|----------|---------|
| `ELEVENLABS_API_KEY` | ElevenLabs API key used for authenticated requests |
| `ELEVENLABS_BASE_URL` | Override the ElevenLabs API base URL (defaults to `https://api.elevenlabs.io`) |
| `ELEVENLABS_WEBHOOK_SECRET` | Shared secret used to validate webhook signatures |

The backend passes `metadata` with `session_id` and `transcription_id` so webhook handlers can locate the correct record. For local development you can simulate a completed transcription by POSTing to the webhook endpoint with the expected payload and optional signature (HMAC SHA-256 of the raw body).

### Run backend tests

```bash
docker compose run --rm --profile test backend-tests
```

This runs the FastAPI test suite (pytest) inside the backend container image.

## Project Structure

```
backend/
  app/               # FastAPI application package
  tests/             # pytest suite
  requirements*.txt  # Python dependencies
  Dockerfile         # Backend image definition
frontend/
  src/               # React application source
  Dockerfile         # Frontend image definition
docker-compose.yml   # Orchestrates the services
PLAN.md              # Phase roadmap
```

## Notes

- Configuration values (database path, storage directory, log level) can be overridden with environment variables prefixed by `SPEAKLY_` for the backend and `VITE_` for the frontend.
- The frontend issues API calls via a relative `/api` path by default. `VITE_BACKEND_URL_INTERNAL` controls where the Vite dev server proxies those requests (defaults to `http://localhost:8000`), while setting `VITE_API_BASE_URL` to a concrete URL skips the proxy and targets that address directly.
- ElevenLabs integration is optional; without an API key the backend records a pending transcription and the UI will show the submission as "pending" until a webhook completes it.
- JSON logs are written to `backend/logs/speakly.log`. When running via Docker they are also emitted to stdout for easy inspection.
- The stack uses SQLite for simplicity; the database file lives at `backend/data/app.db` by default.
