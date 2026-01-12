"""
Orchestrator Configuration Management

Provides configurable thresholds for delegation enforcement instead of hardcoded values.
Supports:
- Threshold configuration (exploration, circuit breaker)
- Time-based violation decay
- Rapid sequence collapsing
- CLI commands to view/edit config
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel


class ThresholdsConfig(BaseModel):
    """Threshold configuration for orchestrator enforcement."""

    exploration_calls: int = 5
    """How many consecutive Grep/Read/Glob calls before warning."""

    circuit_breaker_violations: int = 3
    """How many violations before blocking all operations."""

    violation_decay_seconds: int = 120
    """How old violations can be before they don't count (seconds)."""

    rapid_sequence_window: int = 0
    """Time window for collapsing rapid violations (seconds). 0 = disabled."""


class AntiPatternsConfig(BaseModel):
    """Anti-pattern detection thresholds."""

    consecutive_bash: int = 5
    consecutive_edit: int = 4
    consecutive_grep: int = 4
    consecutive_read: int = 5


class ModeConfig(BaseModel):
    """Configuration for an enforcement mode."""

    block_after_violations: bool = True
    require_work_items: bool = True
    warn_on_patterns: bool = True


class ModesConfig(BaseModel):
    """All enforcement mode configurations."""

    strict: ModeConfig = ModeConfig(
        block_after_violations=True,
        require_work_items=True,
        warn_on_patterns=True,
    )
    moderate: ModeConfig = ModeConfig(
        block_after_violations=False,
        require_work_items=False,
        warn_on_patterns=True,
    )
    guidance: ModeConfig = ModeConfig(
        block_after_violations=False,
        require_work_items=False,
        warn_on_patterns=False,
    )


class OrchestratorConfig(BaseModel):
    """Complete orchestrator configuration."""

    thresholds: ThresholdsConfig = ThresholdsConfig()
    anti_patterns: AntiPatternsConfig = AntiPatternsConfig()
    modes: ModesConfig = ModesConfig()


def get_config_paths() -> list[Path]:
    """
    Get list of config file paths to check (in priority order).

    Returns:
        List of paths to check for config file
    """
    return [
        Path.cwd() / ".htmlgraph" / "orchestrator-config.yaml",
        Path.home() / ".config" / "htmlgraph" / "orchestrator-config.yaml",
    ]


def load_orchestrator_config() -> OrchestratorConfig:
    """
    Load orchestrator configuration from file or use defaults.

    Checks multiple locations:
    1. .htmlgraph/orchestrator-config.yaml (project-specific)
    2. ~/.config/htmlgraph/orchestrator-config.yaml (user defaults)

    Returns:
        OrchestratorConfig with loaded or default values
    """
    for config_path in get_config_paths():
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = yaml.safe_load(f)
                    if data:
                        return OrchestratorConfig(**data)
            except Exception:
                # If file is corrupted, continue to next location
                pass

    # No valid config found, return defaults
    return OrchestratorConfig()


