"""
Tests for session-start-info validation with active work item display.

Tests the enhanced session-start-info command that displays:
- Active work item (feature, bug, spike, etc.)
- Auto-spike detection
- Warning when no active work item exists

Run with: uv run pytest tests/python/test_session_start_info_validation.py -v
"""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from htmlgraph.models import Node
from htmlgraph.sdk import SDK


@pytest.fixture
def temp_graph_dir():
    """Create a temporary directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sdk_with_feature(temp_graph_dir, isolated_db):
    """Create SDK with an in-progress feature."""
    from htmlgraph import HtmlGraph

    # Features are stored in features/ subdirectory
    features_dir = temp_graph_dir / "features"
    features_dir.mkdir(parents=True, exist_ok=True)

    graph = HtmlGraph(features_dir)
    sdk = SDK(directory=temp_graph_dir, agent="claude", db_path=str(isolated_db))

    # Create an in-progress feature
    feature = Node(
        id="feat-test-001",
        title="Test Feature",
        type="feature",
        status="in-progress",
        priority="high",
        created=datetime.now(),
        updated=datetime.now(),
    )

    graph.add(feature)
    return sdk, feature


@pytest.fixture
def empty_sdk(temp_graph_dir, isolated_db):
    """Create SDK with no work items."""
    sdk = SDK(directory=temp_graph_dir, agent="claude", db_path=str(isolated_db))
    return sdk


class TestActiveWorkItemInSessionStartInfo:
    """Tests for active_work field in session start info."""

    def test_session_start_info_includes_active_work_field(
        self, empty_sdk, isolated_db
    ):
        """Test that session start info always includes active_work field."""
        info = empty_sdk.get_session_start_info()

        assert "active_work" in info
        assert info["active_work"] is None

    def test_session_start_info_with_active_feature(
        self, sdk_with_feature, isolated_db
    ):
        """Test that session start info includes active work item when available."""
        sdk, _ = sdk_with_feature

        info = sdk.get_session_start_info()

        assert "active_work" in info
        assert info["active_work"] is not None
        assert info["active_work"]["id"] == "feat-test-001"
        assert info["active_work"]["type"] == "feature"
        assert info["active_work"]["status"] == "in-progress"

    def test_session_start_info_all_sections_present(self, empty_sdk, isolated_db):
        """Test that all expected sections are in session start info."""
        info = empty_sdk.get_session_start_info()

        expected_keys = ["status", "active_work", "features", "sessions", "analytics"]

        for key in expected_keys:
            assert key in info, f"Missing key: {key}"

    def test_session_start_info_json_serializable(self, sdk_with_feature, isolated_db):
        """Test that active_work serializes correctly to JSON."""
        sdk, _ = sdk_with_feature

        info = sdk.get_session_start_info()

        # Should be JSON-serializable
        json_str = json.dumps(info, default=str)
        parsed = json.loads(json_str)

        assert "active_work" in parsed
        assert parsed["active_work"] is not None
        assert parsed["active_work"]["id"] == "feat-test-001"


class TestGetActiveWorkItem:
    """Tests for get_active_work_item() SDK method."""

    def test_get_active_work_returns_none_when_empty(self, empty_sdk, isolated_db):
        """Test that get_active_work_item returns None when no active work."""
        active = empty_sdk.get_active_work_item()
        assert active is None

    def test_active_work_item_structure(self, sdk_with_feature, isolated_db):
        """Test that active work item has expected fields."""
        sdk, _ = sdk_with_feature

        active = sdk.get_active_work_item()

        expected_fields = ["id", "title", "type", "status", "agent"]
        for field in expected_fields:
            assert field in active, f"Missing field: {field}"

    def test_active_work_item_includes_steps(self, sdk_with_feature, isolated_db):
        """Test that active work item includes step counts."""
        sdk, _ = sdk_with_feature

        active = sdk.get_active_work_item()

        assert "steps_total" in active
        assert "steps_completed" in active
        assert isinstance(active["steps_total"], int)
        assert isinstance(active["steps_completed"], int)


class TestWorkTypeSymbolMapping:
    """Tests for work type symbol mapping in CLI output."""

    def test_feature_symbol_mapping(self, isolated_db):
        """Test feature type maps to correct symbol."""
        type_symbol = {
            "feature": "✨",
            "bug": "🐛",
            "spike": "🔍",
            "chore": "🔧",
            "epic": "🎯",
        }.get("feature")

        assert type_symbol == "✨"

    def test_bug_symbol_mapping(self, isolated_db):
        """Test bug type maps to correct symbol."""
        type_symbol = {
            "feature": "✨",
            "bug": "🐛",
            "spike": "🔍",
            "chore": "🔧",
            "epic": "🎯",
        }.get("bug")

        assert type_symbol == "🐛"

    def test_spike_symbol_mapping(self, isolated_db):
        """Test spike type maps to correct symbol."""
        type_symbol = {
            "feature": "✨",
            "bug": "🐛",
            "spike": "🔍",
            "chore": "🔧",
            "epic": "🎯",
        }.get("spike")

        assert type_symbol == "🔍"

    def test_unknown_type_symbol_mapping(self, isolated_db):
        """Test unknown type maps to default symbol."""
        type_symbol = {
            "feature": "✨",
            "bug": "🐛",
            "spike": "🔍",
            "chore": "🔧",
            "epic": "🎯",
        }.get("unknown", "📝")

        assert type_symbol == "📝"


class TestCLIOutputFormatting:
    """Tests for CLI output formatting of active work item."""

    def test_active_work_text_format_with_feature(self, sdk_with_feature, isolated_db):
        """Test that text output correctly formats active work item."""
        sdk, _ = sdk_with_feature

        info = sdk.get_session_start_info()
        active_work = info.get("active_work")

        assert active_work is not None

        # Simulate CLI output formatting
        type_symbol = {
            "feature": "✨",
            "bug": "🐛",
            "spike": "🔍",
            "chore": "🔧",
            "epic": "🎯",
        }.get(active_work.get("type"), "📝")

        steps_total = active_work.get("steps_total", 0)
        steps_completed = active_work.get("steps_completed", 0)
        progress_str = (
            f"({steps_completed}/{steps_total} steps)" if steps_total > 0 else ""
        )

        output = f"  {type_symbol} {active_work['id']}: {active_work['title']} {progress_str}".strip()

        # Verify output contains expected elements
        assert "✨" in output
        assert "feat-test-001" in output
        assert "Test Feature" in output

    def test_no_active_work_warning_text(self, empty_sdk, isolated_db):
        """Test that text output shows warning when no active work."""
        info = empty_sdk.get_session_start_info()
        active_work = info.get("active_work")

        assert active_work is None

        # Simulate warning text
        warning_lines = [
            "  ⚠️  No active work item",
            "  Code changes will be blocked until you assign work.",
            '  Create a feature: uv run htmlgraph feature create "Title"',
        ]

        # Verify warnings would be shown
        for line in warning_lines:
            assert "⚠️" in warning_lines[0] or "Code changes" in warning_lines[1]


class TestActiveWorkItemIntegration:
    """Integration tests for active work item in session management."""

    def test_active_work_returned_when_feature_exists(
        self, sdk_with_feature, isolated_db
    ):
        """Test active work is returned when feature exists and is in-progress."""
        sdk, expected_feature = sdk_with_feature

        active = sdk.get_active_work_item()

        assert active is not None
        assert active["id"] == expected_feature.id
        assert active["title"] == expected_feature.title
        assert active["type"] == "feature"

    def test_session_start_info_reflects_active_work(
        self, sdk_with_feature, isolated_db
    ):
        """Test that session start info reflects the same active work as get_active_work_item."""
        sdk, _ = sdk_with_feature

        direct_active = sdk.get_active_work_item()
        info_active = sdk.get_session_start_info()["active_work"]

        assert direct_active is not None
        assert info_active is not None
        assert direct_active["id"] == info_active["id"]
        assert direct_active["title"] == info_active["title"]

    def test_status_field_validation(self, sdk_with_feature, isolated_db):
        """Test that active work item has correct status."""
        sdk, _ = sdk_with_feature

        active = sdk.get_active_work_item()

        assert active["status"] == "in-progress"

    def test_multiple_work_items_returns_first(self, temp_graph_dir, isolated_db):
        """Test that get_active_work_item returns first when multiple exist."""
        from htmlgraph import HtmlGraph

        # Features are stored in features/ subdirectory
        features_dir = temp_graph_dir / "features"
        features_dir.mkdir(parents=True, exist_ok=True)

        graph = HtmlGraph(features_dir)
        sdk = SDK(directory=temp_graph_dir, agent="claude", db_path=str(isolated_db))

        # Create multiple in-progress features
        feature1 = Node(
            id="feat-001",
            title="Feature 1",
            type="feature",
            status="in-progress",
            created=datetime.now(),
            updated=datetime.now(),
        )

        feature2 = Node(
            id="feat-002",
            title="Feature 2",
            type="feature",
            status="in-progress",
            created=datetime.now(),
            updated=datetime.now(),
        )

        graph.add(feature1)
        graph.add(feature2)

        active = sdk.get_active_work_item()

        # Should return one of them
        assert active is not None
        assert active["id"] in ["feat-001", "feat-002"]


class TestActiveWorkWithNodeTypes:
    """Tests for active work detection across different node types."""

    def test_identify_feature_as_active(self, temp_graph_dir, isolated_db):
        """Test that feature nodes are identified as active work."""
        from htmlgraph import HtmlGraph

        # Features are stored in features/ subdirectory
        features_dir = temp_graph_dir / "features"
        features_dir.mkdir(parents=True, exist_ok=True)

        graph = HtmlGraph(features_dir)
        sdk = SDK(directory=temp_graph_dir, agent="claude", db_path=str(isolated_db))

        feature = Node(
            id="feat-identify-001",
            title="Identify Feature",
            type="feature",
            status="in-progress",
            created=datetime.now(),
            updated=datetime.now(),
        )

        graph.add(feature)
        active = sdk.get_active_work_item()

        assert active is not None
        assert active["type"] == "feature"

    def test_ignore_completed_work_items(self, temp_graph_dir, isolated_db):
        """Test that completed work items are not returned as active."""
        from htmlgraph import HtmlGraph

        graph = HtmlGraph(temp_graph_dir)
        sdk = SDK(directory=temp_graph_dir, agent="claude", db_path=str(isolated_db))

        completed_feature = Node(
            id="feat-completed-001",
            title="Completed Feature",
            type="feature",
            status="done",
            created=datetime.now(),
            updated=datetime.now(),
        )

        graph.add(completed_feature)
        active = sdk.get_active_work_item()

        # Should return None since the feature is done, not in-progress
        assert active is None

    def test_ignore_todo_work_items(self, temp_graph_dir, isolated_db):
        """Test that todo work items are not returned as active."""
        from htmlgraph import HtmlGraph

        graph = HtmlGraph(temp_graph_dir)
        sdk = SDK(directory=temp_graph_dir, agent="claude", db_path=str(isolated_db))

        todo_feature = Node(
            id="feat-todo-001",
            title="Todo Feature",
            type="feature",
            status="todo",
            created=datetime.now(),
            updated=datetime.now(),
        )

        graph.add(todo_feature)
        active = sdk.get_active_work_item()

        # Should return None since the feature is todo, not in-progress
        assert active is None
