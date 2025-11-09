from __future__ import annotations

import datetime as dt
from typing import Any

import jwt
import pytest
from app import auth
from app.config import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.utils import base64url_encode


def _generate_test_keypair() -> tuple[str, dict[str, Any]]:
    """Generate an ephemeral RSA keypair for signing test tokens."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_numbers = private_key.public_key().public_numbers()

    def _int_to_b64(value: int) -> str:
        length = (value.bit_length() + 7) // 8
        return base64url_encode(value.to_bytes(length, "big")).decode("ascii")

    jwk_entry = {
        "kty": "RSA",
        "kid": "test-key-123",
        "use": "sig",
        "alg": "RS256",
        "n": _int_to_b64(public_numbers.n),
        "e": _int_to_b64(public_numbers.e),
    }

    return private_pem, jwk_entry


PRIVATE_KEY, JWK_ENTRY = _generate_test_keypair()

JWKS_RESPONSE = {
    "keys": [
        JWK_ENTRY,
    ]
}


@pytest.fixture(autouse=True)
def reset_jwks_cache():
    """Ensure JWKS cache is cleared between tests."""
    auth._jwks_cache = None
    auth._jwks_cache_expiry = None
    yield
    auth._jwks_cache = None
    auth._jwks_cache_expiry = None


def _issue_token(sub: str = "user_123", kid: str = "test-key-123") -> str:
    now = dt.datetime.now(tz=dt.timezone.utc)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(minutes=5)).timestamp()),
    }
    headers = {"kid": kid, "alg": "RS256"}
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256", headers=headers)


class DummyResponse:
    def __init__(self, data: dict[str, Any], headers: dict[str, str] | None = None):
        self._data = data
        self.headers = headers or {"Cache-Control": "max-age=120"}

    def raise_for_status(self) -> None:  # pragma: no cover - no-op
        return None

    def json(self) -> dict[str, Any]:
        return self._data


class DummyClient:
    calls = 0

    def __init__(self, *args, **kwargs):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, headers=None):
        DummyClient.calls += 1
        return DummyResponse(JWKS_RESPONSE)


def test_verify_clerk_token_uses_jwks(monkeypatch):
    DummyClient.calls = 0
    monkeypatch.setattr(settings, "developer_mode", False)
    monkeypatch.setattr(settings, "environment", "prod")
    monkeypatch.setattr(settings, "clerk_jwks_url", "https://example.com/jwks.json")
    monkeypatch.setattr(settings, "clerk_jwks_cache_ttl_seconds", 120)
    monkeypatch.setattr(auth, "_jwks_cache", None)
    monkeypatch.setattr(auth, "_jwks_cache_expiry", None)
    monkeypatch.setattr("app.auth.httpx.Client", DummyClient)

    token = _issue_token()
    payload = auth.verify_clerk_token(token)
    assert payload["sub"] == "user_123"
    assert DummyClient.calls == 1

    # Second call should use cached JWKS and avoid extra HTTP fetches
    token2 = _issue_token(sub="user_456")
    payload2 = auth.verify_clerk_token(token2)
    assert payload2["sub"] == "user_456"
    assert DummyClient.calls == 1


def test_verify_clerk_token_rejects_invalid_signature(monkeypatch):
    DummyClient.calls = 0
    monkeypatch.setattr(settings, "developer_mode", False)
    monkeypatch.setattr(settings, "environment", "prod")
    monkeypatch.setattr(settings, "clerk_jwks_url", "https://example.com/jwks.json")
    monkeypatch.setattr("app.auth.httpx.Client", DummyClient)

    bad_token = _issue_token(kid="unknown-key")

    with pytest.raises(HTTPException) as excinfo:
        auth.verify_clerk_token(bad_token)

    assert excinfo.value.status_code == 401


def test_verify_clerk_token_falls_back_when_non_prod(monkeypatch):
    monkeypatch.setattr(settings, "developer_mode", False)
    monkeypatch.setattr(settings, "environment", "dev")
    monkeypatch.setattr(settings, "clerk_jwks_url", None)
    monkeypatch.setattr(settings, "developer_verify_clerk_tokens", False)

    token = _issue_token()
    payload = auth.verify_clerk_token(token)
    assert payload["sub"] == "user_123"


def test_verify_clerk_token_skips_when_developer_mode(monkeypatch):
    monkeypatch.setattr(settings, "developer_mode", True)
    monkeypatch.setattr(settings, "environment", "prod")
    monkeypatch.setattr(settings, "clerk_jwks_url", "https://example.com/jwks.json")
    monkeypatch.setattr(settings, "developer_verify_clerk_tokens", False)

    token = _issue_token()
    payload = auth.verify_clerk_token(token)
    assert payload["sub"] == "user_123"


def test_developer_mode_with_verification(monkeypatch):
    DummyClient.calls = 0
    monkeypatch.setattr(settings, "developer_mode", True)
    monkeypatch.setattr(settings, "developer_verify_clerk_tokens", True)
    monkeypatch.setattr(settings, "environment", "dev")
    monkeypatch.setattr(settings, "clerk_jwks_url", "https://example.com/jwks.json")
    monkeypatch.setattr(settings, "clerk_jwks_cache_ttl_seconds", 60)
    monkeypatch.setattr(auth, "_jwks_cache", None)
    monkeypatch.setattr(auth, "_jwks_cache_expiry", None)
    monkeypatch.setattr("app.auth.httpx.Client", DummyClient)

    token = _issue_token(sub="dev-user")
    payload = auth.verify_clerk_token(token)
    assert payload["sub"] == "dev-user"
    assert DummyClient.calls == 1
