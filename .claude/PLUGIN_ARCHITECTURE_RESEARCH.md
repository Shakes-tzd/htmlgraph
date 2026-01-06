# Plugin Architecture Research - System Prompt Persistence Design

**Research Date:** 2026-01-05
**Focus:** Claude Code plugin hooks, SDK integration patterns, and system prompt persistence design
**Status:** COMPLETE - Ready for implementation

---

## Executive Summary

HtmlGraph demonstrates a sophisticated plugin architecture where:

1. **Plugin hooks (SessionStart/PostToolUse/PreToolUse) inject context into Claude Code**
2. **Context is injected via `additionalContext` field in hook output**
3. **System prompts are delivered through SessionStart hook output** (not static files)
4. **SDK operations enable hooks to read/write project-local state dynamically**
5. **Plugin capability discovery happens at hook execution time** (not pre-configured)

This enables **dynamic system prompt persistence** where:
- Hook receives Claude session context (session_id, transcript, cwd, permission_mode)
- Hook executes Python SDK code to query project state (features, sessions, analytics)
- Hook generates context strings dynamically and returns via `additionalContext`
- System prompt behavior adapts to project state without static configuration

---

## Part 1: Claude Code Plugin Architecture

### 1.1 Hook System Fundamentals

**Claude Code Hooks** are event-driven points where plugins intercept Claude's execution:

| Hook | Trigger | Input | Output | Use Case |
|------|---------|-------|--------|----------|
| **SessionStart** | Session begins/resumes | session_id, transcript_path, cwd, permission_mode, source | additionalContext (injected to Claude) | Load project context, initialize features |
| **PreToolUse** | Before tool execution | tool_name, tool_input, tool_use_id, session_id | permissionDecision, updatedInput | Validate/approve/modify tools before use |
| **PostToolUse** | After tool succeeds | tool_name, tool_input, tool_response, tool_use_id | additionalContext | React to tool results, provide feedback |
| **UserPromptSubmit** | User submits prompt | prompt, session_id, transcript_path | additionalContext, decision (block/allow) | Validate prompts, inject context |
| **Stop/SubagentStop** | Agent stops | session_id, stop_hook_active | decision (block/continue) | Decide if agent should continue |
| **SessionEnd** | Session ends | session_id, reason | (cleanup only) | Save session state |

**Key Insight:** `additionalContext` field is how plugins communicate with Claude. All strategic context (system prompts, directives, status) flows through this mechanism.

### 1.2 Hook Output Format

Hooks return JSON with **two communication mechanisms**:

**Method 1: Simple Exit Code**
```bash
exit 0  # Success - stdout shown in verbose mode, added to context for UserPromptSubmit/SessionStart
exit 2  # Blocking error - stderr shown to Claude
exit 1+ # Non-blocking error - logged only
```

**Method 2: Structured JSON Output (Recommended)**
```json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Context string injected to Claude's system prompt"
  },
  "suppressOutput": false,
  "systemMessage": "Optional warning shown to user"
}
```

**Critical:** For `SessionStart` hooks, `additionalContext` becomes part of Claude's immediate context - **not a system prompt file**, but direct conversation context injection.

### 1.3 Plugin Hook Configuration

Plugins define hooks in `.claude-plugin/hooks/hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-start.py",
            "timeout": 60
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/posttooluse-integrator.py"
          }
        ]
      }
    ]
  }
}
```

**Key Variables:**
- `${CLAUDE_PLUGIN_ROOT}` - Plugin installation directory (HtmlGraph: `/Users/.../.claude/plugins/htmlgraph/`)
- `${CLAUDE_PROJECT_DIR}` - Project root directory (where Claude Code was invoked)
- All standard environment variables available

**Hook Merging:** Multiple hooks can respond to the same event. Hooks from:
1. User settings (`.claude/settings.json`)
2. Project settings (`.claude/settings.json`)
3. Local overrides (`.claude/settings.local.json`)
4. Plugin hooks (auto-merged)

