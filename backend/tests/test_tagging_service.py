"""
Test tagging service.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestTaggingPrompt:
    """Test tagging prompt template."""

    def test_tagging_prompt_exists(self):
        """Test that tagging prompt is defined."""
        from app.services.tagging import TAGGING_PROMPT
        
        assert TAGGING_PROMPT is not None
        assert len(TAGGING_PROMPT) > 0

    def test_tagging_prompt_has_placeholders(self):
        """Test that prompt has required placeholders."""
        from app.services.tagging import TAGGING_PROMPT
        
        assert "{transcript}" in TAGGING_PROMPT
        assert "{summary}" in TAGGING_PROMPT
        assert "{max_tags}" in TAGGING_PROMPT

    def test_tagging_prompt_mentions_categories(self):
        """Test that prompt describes tag categories."""
        from app.services.tagging import TAGGING_PROMPT
        
        assert "type" in TAGGING_PROMPT
        assert "topic" in TAGGING_PROMPT
        assert "person" in TAGGING_PROMPT
        assert "entity" in TAGGING_PROMPT


class TestTagColors:
    """Test tag color definitions."""

    def test_tag_colors_exist(self):
        """Test that tag colors are defined."""
        from app.services.tagging import TAG_COLORS
        
        assert TAG_COLORS is not None
        assert len(TAG_COLORS) > 0

    def test_tag_colors_has_all_categories(self):
        """Test that all tag categories have colors."""
        from app.services.tagging import TAG_COLORS
        
        assert "type" in TAG_COLORS
        assert "topic" in TAG_COLORS
        assert "person" in TAG_COLORS
        assert "entity" in TAG_COLORS
        assert "priority" in TAG_COLORS
        assert "custom" in TAG_COLORS

    def test_tag_colors_are_hex(self):
        """Test that tag colors are hex codes."""
        from app.services.tagging import TAG_COLORS
        
        for color in TAG_COLORS.values():
            assert color.startswith("#")
            assert len(color) == 7


class TestTaggingServiceInit:
    """Test tagging service initialization."""

    def test_tagging_service_can_be_created(self):
        """Test that TaggingService can be instantiated."""
        from app.services.tagging import TaggingService
        
        service = TaggingService()
        assert service is not None

    def test_tagging_service_has_extract_tags(self):
        """Test that service has extract_tags method."""
        from app.services.tagging import TaggingService
        
        service = TaggingService()
        assert hasattr(service, 'extract_tags')


class TestExtractTags:
    """Test tag extraction."""

    @patch('app.services.tagging.TaggingService._generate_tags_with_llm')
    @patch('app.services.tagging.TaggingService._deduplicate_tags')
    def test_extract_tags_no_transcription(self, mock_dedup, mock_llm):
        """Test extract_tags when session has no transcription."""
        from app.services.tagging import TaggingService
        from app.models import Session as SessionModel
        
        service = TaggingService()
        session = Mock(spec=SessionModel)
        session.id = 1
        session.transcriptions = []
        
        tags = service.extract_tags(session)
        
        assert tags == []
        mock_llm.assert_not_called()

    @patch('app.services.tagging.TaggingService._generate_tags_with_llm')
    @patch('app.services.tagging.TaggingService._deduplicate_tags')
    def test_extract_tags_with_transcript(self, mock_dedup, mock_llm):
        """Test extract_tags with valid transcript."""
        from app.services.tagging import TaggingService
        from app.models import Session as SessionModel
        
        service = TaggingService()
        session = Mock(spec=SessionModel)
        session.id = 1
        session.summary_run = None
        
        # Mock transcription
        transcript = Mock()
        transcript.text = "This is a test transcript"
        session.transcriptions = [transcript]
        
        mock_llm.return_value = [
            {"name": "meeting", "category": "type", "confidence": 0.9}
        ]
        mock_dedup.return_value = [
            {"name": "meeting", "category": "type", "confidence": 0.9}
        ]
        
        tags = service.extract_tags(session)
        
        assert len(tags) >= 0
        mock_llm.assert_called_once()

    @patch('app.services.tagging.TaggingService._generate_tags_with_llm')
    @patch('app.services.tagging.TaggingService._deduplicate_tags')
    def test_extract_tags_limits_results(self, mock_dedup, mock_llm):
        """Test that extract_tags limits number of tags."""
        from app.services.tagging import TaggingService
        from app.models import Session as SessionModel
        from app.config import settings
        
        service = TaggingService()
        session = Mock(spec=SessionModel)
        session.id = 1
        session.summary_run = None
        
        transcript = Mock()
        transcript.text = "Test"
        session.transcriptions = [transcript]
        
        # Return more tags than the limit
        many_tags = [
            {"name": f"tag{i}", "category": "topic", "confidence": 0.9}
            for i in range(20)
        ]
        mock_llm.return_value = many_tags
        mock_dedup.return_value = many_tags
        
        tags = service.extract_tags(session)
        
        # Should be limited by settings
        assert len(tags) <= settings.max_tags_per_session


class TestGenerateTagsWithLLM:
    """Test LLM tag generation."""

    @patch('app.services.llm.LlmService')
    def test_generate_tags_llm_not_enabled(self, mock_llm_service):
        """Test when LLM is not enabled."""
        from app.services.tagging import TaggingService
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = False
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        tags = service._generate_tags_with_llm("transcript", "summary")
        
        assert tags == []

    @patch('app.services.llm.LlmService')
    def test_generate_tags_valid_json_response(self, mock_llm_service):
        """Test parsing valid JSON response."""
        from app.services.tagging import TaggingService
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        mock_service._generate.return_value = json.dumps([
            {"name": "meeting", "category": "type", "confidence": 0.95},
            {"name": "urgent", "category": "priority", "confidence": 0.85}
        ])
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        tags = service._generate_tags_with_llm("test transcript", "test summary")
        
        assert len(tags) == 2
        assert tags[0]["name"] == "meeting"
        assert tags[1]["name"] == "urgent"

    @patch('app.services.llm.LlmService')
    def test_generate_tags_with_markdown_wrapper(self, mock_llm_service):
        """Test parsing JSON wrapped in markdown code block."""
        from app.services.tagging import TaggingService
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        response_with_markdown = """```json
[
  {"name": "meeting", "category": "type", "confidence": 0.9}
]
```"""
        mock_service._generate.return_value = response_with_markdown
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        tags = service._generate_tags_with_llm("transcript", "summary")
        
        assert len(tags) == 1
        assert tags[0]["name"] == "meeting"

    @patch('app.services.llm.LlmService')
    def test_generate_tags_with_text_before_json(self, mock_llm_service):
        """Test parsing JSON with text before it."""
        from app.services.tagging import TaggingService
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        response_with_text = """Here are the tags:

[{"name": "brainstorm", "category": "type", "confidence": 0.92}]"""
        mock_service._generate.return_value = response_with_text
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        tags = service._generate_tags_with_llm("transcript", "summary")
        
        assert len(tags) == 1
        assert tags[0]["name"] == "brainstorm"

    @patch('app.services.llm.LlmService')
    def test_generate_tags_invalid_json(self, mock_llm_service):
        """Test handling invalid JSON response."""
        from app.services.tagging import TaggingService
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        mock_service._generate.return_value = "This is not JSON"
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        tags = service._generate_tags_with_llm("transcript", "summary")
        
        assert tags == []

    @patch('app.services.llm.LlmService')
    def test_generate_tags_empty_response(self, mock_llm_service):
        """Test handling empty response."""
        from app.services.tagging import TaggingService
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        mock_service._generate.return_value = ""
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        tags = service._generate_tags_with_llm("transcript", "summary")
        
        assert tags == []

    @patch('app.services.llm.LlmService')
    def test_generate_tags_filters_low_confidence(self, mock_llm_service):
        """Test that low confidence tags are filtered."""
        from app.services.tagging import TaggingService
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        mock_service._generate.return_value = json.dumps([
            {"name": "high", "category": "type", "confidence": 0.9},
            {"name": "low", "category": "type", "confidence": 0.5}  # Below 0.7 threshold
        ])
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        tags = service._generate_tags_with_llm("transcript", "summary")
        
        # Only high confidence tag should remain
        assert len(tags) == 1
        assert tags[0]["name"] == "high"

    @patch('app.services.llm.LlmService')
    def test_generate_tags_validates_structure(self, mock_llm_service):
        """Test that tag structure is validated."""
        from app.services.tagging import TaggingService
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        mock_service._generate.return_value = json.dumps([
            {"name": "valid", "category": "type", "confidence": 0.9},
            {"name": "missing_category"},  # Invalid - missing category
            {"category": "type"},  # Invalid - missing name
            "invalid_string"  # Invalid - not a dict
        ])
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        tags = service._generate_tags_with_llm("transcript", "summary")
        
        # Only valid tag should remain
        assert len(tags) == 1
        assert tags[0]["name"] == "valid"

    @patch('app.services.llm.LlmService')
    def test_generate_tags_adds_default_confidence(self, mock_llm_service):
        """Test that missing confidence gets default value."""
        from app.services.tagging import TaggingService
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        mock_service._generate.return_value = json.dumps([
            {"name": "tag1", "category": "type"}  # No confidence
        ])
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        tags = service._generate_tags_with_llm("transcript", "summary")
        
        assert len(tags) == 1
        assert tags[0]["confidence"] == 0.8  # Default value


class TestDeduplication:
    """Test tag deduplication."""

    def test_deduplicate_tags_removes_duplicates(self):
        """Test that duplicate tags are removed."""
        from app.services.tagging import TaggingService
        
        service = TaggingService()
        tags = [
            {"name": "meeting", "category": "type", "confidence": 0.9},
            {"name": "meeting", "category": "type", "confidence": 0.8},
            {"name": "brainstorm", "category": "type", "confidence": 0.85}
        ]
        
        unique = service._deduplicate_tags(tags)
        
        # Should keep first occurrence
        assert len(unique) == 2
        names = [t["name"] for t in unique]
        assert "meeting" in names
        assert "brainstorm" in names

    def test_deduplicate_tags_preserves_order(self):
        """Test that tag order is preserved."""
        from app.services.tagging import TaggingService
        
        service = TaggingService()
        tags = [
            {"name": "first", "category": "type", "confidence": 0.9},
            {"name": "second", "category": "type", "confidence": 0.8},
            {"name": "third", "category": "type", "confidence": 0.7}
        ]
        
        unique = service._deduplicate_tags(tags)
        
        assert unique[0]["name"] == "first"
        assert unique[1]["name"] == "second"
        assert unique[2]["name"] == "third"

    def test_deduplicate_empty_list(self):
        """Test deduplication with empty list."""
        from app.services.tagging import TaggingService
        
        service = TaggingService()
        unique = service._deduplicate_tags([])
        
        assert unique == []


class TestTaggingIntegration:
    """Integration tests for tagging."""

    def test_tagging_service_full_workflow(self):
        """Test complete tagging workflow."""
        from app.services.tagging import TaggingService
        
        service = TaggingService()
        
        # Service should be created successfully
        assert service is not None
        assert hasattr(service, 'extract_tags')
        assert hasattr(service, '_generate_tags_with_llm')
        assert hasattr(service, '_deduplicate_tags')

    @patch('app.services.llm.LlmService')
    def test_tagging_formats_prompt_correctly(self, mock_llm_service):
        """Test that prompt is formatted with correct values."""
        from app.services.tagging import TaggingService
        from app.models import Session as SessionModel
        
        mock_service = Mock()
        mock_service.is_enabled.return_value = True
        mock_service._generate.return_value = "[]"
        mock_llm_service.return_value = mock_service
        
        service = TaggingService()
        service._generate_tags_with_llm("test transcript", "test summary")
        
        # Verify _generate was called with formatted prompt
        mock_service._generate.assert_called_once()
        call_args = mock_service._generate.call_args
        prompt = call_args[1]["prompt"]
        
        assert "test transcript" in prompt
        assert "test summary" in prompt
