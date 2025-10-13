from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.models import Report, ReportCadence, ReportPreference, ReportStatus


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

    pref = test_db.query(ReportPreference).filter_by(user_id=data["user_id"]).one()
    assert pref.cadence is ReportCadence.WEEKLY
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
    assert pref.cadence is ReportCadence.MONTHLY
    assert pref.timezone == "America/New_York"


def test_list_reports_empty(journeys_client):
    response = journeys_client.get("/api/journeys/reports")

    assert response.status_code == 200
    data = response.json()
    assert data["reports"] == []
    assert data["total"] == 0


def test_trigger_report_generation_creates_placeholder(journeys_client, test_db):
    journeys_client.get("/api/journeys/preferences")

    payload = {"cadence": ReportCadence.WEEKLY.value}
    response = journeys_client.post("/api/journeys/reports/generate", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == ReportStatus.PENDING.value
    assert data["cadence"] == ReportCadence.WEEKLY.value

    # Validate the report exists in the database
    report_id = data["id"]
    report = test_db.get(Report, report_id)
    assert report is not None
    assert report.status is ReportStatus.PENDING
    assert report.period_start < report.period_end