All hooks for an event run **in parallel** with automatic deduplication.

---

## Part 2: HtmlGraph Plugin Implementation Patterns

### 2.1 SessionStart Hook - The Primary Context Injection Point

**Location:** `packages/claude-plugin/hooks/scripts/session-start.py`

**Architecture:**

```
SessionStart Hook Flow:
│
├─ Input: Hook JSON (session_id, cwd, transcript_path, source)
│
├─ Step 1: Check SDK availability (htmlgraph Python package)
│  └─ If missing: Fallback to basic context
│
├─ Step 2: Discover project path (git root or cwd)
│
├─ Step 3: Initialize session
│  └─ SessionManager.start_session() or get_active_session()
│  └─ Link to current Claude session (breadcrumb tracking)
│
├─ Step 4: Load project state
│  ├─ Get all features (status, progress, active work)
│  ├─ Get sessions (previous session summary, handoff notes)
│  ├─ Get analytics (recommendations, bottlenecks, parallel work)
│  ├─ Get active agents (multi-agent awareness, conflict detection)
│  └─ Get recent commits (context on recent changes)
│
├─ Step 5: Generate context strings
│  ├─ Version warnings (if htmlgraph outdated)
│  ├─ HtmlGraph process notice (tracking enabled)
│  ├─ Orchestrator mode status (active, level, directives)
│  ├─ Orchestrator directives (delegation patterns)
│  ├─ Tracker workflow (session checklist)
│  ├─ Previous session summary (handoff, blockers)
│  ├─ Project status (progress, active features)
│  ├─ Strategic insights (bottlenecks, recommendations)
│  ├─ Active agents (multi-agent coordination)
│  └─ Session continuity instructions
│
└─ Output: JSON with additionalContext field
   └─ Injected into Claude's conversation context
```

**Key Implementation Detail:**
```python
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
                    "additionalContext": context,  # THIS is the system prompt
                },
            }
        )
    )
```

**The `additionalContext` field is NOT a static system prompt - it's dynamically generated from project state.**

### 2.2 Dynamic Context Generation Pattern

**Key Principle:** Context is built from multiple sources and concatenated:

```python
# In session-start.py main():

context_parts = []

# 1. Version warnings (optional)
if version_warning:
    context_parts.append(version_warning.strip())

# 2. Core process notices
context_parts.append(HTMLGRAPH_PROCESS_NOTICE)
context_parts.append(orchestrator_status)
context_parts.append(ORCHESTRATOR_DIRECTIVES)
context_parts.append(TRACKER_WORKFLOW)

# 3. Previous session context
prev_session = get_session_summary(graph_dir)
if prev_session:
    context_parts.append(f"""## Previous Session
...
""")

# 4. Current project status
context_parts.append(f"""## Project Status
Progress: {stats["done"]}/{stats["total"]} ({stats["percentage"]}%)
...
""")

# 5. Active features
if active_features:
    context_parts.append(f"""## Active Features
...
""")

# 6. Strategic insights
if recommendations or bottlenecks:
    context_parts.append(f"""## 🎯 Strategic Insights
...
""")

# 7. Multi-agent coordination
if other_agents:
    context_parts.append(f"""## 👥 Other Active Agents
...
""")

# 8. Conflict warnings
if conflicts:
    context_parts.append(f"""## ⚠️ CONFLICT DETECTED
...
""")

# 9. Session continuity
context_parts.append("""## Session Continuity
Greet the user with a brief status update...
""")

# Final assembly
context = "\n\n---\n\n".join(context_parts)
output_response(context, status_summary)
```

**Critical Pattern:** Fixed template strings + dynamic data = Final context.

### 2.3 Template Strings vs Dynamic Data

HtmlGraph uses a two-tier approach:

