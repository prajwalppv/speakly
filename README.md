# Speakly Phase 1

This repository contains the Phase 1 "hello pipeline" implementation for Speakly. The backend is a FastAPI application with SQLite storage and JSON logging, and the frontend is a React + Vite interface for uploading sample audio. Both services are containerised so the entire stack can be run and tested with Docker Compose.

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

The frontend issues uploads to the backend and shows the JSON response. Uploaded files are stored under `backend/storage/audio` on the host for inspection.

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
- JSON logs are written to `backend/logs/speakly.log`. When running via Docker they are also emitted to stdout for easy inspection.
- The stack uses SQLite for simplicity in Phase 1; the database file lives at `backend/data/app.db` by default.
