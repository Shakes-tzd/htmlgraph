"""Tests for orchestrator validator."""

from htmlgraph.orchestrator_validator import OrchestratorValidator


def test_sdk_operations_allowed():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "from htmlgraph import SDK\nsdk.features.create('test')"}
    )
    assert result == "allow"
    assert "SDK" in reason


def test_sdk_spikes_allowed():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "sdk.spikes.create('Research findings')"}
    )
    assert result == "allow"
    assert "SDK" in reason


def test_sdk_bugs_allowed():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "sdk.bugs.create('Fix validation error')"}
    )
    assert result == "allow"


def test_git_commit_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "git commit -m 'test'"}
    )
    assert result == "block"
    assert "Git operations" in reason


def test_git_push_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "git push origin main"}
    )
    assert result == "block"
    assert "Git operations" in reason


def test_git_add_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "git add src/main.py"}
    )
    assert result == "block"


def test_git_pull_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "git pull origin main"}
    )
    assert result == "block"


def test_git_merge_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "git merge feature-branch"}
    )
    assert result == "block"


def test_git_branch_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "git branch new-feature"}
    )
    assert result == "block"


def test_git_checkout_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "git checkout main"}
    )
    assert result == "block"


def test_git_rebase_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use("Bash", {"command": "git rebase main"})
    assert result == "block"


def test_strategic_tools_allowed():
    validator = OrchestratorValidator()

    for tool in ["Task", "AskUserQuestion", "TodoWrite"]:
        result, reason = validator.validate_tool_use(tool, {})
        assert result == "allow", f"{tool} should be allowed"
        assert "Strategic" in reason


def test_read_operations_allowed():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use("Read", {"file_path": "src/main.py"})
    assert result == "allow"
    assert "Read operations" in reason


def test_htmlgraph_file_edit_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Edit", {"file_path": ".htmlgraph/features/feat-123.html"}
    )
    assert result == "block"
    assert "SDK" in reason


def test_htmlgraph_file_write_blocked():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Write", {"file_path": ".htmlgraph/spikes/spk-456.html"}
    )
    assert result == "block"
    assert "SDK" in reason


def test_pytest_warned():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use("Bash", {"command": "pytest tests/"})
    assert result == "warn"
    assert "test-runner" in reason


def test_uv_pytest_warned():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "uv run pytest tests/"}
    )
    assert result == "warn"
    assert "test-runner" in reason


def test_python_pytest_warned():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "python -m pytest"}
    )
    assert result == "warn"


def test_npm_test_warned():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use("Bash", {"command": "npm test"})
    assert result == "warn"


def test_yarn_test_warned():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use("Bash", {"command": "yarn test"})
    assert result == "warn"


def test_regular_bash_allowed():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use("Bash", {"command": "ls -la"})
    assert result == "allow"


def test_regular_edit_allowed():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Edit", {"file_path": "src/main.py", "old_string": "foo", "new_string": "bar"}
    )
    assert result == "allow"


def test_regular_write_allowed():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Write", {"file_path": "docs/readme.md", "content": "# Documentation"}
    )
    assert result == "allow"


def test_grep_allowed():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Grep", {"pattern": "TODO", "path": "src/"}
    )
    assert result == "allow"


def test_glob_allowed():
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use("Glob", {"pattern": "**/*.py"})
    assert result == "allow"


def test_active_work_items_parameter():
    """Test that active_work_items parameter is accepted (even if not used yet)."""
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash",
        {"command": "git commit -m 'test'"},
        active_work_items=["feat-123", "spk-456"],
    )
    assert result == "block"  # Still blocks git operations


def test_git_operation_in_complex_command():
    """Test git operations embedded in complex commands are caught."""
    validator = OrchestratorValidator()

    result, reason = validator.validate_tool_use(
        "Bash", {"command": "cd /tmp && git add . && git commit -m 'temp'"}
    )
    assert result == "block"


def test_non_git_operation_with_git_keyword():
    """Test that 'git' keyword alone doesn't trigger block."""
    validator = OrchestratorValidator()

    # This should be allowed (not a git command)
    result, reason = validator.validate_tool_use(
        "Bash", {"command": "echo 'git is cool'"}
    )
    assert result == "allow"