**Tier 1: Fixed Template Strings** (Process notices, directives, workflows)
```python
HTMLGRAPH_PROCESS_NOTICE = """## HTMLGRAPH DEVELOPMENT PROCESS ACTIVE
..."""

ORCHESTRATOR_DIRECTIVES = """## 🎯 ORCHESTRATOR DIRECTIVES (IMPERATIVE)
..."""

TRACKER_WORKFLOW = """## 📊 HTMLGRAPH TRACKING WORKFLOW
..."""
```

**Tier 2: Dynamic Data** (Query project state via SDK)
```python
# Get features
features, stats = get_feature_summary(graph_dir)

# Activate orchestrator mode
orchestrator_active, orchestrator_level = activate_orchestrator_mode(...)

# Get analytics
analytics = get_strategic_recommendations(graph_dir)

# Get active agents
active_agents = get_active_agents(graph_dir)

# Format into final context
context_parts.append(f"""## Project Status
Progress: {stats["done"]}/{stats["total"]} ({stats["percentage"]}%)
...""")
```

**Design Principle:** Templates are stable (committed to repo), data is dynamic (queried at hook time).

### 2.4 SDK Integration in Hooks

Hooks execute Python code that uses the HtmlGraph SDK:

```python
from htmlgraph import SDK, generate_id
from htmlgraph.converter import node_to_dict
from htmlgraph.graph import HtmlGraph
from htmlgraph.orchestrator_mode import OrchestratorModeManager
from htmlgraph.session_manager import SessionManager

def get_features(graph_dir: Path) -> list[dict]:
    """Get all features as dicts."""
    features_dir = graph_dir / "features"
    if not features_dir.exists():
        return []
    graph = HtmlGraph(features_dir, auto_load=True)
    return [node_to_dict(node) for node in graph.nodes.values()]

def activate_orchestrator_mode(graph_dir: Path, features: list[dict], session_id: str):
    """Activate orchestrator mode unconditionally."""
    try:
        manager = OrchestratorModeManager(graph_dir)
        mode = manager.load()

        if mode.disabled_by_user:
            return False, "disabled"

        if not mode.enabled:
            manager.enable(session_id=session_id, level="strict", auto=True)
            return True, "strict"

        return True, mode.enforcement_level
    except Exception as e:
        return False, "error"
```

**Pattern:** Hooks are Python scripts that import SDK classes directly and query `.htmlgraph/` state.

### 2.5 Environment Variables in Hooks

**SessionStart Hook Receives:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../session.jsonl",
  "cwd": "/Users/project/root",
  "permission_mode": "default",
  "hook_event_name": "SessionStart",
  "source": "startup" | "resume" | "clear" | "compact"
}
```

**Available for Hook Use:**
- `${CLAUDE_PROJECT_DIR}` - Project root (for absolute paths)
- `${CLAUDE_ENV_FILE}` - File to persist environment variables (SessionStart only)
- Standard bash environment variables

**Critical for System Prompt Persistence:**
- `cwd` tells us the project directory
- We can use `git rev-parse --show-toplevel` to find git root
- We can locate `.htmlgraph/` relative to project root
- We can read project-local state (`.htmlgraph/features/`, `.htmlgraph/sessions/`, etc.)

---

## Part 3: System Prompt Persistence Design

### 3.1 Current HtmlGraph Approach (Reference Model)

**What HtmlGraph Does:**

1. **Hook receives Claude session context** (via hook input JSON)
2. **Hook queries project state** (SDK operations on `.htmlgraph/` files)
3. **Hook generates context dynamically** (template strings + dynamic data)
4. **Hook returns context via `additionalContext`** (injected to Claude)
5. **Context persists across tool calls** (attached to conversation)
6. **SessionEnd hook saves completion data** (session summary, handoff notes)

**Persistence Mechanism:**
- NOT: Static system prompt files
- NOT: Hook environment variables
- YES: Injected conversation context (survives tool calls within session)
- YES: Project-local `.htmlgraph/` files (survives across sessions via SDK)

### 3.2 System Prompt Persistence Patterns

**Pattern 1: Within-Session Persistence**
```
SessionStart Hook
  └─ Injects additionalContext (system prompt)

