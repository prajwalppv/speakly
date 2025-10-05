"""
Test processing stages tracking.
"""
import pytest
from datetime import datetime


class TestProcessingStagesInitialize:
    """Test stage initialization."""

    def test_initialize_creates_all_stages(self):
        """Test that initialize creates all required stages."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        
        assert "uploaded" in stages
        assert "transcribing" in stages
        assert "diarizing" in stages
        assert "summarizing" in stages
        assert "extracting_tasks" in stages
        assert "tagging" in stages
        assert "syncing_tasks" in stages

    def test_initialize_uploaded_completed(self):
        """Test that uploaded stage starts as completed."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        
        assert stages["uploaded"]["status"] == "completed"
        assert stages["uploaded"]["timestamp"] is not None

    def test_initialize_other_stages_pending(self):
        """Test that other stages start as pending."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        
        assert stages["transcribing"]["status"] == "pending"
        assert stages["diarizing"]["status"] == "pending"
        assert stages["summarizing"]["status"] == "pending"

    def test_initialize_returns_dict(self):
        """Test that initialize returns a dictionary."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        
        assert isinstance(stages, dict)


class TestProcessingStagesStart:
    """Test starting stages."""

    def test_start_stage_changes_status(self):
        """Test that start_stage changes status to in_progress."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.start_stage(stages, "transcribing")
        
        assert stages["transcribing"]["status"] == "in_progress"

    def test_start_stage_adds_timestamp(self):
        """Test that start_stage adds timestamp."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.start_stage(stages, "transcribing")
        
        assert stages["transcribing"]["timestamp"] is not None
        assert isinstance(stages["transcribing"]["timestamp"], str)

    def test_start_stage_multiple_stages(self):
        """Test starting multiple stages."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.start_stage(stages, "transcribing")
        stages = ProcessingStages.start_stage(stages, "diarizing")
        
        assert stages["transcribing"]["status"] == "in_progress"
        assert stages["diarizing"]["status"] == "in_progress"


class TestProcessingStagesComplete:
    """Test completing stages."""

    def test_complete_stage_changes_status(self):
        """Test that complete_stage changes status to completed."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.start_stage(stages, "transcribing")
        stages = ProcessingStages.complete_stage(stages, "transcribing")
        
        assert stages["transcribing"]["status"] == "completed"

    def test_complete_stage_updates_timestamp(self):
        """Test that complete_stage updates timestamp."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.complete_stage(stages, "summarizing")
        
        assert stages["summarizing"]["timestamp"] is not None

    def test_complete_stage_workflow(self):
        """Test complete workflow: initialize → start → complete."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.start_stage(stages, "transcribing")
        stages = ProcessingStages.complete_stage(stages, "transcribing")
        
        assert stages["transcribing"]["status"] == "completed"


