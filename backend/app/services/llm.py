from __future__ import annotations

import asyncio
import json
import logging
import textwrap
from typing import Any, Iterable

import httpx

from ..config import settings
from ..database import SessionLocal
from ..models import LlmRun, Session as SessionModel, Todo, Transcription

logger = logging.getLogger(__name__)


SUMMARY_PROMPT = textwrap.dedent(
    """
    You are Speakly's meeting assistant.
    Summarise the conversation in 3-5 bullet points that capture the key arguments, decisions, and follow ups.
    Keep the tone neutral and concise. Output plain text bullets separated by newline.
    Conversation:
    {transcript}
    """
)

TODO_PROMPT = textwrap.dedent(
    """
    You are Speakly's action item extractor.
    From the conversation below, produce a JSON array. Each element must contain:
      - "title": concise actionable next step
      - "due_hint": optional short phrase about timing (e.g. "by Friday") or null
      - "confidence": float between 0 and 1 representing your certainty that this is actionable
      - "source_excerpt": the exact quote that triggered the todo
    Only include clear action items. If none are present, return [] exactly.
    Conversation:
    {transcript}
    """
)


class LlmError(RuntimeError):
    pass


class LlmService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model_summary = settings.ollama_model_summary
        self.model_todo = settings.ollama_model_todo

    def is_enabled(self) -> bool:
        return bool(self.base_url)

    def _generate(self, prompt: str, model: str) -> str:
        if not self.base_url:
            raise LlmError("OLLAMA_BASE_URL not configured")

        url = f"{self.base_url.rstrip('/')}/api/generate"
        try:
            response = httpx.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network failures
            raise LlmError(str(exc)) from exc

        data = response.json()
        text = data.get("response")
        if not text:
            raise LlmError("Missing response from Ollama")
        return text.strip()

    def generate_summary(self, transcript: str) -> str:
        prompt = SUMMARY_PROMPT.format(transcript=transcript.strip())
        try:
            return self._generate(prompt, self.model_summary)
        except LlmError:
            logger.warning("Falling back to built-in summariser")
            sentences = transcript.split(".")
            return "\n".join(
                f"• {sentence.strip()}" for sentence in sentences[:3] if sentence.strip()
            )

    def extract_todos(self, transcript: str) -> list[dict[str, Any]]:
        prompt = TODO_PROMPT.format(transcript=transcript.strip())
        raw = None
        try:
            raw = self._generate(prompt, self.model_todo)
        except LlmError:
            logger.warning("Falling back to heuristic TODO generator")
            raw = "[]"

        try:
            todos = json.loads(raw)
            if isinstance(todos, list):
                return todos
        except json.JSONDecodeError:
            logger.warning("Todo extraction returned non JSON payload: %s", raw)

        return []


async def schedule_summary_and_todos(session_id: int, transcription_id: int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_summary_and_todos, session_id, transcription_id)


def _run_summary_and_todos(session_id: int, transcription_id: int) -> None:
    service = LlmService()
    if not service.is_enabled():
        logger.info("OLLAMA_BASE_URL not configured; skipping LLM jobs")
        return

    with SessionLocal() as db:
        session = db.query(SessionModel).filter_by(id=session_id).one_or_none()
        transcription = (
            db.query(Transcription).filter_by(id=transcription_id).one_or_none()
        )
        if not session or not transcription or not transcription.text:
            logger.warning(
                "Skipping LLM jobs; missing session/transcription text",
                extra={"extra_data": {"session_id": session_id, "transcription_id": transcription_id}},
            )
            return

        summary_run = LlmRun(
            session_id=session.id,
            transcription_id=transcription.id,
            run_type="summary",
            model=service.model_summary,
            prompt=SUMMARY_PROMPT,
        )
        db.add(summary_run)
        db.commit()
        db.refresh(summary_run)

        try:
            summary_text = service.generate_summary(transcription.text)
            summary_run.response = summary_text
            summary_run.status = "completed"
            session.summary_run = summary_run
        except Exception as exc:  # pragma: no cover - resilience
            summary_run.status = "error"
            summary_run.error = str(exc)
            logger.exception("Failed to generate summary")

        todo_run = LlmRun(
            session_id=session.id,
            transcription_id=transcription.id,
            run_type="todos",
            model=service.model_todo,
            prompt=TODO_PROMPT,
        )
        db.add(todo_run)
        db.commit()
        db.refresh(todo_run)

        todos_payload = []
        try:
            todos_payload = service.extract_todos(transcription.text)
            todo_run.response = json.dumps(todos_payload)
            todo_run.status = "completed"
        except Exception as exc:  # pragma: no cover
            todo_run.status = "error"
            todo_run.error = str(exc)
            logger.exception("Failed to extract todos")
            todos_payload = []

        confidence_threshold = settings.todo_confidence_threshold
        created = 0
        for todo in todos_payload:
            title = str(todo.get("title", "")).strip()
            if not title:
                continue
            confidence = todo.get("confidence")
            if confidence is not None and confidence < confidence_threshold:
                continue
            db.add(
                Todo(
                    session_id=session.id,
                    llm_run_id=todo_run.id,
                    title=title,
                    due_hint=(todo.get("due_hint") or None),
                    confidence=confidence,
                    status="pending",
                    source_start_ms=_safe_ms(todo.get("source_start_ms")),
                    source_end_ms=_safe_ms(todo.get("source_end_ms")),
                    source_excerpt=todo.get("source_excerpt"),
                )
            )
            created += 1

        if created:
            session.todo_count = (
                db.query(Todo).filter_by(session_id=session.id).count()
            )
        db.commit()


def _safe_ms(value: Any) -> int | None:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(float(value))
        return int(float(str(value)))
    except (TypeError, ValueError):  # pragma: no cover
        return None
