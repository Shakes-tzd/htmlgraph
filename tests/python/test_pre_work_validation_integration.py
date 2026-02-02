"""
Integration Tests for PreToolUse Validation Hook

Tests the complete validation flow including:
- Hook script execution
- SDK integration
- Real work item queries
- End-to-end validation decisions

Note: These are true integration tests - they execute the validation script
as a subprocess with real .htmlgraph data.
"""

import json
import subprocess
from pathlib import Path

import pytest

# Test fixtures


@pytest.fixture
def hook_script_path():
    """Path to the PreToolUse validation hook script."""
    return (
        Path(__file__).parent.parent.parent
        / "packages"
        / "claude-plugin"
        / ".claude-plugin"
        / "hooks"
        / "scripts"
        / "validate-work.py"
    )


@pytest.fixture
def temp_project_with_active_feature(tmp_path):
    """Create temp project directory with .htmlgraph and active feature."""
    graph_dir = tmp_path / ".htmlgraph"
    for collection in ["features", "bugs", "spikes", "chores", "sessions"]:
        (graph_dir / collection).mkdir(parents=True)

    feat_path = graph_dir / "features" / "feat-test-001.html"
    feat_path.write_text("""
<!DOCTYPE html>
<html>
<head><title>Test Feature</title></head>
<body>
    <article id="feat-test-001" data-type="feature" data-status="in-progress">
        <h1>Test Feature</h1>
    </article>
</body>
</html>
""")
    return tmp_path


@pytest.fixture
def temp_project_with_active_spike(tmp_path):
    """Create temp project directory with .htmlgraph and active spike."""
    graph_dir = tmp_path / ".htmlgraph"
    for collection in ["features", "bugs", "spikes", "chores", "sessions"]:
        (graph_dir / collection).mkdir(parents=True)

    spike_path = graph_dir / "spikes" / "spike-test-001.html"
    spike_path.write_text("""
<!DOCTYPE html>
<html>
<head><title>Test Spike</title></head>
<body>
    <article id="spike-test-001" data-type="spike" data-status="in-progress">
        <h1>Test Spike</h1>
    </article>
</body>
</html>
""")
    return tmp_path


@pytest.fixture
def temp_project_no_active_work(tmp_path):
    """Create temp project directory with .htmlgraph but no active work."""
    graph_dir = tmp_path / ".htmlgraph"
    for collection in ["features", "bugs", "spikes", "chores", "sessions"]:
        (graph_dir / collection).mkdir(parents=True)

    feat_path = graph_dir / "features" / "feat-test-001.html"
    feat_path.write_text("""
<!DOCTYPE html>
<html>
<head><title>Test Feature</title></head>
<body>
    <article id="feat-test-001" data-type="feature" data-status="todo">
        <h1>Test Feature</h1>
    </article>
</body>
</html>
""")
    return tmp_path