def save_orchestrator_config(
    config: OrchestratorConfig, path: Path | None = None
) -> None:
    """
    Save orchestrator configuration to file.

    Args:
        config: Configuration to save
        path: Optional path to save to. If None, uses first config path.
    """
    if path is None:
        path = get_config_paths()[0]

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict for YAML serialization
    data = config.model_dump()

    # Write YAML with comments
    with open(path, "w") as f:
        f.write("# HtmlGraph Orchestrator Configuration\n")
        f.write("# Controls delegation enforcement behavior\n\n")
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def filter_recent_violations(
    violations: list[dict[str, Any]], decay_seconds: int
) -> list[dict[str, Any]]:
    """
    Filter violations to only include recent ones within decay window.

    Args:
        violations: List of violation dicts with 'timestamp' field
        decay_seconds: How old violations can be (in seconds)

    Returns:
        Filtered list of recent violations only
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=decay_seconds)

    recent = []
    for v in violations:
        try:
            # Parse timestamp (handle both ISO format and timestamp float)
            ts = v.get("timestamp")
            if isinstance(ts, str):
                violation_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            elif isinstance(ts, (int, float)):
                violation_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                continue

            if violation_time > cutoff:
                recent.append(v)
        except Exception:
            # Skip violations with invalid timestamps
            continue

    return recent


def collapse_rapid_sequences(
    violations: list[dict[str, Any]], window_seconds: int
) -> list[dict[str, Any]]:
    """
    Collapse violations within rapid sequence window to one.

    This prevents "violation spam" when user makes multiple rapid mistakes.

    Args:
        violations: List of violation dicts with 'timestamp' field
        window_seconds: Time window for collapsing (seconds)

    Returns:
        Collapsed list where rapid sequences count as one
    """
    if not violations:
        return []

    collapsed = [violations[0]]

    for v in violations[1:]:
        try:
            # Get timestamps
            last_ts = collapsed[-1].get("timestamp")
            curr_ts = v.get("timestamp")

            # Parse timestamps
            if isinstance(last_ts, str):
                last_time = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            elif isinstance(last_ts, (int, float)):
                last_time = datetime.fromtimestamp(last_ts, tz=timezone.utc)
            else:
                collapsed.append(v)
                continue

            if isinstance(curr_ts, str):
                curr_time = datetime.fromisoformat(curr_ts.replace("Z", "+00:00"))
            elif isinstance(curr_ts, (int, float)):
                curr_time = datetime.fromtimestamp(curr_ts, tz=timezone.utc)
            else:
                collapsed.append(v)
                continue

            # Only add if outside rapid sequence window
            if (curr_time - last_time).total_seconds() > window_seconds:
                collapsed.append(v)
        except Exception:
            # On error, include the violation
            collapsed.append(v)

    return collapsed


def get_effective_violation_count(
    violations: list[dict[str, Any]], config: OrchestratorConfig
) -> int:
    """
    Get effective violation count after applying decay and collapsing.

    Args:
        violations: Raw list of all violations
        config: Configuration with thresholds

    Returns:
        Effective violation count (after decay and collapsing)
    """
    # Apply time-based decay
    recent = filter_recent_violations(
        violations, config.thresholds.violation_decay_seconds
    )

    # Collapse rapid sequences
    collapsed = collapse_rapid_sequences(
        recent, config.thresholds.rapid_sequence_window
    )

    return len(collapsed)


def get_config_value(config: OrchestratorConfig, key_path: str) -> Any:
    """
    Get a config value by dot-separated path.

    Args:
        config: Configuration object
        key_path: Dot-separated path (e.g., "thresholds.exploration_calls")

    Returns:
        Value at that path

    Raises:
        KeyError: If path doesn't exist
    """
    parts = key_path.split(".")
    value: Any = config

    for part in parts:
        if hasattr(value, part):
            value = getattr(value, part)
        else:
            raise KeyError(f"Config path not found: {key_path}")

    return value


def set_config_value(config: OrchestratorConfig, key_path: str, value: Any) -> None:
    """
    Set a config value by dot-separated path.

    Args:
        config: Configuration object to modify
        key_path: Dot-separated path (e.g., "thresholds.exploration_calls")
        value: Value to set

    Raises:
        KeyError: If path doesn't exist
    """
    parts = key_path.split(".")
    obj: Any = config

    # Navigate to parent object
    for part in parts[:-1]:
        if hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            raise KeyError(f"Config path not found: {key_path}")

    # Set the final attribute
    final_key = parts[-1]
    if hasattr(obj, final_key):
        setattr(obj, final_key, value)
    else:
        raise KeyError(f"Config path not found: {key_path}")


def format_config_display(config: OrchestratorConfig) -> str:
    """
    Format configuration for human-readable display.

    Args:
        config: Configuration to format

    Returns:
        Formatted string representation
    """
    lines = [
        "HtmlGraph Orchestrator Configuration",
        "=" * 50,
        "",
        "Thresholds:",
        f"  exploration_calls: {config.thresholds.exploration_calls}",
        f"  circuit_breaker_violations: {config.thresholds.circuit_breaker_violations}",
        f"  violation_decay_seconds: {config.thresholds.violation_decay_seconds}",
        f"  rapid_sequence_window: {config.thresholds.rapid_sequence_window}",
        "",
        "Anti-patterns:",
        f"  consecutive_bash: {config.anti_patterns.consecutive_bash}",
        f"  consecutive_edit: {config.anti_patterns.consecutive_edit}",
        f"  consecutive_grep: {config.anti_patterns.consecutive_grep}",
        f"  consecutive_read: {config.anti_patterns.consecutive_read}",
        "",
        "Modes:",
        "  strict:",
        f"    block_after_violations: {config.modes.strict.block_after_violations}",
        f"    require_work_items: {config.modes.strict.require_work_items}",
        f"    warn_on_patterns: {config.modes.strict.warn_on_patterns}",
        "  moderate:",
        f"    block_after_violations: {config.modes.moderate.block_after_violations}",
        f"    require_work_items: {config.modes.moderate.require_work_items}",
        f"    warn_on_patterns: {config.modes.moderate.warn_on_patterns}",
        "  guidance:",
        f"    block_after_violations: {config.modes.guidance.block_after_violations}",
        f"    require_work_items: {config.modes.guidance.require_work_items}",
        f"    warn_on_patterns: {config.modes.guidance.warn_on_patterns}",
    ]
    return "\n".join(lines)
