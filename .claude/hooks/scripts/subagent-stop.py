#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
HtmlGraph SubagentStop Hook - Capture Delegated Task Completions

This hook fires when a subagent spawned via Task() completes.
It creates agent_events records for the subagent delegation completion.

KNOWN LIMITATIONS (GitHub issue #7881, #14859):
- SubagentStop cannot identify which specific subagent finished
- All subagents share the same session_id
- No agent_id, parent_id, or subagent_type fields available

WORKAROUND STRATEGY:
1. Parse transcript_path to extract task description/results
2. Look for most recent pending Task invocation in events
3. Create "subagent_delegation" event with extracted info
4. Mark status as "completed" (inferred from SubagentStop firing)

This provides partial visibility into delegated work until Claude Code
implements the enhancements proposed in GitHub issue #14859.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Skip tracking if disabled
if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({"continue": True}))
    sys.exit(0)


def _resolve_project_dir(cwd: str | None = None) -> str:
    """Prefer Claude's project dir env var; fall back to git root; then cwd."""
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        return env_dir
    start_dir = cwd or os.getcwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=start_dir,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return start_dir


def _bootstrap_pythonpath(project_dir: str) -> None:
    """Make htmlgraph importable from local dev or venv."""
    venv = Path(project_dir) / ".venv"
    if venv.exists():
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidates = [
            venv / "lib" / pyver / "site-packages",
            venv / "Lib" / "site-packages",
        ]
        for c in candidates:
            if c.exists():
                sys.path.insert(0, str(c))

    repo_src = Path(project_dir) / "src" / "python"
    if repo_src.exists():
        sys.path.insert(0, str(repo_src))


project_dir_for_import = _resolve_project_dir()
_bootstrap_pythonpath(project_dir_for_import)

try:
    from htmlgraph.db.schema import HtmlGraphDB
except Exception as e:
    print(
        f"Warning: HtmlGraph not available ({e}). Install with: pip install htmlgraph",
        file=sys.stderr,
    )
    print(json.dumps({"continue": True}))
    sys.exit(0)


def generate_event_id() -> str:
    """Generate unique event ID for subagent completion."""
    import uuid

    return f"subevt-{uuid.uuid4().hex[:8]}"


def parse_transcript(transcript_path: str) -> dict[str, Any]:
    """
    Parse transcript file to extract task information.

    Args:
        transcript_path: Path to transcript .jsonl file

    Returns:
        Dict with extracted task info (description, results, subagent_type)
    """
    result = {
        "description": "Unknown task",
        "subagent_type": "general-purpose",
        "results_summary": "",
        "tool_count": 0,
        "success": True,
    }

    if not transcript_path or not Path(transcript_path).exists():
        return result

    try:
        with open(transcript_path) as f:
            lines = f.readlines()

        # Parse JSONL entries
        for line in lines:
            try:
                entry = json.loads(line.strip())

                # Look for task description in first user message
                if entry.get("type") == "user" and not result.get("found_description"):
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, str) and len(content) > 0:
                        # Extract first 200 chars as description
                        desc = content[:200]
                        if len(content) > 200:
                            desc += "..."
                        result["description"] = desc
                        result["found_description"] = True

                        # Try to extract task ID from description (pattern: TASK-XXXXXXXX:)
                        task_id_match = re.search(r"(TASK-[a-f0-9]{8}):", content)
                        if task_id_match:
                            result["task_id"] = task_id_match.group(1)

                # Count tool uses
                if entry.get("type") == "tool_use":
                    tool_count = int(result.get("tool_count", 0))
                    result["tool_count"] = tool_count + 1

                # Check for errors
                if entry.get("type") == "error" or entry.get("is_error"):
                    result["success"] = False

                # Get last assistant message as results summary
                if entry.get("type") == "assistant":
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, str) and len(content) > 0:
                        summary = content[:500]
                        if len(content) > 500:
                            summary += "..."
                        result["results_summary"] = summary

            except json.JSONDecodeError:
                continue

    except Exception as e:
        print(f"Warning: Could not parse transcript: {e}", file=sys.stderr)

    return result


def find_pending_task_invocation(
    db: HtmlGraphDB, session_id: str
) -> dict[str, Any] | None:
    """
    Find most recent Task tool invocation that might correlate with this SubagentStop.

    This is a workaround for the limitation that SubagentStop doesn't identify
    which subagent completed. We look for Task tool_calls and try to match.

    Args:
        db: Database connection
        session_id: Session ID from hook input

    Returns:
        Task event dict or None
    """
    if not db.connection:
        db.connect()

    try:
        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Find recent Task tool calls in this session
        cursor.execute(
            """
            SELECT event_id, tool_name, input_summary, timestamp, status
            FROM agent_events
            WHERE session_id = ?
              AND tool_name = 'Task'
              AND status != 'subagent_completed'
            ORDER BY timestamp DESC
            LIMIT 1
        """,
            (session_id,),
        )

        row = cursor.fetchone()
        if row:
            return {
                "event_id": row[0],
                "tool_name": row[1],
                "input_summary": row[2],
                "timestamp": row[3],
                "status": row[4],
            }

    except Exception as e:
        print(f"Warning: Could not query pending tasks: {e}", file=sys.stderr)

    return None


def extract_subagent_type_from_input(input_summary: str) -> str:
    """
    Try to extract subagent_type from Task tool input summary.

    Args:
        input_summary: JSON string of tool input

    Returns:
        Subagent type string or "general-purpose"
    """
    try:
        if input_summary:
            data = json.loads(input_summary)
            subagent_type = data.get("subagent_type", "general-purpose")
            return str(subagent_type) if subagent_type else "general-purpose"
    except (json.JSONDecodeError, TypeError):
        # Try regex extraction
        match = re.search(r'"subagent_type":\s*"([^"]+)"', input_summary or "")
        if match:
            return match.group(1)
    return "general-purpose"


