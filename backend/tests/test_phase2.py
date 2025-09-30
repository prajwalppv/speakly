from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Callable

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database import SessionLocal, init_database
from backend.app.main import create_app, ensure_default_user
from backend.app.models import Session as SessionModel
from backend.app.models import Transcription as TranscriptionModel


def _reset_database_state() -> None:
    with SessionLocal() as db:
        db.query(TranscriptionModel).delete()
        db.query(SessionModel).delete()
        db.commit()


def _build_client(tmp_path: Path, webhook_secret: str | None = None) -> tuple[TestClient, Callable[[], None]]:
    original_audio_dir = settings.audio_storage_dir
    original_secret = settings.elevenlabs_webhook_secret
    original_api_key = settings.elevenlabs_api_key

    settings.audio_storage_dir = tmp_path
    settings.elevenlabs_webhook_secret = webhook_secret
    settings.elevenlabs_api_key = None

    init_database()
    _reset_database_state()
    ensure_default_user()

    app = create_app()
    client = TestClient(app)

    def cleanup() -> None:
        client.close()
        settings.audio_storage_dir = original_audio_dir
        settings.elevenlabs_webhook_secret = original_secret
        settings.elevenlabs_api_key = original_api_key

    return client, cleanup


def test_upload_audio_creates_pending_transcription(tmp_path: Path) -> None:
    client, cleanup = _build_client(tmp_path)
    try:
        audio_bytes = b"Fake WAV data"
        response = client.post(
            "/api/audio",
            files={"audio": ("sample.wav", audio_bytes, "audio/wav")},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["session_status"] == "pending"
        assert payload["transcription_status"] == "pending"

        stored_path = Path(payload["file_path"])
        assert stored_path.exists()
        assert stored_path.read_bytes() == audio_bytes

        session_response = client.get(f"/api/sessions/{payload['session_id']}")
        assert session_response.status_code == 200
        session_data = session_response.json()
        assert session_data["status"] == "pending"
        assert session_data["transcriptions"][0]["status"] == "pending"
    finally:
        cleanup()


def test_webhook_marks_transcription_complete(tmp_path: Path) -> None:
    secret = "super-secret"
    client, cleanup = _build_client(tmp_path, webhook_secret=secret)
    try:
        upload = client.post(
            "/api/audio",
            files={"audio": ("clip.wav", b"fake", "audio/wav")},
        )
        data = upload.json()
        transcription_id = data["transcription_id"]
        session_id = data["session_id"]

        webhook_payload = {
            "type": "speech_to_text_transcription",
            "event_timestamp": 0,
            "data": {
                "request_id": "job-123",
                "transcription": {
                    "transcription_id": "job-123",
                    "status": "completed",
                    "text": "hello world",
                },
                "webhook_metadata": {
                    "transcription_id": transcription_id,
                    "session_id": session_id,
                },
            },
        }
        raw_body = json.dumps(webhook_payload).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        webhook_response = client.post(
            "/api/webhooks/elevenlabs",
            data=raw_body,
            headers={
                "content-type": "application/json",
                "x-elevenlabs-signature": signature,
            },
        )

        assert webhook_response.status_code == 204

        session_response = client.get(f"/api/sessions/{session_id}")
        session_data = session_response.json()
        assert session_data["status"] == "completed"
        transcription = session_data["transcriptions"][0]
        assert transcription["status"] == "completed"
        assert transcription["text"] == "hello world"
    finally:
        cleanup()
