from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from ..models import Session as SessionModel
from ..models import Transcription, Todo, SessionTag, Tag, Report


@dataclass
class JourneyMetrics:
    session_count: int
    completed_sessions: int
    total_audio_minutes: float
    average_session_minutes: float
    todo_created: int
    todo_completed: int
    top_tags: list[dict[str, Any]]
    periods: dict[str, str]


class JourneyReportBuilder:
    """Aggregate metrics for Journey reports."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def build_metrics(self, *, user_id: int, period_start: datetime, period_end: datetime) -> JourneyMetrics:
        session_query = (
            self.db.query(SessionModel)
            .filter(SessionModel.user_id == user_id)
            .filter(SessionModel.created_at >= period_start)
            .filter(SessionModel.created_at <= period_end)
        )

        session_count = session_query.count()
        completed_sessions = session_query.filter(SessionModel.status == "completed").count()

        total_duration_ms = (
            self.db.query(func.coalesce(func.sum(Transcription.duration_ms), 0))
            .join(SessionModel, Transcription.session_id == SessionModel.id)
            .filter(SessionModel.user_id == user_id)
            .filter(SessionModel.created_at >= period_start)
            .filter(SessionModel.created_at <= period_end)
            .scalar()
        ) or 0

        total_minutes = total_duration_ms / 1000 / 60 if total_duration_ms else 0.0
        average_minutes = total_minutes / session_count if session_count else 0.0

        todo_query = (
            self.db.query(Todo)
            .join(SessionModel, Todo.session_id == SessionModel.id)
            .filter(SessionModel.user_id == user_id)
            .filter(SessionModel.created_at >= period_start)
            .filter(SessionModel.created_at <= period_end)
        )
        todo_created = todo_query.count()
        todo_completed = todo_query.filter(Todo.status == "completed").count()

        tag_rows = (
            self.db.query(Tag.name, Tag.category, func.count(SessionTag.id).label("count"))
            .join(SessionTag.tag)
            .join(SessionTag.session)
            .filter(SessionModel.user_id == user_id)
            .filter(SessionModel.created_at >= period_start)
            .filter(SessionModel.created_at <= period_end)
            .group_by(Tag.id)
            .order_by(desc("count"))
            .limit(5)
            .all()
        )
        top_tags = [
            {
                "name": row.name,
                "category": row.category,
                "count": int(row.count),
            }
            for row in tag_rows
        ]

        return JourneyMetrics(
            session_count=session_count,
            completed_sessions=completed_sessions,
            total_audio_minutes=round(total_minutes, 2),
            average_session_minutes=round(average_minutes, 2),
            todo_created=todo_created,
            todo_completed=todo_completed,
            top_tags=top_tags,
            periods={
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
        )

    def build_payload(self, report: Report) -> dict[str, Any]:
        metrics = self.build_metrics(
            user_id=report.user_id,
            period_start=report.period_start,
            period_end=report.period_end,
        )

        summary = self._compose_summary(report, metrics)

        return {
            "summary": summary,
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
                },
                "top_tags": metrics.top_tags,
                "period": metrics.periods,
            },
        }

    def _compose_summary(self, report: Report, metrics: JourneyMetrics) -> str:
        parts = [
            f"You recorded {metrics.session_count} session(s) between {report.period_start:%b %d} and {report.period_end:%b %d}.",
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
                todo_line += f", with {metrics.todo_completed} already completed"
            parts.append(todo_line + ".")
        if metrics.top_tags:
            tag_names = ", ".join(tag["name"] for tag in metrics.top_tags[:3])
            parts.append(f"Top themes: {tag_names}.")

        return " ".join(parts)


__all__ = ["JourneyReportBuilder", "JourneyMetrics"]
