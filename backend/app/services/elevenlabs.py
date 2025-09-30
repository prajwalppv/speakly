from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class ElevenLabsError(RuntimeError):
    """Base error raised for ElevenLabs interactions."""


class ElevenLabsNotConfiguredError(ElevenLabsError):
    """Raised when the ElevenLabs client is used without configuration."""


class ElevenLabsClient:
    """Minimal ElevenLabs Scribe STT client."""

    def __init__(self, api_key: str | None, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._timeout = 30.0

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def submit_transcription(
        self,
        *,
        audio_path: Path,
        webhook_url: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured:
            raise ElevenLabsNotConfiguredError("ElevenLabs API key is not configured.")
        if not audio_path.exists():
            raise ElevenLabsError(f"Audio file not found: {audio_path}")

        headers = {"xi-api-key": self.api_key or ""}
        payload = {
            "webhook_url": webhook_url,
            "webhook": "true",
            "model_id": "scribe_v1",
            "language": "en",
        }
        if settings.elevenlabs_webhook_id:
            payload["webhook_id"] = settings.elevenlabs_webhook_id
        if metadata:
            encoded_metadata = json.dumps(metadata)
            payload["metadata"] = encoded_metadata
            payload["webhook_metadata"] = encoded_metadata

        with httpx.Client(base_url=self.base_url, headers=headers, timeout=self._timeout) as client:
            with audio_path.open("rb") as file_obj:
                response = client.post(
                    "/v1/speech-to-text",
                    files={"file": (audio_path.name, file_obj, "application/octet-stream")},
                    data=payload,
                )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network errors
            raise ElevenLabsError(str(exc)) from exc

        data = response.json()
        logger.debug("ElevenLabs submission successful", extra={"extra_data": data})
        return data


def get_elevenlabs_client() -> ElevenLabsClient:
    return ElevenLabsClient(settings.elevenlabs_api_key, settings.elevenlabs_base_url)


__all__ = [
    "ElevenLabsClient",
    "ElevenLabsError",
    "ElevenLabsNotConfiguredError",
    "get_elevenlabs_client",
]
