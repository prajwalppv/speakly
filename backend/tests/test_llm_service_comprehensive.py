"""
Comprehensive test suite for LLM service.
Testing ALL lines for maximum coverage.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestLlmServiceInit:
    """Test LlmService initialization."""

    def test_init_sets_configuration(self):
        """Test that LlmService initializes with correct config."""
        from app.services.llm import LlmService
        
        service = LlmService()
        
        assert hasattr(service, 'base_url')
        assert hasattr(service, 'model_summary')
        assert hasattr(service, 'model_todo')


class TestLlmServiceIsEnabled:
    """Test is_enabled method."""

    @patch('app.services.llm.settings')
    def test_is_enabled_true_when_base_url_set(self, mock_settings):
        """Test is_enabled returns True when base_url is configured."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        service = LlmService()
        
        assert service.is_enabled() is True

    @patch('app.services.llm.settings')
    def test_is_enabled_false_when_no_base_url(self, mock_settings):
        """Test is_enabled returns False when base_url is empty."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = ""
        service = LlmService()
        
        assert service.is_enabled() is False

    @patch('app.services.llm.settings')
    def test_is_enabled_false_when_base_url_none(self, mock_settings):
        """Test is_enabled returns False when base_url is None."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = None
        service = LlmService()
        
        assert service.is_enabled() is False


class TestLlmServiceGenerate:
    """Test _generate method."""

    @patch('app.services.llm.httpx.post')
    @patch('app.services.llm.settings')
    def test_generate_success(self, mock_settings, mock_post):
        """Test successful LLM generation."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Generated text"}
        mock_post.return_value = mock_response
        
        service = LlmService()
        result = service._generate("Test prompt", "llama3")
        
        assert result == "Generated text"
        mock_post.assert_called_once()

    @patch('app.services.llm.settings')
    def test_generate_raises_error_when_not_configured(self, mock_settings):
        """Test _generate raises error when base_url not configured."""
        from app.services.llm import LlmService, LlmError
        
        mock_settings.ollama_base_url = ""
        service = LlmService()
        
        with pytest.raises(LlmError, match="OLLAMA_BASE_URL not configured"):
            service._generate("Test prompt", "llama3")

    @patch('app.services.llm.httpx.post')
    @patch('app.services.llm.settings')
    def test_generate_raises_error_when_response_empty(self, mock_settings, mock_post):
        """Test _generate raises error when response is missing."""
        from app.services.llm import LlmService, LlmError
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        service = LlmService()
        
        with pytest.raises(LlmError, match="Missing response from Ollama"):
            service._generate("Test prompt", "llama3")

    @patch('app.services.llm.httpx.post')
    @patch('app.services.llm.settings')
    def test_generate_strips_whitespace(self, mock_settings, mock_post):
        """Test _generate strips whitespace from response."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        mock_response = Mock()
        mock_response.json.return_value = {"response": "  Generated text  \n"}
        mock_post.return_value = mock_response
        
        service = LlmService()
        result = service._generate("Test prompt", "llama3")
        
        assert result == "Generated text"


