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
import sys
from pathlib import Path


def cmd_serve(args):
    """Start the HtmlGraph server."""
    from htmlgraph.server import serve
    serve(
        port=args.port,
        graph_dir=args.graph_dir,
        static_dir=args.static_dir,
        host=args.host
    )


def cmd_init(args):
    """Initialize a new .htmlgraph directory."""
    from htmlgraph.server import HtmlGraphAPIHandler

    graph_dir = Path(args.dir) / ".htmlgraph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    for collection in HtmlGraphAPIHandler.COLLECTIONS:
        (graph_dir / collection).mkdir(exist_ok=True)

    # Copy stylesheet
    styles_src = Path(__file__).parent / "styles.css"
    styles_dest = graph_dir / "styles.css"
    if styles_src.exists() and not styles_dest.exists():
        styles_dest.write_text(styles_src.read_text())

    # Create default index.html if not exists
    index_path = Path(args.dir) / "index.html"
    if not index_path.exists():
        create_default_index(index_path)

    print(f"Initialized HtmlGraph in {graph_dir}")
    print(f"Collections: {', '.join(HtmlGraphAPIHandler.COLLECTIONS)}")
    print(f"\nStart server with: htmlgraph serve")


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


# =============================================================================
# Feature Management Commands
# =============================================================================

def cmd_feature_start(args):
    """Start working on a feature."""
    from htmlgraph.session_manager import SessionManager
    import json

    manager = SessionManager(args.graph_dir)

    try:
        node = manager.start_feature(args.id, collection=args.collection)
    except FileNotFoundError:
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
        node = manager.complete_feature(args.id, collection=args.collection)
    except FileNotFoundError:
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
        node = manager.set_primary_feature(args.id, collection=args.collection)
    except FileNotFoundError:
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

    # init
    init_parser = subparsers.add_parser("init", help="Initialize .htmlgraph directory")
    init_parser.add_argument("dir", nargs="?", default=".", help="Directory to initialize")

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

    # feature start
    feature_start = feature_subparsers.add_parser("start", help="Start working on a feature")
    feature_start.add_argument("id", help="Feature ID")
    feature_start.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_start.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_start.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature complete
    feature_complete = feature_subparsers.add_parser("complete", help="Mark feature as complete")
    feature_complete.add_argument("id", help="Feature ID")
    feature_complete.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_complete.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_complete.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature primary
    feature_primary = feature_subparsers.add_parser("primary", help="Set primary feature")
    feature_primary.add_argument("id", help="Feature ID")
    feature_primary.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
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
        else:
            session_parser.print_help()
            sys.exit(1)
    elif args.command == "track":
        cmd_track(args)
    elif args.command == "feature":
        if args.feature_command == "start":
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
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
