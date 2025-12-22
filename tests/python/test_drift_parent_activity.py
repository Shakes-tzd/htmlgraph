"""
Test drift detection with parent activities (Skill/Task invocations).

This test verifies that activities performed as part of a Skill or Task
invocation are not flagged as high-drift, even if they wouldn't normally
match the active feature context.
"""

import pytest

from htmlgraph.session_manager import SessionManager


@pytest.fixture
def temp_graph(tmp_path):
    """Create a temporary graph directory."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir()
    (graph_dir / "sessions").mkdir()
    (graph_dir / "features").mkdir()
    (graph_dir / "bugs").mkdir()
    return graph_dir


@pytest.fixture
def manager(temp_graph):
    """Create a SessionManager with a test graph."""
    return SessionManager(temp_graph)


def test_child_activities_have_no_drift(manager):
    """Test that child activities (with parent_activity_id) have no drift score."""
    # Create a feature
    feature = manager.create_feature(
        title="User Authentication",
        collection="features",
        description="Implement user auth",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track a parent activity (Skill invocation)
    parent_activity = manager.track_activity(
        session_id=session.id,
        tool="Skill",
        summary="Skill: create PDF document",
        file_paths=[]
    )

    # Track child activities that wouldn't normally match the feature
    child1 = manager.track_activity(
        session_id=session.id,
        tool="Read",
        summary="Read: /tmp/document.pdf",
        file_paths=["/tmp/document.pdf"],
        parent_activity_id=parent_activity.id
    )

    child2 = manager.track_activity(
        session_id=session.id,
        tool="Bash",
        summary="Bash: pdflatex document.tex",
        file_paths=[],
        parent_activity_id=parent_activity.id
    )

    # Verify parent activity may have drift (independent activity)
    assert parent_activity.drift_score is not None

    # Verify child activities have NO drift score
    assert child1.drift_score is None
    assert child2.drift_score is None

    # Verify child activities are linked to parent
    assert child1.parent_activity_id == parent_activity.id
    assert child2.parent_activity_id == parent_activity.id


def test_child_activities_inherit_feature_context(manager):
    """Test that child activities inherit the feature context from their parent."""
    # Create a feature
    feature = manager.create_feature(
        title="User Authentication",
        collection="features",
        description="Implement user auth",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")
    manager.set_primary_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track a parent activity (Task invocation)
    parent_activity = manager.track_activity(
        session_id=session.id,
        tool="Task",
        summary="Task: Research OAuth providers",
        file_paths=[]
    )

    # Track child activities with different file paths
    child1 = manager.track_activity(
        session_id=session.id,
        tool="WebSearch",
        summary="WebSearch: OAuth 2.0 best practices",
        file_paths=[],
        parent_activity_id=parent_activity.id
    )

    child2 = manager.track_activity(
        session_id=session.id,
        tool="WebFetch",
        summary="WebFetch: https://oauth.net/2/",
        file_paths=[],
        parent_activity_id=parent_activity.id
    )

    # All activities should be attributed to the same feature
    assert parent_activity.feature_id == feature.id
    assert child1.feature_id == feature.id
    assert child2.feature_id == feature.id

    # Child activities should have no drift
    assert child1.drift_score is None
    assert child2.drift_score is None


def test_independent_activities_still_have_drift(manager):
    """Test that independent activities (no parent) still have drift scores."""
    # Create a feature
    feature = manager.create_feature(
        title="User Authentication",
        collection="features",
        description="Implement user auth",
        priority="high",
        steps=["Design", "Implement", "Test"]
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track activities that don't match the feature well
    activity1 = manager.track_activity(
        session_id=session.id,
        tool="Read",
        summary="Read: /tmp/unrelated.txt",
        file_paths=["/tmp/unrelated.txt"]
    )

    activity2 = manager.track_activity(
        session_id=session.id,
        tool="Bash",
        summary="Bash: npm install",
        file_paths=[]
    )

    # These should have drift scores (they're independent activities)
    assert activity1.drift_score is not None
    assert activity2.drift_score is not None

    # They should NOT have parent_activity_id
    assert activity1.parent_activity_id is None
    assert activity2.parent_activity_id is None


def test_nested_parent_activities(manager):
    """Test handling of nested parent activities (Task within Skill)."""
    # Create a feature
    feature = manager.create_feature(
        title="Documentation",
        collection="features",
        description="Write docs",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track outer parent (Skill)
    skill_activity = manager.track_activity(
        session_id=session.id,
        tool="Skill",
        summary="Skill: Generate PDF documentation",
        file_paths=[]
    )

    # Track inner parent (Task within Skill)
    task_activity = manager.track_activity(
        session_id=session.id,
        tool="Task",
        summary="Task: Research PDF generation",
        file_paths=[],
        parent_activity_id=skill_activity.id
    )

    # Track child of Task
    child_activity = manager.track_activity(
        session_id=session.id,
        tool="WebSearch",
        summary="WebSearch: Python PDF libraries",
        file_paths=[],
        parent_activity_id=task_activity.id
    )

    # All should be linked to the feature
    assert skill_activity.feature_id == feature.id
    assert task_activity.feature_id == feature.id
    assert child_activity.feature_id == feature.id

    # Inner parent and child should have no drift
    assert task_activity.drift_score is None
    assert child_activity.drift_score is None


def test_parent_activity_persists_in_html(manager):
    """Test that parent_activity_id is correctly saved and loaded from HTML."""
    # Create a feature and session
    feature = manager.create_feature(title="Test Feature", collection="features")
    manager.start_feature(feature.id, agent="claude-code")
    session = manager.start_session(agent="claude-code")

    # Track parent and child
    parent = manager.track_activity(
        session_id=session.id,
        tool="Skill",
        summary="Skill: test",
        file_paths=[]
    )

    child = manager.track_activity(
        session_id=session.id,
        tool="Read",
        summary="Read: test.txt",
        file_paths=["test.txt"],
        parent_activity_id=parent.id
    )

    # Reload session from disk
    manager._active_session = None  # Clear cache
    reloaded_session = manager.get_session(session.id)

    # Find the activities
    reloaded_parent = next(a for a in reloaded_session.activity_log if a.id == parent.id)
    reloaded_child = next(a for a in reloaded_session.activity_log if a.id == child.id)

    # Verify parent_activity_id persisted
    assert reloaded_parent.parent_activity_id is None
    assert reloaded_child.parent_activity_id == parent.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
