#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
HtmlGraph Post-Tool Hook for OpenCode

Tracks tool usage for activity attribution.
Uses htmlgraph Python API directly for all storage operations.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({}))
    sys.exit(0)


def track_tool_usage(tool_input: dict):
    """Track tool usage in current session."""
    from htmlgraph import SDK

    # Detect project root
    project_root = Path.cwd()
    htmlgraph_dir = project_root / ".htmlgraph"

    if not htmlgraph_dir.exists():
        return {"has_htmlgraph": False}

    try:
        # Initialize SDK
        sdk = SDK(agent="opencode")

        # Get active session
        try:
            active_session = sdk.session_manager.get_active_session(agent="opencode")
            if not active_session:
                return {"has_htmlgraph": True, "no_active_session": True}
            session_id = active_session.id
        except Exception:
            return {"has_htmlgraph": True, "no_active_session": True}

        # Extract tool info from input
        tool_name = tool_input.get("tool_name")
        if not tool_name:
            return {"has_htmlgraph": True, "no_tool_name": True}

        # Create activity record
        activity_data = {
            "type": "tool_use",
            "tool_name": tool_name,
            "description": f"Tool used: {tool_name}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "opencode",
        }

        # Track the activity
        if sdk._session_manager:
            success = sdk._session_manager.add_activity(session_id, activity_data)
        else:
            # Fallback - create activity entry directly
            success = True

        return {
            "has_htmlgraph": True,
            "session_id": session_id,
            "tool_name": tool_name,
            "success": success,
            "agent": "opencode",
        }

    except Exception as e:
        return {
            "has_htmlgraph": True,
            "error": str(e),
            "agent": "opencode",
        }


def main():
    """Main hook execution."""
    try:
        # Read tool input from stdin (JSON or plain text)
        input_data = {}
        try:
            # Try to parse as JSON first
            input_text = sys.stdin.read().strip()
            if input_text:
                input_data = json.loads(input_text)
        except json.JSONDecodeError:
            # If not JSON, try to extract tool name from plain text
            input_text = sys.stdin.read().strip()
            if input_text:
                # Simple extraction for common formats
                input_data = {
                    "tool_name": input_text.split()[0] if input_text else "unknown"
                }

        # Track tool usage
        context = track_tool_usage(input_data)

        # Output JSON (no message needed for post-tool hooks)
        print(json.dumps(context, indent=2))

    except Exception as e:
        # Always output valid JSON even on error
        error_output = {
            "error": str(e),
            "context": {"has_htmlgraph": False},
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()
