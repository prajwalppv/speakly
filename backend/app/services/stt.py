"""Speech-to-Text service with pluggable provider support.

Similar to the LLM service architecture, this provides a provider abstraction
for multiple STT backends (ElevenLabs, Groq Whisper, etc.)
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx
from groq import Groq

from ..config import settings

logger = logging.getLogger(__name__)


class SttError(RuntimeError):
    """Base error raised for STT provider interactions."""


class SttNotConfiguredError(SttError):
    """Raised when the STT provider is used without configuration."""


class SttProvider(ABC):
    """Abstract base class for pluggable STT providers."""

    name: str

    def __init__(self, settings) -> None:
        self._settings = settings

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the provider has enough configuration to operate."""

    @abstractmethod
    def submit_transcription(
        self,
        *,
        audio_path: Path,
        webhook_url: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit audio file for async transcription with webhook callback.
        
        Args:
            audio_path: Path to audio file
            webhook_url: URL to receive transcription webhook
            metadata: Optional metadata to pass through
            
        Returns:
            Dict with provider response (request_id, transcription_id, etc.)
        """

    @abstractmethod
    def supports_diarization(self) -> bool:
        """Return True if provider supports speaker diarization."""


class GroqSttProvider(SttProvider):
    """Groq STT provider using Whisper model.
    
    Groq provides synchronous transcription (no webhook support),
    so we'll handle it synchronously and return immediately.
    """

    name = "groq"

    def __init__(self, settings) -> None:
        super().__init__(settings)
        self._api_key = (getattr(settings, "groq_api_key", "") or "").strip()
        self._model = "whisper-large-v3"  # Groq's Whisper model
        self._client = None

    def is_available(self) -> bool:
        return bool(self._api_key)
    
    def _get_client(self) -> Groq:
        """Lazy initialization of Groq client."""
        if self._client is None:
            if not self._api_key:
                raise SttNotConfiguredError("Groq API key is not configured.")
            self._client = Groq(api_key=self._api_key)
        return self._client

    def supports_diarization(self) -> bool:
        # Groq Whisper doesn't support diarization
        return False

    def submit_transcription(
        self,
        *,
        audio_path: Path,
        webhook_url: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Transcribe audio synchronously using Groq Whisper.
        
        Note: Groq doesn't support async webhooks, so we transcribe immediately
        and return the result. The caller should handle this synchronous response.
        """
        if not self.is_available():
            raise SttNotConfiguredError("Groq API key is not configured.")
        
        if not audio_path.exists():
            raise SttError(f"Audio file not found: {audio_path}")

        # Check file size (Groq has 25MB limit)
        file_size = audio_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb > 25:
            raise SttError(f"Audio file too large: {file_size_mb:.2f}MB (max 25MB)")

        logger.info(f"Transcribing with Groq Whisper: {audio_path.name} ({file_size_mb:.2f}MB)")

        try:
            # Use the Groq SDK for simpler, more reliable file uploads
            client = self._get_client()
            # Normalize filename to lowercase extension for Groq API compatibility
            # Groq expects lowercase extensions (.wav not .WAV)
            normalized_filename = audio_path.stem + audio_path.suffix.lower()
            
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(normalized_filename, audio_file),
                    model=self._model,
                    response_format="verbose_json",
                    language="en",
                )
        except Exception as exc:
            logger.error(f"Groq transcription error: {exc}")
            raise SttError(f"Transcription failed: {exc}") from exc

        # Extract transcription text
        transcription_text = transcription.text if hasattr(transcription, 'text') else str(transcription)
        
        logger.info(f"Groq transcription completed: {len(transcription_text)} characters")

        # Return in a format similar to ElevenLabs async response
        # but include the actual transcription since it's synchronous
        return {
            "provider": "groq",
            "model": self._model,
            "transcription_text": transcription_text,
            "duration": getattr(transcription, 'duration', None),
            "language": getattr(transcription, 'language', 'en'),
            "metadata": metadata,
            "is_sync": True,  # Flag to indicate synchronous response
        }