def run_hook(
    hook_script_path: Path, tool_input: dict, cwd: Path = None
) -> tuple[int, dict]:
    """Run validation hook and return (exit_code, decision)."""
    result = subprocess.run(
        ["python3", str(hook_script_path)],
        input=json.dumps(tool_input),
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    try:
        decision = json.loads(result.stdout)
    except json.JSONDecodeError:
        decision = {
            "decision": "error",
            "reason": f"Invalid JSON: {result.stdout}",
            "stderr": result.stderr,
        }

    return result.returncode, decision


# Integration Tests


class TestFullValidationFlow:
    """Test complete validation flow."""

    def test_read_always_allowed(self, hook_script_path, temp_project_no_active_work):
        """Read tools always allowed."""
        exit_code, decision = run_hook(
            hook_script_path,
            {"tool": "Read", "params": {"file_path": "src/test.py"}},
            cwd=temp_project_no_active_work,
        )
        assert exit_code == 0
        assert decision["decision"] == "allow"

    def test_direct_htmlgraph_write_denied(
        self, hook_script_path, temp_project_with_active_feature
    ):
        """Direct .htmlgraph/ writes always blocked (only blocking case)."""
        exit_code, decision = run_hook(
            hook_script_path,
            {
                "tool": "Write",
                "params": {"file_path": ".htmlgraph/features/feat-999.html"},
            },
            cwd=temp_project_with_active_feature,
        )
        assert exit_code == 1
        assert decision["decision"] == "block"
        assert (
            "direct edits" in decision["reason"].lower()
            or "blocked" in decision["reason"].lower()
        )

    def test_write_denied_no_work(self, hook_script_path, temp_project_no_active_work):
        """Write allowed with guidance when no active work."""
        exit_code, decision = run_hook(
            hook_script_path,
            {"tool": "Write", "params": {"file_path": "src/new.py"}},
            cwd=temp_project_no_active_work,
        )
        assert exit_code == 0
        assert decision["decision"] == "allow"
        # Should suggest creating a work item
        assert "suggestion" in decision or "guidance" in decision

    def test_sdk_allowed_no_work(self, hook_script_path, temp_project_no_active_work):
        """SDK commands allowed without work (creating items)."""
        exit_code, decision = run_hook(
            hook_script_path,
            {
                "tool": "Bash",
                "params": {"command": "uv run htmlgraph feature create 'Test'"},
            },
            cwd=temp_project_no_active_work,
        )
        assert exit_code == 0
        assert decision["decision"] == "allow"


class TestSpikeValidation:
    """Test validation with active spike."""

    def test_write_denied_with_spike(
        self, hook_script_path, temp_project_with_active_spike
    ):
        """Write allowed with guidance when spike active (planning only)."""
        exit_code, decision = run_hook(
            hook_script_path,
            {"tool": "Write", "params": {"file_path": "src/impl.py"}},
            cwd=temp_project_with_active_spike,
        )
        assert exit_code == 0
        assert decision["decision"] == "allow"
        # Should have guidance about spike being for planning
        assert "guidance" in decision or "suggestion" in decision

    def test_sdk_allowed_with_spike(
        self, hook_script_path, temp_project_with_active_spike
    ):
        """SDK commands allowed with spike (creating work)."""
        exit_code, decision = run_hook(
            hook_script_path,
            {
                "tool": "Bash",
                "params": {"command": "uv run htmlgraph feature create 'Task'"},
            },
            cwd=temp_project_with_active_spike,
        )
        assert exit_code == 0
        assert decision["decision"] == "allow"


class TestFeatureValidation:
    """Test validation with active feature."""

    def test_write_allowed_with_feature(
        self, hook_script_path, temp_project_with_active_feature
    ):
        """Write allowed when feature active."""
        exit_code, decision = run_hook(
            hook_script_path,
            {"tool": "Write", "params": {"file_path": "src/new.py"}},
            cwd=temp_project_with_active_feature,
        )
        assert exit_code == 0
        assert decision["decision"] == "allow"

    def test_code_bash_allowed_with_feature(
        self, hook_script_path, temp_project_with_active_feature
    ):
        """Code Bash allowed when feature active."""
        exit_code, decision = run_hook(
            hook_script_path,
            {"tool": "Bash", "params": {"command": "npm install lodash"}},
            cwd=temp_project_with_active_feature,
        )
        assert exit_code == 0
        assert decision["decision"] == "allow"


class TestEdgeCases:
    """Test edge cases."""

    def test_readonly_bash_allowed(self, hook_script_path, temp_project_no_active_work):
        """Readonly Bash always allowed."""
        for cmd in ["git status", "git diff", "ls", "uv run htmlgraph status"]:
            exit_code, decision = run_hook(
                hook_script_path,
                {"tool": "Bash", "params": {"command": cmd}},
                cwd=temp_project_no_active_work,
            )
            assert exit_code == 0, f"Failed for: {cmd}"
            assert decision["decision"] == "allow"

    def test_no_htmlgraph_denies_code_changes(self, hook_script_path):
        """Without .htmlgraph, code changes allowed with guidance (no work item)."""
        # No .htmlgraph directory = no active work
        exit_code, decision = run_hook(
            hook_script_path,
            {"tool": "Write", "params": {"file_path": "src/test.py"}},
            cwd="/tmp",
        )
        assert exit_code == 0  # Allowed with guidance
        assert decision["decision"] == "allow"
        # Should have guidance about no active work
        assert "guidance" in decision or "suggestion" in decision
