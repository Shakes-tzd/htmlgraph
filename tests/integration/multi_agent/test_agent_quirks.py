"""
Tests for agent-specific quirks and edge cases in Git continuity spine.

Each agent (Claude, Codex, Gemini) may have different behaviors:
- Commit message formats
- File organization patterns
- Session lifecycle management
- Feature reference conventions

This test file ensures HtmlGraph handles these variations gracefully.
"""

import subprocess
from pathlib import Path

import pytest
from htmlgraph.event_log import EventRecord, JsonlEventLog
from htmlgraph.git_events import log_git_commit, parse_feature_refs
from htmlgraph.session_manager import SessionManager


def get_all_events(event_log: JsonlEventLog) -> list[EventRecord]:
    """Helper to get all events from event log."""
    events = []
    for _, evt_dict in event_log.iter_events():
        # Convert dict to EventRecord
        from datetime import datetime

        timestamp = evt_dict.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        events.append(
            EventRecord(
                event_id=evt_dict.get("event_id", ""),
                timestamp=timestamp,
                session_id=evt_dict.get("session_id", ""),
                agent=evt_dict.get("agent", ""),
                tool=evt_dict.get("tool", ""),
                summary=evt_dict.get("summary", ""),
                success=evt_dict.get("success", True),
                feature_id=evt_dict.get("feature_id"),
                drift_score=evt_dict.get("drift_score"),
                start_commit=evt_dict.get("start_commit"),
                continued_from=evt_dict.get("continued_from"),
                work_type=evt_dict.get("work_type"),
                session_status=evt_dict.get("session_status"),
                file_paths=evt_dict.get("file_paths", []),
                payload=evt_dict.get("payload", {}),
            )
        )
    return events


class TestClaudeCodeQuirks:
    """Test Claude Code-specific patterns and behaviors."""

    def test_claude_code_commit_format(self, git_repo_fixture):
        """Claude Code uses consistent commit message format."""
        repo_path, graph_dir = git_repo_fixture
        manager = SessionManager(graph_dir)

        feature = manager.create_feature("Claude Feature")

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            # Claude typically uses conventional commits
            (repo_path / "feature.py").write_text("# Feature\n")
            subprocess.run(["git", "add", "feature.py"], check=True)
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"feat: implement feature\n\nImplements: {feature.id}\n\nCo-authored-by: Claude",
                ],
                check=True,
            )

            log_git_commit(graph_dir)

            # Verify parsing handles multi-line commits
            event_log = JsonlEventLog(graph_dir / "events")
            events = get_all_events(event_log)
            git_commits = [e for e in events if e.tool == "GitCommit"]

            latest = git_commits[-1]
            assert feature.id in latest.payload.get("features", [])

        finally:
            os.chdir(original_cwd)

    def test_claude_session_continuity_with_start_commit(self, git_repo_fixture):
        """Claude sessions track start_commit for continuity."""
        repo_path, graph_dir = git_repo_fixture
        manager = SessionManager(graph_dir)

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            # Get current commit as start point
            current_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True,
            ).strip()

            session = manager.start_session(
                session_id="claude-continuity",
                agent="claude-code",
                start_commit=current_commit,
            )

            assert session.start_commit == current_commit

            # Make commits
            (repo_path / "work.py").write_text("# Work\n")
            subprocess.run(["git", "add", "work.py"], check=True)
            subprocess.run(["git", "commit", "-m", "feat: work"], check=True)
            log_git_commit(graph_dir)

            # Session events should reference start_commit
            event_log = JsonlEventLog(graph_dir / "events")
            events = get_all_events(event_log)
            session_events = [e for e in events if e.session_id == "claude-continuity"]

            for event in session_events:
                assert event.start_commit == current_commit

        finally:
            os.chdir(original_cwd)


