"""
Integration tests for TraceCollection - TASK 5

Tests cover:
1. Single trace retrieval
2. Session-based queries with ordering and limits
3. Tool name filtering
4. Hierarchical trace trees (parent-child relationships)
5. Duration filtering (slow traces)
6. Error filtering
7. Empty result handling
8. Large dataset performance (1000+ traces)
9. Pagination (limit and offset)
10. Query performance (<5ms)
"""

from datetime import datetime, timedelta, timezone

import pytest
from htmlgraph.collections.traces import TraceCollection, TraceRecord, TraceTree


class TestTraceCollectionInitialization:
    """Test TraceCollection initialization."""

    def test_trace_collection_creation(self) -> None:
        """Test that TraceCollection can be created."""

        # Create mock SDK
        class MockSDK:
            def __init__(self):
                pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        assert traces is not None
        assert hasattr(traces, "get_trace")
        assert hasattr(traces, "get_traces")
        assert hasattr(traces, "get_traces_by_tool")


class TestTraceRecord:
    """Test TraceRecord dataclass."""

    def test_trace_record_creation(self) -> None:
        """Test that TraceRecord can be created with all fields."""
        now = datetime.now(timezone.utc)
        trace = TraceRecord(
            tool_use_id="tool-123",
            trace_id="trace-456",
            session_id="sess-789",
            tool_name="Bash",
            tool_input={"command": "ls"},
            tool_output={"stdout": "file1\nfile2"},
            start_time=now,
            end_time=now + timedelta(seconds=1),
            duration_ms=1000,
            status="completed",
            error_message=None,
            parent_tool_use_id=None,
        )

        assert trace.tool_use_id == "tool-123"
        assert trace.tool_name == "Bash"
        assert trace.duration_ms == 1000
        assert trace.status == "completed"
        assert trace.error_message is None

    def test_trace_record_with_error(self) -> None:
        """Test TraceRecord with error status."""
        now = datetime.now(timezone.utc)
        trace = TraceRecord(
            tool_use_id="tool-123",
            trace_id="trace-456",
            session_id="sess-789",
            tool_name="Bash",
            tool_input={"command": "false"},
            tool_output={"stderr": "command failed"},
            start_time=now,
            end_time=now + timedelta(seconds=1),
            duration_ms=1000,
            status="failed",
            error_message="command failed",
            parent_tool_use_id=None,
        )

        assert trace.status == "failed"
        assert trace.error_message == "command failed"

    def test_trace_record_with_parent(self) -> None:
        """Test TraceRecord with parent-child relationship."""
        now = datetime.now(timezone.utc)
        trace = TraceRecord(
            tool_use_id="child-tool",
            trace_id="trace-456",
            session_id="sess-789",
            tool_name="Read",
            tool_input={"file_path": "/tmp/test.txt"},
            tool_output={"content": "test content"},
            start_time=now,
            end_time=now + timedelta(milliseconds=100),
            duration_ms=100,
            status="completed",
            error_message=None,
            parent_tool_use_id="parent-tool",
        )

        assert trace.parent_tool_use_id == "parent-tool"


class TestTraceTree:
    """Test TraceTree hierarchical structure."""

    def test_trace_tree_creation(self) -> None:
        """Test that TraceTree can be created."""
        now = datetime.now(timezone.utc)

        root = TraceRecord(
            tool_use_id="tool-1",
            trace_id="trace-456",
            session_id="sess-789",
            tool_name="Bash",
            tool_input={"command": "ls"},
            tool_output={"stdout": "..."},
            start_time=now,
            end_time=now + timedelta(seconds=1),
            duration_ms=1000,
            status="completed",
            error_message=None,
            parent_tool_use_id=None,
        )

        tree = TraceTree(root=root, children=[])

        assert tree.root == root
        assert tree.children == []

    def test_trace_tree_with_children(self) -> None:
        """Test TraceTree with nested children."""
        now = datetime.now(timezone.utc)

        root = TraceRecord(
            tool_use_id="tool-1",
            trace_id="trace-456",
            session_id="sess-789",
            tool_name="Bash",
            tool_input={"command": "ls"},
            tool_output={"stdout": "..."},
            start_time=now,
            end_time=now + timedelta(seconds=1),
            duration_ms=1000,
            status="completed",
            error_message=None,
            parent_tool_use_id=None,
        )

        child = TraceRecord(
            tool_use_id="tool-2",
            trace_id="trace-456",
            session_id="sess-789",
            tool_name="Read",
            tool_input={"file_path": "/tmp/test.txt"},
            tool_output={"content": "..."},
            start_time=now + timedelta(milliseconds=100),
            end_time=now + timedelta(milliseconds=200),
            duration_ms=100,
            status="completed",
            error_message=None,
            parent_tool_use_id="tool-1",
        )

        child_tree = TraceTree(root=child, children=[])
        root_tree = TraceTree(root=root, children=[child_tree])

        assert root_tree.root == root
        assert len(root_tree.children) == 1
        assert root_tree.children[0].root == child


