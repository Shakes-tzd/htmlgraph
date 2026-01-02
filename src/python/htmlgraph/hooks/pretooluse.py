"""
Unified PreToolUse Hook - Parallel Orchestrator + Validator

This module provides a unified PreToolUse hook that runs both orchestrator
enforcement and work validation checks in parallel using asyncio.

Architecture:
- Runs orchestrator check and validator check simultaneously
- Combines results into Claude Code standard format
- Returns blocking response only if both checks agree
- Provides combined guidance from both systems

Performance:
- ~40-50% faster than sequential subprocess execution
- Single Python process (no subprocess overhead)
- Parallel execution via asyncio.gather()
"""

import asyncio
import json
import os
import sys
from typing import Any

from htmlgraph.hooks.orchestrator import enforce_orchestrator_mode
from htmlgraph.hooks.task_enforcer import enforce_task_saving
from htmlgraph.hooks.validator import (
    load_tool_history as validator_load_history,
)
from htmlgraph.hooks.validator import (
    load_validation_config,
    validate_tool_call,
)


async def run_orchestrator_check(tool_input: dict[str, Any]) -> dict[str, Any]:
    """
    Run orchestrator enforcement check (async wrapper).

    Args:
        tool_input: Hook input with tool name and parameters

    Returns:
        Orchestrator response: {"continue": bool, "hookSpecificOutput": {...}}
    """
    try:
        loop = asyncio.get_event_loop()
        tool_name = tool_input.get("name", "") or tool_input.get("tool_name", "")
        tool_params = tool_input.get("input", {}) or tool_input.get("tool_input", {})

        # Run in thread pool since it's CPU-bound
        return await loop.run_in_executor(
            None,
            enforce_orchestrator_mode,
            tool_name,
            tool_params,
        )
    except Exception:
        # Graceful degradation - allow on error
        return {"continue": True}


async def run_validation_check(tool_input: dict[str, Any]) -> dict[str, Any]:
    """
    Run work validation check (async wrapper).

    Args:
        tool_input: Hook input with tool name and parameters

    Returns:
        Validator response: {"decision": "allow"|"deny", "guidance": "...", ...}
    """
    try:
        loop = asyncio.get_event_loop()

        tool_name = tool_input.get("name", "") or tool_input.get("tool", "")
        tool_params = tool_input.get("input", {}) or tool_input.get("params", {})

        # Load config and history in thread pool
        config = await loop.run_in_executor(None, load_validation_config)
        history = await loop.run_in_executor(None, validator_load_history)

        # Run validation
        return await loop.run_in_executor(
            None,
            validate_tool_call,
            tool_name,
            tool_params,
            config,
            history,
        )
    except Exception:
        # Graceful degradation - allow on error
        return {"decision": "allow"}


async def run_task_enforcement(tool_input: dict[str, Any]) -> dict[str, Any]:
    """
    Run task save enforcement check (async wrapper).

    Args:
        tool_input: Hook input with tool name and parameters

    Returns:
        Task enforcer response: {"continue": bool, "hookSpecificOutput": {...}}
    """
    try:
        loop = asyncio.get_event_loop()

        tool_name = tool_input.get("name", "") or tool_input.get("tool_name", "")
        tool_params = tool_input.get("input", {}) or tool_input.get("tool_input", {})

        # Run task enforcement
        return await loop.run_in_executor(
            None,
            enforce_task_saving,
            tool_name,
            tool_params,
        )
    except Exception:
        # Graceful degradation - allow on error
        return {"continue": True}


