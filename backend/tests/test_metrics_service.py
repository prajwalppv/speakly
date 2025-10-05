"""
Comprehensive test suite for metrics service.
Testing all 87 uncovered lines for maximum coverage.
"""
import pytest
import time
from unittest.mock import Mock, patch


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_init_creates_empty_metrics(self):
        """Test MetricsCollector initialization."""
        from app.services.metrics import MetricsCollector
        
        collector = MetricsCollector()
        assert collector.metrics == {}

    def test_track_stage_success(self):
        """Test track_stage context manager with successful execution."""
        from app.services.metrics import MetricsCollector
        
        collector = MetricsCollector()
        
        with collector.track_stage("test_stage", session_id=1):
            time.sleep(0.01)  # Simulate work
        
        metrics = collector.get_session_metrics(1)
        assert "test_stage" in metrics
        assert metrics["test_stage"]["success"] is True
        assert metrics["test_stage"]["error"] is None
        assert metrics["test_stage"]["duration"] > 0

    def test_track_stage_with_error(self):
        """Test track_stage captures errors."""
        from app.services.metrics import MetricsCollector
        
        collector = MetricsCollector()
        
        with pytest.raises(ValueError):
            with collector.track_stage("failing_stage", session_id=2):
                raise ValueError("Test error")
        
        metrics = collector.get_session_metrics(2)
        assert "failing_stage" in metrics
        assert metrics["failing_stage"]["success"] is False
        assert "Test error" in metrics["failing_stage"]["error"]

    def test_get_session_metrics_empty(self):
        """Test getting metrics for non-existent session."""
        from app.services.metrics import MetricsCollector
        
        collector = MetricsCollector()
        metrics = collector.get_session_metrics(999)
        
        assert metrics == {}

    def test_clear_session_metrics(self):
        """Test clearing session metrics."""
        from app.services.metrics import MetricsCollector
        
        collector = MetricsCollector()
        
        with collector.track_stage("stage1", session_id=1):
            pass
        
        assert 1 in collector.metrics
        collector.clear_session_metrics(1)
        assert 1 not in collector.metrics

    def test_clear_session_metrics_non_existent(self):
        """Test clearing non-existent session doesn't error."""
        from app.services.metrics import MetricsCollector
        
        collector = MetricsCollector()
        collector.clear_session_metrics(999)  # Should not raise


class TestLogExecutionDecorator:
    """Test log_execution decorator."""

    def test_log_execution_success(self):
        """Test decorator logs successful execution."""
        from app.services.metrics import log_execution
        
        @log_execution
        def test_function(a, b):
            return a + b
        
        result = test_function(2, 3)
        assert result == 5

    def test_log_execution_with_kwargs(self):
        """Test decorator with keyword arguments."""
        from app.services.metrics import log_execution
        
        @log_execution
        def test_function(a, b=10):
            return a * b
        
        result = test_function(5, b=3)
        assert result == 15

    def test_log_execution_with_exception(self):
        """Test decorator logs exceptions and re-raises."""
        from app.services.metrics import log_execution
        
        @log_execution
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_log_execution_preserves_function_name(self):
        """Test decorator preserves original function metadata."""
        from app.services.metrics import log_execution
        
        @log_execution
        def my_function():
            """My docstring"""
            pass
        
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring"


