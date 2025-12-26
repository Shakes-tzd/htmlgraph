"""
Tests for BaseCollection.filter() method.

This method allows filtering with custom lambda predicates for more complex queries.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from htmlgraph import SDK, Node


@pytest.fixture
def sdk(tmp_path: Path):
    """Create a temporary SDK instance."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir()

    # Create required subdirectories
    (graph_dir / "features").mkdir()
    (graph_dir / "bugs").mkdir()
    (graph_dir / "spikes").mkdir()
    (graph_dir / "chores").mkdir()

    return SDK(directory=graph_dir, agent="test-agent")


def test_filter_by_title_substring(sdk: SDK):
    """Test filtering features by substring in title."""
    # Create features with different titles
    sdk.features.create("High Priority Authentication").save()
    sdk.features.create("Low Priority Logging").save()
    sdk.features.create("High Priority Database").save()
    sdk.features.create("Medium Priority API").save()

    # Filter features with "High" in title
    high_priority = sdk.features.filter(lambda f: "High" in f.title)

    assert len(high_priority) == 2
    assert all("High" in f.title for f in high_priority)


def test_filter_by_multiple_conditions(sdk: SDK):
    """Test filtering with multiple conditions."""
    # Create features with different priorities and statuses
    sdk.features.create("Feature 1", priority="high", status="todo").save()
    sdk.features.create("Feature 2", priority="high", status="in-progress").save()
    sdk.features.create("Feature 3", priority="low", status="todo").save()
    sdk.features.create("Feature 4", priority="high", status="done").save()

    # Filter: high priority AND todo status
    urgent = sdk.features.filter(
        lambda f: f.priority == "high" and f.status == "todo"
    )

    assert len(urgent) == 1
    assert urgent[0].title == "Feature 1"
    assert urgent[0].priority == "high"
    assert urgent[0].status == "todo"


def test_filter_by_creation_date(sdk: SDK):
    """Test filtering by creation date."""
    # Create a feature
    feature = sdk.features.create("Recent Feature").save()

    # Filter features created in the last hour
    recent = sdk.features.filter(
        lambda f: f.created > datetime.now() - timedelta(hours=1)
    )

    assert len(recent) == 1
    assert recent[0].id == feature.id


def test_filter_empty_results(sdk: SDK):
    """Test that filter returns empty list when no matches."""
    # Create some features
    sdk.features.create("Feature 1", priority="low").save()
    sdk.features.create("Feature 2", priority="medium").save()

    # Filter for non-existent condition
    critical = sdk.features.filter(lambda f: f.priority == "critical")

    assert critical == []


def test_filter_with_agent_assigned(sdk: SDK):
    """Test filtering by agent assignment."""
    # Create features assigned to different agents
    f1 = sdk.features.create("Feature 1").save()
    f2 = sdk.features.create("Feature 2").save()
    f3 = sdk.features.create("Feature 3").save()

    # Assign to different agents
    with sdk.features.edit(f1.id) as feature:
        feature.agent_assigned = "claude"
    with sdk.features.edit(f2.id) as feature:
        feature.agent_assigned = "gemini"
    with sdk.features.edit(f3.id) as feature:
        feature.agent_assigned = "claude"

    # Filter by agent
    claude_features = sdk.features.filter(lambda f: f.agent_assigned == "claude")

    assert len(claude_features) == 2
    assert all(f.agent_assigned == "claude" for f in claude_features)


def test_filter_respects_node_type(sdk: SDK):
    """Test that filter only returns nodes of the correct type."""
    # Create features and bugs
    sdk.features.create("Feature 1", priority="high").save()

    from htmlgraph.graph import HtmlGraph
    bugs_graph = HtmlGraph(sdk._directory / "bugs")
    bug = Node(
        id="bug-001",
        title="Bug 1",
        type="bug",
        priority="high"
    )
    bugs_graph.add(bug)

    # Filter features by priority
    high_priority_features = sdk.features.filter(lambda f: f.priority == "high")

    # Should only return features, not bugs
    assert len(high_priority_features) == 1
    assert all(f.type == "feature" for f in high_priority_features)


def test_filter_with_complex_logic(sdk: SDK):
    """Test filter with complex predicate logic."""
    # Create features with various attributes
    sdk.features.create("Urgent Auth Fix", priority="critical", status="todo").save()
    sdk.features.create("Normal Feature", priority="medium", status="todo").save()
    sdk.features.create("High Priority Done", priority="high", status="done").save()
    sdk.features.create("Critical In Progress", priority="critical", status="in-progress").save()

    # Complex filter: (critical OR high) AND (todo OR in-progress)
    important_active = sdk.features.filter(
        lambda f: (f.priority in ["critical", "high"]) and (f.status in ["todo", "in-progress"])
    )

    assert len(important_active) == 2
    titles = [f.title for f in important_active]
    assert "Urgent Auth Fix" in titles
    assert "Critical In Progress" in titles
