from __future__ import annotations
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, selectinload

from ..models import Report, Session as SessionModel, SessionTag, Tag, Todo


@dataclass
class JourneyMetrics:
    session_count: int
    completed_sessions: int
    total_audio_minutes: float
    average_session_minutes: float
    todo_created: int
    todo_completed: int
    top_tags: list[dict[str, Any]]
    period_start: datetime
    period_end: datetime


@dataclass
class JourneyBuildResult:
    payload: dict[str, Any]
    metrics: JourneyMetrics
    context_text: str


class JourneyReportBuilder:
    """Aggregate metrics and context for Journey reports."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self, report: Report) -> JourneyBuildResult:
        sessions = (
            self.db.query(SessionModel)
            .filter(SessionModel.user_id == report.user_id)
            .filter(SessionModel.created_at >= report.period_start)
            .filter(SessionModel.created_at <= report.period_end)
            .options(
                selectinload(SessionModel.transcriptions),
                selectinload(SessionModel.todos),
                selectinload(SessionModel.summary_run),
                selectinload(SessionModel.session_tags).selectinload(SessionTag.tag),
            )
            .order_by(SessionModel.created_at)
            .all()
        )

        metrics = self._compute_metrics(report, sessions)
        session_payload, sessions_context = self._build_session_payload(sessions)
        todo_payload, todos_context = self._build_todo_payload(report, sessions)
        tag_payload = metrics.top_tags

        payload = {
            "metrics": {
                "sessions": {
                    "total": metrics.session_count,
                    "completed": metrics.completed_sessions,
                    "average_minutes": metrics.average_session_minutes,
                    "total_minutes": metrics.total_audio_minutes,
                },
                "todos": {
                    "created": metrics.todo_created,
                    "completed": metrics.todo_completed,
                    "completion_rate": self._completion_rate(metrics),
                },
                "period": {
                    "start": metrics.period_start.isoformat(),
                    "end": metrics.period_end.isoformat(),
                },
                "top_tags": tag_payload,
            },
            "sessions": session_payload,
            "todos": todo_payload,
            "top_tags": tag_payload,
        }

        context_lines = [
            f"Between {report.period_start:%b %d} and {report.period_end:%b %d} there were {metrics.session_count} session(s); {metrics.completed_sessions} completed.",
            f"Total listening time: {metrics.total_audio_minutes:.1f} minutes (avg {metrics.average_session_minutes:.1f}).",
            f"Tasks captured: {metrics.todo_created} created, {metrics.todo_completed} completed.",
        ]
        context_lines.extend(sessions_context)
        context_lines.extend(todos_context)
        context_text = "\n".join(context_lines)

        return JourneyBuildResult(payload=payload, metrics=metrics, context_text=context_text)

    def _compute_metrics(self, report: Report, sessions: list[SessionModel]) -> JourneyMetrics:
        session_count = len(sessions)
        completed_sessions = sum(1 for session in sessions if session.status == "completed")

        total_duration_ms = 0
        for session in sessions:
            for transcription in session.transcriptions:
                if transcription.duration_ms:
                    total_duration_ms += transcription.duration_ms

        total_minutes = total_duration_ms / 1000 / 60 if total_duration_ms else 0.0
        average_minutes = total_minutes / session_count if session_count else 0.0

        todos = [
            todo
            for session in sessions
            for todo in session.todos
            if todo.created_at is None
            or (report.period_start <= todo.created_at <= report.period_end)
        ]
        todo_created = len(todos)
        todo_completed = sum(1 for todo in todos if (todo.status or "").lower() == "completed")

        tag_counts: dict[str, dict[str, Any]] = {}
        for session in sessions:
            for session_tag in session.session_tags:
                tag = session_tag.tag
                if not tag:
                    continue
                entry = tag_counts.setdefault(
                    tag.name,
                    {"name": tag.name, "category": tag.category, "count": 0},
                )
                entry["count"] += 1
        top_tags = sorted(tag_counts.values(), key=lambda item: item["count"], reverse=True)[:5]

        return JourneyMetrics(
            session_count=session_count,
            completed_sessions=completed_sessions,
            total_audio_minutes=round(total_minutes, 2),
            average_session_minutes=round(average_minutes, 2),
            todo_created=todo_created,
            todo_completed=todo_completed,
            top_tags=top_tags,
            period_start=report.period_start,
            period_end=report.period_end,
        )

    def _build_session_payload(self, sessions: list[SessionModel]) -> tuple[list[dict[str, Any]], list[str]]:
        items: list[dict[str, Any]] = []
        context_lines: list[str] = []

        for session in sessions:
            duration_minutes = 0.0
            for transcription in session.transcriptions:
                if transcription.duration_ms:
                    duration_minutes += transcription.duration_ms / 1000 / 60

            summary_text = None
            if session.summary_run and session.summary_run.response:
                summary_text = session.summary_run.response.strip()
            elif session.description:
                summary_text = session.description.strip()
            elif session.transcriptions:
                text = session.transcriptions[0].text or ""
                summary_text = text[:160] + "..." if len(text) > 160 else text

            tags = [
                {"name": st.tag.name, "category": st.tag.category}  # type: ignore[union-attr]
                for st in session.session_tags
                if st.tag
            ]

            items.append(
                {
                    "id": session.id,
                    "created_at": session.created_at.isoformat(),
                    "status": session.status,
                    "todo_count": len(session.todos),
                    "duration_minutes": round(duration_minutes, 2),
                    "summary": summary_text,
                    "tags": tags,
                }
            )

            if summary_text:
                context_lines.append(f"Session {session.id}: {summary_text}")

        return items, context_lines

    def _build_todo_payload(
        self, report: Report, sessions: list[SessionModel]
    ) -> tuple[dict[str, Any], list[str]]:
        todos = [
            todo
            for session in sessions
            for todo in session.todos
            if todo.created_at is None
            or (report.period_start <= todo.created_at <= report.period_end)
        ]

        completion_count = sum(1 for todo in todos if (todo.status or "").lower() == "completed")
        open_count = sum(1 for todo in todos if (todo.status or "").lower() != "completed")
        top_todos = sorted(
            todos,
            key=lambda todo: todo.created_at or report.period_end,
            reverse=True,
        )[:5]

        todo_entries = [
            {
                "title": todo.title,
                "status": todo.status,
                "confidence": todo.confidence,
                "created_at": todo.created_at.isoformat() if todo.created_at else None,
            }
            for todo in top_todos
        ]

        context_lines = [
            f"Tasks captured during the period: {len(todos)}.",
            f"{completion_count} marked completed, {open_count} still open.",
        ]
        for entry in todo_entries[:3]:
            context_lines.append(f"Task \"{entry['title']}\" status {entry['status']}.")

        payload = {
            "created": len(todos),
            "completed": completion_count,
            "open": open_count,
            "highlights": todo_entries,
        }
        return payload, context_lines

    def _completion_rate(self, metrics: JourneyMetrics) -> float:
        if metrics.todo_created == 0:
            return 0.0
        return round((metrics.todo_completed / metrics.todo_created) * 100, 2)


__all__ = ["JourneyReportBuilder", "JourneyBuildResult", "JourneyMetrics"]
