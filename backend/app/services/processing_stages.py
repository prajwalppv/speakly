"""
Processing stages tracking.

Tracks the progress of a session through various processing stages.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

ProcessingStage = Literal[
    "uploaded",
    "transcribing",
    "diarizing",
    "summarizing",
    "extracting_tasks",
    "tagging",
    "review",
    "syncing_tasks",
    "completed",
    "error",
]


class ProcessingStages:
    """Helper for managing session processing stages."""

    @staticmethod
    def initialize() -> dict[str, dict]:
        """Initialize processing stages structure."""
        return {
            "uploaded": {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
            },
            "transcribing": {"status": "pending", "timestamp": None},
            "diarizing": {"status": "pending", "timestamp": None},
            "summarizing": {"status": "pending", "timestamp": None},
            "extracting_tasks": {"status": "pending", "timestamp": None},
            "tagging": {"status": "pending", "timestamp": None},
            "review": {"status": "pending", "timestamp": None},
            "syncing_tasks": {"status": "pending", "timestamp": None},
        }

    @staticmethod
    def start_stage(stages: dict, stage: ProcessingStage) -> dict:
        """Mark a stage as in progress."""
        stages[stage] = {
            "status": "in_progress",
            "timestamp": datetime.utcnow().isoformat(),
        }
        return stages

    @staticmethod
    def complete_stage(stages: dict, stage: ProcessingStage) -> dict:
        """Mark a stage as completed."""
        stages[stage] = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }
        return stages

    @staticmethod
    def error_stage(stages: dict, stage: ProcessingStage, error: str) -> dict:
        """Mark a stage as errored."""
        stages[stage] = {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": error,
        }
        return stages

    @staticmethod
    def get_current_stage(stages: dict) -> tuple[str | None, str]:
        """
        Get the current processing stage.

        Returns:
            Tuple of (stage_name, status)
        """
        stage_order = [
            "uploaded",
            "transcribing",
            "diarizing",
            "summarizing",
            "extracting_tasks",
            "tagging",
            "review",
            "syncing_tasks",
        ]

        for stage in stage_order:
            if stage in stages:
                status = stages[stage].get("status")
                if status in ["in_progress", "pending", "error"]:
                    return stage, status

        return None, "completed"

    @staticmethod
    def estimate_time_remaining(stages: dict) -> int | None:
        """
        Estimate time remaining in seconds.

        Returns:
            Estimated seconds, or None if can't estimate
        """
        # Simple estimates based on stage
        time_estimates = {
            "transcribing": 120,  # 2 minutes
            "diarizing": 30,
            "summarizing": 15,
            "extracting_tasks": 10,
            "tagging": 8,  # Auto-tagging with LLM
            "syncing_tasks": 5,
        }

        current_stage, status = ProcessingStages.get_current_stage(stages)

        if not current_stage or status == "completed":
            return 0

        # Sum remaining stages
        stage_order = [
            "transcribing",
            "diarizing",
            "summarizing",
            "extracting_tasks",
            "tagging",
            "review",
            "syncing_tasks",
        ]

        total = 0
        found_current = False
        for stage in stage_order:
            if stage == current_stage:
                found_current = True
            if found_current:
                total += time_estimates.get(stage, 10)

        return total
