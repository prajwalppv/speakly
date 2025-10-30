from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

from backend.app.services.stt import GroqSttProvider, SttError


def test_transcribe_large_file_retries_with_smaller_chunks(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        groq_api_key="test-key",
        groq_chunk_duration_seconds=600,
        groq_min_chunk_duration_seconds=60,
        developer_mode=False,
    )

    provider = GroqSttProvider(settings)

    call_count = {"value": 0}
    requested_durations: list[int] = []

    def fake_split_audio_file(
        *, audio_path: Path, output_dir: Path, segment_seconds: int
    ) -> list[Path]:
        requested_durations.append(segment_seconds)
        return [output_dir / "chunk_a.wav", output_dir / "chunk_b.wav"]

    def fake_call_groq(*, audio_path: Path, metadata):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise SttError("Transcription failed: Connection error.")
        return {
            "text": f"text-{metadata['chunk_index']}",
            "duration": 1.0,
            "language": "en",
        }

    monkeypatch.setattr(provider, "_split_audio_file", fake_split_audio_file)
    monkeypatch.setattr(provider, "_call_groq", fake_call_groq)
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/local/bin/ffmpeg")

    audio_path = tmp_path / "input.wav"
    audio_path.write_bytes(b"fake audio content")

    result = provider._transcribe_large_file(audio_path=audio_path, metadata=None)

    assert result["transcription_text"] == "text-1\n\ntext-2"
    assert len(requested_durations) >= 2
    assert requested_durations[0] > requested_durations[-1]
    assert result["metadata"]["chunk_duration_seconds"] == requested_durations[-1]
