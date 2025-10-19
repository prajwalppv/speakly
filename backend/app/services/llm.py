"""LLM service for generating summaries and extracting TODOs."""

import asyncio
import json
import logging
import textwrap
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from datetime import datetime
import httpx
try:  # pragma: no cover - optional dependency at runtime
    from groq import Groq  # type: ignore
except ImportError:  # pragma: no cover
    Groq = None  # type: ignore[assignment]
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from ..database import SessionLocal
from ..models import Session as SessionModel, Transcription, LlmRun, Todo
from ..config import settings
from .metrics import track_performance, log_errors
from .task_sync_service import schedule_task_sync
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

# Global semaphore for rate limiting concurrent LLM requests
# This prevents overwhelming the API with too many simultaneous requests
_llm_semaphore: asyncio.Semaphore | None = None


def _get_llm_semaphore() -> asyncio.Semaphore:
    """Get or create the global LLM semaphore for rate limiting."""
    global _llm_semaphore
    if _llm_semaphore is None:
        max_concurrent = settings.llm_max_concurrent_requests
        _llm_semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"Initialized LLM semaphore with max_concurrent={max_concurrent}")
    return _llm_semaphore


SUMMARY_PROMPT = textwrap.dedent(
    """
    You are Speakly's intelligent transcription assistant. Your task is to create a comprehensive, 
    well-structured summary that captures all salient points from the audio content.
    
    The content may be:
    - Personal voice notes/memos to self
    - Multi-speaker conversations or meetings
    - Interviews (one-on-one or panel)
    - Conference presentations or lectures
    - Brainstorming sessions
    - Status updates or project reviews
    
    Your summary should:
    1. **Identify the content type and context** at the start
    2. **Capture all key information** - don't lose important details
    3. **Organize information logically** with clear sections when appropriate
    4. **Preserve speaker perspectives** in multi-speaker contexts
    5. **Highlight decisions, action items, and important dates/deadlines**
    6. **Note any questions raised or issues flagged**
    7. **Include relevant context** that makes the summary useful later
    
    Structure your summary with:
    - **Overview:** Brief context about the content type and main topic
    - **Key Points:** Main discussion items, organized by theme
    - **Decisions/Outcomes:** Any conclusions or resolutions
    - **Action Items:** Tasks mentioned (if any)
    - **Open Questions:** Unresolved items or follow-ups needed
    
    Use clear headings and bullet points for readability. Be thorough but concise.
    Avoid generic statements - be specific about what was discussed.
    
    Transcript:
    {transcript}
    """
)

TODO_PROMPT = textwrap.dedent(
    """
    You are Speakly's action item and task update extractor.
    
    From the transcript below, identify TWO types of items:
    
    1. **NEW ACTION ITEMS**: Tasks that need to be created
    2. **TASK UPDATES**: References to existing tasks with status changes
    
    Return a JSON object with two arrays:
    
    {{
      "new_tasks": [
        {{
          "title": "Concise actionable description",
          "due_hint": "Timing phrase like 'by Friday' or null",
          "confidence": 0.95,
          "source_excerpt": "Exact quote from transcript"
        }}
      ],
      "task_updates": [
        {{
          "title": "Task title or description to match",
          "status": "completed" | "in_progress" | "blocked" | "cancelled",
          "notes": "Additional context about the update",
          "confidence": 0.90,
          "source_excerpt": "Exact quote from transcript"
        }}
      ]
    }}
    
    **Task Update Examples:**
    - "I finished the report" → status: completed
    - "Still working on the database migration" → status: in_progress
    - "Can't proceed with deployment until approval" → status: blocked
    - "We decided not to do the redesign" → status: cancelled
    
    **Guidelines:**
    - Only extract clear, actionable items
    - Be specific about task titles (not "do something" but "Review Q4 budget proposal")
    - Confidence should reflect how certain you are this is a real task/update
    - If no items found, return empty arrays
    - Return ONLY valid JSON, no markdown or explanations
    
    Transcript:
    {transcript}
    """
)

TITLE_PROMPT = textwrap.dedent(
    """
    You are Speakly's title generator.
    Generate a short, memorable title (max 6 words) that captures the main topic or purpose of this conversation.
    The title should be:
    - Specific and descriptive
    - Easy to scan and identify
    - Professional but natural
    - Not a complete sentence
    
    Examples of good titles:
    - "Car repair estimates and comparison"
    - "Project timeline review meeting"
    - "Client contract negotiation discussion"
    - "Marketing budget allocation Q4"
    
    Return ONLY the title text, nothing else.
    
    Conversation:
    {transcript}
    """
)


