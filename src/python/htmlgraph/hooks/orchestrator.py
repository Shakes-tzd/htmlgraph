import logging

logger = logging.getLogger(__name__)

"""
Orchestrator Enforcement Module

This module provides the core logic for enforcing orchestrator delegation patterns
in HtmlGraph-enabled projects. It classifies operations into allowed vs blocked
categories and provides clear Task delegation suggestions.

Architecture:
- Reads orchestrator mode from .htmlgraph/orchestrator-mode.json
- Classifies operations into ALLOWED vs BLOCKED categories
- Tracks tool usage sequences to detect exploration patterns
- Provides clear Task delegation suggestions when blocking
- Subagents spawned via Task() have unrestricted tool access
- Detection uses 5-level strategy: env vars, session state, database

Operation Categories:
1. ALWAYS ALLOWED - Task, AskUserQuestion, TodoWrite, SDK operations
2. SINGLE LOOKUP ALLOWED - First Read/Grep/Glob (check history)
3. BLOCKED - Edit, Write, NotebookEdit, Delete, test/build commands

Enforcement Levels:
- strict: BLOCKS implementation operations with clear error
- guidance: ALLOWS but provides warnings and suggestions

Public API:
- enforce_orchestrator_mode(tool: str, params: dict[str, Any]) -> dict
    Main entry point for hook scripts. Returns hook response dict.
"""

import json
import re
from pathlib import Path
from typing import Any

from htmlgraph.hooks.subagent_detection import is_subagent_context
from htmlgraph.orchestrator_config import load_orchestrator_config
from htmlgraph.orchestrator_mode import OrchestratorModeManager
from htmlgraph.orchestrator_validator import OrchestratorValidator

# Maximum number of recent tool calls to consider for pattern detection
MAX_HISTORY_SIZE = 50  # Keep last 50 tool calls


def load_tool_history(session_id: str) -> list[dict]:
    """
    Load recent tool history from database (session-isolated).

    Args:
        session_id: Session identifier to filter tool history

    Returns:
        List of recent tool calls with tool name and timestamp
    """
    try:
        from htmlgraph.db.schema import HtmlGraphDB

        # Find database path
        cwd = Path.cwd()
        graph_dir = cwd / ".htmlgraph"
        if not graph_dir.exists():
            for parent in [cwd.parent, cwd.parent.parent, cwd.parent.parent.parent]:
                candidate = parent / ".htmlgraph"
                if candidate.exists():
                    graph_dir = candidate
                    break

        db_path = graph_dir / "htmlgraph.db"
        if not db_path.exists():
            return []

        db = HtmlGraphDB(str(db_path))
        if db.connection is None:
            return []

        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT tool_name, timestamp
            FROM agent_events
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (session_id, MAX_HISTORY_SIZE),
        )

        # Return in chronological order (oldest first) for pattern detection
        rows = cursor.fetchall()
        db.disconnect()

        return [{"tool": row[0], "timestamp": row[1]} for row in reversed(rows)]
    except Exception:
        # Graceful degradation - return empty history on error
        return []


