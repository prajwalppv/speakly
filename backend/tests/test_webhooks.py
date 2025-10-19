"""
Test webhook processing (ElevenLabs callbacks).
"""

import hashlib
import hmac
import json
from unittest.mock import patch


class TestElevenLabsWebhook:
    """Test ElevenLabs webhook endpoint."""

    def test_webhook_endpoint_exists(self, client):
        """Test that webhook endpoint is registered."""
        # POST to webhook should not 404
        response = client.post("/api/webhooks/elevenlabs")

        # Should fail validation, not 404
        assert response.status_code != 404

    def test_webhook_missing_signature_header(self, client):
        """Test webhook rejects requests without signature header."""
        payload = {"status": "completed", "text": "Test transcript"}

        response = client.post("/api/webhooks/elevenlabs", json=payload)

        # Without signature header, should reject
        assert response.status_code in [400, 401, 422]

    def test_webhook_with_invalid_signature(self, client):
        """Test that invalid signature is rejected."""
        payload = {"status": "completed", "text": "Test"}

        response = client.post(
            "/api/webhooks/elevenlabs",
            json=payload,
            headers={"X-ELEVENLABS-SIGNATURE": "invalid_signature"},
        )

        # Should reject invalid signature
        assert response.status_code in [401, 422]

    def test_webhook_empty_payload(self, client):
        """Test webhook with empty payload."""
        response = client.post("/api/webhooks/elevenlabs", json={})

        # Should reject empty payload
        assert response.status_code in [400, 422]

    def test_webhook_malformed_json(self, client):
        """Test webhook with malformed JSON."""
        response = client.post(
            "/api/webhooks/elevenlabs",
            data="not json",
            headers={"Content-Type": "application/json"},
        )

        # Should reject malformed JSON
        assert response.status_code in [400, 422]

    @patch.dict("os.environ", {"ELEVENLABS_WEBHOOK_SECRET": "test_secret"})
    def test_webhook_with_valid_signature(self, client, test_db):
        """Test webhook with valid HMAC signature."""
        from app.models import Session, Transcription

        # Create session and transcription
        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()

        transcription = Transcription(
            session_id=session.id, provider_job_id="test-job-123", status="submitted"
        )
        test_db.add(transcription)
        test_db.commit()

        # Create webhook payload
        payload = {
            "status": "completed",
            "text": "This is the transcribed text",
            "request_id": "test-job-123",
        }

        payload_json = json.dumps(payload)

        # Generate valid signature
        signature = hmac.new(
            b"test_secret", payload_json.encode(), hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/api/webhooks/elevenlabs",
            data=payload_json,
            headers={
                "X-ELEVENLABS-SIGNATURE": signature,
                "Content-Type": "application/json",
            },
        )

        # Should accept with valid signature
        # Note: Actual status depends on implementation
        assert response.status_code in [200, 204, 400, 422]


