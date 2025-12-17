#!/usr/bin/env python3
"""
HtmlGraph CLI.

Usage:
    htmlgraph serve [--port PORT] [--dir DIR]
    htmlgraph init [DIR]
    htmlgraph status [--dir DIR]
    htmlgraph query SELECTOR [--dir DIR]

Session Management:
    htmlgraph session start [--id ID] [--agent AGENT]
    htmlgraph session end ID
    htmlgraph session list
    htmlgraph track TOOL SUMMARY [--session ID] [--files FILE...]

Feature Management:
    htmlgraph feature start ID
    htmlgraph feature complete ID
    htmlgraph feature primary ID
"""

import argparse
import os
import sys
from pathlib import Path


def cmd_serve(args):
    """Start the HtmlGraph server."""
    from htmlgraph.server import serve
    serve(
        port=args.port,
        graph_dir=args.graph_dir,
        static_dir=args.static_dir,
        host=args.host,
        watch=not args.no_watch
    )


def cmd_init(args):
    """Initialize a new .htmlgraph directory."""
    from htmlgraph.server import HtmlGraphAPIHandler
    from htmlgraph.analytics_index import AnalyticsIndex
    import shutil

    graph_dir = Path(args.dir) / ".htmlgraph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    for collection in HtmlGraphAPIHandler.COLLECTIONS:
        (graph_dir / collection).mkdir(exist_ok=True)

    # Event stream directory (Git-friendly source of truth)
    events_dir = graph_dir / "events"
    events_dir.mkdir(exist_ok=True)
    if not args.no_events_keep:
        keep = events_dir / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")

    # Copy stylesheet
    styles_src = Path(__file__).parent / "styles.css"
    styles_dest = graph_dir / "styles.css"
    if styles_src.exists() and not styles_dest.exists():
        styles_dest.write_text(styles_src.read_text())

    # Create default index.html if not exists
    index_path = Path(args.dir) / "index.html"
    if not index_path.exists():
        create_default_index(index_path)

    # Create analytics cache DB (rebuildable; typically gitignored)
    if not args.no_index:
        try:
            AnalyticsIndex(graph_dir / "index.sqlite").ensure_schema()
        except Exception:
            # Never fail init because of analytics cache.
            pass

    def ensure_gitignore_entries(project_dir: Path, lines: list[str]) -> None:
        if args.no_update_gitignore:
            return
        gitignore_path = project_dir / ".gitignore"
        existing = ""
        if gitignore_path.exists():
            try:
                existing = gitignore_path.read_text(encoding="utf-8")
            except Exception:
                existing = ""
        existing_lines = set(existing.splitlines())
        missing = [ln for ln in lines if ln not in existing_lines]
        if not missing:
            return
        block = "\n".join(
            ["", "# HtmlGraph analytics index (rebuildable cache)", *missing, ""]
            if "# HtmlGraph analytics index (rebuildable cache)" not in existing_lines
            else ["", *missing, ""]
        )
        try:
            gitignore_path.write_text(existing + block, encoding="utf-8")
        except Exception:
            # Don't fail init on .gitignore issues.
            pass

    ensure_gitignore_entries(
        Path(args.dir),
        [
            ".htmlgraph/index.sqlite",
            ".htmlgraph/index.sqlite-wal",
            ".htmlgraph/index.sqlite-shm",
            ".htmlgraph/git-hook-errors.log",
        ],
    )

    # Ensure versioned hook scripts exist (installation into .git/hooks is optional)
    hooks_dir = graph_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    # Hook templates (used when htmlgraph is installed without this repo layout).
    post_commit = """#!/bin/bash
#
# HtmlGraph Post-Commit Hook
# Logs Git commit events for agent-agnostic continuity tracking
#

set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 0

if [ ! -d ".htmlgraph" ]; then
  exit 0
fi

if ! command -v htmlgraph &> /dev/null; then
  if command -v python3 &> /dev/null; then
    python3 -m htmlgraph.git_events commit &> /dev/null &
  fi
  exit 0
fi

htmlgraph git-event commit &> /dev/null &
exit 0
"""

    post_checkout = """#!/bin/bash
#
# HtmlGraph Post-Checkout Hook
# Logs branch switches / checkouts for continuity tracking
#

set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 0

if [ ! -d ".htmlgraph" ]; then
  exit 0
fi

OLD_HEAD="$1"
NEW_HEAD="$2"
FLAG="$3"

if ! command -v htmlgraph &> /dev/null; then
  if command -v python3 &> /dev/null; then
    python3 -m htmlgraph.git_events checkout "$OLD_HEAD" "$NEW_HEAD" "$FLAG" &> /dev/null &
  fi
  exit 0
fi

htmlgraph git-event checkout "$OLD_HEAD" "$NEW_HEAD" "$FLAG" &> /dev/null &
exit 0
"""

    post_merge = """#!/bin/bash
#
# HtmlGraph Post-Merge Hook
# Logs successful merges for continuity tracking
#

set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 0

if [ ! -d ".htmlgraph" ]; then
  exit 0
fi

SQUASH_FLAG="$1"

if ! command -v htmlgraph &> /dev/null; then
  if command -v python3 &> /dev/null; then
    python3 -m htmlgraph.git_events merge "$SQUASH_FLAG" &> /dev/null &
  fi
  exit 0
fi

htmlgraph git-event merge "$SQUASH_FLAG" &> /dev/null &
exit 0
"""

    pre_push = """#!/bin/bash
#
# HtmlGraph Pre-Push Hook
# Logs pushes for continuity tracking / team boundary events
#

set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 0

if [ ! -d ".htmlgraph" ]; then
  exit 0
fi

REMOTE_NAME="$1"
REMOTE_URL="$2"
UPDATES="$(cat)"

if ! command -v htmlgraph &> /dev/null; then
  if command -v python3 &> /dev/null; then
    printf "%s" "$UPDATES" | python3 -m htmlgraph.git_events push "$REMOTE_NAME" "$REMOTE_URL" &> /dev/null &
  fi
  exit 0
fi

printf "%s" "$UPDATES" | htmlgraph git-event push "$REMOTE_NAME" "$REMOTE_URL" &> /dev/null &
exit 0
"""

    def ensure_hook_file(hook_name: str, hook_content: str) -> Path:
        hook_dest = hooks_dir / f"{hook_name}.sh"
        if not hook_dest.exists():
            hook_dest.write_text(hook_content)
        try:
            hook_dest.chmod(0o755)
        except Exception:
            pass
        return hook_dest

    hook_files = {
        "post-commit": ensure_hook_file("post-commit", post_commit),
        "post-checkout": ensure_hook_file("post-checkout", post_checkout),
        "post-merge": ensure_hook_file("post-merge", post_merge),
        "pre-push": ensure_hook_file("pre-push", pre_push),
    }

    print(f"Initialized HtmlGraph in {graph_dir}")
    print(f"Collections: {', '.join(HtmlGraphAPIHandler.COLLECTIONS)}")
    print(f"\nStart server with: htmlgraph serve")
    if not args.no_index:
        print(f"Analytics cache: {graph_dir / 'index.sqlite'} (rebuildable; typically gitignored)")
    print(f"Events: {events_dir}/ (append-only JSONL)")

    # Install Git hooks if requested
    if args.install_hooks:
        git_dir = Path(args.dir) / ".git"
        if not git_dir.exists():
            print(f"\n⚠️  Warning: No .git directory found. Git hooks not installed.")
            print(f"   Initialize git first: git init")
            return

        def install_hook(hook_name: str, hook_dest: Path, hook_content: str | None) -> None:
            """
            Install one Git hook:
              - Ensure `.htmlgraph/hooks/<hook>.sh` exists (copy template if present; else inline)
              - Install to `.git/hooks/<hook>` (symlink or chained wrapper if existing)
            """
            # Try to copy a template from this repo layout (dev), otherwise inline.
            hook_src = Path(__file__).parent.parent.parent.parent / ".htmlgraph" / "hooks" / f"{hook_name}.sh"
            if hook_src.exists() and hook_src.resolve() != hook_dest.resolve():
                shutil.copy(hook_src, hook_dest)
            elif not hook_dest.exists():
                if not hook_content:
                    raise RuntimeError(f"Missing hook content for {hook_name}")
                hook_dest.write_text(hook_content)
            # Ensure executable (covers the case where the file already existed)
            try:
                hook_dest.chmod(0o755)
            except Exception:
                pass

            git_hook_path = git_dir / "hooks" / hook_name

            if git_hook_path.exists():
                print(f"\n⚠️  Existing {hook_name} hook found")
                backup_path = git_hook_path.with_suffix(".existing")
                if not backup_path.exists():
                    shutil.copy(git_hook_path, backup_path)
                    print(f"   Backed up to: {backup_path}")

                chain_content = f'''#!/bin/bash
# Chained hook - runs existing hook then HtmlGraph hook

if [ -f "{backup_path}" ]; then
  "{backup_path}" || exit $?
fi

if [ -f "{hook_dest}" ]; then
  "{hook_dest}" || true
fi
'''
                git_hook_path.write_text(chain_content)
                git_hook_path.chmod(0o755)
                print(f"   Installed chained hook at: {git_hook_path}")
                return

            try:
                git_hook_path.symlink_to(hook_dest.resolve())
                print(f"\n✓ Git hooks installed")
                print(f"  {hook_name}: {git_hook_path} -> {hook_dest}")
            except OSError:
                shutil.copy(hook_dest, git_hook_path)
                git_hook_path.chmod(0o755)
                print(f"\n✓ Git hooks installed")
                print(f"  {hook_name}: {git_hook_path}")

        install_hook("post-commit", hook_files["post-commit"], post_commit)
        install_hook("post-checkout", hook_files["post-checkout"], post_checkout)
        install_hook("post-merge", hook_files["post-merge"], post_merge)
        install_hook("pre-push", hook_files["pre-push"], pre_push)

        print("\nGit events will now be logged to HtmlGraph automatically.")


