"""
Tests for Pre-Work Validation Hook (validate-work.py)

Tests the validation logic that enforces HtmlGraph workflow before code changes.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the validation functions (validate-work.py has hyphen, so use importlib)
import sys
import importlib.util
from pathlib import Path

# Load validate-work.py module
script_path = Path(__file__).parent.parent.parent / "packages" / "claude-plugin" / "hooks" / "scripts" / "validate-work.py"
spec = importlib.util.spec_from_file_location("validate_work", script_path)
validate_work = importlib.util.module_from_spec(spec)
sys.modules["validate_work"] = validate_work
spec.loader.exec_module(validate_work)

# Import functions
load_validation_config = validate_work.load_validation_config
is_always_allowed = validate_work.is_always_allowed
is_direct_htmlgraph_write = validate_work.is_direct_htmlgraph_write
is_sdk_command = validate_work.is_sdk_command
is_code_operation = validate_work.is_code_operation
validate_tool_call = validate_work.validate_tool_call


@pytest.fixture
def config():
    """Load validation config for tests."""
    return load_validation_config()


@pytest.fixture
def mock_no_active_work():
    """Mock SDK to return no active work item."""
    with patch('validate_work.get_active_work_item', return_value=None):
        yield


@pytest.fixture
def mock_spike_active():
    """Mock SDK to return active spike."""
    with patch('validate_work.get_active_work_item', return_value={
        "id": "spike-test-123",
        "type": "spike",
        "title": "Test Spike",
        "status": "in-progress"
    }):
        yield


@pytest.fixture
def mock_feature_active():
    """Mock SDK to return active feature."""
    with patch('validate_work.get_active_work_item', return_value={
        "id": "feat-test-456",
        "type": "feature",
        "title": "Test Feature",
        "status": "in-progress"
    }):
        yield


class TestAlwaysAllowed:
    """Test always-allowed operations (Read, Glob, Grep, LSP, read-only Bash)."""

    def test_read_tool_always_allowed(self, config):
        """Read tool should always be allowed."""
        assert is_always_allowed("Read", {"file_path": "src/test.py"}, config)

    def test_glob_tool_always_allowed(self, config):
        """Glob tool should always be allowed."""
        assert is_always_allowed("Glob", {"pattern": "**/*.py"}, config)

    def test_grep_tool_always_allowed(self, config):
        """Grep tool should always be allowed."""
        assert is_always_allowed("Grep", {"pattern": "test"}, config)

    def test_lsp_tool_always_allowed(self, config):
        """LSP tool should always be allowed."""
        assert is_always_allowed("LSP", {}, config)

    def test_readonly_bash_allowed(self, config):
        """Read-only Bash commands should be allowed."""
        readonly_commands = [
            "git status",
            "git diff",
            "ls -la",
            "cat file.txt",
            "uv run htmlgraph status"
        ]
        for cmd in readonly_commands:
            assert is_always_allowed("Bash", {"command": cmd}, config), f"Failed for: {cmd}"

    def test_write_tool_not_always_allowed(self, config):
        """Write tool should NOT be in always-allowed list."""
        assert not is_always_allowed("Write", {"file_path": "test.py"}, config)


class TestDirectHtmlGraphWrites:
    """Test detection of direct writes to .htmlgraph/ (always denied)."""

    def test_write_to_htmlgraph_detected(self):
        """Direct Write to .htmlgraph/ should be detected."""
        is_denied, path = is_direct_htmlgraph_write("Write", {
            "file_path": ".htmlgraph/features/feat-123.html"
        })
        assert is_denied
        assert ".htmlgraph/" in path

    def test_edit_to_htmlgraph_detected(self):
        """Direct Edit to .htmlgraph/ should be detected."""
        is_denied, _ = is_direct_htmlgraph_write("Edit", {
            "file_path": ".htmlgraph/sessions/sess-abc.html"
        })
        assert is_denied

    def test_delete_to_htmlgraph_detected(self):
        """Direct Delete to .htmlgraph/ should be detected."""
        is_denied, _ = is_direct_htmlgraph_write("Delete", {
            "file_path": ".htmlgraph/bugs/bug-001.html"
        })
        assert is_denied

    def test_write_to_src_not_htmlgraph(self):
        """Write to src/ should NOT be detected as .htmlgraph/ write."""
        is_denied, _ = is_direct_htmlgraph_write("Write", {
            "file_path": "src/python/htmlgraph/models.py"
        })
        assert not is_denied

    def test_read_htmlgraph_allowed(self):
        """Read from .htmlgraph/ should NOT be flagged."""
        is_denied, _ = is_direct_htmlgraph_write("Read", {
            "file_path": ".htmlgraph/features/feat-123.html"
        })
        assert not is_denied


class TestSDKCommands:
    """Test SDK command detection."""

    def test_uv_run_htmlgraph_detected(self, config):
        """uv run htmlgraph commands should be detected as SDK."""
        assert is_sdk_command("Bash", {
            "command": "uv run htmlgraph feature create 'Test'"
        }, config)

    def test_htmlgraph_direct_detected(self, config):
        """Direct htmlgraph commands should be detected as SDK."""
        assert is_sdk_command("Bash", {
            "command": "htmlgraph status"
        }, config)

    def test_non_sdk_bash_not_detected(self, config):
        """Non-SDK Bash commands should NOT be detected as SDK."""
        assert not is_sdk_command("Bash", {
            "command": "npm install"
        }, config)

    def test_write_tool_not_sdk(self, config):
        """Write tool should NOT be detected as SDK command."""
        assert not is_sdk_command("Write", {
            "file_path": "test.py"
        }, config)


class TestCodeOperations:
    """Test code operation detection."""

    def test_write_is_code_operation(self, config):
        """Write tool should be detected as code operation."""
        assert is_code_operation("Write", {"file_path": "src/test.py"}, config)

    def test_edit_is_code_operation(self, config):
        """Edit tool should be detected as code operation."""
        assert is_code_operation("Edit", {"file_path": "test.py"}, config)

    def test_delete_is_code_operation(self, config):
        """Delete tool should be detected as code operation."""
        assert is_code_operation("Delete", {"file_path": "old.py"}, config)

    def test_code_bash_detected(self, config):
        """Code-modifying Bash should be detected."""
        code_commands = [
            "npm install",
            "git commit -m 'test'",
            "uv build",
            "python setup.py"
        ]
        for cmd in code_commands:
            assert is_code_operation("Bash", {"command": cmd}, config), f"Failed for: {cmd}"

    def test_readonly_bash_not_code_operation(self, config):
        """Read-only Bash should NOT be code operation."""
        assert not is_code_operation("Bash", {"command": "git status"}, config)


class TestValidationLogicNoActiveWork:
    """Test validation with no active work item."""

    def test_read_allowed_no_work(self, config, mock_no_active_work):
        """Read should be allowed with no active work."""
        decision = validate_tool_call("Read", {"file_path": "test.py"}, config)
        assert decision["decision"] == "allow"

    def test_sdk_command_allowed_no_work(self, config, mock_no_active_work):
        """SDK commands should be allowed with no active work (creating work items)."""
        decision = validate_tool_call("Bash", {
            "command": "uv run htmlgraph feature create 'Test'"
        }, config)
        assert decision["decision"] == "allow"

    def test_write_denied_no_work(self, config, mock_no_active_work):
        """Write should be denied with no active work."""
        decision = validate_tool_call("Write", {"file_path": "src/test.py"}, config)
        assert decision["decision"] == "deny"
        assert "suggestion" in decision

    def test_code_bash_denied_no_work(self, config, mock_no_active_work):
        """Code-modifying Bash should be denied with no active work."""
        decision = validate_tool_call("Bash", {"command": "git commit -m 'test'"}, config)
        assert decision["decision"] == "deny"


class TestValidationLogicSpikeActive:
    """Test validation with active spike (planning only)."""

    def test_read_allowed_with_spike(self, config, mock_spike_active):
        """Read should be allowed with spike active."""
        decision = validate_tool_call("Read", {"file_path": "test.py"}, config)
        assert decision["decision"] == "allow"

    def test_sdk_command_allowed_with_spike(self, config, mock_spike_active):
        """SDK commands should be allowed with spike (creating work items)."""
        decision = validate_tool_call("Bash", {
            "command": "uv run htmlgraph feature create 'Implementation'"
        }, config)
        assert decision["decision"] == "allow"
        assert "spike" in decision["reason"].lower()

    def test_write_denied_with_spike(self, config, mock_spike_active):
        """Write should be denied with spike active (planning only)."""
        decision = validate_tool_call("Write", {"file_path": "src/test.py"}, config)
        assert decision["decision"] == "deny"
        assert "spike" in decision["reason"].lower()
        assert "suggestion" in decision

    def test_edit_denied_with_spike(self, config, mock_spike_active):
        """Edit should be denied with spike active."""
        decision = validate_tool_call("Edit", {"file_path": "packages/test.py"}, config)
        assert decision["decision"] == "deny"

    def test_code_bash_denied_with_spike(self, config, mock_spike_active):
        """Code-modifying Bash should be denied with spike active."""
        decision = validate_tool_call("Bash", {"command": "npm install react"}, config)
        assert decision["decision"] == "deny"
        assert "spike" in decision["reason"].lower()


class TestValidationLogicFeatureActive:
    """Test validation with active feature (implementation work)."""

    def test_read_allowed_with_feature(self, config, mock_feature_active):
        """Read should be allowed with feature active."""
        decision = validate_tool_call("Read", {"file_path": "test.py"}, config)
        assert decision["decision"] == "allow"

    def test_write_allowed_with_feature(self, config, mock_feature_active):
        """Write should be allowed with feature active."""
        decision = validate_tool_call("Write", {"file_path": "src/new_file.py"}, config)
        assert decision["decision"] == "allow"
        assert "feat-test-456" in decision["reason"]

    def test_edit_allowed_with_feature(self, config, mock_feature_active):
        """Edit should be allowed with feature active."""
        decision = validate_tool_call("Edit", {"file_path": "packages/test.py"}, config)
        assert decision["decision"] == "allow"

    def test_code_bash_allowed_with_feature(self, config, mock_feature_active):
        """Code-modifying Bash should be allowed with feature active."""
        decision = validate_tool_call("Bash", {"command": "uv build"}, config)
        assert decision["decision"] == "allow"

    def test_sdk_command_allowed_with_feature(self, config, mock_feature_active):
        """SDK commands should be allowed with feature active."""
        decision = validate_tool_call("Bash", {
            "command": "uv run htmlgraph status"
        }, config)
        assert decision["decision"] == "allow"


class TestAlwaysDenyHtmlGraphWrites:
    """Test that direct .htmlgraph/ writes are ALWAYS denied (even with feature active)."""

    def test_write_htmlgraph_denied_with_feature(self, config, mock_feature_active):
        """Direct Write to .htmlgraph/ should be denied even with feature active."""
        decision = validate_tool_call("Write", {
            "file_path": ".htmlgraph/features/feat-999.html"
        }, config)
        assert decision["decision"] == "deny"
        assert "sdk" in decision["reason"].lower() or "direct" in decision["reason"].lower()

    def test_edit_htmlgraph_denied_with_spike(self, config, mock_spike_active):
        """Direct Edit to .htmlgraph/ should be denied even with spike active."""
        decision = validate_tool_call("Edit", {
            "file_path": ".htmlgraph/sessions/sess-xyz.html"
        }, config)
        assert decision["decision"] == "deny"

    def test_delete_htmlgraph_denied_no_work(self, config, mock_no_active_work):
        """Direct Delete to .htmlgraph/ should be denied with no work."""
        decision = validate_tool_call("Delete", {
            "file_path": ".htmlgraph/bugs/bug-001.html"
        }, config)
        assert decision["decision"] == "deny"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_tool_allowed(self, config, mock_no_active_work):
        """Unknown tools should default to allow (graceful degradation)."""
        decision = validate_tool_call("UnknownTool", {}, config)
        # Should not crash, may allow or deny based on logic
        assert "decision" in decision

    def test_empty_params(self, config, mock_no_active_work):
        """Empty params should not crash."""
        decision = validate_tool_call("Write", {}, config)
        assert "decision" in decision

    def test_config_missing_templates(self):
        """Should handle missing config templates gracefully."""
        minimal_config = {"always_allow": {"tools": ["Read"]}}
        decision = validate_tool_call("Read", {}, minimal_config)
        assert decision["decision"] == "allow"
