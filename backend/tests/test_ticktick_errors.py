"""
Critical error path tests for ticktick.py production stability.
Ensures all error handlers work correctly.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta


@pytest.mark.asyncio
@patch('app.services.ticktick.httpx.AsyncClient')
@patch('app.services.ticktick.settings')
async def test_create_task_http_error(mock_settings, mock_client_class):
    """Test create_task HTTP error handling."""
    from app.services.ticktick import TickTickClient, TickTickAPIError
    import httpx
    
    mock_settings.ticktick_enabled = True
    mock_settings.ticktick_client_id = "test"
    mock_settings.ticktick_client_secret = "test"
    mock_settings.ticktick_base_url = "https://api.ticktick.com"
    
    mock_token = Mock()
    mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
    mock_token.access_token = "token"
    mock_db = Mock()
    mock_db.query().filter().first.return_value = mock_token
    
    mock_response = httpx.Response(400, text="Bad Request")
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.HTTPStatusError("Error", request=Mock(), response=mock_response)
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    client = TickTickClient(1, mock_db)
    with pytest.raises(TickTickAPIError, match="Failed to create task"):
        await client.create_task("Test")


@pytest.mark.asyncio
@patch('app.services.ticktick.httpx.AsyncClient')
@patch('app.services.ticktick.settings')
async def test_create_task_request_error(mock_settings, mock_client_class):
    """Test create_task request error handling."""
    from app.services.ticktick import TickTickClient, TickTickAPIError
    import httpx
    
    mock_settings.ticktick_enabled = True
    mock_settings.ticktick_client_id = "test"
    mock_settings.ticktick_client_secret = "test"
    mock_settings.ticktick_base_url = "https://api.ticktick.com"
    
    mock_token = Mock()
    mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
    mock_token.access_token = "token"
    mock_db = Mock()
    mock_db.query().filter().first.return_value = mock_token
    
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection failed")
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    client = TickTickClient(1, mock_db)
    with pytest.raises(TickTickAPIError, match="Failed to connect"):
        await client.create_task("Test")


@pytest.mark.asyncio
@patch('app.services.ticktick.httpx.AsyncClient')
@patch('app.services.ticktick.settings')
async def test_get_projects_errors(mock_settings, mock_client_class):
    """Test get_projects error handling."""
    from app.services.ticktick import TickTickClient, TickTickAPIError
    import httpx
    
    mock_settings.ticktick_enabled = True
    mock_settings.ticktick_client_id = "test"
    mock_settings.ticktick_client_secret = "test"
    mock_settings.ticktick_base_url = "https://api.ticktick.com"
    
    mock_token = Mock()
    mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
    mock_token.access_token = "token"
    mock_db = Mock()
    mock_db.query().filter().first.return_value = mock_token
    
    mock_response = httpx.Response(500, text="Server Error")
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.HTTPStatusError("Error", request=Mock(), response=mock_response)
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    client = TickTickClient(1, mock_db)
    with pytest.raises(TickTickAPIError):
        await client.get_projects()


@pytest.mark.asyncio
@patch('app.services.ticktick.httpx.AsyncClient')
@patch('app.services.ticktick.settings')
async def test_get_or_create_project_creation_errors(mock_settings, mock_client_class):
    """Test get_or_create_speakly_project when creation fails."""
    from app.services.ticktick import TickTickClient, TickTickAPIError
    import httpx
    
    mock_settings.ticktick_enabled = True
    mock_settings.ticktick_client_id = "test"
    mock_settings.ticktick_client_secret = "test"
    mock_settings.ticktick_base_url = "https://api.ticktick.com"
    
    mock_token = Mock()
    mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
    mock_token.access_token = "token"
    mock_db = Mock()
    mock_db.query().filter().first.return_value = mock_token
    
    mock_get_response = Mock()
    mock_get_response.json.return_value = []
    mock_get_response.raise_for_status = Mock()
    
    mock_response = httpx.Response(403, text="Forbidden")
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_get_response
    mock_client.post.side_effect = httpx.HTTPStatusError("Error", request=Mock(), response=mock_response)
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    client = TickTickClient(1, mock_db)
    with pytest.raises(TickTickAPIError, match="Failed to create Speakly project"):
        await client.get_or_create_speakly_project()


@pytest.mark.asyncio
@patch('app.services.ticktick.httpx.AsyncClient')
@patch('app.services.ticktick.settings')
async def test_get_tasks_errors(mock_settings, mock_client_class):
    """Test get_tasks error handling."""
    from app.services.ticktick import TickTickClient, TickTickAPIError
    import httpx
    
    mock_settings.ticktick_enabled = True
    mock_settings.ticktick_client_id = "test"
    mock_settings.ticktick_client_secret = "test"
    mock_settings.ticktick_base_url = "https://api.ticktick.com"
    
    mock_token = Mock()
    mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
    mock_token.access_token = "token"
    mock_db = Mock()
    mock_db.query().filter().first.return_value = mock_token
    
    mock_response = httpx.Response(401, text="Unauthorized")
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.HTTPStatusError("Error", request=Mock(), response=mock_response)
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    client = TickTickClient(1, mock_db)
    with pytest.raises(TickTickAPIError):
        await client.get_tasks()


@pytest.mark.asyncio
@patch('app.services.ticktick.httpx.AsyncClient')
@patch('app.services.ticktick.settings')
async def test_update_task_errors(mock_settings, mock_client_class):
    """Test update_task error handling."""
    from app.services.ticktick import TickTickClient, TickTickAPIError
    import httpx
    
    mock_settings.ticktick_enabled = True
    mock_settings.ticktick_client_id = "test"
    mock_settings.ticktick_client_secret = "test"
    mock_settings.ticktick_base_url = "https://api.ticktick.com"
    
    mock_token = Mock()
    mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
    mock_token.access_token = "token"
    mock_db = Mock()
    mock_db.query().filter().first.return_value = mock_token
    
    mock_response = httpx.Response(404, text="Not Found")
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.HTTPStatusError("Error", request=Mock(), response=mock_response)
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    client = TickTickClient(1, mock_db)
    with pytest.raises(TickTickAPIError):
        await client.update_task("task-1", {"title": "Updated"}, project_id="p1")


@pytest.mark.asyncio
@patch('app.services.ticktick.httpx.AsyncClient')
@patch('app.services.ticktick.settings')
async def test_complete_task_401_auth_error(mock_settings, mock_client_class):
    """Test complete_task 401 raises TickTickAuthError."""
    from app.services.ticktick import TickTickClient, TickTickAuthError
    import httpx
    
    mock_settings.ticktick_enabled = True
    mock_settings.ticktick_client_id = "test"
    mock_settings.ticktick_client_secret = "test"
    mock_settings.ticktick_base_url = "https://api.ticktick.com"
    
    mock_token = Mock()
    mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
    mock_token.access_token = "token"
    mock_db = Mock()
    mock_db.query().filter().first.return_value = mock_token
    
    mock_response = httpx.Response(401, text="Unauthorized")
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.HTTPStatusError("Error", request=Mock(), response=mock_response)
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    client = TickTickClient(1, mock_db)
    with pytest.raises(TickTickAuthError, match="Authentication failed"):
        await client.complete_task("task-1", project_id="p1")


@pytest.mark.asyncio
@patch('app.services.ticktick.httpx.AsyncClient')
@patch('app.services.ticktick.settings')
async def test_delete_task_status_codes(mock_settings, mock_client_class):
    """Test delete_task different status codes."""
    from app.services.ticktick import TickTickClient, TickTickAuthError, TickTickAPIError
    
    mock_settings.ticktick_enabled = True
    mock_settings.ticktick_client_id = "test"
    mock_settings.ticktick_client_secret = "test"
    mock_settings.ticktick_base_url = "https://api.ticktick.com"
    
    mock_token = Mock()
    mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
    mock_token.access_token = "token"
    mock_db = Mock()
    mock_db.query().filter().first.return_value = mock_token
    
    # Test 401
    mock_response = Mock()
    mock_response.status_code = 401
    mock_client = AsyncMock()
    mock_client.delete.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    client = TickTickClient(1, mock_db)
    with pytest.raises(TickTickAuthError):
        await client.delete_task("task-1", "proj-1")
    
    # Test 404 (should not raise)
    mock_response.status_code = 404
    await client.delete_task("task-1", "proj-1")  # Should not raise
    
    # Test 500
    mock_response.status_code = 500
    mock_response.text = "Error"
    with pytest.raises(TickTickAPIError):
        await client.delete_task("task-1", "proj-1")


@pytest.mark.asyncio
@patch('app.services.ticktick.httpx.AsyncClient')
@patch('app.services.ticktick.settings')
async def test_oauth_errors(mock_settings, mock_client_class):
    """Test OAuth error handling."""
    from app.services.ticktick import TickTickOAuth, TickTickAuthError
    import httpx
    
    mock_settings.ticktick_client_id = "test"
    mock_settings.ticktick_client_secret = "secret"
    mock_settings.ticktick_redirect_uri = "http://localhost/callback"
    
    mock_response = httpx.Response(400, text="Invalid code")
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.HTTPStatusError("Error", request=Mock(), response=mock_response)
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    with pytest.raises(TickTickAuthError, match="Token exchange failed"):
        await TickTickOAuth.exchange_code_for_token("bad_code")


@patch('app.services.ticktick.settings')
def test_oauth_missing_config(mock_settings):
    """Test OAuth with missing configuration."""
    from app.services.ticktick import TickTickOAuth, TickTickNotConfiguredError
    
    mock_settings.ticktick_client_id = None
    
    with pytest.raises(TickTickNotConfiguredError):
        TickTickOAuth.get_authorization_url()
