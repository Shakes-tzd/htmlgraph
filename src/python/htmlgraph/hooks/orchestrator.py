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

Operation Categories:
1. ALWAYS ALLOWED - Task, AskUserQuestion, TodoWrite, SDK operations
2. SINGLE LOOKUP ALLOWED - First Read/Grep/Glob (check history)
3. BLOCKED - Edit, Write, NotebookEdit, Delete, test/build commands

Enforcement Levels:
- strict: BLOCKS implementation operations with clear error
- guidance: ALLOWS but provides warnings and suggestions

Public API:
- enforce_orchestrator_mode(tool: str, params: dict) -> dict
    Main entry point for hook scripts. Returns hook response dict.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from htmlgraph.orchestrator_mode import OrchestratorModeManager
from htmlgraph.orchestrator_validator import OrchestratorValidator

# Tool history file (temporary storage for session)
TOOL_HISTORY_FILE = Path("/tmp/htmlgraph-tool-history.json")
MAX_HISTORY_SIZE = 50  # Keep last 50 tool calls


def load_tool_history() -> list[dict]:
    """
    Load recent tool history from temp file.

    Returns:
        List of recent tool calls with tool name and timestamp
    """
    if not TOOL_HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(TOOL_HISTORY_FILE.read_text())
        # Handle both formats: {"history": [...]} and [...] (legacy)
        if isinstance(data, list):
            return cast(list[dict[Any, Any]], data)
        return cast(list[dict[Any, Any]], data.get("history", []))
    except Exception:
        return []


def save_tool_history(history: list[dict]) -> None:
    """
    Save tool history to temp file.

    Args:
        history: List of tool calls to persist
    """
    try:
        # Keep only recent history
        recent = (
            history[-MAX_HISTORY_SIZE:] if len(history) > MAX_HISTORY_SIZE else history
        )
        TOOL_HISTORY_FILE.write_text(json.dumps({"history": recent}, indent=2))
    except Exception:
        pass  # Fail silently on history save errors


def add_to_tool_history(tool: str) -> None:
    """
    Add a tool call to history.

    Args:
        tool: Name of the tool being called
    """
    history = load_tool_history()
    history.append(
        {
            "tool": tool,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_tool_history(history)


def is_allowed_orchestrator_operation(tool: str, params: dict) -> tuple[bool, str, str]:
    """
    Check if operation is allowed for orchestrators.

    Args:
        tool: Tool name (e.g., "Read", "Edit", "Bash")
        params: Tool parameters dict

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

        # Allow git read-only commands
        if (
            command.startswith("git status")
            or command.startswith("git diff")
            or command.startswith("git log")
        ):
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
        history = load_tool_history()

        # FIX #4: Check for mixed exploration pattern
        exploration_count = sum(
            1 for h in history[-5:] if h["tool"] in ["Read", "Grep", "Glob"]
        )
        if exploration_count >= 3 and enforcement_level == "strict":
            return (
                False,
                "Multiple exploration calls detected. Delegate to Explorer agent.\n\n"
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


def create_task_suggestion(tool: str, params: dict) -> str:
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


def enforce_orchestrator_mode(tool: str, params: dict) -> dict:
    """
    Enforce orchestrator mode rules.

    This is the main public API for hook scripts. It checks if orchestrator mode
    is enabled, classifies the operation, and returns a hook response dict.

    Args:
        tool: Tool being called
        params: Tool parameters

    Returns:
        Hook response dict with decision (allow/block) and guidance
        Format: {"continue": bool, "hookSpecificOutput": {...}}
    """
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
            # Mode not active, allow everything
            add_to_tool_history(tool)
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                },
            }

        enforcement_level = manager.get_enforcement_level()
    except Exception:
        # If we can't check mode, fail open (allow)
        add_to_tool_history(tool)
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            },
        }

    # Check if circuit breaker is triggered in strict mode
    if enforcement_level == "strict" and manager.is_circuit_breaker_triggered():
        # Circuit breaker triggered - block all non-core operations
        if tool not in ["Task", "AskUserQuestion", "TodoWrite"]:
            circuit_breaker_message = (
                "🚨 ORCHESTRATOR CIRCUIT BREAKER TRIGGERED\n\n"
                f"You have violated delegation rules {manager.get_violation_count()} times this session.\n\n"
                "Violations detected:\n"
                "- Direct execution instead of delegation\n"
                "- Context waste on tactical operations\n\n"
                "Options:\n"
                "1. Disable orchestrator mode: uv run htmlgraph orchestrator disable\n"
                "2. Change to guidance mode: uv run htmlgraph orchestrator set-level guidance\n"
                "3. Reset counter (acknowledge violations): uv run htmlgraph orchestrator reset-violations\n\n"
                "To proceed, choose an option above."
            )

            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": circuit_breaker_message,
                },
            }

    # Check if operation is allowed
    is_allowed, reason, category = is_allowed_orchestrator_operation(tool, params)

    # Add to history (for sequence detection)
    add_to_tool_history(tool)

    # Operation is allowed
    if is_allowed:
        if (
            reason
            and enforcement_level == "strict"
            and category not in ["orchestrator-core", "sdk-command"]
        ):
            # Provide guidance even when allowing
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": f"✅ {reason}",
                },
            }
        return {
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
        # STRICT mode - loud warning with violation count
        error_message = (
            f"🚫 ORCHESTRATOR MODE VIOLATION ({violations}/3): {reason}\n\n"
            f"⚠️  WARNING: Direct operations waste context and break delegation pattern!\n\n"
            f"Suggested delegation:\n"
            f"{suggestion}\n\n"
        )

        # Add circuit breaker warning if approaching threshold
        if violations >= 3:
            error_message += (
                "🚨 CIRCUIT BREAKER TRIGGERED - Further violations will be blocked!\n\n"
                "Reset with: uv run htmlgraph orchestrator reset-violations\n"
            )
        elif violations == 2:
            error_message += "⚠️  Next violation will trigger circuit breaker!\n\n"

        error_message += (
            "See ORCHESTRATOR_DIRECTIVES in session context for HtmlGraph delegation pattern.\n"
            "To disable orchestrator mode: uv run htmlgraph orchestrator disable"
        )

        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": error_message,
            },
        }
    else:
        # GUIDANCE mode - softer warning
        warning_message = (
            f"⚠️ ORCHESTRATOR: {reason}\n\nSuggested delegation:\n{suggestion}"
        )

        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": warning_message,
            },
        }
