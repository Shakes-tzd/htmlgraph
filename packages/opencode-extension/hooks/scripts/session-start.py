#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
HtmlGraph Session Start Hook for OpenCode

Records session start and provides feature context to OpenCode.
Uses htmlgraph Python API directly for all storage operations.

Architecture:
- HTML files = Single source of truth
- htmlgraph Python API = Feature/session management
- No external database required
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({}))
    sys.exit(0)


def check_htmlgraph_version() -> tuple[str | None, str | None, bool]:
    """
    Check if installed htmlgraph version matches latest on PyPI.

    Returns:
        (installed_version, latest_version, is_outdated)
    """
    installed_version = None
    latest_version = None

    # Get installed version
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "import htmlgraph; print(htmlgraph.__version__)",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            installed_version = result.stdout.strip()
    except Exception:
        # Fallback to pip show
        try:
            result = subprocess.run(
                ["pip", "show", "htmlgraph"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith("Version:"):
                        installed_version = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

    # Get latest version from PyPI
    try:
        import urllib.request

        req = urllib.request.Request(
            "https://pypi.org/pypi/htmlgraph/json",
            headers={"User-Agent": "htmlgraph-hook-version-check"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            latest_version = data["info"]["version"]
    except Exception:
        pass

    is_outdated = (
        installed_version and latest_version and installed_version != latest_version
    )

    return installed_version, latest_version, is_outdated


def generate_session_context() -> dict:
    """Generate comprehensive session context for OpenCode."""
    from htmlgraph import SDK

    # Detect project root
    project_root = Path.cwd()
    htmlgraph_dir = project_root / ".htmlgraph"

    if not htmlgraph_dir.exists():
        return {"has_htmlgraph": False}

    try:
        # Initialize SDK
        sdk = SDK(agent="opencode")

        # Get comprehensive session start info
        session_start_info = sdk.get_session_start_info()

        # Check for handoff context (simplified - not currently implemented)
        handoff_context = None

        # Get version info
        installed_version, latest_version, is_outdated = check_htmlgraph_version()

        return {
            "has_htmlgraph": True,
            "session_info": session_start_info,
            "handoff_context": handoff_context,
            "version_info": {
                "installed": installed_version,
                "latest": latest_version,
                "is_outdated": is_outdated,
            },
            "agent": "opencode",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        # Return minimal info on error
        return {
            "has_htmlgraph": True,
            "error": str(e),
            "agent": "opencode",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def format_opencode_message(context: dict) -> str:
    """Format context as a message for OpenCode."""
    if not context.get("has_htmlgraph"):
        return ""

    lines = [
        "",
        "---",
        "",
        "## HTMLGRAPH DEVELOPMENT PROCESS ACTIVE",
        "",
        "**CRITICAL: HtmlGraph is tracking this session. Read OPENCODE.md for complete instructions.**",
        "",
        "### Feature Creation Decision Framework",
        "",
        "**Use this framework for EVERY user request:**",
        "",
        "Create a **FEATURE** if ANY apply:",
        "- >30 minutes work",
        "- 3+ files",
        "- New tests needed",
        "- Multi-component impact",
        "- Hard to revert",
        "- Needs docs",
        "",
        "Implement **DIRECTLY** if ALL apply:",
        "- Single file",
        "- <30 minutes",
        "- Trivial change",
        "- Easy to revert",
        "- No tests needed",
        "",
        "**When in doubt, CREATE A FEATURE.** Over-tracking is better than losing attribution.",
        "",
        "---",
        "",
        "### Quick Reference",
        "",
        "**IMPORTANT:** Always use `uv run` when running htmlgraph commands.",
        "",
        "**Check Status:**",
        "```bash",
        "uv run htmlgraph status",
        "uv run htmlgraph feature list",
        "uv run htmlgraph session list",
        "```",
        "",
        "**Work Item Commands:**",
        "- `uv run htmlgraph feature start <id>` - Start working on a feature",
        "- `uv run htmlgraph feature complete <id>` - Mark feature as done",
        "",
        "**Dashboard:**",
        "```bash",
        "uv run htmlgraph serve",
        "# Open http://localhost:8080",
        "```",
        "",
        "---",
        "",
    ]

    # Add session info if available
    if "session_info" in context:
        session_info = context["session_info"]
        if isinstance(session_info, str):
            lines.extend(
                [
                    session_info,
                    "",
                ]
            )
        elif isinstance(session_info, dict):
            # Format dict version
            lines.append("### Project Status")
            lines.append("")
            if "status" in session_info:
                status = session_info["status"]
                if isinstance(status, dict):
                    for key, value in status.items():
                        lines.append(f"- {key}: {value}")
                    lines.append("")
            if "recommendations" in session_info:
                lines.append("**Recommendations:**")
                lines.append("")
                recommendations = session_info["recommendations"]
                if isinstance(recommendations, list):
                    for rec in recommendations:
                        lines.append(f"- {rec}")
                    lines.append("")

    # Add handoff context if available
    if context.get("handoff_context"):
        handoff = context["handoff_context"]
        lines.extend(
            [
                "## Handoff Context",
                "",
                f"**From:** {handoff.get('from_agent', 'Unknown')}",
                f"**Feature:** {handoff.get('feature_id', 'Unknown')}",
                f"**Reason:** {handoff.get('reason', 'Unknown')}",
                "",
            ]
        )
        if handoff.get("notes"):
            lines.extend(
                [
                    "**Notes:**",
                    handoff["notes"],
                    "",
                ]
            )
        lines.append("---")
        lines.append("")

    # Add version warning if outdated
    version_info = context.get("version_info", {})
    if version_info.get("is_outdated"):
        lines.extend(
            [
                "⚠️ **HtmlGraph Update Available**",
                "",
                f"Installed: {version_info.get('installed')}",
                f"Latest: {version_info.get('latest')}",
                "",
                "Update with: `uv pip install --upgrade htmlgraph`",
                "",
                "---",
                "",
            ]
        )

    lines.extend(
        [
            "## Session Continuity",
            "",
            "HtmlGraph is tracking all activity to this session. Activities are automatically attributed to in-progress features.",
            "",
            "**REMEMBER:**",
            "1. Start features before coding: `uv run htmlgraph feature start <id>`",
            "2. Mark steps complete immediately using SDK",
            "3. Complete features when done: `uv run htmlgraph feature complete <id>`",
            "",
            "See OPENCODE.md for complete workflow and SDK usage instructions.",
            "",
            "---",
            "",
        ]
    )

    return "\n".join(lines)


def main():
    """Main hook execution."""
    try:
        # Generate context
        context = generate_session_context()

        # Output JSON for tool integration and message for user
        output = {
            "context": context,
            "message": format_opencode_message(context),
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
        sys.exit(0)  # Don't fail session start due to hook issues


if __name__ == "__main__":
    main()
