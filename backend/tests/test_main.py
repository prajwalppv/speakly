"""
Comprehensive test suite for main app module.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException


class TestCustomJSONEncoder:
    """Test custom JSON encoder."""

    def test_custom_jsonable_encoder_datetime(self):
        """Test encoder adds Z to datetime."""
        from app.main import custom_jsonable_encoder
        
        dt = datetime(2025, 1, 1, 12, 0, 0)
        result = custom_jsonable_encoder(dt)
        
        assert result.endswith('Z')
        assert '2025-01-01' in result

    def test_custom_jsonable_encoder_other_types(self):
        """Test encoder handles other types."""
        from app.main import custom_jsonable_encoder
        
        # Should handle regular types
        result = custom_jsonable_encoder({"key": "value"})
        assert "key" in result


class TestCreateApp:
    """Test create_app function."""

    @patch('app.main.run_startup_tasks')
    @patch('app.main.ensure_pj_profile')
    @patch('app.main.init_database')
    @patch('app.main.configure_logging')
    def test_create_app_returns_fastapi(self, mock_log, mock_init_db, mock_pj, mock_startup):
        """Test create_app returns FastAPI instance."""
        from app.main import create_app
        from fastapi import FastAPI
        
        app = create_app()
        
        assert isinstance(app, FastAPI)
        assert app.title == "Speakly API"

    @patch('app.main.run_startup_tasks')
    @patch('app.main.ensure_pj_profile')
    @patch('app.main.init_database')
    @patch('app.main.configure_logging')
    def test_create_app_registers_middleware(self, mock_log, mock_init_db, mock_pj, mock_startup):
        """Test CORS middleware is registered."""
        from app.main import create_app
        
        app = create_app()
        
        # Check middleware is present
        assert len(app.user_middleware) > 0


class TestRegisterRoutes:
    """Test register_routes function."""

    def test_register_routes_includes_all_routers(self):
        """Test all routers are registered."""
        from app.main import register_routes
        from fastapi import FastAPI
        
        app = FastAPI()
        register_routes(app)
        
        # Check routes are registered
        routes = [route.path for route in app.routes]
        assert any('/api/audio' in path for path in routes)
        assert any('/api/sessions' in path for path in routes)




class TestLogRequest:
    """Test log_request middleware."""

    @pytest.mark.asyncio
    async def test_log_request_middleware(self):
        """Test request logging middleware."""
        from app.main import log_request
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/test"
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        async def mock_call_next(req):
            return mock_response
        
        result = await log_request(mock_request, mock_call_next)
        
        assert result == mock_response


class TestExceptionHandlers:
    """Test exception handlers."""

    @patch('app.main.run_startup_tasks')
    @patch('app.main.ensure_pj_profile')
    @patch('app.main.init_database')
    @patch('app.main.configure_logging')
    def test_http_exception_handler(self, mock_log, mock_init_db, mock_pj, mock_startup):
        """Test HTTP exception handler."""
        from app.main import create_app
        from fastapi.testclient import TestClient
        
        app = create_app()
        
        @app.get("/test-error")
        def test_endpoint():
            raise HTTPException(status_code=404, detail="Not found")
        
        client = TestClient(app)
        response = client.get("/test-error")
        
        assert response.status_code == 404
        data = response.json()
        assert "type" in data
        assert "message" in data


    @patch('app.main.run_startup_tasks')
    @patch('app.main.ensure_pj_profile')
    @patch('app.main.init_database')
    @patch('app.main.configure_logging')
    @patch('app.main.settings')
    def test_exception_handler_developer_mode(self, mock_settings, mock_log, mock_init_db, mock_pj, mock_startup):
        """Test exception handler includes debug info in dev mode."""
        from app.main import create_app
        from fastapi.testclient import TestClient
        
        mock_settings.developer_mode = True
        mock_settings.environment = "dev"
        
        app = create_app()
        
        @app.get("/test-dev-error")
        def test_endpoint():
            raise HTTPException(status_code=400, detail="Bad request")
        
        client = TestClient(app)
        response = client.get("/test-dev-error")
        
        assert response.status_code == 400
        data = response.json()
        # Should include debug info
        assert "debug" in data or "detail" in data.get("message", "")


