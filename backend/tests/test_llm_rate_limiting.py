"""Tests for LLM rate limiting and retry mechanisms."""

import asyncio
from unittest.mock import Mock, patch, MagicMock
import pytest
import httpx

from app.services.llm import (
    GroqProvider,
    GroqRateLimitError,
    LlmError,
    LlmTask,
    schedule_summary_and_todos,
    _get_llm_semaphore,
)
from app.config import settings


@pytest.fixture
def mock_settings():
    """Mock settings with retry configuration."""
    mock = Mock()
    mock.groq_api_key = "test-api-key"
    mock.groq_model = "test-model"
    mock.llm_retry_max_attempts = 3
    mock.llm_retry_min_wait_seconds = 0.1  # Short for testing (not prod value)
    mock.llm_retry_max_wait_seconds = 1
    mock.llm_max_concurrent_requests = 2  # Matches new production default
    return mock


class TestGroqProviderRetry:
    """Test retry logic with exponential backoff in GroqProvider."""

    def test_retry_on_429_rate_limit(self, mock_settings):
        """Test that 429 errors trigger retry with backoff."""
        provider = GroqProvider(mock_settings)
        
        # Create mock responses: 2 failures, then success
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}
        mock_response_429.json.return_value = {"error": "rate limit"}
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        
        with patch("httpx.post") as mock_post:
            # First two calls return 429, third succeeds
            mock_post.side_effect = [
                mock_response_429,
                mock_response_429,
                mock_response_success,
            ]
            
            # Should succeed after retries
            result = provider.generate("test prompt", LlmTask.SUMMARY)
            
            assert result == "Test response"
            assert mock_post.call_count == 3

    def test_retry_exhausted_raises_error(self, mock_settings):
        """Test that exhausted retries raise LlmError."""
        provider = GroqProvider(mock_settings)
        
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}
        
        with patch("httpx.post") as mock_post:
            # Always return 429
            mock_post.return_value = mock_response_429
            
            # Should raise LlmError after max attempts
            with pytest.raises(LlmError, match="failed after retries"):
                provider.generate("test prompt", LlmTask.SUMMARY)
            
            # Should have tried settings.llm_retry_max_attempts times (uses global settings)
            assert mock_post.call_count == settings.llm_retry_max_attempts

    def test_retry_on_5xx_server_error(self, mock_settings):
        """Test that 5xx errors trigger retry."""
        provider = GroqProvider(mock_settings)
        
        mock_response_500 = Mock()
        mock_response_500.status_code = 503
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = [mock_response_500, mock_response_success]
            
            result = provider.generate("test prompt", LlmTask.SUMMARY)
            
            assert result == "Test response"
            assert mock_post.call_count == 2

    def test_retry_on_timeout(self, mock_settings):
        """Test that timeout errors trigger retry."""
        provider = GroqProvider(mock_settings)
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        
        with patch("httpx.post") as mock_post:
            # First call times out, second succeeds
            mock_post.side_effect = [
                httpx.TimeoutException("Request timeout"),
                mock_response_success,
            ]
            
            result = provider.generate("test prompt", LlmTask.SUMMARY)
            
            assert result == "Test response"
            assert mock_post.call_count == 2

    def test_no_retry_on_auth_error(self, mock_settings):
        """Test that 401 errors do not trigger retry."""
        provider = GroqProvider(mock_settings)
        
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response_401
        )
        
        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_response_401
            
            with pytest.raises(LlmError, match="Groq API error"):
                provider.generate("test prompt", LlmTask.SUMMARY)
            
            # Should only try once (no retry)
            assert mock_post.call_count == 1

    def test_strips_thinking_tags(self, mock_settings):
        """Test that thinking tags are stripped from response."""
        provider = GroqProvider(mock_settings)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "<think>reasoning</think>Final answer"}}]
        }
        
        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_response
            
            result = provider.generate("test prompt", LlmTask.SUMMARY)
            
            assert result == "Final answer"
            assert "<think>" not in result


