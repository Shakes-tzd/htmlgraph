#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
HtmlGraph Event Tracker

Unified script for tracking tool calls, stops, and user queries.
Uses htmlgraph Python API directly for all storage operations.
Includes drift detection and auto-classification support.

Thin wrapper around SDK event_tracker module. All business logic lives in:
    htmlgraph.hooks.event_tracker
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Bootstrap Python path and setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bootstrap import bootstrap_pythonpath, is_tracking_disabled, resolve_project_dir

if is_tracking_disabled():
    print(json.dumps({"continue": True}))
    sys.exit(0)

project_dir_for_import = resolve_project_dir()
bootstrap_pythonpath(project_dir_for_import)

try:
    from htmlgraph.session_manager import SessionManager
except Exception as e:
    # Do not break Claude execution if the dependency isn't installed.
    print(
        f"Warning: HtmlGraph not available ({e}). Install with: pip install htmlgraph",
        file=sys.stderr,
    )
    print(json.dumps({"continue": True}))
    sys.exit(0)

# Import drift/classification helpers from SDK event_tracker
from htmlgraph.hooks.event_tracker import (
    add_to_drift_queue,
    build_classification_prompt,
    clear_drift_queue_activities,
    extract_file_paths,
    format_tool_summary,
    load_drift_config,
    save_drift_queue,
    should_trigger_classification,
)

# Active parent activity tracker (for Skill/Task invocations)
PARENT_ACTIVITY_FILE = "parent-activity.json"


def load_parent_activity(graph_dir: Path) -> dict[str, Any]:
    """Load the active parent activity state."""
    path = graph_dir / PARENT_ACTIVITY_FILE
    if path.exists():
        try:
            with open(path) as f:
                data: dict[str, Any] = json.load(f)
                # Clean up stale parent activities (older than 5 minutes)
                if data.get("timestamp"):
                    ts = datetime.fromisoformat(data["timestamp"])
                    if datetime.now() - ts > timedelta(minutes=5):
                        return {}
                return data
        except Exception:
            pass
    return {}


def save_parent_activity(
    graph_dir: Path, parent_id: str | None, tool: str | None = None
) -> None:
    """Save the active parent activity state."""
    path = graph_dir / PARENT_ACTIVITY_FILE
    try:
        if parent_id:
            with open(path, "w") as f:
                json.dump(
                    {
                        "parent_id": parent_id,
                        "tool": tool,
                        "timestamp": datetime.now().isoformat(),
                    },
                    f,
                )
        else:
            # Clear parent activity
            path.unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning: Could not save parent activity: {e}", file=sys.stderr)


def output_response(nudge: str | None = None) -> None:
    """Output JSON response."""
    response: dict = {"continue": True}

    if nudge:
        response["hookSpecificOutput"] = {
            "hookEventName": os.environ.get("HTMLGRAPH_HOOK_TYPE", "PostToolUse"),
            "additionalContext": nudge,
        }
    print(json.dumps(response))