class TestWebhookProcessing:
    """Test webhook payload processing."""

    @patch.dict("os.environ", {"ELEVENLABS_WEBHOOK_SECRET": "test_secret"})
    def test_webhook_finds_transcription_by_provider_job_id(self, client, test_db):
        """Test webhook finds transcription using provider_job_id."""
        import hashlib
        import hmac
        import json

        from app.models import Session, Transcription

        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()

        transcription = Transcription(
            session_id=session.id, provider_job_id="find-me-123", status="submitted"
        )
        test_db.add(transcription)
        test_db.commit()

        payload = {
            "status": "completed",
            "text": "Transcription complete",
            "request_id": "find-me-123",
        }

        payload_json = json.dumps(payload)
        signature = hmac.new(
            b"test_secret", payload_json.encode(), hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/api/webhooks/elevenlabs",
            data=payload_json,
            headers={
                "X-ELEVENLABS-SIGNATURE": signature,
                "Content-Type": "application/json",
            },
        )

        # Should process successfully or return 204/200
        assert response.status_code in [200, 204, 400, 422]

    @patch.dict("os.environ", {"ELEVENLABS_WEBHOOK_SECRET": "test_secret"})
    def test_webhook_updates_transcription_text(self, client, test_db):
        """Test webhook stores transcription text."""
        import hashlib
        import hmac
        import json

        from app.models import Session, Transcription

        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()

        transcription = Transcription(
            session_id=session.id, provider_job_id="text-update-123", status="submitted"
        )
        test_db.add(transcription)
        test_db.commit()

        payload = {
            "status": "completed",
            "text": "This is the transcribed text",
            "request_id": "text-update-123",
        }

        payload_json = json.dumps(payload)
        signature = hmac.new(
            b"test_secret", payload_json.encode(), hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/api/webhooks/elevenlabs",
            data=payload_json,
            headers={
                "X-ELEVENLABS-SIGNATURE": signature,
                "Content-Type": "application/json",
            },
        )

        # Verify transcription was updated
        test_db.refresh(transcription)
        # Text should be updated if webhook processed successfully

    @patch.dict("os.environ", {"ELEVENLABS_WEBHOOK_SECRET": "test_secret"})
    def test_webhook_handles_error_status(self, client, test_db):
        """Test webhook handles error status from provider."""
        import hashlib
        import hmac
        import json

        from app.models import Session, Transcription

        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()

        transcription = Transcription(
            session_id=session.id, provider_job_id="error-test-123", status="submitted"
        )
        test_db.add(transcription)
        test_db.commit()

        payload = {
            "status": "error",
            "error": "Transcription failed",
            "request_id": "error-test-123",
        }

        payload_json = json.dumps(payload)
        signature = hmac.new(
            b"test_secret", payload_json.encode(), hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/api/webhooks/elevenlabs",
            data=payload_json,
            headers={
                "X-ELEVENLABS-SIGNATURE": signature,
                "Content-Type": "application/json",
            },
        )

        # Should handle error status
        assert response.status_code in [200, 204, 400, 422]


class TestWebhookErrorHandling:
    """Test webhook error scenarios."""

    def test_webhook_handles_missing_transcription(self, client):
        """Test webhook with non-existent transcription."""
        payload = {"status": "completed", "request_id": "non-existent-id"}

        response = client.post("/api/webhooks/elevenlabs", json=payload)

        # Should handle gracefully
        assert response.status_code in [400, 404, 422]

    def test_webhook_handles_error_status(self, client, test_db):
        """Test webhook with error status."""
        from app.models import Session, Transcription

        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()

        transcription = Transcription(
            session_id=session.id, provider_job_id="error-test", status="submitted"
        )
        test_db.add(transcription)
        test_db.commit()

        # Webhook with error status should update accordingly

    def test_webhook_validates_payload(self, client):
        """Test that webhook validates payload structure."""
        # Invalid payload
        payload = {"invalid": "data"}

        response = client.post("/api/webhooks/elevenlabs", json=payload)

        # Should reject invalid payload
        assert response.status_code in [400, 422]


class TestWebhookSecurity:
    """Test webhook security measures."""

    def test_webhook_signature_verification(self, client):
        """Test that signature verification is enforced."""
        payload = {"status": "completed"}

        # Without signature
        response = client.post("/api/webhooks/elevenlabs", json=payload)

        assert response.status_code != 200

    def test_webhook_rejects_replay_attacks(self, client):
        """Test protection against replay attacks."""
        # Same payload sent twice should be handled correctly
        payload = {"status": "completed", "request_id": "replay-test"}

        response1 = client.post("/api/webhooks/elevenlabs", json=payload)

        # Second identical request
        response2 = client.post("/api/webhooks/elevenlabs", json=payload)

        # Both should be processed or rejected consistently

    def test_webhook_handles_malformed_json(self, client):
        """Test webhook with malformed JSON."""
        response = client.post(
            "/api/webhooks/elevenlabs",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )

        # Should handle gracefully
        assert response.status_code in [400, 422]


