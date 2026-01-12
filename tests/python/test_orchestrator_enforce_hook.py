"""
Tests for Orchestrator Enforcement Hook

Tests the PreToolUse hook that enforces orchestrator delegation patterns.
"""

import json
import subprocess
from pathlib import Path

import pytest
from htmlgraph.orchestrator_mode import OrchestratorModeManager


@pytest.fixture
def temp_graph_dir(tmp_path):
    """Create temporary .htmlgraph directory."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir(parents=True)
    return graph_dir


@pytest.fixture
def hook_script():
    """Path to orchestrator-enforce.py hook script."""
    return (
        Path(__file__).parent.parent.parent
        / "packages"
        / "claude-plugin"
        / "hooks"
        / "scripts"
        / "orchestrator-enforce.py"
    )


@pytest.fixture
def clean_tool_history():
    """
    Clean up tool history (no-op now that history is in database).

    Tool history is now stored in SQLite database (.htmlgraph/htmlgraph.db)
    and isolated by session_id. This fixture is kept for backward compatibility.
    """
    yield


def run_hook(
    hook_script: Path,
    tool_name: str,
    tool_input: dict,
    cwd: Path = None,
    session_id: str = "test-session",
) -> dict:
    """
    Run the orchestrator enforcement hook.

    Args:
        hook_script: Path to hook script
        tool_name: Name of tool being called
        tool_input: Tool input parameters
        cwd: Working directory (for .htmlgraph lookup)
        session_id: Session identifier for tool history isolation

    Returns:
        Hook response dict
    """
    hook_input = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "session_id": session_id,
    }

    # Use python directly instead of 'uv run' to avoid PEP 723 isolated environment
    # that might have cached/old versions of htmlgraph
    import sys

    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Hook failed: {result.stderr}")

    return json.loads(result.stdout)


class TestOrchestratorModeDisabled:
    """Test behavior when orchestrator mode is disabled."""

    def test_allows_all_operations_when_disabled(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """When mode is disabled, all operations should be allowed."""
        # Don't create orchestrator-mode.json (mode disabled by default)

        # Test various tools
        tools = [
            ("Read", {"file_path": "/tmp/test.py"}),
            (
                "Edit",
                {"file_path": "/tmp/test.py", "old_string": "a", "new_string": "b"},
            ),
            ("Write", {"file_path": "/tmp/test.py", "content": "test"}),
            ("Bash", {"command": "pytest"}),
            ("Task", {"prompt": "test"}),
        ]

        for tool_name, tool_input in tools:
            response = run_hook(
                hook_script, tool_name, tool_input, cwd=temp_graph_dir.parent
            )
            assert response["continue"] is True
            assert "hookSpecificOutput" not in response  # No warnings/blocks


class TestAlwaysAllowedOperations:
    """Test operations that are always allowed in orchestrator mode."""

    def test_task_always_allowed(self, hook_script, temp_graph_dir, clean_tool_history):
        """Task tool is always allowed (core orchestration)."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Task", {"prompt": "Test task"}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True
        assert "error" not in response.get("hookSpecificOutput", {})

    def test_ask_user_question_always_allowed(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """AskUserQuestion is always allowed."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script,
            "AskUserQuestion",
            {"question": "Test?"},
            cwd=temp_graph_dir.parent,
        )

        assert response["continue"] is True
        assert "error" not in response.get("hookSpecificOutput", {})

    def test_todo_write_always_allowed(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """TodoWrite is always allowed."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "TodoWrite", {"todos": []}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True
        assert "error" not in response.get("hookSpecificOutput", {})


class TestSDKOperations:
    """Test SDK operations that are always allowed."""

    def test_htmlgraph_sdk_command_allowed(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """uv run htmlgraph commands are always allowed."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script,
            "Bash",
            {"command": "uv run htmlgraph feature list"},
            cwd=temp_graph_dir.parent,
        )

        assert response["continue"] is True
        assert "error" not in response.get("hookSpecificOutput", {})

    def test_git_status_allowed(self, hook_script, temp_graph_dir, clean_tool_history):
        """git status is allowed (read-only)."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Bash", {"command": "git status"}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True
        assert "error" not in response.get("hookSpecificOutput", {})

    def test_git_diff_allowed(self, hook_script, temp_graph_dir, clean_tool_history):
        """git diff is allowed (read-only)."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Bash", {"command": "git diff"}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True
        assert "error" not in response.get("hookSpecificOutput", {})

    def test_sdk_inline_allowed(self, hook_script, temp_graph_dir, clean_tool_history):
        """Inline Python with htmlgraph import is allowed."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script,
            "Bash",
            {"command": "uv run python -c 'from htmlgraph import SDK; print(SDK)'"},
            cwd=temp_graph_dir.parent,
        )

        assert response["continue"] is True
        assert "error" not in response.get("hookSpecificOutput", {})


class TestSingleLookupAllowed:
    """Test that single Read/Grep/Glob operations are allowed."""

    def test_first_read_allowed(self, hook_script, temp_graph_dir, clean_tool_history):
        """First Read operation is allowed."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script,
            "Read",
            {"file_path": "/tmp/test.py"},
            cwd=temp_graph_dir.parent,
        )

        assert response["continue"] is True
        # May have guidance message but no error
        assert "error" not in response.get("hookSpecificOutput", {})

    def test_first_grep_allowed(self, hook_script, temp_graph_dir, clean_tool_history):
        """First Grep operation is allowed."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Grep", {"pattern": "test"}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True
        assert "error" not in response.get("hookSpecificOutput", {})

    def test_first_glob_allowed(self, hook_script, temp_graph_dir, clean_tool_history):
        """First Glob operation is allowed."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Glob", {"pattern": "*.py"}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True
        assert "error" not in response.get("hookSpecificOutput", {})


class TestMultipleLookupBlocked:
    """Test that multiple Read/Grep/Glob operations are blocked in strict mode."""

    def test_multiple_reads_blocked(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """Multiple Read operations should be blocked."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        # First read - allowed
        response1 = run_hook(
            hook_script,
            "Read",
            {"file_path": "/tmp/test1.py"},
            cwd=temp_graph_dir.parent,
        )
        assert response1["continue"] is True

        # Second read - blocked (advisory-only: warns but allows)
        response2 = run_hook(
            hook_script,
            "Read",
            {"file_path": "/tmp/test2.py"},
            cwd=temp_graph_dir.parent,
        )
        assert response2["continue"] is True  # Advisory-only: warnings but no blocking
        assert (
            "Multiple Read calls detected"
            in response2["hookSpecificOutput"]["additionalContext"]
        )
        assert (
            "Explorer subagent" in response2["hookSpecificOutput"]["additionalContext"]
        )

    def test_multiple_greps_blocked(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """Multiple Grep operations should be blocked."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        # First grep - allowed
        response1 = run_hook(
            hook_script, "Grep", {"pattern": "test1"}, cwd=temp_graph_dir.parent
        )
        assert response1["continue"] is True

        # Second grep - blocked (advisory-only: warns but allows)
        response2 = run_hook(
            hook_script, "Grep", {"pattern": "test2"}, cwd=temp_graph_dir.parent
        )
        assert response2["continue"] is True  # Advisory-only: warnings but no blocking
        assert (
            "Multiple Grep calls detected"
            in response2["hookSpecificOutput"]["additionalContext"]
        )


class TestImplementationBlocked:
    """Test that implementation tools are blocked in strict mode."""

    def test_edit_blocked(self, hook_script, temp_graph_dir, clean_tool_history):
        """Edit should be blocked in strict mode."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script,
            "Edit",
            {"file_path": "/tmp/test.py", "old_string": "a", "new_string": "b"},
            cwd=temp_graph_dir.parent,
        )

        assert response["continue"] is True  # Advisory-only: warnings but no blocking
        assert (
            "Edit is implementation work"
            in response["hookSpecificOutput"]["additionalContext"]
        )
        assert "Task(" in response["hookSpecificOutput"]["additionalContext"]
        assert "Coder subagent" in response["hookSpecificOutput"]["additionalContext"]

    def test_write_blocked(self, hook_script, temp_graph_dir, clean_tool_history):
        """Write should be blocked in strict mode."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script,
            "Write",
            {"file_path": "/tmp/test.py", "content": "test"},
            cwd=temp_graph_dir.parent,
        )

        assert response["continue"] is True  # Advisory-only: warnings but no blocking
        assert (
            "Write is implementation work"
            in response["hookSpecificOutput"]["additionalContext"]
        )
        assert "Task(" in response["hookSpecificOutput"]["additionalContext"]

    def test_notebook_edit_blocked(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """NotebookEdit should be blocked in strict mode."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script,
            "NotebookEdit",
            {"notebook_path": "/tmp/test.ipynb", "new_source": "test"},
            cwd=temp_graph_dir.parent,
        )

        assert response["continue"] is True  # Advisory-only: warnings but no blocking
        assert (
            "NotebookEdit is implementation work"
            in response["hookSpecificOutput"]["additionalContext"]
        )

    def test_delete_blocked(self, hook_script, temp_graph_dir, clean_tool_history):
        """Delete should be blocked in strict mode."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Delete", {"path": "/tmp/test.py"}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True  # Advisory-only: warnings but no blocking
        assert (
            "Delete is a destructive"
            in response["hookSpecificOutput"]["additionalContext"]
        )


class TestTestBuildBlocked:
    """Test that testing/building commands are blocked in strict mode."""

    def test_pytest_blocked(self, hook_script, temp_graph_dir, clean_tool_history):
        """pytest should be blocked in strict mode."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Bash", {"command": "pytest tests/"}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True  # Advisory-only: warnings but no blocking
        assert "Testing/building" in response["hookSpecificOutput"]["additionalContext"]
        assert "Task tool" in response["hookSpecificOutput"]["additionalContext"]

    def test_npm_test_blocked(self, hook_script, temp_graph_dir, clean_tool_history):
        """npm test should be blocked in strict mode."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Bash", {"command": "npm test"}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True  # Advisory-only: warnings but no blocking
        assert "Testing/building" in response["hookSpecificOutput"]["additionalContext"]

    def test_npm_build_blocked(self, hook_script, temp_graph_dir, clean_tool_history):
        """npm build should be blocked in strict mode."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Bash", {"command": "npm run build"}, cwd=temp_graph_dir.parent
        )

        assert response["continue"] is True  # Advisory-only: warnings but no blocking
        assert "Testing/building" in response["hookSpecificOutput"]["additionalContext"]


