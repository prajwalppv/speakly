from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import create_app, ensure_default_user
from backend.app.database import init_database


def test_upload_audio(tmp_path) -> None:
    settings.audio_storage_dir = tmp_path

    init_database()
    ensure_default_user()

    app = create_app()
    client = TestClient(app)

    audio_bytes = b"Fake WAV data"
    response = client.post(
        "/api/audio",
        files={"audio": ("sample.wav", audio_bytes, "audio/wav")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "received"
    stored_path = Path(payload["file_path"])
    assert stored_path.exists()
    assert stored_path.read_bytes() == audio_bytes
