#!/usr/bin/env python3
"""
HtmlGraph Session Start Hook

Records session start and provides feature context to Claude.
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
from typing import Optional, Tuple

if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({}))
    sys.exit(0)


def check_htmlgraph_version() -> Tuple[Optional[str], Optional[str], bool]:
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
            ["uv", "run", "python", "-c", "import htmlgraph; print(htmlgraph.__version__)"],
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
            headers={"Accept": "application/json", "User-Agent": "htmlgraph-version-check"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get("info", {}).get("version")
    except Exception:
        pass

    is_outdated = False
    if installed_version and latest_version and installed_version != latest_version:
        # Simple version comparison (works for semver)
        try:
            installed_parts = [int(x) for x in installed_version.split(".")]
            latest_parts = [int(x) for x in latest_version.split(".")]
            is_outdated = installed_parts < latest_parts
        except ValueError:
            # Fallback to string comparison
            is_outdated = installed_version != latest_version

    return installed_version, latest_version, is_outdated

def _resolve_project_dir(cwd: Optional[str] = None) -> str:
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
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.session_manager import SessionManager
    from htmlgraph.converter import node_to_dict
except Exception as e:
    print(f"Warning: HtmlGraph not available ({e}). Install with: pip install htmlgraph", file=sys.stderr)
    print(json.dumps({}))
    sys.exit(0)


def get_features(graph_dir: Path) -> list[dict]:
    """Get all features as dicts."""
    features_dir = graph_dir / "features"
    if not features_dir.exists():
        return []
    graph = HtmlGraph(features_dir, auto_load=True)
    return [node_to_dict(node) for node in graph.nodes.values()]


def get_sessions(graph_dir: Path) -> list[dict]:
    """Get all sessions as dicts."""
    sessions_dir = graph_dir / "sessions"
    if not sessions_dir.exists():
        return []
    from htmlgraph.converter import SessionConverter, session_to_dict

    converter = SessionConverter(sessions_dir)
    sessions = converter.load_all()
    return [session_to_dict(s) for s in sessions]


def get_head_commit(project_dir: str) -> Optional[str]:
    """Get current HEAD commit hash (short form)."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


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


# HtmlGraph process notice (template with placeholder for version warning)
HTMLGRAPH_VERSION_WARNING = """## ⚠️ HTMLGRAPH UPDATE AVAILABLE

**Installed:** {installed} → **Latest:** {latest}

Update now to get the latest features and fixes:
```bash
uv pip install --upgrade htmlgraph
```

---

"""

HTMLGRAPH_PROCESS_NOTICE = """## HTMLGRAPH DEVELOPMENT PROCESS ACTIVE

**IMPORTANT: Activate the `htmlgraph-tracker` skill now using the Skill tool.**

This skill ensures proper activity attribution, documentation, and provides the Feature Creation Decision Framework throughout the session.

---

**HtmlGraph is tracking this session. All activity is logged to HTML files.**

### Feature Creation Decision Framework

**Use this framework for EVERY user request:**

Create a **FEATURE** if ANY apply:
- >30 minutes work
- 3+ files
- New tests needed
- Multi-component impact
- Hard to revert
- Needs docs

Implement **DIRECTLY** if ALL apply:
- Single file
- <30 minutes
- Trivial change
- Easy to revert
- No tests needed

**When in doubt, CREATE A FEATURE.** Over-tracking is better than losing attribution.

See the `htmlgraph-tracker` skill for complete framework details.

---

### Quick Reference

**IMPORTANT:** Always use `uv run` when running htmlgraph commands.

**Check Status:**
```bash
uv run htmlgraph status
uv run htmlgraph feature list
uv run htmlgraph session list
```

**Feature Commands:**
- `uv run htmlgraph feature start <id>` - Start working on a feature
- `uv run htmlgraph feature complete <id>` - Mark feature as done
- `uv run htmlgraph feature primary <id>` - Set primary feature for attribution

**Track Creation (for multi-feature work):**
```python
from htmlgraph import SDK
sdk = SDK(agent="claude")

# Create track with spec and plan in one command
track = sdk.tracks.builder() \\
    .title("Feature Name") \\
    .priority("high") \\
    .with_spec(overview="...", requirements=[...]) \\
    .with_plan_phases([("Phase 1", ["Task 1 (2h)", ...])]) \\
    .create()

# Link features to track
feature = sdk.features.create("Feature") \\
    .set_track(track.id) \\
    .add_steps([...]) \\
    .save()
```

**See:** `docs/TRACK_BUILDER_QUICK_START.md` for complete track creation guide

**Session Management:**
- Sessions auto-start when you begin working
- Activities are attributed to in-progress features
- Session history preserved in `.htmlgraph/sessions/`

**Dashboard:**
```bash
uv run htmlgraph serve
# Open http://localhost:8080
```

**Key Files:**
- `.htmlgraph/features/` - Feature HTML files
- `.htmlgraph/sessions/` - Session HTML files with activity logs
- `index.html` - Dashboard (open in browser)
"""


def get_feature_summary(graph_dir: Path) -> tuple[list, dict]:
    """Get features and calculate stats."""
    features = get_features(graph_dir)

    stats = {
        "total": len(features),
        "done": sum(1 for f in features if f.get("status") == "done"),
        "in_progress": sum(1 for f in features if f.get("status") == "in-progress"),
        "blocked": sum(1 for f in features if f.get("status") == "blocked"),
        "todo": sum(1 for f in features if f.get("status") == "todo"),
    }
    stats["percentage"] = int(stats["done"] * 100 / stats["total"]) if stats["total"] > 0 else 0

    return features, stats


