#!/usr/bin/env python3
"""
HtmlGraph Status Line for Claude Code

Displays context tracking information including:
- Current model and context usage
- Active HtmlGraph session and feature
- Activity counts and drift detection
- Work type breakdown

Usage:
    Configure in .claude/settings.json:
    {
        "statusLine": {
            "type": "command",
            "command": "python3 ~/.htmlgraph/scripts/statusline.py"
        }
    }

Input: JSON from Claude Code via stdin (see context_window, model, etc.)
Output: Single line with ANSI colors for terminal display
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Colors
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Bright colors
BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Background colors
BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"


def get_context_percentage(data: dict) -> tuple[int, str]:
    """Calculate context window usage percentage and color."""
    context = data.get("context_window", {})
    context_size = context.get("context_window_size", 200000)
    usage = context.get("current_usage")

    if usage is None:
        return 0, GREEN

    # Calculate tokens in current context
    current_tokens = (
        usage.get("input_tokens", 0) +
        usage.get("cache_creation_input_tokens", 0) +
        usage.get("cache_read_input_tokens", 0)
    )

    percent = int(current_tokens * 100 / context_size) if context_size > 0 else 0

    # Color based on usage
    if percent >= 80:
        color = BRIGHT_RED
    elif percent >= 60:
        color = BRIGHT_YELLOW
    elif percent >= 40:
        color = YELLOW
    else:
        color = GREEN

    return percent, color


def find_htmlgraph_dir() -> Path | None:
    """Find .htmlgraph directory from current working directory."""
    try:
        current = Path.cwd()

        # Check current directory
        if (current / ".htmlgraph").exists():
            return current / ".htmlgraph"

        # Check parent directories
        for parent in current.parents:
            if (parent / ".htmlgraph").exists():
                return parent / ".htmlgraph"
    except Exception:
        pass

    return None


def record_context_snapshot(htmlgraph_dir: Path, data: dict, feature_id: str | None) -> None:
    """
    Record a context snapshot to the active session.

    This enables context analytics to track usage over time.
    Runs asynchronously to not slow down status line display.
    """
    try:
        # Only record if we have meaningful context data
        context = data.get("context_window", {})
        usage = context.get("current_usage")
        if not usage:
            return

        # Import SDK and record snapshot
        sys.path.insert(0, str(htmlgraph_dir.parent / "src" / "python"))
        from htmlgraph import SDK, ContextSnapshot

        sdk = SDK(directory=htmlgraph_dir)
        session = sdk.session_manager.get_active_session()

        if session:
            # Create snapshot from Claude Code input
            snapshot = ContextSnapshot.from_claude_input(
                data,
                trigger="status_update",
                feature_id=feature_id
            )

            # Record to session (with sampling to avoid bloat)
            session.record_context(snapshot, sample_interval=10)

            # Save session back to disk
            from htmlgraph.converter import SessionConverter
            converter = SessionConverter(htmlgraph_dir / "sessions")
            converter.save(session)

    except Exception:
        # Silently fail - recording shouldn't break status line
        pass


def get_htmlgraph_context(htmlgraph_dir: Path, input_data: dict | None = None) -> dict:
    """Get current HtmlGraph session and feature context."""
    context = {
        "session": None,
        "feature": None,
        "activity_count": 0,
        "drift_score": None,
        "work_type": None,
    }

    try:
        # Try to import SDK
        sys.path.insert(0, str(htmlgraph_dir.parent / "src" / "python"))
        from htmlgraph import SDK

        sdk = SDK(directory=htmlgraph_dir)

        # Get active session
        active_session = sdk.session_manager.get_active_session()
        if active_session:
            context["session"] = {
                "id": active_session.id[:12] + "..." if len(active_session.id) > 15 else active_session.id,
                "full_id": active_session.id,
                "agent": active_session.agent,
                "event_count": active_session.event_count,
                "status": active_session.status,
                "work_type": active_session.primary_work_type,
                "peak_context": active_session.peak_context_tokens,
                "total_cost": active_session.total_cost_usd,
            }
            context["activity_count"] = active_session.event_count
            context["work_type"] = active_session.primary_work_type

            # Get worked on features
            if active_session.worked_on:
                context["feature"] = active_session.worked_on[-1]  # Most recent (last)

            # Record context snapshot if we have input data
            if input_data:
                record_context_snapshot(htmlgraph_dir, input_data, context.get("feature"))

        # Check drift queue for high-drift activities
        drift_queue_path = htmlgraph_dir / "drift-queue.json"
        if drift_queue_path.exists():
            with open(drift_queue_path) as f:
                drift_data = json.load(f)
                activities = drift_data.get("activities", [])
                if activities:
                    # Average drift score of pending items
                    total_drift = sum(a.get("drift_score", 0) for a in activities)
                    context["drift_score"] = total_drift / len(activities) if activities else None
                    context["drift_count"] = len(activities)

    except ImportError:
        # SDK not available, try direct file access
        pass
    except Exception as e:
        # Silently fail - status line should not break
        pass

    return context


def format_work_type(work_type: str | None) -> str:
    """Format work type with emoji."""
    if not work_type:
        return ""

    emoji_map = {
        "feature": "✨",
        "bugfix": "🐛",
        "refactor": "♻️",
        "docs": "📝",
        "test": "🧪",
        "chore": "🔧",
        "review": "👀",
        "debug": "🔍",
    }

    emoji = emoji_map.get(work_type.lower(), "📋")
    return f"{emoji}{work_type}"


def format_status_line(data: dict) -> str:
    """Format the complete status line."""
    parts = []

    # Model name
    model = data.get("model", {})
    model_name = model.get("display_name", "Claude")
    parts.append(f"{CYAN}{model_name}{RESET}")

    # Context usage
    percent, color = get_context_percentage(data)
    if percent > 0:
        parts.append(f"{color}{percent}%{RESET}")

    # Git branch (if available)
    try:
        git_head = Path(".git/HEAD")
        if git_head.exists():
            ref = git_head.read_text().strip()
            if ref.startswith("ref: refs/heads/"):
                branch = ref.replace("ref: refs/heads/", "")
                # Truncate long branch names
                if len(branch) > 25:
                    branch = branch[:22] + "..."
                parts.append(f"{MAGENTA}{branch}{RESET}")
    except Exception:
        pass

    # HtmlGraph context (also records context snapshot)
    htmlgraph_dir = find_htmlgraph_dir()
    if htmlgraph_dir:
        hg_context = get_htmlgraph_context(htmlgraph_dir, input_data=data)

        # Session info
        session = hg_context.get("session")
        if session:
            agent = session.get("agent", "")
            event_count = session.get("event_count", 0)
            parts.append(f"{BRIGHT_BLUE}[{agent}:{event_count}]{RESET}")

        # Current feature
        feature = hg_context.get("feature")
        if feature:
            feat_short = feature[:12] + "..." if len(feature) > 15 else feature
            parts.append(f"{YELLOW}{feat_short}{RESET}")

        # Work type
        work_type = hg_context.get("work_type")
        if work_type:
            parts.append(f"{GREEN}{format_work_type(work_type)}{RESET}")

        # Drift warning
        drift_count = hg_context.get("drift_count", 0)
        if drift_count > 0:
            parts.append(f"{BRIGHT_YELLOW}⚠{drift_count}{RESET}")

    # Cost (if significant)
    cost = data.get("cost", {})
    total_cost = cost.get("total_cost_usd", 0)
    if total_cost >= 0.01:
        parts.append(f"{DIM}${total_cost:.2f}{RESET}")

    return " │ ".join(parts)


def main():
    """Main entry point."""
    try:
        # Read JSON from stdin
        input_data = json.load(sys.stdin)

        # Format and print status line
        status = format_status_line(input_data)
        print(status)

    except json.JSONDecodeError:
        # Invalid JSON, show minimal status
        print(f"{CYAN}Claude{RESET}")
    except Exception as e:
        # Any other error, show minimal status
        print(f"{CYAN}Claude{RESET} {DIM}(error){RESET}")


if __name__ == "__main__":
    main()
