from __future__ import annotations

from datetime import datetime, timedelta

from app.config import settings
from app.models import (
    Report,
    ReportCadence,
    ReportPreference,
    ReportStatus,
    Session,
    SessionTag,
    Tag,
    Todo,
    Transcription,
    User,
)
from app.services import JourneyReportService, calculate_period_bounds


def test_journeys_feature_disabled(client):
    settings.feature_report_generation = False

    response = client.get("/api/journeys/preferences")

    assert response.status_code == 404


def test_get_preference_creates_default(journeys_client, test_db):
    response = journeys_client.get("/api/journeys/preferences")

    assert response.status_code == 200
    data = response.json()
    assert data["cadence"] == ReportCadence.WEEKLY.value
    assert data["timezone"] == "UTC"
    assert data["is_active"] is True
    assert data["email_enabled"] is True

    pref = test_db.query(ReportPreference).filter_by(user_id=data["user_id"]).one()
    assert pref.cadence == ReportCadence.WEEKLY.value
    assert pref.next_scheduled_at is not None


def test_update_preference(journeys_client, test_db):
    journeys_client.get("/api/journeys/preferences")

    payload = {
        "cadence": ReportCadence.MONTHLY.value,
        "timezone": "America/New_York",
        "delivery_channels": ["email"],
        "is_active": False,
    }
    response = journeys_client.put("/api/journeys/preferences", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["cadence"] == payload["cadence"]
    assert data["timezone"] == payload["timezone"]
    assert data["delivery_channels"] == payload["delivery_channels"]
    assert data["is_active"] is False

    pref = test_db.query(ReportPreference).filter_by(user_id=data["user_id"]).one()
    assert pref.cadence == ReportCadence.MONTHLY.value
    assert pref.timezone == "America/New_York"


def test_list_reports_empty(journeys_client):
    response = journeys_client.get("/api/journeys/reports")

    assert response.status_code == 200
    data = response.json()
    assert data["reports"] == []
    assert data["total"] == 0


def _seed_journey_data(test_db):
    user = test_db.query(User).filter_by(name="default").one()
    now = datetime.utcnow()
    earlier = now - timedelta(days=2)

    session = Session(
        user_id=user.id,
        description="Weekly sync",
        status="completed",
        created_at=earlier,
        updated_at=now,
        has_pj=False,
        todo_count=2,
    )
    test_db.add(session)
    test_db.flush()

    transcription = Transcription(
        session_id=session.id,
        provider="mock",
        status="completed",
        text="Discussed roadmap and deliverables",
        created_at=earlier,
        updated_at=earlier,
        duration_ms=900000,
    )
    test_db.add(transcription)
    test_db.flush()

    from app.models import LlmRun  # local import to avoid circular.

    llm_run = LlmRun(
        session_id=session.id,
        transcription_id=transcription.id,
        run_type="summary",
        model="mock",
        prompt="",
        response="",
        status="completed",
        created_at=earlier,
        updated_at=earlier,
    )
    test_db.add(llm_run)
    test_db.flush()

    # minimal todo entries
    todo1 = Todo(
        session_id=session.id,
        llm_run_id=llm_run.id,
        title="Send summary email",
        status="completed",
        created_at=now,
        updated_at=now,
    )
    test_db.add(todo1)

    todo2 = Todo(
        session_id=session.id,
        llm_run_id=llm_run.id,
        title="Prepare deck",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    test_db.add(todo2)

    tag = Tag(
        name="planning",
        category="topic",
        color="#ffcc00",
        auto_generated=True,
        created_at=now,
        updated_at=now,
    )
    test_db.add(tag)
    test_db.flush()

    session_tag = SessionTag(
        session_id=session.id,
        tag_id=tag.id,
        confidence=0.9,
        auto_generated=True,
        created_at=now,
        updated_at=now,
    )
    test_db.add(session_tag)
    test_db.commit()


def test_generate_report_updates_schedule(journeys_client, test_db, monkeypatch):
    monkeypatch.setattr(
        "app.services.journeys.send_journey_report_email", lambda report, payload: None
    )
    journeys_client.get("/api/journeys/preferences")
    _seed_journey_data(test_db)

    service = JourneyReportService(test_db)
    pref = service.get_preference(user_id=1)
    assert pref is not None

    period_start, period_end = calculate_period_bounds(
        datetime.utcnow(), ReportCadence.WEEKLY
    )
    report = service.create_report_placeholder(
        user_id=1,
        cadence=ReportCadence.WEEKLY,
        period_start=period_start,
        period_end=period_end,
        preference=pref,
    )
    service.generate_report(report)

    assert pref.last_generated_at is not None
    assert pref.next_scheduled_at is not None


def test_trigger_report_generation_populates_report(
    journeys_client, test_db, monkeypatch
):
    email_called: dict[str, bool] = {"value": False}

    def fake_send(report, payload):
        email_called["value"] = True

    monkeypatch.setattr("app.services.journeys.send_journey_report_email", fake_send)

    journeys_client.get("/api/journeys/preferences")
    _seed_journey_data(test_db)

    payload = {"cadence": ReportCadence.WEEKLY.value}
    response = journeys_client.post("/api/journeys/reports/generate", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == ReportStatus.COMPLETED.value
    assert data["cadence"] == ReportCadence.WEEKLY.value
    assert data["summary"]
    assert data["payload"]["metrics"]["sessions"]["total"] >= 1

    report = test_db.get(Report, data["id"])
    assert report is not None
    assert report.status == ReportStatus.COMPLETED.value
    assert report.summary
    assert report.payload
    assert email_called["value"] is True
