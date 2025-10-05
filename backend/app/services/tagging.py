"""Service for extracting and managing tags for sessions."""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from ..models import Session as SessionModel, Tag, SessionTag
from ..config import settings

logger = logging.getLogger(__name__)

# Tag category colors for UI
TAG_COLORS = {
    "type": "#3b82f6",      # Blue - meeting types
    "topic": "#8b5cf6",     # Purple - topics/themes
    "person": "#10b981",    # Green - people
    "entity": "#f59e0b",    # Amber - projects/clients/features
    "priority": "#ef4444",  # Red - priority/urgency
    "custom": "#d4af37",    # Gold - user-added
}

TAGGING_PROMPT = """Analyze this recording to extract the MOST INFORMATIVE tags that help mentally map and recall this content.

Transcript (first 3000 chars):
{transcript}

Summary:
{summary}

Your goal: Select {max_tags} tags that answer "What is this about?" in the most useful way.

PRIORITIZE TAGS BY INFORMATION VALUE:
1. WHAT happened: Meeting type or activity (meeting, brainstorm, update, decision, call, etc.)
2. WHO was involved: Key people mentioned (prefix with @, e.g., @sarah)
3. MAIN TOPIC: The primary subject or domain (product, engineering, sales, personal, etc.)
4. SPECIFIC CONTEXT: Projects, clients, or specific areas (prefix with # e.g., #website-redesign, #client-acme)
5. URGENCY/ACTION: Only if critical (urgent, followup, blocked, decision-needed)

AVOID generic tags like "informational", "general", "update" unless nothing more specific applies.

Tag Categories:
- type: meeting, brainstorm, review, planning, standup, call, interview, training, decision
- topic: product, engineering, design, marketing, sales, support, personal, errands, family, health, finance
- person: @name (people mentioned, lowercase, no spaces)
- entity: #project-name, #client-name, #feature-name (specific things discussed)
- priority: urgent, followup, blocked, decision-needed (ONLY if clearly applicable)

Return ONLY a JSON array ordered from MOST to LEAST informative:
[
  {{"name": "brainstorm", "category": "type", "confidence": 0.95}},
  {{"name": "@sarah", "category": "person", "confidence": 0.92}},
  {{"name": "#website-redesign", "category": "entity", "confidence": 0.90}},
  {{"name": "design", "category": "topic", "confidence": 0.85}},
  {{"name": "urgent", "category": "priority", "confidence": 0.82}}
]

RULES:
- Maximum {max_tags} tags total
- Order by informativeness (most useful first)
- Only include tags with confidence > 0.7
- Use lowercase, no spaces in names (use hyphens)
- Be specific > generic (e.g., "product-launch" > "planning")
- NO DUPLICATES: Avoid semantically similar tags (e.g., don't include both "car-repair" AND "#car-repair-project", pick the MOST specific one)
- NO REDUNDANCY: Each tag must add NEW information (e.g., if you have "#website-redesign", don't also add "design")
- Must return valid JSON array only, no other text

JSON:"""