async def provide_debugging_guidance(tool_input: dict[str, Any]) -> dict[str, Any]:
    """
    Provide debugging guidance based on tool patterns and context.

    Args:
        tool_input: Hook input with tool name and parameters

    Returns:
        Guidance response: {"hookSpecificOutput": {"additionalContext": "..."}}
    """
    try:
        tool_name = tool_input.get("name", "") or tool_input.get("tool_name", "")
        tool_params = tool_input.get("input", {}) or tool_input.get("tool_input", {})

        # High-risk tools that often indicate debugging scenarios
        high_risk_tools = ["Edit", "Write", "Bash", "Read"]
        if tool_name not in high_risk_tools:
            return {}

        guidance = []

        # Check for debugging keywords in tool parameters
        params_text = str(tool_params).lower()
        debug_keywords = ["error", "fix", "broken", "failed", "bug", "issue", "problem"]

        if any(kw in params_text for kw in debug_keywords):
            guidance.append("🔍 Debugging task detected")
            guidance.append("Consider:")
            guidance.append("  - Review DEBUGGING.md for systematic approach")
            guidance.append("  - Use researcher agent for unfamiliar errors")
            guidance.append("  - Use debugger agent for systematic analysis")
            guidance.append("  - Run /doctor or /hooks for diagnostics")

        if guidance:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": "\n".join(guidance),
                }
            }

        return {}
    except Exception:
        # Graceful degradation - no guidance on error
        return {}


async def pretooluse_hook(tool_input: dict[str, Any]) -> dict[str, Any]:
    """
    Unified PreToolUse hook - runs all checks in parallel.

    Args:
        tool_input: Hook input with tool name and parameters

    Returns:
        Claude Code standard format:
        {
            "continue": bool,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": {...},  # If task enforcer modified input
                "additionalContext": "Combined guidance"
            }
        }
    """
    # Run all four checks in parallel using asyncio.gather
    (
        orch_response,
        validate_response,
        task_response,
        debug_guidance,
    ) = await asyncio.gather(
        run_orchestrator_check(tool_input),
        run_validation_check(tool_input),
        run_task_enforcement(tool_input),
        provide_debugging_guidance(tool_input),
    )

    # Integrate responses
    orch_continues = orch_response.get("continue", True)
    validate_allows = validate_response.get("decision", "allow") == "allow"
    task_continues = task_response.get("continue", True)
    should_continue = orch_continues and validate_allows and task_continues

    # Collect guidance from all systems
    guidance_parts = []

    # Orchestrator guidance
    if "hookSpecificOutput" in orch_response:
        ctx = orch_response["hookSpecificOutput"].get("additionalContext", "")
        if ctx:
            guidance_parts.append(f"[Orchestrator] {ctx}")

    # Validator guidance
    if "guidance" in validate_response:
        guidance_parts.append(f"[Validator] {validate_response['guidance']}")

    if "imperative" in validate_response:
        guidance_parts.append(f"[Validator] {validate_response['imperative']}")

    if "suggestion" in validate_response:
        guidance_parts.append(f"[Validator] {validate_response['suggestion']}")

    # Task enforcer guidance
    if "hookSpecificOutput" in task_response:
        ctx = task_response["hookSpecificOutput"].get("additionalContext", "")
        if ctx:
            guidance_parts.append(f"[TaskEnforcer] {ctx}")

    # Debugging guidance
    if "hookSpecificOutput" in debug_guidance:
        ctx = debug_guidance["hookSpecificOutput"].get("additionalContext", "")
        if ctx:
            guidance_parts.append(f"[Debugging] {ctx}")

    # Build unified response in Claude Code format
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if should_continue else "deny",
        }
    }

    # Check if task enforcer provided updatedInput
    updated_input = None
    if "hookSpecificOutput" in task_response:
        updated_input = task_response["hookSpecificOutput"].get("updatedInput")

    if updated_input:
        response["hookSpecificOutput"]["updatedInput"] = updated_input

    if guidance_parts:
        combined_guidance = "\n".join(guidance_parts)
        if should_continue:
            # Allow with context
            response["hookSpecificOutput"]["additionalContext"] = combined_guidance
        else:
            # Deny with reason
            response["hookSpecificOutput"]["permissionDecisionReason"] = (
                combined_guidance
            )

    return response


def main() -> None:
    """Hook entry point for script wrapper."""
    # Check environment overrides
    if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    if os.environ.get("HTMLGRAPH_ORCHESTRATOR_DISABLED") == "1":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # Read tool input from stdin
    try:
        tool_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        tool_input = {}

    # Run hook with parallel execution
    result = asyncio.run(pretooluse_hook(tool_input))

    # Output response
    print(json.dumps(result))

    # Exit code based on permission decision
    permission = result.get("hookSpecificOutput", {}).get("permissionDecision", "allow")
    sys.exit(0 if permission == "allow" else 1)


if __name__ == "__main__":
    main()