class TestGenerateTitle:
    """Test generate_title method."""

    @patch('app.services.llm.settings')
    def test_generate_title_success(self, mock_settings):
        """Test successful title generation."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        service = LlmService()
        service._generate = Mock(return_value="Meeting about project planning")
        
        title = service.generate_title("Transcript about meeting")
        
        assert title == "Meeting about project planning"

    @patch('app.services.llm.settings')
    def test_generate_title_strips_quotes(self, mock_settings):
        """Test title generation strips surrounding quotes."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        service = LlmService()
        service._generate = Mock(return_value='"Project Planning Meeting"')
        
        title = service.generate_title("Transcript")
        
        assert title == "Project Planning Meeting"

    @patch('app.services.llm.settings')
    def test_generate_title_truncates_long_titles(self, mock_settings):
        """Test title generation truncates titles longer than 60 chars."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        long_title = "A" * 70
        service = LlmService()
        service._generate = Mock(return_value=long_title)
        
        title = service.generate_title("Transcript")
        
        assert len(title) == 60
        assert title.endswith("...")

    @patch('app.services.llm.settings')
    def test_generate_title_fallback_on_error(self, mock_settings):
        """Test title generation falls back on LlmError."""
        from app.services.llm import LlmService, LlmError
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        service = LlmService()
        service._generate = Mock(side_effect=LlmError("Connection failed"))
        
        title = service.generate_title("First sentence. Second sentence.")
        
        assert title == "First sentence"

    @patch('app.services.llm.settings')
    def test_generate_title_fallback_truncates(self, mock_settings):
        """Test fallback title truncates long first sentence."""
        from app.services.llm import LlmService, LlmError
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        long_sentence = "A" * 70
        service = LlmService()
        service._generate = Mock(side_effect=LlmError("Failed"))
        
        title = service.generate_title(long_sentence)
        
        assert len(title) == 60
        assert title.endswith("...")


class TestGenerateSummary:
    """Test generate_summary method."""

    @patch('app.services.llm.settings')
    def test_generate_summary_success(self, mock_settings):
        """Test successful summary generation."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        service = LlmService()
        service._generate = Mock(return_value="Summary of the meeting")
        
        summary = service.generate_summary("Long transcript text")
        
        assert summary == "Summary of the meeting"

    @patch('app.services.llm.settings')
    def test_generate_summary_fallback_on_error(self, mock_settings):
        """Test summary generation falls back on error."""
        from app.services.llm import LlmService, LlmError
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        service = LlmService()
        service._generate = Mock(side_effect=LlmError("Failed"))
        
        summary = service.generate_summary("First. Second. Third. Fourth.")
        
        assert "• First" in summary
        assert "• Second" in summary
        assert "• Third" in summary