class LlmError(RuntimeError):
    """Raised when an LLM provider cannot fulfil a request."""


class LlmTask(Enum):
    """Enumeration of supported generation tasks."""

    TITLE = "title"
    SUMMARY = "summary"
    TODO = "todo"
    TAGGING = "tagging"


class LlmProvider(ABC):
    """Abstract base class for pluggable LLM providers."""

    name: str

    def __init__(self, settings) -> None:
        self._settings = settings

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the provider has enough configuration to operate."""

    @abstractmethod
    def generate(self, prompt: str, task: LlmTask) -> str:
        """Generate content for the given task."""

    def model_for(self, task: LlmTask) -> str:
        return ""

    @property
    def base_url(self) -> str | None:  # pragma: no cover - default implementation
        return None


class GroqRateLimitError(LlmError):
    """Raised when Groq API rate limit is exceeded."""
    pass


class GroqProvider(LlmProvider):
    name = "groq"

    def __init__(self, settings) -> None:
        super().__init__(settings)
        self._api_key = (getattr(settings, "groq_api_key", "") or "").strip()
        self._model = (getattr(settings, "groq_model", "") or "gpt-4o-mini").strip() or "gpt-4o-mini"
        self._client = None
        base_url = getattr(settings, "groq_api_base_url", "https://api.groq.com") or "https://api.groq.com"
        self._base_url = base_url.rstrip("/")

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        """Lazy initialization of Groq client."""
        if self._client is None:
            if not self._api_key:
                raise LlmError("Groq API key not configured")
            if Groq is None:
                raise LlmError("Groq SDK is not installed. Install the 'groq' package to enable Groq support.")
            self._client = Groq(api_key=self._api_key)
        return self._client

    def generate(self, prompt: str, task: LlmTask) -> str:
        """Generate content with retry logic and rate limiting.
        
        This method includes:
        - Exponential backoff retry for rate limits and transient errors
        - Configurable retry attempts and wait times
        - Proper error handling and logging
        """
        if not self.is_available():
            raise LlmError("Groq provider not configured")

        api_url = f"{self._base_url}/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Use retry decorator configuration from settings
        @retry(
            retry=retry_if_exception_type((GroqRateLimitError, httpx.TimeoutException, httpx.NetworkError)),
            stop=stop_after_attempt(settings.llm_retry_max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=settings.llm_retry_min_wait_seconds,
                max=settings.llm_retry_max_wait_seconds
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _make_request() -> str:
            try:
                response = httpx.post(
                    api_url,
                    headers=headers,
                    json={
                        "model": self._model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a helpful assistant. Be concise and direct in your responses.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 1.0,
                        "max_tokens": 4000,
                    },
                    timeout=60,
                )
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                raise exc

            status = response.status_code

            if status == 429:
                logger.warning(
                    "Groq API rate limit hit. Will retry.",
                    extra={"extra_data": {"task": task.value}}
                )
                retry_after = response.headers.get("Retry-After")
                detail = (
                    f"Rate limit exceeded (Retry-After={retry_after})"
                    if retry_after
                    else "Rate limit exceeded"
                )
                raise GroqRateLimitError(detail)

            if 500 <= status < 600:
                logger.warning(
                    "Groq API server error. Will retry.",
                    extra={"extra_data": {"task": task.value}}
                )
                raise GroqRateLimitError(f"Server error {status}")

            if status == 401:
                raise LlmError("Groq API error: Unauthorized")

            if status >= 400:
                response_text = getattr(response, "text", "")
                raise LlmError(f"Groq API error {status}: {response_text[:200]}")

            try:
                data = response.json()
            except Exception as exc:  # pragma: no cover - unexpected parse error
                raise LlmError(f"Groq API response parse error: {exc}") from exc

            try:
                text = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise LlmError("Groq API response missing content") from exc

            if not text:
                raise LlmError("Empty response from Groq API")

            return self._strip_thinking_tags(text).strip()
        
        # Execute with retry logic
        try:
            return _make_request()
        except (GroqRateLimitError, httpx.TimeoutException, httpx.NetworkError) as exc:
            # All retries exhausted
            logger.error(
                f"Groq API request failed after {settings.llm_retry_max_attempts} attempts: {exc}",
                extra={"extra_data": {"task": task.value}}
            )
            raise LlmError(f"Groq API request failed after retries: {exc}") from exc

    def model_for(self, task: LlmTask) -> str:
        return self._model

    @staticmethod
    def _strip_thinking_tags(text: str) -> str:
        import re

        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL)
        return re.sub(r"</?think>", "", text)


class OllamaProvider(LlmProvider):
    name = "ollama"

    def __init__(self, settings) -> None:
        super().__init__(settings)
        base_url = (getattr(settings, "ollama_base_url", "") or "").strip()
        self._base_url = base_url.rstrip("/")
        summary_model = (getattr(settings, "ollama_model_summary", "") or "llama3").strip()
        self._summary_model = summary_model or "llama3"
        todo_model = (getattr(settings, "ollama_model_todo", "") or self._summary_model).strip()
        self._todo_model = todo_model or self._summary_model

    def is_available(self) -> bool:
        return bool(self._base_url)

    def generate(self, prompt: str, task: LlmTask) -> str:
        if not self.is_available():
            raise LlmError("Ollama provider not configured")

        model = self.model_for(task) or self._summary_model
        url = f"{self._base_url}/api/generate"
        try:
            response = httpx.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network failure path
            raise LlmError(f"Ollama error: {exc}") from exc

        data = response.json()
        text = data.get("response")
        if not text:
            raise LlmError("Missing response from Ollama")
        return text.strip()

    def model_for(self, task: LlmTask) -> str:
        if task is LlmTask.TODO:
            return self._todo_model
        return self._summary_model

    @property
    def base_url(self) -> str | None:
        return self._base_url or None


PROVIDER_REGISTRY: tuple[type[LlmProvider], ...] = (
    GroqProvider,
    OllamaProvider,
)


class LlmService:
    """High-level orchestration layer that delegates to the selected provider."""

    def __init__(self, provider_name: str | None = None) -> None:
        raw_requested = provider_name or getattr(settings, "llm_provider", "auto") or "auto"
        requested = str(raw_requested).strip().lower() or "auto"

        self.requested_provider = requested
        self._providers = [provider_cls(settings) for provider_cls in PROVIDER_REGISTRY]
        self._available_providers = [provider for provider in self._providers if provider.is_available()]
        self._provider = self._select_provider(requested)

    def _select_provider(self, requested: str) -> LlmProvider | None:
        if requested == "none":
            return None

        if requested == "auto" or not requested:
            return self._available_providers[0] if self._available_providers else None

        for provider in self._available_providers:
            if provider.name == requested:
                return provider

        if requested not in {"auto", "none"}:
            logger.warning(
                "Requested LLM provider '%s' not available; falling back to first available",
                requested,
            )
        return self._available_providers[0] if self._available_providers else None

    @property
    def provider(self) -> LlmProvider | None:
        return self._provider

    @property
    def provider_name(self) -> str:
        return self._provider.name if self._provider else "none"

    def is_enabled(self) -> bool:
        return self.provider is not None

    @property
    def base_url(self) -> str | None:
        provider = self.provider
        return provider.base_url if provider else None

    @property
    def summary_model_name(self) -> str:
        provider = self.provider
        return provider.model_for(LlmTask.SUMMARY) if provider else ""

    @property
    def model_summary(self) -> str:
        return self.summary_model_name

    @property
    def todo_model_name(self) -> str:
        provider = self.provider
        return provider.model_for(LlmTask.TODO) if provider else ""

    @property
    def model_todo(self) -> str:
        return self.todo_model_name

    def _generate(self, prompt: str, task: LlmTask) -> str:
        return self.generate_with_provider(prompt, task)

    def generate_with_provider(self, prompt: str, task: LlmTask) -> str:
        provider = self.provider
        if not provider:
            raise LlmError("LLM provider disabled")
        return provider.generate(prompt, task)

    def generate_title(self, transcript: str) -> str:
        """Generate a short, memorable title from the transcript."""
        prompt = TITLE_PROMPT.format(transcript=transcript.strip())
        try:
            title = self._generate(prompt, LlmTask.TITLE)
            # Clean up and limit length
            title = title.strip().strip('"').strip("'")
            if len(title) > 60:
                title = title[:57] + "..."
            return title
        except LlmError:
            logger.warning("Falling back to simple title generator")
            # Fallback: use first sentence
            first_sentence = transcript.split(".")[0].strip()
            if len(first_sentence) > 60:
                return first_sentence[:57] + "..."
            return first_sentence

    def generate_summary(self, transcript: str) -> str:
        prompt = SUMMARY_PROMPT.format(transcript=transcript.strip())
        try:
            return self._generate(prompt, LlmTask.SUMMARY)
        except LlmError:
            logger.warning("Falling back to built-in summariser")
            sentences = transcript.split(".")
            return "\n".join(
                f"• {sentence.strip()}" for sentence in sentences[:3] if sentence.strip()
            )

    def extract_todos(self, transcript: str) -> dict[str, Any]:
        """Extract new tasks and task updates from transcript.
        
        Returns:
            Dict with 'new_tasks' and 'task_updates' arrays
        """
        prompt = TODO_PROMPT.format(transcript=transcript.strip())
        raw = None
        try:
            raw = self._generate(prompt, LlmTask.TODO)
        except LlmError:
            logger.warning("Falling back to empty TODO response")
            return {"new_tasks": [], "task_updates": []}

        # Strip markdown code blocks if present
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines).strip()

        try:
            result = json.loads(raw)
            
            # Handle both new and legacy formats
            if isinstance(result, dict):
                return {
                    "new_tasks": result.get("new_tasks", []),
                    "task_updates": result.get("task_updates", [])
                }
            elif isinstance(result, list):
                # Legacy format - treat as new tasks only
                return {"new_tasks": result, "task_updates": []}
                
        except json.JSONDecodeError:
            logger.warning("Todo extraction returned non-JSON payload: %s", raw[:200])

        return {"new_tasks": [], "task_updates": []}


async def schedule_summary_and_todos(session_id: int, transcription_id: int) -> None:
    """Schedule LLM processing with rate limiting to prevent overwhelming the API.
    
    Uses a semaphore to limit concurrent LLM operations, preventing throttling
    when processing multiple audio files simultaneously.
    """
    semaphore = _get_llm_semaphore()
    
    async with semaphore:
        logger.info(
            f"Acquired LLM semaphore for session {session_id}",
            extra={"extra_data": {"session_id": session_id, "transcription_id": transcription_id}}
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run_summary_and_todos, session_id, transcription_id)
        logger.info(
            f"Released LLM semaphore for session {session_id}",
            extra={"extra_data": {"session_id": session_id}}
        )


def _generate_title(service: LlmService, session: SessionModel, transcript: str, db) -> bool:
    """Generate and save session title.
    
    Returns:
        True if successful, False if failed
    """
    try:
        title = service.generate_title(transcript)
        session.description = title
        db.commit()
        db.refresh(session)
        logger.info(
            f"Generated title: {title}",
            extra={"extra_data": {"session_id": session.id, "title": title}}
        )
        return True
    except Exception as exc:
        logger.warning(f"Failed to generate title: {exc}", exc_info=True)
        return False


def _generate_summary(service: LlmService, summary_run: LlmRun, transcript: str, session: SessionModel) -> bool:
    """Generate and save session summary.
    
    Returns:
        True if successful, False if failed
    """
    try:
        summary_text = service.generate_summary(transcript)
        summary_run.response = summary_text
        summary_run.status = "completed"
        session.summary_run = summary_run
        
        # Update processing stages
        if session.processing_stages:
            stages = session.processing_stages.copy()
            stages["summarizing"] = {"status": "completed", "timestamp": datetime.utcnow().isoformat()}
            session.processing_stages = stages
        return True
    except Exception as exc:  # pragma: no cover - resilience
        summary_run.status = "error"
        summary_run.error = str(exc)
        logger.exception("Failed to generate summary")
        
        # Mark stage as failed
        if session.processing_stages:
            stages = session.processing_stages.copy()
            stages["summarizing"] = {
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc)[:200]  # Truncate long errors
            }
            session.processing_stages = stages
        return False


def _extract_and_create_todos(
    service: LlmService,
    todo_run: LlmRun,
    transcript: str,
    session: SessionModel,
    db,
) -> tuple[bool, int, list[dict[str, Any]]]:
    """Extract todos and task updates from transcript.
    
    Returns:
        Tuple of (success: bool, number of new todos created, list of task updates)
    """
    extraction_result = {"new_tasks": [], "task_updates": []}
    try:
        extraction_result = service.extract_todos(transcript)
        todo_run.response = json.dumps(extraction_result)
        todo_run.status = "completed"
        
        # Update processing stages
        if session.processing_stages:
            stages = session.processing_stages.copy()
            stages["extracting_tasks"] = {"status": "completed", "timestamp": datetime.utcnow().isoformat()}
            session.processing_stages = stages
    except Exception as exc:  # pragma: no cover
        todo_run.status = "error"
        todo_run.error = str(exc)
        logger.exception("Failed to extract todos")
        
        # Mark stage as failed
        if session.processing_stages:
            stages = session.processing_stages.copy()
            stages["extracting_tasks"] = {
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc)[:200]
            }
            session.processing_stages = stages
        return False, 0, []

    confidence_threshold = settings.todo_confidence_threshold
    created = 0
    
    # Create new tasks
    for todo in extraction_result.get("new_tasks", []):
        title = str(todo.get("title", "")).strip()
        if not title:
            continue
        confidence = todo.get("confidence")
        if confidence is not None and confidence < confidence_threshold:
            continue
            
        db.add(
            Todo(
                session_id=session.id,
                llm_run_id=todo_run.id,
                title=title,
                due_hint=(todo.get("due_hint") or None),
                confidence=confidence,
                status="pending",
                source_start_ms=_safe_ms(todo.get("source_start_ms")),
                source_end_ms=_safe_ms(todo.get("source_end_ms")),
                source_excerpt=todo.get("source_excerpt"),
            )
        )
        created += 1
    
    # Return task updates for processing by task sync service
    task_updates = extraction_result.get("task_updates", [])
    
    return True, created, task_updates


def _run_summary_and_todos(session_id: int, transcription_id: int) -> None:
    """Process LLM tasks for a transcribed session.
    
    This orchestrates title generation, summary creation, and TODO extraction.
    Each task is handled by a separate function for better modularity.
    """
    service = LlmService()
    if not service.is_enabled():
        logger.info(
            "LLM provider disabled; skipping LLM jobs",
            extra={"extra_data": {"requested_provider": service.requested_provider}},
        )
        return

    with SessionLocal() as db:
        # Fetch session and transcription
        session = (
            db.query(SessionModel)
            .options(joinedload(SessionModel.user))
            .filter_by(id=session_id)
            .one_or_none()
        )
        transcription = (
            db.query(Transcription).filter_by(id=transcription_id).one_or_none()
        )
        
        if not session or not transcription or not transcription.text:
            logger.warning(
                "Skipping LLM jobs; missing session/transcription text",
                extra={"extra_data": {"session_id": session_id, "transcription_id": transcription_id}},
            )
            return

        transcript = transcription.text
        auto_approve = True
        if session.user and session.user.auto_approve_sessions is not None:
            auto_approve = bool(session.user.auto_approve_sessions)

        # Create summary run record
        summary_run = LlmRun(
            session_id=session.id,
            transcription_id=transcription.id,
            run_type="summary",
            model=service.summary_model_name,
            prompt=SUMMARY_PROMPT,
        )
        db.add(summary_run)
        db.commit()
        db.refresh(summary_run)

        # Update stage: diarizing complete, summarizing starts
        if session.processing_stages:
            stages = session.processing_stages.copy()
            stages["diarizing"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }
            stages["summarizing"] = {
                "status": "in_progress",
                "timestamp": datetime.utcnow().isoformat()
            }
            session.processing_stages = stages
            db.commit()
        
        # Track failed stages for final status
        failed_stages = []
        
        # Generate title (independent task)
        if not _generate_title(service, session, transcript, db):
            failed_stages.append("title_generation")

        # Generate summary
        if not _generate_summary(service, summary_run, transcript, session):
            failed_stages.append("summarizing")
        
        # Update stage: summarizing complete, extracting tasks starts
        if session.processing_stages:
            session.processing_stages["summarizing"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }
            session.processing_stages["extracting_tasks"] = {
                "status": "in_progress",
                "timestamp": datetime.utcnow().isoformat()
            }
            db.commit()

        # Create TODO run record
        todo_run = LlmRun(
            session_id=session.id,
            transcription_id=transcription.id,
            run_type="todos",
            model=service.todo_model_name,
            prompt=TODO_PROMPT,
        )
        db.add(todo_run)
        db.commit()
        db.refresh(todo_run)

        # Extract and create TODOs, get task updates
        todos_success, created, task_updates = _extract_and_create_todos(service, todo_run, transcript, session, db)
        if not todos_success:
            failed_stages.append("extracting_tasks")

        # Store task updates in metadata for UI display
        if task_updates:
            if not todo_run.metadata_payload:
                todo_run.metadata_payload = {}
            todo_run.metadata_payload["task_updates"] = task_updates
            db.commit()

        # Update session todo count
        session.todo_count = db.query(Todo).filter_by(session_id=session.id).count()
        
        # Update stage: extracting tasks complete, syncing tasks starts
        if session.processing_stages:
            stages = session.processing_stages.copy()
            stages["extracting_tasks"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }
            if created > 0 or task_updates:
                stages["syncing_tasks"] = {
                    "status": "pending",
                    "timestamp": None
                }
            else:
                # No tasks to sync
                stages["syncing_tasks"] = {
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            session.processing_stages = stages
        
        db.commit()
        
        logger.info(
            f"TODO extraction completed: {created} new todos, {len(task_updates)} task updates",
            extra={"extra_data": {
                "session_id": session.id,
                "new_todos": created,
                "task_updates": len(task_updates),
                "total_count": session.todo_count
            }}
        )
        
        # Extract and save tags (if feature enabled)
        if settings.feature_auto_tagging:
            try:
                logger.info(f"Extracting tags for session {session.id}")
                from .tagging import TaggingService
                tagging_service = TaggingService()
                tags = tagging_service.extract_tags(session)
                tagging_service.save_tags(session.id, tags, db)
                
                # Update processing stages
                if session.processing_stages:
                    stages = session.processing_stages.copy()
                    stages["tagging"] = {
                        "status": "completed",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    session.processing_stages = stages
                    db.commit()
                
                logger.info(f"Saved {len(tags)} tags for session {session.id}")
            except Exception as e:
                logger.error(f"Failed to extract tags for session {session.id}: {e}", exc_info=True)
                failed_stages.append("tagging")
                
                # Mark stage as failed
                if session.processing_stages:
                    stages = session.processing_stages.copy()
                    stages["tagging"] = {
                        "status": "failed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": str(e)[:200]
                    }
                    session.processing_stages = stages
                    db.commit()
        
        has_tasks_to_sync = bool(created > 0 or task_updates)

        if failed_stages:
            session.last_error = f"Partial processing failure in stages: {', '.join(failed_stages)}"
        elif session.last_error and "Partial processing failure" in session.last_error:
            # Clear stale warnings if latest run succeeded fully
            session.last_error = None

        if auto_approve:
            session.review_status = "auto_approved"
            session.reviewed_at = datetime.utcnow()

            if session.processing_stages:
                stages = session.processing_stages.copy()
                stages["review"] = {
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat()
                }
                if has_tasks_to_sync:
                    stages["syncing_tasks"] = {
                        "status": "in_progress",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    stages["syncing_tasks"] = {
                        "status": "completed",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                session.processing_stages = stages

            if has_tasks_to_sync:
                schedule_task_sync(session.id, task_updates=task_updates)
                session.status = "processing"
                logger.info(
                    f"Session {session.id} LLM processing done, task sync pending" +
                    (f" (failed stages: {', '.join(failed_stages)})" if failed_stages else ""),
                    extra={"session_id": session.id, "failed_stages": failed_stages}
                )
            else:
                # No tasks to sync, mark as completed now
                if failed_stages:
                    session.status = "completed_with_warnings"
                    logger.warning(
                        f"Session {session.id} completed with warnings: {', '.join(failed_stages)}",
                        extra={"session_id": session.id, "failed_stages": failed_stages}
                    )
                else:
                    session.status = "completed"
                    logger.info(
                        f"Session {session.id} processing completed and auto-approved",
                        extra={"session_id": session.id}
                    )
        else:
            session.status = "awaiting_review"
            session.review_status = "pending"
            session.reviewed_at = None

            if session.processing_stages:
                stages = session.processing_stages.copy()
                stages["review"] = {
                    "status": "in_progress",
                    "timestamp": datetime.utcnow().isoformat()
                }
                if has_tasks_to_sync:
                    stages["syncing_tasks"] = {
                        "status": "pending",
                        "timestamp": None
                    }
                else:
                    stages["syncing_tasks"] = {
                        "status": "completed",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                session.processing_stages = stages

            logger.info(
                f"Session {session.id} awaiting user review before finalizing",
                extra={
                    "session_id": session.id,
                    "failed_stages": failed_stages,
                    "has_tasks_to_sync": has_tasks_to_sync,
                },
            )

        db.commit()


def _safe_ms(value: Any) -> int | None:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(float(value))
        return int(float(str(value)))
    except (TypeError, ValueError):  # pragma: no cover
        return None