def count_child_spikes(
    db: HtmlGraphDB,
    parent_event_id: str,
    parent_timestamp: str,
) -> int:
    """
    Count spikes created by subagent after parent event timestamp.

    Args:
        db: Database connection
        parent_event_id: Parent event ID
        parent_timestamp: Parent event timestamp (ISO format)

    Returns:
        Count of child spikes created after parent event
    """
    try:
        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Count features (spikes) created after parent event
        # This assumes spikes are stored in features table with type='spike'
        cursor.execute(
            """
            SELECT COUNT(*) FROM features
            WHERE type = 'spike'
              AND created_at > ?
            LIMIT 100
        """,
            (parent_timestamp,),
        )

        row = cursor.fetchone()
        count = row[0] if row else 0
        return count

    except Exception as e:
        print(f"Warning: Could not count child spikes: {e}", file=sys.stderr)
        return 0


def create_subagent_completion_event(
    db: HtmlGraphDB,
    session_id: str,
    transcript_info: dict[str, Any],
    parent_task: dict[str, Any] | None = None,
) -> str | None:
    """
    Create agent_events record for subagent completion.

    Also updates parent Task event with completion status and
    child spike count for parent-child event nesting.

    Args:
        db: Database connection
        session_id: Session ID from hook input
        transcript_info: Parsed transcript information
        parent_task: Parent Task event if found

    Returns:
        Event ID if successful, None otherwise
    """
    if not db.connection:
        db.connect()

    try:
        event_id = generate_event_id()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Determine subagent type
        subagent_type = transcript_info.get("subagent_type", "general-purpose")
        if parent_task:
            subagent_type = extract_subagent_type_from_input(
                parent_task.get("input_summary", "")
            )

        # Build agent_id from subagent type
        agent_id = f"subagent-{subagent_type}"

        # Build input summary
        input_summary = json.dumps(
            {
                "task_description": transcript_info.get("description", ""),
                "subagent_type": subagent_type,
                "tool_count": transcript_info.get("tool_count", 0),
                "task_id": transcript_info.get("task_id"),
            }
        )[:500]

        # Build output summary
        output_summary = transcript_info.get("results_summary", "")[:500]

        # Ensure session exists
        db._ensure_session_exists(session_id, agent_id)

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert subagent completion event
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             input_summary, output_summary, session_id, status,
             parent_event_id, subagent_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event_id,
                agent_id,
                "delegation",  # Use 'delegation' event type (allowed in schema)
                timestamp,
                "SubagentStop",  # Tool name indicates this is a subagent completion
                input_summary,
                output_summary,
                session_id,
                "completed" if transcript_info.get("success", True) else "error",
                parent_task.get("event_id") if parent_task else None,
                subagent_type,
            ),
        )

        # Update parent Task event status if found
        if parent_task:
            parent_event_id = parent_task.get("event_id")
            parent_timestamp = parent_task.get("timestamp", "")

            # Count child spikes created during subagent execution
            child_spike_count = count_child_spikes(
                db, parent_event_id, parent_timestamp
            )

            # Build output summary for parent event
            parent_output = json.dumps(
                {
                    "subagent_type": subagent_type,
                    "spikes_created": child_spike_count,
                    "completion_time": timestamp,
                }
            )[:500]

            cursor.execute(
                """
                UPDATE agent_events
                SET status = 'completed',
                    child_spike_count = ?,
                    output_summary = ?
                WHERE event_id = ?
            """,
                (child_spike_count, parent_output, parent_event_id),
            )

        db.connection.commit()  # type: ignore[union-attr]

        return event_id

    except Exception as e:
        print(f"Warning: Could not create subagent event: {e}", file=sys.stderr)
        return None


def main() -> None:
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    session_id = hook_input.get("session_id") or os.environ.get("HTMLGRAPH_SESSION_ID")
    transcript_path = hook_input.get("transcript_path")
    cwd = hook_input.get("cwd")

    project_dir = _resolve_project_dir(cwd if cwd else None)
    graph_dir = Path(project_dir) / ".htmlgraph"
    db_path = str(graph_dir / "index.sqlite")

    # Initialize database
    try:
        db = HtmlGraphDB(db_path)
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}", file=sys.stderr)
        print(json.dumps({"continue": True}))
        return

    # Parse transcript if available
    transcript_info = {}
    if transcript_path:
        transcript_info = parse_transcript(transcript_path)

    # Try to find parent Task invocation
    parent_task = None
    if session_id:
        parent_task = find_pending_task_invocation(db, session_id)

    # Create subagent completion event
    event_id = None
    if session_id:
        event_id = create_subagent_completion_event(
            db, session_id, transcript_info, parent_task
        )

    # Close database
    db.disconnect()

    # Build response
    response: dict[str, Any] = {"continue": True}

    if event_id:
        subagent_type = transcript_info.get("subagent_type", "general-purpose")
        if parent_task:
            subagent_type = extract_subagent_type_from_input(
                parent_task.get("input_summary", "")
            )

        response["hookSpecificOutput"] = {
            "hookEventName": "SubagentStop",
            "additionalContext": (
                f"Subagent completed: {subagent_type}\n"
                f"Event ID: {event_id}\n"
                f"Tools used: {transcript_info.get('tool_count', 0)}\n"
                f"Status: {'success' if transcript_info.get('success', True) else 'error'}"
            ),
        }

    print(json.dumps(response))


if __name__ == "__main__":
    main()