User Issues Prompt
  └─ Claude has system prompt + user prompt in context

Claude Executes Tools (Read, Edit, Bash, etc.)
  └─ System prompt stays in conversation

Claude Responds
  └─ Has system prompt throughout session
```

**Pattern 2: Cross-Session Persistence**
```
Session 1 SessionStart
  └─ Queries .htmlgraph/ state
  └─ Generates context based on current progress
  └─ Injects context

  Work happens...

Session 1 SessionEnd
  └─ Saves session summary, handoff notes, blockers
  └─ Writes to .htmlgraph/sessions/ (HTML files)
  └─ Writes to .htmlgraph/events/ (JSONL files)

Session 2 SessionStart
  └─ Queries .htmlgraph/sessions/
  └─ Reads previous session summary
  └─ Generates context with: "Previous Session: [summary]"
  └─ Injects into new session

  Work resumes...
```

**Pattern 3: Hook-Based Context Updates**
```
UserPromptSubmit Hook (Optional)
  └─ Can inject additional context based on prompt content
  └─ Example: "You mentioned 'auth' - here's recent auth work"

PostToolUse Hook (Optional)
  └─ Can inject context based on tool result
  └─ Example: "Test failed - here's why"
  └─ Uses additionalContext or decision field

Stop Hook (Optional)
  └─ Can block stop and provide context to continue
  └─ Example: "You still have pending steps"
```

### 3.3 Design Decisions for Plugin System Prompt

**Decision 1: Where Should System Prompt Live?**

Option A: Static file in `.claude/`
- Pro: Visible, easy to edit
- Con: Never updated, ignores project state

Option B: Hook output (additionalContext) - CHOSEN
- Pro: Dynamic, reflects current state, adapts to project
- Con: Requires hook execution at session start
- Used by: HtmlGraph (proven pattern)

Option C: Hybrid - Static base + Hook additions
- Pro: Combines visibility + dynamism
- Con: Complexity, two sources of truth
- Possible improvement for future

**Decision 2: How Should Hook Access Project State?**

Option A: Read files directly
- Pro: Simple
- Con: Reinvents SDK functionality

Option B: Use SDK (Python SDK) - CHOSEN
- Pro: Leverages existing abstractions
- Con: Requires htmlgraph package installed
- Used by: HtmlGraph (proven pattern)

Option C: Use CLI commands
- Pro: Works without SDK import
- Con: Slower (subprocess overhead)
- Fallback option if SDK unavailable

**Decision 3: What Context Should Be Injected?**

Required (Every Session):
- Process notice (tracking enabled)
- System prompt template/directives
- Current project status (progress, active work)

Optional (If Available):
- Previous session summary
- Active agents (multi-agent context)
- Conflict warnings
- Strategic recommendations

---

## Part 4: Plugin-to-SDK Feature Exposure

### 4.1 How Plugin Features Reach Users

**Two User Groups:**

**Group A: Claude Code Plugin Users** (Most users)
- Install: `claude plugin install htmlgraph@htmlgraph`
- Get: Plugin hooks, skills, commands, templates
- No SDK knowledge required
- Works in Claude Code interface (web/desktop)

**Group B: Python SDK Users** (Developers)
- Install: `uv pip install htmlgraph`
- Get: Python SDK for automation
- Use in scripts, tools, CI/CD pipelines
- Works anywhere Python runs

### 4.2 Plugin Architecture (What Users See)

Plugin structure in `packages/claude-plugin/`:

```
claude-plugin/
├── .claude-plugin/
│   ├── plugin.json              # Plugin metadata
│   └── marketplace.json         # Plugin distribution
├── hooks/
│   ├── hooks.json               # Hook configurations
│   └── scripts/                 # Hook Python scripts
├── commands/                    # Slash commands (/feature, /spike, etc.)
├── agents/                      # Subagents (researcher, test-runner, etc.)
├── skills/                      # Reusable skill extensions
└── rules/                       # Context rules (orchestration.md)
```

**Key Insight:** Plugin is distribution mechanism for:
- Hook scripts (which use SDK internally)
- Commands (which use SDK to create work items)
- Agents (which use SDK to query/update state)
- Skills (which teach orchestration patterns)

### 4.3 Hook Scripts Use SDK Internally

**Pattern: Hooks are SDK client scripts**

Example from `session-start.py`:
```python
try:
    from htmlgraph import SDK, generate_id
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.session_manager import SessionManager
except Exception as e:
    print(f"Warning: HtmlGraph not available ({e})")
    print(json.dumps({}))
    sys.exit(0)

