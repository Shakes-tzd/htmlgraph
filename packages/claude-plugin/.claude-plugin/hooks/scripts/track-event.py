#!/usr/bin/env -S uv run --with htmlgraph>=0.26.0
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
