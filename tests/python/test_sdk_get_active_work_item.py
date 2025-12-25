"""
Tests for SDK.get_active_work_item() method.

This method is used by the PreToolUse validation hook to check if code changes
have an active work item for attribution.
"""

import pytest
from pathlib import Path
from htmlgraph import SDK, Node, Step


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
    (graph_dir / "epics").mkdir()
    (graph_dir / "sessions").mkdir()

    return SDK(directory=graph_dir, agent="test-agent")


def test_get_active_work_item_no_items(sdk: SDK):
    """Test when no work items exist (excluding auto-generated spikes)."""
    # Auto-spike may exist, but we're looking for user-created work items
    # Exclude spikes from search
    result = sdk.get_active_work_item(work_types=["features", "bugs", "chores", "epics"])
    assert result is None


def test_get_active_work_item_only_todo(sdk: SDK):
    """Test when only todo items exist (no in-progress user work)."""
    # Create a todo feature
    feature = sdk.features.create("Test Feature") \
        .set_priority("high") \
        .add_steps(["Step 1", "Step 2"]) \
        .save()

    # Exclude auto-generated spikes
    result = sdk.get_active_work_item(work_types=["features", "bugs", "chores", "epics"])
    assert result is None


def test_get_active_work_item_single_in_progress_feature(sdk: SDK):
    """Test with a single in-progress feature."""
    # Create an in-progress feature
    feature = sdk.features.create("Active Feature") \
        .set_priority("high") \
        .add_steps(["Step 1", "Step 2", "Step 3"]) \
        .save()

    # Start the feature
    with sdk.features.edit(feature.id) as f:
        f.status = "in-progress"
        f.agent_assigned = "test-agent"
        f.steps[0].completed = True

    result = sdk.get_active_work_item()

    assert result is not None
    assert result["id"] == feature.id
    assert result["title"] == "Active Feature"
    assert result["type"] == "feature"
    assert result["status"] == "in-progress"
    assert result["agent"] == "test-agent"
    assert result["steps_total"] == 3
    assert result["steps_completed"] == 1


def test_get_active_work_item_multiple_types(sdk: SDK):
    """Test with multiple work item types (feature, bug)."""
    # Create in-progress feature
    feature = sdk.features.create("Active Feature").save()
    with sdk.features.edit(feature.id) as f:
        f.status = "in-progress"

    # Create in-progress bug using SDK (proper way)
    from htmlgraph.graph import HtmlGraph
    bugs_graph = HtmlGraph(sdk._directory / "bugs")
    bug = Node(
        id="bug-001",
        title="Active Bug",
        type="bug",
        status="in-progress",
        steps=[Step(description="Fix bug")]
    )
    bugs_graph.add(bug)

    # Should return the first in-progress item found
    # Exclude auto-spikes to avoid interference
    result = sdk.get_active_work_item(work_types=["features", "bugs"])
    assert result is not None
    assert result["status"] == "in-progress"
    assert result["type"] in ["feature", "bug"]


def test_get_active_work_item_filter_by_agent(sdk: SDK):
    """Test filtering by agent."""
    # Create features assigned to different agents using the graph directly
    from htmlgraph.graph import HtmlGraph
    features_graph = HtmlGraph(sdk._directory / "features")

    feature1 = Node(
        id="feat-agent1",
        title="Feature 1",
        type="feature",
        status="in-progress",
        agent_assigned="agent-1",
        steps=[]
    )
    features_graph.add(feature1)

    feature2 = Node(
        id="feat-agent2",
        title="Feature 2",
        type="feature",
        status="in-progress",
        agent_assigned="agent-2",
        steps=[]
    )
    features_graph.add(feature2)

    # Without filtering - should return first in-progress (excluding spikes)
    result = sdk.get_active_work_item(filter_by_agent=False, work_types=["features"])
    assert result is not None

    # With agent filtering - should return only agent-1's work
    result = sdk.get_active_work_item(agent="agent-1", filter_by_agent=True, work_types=["features"])
    assert result is not None
    assert result["agent"] == "agent-1"
    assert result["id"] == "feat-agent1"

    # With agent filtering for agent-2
    result = sdk.get_active_work_item(agent="agent-2", filter_by_agent=True, work_types=["features"])
    assert result is not None
    assert result["agent"] == "agent-2"
    assert result["id"] == "feat-agent2"

    # With agent filtering for non-existent agent
    result = sdk.get_active_work_item(agent="agent-3", filter_by_agent=True, work_types=["features"])
    assert result is None


def test_get_active_work_item_specific_work_types(sdk: SDK):
    """Test filtering by specific work item types."""
    # Create in-progress items of different types using graphs
    from htmlgraph.graph import HtmlGraph

    features_graph = HtmlGraph(sdk._directory / "features")
    feature = Node(
        id="feat-001",
        title="Active Feature",
        type="feature",
        status="in-progress",
        steps=[]
    )
    features_graph.add(feature)

    bugs_graph = HtmlGraph(sdk._directory / "bugs")
    bug = Node(
        id="bug-001",
        title="Active Bug",
        type="bug",
        status="in-progress",
        steps=[]
    )
    bugs_graph.add(bug)

    # Query only features
    result = sdk.get_active_work_item(work_types=["features"])
    assert result is not None
    assert result["type"] == "feature"

    # Query only bugs
    result = sdk.get_active_work_item(work_types=["bugs"])
    assert result is not None
    assert result["type"] == "bug"

    # Query non-existent type
    result = sdk.get_active_work_item(work_types=["epics"])
    assert result is None


def test_get_active_work_item_done_items_ignored(sdk: SDK):
    """Test that done/completed items are not returned."""
    # Create a done feature using graph
    from htmlgraph.graph import HtmlGraph
    features_graph = HtmlGraph(sdk._directory / "features")

    feature = Node(
        id="feat-done",
        title="Done Feature",
        type="feature",
        status="done",
        priority="high",
        steps=[Step(description="Step 1", completed=True)]
    )
    features_graph.add(feature)

    # Should not return done items (exclude spikes to avoid auto-spikes)
    result = sdk.get_active_work_item(work_types=["features", "bugs", "chores", "epics"])
    assert result is None


def test_get_active_work_item_step_progress(sdk: SDK):
    """Test step progress calculation."""
    feature = sdk.features.create("Feature with Steps") \
        .add_steps([
            "Step 1",
            "Step 2",
            "Step 3",
            "Step 4",
            "Step 5"
        ]) \
        .save()

    with sdk.features.edit(feature.id) as f:
        f.status = "in-progress"
        f.steps[0].completed = True
        f.steps[1].completed = True
        f.steps[2].completed = True

    result = sdk.get_active_work_item()
    assert result is not None
    assert result["steps_total"] == 5
    assert result["steps_completed"] == 3
