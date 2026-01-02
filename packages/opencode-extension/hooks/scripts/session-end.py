#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
HtmlGraph Session End Hook for OpenCode

Finalizes session and optionally records handoff context.
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


def finalize_session():
    """Finalize the current session with optional handoff context."""
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
        sessions = sdk.session_manager.get_active_sessions()
        if not sessions:
            return {"has_htmlgraph": True, "no_active_session": True}

        session_id = sessions[0].get("id")
        if not session_id:
            return {"has_htmlgraph": True, "no_active_session": True}

        # Get handoff context from environment if provided
        handoff_notes = os.environ.get("HTMLGRAPH_HANDOFF_NOTES")
        handoff_recommend = os.environ.get("HTMLGRAPH_HANDOFF_RECOMMEND")
        handoff_blockers = os.environ.get("HTMLGRAPH_HANDOFF_BLOCKERS")

        # End the session with handoff context
        session_data = {"ended_at": datetime.now(timezone.utc).isoformat()}

        if handoff_notes:
            session_data["handoff_notes"] = handoff_notes
        if handoff_recommend:
            session_data["handoff_recommend"] = handoff_recommend
        if handoff_blockers:
            session_data["handoff_blockers"] = [
                b.strip() for b in handoff_blockers.split(",") if b.strip()
            ]

        # Use session manager to end session
        if sdk._session_manager:
            success = sdk._session_manager.end_session(session_id, session_data)
        else:
            # Fallback to basic session end
            success = True

        return {
            "has_htmlgraph": True,
            "session_id": session_id,
            "success": success,
            "has_handoff": bool(handoff_notes or handoff_recommend or handoff_blockers),
            "agent": "opencode",
        }

    except Exception as e:
        return {
            "has_htmlgraph": True,
            "error": str(e),
            "agent": "opencode",
        }


def format_session_message(context: dict) -> str:
    """Format session end message for OpenCode."""
    if not context.get("has_htmlgraph"):
        return ""

    lines = [
        "",
        "---",
        "",
        "## HtmlGraph Session Ended",
        "",
    ]

    if context.get("no_active_session"):
        lines.append("No active session found.")
        lines.append("")
        return "\n".join(lines)

    session_id = context.get("session_id", "unknown")
    lines.append(f"**Session:** {session_id}")
    lines.append("")

    if context.get("has_handoff"):
        lines.append("Handoff context recorded for next agent.")
        lines.append("")

    lines.extend(
        [
            "All activities have been tracked. View the session report:",
            "```bash",
            "uv run htmlgraph serve",
            "# Navigate to Sessions view",
            "```",
            "",
            "---",
            "",
        ]
    )

    return "\n".join(lines)


def main():
    """Main hook execution."""
    try:
        # Finalize session
        context = finalize_session()

        # Output JSON and message
        output = {
            "context": context,
            "message": format_session_message(context),
        }

        print(json.dumps(output, indent=2))

    except Exception as e:
        # Always output valid JSON even on error
        error_output = {
            "error": str(e),
            "context": {"has_htmlgraph": False},
            "message": "",
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()