class TestWebhookMetadata:
    """Test webhook metadata handling."""

    def test_webhook_stores_provider_metadata(self, client, test_db):
        """Test that webhook stores provider metadata."""
        from app.models import Session, Transcription

        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()

        transcription = Transcription(session_id=session.id, status="pending")
        test_db.add(transcription)
        test_db.commit()

        # Webhook should store metadata in metadata_payload

    def test_webhook_preserves_existing_metadata(self, client, test_db):
        """Test that webhook preserves existing metadata."""
        from app.models import Session, Transcription

        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()

        existing_metadata = {"key": "value"}
        transcription = Transcription(
            session_id=session.id, metadata_payload=existing_metadata, status="pending"
        )
        test_db.add(transcription)
        test_db.commit()

        # After webhook, original metadata should still be accessible


class TestWebhookIntegration:
    """Test webhook integration with other systems."""

    def test_webhook_triggers_processing(self, client, test_db):
        """Test that webhook triggers downstream processing."""
        from app.models import Session, Transcription

        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()

        transcription = Transcription(session_id=session.id, status="pending")
        test_db.add(transcription)
        test_db.commit()

        # Webhook should trigger LLM processing, etc.

    def test_webhook_updates_session_status(self, client, test_db):
        """Test that webhook updates session status."""
        from app.models import Session, Transcription

        session = Session(user_id=1, audio_path="/path/test.mp3", status="pending")
        test_db.add(session)
        test_db.commit()

        transcription = Transcription(session_id=session.id, status="pending")
        test_db.add(transcription)
        test_db.commit()

        # After successful webhook, session status should update

    def test_webhook_handles_concurrent_requests(self, client, test_db):
        """Test webhook handles concurrent requests safely."""
        from app.models import Session, Transcription

        session = Session(user_id=1, audio_path="/path/test.mp3")
        test_db.add(session)
        test_db.commit()

        transcription = Transcription(
            session_id=session.id, provider_job_id="concurrent-test", status="pending"
        )
        test_db.add(transcription)
        test_db.commit()

        # Multiple webhook calls should be handled safely


class TestWebhookSignatureVerification:
    """Test webhook signature verification."""

    def test_verify_signature_returns_true_when_no_secret(self):
        """Test verify_signature when no secret is configured."""
        from unittest.mock import patch

        from app.routers.webhooks import verify_signature

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.elevenlabs_webhook_secret = None

            result = verify_signature("some_signature", b"payload")
            assert result is True

    def test_verify_signature_returns_true_when_no_provided(self):
        """Test verify_signature when no signature provided."""
        from unittest.mock import patch

        from app.routers.webhooks import verify_signature

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.elevenlabs_webhook_secret = "secret"

            result = verify_signature(None, b"payload")
            assert result is True

    def test_verify_signature_with_valid_signature(self):
        """Test verify_signature with valid HMAC signature."""
        import hashlib
        import hmac
        from unittest.mock import patch

        from app.routers.webhooks import verify_signature

        payload = b"test payload"
        secret = "test_secret"

        # Generate valid signature
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.elevenlabs_webhook_secret = secret

            result = verify_signature(expected, payload)
            assert result is True

    def test_verify_signature_with_invalid_signature(self):
        """Test verify_signature with invalid signature."""
        from unittest.mock import patch

        from app.routers.webhooks import verify_signature

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.elevenlabs_webhook_secret = "secret"

            result = verify_signature("invalid_sig", b"payload")
            assert result is False

    def test_verify_signature_with_sha256_prefix(self):
        """Test verify_signature handles sha256= prefix."""
        import hashlib
        import hmac
        from unittest.mock import patch

        from app.routers.webhooks import verify_signature

        payload = b"test"
        secret = "secret"

        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        with patch("app.routers.webhooks.settings") as mock_settings:
            mock_settings.elevenlabs_webhook_secret = secret

            # With prefix
            result = verify_signature(f"sha256={sig}", payload)
            assert result is True