class TestGuidanceMode:
    """Test guidance mode behavior (warns but allows)."""

    def test_edit_allowed_with_warning(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """In guidance mode, Edit is allowed but warned."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="guidance")

        response = run_hook(
            hook_script,
            "Edit",
            {"file_path": "/tmp/test.py", "old_string": "a", "new_string": "b"},
            cwd=temp_graph_dir.parent,
        )

        assert response["continue"] is True
        assert "⚠️ ORCHESTRATOR" in response["hookSpecificOutput"]["additionalContext"]
        assert "Task(" in response["hookSpecificOutput"]["additionalContext"]

    def test_multiple_reads_warned(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """In guidance mode, multiple reads are allowed but warned."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="guidance")

        # First read
        run_hook(
            hook_script,
            "Read",
            {"file_path": "/tmp/test1.py"},
            cwd=temp_graph_dir.parent,
        )

        # Second read - allowed with warning
        response = run_hook(
            hook_script,
            "Read",
            {"file_path": "/tmp/test2.py"},
            cwd=temp_graph_dir.parent,
        )

        assert response["continue"] is True
        assert "⚠️ ORCHESTRATOR" in response["hookSpecificOutput"]["additionalContext"]


class TestTaskSuggestions:
    """Test that appropriate Task suggestions are provided."""

    def test_edit_suggests_coder_subagent(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """Edit block should suggest Coder subagent."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script,
            "Edit",
            {"file_path": "/tmp/test.py", "old_string": "a", "new_string": "b"},
            cwd=temp_graph_dir.parent,
        )

        context = response["hookSpecificOutput"]["additionalContext"]
        assert "Task(" in context
        assert "general-purpose" in context
        assert "/tmp/test.py" in context

    def test_grep_suggests_explorer_subagent(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """Multiple Grep should suggest Explorer subagent."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        # First grep
        run_hook(hook_script, "Grep", {"pattern": "test1"}, cwd=temp_graph_dir.parent)

        # Second grep - blocked with Explorer suggestion
        response = run_hook(
            hook_script, "Grep", {"pattern": "test2"}, cwd=temp_graph_dir.parent
        )

        context = response["hookSpecificOutput"]["additionalContext"]
        assert "Task(" in context
        assert "Explore" in context

    def test_pytest_suggests_test_subagent(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """pytest should suggest testing subagent."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        response = run_hook(
            hook_script, "Bash", {"command": "pytest tests/"}, cwd=temp_graph_dir.parent
        )

        context = response["hookSpecificOutput"]["additionalContext"]
        assert "Task(" in context
        assert "run tests" in context.lower()


class TestEnvironmentOverrides:
    """Test environment variable overrides."""

    def test_htmlgraph_disabled_env_allows_all(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """HTMLGRAPH_DISABLE_TRACKING=1 should allow all operations."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        # Create custom environment with override
        import sys

        env = {**subprocess.os.environ, "HTMLGRAPH_DISABLE_TRACKING": "1"}

        hook_input = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/tmp/test.py",
                "old_string": "a",
                "new_string": "b",
            },
        }

        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            cwd=str(temp_graph_dir.parent),
            env=env,
        )

        response = json.loads(result.stdout)
        assert response["continue"] is True
        assert "hookSpecificOutput" not in response

    def test_orchestrator_disabled_env_allows_all(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """HTMLGRAPH_ORCHESTRATOR_DISABLED=1 should allow all operations."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        # Create custom environment with override
        import sys

        env = {**subprocess.os.environ, "HTMLGRAPH_ORCHESTRATOR_DISABLED": "1"}

        hook_input = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/tmp/test.py",
                "old_string": "a",
                "new_string": "b",
            },
        }

        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            cwd=str(temp_graph_dir.parent),
            env=env,
        )

        response = json.loads(result.stdout)
        assert response["continue"] is True
        assert "hookSpecificOutput" not in response


class TestToolHistorySequenceDetection:
    """Test that tool history correctly detects sequences."""

    def test_different_tools_dont_block_each_other(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """Read, Grep, and Glob shouldn't block each other."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        # Read, then Grep, then Glob - all should be allowed
        response1 = run_hook(
            hook_script,
            "Read",
            {"file_path": "/tmp/test.py"},
            cwd=temp_graph_dir.parent,
        )
        assert response1["continue"] is True

        response2 = run_hook(
            hook_script, "Grep", {"pattern": "test"}, cwd=temp_graph_dir.parent
        )
        assert response2["continue"] is True

        response3 = run_hook(
            hook_script, "Glob", {"pattern": "*.py"}, cwd=temp_graph_dir.parent
        )
        assert response3["continue"] is True

    def test_history_window_is_limited(
        self, hook_script, temp_graph_dir, clean_tool_history
    ):
        """Only recent history (last 3 calls) should matter."""
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        # Do 3 different tool calls to flush history window
        run_hook(hook_script, "Task", {"prompt": "test1"}, cwd=temp_graph_dir.parent)
        run_hook(hook_script, "Task", {"prompt": "test2"}, cwd=temp_graph_dir.parent)
        run_hook(hook_script, "Task", {"prompt": "test3"}, cwd=temp_graph_dir.parent)

        # Now Read should be allowed again (history window reset)
        response = run_hook(
            hook_script,
            "Read",
            {"file_path": "/tmp/test.py"},
            cwd=temp_graph_dir.parent,
        )
        assert response["continue"] is True
