#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
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

if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({}))
    sys.exit(0)


def check_htmlgraph_version() -> tuple[str | None, str | None, bool]:
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
            [
                "uv",
                "run",
                "python",
                "-c",
                "import htmlgraph; print(htmlgraph.__version__)",
            ],
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
            headers={
                "Accept": "application/json",
                "User-Agent": "htmlgraph-version-check",
            },
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


def install_git_hooks(project_dir: str) -> bool:
    """
    Install pre-commit hooks if not already installed.

    Returns True if hooks were installed or already exist.
    """
    hooks_source = Path(project_dir) / "scripts" / "hooks" / "pre-commit"
    hooks_target = Path(project_dir) / ".git" / "hooks" / "pre-commit"

    # Skip if not a git repo or hooks source doesn't exist
    if not (Path(project_dir) / ".git").exists():
        return False
    if not hooks_source.exists():
        return False

    # Skip if hook already installed and up to date
    if hooks_target.exists():
        try:
            if hooks_source.read_text() == hooks_target.read_text():
                return True  # Already installed and current
        except Exception:
            pass

    # Install the hook
    try:
        import shutil

        shutil.copy2(hooks_source, hooks_target)
        hooks_target.chmod(0o755)
        return True
    except Exception:
        return False


try:
    from htmlgraph import SDK, generate_id
    from htmlgraph.converter import node_to_dict  # type: ignore[import]
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.orchestrator_mode import OrchestratorModeManager
    from htmlgraph.reflection import get_reflection_context
    from htmlgraph.session_manager import SessionManager
except Exception as e:
    print(
        f"Warning: HtmlGraph not available ({e}). Install with: uv pip install htmlgraph",
        file=sys.stderr,
    )
    print(json.dumps({}))
    sys.exit(0)


def activate_orchestrator_mode(
    graph_dir: Path, features: list[dict], session_id: str
) -> tuple[bool, str]:
    """
    Activate orchestrator mode unconditionally.

    Plugin installed = Orchestrator mode enabled.
    This is the default operating mode for all htmlgraph projects.

    Args:
        graph_dir: Path to .htmlgraph directory
        features: List of features (unused, kept for compatibility)
        session_id: Current session ID

    Returns:
        (is_active, enforcement_level)
    """
    try:
        manager = OrchestratorModeManager(graph_dir)

        # Get current mode
        mode = manager.load()

        # Decision: Always enable orchestrator mode unless user explicitly disabled
        if mode.disabled_by_user:
            # User explicitly disabled - respect their choice
            return False, "disabled"

        # Enable if not already enabled
        if not mode.enabled:
            manager.enable(session_id=session_id, level="strict", auto=True)
            return True, "strict"

        # Already enabled - return current state
        return True, mode.enforcement_level

    except Exception as e:
        print(f"Warning: Could not manage orchestrator mode: {e}", file=sys.stderr)
        return False, "error"


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
    from htmlgraph.converter import (  # type: ignore[import]
        SessionConverter,
        session_to_dict,
    )

    converter = SessionConverter(sessions_dir)
    sessions = converter.load_all()
    return [session_to_dict(s) for s in sessions]


def get_head_commit(project_dir: str) -> str | None:
    """Get current HEAD commit hash (short form)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


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

TRACKER_WORKFLOW = """## 📊 HTMLGRAPH TRACKING WORKFLOW

**CRITICAL: Follow this checklist for EVERY session.**

### Session Start (DO THESE FIRST)
1. ✅ Check active features: `uv run htmlgraph status`
2. ✅ Review session context and decide what to work on
3. ✅ **DECIDE:** Create feature or implement directly?
   - Create FEATURE if ANY apply: >30min, 3+ files, needs tests, multi-component, hard to revert
   - Implement DIRECTLY if ALL apply: single file, <30min, trivial, easy to revert

### During Work (DO CONTINUOUSLY)
1. ✅ **Feature MUST be in-progress before writing code**
   - Start feature: `sdk.features.start("feature-id")` or `uv run htmlgraph feature start <id>`
