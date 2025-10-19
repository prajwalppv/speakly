"""Performance metrics and monitoring utilities."""

import functools
import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# Type variable for decorator generic typing
F = TypeVar("F", bound=Callable[..., Any])


class MetricsCollector:
    """Collects performance metrics for processing stages."""

    def __init__(self):
        self.metrics: dict[str, dict[str, Any]] = {}

    @contextmanager
    def track_stage(self, stage_name: str, session_id: int):
        """Context manager to track execution time of a processing stage.

        Usage:
            with metrics.track_stage("summarizing", session_id):
                # do work
        """
        start_time = time.time()
        error: str | None = None

        try:
            yield
        except Exception as e:
            error = str(e)
            raise
        finally:
            duration = time.time() - start_time

            # Log metrics
            logger.info(
                f"Stage {stage_name} completed",
                extra={
                    "stage": stage_name,
                    "session_id": session_id,
                    "duration_seconds": round(duration, 2),
                    "success": error is None,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            # Store in instance for aggregation
            if session_id not in self.metrics:
                self.metrics[session_id] = {}

            self.metrics[session_id][stage_name] = {
                "duration": duration,
                "success": error is None,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_session_metrics(self, session_id: int) -> dict[str, Any]:
        """Get all metrics for a session."""
        return self.metrics.get(session_id, {})

    def clear_session_metrics(self, session_id: int):
        """Clear metrics for a session (after successful completion)."""
        self.metrics.pop(session_id, None)


# Global metrics collector instance
metrics_collector = MetricsCollector()


# ============================================================================
# LOGGING DECORATORS
# ============================================================================


def log_execution(func: F) -> F:
    """Decorator to log function execution with timing and error handling.

    Usage:
        @log_execution
        def my_function(arg1, arg2):
            # do work
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        start_time = time.time()

        logger.debug(
            f"Executing {func_name}",
            extra={
                "function": func_name,
                "args_count": len(args),
                "kwargs_count": len(kwargs),
            },
        )

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            logger.debug(
                f"Completed {func_name}",
                extra={
                    "function": func_name,
                    "duration_seconds": round(duration, 3),
                    "success": True,
                },
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                f"Failed {func_name}: {str(e)}",
                extra={
                    "function": func_name,
                    "duration_seconds": round(duration, 3),
                    "success": False,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    return wrapper  # type: ignore


def log_api_call(endpoint: str) -> Callable[[F], F]:
    """Decorator to log API endpoint calls with request/response info.

    Usage:
        @log_api_call("POST /api/audio")
        async def upload_audio(...):
            # handle request
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()

            logger.info(
                f"API request received: {endpoint}",
                extra={"endpoint": endpoint, "function": func.__name__},
            )

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    f"API request completed: {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "duration_seconds": round(duration, 3),
                        "success": True,
                    },
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    f"API request failed: {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "duration_seconds": round(duration, 3),
                        "success": False,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()

            logger.info(
                f"API request received: {endpoint}",
                extra={"endpoint": endpoint, "function": func.__name__},
            )

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    f"API request completed: {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "duration_seconds": round(duration, 3),
                        "success": True,
                    },
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    f"API request failed: {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "duration_seconds": round(duration, 3),
                        "success": False,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        # Return appropriate wrapper based on whether function is async
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def track_performance(
    stage_name: str, session_id_param: str = "session_id"
) -> Callable[[F], F]:
    """Decorator to track performance metrics for a processing stage.

    Usage:
        @track_performance("summarizing", session_id_param="session_id")
        def generate_summary(session_id: int, ...):
            # do work
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract session_id from function arguments
            import inspect

            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            session_id = bound_args.arguments.get(session_id_param)

            if session_id is None:
                # If session_id not found, execute without tracking
                logger.warning(
                    f"Could not extract session_id from {func.__name__} for performance tracking"
                )
                return func(*args, **kwargs)

            # Track with metrics collector
            with metrics_collector.track_stage(stage_name, session_id):
                return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def log_errors(context: str = "") -> Callable[[F], F]:
    """Decorator to automatically log errors with context.

    Usage:
        @log_errors(context="Failed to process audio upload")
        def process_audio(file_path: str):
            # do work that might fail
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = context or f"Error in {func.__name__}"

                logger.error(
                    f"{error_context}: {str(e)}",
                    extra={
                        "function": func.__name__,
                        "context": error_context,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        return wrapper  # type: ignore

    return decorator
