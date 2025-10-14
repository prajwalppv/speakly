from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_session
from ..models import Report, ReportCadence, ReportStatus, User
from ..schemas import (
    ReportGenerateRequest,
    ReportListResponse,
    ReportPreferenceRequest,
    ReportPreferenceResponse,
    ReportResponse,
)
from ..services import (
    JourneyReportService,
    calculate_period_bounds,
    get_journey_service,
    ReportStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/journeys", tags=["journeys"])


def _ensure_feature_enabled() -> None:
    if not settings.feature_report_generation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


@router.get("/preferences", response_model=ReportPreferenceResponse)
def get_journey_preference(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> ReportPreferenceResponse:
    _ensure_feature_enabled()
    service = get_journey_service(db)
    preference = service.get_preference(user_id=current_user.id)
    if preference is None:
        preference = service.ensure_preference(
            user_id=current_user.id,
            cadence=ReportCadence.WEEKLY,
            timezone="UTC",
        )
        db.commit()
    return preference


@router.put("/preferences", response_model=ReportPreferenceResponse)
def update_journey_preference(
    payload: ReportPreferenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> ReportPreferenceResponse:
    _ensure_feature_enabled()
    service = get_journey_service(db)
    timezone = payload.timezone or "UTC"
    preference = service.ensure_preference(
        user_id=current_user.id,
        cadence=payload.cadence,
        timezone=timezone,
        delivery_channels=payload.delivery_channels,
        is_active=payload.is_active,
        email_enabled=payload.email_enabled,
    )
    db.commit()
    return preference


@router.get("/reports", response_model=ReportListResponse)
def list_journey_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    cadence: list[ReportCadence] | None = Query(default=None),
) -> ReportListResponse:
    _ensure_feature_enabled()
    service = get_journey_service(db)

    reports = service.list_reports(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        cadences=cadence,
    )
    reports.sort(key=lambda report: report.period_end, reverse=True)
    total = service.count_reports(user_id=current_user.id, cadences=cadence)

    return ReportListResponse(reports=reports, total=total)


@router.post("/reports/generate", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_journey_report_generation(
    payload: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> ReportResponse:
    _ensure_feature_enabled()
    service: JourneyReportService = get_journey_service(db)

    preference = service.get_preference(user_id=current_user.id)
    if preference is None:
        preference = service.ensure_preference(
            user_id=current_user.id,
            cadence=ReportCadence.WEEKLY,
            timezone="UTC",
        )

    try:
        preference_cadence = ReportCadence(preference.cadence)
    except ValueError:
        preference_cadence = ReportCadence.WEEKLY

    cadence_enum = payload.cadence or preference_cadence
    tz_name = preference.timezone or "UTC"

    end_reference = payload.period_end or datetime.utcnow()
    if payload.period_start and payload.period_end:
        period_start, period_end = payload.period_start, payload.period_end
    else:
        period_start, period_end = calculate_period_bounds(end_reference, cadence_enum, tz_name)

    if period_start >= period_end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid period range")

    report = service.create_report_placeholder(
        user_id=current_user.id,
        cadence=cadence_enum,
        period_start=period_start,
        period_end=period_end,
        preference=preference if preference.cadence == cadence_enum.value else None,
    )

    logger.info(
        "Journeys report requested",
        extra={
            "extra_data": {
                "user_id": current_user.id,
                "report_id": report.id,
                "cadence": cadence_enum.value,
                "timezone": tz_name,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            }
        },
    )

    try:
        report = service.generate_report(report)
        db.commit()
    except Exception as exc:  # pragma: no cover - unexpected errors logged
        logger.exception("Failed to generate journey report", extra={"report_id": report.id})
        service.mark_report_progress(report=report, status=ReportStatus.FAILED, summary=str(exc))
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to generate report") from exc

    db.refresh(report)
    return report


@router.delete("/reports/{report_id}", status_code=status.HTTP_200_OK)
def delete_journey_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> None:
    _ensure_feature_enabled()
    report = db.query(Report).filter(Report.id == report_id, Report.user_id == current_user.id).one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