2. ✅ **CRITICAL:** Mark each step complete IMMEDIATELY after finishing it:
   ```python
   from htmlgraph import SDK
   sdk = SDK(agent="claude")
   with sdk.features.edit("feature-id") as f:
       f.steps[0].completed = True  # First step done
       f.steps[1].completed = True  # Second step done
   ```
3. ✅ Document decisions as you make them
4. ✅ Test incrementally - don't wait until the end

### Session End (MUST DO BEFORE COMPLETING FEATURE)
1. ✅ **RUN TESTS:** All tests MUST pass
2. ✅ **VERIFY STEPS:** ALL feature steps marked complete
3. ✅ **CLEAN CODE:** Remove debug code, console.logs, TODOs
4. ✅ **COMMIT WORK:** Git commit IMMEDIATELY (include feature ID in message)
5. ✅ **COMPLETE FEATURE:** `sdk.features.complete("feature-id")` or `uv run htmlgraph feature complete <id>`

### SDK Usage (ALWAYS USE SDK, NEVER DIRECT FILE EDITS)
❌ **FORBIDDEN:** `Write('/path/.htmlgraph/features/...', ...)` `Edit('/path/.htmlgraph/...')`
✅ **REQUIRED:** Use SDK for ALL operations on `.htmlgraph/` files

```python
from htmlgraph import SDK
sdk = SDK(agent="claude")

# Create and work on features
feature = sdk.features.create("Title").set_priority("high").add_steps(["Step 1", "Step 2"]).save()
with sdk.features.edit("feature-id") as f:
    f.status = "done"

# Query and batch operations
high_priority = sdk.features.where(status="todo", priority="high")
sdk.features.batch_update(["feat-1", "feat-2"], {"status": "done"})
```

**For complete SDK documentation → see `docs/AGENTS.md`**
"""

ORCHESTRATOR_DIRECTIVES = """## 🎯 ORCHESTRATOR DIRECTIVES (IMPERATIVE)

**YOU ARE THE ORCHESTRATOR.** Follow these directives:

### 1. ALWAYS DELEGATE - Even "Simple" Operations

**CRITICAL INSIGHT:** What looks like "one tool call" often becomes 2, 3, 4+ calls.

**ALWAYS delegate, even if you think it's simple:**
- ❌ "Just read one file" → ✅ Delegate to Explorer
- ❌ "Just edit one file" → ✅ Delegate to Coder
- ❌ "Just run tests" → ✅ Delegate to Tester
- ❌ "Just search for X" → ✅ Delegate to Explorer

**Why ALWAYS delegate:**
- Tool outputs are unknown until execution
- "One operation" often expands into many
- Each subagent has self-contained context
- Orchestrator only pays for: Task() call + Task output (not intermediate tool calls)
- Your context stays strategic, not filled with implementation details

**ONLY execute directly:**
- Task() - Delegation itself
- AskUserQuestion() - Clarifying with user
- TodoWrite() - Tracking work
- SDK operations - Creating features/work items

**Everything else → DELEGATE.**

### 2. YOUR ONLY JOB: Provide Clear Task Descriptions

**You don't execute, you describe what needs executing.**

**Good delegation:**
```python
Task(
    prompt="Find all files in src/auth/ that handle JWT validation.
            List the files and explain what each one does.",
    subagent_type="Explore"
)

Task(
    prompt="Fix the bug in src/auth/jwt.py where tokens expire immediately.
            The issue is in the validate_token() function.
            Run tests after fixing to verify the fix works.",
    subagent_type="general-purpose"
)
```

**Your job:**
- ✅ Describe the task clearly
- ✅ Provide context the subagent needs
- ✅ Specify what success looks like
- ✅ Give enough detail for self-contained execution

**Not your job:**
- ❌ Execute the task yourself
- ❌ Guess how many tool calls it will take
- ❌ Read files to "check if it's simple"

