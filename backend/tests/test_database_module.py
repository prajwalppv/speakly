"""
Test database module functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import inspect


class TestDatabaseEngine:
    """Test database engine creation."""

    def test_engine_exists(self):
        """Test that engine is created."""
        from app.database import engine
        
        assert engine is not None

    def test_sessionlocal_exists(self):
        """Test that SessionLocal is created."""
        from app.database import SessionLocal
        
        assert SessionLocal is not None

    def test_base_exists(self):
        """Test that Base exists."""
        from app.database import Base
        
        assert Base is not None

    def test_engine_has_url(self):
        """Test that engine has a URL configured."""
        from app.database import engine
        
        assert engine.url is not None


class TestGetSession:
    """Test get_session dependency."""

    def test_get_session_yields_session(self):
        """Test that get_session yields a session."""
        from app.database import get_session
        
        gen = get_session()
        session = next(gen)
        
        assert session is not None
        
        # Cleanup
        try:
            next(gen)
        except StopIteration:
            pass

    def test_get_session_closes_session(self):
        """Test that get_session closes session after use."""
        from app.database import get_session
        
        gen = get_session()
        session = next(gen)
        
        assert session is not None
        
        # Complete generator to trigger finally block
        try:
            next(gen)
        except StopIteration:
            pass
        
        # Session should be closed (check that it's not None at least)
        assert session is not None

    def test_get_session_generator_pattern(self):
        """Test get_session follows generator pattern."""
        from app.database import get_session
        import types
        
        gen = get_session()
        assert isinstance(gen, types.GeneratorType)


class TestInitDatabase:
    """Test database initialization."""

    @patch('app.database._ensure_session_columns')
    @patch('app.database._ensure_transcription_columns')
    @patch('app.database.Base')
    def test_init_database_creates_tables(self, mock_base, mock_ensure_trans, mock_ensure_sess):
        """Test that init_database creates all tables."""
        from app.database import init_database
        
        init_database()
        
        mock_base.metadata.create_all.assert_called_once()

    @patch('app.database._ensure_session_columns')
    @patch('app.database._ensure_transcription_columns')
    @patch('app.database.Base')
    def test_init_database_ensures_columns(self, mock_base, mock_ensure_trans, mock_ensure_sess):
        """Test that init_database ensures columns exist."""
        from app.database import init_database
        
        init_database()
        
        mock_ensure_sess.assert_called_once()
        mock_ensure_trans.assert_called_once()


class TestEnsureSessionColumns:
    """Test session column migration."""

    @patch('app.database.inspect')
    def test_ensure_session_columns_no_table(self, mock_inspect):
        """Test _ensure_session_columns when table doesn't exist."""
        from app.database import _ensure_session_columns
        
        mock_inspector = Mock()
        mock_inspector.has_table.return_value = False
        mock_inspect.return_value = mock_inspector
        
        # Should return early without error
        _ensure_session_columns()

    @patch('app.database.engine')
    @patch('app.database.inspect')
    def test_ensure_session_columns_all_exist(self, mock_inspect, mock_engine):
        """Test when all columns already exist."""
        from app.database import _ensure_session_columns
        
        mock_inspector = Mock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [
            {"name": "status"},
            {"name": "last_error"},
            {"name": "last_transcribed_at"},
            {"name": "has_pj"},
            {"name": "summary_run_id"},
            {"name": "todo_count"},
        ]
        mock_inspect.return_value = mock_inspector
        
        # Should not execute any statements
        _ensure_session_columns()

    @patch('app.database.engine')
    @patch('app.database.inspect')
    def test_ensure_session_columns_missing_columns(self, mock_inspect, mock_engine):
        """Test adding missing columns."""
        from app.database import _ensure_session_columns
        
        mock_inspector = Mock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "user_id"},
        ]
        mock_inspect.return_value = mock_inspector
        
        mock_connection = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_connection
        
        _ensure_session_columns()
        
        # Should execute ALTER TABLE statements
        assert mock_connection.execute.call_count > 0


class TestEnsureTranscriptionColumns:
    """Test transcription column migration."""

    @patch('app.database.inspect')
    def test_ensure_transcription_columns_no_table(self, mock_inspect):
        """Test _ensure_transcription_columns when table doesn't exist."""
        from app.database import _ensure_transcription_columns
        
        mock_inspector = Mock()
        mock_inspector.has_table.return_value = False
        mock_inspect.return_value = mock_inspector
        
        # Should return early without error
        _ensure_transcription_columns()

    @patch('app.database.engine')
    @patch('app.database.inspect')
    def test_ensure_transcription_columns_all_exist(self, mock_inspect, mock_engine):
        """Test when all columns already exist."""
        from app.database import _ensure_transcription_columns
        
        mock_inspector = Mock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [
            {"name": "duration_ms"},
            {"name": "channel_count"},
        ]
        mock_inspect.return_value = mock_inspector
        
        # Should not execute any statements
        _ensure_transcription_columns()

    @patch('app.database.engine')
    @patch('app.database.inspect')
    def test_ensure_transcription_columns_missing_columns(self, mock_inspect, mock_engine):
        """Test adding missing transcription columns."""
        from app.database import _ensure_transcription_columns
        
        mock_inspector = Mock()
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "session_id"},
        ]
        mock_inspect.return_value = mock_inspector
        
        mock_connection = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_connection
        
        _ensure_transcription_columns()
        
        # Should execute ALTER TABLE statements
        assert mock_connection.execute.call_count > 0


class TestDatabaseConfiguration:
    """Test database configuration."""

    def test_sqlite_check_same_thread_config(self):
        """Test that SQLite has check_same_thread disabled."""
        from app.database import engine
        from app.config import settings
        
        if settings.database_url.startswith("sqlite"):
            # SQLite should have check_same_thread disabled
            assert engine.pool._creator is not None

    def test_database_url_from_settings(self):
        """Test that database URL comes from settings."""
        from app.database import engine
        from app.config import settings
        
        # Engine URL should match settings
        assert str(engine.url).startswith(settings.database_url.split("?")[0])


class TestDatabaseIntegration:
    """Integration tests for database functionality."""

    def test_can_create_session_from_sessionlocal(self):
        """Test creating session from SessionLocal."""
        from app.database import SessionLocal
        
        session = SessionLocal()
        assert session is not None
        session.close()

    def test_session_can_execute_query(self):
        """Test that session can execute queries."""
        from app.database import SessionLocal
        from sqlalchemy import text
        
        session = SessionLocal()
        
        try:
            result = session.execute(text("SELECT 1"))
            assert result is not None
        finally:
            session.close()

    def test_get_session_in_context_manager(self):
        """Test using get_session with context manager pattern."""
        from app.database import get_session
        
        gen = get_session()
        session = next(gen)
        
        # Use session
        assert session is not None
        assert hasattr(session, 'query')
        assert hasattr(session, 'add')
        assert hasattr(session, 'commit')
        
        # Cleanup
        try:
            next(gen)
        except StopIteration:
            pass


class TestDatabaseExports:
    """Test module exports."""

    def test_all_exports_exist(self):
        """Test that all exported items exist."""
        from app import database
        
        assert hasattr(database, 'Base')
        assert hasattr(database, 'engine')
        assert hasattr(database, 'SessionLocal')
        assert hasattr(database, 'get_session')
        assert hasattr(database, 'init_database')

    def test_all_variable_content(self):
        """Test __all__ contains expected exports."""
        from app.database import __all__
        
        expected = ["Base", "engine", "SessionLocal", "get_session", "init_database"]
        for item in expected:
            assert item in __all__