class TestProcessingStagesError:
    """Test error handling for stages."""

    def test_error_stage_sets_error_status(self):
        """Test that error_stage sets status to error."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.error_stage(stages, "transcribing", "Test error")
        
        assert stages["transcribing"]["status"] == "error"

    def test_error_stage_stores_error_message(self):
        """Test that error_stage stores error message."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.error_stage(stages, "transcribing", "Connection failed")
        
        assert stages["transcribing"]["error"] == "Connection failed"

    def test_error_stage_adds_timestamp(self):
        """Test that error_stage adds timestamp."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.error_stage(stages, "summarizing", "LLM error")
        
        assert stages["summarizing"]["timestamp"] is not None

    def test_error_stage_with_long_message(self):
        """Test error stage with long error message."""
        from app.services.processing_stages import ProcessingStages
        
        long_error = "A" * 500
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.error_stage(stages, "tagging", long_error)
        
        assert stages["tagging"]["error"] == long_error


class TestProcessingStagesGetCurrent:
    """Test getting current stage."""

    def test_get_current_stage_initial(self):
        """Test get_current_stage returns first pending stage."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        current, status = ProcessingStages.get_current_stage(stages)
        
        assert current == "transcribing"
        assert status == "pending"

    def test_get_current_stage_after_completion(self):
        """Test get_current_stage after completing a stage."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.complete_stage(stages, "transcribing")
        
        current, status = ProcessingStages.get_current_stage(stages)
        
        assert current == "diarizing"

    def test_get_current_stage_in_progress(self):
        """Test get_current_stage with stage in progress."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        # Complete earlier stages first
        stages = ProcessingStages.complete_stage(stages, "transcribing")
        stages = ProcessingStages.complete_stage(stages, "diarizing")
        stages = ProcessingStages.start_stage(stages, "summarizing")
        
        current, status = ProcessingStages.get_current_stage(stages)
        
        assert current == "summarizing"
        assert status == "in_progress"

    def test_get_current_stage_with_error(self):
        """Test get_current_stage with error status."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.complete_stage(stages, "transcribing")
        stages = ProcessingStages.error_stage(stages, "diarizing", "Failed")
        
        current, status = ProcessingStages.get_current_stage(stages)
        
        assert current == "diarizing"
        assert status == "error"


class TestProcessingStagesWorkflow:
    """Test complete processing workflows."""

    def test_happy_path_workflow(self):
        """Test complete happy path through all stages."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        
        # Process through all stages
        for stage in ["transcribing", "diarizing", "summarizing", "extracting_tasks", "tagging"]:
            stages = ProcessingStages.start_stage(stages, stage)
            assert stages[stage]["status"] == "in_progress"
            
            stages = ProcessingStages.complete_stage(stages, stage)
            assert stages[stage]["status"] == "completed"

    def test_error_recovery_workflow(self):
        """Test workflow with error and recovery."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        
        # Start transcribing
        stages = ProcessingStages.start_stage(stages, "transcribing")
        
        # Error occurs
        stages = ProcessingStages.error_stage(stages, "transcribing", "Timeout")
        assert stages["transcribing"]["status"] == "error"
        
        # Retry and complete
        stages = ProcessingStages.start_stage(stages, "transcribing")
        stages = ProcessingStages.complete_stage(stages, "transcribing")
        assert stages["transcribing"]["status"] == "completed"

    def test_partial_completion(self):
        """Test partial completion of stages."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        
        # Complete first two stages
        stages = ProcessingStages.complete_stage(stages, "transcribing")
        stages = ProcessingStages.complete_stage(stages, "diarizing")
        
        # Current should be next stage
        current, _ = ProcessingStages.get_current_stage(stages)
        assert current == "summarizing"


class TestProcessingStagesEdgeCases:
    """Test edge cases and error conditions."""

    def test_stages_immutability(self):
        """Test that operations return new dict (or modify in place correctly)."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        original_status = stages["transcribing"]["status"]
        
        ProcessingStages.start_stage(stages, "transcribing")
        
        # Should be modified
        assert stages["transcribing"]["status"] != original_status

    def test_timestamp_format(self):
        """Test that timestamps are in ISO format."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        timestamp = stages["uploaded"]["timestamp"]
        
        # Should be ISO format string
        assert isinstance(timestamp, str)
        assert "T" in timestamp

    def test_multiple_errors_same_stage(self):
        """Test multiple errors on same stage."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        
        stages = ProcessingStages.error_stage(stages, "tagging", "Error 1")
        assert stages["tagging"]["error"] == "Error 1"
        
        stages = ProcessingStages.error_stage(stages, "tagging", "Error 2")
        assert stages["tagging"]["error"] == "Error 2"


class TestProcessingStagesTimeEstimation:
    """Test time estimation functionality."""

    def test_estimate_time_remaining_all_pending(self):
        """Test time estimation when all stages are pending."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        estimate = ProcessingStages.estimate_time_remaining(stages)
        
        # Should return sum of all stages
        assert estimate is not None
        assert estimate > 0

    def test_estimate_time_remaining_some_complete(self):
        """Test time estimation with some stages complete."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.complete_stage(stages, "transcribing")
        stages = ProcessingStages.complete_stage(stages, "diarizing")
        
        estimate = ProcessingStages.estimate_time_remaining(stages)
        
        # Should be less than full time
        assert estimate is not None
        assert estimate > 0

    def test_estimate_time_remaining_all_complete(self):
        """Test time estimation when all complete."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        for stage in ["transcribing", "diarizing", "summarizing", "extracting_tasks", "tagging", "syncing_tasks"]:
            stages = ProcessingStages.complete_stage(stages, stage)
        
        estimate = ProcessingStages.estimate_time_remaining(stages)
        
        assert estimate == 0

    def test_estimate_time_remaining_returns_int(self):
        """Test that estimate returns integer seconds."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        estimate = ProcessingStages.estimate_time_remaining(stages)
        
        assert isinstance(estimate, int)

    def test_estimate_time_remaining_with_error(self):
        """Test time estimation with error state."""
        from app.services.processing_stages import ProcessingStages
        
        stages = ProcessingStages.initialize()
        stages = ProcessingStages.complete_stage(stages, "transcribing")
        stages = ProcessingStages.error_stage(stages, "diarizing", "Error")
        
        estimate = ProcessingStages.estimate_time_remaining(stages)
        
        # Should still provide estimate
        assert estimate is not None