### 3. CREATE Work Items FIRST
**Before ANY implementation, create features:**
```python
from htmlgraph import SDK
sdk = SDK(agent="claude-code")
feature = sdk.features.create("Feature Title").save()
```

**Why:** Work items enable learning, pattern detection, and progress tracking.

### 4. PARALLELIZE Independent Tasks
**Spawn multiple `Task()` calls in a single message when tasks don't depend on each other.**

**Example:**
```python
# DO THIS (parallel):
Task("Implement auth API", subagent_type="general-purpose")
Task("Write auth tests", subagent_type="general-purpose")
Task("Update docs", subagent_type="general-purpose")

# NOT THIS (sequential):
Task("Implement auth API")  # wait...
# then later:
Task("Write auth tests")    # wait...
# then later:
Task("Update docs")         # wait...
```

**Why:** Parallel delegation is faster. You coordinate, subagents execute.

### 5. CONTEXT COST MODEL

**Understand what uses YOUR context:**
- ✅ Task() call (tiny - just the prompt)
- ✅ Task output (small - summary from subagent)
- ❌ Subagent's tool calls (NOT in your context!)
- ❌ Subagent's file reads (NOT in your context!)
- ❌ Subagent's intermediate results (NOT in your context!)

**Example:**
```
Your context cost for "Fix auth bug":
- Task("Fix auth bug in jwt.py...") → 100 tokens
- Task output: "Fixed. Tests pass." → 50 tokens
Total: 150 tokens

If you did it yourself:
- Read jwt.py → 5000 tokens
- Read tests → 3000 tokens
- Edit jwt.py → 200 tokens
- Run tests → 1000 tokens
Total: 9200 tokens (61x more expensive!)
```

**Your context is precious. Delegate everything.**

### 6. HTMLGRAPH DELEGATION PATTERN (CRITICAL)

**PROBLEM:** TaskOutput tool is unreliable - subagent results often can't be retrieved.

**SOLUTION:** Use HtmlGraph for subagent communication.

**How it works:**

**Step 1 - Orchestrator delegates with reporting instructions:**

Include this in every Task prompt:
  🔴 CRITICAL - Report Results to HtmlGraph:
  from htmlgraph import SDK
  sdk = SDK(agent='explorer')
  sdk.spikes.create('Task Results').set_findings('...').save()

**Step 2 - Wait for Task completion:**

Wait for the Task tool to show "Done". Ignore TaskOutput errors.

**Step 3 - Retrieve results from HtmlGraph:**

Use this command:
  uv run python -c "from htmlgraph import SDK; findings = SDK().spikes.get_latest(agent='explorer'); print(findings[0].findings if findings else 'No results')"

**IMPORTANT:**
- ✅ ALWAYS include the "Report Results to HtmlGraph" section in Task prompts
- ✅ ALWAYS retrieve results via SDK after Task completes
- ❌ NEVER rely on TaskOutput - it's broken
- ✅ Each subagent type should use a unique agent name (explorer, coder, tester)

**Template:**

Every Task() call must include the reporting pattern in the prompt.
After Task completes, retrieve results with SDK command above.

**Why this works:**
- HtmlGraph provides persistent, file-based communication
- No reliance on broken TaskOutput mechanism
- Full traceability - all delegation history in `.htmlgraph/spikes/`
- Orchestrator context stays clean - only reads final spike findings

---

**YOU ARE THE ARCHITECT. SUBAGENTS ARE BUILDERS. DELEGATE EVERYTHING.**
"""


def _build_orchestrator_status(active: bool, level: str) -> str:
    """
    Build orchestrator status section for context.

    Args:
        active: Whether orchestrator mode is active
        level: Enforcement level ('strict', 'guidance', 'disabled', 'error')

    Returns:
        Formatted status message
    """
    if not active or level == "disabled":
        return """## 🎯 ORCHESTRATOR MODE: INACTIVE

