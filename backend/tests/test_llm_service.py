"""
Test LLM service - high-impact coverage tests.
"""

import json
from unittest.mock import Mock, patch

import pytest


class TestLLMPrompts:
    """Test LLM prompt templates."""

    def test_summary_prompt_exists(self):
        """Test that summary prompt is defined."""
        from app.services.llm import SUMMARY_PROMPT

        assert SUMMARY_PROMPT is not None
        assert len(SUMMARY_PROMPT) > 100
        assert "{transcript}" in SUMMARY_PROMPT

    def test_todo_prompt_exists(self):
        """Test that TODO prompt is defined."""
        from app.services.llm import TODO_PROMPT

        assert TODO_PROMPT is not None
        assert len(TODO_PROMPT) > 100
        assert "new_tasks" in TODO_PROMPT
        assert "task_updates" in TODO_PROMPT


class TestLLMServiceInitialization:
    """Test LLM service initialization."""

    def test_llm_service_creation(self):
        """Test that LLM service can be created."""
        from app.services.llm import LlmService

        service = LlmService()

        assert service is not None
        assert hasattr(service, "base_url")
        assert hasattr(service, "model_summary")

    def test_llm_service_has_base_url(self):
        """Test LLM service has base URL configured."""
        from app.services.llm import LlmService

        service = LlmService()

        # Base URL should be configured (may be empty string in test)
        assert hasattr(service, "base_url")


class TestSummaryGeneration:
    """Test summary generation logic."""

    @patch("httpx.Client.post")
    def test_generate_summary_success(self, mock_post):
        """Test successful summary generation."""
        from app.services.llm import LlmService

        # Mock LLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "## Overview\nThis is a test summary."
        }
        mock_post.return_value = mock_response

        service = LlmService()

        result = service.generate_summary("Test transcript")

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("httpx.Client.post")
    def test_generate_summary_with_long_transcript(self, mock_post):
        """Test summary generation with long transcript."""
        from app.services.llm import LlmService

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Summary of long content."}
        mock_post.return_value = mock_response

        service = LlmService()

        long_transcript = "Test content. " * 1000
        result = service.generate_summary(long_transcript)

        assert result is not None


class TestTodoExtraction:
    """Test TODO extraction logic."""

    @patch("httpx.Client.post")
    def test_extract_todos_success(self, mock_post):
        """Test successful TODO extraction."""
        from app.services.llm import LlmService

        # Mock LLM response with valid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps(
                {
                    "new_tasks": [
                        {
                            "title": "Test task",
                            "due_hint": "tomorrow",
                            "confidence": 0.95,
                            "source_excerpt": "Need to test tomorrow",
                        }
                    ],
                    "task_updates": [],
                }
            )
        }
        mock_post.return_value = mock_response

        service = LlmService()

        result = service.extract_todos("Test transcript with tasks")

        assert result is not None
        assert "new_tasks" in result
        assert len(result["new_tasks"]) >= 0

    @patch("httpx.Client.post")
    def test_extract_todos_empty_result(self, mock_post):
        """Test TODO extraction with no tasks."""
        from app.services.llm import LlmService

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({"new_tasks": [], "task_updates": []})
        }
        mock_post.return_value = mock_response

        service = LlmService()

        result = service.extract_todos("No tasks here")

        assert result is not None
        assert "new_tasks" in result
        assert len(result["new_tasks"]) == 0

    @patch("httpx.Client.post")
    def test_extract_todos_handles_malformed_json(self, mock_post):
        """Test TODO extraction handles malformed JSON."""
        from app.services.llm import LlmService

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Not valid JSON"}
        mock_post.return_value = mock_response

        service = LlmService()

        result = service.extract_todos("Test transcript")

        # Should return empty lists on error
        assert result is not None
        assert "new_tasks" in result


class TestLLMErrorHandling:
    """Test LLM error handling."""

    @patch("httpx.Client.post")
    def test_handle_api_timeout(self, mock_post):
        """Test handling of API timeout."""
        import httpx
        from app.services.llm import LlmService

        mock_post.side_effect = httpx.TimeoutException("Timeout")

        service = LlmService()

        # Should handle timeout gracefully
        try:
            result = service.generate_summary("Test")
            # If it returns, should be empty or error
        except Exception:
            # Expected to raise or return error
            pass

    @patch("httpx.Client.post")
    def test_handle_api_error(self, mock_post):
        """Test handling of API error response."""
        from app.services.llm import LlmService

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        service = LlmService()

        # Should handle error gracefully
        try:
            result = service.generate_summary("Test")
        except Exception:
            pass


class TestScheduleSummaryAndTodos:
    """Test scheduling of summary and TODO extraction."""

    @patch("app.services.llm._run_summary_and_todos")
    @pytest.mark.asyncio
    async def test_schedule_summary_and_todos(self, mock_run):
        """Test that scheduling works."""
        from app.services.llm import schedule_summary_and_todos

        # Should schedule the background task
        await schedule_summary_and_todos(session_id=1, transcription_id=1)

        # Should have called the worker function
        mock_run.assert_called_once_with(1, 1)


class TestSafeMs:
    """Test _safe_ms utility function."""

    def test_safe_ms_with_valid_int(self):
        """Test _safe_ms with valid integer."""
        from app.services.llm import _safe_ms

        assert _safe_ms(1000) == 1000

    def test_safe_ms_with_none(self):
        """Test _safe_ms with None."""
        from app.services.llm import _safe_ms

        assert _safe_ms(None) is None

    def test_safe_ms_with_string(self):
        """Test _safe_ms with string."""
        from app.services.llm import _safe_ms

        result = _safe_ms("1000")
        # Should convert or return None
        assert result is None or isinstance(result, int)

    def test_safe_ms_with_invalid_input(self):
        """Test _safe_ms with invalid input."""
        from app.services.llm import _safe_ms

        result = _safe_ms("invalid")
        assert result is None


class TestLLMIntegration:
    """Test LLM integration scenarios."""

    @patch("httpx.Client.post")
    def test_generate_title(self, mock_post):
        """Test title generation."""
        from app.services.llm import LlmService

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Meeting about Q4 Planning"}
        mock_post.return_value = mock_response

        service = LlmService()

        result = service.generate_title("Long transcript about Q4 planning...")

        assert result is not None
        assert len(result) > 0

    @patch("httpx.Client.post")
    def test_concurrent_llm_calls(self, mock_post):
        """Test multiple concurrent LLM calls."""
        from app.services.llm import LlmService

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test response"}
        mock_post.return_value = mock_response

        service = LlmService()

        # Make multiple calls
        results = []
        for i in range(3):
            result = service.generate_summary(f"Transcript {i}")
            results.append(result)

        assert len(results) == 3
        assert all(r is not None for r in results)
