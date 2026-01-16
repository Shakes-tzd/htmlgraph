"""Tests for cross-session analytics using Git commits as continuity spine."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from htmlgraph import SDK
from htmlgraph.analytics.cross_session import (
    CommitRangeReport,
    CommitWorkSummary,
    CrossSessionAnalytics,
    FeatureCrossSessionReport,
)
from htmlgraph.event_log import JsonlEventLog


@pytest.fixture
def temp_repo(isolated_graph_dir_full: Path, isolated_db: Path):
    """Create a temporary Git repository with HtmlGraph structure."""
    repo_path = isolated_graph_dir_full / "test_repo"
    repo_path.mkdir()

    # Initialize Git repo
    import subprocess

    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create .htmlgraph structure
    graph_dir = repo_path / ".htmlgraph"
    graph_dir.mkdir()
    (graph_dir / "features").mkdir()
    (graph_dir / "sessions").mkdir()
    (graph_dir / "events").mkdir()

    # Create initial commit
    readme = repo_path / "README.md"
    readme.write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def sdk_with_commits(temp_repo, isolated_db):
    """Create SDK with events linked to Git commits."""
    import subprocess

    graph_dir = temp_repo / ".htmlgraph"
    sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))

    # Get initial commit hash
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    initial_commit = result.stdout.strip()

    # Create events for initial commit
    JsonlEventLog(graph_dir / "events")
    now = datetime.now()

    events = [
        {
            "event_id": "evt-001",
            "timestamp": now.isoformat(),
            "session_id": "session-001",
            "agent": "test",
            "tool": "GitCommit",
            "summary": "Commit abc123: Initial commit",
            "success": True,
            "feature_id": "feature-setup",
            "drift_score": None,
            "start_commit": None,
            "continued_from": None,
            "work_type": "feature-implementation",
            "file_paths": ["README.md"],
            "payload": {
                "type": "GitCommit",
                "commit_hash": initial_commit,
                "commit_hash_short": initial_commit[:8],
                "branch": "main",
                "author_name": "Test User",
                "author_email": "test@example.com",
                "commit_message": "Initial commit",
                "subject": "Initial commit",
                "files_changed": ["README.md"],
                "insertions": 1,
                "deletions": 0,
                "features": ["feature-setup"],
            },
        }
    ]

    # Write events
    for evt in events:
        event_path = graph_dir / "events" / f"{evt['session_id']}.jsonl"
        with event_path.open("a") as f:
            f.write(json.dumps(evt) + "\n")

    # Create a second commit
    code_file = temp_repo / "code.py"
    code_file.write_text("print('Hello, World!')\n")
    subprocess.run(["git", "add", "code.py"], cwd=temp_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: Add hello world"],
        cwd=temp_repo,
        check=True,
        capture_output=True,
    )

    # Get second commit hash
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    second_commit = result.stdout.strip()

    # Create events for second commit
    second_events = [
        {
            "event_id": "evt-002",
            "timestamp": (now + timedelta(hours=1)).isoformat(),
            "session_id": "session-002",
            "agent": "test",
            "tool": "GitCommit",
            "summary": "Commit def456: feat: Add hello world",
            "success": True,
            "feature_id": "feature-hello",
            "drift_score": None,
            "start_commit": None,
            "continued_from": None,
            "work_type": "feature-implementation",
            "file_paths": ["code.py"],
            "payload": {
                "type": "GitCommit",
                "commit_hash": second_commit,
                "commit_hash_short": second_commit[:8],
                "branch": "main",
                "author_name": "Test User",
                "author_email": "test@example.com",
                "commit_message": "feat: Add hello world",
                "subject": "feat: Add hello world",
                "files_changed": ["code.py"],
                "insertions": 1,
                "deletions": 0,
                "features": ["feature-hello"],
            },
        },
        {
            "event_id": "evt-003",
            "timestamp": (now + timedelta(hours=2)).isoformat(),
            "session_id": "session-002",
            "agent": "test",
            "tool": "Edit",
            "summary": "Edit code.py",
            "success": True,
            "feature_id": "feature-hello",
            "drift_score": None,
            "start_commit": None,
            "continued_from": None,
            "work_type": "feature-implementation",
            "file_paths": ["code.py"],
            "payload": {
                "type": "GitCommit",
                "commit_hash": second_commit,
                "files_changed": ["code.py"],
            },
        },
    ]

    for evt in second_events:
        event_path = graph_dir / "events" / f"{evt['session_id']}.jsonl"
        with event_path.open("a") as f:
            f.write(json.dumps(evt) + "\n")

    return sdk, temp_repo, [initial_commit, second_commit]


class TestCrossSessionAnalytics:
    """Test CrossSessionAnalytics class."""

    def test_initialization(self, sdk_with_commits, isolated_db):
        """Test that CrossSessionAnalytics initializes correctly."""
        sdk, _, _ = sdk_with_commits

        analytics = CrossSessionAnalytics(sdk)

        assert analytics.sdk is sdk
        assert analytics._event_log is not None
        assert analytics._repo_root is not None

    def test_work_in_commit_range_all_commits(self, sdk_with_commits, isolated_db):
        """Test getting work for all commits."""
        sdk, temp_repo, commits = sdk_with_commits

        analytics = sdk.cross_session_analytics
        report = analytics.work_in_commit_range(from_commit=None, to_commit="HEAD")

        assert isinstance(report, CommitRangeReport)
        assert report.total_events >= 2  # At least 2 commit events
        assert "feature-setup" in report.features
        assert "feature-hello" in report.features
        assert "session-001" in report.sessions
        assert "session-002" in report.sessions

    def test_work_in_commit_range_specific_range(self, sdk_with_commits, isolated_db):
        """Test getting work for specific commit range."""
        sdk, temp_repo, commits = sdk_with_commits

        analytics = sdk.cross_session_analytics

        # Get work from first commit to HEAD
        report = analytics.work_in_commit_range(
            from_commit=f"{commits[0]}", to_commit="HEAD"
        )

        assert isinstance(report, CommitRangeReport)
        assert report.from_commit == commits[0]
        assert report.to_commit == "HEAD"

    def test_sessions_for_feature(self, sdk_with_commits, isolated_db):
        """Test finding sessions that worked on a feature."""
        sdk, _, _ = sdk_with_commits

        analytics = sdk.cross_session_analytics

        # Find sessions for feature-hello
        sessions = analytics.sessions_for_feature("feature-hello")

        assert "session-002" in sessions
        assert isinstance(sessions, list)

    def test_sessions_for_feature_nonexistent(self, sdk_with_commits, isolated_db):
        """Test finding sessions for nonexistent feature."""
        sdk, _, _ = sdk_with_commits

        analytics = sdk.cross_session_analytics

        sessions = analytics.sessions_for_feature("feature-nonexistent")

        assert sessions == []

    def test_feature_cross_session_report(self, sdk_with_commits, isolated_db):
        """Test generating cross-session report for a feature."""
        sdk, _, commits = sdk_with_commits

        analytics = sdk.cross_session_analytics

        report = analytics.feature_cross_session_report("feature-hello")

        assert isinstance(report, FeatureCrossSessionReport)
        assert report.feature_id == "feature-hello"
        assert "session-002" in report.sessions
        assert len(report.commits) > 0
        assert "test@example.com" in report.authors
        assert report.event_count >= 1
        assert "feature-implementation" in report.work_type_distribution

    def test_feature_cross_session_report_calculates_duration(
        self, sdk_with_commits, isolated_db
    ):
        """Test that feature report calculates duration correctly."""
        sdk, _, _ = sdk_with_commits

        analytics = sdk.cross_session_analytics

        report = analytics.feature_cross_session_report("feature-hello")

        assert report.start_time is not None
        assert report.end_time is not None
        assert report.duration_hours is not None
        assert report.duration_hours >= 0

    def test_work_by_author(self, sdk_with_commits, isolated_db):
        """Test analyzing work by author."""
        sdk, _, _ = sdk_with_commits

        analytics = sdk.cross_session_analytics

        authors = analytics.work_by_author()

        assert "test@example.com" in authors
        author_stats = authors["test@example.com"]
        assert author_stats["event_count"] >= 2
        assert "feature-setup" in author_stats["features"]
        assert "feature-hello" in author_stats["features"]
        assert len(author_stats["sessions"]) >= 2

    def test_work_by_author_filtered(self, sdk_with_commits, isolated_db):
        """Test filtering work by specific author."""
        sdk, _, _ = sdk_with_commits

        analytics = sdk.cross_session_analytics

        authors = analytics.work_by_author(author_email="test@example.com")

        assert len(authors) == 1
        assert "test@example.com" in authors

    def test_work_by_author_since_commit(self, sdk_with_commits, isolated_db):
        """Test analyzing work since a specific commit."""
        sdk, _, commits = sdk_with_commits

        analytics = sdk.cross_session_analytics

        # Get work since first commit (should include second commit)
        authors = analytics.work_by_author(since_commit=commits[0])

        assert "test@example.com" in authors

    def test_commits_for_session(self, sdk_with_commits, isolated_db):
        """Test getting commits for a session."""
        sdk, _, commits = sdk_with_commits

        analytics = sdk.cross_session_analytics

        session_commits = analytics.commits_for_session("session-002")

        assert len(session_commits) >= 1
        assert commits[1] in session_commits

    def test_commits_for_session_nonexistent(self, sdk_with_commits, isolated_db):
        """Test getting commits for nonexistent session."""
        sdk, _, _ = sdk_with_commits

        analytics = sdk.cross_session_analytics

        session_commits = analytics.commits_for_session("session-nonexistent")

        assert session_commits == []

    def test_commit_work_summary_structure(self, sdk_with_commits, isolated_db):
        """Test that CommitWorkSummary has correct structure."""
        sdk, _, _ = sdk_with_commits

        analytics = sdk.cross_session_analytics

        report = analytics.work_in_commit_range(from_commit=None, to_commit="HEAD")

        if report.commits:
            summary = report.commits[0]
            assert isinstance(summary, CommitWorkSummary)
            assert hasattr(summary, "commit_hash")
            assert hasattr(summary, "author_name")
            assert hasattr(summary, "commit_message")
            assert hasattr(summary, "features")
            assert hasattr(summary, "sessions")
            assert hasattr(summary, "event_count")


class TestCrossSessionAnalyticsEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_repository(self, isolated_graph_dir_full, isolated_db):
        """Test analytics on empty repository."""
        graph_dir = isolated_graph_dir_full

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        analytics = sdk.cross_session_analytics

        # Should not crash, just return empty results
        report = analytics.work_in_commit_range(from_commit=None, to_commit="HEAD")

        assert report.total_events == 0
        assert report.features == []
        assert report.sessions == []

    def test_no_git_repository(self, isolated_graph_dir_full, isolated_db):
        """Test analytics when not in a Git repository."""
        graph_dir = isolated_graph_dir_full

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        analytics = sdk.cross_session_analytics

        # Should handle gracefully
        assert analytics._repo_root is None

    def test_events_without_commits(self, isolated_graph_dir_full, isolated_db):
        """Test handling events that don't have commit hashes."""
        graph_dir = isolated_graph_dir_full

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))

        # Create events without commit hashes
        JsonlEventLog(graph_dir / "events")
        event_path = graph_dir / "events" / "session-001.jsonl"
        with event_path.open("w") as f:
            evt = {
                "event_id": "evt-001",
                "timestamp": datetime.now().isoformat(),
                "session_id": "session-001",
                "agent": "test",
                "tool": "Edit",
                "summary": "Edit file",
                "success": True,
                "feature_id": "feature-test",
                "drift_score": None,
                "start_commit": None,
                "continued_from": None,
                "work_type": "feature-implementation",
                "file_paths": ["test.py"],
                "payload": {},  # No commit hash
            }
            f.write(json.dumps(evt) + "\n")

        analytics = sdk.cross_session_analytics

        # Should not include uncommitted work by default
        report = analytics.work_in_commit_range(from_commit=None, to_commit="HEAD")
        assert report.total_events == 0

        # Should include when requested
        report = analytics.work_in_commit_range(
            from_commit=None, to_commit="HEAD", include_uncommitted=True
        )
        assert report.total_events == 1


class TestCrossSessionAnalyticsIntegration:
    """Integration tests with SDK."""

    def test_sdk_has_cross_session_analytics_property(
        self, isolated_graph_dir_full, isolated_db
    ):
        """Test that SDK has cross_session_analytics property."""
        graph_dir = isolated_graph_dir_full

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))

        assert hasattr(sdk, "cross_session_analytics")
        assert isinstance(sdk.cross_session_analytics, CrossSessionAnalytics)

    def test_cross_session_analytics_has_sdk_reference(
        self, isolated_graph_dir_full, isolated_db
    ):
        """Test that CrossSessionAnalytics has reference to SDK."""
        graph_dir = isolated_graph_dir_full

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))

        assert sdk.cross_session_analytics.sdk is sdk
