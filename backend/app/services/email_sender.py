from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import settings
from ..models import Report
from .journey_builder import JourneyBuildResult

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _build_html_content(build: JourneyBuildResult) -> str:
    metrics = build.metrics
    payload = build.payload

    sessions = payload.get("sessions", [])
    todos = payload.get("todos", {})
    top_tags = payload.get("top_tags", [])

    summary_html = (build.payload.get("summary") if isinstance(build.payload, dict) else "") or ""
    summary_html = str(summary_html).replace("\n", "<br>")

    lines = [
        "<html><body>",
        f"<h2>Your Journey Report ({metrics.period_start:%b %d} &rarr; {metrics.period_end:%b %d} {metrics.timezone})</h2>",
        f"<p>{build.metrics.session_count} session(s), {build.metrics.todo_created} task(s) captured.</p>",
        "<h3>Summary</h3>",
        f"<p>{summary_html}</p>",
        "<h3>Key Metrics</h3>",
        "<ul>",
        f"<li>Total listening time: {metrics.total_audio_minutes:.1f} minutes</li>",
        f"<li>Tasks completed: {metrics.todo_completed} / {metrics.todo_created}</li>",
        "</ul>",
    ]

    if top_tags:
        lines.append("<h3>Top Themes</h3><ul>")
        for tag in top_tags[:5]:
            lines.append(f"<li>{tag['name']} ({tag.get('category', 'tag')})</li>")
        lines.append("</ul>")

    if sessions:
        lines.append("<h3>Session Highlights</h3>")
        for session in sessions[:5]:
            summary = session.get("summary") or "(no summary)"
            lines.append(
                f"<p><strong>Session {session.get('id')}</strong>: {summary}<br>"
                f"Tasks: {session.get('todo_count', 0)} • Duration: {session.get('duration_minutes', 0)} min</p>"
            )

    if todos.get("highlights"):
        lines.append("<h3>Task Highlights</h3><ul>")
        for todo in todos["highlights"][:5]:
            lines.append(f"<li>{todo.get('title')} – status: {todo.get('status') or 'unknown'}</li>")
        lines.append("</ul>")

    lines.append("<p>You can view full details in Speakly.</p>")
    lines.append("</body></html>")
    return "".join(lines)


def send_journey_report_email(report: Report, build: JourneyBuildResult) -> None:
    if not settings.report_email_enabled:
        return
    if not settings.brevo_api_key:
        logger.debug("Brevo API key missing; skipping journey email")
        return
    if not settings.report_email_from_email:
        logger.debug("Report FROM email not set; skipping journey email")
        return

    user = report.user
    if not user or not user.email:
        logger.debug("User email missing for report %s; skipping", report.id)
        return

    preference = report.preference
    if preference and not preference.email_enabled:
        logger.debug("Email disabled for preference %s; skipping", preference.id)
        return

    subject = f"Your Speakly Journey • {build.metrics.period_start:%b %d} – {build.metrics.period_end:%b %d}"
    logger.info(
        f"Preparing journey email to email: {user.email}",
        extra={
            "report_id": report.id,
            "user_id": user.id,
            "email": user.email,
            "timezone": build.metrics.timezone,
        },
    )
    html_content = _build_html_content(build)

    payload: dict[str, Any] = {
        "sender": {
            "name": settings.report_email_from_name or "Speakly",
            "email": settings.report_email_from_email,
        },
        "to": [{"email": user.email, "name": user.name or user.email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                BREVO_API_URL,
                json=payload,
                headers={
                    "api-key": settings.brevo_api_key,
                    "accept": "application/json",
                    "content-type": "application/json",
                },
            )
            response.raise_for_status()
            logger.info("Journey email sent", extra={"report_id": report.id, "user_id": user.id})
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Brevo send failed: %s", exc.response.text[:200], extra={"report_id": report.id}
        )
    except Exception:
        logger.exception("Unexpected error sending journey email", extra={"report_id": report.id})
