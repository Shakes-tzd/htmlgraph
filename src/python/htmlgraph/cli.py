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
    htmlgraph session end ID [--notes NOTES] [--recommend NEXT] [--blocker BLOCKER]
    htmlgraph session list
    htmlgraph session handoff [--session-id ID] [--notes NOTES] [--recommend NEXT] [--blocker BLOCKER] [--show]
    htmlgraph activity TOOL SUMMARY [--session ID] [--files FILE...]

Feature Management:
    htmlgraph feature start ID
    htmlgraph feature complete ID
    htmlgraph feature primary ID
    htmlgraph feature claim ID
    htmlgraph feature release ID
    htmlgraph feature auto-release

Track Management (Conductor-Style Planning):
    htmlgraph track new TITLE [--priority PRIORITY]
    htmlgraph track list
    htmlgraph track spec TRACK_ID TITLE
    htmlgraph track plan TRACK_ID TITLE
    htmlgraph track delete TRACK_ID

Analytics:
    htmlgraph analytics                           # Project-wide analytics
    htmlgraph analytics --session-id SESSION_ID   # Single session analysis
    htmlgraph analytics --recent N                # Analyze recent N sessions
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path


def cmd_install_gemini_extension(args):
    """Install the Gemini CLI extension from the bundled package files."""
    import htmlgraph

    # Find the extension path in the installed package
    package_dir = Path(htmlgraph.__file__).parent
    extension_dir = package_dir / "extensions" / "gemini"

    if not extension_dir.exists():
        print(f"Error: Gemini extension not found at {extension_dir}", file=sys.stderr)
        print("The extension may not be bundled with this version of htmlgraph.", file=sys.stderr)
        sys.exit(1)

    print(f"Installing Gemini extension from: {extension_dir}")

    # Run gemini extensions install with the bundled path
    try:
        result = subprocess.run(
            ["gemini", "extensions", "install", str(extension_dir), "--consent"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        print("\n✅ Gemini extension installed successfully!")
        print("\nTo verify installation:")
        print("  gemini extensions list")
    except subprocess.CalledProcessError as e:
        print(f"Error installing extension: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'gemini' command not found.", file=sys.stderr)
        print("Please install Gemini CLI first:", file=sys.stderr)
        print("  npm install -g @google/gemini-cli", file=sys.stderr)
        sys.exit(1)


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

    pre_commit = """#!/bin/bash
#
# HtmlGraph Pre-Commit Hook
# Reminds developers to create/start features for non-trivial work
#
# To disable: git config htmlgraph.precommit false
# To bypass once: git commit --no-verify

# Check if hook is disabled via config
if [ "$(git config --type=bool htmlgraph.precommit)" = "false" ]; then
    exit 0
fi

# Check if HtmlGraph is initialized
if [ ! -d ".htmlgraph" ]; then
    # Not an HtmlGraph project, skip silently
    exit 0
fi

# Fast check for in-progress features using grep (avoids Python startup)
# This is 10-100x faster than calling the CLI
ACTIVE_COUNT=$(find .htmlgraph/features -name "*.html" -exec grep -l 'data-status="in-progress"' {} \\; 2>/dev/null | wc -l | tr -d ' ')

# If we have active features and htmlgraph CLI is available, get details
if [ "$ACTIVE_COUNT" -gt 0 ] && command -v htmlgraph &> /dev/null; then
    ACTIVE_FEATURES=$(htmlgraph feature list --status in-progress 2>/dev/null)
else
    ACTIVE_FEATURES=""
fi

# Redirect output to stderr (standard for git hooks)
exec 1>&2

if [ "$ACTIVE_COUNT" -gt 0 ]; then
    # Active features exist - show them
    echo ""
    echo "✓ HtmlGraph: $ACTIVE_COUNT active feature(s)"
    echo ""
    echo "$ACTIVE_FEATURES"
    echo ""
else
    # No active features - show reminder
    echo ""
    echo "⚠️  HtmlGraph Feature Reminder"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "No active features found. Did you forget to start one?"
    echo ""
    echo "For non-trivial work, consider:"
    echo "  1. Create feature: (use Python API or dashboard)"
    echo "  2. Start feature: htmlgraph feature start <feature-id>"
    echo ""
    echo "Quick decision:"
    echo "  • >30 min work? → Create feature"
    echo "  • 3+ files? → Create feature"
    echo "  • Needs tests? → Create feature"
    echo "  • Simple fix? → Direct commit OK"
    echo ""
    echo "To disable this reminder: git config htmlgraph.precommit false"
    echo "To bypass once: git commit --no-verify"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Proceeding with commit..."
    echo ""
fi

# Always exit 0 (allow commit)
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
        "pre-commit": ensure_hook_file("pre-commit", pre_commit),
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

        install_hook("pre-commit", hook_files["pre-commit"], pre_commit)
        install_hook("post-commit", hook_files["post-commit"], post_commit)
        install_hook("post-checkout", hook_files["post-checkout"], post_checkout)
        install_hook("post-merge", hook_files["post-merge"], post_merge)
        install_hook("pre-push", hook_files["pre-push"], pre_push)

        print("\nGit events will now be logged to HtmlGraph automatically.")


def cmd_status(args):
    """Show status of the graph."""
    from htmlgraph.sdk import SDK
    from collections import Counter

    # Use SDK to query all collections
    sdk = SDK(directory=args.graph_dir)

    total = 0
    by_status = Counter()
    by_collection = {}

    # All available collections
    collections = ['features', 'bugs', 'chores', 'spikes', 'epics', 'phases', 'sessions', 'tracks', 'agents']

    for coll_name in collections:
        coll = getattr(sdk, coll_name)
        try:
            nodes = coll.all()
            count = len(nodes)
            if count > 0:
                by_collection[coll_name] = count
                total += count

                # Count by status
                for node in nodes:
                    status = getattr(node, 'status', 'unknown')
                    by_status[status] += 1
        except Exception:
            # Collection might not exist yet
            pass

    print(f"HtmlGraph Status: {args.graph_dir}")
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
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    session = sdk.start_session(
        session_id=args.id,
        title=args.title,
        agent=args.agent
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
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir)
    blockers = args.blocker if args.blocker else None
    session = sdk.end_session(
        args.id,
        handoff_notes=args.notes,
        recommended_next=args.recommend,
        blockers=blockers,
    )

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


def cmd_session_handoff(args):
    """Set or show session handoff context."""
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    if args.show:
        # For showing, we might still need direct manager access or add more methods to SDK
        # But for now, let's keep using SessionManager logic via SDK property if needed
        # or implement show logic here using SDK collections
        
        # If args.session_id, use SDK.sessions.get()
        if args.session_id:
            session = sdk.sessions.get(args.session_id)
        else:
            # Need "last ended session" - SDK doesn't expose this yet.
            # Fallback to session_manager logic exposed on SDK
            session = sdk.session_manager.get_last_ended_session(agent=args.agent)

        if not session:
            if args.format == "json":
                print(json.dumps({}))
            else:
                print("No handoff context found.")
            return

        if args.format == "json":
            from htmlgraph.converter import session_to_dict
            print(json.dumps(session_to_dict(session), indent=2))
        else:
            print(f"Session: {session.id}")
            if session.handoff_notes:
                print(f"Notes: {session.handoff_notes}")
            if session.recommended_next:
                print(f"Recommended next: {session.recommended_next}")
            if session.blockers:
                print(f"Blockers: {', '.join(session.blockers)}")
        return

    # Setting handoff
    if not (args.notes or args.recommend or args.blocker):
        print("Error: Provide --notes, --recommend, or --blocker (or use --show).", file=sys.stderr)
        sys.exit(1)

    session = sdk.set_session_handoff(
        session_id=args.session_id, # Optional, defaults to active
        handoff_notes=args.notes,
        recommended_next=args.recommend,
        blockers=args.blocker if args.blocker else None,
    )

    if session is None:
        if args.session_id:
            print(f"Error: Session '{args.session_id}' not found.", file=sys.stderr)
        else:
            print(f"Error: No active session found. Provide --session-id.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import session_to_dict
        print(json.dumps(session_to_dict(session), indent=2))
    else:
        print(f"Session handoff updated: {session.id}")

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


def cmd_session_status_report(args):
    """Print a comprehensive status report (Markdown)."""
    from htmlgraph.sdk import SDK
    import subprocess

    sdk = SDK(directory=args.graph_dir)
    status = sdk.get_status()

    # Git log
    try:
        git_log = subprocess.check_output(
            ["git", "log", "--oneline", "-n", "3"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        git_log = "(Git log unavailable)"

    # Active features detail
    active_features_text = ""
    if status['active_features']:
        active_features_text = "\n### Current Feature(s)\n"
        for fid in status['active_features']:
            # Use SDK to get nodes
            node = sdk.features.get(fid) or sdk.bugs.get(fid)
            if node:
                active_features_text += f"**Working On:** {node.title} ({node.id})\n"
                active_features_text += f"**Status:** {node.status}\n"
                if node.steps:
                    active_features_text += "**Step Progress**\n"
                    for step in node.steps:
                        mark = "[x]" if step.completed else "[ ]"
                        active_features_text += f"- {mark} {step.description}\n"
                active_features_text += "\n"
    else:
        active_features_text = "\n### Current Feature(s)\nNo active features. Start one with `htmlgraph feature start <id>`.\n"

    # Project Name (from directory)
    project_name = Path(args.graph_dir).resolve().parent.name

    completed = status['by_status'].get('done', 0)
    total = status['total_features']
    pct = int(completed / max(1, total) * 100)

    print(f"""## Session Status

**Project:** {project_name}
**Progress:** {completed}/{total} features ({pct}%)
**Active Features (WIP):** {status['wip_count']}

---
{active_features_text}---

### Recent Commits
{git_log}

---

### What's Next
Use `htmlgraph feature list --status todo` to see backlog.
""")


def cmd_session_dedupe(args):
    """Move low-signal session files out of the main sessions directory."""
    from htmlgraph import SDK

    sdk = SDK(directory=args.graph_dir)
    result = sdk.dedupe_sessions(
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
    from htmlgraph import SDK
    import json

    agent = os.environ.get("HTMLGRAPH_AGENT")
    sdk = SDK(directory=args.graph_dir, agent=agent)

    try:
        entry = sdk.track_activity(
            tool=args.tool,
            summary=args.summary,
            file_paths=args.files,
            success=not args.failed,
            session_id=args.session  # None if not specified, SDK will find active session
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

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
# Work Management Commands (Smart Routing)
# =============================================================================

def cmd_work_next(args):
    """Get next best task using smart routing."""
    from htmlgraph.sdk import SDK
    from htmlgraph.converter import node_to_dict
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    try:
        task = sdk.work_next(
            agent_id=args.agent,
            auto_claim=args.auto_claim,
            min_score=args.min_score
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        if task:
            print(json.dumps(node_to_dict(task), indent=2, default=str))
        else:
            print(json.dumps({"task": None, "message": "No suitable tasks found"}, indent=2))
    else:
        if task:
            print(f"Next task: {task.id}")
            print(f"  Title: {task.title}")
            print(f"  Priority: {task.priority}")
            print(f"  Status: {task.status}")
            if task.required_capabilities:
                print(f"  Required capabilities: {', '.join(task.required_capabilities)}")
            if task.complexity:
                print(f"  Complexity: {task.complexity}")
            if task.estimated_effort:
                print(f"  Estimated effort: {task.estimated_effort}h")
            if args.auto_claim:
                print(f"  ✓ Task claimed by {args.agent}")
        else:
            print("No suitable tasks found.")
            print("Try lowering --min-score or check available tasks with 'htmlgraph feature list --status todo'")


def cmd_work_queue(args):
    """Get prioritized work queue for an agent."""
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    try:
        queue = sdk.get_work_queue(
            agent_id=args.agent,
            limit=args.limit,
            min_score=args.min_score
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps({"queue": queue, "count": len(queue)}, indent=2))
    else:
        if not queue:
            print(f"No tasks found for agent '{args.agent}'.")
            print("Try lowering --min-score or check available tasks with 'htmlgraph feature list --status todo'")
            return

        print(f"Work queue for {args.agent} ({len(queue)} tasks):")
        print("=" * 90)
        print(f"{'Score':<8} {'Priority':<10} {'Complexity':<12} {'ID':<25} {'Title'}")
        print("=" * 90)

        for item in queue:
            complexity = item.get('complexity', 'N/A') or 'N/A'
            title = item['title'][:30] + "..." if len(item['title']) > 33 else item['title']
            print(f"{item['score']:<8.1f} {item['priority']:<10} {complexity:<12} {item['task_id']:<25} {title}")


def cmd_agent_list(args):
    """List all registered agents."""
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir)
    agents = sdk.list_agents(active_only=args.active_only)

    if args.format == "json":
        print(json.dumps(
            {"agents": [agent.to_dict() for agent in agents], "count": len(agents)},
            indent=2
        ))
    else:
        if not agents:
            print("No agents registered.")
            print("Agents are automatically registered in .htmlgraph/agents.json")
            return

        print(f"Registered agents ({len(agents)}):")
        print("=" * 90)

        for agent in agents:
            status = "✓ active" if agent.active else "✗ inactive"
            print(f"\n{agent.id} ({agent.name}) - {status}")
            print(f"  Capabilities: {', '.join(agent.capabilities)}")
            print(f"  Max parallel tasks: {agent.max_parallel_tasks}")
            print(f"  Preferred complexity: {', '.join(agent.preferred_complexity)}")


# =============================================================================
# Feature Management Commands
# =============================================================================

def cmd_feature_create(args):
    """Create a new feature."""
    from htmlgraph.sdk import SDK
    import json

    # Use SDK for feature creation (which now handles logging)
    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    try:
        # Determine collection (features -> create builder, others -> manual create?)
        # For now, only 'features' has a builder in SDK.features.create()
        # But BaseCollection doesn't have create().
        
        # If collection is 'features', use builder
        if args.collection == "features":
            builder = sdk.features.create(
                title=args.title,
                description=args.description or "",
                priority=args.priority
            )
            if args.steps:
                builder.add_steps(args.steps)
            node = builder.save()
        else:
            # Fallback to SessionManager directly for non-feature collections 
            # (or extend SDK to support create on all collections)
            # For consistency with old CLI, we use SessionManager here if not features.
            # But wait, SDK initializes SessionManager.
            
            # Creating bugs/chores via SDK isn't fully fluent yet.
            # Let's use the low-level SessionManager.create_feature logic for now via SDK's session_manager
            # IF we want to strictly use SDK. But SDK.session_manager IS exposed now.
            node = sdk.session_manager.create_feature(
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
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    collection = getattr(sdk, args.collection, None)
    
    if not collection:
        print(f"Error: Collection '{args.collection}' not found in SDK.", file=sys.stderr)
        sys.exit(1)

    try:
        node = collection.start(args.id)
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
        status = sdk.session_manager.get_status()
        print(f"  WIP: {status['wip_count']}/{status['wip_limit']}")


def cmd_feature_complete(args):
    """Mark a feature as complete."""
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    collection = getattr(sdk, args.collection, None)

    if not collection:
        print(f"Error: Collection '{args.collection}' not found in SDK.", file=sys.stderr)
        sys.exit(1)

    try:
        node = collection.complete(args.id)
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
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    
    # Only FeatureCollection has set_primary currently
    if args.collection == "features":
        node = sdk.features.set_primary(args.id)
    else:
        # Fallback to direct session manager for other collections
        node = sdk.session_manager.set_primary_feature(args.id, collection=args.collection, agent=args.agent)

    if node is None:
        print(f"Error: Feature '{args.id}' not found in {args.collection}.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict
        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Primary feature set: {node.id}")
        print(f"  Title: {node.title}")


def cmd_feature_claim(args):
    """Claim a feature."""
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    collection = getattr(sdk, args.collection, None)

    if not collection:
        print(f"Error: Collection '{args.collection}' not found in SDK.", file=sys.stderr)
        sys.exit(1)

    try:
        node = collection.claim(args.id)
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
        print(f"Claimed: {node.id}")
        print(f"  Agent: {node.agent_assigned}")
        print(f"  Session: {node.claimed_by_session}")


def cmd_feature_release(args):
    """Release a feature."""
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    collection = getattr(sdk, args.collection, None)

    if not collection:
        print(f"Error: Collection '{args.collection}' not found in SDK.", file=sys.stderr)
        sys.exit(1)

    try:
        node = collection.release(args.id)
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
        print(f"Released: {node.id}")


def cmd_feature_auto_release(args):
    """Release all features claimed by an agent."""
    from htmlgraph.sdk import SDK
    import json

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    # auto_release_features is on SessionManager, exposed via SDK
    released = sdk.session_manager.auto_release_features(agent=args.agent)

    if args.format == "json":
        print(json.dumps({"released": released}, indent=2))
    else:
        if not released:
            print(f"No features claimed by agent '{args.agent}'.")
        else:
            print(f"Released {len(released)} feature(s):")
            for node_id in released:
                print(f"  - {node_id}")


def cmd_publish(args):
    """Build and publish the package to PyPI (Interoperable)."""
    import shutil
    import subprocess

    # Ensure we are in project root
    if not Path("pyproject.toml").exists():
        print("Error: pyproject.toml not found. Run this from the project root.", file=sys.stderr)
        sys.exit(1)

    # 1. Clean dist/
    dist_dir = Path("dist")
    if dist_dir.exists():
        print("Cleaning dist/...")
        shutil.rmtree(dist_dir)

    # 2. Build
    print("Building package with uv...")
    try:
        subprocess.run(["uv", "build"], check=True)
    except subprocess.CalledProcessError:
        print("Error: Build failed.", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'uv' command not found.", file=sys.stderr)
        sys.exit(1)

    # 3. Publish
    if args.dry_run:
        print("Dry run: Skipping publish.")
        return

    print("Publishing to PyPI...")
    env = os.environ.copy()

    # Smart credential loading from .env
    # Maps PyPI_API_TOKEN (common in .env) to UV_PUBLISH_TOKEN (needed by uv)
    if "UV_PUBLISH_TOKEN" not in env:
        dotenv = Path(".env")
        if dotenv.exists():
            try:
                content = dotenv.read_text()
                for line in content.splitlines():
                    if line.strip() and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'").strip('"')
                        if key == "PyPI_API_TOKEN":
                            env["UV_PUBLISH_TOKEN"] = val
                            print("Loaded credentials from .env")
            except Exception:
                pass

    try:
        subprocess.run(["uv", "publish"], env=env, check=True)
        print("\n✅ Successfully published!")
    except subprocess.CalledProcessError:
        print("\n❌ Publish failed.", file=sys.stderr)
        sys.exit(1)


def cmd_feature_list(args):
    """List features by status."""
    from htmlgraph.sdk import SDK
    from htmlgraph.converter import node_to_dict
    import json

    # Use SDK for feature queries
    sdk = SDK(directory=args.graph_dir)

    # Query features with SDK
    if args.status:
        nodes = sdk.features.where(status=args.status)
    else:
        nodes = sdk.features.all()

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


# =============================================================================
# Track Management Commands (Conductor-Style Planning)
# =============================================================================

def cmd_feature_step_complete(args):
    """Mark one or more feature steps as complete via API."""
    import json
    import http.client

    # Parse step indices (support both space-separated and comma-separated)
    step_indices = []
    for step_arg in args.steps:
        if ',' in step_arg:
            # Comma-separated: "0,1,2"
            step_indices.extend(int(s.strip()) for s in step_arg.split(',') if s.strip())
        else:
            # Space-separated: "0" "1" "2"
            step_indices.append(int(step_arg))

    # Remove duplicates and sort
    step_indices = sorted(set(step_indices))

    if not step_indices:
        print("Error: No step indices provided", file=sys.stderr)
        sys.exit(1)

    # Make API requests for each step
    success_count = 0
    error_count = 0
    results = []

    for step_index in step_indices:
        try:
            conn = http.client.HTTPConnection(args.host, args.port, timeout=5)
            body = json.dumps({"complete_step": step_index})
            headers = {"Content-Type": "application/json"}
            
            conn.request("PATCH", f"/api/{args.collection}/{args.id}", body, headers)
            response = conn.getresponse()
            response_data = response.read().decode()
            
            if response.status == 200:
                success_count += 1
                results.append({"step": step_index, "status": "success"})
                if args.format != "json":
                    print(f"✓ Marked step {step_index} complete")
            else:
                error_count += 1
                results.append({"step": step_index, "status": "error", "message": response_data})
                if args.format != "json":
                    print(f"✗ Failed to mark step {step_index} complete: {response_data}", file=sys.stderr)
            
            conn.close()
        except Exception as e:
            error_count += 1
            results.append({"step": step_index, "status": "error", "message": str(e)})
            if args.format != "json":
                print(f"✗ Error marking step {step_index} complete: {e}", file=sys.stderr)

    # Output results
    if args.format == "json":
        output = {
            "feature_id": args.id,
            "total_steps": len(step_indices),
            "success": success_count,
            "errors": error_count,
            "results": results
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nCompleted {success_count}/{len(step_indices)} steps for feature '{args.id}'")
        if error_count > 0:
            sys.exit(1)



def cmd_feature_delete(args):
    """Delete a feature."""
    from htmlgraph import SDK
    import json
    import sys

    sdk = SDK(agent=getattr(args, "agent", "cli"), directory=args.graph_dir)

    # Get the feature first to show confirmation
    collection = getattr(sdk, args.collection, None)
    if not collection:
        print(f"Error: Collection '{args.collection}' not found", file=sys.stderr)
        sys.exit(1)

    feature = collection.get(args.id)
    if not feature:
        print(f"Error: {args.collection.rstrip('s').capitalize()} '{args.id}' not found", file=sys.stderr)
        sys.exit(1)

    # Confirmation prompt (unless --yes flag)
    if not args.yes:
        print(f"Delete {args.collection.rstrip('s')} '{args.id}'?")
        print(f"  Title: {feature.title}")
        print(f"  Status: {feature.status}")
        print(f"\nThis cannot be undone. Continue? [y/N] ", end="")

        response = input().strip().lower()
        if response not in ('y', 'yes'):
            print("Cancelled")
            sys.exit(0)

    # Delete
    try:
        success = collection.delete(args.id)
        if success:
            if args.format == "json":
                data = {
                    "id": args.id,
                    "title": feature.title,
                    "deleted": True
                }
                print(json.dumps(data, indent=2))
            else:
                print(f"Deleted {args.collection.rstrip('s')}: {args.id}")
                print(f"  Title: {feature.title}")
        else:
            print(f"Error: Failed to delete {args.collection.rstrip('s')} '{args.id}'", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_track_new(args):
    """Create a new track."""
    from htmlgraph.track_manager import TrackManager
    import json

    manager = TrackManager(args.graph_dir)

    try:
        track = manager.create_track(
            title=args.title,
            description=args.description or "",
            priority=args.priority,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {
            "id": track.id,
            "title": track.title,
            "status": track.status,
            "priority": track.priority,
            "path": f"{args.graph_dir}/tracks/{track.id}/"
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Created track: {track.id}")
        print(f"  Title: {track.title}")
        print(f"  Status: {track.status}")
        print(f"  Priority: {track.priority}")
        print(f"  Path: {args.graph_dir}/tracks/{track.id}/")
        print(f"\nNext steps:")
        print(f"  - Create spec: htmlgraph track spec {track.id} 'Spec Title'")
        print(f"  - Create plan: htmlgraph track plan {track.id} 'Plan Title'")


def cmd_track_list(args):
    """List all tracks."""
    from htmlgraph.track_manager import TrackManager
    import json

    manager = TrackManager(args.graph_dir)
    track_ids = manager.list_tracks()

    if args.format == "json":
        print(json.dumps({"tracks": track_ids}, indent=2))
    else:
        if not track_ids:
            print("No tracks found.")
            print(f"\nCreate a track with: htmlgraph track new 'Track Title'")
            return

        print(f"Tracks in {args.graph_dir}/tracks/:")
        print("=" * 60)
        for track_id in track_ids:
            # Check for both consolidated (single file) and directory-based formats
            track_file = Path(args.graph_dir) / "tracks" / f"{track_id}.html"
            track_dir = Path(args.graph_dir) / "tracks" / track_id

            if track_file.exists():
                # Consolidated format - spec and plan are in the same file
                content = track_file.read_text(encoding="utf-8")
                has_spec = 'data-section="overview"' in content or 'data-section="requirements"' in content
                has_plan = 'data-section="plan"' in content
                format_indicator = " (consolidated)"
            else:
                # Directory format
                has_spec = (track_dir / "spec.html").exists()
                has_plan = (track_dir / "plan.html").exists()
                format_indicator = ""

            components = []
            if has_spec:
                components.append("spec")
            if has_plan:
                components.append("plan")

            components_str = f" [{', '.join(components)}]" if components else " [empty]"
            print(f"  {track_id}{components_str}{format_indicator}")


def cmd_track_spec(args):
    """Create a spec for a track."""
    from htmlgraph.track_manager import TrackManager
    import json

    manager = TrackManager(args.graph_dir)

    # Check if track uses consolidated format
    if manager.is_consolidated(args.track_id):
        track_file = manager.tracks_dir / f"{args.track_id}.html"
        print(f"Track '{args.track_id}' uses consolidated single-file format.")
        print(f"Spec is embedded in: {track_file}")
        print(f"\nTo create a track with separate spec/plan files, use:")
        print(f"  sdk.tracks.builder().separate_files().title('...').create()")
        return

    try:
        spec = manager.create_spec(
            track_id=args.track_id,
            title=args.title,
            overview=args.overview or "",
            context=args.context or "",
            author=args.author,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {
            "id": spec.id,
            "title": spec.title,
            "track_id": spec.track_id,
            "status": spec.status,
            "path": f"{args.graph_dir}/tracks/{args.track_id}/spec.html"
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Created spec: {spec.id}")
        print(f"  Title: {spec.title}")
        print(f"  Track: {spec.track_id}")
        print(f"  Status: {spec.status}")
        print(f"  Path: {args.graph_dir}/tracks/{args.track_id}/spec.html")
        print(f"\nView spec: open {args.graph_dir}/tracks/{args.track_id}/spec.html")


def cmd_track_plan(args):
    """Create a plan for a track."""
    from htmlgraph.track_manager import TrackManager
    import json

    manager = TrackManager(args.graph_dir)

    # Check if track uses consolidated format
    if manager.is_consolidated(args.track_id):
        track_file = manager.tracks_dir / f"{args.track_id}.html"
        print(f"Track '{args.track_id}' uses consolidated single-file format.")
        print(f"Plan is embedded in: {track_file}")
        print(f"\nTo create a track with separate spec/plan files, use:")
        print(f"  sdk.tracks.builder().separate_files().title('...').create()")
        return

    try:
        plan = manager.create_plan(
            track_id=args.track_id,
            title=args.title,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {
            "id": plan.id,
            "title": plan.title,
            "track_id": plan.track_id,
            "status": plan.status,
            "path": f"{args.graph_dir}/tracks/{args.track_id}/plan.html"
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Created plan: {plan.id}")
        print(f"  Title: {plan.title}")
        print(f"  Track: {plan.track_id}")
        print(f"  Status: {plan.status}")
        print(f"  Path: {args.graph_dir}/tracks/{args.track_id}/plan.html")
        print(f"\nView plan: open {args.graph_dir}/tracks/{args.track_id}/plan.html")


def cmd_track_delete(args):
    """Delete a track."""
    from htmlgraph.track_manager import TrackManager
    import json

    manager = TrackManager(args.graph_dir)

    try:
        manager.delete_track(args.track_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {
            "deleted": True,
            "track_id": args.track_id
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"✓ Deleted track: {args.track_id}")
        print(f"  Removed: {args.graph_dir}/tracks/{args.track_id}/")


def create_default_index(path: Path):
    """
    Create a default index.html for new projects.

    The dashboard UI evolves quickly; to keep new projects consistent with the
    current dashboard, prefer a packaged HTML template over a hardcoded string.
    """
    template = Path(__file__).parent / "dashboard.html"
    try:
        if template.exists():
            path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
            return
    except Exception:
        pass

    # Fallback (rare): minimal landing page.
    path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>HtmlGraph</title></head>"
        "<body><h1>HtmlGraph</h1><p>Run <code>htmlgraph serve</code> and open "
        "<code>http://localhost:8080</code>.</p></body></html>",
        encoding="utf-8",
    )


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
  htmlgraph activity Edit "Edit: src/app.py:45-60" --files src/app.py

Feature Management:
  htmlgraph feature list            # List all features
  htmlgraph feature start feat-001  # Start working on a feature
  htmlgraph feature primary feat-001  # Set primary feature
  htmlgraph feature claim feat-001  # Claim feature for current agent
  htmlgraph feature release feat-001  # Release claim
  htmlgraph feature auto-release    # Release all claims for agent
  htmlgraph feature step-complete feat-001 0 1 2  # Mark steps complete
  htmlgraph feature complete feat-001  # Mark feature as done

Track Management (Conductor-Style Planning):
  htmlgraph track new "User Authentication"  # Create a new track
  htmlgraph track list              # List all tracks
  htmlgraph track spec track-001-auth "Auth Specification"  # Create spec
  htmlgraph track plan track-001-auth "Auth Implementation Plan"  # Create plan

Analytics:
  htmlgraph analytics               # Project-wide work type analytics
  htmlgraph analytics --recent 10   # Analyze last 10 sessions
  htmlgraph analytics --session-id session-123  # Detailed session metrics

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
    session_end.add_argument("--notes", help="Handoff notes for the next session")
    session_end.add_argument("--recommend", help="Recommended next steps")
    session_end.add_argument("--blocker", action="append", default=[], help="Blocker to record (repeatable)")
    session_end.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    session_end.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # session handoff
    session_handoff = session_subparsers.add_parser("handoff", help="Set or show session handoff context")
    session_handoff.add_argument("--session-id", help="Session ID (defaults to active session)")
    session_handoff.add_argument("--agent", help="Agent filter (used for --show when no session provided)")
    session_handoff.add_argument("--notes", help="Handoff notes for the next session")
    session_handoff.add_argument("--recommend", help="Recommended next steps")
    session_handoff.add_argument("--blocker", action="append", default=[], help="Blocker to record (repeatable)")
    session_handoff.add_argument("--show", action="store_true", help="Show handoff context instead of setting it")
    session_handoff.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    session_handoff.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # session list
    session_list = session_subparsers.add_parser("list", help="List all sessions")
    session_list.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    session_list.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # session status-report (and resume alias)
    session_report = session_subparsers.add_parser("status-report", help="Print comprehensive session status report")
    session_report.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    
    session_resume = session_subparsers.add_parser("resume", help="Alias for status-report (Resume session context)")
    session_resume.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")

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

    # activity (legacy: was "track")
    activity_parser = subparsers.add_parser("activity", help="Track an activity (legacy: use 'htmlgraph track' for new features)")
    activity_parser.add_argument("tool", help="Tool name (Edit, Bash, Read, etc.)")
    activity_parser.add_argument("summary", help="Activity summary")
    activity_parser.add_argument("--session", help="Session ID (uses active session if not provided)")
    activity_parser.add_argument("--files", nargs="*", help="Files involved")
    activity_parser.add_argument("--failed", action="store_true", help="Mark as failed")
    activity_parser.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    activity_parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # =========================================================================
    # Work Management (Smart Routing)
    # =========================================================================

    # work (with subcommands)
    work_parser = subparsers.add_parser("work", help="Work management with smart routing")
    work_subparsers = work_parser.add_subparsers(dest="work_command", help="Work command")

    # work next
    work_next = work_subparsers.add_parser("next", help="Get next best task using smart routing")
    work_next.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "claude",
        help="Agent ID (default: $HTMLGRAPH_AGENT or 'claude')",
    )
    work_next.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    work_next.add_argument("--auto-claim", action="store_true", help="Automatically claim the task")
    work_next.add_argument("--min-score", type=float, default=20.0, help="Minimum routing score (default: 20.0)")
    work_next.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # work queue
    work_queue = work_subparsers.add_parser("queue", help="Get prioritized work queue")
    work_queue.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "claude",
        help="Agent ID (default: $HTMLGRAPH_AGENT or 'claude')",
    )
    work_queue.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    work_queue.add_argument("--limit", "-l", type=int, default=10, help="Maximum tasks to show (default: 10)")
    work_queue.add_argument("--min-score", type=float, default=20.0, help="Minimum routing score (default: 20.0)")
    work_queue.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # agent (with subcommands)
    agent_parser = subparsers.add_parser("agent", help="Agent management")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command", help="Agent command")

    # agent list
    agent_list = agent_subparsers.add_parser("list", help="List all registered agents")
    agent_list.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    agent_list.add_argument("--active-only", action="store_true", help="Only show active agents")
    agent_list.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

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

    # feature claim
    feature_claim = feature_subparsers.add_parser("claim", help="Claim a feature")
    feature_claim.add_argument("id", help="Feature ID")
    feature_claim.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_claim.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_claim.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_claim.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature release
    feature_release = feature_subparsers.add_parser("release", help="Release a feature claim")
    feature_release.add_argument("id", help="Feature ID")
    feature_release.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_release.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_release.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_release.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature auto-release
    feature_auto_release = feature_subparsers.add_parser("auto-release", help="Release all features claimed by agent")
    feature_auto_release.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_auto_release.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_auto_release.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature list
    feature_list = feature_subparsers.add_parser("list", help="List features")
    feature_list.add_argument("--status", "-s", help="Filter by status")
    feature_list.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_list.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_list.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # feature step-complete
    feature_step_complete = feature_subparsers.add_parser("step-complete", help="Mark feature step(s) as complete")
    feature_step_complete.add_argument("id", help="Feature ID")
    feature_step_complete.add_argument("steps", nargs="+", help="Step index(es) to mark complete (0-based, supports: 0 1 2 or 0,1,2)")
    feature_step_complete.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_step_complete.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_step_complete.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_step_complete.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")
    feature_step_complete.add_argument("--host", default="localhost", help="API host (default: localhost)")
    feature_step_complete.add_argument("--port", type=int, default=8080, help="API port (default: 8080)")

    # feature delete
    feature_delete = feature_subparsers.add_parser("delete", help="Delete a feature")
    feature_delete.add_argument("id", help="Feature ID to delete")
    feature_delete.add_argument("--collection", "-c", default="features", help="Collection (features, bugs)")
    feature_delete.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    feature_delete.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    feature_delete.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # =========================================================================
    # Track Management (Conductor-Style Planning)
    # =========================================================================

    # track (with subcommands)
    track_parser = subparsers.add_parser("track", help="Track management (Conductor-style planning)")
    track_subparsers = track_parser.add_subparsers(dest="track_command", help="Track command")

    # track new
    track_new = track_subparsers.add_parser("new", help="Create a new track")
    track_new.add_argument("title", help="Track title")
    track_new.add_argument("--description", "-d", help="Track description")
    track_new.add_argument("--priority", "-p", default="medium", choices=["low", "medium", "high", "critical"], help="Priority")
    track_new.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    track_new.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # track list
    track_list = track_subparsers.add_parser("list", help="List all tracks")
    track_list.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    track_list.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # track spec
    track_spec = track_subparsers.add_parser("spec", help="Create a spec for a track")
    track_spec.add_argument("track_id", help="Track ID")
    track_spec.add_argument("title", help="Spec title")
    track_spec.add_argument("--overview", "-o", help="Spec overview")
    track_spec.add_argument("--context", "-c", help="Context/rationale")
    track_spec.add_argument("--author", "-a", default="claude-code", help="Spec author")
    track_spec.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    track_spec.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # track plan
    track_plan = track_subparsers.add_parser("plan", help="Create a plan for a track")
    track_plan.add_argument("track_id", help="Track ID")
    track_plan.add_argument("title", help="Plan title")
    track_plan.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    track_plan.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # track delete
    track_delete = track_subparsers.add_parser("delete", help="Delete a track")
    track_delete.add_argument("track_id", help="Track ID to delete")
    track_delete.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")
    track_delete.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")

    # =========================================================================
    # Analytics
    # =========================================================================

    # analytics
    analytics_parser = subparsers.add_parser("analytics", help="Work type analytics and project health metrics")
    analytics_parser.add_argument("--session-id", "-s", help="Analyze specific session ID")
    analytics_parser.add_argument("--recent", "-r", type=int, help="Analyze N recent sessions")
    analytics_parser.add_argument("--agent", default="cli", help="Agent name for SDK initialization")
    analytics_parser.add_argument("--graph-dir", "-g", default=".htmlgraph", help="Graph directory")

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

    # setup
    setup_parser = subparsers.add_parser("setup", help="Set up HtmlGraph for AI CLI platforms")
    setup_subparsers = setup_parser.add_subparsers(dest="setup_command", help="Platform to set up")

    setup_claude = setup_subparsers.add_parser("claude", help="Set up for Claude Code")
    setup_claude.add_argument("--auto-install", action="store_true", help="Automatically install when possible")

    setup_codex = setup_subparsers.add_parser("codex", help="Set up for Codex CLI")
    setup_codex.add_argument("--auto-install", action="store_true", help="Automatically install when possible")

    setup_gemini = setup_subparsers.add_parser("gemini", help="Set up for Gemini CLI")
    setup_gemini.add_argument("--auto-install", action="store_true", help="Automatically install when possible")

    setup_all_parser = setup_subparsers.add_parser("all", help="Set up for all supported platforms")
    setup_all_parser.add_argument("--auto-install", action="store_true", help="Automatically install when possible")

    # publish
    publish_parser = subparsers.add_parser("publish", help="Build and publish package to PyPI")
    publish_parser.add_argument("--dry-run", action="store_true", help="Build only, do not publish")

    # sync-docs
    sync_docs_parser = subparsers.add_parser("sync-docs", help="Synchronize AI agent memory files across platforms")
    sync_docs_parser.add_argument("--check", action="store_true", help="Check if files are synchronized (no changes)")
    sync_docs_parser.add_argument("--generate", metavar="PLATFORM", help="Generate a platform-specific file (gemini, claude, codex)")
    sync_docs_parser.add_argument("--project-root", type=str, help="Project root directory (default: current directory)")
    sync_docs_parser.add_argument("--force", action="store_true", help="Overwrite existing files when generating")

    # deploy
    deploy_parser = subparsers.add_parser("deploy", help="Flexible deployment system for packaging and publishing")
    deploy_subparsers = deploy_parser.add_subparsers(dest="deploy_command", help="Deploy command")

    # deploy init
    deploy_init = deploy_subparsers.add_parser("init", help="Initialize deployment configuration")
    deploy_init.add_argument("--output", "-o", help="Output file path (default: htmlgraph-deploy.toml)")
    deploy_init.add_argument("--force", action="store_true", help="Overwrite existing configuration")

    # deploy run
    deploy_run = deploy_subparsers.add_parser("run", help="Run deployment process")
    deploy_run.add_argument("--config", "-c", help="Configuration file (default: htmlgraph-deploy.toml)")
    deploy_run.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    deploy_run.add_argument("--docs-only", action="store_true", help="Only commit and push to git")
    deploy_run.add_argument("--build-only", action="store_true", help="Only build package")
    deploy_run.add_argument("--skip-pypi", action="store_true", help="Skip PyPI publishing")
    deploy_run.add_argument("--skip-plugins", action="store_true", help="Skip plugin updates")

    # install-gemini-extension
    install_gemini_parser = subparsers.add_parser(
        "install-gemini-extension",
        help="Install the Gemini CLI extension from the bundled package"
    )

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
        elif args.session_command == "status-report" or args.session_command == "resume":
            cmd_session_status_report(args)
        elif args.session_command == "dedupe":
            cmd_session_dedupe(args)
        elif args.session_command == "link":
            cmd_session_link(args)
        elif args.session_command == "validate-attribution":
            cmd_session_validate_attribution(args)
        elif args.session_command == "handoff":
            cmd_session_handoff(args)
        else:
            session_parser.print_help()
            sys.exit(1)
    elif args.command == "activity":
        # Legacy activity tracking command
        cmd_track(args)
    elif args.command == "track":
        # New track management commands
        if args.track_command == "new":
            cmd_track_new(args)
        elif args.track_command == "list":
            cmd_track_list(args)
        elif args.track_command == "spec":
            cmd_track_spec(args)
        elif args.track_command == "plan":
            cmd_track_plan(args)
        elif args.track_command == "delete":
            cmd_track_delete(args)
        else:
            track_parser.print_help()
            sys.exit(1)
    elif args.command == "work":
        # Work management with smart routing
        if args.work_command == "next":
            cmd_work_next(args)
        elif args.work_command == "queue":
            cmd_work_queue(args)
        else:
            work_parser.print_help()
            sys.exit(1)
    elif args.command == "agent":
        # Agent management
        if args.agent_command == "list":
            cmd_agent_list(args)
        else:
            agent_parser.print_help()
            sys.exit(1)
    elif args.command == "feature":
        if args.feature_command == "create":
            cmd_feature_create(args)
        elif args.feature_command == "start":
            cmd_feature_start(args)
        elif args.feature_command == "complete":
            cmd_feature_complete(args)
        elif args.feature_command == "primary":
            cmd_feature_primary(args)
        elif args.feature_command == "claim":
            cmd_feature_claim(args)
        elif args.feature_command == "release":
            cmd_feature_release(args)
        elif args.feature_command == "auto-release":
            cmd_feature_auto_release(args)
        elif args.feature_command == "list":
            cmd_feature_list(args)
        elif args.feature_command == "step-complete":
            cmd_feature_step_complete(args)
        elif args.feature_command == "delete":
            cmd_feature_delete(args)
        else:
            feature_parser.print_help()
            sys.exit(1)
    elif args.command == "analytics":
        from htmlgraph.cli_analytics import cmd_analytics
        cmd_analytics(args)
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
    elif args.command == "setup":
        from htmlgraph.setup import setup_claude, setup_codex, setup_gemini, setup_all

        if args.setup_command == "claude":
            setup_claude(args)
        elif args.setup_command == "codex":
            setup_codex(args)
        elif args.setup_command == "gemini":
            setup_gemini(args)
        elif args.setup_command == "all":
            setup_all(args)
        else:
            setup_parser.print_help()
            sys.exit(1)
    elif args.command == "publish":
        cmd_publish(args)
    elif args.command == "sync-docs":
        cmd_sync_docs(args)
    elif args.command == "deploy":
        if args.deploy_command == "init":
            cmd_deploy_init(args)
        elif args.deploy_command == "run":
            cmd_deploy_run(args)
        else:
            deploy_parser.print_help()
            sys.exit(1)
    elif args.command == "install-gemini-extension":
        cmd_install_gemini_extension(args)
    else:
        parser.print_help()
        sys.exit(1)


# =============================================================================
# Deployment Commands
# =============================================================================

def cmd_deploy_init(args):
    """Initialize deployment configuration."""
    from htmlgraph.deploy import create_deployment_config_template

    output_path = Path(args.output or "htmlgraph-deploy.toml")

    if output_path.exists() and not args.force:
        print(f"Error: {output_path} already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    create_deployment_config_template(output_path)


def cmd_deploy_run(args):
    """Run deployment process."""
    from htmlgraph.deploy import DeploymentConfig, Deployer

    # Load configuration
    config_path = Path(args.config or "htmlgraph-deploy.toml")

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        print("Run 'htmlgraph deploy init' to create a template configuration.", file=sys.stderr)
        sys.exit(1)

    try:
        config = DeploymentConfig.from_toml(config_path)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle shortcut flags
    skip_steps = []
    only_steps = None

    if args.docs_only:
        only_steps = ['git-push']
    elif args.build_only:
        only_steps = ['build']
    elif args.skip_pypi:
        skip_steps.append('pypi-publish')
    elif args.skip_plugins:
        skip_steps.append('update-plugins')

    # Create deployer
    deployer = Deployer(
        config=config,
        dry_run=args.dry_run,
        skip_steps=skip_steps,
        only_steps=only_steps
    )

    # Run deployment
    deployer.deploy()


# =============================================================================
# Documentation Sync Command
# =============================================================================

def cmd_sync_docs(args):
    """Synchronize AI agent memory files across platforms."""
    from htmlgraph.sync_docs import check_all_files, sync_all_files, generate_platform_file

    project_root = Path(args.project_root or os.getcwd()).resolve()

    if args.check:
        # Check mode
        print("🔍 Checking memory files...")
        results = check_all_files(project_root)

        print("\nStatus:")
        all_good = True
        for filename, status in results.items():
            if filename == "AGENTS.md":
                if status:
                    print(f"  ✅ {filename} exists")
                else:
                    print(f"  ❌ {filename} MISSING (required)")
                    all_good = False
            else:
                if status:
                    print(f"  ✅ {filename} references AGENTS.md")
                else:
                    print(f"  ⚠️  {filename} missing reference")
                    all_good = False

        if all_good:
            print("\n✅ All files are properly synchronized!")
            return 0
        else:
            print("\n⚠️  Some files need attention")
            return 1

    elif args.generate:
        # Generate mode
        platform = args.generate.lower()
        print(f"📝 Generating {platform.upper()} memory file...")

        try:
            content = generate_platform_file(platform, project_root)
            from htmlgraph.sync_docs import PLATFORM_TEMPLATES
            template = PLATFORM_TEMPLATES[platform]
            filepath = project_root / template["filename"]

            if filepath.exists() and not args.force:
                print(f"⚠️  {filepath.name} already exists. Use --force to overwrite.")
                return 1

            filepath.write_text(content)
            print(f"✅ Created: {filepath}")
            print(f"\nThe file references AGENTS.md for core documentation.")
            return 0

        except ValueError as e:
            print(f"❌ Error: {e}")
            return 1

    else:
        # Sync mode (default)
        print("🔄 Synchronizing memory files...")
        changes = sync_all_files(project_root)

        print("\nResults:")
        for change in changes:
            print(f"  {change}")

        return 1 if any("⚠️" in c or "❌" in c for c in changes) else 0


if __name__ == "__main__":
    main()
