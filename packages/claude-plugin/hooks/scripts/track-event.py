#!/usr/bin/env python3
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
from typing import Optional

if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({"continue": True}))
    sys.exit(0)

def _resolve_project_dir(cwd: Optional[str] = None) -> str:
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
            venv / "lib" / pyver / "site-packages",   # mac/linux
            venv / "Lib" / "site-packages",           # windows
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
    from htmlgraph.session_manager import SessionManager
except Exception as e:
    # Do not break Claude execution if the dependency isn't installed.
    print(f"Warning: HtmlGraph not available ({e}). Install with: pip install htmlgraph", file=sys.stderr)
    print(json.dumps({"continue": True}))
    sys.exit(0)


# Drift classification queue (stored in session directory)
DRIFT_QUEUE_FILE = "drift-queue.json"


def load_drift_config() -> dict:
    """Load drift configuration from plugin config."""
    config_paths = [
        Path(__file__).parent.parent.parent / "config" / "drift-config.json",
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
            "cooldown_minutes": 10
        },
        "classification": {
            "enabled": True,
            "use_haiku_agent": True
        },
        "queue": {
            "max_pending_classifications": 5,
            "process_on_stop": True,
            "process_on_threshold": True
        }
    }


def load_drift_queue(graph_dir: Path) -> dict:
    """Load the drift queue from file."""
    queue_path = graph_dir / DRIFT_QUEUE_FILE
    if queue_path.exists():
        try:
            with open(queue_path) as f:
                return json.load(f)
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


def add_to_drift_queue(graph_dir: Path, activity: dict, config: dict) -> dict:
    """Add a high-drift activity to the queue."""
    queue = load_drift_queue(graph_dir)
    max_pending = config.get("queue", {}).get("max_pending_classifications", 5)

    queue["activities"].append({
        "timestamp": datetime.now().isoformat(),
        "tool": activity.get("tool"),
        "summary": activity.get("summary"),
        "file_paths": activity.get("file_paths", []),
        "drift_score": activity.get("drift_score"),
        "feature_id": activity.get("feature_id")
    })

    # Keep only recent activities
    queue["activities"] = queue["activities"][-max_pending:]
    save_drift_queue(graph_dir, queue)
    return queue


def should_trigger_classification(queue: dict, config: dict) -> bool:
    """Check if we should trigger auto-classification."""
    drift_config = config.get("drift_detection", {})
    queue_config = config.get("queue", {})

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
        if act.get('file_paths'):
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


def resolve_project_path(cwd: Optional[str] = None) -> str:
    """Resolve project path (git root or cwd)."""
    start_dir = cwd or os.getcwd()
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            cwd=start_dir,
            timeout=5
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
        file_matches = re.findall(r'[\w./\-_]+\.[a-zA-Z]{1,5}', cmd)
        paths.extend(file_matches[:3])

    return paths


def format_tool_summary(tool_name: str, tool_input: dict, tool_result: dict = None) -> str:
    """Format a human-readable summary of the tool call."""
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

    else:
        return f"{tool_name}: {str(tool_input)[:50]}"


def output_response(nudge: Optional[str] = None) -> None:
    """Output JSON response."""
    response: dict = {"continue": True}

    if nudge:
        response["hookSpecificOutput"] = {
            "hookEventName": os.environ.get("HTMLGRAPH_HOOK_TYPE", "PostToolUse"),
            "additionalContext": nudge
        }
    print(json.dumps(response))


def main():
    hook_type = os.environ.get("HTMLGRAPH_HOOK_TYPE", "PostToolUse")

    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    session_id = hook_input.get("session_id") or os.environ.get("CLAUDE_SESSION_ID", "unknown")
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
        # Session is ending - track stop event
        try:
            manager.track_activity(
                session_id=active_session_id,
                tool="Stop",
                summary="Agent stopped"
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
                session_id=active_session_id,
                tool="UserQuery",
                summary=f'"{preview}"'
            )
        except Exception as e:
            print(f"Warning: Could not track query: {e}", file=sys.stderr)
        output_response()
        return

    elif hook_type == "PostToolUse":
        # Tool was used - track it
        tool_name = hook_input.get("tool_name", "unknown")
        tool_input_data = hook_input.get("tool_input", {})
        tool_response = hook_input.get("tool_response", hook_input.get("tool_result", {})) or {}

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
        success_field = tool_response.get("success")
        if isinstance(success_field, bool):
            is_error = not success_field
        else:
            is_error = bool(tool_response.get("is_error", False))

        # Get drift thresholds from config
        drift_settings = drift_config.get("drift_detection", {})
        warning_threshold = drift_settings.get("warning_threshold", 0.7)
        auto_classify_threshold = drift_settings.get("auto_classify_threshold", 0.85)

        # Track the activity
        nudge = None
        try:
            result = manager.track_activity(
                session_id=active_session_id,
                tool=tool_name,
                summary=summary,
                file_paths=file_paths if file_paths else None,
                success=not is_error
            )

            # Check for drift and handle accordingly
            if result and hasattr(result, 'drift_score'):
                drift_score = result.drift_score
                feature_id = getattr(result, 'feature_id', 'unknown')

                if drift_score >= auto_classify_threshold:
                    # High drift - add to classification queue
                    queue = add_to_drift_queue(graph_dir, {
                        "tool": tool_name,
                        "summary": summary,
                        "file_paths": file_paths,
                        "drift_score": drift_score,
                        "feature_id": feature_id
                    }, drift_config)

                    # Check if we should trigger classification
                    if should_trigger_classification(queue, drift_config):
                        classification_prompt = build_classification_prompt(queue, feature_id)

                        # Try to run headless classification
                        use_headless = drift_config.get("classification", {}).get("use_headless", True)
                        if use_headless:
                            try:
                                # Run claude in print mode for classification
                                result = subprocess.run(
                                    ["claude", "-p", classification_prompt, "--model", "haiku", "--dangerously-skip-permissions"],
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
                                    nudge = f"Drift auto-classification completed. Check .htmlgraph/ for new work item."
                                    queue["last_classification"] = datetime.now().isoformat()
                                    save_drift_queue(graph_dir, queue)
                                else:
                                    # Fallback to manual prompt
                                    nudge = f"""HIGH DRIFT ({drift_score:.2f}) - Headless classification failed.

{len(queue['activities'])} activities don't align with '{feature_id}'.

Please classify manually: bug, feature, spike, or chore in .htmlgraph/"""
                            except Exception as e:
                                nudge = f"Drift classification error: {e}. Please classify manually."
                        else:
                            nudge = f"""HIGH DRIFT DETECTED ({drift_score:.2f}) - Auto-classification triggered.

{len(queue['activities'])} activities don't align with '{feature_id}'.

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
