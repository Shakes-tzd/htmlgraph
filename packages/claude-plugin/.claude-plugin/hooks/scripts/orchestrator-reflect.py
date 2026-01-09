#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Orchestrator Reflection Hook

Detects when Claude executes Python code directly via Bash and provides
a gentle reflection prompt to encourage delegation to subagents.

This helps reinforce orchestrator patterns:
- Delegation over direct execution
- Parallel Task() calls for efficiency
- Work item tracking for all efforts
"""

import json
import os
import re
import sys

# Check if tracking is disabled
if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({"continue": True}))
    sys.exit(0)


def is_python_execution(command: str) -> bool:
    """
    Detect if a bash command is executing Python code.

    Patterns to detect:
    - uv run <script>
    - python -c <code>
    - python <script>
    - pytest
    - python -m <module>

    Excludes:
    - git commands (even if they mention python)
    - simple tool calls that happen to have "python" in path
    """
    # Normalize command
    cmd = command.strip().lower()

    # Exclude git commands entirely
    if cmd.startswith("git ") or " git " in cmd:
        return False

    # Exclude simple file operations
    if cmd.startswith(("ls ", "cat ", "grep ", "find ")):
        return False

    # Check for Python execution patterns
    python_patterns = [
        r"\buv\s+run\b",  # uv run <anything>
        r"\bpython\s+-c\b",  # python -c "code"
        r"\bpython\s+[\w/.-]+\.py\b",  # python script.py
        r"\bpython\s+-m\s+\w+",  # python -m module
        r"\bpytest\b",  # pytest
        r"\bpython3\s+",  # python3 command
    ]

    for pattern in python_patterns:
        if re.search(pattern, cmd):
            return True

    return False


def should_reflect(hook_input: dict) -> tuple[bool, str]:
    """
    Check if we should show reflection prompt.

    Returns:
        (should_show, command_preview) tuple
    """
    tool_name = hook_input.get("tool_name", "")

    # Only check Bash tool usage
    if tool_name != "Bash":
        return False, ""

    # Get the command
    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        return False, ""

    # Check if it's Python execution
    if is_python_execution(command):
        # Create a preview of the command (first 60 chars)
        preview = command[:60].replace("\n", " ")
        if len(command) > 60:
            preview += "..."
        return True, preview

    return False, ""


def build_reflection_message(command_preview: str) -> str:
    """
    Build the reflection message for orchestrator.

    This should be:
    - Gentle and non-blocking
    - Encourage reflection without being preachy
    - Point to specific alternatives
    """
    return f"""ORCHESTRATOR REFLECTION: You executed code directly.

Command: {command_preview}

Ask yourself:
- Could this have been delegated to a subagent?
- Would parallel Task() calls have been faster?
- Is a work item tracking this effort?

Continue, but consider delegation for similar future tasks."""


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    # Check if we should reflect
    should_show, command_preview = should_reflect(hook_input)

    # Build response
    response = {"continue": True}

    if should_show:
        reflection = build_reflection_message(command_preview)
        response["hookSpecificOutput"] = {
            "hookEventName": "PostToolUse",
            "additionalContext": reflection,
        }

    # Output JSON response
    print(json.dumps(response))


if __name__ == "__main__":
    main()
