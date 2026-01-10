#!/usr/bin/env -S uv run --with htmlgraph>=0.25.0
"""
HtmlGraph Event Tracker

Unified script for tracking tool calls, stops, and user queries.
Uses htmlgraph Python API directly for all storage operations.
Includes drift detection and auto-classification support.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({"continue": True}))
    sys.exit(0)


def _resolve_project_dir(cwd: str | None = None) -> str:
    """
    Prefer Claude's project dir env var; fall back to git root; then cwd.
    """
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
    """
    Make `htmlgraph` importable in two common modes:
    - Running inside the htmlgraph repo (src/python)
    - Running in a project where htmlgraph is installed (do nothing)
    """
    # If the project uses a local venv, add its site-packages so imports work
    # even when hooks execute with system python.
    venv = Path(project_dir) / ".venv"
    if venv.exists():
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidates = [
            venv / "lib" / pyver / "site-packages",  # mac/linux
            venv / "Lib" / "site-packages",  # windows
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
    from htmlgraph.ids import generate_id
    from htmlgraph.session_manager import SessionManager
except Exception as e:
    # Do not break Claude execution if the dependency isn't installed.
    print(
        f"Warning: HtmlGraph not available ({e}). Install with: pip install htmlgraph",
        file=sys.stderr,
    )
    print(json.dumps({"continue": True}))
    sys.exit(0)


# Drift classification queue (stored in session directory)
DRIFT_QUEUE_FILE = "drift-queue.json"
# Active parent activity tracker (for Skill/Task invocations)
PARENT_ACTIVITY_FILE = "parent-activity.json"
# UserQuery event tracker (for parent-child linking)
# NOTE: This is a legacy global file name - now replaced with session-scoped files
USER_QUERY_EVENT_FILE = "user-query-event.json"


def get_user_query_event_file(graph_dir: Path, session_id: str) -> Path:
    """Get the session-scoped user query event file path."""
    return graph_dir / f"user-query-event-{session_id}.json"


def load_drift_config() -> dict:
    """Load drift configuration from plugin config or project .claude directory."""
    config_paths = [
        Path(__file__).parent.parent.parent / "config" / "drift-config.json",
        Path(os.environ.get("CLAUDE_PROJECT_DIR", ""))
        / ".claude"
        / "config"
        / "drift-config.json",
        Path(os.environ.get("CLAUDE_PLUGIN_ROOT", "")) / "config" / "drift-config.json",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return json.load(f)
            except Exception:
                pass

    # Default config
    return {
        "drift_detection": {
            "enabled": True,
            "warning_threshold": 0.7,
            "auto_classify_threshold": 0.85,
            "min_activities_before_classify": 3,
            "cooldown_minutes": 10,
        },
        "classification": {"enabled": True, "use_haiku_agent": True},
        "queue": {
            "max_pending_classifications": 5,
            "max_age_hours": 48,
            "process_on_stop": True,
            "process_on_threshold": True,
        },
    }


def load_parent_activity(graph_dir: Path) -> dict:
    """Load the active parent activity state."""
    path = graph_dir / PARENT_ACTIVITY_FILE
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
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


def load_user_query_event(graph_dir: Path, session_id: str) -> str | None:
    """
    Load the active UserQuery event ID for parent-child linking.

    Session-scoped: Each session maintains its own parent context via
    user-query-event-{SESSION_ID}.json to support multiple concurrent
    Claude windows in the same project.
    """
    path = get_user_query_event_file(graph_dir, session_id)
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
                # Clean up stale UserQuery events (older than 2 minutes)
                if data.get("timestamp"):
                    ts = datetime.fromisoformat(data["timestamp"])
                    # UserQuery events expire after 2 minutes (conversation turn boundary)
                    if datetime.now() - ts > timedelta(minutes=2):
                        return None
                return data.get("event_id")
        except Exception:
            pass
    return None


def save_user_query_event(
    graph_dir: Path, session_id: str, event_id: str | None
) -> None:
    """
    Save the active UserQuery event ID for parent-child linking.

    Session-scoped: Each session maintains its own parent context via
    user-query-event-{SESSION_ID}.json to support multiple concurrent
    Claude windows in the same project.
    """
    path = get_user_query_event_file(graph_dir, session_id)
    try:
        if event_id:
            with open(path, "w") as f:
                json.dump(
                    {
                        "event_id": event_id,
                        "timestamp": datetime.now().isoformat(),
                    },
                    f,
                )
        else:
            # Clear UserQuery event
            path.unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning: Could not save UserQuery event: {e}", file=sys.stderr)


def load_drift_queue(graph_dir: Path, max_age_hours: int = 48) -> dict:
    """
    Load the drift queue from file and clean up stale entries.

    Args:
        graph_dir: Path to .htmlgraph directory
        max_age_hours: Maximum age in hours before activities are removed (default: 48)

    Returns:
        Drift queue dict with only recent activities
    """
    queue_path = graph_dir / DRIFT_QUEUE_FILE
    if queue_path.exists():
        try:
            with open(queue_path) as f:
                queue = json.load(f)

            # Filter out stale activities
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            original_count = len(queue.get("activities", []))

            fresh_activities = []
            for activity in queue.get("activities", []):
                try:
                    activity_time = datetime.fromisoformat(
                        activity.get("timestamp", "")
                    )
                    if activity_time >= cutoff_time:
                        fresh_activities.append(activity)
                except (ValueError, TypeError):
                    # Keep activities with invalid timestamps to avoid data loss
                    fresh_activities.append(activity)

            # Update queue if we removed stale entries
            if len(fresh_activities) < original_count:
                queue["activities"] = fresh_activities
                save_drift_queue(graph_dir, queue)
                removed = original_count - len(fresh_activities)
                print(
                    f"Cleaned {removed} stale drift queue entries (older than {max_age_hours}h)",
                    file=sys.stderr,
                )

            return queue
        except Exception:
            pass
    return {"activities": [], "last_classification": None}


def save_drift_queue(graph_dir: Path, queue: dict) -> None:
    """Save the drift queue to file."""
    queue_path = graph_dir / DRIFT_QUEUE_FILE
    try:
        with open(queue_path, "w") as f:
            json.dump(queue, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Could not save drift queue: {e}", file=sys.stderr)


def clear_drift_queue_activities(graph_dir: Path) -> None:
    """
    Clear activities from the drift queue after successful classification.

    This removes stale entries that have been processed, preventing indefinite accumulation.
    """
    queue_path = graph_dir / DRIFT_QUEUE_FILE
    try:
        # Load existing queue to preserve last_classification timestamp
        queue = {"activities": [], "last_classification": datetime.now().isoformat()}
        if queue_path.exists():
            with open(queue_path) as f:
                existing = json.load(f)
                # Preserve the classification timestamp if it exists
                if existing.get("last_classification"):
                    queue["last_classification"] = existing["last_classification"]

        # Save cleared queue
        with open(queue_path, "w") as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not clear drift queue: {e}", file=sys.stderr)


def add_to_drift_queue(graph_dir: Path, activity: dict, config: dict) -> dict:
    """Add a high-drift activity to the queue."""
    max_age_hours = config.get("queue", {}).get("max_age_hours", 48)
    queue = load_drift_queue(graph_dir, max_age_hours=max_age_hours)
    max_pending = config.get("queue", {}).get("max_pending_classifications", 5)

    queue["activities"].append(
        {
            "timestamp": datetime.now().isoformat(),
            "tool": activity.get("tool"),
            "summary": activity.get("summary"),
            "file_paths": activity.get("file_paths", []),
            "drift_score": activity.get("drift_score"),
            "feature_id": activity.get("feature_id"),
        }
    )

    # Keep only recent activities
    queue["activities"] = queue["activities"][-max_pending:]
    save_drift_queue(graph_dir, queue)
    return queue


def should_trigger_classification(queue: dict, config: dict) -> bool:
    """Check if we should trigger auto-classification."""
    drift_config = config.get("drift_detection", {})

    if not config.get("classification", {}).get("enabled", True):
        return False

    min_activities = drift_config.get("min_activities_before_classify", 3)
    cooldown_minutes = drift_config.get("cooldown_minutes", 10)

    # Check minimum activities threshold
    if len(queue.get("activities", [])) < min_activities:
        return False

    # Check cooldown
    last_classification = queue.get("last_classification")
    if last_classification:
        try:
            last_time = datetime.fromisoformat(last_classification)
            if datetime.now() - last_time < timedelta(minutes=cooldown_minutes):
                return False
        except Exception:
            pass

    return True


def build_classification_prompt(queue: dict, feature_id: str) -> str:
    """Build the prompt for the classification agent."""
    activities = queue.get("activities", [])

    activity_lines = []
    for act in activities:
        line = f"- {act.get('tool', 'unknown')}: {act.get('summary', 'no summary')}"
        if act.get("file_paths"):
            line += f" (files: {', '.join(act['file_paths'][:2])})"
        line += f" [drift: {act.get('drift_score', 0):.2f}]"
        activity_lines.append(line)

    return f"""Classify these high-drift activities into a work item.