def get_features(graph_dir: Path) -> list[dict]:
    features_dir = graph_dir / "features"
    if not features_dir.exists():
        return []
    graph = HtmlGraph(features_dir, auto_load=True)
    return [node_to_dict(node) for node in graph.nodes.values()]

def activate_orchestrator_mode(graph_dir: Path, features: list[dict], session_id: str):
    manager = OrchestratorModeManager(graph_dir)
    mode = manager.load()
    # ... use SDK manager to query/update state
```

**Design Pattern:**
```
Plugin Hook Script
  └─ Imports htmlgraph SDK
  └─ Queries .htmlgraph/ state
  └─ Runs business logic
  └─ Returns hook output (JSON)
```

### 4.4 Commands Use SDK (Slash Commands)

Commands in `packages/claude-plugin/commands/` call SDK operations.

Example: `/feature` command creates features via SDK
```python
from htmlgraph import SDK

sdk = SDK(agent="claude-code")
feature = sdk.features.create("Title") \
    .set_priority("high") \
    .add_steps([...]) \
    .save()
```

### 4.5 SDK Capabilities Exposed to Plugin Users

When user installs plugin, they implicitly get access to SDK capabilities via commands/hooks:

| Capability | Plugin Access | SDK Access | Method |
|-----------|---|---|---|
| Create features | `/feature add` command | `sdk.features.create()` | Both |
| Track spikes | `/spike` command | `sdk.spikes.create()` | Both |
| Query status | `/status` command | `sdk.features.where()` | Both |
| Analytics | Dashboard + recommendations | `sdk.recommend_next_work()` | Both |
| Session tracking | Automatic (hooks) | `SessionManager` | Hook-based |
| Orchestration | Directives injected | `OrchestratorModeManager` | Hook-based |

**Key Insight:** Plugin users don't write SDK code - they get SDK benefits through commands/hooks that use SDK internally.

---

## Part 5: Critical Findings for System Prompt Persistence

### 5.1 Hook Input/Output Contract

**What Hooks Receive (SessionStart Input JSON):**
```json
{
  "session_id": "user-session-identifier",
  "transcript_path": "/path/to/conversation.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "default|plan|acceptEdits|dontAsk|bypassPermissions",
  "hook_event_name": "SessionStart",
  "source": "startup|resume|clear|compact"
}
```

**What Hook Must Return (SessionStart Output JSON):**
```json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "String injected to Claude's conversation context"
  }
}
```

**Critical:** `additionalContext` is NOT written to a file - it's injected into Claude's immediate conversation context. This is how system prompts are delivered.

### 5.2 SessionStart Hook Execution Timing

- Triggered: Every time Claude Code session starts (fresh or resumed)
- Timeout: 60 seconds default (configurable per hook)
- Execution: Synchronous - waits for hook completion before showing Claude context
- Failures: Non-blocking (hook failure = no context injected, session continues)

**Design Implication:** SystemPrompt must be generated within 60 seconds. Must be fast enough for user-facing experience.

### 5.3 Persistence Across Tool Calls

**Within a Session:**
- System prompt injected at SessionStart
- Remains in conversation throughout all tool calls
- Not re-injected for each tool use
- Post-ToolUse hook can ADD additional context via `additionalContext`

**Pattern: SessionStart + PostToolUse**
```
SessionStart (system prompt injection)
  └─ additionalContext: "Orchestrator directives..."