class TaggingService:
    """Service for extracting and managing session tags."""
    
    def extract_tags(self, session: SessionModel) -> List[Dict[str, Any]]:
        """
        Extract tags from session transcript and summary using LLM.
        
        Args:
            session: Session model instance
            
        Returns:
            List of tag dicts with name, category, and confidence
        """
        if not session.transcriptions or not session.transcriptions[0].text:
            logger.warning(f"No transcription found for session {session.id}")
            return []
        
        transcript = session.transcriptions[0].text[:3000]  # Limit length
        summary = session.summary_run.response if session.summary_run else ""
        
        # Generate tags using LLM
        ai_tags = self._generate_tags_with_llm(transcript, summary)
        
        # Deduplicate and limit
        unique_tags = self._deduplicate_tags(ai_tags)
        limited_tags = unique_tags[:settings.max_tags_per_session]
        
        logger.info(f"Extracted {len(limited_tags)} tags for session {session.id} (limit: {settings.max_tags_per_session})")
        return limited_tags
    
    def _generate_tags_with_llm(self, transcript: str, summary: str) -> List[Dict[str, Any]]:
        """Generate tags using LLM."""
        try:
            from .llm import LlmService, LlmError
            
            service = LlmService()
            if not service.is_enabled():
                logger.info("Ollama not configured, skipping AI tag generation")
                return []
            
            # Get max tags from settings
            max_llm_tags = settings.max_tags_per_session
            
            prompt = TAGGING_PROMPT.format(
                transcript=transcript, 
                summary=summary,
                max_tags=max_llm_tags
            )
            
            response = service._generate(
                prompt=prompt,
                model=settings.ollama_model_summary  # Use same model as summaries
            )
            
            # Debug: Log the raw response
            logger.info(f"LLM raw response (first 500 chars): {response[:500]}")
            
            # Parse JSON response
            # Clean up response to extract just the JSON array
            response = response.strip()
            
            # Handle markdown code blocks
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
                response = response.strip()
            
            # Handle text before JSON (e.g., "Here are the tags:\n\n[...]")
            # Find the first '[' and extract from there
            json_start = response.find('[')
            if json_start > 0:
                response = response[json_start:]
            
            # Find the last ']' to handle any text after JSON
            json_end = response.rfind(']')
            if json_end >= 0:
                response = response[:json_end + 1]
            
            response = response.strip()
            
            if not response:
                logger.warning("LLM returned empty response for tags")
                return []
            
            tags = json.loads(response)
            
            # Validate structure
            if not isinstance(tags, list):
                logger.error(f"LLM returned non-list response: {response}")
                return []
            
            # Filter and validate each tag
            valid_tags = []
            for tag in tags:
                if isinstance(tag, dict) and "name" in tag and "category" in tag:
                    tag["confidence"] = tag.get("confidence", 0.8)
                    if tag["confidence"] >= 0.7:
                        valid_tags.append(tag)
            
            return valid_tags[:max_llm_tags]
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM tag response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error generating tags with LLM: {e}")
            return []
    
    def _generate_context_tags(self, session: SessionModel) -> List[Dict[str, Any]]:
        """Generate automatic context-based tags."""
        context_tags = []
        
        # Day of week
        day = session.created_at.strftime("%A").lower()
        context_tags.append({
            "name": day,
            "category": "context",
            "confidence": 1.0
        })
        
        # Time of day
        hour = session.created_at.hour
        if hour < 12:
            time_tag = "morning"
        elif hour < 17:
            time_tag = "afternoon"
        else:
            time_tag = "evening"
        
        context_tags.append({
            "name": time_tag,
            "category": "context",
            "confidence": 1.0
        })
        
        # Duration-based (based on word count)
        if session.transcriptions and session.transcriptions[0].text:
            word_count = len(session.transcriptions[0].text.split())
            if word_count < 100:
                duration_tag = "quick-note"
            elif word_count > 1000:
                duration_tag = "long-session"
            else:
                duration_tag = "standard"
            
            context_tags.append({
                "name": duration_tag,
                "category": "context",
                "confidence": 1.0
            })
        
        return context_tags
    
    def _deduplicate_tags(self, tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate tags, keeping highest confidence."""
        seen = {}
        for tag in tags:
            name = tag["name"].lower()
            if name not in seen or tag["confidence"] > seen[name]["confidence"]:
                seen[name] = tag
        return list(seen.values())
    
    def save_tags(self, session_id: int, tags: List[Dict[str, Any]], db: Session) -> None:
        """
        Save extracted tags to database.
        
        Args:
            session_id: Session ID to tag
            tags: List of tag dicts with name, category, confidence
            db: Database session
        """
        for tag_data in tags:
            # Get or create tag
            tag = db.query(Tag).filter_by(name=tag_data["name"]).first()
            if not tag:
                tag = Tag(
                    name=tag_data["name"],
                    category=tag_data.get("category", "custom"),
                    color=TAG_COLORS.get(tag_data.get("category", "custom"), TAG_COLORS["custom"]),
                    auto_generated=True
                )
                db.add(tag)
                db.flush()
            
            # Check if already associated
            existing = db.query(SessionTag).filter_by(
                session_id=session_id,
                tag_id=tag.id
            ).first()
            
            if not existing:
                # Create association
                session_tag = SessionTag(
                    session_id=session_id,
                    tag_id=tag.id,
                    confidence=tag_data.get("confidence", 1.0),
                    auto_generated=True
                )
                db.add(session_tag)
        
        db.commit()
        logger.info(f"Saved {len(tags)} tags for session {session_id}")
    
    def assign_color(self, category: str) -> str:
        """Get color for a tag category."""
        return TAG_COLORS.get(category, TAG_COLORS["custom"])