def main() -> None:
    hook_type = os.environ.get("HTMLGRAPH_HOOK_TYPE", "PostToolUse")

    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    cwd = hook_input.get("cwd")
    project_dir = resolve_project_dir(cwd if cwd else None)
    graph_dir = Path(project_dir) / ".htmlgraph"

    # Load drift configuration (SDK)
    drift_config = load_drift_config()

    # Initialize SessionManager
    try:
        manager = SessionManager(graph_dir)
    except Exception as e:
        print(f"Warning: Could not initialize SessionManager: {e}", file=sys.stderr)
        output_response()
        return

    # Get active session ID
    active_session = manager.get_active_session()
    if not active_session:
        # No active HtmlGraph session yet; start one (stable internal id).
        try:
            active_session = manager.start_session(
                session_id=None,
                agent="claude-code",
                title=f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )
        except Exception:
            output_response()
            return

    active_session_id = active_session.id

    # Handle different hook types
    if hook_type == "Stop":
        # Session is ending - get current commit and end session
        try:
            # Get current commit hash
            end_commit = None
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=project_dir,
                    timeout=5,
                )
                if result.returncode == 0:
                    end_commit = result.stdout.strip()
            except Exception:
                pass

            # End the session with commit info
            manager.end_session(session_id=active_session_id, end_commit=end_commit)
        except Exception as e:
            print(f"Warning: Could not end session: {e}", file=sys.stderr)
        output_response()
        return

    elif hook_type == "UserPromptSubmit":
        # User submitted a query
        prompt = hook_input.get("prompt", "")
        preview = prompt[:100].replace("\n", " ")
        if len(prompt) > 100:
            preview += "..."

        # Use HookContext for correct session ID resolution
        try:
            from htmlgraph.hooks.context import HookContext

            context = HookContext.from_input(hook_input)
            resolved_session_id = context.session_id

            print(
                f"DEBUG UserPromptSubmit: hook_input session_id={hook_input.get('session_id')}, "
                f"resolved session_id={resolved_session_id}",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"Warning: Could not resolve session via HookContext: {e}",
                file=sys.stderr,
            )
            resolved_session_id = active_session_id

        try:
            result = manager.track_activity(
                session_id=resolved_session_id, tool="UserQuery", summary=f'"{preview}"'
            )
            print(
                f"DEBUG UserPromptSubmit: tracked successfully, event_id={result.id if result else 'None'}",
                file=sys.stderr,
            )

            # Record to SQLite agent_events table (CRITICAL for Activity Feed)
            # This creates the UserQuery parent event that the Activity Feed groups by
            try:
                from htmlgraph.db.schema import HtmlGraphDB
                from htmlgraph.hooks.event_tracker import record_event_to_sqlite

                db = HtmlGraphDB(graph_dir / "htmlgraph.db")
                db.connect()

                # Record UserQuery event to agent_events table
                event_id = record_event_to_sqlite(
                    db=db,
                    session_id=resolved_session_id,
                    tool_name="UserQuery",
                    tool_input={"prompt": prompt},
                    tool_response={"content": "Query received"},
                    is_error=False,
                    agent_id="claude-code",
                    model=None,
                    feature_id=result.feature_id if result else None,
                )

                print(
                    f"DEBUG UserPromptSubmit: Recorded to agent_events, event_id={event_id}",
                    file=sys.stderr,
                )

                # Create event data for dashboard display
                event_data = {
                    "tool": "UserQuery",
                    "summary": preview,
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                }

                # Insert live event for WebSocket real-time dashboard
                db.insert_live_event(
                    event_type="user_query",
                    event_data=event_data,
                    parent_event_id=event_id,
                    session_id=resolved_session_id,
                    spawner_type=None,
                )

                db.disconnect()
            except Exception as e:
                # Don't fail the hook if database insertion fails
                print(
                    f"Warning: Could not record UserQuery to database: {e}",
                    file=sys.stderr,
                )
                import traceback

                traceback.print_exc(file=sys.stderr)

        except Exception as e:
            print(f"Warning: Could not track query: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
        output_response()
        return

    elif hook_type == "PostToolUse":
        # Tool was used - track it
        tool_name = hook_input.get("tool_name", "unknown")
        tool_input_data = hook_input.get("tool_input", {})
        tool_response = (
            hook_input.get("tool_response", hook_input.get("tool_result", {})) or {}
        )

        # Skip tracking for some tools
        skip_tools = {"AskUserQuestion"}
        if tool_name in skip_tools:
            output_response()
            return

        # Use HookContext for correct session ID resolution in PostToolUse
        try:
            from htmlgraph.hooks.context import HookContext

            context = HookContext.from_input(hook_input)
            resolved_session_id = context.session_id

            print(
                f"DEBUG PostToolUse: hook_input session_id={hook_input.get('session_id')}, "
                f"resolved session_id={resolved_session_id}, "
                f"active_session_id={active_session_id}",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"Warning: Could not resolve session via HookContext: {e}",
                file=sys.stderr,
            )
            resolved_session_id = active_session_id

        # Extract file paths (SDK)
        file_paths = extract_file_paths(tool_input_data, tool_name)

        # Format summary (SDK)
        summary = format_tool_summary(tool_name, tool_input_data, tool_response)

        # Determine success
        if isinstance(tool_response, dict):
            success_field = tool_response.get("success")
            if isinstance(success_field, bool):
                is_error = not success_field
            else:
                is_error = bool(tool_response.get("is_error", False))

            # Additional check for Bash failures: detect non-zero exit codes
            if tool_name == "Bash" and not is_error:
                output = str(
                    tool_response.get("output", "") or tool_response.get("content", "")
                )
                if re.search(
                    r"Exit code [1-9]\d*|exit status [1-9]\d*", output, re.IGNORECASE
                ):
                    is_error = True
        else:
            # For list or other non-dict responses (like Playwright), assume success
            is_error = False

        # Get drift thresholds from config
        drift_settings = drift_config.get("drift_detection", {})
        warning_threshold = drift_settings.get("warning_threshold", 0.7)
        auto_classify_threshold = drift_settings.get("auto_classify_threshold", 0.85)

        # Determine parent activity context
        parent_activity_state = load_parent_activity(graph_dir)
        parent_activity_id = None

        # Tools that create parent context (Skill, Task)
        parent_tools = {"Skill", "Task"}

        # If this is a parent tool invocation, save its context for subsequent activities
        if tool_name in parent_tools:
            is_parent_tool = True
        else:
            is_parent_tool = False
            # Check if there's an active parent context
            if parent_activity_state.get("parent_id"):
                parent_activity_id = parent_activity_state["parent_id"]

        # Track the activity
        nudge = None
        try:
            result = manager.track_activity(
                session_id=resolved_session_id,
                tool=tool_name,
                summary=summary,
                file_paths=file_paths if file_paths else None,
                success=not is_error,
                parent_activity_id=parent_activity_id,
            )

            # Record live event for WebSocket real-time dashboard
            try:
                from htmlgraph.db.schema import HtmlGraphDB

                db = HtmlGraphDB(graph_dir / "htmlgraph.db")
                db.connect()

                # Create event data for dashboard display
                event_data = {
                    "tool": tool_name,
                    "summary": summary,
                    "success": not is_error,
                    "feature_id": result.feature_id if result else None,
                    "drift_score": result.drift_score
                    if result and hasattr(result, "drift_score")
                    else None,
                    "file_paths": file_paths,
                    "timestamp": datetime.now().isoformat(),
                }

                # Insert live event (event_type matches what dashboard expects)
                db.insert_live_event(
                    event_type="tool_call",
                    event_data=event_data,
                    parent_event_id=parent_activity_id,
                    session_id=resolved_session_id,
                    spawner_type=None,  # Regular tool calls don't have spawner_type
                )

                db.disconnect()
            except Exception as e:
                # Don't fail the hook if live event insertion fails
                print(f"Warning: Could not record live event: {e}", file=sys.stderr)

            # If this was a parent tool, save its ID for subsequent activities
            if is_parent_tool and result:
                save_parent_activity(graph_dir, result.id, tool_name)

            # Check for drift and handle accordingly (using SDK helpers)
            # Skip drift detection for child activities (they inherit parent's context)
            if result and hasattr(result, "drift_score") and not parent_activity_id:
                drift_score = result.drift_score
                feature_id = getattr(result, "feature_id", "unknown")

                if drift_score and drift_score >= auto_classify_threshold:
                    # High drift - add to classification queue (SDK)
                    queue = add_to_drift_queue(
                        graph_dir,
                        {
                            "tool": tool_name,
                            "summary": summary,
                            "file_paths": file_paths,
                            "drift_score": drift_score,
                            "feature_id": feature_id,
                        },
                        drift_config,
                    )

                    # Check if we should trigger classification (SDK)
                    if should_trigger_classification(queue, drift_config):
                        classification_prompt = build_classification_prompt(
                            queue, feature_id
                        )

                        # Try to run headless classification
                        use_headless = drift_config.get("classification", {}).get(
                            "use_headless", True
                        )
                        if use_headless:
                            try:
                                # Run claude in print mode for classification
                                result = subprocess.run(
                                    [
                                        "claude",
                                        "-p",
                                        classification_prompt,
                                        "--model",
                                        "haiku",
                                        "--dangerously-skip-permissions",
                                    ],
                                    capture_output=True,
                                    text=True,
                                    timeout=120,
                                    cwd=str(graph_dir.parent),
                                    env={
                                        **os.environ,
                                        "HTMLGRAPH_DISABLE_TRACKING": "1",
                                    },
                                )
                                if result.returncode == 0:
                                    nudge = "Drift auto-classification completed. Check .htmlgraph/ for new work item."
                                    # Clear the queue after successful classification (SDK)
                                    clear_drift_queue_activities(graph_dir)
                                else:
                                    nudge = f"""HIGH DRIFT ({drift_score:.2f}) - Headless classification failed.

{len(queue["activities"])} activities don't align with '{feature_id}'.

Please classify manually: bug, feature, spike, or chore in .htmlgraph/"""
                            except Exception as e:
                                nudge = f"Drift classification error: {e}. Please classify manually."
                        else:
                            nudge = f"""HIGH DRIFT DETECTED ({drift_score:.2f}) - Auto-classification triggered.

{len(queue["activities"])} activities don't align with '{feature_id}'.

ACTION REQUIRED: Spawn a Haiku agent to classify this work:
```
Task tool with subagent_type="general-purpose", model="haiku", prompt:
{classification_prompt[:500]}...
```

Or manually create a work item in .htmlgraph/ (bug, feature, spike, or chore)."""

                        # Mark classification as triggered (SDK)
                        queue["last_classification"] = datetime.now().isoformat()
                        save_drift_queue(graph_dir, queue)
                    else:
                        nudge = f"Drift detected ({drift_score:.2f}): Activity queued for classification ({len(queue['activities'])}/{drift_settings.get('min_activities_before_classify', 3)} needed)."

                elif drift_score > warning_threshold:
                    # Moderate drift - just warn
                    nudge = f"Drift detected ({drift_score:.2f}): Activity may not align with {feature_id}. Consider refocusing or updating the feature."

        except Exception as e:
            print(f"Warning: Could not track activity: {e}", file=sys.stderr)

        output_response(nudge)
        return

    # Unknown hook type
    output_response()


if __name__ == "__main__":
    main()