⚠️  Orchestrator mode has been manually disabled. This is unusual - the default mode is ORCHESTRATOR ENABLED.

**Note:** Without orchestrator mode, you will fill context with implementation details instead of delegating to subagents.

To re-enable: `uv run htmlgraph orchestrator enable`
"""

    if level == "error":
        return """## 🎯 ORCHESTRATOR MODE: ERROR

Warning: Could not determine orchestrator mode status. Proceeding without enforcement.
"""

    # Active mode
    enforcement_desc = (
        "blocks direct implementation"
        if level == "strict"
        else "provides guidance only"
    )

    return f"""## 🎯 ORCHESTRATOR MODE: ACTIVE ({level} enforcement)

**Default operating mode** - Plugin installed = Orchestrator enabled.

**Enforcement:** This mode {enforcement_desc}. Follow the delegation workflow in ORCHESTRATOR DIRECTIVES below.

**Why:** Orchestrator mode saves 80%+ context by delegating implementation to subagents instead of executing directly.

To disable: `uv run htmlgraph orchestrator disable`
To change level: `uv run htmlgraph orchestrator set-level guidance`
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
    stats["percentage"] = (
        int(stats["done"] * 100 / stats["total"]) if stats["total"] > 0 else 0
    )

    return features, stats


def get_session_summary(graph_dir: Path) -> dict | None:
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
        ended.sort(
            key=lambda s: parse_ts(s.get("ended_at") or s.get("last_activity")),
            reverse=True,
        )
        return ended[0]
    return None


def get_strategic_recommendations(graph_dir: Path, agent_count: int = 1) -> dict:
    """Get strategic recommendations using SDK analytics."""
    try:
        sdk = SDK(directory=graph_dir, agent="claude-code")

        # Get recommendations
        recs = sdk.recommend_next_work(agent_count=agent_count)

        # Get bottlenecks
        bottlenecks = sdk.find_bottlenecks(top_n=3)

        # Get parallel work capacity
        parallel = sdk.get_parallel_work(max_agents=5)

        return {
            "recommendations": recs[:3] if recs else [],
            "bottlenecks": bottlenecks,
            "parallel_capacity": parallel,
        }
    except Exception as e:
        print(f"Warning: Could not get strategic recommendations: {e}", file=sys.stderr)
        return {
            "recommendations": [],
            "bottlenecks": [],
            "parallel_capacity": {
                "max_parallelism": 0,
                "ready_now": 0,
                "total_ready": 0,
            },
        }


def get_active_agents(graph_dir: Path) -> list[dict]:
    """Get information about other active agents."""
    try:
        # Get all active sessions
        sessions_dir = graph_dir / "sessions"
        if not sessions_dir.exists():
            return []

        from htmlgraph.converter import SessionConverter  # type: ignore[import]

        converter = SessionConverter(sessions_dir)
        all_sessions = converter.load_all()

        active_agents = []
        for session in all_sessions:
            if session.status == "active":
                active_agents.append(
                    {
                        "agent": session.agent,
                        "session_id": session.id,
                        "started_at": session.started_at.isoformat()
                        if session.started_at
                        else None,
                        "event_count": session.event_count,
                        "worked_on": list(session.worked_on)
                        if hasattr(session, "worked_on")
                        else [],
                    }
                )

        return active_agents
    except Exception as e:
        print(f"Warning: Could not get active agents: {e}", file=sys.stderr)
        return []


def detect_feature_conflicts(
    features: list[dict], active_agents: list[dict]
) -> list[dict]:
    """Detect features being worked on by multiple agents simultaneously."""
    conflicts = []

    try:
        # Build map of feature -> agents
        feature_agents = {}

        for agent_info in active_agents:
            for feature_id in agent_info.get("worked_on", []):
                if feature_id not in feature_agents:
                    feature_agents[feature_id] = []
                feature_agents[feature_id].append(agent_info["agent"])

        # Find features with multiple agents
        for feature_id, agents in feature_agents.items():
            if len(agents) > 1:
                # Get feature details
                feature = next((f for f in features if f.get("id") == feature_id), None)
                if feature:
                    conflicts.append(
                        {
                            "feature_id": feature_id,
                            "title": feature.get("title", "Unknown"),
                            "agents": agents,
                        }
                    )
    except Exception as e:
        print(f"Warning: Could not detect conflicts: {e}", file=sys.stderr)

    return conflicts


