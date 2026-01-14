"""
HtmlGraph Drift Handler Module

Centralizes drift detection and auto-classification logic for hook operations.

This module provides a unified interface for:
- Loading drift configuration from project or plugin defaults
- Detecting drift in activity results based on configurable thresholds
- Handling high-drift conditions with cooldown awareness
- Triggering auto-classification when thresholds are met
- Building classification prompts from queued activities

Drift detection identifies when tool usage diverges from the active feature's
scope, allowing automatic classification into appropriate work items (bug, feature,
spike, chore, hotfix).

File Locations:
- Config: .htmlgraph/drift-config.json (or plugin default)
- Queue: .htmlgraph/drift-queue.json (activities for classification)
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from htmlgraph.hooks.context import HookContext

logger = logging.getLogger(__name__)

# Default drift configuration thresholds and settings
DEFAULT_DRIFT_CONFIG = {
    "drift_detection": {
        "enabled": True,
        "warning_threshold": 0.7,
        "auto_classify_threshold": 0.85,
        "min_activities_before_classify": 3,
        "cooldown_minutes": 10,
    },
    "classification": {
        "enabled": False,
        "use_haiku_agent": True,
        "use_headless": False,
        "work_item_types": {
            "bug": {
                "keywords": [
                    "fix",
                    "error",
                    "broken",
                    "crash",
                    "fail",
                    "issue",
                    "wrong",
                    "incorrect",
                ],
                "description": "Fix incorrect behavior - must include repro steps",
            },
            "feature": {
                "keywords": [
                    "add",
                    "implement",
                    "create",
                    "new",
                    "build",
                    "develop",
                ],
                "description": "Deliver user value - normal flow item",
            },
            "spike": {
                "keywords": [
                    "research",
                    "explore",
                    "investigate",
                    "understand",
                    "analyze",
                    "learn",
                ],
                "description": "Reduce uncertainty - time-boxed, ends in decision",
            },
            "chore": {
                "keywords": [
                    "refactor",
                    "cleanup",
                    "update",
                    "upgrade",
                    "maintain",
                    "organize",
                ],
                "description": "Maintenance / tech debt - first-class work",
            },
            "hotfix": {
                "keywords": [
                    "urgent",
                    "critical",
                    "production",
                    "emergency",
                    "asap",
                ],
                "description": "Emergency production fix - expedite lane only",
            },
        },
    },
    "queue": {
        "max_pending_classifications": 5,
        "max_age_hours": 48,
        "process_on_stop": True,
        "process_on_threshold": True,
    },
}


def load_drift_config(graph_dir: Path) -> dict[str, Any]:
    """
    Load drift configuration from project or fallback to defaults.

    Searches for drift configuration in multiple locations with priority:
    1. .htmlgraph/drift-config.json (project-specific)
    2. Plugin config/drift-config.json (via CLAUDE_PLUGIN_ROOT)
    3. Default configuration (hardcoded fallback)

    Args:
        graph_dir: Path to .htmlgraph directory

    Returns:
        Drift configuration dict with keys: drift_detection, classification, queue

    Raises:
        OSError: If graph_dir cannot be accessed

    Example:
        ```python
        config = load_drift_config(Path(".htmlgraph"))
        logger.info(f"Auto-classify threshold: {config['drift_detection']['auto_classify_threshold']}")
        ```
    """
    graph_dir = Path(graph_dir)

    # Configuration search paths in priority order
    config_paths = [
        graph_dir / "drift-config.json",  # Project-specific (highest priority)
        Path(os.environ.get("CLAUDE_PLUGIN_ROOT", ""))
        / "config"
        / "drift-config.json",  # Plugin config
    ]

    for config_path in config_paths:
        if config_path.exists() and config_path.is_file():
            try:
                with open(config_path) as f:
                    config: dict[str, Any] = json.load(f)
                    logger.debug(f"Loaded drift config from {config_path}")
                    return config
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in {config_path}: {e}, using defaults")
            except OSError as e:
                logger.warning(f"Error reading {config_path}: {e}, using defaults")

    logger.debug("No drift config found, using defaults")
    return DEFAULT_DRIFT_CONFIG


def detect_drift(
    activity_result: dict[str, Any], config: dict[str, Any]
) -> tuple[float, str | None]:
    """
    Calculate drift score from activity result and check thresholds.

    Drift scoring logic analyzes the activity result to determine if tool usage
    aligns with the current feature context:
    - Multiple "continue": true in sequence = high drift (agent exploring options)
    - Tool errors/timeouts = high drift (unexpected behavior)
    - Normal success = low drift (expected behavior)
    - Errors = high drift (something went wrong)

    Scoring is from 0.0 (perfect alignment) to 1.0 (high drift).

    Args:
        activity_result: Activity result dict from SessionManager.track_activity()
                        Should have attributes: drift_score (optional), feature_id
        config: Drift configuration dict

    Returns:
        Tuple of (drift_score: float, feature_id: str | None)
        - drift_score: 0.0 to 1.0 (higher = more drift)
        - feature_id: Feature ID if high drift detected, else None

    Note:
        This function extracts pre-calculated drift_score from the activity
        result (calculated by SessionManager). If no drift_score exists,
        returns 0.0 (no drift).

    Example:
        ```python
        score, feature_id = detect_drift(activity_result, config)
        if score > config['drift_detection']['auto_classify_threshold']:
            logger.info(f"HIGH DRIFT: {score:.2f}")
        ```
    """
    drift_score = getattr(activity_result, "drift_score", 0.0) or 0.0
    feature_id = getattr(activity_result, "feature_id", None)

    logger.debug(f"Drift detected: score={drift_score:.2f}, feature={feature_id}")

    return (drift_score, feature_id)


def handle_high_drift(
    context: HookContext,
    drift_score: float,
    queue: dict[str, Any],
    config: dict[str, Any],
) -> str | None:
    """
    Generate nudge message for high-drift activities.

    When drift exceeds the auto-classify threshold:
    1. Adds activity to classification queue
    2. Checks cooldown to avoid spamming nudges
    3. Returns user-facing nudge message with guidance

    The cooldown prevents excessive notifications when drift is detected
    repeatedly in short timeframes.

    Args:
        context: Hook execution context with graph_dir access
        drift_score: Calculated drift score (0.0 to 1.0)
        queue: Current drift queue dict from DriftQueueManager
        config: Drift configuration dict

    Returns:
        Nudge message string for user, or None if high drift but on cooldown

    Note:
        This function generates nudges but does NOT trigger classification.
        Use trigger_auto_classification() separately to check if classification
        should be spawned.

    Example:
        ```python
        nudge = handle_high_drift(context, 0.87, queue, config)
        if nudge:
            logger.info("%s", nudge)  # "HIGH DRIFT (0.87): Activity queued for classification..."
        ```
    """
    drift_config = config.get("drift_detection", {})
    auto_classify_threshold = drift_config.get("auto_classify_threshold", 0.85)
    min_score = drift_config.get("warning_threshold", 0.7)

    # Check if drift exceeds threshold
    if drift_score < min_score:
        return None

    # Get queue size for nudge message
    min_activities = drift_config.get("min_activities_before_classify", 3)
    current_count = len(queue.get("activities", []))

    if drift_score >= auto_classify_threshold:
        # High drift - queued for classification
        return (
            f"Drift detected ({drift_score:.2f}): Activity queued for "
            f"classification ({current_count}/{min_activities} needed)."
        )
    else:
        # Moderate drift - just warn
        return (
            f"Drift detected ({drift_score:.2f}): Activity may not align with "
            f"current feature context. Consider refocusing or updating the feature."
        )


def trigger_auto_classification(
    context: HookContext,
    queue: dict[str, Any],
    feature_id: str,
    config: dict[str, Any],
) -> bool:
    """
    Check if auto-classification should be triggered.

    Validates whether classification conditions are met:
    1. Classification is enabled in config
    2. Minimum activities threshold reached
    3. Cooldown period has elapsed since last classification

    Args:
        context: Hook execution context
        queue: Current drift queue dict
        feature_id: Current feature ID for context
        config: Drift configuration dict

    Returns:
        True if classification should be triggered, False otherwise

    Example:
        ```python
        if trigger_auto_classification(context, queue, "feat-123", config):
            prompt = build_classification_prompt(queue, feature_id)
            # Spawn classification agent with prompt
        ```
    """
    drift_config = config.get("drift_detection", {})
    classification_config = config.get("classification", {})

    # Check if classification is enabled
    if not classification_config.get("enabled", False):
        logger.debug("Classification disabled in config")
        return False

    # Check minimum activities threshold
    min_activities = drift_config.get("min_activities_before_classify", 3)
    current_activities = len(queue.get("activities", []))
    if current_activities < min_activities:
        logger.debug(
            f"Not enough activities for classification: {current_activities}/{min_activities}"
        )
        return False

    # Check cooldown
    cooldown_minutes = drift_config.get("cooldown_minutes", 10)
    last_classification = queue.get("last_classification")

    if last_classification:
        try:
            last_time = datetime.fromisoformat(last_classification)
            time_since = datetime.now() - last_time
            if time_since < timedelta(minutes=cooldown_minutes):
                logger.debug(
                    f"Classification on cooldown: {time_since.total_seconds():.0f}s "
                    f"< {cooldown_minutes}min"
                )
                return False
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing last_classification timestamp: {e}")

    logger.info(
        f"Classification conditions met: {current_activities} activities, "
        f"threshold {min_activities}, cooldown {cooldown_minutes}min"
    )
    return True


def build_classification_prompt(queue: dict[str, Any], feature_id: str) -> str:
    """
    Build structured prompt for auto-classification agent.

    Formats queued activities as a clear prompt for an LLM to classify into
    appropriate work item types (bug, feature, spike, chore, hotfix).

    The prompt includes:
    - Feature context (what the current feature is supposed to do)
    - Activity list with drift scores (what the agent actually did)
    - Classification rules with descriptions
    - Instruction to create work item in .htmlgraph/

    Args:
        queue: Drift queue dict with activities list
        feature_id: Current feature ID for context

    Returns:
        Prompt string suitable for passing to classification agent

    Example:
        ```python
        prompt = build_classification_prompt(queue, "feat-abc123")
        # Use with Task tool or claude CLI
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "haiku"],
            cwd=str(project_dir),
        )
        ```
    """
    activities = queue.get("activities", [])

    # Format activity lines with summaries and drift scores
    activity_lines = []
    for activity in activities:
        tool = activity.get("tool", "unknown")
        summary = activity.get("summary", "no summary")
        drift_score = activity.get("drift_score", 0)
        file_paths = activity.get("file_paths", [])

        # Build activity line
        line = f"- {tool}: {summary}"

        # Add file context if available
        if file_paths:
            files_str = ", ".join(str(f) for f in file_paths[:2])
            line += f" (files: {files_str})"

        # Add drift score
        line += f" [drift: {drift_score:.2f}]"
        activity_lines.append(line)

    # Build classification prompt
    prompt = f"""Classify these high-drift activities into a work item.

