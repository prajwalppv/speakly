from backend.app.auth import _extract_email_from_payload, _select_email_from_addresses


def test_extract_email_direct_field():
    payload = {"email": "user@example.com"}
    assert _extract_email_from_payload(payload) == "user@example.com"


def test_extract_email_from_primary_address():
    payload = {
        "primary_email_address_id": "idn_primary",
        "email_addresses": [
            {"id": "idn_primary", "email_address": "primary@example.com"},
            {"id": "idn_other", "email_address": "other@example.com"},
        ],
    }
    assert _extract_email_from_payload(payload) == "primary@example.com"


def test_selects_verified_email_when_primary_missing():
    email_addresses = [
        {"id": "idn_a", "email_address": "unverified@example.com"},
        {
            "id": "idn_b",
            "email_address": "verified@example.com",
            "verification": {"status": "verified"},
        },
    ]
    assert (
        _select_email_from_addresses(email_addresses, primary_id=None)
        == "verified@example.com"
    )


def test_extract_email_falls_back_to_first_available():
    payload = {
        "email_addresses": [
            {"id": "idn_a", "email_address": "first@example.com"},
            {"id": "idn_b", "email_address": "second@example.com"},
        ]
    }
    assert _extract_email_from_payload(payload) == "first@example.com"


def test_extract_email_returns_none_when_not_found():
    assert _extract_email_from_payload({}) is None