def cmd_status(args):
    """Show status of the graph."""
    from htmlgraph.graph import HtmlGraph

    graph_dir = Path(args.graph_dir)
    if not graph_dir.exists():
        print(f"Error: {graph_dir} not found. Run 'htmlgraph init' first.")
        sys.exit(1)

    total = 0
    by_status = {}
    by_collection = {}

    for collection_dir in graph_dir.iterdir():
        if collection_dir.is_dir() and not collection_dir.name.startswith("."):
            graph = HtmlGraph(collection_dir, auto_load=True)
            stats = graph.stats()
            by_collection[collection_dir.name] = stats["total"]
            total += stats["total"]
            for status, count in stats["by_status"].items():
                by_status[status] = by_status.get(status, 0) + count

    print(f"HtmlGraph Status: {graph_dir}")
    print(f"{'=' * 40}")
    print(f"Total nodes: {total}")
    print(f"\nBy Collection:")
    for coll, count in sorted(by_collection.items()):
        print(f"  {coll}: {count}")
    print(f"\nBy Status:")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")


def cmd_query(args):
    """Query nodes with CSS selector."""
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.converter import node_to_dict
    import json

    graph_dir = Path(args.graph_dir)
    if not graph_dir.exists():
        print(f"Error: {graph_dir} not found.", file=sys.stderr)
        sys.exit(1)

    results = []
    for collection_dir in graph_dir.iterdir():
        if collection_dir.is_dir() and not collection_dir.name.startswith("."):
            graph = HtmlGraph(collection_dir, auto_load=True)
            for node in graph.query(args.selector):
                data = node_to_dict(node)
                data["_collection"] = collection_dir.name
                results.append(data)

    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))
    else:
        for node in results:
            status = node.get("status", "?")
            priority = node.get("priority", "?")
            print(f"[{node['_collection']}] {node['id']}: {node['title']} ({status}, {priority})")