class TestExtractTodos:
    """Test extract_todos method."""

    @patch('app.services.llm.settings')
    def test_extract_todos_success(self, mock_settings):
        """Test successful TODO extraction."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        response = {
            "new_tasks": [{"title": "Task 1", "confidence": 0.9}],
            "task_updates": [{"title": "Task 2", "status": "completed"}]
        }
        
        service = LlmService()
        service._generate = Mock(return_value=json.dumps(response))
        
        result = service.extract_todos("Transcript")
        
        assert len(result["new_tasks"]) == 1
        assert len(result["task_updates"]) == 1

    @patch('app.services.llm.settings')
    def test_extract_todos_strips_markdown(self, mock_settings):
        """Test TODO extraction strips markdown code blocks."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        response_json = {"new_tasks": [], "task_updates": []}
        markdown_response = f"```json\n{json.dumps(response_json)}\n```"
        
        service = LlmService()
        service._generate = Mock(return_value=markdown_response)
        
        result = service.extract_todos("Transcript")
        
        assert "new_tasks" in result
        assert "task_updates" in result

    @patch('app.services.llm.settings')
    def test_extract_todos_handles_legacy_list_format(self, mock_settings):
        """Test TODO extraction handles legacy list format."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        legacy_response = [{"title": "Task 1"}, {"title": "Task 2"}]
        
        service = LlmService()
        service._generate = Mock(return_value=json.dumps(legacy_response))
        
        result = service.extract_todos("Transcript")
        
        assert len(result["new_tasks"]) == 2
        assert len(result["task_updates"]) == 0

    @patch('app.services.llm.settings')
    def test_extract_todos_handles_invalid_json(self, mock_settings):
        """Test TODO extraction handles invalid JSON."""
        from app.services.llm import LlmService
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        service = LlmService()
        service._generate = Mock(return_value="Not valid JSON at all")
        
        result = service.extract_todos("Transcript")
        
        assert result == {"new_tasks": [], "task_updates": []}

    @patch('app.services.llm.settings')
    def test_extract_todos_fallback_on_llm_error(self, mock_settings):
        """Test TODO extraction falls back on LLM error."""
        from app.services.llm import LlmService, LlmError
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        
        service = LlmService()
        service._generate = Mock(side_effect=LlmError("Failed"))
        
        result = service.extract_todos("Transcript")
        
        assert result == {"new_tasks": [], "task_updates": []}


class TestSafeMs:
    """Test _safe_ms utility function."""

    def test_safe_ms_with_none(self):
        """Test _safe_ms returns None for None input."""
        from app.services.llm import _safe_ms
        
        assert _safe_ms(None) is None

    def test_safe_ms_with_int(self):
        """Test _safe_ms returns int for int input."""
        from app.services.llm import _safe_ms
        
        assert _safe_ms(1000) == 1000

    def test_safe_ms_with_float(self):
        """Test _safe_ms converts float to int."""
        from app.services.llm import _safe_ms
        
        assert _safe_ms(1000.5) == 1000

    def test_safe_ms_with_string(self):
        """Test _safe_ms converts string to int."""
        from app.services.llm import _safe_ms
        
        assert _safe_ms("1000") == 1000

    def test_safe_ms_with_invalid_value(self):
        """Test _safe_ms returns None for invalid value."""
        from app.services.llm import _safe_ms
        
        assert _safe_ms("invalid") is None


class TestGenerateTitleHelper:
    """Test _generate_title helper function."""

    @patch('app.services.llm.LlmService')
    def test_generate_title_helper_success(self, mock_service_class):
        """Test _generate_title helper succeeds."""
        from app.services.llm import _generate_title
        
        mock_service = Mock()
        mock_service.generate_title.return_value = "Test Title"
        mock_service_class.return_value = mock_service
        
        mock_session = Mock()
        mock_session.id = 1
        mock_db = Mock()
        
        result = _generate_title(mock_service, mock_session, "transcript", mock_db)
        
        assert result is True
        assert mock_session.description == "Test Title"
        mock_db.commit.assert_called()

    @patch('app.services.llm.LlmService')
    def test_generate_title_helper_handles_exception(self, mock_service_class):
        """Test _generate_title helper handles exceptions."""
        from app.services.llm import _generate_title
        
        mock_service = Mock()
        mock_service.generate_title.side_effect = Exception("Failed")
        
        mock_session = Mock()
        mock_session.id = 1
        mock_db = Mock()
        
        result = _generate_title(mock_service, mock_session, "transcript", mock_db)
        
        assert result is False


class TestGenerateSummaryHelper:
    """Test _generate_summary helper function."""

    def test_generate_summary_helper_success(self):
        """Test _generate_summary helper succeeds."""
        from app.services.llm import _generate_summary
        
        mock_service = Mock()
        mock_service.generate_summary.return_value = "Summary text"
        
        mock_summary_run = Mock()
        mock_summary_run.status = "pending"
        
        mock_session = Mock()
        mock_session.id = 1
        mock_session.processing_stages = {"summarizing": {"status": "pending"}}
        
        result = _generate_summary(mock_service, mock_summary_run, "transcript", mock_session)
        
        assert result is True
        assert mock_summary_run.response == "Summary text"
        assert mock_summary_run.status == "completed"


class TestExtractAndCreateTodosHelper:
    """Test _extract_and_create_todos helper function."""

    @patch('app.services.llm.settings')
    def test_extract_and_create_todos_success(self, mock_settings):
        """Test _extract_and_create_todos succeeds."""
        from app.services.llm import _extract_and_create_todos
        
        mock_settings.todo_confidence_threshold = 0.7
        
        mock_service = Mock()
        mock_service.extract_todos.return_value = {
            "new_tasks": [
                {"title": "Task 1", "confidence": 0.9, "due_hint": "tomorrow"},
                {"title": "Task 2", "confidence": 0.8}
            ],
            "task_updates": [{"title": "Update 1", "status": "completed"}]
        }
        
        mock_todo_run = Mock()
        mock_todo_run.id = 1
        
        mock_session = Mock()
        mock_session.id = 1
        mock_session.processing_stages = {}
        
        mock_db = Mock()
        
        success, created, updates = _extract_and_create_todos(
            mock_service, mock_todo_run, "transcript", mock_session, mock_db
        )
        
        assert success is True
        assert created == 2
        assert len(updates) == 1
        assert mock_db.add.call_count == 2

    @patch('app.services.llm.settings')
    def test_extract_and_create_todos_filters_by_confidence(self, mock_settings):
        """Test _extract_and_create_todos filters low confidence tasks."""
        from app.services.llm import _extract_and_create_todos
        
        mock_settings.todo_confidence_threshold = 0.8
        
        mock_service = Mock()
        mock_service.extract_todos.return_value = {
            "new_tasks": [
                {"title": "High", "confidence": 0.9},
                {"title": "Low", "confidence": 0.5}
            ],
            "task_updates": []
        }
        
        mock_todo_run = Mock()
        mock_todo_run.id = 1
        
        mock_session = Mock()
        mock_session.id = 1
        mock_session.processing_stages = {}
        
        mock_db = Mock()
        
        success, created, updates = _extract_and_create_todos(
            mock_service, mock_todo_run, "transcript", mock_session, mock_db
        )
        
        assert created == 1  # Only high confidence task

    @patch('app.services.llm.settings')
    def test_extract_and_create_todos_skips_empty_titles(self, mock_settings):
        """Test _extract_and_create_todos skips tasks with empty titles."""
        from app.services.llm import _extract_and_create_todos
        
        mock_settings.todo_confidence_threshold = 0.7
        
        mock_service = Mock()
        mock_service.extract_todos.return_value = {
            "new_tasks": [
                {"title": "", "confidence": 0.9},
                {"title": "Valid Task", "confidence": 0.9}
            ],
            "task_updates": []
        }
        
        mock_todo_run = Mock()
        mock_todo_run.id = 1
        
        mock_session = Mock()
        mock_session.id = 1
        mock_session.processing_stages = {}
        
        mock_db = Mock()
        
        success, created, updates = _extract_and_create_todos(
            mock_service, mock_todo_run, "transcript", mock_session, mock_db
        )
        
        assert created == 1  # Only valid task


class TestRunSummaryAndTodos:
    """Test _run_summary_and_todos orchestrator function."""

    @patch('app.services.llm.schedule_task_sync')
    @patch('app.services.llm._extract_and_create_todos')
    @patch('app.services.llm._generate_summary')
    @patch('app.services.llm._generate_title')
    @patch('app.services.llm.SessionLocal')
    @patch('app.services.llm.LlmService')
    @patch('app.services.llm.settings')
    def test_run_summary_and_todos_llm_not_enabled(
        self, mock_settings, mock_llm_class, mock_session_local,
        mock_gen_title, mock_gen_summary, mock_extract_todos, mock_schedule_sync
    ):
        """Test _run_summary_and_todos exits early when LLM not enabled."""
        from app.services.llm import _run_summary_and_todos
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = False
        mock_llm_class.return_value = mock_service
        
        _run_summary_and_todos(1, 1)
        
        mock_gen_title.assert_not_called()
        mock_gen_summary.assert_not_called()

    @patch('app.services.llm.settings')
    @patch('app.services.llm.LlmService')
    @patch('app.services.llm.SessionLocal')
    def test_run_summary_and_todos_missing_session(
        self, mock_session_local, mock_llm_class, mock_settings
    ):
        """Test _run_summary_and_todos handles missing session."""
        from app.services.llm import _run_summary_and_todos
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        mock_llm_class.return_value = mock_service
        
        mock_db = Mock()
        mock_db.query().filter_by().one_or_none.return_value = None
        mock_session_local.return_value.__enter__.return_value = mock_db
        
        _run_summary_and_todos(999, 999)
        
        # Should exit early without errors

    @patch('app.services.llm.settings')
    @patch('app.services.llm.schedule_task_sync')
    @patch('app.services.llm._extract_and_create_todos')
    @patch('app.services.llm._generate_summary')
    @patch('app.services.llm._generate_title')
    @patch('app.services.llm.LlmService')
    @patch('app.services.llm.SessionLocal')
    def test_run_summary_and_todos_complete_workflow(
        self, mock_session_local, mock_llm_class, mock_gen_title,
        mock_gen_summary, mock_extract_todos, mock_schedule_sync, mock_settings
    ):
        """Test _run_summary_and_todos complete workflow."""
        from app.services.llm import _run_summary_and_todos
        from app.models import Session, Transcription
        
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model_summary = "llama3"
        mock_settings.ollama_model_todo = "llama3"
        mock_settings.feature_auto_tagging = False
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        mock_service.model_summary = "llama3"
        mock_service.model_todo = "llama3"
        mock_llm_class.return_value = mock_service
        
        mock_session = Mock(spec=Session)
        mock_session.id = 1
        mock_session.processing_stages = {}
        
        mock_transcription = Mock(spec=Transcription)
        mock_transcription.id = 1
        mock_transcription.text = "Test transcript"
        
        mock_db = Mock()
        mock_db.query().filter_by().one_or_none.side_effect = [
            mock_session, mock_transcription
        ]
        mock_db.query().filter_by().count.return_value = 2
        
        mock_session_local.return_value.__enter__.return_value = mock_db
        
        # Mock helper functions
        mock_gen_title.return_value = True
        mock_gen_summary.return_value = True
        mock_extract_todos.return_value = (True, 2, [])
        
        _run_summary_and_todos(1, 1)
        
        # Verify all steps were called
        mock_gen_title.assert_called_once()
        mock_gen_summary.assert_called_once()
        mock_extract_todos.assert_called_once()
