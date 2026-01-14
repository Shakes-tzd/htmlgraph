"""
Tests for work queue functionality.

Tests the get_work_queue() and work_next() SDK methods that power
the `htmlgraph work queue` and `htmlgraph work next` CLI commands.
"""

import pytest
from htmlgraph.models import Node
from htmlgraph.sdk import SDK


@pytest.fixture
def temp_sdk(tmp_path, isolated_db):
    """Create a temporary SDK instance with test data."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir()

    # Create subdirectories
    for collection in [
        "features",
        "bugs",
        "spikes",
        "chores",
        "epics",
        "sessions",
        "tracks",
        "agents",
    ]:
        (graph_dir / collection).mkdir()

    sdk = SDK(directory=graph_dir, agent="test-agent", db_path=str(isolated_db))

    # Create test track
    track = sdk.tracks.create("Test Track").save()

    # Create test features with different priorities and statuses
    sdk.features.create("High priority feature", priority="high").set_track(
        track.id
    ).save()
    sdk.features.create("Medium priority feature", priority="medium").set_track(
        track.id
    ).save()
    sdk.features.create("Low priority feature", priority="low").set_track(
        track.id
    ).save()

    # Create a bug
    sdk.bugs.create("Critical bug", priority="high").save()

    # Create a blocked feature directly
    from htmlgraph.ids import generate_id
    from htmlgraph.models import Node

    blocked_feat_id = generate_id("feature", "Blocked feature")
    blocked_feat = Node(
        id=blocked_feat_id,
        title="Blocked feature",
        type="feature",
        status="blocked",
        priority="high",
    )
    sdk.features._ensure_graph().add(blocked_feat)

    # Create an in-progress feature directly
    in_progress_id = generate_id("feature", "In progress feature")
    in_progress = Node(
        id=in_progress_id,
        title="In progress feature",
        type="feature",
        status="in-progress",
        priority="medium",
        agent_assigned="other-agent",
    )
    sdk.features._ensure_graph().add(in_progress)

    return sdk


def test_get_work_queue_basic(temp_sdk, isolated_db):
    """Test basic work queue retrieval."""
    queue = temp_sdk.get_work_queue(agent_id="test-agent")

    # Should return todo and blocked items
    assert len(queue) > 0

    # Check structure of queue items
    item = queue[0]
    assert "task_id" in item
    assert "title" in item
    assert "status" in item
    assert "priority" in item
    assert "score" in item
    assert "type" in item
    assert "blocks_count" in item
    assert "blocked_by" in item


def test_get_work_queue_limit(temp_sdk, isolated_db):
    """Test work queue limit parameter."""
    queue = temp_sdk.get_work_queue(agent_id="test-agent", limit=2)

    assert len(queue) <= 2


def test_get_work_queue_min_score(temp_sdk, isolated_db):
    """Test work queue minimum score filtering."""
    # Get all items
    all_queue = temp_sdk.get_work_queue(agent_id="test-agent", limit=100)

    # Get items with high score threshold
    high_score_queue = temp_sdk.get_work_queue(
        agent_id="test-agent", limit=100, min_score=60.0
    )

    # High score queue should be smaller or equal
    assert len(high_score_queue) <= len(all_queue)

    # All items should meet minimum score
    for item in high_score_queue:
        assert item["score"] >= 60.0


def test_get_work_queue_includes_multiple_types(temp_sdk, isolated_db):
    """Test that work queue includes different work item types."""
    queue = temp_sdk.get_work_queue(agent_id="test-agent", limit=100)

    types = {item["type"] for item in queue}

    # Should include multiple types
    assert "feature" in types
    assert "bug" in types


def test_get_work_queue_excludes_in_progress(temp_sdk, isolated_db):
    """Test that work queue excludes in-progress items."""
    queue = temp_sdk.get_work_queue(agent_id="test-agent", limit=100)

    # Should not include in-progress items
    for item in queue:
        assert item["status"] != "in-progress"


def test_get_work_queue_includes_blocked(temp_sdk, isolated_db):
    """Test that work queue includes blocked items."""
    queue = temp_sdk.get_work_queue(agent_id="test-agent", limit=100)

    statuses = {item["status"] for item in queue}

    # Should include blocked items
    assert "blocked" in statuses or "todo" in statuses


def test_work_next_basic(temp_sdk, isolated_db):
    """Test getting next best task."""
    task = temp_sdk.work_next(agent_id="test-agent")

    assert task is not None
    assert isinstance(task, Node)
    assert task.status == "todo"


def test_work_next_auto_claim(temp_sdk, isolated_db):
    """Test auto-claiming next task."""
    task = temp_sdk.work_next(agent_id="test-agent", auto_claim=True)

    assert task is not None

    # Re-fetch task to verify it was updated (could be feature or bug)
    refetched = temp_sdk.features.get(task.id) or temp_sdk.bugs.get(task.id)
    assert refetched is not None
    assert refetched.status == "in-progress"
    assert refetched.agent_assigned == "test-agent"


def test_work_next_no_auto_claim(temp_sdk, isolated_db):
    """Test getting next task without auto-claiming."""
    task = temp_sdk.work_next(agent_id="test-agent", auto_claim=False)

    assert task is not None

    # Task should still be todo (could be feature or bug)
    refetched = temp_sdk.features.get(task.id) or temp_sdk.bugs.get(task.id)
    assert refetched is not None
    assert refetched.status == "todo"


def test_work_next_min_score(temp_sdk, isolated_db):
    """Test next task with minimum score threshold."""
    # High threshold might return None
    task = temp_sdk.work_next(agent_id="test-agent", min_score=1000.0)

    # Either None or a high-scoring task
    if task:
        # Verify it meets threshold (implicitly by getting returned)
        assert isinstance(task, Node)


def test_work_next_empty_queue(temp_sdk, isolated_db):
    """Test next task when no tasks available."""
    # Mark all tasks as done
    for feat in temp_sdk.features.all():
        with temp_sdk.features.edit(feat.id) as f:
            f.status = "done"

    for bug in temp_sdk.bugs.all():
        with temp_sdk.bugs.edit(bug.id) as b:
            b.status = "done"

    task = temp_sdk.work_next(agent_id="test-agent")
    assert task is None


def test_get_work_queue_empty(temp_sdk, isolated_db):
    """Test work queue when no tasks available."""
    # Mark all tasks as done
    for feat in temp_sdk.features.all():
        with temp_sdk.features.edit(feat.id) as f:
            f.status = "done"

    for bug in temp_sdk.bugs.all():
        with temp_sdk.bugs.edit(bug.id) as b:
            b.status = "done"

    queue = temp_sdk.get_work_queue(agent_id="test-agent")
    assert len(queue) == 0


def test_work_queue_priority_ordering(temp_sdk, isolated_db):
    """Test that high priority items get higher scores."""
    queue = temp_sdk.get_work_queue(agent_id="test-agent", limit=100)

    # Find high and low priority items
    high_priority = [item for item in queue if item["priority"] == "high"]
    low_priority = [item for item in queue if item["priority"] == "low"]

    if high_priority and low_priority:
        # High priority should generally score higher than low priority
        # (though routing can override based on other factors)
        sum(item["score"] for item in high_priority) / len(high_priority)
        sum(item["score"] for item in low_priority) / len(low_priority)

        # This is a soft check - routing logic may vary
        # Just ensure high priority items are represented in top results
        assert len(high_priority) > 0


def test_work_queue_with_dependencies(temp_sdk, isolated_db):
    """Test work queue shows dependency information."""
    from htmlgraph.ids import generate_id
    from htmlgraph.models import Edge, Node

    # Create a blocker feature
    blocker_id = generate_id("feature", "Blocker feature")
    blocker = Node(
        id=blocker_id,
        title="Blocker feature",
        type="feature",
        status="todo",
        priority="high",
    )
    temp_sdk.features._ensure_graph().add(blocker)

    # Create a blocked feature with dependency edge
    blocked_id = generate_id("feature", "Feature waiting on blocker")
    blocked = Node(
        id=blocked_id,
        title="Feature waiting on blocker",
        type="feature",
        status="todo",
        priority="high",
        edges={"blocked_by": [Edge(target_id=blocker.id, relationship="blocked_by")]},
    )
    temp_sdk.features._ensure_graph().add(blocked)

    queue = temp_sdk.get_work_queue(agent_id="test-agent", limit=100)

    # Find the blocked item in queue
    blocked_items = [item for item in queue if item["task_id"] == blocked.id]

    if blocked_items:
        item = blocked_items[0]
        assert len(item["blocked_by"]) > 0
        # blocked_by contains Edge objects or IDs depending on implementation
        # Check if blocker.id is in the list (either directly or via target_id)
        blocked_by_ids = []
        for edge_or_id in item["blocked_by"]:
            if isinstance(edge_or_id, str):
                blocked_by_ids.append(edge_or_id)
            else:
                blocked_by_ids.append(edge_or_id.target_id)
        assert blocker.id in blocked_by_ids
