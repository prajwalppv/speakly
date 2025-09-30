from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Session as SessionModel
from ..models import SpeakerProfile, SpeakerSegment, Transcription


@dataclass
class WordToken:
    text: str
    start: float | None
    end: float | None
    speaker_id: str | None
    confidence: float | None
    channel_index: int | None


@dataclass
class SegmentDraft:
    speaker_id: str | None
    start_ms: int
    end_ms: int
    confidence: float | None
    channel_index: int | None


def _seconds_to_ms(value: float | None) -> int:
    if value is None:
        return 0
    return int(value * 1000)


def words_to_tokens(words: Sequence[dict]) -> list[WordToken]:
    tokens: list[WordToken] = []
    for item in words:
        if item.get("type") == "spacing":
            continue
        tokens.append(
            WordToken(
                text=item.get("text", ""),
                start=item.get("start"),
                end=item.get("end"),
                speaker_id=item.get("speaker_id") or item.get("speaker"),
                confidence=item.get("logprob"),
                channel_index=item.get("channel_index"),
            )
        )
    return tokens


def tokens_to_segments(tokens: Sequence[WordToken]) -> list[SegmentDraft]:
    segments: list[SegmentDraft] = []
    current: SegmentDraft | None = None

    for token in tokens:
        label = token.speaker_id or "speaker_1"
        start_ms = _seconds_to_ms(token.start)
        end_ms = _seconds_to_ms(token.end or token.start)

        if current and current.speaker_id == label:
            current.end_ms = max(current.end_ms, end_ms)
            if token.confidence is not None:
                current.confidence = token.confidence
            continue

        if current:
            segments.append(current)

        segments.append(
            SegmentDraft(
                speaker_id=label,
                start_ms=start_ms,
                end_ms=end_ms,
                confidence=token.confidence,
                channel_index=token.channel_index,
            )
        )
        current = segments[-1]

    return segments


def ensure_pj_profile(db: Session) -> SpeakerProfile:
    profile = (
        db.query(SpeakerProfile)
        .filter(SpeakerProfile.name == settings.pj_profile_name)
        .one_or_none()
    )
    if profile:
        return profile

    profile = SpeakerProfile(
        name=settings.pj_profile_name,
        description="Autocreated profile for PJ voice identification",
        is_primary=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def match_profile_for_segment(
    segment: SegmentDraft,
    profiles: Iterable[SpeakerProfile],
) -> tuple[SpeakerProfile | None, bool]:
    segment_label = (segment.speaker_id or "").lower()
    for profile in profiles:
        if profile.external_id and profile.external_id.lower() == segment_label:
            return profile, profile.name.lower() == settings.pj_profile_name.lower()
        if segment_label in settings.pj_voice_tag_set and profile.name.lower() == settings.pj_profile_name.lower():
            return profile, True
    return None, False


def persist_speaker_segments(
    db: Session,
    session: SessionModel,
    transcription: Transcription,
    payload_words: Sequence[dict] | None,
) -> None:
    if not payload_words:
        return

    tokens = words_to_tokens(payload_words)
    if not tokens:
        return

    segments = tokens_to_segments(tokens)
    pj_profile = ensure_pj_profile(db)
    profiles = [pj_profile]

    # Clear existing segments for this transcription
    db.query(SpeakerSegment).filter_by(transcription_id=transcription.id).delete()

    has_pj = False
    for draft in segments:
        profile, is_pj = match_profile_for_segment(draft, profiles)
        has_pj = has_pj or is_pj
        db.add(
            SpeakerSegment(
                session_id=session.id,
                transcription_id=transcription.id,
                speaker_label=draft.speaker_id,
                speaker_profile_id=profile.id if profile else None,
                start_ms=draft.start_ms,
                end_ms=draft.end_ms,
                confidence=draft.confidence,
                is_pj=is_pj,
                channel_index=draft.channel_index,
            )
        )

    session.has_pj = has_pj or session.has_pj