Claude processes prompt + system prompt
  └─ Issues tool call (Read, Edit, Bash)

PostToolUse Hook (optional feedback)
  └─ additionalContext: "Tool succeeded, here's what changed"

Claude sees original system prompt + tool feedback
  └─ Makes decision with both contexts
```

### 5.4 Multi-Session Persistence

HtmlGraph pattern for cross-session persistence:

**Session 1 Ends:**
```python
# session-end.py hook saves:
session.handoff_notes = "Completed auth implementation"
session.recommended_next = "Write integration tests"
session.blockers = ["Missing database schema"]
session.save()
```

**Session 2 Starts:**
```python
# session-start.py hook reads:
prev_session = get_session_summary(graph_dir)
context = f"""## Previous Session
Notes: {prev_session['handoff_notes']}
Recommended: {prev_session['recommended_next']}
Blockers: {prev_session['blockers']}
"""
```

**Design Pattern:** Session end writes `.htmlgraph/sessions/` files, session start reads them.

### 5.5 Plugin Hook Merging Behavior

**Critical:** Multiple hooks for same event ALL EXECUTE (no override):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "plugin-hook.py" },
          { "type": "command", "command": "user-hook.py" },
          { "type": "command", "command": "project-hook.py" }
        ]
      }
    ]
  }
}
```

**Execution:** All three hooks run in parallel. JSON outputs are MERGED:
```python
# If all hooks return additionalContext:
# Final context = hook1.context + hook2.context + hook3.context
```

**Design Implication:** Multiple plugins can contribute context. System prompt context gets merged, not replaced.

---

## Part 6: Recommendations for System Prompt Persistence Implementation

### 6.1 Recommended Architecture

```
Plugin Hook (SessionStart)
  │
  ├─ Receive: Hook input JSON (session_id, cwd, transcript, source)
  │
  ├─ Step 1: Discover project capabilities
  │  ├─ Check if htmlgraph SDK available
  │  ├─ Check if .htmlgraph/ exists
  │  └─ Fallback if neither available
  │
  ├─ Step 2: Load project-local system prompt config
  │  ├─ Read: .claude/system-prompt-config.json (or similar)
  │  ├─ Contains: Prompt templates, enabled features, customizations
  │  └─ Merge: Plugin defaults + user overrides
  │
  ├─ Step 3: Generate dynamic context
  │  ├─ Query: Project state via SDK (if available)
  │  ├─ Load: Previous session context (if available)
  │  ├─ Build: Final system prompt from templates + dynamic data
  │  └─ Handle: Graceful degradation if SDK unavailable
  │
  ├─ Step 4: Inject context
  │  └─ Return: JSON with additionalContext field
  │
  └─ Step 5: Document for users
     └─ Include: Comments in generated context about customization
```

### 6.2 Graceful Degradation Strategy

**Level 1: SDK Available + .htmlgraph/ Exists** (Full features)
- Load features, sessions, analytics
- Generate rich project-aware context
- Adapt system prompt to current work

