"""Tests for PostToolUseFailure hook."""

import json
from unittest.mock import MagicMock, patch

import pytest
from htmlgraph.hooks.post_tool_use_failure import (
    create_debug_spike,
    run,
    should_create_debug_spike,
)


@pytest.fixture
def mock_htmlgraph_dir(tmp_path, monkeypatch):
    """Create temporary .htmlgraph directory."""
    htmlgraph_dir = tmp_path / ".htmlgraph"
    htmlgraph_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    return htmlgraph_dir


def test_error_logging(mock_htmlgraph_dir):
    """Test that errors are logged to file."""
    hook_input = {
        "name": "Bash",
        "result": {"error": "Command failed with exit code 1"},
        "session_id": "test-session",
    }

    result = run(hook_input)

    assert result["continue"] is True

    error_log = mock_htmlgraph_dir / "errors.jsonl"
    assert error_log.exists()

    with open(error_log) as f:
        logged = json.loads(f.read())
        assert logged["tool"] == "Bash"
        assert "Command failed" in logged["error"]
        assert logged["session_id"] == "test-session"
        assert "timestamp" in logged


def test_error_logging_with_name_field(mock_htmlgraph_dir):
    """Test that errors are logged when using PostToolUse format with result.error."""
    hook_input = {
        "name": "Read",
        "result": {"error": "File not found"},
        "session_id": "test-session-2",
    }

    result = run(hook_input)

    assert result["continue"] is True

    error_log = mock_htmlgraph_dir / "errors.jsonl"
    assert error_log.exists()

    with open(error_log) as f:
        logged = json.loads(f.read())
        assert logged["tool"] == "Read"
        assert "File not found" in logged["error"]


def test_pattern_detection(mock_htmlgraph_dir):
    """Test that recurring errors are detected."""
    error_log = mock_htmlgraph_dir / "errors.jsonl"

    # Create 3 occurrences of same error
    for i in range(3):
        with open(error_log, "a") as f:
            f.write(
                json.dumps(
                    {
                        "tool": "Bash",
                        "error": "git command failed with exit code 128",
                        "timestamp": f"2025-01-01T00:00:0{i}Z",
                    }
                )
                + "\n"
            )

    # Should detect pattern
    assert should_create_debug_spike(
        "Bash", "git command failed with exit code 128", error_log
    )

    # Should not detect different error
    assert not should_create_debug_spike("Read", "file not found", error_log)

    # Should not detect different tool
    assert not should_create_debug_spike(
        "Edit", "git command failed with exit code 128", error_log
    )


def test_pattern_detection_partial_match(mock_htmlgraph_dir):
    """Test that pattern detection uses first 100 chars for matching."""
    error_log = mock_htmlgraph_dir / "errors.jsonl"

    base_error = "x" * 100 + " different suffix 1"

    # Create 3 occurrences with same prefix (first 100 chars)
    for suffix in ["suffix 1", "suffix 2", "suffix 3"]:
        with open(error_log, "a") as f:
            f.write(
                json.dumps({"tool": "Test", "error": "x" * 100 + f" {suffix}"}) + "\n"
            )

    # Should detect pattern based on first 100 chars
    assert should_create_debug_spike("Test", base_error, error_log)


def test_no_pattern_with_insufficient_occurrences(mock_htmlgraph_dir):
    """Test that pattern is not detected with fewer than 3 occurrences."""
    error_log = mock_htmlgraph_dir / "errors.jsonl"

    # Create only 2 occurrences
    for i in range(2):
        with open(error_log, "a") as f:
            f.write(
                json.dumps(
                    {"tool": "Bash", "error": "git command failed", "timestamp": "..."}
                )
                + "\n"
            )

    # Should not detect pattern (need 3+)
    assert not should_create_debug_spike("Bash", "git command failed", error_log)


