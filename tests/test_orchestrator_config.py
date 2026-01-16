"""Tests for orchestrator configuration management."""

from datetime import datetime, timedelta, timezone

import pytest
import yaml
from htmlgraph.hooks.validator import get_anti_patterns
from htmlgraph.orchestrator_config import (
    OrchestratorConfig,
    collapse_rapid_sequences,
    filter_recent_violations,
    format_config_display,
    get_config_paths,
    get_config_value,
    get_effective_violation_count,
    load_orchestrator_config,
    save_orchestrator_config,
    set_config_value,
)


def test_default_config():
    """Test default configuration values."""
    config = OrchestratorConfig()

    # Check thresholds
    assert config.thresholds.exploration_calls == 5
    assert (
        config.thresholds.circuit_breaker_violations == 3
    )  # Updated to match actual default
    assert config.thresholds.violation_decay_seconds == 120
    assert (
        config.thresholds.rapid_sequence_window == 0
    )  # Updated to match actual default (disabled)

    # Check anti-patterns
    assert config.anti_patterns.consecutive_bash == 5
    assert config.anti_patterns.consecutive_edit == 4
    assert config.anti_patterns.consecutive_grep == 4
    assert config.anti_patterns.consecutive_read == 5


def test_load_save_config(tmp_path):
    """Test loading and saving configuration."""
    config_path = tmp_path / "orchestrator-config.yaml"

    # Create custom config
    config = OrchestratorConfig()
    config.thresholds.exploration_calls = 7
    config.thresholds.circuit_breaker_violations = 8

    # Save
    save_orchestrator_config(config, config_path)
    assert config_path.exists()

    # Load
    with open(config_path) as f:
        data = yaml.safe_load(f)

    assert data["thresholds"]["exploration_calls"] == 7
    assert data["thresholds"]["circuit_breaker_violations"] == 8


def test_get_set_config_value():
    """Test getting and setting config values by path."""
    config = OrchestratorConfig()

    # Get value
    value = get_config_value(config, "thresholds.exploration_calls")
    assert value == 5

    # Set value
    set_config_value(config, "thresholds.exploration_calls", 10)
    assert config.thresholds.exploration_calls == 10

    # Nested value
    set_config_value(config, "anti_patterns.consecutive_bash", 7)
    assert config.anti_patterns.consecutive_bash == 7


def test_get_config_value_invalid_path():
    """Test getting invalid config path raises error."""
    config = OrchestratorConfig()

    with pytest.raises(KeyError):
        get_config_value(config, "invalid.path")


def test_set_config_value_invalid_path():
    """Test setting invalid config path raises error."""
    config = OrchestratorConfig()

    with pytest.raises(KeyError):
        set_config_value(config, "invalid.path", 10)


def test_filter_recent_violations():
    """Test time-based violation filtering."""
    now = datetime.now(timezone.utc)

    violations = [
        {"timestamp": (now - timedelta(seconds=30)).isoformat(), "tool": "Edit"},
        {"timestamp": (now - timedelta(seconds=90)).isoformat(), "tool": "Read"},
        {
            "timestamp": (now - timedelta(seconds=150)).isoformat(),
            "tool": "Bash",
        },  # Old
        {
            "timestamp": (now - timedelta(seconds=200)).isoformat(),
            "tool": "Grep",
        },  # Old
    ]

    # Filter with 120 second window
    recent = filter_recent_violations(violations, 120)

    # Should only keep violations within 120 seconds
    assert len(recent) == 2
    assert recent[0]["tool"] == "Edit"
    assert recent[1]["tool"] == "Read"


def test_filter_recent_violations_timestamp_formats():
    """Test filtering works with different timestamp formats."""
    now = datetime.now(timezone.utc)

    violations = [
        {"timestamp": now.isoformat(), "tool": "Edit"},  # ISO string
        {"timestamp": now.timestamp(), "tool": "Read"},  # Float timestamp
        {
            "timestamp": (now - timedelta(seconds=200)).isoformat(),
            "tool": "Bash",
        },  # Old
    ]

    recent = filter_recent_violations(violations, 120)
    assert len(recent) == 2


def test_collapse_rapid_sequences():
    """Test collapsing rapid violation sequences."""
    now = datetime.now(timezone.utc)

    violations = [
        {"timestamp": (now - timedelta(seconds=50)).isoformat(), "tool": "Edit"},
        {
            "timestamp": (now - timedelta(seconds=45)).isoformat(),
            "tool": "Edit",
        },  # Rapid
        {
            "timestamp": (now - timedelta(seconds=43)).isoformat(),
            "tool": "Edit",
        },  # Rapid
        {
            "timestamp": (now - timedelta(seconds=20)).isoformat(),
            "tool": "Read",
        },  # After gap
    ]

    # Collapse with 10 second window
    collapsed = collapse_rapid_sequences(violations, 10)

    # Should collapse the 3 rapid edits into 1, keep the read
    assert len(collapsed) == 2
    assert collapsed[0]["tool"] == "Edit"
    assert collapsed[1]["tool"] == "Read"


def test_collapse_rapid_sequences_empty():
    """Test collapsing with empty list."""
    collapsed = collapse_rapid_sequences([], 10)
    assert len(collapsed) == 0


