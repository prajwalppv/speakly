"""
Test configuration and fixtures for backend unit tests.
"""
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_session
from app.main import create_app
from app.models import User
from app.config import settings

# Use in-memory SQLite with shared cache for tests
import tempfile
import os
from pathlib import Path

# Use a named in-memory database that can be shared across connections
TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared&uri=true"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "uri": True
    },
    poolclass=None,  # Disable connection pooling to ensure same connection
    echo=False
)

# Create test session factory
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a fresh test database for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = TestSessionLocal()
    
    # Create default user (required by audio upload endpoint)
    default_user = User(
        name="default",
        email="test@test.com",
        clerk_user_id="test_clerk_user_123"
    )
    db.add(default_user)
    db.commit()
    
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db: Session):
    """Create a FastAPI test client with test database."""
    from unittest.mock import Mock
    from app.main import create_app
    from app.auth import get_current_user
    from app.services import get_elevenlabs_client, ElevenLabsClient
    
    # Create a fresh app instance  
    app = create_app()
    
    # Get the default test user from the database
    default_user = test_db.query(User).filter(User.name == "default").first()
    
    # Override the database dependency - it needs to yield since get_session is a generator
    def override_get_db():
        """Yield the test database session."""
        yield test_db
    
    # Override authentication to return the default test user
    async def override_get_current_user():
        """Return the default test user for all authenticated requests."""
        return default_user
    
    # Override ElevenLabs client to return a mock that never makes real API calls
    def override_get_elevenlabs_client() -> ElevenLabsClient:
        """Return a mock ElevenLabs client for testing."""
        import uuid
        mock_client = Mock(spec=ElevenLabsClient)
        mock_client.is_configured = True
        # Use a lambda to generate unique IDs for each call
        mock_client.submit_transcription.side_effect = lambda **kwargs: {
            "request_id": f"test-mock-{uuid.uuid4().hex[:16]}",
            "transcription_id": f"test-mock-trans-{uuid.uuid4().hex[:16]}",
        }
        return mock_client
    
    # Apply the overrides
    app.dependency_overrides[get_session] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_elevenlabs_client] = override_get_elevenlabs_client
    
    # Clear startup event handlers to prevent init_database() from running
    # (which would try to use production DB instead of test DB)
    app.router.on_startup = []
    
    # Create test client
    test_client = TestClient(app, raise_server_exceptions=True)
    yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def temp_audio_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for audio files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_audio_file():
    """Create a test audio file for uploads."""
    # Simple MP3 header + fake data
    mp3_header = b'\xff\xfb\x90\x00'
    fake_audio_data = mp3_header + b'\x00' * 1024
    return ("test_audio.mp3", fake_audio_data, "audio/mpeg")


@pytest.fixture
def test_transcript_text() -> str:
    """Sample transcript text for testing."""
    return """
    Hey, this is a test recording from the team meeting today.
    John mentioned we need to call Sarah tomorrow at 2pm to discuss the project timeline.
    Also, I need to send the invoice to the client by Friday.
    Don't forget to book the conference room for next week's presentation.
    """


@pytest.fixture
def test_summary_response() -> dict:
    """Mock LLM summary response."""
    return {
        "summary": "Team meeting discussing project timeline and administrative tasks.",
        "key_points": [
            "Call Sarah tomorrow at 2pm",
            "Send invoice by Friday",
            "Book conference room for presentation"
        ]
    }


@pytest.fixture
def test_action_items() -> list[dict]:
    """Mock extracted action items."""
    return [
        {
            "title": "Call Sarah tomorrow at 2pm",
            "due_hint": "tomorrow at 2pm",
            "confidence": 0.95,
            "source_excerpt": "need to call Sarah tomorrow at 2pm"
        },
        {
            "title": "Send invoice to client by Friday",
            "due_hint": "Friday",
            "confidence": 0.88,
            "source_excerpt": "send the invoice to the client by Friday"
        },
        {
            "title": "Book conference room for next week",
            "due_hint": "next week",
            "confidence": 0.82,
            "source_excerpt": "book the conference room for next week's presentation"
        }
    ]


@pytest.fixture
def test_tags() -> list[dict]:
    """Mock generated tags."""
    return [
        {"name": "meeting", "category": "event", "color": "#3b82f6"},
        {"name": "project", "category": "work", "color": "#10b981"},
        {"name": "admin", "category": "category", "color": "#f59e0b"}
    ]


@pytest.fixture
def mock_elevenlabs_response() -> dict:
    """Mock ElevenLabs webhook response."""
    return {
        "status": "completed",
        "text": "This is the transcribed text from ElevenLabs.",
        "task_id": "test-task-123"
    }


@pytest.fixture
def journeys_client(client):
    """Test client with Journeys feature flag enabled."""
    original = settings.feature_report_generation
    settings.feature_report_generation = True
    try:
        yield client
    finally:
        settings.feature_report_generation = original
