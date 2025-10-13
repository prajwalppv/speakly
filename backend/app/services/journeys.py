from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Sequence
import calendar

from sqlalchemy.orm import Session

from ..models import Report, ReportCadence, ReportPreference, ReportStatus


def _add_months(base: datetime, months: int) -> datetime:
    """Return `base` plus `months`, preserving day when possible."""
    month = base.month - 1 + months
    year = base.year + month // 12
    month = month % 12 + 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    return base.replace(year=year, month=month, day=day)


def _calculate_next_run(start: datetime, cadence: ReportCadence) -> datetime:
    """Calculate next scheduled execution based on cadence."""
    if cadence is ReportCadence.DAILY:
        return start + timedelta(days=1)
    if cadence is ReportCadence.WEEKLY:
        return start + timedelta(weeks=1)
    if cadence is ReportCadence.BIWEEKLY:
        return start + timedelta(weeks=2)
    if cadence is ReportCadence.MONTHLY:
        return _add_months(start, 1)
    if cadence is ReportCadence.QUARTERLY:
        return _add_months(start, 3)
    if cadence is ReportCadence.YEARLY:
        return _add_months(start, 12)
    return start + timedelta(weeks=1)


def calculate_period_bounds(reference: datetime, cadence: ReportCadence) -> tuple[datetime, datetime]:
    """Return (start, end) window for a cadence ending at `reference`."""
    end = reference
    if cadence is ReportCadence.DAILY:
        start = end - timedelta(days=1)
    elif cadence is ReportCadence.WEEKLY:
        start = end - timedelta(weeks=1)
    elif cadence is ReportCadence.BIWEEKLY:
        start = end - timedelta(weeks=2)
    elif cadence is ReportCadence.MONTHLY:
        start = _add_months(end, -1)
    elif cadence is ReportCadence.QUARTERLY:
        start = _add_months(end, -3)
    elif cadence is ReportCadence.YEARLY:
        start = _add_months(end, -12)
    else:
        start = end - timedelta(weeks=1)

    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(microsecond=0)
    return start, end


class JourneyReportService:
    """Data access and orchestration helpers for Journeys."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_preference(self, *, user_id: int) -> ReportPreference | None:
        return (
            self.db.query(ReportPreference)
            .filter(ReportPreference.user_id == user_id)
            .one_or_none()
        )

    def ensure_preference(
        self,
        *,
        user_id: int,
        cadence: ReportCadence,
        timezone: str = "UTC",
        delivery_channels: Iterable[str] | None = None,
        is_active: bool = True,
    ) -> ReportPreference:
        preference = self.get_preference(user_id=user_id)
        now = datetime.utcnow()

        if preference is None:
            preference = ReportPreference(
                user_id=user_id,
                cadence=cadence,
                timezone=timezone,
                delivery_channels=list(delivery_channels or []),
                is_active=is_active,
                last_generated_at=None,
                next_scheduled_at=_calculate_next_run(now, cadence),
            )
            self.db.add(preference)
        else:
            preference.cadence = cadence
            preference.timezone = timezone
            preference.delivery_channels = list(delivery_channels or [])
            preference.is_active = is_active
            preference.next_scheduled_at = _calculate_next_run(now, cadence)

        self.db.flush()
        self.db.refresh(preference)
        return preference

    def list_reports(
        self,
        *,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        cadences: Sequence[ReportCadence] | None = None,
    ) -> list[Report]:
        query = self.db.query(Report).filter(Report.user_id == user_id)
        if cadences:
            query = query.filter(Report.cadence.in_(cadences))

        return (
            query.order_by(Report.period_start.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_reports(
        self,
        *,
        user_id: int,
        cadences: Sequence[ReportCadence] | None = None,
    ) -> int:
        query = self.db.query(Report).filter(Report.user_id == user_id)
        if cadences:
            query = query.filter(Report.cadence.in_(cadences))
        return query.count()

    def create_report_placeholder(
        self,
        *,
        user_id: int,
        cadence: ReportCadence,
        period_start: datetime,
        period_end: datetime,
        preference: ReportPreference | None = None,
    ) -> Report:
        report = Report(
            user_id=user_id,
            cadence=cadence,
            period_start=period_start,
            period_end=period_end,
            status=ReportStatus.PENDING,
            preference=preference,
        )
        self.db.add(report)
        self.db.flush()
        self.db.refresh(report)
        return report

    def mark_report_progress(
        self,
        *,
        report: Report,
        status: ReportStatus,
        summary: str | None = None,
        payload: dict | None = None,
        metadata: dict | None = None,
    ) -> Report:
        report.status = status
        if summary is not None:
            report.summary = summary
        if payload is not None:
            report.payload = payload
        if metadata is not None:
            report.metadata_payload = metadata
        if status is ReportStatus.COMPLETED:
            report.generated_at = datetime.utcnow()
        self.db.flush()
        self.db.refresh(report)
        return report


def get_journey_service(db: Session) -> JourneyReportService:
    return JourneyReportService(db)


__all__ = [
    "JourneyReportService",
    "get_journey_service",
    "ReportCadence",
    "ReportStatus",
    "calculate_period_bounds",
]