def test_get_effective_violation_count():
    """Test effective violation count with decay and collapsing."""
    config = OrchestratorConfig()
    # Enable rapid sequence collapsing for this test
    config.thresholds.rapid_sequence_window = 10
    now = datetime.now(timezone.utc)

    violations = [
        # Recent cluster (should collapse to 1)
        {"timestamp": (now - timedelta(seconds=30)).isoformat(), "tool": "Edit"},
        {"timestamp": (now - timedelta(seconds=28)).isoformat(), "tool": "Edit"},
        {"timestamp": (now - timedelta(seconds=26)).isoformat(), "tool": "Edit"},
        # Recent separate violation
        {"timestamp": (now - timedelta(seconds=10)).isoformat(), "tool": "Read"},
        # Old violation (should be filtered out)
        {"timestamp": (now - timedelta(seconds=200)).isoformat(), "tool": "Bash"},
    ]

    effective = get_effective_violation_count(violations, config)

    # Should be 2: collapsed cluster + separate violation
    assert effective == 2


def test_get_anti_patterns_from_config():
    """Test generating anti-pattern rules from config."""
    config = OrchestratorConfig()
    config.anti_patterns.consecutive_bash = 3
    config.anti_patterns.consecutive_edit = 2

    patterns = get_anti_patterns(config)

    # Check bash pattern
    bash_pattern = tuple(["Bash"] * 3)
    assert bash_pattern in patterns
    assert "3 consecutive Bash" in patterns[bash_pattern]

    # Check edit pattern
    edit_pattern = tuple(["Edit"] * 2)
    assert edit_pattern in patterns
    assert "2 consecutive Edits" in patterns[edit_pattern]


def test_format_config_display():
    """Test config formatting for display."""
    config = OrchestratorConfig()
    output = format_config_display(config)

    assert "HtmlGraph Orchestrator Configuration" in output
    assert "exploration_calls: 5" in output
    assert "circuit_breaker_violations: 3" in output  # Updated to match actual default
    assert "violation_decay_seconds: 120" in output


def test_load_orchestrator_config_defaults(tmp_path, monkeypatch):
    """Test loading config returns defaults when no file exists."""
    # Mock config paths to use tmp directory
    monkeypatch.setattr(
        "htmlgraph.orchestrator_config.get_config_paths",
        lambda: [tmp_path / "orchestrator-config.yaml"],
    )

    config = load_orchestrator_config()

    # Should return defaults
    assert config.thresholds.exploration_calls == 5
    assert (
        config.thresholds.circuit_breaker_violations == 3
    )  # Updated to match actual default


def test_load_orchestrator_config_from_file(tmp_path, monkeypatch):
    """Test loading config from file."""
    config_path = tmp_path / "orchestrator-config.yaml"

    # Create config file
    data = {
        "thresholds": {
            "exploration_calls": 10,
            "circuit_breaker_violations": 8,
            "violation_decay_seconds": 180,
            "rapid_sequence_window": 15,
        },
        "anti_patterns": {
            "consecutive_bash": 6,
            "consecutive_edit": 5,
            "consecutive_grep": 5,
            "consecutive_read": 6,
        },
        "modes": {
            "strict": {
                "block_after_violations": True,
                "require_work_items": True,
                "warn_on_patterns": True,
            },
            "moderate": {
                "block_after_violations": False,
                "require_work_items": False,
                "warn_on_patterns": True,
            },
            "guidance": {
                "block_after_violations": False,
                "require_work_items": False,
                "warn_on_patterns": False,
            },
        },
    }

    with open(config_path, "w") as f:
        yaml.dump(data, f)

    # Mock config paths
    monkeypatch.setattr(
        "htmlgraph.orchestrator_config.get_config_paths", lambda: [config_path]
    )

    config = load_orchestrator_config()

    # Check loaded values
    assert config.thresholds.exploration_calls == 10
    assert config.thresholds.circuit_breaker_violations == 8
    assert config.anti_patterns.consecutive_bash == 6


def test_config_paths():
    """Test config path priority."""
    paths = get_config_paths()

    # Should have project-specific and user paths
    assert len(paths) >= 2
    assert ".htmlgraph" in str(paths[0])  # Project-specific
    assert ".config/htmlgraph" in str(paths[1])  # User default


def test_violation_decay_edge_cases():
    """Test edge cases in violation decay."""
    now = datetime.now(timezone.utc)

    # Test with violation exactly at boundary
    violations = [
        {"timestamp": (now - timedelta(seconds=120)).isoformat(), "tool": "Edit"},
    ]

    recent = filter_recent_violations(violations, 120)
    # Boundary case: should be filtered out (older than cutoff)
    assert len(recent) == 0


def test_rapid_sequence_window_edge_cases():
    """Test edge cases in rapid sequence collapsing."""
    now = datetime.now(timezone.utc)

    violations = [
        {"timestamp": (now - timedelta(seconds=20)).isoformat(), "tool": "Edit"},
        {
            "timestamp": (now - timedelta(seconds=10)).isoformat(),
            "tool": "Edit",
        },  # Exactly at window
    ]

    collapsed = collapse_rapid_sequences(violations, 10)
    # At boundary (10s gap): should be collapsed since gap <= 10s
    # The implementation collapses when diff <= window
    assert len(collapsed) == 1


def test_invalid_timestamp_handling():
    """Test handling of invalid timestamps."""
    violations = [
        {"timestamp": "invalid", "tool": "Edit"},
        {"timestamp": datetime.now(timezone.utc).isoformat(), "tool": "Read"},
    ]

    # Should skip invalid timestamps gracefully
    recent = filter_recent_violations(violations, 120)
    assert len(recent) == 1
    assert recent[0]["tool"] == "Read"


def test_model_dump_compatibility():
    """Test Pydantic model serialization."""
    config = OrchestratorConfig()
    data = config.model_dump()

    assert "thresholds" in data
    assert "anti_patterns" in data
    assert "modes" in data
    assert data["thresholds"]["exploration_calls"] == 5
