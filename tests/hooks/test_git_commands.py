"""
Tests for git command classification module.

Ensures validator and orchestrator have consistent git command handling.
"""

import pytest
from htmlgraph.hooks.git_commands import (
    classify_git_command,
    get_git_delegation_reason,
    should_allow_git_command,
)


class TestGitCommandClassification:
    """Test git command classification (read/write/unknown)."""

    def test_classify_read_only_commands(self):
        """Test that read-only git commands are classified correctly."""
        read_commands = [
            "git status",
            "git log",
            "git log --oneline",
            "git log --graph --all",
            "git diff",
            "git diff HEAD~1",
            "git diff main..feature",
            "git show HEAD",
            "git show abc123",
            "git branch",
            "git branch -l",
            "git branch --list",
            "git reflog",
            "git ls-files",
            "git ls-remote origin",
            "git rev-parse HEAD",
            "git describe --tags",
            "git tag",
            "git tag -l",
            "git remote -v",
            "git remote show origin",
        ]

        for cmd in read_commands:
            assert classify_git_command(cmd) == "read", f"Expected {cmd} to be 'read'"

    def test_classify_write_commands(self):
        """Test that write git commands are classified correctly."""
        write_commands = [
            "git add .",
            "git add file.py",
            "git commit -m 'message'",
            "git commit --amend",
            "git push",
            "git push origin main",
            "git push --force",
            "git pull",
            "git pull origin main",
            "git fetch",
            "git fetch --all",
            "git merge main",
            "git merge --no-ff feature",
            "git rebase main",
            "git rebase -i HEAD~3",
            "git cherry-pick abc123",
            "git reset --hard HEAD",
            "git reset --soft HEAD~1",
            "git checkout main",
            "git checkout -b feature",
            "git switch main",
            "git restore file.py",
            "git rm file.py",
            "git mv old.py new.py",
            "git clean -fd",
            "git stash",
            "git stash pop",
            "git branch -d feature",
            "git branch -D feature",
            "git tag -a v1.0 -m 'Release'",
            "git tag -d v1.0",
        ]

        for cmd in write_commands:
            assert classify_git_command(cmd) == "write", f"Expected {cmd} to be 'write'"

    def test_classify_unknown_commands(self):
        """Test that non-git commands return 'unknown'."""
        unknown_commands = [
            "ls -la",
            "cat file.txt",
            "python script.py",
            "git",  # No subcommand
            "git unknown-subcommand",
            "",
        ]

        for cmd in unknown_commands:
            result = classify_git_command(cmd)
            assert result == "unknown", f"Expected {cmd} to be 'unknown', got {result}"

    def test_should_allow_read_commands(self):
        """Test that read-only commands are allowed."""
        assert should_allow_git_command("git status") is True
        assert should_allow_git_command("git log --oneline") is True
        assert should_allow_git_command("git diff HEAD~1") is True

    def test_should_not_allow_write_commands(self):
        """Test that write commands are not allowed."""
        assert should_allow_git_command("git add .") is False
        assert should_allow_git_command("git commit -m 'msg'") is False
        assert should_allow_git_command("git push origin main") is False

    def test_should_not_allow_unknown_commands(self):
        """Test that unknown commands are not allowed."""
        assert should_allow_git_command("ls -la") is False
        assert should_allow_git_command("git unknown") is False


class TestGitDelegationSuggestions:
    """Test git delegation reason messages."""

    def test_commit_delegation_reason(self):
        """Test delegation reason for git commit."""
        reason = get_git_delegation_reason("git commit -m 'message'")
        assert "commit" in reason.lower()
        assert "Skill('.claude-plugin:copilot')" in reason

    def test_merge_delegation_reason(self):
        """Test delegation reason for git merge."""
        reason = get_git_delegation_reason("git merge main")
        assert "merge" in reason.lower()
        assert "complex merge operation" in reason.lower()

    def test_reset_delegation_reason(self):
        """Test delegation reason for git reset."""
        reason = get_git_delegation_reason("git reset --hard HEAD")
        assert "reset" in reason.lower()
        assert "modify working tree" in reason.lower()


class TestValidatorIntegration:
    """Test that validator uses shared git classification."""

    def test_validator_imports_git_commands(self):
        """Test that validator can import git_commands module."""
        from htmlgraph.hooks.validator import is_always_allowed

        # This should not raise ImportError
        assert is_always_allowed is not None

    def test_validator_allows_git_reads(self):
        """Test that validator allows git read-only commands."""
        from htmlgraph.hooks.validator import is_always_allowed

        config = {"always_allow": {"tools": [], "bash_patterns": []}}
        params = {"command": "git status"}

        assert is_always_allowed("Bash", params, config) is True

    def test_validator_blocks_git_writes(self):
        """Test that validator does not auto-allow git write commands."""
        from htmlgraph.hooks.validator import is_always_allowed

        config = {"always_allow": {"tools": [], "bash_patterns": []}}
        params = {"command": "git commit -m 'msg'"}

        # Should NOT be auto-allowed (returns False)
        assert is_always_allowed("Bash", params, config) is False


