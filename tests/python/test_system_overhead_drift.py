"""
Test drift detection for system overhead activities.

This test verifies that system overhead activities (Skill invocations for system skills,
reads from .htmlgraph/ directory) are not flagged as high-drift.
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


def test_skill_invocations_no_drift(manager):
    """Test that system skill invocations (htmlgraph-tracker) have no drift score."""
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

    # Track a Skill invocation for htmlgraph-tracker
    skill_activity = manager.track_activity(
        session_id=session.id,
        tool="Skill",
        summary="Skill: {'skill': 'htmlgraph-tracker'}",
        file_paths=[]
    )

    # Verify the skill invocation has NO drift score (system overhead)
    assert skill_activity.drift_score is None
    assert skill_activity.feature_id == feature.id  # Still attributed to feature
    assert "system_overhead" in str(skill_activity.payload.get("attribution_reason", ""))


def test_htmlgraph_metadata_reads_no_drift(manager):
    """Test that reads from .htmlgraph/ directory have no drift score."""
    # Create a feature
    feature = manager.create_feature(
        title="Bug Tracking",
        collection="features",
        description="Track bugs",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track a Read of .htmlgraph metadata file
    read_activity = manager.track_activity(
        session_id=session.id,
        tool="Read",
        summary="Read: /path/to/.htmlgraph/bugs/bug-001.html",
        file_paths=["/path/to/.htmlgraph/bugs/bug-001.html"]
    )

    # Verify the read has NO drift score (system overhead)
    assert read_activity.drift_score is None
    assert read_activity.feature_id == feature.id  # Still attributed to feature


def test_htmlgraph_metadata_writes_no_drift(manager):
    """Test that writes to .htmlgraph/ directory have no drift score."""
    # Create a feature
    feature = manager.create_feature(
        title="Feature Tracking",
        collection="features",
        description="Track features",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track a Write to .htmlgraph metadata file
    write_activity = manager.track_activity(
        session_id=session.id,
        tool="Write",
        summary="Write: .htmlgraph/features/feat-001.html",
        file_paths=[".htmlgraph/features/feat-001.html"]
    )

    # Verify the write has NO drift score (system overhead)
    assert write_activity.drift_score is None
    assert write_activity.feature_id == feature.id  # Still attributed to feature


def test_non_system_activities_still_have_drift(manager):
    """Test that non-system activities still get drift scores when appropriate."""
    # Create a feature with specific file patterns (but NO agent assignment)
    feature = manager.create_feature(
        title="User Authentication",
        collection="features",
        description="Implement user auth",
        priority="high",
    )

    # Set file patterns via properties
    feature.properties["file_patterns"] = ["src/auth/*.py"]
    manager.features_graph.update(feature)

    # Start the feature WITHOUT agent assignment
    manager.start_feature(feature.id, agent=None)

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track a Read of an unrelated file (should have drift)
    unrelated_activity = manager.track_activity(
        session_id=session.id,
        tool="Read",
        summary="Read: /tmp/unrelated.txt",
        file_paths=["/tmp/unrelated.txt"]
    )

    # Verify this activity HAS a drift score (not system overhead)
    assert unrelated_activity.drift_score is not None
    assert unrelated_activity.drift_score > 0.5  # High drift expected


def test_multiple_skill_invocations_no_drift(manager):
    """Test that repeated skill invocations don't accumulate drift."""
    # Create a feature
    feature = manager.create_feature(
        title="Self-Tracking",
        collection="features",
        description="Use HtmlGraph to track HtmlGraph",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track multiple skill invocations (simulating repeated tracker calls)
    activities = []
    for i in range(5):
        activity = manager.track_activity(
            session_id=session.id,
            tool="Skill",
            summary=f"Skill: {{'skill': 'htmlgraph:htmlgraph-tracker'}}",
            file_paths=[]
        )
        activities.append(activity)

    # Verify ALL skill invocations have NO drift score
    for activity in activities:
        assert activity.drift_score is None
        assert activity.feature_id == feature.id


def test_mixed_activities_correct_drift(manager):
    """Test that a mix of system and non-system activities are handled correctly."""
    # Create a feature (without agent assignment for realistic drift scores)
    feature = manager.create_feature(
        title="Mixed Work",
        collection="features",
        description="Mix of system and real work",
        priority="high",
    )

    # Set file patterns via properties
    feature.properties["file_patterns"] = ["src/*.py"]
    manager.features_graph.update(feature)

    # Start the feature WITHOUT agent assignment
    manager.start_feature(feature.id, agent=None)

    # Start a session
    session = manager.start_session(agent="claude-code")

    # 1. System overhead - Skill invocation
    skill_act = manager.track_activity(
        session_id=session.id,
        tool="Skill",
        summary="Skill: {'skill': 'htmlgraph-tracker'}",
        file_paths=[]
    )

    # 2. System overhead - .htmlgraph read
    meta_act = manager.track_activity(
        session_id=session.id,
        tool="Read",
        summary="Read: .htmlgraph/features/feat-001.html",
        file_paths=[".htmlgraph/features/feat-001.html"]
    )

    # 3. Real work - matching file pattern
    work_act = manager.track_activity(
        session_id=session.id,
        tool="Edit",
        summary="Edit: src/main.py",
        file_paths=["src/main.py"]
    )

    # 4. Real work - unrelated file (drift)
    drift_act = manager.track_activity(
        session_id=session.id,
        tool="Read",
        summary="Read: /tmp/unrelated.txt",
        file_paths=["/tmp/unrelated.txt"]
    )

    # Verify drift scores
    assert skill_act.drift_score is None  # System overhead
    assert meta_act.drift_score is None  # System overhead
    assert work_act.drift_score is not None  # Real work (should be low drift)
    assert work_act.drift_score < 0.5  # Low drift (matches pattern)
    assert drift_act.drift_score is not None  # Real work (should be high drift)
    assert drift_act.drift_score > 0.5  # High drift (doesn't match)


def test_config_files_no_drift(manager):
    """Test that configuration files have no drift score."""
    # Create a feature
    feature = manager.create_feature(
        title="Backend Development",
        collection="features",
        description="Backend work",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Test various config files
    config_files = [
        "pyproject.toml",
        "/home/user/project/pyproject.toml",
        "package.json",
        "pytest.ini",
        ".gitignore",
        ".pre-commit-config.yaml",
        "/abs/path/to/.github/workflows/ci.yml",
    ]

    for file_path in config_files:
        activity = manager.track_activity(
            session_id=session.id,
            tool="Edit",
            summary=f"Edit: {file_path}",
            file_paths=[file_path]
        )
        # Verify NO drift score (system overhead)
        assert activity.drift_score is None, f"Config file {file_path} should have no drift"
        assert activity.feature_id == feature.id


def test_documentation_files_no_drift(manager):
    """Test that documentation files have no drift score."""
    # Create a feature
    feature = manager.create_feature(
        title="Feature Work",
        collection="features",
        description="Main feature",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Test various documentation files
    doc_files = [
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "CHANGELOG.md",
        "docs/guide/index.md",
        "/home/user/project/docs/api/reference.md",
    ]

    for file_path in doc_files:
        activity = manager.track_activity(
            session_id=session.id,
            tool="Write",
            summary=f"Write: {file_path}",
            file_paths=[file_path]
        )
        # Verify NO drift score (system overhead)
        assert activity.drift_score is None, f"Doc file {file_path} should have no drift"


def test_build_artifacts_no_drift(manager):
    """Test that build artifacts have no drift score."""
    # Create a feature
    feature = manager.create_feature(
        title="Build Testing",
        collection="features",
        description="Test builds",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Test build artifacts
    build_files = [
        "dist/htmlgraph-0.9.0.tar.gz",
        "build/lib/module.py",
        "__pycache__/test.cpython-311.pyc",
        "htmlgraph.egg-info/PKG-INFO",
    ]

    for file_path in build_files:
        activity = manager.track_activity(
            session_id=session.id,
            tool="Read",
            summary=f"Read: {file_path}",
            file_paths=[file_path]
        )
        # Verify NO drift score (system overhead)
        assert activity.drift_score is None, f"Build artifact {file_path} should have no drift"


def test_ide_files_no_drift(manager):
    """Test that IDE and editor files have no drift score."""
    # Create a feature
    feature = manager.create_feature(
        title="IDE Setup",
        collection="features",
        description="IDE config",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Test IDE files
    ide_files = [
        ".vscode/settings.json",
        ".idea/workspace.xml",
        "file.swp",
        ".DS_Store",
        "Thumbs.db",
    ]

    for file_path in ide_files:
        activity = manager.track_activity(
            session_id=session.id,
            tool="Edit",
            summary=f"Edit: {file_path}",
            file_paths=[file_path]
        )
        # Verify NO drift score (system overhead)
        assert activity.drift_score is None, f"IDE file {file_path} should have no drift"


def test_testing_artifacts_no_drift(manager):
    """Test that testing artifacts have no drift score."""
    # Create a feature
    feature = manager.create_feature(
        title="Testing",
        collection="features",
        description="Test suite",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Test testing artifacts
    test_files = [
        ".pytest_cache/v/cache/nodeids",
        ".coverage",
        "htmlcov/index.html",
        ".tox/py311/log/py311-1.log",
    ]

    for file_path in test_files:
        activity = manager.track_activity(
            session_id=session.id,
            tool="Read",
            summary=f"Read: {file_path}",
            file_paths=[file_path]
        )
        # Verify NO drift score (system overhead)
        assert activity.drift_score is None, f"Test artifact {file_path} should have no drift"


def test_source_code_files_have_drift(manager):
    """Test that actual source code files still get drift scores."""
    # Create a feature with specific file patterns (but NO agent assignment)
    feature = manager.create_feature(
        title="Backend API",
        collection="features",
        description="Backend API development",
        priority="high",
    )

    # Set file patterns via properties
    feature.properties["file_patterns"] = ["src/api/*.py"]
    manager.features_graph.update(feature)

    # Start the feature WITHOUT agent assignment
    manager.start_feature(feature.id, agent=None)

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track activity on an unrelated source file (should have drift)
    activity = manager.track_activity(
        session_id=session.id,
        tool="Edit",
        summary="Edit: src/frontend/app.js",
        file_paths=["src/frontend/app.js"]
    )

    # Verify this activity HAS a drift score (not infrastructure)
    assert activity.drift_score is not None
    assert activity.drift_score > 0.5  # High drift expected


def test_mixed_infrastructure_and_code_files(manager):
    """Test that a mix of infrastructure and code files are handled correctly."""
    # Create a feature (without agent assignment)
    feature = manager.create_feature(
        title="Full Stack Work",
        collection="features",
        description="Mix of infrastructure and code",
        priority="high",
    )

    # Set file patterns via properties
    feature.properties["file_patterns"] = ["src/*.py"]
    manager.features_graph.update(feature)

    # Start the feature WITHOUT agent assignment
    manager.start_feature(feature.id, agent=None)

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Track multiple files including infrastructure
    activity = manager.track_activity(
        session_id=session.id,
        tool="Edit",
        summary="Edit: multiple files",
        file_paths=[
            "src/main.py",  # Real work - matches pattern
            "pyproject.toml",  # Infrastructure
            "README.md",  # Infrastructure
        ]
    )

    # If ANY file is infrastructure, the whole activity is treated as system overhead
    assert activity.drift_score is None, "Activity with infrastructure files should have no drift"


def test_github_ci_files_no_drift(manager):
    """Test that GitHub CI/CD files have no drift score."""
    # Create a feature
    feature = manager.create_feature(
        title="CI Setup",
        collection="features",
        description="CI/CD work",
        priority="high",
    )

    # Start the feature
    manager.start_feature(feature.id, agent="claude-code")

    # Start a session
    session = manager.start_session(agent="claude-code")

    # Test CI/CD files
    ci_files = [
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".gitlab-ci.yml",
        ".travis.yml",
    ]

    for file_path in ci_files:
        activity = manager.track_activity(
            session_id=session.id,
            tool="Edit",
            summary=f"Edit: {file_path}",
            file_paths=[file_path]
        )
        # Verify NO drift score (system overhead)
        assert activity.drift_score is None, f"CI file {file_path} should have no drift"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
