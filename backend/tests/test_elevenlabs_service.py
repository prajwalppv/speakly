"""
Comprehensive tests for ElevenLabs service business logic.
Tests API error handling, network failures, and configuration.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock, mock_open
from pathlib import Path

from app.services.elevenlabs import (
    ElevenLabsClient,
    ElevenLabsError,
    ElevenLabsNotConfiguredError,
    get_elevenlabs_client
)


class TestElevenLabsClientInit:
    """Test ElevenLabs client initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = ElevenLabsClient(api_key="test_key", base_url="https://api.elevenlabs.io")
        assert client.api_key == "test_key"
        assert client.is_configured is True

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        client = ElevenLabsClient(api_key=None, base_url="https://api.elevenlabs.io")
        assert client.api_key is None
        assert client.is_configured is False

    def test_get_client_function(self):
        """Test get_elevenlabs_client function."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.elevenlabs_api_key = "test_key"
            mock_settings.elevenlabs_base_url = "https://api.elevenlabs.io"
            
            client = get_elevenlabs_client()
            assert isinstance(client, ElevenLabsClient)
            assert client.api_key == "test_key"


class TestSubmitTranscriptionDeveloperMode:
    """Test submit_transcription in developer mode."""

    def test_developer_mode_returns_mock_response(self, tmp_path):
        """Test developer mode returns mock response without API call."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = True
            
            audio_file = tmp_path / "test.wav"
            audio_file.write_bytes(b"fake audio")
            
            client = ElevenLabsClient(api_key="test_key", base_url="https://api.elevenlabs.io")
            result = client.submit_transcription(
                audio_path=audio_file,
                webhook_url="https://example.com/webhook"
            )
            
            assert "request_id" in result
            assert "mock_request_" in result["request_id"]
            assert result["message"] == "[MOCK] Request accepted. Transcription will be sent to webhook."


class TestSubmitTranscriptionValidation:
    """Test submit_transcription validation."""

    def test_submit_without_api_key_raises_error(self, tmp_path):
        """Test submission without API key raises error."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = False
            
            audio_file = tmp_path / "test.wav"
            audio_file.write_bytes(b"fake audio")
            
            client = ElevenLabsClient(api_key=None, base_url="https://api.elevenlabs.io")
            
            with pytest.raises(ElevenLabsNotConfiguredError, match="not configured"):
                client.submit_transcription(
                    audio_path=audio_file,
                    webhook_url="https://example.com/webhook"
                )

    def test_submit_nonexistent_file_raises_error(self):
        """Test submission with non-existent file raises error."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = False
            
            client = ElevenLabsClient(api_key="test_key", base_url="https://api.elevenlabs.io")
            
            with pytest.raises(ElevenLabsError, match="not found"):
                client.submit_transcription(
                    audio_path=Path("/nonexistent/file.wav"),
                    webhook_url="https://example.com/webhook"
                )


class TestSubmitTranscriptionSuccess:
    """Test successful transcription submission."""

    def test_submit_transcription_success(self, tmp_path):
        """Test successful transcription submission."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = False
            mock_settings.elevenlabs_diarization_enabled = False
            mock_settings.elevenlabs_webhook_id = None
            
            audio_file = tmp_path / "test.wav"
            audio_file.write_bytes(b"fake audio")
            
            with patch('app.services.elevenlabs.httpx.Client') as mock_client_class:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "request_id": "test-request-123",
                    "status": "submitted"
                }
                mock_response.raise_for_status = Mock()
                
                mock_client = MagicMock()
                mock_client.__enter__.return_value = mock_client
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client
                
                client = ElevenLabsClient(api_key="test_key", base_url="https://api.elevenlabs.io")
                result = client.submit_transcription(
                    audio_path=audio_file,
                    webhook_url="https://example.com/webhook"
                )
                
                assert result["request_id"] == "test-request-123"
                assert result["status"] == "submitted"

    def test_submit_with_metadata(self, tmp_path):
        """Test submission with metadata."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = False
            mock_settings.elevenlabs_diarization_enabled = False
            mock_settings.elevenlabs_webhook_id = None
            
            audio_file = tmp_path / "test.wav"
            audio_file.write_bytes(b"fake audio")
            
            with patch('app.services.elevenlabs.httpx.Client') as mock_client_class:
                mock_response = Mock()
                mock_response.json.return_value = {"request_id": "123"}
                mock_response.raise_for_status = Mock()
                
                mock_client = MagicMock()
                mock_client.__enter__.return_value = mock_client
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client
                
                client = ElevenLabsClient(api_key="test_key", base_url="https://api.elevenlabs.io")
                result = client.submit_transcription(
                    audio_path=audio_file,
                    webhook_url="https://example.com/webhook",
                    metadata={"session_id": 123}
                )
                
                # Verify metadata was included in call
                call_kwargs = mock_client.post.call_args[1]
                assert "data" in call_kwargs