Current feature context: {feature_id}

Recent activities with high drift:
{chr(10).join(activity_lines)}

Based on the activity patterns:
1. Determine the work item type (bug, feature, spike, chore, or hotfix)
2. Create an appropriate title and description
3. Create the work item HTML file in .htmlgraph/

Use the classification rules:
- bug: fixing errors, incorrect behavior
- feature: new functionality, additions
- spike: research, exploration, investigation
- chore: maintenance, refactoring, cleanup
- hotfix: urgent production issues

Create the work item now using Write tool."""


def resolve_project_path(cwd: str | None = None) -> str:
    """Resolve project path (git root or cwd)."""
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


def extract_file_paths(tool_input: dict, tool_name: str) -> list[str]:
    """Extract file paths from tool input based on tool type."""
    paths = []

    # Common path fields
    for field in ["file_path", "path", "filepath"]:
        if field in tool_input:
            paths.append(tool_input[field])

    # Glob/Grep patterns
    if "pattern" in tool_input and tool_name in ["Glob", "Grep"]:
        pattern = tool_input.get("pattern", "")
        if "." in pattern:
            paths.append(f"pattern:{pattern}")

    # Bash commands - extract paths heuristically
    if tool_name == "Bash" and "command" in tool_input:
        cmd = tool_input["command"]
        file_matches = re.findall(r"[\w./\-_]+\.[a-zA-Z]{1,5}", cmd)
        paths.extend(file_matches[:3])

    return paths


def record_event_to_sqlite(
    db,
    session_id: str,
    tool_name: str,
    tool_input: dict,
    tool_response: dict,
    is_error: bool,
    file_paths: list[str] | None = None,
    parent_event_id: str | None = None,
    agent_id: str | None = None,
    subagent_type: str | None = None,
) -> str | None:
    """
    Record a tool call event to SQLite database for dashboard queries.

    Args:
        db: HtmlGraphDB instance
        session_id: Session ID from HtmlGraph
        tool_name: Name of the tool called
        tool_input: Tool input parameters
        tool_response: Tool response/result
        is_error: Whether the tool call resulted in an error
        file_paths: File paths affected by the tool
        parent_event_id: Parent event ID if this is a child event
        agent_id: Agent identifier (optional)
        subagent_type: Subagent type for Task delegations (optional)

    Returns:
        event_id if successful, None otherwise
    """
    try:
        event_id = generate_id("event")
        input_summary = format_tool_summary(tool_name, tool_input, tool_response)

        # Build output summary from tool response
        output_summary = ""
        if isinstance(tool_response, dict):
            if is_error:
                output_summary = tool_response.get("error", "error")[:200]
            else:
                # Extract summary from response
                content = tool_response.get("content", tool_response.get("output", ""))
                if isinstance(content, str):
                    output_summary = content[:200]
                elif isinstance(content, list):
                    output_summary = f"{len(content)} items"
                else:
                    output_summary = "success"

        # Build context metadata
        context = {
            "file_paths": file_paths or [],
            "tool_input_keys": list(tool_input.keys()),
            "is_error": is_error,
        }

        # Insert event to SQLite
        success = db.insert_event(
            event_id=event_id,
            agent_id=agent_id or "claude-code",
            event_type="tool_call",
            session_id=session_id,
            tool_name=tool_name,
            input_summary=input_summary,
            output_summary=output_summary,
            context=context,
            parent_event_id=parent_event_id,
            cost_tokens=0,
            subagent_type=subagent_type,
        )

        if success:
            return event_id
        return None

    except Exception as e:
        print(f"Warning: Could not record event to SQLite: {e}", file=sys.stderr)
        return None


def format_tool_summary(
    tool_name: str, tool_input: dict, tool_result: dict = None
) -> str:
    """Format a human-readable summary of the tool call."""
    # Normalize tool_name to handle whitespace or None
    tool_name = (tool_name or "").strip()

    if tool_name == "Read":
        path = tool_input.get("file_path", "unknown")
        return f"Read: {path}"

    elif tool_name == "Write":
        path = tool_input.get("file_path", "unknown")
        return f"Write: {path}"

    elif tool_name == "Edit":
        path = tool_input.get("file_path", "unknown")
        old = tool_input.get("old_string", "")[:30]
        return f"Edit: {path} ({old}...)"

    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")[:60]
        desc = tool_input.get("description", "")
        if desc:
            return f"Bash: {desc}"
        return f"Bash: {cmd}"

    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        return f"Glob: {pattern}"

    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        return f"Grep: {pattern}"

    elif tool_name == "Task":
        desc = tool_input.get("description", "")[:50]
        agent = tool_input.get("subagent_type", "")
        return f"Task ({agent}): {desc}"

    elif tool_name == "TodoWrite":
        todos = tool_input.get("todos", [])
        return f"TodoWrite: {len(todos)} items"

    elif tool_name == "WebSearch":
        query = tool_input.get("query", "")[:40]
        return f"WebSearch: {query}"

    elif tool_name == "WebFetch":
        url = tool_input.get("url", "")[:40]
        return f"WebFetch: {url}"

    elif tool_name == "UserQuery":
        # Extract the actual prompt text from the tool_input
        try:
            prompt = str(tool_input.get("prompt", ""))
            preview = prompt[:100].replace("\n", " ")
            if len(prompt) > 100:
                preview += "..."
            return preview
        except Exception:
            # Fallback if tool_input is not a dict (defensive programming)
            pass

    # Default: format as tool: input
    # Special case: if tool_input looks like a UserQuery, extract just the prompt
    if isinstance(tool_input, dict) and "prompt" in tool_input:
        try:
            prompt = str(tool_input.get("prompt", ""))
            preview = prompt[:100].replace("\n", " ")
            if len(prompt) > 100:
                preview += "..."
            return preview
        except Exception:
            pass

    return f"{tool_name}: {str(tool_input)[:50]}"


def output_response(nudge: str | None = None) -> None:
    """Output JSON response."""
    response: dict = {"continue": True}

    if nudge:
        response["hookSpecificOutput"] = {
            "hookEventName": os.environ.get("HTMLGRAPH_HOOK_TYPE", "PostToolUse"),
            "additionalContext": nudge,
        }
    print(json.dumps(response))


def main():
    hook_type = os.environ.get("HTMLGRAPH_HOOK_TYPE", "PostToolUse")

    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    cwd = hook_input.get("cwd")
    project_dir = _resolve_project_dir(cwd if cwd else None)
    graph_dir = Path(project_dir) / ".htmlgraph"

    # Load drift configuration
    drift_config = load_drift_config()

    # Initialize SessionManager
    try:
        manager = SessionManager(graph_dir)
    except Exception as e:
        print(f"Warning: Could not initialize SessionManager: {e}", file=sys.stderr)
        output_response()
        return

    # Initialize SQLite database for event recording
    db = None
    try:
        db = HtmlGraphDB(str(graph_dir / "htmlgraph.db"))
    except Exception as e:
        print(f"Warning: Could not initialize SQLite database: {e}", file=sys.stderr)
        # Continue without SQLite (graceful degradation)

    # Detect agent from environment
    detected_agent = os.environ.get("HTMLGRAPH_AGENT", "claude-code")

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

    # Ensure session exists in SQLite database (for foreign key constraints)
    if db:
        try:
            db.insert_session(
                session_id=active_session_id,
                agent_assigned=getattr(active_session, "agent", None) or detected_agent,
                is_subagent=getattr(active_session, "is_subagent", False),
                transcript_id=getattr(active_session, "transcript_id", None),
                transcript_path=getattr(active_session, "transcript_path", None),
            )
        except Exception:
            # Session may already exist, that's OK - continue
            pass

    # Handle different hook types
    if hook_type == "Stop":
        # Session is ending - track stop event
        try:
            manager.track_activity(
                session_id=active_session_id, tool="Stop", summary="Agent stopped"
            )

            # Record to SQLite if available
            if db:
                record_event_to_sqlite(
                    db=db,
                    session_id=active_session_id,
                    tool_name="Stop",
                    tool_input={},
                    tool_response={"content": "Agent stopped"},
                    is_error=False,
                    agent_id=detected_agent,
                )
        except Exception as e:
            print(f"Warning: Could not track stop: {e}", file=sys.stderr)
        output_response()
        return

    elif hook_type == "UserPromptSubmit":
        # User submitted a query
        prompt = hook_input.get("prompt", "")
        preview = prompt[:100].replace("\n", " ")
        if len(prompt) > 100:
            preview += "..."

        try:
            manager.track_activity(
                session_id=active_session_id, tool="UserQuery", summary=f'"{preview}"'
            )

            # Record to SQLite if available and capture event_id for parent-child linking
            user_query_event_id = None
            if db:
                user_query_event_id = record_event_to_sqlite(
                    db=db,
                    session_id=active_session_id,
                    tool_name="UserQuery",
                    tool_input={"prompt": prompt},
                    tool_response={"content": "Query received"},
                    is_error=False,
                    agent_id=detected_agent,
                )

                # Store the UserQuery event_id for subsequent tool calls to use as parent
                if user_query_event_id:
                    save_user_query_event(
                        graph_dir, active_session_id, user_query_event_id
                    )

        except Exception as e:
            print(f"Warning: Could not track query: {e}", file=sys.stderr)
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

        # Extract file paths
        file_paths = extract_file_paths(tool_input_data, tool_name)

        # Format summary
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
                # Check for exit code patterns (e.g., "Exit code 1", "exit status 1")
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
            # We'll get the event_id after tracking, so we use a placeholder for now
            # The actual parent_id will be set below after we track the activity
            is_parent_tool = True
        else:
            is_parent_tool = False
            # Check environment variable FIRST for cross-process parent linking
            # This is set by PreToolUse hook when Task() spawns a subagent
            env_parent = os.environ.get("HTMLGRAPH_PARENT_EVENT")
            if env_parent:
                parent_activity_id = env_parent
            # Fall back to file-based parent context if no env var set
            elif parent_activity_state.get("parent_id"):
                parent_activity_id = parent_activity_state["parent_id"]
            # Finally, check for UserQuery event as parent (for prompt-based grouping)
            elif not parent_activity_id:
                user_query_event_id = load_user_query_event(
                    graph_dir, active_session_id
                )
                if user_query_event_id:
                    parent_activity_id = user_query_event_id

        # Track the activity
        nudge = None
        try:
            result = manager.track_activity(
                session_id=active_session_id,
                tool=tool_name,
                summary=summary,
                file_paths=file_paths if file_paths else None,
                success=not is_error,
                parent_activity_id=parent_activity_id,
            )

            # Record to SQLite if available
            if db:
                # Extract subagent_type for Task delegations
                task_subagent_type = None
                if tool_name == "Task":
                    task_subagent_type = tool_input_data.get(
                        "subagent_type", "general-purpose"
                    )

                record_event_to_sqlite(
                    db=db,
                    session_id=active_session_id,
                    tool_name=tool_name,
                    tool_input=tool_input_data,
                    tool_response=tool_response,
                    is_error=is_error,
                    file_paths=file_paths if file_paths else None,
                    parent_event_id=parent_activity_id,  # Link to parent event
                    agent_id=detected_agent,
                    subagent_type=task_subagent_type,
                )

            # If this was a parent tool, save its ID for subsequent activities
            if is_parent_tool and result:
                save_parent_activity(graph_dir, result.id, tool_name)
            # If this tool finished a parent context (e.g., Task completed), clear it
            # We'll clear parent context after 5 minutes automatically (see load_parent_activity)

            # Check for drift and handle accordingly
            # Skip drift detection for child activities (they inherit parent's context)
            if result and hasattr(result, "drift_score") and not parent_activity_id:
                drift_score = result.drift_score
                feature_id = getattr(result, "feature_id", "unknown")

                if drift_score and drift_score >= auto_classify_threshold:
                    # High drift - add to classification queue
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

                    # Check if we should trigger classification
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
                                        # Prevent hooks from writing new HtmlGraph sessions/events
                                        # when we spawn nested `claude` processes.
                                        "HTMLGRAPH_DISABLE_TRACKING": "1",
                                    },
                                )
                                if result.returncode == 0:
                                    nudge = "Drift auto-classification completed. Check .htmlgraph/ for new work item."
                                    # Clear the queue after successful classification
                                    clear_drift_queue_activities(graph_dir)
                                else:
                                    # Fallback to manual prompt
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

                        # Mark classification as triggered
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