class TestGitHubCodexQuirks:
    """Test GitHub Codex-specific patterns and behaviors."""

    def test_codex_inline_feature_refs(self, git_repo_fixture):
        """Codex may use inline feature references in commits."""
        repo_path, graph_dir = git_repo_fixture
        manager = SessionManager(graph_dir)

        feature = manager.create_feature("Codex Task")

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            # Codex might use more casual references
            (repo_path / "codex.py").write_text("# Codex\n")
            subprocess.run(["git", "add", "codex.py"], check=True)
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"working on {feature.id} - added codex module",
                ],
                check=True,
            )

            log_git_commit(graph_dir)

            # Verify inline reference is parsed
            refs = parse_feature_refs(f"working on {feature.id} - added codex module")
            assert feature.id in refs

        finally:
            os.chdir(original_cwd)

    def test_codex_no_active_session_fallback(self, git_repo_fixture):
        """Codex working without active session uses git pseudo-session."""
        repo_path, graph_dir = git_repo_fixture

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            # No session started - Codex working independently
            (repo_path / "independent.py").write_text("# Independent\n")
            subprocess.run(["git", "add", "independent.py"], check=True)
            subprocess.run(
                ["git", "commit", "-m", "add independent module"],
                check=True,
            )

            log_git_commit(graph_dir)

            # Should use 'git' pseudo-session
            event_log = JsonlEventLog(graph_dir / "events")
            events = get_all_events(event_log)
            git_commits = [e for e in events if e.tool == "GitCommit"]

            latest = git_commits[-1]
            assert latest.session_id == "git"
            assert latest.agent == "git"

        finally:
            os.chdir(original_cwd)


class TestGoogleGeminiQuirks:
    """Test Google Gemini-specific patterns and behaviors."""

    def test_gemini_multi_file_commits(self, git_repo_fixture):
        """Gemini may commit multiple files at once."""
        repo_path, graph_dir = git_repo_fixture
        manager = SessionManager(graph_dir)

        manager.start_session(
            session_id="gemini-multi",
            agent="gemini-pro",
        )

        feature = manager.create_feature("Multi-file Feature", agent="gemini-pro")
        manager.start_feature(feature.id, agent="gemini-pro")

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            # Gemini creates multiple related files
            components_dir = repo_path / "components"
            components_dir.mkdir(exist_ok=True)

            (components_dir / "header.tsx").write_text("// Header\n")
            (components_dir / "footer.tsx").write_text("// Footer\n")
            (components_dir / "sidebar.tsx").write_text("// Sidebar\n")

            subprocess.run(["git", "add", "components/"], check=True)
            subprocess.run(
                ["git", "commit", "-m", f"feat: add components [{feature.id}]"],
                check=True,
            )

            log_git_commit(graph_dir)

            # Verify all files tracked in event
            event_log = JsonlEventLog(graph_dir / "events")
            events = get_all_events(event_log)
            git_commits = [e for e in events if e.tool == "GitCommit"]

            latest = git_commits[-1]
            files_changed = latest.payload.get("files_changed", [])

            assert "components/header.tsx" in files_changed
            assert "components/footer.tsx" in files_changed
            assert "components/sidebar.tsx" in files_changed

        finally:
            os.chdir(original_cwd)

    def test_gemini_branch_workflow(self, git_repo_fixture):
        """Gemini may use feature branches heavily."""
        repo_path, graph_dir = git_repo_fixture
        manager = SessionManager(graph_dir)

        feature = manager.create_feature("Branch Feature")

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            # Create feature branch
            subprocess.run(
                ["git", "checkout", "-b", f"gemini/{feature.id}"],
                check=True,
                capture_output=True,
            )

            # Work on branch
            (repo_path / "branch_work.py").write_text("# Branch work\n")
            subprocess.run(["git", "add", "branch_work.py"], check=True)
            subprocess.run(
                ["git", "commit", "-m", f"feat: work on branch [{feature.id}]"],
                check=True,
            )

            log_git_commit(graph_dir)

            # Verify branch is tracked
            event_log = JsonlEventLog(graph_dir / "events")
            events = get_all_events(event_log)
            git_commits = [e for e in events if e.tool == "GitCommit"]

            latest = git_commits[-1]
            assert latest.payload.get("branch") == f"gemini/{feature.id}"

        finally:
            os.chdir(original_cwd)