class TestOrchestratorIntegration:
    """Test that orchestrator uses shared git classification."""

    def test_orchestrator_imports_git_commands(self):
        """Test that orchestrator can import git_commands module."""
        from htmlgraph.hooks.orchestrator import is_allowed_orchestrator_operation

        # This should not raise ImportError
        assert is_allowed_orchestrator_operation is not None

    def test_orchestrator_allows_git_reads(self):
        """Test that orchestrator allows git read-only commands."""
        from htmlgraph.hooks.orchestrator import is_allowed_orchestrator_operation

        params = {"command": "git status"}
        is_allowed, reason, category = is_allowed_orchestrator_operation(
            "Bash", params, session_id="test-session"
        )

        assert is_allowed is True
        assert category == "git-readonly"

    def test_orchestrator_blocks_git_writes_in_strict_mode(self):
        """Test that orchestrator blocks git write commands in strict mode."""
        from htmlgraph.hooks.orchestrator import is_allowed_orchestrator_operation

        params = {"command": "git commit -m 'msg'"}
        is_allowed, reason, category = is_allowed_orchestrator_operation(
            "Bash", params, session_id="test-session"
        )

        # Should NOT be allowed in strict mode
        assert is_allowed is False


class TestConsistencyBetweenHooks:
    """Test that validator and orchestrator have consistent behavior."""

    def test_git_status_allowed_by_both(self):
        """Test that git status is allowed by both validator and orchestrator."""
        from htmlgraph.hooks.orchestrator import is_allowed_orchestrator_operation
        from htmlgraph.hooks.validator import is_always_allowed

        params = {"command": "git status"}
        config = {"always_allow": {"tools": [], "bash_patterns": []}}

        # Validator should allow
        validator_allows = is_always_allowed("Bash", params, config)

        # Orchestrator should allow
        orch_allows, _, _ = is_allowed_orchestrator_operation(
            "Bash", params, session_id="test-session"
        )

        assert validator_allows is True
        assert orch_allows is True

    def test_git_log_allowed_by_both(self):
        """Test that git log is allowed by both validator and orchestrator."""
        from htmlgraph.hooks.orchestrator import is_allowed_orchestrator_operation
        from htmlgraph.hooks.validator import is_always_allowed

        params = {"command": "git log --oneline"}
        config = {"always_allow": {"tools": [], "bash_patterns": []}}

        # Validator should allow
        validator_allows = is_always_allowed("Bash", params, config)

        # Orchestrator should allow
        orch_allows, _, _ = is_allowed_orchestrator_operation(
            "Bash", params, session_id="test-session"
        )

        assert validator_allows is True
        assert orch_allows is True

    def test_git_diff_allowed_by_both(self):
        """Test that git diff is allowed by both validator and orchestrator."""
        from htmlgraph.hooks.orchestrator import is_allowed_orchestrator_operation
        from htmlgraph.hooks.validator import is_always_allowed

        params = {"command": "git diff HEAD~1"}
        config = {"always_allow": {"tools": [], "bash_patterns": []}}

        # Validator should allow
        validator_allows = is_always_allowed("Bash", params, config)

        # Orchestrator should allow
        orch_allows, _, _ = is_allowed_orchestrator_operation(
            "Bash", params, session_id="test-session"
        )

        assert validator_allows is True
        assert orch_allows is True

    def test_git_commit_blocked_by_both(self):
        """Test that git commit is not auto-allowed by either hook."""
        from htmlgraph.hooks.orchestrator import is_allowed_orchestrator_operation
        from htmlgraph.hooks.validator import is_always_allowed

        params = {"command": "git commit -m 'msg'"}
        config = {"always_allow": {"tools": [], "bash_patterns": []}}

        # Validator should NOT auto-allow
        validator_allows = is_always_allowed("Bash", params, config)

        # Orchestrator should NOT allow in strict mode
        orch_allows, _, _ = is_allowed_orchestrator_operation(
            "Bash", params, session_id="test-session"
        )

        assert validator_allows is False
        assert orch_allows is False

    def test_git_push_blocked_by_both(self):
        """Test that git push is not auto-allowed by either hook."""
        from htmlgraph.hooks.orchestrator import is_allowed_orchestrator_operation
        from htmlgraph.hooks.validator import is_always_allowed

        params = {"command": "git push origin main"}
        config = {"always_allow": {"tools": [], "bash_patterns": []}}

        # Validator should NOT auto-allow
        validator_allows = is_always_allowed("Bash", params, config)

        # Orchestrator should NOT allow in strict mode
        orch_allows, _, _ = is_allowed_orchestrator_operation(
            "Bash", params, session_id="test-session"
        )

        assert validator_allows is False
        assert orch_allows is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
