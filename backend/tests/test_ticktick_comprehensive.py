"""
Comprehensive TickTick service tests for maximum coverage.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest


@patch("app.services.ticktick.settings")
class TestTickTickClientInit:
    """Test TickTickClient initialization."""

    def test_init_raises_when_not_enabled(self, mock_settings):
        from app.services.ticktick import TickTickClient, TickTickNotConfiguredError

        mock_settings.ticktick_enabled = False
        with pytest.raises(TickTickNotConfiguredError):
            TickTickClient(1, Mock())

    def test_init_raises_when_no_credentials(self, mock_settings):
        from app.services.ticktick import TickTickClient, TickTickNotConfiguredError

        mock_settings.ticktick_enabled = True
        mock_settings.ticktick_client_id = None
        with pytest.raises(TickTickNotConfiguredError):
            TickTickClient(1, Mock())

    def test_init_success(self, mock_settings):
        from app.services.ticktick import TickTickClient

        mock_settings.ticktick_enabled = True
        mock_settings.ticktick_client_id = "test"
        mock_settings.ticktick_client_secret = "test"
        client = TickTickClient(1, Mock())
        assert client.user_id == 1


@patch("app.services.ticktick.settings")
class TestGetToken:
    """Test _get_token method."""

    def test_get_token_raises_when_no_token(self, mock_settings):
        from app.services.ticktick import TickTickAuthError, TickTickClient

        mock_settings.ticktick_enabled = True
        mock_settings.ticktick_client_id = "test"
        mock_settings.ticktick_client_secret = "test"
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None
        client = TickTickClient(1, mock_db)
        with pytest.raises(TickTickAuthError):
            client._get_token()

    def test_get_token_raises_when_expired(self, mock_settings):
        from app.services.ticktick import TickTickAuthError, TickTickClient

        mock_settings.ticktick_enabled = True
        mock_settings.ticktick_client_id = "test"
        mock_settings.ticktick_client_secret = "test"
        mock_token = Mock()
        mock_token.expires_at = datetime.utcnow() - timedelta(hours=1)
        mock_db = Mock()
        mock_db.query().filter().first.return_value = mock_token
        client = TickTickClient(1, mock_db)
        with pytest.raises(TickTickAuthError):
            client._get_token()


@patch("app.services.ticktick.httpx.AsyncClient")
@patch("app.services.ticktick.settings")
class TestCreateTask:
    """Test create_task method."""

    @pytest.mark.asyncio
    async def test_create_task_minimal(self, mock_settings, mock_client_class):
        from app.services.ticktick import TickTickClient

        mock_settings.ticktick_enabled = True
        mock_settings.ticktick_client_id = "test"
        mock_settings.ticktick_client_secret = "test"
        mock_settings.ticktick_base_url = "https://api.ticktick.com"

        mock_token = Mock()
        mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_token.access_token = "token"

        mock_db = Mock()
        mock_db.query().filter().first.return_value = mock_token

        mock_response = Mock()
        mock_response.json.return_value = {"id": "task-1"}

        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        client = TickTickClient(1, mock_db)
        result = await client.create_task("Test")
        assert result["id"] == "task-1"

    @pytest.mark.asyncio
    async def test_create_task_with_all_fields(self, mock_settings, mock_client_class):
        from app.services.ticktick import TickTickClient

        mock_settings.ticktick_enabled = True
        mock_settings.ticktick_client_id = "test"
        mock_settings.ticktick_client_secret = "test"
        mock_settings.ticktick_base_url = "https://api.ticktick.com"

        mock_token = Mock()
        mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_token.access_token = "token"
        mock_db = Mock()
        mock_db.query().filter().first.return_value = mock_token

        mock_response = Mock()
        mock_response.json.return_value = {"id": "task-1"}
        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        client = TickTickClient(1, mock_db)
        result = await client.create_task(
            "Task",
            content="Desc",
            project_id="p1",
            start_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=1),
            priority=5,
            tags=["test"],
        )
        assert result["id"] == "task-1"


@patch("app.services.ticktick.settings")
class TestTickTickOAuth:
    """Test TickTickOAuth class."""

    def test_get_authorization_url(self, mock_settings):
        from app.services.ticktick import TickTickOAuth

        mock_settings.ticktick_client_id = "test_id"
        mock_settings.ticktick_redirect_uri = "http://localhost/callback"

        url = TickTickOAuth.get_authorization_url()
        assert "client_id=test_id" in url
        assert "ticktick.com/oauth/authorize" in url

    def test_get_authorization_url_with_state(self, mock_settings):
        from app.services.ticktick import TickTickOAuth

        mock_settings.ticktick_client_id = "test_id"
        mock_settings.ticktick_redirect_uri = "http://localhost/callback"

        url = TickTickOAuth.get_authorization_url(state="random123")
        assert "state=random123" in url

    @pytest.mark.asyncio
    @patch("app.services.ticktick.httpx.AsyncClient")
    async def test_exchange_code_for_token(self, mock_client_class, mock_settings):
        from app.services.ticktick import TickTickOAuth

        mock_settings.ticktick_client_id = "test_id"
        mock_settings.ticktick_client_secret = "test_secret"
        mock_settings.ticktick_redirect_uri = "http://localhost/callback"

        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "token123"}
        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await TickTickOAuth.exchange_code_for_token("code123")
        assert result["access_token"] == "token123"

    def test_save_token_creates_new(self, mock_settings):
        from app.models import User
        from app.services.ticktick import TickTickOAuth

        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        user = User(id=1, name="test")
        token_data = {"access_token": "token", "expires_in": 3600}

        result = TickTickOAuth.save_token(mock_db, user, token_data)
        mock_db.add.assert_called_once()

    def test_save_token_updates_existing(self, mock_settings):
        from app.models import User
        from app.services.ticktick import TickTickOAuth

        existing_token = Mock()
        mock_db = Mock()
        mock_db.query().filter().first.return_value = existing_token

        user = User(id=1, name="test")
        token_data = {"access_token": "new_token", "expires_in": 3600}

        result = TickTickOAuth.save_token(mock_db, user, token_data)
        assert existing_token.access_token == "new_token"
        mock_db.commit.assert_called()
        mock_settings.ticktick_base_url = "https://api.ticktick.com"