class ElevenLabsSttProvider(SttProvider):
    """ElevenLabs STT provider using Scribe model."""

    name = "elevenlabs"

    def __init__(self, settings) -> None:
        super().__init__(settings)
        self._api_key = (getattr(settings, "elevenlabs_api_key", "") or "").strip()
        self._base_url = (
            getattr(settings, "elevenlabs_base_url", "https://api.elevenlabs.io") or ""
        ).rstrip("/")
        self._webhook_id = getattr(settings, "elevenlabs_webhook_id", None)
        self._diarization_enabled = getattr(settings, "elevenlabs_diarization_enabled", True)
        self._diarization_threshold = getattr(settings, "elevenlabs_diarization_threshold", None)

    def is_available(self) -> bool:
        return bool(self._api_key)

    def supports_diarization(self) -> bool:
        return True

    def submit_transcription(
        self,
        *,
        audio_path: Path,
        webhook_url: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit audio for async transcription via webhook."""
        if not self.is_available():
            raise SttNotConfiguredError("ElevenLabs API key is not configured.")

        if not audio_path.exists():
            raise SttError(f"Audio file not found: {audio_path}")

        logger.info(f"Submitting to ElevenLabs: {audio_path.name}")

        headers = {"xi-api-key": self._api_key}
        payload = {
            "webhook_url": webhook_url,
            "webhook": "true",
            "model_id": "scribe_v1",
            "language_code": "en",
        }

        if self._diarization_enabled:
            payload["diarize"] = "true"
            if self._diarization_threshold is not None:
                payload["diarization_threshold"] = str(self._diarization_threshold)

        if self._webhook_id:
            payload["webhook_id"] = self._webhook_id

        if metadata:
            encoded_metadata = json.dumps(metadata)
            payload["metadata"] = encoded_metadata
            payload["webhook_metadata"] = encoded_metadata

        try:
            with httpx.Client(base_url=self._base_url, headers=headers, timeout=30.0) as client:
                with audio_path.open("rb") as file_obj:
                    response = client.post(
                        "/v1/speech-to-text",
                        files={"file": (audio_path.name, file_obj, "application/octet-stream")},
                        data=payload,
                    )
        except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.error(f"Network error connecting to ElevenLabs: {exc}")
            raise SttError(f"Network error: {exc}") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(f"ElevenLabs API error: {response.status_code} - {response.text[:500]}")
            raise SttError(f"API error {response.status_code}: {response.text[:200]}") from exc

        try:
            data = response.json()
        except Exception as exc:
            logger.error(f"Failed to parse ElevenLabs response: {response.text[:500]}")
            raise SttError(f"Invalid JSON response: {exc}") from exc

        logger.debug(f"ElevenLabs submission successful: {data}")
        
        return {
            "provider": "elevenlabs",
            "request_id": data.get("request_id"),
            "transcription_id": data.get("transcription_id"),
            "message": data.get("message"),
            "is_sync": False,  # Async via webhook
        }


class MockSttProvider(SttProvider):
    """Mock STT provider for developer mode."""

    name = "mock"

    def is_available(self) -> bool:
        return True

    def supports_diarization(self) -> bool:
        return True

    def submit_transcription(
        self,
        *,
        audio_path: Path,
        webhook_url: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return mock response for testing."""
        import uuid
        
        mock_id = str(uuid.uuid4())[:16]
        logger.info(f"Mock STT: returning mock response with ID {mock_id}")
        
        return {
            "provider": "mock",
            "message": "[MOCK] Request accepted. Transcription will be sent to webhook.",
            "request_id": f"mock_request_{mock_id}",
            "transcription_id": f"mock_transcription_{mock_id}",
            "is_sync": False,
        }


# Provider registry
STT_PROVIDER_REGISTRY: tuple[type[SttProvider], ...] = (
    GroqSttProvider,
    ElevenLabsSttProvider,
    MockSttProvider,
)


class SttService:
    """High-level STT orchestration that delegates to the selected provider."""

    def __init__(self, provider_name: str | None = None) -> None:
        raw_requested = provider_name or getattr(settings, "stt_provider", "auto") or "auto"
        requested = str(raw_requested).strip().lower() or "auto"

        # Developer mode always uses mock
        if settings.developer_mode:
            requested = "mock"

        self.requested_provider = requested
        self._providers = [provider_cls(settings) for provider_cls in STT_PROVIDER_REGISTRY]
        self._available_providers = [p for p in self._providers if p.is_available()]
        self._provider = self._select_provider(requested)

    def _select_provider(self, requested: str) -> SttProvider | None:
        # Developer mode override
        if settings.developer_mode:
            for provider in self._providers:
                if provider.name == "mock":
                    logger.info("Using mock STT provider (developer mode)")
                    return provider

        if requested == "auto" or not requested:
            if self._available_providers:
                selected = self._available_providers[0]
                logger.info(f"Auto-selected STT provider: {selected.name}")
                return selected
            return None

        # Find requested provider
        for provider in self._available_providers:
            if provider.name == requested:
                logger.info(f"Using requested STT provider: {provider.name}")
                return provider

        logger.warning(
            f"Requested STT provider '{requested}' not available; falling back to first available"
        )
        return self._available_providers[0] if self._available_providers else None

    @property
    def provider(self) -> SttProvider | None:
        return self._provider

    @property
    def provider_name(self) -> str:
        return self._provider.name if self._provider else "none"

    def is_enabled(self) -> bool:
        return self.provider is not None

    def supports_diarization(self) -> bool:
        return self._provider.supports_diarization() if self._provider else False

    def submit_transcription(
        self,
        *,
        audio_path: Path,
        webhook_url: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit audio for transcription using the selected provider."""
        if not self._provider:
            raise SttNotConfiguredError("No STT provider is configured or available.")

        return self._provider.submit_transcription(
            audio_path=audio_path,
            webhook_url=webhook_url,
            metadata=metadata,
        )


def get_stt_service() -> SttService:
    """Get the global STT service instance."""
    return SttService()


__all__ = [
    "SttService",
    "SttProvider",
    "SttError",
    "SttNotConfiguredError",
    "GroqSttProvider",
    "ElevenLabsSttProvider",
    "MockSttProvider",
    "get_stt_service",
]
