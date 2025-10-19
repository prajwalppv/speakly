from __future__ import annotations

import logging
from typing import Any

from .journey_builder import JourneyBuildResult, JourneyMetrics

try:  # pragma: no cover - optional LLM dependency
    from .llm import LlmError, LlmService
except Exception:  # pragma: no cover
    LlmService = None  # type: ignore
    LlmError = Exception  # type: ignore


logger = logging.getLogger(__name__)


class JourneySummaryGenerator:
    """Create a narrative summary for a Journey report."""

    def __init__(self) -> None:
        self._llm: LlmService | None = None
        if LlmService is not None:
            try:
                candidate = LlmService()
                if candidate.is_enabled():
                    self._llm = candidate
            except Exception:
                logger.info("LLM service unavailable; using fallback summaries")

    def generate(self, build_result: JourneyBuildResult) -> str:
        if self._llm:
            try:
                return self._llm.generate_summary(self._compose_prompt(build_result))
            except LlmError:
                logger.warning(
                    "LLM summary generation failed; using fallback narrative"
                )
            except Exception:
                logger.exception("Unexpected error during LLM summary generation")

        return self._fallback_summary(build_result.metrics, build_result.payload)

    def _compose_prompt(self, build_result: JourneyBuildResult) -> str:
        metrics = build_result.metrics
        prompt_lines = [
            "You are generating a multi-session report summary. Summarize concisely in 3-4 paragraphs.",
            f"Time range: {metrics.period_start:%Y-%m-%d} to {metrics.period_end:%Y-%m-%d} ({metrics.timezone}).",
            f"Sessions: {metrics.session_count} total; {metrics.completed_sessions} completed; total {metrics.total_audio_minutes:.1f} minutes.",
            f"Tasks: {metrics.todo_created} captured; {metrics.todo_completed} completed.",
            (
                "Key themes: " + ", ".join(tag["name"] for tag in metrics.top_tags)
                if metrics.top_tags
                else "No tags captured."
            ),
            "Detailed context:\n" + build_result.context_text,
            "Focus on trends, notable sessions, and task outcomes. Keep it under 180 words.",
        ]
        return "\n".join(prompt_lines)

    def _fallback_summary(
        self, metrics: JourneyMetrics, payload: dict[str, Any]
    ) -> str:
        parts = [
            f"Recorded {metrics.session_count} session(s) between {metrics.period_start:%b %d} and {metrics.period_end:%b %d} ({metrics.timezone}).",
        ]
        if metrics.completed_sessions:
            parts.append(f"{metrics.completed_sessions} reached the completed state.")
        if metrics.total_audio_minutes:
            parts.append(
                f"Total listening time was {metrics.total_audio_minutes:.1f} minutes (avg {metrics.average_session_minutes:.1f} per session)."
            )
        if metrics.todo_created:
            todo_line = f"Captured {metrics.todo_created} task(s)"
            if metrics.todo_completed:
                todo_line += f", with {metrics.todo_completed} completed"
            parts.append(todo_line + ".")
        if metrics.top_tags:
            tag_names = ", ".join(tag["name"] for tag in metrics.top_tags[:3])
            parts.append(f"Top themes: {tag_names}.")

        sessions = payload.get("sessions", [])
        for session in sessions[:3]:
            summary = session.get("summary")
            if summary:
                parts.append(f"Session {session['id']}: {summary}")

        return " ".join(parts)


__all__ = ["JourneySummaryGenerator"]