class TestEdgeCases:
    """Test edge cases and error handling across all agents."""

    def test_commit_without_feature_reference(self, git_repo_fixture):
        """Commits without feature references are tracked but not attributed."""
        repo_path, graph_dir = git_repo_fixture

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            (repo_path / "unattributed.py").write_text("# Unattributed\n")
            subprocess.run(["git", "add", "unattributed.py"], check=True)
            subprocess.run(
                ["git", "commit", "-m", "misc: random fix"],
                check=True,
            )

            log_git_commit(graph_dir)

            # Verify event exists but feature_id is None
            event_log = JsonlEventLog(graph_dir / "events")
            events = get_all_events(event_log)
            git_commits = [e for e in events if e.tool == "GitCommit"]

            latest = git_commits[-1]
            # Should have no feature attribution
            assert latest.feature_id is None or latest.feature_id == ""

        finally:
            os.chdir(original_cwd)

    def test_merge_commit_with_multiple_features(self, git_repo_fixture):
        """Merge commits may reference multiple features."""
        repo_path, graph_dir = git_repo_fixture
        manager = SessionManager(graph_dir)

        feat1 = manager.create_feature("Feature 1")
        feat2 = manager.create_feature("Feature 2")

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            # Create branch with both features
            subprocess.run(
                ["git", "checkout", "-b", "multi-feature"],
                check=True,
                capture_output=True,
            )

            (repo_path / "multi.py").write_text("# Multi\n")
            subprocess.run(["git", "add", "multi.py"], check=True)
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"feat: implement both\n\n{feat1.id}\n{feat2.id}",
                ],
                check=True,
            )

            subprocess.run(
                ["git", "checkout", "main"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "git",
                    "merge",
                    "multi-feature",
                    "--no-ff",
                    "-m",
                    f"Merge multi-feature branch\n\n{feat1.id}\n{feat2.id}",
                ],
                check=True,
                capture_output=True,
            )

            log_git_commit(graph_dir)

            # Verify both features are in payload
            event_log = JsonlEventLog(graph_dir / "events")
            events = get_all_events(event_log)
            git_commits = [e for e in events if e.tool == "GitCommit"]

            latest = git_commits[-1]
            features = latest.payload.get("features", [])

            assert feat1.id in features
            assert feat2.id in features

        finally:
            os.chdir(original_cwd)

    def test_empty_commit_message(self, git_repo_fixture):
        """Empty commit messages are handled gracefully."""
        repo_path, graph_dir = git_repo_fixture

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            (repo_path / "empty_msg.py").write_text("# Empty msg\n")
            subprocess.run(["git", "add", "empty_msg.py"], check=True)
            subprocess.run(
                ["git", "commit", "--allow-empty-message", "-m", ""],
                check=True,
            )

            # Should not crash
            success = log_git_commit(graph_dir)
            assert success is True

        finally:
            os.chdir(original_cwd)

    def test_very_large_commit(self, git_repo_fixture):
        """Large commits with many files are handled correctly."""
        repo_path, graph_dir = git_repo_fixture

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            # Create many files
            large_dir = repo_path / "large"
            large_dir.mkdir(exist_ok=True)

            for i in range(50):
                (large_dir / f"file_{i}.py").write_text(f"# File {i}\n")

            subprocess.run(["git", "add", "large/"], check=True)
            subprocess.run(
                ["git", "commit", "-m", "feat: large commit"],
                check=True,
            )

            success = log_git_commit(graph_dir)
            assert success is True

            # Verify all files tracked
            event_log = JsonlEventLog(graph_dir / "events")
            events = get_all_events(event_log)
            git_commits = [e for e in events if e.tool == "GitCommit"]

            latest = git_commits[-1]
            files_changed = latest.payload.get("files_changed", [])

            # Should have all 50 files
            assert len([f for f in files_changed if f.startswith("large/file_")]) == 50

        finally:
            os.chdir(original_cwd)


class TestAgentDetection:
    """Test agent detection from Git author and commit patterns."""

    def test_detect_agent_from_author(self, git_repo_fixture):
        """Agent can be inferred from git author metadata."""
        repo_path, graph_dir = git_repo_fixture

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(repo_path)

            # Temporarily change git author to simulate different agents
            subprocess.run(
                ["git", "config", "user.name", "Claude Code"],
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "claude@anthropic.com"],
                check=True,
            )

            (repo_path / "claude_author.py").write_text("# Claude\n")
            subprocess.run(["git", "add", "claude_author.py"], check=True)
            subprocess.run(
                ["git", "commit", "-m", "feat: by claude"],
                check=True,
            )

            log_git_commit(graph_dir)

            event_log = JsonlEventLog(graph_dir / "events")
            events = get_all_events(event_log)
            git_commits = [e for e in events if e.tool == "GitCommit"]

            latest = git_commits[-1]
            # Author metadata is in payload
            assert latest.payload.get("author_name") == "Claude Code"
            assert latest.payload.get("author_email") == "claude@anthropic.com"

            # Restore original git config
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                check=True,
            )

        finally:
            os.chdir(original_cwd)


# Reuse fixture from main test file
@pytest.fixture
def git_repo_fixture(tmp_path):
    """Create a temporary Git repository with HtmlGraph initialized."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo with main branch
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
    )

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
    )

    # Initialize HtmlGraph
    graph_dir = repo_path / ".htmlgraph"
    graph_dir.mkdir()
    (graph_dir / "features").mkdir()
    (graph_dir / "sessions").mkdir()
    (graph_dir / "events").mkdir()

    yield repo_path, graph_dir