# =============================================================================
# Session Management Commands
# =============================================================================

def cmd_session_start(args):
    """Start a new session."""
    from htmlgraph.session_manager import SessionManager
    import json

    manager = SessionManager(args.graph_dir)
    session = manager.start_session(
        session_id=args.id,
        agent=args.agent,
        title=args.title
    )

    if args.format == "json":
        from htmlgraph.converter import session_to_dict
        print(json.dumps(session_to_dict(session), indent=2))
    else:
        print(f"Session started: {session.id}")
        print(f"  Agent: {session.agent}")
        print(f"  Started: {session.started_at.isoformat()}")
        if session.title:
            print(f"  Title: {session.title}")


def cmd_session_end(args):
    """End a session."""
    from htmlgraph.session_manager import SessionManager
    import json

    manager = SessionManager(args.graph_dir)
    session = manager.end_session(args.id)

    if session is None:
        print(f"Error: Session '{args.id}' not found.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import session_to_dict
        print(json.dumps(session_to_dict(session), indent=2))
    else:
        print(f"Session ended: {session.id}")
        print(f"  Duration: {session.ended_at - session.started_at}")
        print(f"  Events: {session.event_count}")
        if session.worked_on:
            print(f"  Worked on: {', '.join(session.worked_on)}")


def cmd_session_list(args):
    """List all sessions."""
    from htmlgraph.converter import SessionConverter
    import json

    sessions_dir = Path(args.graph_dir) / "sessions"
    if not sessions_dir.exists():
        print("No sessions found.")
        return

    converter = SessionConverter(sessions_dir)
    sessions = converter.load_all()

    # Sort by started_at descending (handle mixed tz-aware/naive datetimes)
    def sort_key(s):
        ts = s.started_at
        # Make naive datetimes comparable by assuming UTC
        if ts.tzinfo is None:
            return ts.replace(tzinfo=None)
        return ts.replace(tzinfo=None)  # Compare as naive for sorting
    sessions.sort(key=sort_key, reverse=True)

    if args.format == "json":
        from htmlgraph.converter import session_to_dict
        print(json.dumps([session_to_dict(s) for s in sessions], indent=2))
    else:
        if not sessions:
            print("No sessions found.")
            return

        print(f"{'ID':<30} {'Status':<10} {'Agent':<15} {'Events':<8} {'Started'}")
        print("=" * 90)
        for session in sessions:
            started = session.started_at.strftime("%Y-%m-%d %H:%M")
            print(f"{session.id:<30} {session.status:<10} {session.agent:<15} {session.event_count:<8} {started}")


def cmd_session_dedupe(args):
    """Move low-signal session files out of the main sessions directory."""
    from htmlgraph.session_manager import SessionManager

    manager = SessionManager(args.graph_dir)
    result = manager.dedupe_orphan_sessions(
        max_events=args.max_events,
        move_dir_name=args.move_dir,
        dry_run=args.dry_run,
        stale_extra_active=not args.no_stale_active,
    )

    print(f"Scanned: {result['scanned']}")
    print(f"Moved:   {result['moved']}")
    if result.get("missing"):
        print(f"Missing: {result['missing']}")
    if not args.dry_run:
        if result.get("staled_active"):
            print(f"Staled:  {result['staled_active']} extra active sessions")
        if result.get("kept_active"):
            print(f"Kept:    {result['kept_active']} canonical active sessions")


def cmd_session_link(args):
    """Link a feature to a session retroactively."""
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.models import Edge
    import json

    graph_dir = Path(args.graph_dir)
    sessions_dir = graph_dir / "sessions"
    feature_dir = graph_dir / args.collection

    # Load session
    session_file = sessions_dir / f"{args.session_id}.html"
    if not session_file.exists():
        print(f"Error: Session '{args.session_id}' not found at {session_file}", file=sys.stderr)
        sys.exit(1)

    session_graph = HtmlGraph(sessions_dir)
    session = session_graph.get(args.session_id)
    if not session:
        print(f"Error: Failed to load session '{args.session_id}'", file=sys.stderr)
        sys.exit(1)

    # Load feature
    feature_file = feature_dir / f"{args.feature_id}.html"
    if not feature_file.exists():
        print(f"Error: Feature '{args.feature_id}' not found at {feature_file}", file=sys.stderr)
        sys.exit(1)

    feature_graph = HtmlGraph(feature_dir)
    feature = feature_graph.get(args.feature_id)
    if not feature:
        print(f"Error: Failed to load feature '{args.feature_id}'", file=sys.stderr)
        sys.exit(1)

    # Check if already linked
    worked_on = session.edges.get("worked-on", [])
    already_linked = any(e.target_id == args.feature_id for e in worked_on)

    if already_linked:
        print(f"Feature '{args.feature_id}' is already linked to session '{args.session_id}'")
        if not args.bidirectional:
            sys.exit(0)

    # Add edge from session to feature
    if not already_linked:
        new_edge = Edge(
            target_id=args.feature_id,
            relationship="worked-on",
            title=feature.title
        )
        if "worked-on" not in session.edges:
            session.edges["worked-on"] = []
        session.edges["worked-on"].append(new_edge)
        session_graph.update(session)
        print(f"✓ Linked feature '{args.feature_id}' to session '{args.session_id}'")

    # Optionally add reciprocal edge from feature to session
    if args.bidirectional:
        implemented_in = feature.edges.get("implemented-in", [])
        feature_already_linked = any(e.target_id == args.session_id for e in implemented_in)

        if not feature_already_linked:
            reciprocal_edge = Edge(
                target_id=args.session_id,
                relationship="implemented-in",
                title=f"Session {session.id}"
            )
            if "implemented-in" not in feature.edges:
                feature.edges["implemented-in"] = []
            feature.edges["implemented-in"].append(reciprocal_edge)
            feature_graph.update(feature)
            print(f"✓ Added reciprocal link from feature '{args.feature_id}' to session '{args.session_id}'")
        else:
            print(f"Feature '{args.feature_id}' already has reciprocal link to session")

    if args.format == "json":
        result = {
            "session_id": args.session_id,
            "feature_id": args.feature_id,
            "bidirectional": args.bidirectional,
            "linked": not already_linked
        }
        print(json.dumps(result, indent=2))


def cmd_session_validate_attribution(args):
    """Validate feature attribution and tracking."""
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.converter import SessionConverter
    import json
    from datetime import datetime

    graph_dir = Path(args.graph_dir)
    feature_dir = graph_dir / args.collection
    sessions_dir = graph_dir / "sessions"
    events_dir = graph_dir / "events"

    # Load feature
    feature_graph = HtmlGraph(feature_dir)
    feature = feature_graph.get(args.feature_id)
    if not feature:
        print(f"Error: Feature '{args.feature_id}' not found", file=sys.stderr)
        sys.exit(1)

    # Find sessions that worked on this feature
    sessions_graph = HtmlGraph(sessions_dir)
    all_sessions = sessions_graph.query('[data-type="session"]')
    linked_sessions = []

    for session in all_sessions:
        worked_on = session.edges.get("worked-on", [])
        if any(e.target_id == args.feature_id for e in worked_on):
            linked_sessions.append(session)

    # Count events attributed to this feature
    event_count = 0
    last_activity = None
    high_drift_events = []

    for session in linked_sessions:
        session_events_file = events_dir / f"{session.id}.jsonl"
        if session_events_file.exists():
            with open(session_events_file, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if event.get('feature_id') == args.feature_id:
                            event_count += 1
                            timestamp = event.get('timestamp')
                            if timestamp:
                                event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                if not last_activity or event_time > last_activity:
                                    last_activity = event_time

                            # Check for high drift
                            drift_score = event.get('drift_score')
                            if drift_score and drift_score > 0.8:
                                high_drift_events.append({
                                    'timestamp': timestamp,
                                    'tool': event.get('tool'),
                                    'drift': drift_score
                                })
                    except json.JSONDecodeError:
                        continue

    # Calculate attribution health
    health = "UNKNOWN"
    issues = []

    if len(linked_sessions) == 0:
        health = "CRITICAL"
        issues.append("Feature not linked to any session")
    elif event_count == 0:
        health = "CRITICAL"
        issues.append("No events attributed to feature")
    elif event_count < 5:
        health = "WARNING"
        issues.append(f"Only {event_count} events attributed (unusually low)")
    else:
        health = "GOOD"

    if len(high_drift_events) > 3:
        if health == "GOOD":
            health = "WARNING"
        issues.append(f"{len(high_drift_events)} events with drift > 0.8 (may be misattributed)")

    # Output results
    if args.format == "json":
        result = {
            "feature_id": args.feature_id,
            "feature_title": feature.title,
            "health": health,
            "linked_sessions": len(linked_sessions),
            "event_count": event_count,
            "last_activity": last_activity.isoformat() if last_activity else None,
            "high_drift_count": len(high_drift_events),
            "issues": issues
        }
        print(json.dumps(result, indent=2))
    else:
        status_symbol = "✓" if health == "GOOD" else "⚠" if health == "WARNING" else "✗"
        print(f"{status_symbol} Feature '{args.feature_id}' validation:")
        print(f"  Title: {feature.title}")
        print(f"  Health: {health}")
        print(f"  - Linked to {len(linked_sessions)} session(s)")
        print(f"  - {event_count} events attributed")
        if last_activity:
            print(f"  - Last activity: {last_activity.strftime('%Y-%m-%d %H:%M:%S')}")

        if issues:
            print(f"\n⚠ Issues detected:")
            for issue in issues:
                print(f"  - {issue}")

        if len(high_drift_events) > 0 and len(high_drift_events) <= 5:
            print(f"\n⚠ High drift events:")
            for event in high_drift_events[:5]:
                print(f"  - {event['timestamp']}: {event['tool']} (drift: {event['drift']:.2f})")


def cmd_track(args):
    """Track an activity in the current session."""
    from htmlgraph.session_manager import SessionManager
    import json

    manager = SessionManager(args.graph_dir)

    # Find active session or use specified one
    session_id = args.session
    if not session_id:
        active = manager.get_active_session()
        if not active:
            print("Error: No active session. Start one with 'htmlgraph session start'.", file=sys.stderr)
            sys.exit(1)
        session_id = active.id

    entry = manager.track_activity(
        session_id=session_id,
        tool=args.tool,
        summary=args.summary,
        file_paths=args.files,
        success=not args.failed
    )

    if args.format == "json":
        data = {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "tool": entry.tool,
            "summary": entry.summary,
            "success": entry.success,
            "feature_id": entry.feature_id,
            "drift_score": entry.drift_score
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Tracked: [{entry.tool}] {entry.summary}")
        if entry.feature_id:
            print(f"  Attributed to: {entry.feature_id}")
        if entry.drift_score and entry.drift_score > 0.3:
            print(f"  Drift warning: {entry.drift_score:.2f}")


# =============================================================================
# Events & Index Commands
# =============================================================================

def cmd_events_export(args):
    """Export legacy session HTML activity logs to JSONL event logs."""
    from htmlgraph.event_migration import export_sessions_to_jsonl

    graph_dir = Path(args.graph_dir)
    sessions_dir = graph_dir / "sessions"
    events_dir = graph_dir / "events"

    result = export_sessions_to_jsonl(
        sessions_dir=sessions_dir,
        events_dir=events_dir,
        overwrite=args.overwrite,
        include_subdirs=args.include_subdirs,
    )

    print(f"Written: {result['written']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Failed:  {result['failed']}")


def cmd_index_rebuild(args):
    """Rebuild the SQLite analytics index from JSONL event logs."""
    from htmlgraph.event_log import JsonlEventLog
    from htmlgraph.analytics_index import AnalyticsIndex

    graph_dir = Path(args.graph_dir)
    events_dir = graph_dir / "events"
    db_path = graph_dir / "index.sqlite"

    log = JsonlEventLog(events_dir)
    index = AnalyticsIndex(db_path)

    events = (event for _, event in log.iter_events())
    result = index.rebuild_from_events(events)

    print(f"DB: {db_path}")
    print(f"Inserted: {result['inserted']}")
    print(f"Skipped:  {result['skipped']}")


def cmd_watch(args):
    """Watch filesystem changes and record them as activity events."""
    from htmlgraph.watch import watch_and_track

    root = Path(args.root).resolve()
    graph_dir = Path(args.graph_dir)

    watch_and_track(
        root=root,
        graph_dir=graph_dir,
        session_id=args.session_id,
        agent=args.agent,
        interval_seconds=args.interval,
        batch_seconds=args.batch_seconds,
    )


def cmd_git_event(args):
    """Log a Git event (commit, checkout, merge, push)."""
    import sys
    from htmlgraph.git_events import (
        log_git_checkout,
        log_git_commit,
        log_git_merge,
        log_git_push,
    )

    if args.event_type == "commit":
        success = log_git_commit()
        if not success:
            sys.exit(1)
        return

    if args.event_type == "checkout":
        if len(args.args) < 3:
            print("Error: checkout requires args: <old_head> <new_head> <flag>", file=sys.stderr)
            sys.exit(1)
        old_head, new_head, flag = args.args[0], args.args[1], args.args[2]
        if not log_git_checkout(old_head, new_head, flag):
            sys.exit(1)
        return

    if args.event_type == "merge":
        squash_flag = args.args[0] if args.args else "0"
        if not log_git_merge(squash_flag):
            sys.exit(1)
        return

    if args.event_type == "push":
        if len(args.args) < 2:
            print("Error: push requires args: <remote_name> <remote_url>", file=sys.stderr)
            sys.exit(1)
        remote_name, remote_url = args.args[0], args.args[1]
        updates_text = sys.stdin.read()
        if not log_git_push(remote_name, remote_url, updates_text):
            sys.exit(1)
        return
    else:
        print(f"Error: Unknown event type '{args.event_type}'", file=sys.stderr)
        sys.exit(1)


def cmd_mcp_serve(args):
    """Run the minimal MCP server over stdio."""
    from htmlgraph.mcp_server import serve_stdio

    serve_stdio(graph_dir=Path(args.graph_dir), default_agent=args.agent)


# =============================================================================
# Feature Management Commands
# =============================================================================

def cmd_feature_create(args):
    """Create a new feature."""
    from htmlgraph.session_manager import SessionManager
    import json

    manager = SessionManager(args.graph_dir)

    try:
        node = manager.create_feature(
            title=args.title,
            collection=args.collection,
            description=args.description or "",
            priority=args.priority,
            steps=args.steps,
            agent=args.agent
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict
        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Created: {node.id}")
        print(f"  Title: {node.title}")
        print(f"  Status: {node.status}")
        print(f"  Path: {args.graph_dir}/{args.collection}/{node.id}.html")


def cmd_feature_start(args):
    """Start working on a feature."""
    from htmlgraph.session_manager import SessionManager
    import json

    manager = SessionManager(args.graph_dir)

    try:
        node = manager.start_feature(args.id, collection=args.collection, agent=args.agent)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if node is None:
        print(f"Error: Feature '{args.id}' not found in {args.collection}.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict
        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Started: {node.id}")
        print(f"  Title: {node.title}")
        print(f"  Status: {node.status}")

        # Show WIP status
        status = manager.get_status()
        print(f"  WIP: {status['wip_count']}/{status['wip_limit']}")


def cmd_feature_complete(args):
    """Mark a feature as complete."""
    from htmlgraph.session_manager import SessionManager
    import json

    manager = SessionManager(args.graph_dir)

    try:
        node = manager.complete_feature(args.id, collection=args.collection, agent=args.agent)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if node is None:
        print(f"Error: Feature '{args.id}' not found in {args.collection}.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict
        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Completed: {node.id}")
        print(f"  Title: {node.title}")


def cmd_feature_primary(args):
    """Set the primary feature for attribution."""
    from htmlgraph.session_manager import SessionManager
    import json

    manager = SessionManager(args.graph_dir)

    try:
        node = manager.set_primary_feature(args.id, collection=args.collection, agent=args.agent)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if node is None:
        print(f"Error: Feature '{args.id}' not found in {args.collection}.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict
        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Primary feature set: {node.id}")
        print(f"  Title: {node.title}")


def cmd_feature_list(args):
    """List features by status."""
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.converter import node_to_dict
    import json

    collection_dir = Path(args.graph_dir) / args.collection
    if not collection_dir.exists():
        print(f"Error: Collection '{args.collection}' not found.", file=sys.stderr)
        sys.exit(1)

    graph = HtmlGraph(collection_dir, auto_load=True)

    if args.status:
        nodes = graph.query(f"[data-status='{args.status}']")
    else:
        nodes = list(graph.nodes.values())

    # Sort by priority then updated
    from datetime import timezone
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def sort_key(n):
        # Ensure timezone-aware datetime for comparison
        updated = n.updated
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return (priority_order.get(n.priority, 99), updated)

    nodes.sort(key=sort_key, reverse=True)

    if args.format == "json":
        print(json.dumps([node_to_dict(n) for n in nodes], indent=2, default=str))
    else:
        if not nodes:
            print(f"No features found with status '{args.status}'." if args.status else "No features found.")
            return

        print(f"{'ID':<25} {'Status':<12} {'Priority':<10} {'Title'}")
        print("=" * 80)
        for node in nodes:
            title = node.title[:35] + "..." if len(node.title) > 38 else node.title
            print(f"{node.id:<25} {node.status:<12} {node.priority:<10} {title}")


def create_default_index(path: Path):
    """Create a default index.html that uses the API."""
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HtmlGraph Dashboard</title>
    <style>
        :root {
            --color-primary: #2563eb;
            --color-success: #16a34a;
            --color-warning: #d97706;
            --color-danger: #dc2626;
            --color-bg: #f9fafb;
            --color-card: #ffffff;
            --color-text: #1f2937;
            --color-muted: #6b7280;
            --color-border: #e5e7eb;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --color-bg: #111827;
                --color-card: #1f2937;
                --color-text: #f9fafb;
                --color-muted: #9ca3af;
                --color-border: #374151;
            }
        }
        * { box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            margin: 0;
            padding: 2rem;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 2rem; }
        header h1 { margin: 0; }
        header p { color: var(--color-muted); }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat {
            background: var(--color-card);
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value { font-size: 2rem; font-weight: 700; color: var(--color-primary); }
        .stat-label { font-size: 0.75rem; color: var(--color-muted); text-transform: uppercase; }
        .kanban {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
        }
        .column {
            background: var(--color-card);
            border-radius: 8px;
            padding: 1rem;
        }
        .column h2 {
            font-size: 0.875rem;
            margin: 0 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--color-border);
            display: flex;
            justify-content: space-between;
        }
        .column h2 span {
            background: var(--color-bg);
            padding: 0.125rem 0.5rem;
            border-radius: 999px;
            font-size: 0.75rem;
        }
        .cards { display: flex; flex-direction: column; gap: 0.5rem; }
        .card {
            display: block;
            background: var(--color-bg);
            padding: 0.75rem;
            border-radius: 6px;
            text-decoration: none;
            color: inherit;
            border-left: 3px solid var(--color-primary);
        }
        .card:hover { opacity: 0.8; }
        .card-title { font-weight: 600; margin-bottom: 0.25rem; }
        .card-meta { font-size: 0.75rem; color: var(--color-muted); }
        .badge {
            display: inline-block;
            padding: 0.125rem 0.375rem;
            border-radius: 999px;
            font-size: 0.625rem;
            font-weight: 600;
            margin-right: 0.25rem;
        }
        .priority-critical { background: #fee2e2; color: #dc2626; }
        .priority-high { background: #fef3c7; color: #d97706; }
        .priority-medium { background: #dbeafe; color: #2563eb; }
        .priority-low { background: #f3f4f6; color: #6b7280; }
        .type-feature { border-left-color: var(--color-warning); }
        .type-bug { border-left-color: var(--color-danger); }
        .type-spike { border-left-color: #8b5cf6; }
        .type-chore { border-left-color: var(--color-muted); }
        .empty { color: var(--color-muted); text-align: center; padding: 2rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>HtmlGraph</h1>
            <p>"HTML is All You Need"</p>
        </header>
        <div class="stats" id="stats">Loading...</div>
        <div class="kanban" id="kanban"></div>
    </div>
    <script>
        const API = '/api';
        const STATUSES = ['in-progress', 'todo', 'blocked', 'done'];
        const STATUS_LABELS = {
            'in-progress': 'In Progress',
            'todo': 'Todo',
            'blocked': 'Blocked',
            'done': 'Done'
        };

        async function loadData() {
            const [status, query] = await Promise.all([
                fetch(`${API}/status`).then(r => r.json()),
                fetch(`${API}/query`).then(r => r.json())
            ]);
            return { status, nodes: query.nodes };
        }

        function renderStats(status) {
            const s = status.by_status || {};
            document.getElementById('stats').innerHTML = `
                <div class="stat"><div class="stat-value">${status.total_nodes}</div><div class="stat-label">Total</div></div>
                <div class="stat"><div class="stat-value">${s['done'] || 0}</div><div class="stat-label">Done</div></div>
                <div class="stat"><div class="stat-value">${s['in-progress'] || 0}</div><div class="stat-label">Active</div></div>
                <div class="stat"><div class="stat-value">${s['blocked'] || 0}</div><div class="stat-label">Blocked</div></div>
            `;
        }

        function renderKanban(nodes) {
            const byStatus = {};
            STATUSES.forEach(s => byStatus[s] = []);
            nodes.forEach(n => {
                if (byStatus[n.status]) byStatus[n.status].push(n);
            });

            document.getElementById('kanban').innerHTML = STATUSES.map(status => `
                <div class="column">
                    <h2>${STATUS_LABELS[status]} <span>${byStatus[status].length}</span></h2>
                    <div class="cards">
                        ${byStatus[status].length === 0 ? '<div class="empty">Empty</div>' : ''}
                        ${byStatus[status].map(n => `
                            <div class="card type-${n.type}">
                                <div class="card-title">${n.title}</div>
                                <div class="card-meta">
                                    <span class="badge priority-${n.priority}">${n.priority}</span>
                                    ${n._collection}/${n.id}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('');
        }

        loadData().then(({ status, nodes }) => {
            renderStats(status);
            renderKanban(nodes);
        }).catch(err => {
            document.getElementById('stats').innerHTML = `<div class="empty">Error loading data: ${err.message}</div>`;
        });
    </script>
</body>
</html>
'''
    path.write_text(html)


def main():
    parser = argparse.ArgumentParser(
        description="HtmlGraph - HTML is All You Need",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  htmlgraph init                    # Initialize .htmlgraph in current dir
  htmlgraph serve                   # Start server on port 8080
  htmlgraph status                  # Show graph status
  htmlgraph query "[data-status='todo']"  # Query nodes

Session Management:
  htmlgraph session start           # Start a new session (auto-ID)
  htmlgraph session start --id my-session --title "Bug fixes"
  htmlgraph session end my-session  # End a session
  htmlgraph session list            # List all sessions
  htmlgraph track Edit "Edit: src/app.py:45-60" --files src/app.py

Feature Management:
  htmlgraph feature list            # List all features
  htmlgraph feature start feat-001  # Start working on a feature
  htmlgraph feature primary feat-001  # Set primary feature
  htmlgraph feature complete feat-001  # Mark feature as done

curl Examples:
  curl localhost:8080/api/status
  curl localhost:8080/api/features
  curl -X POST localhost:8080/api/features -d '{"title": "New feature"}'
  curl -X PATCH localhost:8080/api/features/feat-001 -d '{"status": "done"}'
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the HtmlGraph server")
    serve_parser.add_argument("--port", "-p", type=int, default=8080, help="Port (default: 8080)")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    serve_parser.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    serve_parser.add_argument("--static-dir", "-s", default=".", help="Static files directory")
    serve_parser.add_argument("--no-watch", action="store_true", help="Disable file watching (auto-reload disabled)")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize .htmlgraph directory")
    init_parser.add_argument("dir", nargs="?", default=".", help="Directory to initialize")
    init_parser.add_argument("--install-hooks", action="store_true", help="Install Git hooks for event logging")
    init_parser.add_argument("--no-index", action="store_true", help="Do not create the analytics cache (index.sqlite)")
    init_parser.add_argument("--no-update-gitignore", action="store_true", help="Do not update/create .gitignore for HtmlGraph cache files")
    init_parser.add_argument("--no-events-keep", action="store_true", help="Do not create .htmlgraph/events/.gitkeep")

    # status
    status_parser = subparsers.add_parser("status", help="Show graph status")
    status_parser.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")

    # query
    query_parser = subparsers.add_parser("query", help="Query nodes with CSS selector")
    query_parser.add_argument("selector", help="CSS selector (e.g. [data-status='todo'])")
    query_parser.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    query_parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # =========================================================================
    # Session Management
    # =========================================================================

    # session (with subcommands)
    session_parser = subparsers.add_parser("session", help="Session management")
    session_subparsers = session_parser.add_subparsers(dest="session_command", help="Session command")

    # session start
    session_start = session_subparsers.add_parser("start", help="Start a new session")
    session_start.add_argument("--id", help="Session ID (auto-generated if not provided)")
    session_start.add_argument("--agent", default="claude-code", help="Agent name")
    session_start.add_argument("--title", help="Session title")
    session_start.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    session_start.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # session end
    session_end = session_subparsers.add_parser("end", help="End a session")
    session_end.add_argument("id", help="Session ID to end")
    session_end.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    session_end.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # session list
    session_list = session_subparsers.add_parser("list", help="List all sessions")
    session_list.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    session_list.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # session dedupe
    session_dedupe = session_subparsers.add_parser(
        "dedupe",
        help="Move SessionStart-only sessions into a subfolder",
    )
    session_dedupe.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    session_dedupe.add_argument("--max-events", type=int, default=1, help="Max events to consider orphaned")
    session_dedupe.add_argument("--move-dir", default="_orphans", help="Subfolder name under sessions/")
    session_dedupe.add_argument("--dry-run", action="store_true", help="Show what would happen without moving files")
    session_dedupe.add_argument("--no-stale-active", action="store_true", help="Do not mark extra active sessions as stale")

    # session link
    session_link = session_subparsers.add_parser(
        "link",
        help="Link a feature to a session retroactively"
    )
    session_link.add_argument("session_id", help="Session ID")
    session_link.add_argument("feature_id", help="Feature ID to link")
    session_link.add_argument("--collection", "-c", default="features", help="Feature collection")
    session_link.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    session_link.add_argument("--bidirectional", "-b", action="store_true", help="Also add session to feature's implemented-in edges")
    session_link.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # session validate-attribution
    session_validate = session_subparsers.add_parser(
        "validate-attribution",
        help="Validate feature attribution and tracking"
    )
    session_validate.add_argument("feature_id", help="Feature ID to validate")
    session_validate.add_argument("--collection", "-c", default="features", help="Feature collection")
    session_validate.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    session_validate.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # track
    track_parser = subparsers.add_parser("track", help="Track an activity")
    track_parser.add_argument("tool", help="Tool name (Edit, Bash, Read, etc.)")
    track_parser.add_argument("summary", help="Activity summary")
    track_parser.add_argument("--session", help="Session ID (uses active session if not provided)")
    track_parser.add_argument("--files", nargs="*", help="Files involved")
    track_parser.add_argument("--failed", action="store_true", help="Mark as failed")
    track_parser.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    track_parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # =========================================================================
    # Feature Management
    # =========================================================================

    # feature (with subcommands)
    feature_parser = subparsers.add_parser("feature", help="Feature management")
    feature_subparsers = feature_parser.add_subparsers(dest="feature_command", help="Feature command")

    # feature create
    feature_create = feature_subparsers.add_parser("create", help="Create a new feature")
    feature_create.add_argument("title", help="Feature title")
    feature_create.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_create.add_argument("--description", "-d", help="Description")
    feature_create.add_argument("--priority", "-p", default="medium", choices=["low", "medium", "high", "critical"], help="Priority")
    feature_create.add_argument("--steps", nargs="*", help="Implementation steps")
    feature_create.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_create.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_create.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature start
    feature_start = feature_subparsers.add_parser("start", help="Start working on a feature")
    feature_start.add_argument("id", help="Feature ID")
    feature_start.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_start.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_start.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_start.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature complete
    feature_complete = feature_subparsers.add_parser("complete", help="Mark feature as complete")
    feature_complete.add_argument("id", help="Feature ID")
    feature_complete.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_complete.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_complete.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_complete.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature primary
    feature_primary = feature_subparsers.add_parser("primary", help="Set primary feature")
    feature_primary.add_argument("id", help="Feature ID")
    feature_primary.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_primary.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_primary.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_primary.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature list
    feature_list = feature_subparsers.add_parser("list", help="List features")
    feature_list.add_argument("--status", "-s", help="Filter by status")
    feature_list.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_list.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_list.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # =========================================================================
    # Events & Analytics Index
    # =========================================================================

    events_parser = subparsers.add_parser("events", help="Event log utilities")
    events_subparsers = events_parser.add_subparsers(dest="events_command", help="Events command")

    events_export = events_subparsers.add_parser(
        "export-sessions",
        help="Export session HTML activity logs to JSONL under .htmlgraph/events/",
    )
    events_export.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    events_export.add_argument("--overwrite", action="store_true", help="Overwrite existing JSONL files")
    events_export.add_argument("--include-subdirs", action="store_true", help="Include subdirectories like sessions/_orphans/")

    index_parser = subparsers.add_parser("index", help="Analytics index commands")
    index_subparsers = index_parser.add_subparsers(dest="index_command", help="Index command")

    index_rebuild = index_subparsers.add_parser(
        "rebuild",
        help="Rebuild .htmlgraph/index.sqlite from .htmlgraph/events/*.jsonl",
    )
    index_rebuild.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")

    # watch
    watch_parser = subparsers.add_parser("watch", help="Watch file changes and log events")
    watch_parser.add_argument("--root", "-r", default=".", help="Root directory to watch")
    watch_parser.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    watch_parser.add_argument("--session-id", help="Session ID (defaults to deduped active session)")
    watch_parser.add_argument("--agent", default="codex", help="Agent name for the watcher")
    watch_parser.add_argument("--interval", type=float, default=2.0, help="Polling interval seconds")
    watch_parser.add_argument("--batch-seconds", type=float, default=5.0, help="Batch window seconds")

    # git-event
    git_event_parser = subparsers.add_parser("git-event", help="Log Git events (commit, checkout, merge, push)")
    git_event_parser.add_argument("event_type", choices=["commit", "checkout", "merge", "push"], help="Type of Git event")
    git_event_parser.add_argument(
        "args",
        nargs="*",
        help="Event-specific args (checkout: old new flag; merge: squash_flag; push: remote_name remote_url)",
    )

    # mcp
    mcp_parser = subparsers.add_parser("mcp", help="Minimal MCP server (stdio)")
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command", help="MCP command")
    mcp_serve = mcp_subparsers.add_parser("serve", help="Serve MCP over stdio")
    mcp_serve.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    mcp_serve.add_argument("--agent", default="mcp", help="Agent name for session attribution")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "session":
        if args.session_command == "start":
            cmd_session_start(args)
        elif args.session_command == "end":
            cmd_session_end(args)
        elif args.session_command == "list":
            cmd_session_list(args)
        elif args.session_command == "dedupe":
            cmd_session_dedupe(args)
        elif args.session_command == "link":
            cmd_session_link(args)
        elif args.session_command == "validate-attribution":
            cmd_session_validate_attribution(args)
        else:
            session_parser.print_help()
            sys.exit(1)
    elif args.command == "track":
        cmd_track(args)
    elif args.command == "feature":
        if args.feature_command == "create":
            cmd_feature_create(args)
        elif args.feature_command == "start":
            cmd_feature_start(args)
        elif args.feature_command == "complete":
            cmd_feature_complete(args)
        elif args.feature_command == "primary":
            cmd_feature_primary(args)
        elif args.feature_command == "list":
            cmd_feature_list(args)
        else:
            feature_parser.print_help()
            sys.exit(1)
    elif args.command == "events":
        if args.events_command == "export-sessions":
            cmd_events_export(args)
        else:
            events_parser.print_help()
            sys.exit(1)
    elif args.command == "index":
        if args.index_command == "rebuild":
            cmd_index_rebuild(args)
        else:
            index_parser.print_help()
            sys.exit(1)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "git-event":
        cmd_git_event(args)
    elif args.command == "mcp":
        if args.mcp_command == "serve":
            cmd_mcp_serve(args)
        else:
            mcp_parser.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
