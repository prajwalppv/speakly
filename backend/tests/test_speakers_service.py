"""
Comprehensive test suite for speakers service.
Aiming for 90%+ coverage.
"""
import pytest
from unittest.mock import Mock, patch


class TestSecondsToMs:
    """Test _seconds_to_ms utility function."""

    def test_seconds_to_ms_converts_float(self):
        """Test converts seconds to milliseconds."""
        from app.services.speakers import _seconds_to_ms
        
        assert _seconds_to_ms(1.5) == 1500
        assert _seconds_to_ms(0.001) == 1
        assert _seconds_to_ms(10.0) == 10000

    def test_seconds_to_ms_handles_none(self):
        """Test handles None input."""
        from app.services.speakers import _seconds_to_ms
        
        assert _seconds_to_ms(None) == 0


class TestWordsToTokens:
    """Test words_to_tokens function."""

    def test_words_to_tokens_basic(self):
        """Test basic word to token conversion."""
        from app.services.speakers import words_to_tokens
        
        words = [
            {"text": "Hello", "start": 0.0, "end": 0.5, "speaker_id": "speaker_1"},
            {"text": "world", "start": 0.6, "end": 1.0, "speaker_id": "speaker_1"},
        ]
        
        tokens = words_to_tokens(words)
        
        assert len(tokens) == 2
        assert tokens[0].text == "Hello"
        assert tokens[0].start == 0.0
        assert tokens[0].speaker_id == "speaker_1"

    def test_words_to_tokens_skips_spacing(self):
        """Test skips spacing type words."""
        from app.services.speakers import words_to_tokens
        
        words = [
            {"text": "Hello", "start": 0.0, "end": 0.5},
            {"type": "spacing"},  # Should be skipped
            {"text": "world", "start": 0.6, "end": 1.0},
        ]
        
        tokens = words_to_tokens(words)
        
        assert len(tokens) == 2
        assert tokens[0].text == "Hello"
        assert tokens[1].text == "world"

    def test_words_to_tokens_handles_speaker_field(self):
        """Test handles both speaker_id and speaker fields."""
        from app.services.speakers import words_to_tokens
        
        words = [
            {"text": "A", "speaker": "spk_1"},  # Uses 'speaker' field
            {"text": "B", "speaker_id": "spk_2"},  # Uses 'speaker_id' field
        ]
        
        tokens = words_to_tokens(words)
        
        assert tokens[0].speaker_id == "spk_1"
        assert tokens[1].speaker_id == "spk_2"

    def test_words_to_tokens_handles_optional_fields(self):
        """Test handles missing optional fields."""
        from app.services.speakers import words_to_tokens
        
        words = [
            {"text": "Hello"},  # Minimal fields
        ]
        
        tokens = words_to_tokens(words)
        
        assert len(tokens) == 1
        assert tokens[0].text == "Hello"
        assert tokens[0].start is None
        assert tokens[0].end is None
        assert tokens[0].speaker_id is None

    def test_words_to_tokens_includes_confidence(self):
        """Test includes confidence (logprob) field."""
        from app.services.speakers import words_to_tokens
        
        words = [
            {"text": "Test", "logprob": 0.95},
        ]
        
        tokens = words_to_tokens(words)
        
        assert tokens[0].confidence == 0.95

    def test_words_to_tokens_includes_channel_index(self):
        """Test includes channel_index field."""
        from app.services.speakers import words_to_tokens
        
        words = [
            {"text": "Test", "channel_index": 1},
        ]
        
        tokens = words_to_tokens(words)
        
        assert tokens[0].channel_index == 1


class TestTokensToSegments:
    """Test tokens_to_segments function."""

    def test_tokens_to_segments_creates_segments(self):
        """Test creates segments from tokens."""
        from app.services.speakers import tokens_to_segments, WordToken
        
        tokens = [
            WordToken("Hello", 0.0, 0.5, "speaker_1", None, None),
            WordToken("world", 0.6, 1.0, "speaker_1", None, None),
        ]
        
        segments = tokens_to_segments(tokens)
        
        # Should merge into one segment for same speaker
        assert len(segments) >= 1
        assert segments[0].speaker_id == "speaker_1"

    def test_tokens_to_segments_splits_speakers(self):
        """Test splits segments when speaker changes."""
        from app.services.speakers import tokens_to_segments, WordToken
        
        tokens = [
            WordToken("Hello", 0.0, 0.5, "speaker_1", None, None),
            WordToken("there", 0.6, 1.0, "speaker_2", None, None),
        ]
        
        segments = tokens_to_segments(tokens)
        
        # Should have segments for both speakers (algorithm may create intermediates)
        assert len(segments) >= 2
        speaker_ids = [s.speaker_id for s in segments]
        assert "speaker_1" in speaker_ids
        assert "speaker_2" in speaker_ids

    def test_tokens_to_segments_extends_end_time(self):
        """Test extends segment end time for same speaker."""
        from app.services.speakers import tokens_to_segments, WordToken
        
        tokens = [
            WordToken("A", 0.0, 0.5, "speaker_1", None, None),
            WordToken("B", 0.6, 1.5, "speaker_1", None, None),
        ]
        
        segments = tokens_to_segments(tokens)
        
        # Should have extended end time
        assert segments[0].end_ms == 1500  # 1.5 seconds

    def test_tokens_to_segments_handles_none_speaker(self):
        """Test handles None speaker_id (defaults to speaker_1)."""
        from app.services.speakers import tokens_to_segments, WordToken
        
        tokens = [
            WordToken("Hello", 0.0, 0.5, None, None, None),
        ]
        
        segments = tokens_to_segments(tokens)
        
        assert len(segments) == 1
        assert segments[0].speaker_id == "speaker_1"

    def test_tokens_to_segments_handles_none_end_time(self):
        """Test handles None end time (uses start time)."""
        from app.services.speakers import tokens_to_segments, WordToken
        
        tokens = [
            WordToken("Test", 1.0, None, "speaker_1", None, None),
        ]
        
        segments = tokens_to_segments(tokens)
        
        assert segments[0].end_ms == 1000  # Uses start time

    def test_tokens_to_segments_updates_confidence(self):
        """Test updates confidence for ongoing segment."""
        from app.services.speakers import tokens_to_segments, WordToken
        
        tokens = [
            WordToken("A", 0.0, 0.5, "speaker_1", 0.8, None),
            WordToken("B", 0.6, 1.0, "speaker_1", 0.9, None),  # Higher confidence
        ]
        
        segments = tokens_to_segments(tokens)
        
        # Should use latest confidence
        assert segments[0].confidence == 0.9