def get_session_summary(graph_dir: Path) -> Optional[dict]:
    """Get previous session summary."""
    sessions = get_sessions(graph_dir)

    def parse_ts(value: str | None) -> datetime:
        if not value:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            # Ensure timezone-aware: if naive, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    ended = [s for s in sessions if s.get("status") == "ended"]
    if ended:
        ended.sort(key=lambda s: parse_ts(s.get("ended_at") or s.get("last_activity")), reverse=True)
        return ended[0]
    return None


def output_response(context: str, status_summary: Optional[str] = None) -> None:
    """Output JSON response with context."""
    if status_summary:
        print(f"\n{status_summary}\n", file=sys.stderr)

    print(json.dumps({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context
        }
    }))


def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    # Check for version updates (non-blocking, best-effort)
    version_warning = ""
    try:
        installed_ver, latest_ver, is_outdated = check_htmlgraph_version()
        if is_outdated and installed_ver and latest_ver:
            version_warning = HTMLGRAPH_VERSION_WARNING.format(
                installed=installed_ver,
                latest=latest_ver
            )
            print(f"⚠️  HtmlGraph update available: {installed_ver} → {latest_ver}", file=sys.stderr)
    except Exception:
        pass  # Never block on version check failure

    external_session_id = hook_input.get("session_id") or os.environ.get("CLAUDE_SESSION_ID", "unknown")
    cwd = hook_input.get("cwd")
    project_dir = _resolve_project_dir(cwd if cwd else None)
    graph_dir = Path(project_dir) / ".htmlgraph"

    # Ensure a single stable HtmlGraph session exists.
    # Do NOT create a new HtmlGraph session per external Claude session id (that can explode into many files).
    #
    # DESIGN DECISION: Task subagents share the parent's session.
    # - All work related to a conversation stays in one session file
    # - Agent attribution is tracked via data-agent attribute in activity logs
    # - This provides better continuity and easier debugging
    # - Alternative would be separate sessions per Task, but that fragments related work
    try:
        manager = SessionManager(graph_dir)
        active = manager.get_active_session()
        if not active:
            active = manager.start_session(
                session_id=None,
                agent="claude-code",
                start_commit=get_head_commit(project_dir),
                title=f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )

        # Record the external session id as a low-cost breadcrumb (for continuity debugging).
        try:
            manager.track_activity(
                session_id=active.id,
                tool="ClaudeSessionStart",
                summary=f"Claude session started: {external_session_id}",
                payload={"claude_session_id": external_session_id},
            )
        except Exception:
            pass
    except Exception as e:
        print(f"Warning: Could not start session: {e}", file=sys.stderr)

    # Get features and stats
    features, stats = get_feature_summary(graph_dir)

    if not features:
        context = f"""{version_warning}{HTMLGRAPH_PROCESS_NOTICE}

---

## No Features Found

Initialize HtmlGraph in this project:
```bash
uv pip install htmlgraph
htmlgraph init
```

Or create features manually in `.htmlgraph/features/`
"""
        output_response(context, "No features found. Run 'htmlgraph init' to set up.")
        return

    # Find active feature(s)
    active_features = [f for f in features if f.get("status") == "in-progress"]
    pending_features = [f for f in features if f.get("status") == "todo"]

    # Build context (prepend version warning if outdated)
    context_parts = []
    if version_warning:
        context_parts.append(version_warning.strip())
    context_parts.append(HTMLGRAPH_PROCESS_NOTICE)

    # Previous session summary
    prev_session = get_session_summary(graph_dir)
    if prev_session:
        context_parts.append(f"""## Previous Session

**Session:** {prev_session.get('id', 'unknown')}
**Events:** {prev_session.get('event_count', 0)}
**Worked On:** {', '.join(prev_session.get('worked_on', [])) or 'N/A'}
""")

    # Current status
    context_parts.append(f"""## Project Status

**Progress:** {stats['done']}/{stats['total']} features complete ({stats['percentage']}%)
**Active:** {stats['in_progress']} | **Blocked:** {stats['blocked']} | **Todo:** {stats['todo']}
""")

    if active_features:
        active_list = "\n".join([f"- **{f['id']}**: {f['title']}" for f in active_features[:3]])
        context_parts.append(f"""## Active Features

{active_list}

*Activity will be attributed to these features based on file patterns and keywords.*
""")
    else:
        context_parts.append("""## No Active Features

Start working on a feature:
```bash
htmlgraph feature start <feature-id>
```
""")

    if pending_features:
        pending_list = "\n".join([f"- {f['id']}: {f['title'][:50]}" for f in pending_features[:5]])
        context_parts.append(f"""## Pending Features

{pending_list}
""")

    context_parts.append("""## Session Continuity & Checklist

**CRITICAL - DO THIS FIRST:**
1. **IMMEDIATELY activate the `htmlgraph-tracker` skill** using the Skill tool (required for every session start and after every compact)
2. **Follow the Session Workflow Checklist** (see skill for quick reference, `docs/WORKFLOW.md` for full version)
3. Then greet the user with a brief status update:
   - Previous session summary (if any)
   - Current feature progress
   - What remains to be done
   - Ask what they'd like to work on next

The htmlgraph-tracker skill contains the Session Workflow Checklist to ensure:
- Proper feature creation decisions (use decision framework)
- Correct attribution throughout work
- Quality checks before completion
- Proper testing and validation
""")

    context = "\n\n---\n\n".join(context_parts)

    # Terminal status
    if active_features:
        status_summary = f"Feature: {active_features[0]['title'][:40]} | Progress: {stats['done']}/{stats['total']} ({stats['percentage']}%)"
    else:
        status_summary = f"No active feature | Progress: {stats['done']}/{stats['total']} ({stats['percentage']}%) | {len(pending_features)} pending"

    output_response(context, status_summary)


if __name__ == "__main__":
    main()
