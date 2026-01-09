#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
Orchestrator Enforcement Hook (PreToolUse)

Enforces orchestrator delegation patterns when orchestrator mode is active.
Uses OrchestratorModeManager to check mode state and enforcement level.

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
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Check if tracking is disabled
if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({"continue": True}))
    sys.exit(0)

# Check for orchestrator mode environment override
if os.environ.get("HTMLGRAPH_ORCHESTRATOR_DISABLED") == "1":
    print(json.dumps({"continue": True}))
    sys.exit(0)

try:
    from htmlgraph.orchestrator_mode import OrchestratorModeManager
except Exception:
    # If htmlgraph not available, allow all operations
    print(json.dumps({"continue": True}))
    sys.exit(0)


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
            return data
        return data.get("history", [])
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
    # Category 1: ALWAYS ALLOWED - Orchestrator core operations
    if tool in ["Task", "AskUserQuestion", "TodoWrite"]:
        return True, "", "orchestrator-core"

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

    # Category 3: Quick Lookups - Single operations only
    if tool in ["Read", "Grep", "Glob"]:
        # Check tool history to see if this is a single lookup or part of a sequence
        history = load_tool_history()

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
        blocked_patterns = [
            (r"^npm (run|test|build)", "npm test/build"),
            (r"^pytest", "pytest"),
            (r"^uv run pytest", "pytest"),
            (r"^python -m pytest", "pytest"),
            (r"^cargo (build|test)", "cargo build/test"),
            (r"^mvn (compile|test|package)", "maven build/test"),
            (r"^make (test|build)", "make test/build"),
        ]

        for pattern, name in blocked_patterns:
            if re.match(pattern, command):
                return (
                    False,
                    f"Testing/building ({name}) should be delegated to subagent.\n\n"
                    f"Use Task tool to run tests and report results.",
                    "test-build-blocked",
                )

    # Default: Allow with guidance
    return True, "Allowed but consider if delegation would be better", "allowed-default"


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

    Args:
        tool: Tool being called
        params: Tool parameters

    Returns:
        Hook response dict with decision (allow/block) and guidance
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
            return {"continue": True}

        enforcement_level = manager.get_enforcement_level()
    except Exception:
        # If we can't check mode, fail open (allow)
        add_to_tool_history(tool)
        return {"continue": True}

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
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": f"✅ {reason}",
                },
            }
        return {"continue": True}

    # Operation not allowed - provide strong warnings
    # NOTE: {"continue": False} doesn't work in Claude Code, so we use advisory warnings only
    suggestion = create_task_suggestion(tool, params)

    if enforcement_level == "strict":
        # STRICT mode - loud warning but allow (blocking doesn't work)
        error_message = (
            f"🚫 ORCHESTRATOR MODE VIOLATION: {reason}\n\n"
            f"⚠️  WARNING: Direct operations waste context and break delegation pattern!\n\n"
            f"Suggested delegation:\n"
            f"{suggestion}\n\n"
            f"See ORCHESTRATOR_DIRECTIVES in session context for HtmlGraph delegation pattern.\n"
            f"To disable orchestrator mode: uv run htmlgraph orchestrator disable"
        )

        return {
            "continue": True,  # Changed from False - blocking doesn't work
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": error_message,
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
                "additionalContext": warning_message,
            },
        }


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    # Get tool name and parameters (Claude Code uses "name" and "input")
    tool_name = hook_input.get("name", "") or hook_input.get("tool_name", "")
    tool_input = hook_input.get("input", {}) or hook_input.get("tool_input", {})

    if not tool_name:
        # No tool name, allow
        print(json.dumps({"continue": True}))
        return

    # Enforce orchestrator mode (saves to history internally)
    response = enforce_orchestrator_mode(tool_name, tool_input)

    # Output JSON response
    print(json.dumps(response))


if __name__ == "__main__":
    main()