Current feature context: {feature_id}

Recent activities with high drift:
{chr(10).join(activity_lines)}

Based on the activity patterns:
1. Determine the work item type (bug, feature, spike, chore, or hotfix)
2. Create an appropriate title and description
3. Create the work item HTML file in .htmlgraph/

Use the classification rules:
- bug: fixing errors, incorrect behavior
- feature: new functionality, additions
- spike: research, exploration, investigation
- chore: maintenance, refactoring, cleanup
- hotfix: urgent production issues

Create the work item now using Write tool."""

    logger.debug(f"Built classification prompt ({len(activity_lines)} activities)")
    return prompt


def run_headless_classification(
    context: HookContext, prompt: str, config: dict[str, Any]
) -> tuple[bool, str | None]:
    """
    Attempt to run auto-classification via headless claude subprocess.

    Spawns a subprocess with the classification prompt to avoid blocking
    the main hook execution. Sets HTMLGRAPH_DISABLE_TRACKING to prevent
    recursive hook execution.

    Args:
        context: Hook execution context with project_dir access
        prompt: Classification prompt to send to claude
        config: Drift configuration dict

    Returns:
        Tuple of (success: bool, nudge: str | None)
        - success: True if classification subprocess succeeded
        - nudge: Message to include in hook response

    Raises:
        subprocess.TimeoutExpired: If classification takes > 120 seconds
        OSError: If claude command not found

    Example:
        ```python
        success, nudge = run_headless_classification(context, prompt, config)
        if success:
            logger.info("Classification completed")
        else:
            logger.warning("Fallback to manual classification needed")
        ```
    """
    classification_config = config.get("classification", {})
    model = classification_config.get("model", "haiku")

    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--model",
                model,
                "--dangerously-skip-permissions",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=context.project_dir,
            env={
                **os.environ,
                # Prevent hooks from creating nested HtmlGraph sessions
                "HTMLGRAPH_DISABLE_TRACKING": "1",
            },
        )

        if result.returncode == 0:
            logger.info("Headless classification completed successfully")
            nudge = (
                "Drift auto-classification completed. "
                "Check .htmlgraph/ for new work item."
            )
            return (True, nudge)
        else:
            logger.warning(f"Classification subprocess failed: {result.stderr}")
            nudge = (
                "HIGH DRIFT - Headless classification failed. "
                "Please classify manually in .htmlgraph/"
            )
            return (False, nudge)

    except subprocess.TimeoutExpired as e:
        logger.error(f"Classification timeout after {e.timeout}s")
        nudge = (
            "HIGH DRIFT - Classification timeout. "
            "Please classify manually in .htmlgraph/"
        )
        return (False, nudge)
    except FileNotFoundError:
        logger.error("claude command not found")
        nudge = (
            "HIGH DRIFT - claude not available. Please classify manually in .htmlgraph/"
        )
        return (False, nudge)
    except Exception as e:
        logger.error(f"Unexpected error during classification: {e}")
        nudge = (
            f"HIGH DRIFT - Classification error: {e}. "
            "Please classify manually in .htmlgraph/"
        )
        return (False, nudge)


__all__ = [
    "load_drift_config",
    "detect_drift",
    "handle_high_drift",
    "trigger_auto_classification",
    "build_classification_prompt",
    "run_headless_classification",
    "DEFAULT_DRIFT_CONFIG",
]