def get_recent_commits(project_dir: str, count: int = 5) -> list[str]:
    """Get recent git commits."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{count}"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")
    except Exception:
        pass
    return []


def output_response(context: str, status_summary: str | None = None) -> None:
    """Output JSON response with context."""
    if status_summary:
        print(f"\n{status_summary}\n", file=sys.stderr)

    print(
        json.dumps(
            {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                },
            }
        )
    )


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
                installed=installed_ver, latest=latest_ver
            )
            print(
                f"⚠️  HtmlGraph update available: {installed_ver} → {latest_ver}",
                file=sys.stderr,
            )
    except Exception:
        pass  # Never block on version check failure

    external_session_id = hook_input.get("session_id") or os.environ.get(
        "CLAUDE_SESSION_ID", "unknown"
    )
    cwd = hook_input.get("cwd")
    project_dir = resolve_project_path(cwd if cwd else None)
    graph_dir = Path(project_dir) / ".htmlgraph"

    # Install pre-commit hooks if available (silent, non-blocking)
    try:
        install_git_hooks(project_dir)
    except Exception:
        pass  # Never block on hook installation

    # Ensure a single stable HtmlGraph session exists for this agent.
    # Do NOT create a new HtmlGraph session per external Claude session id (that can explode into many files).
    #
    # DESIGN DECISION: Task subagents share the parent's session.
    # - All work related to a conversation stays in one session file
    # - Agent attribution is tracked via data-agent attribute in activity logs
    # - This provides better continuity and easier debugging
    # - Alternative would be separate sessions per Task, but that fragments related work
    #
    # CONVERSATION-LEVEL AUTO-SPIKES:
    # - Each new conversation gets a new auto-spike
    # - Previous auto-spikes are closed when a new conversation starts
    # - Tracked via last_conversation_id in session metadata
    try:
        manager = SessionManager(graph_dir)
        # Get or create session for THIS specific agent (claude-code)
        active = manager.get_active_session_for_agent(agent="claude-code")
        if not active:
            active = manager.start_session(
                session_id=None,
                agent="claude-code",
                start_commit=get_head_commit(project_dir),
                title=f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )

        # Check if this is a new conversation
        last_conversation_id = getattr(active, "last_conversation_id", None)
        is_new_conversation = last_conversation_id != external_session_id

        # Record the external session id as a low-cost breadcrumb (for continuity debugging).
        try:
            manager.track_activity(
                session_id=active.id,
                tool="ClaudeSessionStart",
                summary=f"Claude session started: {external_session_id}",
                payload={
                    "claude_session_id": external_session_id,
                    "is_new_conversation": is_new_conversation,
                },
            )
        except Exception:
            pass

        # If new conversation, close open auto-spikes and create new one
        if is_new_conversation:
            try:
                # Close any open auto-spikes from previous conversation
                from htmlgraph.converter import NodeConverter  # type: ignore[import]

                spike_converter = NodeConverter(graph_dir / "spikes")
                all_spikes = spike_converter.load_all()

                for spike in all_spikes:
                    if (
                        spike.type == "spike"
                        and spike.auto_generated
                        and spike.spike_subtype
                        in ("session-init", "transition", "conversation-init")
                        and spike.status == "in-progress"
                    ):
                        spike.status = "done"
                        spike.updated = datetime.now()
                        spike_converter.save(spike)

                # Create new conversation-init spike
                spike_id = (
                    f"spk-{external_session_id[:8]}"
                    if external_session_id != "unknown"
                    else generate_id("spike", "conversation")
                )

                from htmlgraph.models import Node  # type: ignore[import]

                conversation_spike = Node(
                    id=spike_id,
                    title=f"Conversation {datetime.now().strftime('%H:%M')}",
                    type="spike",
                    status="in-progress",
                    priority="low",
                    spike_subtype="conversation-init",
                    auto_generated=True,
                    session_id=active.id,
                    model_name=active.agent,
                    content="Auto-generated spike for conversation startup.\n\nCaptures:\n- Context review\n- Planning\n- Exploration\n\nAuto-completes when feature is started or next conversation begins.",
                )
                spike_converter.save(conversation_spike)

                # Update session metadata
                active.last_conversation_id = external_session_id
                if conversation_spike.id not in active.worked_on:
                    active.worked_on.append(conversation_spike.id)
                manager.session_converter.save(active)

            except Exception as e:
                print(
                    f"Warning: Could not create conversation spike: {e}",
                    file=sys.stderr,
                )
    except Exception as e:
        print(f"Warning: Could not start session: {e}", file=sys.stderr)

    # Get features and stats
    features, stats = get_feature_summary(graph_dir)

    # Activate orchestrator mode (default operating mode for htmlgraph)
    orchestrator_active, orchestrator_level = activate_orchestrator_mode(
        graph_dir, features, external_session_id
    )

    if not features:
        context = f"""{version_warning}{HTMLGRAPH_PROCESS_NOTICE}

