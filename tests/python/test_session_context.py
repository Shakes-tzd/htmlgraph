"""
Tests for SessionContextBuilder and related classes.

Verifies that session context building logic extracted from the session-start
hook works correctly as standalone SDK methods.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from htmlgraph.session_context import (
    HTMLGRAPH_PROCESS_NOTICE,
    HTMLGRAPH_VERSION_WARNING,
    ORCHESTRATOR_DIRECTIVES,
    RESEARCH_FIRST_DEBUGGING,
    TRACKER_WORKFLOW,
    GitHooksInstaller,
    SessionContextBuilder,
    VersionChecker,
)

# ===========================================================================
# VersionChecker Tests
# ===========================================================================


class TestVersionChecker:
    """Tests for VersionChecker class."""

    def test_compare_versions_outdated(self):
        """Older version should be detected as outdated."""
        assert VersionChecker.compare_versions("0.25.0", "0.27.0") is True

    def test_compare_versions_current(self):
        """Same version should not be outdated."""
        assert VersionChecker.compare_versions("0.27.0", "0.27.0") is False

    def test_compare_versions_newer(self):
        """Newer version should not be outdated."""
        assert VersionChecker.compare_versions("0.28.0", "0.27.0") is False

    def test_compare_versions_patch_outdated(self):
        """Patch version difference detected."""
        assert VersionChecker.compare_versions("0.27.0", "0.27.1") is True

    def test_compare_versions_invalid_fallback(self):
        """Invalid version strings fall back to string comparison."""
        assert VersionChecker.compare_versions("abc", "def") is True

    def test_compare_versions_same_invalid(self):
        """Same invalid version strings are not outdated."""
        assert VersionChecker.compare_versions("abc", "abc") is False

    @patch.object(VersionChecker, "get_installed_version", return_value="0.25.0")
    @patch.object(VersionChecker, "get_latest_version", return_value="0.27.0")
    def test_get_version_status_outdated(self, mock_latest, mock_installed):
        """Status reports outdated when installed < latest."""
        status = VersionChecker.get_version_status()
        assert status["installed_version"] == "0.25.0"
        assert status["latest_version"] == "0.27.0"
        assert status["is_outdated"] is True

    @patch.object(VersionChecker, "get_installed_version", return_value="0.27.0")
    @patch.object(VersionChecker, "get_latest_version", return_value="0.27.0")
    def test_get_version_status_current(self, mock_latest, mock_installed):
        """Status reports current when versions match."""
        status = VersionChecker.get_version_status()
        assert status["is_outdated"] is False

    @patch.object(VersionChecker, "get_installed_version", return_value=None)
    @patch.object(VersionChecker, "get_latest_version", return_value="0.27.0")
    def test_get_version_status_missing_installed(self, mock_latest, mock_installed):
        """Status handles missing installed version gracefully."""
        status = VersionChecker.get_version_status()
        assert status["installed_version"] is None
        assert status["is_outdated"] is False

    @patch.object(VersionChecker, "get_installed_version", return_value="0.27.0")
    @patch.object(VersionChecker, "get_latest_version", return_value=None)
    def test_get_version_status_missing_latest(self, mock_latest, mock_installed):
        """Status handles missing latest version gracefully."""
        status = VersionChecker.get_version_status()
        assert status["latest_version"] is None
        assert status["is_outdated"] is False


# ===========================================================================
# GitHooksInstaller Tests
# ===========================================================================


class TestGitHooksInstaller:
    """Tests for GitHooksInstaller class."""

    def test_install_no_git_dir(self):
        """Returns False if not a git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert GitHooksInstaller.install(tmpdir) is False

    def test_install_no_hooks_source(self):
        """Returns False if hooks source doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / ".git").mkdir()
            assert GitHooksInstaller.install(tmpdir) is False

    def test_install_creates_hook(self):
        """Installs hook from source to target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create git hooks directory
            git_hooks_dir = project_dir / ".git" / "hooks"
            git_hooks_dir.mkdir(parents=True)

            # Create source hook
            hooks_source_dir = project_dir / "scripts" / "hooks"
            hooks_source_dir.mkdir(parents=True)
            source = hooks_source_dir / "pre-commit"
            source.write_text("#!/bin/bash\necho 'pre-commit hook'\n")

            assert GitHooksInstaller.install(tmpdir) is True

            target = git_hooks_dir / "pre-commit"
            assert target.exists()
            assert target.read_text() == source.read_text()

    def test_install_skips_if_current(self):
        """Returns True without copying if hook already up to date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create matching hooks
            git_hooks_dir = project_dir / ".git" / "hooks"
            git_hooks_dir.mkdir(parents=True)
            hooks_source_dir = project_dir / "scripts" / "hooks"
            hooks_source_dir.mkdir(parents=True)

            content = "#!/bin/bash\necho 'hook'\n"
            (hooks_source_dir / "pre-commit").write_text(content)
            (git_hooks_dir / "pre-commit").write_text(content)

            assert GitHooksInstaller.install(tmpdir) is True


# ===========================================================================
# SessionContextBuilder Tests
# ===========================================================================


class TestSessionContextBuilder:
    """Tests for SessionContextBuilder class."""

    def _make_builder(self, tmpdir: str) -> SessionContextBuilder:
        """Create a builder with standard test directories."""
        graph_dir = Path(tmpdir) / ".htmlgraph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "features").mkdir()
        (graph_dir / "sessions").mkdir()
        return SessionContextBuilder(graph_dir, tmpdir)

    def test_init(self):
        """Builder initializes with correct paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            assert builder.graph_dir == Path(tmpdir) / ".htmlgraph"
            assert builder.project_dir == Path(tmpdir)

    def test_get_feature_summary_empty(self):
        """Returns empty features and zero stats when no features exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            features, stats = builder.get_feature_summary()
            assert features == []
            assert stats["total"] == 0
            assert stats["done"] == 0
            assert stats["percentage"] == 0

    def test_get_session_summary_empty(self):
        """Returns None when no ended sessions exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            assert builder.get_session_summary() is None

    def test_detect_feature_conflicts_empty(self):
        """Returns empty list when no conflicts exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            conflicts = builder.detect_feature_conflicts()
            assert conflicts == []

    def test_detect_feature_conflicts_with_data(self):
        """Detects conflicts when multiple agents work on same feature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)

            features = [
                {"id": "feat-001", "title": "Test Feature", "status": "in-progress"},
            ]
            active_agents = [
                {"agent": "claude-code", "worked_on": ["feat-001"]},
                {"agent": "gemini", "worked_on": ["feat-001"]},
            ]

            conflicts = builder.detect_feature_conflicts(features, active_agents)
            assert len(conflicts) == 1
            assert conflicts[0]["feature_id"] == "feat-001"
            assert "claude-code" in conflicts[0]["agents"]
            assert "gemini" in conflicts[0]["agents"]

    def test_detect_feature_conflicts_no_overlap(self):
        """No conflicts when agents work on different features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)

            features = [
                {"id": "feat-001", "title": "Feature 1", "status": "in-progress"},
                {"id": "feat-002", "title": "Feature 2", "status": "in-progress"},
            ]
            active_agents = [
                {"agent": "claude-code", "worked_on": ["feat-001"]},
                {"agent": "gemini", "worked_on": ["feat-002"]},
            ]

            conflicts = builder.detect_feature_conflicts(features, active_agents)
            assert conflicts == []

    def test_build_version_section_not_outdated(self):
        """Returns empty string when version is current."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            with patch.object(
                VersionChecker,
                "get_version_status",
                return_value={
                    "installed_version": "0.27.0",
                    "latest_version": "0.27.0",
                    "is_outdated": False,
                },
            ):
                assert builder.build_version_section() == ""

    def test_build_version_section_outdated(self):
        """Returns warning when version is outdated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            with patch.object(
                VersionChecker,
                "get_version_status",
                return_value={
                    "installed_version": "0.25.0",
                    "latest_version": "0.27.0",
                    "is_outdated": True,
                },
            ):
                result = builder.build_version_section()
                assert "0.25.0" in result
                assert "0.27.0" in result
                assert "UPDATE AVAILABLE" in result

    def test_build_features_section_empty(self):
        """Features section shows 'No Active Features' when empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            features: list[dict] = []
            stats = {
                "total": 0,
                "done": 0,
                "in_progress": 0,
                "blocked": 0,
                "todo": 0,
                "percentage": 0,
            }
            result = builder.build_features_section(features, stats)
            assert "No Active Features" in result

    def test_build_features_section_with_active(self):
        """Features section shows active features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            features = [
                {"id": "feat-001", "title": "Test Feature", "status": "in-progress"},
            ]
            stats = {
                "total": 1,
                "done": 0,
                "in_progress": 1,
                "blocked": 0,
                "todo": 0,
                "percentage": 0,
            }
            result = builder.build_features_section(features, stats)
            assert "feat-001" in result
            assert "Test Feature" in result
            assert "Active Features" in result

    def test_build_features_section_with_pending(self):
        """Features section shows pending features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            features = [
                {"id": "feat-001", "title": "Pending Feature", "status": "todo"},
            ]
            stats = {
                "total": 1,
                "done": 0,
                "in_progress": 0,
                "blocked": 0,
                "todo": 1,
                "percentage": 0,
            }
            result = builder.build_features_section(features, stats)
            assert "Pending Features" in result
            assert "feat-001" in result

    def test_build_previous_session_section_empty(self):
        """Returns empty string when no previous session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            assert builder.build_previous_session_section() == ""

    def test_build_commits_section_empty(self):
        """Returns empty string when no commits (non-git dir)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            assert builder.build_commits_section() == ""

    def test_build_strategic_insights_section_empty(self):
        """Returns empty string when no analytics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            result = builder.build_strategic_insights_section(
                analytics={
                    "recommendations": [],
                    "bottlenecks": [],
                    "parallel_capacity": {"max_parallelism": 0},
                }
            )
            assert result == ""

    def test_build_strategic_insights_with_recommendations(self):
        """Shows recommendations when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            analytics = {
                "recommendations": [
                    {
                        "title": "Fix auth",
                        "score": 8.5,
                        "reasons": ["Critical path", "Blocking others"],
                    }
                ],
                "bottlenecks": [],
                "parallel_capacity": {"max_parallelism": 0},
            }
            result = builder.build_strategic_insights_section(analytics)
            assert "Fix auth" in result
            assert "8.5" in result
            assert "Strategic Insights" in result

    def test_build_strategic_insights_with_bottlenecks(self):
        """Shows bottlenecks when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            analytics = {
                "recommendations": [],
                "bottlenecks": [
                    {
                        "title": "Auth module",
                        "blocks_count": 3,
                        "impact_score": 9.0,
                    }
                ],
                "parallel_capacity": {"max_parallelism": 0},
            }
            result = builder.build_strategic_insights_section(analytics)
            assert "Auth module" in result
            assert "Bottlenecks" in result

    def test_build_agents_section_no_other_agents(self):
        """Returns empty when only claude-code is active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            agents = [{"agent": "claude-code", "event_count": 10}]
            assert builder.build_agents_section(agents) == ""

    def test_build_agents_section_with_other_agents(self):
        """Shows other active agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            agents = [
                {"agent": "claude-code", "event_count": 10},
                {"agent": "gemini", "event_count": 5, "worked_on": ["feat-001"]},
            ]
            result = builder.build_agents_section(agents)
            assert "gemini" in result
            assert "Other Active Agents" in result

    def test_build_conflicts_section_empty(self):
        """Returns empty string when no conflicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            assert builder.build_conflicts_section([]) == ""

    def test_build_conflicts_section_with_conflicts(self):
        """Shows conflict details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            conflicts = [
                {
                    "feature_id": "feat-001",
                    "title": "Auth Feature",
                    "agents": ["claude-code", "gemini"],
                }
            ]
            result = builder.build_conflicts_section(conflicts)
            assert "CONFLICT DETECTED" in result
            assert "Auth Feature" in result

    def test_build_continuity_section(self):
        """Continuity section contains expected instructions."""
        result = SessionContextBuilder.build_continuity_section()
        assert "Session Continuity" in result
        assert "brief status update" in result

    def test_build_status_summary_active_feature(self):
        """Status summary for active feature includes feature title."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            features = [
                {"id": "feat-001", "title": "My Feature", "status": "in-progress"},
            ]
            stats = {"done": 1, "total": 3, "percentage": 33}
            result = builder.build_status_summary(features, stats)
            assert "My Feature" in result
            assert "1/3" in result

    def test_build_status_summary_no_active_feature(self):
        """Status summary shows pending count when no active feature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            features = [
                {"id": "feat-001", "title": "Pending", "status": "todo"},
            ]
            stats = {"done": 0, "total": 1, "percentage": 0}
            result = builder.build_status_summary(features, stats)
            assert "No active feature" in result
            assert "1 pending" in result

    def test_orchestrator_status_active_strict(self):
        """Orchestrator status shows active strict mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            result = builder._build_orchestrator_status(True, "strict")
            assert "ACTIVE" in result
            assert "strict" in result
            assert "blocks direct implementation" in result

    def test_orchestrator_status_inactive(self):
        """Orchestrator status shows inactive state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            result = builder._build_orchestrator_status(False, "disabled")
            assert "INACTIVE" in result

    def test_orchestrator_status_error(self):
        """Orchestrator status shows error state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            result = builder._build_orchestrator_status(True, "error")
            assert "ERROR" in result

    def test_orchestrator_status_guidance(self):
        """Orchestrator status shows guidance mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            result = builder._build_orchestrator_status(True, "guidance")
            assert "guidance" in result
            assert "provides guidance only" in result

    def test_build_no_features(self):
        """Build returns minimal context when no features exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)

            # Mock to avoid actual async operations
            with (
                patch.object(
                    builder,
                    "run_parallel_init",
                    return_value={
                        "system_prompt": None,
                        "analytics": {},
                        "parallelized": False,
                    },
                ),
                patch.object(
                    builder, "activate_orchestrator_mode", return_value=(True, "strict")
                ),
            ):
                context = builder.build(session_id="test-session", compute_async=True)
                assert "No Features Found" in context
                assert "htmlgraph init" in context

    def test_build_with_features(self):
        """Build includes all sections when features exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            (graph_dir / "features").mkdir()
            (graph_dir / "sessions").mkdir()

            builder = SessionContextBuilder(graph_dir, tmpdir)

            mock_features = [
                {
                    "id": "feat-001",
                    "title": "Test Feature",
                    "status": "in-progress",
                    "priority": "high",
                    "done_steps": 1,
                    "total_steps": 3,
                },
            ]
            mock_stats = {
                "total": 1,
                "done": 0,
                "in_progress": 1,
                "blocked": 0,
                "todo": 0,
                "percentage": 0,
            }

            with (
                patch.object(
                    builder,
                    "run_parallel_init",
                    return_value={
                        "system_prompt": None,
                        "analytics": {
                            "recommendations": [],
                            "bottlenecks": [],
                            "parallel_capacity": {"max_parallelism": 0},
                        },
                        "parallelized": False,
                    },
                ),
                patch.object(
                    builder,
                    "get_feature_summary",
                    return_value=(mock_features, mock_stats),
                ),
                patch.object(
                    builder, "activate_orchestrator_mode", return_value=(True, "strict")
                ),
                patch.object(builder, "get_active_agents", return_value=[]),
                patch.object(builder, "get_cigs_context", return_value=""),
                patch.object(builder, "get_reflection_context", return_value=None),
            ):
                context = builder.build(session_id="test-session", compute_async=True)
                assert "HTMLGRAPH DEVELOPMENT PROCESS ACTIVE" in context
                assert "ORCHESTRATOR DIRECTIVES" in context
                assert "feat-001" in context
                assert "Test Feature" in context

    def test_build_with_system_prompt(self):
        """Build prepends system prompt when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)

            with (
                patch.object(
                    builder,
                    "run_parallel_init",
                    return_value={
                        "system_prompt": "Test system prompt content",
                        "analytics": {},
                        "parallelized": False,
                    },
                ),
                patch.object(
                    builder, "activate_orchestrator_mode", return_value=(True, "strict")
                ),
                patch.object(builder, "validate_token_count", return_value=(True, 10)),
            ):
                context = builder.build(session_id="test-session", compute_async=True)
                assert "SYSTEM PROMPT RESTORED" in context
                assert "Test system prompt content" in context

    def test_build_sync_mode(self):
        """Build works in synchronous mode (compute_async=False)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)

            with (
                patch.object(builder, "load_system_prompt", return_value=None),
                patch.object(
                    builder, "activate_orchestrator_mode", return_value=(True, "strict")
                ),
            ):
                context = builder.build(session_id="test-session", compute_async=False)
                assert "No Features Found" in context

    def test_wrap_with_system_prompt_none(self):
        """Wrapping with None system prompt returns context unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            context = "test context"
            result = builder._wrap_with_system_prompt(context, None, "sess-001")
            assert result == "test context"

    def test_wrap_with_system_prompt_present(self):
        """Wrapping with system prompt prepends it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = self._make_builder(tmpdir)
            with patch.object(builder, "validate_token_count", return_value=(True, 10)):
                result = builder._wrap_with_system_prompt(
                    "main context", "system prompt text", "sess-001"
                )
                assert "system prompt text" in result
                assert "main context" in result
                # System prompt should come first
                sys_idx = result.index("system prompt text")
                main_idx = result.index("main context")
                assert sys_idx < main_idx


# ===========================================================================
# Template content tests
# ===========================================================================


class TestContextTemplates:
    """Tests for static context templates."""

    def test_version_warning_format(self):
        """Version warning template formats correctly."""
        result = HTMLGRAPH_VERSION_WARNING.format(installed="0.25.0", latest="0.27.0")
        assert "0.25.0" in result
        assert "0.27.0" in result
        assert "uv pip install --upgrade htmlgraph" in result

    def test_process_notice_content(self):
        """Process notice contains expected sections."""
        assert "Feature Creation Decision Framework" in HTMLGRAPH_PROCESS_NOTICE
        assert "Quick Reference" in HTMLGRAPH_PROCESS_NOTICE
        assert "uv run htmlgraph status" in HTMLGRAPH_PROCESS_NOTICE

    def test_tracker_workflow_content(self):
        """Tracker workflow contains expected sections."""
        assert "Session Start" in TRACKER_WORKFLOW
        assert "During Work" in TRACKER_WORKFLOW
        assert "Session End" in TRACKER_WORKFLOW

    def test_research_first_debugging_content(self):
        """Research-first debugging contains expected methodology."""
        assert "Research First" in RESEARCH_FIRST_DEBUGGING
        assert "sdk.help()" in RESEARCH_FIRST_DEBUGGING

    def test_orchestrator_directives_content(self):
        """Orchestrator directives contain expected patterns."""
        assert "ALWAYS DELEGATE" in ORCHESTRATOR_DIRECTIVES
        assert "Task()" in ORCHESTRATOR_DIRECTIVES
        assert "CONTEXT COST MODEL" in ORCHESTRATOR_DIRECTIVES


# ===========================================================================
# SessionManager integration tests (new methods)
# ===========================================================================


class TestSessionManagerContextMethods:
    """Test the new context methods added to SessionManager."""

    def test_get_version_status(self):
        """SessionManager.get_version_status delegates to VersionChecker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            (graph_dir / "features").mkdir()
            (graph_dir / "sessions").mkdir()
            (graph_dir / "bugs").mkdir()

            from htmlgraph.session_manager import SessionManager

            manager = SessionManager(graph_dir)

            with patch(
                "htmlgraph.session_context.VersionChecker.get_version_status",
                return_value={
                    "installed_version": "0.27.0",
                    "latest_version": "0.27.0",
                    "is_outdated": False,
                },
            ):
                status = manager.get_version_status()
                assert status["is_outdated"] is False

    def test_initialize_git_hooks(self):
        """SessionManager.initialize_git_hooks delegates to GitHooksInstaller."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            (graph_dir / "features").mkdir()
            (graph_dir / "sessions").mkdir()
            (graph_dir / "bugs").mkdir()

            from htmlgraph.session_manager import SessionManager

            manager = SessionManager(graph_dir)

            with patch(
                "htmlgraph.session_context.GitHooksInstaller.install",
                return_value=False,
            ):
                result = manager.initialize_git_hooks(tmpdir)
                assert result is False

    def test_detect_feature_conflicts(self):
        """SessionManager.detect_feature_conflicts delegates to SessionContextBuilder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            (graph_dir / "features").mkdir()
            (graph_dir / "sessions").mkdir()
            (graph_dir / "bugs").mkdir()

            from htmlgraph.session_manager import SessionManager

            manager = SessionManager(graph_dir)
            conflicts = manager.detect_feature_conflicts()
            assert isinstance(conflicts, list)
            assert conflicts == []

    def test_get_start_context(self):
        """SessionManager.get_start_context delegates to SessionContextBuilder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            (graph_dir / "features").mkdir()
            (graph_dir / "sessions").mkdir()
            (graph_dir / "bugs").mkdir()

            from htmlgraph.session_manager import SessionManager

            manager = SessionManager(graph_dir)

            with patch(
                "htmlgraph.session_context.SessionContextBuilder.build",
                return_value="mocked context",
            ):
                context = manager.get_start_context(
                    session_id="test-001",
                    project_dir=tmpdir,
                    compute_async=False,
                )
                assert context == "mocked context"
