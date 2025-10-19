# Speakly Backend Tests

Comprehensive test suite for Speakly backend with 80%+ coverage.

## Running Tests

### Run All Tests
```bash
# From backend directory
uv run pytest

# With coverage report
uv run pytest --cov=app --cov-report=html
```

### Run Specific Test Files
```bash
uv run pytest tests/test_audio.py
uv run pytest tests/test_llm.py
uv run pytest tests/test_sessions.py
```

### Run Tests by Marker
```bash
# Run only unit tests
uv run pytest -m unit

# Skip slow tests
uv run pytest -m "not slow"

# Run integration tests only
uv run pytest -m integration
```

### Run with Docker
```bash
# From project root
docker compose run --rm backend-tests
```

## Test Structure

```
tests/
├── conftest.py           # Test fixtures and configuration
├── test_audio.py         # Audio upload tests
├── test_webhooks.py      # Webhook processing tests
├── test_llm.py           # LLM service tests (summary, actions, tags)
├── test_ticktick.py      # TickTick integration tests
├── test_sessions.py      # Sessions API tests
└── test_models.py        # Database model tests
```

## Coverage Goals

- **Core business logic**: 80%+
- **API endpoints**: 90%+
- **Database models**: 85%+

## Test Categories

### Unit Tests
Test individual functions and methods in isolation with mocked dependencies.
- LLM parsing logic
- Data formatting
- Validation functions

### Integration Tests
Test multiple components working together.
- API endpoints with database
- Full request/response cycles
- Service layer interactions

### External API Tests
Tests that mock external services (ElevenLabs, LLMs, TickTick).
- All external API calls are mocked
- No actual API costs during testing
- Fast and reliable execution

## Writing New Tests

### Test Naming Convention
```python
def test_<feature>_<scenario>():
    """Test that <feature> <expected behavior>."""
    # Arrange
    # Act
    # Assert
```

### Using Fixtures
```python
def test_example(client, test_db, test_audio_file):
    """Use fixtures for common test setup."""
    response = client.post("/api/audio", files={"audio": test_audio_file})
    assert response.status_code == 201
```

### Mocking External Calls
```python
@patch('app.services.llm.openai_client.chat.completions.create')
def test_with_mock(mock_llm):
    mock_llm.return_value = Mock(choices=[...])
    # Test your code
```

## Continuous Integration

Tests run automatically on:
- Every commit (local pre-commit hook)
- Pull requests (GitHub Actions)
- Before deployment

## Coverage Report

After running tests with coverage:
```bash
# View in terminal
uv run pytest --cov=app --cov-report=term-missing

# Generate HTML report
uv run pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### Tests Failing Locally
1. Ensure all dependencies installed: `uv sync --extra dev`
2. Check database is clean: Tests use in-memory SQLite
3. Verify environment variables are not interfering

### Mock Not Working
- Ensure you're patching the right import path
- Use `patch.object` for class methods
- Check that patch target matches actual usage

### Database Errors
- Tests use isolated in-memory database
- Each test gets fresh database via fixtures
- Check foreign key constraints

## Best Practices

1. **Keep tests independent** - No test should depend on another
2. **Use meaningful names** - Test name should describe what it tests
3. **Test one thing** - Each test should have a single assertion focus
4. **Mock external services** - Never hit real APIs in tests
5. **Fast tests** - Unit tests should run in milliseconds
6. **Clean fixtures** - Always clean up resources after tests