class TestConcurrencyLimiting:
    """Test semaphore-based rate limiting for concurrent operations."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_requests(self):
        """Test that semaphore limits concurrent LLM operations."""
        # Reset semaphore for test
        import app.services.llm as llm_module
        llm_module._llm_semaphore = None
        
        with patch.object(settings, 'llm_max_concurrent_requests', 2):
            semaphore = _get_llm_semaphore()
            assert semaphore._value == 2
            
            # Track concurrent executions
            concurrent_count = 0
            max_concurrent = 0
            
            async def mock_task():
                nonlocal concurrent_count, max_concurrent
                async with semaphore:
                    concurrent_count += 1
                    max_concurrent = max(max_concurrent, concurrent_count)
                    await asyncio.sleep(0.1)  # Simulate work
                    concurrent_count -= 1
            
            # Start 5 tasks
            tasks = [mock_task() for _ in range(5)]
            await asyncio.gather(*tasks)
            
            # Max concurrent should not exceed semaphore limit
            assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_schedule_summary_uses_semaphore(self):
        """Test that schedule_summary_and_todos uses semaphore."""
        # Reset semaphore
        import app.services.llm as llm_module
        llm_module._llm_semaphore = None
        
        with patch.object(settings, 'llm_max_concurrent_requests', 2):
            with patch("app.services.llm._run_summary_and_todos") as mock_run:
                mock_run.return_value = None
                
                # Track when semaphore is acquired
                semaphore = _get_llm_semaphore()
                original_acquire = semaphore.acquire
                acquire_count = 0
                
                async def track_acquire(*args, **kwargs):
                    nonlocal acquire_count
                    acquire_count += 1
                    return await original_acquire(*args, **kwargs)
                
                with patch.object(semaphore, 'acquire', side_effect=track_acquire):
                    # Schedule multiple tasks
                    tasks = [
                        schedule_summary_and_todos(1, 1),
                        schedule_summary_and_todos(2, 2),
                    ]
                    await asyncio.gather(*tasks)
                
                # Each task should acquire the semaphore
                assert acquire_count == 2
                assert mock_run.call_count == 2


class TestRateLimitingIntegration:
    """Integration tests for rate limiting across bulk uploads."""

    @pytest.mark.asyncio
    async def test_bulk_upload_rate_limiting(self):
        """Test that bulk uploads respect rate limits."""
        # Reset semaphore
        import app.services.llm as llm_module
        llm_module._llm_semaphore = None
        
        with patch.object(settings, 'llm_max_concurrent_requests', 2):
            execution_order = []
            
            async def mock_process(session_id: int):
                """Mock processing that tracks execution."""
                semaphore = _get_llm_semaphore()
                async with semaphore:
                    execution_order.append(f"start_{session_id}")
                    await asyncio.sleep(0.05)  # Simulate work
                    execution_order.append(f"end_{session_id}")
            
            # Simulate 5 uploads
            tasks = [mock_process(i) for i in range(5)]
            await asyncio.gather(*tasks)
            
            # Verify ordering shows concurrency limiting
            # At any point, no more than 2 should be running
            running = []
            for event in execution_order:
                if event.startswith("start"):
                    running.append(event)
                    assert len(running) <= 2, f"Too many concurrent: {running}"
                elif event.startswith("end"):
                    session = event.replace("end", "start")
                    running.remove(session)


class TestConfigurationValidation:
    """Test configuration settings for rate limiting."""

    def test_default_configuration(self):
        """Test that default configuration is reasonable."""
        assert settings.llm_max_concurrent_requests >= 1
        assert settings.llm_retry_max_attempts >= 1
        assert settings.llm_retry_min_wait_seconds >= 0
        assert settings.llm_retry_max_wait_seconds > settings.llm_retry_min_wait_seconds

    def test_configuration_override(self):
        """Test that configuration can be overridden."""
        with patch.object(settings, 'llm_max_concurrent_requests', 10):
            assert settings.llm_max_concurrent_requests == 10
        
        with patch.object(settings, 'llm_retry_max_attempts', 10):
            assert settings.llm_retry_max_attempts == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