class TestSubmitTranscriptionNetworkErrors:
    """Test network error handling."""

    def test_submit_connection_error(self, tmp_path):
        """Test handling of connection error."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = False
            
            audio_file = tmp_path / "test.wav"
            audio_file.write_bytes(b"fake audio")
            
            with patch('app.services.elevenlabs.httpx.Client') as mock_client_class:
                import httpx
                mock_client = MagicMock()
                mock_client.__enter__.return_value = mock_client
                mock_client.post.side_effect = httpx.ConnectError("Connection failed")
                mock_client_class.return_value = mock_client
                
                client = ElevenLabsClient(api_key="test_key", base_url="https://api.elevenlabs.io")
                
                with pytest.raises(ElevenLabsError, match="Network error"):
                    client.submit_transcription(
                        audio_path=audio_file,
                        webhook_url="https://example.com/webhook"
                    )

    def test_submit_timeout_error(self, tmp_path):
        """Test handling of timeout error."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = False
            
            audio_file = tmp_path / "test.wav"
            audio_file.write_bytes(b"fake audio")
            
            with patch('app.services.elevenlabs.httpx.Client') as mock_client_class:
                import httpx
                mock_client = MagicMock()
                mock_client.__enter__.return_value = mock_client
                mock_client.post.side_effect = httpx.TimeoutException("Timeout")
                mock_client_class.return_value = mock_client
                
                client = ElevenLabsClient(api_key="test_key", base_url="https://api.elevenlabs.io")
                
                with pytest.raises(ElevenLabsError, match="Network error"):
                    client.submit_transcription(
                        audio_path=audio_file,
                        webhook_url="https://example.com/webhook"
                    )


class TestSubmitTranscriptionHTTPErrors:
    """Test HTTP error handling."""

    def test_submit_401_unauthorized(self, tmp_path):
        """Test handling of 401 Unauthorized."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = False
            
            audio_file = tmp_path / "test.wav"
            audio_file.write_bytes(b"fake audio")
            
            with patch('app.services.elevenlabs.httpx.Client') as mock_client_class:
                import httpx
                
                mock_response = Mock()
                mock_response.status_code = 401
                mock_response.text = "Unauthorized"
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Unauthorized", request=Mock(), response=mock_response
                )
                
                mock_client = MagicMock()
                mock_client.__enter__.return_value = mock_client
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client
                
                client = ElevenLabsClient(api_key="invalid_key", base_url="https://api.elevenlabs.io")
                
                with pytest.raises(ElevenLabsError, match="API error 401"):
                    client.submit_transcription(
                        audio_path=audio_file,
                        webhook_url="https://example.com/webhook"
                    )

    def test_submit_500_server_error(self, tmp_path):
        """Test handling of 500 Server Error."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = False
            
            audio_file = tmp_path / "test.wav"
            audio_file.write_bytes(b"fake audio")
            
            with patch('app.services.elevenlabs.httpx.Client') as mock_client_class:
                import httpx
                
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Error", request=Mock(), response=mock_response
                )
                
                mock_client = MagicMock()
                mock_client.__enter__.return_value = mock_client
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client
                
                client = ElevenLabsClient(api_key="test_key", base_url="https://api.elevenlabs.io")
                
                with pytest.raises(ElevenLabsError, match="API error 500"):
                    client.submit_transcription(
                        audio_path=audio_file,
                        webhook_url="https://example.com/webhook"
                    )

    def test_submit_invalid_json_response(self, tmp_path):
        """Test handling of invalid JSON response."""
        with patch('app.services.elevenlabs.settings') as mock_settings:
            mock_settings.developer_mode = False
            
            audio_file = tmp_path / "test.wav"
            audio_file.write_bytes(b"fake audio")
            
            with patch('app.services.elevenlabs.httpx.Client') as mock_client_class:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.json.side_effect = ValueError("Invalid JSON")
                mock_response.text = "not json"
                
                mock_client = MagicMock()
                mock_client.__enter__.return_value = mock_client
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client
                
                client = ElevenLabsClient(api_key="test_key", base_url="https://api.elevenlabs.io")
                
                with pytest.raises(ElevenLabsError, match="Invalid JSON"):
                    client.submit_transcription(
                        audio_path=audio_file,
                        webhook_url="https://example.com/webhook"
                    )