def record_tool_event(tool_name: str, session_id: str) -> None:
    """
    Record a tool event to the database for history tracking.

    This is called at the end of PreToolUse hook execution to track
    tool usage patterns for sequence detection.

    Args:
        tool_name: Name of the tool being called
        session_id: Session identifier for isolation
    """
    try:
        import datetime
        import uuid

        from htmlgraph.db.schema import HtmlGraphDB

        # Find database path
        cwd = Path.cwd()
        graph_dir = cwd / ".htmlgraph"
        if not graph_dir.exists():
            for parent in [cwd.parent, cwd.parent.parent, cwd.parent.parent.parent]:
                candidate = parent / ".htmlgraph"
                if candidate.exists():
                    graph_dir = candidate
                    break

        if not graph_dir.exists():
            return

        db_path = graph_dir / "htmlgraph.db"
        db = HtmlGraphDB(str(db_path))
        if db.connection is None:
            return

        cursor = db.connection.cursor()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Ensure session exists (required by FK constraint)
        cursor.execute(
            """
            INSERT OR IGNORE INTO sessions (session_id, agent_assigned, created_at, status)
            VALUES (?, ?, ?, ?)
        """,
            (session_id, "orchestrator-hook", timestamp, "active"),
        )

        # Record the tool event using the actual schema
        # Schema has: event_id, agent_id, event_type, timestamp, tool_name, session_id, etc.
        event_id = str(uuid.uuid4())
        agent_id = "orchestrator-hook"  # Identifier for the hook

        cursor.execute(
            """
            INSERT INTO agent_events (event_id, agent_id, event_type, timestamp, tool_name, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (event_id, agent_id, "tool_call", timestamp, tool_name, session_id),
        )

        db.connection.commit()
        db.disconnect()
    except Exception:
        # Graceful degradation - don't fail hook on recording error
        pass


def is_allowed_orchestrator_operation(
    tool: str, params: dict[str, Any], session_id: str = "unknown"
) -> tuple[bool, str, str]:
    """
    Check if operation is allowed for orchestrators.

    Args:
        tool: Tool name (e.g., "Read", "Edit", "Bash")
        params: Tool parameters dict
        session_id: Session identifier for loading tool history

    Returns:
        Tuple of (is_allowed, reason_if_not, category)
        - is_allowed: True if operation should proceed
        - reason_if_not: Explanation if blocked (empty if allowed)
        - category: Operation category for logging
    """
    # Get enforcement level from manager
    try:
        cwd = Path.cwd()
        graph_dir = cwd / ".htmlgraph"
        if not graph_dir.exists():
            for parent in [cwd.parent, cwd.parent.parent, cwd.parent.parent.parent]:
                candidate = parent / ".htmlgraph"
                if candidate.exists():
                    graph_dir = candidate
                    break
        manager = OrchestratorModeManager(graph_dir)
        enforcement_level = (
            manager.get_enforcement_level() if manager.is_enabled() else "guidance"
        )
    except Exception:
        enforcement_level = "guidance"

    # Use OrchestratorValidator for comprehensive validation
    validator = OrchestratorValidator()
    result, reason = validator.validate_tool_use(tool, params)

    if result == "block":
        return False, reason, "validator-blocked"
    elif result == "warn":
        # Continue but with warning
        pass  # Fall through to existing checks

    # Category 1: ALWAYS ALLOWED - Orchestrator core operations
    if tool in ["Task", "AskUserQuestion", "TodoWrite"]:
        return True, "", "orchestrator-core"

    # FIX #2: Block Skills in strict mode (must be invoked via Task delegation)
    if tool == "Skill" and enforcement_level == "strict":
        return False, "Skills must be invoked via Task delegation", "skill-blocked"

    # Category 2: SDK Operations - Always allowed
    if tool == "Bash":
        command = params.get("command", "")

        # Allow htmlgraph SDK commands
        if command.startswith("uv run htmlgraph ") or command.startswith("htmlgraph "):
            return True, "", "sdk-command"

        # Allow git read-only commands using shared classification
        if command.strip().startswith("git"):
            from htmlgraph.hooks.git_commands import should_allow_git_command

            if should_allow_git_command(command):
                return True, "", "git-readonly"

        # Allow SDK inline usage (Python inline with htmlgraph import)
        if "from htmlgraph import" in command or "import htmlgraph" in command:
            return True, "", "sdk-inline"

        # FIX #3: Check if bash command is in allowed whitelist (strict mode only)
        # If we've gotten here, it's not a whitelisted command above
        # Block non-whitelisted bash commands in strict mode
        if enforcement_level == "strict":
            # Check if it's a blocked test/build pattern (handled below)
            blocked_patterns = [
                r"^npm (run|test|build)",
                r"^pytest",
                r"^uv run pytest",
                r"^python -m pytest",
                r"^cargo (build|test)",
                r"^mvn (compile|test|package)",
                r"^make (test|build)",
            ]
            is_blocked_pattern = any(
                re.match(pattern, command) for pattern in blocked_patterns
            )

            if not is_blocked_pattern:
                # Not a specifically blocked pattern, but also not whitelisted
                # In strict mode, we should delegate
                return (
                    False,
                    f"Bash command not in allowed list. Delegate to subagent.\n\n"
                    f"Command: {command[:100]}",
                    "bash-blocked",
                )

    # Category 3: Quick Lookups - Single operations only
    if tool in ["Read", "Grep", "Glob"]:
        # Check tool history to see if this is a single lookup or part of a sequence
        history = load_tool_history(session_id)

        # FIX #4: Check for mixed exploration pattern (configurable threshold)
        config = load_orchestrator_config()
        exploration_threshold = config.thresholds.exploration_calls

        # Check last N calls (where N = threshold + 2)
        lookback = min(exploration_threshold + 2, len(history))
        exploration_count = sum(
            1 for h in history[-lookback:] if h["tool"] in ["Read", "Grep", "Glob"]
        )
        if exploration_count >= exploration_threshold and enforcement_level == "strict":
            return (
                False,
                f"Multiple exploration calls detected ({exploration_count}/{exploration_threshold}). Delegate to Explorer agent.\n\n"
                "Use Task tool with explorer subagent.",
                "exploration-blocked",
            )

        # Look at last 3 tool calls
        recent_same_tool = sum(1 for h in history[-3:] if h["tool"] == tool)

        if recent_same_tool == 0:  # First use
            return True, "Single lookup allowed", "single-lookup"
        else:
            return (
                False,
                f"Multiple {tool} calls detected. This is exploration work.\n\n"
                f"Delegate to Explorer subagent using Task tool.",
                "multi-lookup-blocked",
            )

    # Category 4: BLOCKED - Implementation tools
    if tool in ["Edit", "Write", "NotebookEdit"]:
        return (
            False,
            f"{tool} is implementation work.\n\n"
            f"Delegate to Coder subagent using Task tool.",
            "implementation-blocked",
        )

    if tool == "Delete":
        return (
            False,
            "Delete is a destructive implementation operation.\n\n"
            "Delegate to Coder subagent using Task tool.",
            "delete-blocked",
        )

    # Category 5: BLOCKED - Testing/Building
    if tool == "Bash":
        command = params.get("command", "")

        # Block compilation, testing, building (should be in subagent)
        test_build_patterns: list[tuple[str, str]] = [
            (r"^npm (run|test|build)", "npm test/build"),
            (r"^pytest", "pytest"),
            (r"^uv run pytest", "pytest"),
            (r"^python -m pytest", "pytest"),
            (r"^cargo (build|test)", "cargo build/test"),
            (r"^mvn (compile|test|package)", "maven build/test"),
            (r"^make (test|build)", "make test/build"),
        ]

        for pattern, name in test_build_patterns:
            if re.match(pattern, command):
                return (
                    False,
                    f"Testing/building ({name}) should be delegated to subagent.\n\n"
                    f"Use Task tool to run tests and report results.",
                    "test-build-blocked",
                )

    # FIX #1: Remove "allowed-default" escape hatch in strict mode
    if enforcement_level == "strict":
        return False, "Not in allowed whitelist", "strict-blocked"
    else:
        return True, "Allowed in guidance mode", "guidance-allowed"


def create_task_suggestion(tool: str, params: dict[str, Any]) -> str:
    """
    Create Task tool suggestion based on blocked operation.

    Includes HtmlGraph reporting pattern for result retrieval.

    Args:
        tool: Tool that was blocked
        params: Tool parameters

    Returns:
        Example Task() code with HtmlGraph reporting pattern
    """
    if tool in ["Edit", "Write", "NotebookEdit"]:
        file_path = params.get("file_path", "<file>")
        return (
            "# Delegate to Coder subagent:\n"
            "Task(\n"
            f"    prompt='''Implement changes to {file_path}\n\n"
            "    🔴 CRITICAL - Report Results:\n"
            "    from htmlgraph import SDK\n"
            "    sdk = SDK(agent='coder')\n"
            "    sdk.spikes.create('Code Changes Complete') \\\\\n"
            "        .set_findings('Changes made: ...') \\\\\n"
            "        .save()\n"
            "    ''',\n"
            "    subagent_type='general-purpose'\n"
            ")\n"
            "# Then retrieve: uv run python -c \"from htmlgraph import SDK; print(SDK().spikes.get_latest(agent='coder')[0].findings)\""
        )

    elif tool in ["Read", "Grep", "Glob"]:
        pattern = params.get("pattern", params.get("file_path", "<pattern>"))
        return (
            "# Delegate to Explorer subagent:\n"
            "Task(\n"
            f"    prompt='''Find {pattern} in codebase\n\n"
            "    🔴 CRITICAL - Report Results:\n"
            "    from htmlgraph import SDK\n"
            "    sdk = SDK(agent='explorer')\n"
            "    sdk.spikes.create('Search Results') \\\\\n"
            "        .set_findings('Found files: ...') \\\\\n"
            "        .save()\n"
            "    ''',\n"
            "    subagent_type='Explore'\n"
            ")\n"
            "# Then retrieve: uv run python -c \"from htmlgraph import SDK; print(SDK().spikes.get_latest(agent='explorer')[0].findings)\""
        )

    elif tool == "Bash":
        command = params.get("command", "")
        if "test" in command.lower() or "pytest" in command.lower():
            return (
                "# Delegate testing to subagent:\n"
                "Task(\n"
                "    prompt='''Run tests and report results\n\n"
                "    🔴 CRITICAL - Report Results:\n"
                "    from htmlgraph import SDK\n"
                "    sdk = SDK(agent='tester')\n"
                "    sdk.spikes.create('Test Results') \\\\\n"
                "        .set_findings('Tests passed: X, failed: Y') \\\\\n"
                "        .save()\n"
                "    ''',\n"
                "    subagent_type='general-purpose'\n"
                ")\n"
                "# Then retrieve: uv run python -c \"from htmlgraph import SDK; print(SDK().spikes.get_latest(agent='tester')[0].findings)\""
            )
        elif any(x in command.lower() for x in ["build", "compile", "make"]):
            return (
                "# Delegate build to subagent:\n"
                "Task(\n"
                "    prompt='''Build project and report any errors\n\n"
                "    🔴 CRITICAL - Report Results:\n"
                "    from htmlgraph import SDK\n"
                "    sdk = SDK(agent='builder')\n"
                "    sdk.spikes.create('Build Results') \\\\\n"
                "        .set_findings('Build status: ...') \\\\\n"
                "        .save()\n"
                "    ''',\n"
                "    subagent_type='general-purpose'\n"
                ")\n"
                "# Then retrieve: uv run python -c \"from htmlgraph import SDK; print(SDK().spikes.get_latest(agent='builder')[0].findings)\""
            )

    # Generic suggestion
    return (
        "# Use Task tool with HtmlGraph reporting:\n"
        "Task(\n"
        "    prompt='''<describe task>\n\n"
        "    🔴 CRITICAL - Report Results:\n"
        "    from htmlgraph import SDK\n"
        "    sdk = SDK(agent='subagent')\n"
        "    sdk.spikes.create('Task Results') \\\\\n"
        "        .set_findings('...') \\\\\n"
        "        .save()\n"
        "    ''',\n"
        "    subagent_type='general-purpose'\n"
        ")\n"
        "# Then retrieve: uv run python -c \"from htmlgraph import SDK; print(SDK().spikes.get_latest(agent='subagent')[0].findings)\""
    )


def enforce_orchestrator_mode(
    tool: str, params: dict[str, Any], session_id: str = "unknown"
) -> dict[str, Any]:
    """
    Enforce orchestrator mode rules.

    This is the main public API for hook scripts. It checks if orchestrator mode
    is enabled, classifies the operation, and returns a hook response dict.

    Subagents spawned via Task() have unrestricted tool access.
    Detection uses 5-level strategy: env vars, session state, database.

    Args:
        tool: Tool being called
        params: Tool parameters
        session_id: Session identifier for loading tool history

    Returns:
        Hook response dict with decision (allow/block) and guidance
        Format: {"continue": bool, "hookSpecificOutput": {...}}
    """
    # Check if this is a subagent context - subagents have unrestricted tool access
    if is_subagent_context():
        return {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            },
        }

    # Get manager and check if mode is enabled
    try:
        # Look for .htmlgraph directory starting from cwd
        cwd = Path.cwd()
        graph_dir = cwd / ".htmlgraph"

        # If not found in cwd, try parent directories (up to 3 levels)
        if not graph_dir.exists():
            for parent in [cwd.parent, cwd.parent.parent, cwd.parent.parent.parent]:
                candidate = parent / ".htmlgraph"
                if candidate.exists():
                    graph_dir = candidate
                    break

        manager = OrchestratorModeManager(graph_dir)

        if not manager.is_enabled():
            # Mode not active, allow everything with no additional output
            return {"continue": True}

        enforcement_level = manager.get_enforcement_level()
    except Exception:
        # If we can't check mode, fail open (allow)
        return {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            },
        }

    # Check if circuit breaker is triggered in strict mode (configurable threshold)
    config = load_orchestrator_config()
    circuit_breaker_threshold = config.thresholds.circuit_breaker_violations

    if enforcement_level == "strict" and manager.is_circuit_breaker_triggered():
        # Circuit breaker triggered - block all non-core operations
        if tool not in ["Task", "AskUserQuestion", "TodoWrite"]:
            violation_count = manager.get_violation_count()
            circuit_breaker_message = (
                "🚨 ORCHESTRATOR CIRCUIT BREAKER TRIGGERED\n\n"
                f"You have violated delegation rules {violation_count} times this session "
                f"(threshold: {circuit_breaker_threshold}).\n\n"
                "Violations detected:\n"
                "- Direct execution instead of delegation\n"
                "- Context waste on tactical operations\n\n"
                "Options:\n"
                "1. Disable orchestrator mode: uv run htmlgraph orchestrator disable\n"
                "2. Change to guidance mode: uv run htmlgraph orchestrator set-level guidance\n"
                "3. Reset counter (acknowledge violations): uv run htmlgraph orchestrator reset-violations\n"
                "4. Adjust thresholds: uv run htmlgraph orchestrator config set thresholds.circuit_breaker_violations <N>\n\n"
                "To proceed, choose an option above."
            )

            return {
                "continue": False,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": circuit_breaker_message,
                },
            }

    # Check if operation is allowed (pass session_id for history lookup)
    is_allowed, reason, category = is_allowed_orchestrator_operation(
        tool, params, session_id
    )

    # Note: Tool recording is now handled by track-event.py PostToolUse hook
    # No need to call add_to_tool_history() here

    # Operation is allowed
    if is_allowed:
        if (
            reason
            and enforcement_level == "strict"
            and category not in ["orchestrator-core", "sdk-command"]
        ):
            # Provide guidance even when allowing
            return {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": f"✅ {reason}",
                },
            }
        return {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            },
        }

    # Operation not allowed - track violation and provide warnings
    if enforcement_level == "strict":
        # Increment violation counter
        mode = manager.increment_violation()
        violations = mode.violations

    suggestion = create_task_suggestion(tool, params)

    if enforcement_level == "strict":
        # STRICT mode - advisory warning with violation count (does not block)
        warning_message = (
            f"🚫 ORCHESTRATOR MODE VIOLATION ({violations}/{circuit_breaker_threshold}): {reason}\n\n"
            f"⚠️  WARNING: Direct operations waste context and break delegation pattern!\n\n"
            f"Suggested delegation:\n"
            f"{suggestion}\n\n"
        )

        # Add circuit breaker warning if approaching threshold
        if violations >= circuit_breaker_threshold:
            warning_message += (
                "🚨 CIRCUIT BREAKER TRIGGERED - Further violations will be blocked!\n\n"
                "Reset with: uv run htmlgraph orchestrator reset-violations\n"
            )
        elif violations == circuit_breaker_threshold - 1:
            warning_message += "⚠️  Next violation will trigger circuit breaker!\n\n"

        warning_message += (
            "See ORCHESTRATOR_DIRECTIVES in session context for HtmlGraph delegation pattern.\n"
            "To disable orchestrator mode: uv run htmlgraph orchestrator disable"
        )

        # Advisory-only: allow operation but provide warning
        return {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": warning_message,
            },
        }
    else:
        # GUIDANCE mode - softer warning
        warning_message = (
            f"⚠️ ORCHESTRATOR: {reason}\n\nSuggested delegation:\n{suggestion}"
        )

        return {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": warning_message,
            },
        }


def main() -> None:
    """Hook entry point for script wrapper."""
    import os
    import sys

    # Check if tracking is disabled
    if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # Check for orchestrator mode environment override
    if os.environ.get("HTMLGRAPH_ORCHESTRATOR_DISABLED") == "1":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    # Get tool name and parameters (Claude Code uses "name" and "input")
    tool_name = hook_input.get("name", "") or hook_input.get("tool_name", "")
    tool_input = hook_input.get("input", {}) or hook_input.get("tool_input", {})

    # Get session_id from hook_input (NEW: required for session-isolated history)
    session_id = hook_input.get("session_id", "unknown")

    if not tool_name:
        # No tool name, allow
        print(json.dumps({"continue": True}))
        return

    # Enforce orchestrator mode with session_id for history lookup
    response = enforce_orchestrator_mode(tool_name, tool_input, session_id)

    # Record tool event to database for history tracking
    # This allows subsequent calls to detect patterns (e.g., multiple Reads)
    record_tool_event(tool_name, session_id)

    # Output JSON response
    print(json.dumps(response))
