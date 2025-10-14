from __future__ import annotations

import asyncio
import logging
from datetime import datetime, UTC

from ..database import SessionLocal
from ..models import ReportCadence
from ..services import JourneyReportService, calculate_period_bounds

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None


def _generate_due_reports_sync() -> None:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        service = JourneyReportService(db)
        due = service.get_due_preferences(now)
        if not due:
            return

        generated = 0
        for preference in due:
            try:
                cadence = ReportCadence(preference.cadence)
            except ValueError:
                cadence = ReportCadence.WEEKLY

            timezone_name = preference.timezone or "UTC"
            period_start, period_end = calculate_period_bounds(now, cadence, timezone_name)

            if service.has_report_for_period(
                user_id=preference.user_id,
                cadence=cadence,
                period_start=period_start,
                period_end=period_end,
            ):
                preference.next_scheduled_at = preference.next_scheduled_at or period_end
                continue

            report = service.create_report_placeholder(
                user_id=preference.user_id,
                cadence=cadence,
                period_start=period_start,
                period_end=period_end,
                preference=preference,
            )
            service.generate_report(report)
            generated += 1

        if generated:
            logger.info(
                "Journeys scheduler generated reports",
                extra={"count": generated},
            )
        db.commit()


async def _journey_scheduler_loop(interval_seconds: int = 900) -> None:
    logger.info("Journeys scheduler loop started", extra={"interval_seconds": interval_seconds})
    while True:
        try:
            await asyncio.to_thread(_generate_due_reports_sync)
        except Exception:
            logger.exception("Journeys scheduler encountered an error")
        await asyncio.sleep(interval_seconds)


def start_journey_scheduler() -> None:
    global _scheduler_task
    loop = asyncio.get_running_loop()
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = loop.create_task(_journey_scheduler_loop())


def stop_journey_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
