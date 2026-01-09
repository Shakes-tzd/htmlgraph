#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
Link Activities to Work Item

Links queued drift activities to a newly created work item.
Called after a work item is created from drift classification.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DRIFT_QUEUE_FILE = "drift-queue.json"


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
            from datetime import timedelta

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
                # Save cleaned queue
                try:
                    with open(queue_path, "w") as f:
                        json.dump(queue, f, indent=2)
                except Exception:
                    pass

            return queue
        except Exception:
            pass
    return {"activities": [], "last_classification": None}


def clear_drift_queue(graph_dir: Path) -> None:
    """Clear the drift queue after linking."""
    queue_path = graph_dir / DRIFT_QUEUE_FILE
    queue = {"activities": [], "last_classification": datetime.now().isoformat()}
    try:
        with open(queue_path, "w") as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not clear drift queue: {e}", file=sys.stderr)


def update_work_item_with_activities(work_item_path: Path, activities: list) -> bool:
    """Add activity references to the work item's activity log."""
    if not work_item_path.exists():
        return False

    try:
        content = work_item_path.read_text()

        # Build activity log entries
        activity_entries = []
        for act in activities:
            ts = act.get("timestamp", datetime.now().isoformat())
            tool = act.get("tool", "unknown")
            summary = act.get("summary", "")
            drift = act.get("drift_score", 0)
            entry = f'                <li data-timestamp="{ts}" data-tool="{tool}" data-drift="{drift:.2f}">Source: {summary}</li>'
            activity_entries.append(entry)

        # Find the activity log section and insert entries
        activity_log_pattern = r"(<section data-activity-log>.*?<ol reversed>)"
        match = re.search(activity_log_pattern, content, re.DOTALL)

        if match:
            insert_point = match.end()
            new_entries = "\n" + "\n".join(activity_entries)
            content = content[:insert_point] + new_entries + content[insert_point:]
            work_item_path.write_text(content)
            return True

    except Exception as e:
        print(f"Error updating work item: {e}", file=sys.stderr)

    return False


def update_session_with_work_item_link(
    graph_dir: Path, work_item_id: str, work_item_type: str
) -> bool:
    """Add work item link to the current session's edges."""
    from htmlgraph.session_manager import SessionManager

    try:
        manager = SessionManager(graph_dir)
        session = manager.get_active_session()
        if not session:
            return False

        session_path = graph_dir / "sessions" / f"{session.id}.html"
        if not session_path.exists():
            return False

        content = session_path.read_text()

        # Find the nav section and add a "created" edge
        nav_pattern = r"(<nav data-graph-edges>)"
        if nav_pattern not in content:
            return False

        # Check if "created" section exists
        if 'data-edge-type="created"' not in content:
            # Add a new created section after the nav opening
            created_section = f'''
            <section data-edge-type="created">
                <h3>Created:</h3>
                <ul>
                    <li><a href="../{work_item_type}s/{work_item_id}.html" data-relationship="created" data-since="{datetime.now().isoformat()}">{work_item_id}</a></li>
                </ul>
            </section>'''

            content = re.sub(
                r"(<nav data-graph-edges>)", r"\1" + created_section, content
            )
        else:
            # Add to existing created section
            new_link = f'                    <li><a href="../{work_item_type}s/{work_item_id}.html" data-relationship="created" data-since="{datetime.now().isoformat()}">{work_item_id}</a></li>'
            content = re.sub(
                r'(data-edge-type="created".*?<ul>)',
                r"\1\n" + new_link,
                content,
                flags=re.DOTALL,
            )

        session_path.write_text(content)
        return True

    except Exception as e:
        print(f"Error updating session: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: link-activities.py <work_item_type> <work_item_id>")
        print("Example: link-activities.py bug bug-password-validation")
        sys.exit(1)

    work_item_type = sys.argv[1]  # bug, feature, spike, chore
    work_item_id = sys.argv[2]  # e.g., bug-password-validation

    project_dir = resolve_project_path()
    graph_dir = Path(project_dir) / ".htmlgraph"

    # Determine work item path
    type_dirs = {
        "bug": "bugs",
        "feature": "features",
        "spike": "spikes",
        "chore": "chores",
        "hotfix": "hotfixes",
    }
    work_item_dir = type_dirs.get(work_item_type, f"{work_item_type}s")
    work_item_path = graph_dir / work_item_dir / f"{work_item_id}.html"

    # Load queued activities
    queue = load_drift_queue(graph_dir)
    activities = queue.get("activities", [])

    if not activities:
        print("No activities in drift queue to link")
        sys.exit(0)

    print(f"Linking {len(activities)} activities to {work_item_id}...")

    # Update work item with activity references
    if update_work_item_with_activities(work_item_path, activities):
        print(f"  Updated {work_item_path}")
    else:
        print(f"  Warning: Could not update {work_item_path}")

    # Update session with work item link
    if update_session_with_work_item_link(graph_dir, work_item_id, work_item_type):
        print("  Added 'created' link to session")
    else:
        print("  Warning: Could not update session")

    # Clear the queue
    clear_drift_queue(graph_dir)
    print("Drift queue cleared")

    print(f"Successfully linked activities to {work_item_id}")


if __name__ == "__main__":
    main()
