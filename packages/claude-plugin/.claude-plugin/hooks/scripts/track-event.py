#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
HtmlGraph Event Tracker - Thin Shell Wrapper

This script is a minimal wrapper around the htmlgraph.hooks package.
All logic is delegated to reusable modules:

- htmlgraph.hooks.context: HookContext for environment setup and resource management
- htmlgraph.hooks.event_tracker: track_event() for unified event tracking
- htmlgraph.hooks.bootstrap: init_logger() for logging setup

The wrapper handles:
1. Graceful degradation when htmlgraph is not installed
2. Disable tracking via HTMLGRAPH_DISABLE_TRACKING environment variable
3. JSON input/output for Claude Code hook system
4. Exception handling with continue: true fallback
"""

import json
import os
import sys

# Check if tracking is disabled
if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({"continue": True}))
    sys.exit(0)

try:
    from htmlgraph.hooks.bootstrap import (
        bootstrap_pythonpath,
        init_logger,
        resolve_project_dir,
    )
    from htmlgraph.hooks.event_tracker import track_event
except ImportError as e:
    # Graceful degradation: htmlgraph not available
    print(
        f"Warning: HtmlGraph not available ({e}). Install with: pip install htmlgraph",
        file=sys.stderr,
    )
    print(json.dumps({"continue": True}))
    sys.exit(0)


def detect_model_from_input(hook_input: dict) -> str | None:
    """
    Detect the Claude model from hook input.

    Checks:
    1. Task() model parameter (if tool_name == 'Task')
    2. Environment variables (ANTHROPIC_MODEL, CLAUDE_MODEL, HTMLGRAPH_MODEL)

    Args:
        hook_input: Hook input dict containing tool_name and tool_input

    Returns:
        Model name (e.g., 'claude-opus', 'claude-sonnet') or None
    """
    # Get tool info
    tool_name = hook_input.get("tool_name", "") or hook_input.get("name", "")
    tool_input = hook_input.get("tool_input", {}) or hook_input.get("input", {})

    # 1. Check for Task() model parameter
    if tool_name == "Task" and "model" in tool_input:
        model = tool_input.get("model")
        if model and isinstance(model, str):
            model = model.strip().lower()
            if not model.startswith("claude-"):
                model = f"claude-{model}"
            return model

    # 2. Check environment variables
    for env_var in ["HTMLGRAPH_MODEL", "ANTHROPIC_MODEL", "CLAUDE_MODEL"]:
        model = os.environ.get(env_var)
        if model and isinstance(model, str):
            model = model.strip()
            if model:
                return model

    return None


def main() -> None:
    """Main entry point for the hook script."""
    # Initialize logging
    logger = init_logger(__name__)

    # Bootstrap Python path for imports
    project_dir = resolve_project_dir()
    bootstrap_pythonpath(project_dir)

    # Get hook type from environment
    hook_type = os.environ.get("HTMLGRAPH_HOOK_TYPE", "PostToolUse")

    # Load hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    try:
        # Delegate to event tracker
        response = track_event(hook_type, hook_input)
        print(json.dumps(response))
    except Exception as e:
        # Log error but continue execution (graceful degradation)
        logger.error(f"Error tracking event: {e}", exc_info=True)
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
