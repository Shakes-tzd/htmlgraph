#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
HtmlGraph Session Start Hook - Thin Shell Wrapper

Delegates session initialization to htmlgraph.hooks.session_handler module.

This is now a thin wrapper (~45 lines) that:
1. Loads hook input from stdin
2. Creates HookContext
3. Initializes/retrieves session via session_handler
4. Builds session start response
5. Merges and outputs JSON

All heavy lifting delegated to:
- htmlgraph.hooks.context.HookContext
- htmlgraph.hooks.session_handler (init_or_get_session, handle_session_start, check_version_status)
- htmlgraph.hooks.bootstrap.init_logger
"""

import json
import os
import sys

if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({}))
    sys.exit(0)

try:
    from htmlgraph.hooks.bootstrap import init_logger
    from htmlgraph.hooks.context import HookContext
    from htmlgraph.hooks.session_handler import (
        handle_session_start,
        init_or_get_session,
    )
except ImportError as e:
    print(
        f"Warning: HtmlGraph not available ({e}). Install with: uv pip install htmlgraph",
        file=sys.stderr,
    )
    print(json.dumps({}))
    sys.exit(0)

from typing import Any

logger = init_logger(__name__)


def main() -> None:
    """
    Main hook entry point.

    Thin wrapper that:
    1. Loads hook input from stdin
    2. Creates HookContext from hook input
    3. Initializes or retrieves session
    4. Handles session start operations
    5. Outputs response as JSON
    """
    try:
        # Load hook input from stdin
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    try:
        # Create context from hook input
        context = HookContext.from_input(hook_input)

        # Initialize or retrieve session
        session = init_or_get_session(context)

        # Handle session start (builds feature context, checks version)
        session_output = handle_session_start(context, session)

        # Merge outputs
        output: dict[str, Any] = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "sessionFeatureContext": session_output.get(
                    "hookSpecificOutput", {}
                ).get("sessionFeatureContext", ""),
                "sessionContext": session_output.get("hookSpecificOutput", {}).get(
                    "sessionContext", ""
                ),
            },
        }

        # Add version info if available
        version_info = session_output.get("hookSpecificOutput", {}).get("versionInfo")
        if version_info:
            hook_output = output["hookSpecificOutput"]
            if isinstance(hook_output, dict):
                hook_output["versionInfo"] = version_info

        # Output response
        print(json.dumps(output))

    except Exception as e:
        logger.error(f"Session start hook failed: {e}")
        print(
            json.dumps(
                {
                    "continue": True,
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "error": str(e),
                    },
                }
            )
        )


if __name__ == "__main__":
    main()