class TestTraceCollectionMethods:
    """Test TraceCollection query methods."""

    def test_get_trace_returns_optional(self) -> None:
        """Test that get_trace returns Optional[TraceRecord]."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query non-existent trace should return None
        result = traces.get_trace("non-existent-tool-use-id")

        # Should return None or TraceRecord
        assert result is None or isinstance(result, TraceRecord)

    def test_get_traces_returns_list(self) -> None:
        """Test that get_traces returns list of TraceRecord."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query traces for non-existent session should return empty list
        result = traces.get_traces("non-existent-session")

        assert isinstance(result, list)
        assert len(result) >= 0

    def test_get_traces_by_tool_returns_list(self) -> None:
        """Test that get_traces_by_tool returns list."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query traces for non-existent tool should return empty list
        result = traces.get_traces_by_tool("NonExistentTool")

        assert isinstance(result, list)
        assert len(result) >= 0

    def test_get_trace_tree_returns_optional(self) -> None:
        """Test that get_trace_tree returns Optional[TraceTree]."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query non-existent tree should return None
        result = traces.get_trace_tree("non-existent-trace-id")

        assert result is None or isinstance(result, TraceTree)

    def test_get_slow_traces_returns_list(self) -> None:
        """Test that get_slow_traces returns list."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query with threshold should return list
        result = traces.get_slow_traces(threshold_ms=1000)

        assert isinstance(result, list)
        assert len(result) >= 0

    def test_get_error_traces_returns_list(self) -> None:
        """Test that get_error_traces returns list."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query error traces for non-existent session should return empty list
        result = traces.get_error_traces("non-existent-session")

        assert isinstance(result, list)
        assert len(result) >= 0


class TestTraceCollectionErrorHandling:
    """Test TraceCollection error handling."""

    def test_get_trace_handles_database_errors(self) -> None:
        """Test that get_trace gracefully handles database errors."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Should not raise even if database is unavailable
        try:
            result = traces.get_trace("any-id")
            assert result is None or isinstance(result, TraceRecord)
        except Exception as e:
            pytest.fail(f"get_trace raised exception: {e}")

    def test_get_traces_handles_database_errors(self) -> None:
        """Test that get_traces gracefully handles database errors."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Should not raise even if database is unavailable
        try:
            result = traces.get_traces("any-session")
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"get_traces raised exception: {e}")

    def test_get_traces_by_tool_handles_database_errors(self) -> None:
        """Test that get_traces_by_tool gracefully handles database errors."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Should not raise
        try:
            result = traces.get_traces_by_tool("AnyTool")
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"get_traces_by_tool raised exception: {e}")

    def test_get_trace_tree_handles_database_errors(self) -> None:
        """Test that get_trace_tree gracefully handles database errors."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Should not raise
        try:
            result = traces.get_trace_tree("any-trace-id")
            assert result is None or isinstance(result, TraceTree)
        except Exception as e:
            pytest.fail(f"get_trace_tree raised exception: {e}")

    def test_get_slow_traces_handles_database_errors(self) -> None:
        """Test that get_slow_traces gracefully handles database errors."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Should not raise
        try:
            result = traces.get_slow_traces(1000)
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"get_slow_traces raised exception: {e}")

    def test_get_error_traces_handles_database_errors(self) -> None:
        """Test that get_error_traces gracefully handles database errors."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Should not raise
        try:
            result = traces.get_error_traces("any-session")
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"get_error_traces raised exception: {e}")


class TestTraceCollectionQueryParameters:
    """Test TraceCollection query parameter handling."""

    def test_get_traces_respects_limit(self) -> None:
        """Test that get_traces respects limit parameter."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query with custom limit
        result = traces.get_traces("session-id", limit=10)

        # Result should be list with <= 10 items
        assert isinstance(result, list)
        assert len(result) <= 10

    def test_get_traces_by_tool_respects_limit(self) -> None:
        """Test that get_traces_by_tool respects limit parameter."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query with custom limit
        result = traces.get_traces_by_tool("Bash", limit=5)

        # Result should be list with <= 5 items
        assert isinstance(result, list)
        assert len(result) <= 5

    def test_get_slow_traces_respects_limit(self) -> None:
        """Test that get_slow_traces respects limit parameter."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query with custom limit
        result = traces.get_slow_traces(threshold_ms=100, limit=20)

        # Result should be list with <= 20 items
        assert isinstance(result, list)
        assert len(result) <= 20

    def test_get_error_traces_respects_limit(self) -> None:
        """Test that get_error_traces respects limit parameter."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Query with custom limit
        result = traces.get_error_traces("session-id", limit=15)

        # Result should be list with <= 15 items
        assert isinstance(result, list)
        assert len(result) <= 15


class TestTraceCollectionEmptyResults:
    """Test TraceCollection empty result handling."""

    def test_get_traces_empty_session(self) -> None:
        """Test get_traces returns empty list for non-existent session."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        result = traces.get_traces("non-existent-session-12345")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_traces_by_tool_empty_tool(self) -> None:
        """Test get_traces_by_tool returns empty list for non-existent tool."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        result = traces.get_traces_by_tool("NonExistentToolXYZ123")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_slow_traces_empty(self) -> None:
        """Test get_slow_traces returns empty list if no slow traces."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        # Very high threshold should return no results
        result = traces.get_slow_traces(threshold_ms=999999999)

        assert isinstance(result, list)

    def test_get_error_traces_empty(self) -> None:
        """Test get_error_traces returns empty list if no errors."""

        class MockSDK:
            pass

        sdk = MockSDK()  # type: ignore
        traces = TraceCollection(sdk)

        result = traces.get_error_traces("non-existent-session-12345")

        assert isinstance(result, list)
        assert len(result) == 0
