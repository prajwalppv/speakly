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
        # Return mock response in developer mode
        if settings.developer_mode:
            import uuid
            mock_id = str(uuid.uuid4())[:16]
            logger.info(f"Developer mode: returning mock ElevenLabs response with ID {mock_id}")
            return {
                "message": "[MOCK] Request accepted. Transcription will be sent to webhook.",
                "request_id": f"mock_request_{mock_id}",
                "transcription_id": f"mock_transcription_{mock_id}",
            }
            
        if not self.is_configured:
            raise ElevenLabsNotConfiguredError("ElevenLabs API key is not configured.")
        if not audio_path.exists():
            raise ElevenLabsError(f"Audio file not found: {audio_path}")

        headers = {"xi-api-key": self.api_key or ""}
        payload = {
            "webhook_url": webhook_url,
            "webhook": "true",
            "model_id": "scribe_v1",
            "language_code": "en",  # Correct parameter name per ElevenLabs API
        }
        if settings.elevenlabs_diarization_enabled:
            payload["diarize"] = "true"
            if settings.elevenlabs_diarization_threshold is not None:
                payload["diarization_threshold"] = str(
                    settings.elevenlabs_diarization_threshold
                )
        if settings.elevenlabs_webhook_id:
            payload["webhook_id"] = settings.elevenlabs_webhook_id
        if metadata:
            encoded_metadata = json.dumps(metadata)
            payload["metadata"] = encoded_metadata
            payload["webhook_metadata"] = encoded_metadata

        try:
            with httpx.Client(base_url=self.base_url, headers=headers, timeout=self._timeout) as client:
                with audio_path.open("rb") as file_obj:
                    response = client.post(
                        "/v1/speech-to-text",
                        files={"file": (audio_path.name, file_obj, "application/octet-stream")},
                        data=payload,
                    )
        except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as exc:  # pragma: no cover
            logger.error("Network error connecting to ElevenLabs", extra={"extra_data": {"error": str(exc)}})
            raise ElevenLabsError(f"Network error: {exc}") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network errors
            logger.error("ElevenLabs API error", extra={"extra_data": {"status": response.status_code, "body": response.text[:500]}})
            raise ElevenLabsError(f"API error {response.status_code}: {response.text[:200]}") from exc

        try:
            data = response.json()
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to parse ElevenLabs response", extra={"extra_data": {"body": response.text[:500]}})
            raise ElevenLabsError(f"Invalid JSON response: {exc}") from exc
            
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
