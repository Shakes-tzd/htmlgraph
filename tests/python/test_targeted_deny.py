"""
Tests for targeted deny enforcement (feat-2f7a486b).

Verifies that:
- Strict mode preserves deny decisions for git-write and implementation tools
- Non-strict mode converts deny to guidance (original safety net)
- NEVER_BLOCK_TOOLS remain unconditionally allowed
- Recovery commands (htmlgraph orchestrator *) are always allowed
- deny reason includes a specific delegation target
"""

import asyncio

import pytest
from htmlgraph.hooks.orchestrator import (
    enforce_orchestrator_mode,
    is_allowed_orchestrator_operation,
)
from htmlgraph.orchestrator_mode import OrchestratorModeManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hook_input(tool_name: str, command: str = "", file_path: str = "") -> dict:
    """Build a minimal hook stdin dict for pretooluse_hook."""
    tool_input: dict = {}
    if command:
        tool_input["command"] = command
    if file_path:
        tool_input["file_path"] = file_path
    return {"name": tool_name, "input": tool_input, "session_id": "sess-test"}


def _run(coro):
    """Run a coroutine in a new event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Test 1: git commit is denied in strict mode with delegation guidance
# ---------------------------------------------------------------------------


class TestGitWriteDeniedStrictMode:
    def test_git_commit_denied(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        result = enforce_orchestrator_mode(
            "Bash", {"command": "git commit -m 'test'"}, session_id="sess-test"
        )

        # Should deny (continue=False) with a reason that mentions delegation
        assert result["continue"] is False
        output = result["hookSpecificOutput"]
        assert output["permissionDecision"] == "deny"
        reason = output["permissionDecisionReason"]
        assert (
            "git commit" in reason.lower()
            or "git-write" in reason.lower()
            or "copilot" in reason.lower()
        )
        assert "Skill" in reason or "Agent" in reason


# ---------------------------------------------------------------------------
# Test 2: git status is allowed (read-only)
# ---------------------------------------------------------------------------


class TestGitReadAllowed:
    def test_git_status_allowed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        result = enforce_orchestrator_mode(
            "Bash", {"command": "git status"}, session_id="sess-test"
        )

        assert result["continue"] is True
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_git_log_allowed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        result = enforce_orchestrator_mode(
            "Bash", {"command": "git log --oneline -5"}, session_id="sess-test"
        )

        assert result["continue"] is True
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_git_diff_allowed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        result = enforce_orchestrator_mode(
            "Bash", {"command": "git diff HEAD~1"}, session_id="sess-test"
        )

        assert result["continue"] is True


# ---------------------------------------------------------------------------
# Test 3: git push is denied with copilot suggestion
# ---------------------------------------------------------------------------


class TestGitPushDenied:
    def test_git_push_denied(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        result = enforce_orchestrator_mode(
            "Bash", {"command": "git push origin main"}, session_id="sess-test"
        )

        assert result["continue"] is False
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        # Must mention copilot skill or coder agent as specific delegation target
        assert "copilot" in reason.lower() or "sonnet-coder" in reason.lower()


# ---------------------------------------------------------------------------
# Test 4: Edit tool is denied in strict mode with coder agent suggestion
# ---------------------------------------------------------------------------


class TestEditDeniedStrictMode:
    def test_edit_denied_strict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Edit is a violation but advisory — circuit breaker must trigger for actual deny
        # Three violations to trigger circuit breaker
        for _ in range(3):
            enforce_orchestrator_mode(
                "Edit", {"file_path": "src/foo.py"}, session_id="sess-test"
            )

        # After circuit breaker, Edit should be denied
        result = enforce_orchestrator_mode(
            "Edit", {"file_path": "src/bar.py"}, session_id="sess-test"
        )
        assert result["continue"] is False
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------------------------------------------------------------------------
# Test 5: Read/Grep/Glob always allowed (NEVER_BLOCK_TOOLS)
# ---------------------------------------------------------------------------


class TestNeverBlockTools:
    @pytest.mark.parametrize("tool_name", ["Read", "Grep", "Glob"])
    def test_exploration_tools_always_allowed(self, tool_name, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        from htmlgraph.hooks.pretooluse import pretooluse_hook

        hook_input = _make_hook_input(tool_name, file_path="src/foo.py")
        # Add pattern for Grep/Glob
        hook_input["input"]["pattern"] = "*.py"

        result = _run(pretooluse_hook(hook_input))
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


# ---------------------------------------------------------------------------
# Test 6: Task/Agent/Skill always allowed
# ---------------------------------------------------------------------------


class TestOrchestrationToolsAlwaysAllowed:
    @pytest.mark.parametrize("tool_name", ["Task", "Agent", "Skill"])
    def test_orchestration_tools_always_allowed(self, tool_name, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        from htmlgraph.hooks.pretooluse import pretooluse_hook

        hook_input = _make_hook_input(tool_name)
        hook_input["input"]["prompt"] = "do something"

        result = _run(pretooluse_hook(hook_input))
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


# ---------------------------------------------------------------------------
# Test 7: "htmlgraph orchestrator reset-violations" always allowed (recovery)
# ---------------------------------------------------------------------------


class TestRecoveryCommandAlwaysAllowed:
    def test_orchestrator_reset_always_allowed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Trigger circuit breaker
        for _ in range(3):
            enforce_orchestrator_mode(
                "Edit", {"file_path": "src/foo.py"}, session_id="sess-test"
            )
        assert manager.is_circuit_breaker_triggered()

        from htmlgraph.hooks.pretooluse import pretooluse_hook

        hook_input = _make_hook_input(
            "Bash", command="uv run htmlgraph orchestrator reset-violations"
        )
        result = _run(pretooluse_hook(hook_input))
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_orchestrator_disable_always_allowed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        from htmlgraph.hooks.pretooluse import pretooluse_hook

        hook_input = _make_hook_input(
            "Bash", command="uv run htmlgraph orchestrator disable"
        )
        result = _run(pretooluse_hook(hook_input))
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


# ---------------------------------------------------------------------------
# Test 8: deny converts to guidance when NOT in strict mode
# ---------------------------------------------------------------------------


class TestDenyConvertsToGuidanceNonStrict:
    def test_deny_stripped_in_guidance_mode(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="guidance")

        from htmlgraph.hooks.pretooluse import pretooluse_hook

        # Build a hook input that would normally produce a deny (git write)
        hook_input = _make_hook_input("Bash", command="git commit -m 'x'")
        result = _run(pretooluse_hook(hook_input))

        # In guidance mode, deny must be stripped — result is always allow
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_deny_stripped_when_mode_disabled(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # No orchestrator mode enabled — default is disabled

        from htmlgraph.hooks.pretooluse import pretooluse_hook

        hook_input = _make_hook_input("Bash", command="git push origin main")
        result = _run(pretooluse_hook(hook_input))

        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


# ---------------------------------------------------------------------------
# Test 9: deny is preserved when in strict mode
# ---------------------------------------------------------------------------


class TestDenyPreservedInStrictMode:
    def test_git_commit_deny_preserved(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        from htmlgraph.hooks.pretooluse import pretooluse_hook

        hook_input = _make_hook_input("Bash", command="git commit -m 'feat: something'")
        result = _run(pretooluse_hook(hook_input))

        # Strict mode: deny must NOT be converted to allow
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "permissionDecisionReason" in result["hookSpecificOutput"]

    def test_git_push_deny_preserved(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        from htmlgraph.hooks.pretooluse import pretooluse_hook

        hook_input = _make_hook_input("Bash", command="git push origin main")
        result = _run(pretooluse_hook(hook_input))

        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------------------------------------------------------------------------
# Test 10: permissionDecisionReason includes specific delegation target
# ---------------------------------------------------------------------------


class TestDenyReasonIncludesDelegationTarget:
    @pytest.mark.parametrize(
        "command",
        [
            "git commit -m 'fix bug'",
            "git push origin main",
            "git add .",
            "git merge feature-branch",
        ],
    )
    def test_deny_reason_has_specific_target(self, command, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        result = enforce_orchestrator_mode(
            "Bash", {"command": command}, session_id="sess-test"
        )

        assert result["continue"] is False
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        # Reason must name a specific delegation target, not a generic message
        has_specific_target = (
            "Skill" in reason
            or "Agent" in reason
            or "copilot" in reason.lower()
            or "sonnet-coder" in reason.lower()
        )
        assert has_specific_target, f"No delegation target in reason: {reason!r}"


# ---------------------------------------------------------------------------
# Test: is_allowed_orchestrator_operation returns False for git-write
# ---------------------------------------------------------------------------


class TestIsAllowedOrchestrator:
    def test_git_write_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        allowed, reason, category = is_allowed_orchestrator_operation(
            "Bash", {"command": "git commit -m 'x'"}, session_id="sess-test"
        )
        assert allowed is False
        assert category == "git-write-violation"
        assert reason  # Non-empty

    def test_git_readonly_returns_true(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        allowed, _reason, category = is_allowed_orchestrator_operation(
            "Bash", {"command": "git status"}, session_id="sess-test"
        )
        assert allowed is True
        assert category == "git-readonly"