---

{ORCHESTRATOR_DIRECTIVES}

---

{TRACKER_WORKFLOW}

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

    # Get strategic recommendations (analytics)
    analytics = get_strategic_recommendations(graph_dir, agent_count=1)

    # Get active agents and detect conflicts
    active_agents = get_active_agents(graph_dir)
    conflicts = detect_feature_conflicts(features, active_agents)

    # Get recent commits
    recent_commits = get_recent_commits(project_dir, count=5)

    # Build orchestrator status section
    orchestrator_status = _build_orchestrator_status(
        orchestrator_active, orchestrator_level
    )

    # Build context (prepend version warning if outdated)
    context_parts = []
    if version_warning:
        context_parts.append(version_warning.strip())
    context_parts.append(HTMLGRAPH_PROCESS_NOTICE)
    context_parts.append(orchestrator_status)
    context_parts.append(ORCHESTRATOR_DIRECTIVES)
    context_parts.append(TRACKER_WORKFLOW)

    # Previous session summary (enhanced with more detail)
    prev_session = get_session_summary(graph_dir)
    if prev_session:
        handoff_lines = []
        if prev_session.get("handoff_notes"):
            handoff_lines.append(f"**Notes:** {prev_session.get('handoff_notes')}")
        if prev_session.get("recommended_next"):
            handoff_lines.append(
                f"**Recommended Next:** {prev_session.get('recommended_next')}"
            )
        blockers = prev_session.get("blockers") or []
        if blockers:
            handoff_lines.append(f"**Blockers:** {', '.join(blockers)}")

        handoff_text = ""
        if handoff_lines:
            handoff_text = "\n\n" + "\n".join(handoff_lines)

        # Format worked_on list
        worked_on = prev_session.get("worked_on", [])
        worked_on_text = ", ".join(worked_on[:3]) if worked_on else "N/A"
        if len(worked_on) > 3:
            worked_on_text += f" (+{len(worked_on) - 3} more)"

        context_parts.append(f"""## Previous Session

**Session:** {prev_session.get("id", "unknown")[:12]}...
**Events:** {prev_session.get("event_count", 0)}
**Worked On:** {worked_on_text}
{handoff_text}
""")

    # Current status
    context_parts.append(f"""## Project Status

**Progress:** {stats["done"]}/{stats["total"]} features complete ({stats["percentage"]}%)
**Active:** {stats["in_progress"]} | **Blocked:** {stats["blocked"]} | **Todo:** {stats["todo"]}
""")

    if active_features:
        active_list = "\n".join(
            [f"- **{f['id']}**: {f['title']}" for f in active_features[:3]]
        )
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
        pending_list = "\n".join(
            [f"- {f['id']}: {f['title'][:50]}" for f in pending_features[:5]]
        )
        context_parts.append(f"""## Pending Features

{pending_list}
""")

    # Add recent commits
    if recent_commits:
        commits_text = "\n".join([f"  {commit}" for commit in recent_commits])
        context_parts.append(f"""## Recent Commits

{commits_text}
""")

    # Add strategic insights
    recommendations = analytics.get("recommendations", [])
    bottlenecks = analytics.get("bottlenecks", [])
    parallel = analytics.get("parallel_capacity", {})

    if recommendations or bottlenecks or parallel.get("max_parallelism", 0) > 0:
        insights_parts = []

        # Bottlenecks
        if bottlenecks:
            bottleneck_count = len(bottlenecks)
            bottleneck_list = "\n".join(
                [
                    f"  - **{bn['title']}** (blocks {bn['blocks_count']} tasks, impact: {bn['impact_score']:.1f})"
                    for bn in bottlenecks[:3]
                ]
            )
            insights_parts.append(f"""#### Bottlenecks ({bottleneck_count})
{bottleneck_list}""")

        # Recommendations
        if recommendations:
            rec_list = "\n".join(
                [
                    f"  {i + 1}. **{rec['title']}** (score: {rec['score']:.1f})\n     - Why: {', '.join(rec['reasons'][:2])}"
                    for i, rec in enumerate(recommendations[:3])
                ]
            )
            insights_parts.append(f"""#### Top Recommendations
{rec_list}""")

        # Parallel capacity
        if parallel.get("max_parallelism", 0) > 0:
            ready_now = parallel.get("ready_now", 0)
            total_ready = parallel.get("total_ready", 0)
            insights_parts.append(f"""#### Parallel Work
**Can work on {parallel["max_parallelism"]} tasks simultaneously**
- {ready_now} tasks ready now
- {total_ready} total tasks ready""")

        if insights_parts:
            context_parts.append(f"""## 🎯 Strategic Insights

{chr(10).join(insights_parts)}
""")

    # Add active agents section (multi-agent awareness)
    other_agents = [a for a in active_agents if a["agent"] != "claude-code"]
    if other_agents:
        agents_list = "\n".join(
            [
                f"  - **{agent['agent']}**: {agent['event_count']} events, working on {', '.join(agent.get('worked_on', [])[:2]) or 'unknown'}"
                for agent in other_agents[:5]
            ]
        )
        context_parts.append(f"""## 👥 Other Active Agents

{agents_list}

**Note:** Coordinate with other agents to avoid conflicts.
""")

    # Add conflict warnings
    if conflicts:
        conflict_list = "\n".join(
            [
                f"  - **{conf['title']}** ({conf['feature_id']}): {', '.join(conf['agents'])}"
                for conf in conflicts
            ]
        )
        context_parts.append(f"""## ⚠️ CONFLICT DETECTED

**Multiple agents working on the same features:**

{conflict_list}

**Action required:** Coordinate with other agents or choose a different feature.
""")

    # Add computational reflections (pre-computed context from history)
    try:
        sdk = SDK(directory=graph_dir, agent="claude-code")
        current_feature_id = active_features[0]["id"] if active_features else None
        reflection_context = get_reflection_context(
            sdk,
            feature_id=current_feature_id,
            track=None,
        )
        if reflection_context:
            context_parts.append(reflection_context)
    except Exception as e:
        print(f"Warning: Could not compute reflections: {e}", file=sys.stderr)

    # Session continuity instructions (minimal - no forced skill activation)
    context_parts.append("""## Session Continuity

Greet the user with a brief status update:
- Previous session summary (if any)
- Current feature progress
- What remains to be done
- Ask what they'd like to work on next

**Note:** Orchestrator directives are loaded via system prompt. Skills activate on-demand when needed.
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
