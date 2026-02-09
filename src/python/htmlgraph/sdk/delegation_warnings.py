"""
Delegation warnings for orchestrator mode.

Provides warnings when orchestrators execute tools directly instead of delegating,
with automatic suppression when running in subagent contexts.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def is_orchestrator_mode_active() -> bool:
    """
    Check if orchestrator mode is active.

    Returns:
        True if orchestrator mode is enabled
    """
    # Check environment variable override
    if os.environ.get("HTMLGRAPH_ORCHESTRATOR_DISABLED") == "1":
        return False

    # Check orchestrator mode file
    try:
        from pathlib import Path

        from htmlgraph.orchestrator_mode import OrchestratorModeManager

        # Find .htmlgraph directory
        cwd = Path.cwd()
        graph_dir = cwd / ".htmlgraph"

        if not graph_dir.exists():
            for parent in [cwd.parent, cwd.parent.parent, cwd.parent.parent.parent]:
                candidate = parent / ".htmlgraph"
                if candidate.exists():
                    graph_dir = candidate
                    break

        if not graph_dir.exists():
            return False

        manager = OrchestratorModeManager(graph_dir)
        return manager.is_enabled()
    except Exception:
        return False


def is_in_subagent_context() -> bool:
    """
    Check if running in a subagent context.

    Subagents are spawned via Task() and should be allowed to execute
    tools directly without delegation warnings.

    Returns:
        True if in subagent context
    """
    # Check for subagent environment variable
    subagent_type = os.environ.get("HTMLGRAPH_SUBAGENT_TYPE")
    if subagent_type:
        return True

    # Check for general subagent marker
    if os.environ.get("HTMLGRAPH_IS_SUBAGENT") == "1":
        return True

    # Check if spawned by Task tool (Claude Code sets this)
    if os.environ.get("CLAUDE_SPAWNED_BY_TASK") == "1":
        return True

    return False


def should_show_delegation_warning() -> bool:
    """
    Determine if delegation warnings should be shown.

    Warnings are shown when:
    - Orchestrator mode is active
    - NOT running in subagent context
    - Warnings are not explicitly disabled

    Returns:
        True if warnings should be shown
    """
    # Check explicit disable
    if os.environ.get("HTMLGRAPH_DISABLE_DELEGATION_WARNINGS") == "1":
        return False

    # Don't warn in subagent contexts
    if is_in_subagent_context():
        return False

    # Only warn if orchestrator mode is active
    return is_orchestrator_mode_active()


def get_delegation_warning(tool_name: str, context: str = "") -> str:
    """
    Generate delegation warning message.

    Args:
        tool_name: Name of the tool being executed directly
        context: Additional context about the operation

    Returns:
        Formatted warning message
    """
    # Map tools to suggested subagent types
    tool_to_agent = {
        "Read": "Explore",
        "Grep": "Explore",
        "Glob": "Explore",
        "Edit": "general-purpose",
        "Write": "general-purpose",
        "NotebookEdit": "general-purpose",
        "Bash": "general-purpose",
    }

    suggested_agent = tool_to_agent.get(tool_name, "general-purpose")

    warning = f"""
⚠️  ORCHESTRATOR MODE: Direct tool execution detected

Tool: {tool_name}
Suggestion: Delegate to subagent using Task()

Recommended subagent type: {suggested_agent}

Example delegation:
  Task(
      prompt='''<describe task>

      🔴 CRITICAL - Report Results:
      from htmlgraph import SDK
      sdk = SDK(agent='subagent')
      sdk.spikes.create('Task Results') \\
          .set_findings('...') \\
          .save()
      ''',
      subagent_type='{suggested_agent}'
  )

Why delegate?
  - Reduces orchestrator context usage
  - Enables parallel execution
  - Improves cost efficiency
  - Follows delegation pattern

To disable warnings:
  - Set HTMLGRAPH_DISABLE_DELEGATION_WARNINGS=1
  - Or: uv run htmlgraph orchestrator disable
"""

    if context:
        warning += f"\nContext: {context}\n"

    return warning


def show_delegation_warning(
    tool_name: str, params: dict[str, Any] | None = None
) -> None:
    """
    Display delegation warning if appropriate.

    Args:
        tool_name: Name of the tool being executed
        params: Tool parameters (optional, for context)
    """
    if not should_show_delegation_warning():
        return

    # Extract context from params
    context = ""
    if params:
        if "file_path" in params:
            context = f"File: {params['file_path']}"
        elif "pattern" in params:
            context = f"Pattern: {params['pattern']}"
        elif "command" in params:
            cmd = params["command"]
            if len(cmd) > 80:
                cmd = cmd[:77] + "..."
            context = f"Command: {cmd}"

    warning = get_delegation_warning(tool_name, context)
    # Use logger to output to stderr
    logger.warning(warning)


def track_tool_execution(tool_name: str, params: dict[str, Any] | None = None) -> None:
    """
    Track tool execution and show delegation warning if needed.

    This is the main entry point for tracking tool usage in orchestrator mode.

    Args:
        tool_name: Name of the tool being executed
        params: Tool parameters (optional)
    """
    # Only track direct tool execution, not SDK operations
    tracked_tools = [
        "Read",
        "Write",
        "Edit",
        "NotebookEdit",
        "Grep",
        "Glob",
        "Bash",
    ]

    if tool_name not in tracked_tools:
        return

    show_delegation_warning(tool_name, params)


__all__ = [
    "is_orchestrator_mode_active",
    "is_in_subagent_context",
    "should_show_delegation_warning",
    "get_delegation_warning",
    "show_delegation_warning",
    "track_tool_execution",
]