@patch("htmlgraph.SDK")
def test_spike_creation(mock_sdk_class, mock_htmlgraph_dir):
    """Test that debug spikes are created for recurring errors."""
    # Setup mock SDK
    mock_spike = MagicMock()
    mock_spike.id = "spk-test-123"
    mock_spike.set_spike_type.return_value = mock_spike
    mock_spike.set_findings.return_value = mock_spike
    mock_spike.save.return_value = mock_spike

    mock_sdk = MagicMock()
    mock_sdk.spikes.create.return_value = mock_spike
    mock_sdk_class.return_value = mock_sdk

    # Create error log with 3 occurrences
    error_log = mock_htmlgraph_dir / "errors.jsonl"
    for i in range(3):
        with open(error_log, "a") as f:
            f.write(
                json.dumps(
                    {
                        "tool": "Bash",
                        "error": "test error message",
                        "timestamp": f"2025-01-01T00:00:0{i}Z",
                        "session_id": f"session-{i}",
                    }
                )
                + "\n"
            )

    # Create spike
    create_debug_spike("Bash", "test error message", error_log)

    # Verify SDK was called correctly
    mock_sdk_class.assert_called_once_with(agent="error-tracker")
    mock_sdk.spikes.create.assert_called_once_with("Recurring Error: Bash")
    mock_spike.set_spike_type.assert_called_once_with("technical")
    assert mock_spike.set_findings.called
    mock_spike.save.assert_called_once()

    # Verify findings content
    findings = mock_spike.set_findings.call_args[0][0]
    assert "Recurring Tool Failure Detected" in findings
    assert "Tool**: Bash" in findings
    assert "Occurrences**: 3" in findings
    assert "test error message" in findings


@patch("htmlgraph.SDK")
def test_spike_creation_deduplication(mock_sdk_class, mock_htmlgraph_dir):
    """Test that duplicate spikes are not created for the same error."""
    # Setup mock SDK
    mock_spike = MagicMock()
    mock_spike.id = "spk-test-456"
    mock_spike.set_spike_type.return_value = mock_spike
    mock_spike.set_findings.return_value = mock_spike
    mock_spike.save.return_value = mock_spike

    mock_sdk = MagicMock()
    mock_sdk.spikes.create.return_value = mock_spike
    mock_sdk_class.return_value = mock_sdk

    # Create error log with proper structure
    error_log = mock_htmlgraph_dir / "errors.jsonl"
    with open(error_log, "a") as f:
        f.write(
            json.dumps(
                {
                    "tool": "Bash",
                    "error": "test error",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "session_id": "test",
                }
            )
            + "\n"
        )

    # Create first spike
    create_debug_spike("Bash", "test error", error_log)
    assert mock_sdk.spikes.create.call_count == 1

    # Try to create spike again for same error
    create_debug_spike("Bash", "test error", error_log)

    # Should not create duplicate
    assert mock_sdk.spikes.create.call_count == 1


def test_error_logging_with_missing_fields(mock_htmlgraph_dir):
    """Test that hook handles missing fields gracefully."""
    hook_input = {}  # Empty input

    result = run(hook_input)

    assert result["continue"] is True

    error_log = mock_htmlgraph_dir / "errors.jsonl"
    assert error_log.exists()

    with open(error_log) as f:
        logged = json.loads(f.read())
        assert logged["tool"] == "unknown"
        assert logged["error"] == "No error message"
        assert logged["session_id"] == "unknown"


def test_hook_never_blocks(mock_htmlgraph_dir):
    """Test that hook always returns continue=True, even on internal errors."""
    # Test with invalid JSON in error log (should handle gracefully)
    error_log = mock_htmlgraph_dir / "errors.jsonl"
    with open(error_log, "w") as f:
        f.write("invalid json\n")

    hook_input = {
        "name": "Bash",
        "result": {"error": "test error"},
        "session_id": "test",
    }

    result = run(hook_input)

    # Should still return continue=True
    assert result["continue"] is True


def test_integration_with_auto_spike_creation(mock_htmlgraph_dir):
    """Test full integration: logging -> pattern detection -> spike creation."""
    with patch("htmlgraph.SDK") as mock_sdk_class:
        # Setup mock
        mock_spike = MagicMock()
        mock_spike.id = "spk-integration-test"
        mock_spike.set_spike_type.return_value = mock_spike
        mock_spike.set_findings.return_value = mock_spike
        mock_spike.save.return_value = mock_spike

        mock_sdk = MagicMock()
        mock_sdk.spikes.create.return_value = mock_spike
        mock_sdk_class.return_value = mock_sdk

        hook_input = {
            "name": "Edit",
            "result": {"error": "Pattern matching failed"},
            "session_id": "integration-test",
        }

        # First two calls - no spike created
        run(hook_input)
        run(hook_input)
        assert not mock_sdk.spikes.create.called

        # Third call - spike should be created
        run(hook_input)
        assert mock_sdk.spikes.create.called


def test_error_log_creates_directory(tmp_path, monkeypatch):
    """Test that .htmlgraph directory is created if it doesn't exist."""
    monkeypatch.chdir(tmp_path)

    hook_input = {
        "name": "Test",
        "result": {"error": "test error"},
        "session_id": "test",
    }

    run(hook_input)

    # Directory should be created
    assert (tmp_path / ".htmlgraph").exists()
    assert (tmp_path / ".htmlgraph" / "errors.jsonl").exists()