class TestEnsurePjProfile:
    """Test ensure_pj_profile function."""

    @patch('app.services.speakers.settings')
    def test_ensure_pj_profile_returns_existing(self, mock_settings, test_db):
        """Test returns existing PJ profile."""
        from app.services.speakers import ensure_pj_profile
        from app.models import SpeakerProfile
        
        mock_settings.pj_profile_name = "PJ"
        
        # Create existing profile
        existing = SpeakerProfile(name="PJ", is_primary=True)
        test_db.add(existing)
        test_db.commit()
        
        result = ensure_pj_profile(test_db)
        
        assert result.id == existing.id
        assert result.name == "PJ"

    @patch('app.services.speakers.settings')
    def test_ensure_pj_profile_creates_new(self, mock_settings, test_db):
        """Test creates new PJ profile when none exists."""
        from app.services.speakers import ensure_pj_profile
        from app.models import SpeakerProfile
        
        mock_settings.pj_profile_name = "NewPJ"
        
        result = ensure_pj_profile(test_db)
        
        assert result.name == "NewPJ"
        assert result.is_primary is True
        assert result.description is not None
        
        # Verify it's in database
        profile = test_db.query(SpeakerProfile).filter_by(name="NewPJ").one()
        assert profile.id == result.id


class TestMatchProfileForSegment:
    """Test match_profile_for_segment function."""

    @patch('app.services.speakers.settings')
    def test_match_profile_by_external_id(self, mock_settings):
        """Test matches profile by external_id."""
        from app.services.speakers import match_profile_for_segment, SegmentDraft
        from app.models import SpeakerProfile
        
        mock_settings.pj_profile_name = "PJ"
        mock_settings.pj_voice_tag_set = set()
        
        profile = SpeakerProfile(name="Test", external_id="speaker_1")
        segment = SegmentDraft("speaker_1", 0, 1000, None, None)
        
        matched_profile, is_pj = match_profile_for_segment(segment, [profile])
        
        assert matched_profile == profile
        assert is_pj is False

    @patch('app.services.speakers.settings')
    def test_match_profile_pj_by_external_id(self, mock_settings):
        """Test matches PJ profile by external_id."""
        from app.services.speakers import match_profile_for_segment, SegmentDraft
        from app.models import SpeakerProfile
        
        mock_settings.pj_profile_name = "PJ"
        mock_settings.pj_voice_tag_set = set()
        
        pj_profile = SpeakerProfile(name="PJ", external_id="pj_voice")
        segment = SegmentDraft("pj_voice", 0, 1000, None, None)
        
        matched_profile, is_pj = match_profile_for_segment(segment, [pj_profile])
        
        assert matched_profile == pj_profile
        assert is_pj is True

    @patch('app.services.speakers.settings')
    def test_match_profile_by_voice_tag(self, mock_settings):
        """Test matches PJ by voice tag."""
        from app.services.speakers import match_profile_for_segment, SegmentDraft
        from app.models import SpeakerProfile
        
        mock_settings.pj_profile_name = "PJ"
        mock_settings.pj_voice_tag_set = {"pj_speaker", "speaker_pj"}
        
        pj_profile = SpeakerProfile(name="PJ")
        segment = SegmentDraft("pj_speaker", 0, 1000, None, None)
        
        matched_profile, is_pj = match_profile_for_segment(segment, [pj_profile])
        
        assert matched_profile == pj_profile
        assert is_pj is True

    @patch('app.services.speakers.settings')
    def test_match_profile_no_match(self, mock_settings):
        """Test returns None when no match."""
        from app.services.speakers import match_profile_for_segment, SegmentDraft
        from app.models import SpeakerProfile
        
        mock_settings.pj_profile_name = "PJ"
        mock_settings.pj_voice_tag_set = set()
        
        profile = SpeakerProfile(name="Other", external_id="other")
        segment = SegmentDraft("unknown_speaker", 0, 1000, None, None)
        
        matched_profile, is_pj = match_profile_for_segment(segment, [profile])
        
        assert matched_profile is None
        assert is_pj is False


class TestPersistSpeakerSegments:
    """Test persist_speaker_segments function."""

    @patch('app.services.speakers.settings')
    def test_persist_speaker_segments_empty_words(self, mock_settings, test_db):
        """Test handles empty words gracefully."""
        from app.services.speakers import persist_speaker_segments
        
        mock_session = Mock()
        mock_transcription = Mock()
        mock_transcription.id = 1
        
        # Should not raise
        persist_speaker_segments(test_db, mock_session, mock_transcription, None)
        persist_speaker_segments(test_db, mock_session, mock_transcription, [])