**Level 2: SDK Available, No .htmlgraph/** (Minimal features)
- Skip project state queries
- Use static system prompt only
- Still benefit from orchestration directives

**Level 3: SDK Unavailable** (Fallback)
- Skip all SDK imports
- Use static system prompt only
- Still functional with basic features

**Level 4: .claude/ Missing** (Edge case)
- Exit gracefully
- Log warning (not to Claude)
- Session continues without system prompt

### 6.3 Configuration Pattern

**Recommended:** `.claude/system-prompt-config.json`

```json
{
  "version": "1.0",
  "enabled": true,
  "persistence": {
    "inject_at_session_start": true,
    "update_on_tool_use": false,
    "cross_session_memory": true
  },
  "templates": {
    "process_notice": true,
    "orchestrator_directives": true,
    "project_status": true,
    "active_features": true,
    "strategic_insights": true
  },
  "customizations": {
    "model_preferences": "gemini-codex-copilot",
    "enforcement_level": "strict",
    "enable_learning_insights": true
  }
}
```

**Hook reads this:** Determines which context sections to generate/include.

### 6.4 Implementation Checklist

For system prompt persistence in plugin context:

**Pre-Implementation:**
- [ ] Document hook input/output contract
- [ ] Design configuration file schema
- [ ] Plan graceful degradation strategy
- [ ] Identify performance requirements (must complete in <60s)

**Implementation:**
- [ ] Create SessionStart hook script
- [ ] Implement configuration loading
- [ ] Build context generation logic
- [ ] Add SDK integration with error handling
- [ ] Create default configuration file

**Testing:**
- [ ] Test with SDK available
- [ ] Test without SDK (fallback)
- [ ] Test with missing .htmlgraph/
- [ ] Test hook timeout behavior
- [ ] Test multi-hook merging
- [ ] Test cross-session persistence

**Documentation:**
- [ ] Document hook capabilities
- [ ] Document configuration options
- [ ] Document customization examples
- [ ] Document troubleshooting guide

---

## Part 7: Key Insights & Design Patterns

### 7.1 Plugin Hooks are Not System Prompts

**Common Misconception:** "Hooks inject system prompts"

**Reality:** "Hooks inject conversation context"

- System prompts are static (baked into Claude's weights)
- Hooks inject context into CONVERSATION
- Context persists throughout session (not per-tool)
- Context is composable (multiple hooks contribute)

**Implication:** System prompt "persistence" actually means "context persistence in conversation."

### 7.2 The Hook-SDK Partnership

**Hooks cannot act alone.** The complete pattern is:

1. **Hook** (Plugin infrastructure) - Executes at events, can execute code
2. **SDK** (Python library) - Provides abstractions for .htmlgraph/ operations
3. **Together** - Hook + SDK = Dynamic project-aware context

Without SDK, hooks can only read static files.
Without hooks, SDK features aren't integrated into Claude's workflow.

### 7.3 Plugin Capability Discovery

Plugins DON'T pre-declare all capabilities. Instead:

**Runtime Discovery:**
```python
# At hook time:
1. Check if SDK importable
2. Check if .htmlgraph/ exists
3. Check what features are present
4. Adapt behavior accordingly

# Result: Plugins work even if project partially set up
```

**Design Principle:** Graceful degradation > hard requirements.

### 7.4 Cross-Session Memory Pattern

HtmlGraph's cross-session approach:

```
Session 1 → Save state → Session 2 reads state
   ↓          ↓            ↓
 Code      .htmlgraph/  SD K
 runs       files     queries
```

**Key:** State is stored in project-local files (`.htmlgraph/`), not in plugin config or Claude state.

### 7.5 Context Injection Points (Ordered by Coverage)

1. **SessionStart** (Most comprehensive) - Full project context at session beginning
2. **UserPromptSubmit** (Optional) - Context based on what user asked
3. **PostToolUse** (Optional) - Context based on tool results
4. **PreToolUse** (Optional) - Context before tool execution

**Design Implication:** Most important context should go in SessionStart (executes first, covers entire session).

---

## Part 8: Reference Implementation (HtmlGraph as Example)

### 8.1 File Organization

```
HtmlGraph Plugin:
├── hooks/
│   ├── hooks.json (hook configuration)
│   └── scripts/
│       ├── session-start.py        (Primary system prompt injection)
│       ├── session-end.py           (Save session context)
│       ├── posttooluse-integrator.py (Optional feedback)
│       ├── pretooluse-integrator.py  (Optional validation)
│       └── user-prompt-submit.py    (Optional context injection)
├── .claude-plugin/
│   └── plugin.json (plugin metadata)
└── commands/ (slash commands using SDK)
```

### 8.2 Key Python Patterns

**Pattern 1: SDK Import with Fallback**
```python
try:
    from htmlgraph import SDK
except ImportError:
    SDK = None

def use_sdk():
    if SDK:
        # Full functionality
    else:
        # Fallback behavior
```

**Pattern 2: Project Discovery**
```python
def resolve_project_path(cwd: str | None = None) -> str:
    """Find git root or use cwd."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else cwd
```

**Pattern 3: Dynamic Context Building**
```python
context_parts = []
context_parts.append(STATIC_TEMPLATE_1)
context_parts.append(STATIC_TEMPLATE_2)
context_parts.append(dynamic_data_1)
context_parts.append(dynamic_data_2)
context = "\n\n---\n\n".join(context_parts)
```

**Pattern 4: Hook Output JSON**
```python
output = {
    "continue": True,
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context
    }
}
print(json.dumps(output))
```

---

## Part 9: Open Questions & Future Directions

### 9.1 Outstanding Questions

1. **How should system prompt configuration be versioned?**
   - Should `.claude/system-prompt-config.json` be committed to git?
   - Or should it be local-only (`.gitignore`)?
   - Current HtmlGraph pattern: Committed (shared across team)

2. **Can system prompt be updated mid-session?**
   - PostToolUse hook can inject additional context
   - Can we update existing context? (Not directly)
   - Workaround: Acknowledge new context in PostToolUse output

3. **How to handle conflicting plugin contributions?**
   - Multiple plugins might try to inject conflicting directives
   - Current behavior: All execute in parallel (merge)
   - Need documented merge strategy

4. **Should system prompt be model-specific?**
   - Claude Opus vs Haiku might need different directives
   - Hook receives `hook_event_name` but not model info
   - Would need additional context injection point

### 9.2 Potential Future Extensions

1. **UserPromptSubmit Hook Enhancement**
   - Currently can only add context or block
   - Could allow Claude to request updated system prompt
   - Pattern: UserPromptSubmit → SessionStart-like context

2. **PostToolUse Context Updates**
   - Hook can inject `additionalContext`
   - Could be used for adaptive system prompts
   - Example: "Test failed, here's recovery guidance"

3. **Prompt-Based Hooks for System Prompt**
   - Currently hooks can execute code or scripts
   - Could add LLM-powered decision making
   - Example: "Should we update orchestrator mode level?"

4. **System Prompt Versioning**
   - Track history of injected system prompts
   - Enable rollback if configuration causes issues
   - Store in `.htmlgraph/prompts/` history

---

## Conclusion

### Key Takeaways

1. **System prompts in plugins are NOT static files - they are dynamically generated conversation context injected via SessionStart hooks.**

2. **The plugin-SDK partnership enables hooks to query project state at runtime and generate context-aware system prompts.**

3. **HtmlGraph demonstrates a proven pattern:**
   - SessionStart hook injects context
   - SessionEnd hook saves state
   - SessionStart (next session) reads state
   - System prompt adapts to project evolution

4. **Graceful degradation is essential:** Plugins must work even when:
   - SDK unavailable
   - .htmlgraph/ missing
   - Configuration incomplete

5. **Context composition is powerful:** Multiple hooks contribute context, final system prompt is assembled from multiple sources.

### Next Steps

This research enables implementation of:
- Dynamic system prompt persistence in plugin context
- Cross-session memory for system prompts
- Adaptive system prompts based on project state
- Configuration-driven prompt customization
- Multi-plugin context composition

The HtmlGraph plugin serves as a reference implementation for all these patterns.

---

**Research Complete:** January 5, 2026
**Researcher:** Plugin Architecture Analysis Agent
**Status:** Ready for Implementation Phase