class TestLogApiCallDecorator:
    """Test log_api_call decorator."""

    @pytest.mark.asyncio
    async def test_log_api_call_async_success(self):
        """Test decorator with async function success."""
        from app.services.metrics import log_api_call
        
        @log_api_call("POST /api/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        result = await test_endpoint()
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_log_api_call_async_with_error(self):
        """Test decorator with async function error."""
        from app.services.metrics import log_api_call
        
        @log_api_call("POST /api/test")
        async def failing_endpoint():
            raise ValueError("API error")
        
        with pytest.raises(ValueError, match="API error"):
            await failing_endpoint()

    def test_log_api_call_sync_success(self):
        """Test decorator with sync function success."""
        from app.services.metrics import log_api_call
        
        @log_api_call("GET /api/test")
        def test_endpoint():
            return {"data": "test"}
        
        result = test_endpoint()
        assert result["data"] == "test"

    def test_log_api_call_sync_with_error(self):
        """Test decorator with sync function error."""
        from app.services.metrics import log_api_call
        
        @log_api_call("GET /api/test")
        def failing_endpoint():
            raise RuntimeError("Sync API error")
        
        with pytest.raises(RuntimeError, match="Sync API error"):
            failing_endpoint()

    @pytest.mark.asyncio
    async def test_log_api_call_async_with_args(self):
        """Test async decorator with arguments."""
        from app.services.metrics import log_api_call
        
        @log_api_call("POST /api/data")
        async def endpoint_with_args(data: dict):
            return data
        
        result = await endpoint_with_args({"key": "value"})
        assert result["key"] == "value"

    def test_log_api_call_preserves_metadata(self):
        """Test decorator preserves function metadata."""
        from app.services.metrics import log_api_call
        
        @log_api_call("GET /test")
        def my_endpoint():
            """Endpoint docstring"""
            pass
        
        assert my_endpoint.__name__ == "my_endpoint"
        assert my_endpoint.__doc__ == "Endpoint docstring"


class TestTrackPerformanceDecorator:
    """Test track_performance decorator."""

    def test_track_performance_success(self):
        """Test decorator tracks performance successfully."""
        from app.services.metrics import track_performance, metrics_collector
        
        @track_performance("test_stage")
        def process_session(session_id: int):
            time.sleep(0.01)
            return session_id * 2
        
        # Clear any existing metrics
        metrics_collector.metrics.clear()
        
        result = process_session(session_id=5)
        
        assert result == 10
        metrics = metrics_collector.get_session_metrics(5)
        assert "test_stage" in metrics

    def test_track_performance_with_custom_param(self):
        """Test decorator with custom session_id parameter name."""
        from app.services.metrics import track_performance, metrics_collector
        
        @track_performance("custom_stage", session_id_param="sid")
        def process_data(sid: int, data: str):
            return f"{sid}:{data}"
        
        metrics_collector.metrics.clear()
        
        result = process_data(sid=10, data="test")
        
        assert result == "10:test"
        metrics = metrics_collector.get_session_metrics(10)
        assert "custom_stage" in metrics

    def test_track_performance_missing_session_id(self):
        """Test decorator handles missing session_id gracefully."""
        from app.services.metrics import track_performance
        
        @track_performance("stage", session_id_param="session_id")
        def no_session_function(data: str):
            return data.upper()
        
        # Should execute without tracking
        result = no_session_function("test")
        assert result == "TEST"

    def test_track_performance_with_exception(self):
        """Test decorator tracks failures."""
        from app.services.metrics import track_performance, metrics_collector
        
        @track_performance("failing_stage")
        def failing_process(session_id: int):
            raise ValueError("Processing failed")
        
        metrics_collector.metrics.clear()
        
        with pytest.raises(ValueError):
            failing_process(session_id=20)
        
        metrics = metrics_collector.get_session_metrics(20)
        assert "failing_stage" in metrics
        assert metrics["failing_stage"]["success"] is False


class TestLogErrorsDecorator:
    """Test log_errors decorator."""

    def test_log_errors_success(self):
        """Test decorator with successful execution."""
        from app.services.metrics import log_errors
        
        @log_errors(context="Test context")
        def successful_function(x):
            return x * 2
        
        result = successful_function(5)
        assert result == 10

    def test_log_errors_with_exception(self):
        """Test decorator logs and re-raises exceptions."""
        from app.services.metrics import log_errors
        
        @log_errors(context="Failed to process")
        def failing_function():
            raise RuntimeError("Something went wrong")
        
        with pytest.raises(RuntimeError, match="Something went wrong"):
            failing_function()

    def test_log_errors_without_context(self):
        """Test decorator with no context provided."""
        from app.services.metrics import log_errors
        
        @log_errors()
        def function_with_error():
            raise ValueError("Error")
        
        with pytest.raises(ValueError):
            function_with_error()

    def test_log_errors_preserves_metadata(self):
        """Test decorator preserves function metadata."""
        from app.services.metrics import log_errors
        
        @log_errors(context="Test")
        def my_function():
            """Function docstring"""
            pass
        
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "Function docstring"

    def test_log_errors_with_multiple_args(self):
        """Test decorator with function that has multiple arguments."""
        from app.services.metrics import log_errors
        
        @log_errors(context="Multi-arg function")
        def multi_arg_function(a, b, c=10):
            if a < 0:
                raise ValueError("Negative value")
            return a + b + c
        
        # Test success
        result = multi_arg_function(1, 2, c=3)
        assert result == 6
        
        # Test failure
        with pytest.raises(ValueError):
            multi_arg_function(-1, 2)


class TestGlobalMetricsCollector:
    """Test global metrics_collector instance."""

    def test_global_collector_exists(self):
        """Test global metrics collector is available."""
        from app.services.metrics import metrics_collector
        
        assert metrics_collector is not None
        assert hasattr(metrics_collector, 'metrics')

    def test_global_collector_shared_state(self):
        """Test global collector maintains state across imports."""
        from app.services.metrics import metrics_collector
        
        # Store some data
        metrics_collector.metrics[999] = {"test": "data"}
        
        # Re-import and check it's the same instance
        from app.services.metrics import metrics_collector as collector2
        assert collector2.metrics[999] == {"test": "data"}
        
        # Cleanup
        metrics_collector.clear_session_metrics(999)


class TestDecoratorIntegration:
    """Test decorator combinations and real-world usage."""

    def test_multiple_decorators_stacked(self):
        """Test stacking multiple decorators."""
        from app.services.metrics import log_execution, log_errors
        
        @log_errors(context="Stacked test")
        @log_execution
        def stacked_function(x, y):
            return x + y
        
        result = stacked_function(10, 20)
        assert result == 30

    @pytest.mark.asyncio
    async def test_async_with_multiple_decorators(self):
        """Test async function with multiple decorators."""
        from app.services.metrics import log_api_call, log_errors
        
        @log_errors(context="Async test")
        @log_api_call("POST /test")
        async def async_endpoint(data):
            return {"result": data}
        
        result = await async_endpoint("test_data")
        assert result["result"] == "test_data"

    def test_track_performance_with_log_errors(self):
        """Test track_performance combined with log_errors."""
        from app.services.metrics import track_performance, log_errors, metrics_collector
        
        @log_errors(context="Combined test")
        @track_performance("combined_stage")
        def combined_function(session_id: int, value: int):
            return session_id + value
        
        metrics_collector.metrics.clear()
        
        result = combined_function(session_id=100, value=50)
        assert result == 150
        
        metrics = metrics_collector.get_session_metrics(100)
        assert "combined_stage" in metrics
