from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Iterable, Sequence
import calendar

from sqlalchemy.orm import Session

from ..models import Report, ReportCadence, ReportPreference, ReportStatus
from .journey_builder import JourneyReportBuilder
from .journey_summary import JourneySummaryGenerator
from .email_sender import send_journey_report_email


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


def calculate_period_bounds(
    reference: datetime, cadence: ReportCadence, timezone: str | ZoneInfo | None = None
) -> tuple[datetime, datetime]:
    """Return (start, end) window for a cadence ending at `reference`.

    Results are returned as naive UTC datetimes for database storage.
    """
    tzinfo: ZoneInfo
    if timezone:
        try:
            tzinfo = ZoneInfo(timezone) if isinstance(timezone, str) else timezone
        except ZoneInfoNotFoundError:
            tzinfo = ZoneInfo("UTC")
    else:
        tzinfo = ZoneInfo("UTC")

    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    else:
        reference = reference.astimezone(UTC)

    local_end = reference.astimezone(tzinfo)
    local_end = local_end.replace(second=0, microsecond=0)

    if cadence is ReportCadence.DAILY:
        start_local = local_end.replace(hour=0, minute=0, second=0, microsecond=0)
    elif cadence is ReportCadence.WEEKLY:
        start_local = (local_end - timedelta(weeks=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif cadence is ReportCadence.BIWEEKLY:
        start_local = (local_end - timedelta(weeks=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif cadence is ReportCadence.MONTHLY:
        start_local = _add_months(local_end, -1).replace(hour=0, minute=0, second=0, microsecond=0)
    elif cadence is ReportCadence.QUARTERLY:
        start_local = _add_months(local_end, -3).replace(hour=0, minute=0, second=0, microsecond=0)
    elif cadence is ReportCadence.YEARLY:
        start_local = _add_months(local_end, -12).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start_local = (local_end - timedelta(weeks=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    start_utc = start_local.astimezone(UTC).replace(tzinfo=None)
    end_utc = local_end.astimezone(UTC).replace(tzinfo=None)
    return start_utc, end_utc


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
        email_enabled: bool = True,
    ) -> ReportPreference:
        preference = self.get_preference(user_id=user_id)
        now = datetime.utcnow()

        if preference is None:
            preference = ReportPreference(
                user_id=user_id,
                cadence=cadence.value,
                timezone=timezone,
                delivery_channels=list(delivery_channels or []),
                is_active=is_active,
                email_enabled=email_enabled,
                last_generated_at=None,
                next_scheduled_at=_calculate_next_run(now, cadence),
            )
            self.db.add(preference)
        else:
            preference.cadence = cadence.value
            preference.timezone = timezone
            preference.delivery_channels = list(delivery_channels or [])
            preference.is_active = is_active
            preference.email_enabled = email_enabled
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
            query = query.filter(Report.cadence.in_([c.value for c in cadences]))

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
            query = query.filter(Report.cadence.in_([c.value for c in cadences]))
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
            cadence=cadence.value,
            period_start=period_start,
            period_end=period_end,
            status=ReportStatus.PENDING.value,
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
        report.status = status.value if isinstance(status, ReportStatus) else status
        if summary is not None:
            report.summary = summary
        if payload is not None:
            report.payload = payload
        if metadata is not None:
            report.metadata_payload = metadata
        if status is ReportStatus.COMPLETED:
            report.generated_at = datetime.utcnow()
        self.db.flush()
        return report

    def generate_report(self, report: Report) -> Report:
        builder = JourneyReportBuilder(self.db)
        summary_generator = JourneySummaryGenerator()

        self.mark_report_progress(report=report, status=ReportStatus.IN_PROGRESS)
        timezone_name = report.preference.timezone if report.preference else "UTC"
        result = builder.build(report, timezone_name)
        summary_text = summary_generator.generate(result)
        period_info = result.payload.setdefault("metrics", {}).setdefault("period", {})
        period_info.setdefault("timezone", timezone_name)
        result.payload.setdefault("summary", summary_text)

        self.mark_report_progress(
            report=report,
            status=ReportStatus.COMPLETED,
            summary=summary_text,
            payload=result.payload,
        )
        send_journey_report_email(report, result)
        self._update_preference_after_generation(report)
        return report

    def get_due_preferences(self, now: datetime) -> list[ReportPreference]:
        return (
            self.db.query(ReportPreference)
            .filter(ReportPreference.is_active.is_(True))
            .filter(
                (ReportPreference.next_scheduled_at == None)
                | (ReportPreference.next_scheduled_at <= now)
            )
            .all()
        )

    def has_report_for_period(
        self, *, user_id: int, cadence: ReportCadence, period_start: datetime, period_end: datetime
    ) -> bool:
        return (
            self.db.query(Report)
            .filter(Report.user_id == user_id)
            .filter(Report.cadence == cadence.value)
            .filter(Report.period_start == period_start)
            .filter(Report.period_end == period_end)
            .first()
            is not None
        )

    def _update_preference_after_generation(self, report: Report) -> None:
        preference = report.preference
        if not preference:
            return
        try:
            cadence = ReportCadence(preference.cadence)
        except ValueError:
            cadence = ReportCadence.WEEKLY
        preference.last_generated_at = datetime.utcnow()
        preference.next_scheduled_at = _calculate_next_run(report.period_end, cadence)
        self.db.flush()


def get_journey_service(db: Session) -> JourneyReportService:
    return JourneyReportService(db)


__all__ = [
    "JourneyReportService",
    "get_journey_service",
    "ReportCadence",
    "ReportStatus",
    "calculate_period_bounds",
]
