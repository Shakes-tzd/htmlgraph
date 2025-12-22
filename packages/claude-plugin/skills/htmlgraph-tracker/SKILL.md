---
name: htmlgraph-tracker
description: HtmlGraph session tracking and documentation skill. Activated automatically at session start to ensure proper activity attribution, feature awareness, and documentation habits. Use when working with HtmlGraph-enabled projects, when drift warnings appear, or when the user asks about tracking features or sessions.
---

# HtmlGraph Tracker Skill

Use this skill when HtmlGraph is tracking the session to ensure proper activity attribution and documentation. This skill should be activated at session start via the SessionStart hook.

## When to Activate This Skill

- At the start of every session when HtmlGraph plugin is enabled
- When the user asks about tracking, features, or session management
- When drift detection warnings appear
- When the user mentions htmlgraph, features, sessions, or activity tracking
- When discussing work attribution or documentation

**Trigger keywords:** htmlgraph, feature tracking, session tracking, drift detection, activity log, work attribution, feature status, session management

---

## Core Responsibilities

### 1. **Use SDK, Not MCP Tools** (CRITICAL)

**IMPORTANT: For Claude Code, use the Python SDK directly instead of MCP tools.**

**Why SDK over MCP:**
- ✅ **No context bloat** - MCP tool schemas consume precious tokens
- ✅ **Runtime discovery** - Explore all operations via Python introspection
- ✅ **Type hints** - See all available methods without schemas
- ✅ **More powerful** - Full programmatic access, not limited to 3 MCP tools
- ✅ **Faster** - Direct Python, no JSON-RPC overhead

The SDK provides access to ALL HtmlGraph operations without adding tool definitions to your context.

**ABSOLUTE RULE: You must NEVER use Read, Write, or Edit tools on `.htmlgraph/` HTML files.**

AI agents MUST use the SDK (or API/CLI for special cases) to ensure all HTML is validated through Pydantic + justhtml.

❌ **FORBIDDEN:**
```python
# NEVER DO THIS
Write('/path/to/.htmlgraph/features/feature-123.html', ...)
Edit('/path/to/.htmlgraph/sessions/session-456.html', ...)
with open('.htmlgraph/features/feature-123.html', 'w') as f:
    f.write('<html>...</html>')
```

✅ **REQUIRED - Use SDK (BEST CHOICE FOR AI AGENTS):**
```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Work with ANY collection (features, bugs, chores, spikes, epics, phases)
sdk.features    # Features with builder support
sdk.bugs        # Bug reports
sdk.chores      # Maintenance tasks
sdk.spikes      # Investigation spikes
sdk.epics       # Large bodies of work
sdk.phases      # Project phases

# Create features (fluent interface)
feature = sdk.features.create("Title") \
    .set_priority("high") \
    .add_steps(["Step 1", "Step 2"]) \
    .save()

# Edit ANY collection (auto-saves)
with sdk.features.edit("feature-123") as f:
    f.status = "done"

with sdk.bugs.edit("bug-001") as bug:
    bug.status = "in-progress"
    bug.priority = "critical"

# Vectorized batch updates (efficient!)
sdk.bugs.batch_update(
    ["bug-001", "bug-002", "bug-003"],
    {"status": "done", "resolution": "fixed"}
)

# Query across collections
high_priority = sdk.features.where(status="todo", priority="high")
in_progress_bugs = sdk.bugs.where(status="in-progress")

# All collections have same interface
sdk.chores.mark_done(["chore-1", "chore-2"])
sdk.spikes.assign(["spike-1"], agent="claude")
```

**Why SDK is best:**
- ✅ 3-16x faster than CLI (no process startup)
- ✅ Type-safe with auto-complete
- ✅ Context managers (auto-save)
- ✅ Vectorized batch operations
- ✅ Works offline (no server needed)
- ✅ Supports ALL collections (features, bugs, chores, spikes, epics, etc.)

✅ **ALTERNATIVE - Use CLI (for one-off commands):**
```bash
# CLI is slower (400ms startup per command) but convenient for one-off queries
uv run htmlgraph feature create/start/complete
uv run htmlgraph status
```

⚠️ **AVOID - API/curl (use only for remote access):**
```bash
# Requires server + network overhead, only use for remote access
curl -X PATCH localhost:8080/api/features/feat-123 -d '{"status": "done"}'
```

**Why this matters:**
- Direct file edits bypass Pydantic validation
- Bypass justhtml HTML generation (can create invalid HTML)
- Break the SQLite index sync
- Skip event logging and activity tracking
- Can corrupt graph structure and relationships

**Exception:** You MAY read `.htmlgraph/` files to view content, but NEVER write or edit them.

**Documentation:** See `AGENTS.md` for complete SDK guide and best practices.

### 2. Feature Awareness
Always be aware of which feature(s) are currently in progress:
- Check active features at session start
- Reference the current feature when discussing work
- Alert if work appears to drift from the assigned feature

### 3. Step Completion (CRITICAL)
**Mark each step complete IMMEDIATELY after finishing it:**
- Use curl PATCH to `/api/features/<id>` with `{"complete_step": index}`
- Step 0 = first step, step 1 = second step (0-based indexing)
- Do NOT wait until all steps are done - mark each one as you finish
- See "How to Mark Steps Complete" section below for exact commands

### 4. Activity Attribution
HtmlGraph automatically tracks tool usage, but you should:
- Use descriptive summaries in Bash `description` parameter
- Reference feature IDs in commit messages
- Mention the feature context when starting new tasks

### 5. Documentation Habits
For every significant piece of work:
- Summarize what was done and why
- Note any decisions made and alternatives considered
- Record blockers or dependencies discovered

## Working with HtmlGraph

**RECOMMENDED:** Use the Python SDK for AI agents (cleanest, fastest, most powerful)

### Python SDK (PRIMARY INTERFACE - Use This!)

The SDK supports ALL collections with a unified interface. Use it for maximum performance and type safety.

```python
from htmlgraph import SDK

# Initialize (auto-discovers .htmlgraph)
sdk = SDK(agent="claude")

# ===== ALL COLLECTIONS SUPPORTED =====
# Features (with builder support)
feature = sdk.features.create("User Authentication") \
    .set_priority("high") \
    .add_steps([
        "Create login endpoint",
        "Add JWT middleware",
        "Write tests"
    ]) \
    .save()

# Bugs
with sdk.bugs.edit("bug-001") as bug:
    bug.status = "in-progress"
    bug.priority = "critical"

# Chores, Spikes, Epics - all work the same way
chore = sdk.chores.where(status="todo")[0]
spike_results = sdk.spikes.all()
epic_steps = sdk.epics.get("epic-001").steps

# ===== EFFICIENT BATCH OPERATIONS =====
# Mark multiple items done (vectorized!)
sdk.bugs.mark_done(["bug-001", "bug-002", "bug-003"])

# Assign multiple items to agent
sdk.features.assign(["feat-001", "feat-002"], agent="claude")

# Custom batch updates (any attributes)
sdk.chores.batch_update(
    ["chore-001", "chore-002"],
    {"status": "done", "agent_assigned": "claude"}
)

# ===== CROSS-COLLECTION QUERIES =====
# Find all in-progress work
in_progress = []
for coll_name in ['features', 'bugs', 'chores', 'spikes', 'epics']:
    coll = getattr(sdk, coll_name)
    in_progress.extend(coll.where(status='in-progress'))

# Find low-lift tasks
for item in in_progress:
    if hasattr(item, 'steps'):
        for step in item.steps:
            if not step.completed and 'document' in step.description.lower():
                print(f"📝 {item.id}: {step.description}")
```

**SDK Performance (vs CLI):**
- Single query: **3x faster**
- 5 queries: **9x faster**
- 10 batch updates: **16x faster**

### CLI (For One-Off Commands Only)

**IMPORTANT:** Always use `uv run` when running htmlgraph commands to ensure the correct environment.

⚠️ CLI is slower than SDK (400ms startup per command). Use for quick one-off queries only.

```bash
# Check Current Status
uv run htmlgraph status
uv run htmlgraph feature list

# Start Working on a Feature
uv run htmlgraph feature start <feature-id>

# Set Primary Feature (when multiple are active)
uv run htmlgraph feature primary <feature-id>

# Complete a Feature
uv run htmlgraph feature complete <feature-id>
```

**When to use CLI vs SDK:**
- CLI: Quick one-off shell command
- SDK: Everything else (faster, more powerful, better for scripts)

## Feature Creation Decision Framework

**CRITICAL**: Use this framework to decide when to create a feature vs implementing directly.

### Quick Decision Rule

Create a **FEATURE** if ANY apply:
- Estimated >30 minutes of work
- Involves 3+ files
- Requires new automated tests
- Affects multiple components
- Hard to revert (schema, API changes)
- Needs user/API documentation

Implement **DIRECTLY** if ALL apply:
- Single file, obvious change
- <30 minutes work
- No cross-system impact
- Easy to revert
- No tests needed
- Internal/trivial change

### Decision Tree (Quick Reference)

```
User request received
  ├─ Bug in existing feature? → See Bug Fix Workflow in WORKFLOW.md
  ├─ >30 minutes? → CREATE FEATURE
  ├─ 3+ files? → CREATE FEATURE
  ├─ New tests needed? → CREATE FEATURE
  ├─ Multi-component impact? → CREATE FEATURE
  ├─ Hard to revert? → CREATE FEATURE
  └─ Otherwise → IMPLEMENT DIRECTLY
```

### Examples

**✅ CREATE FEATURE:**
- "Add user authentication" (multi-file, tests, docs)
- "Implement session comparison view" (new UI, Playwright tests)
- "Fix attribution drift algorithm" (complex, backend tests)

**❌ IMPLEMENT DIRECTLY:**
- "Fix typo in README" (single file, trivial)
- "Update CSS color" (single file, quick, reversible)
- "Add missing import" (obvious fix, no impact)

### Default Rule

**When in doubt, CREATE A FEATURE.** Over-tracking is better than losing attribution.

See `docs/WORKFLOW.md` for the complete decision framework with detailed criteria, thresholds, and edge cases.

## Session Workflow Checklist

**Use this checklist for EVERY session to ensure quality and proper attribution.**

### Session Start
- [ ] Activate this skill (done)
- [ ] Check status: `uv run htmlgraph status`
- [ ] Review active features
- [ ] Greet user with status update
- [ ] Decide: Create feature or implement directly? (use decision framework)
- [ ] Start feature: `uv run htmlgraph feature start <id>`

### During Work
- [ ] Feature marked "in-progress" before coding
- [ ] **CRITICAL: Mark each step complete IMMEDIATELY after finishing it** (see below)
- [ ] Document decisions with `uv run htmlgraph track`
- [ ] Test incrementally
- [ ] Watch for drift warnings

#### How to Mark Steps Complete

**IMPORTANT:** After finishing each step, mark it complete using curl:

```bash
# Mark step 0 (first step) as complete
curl -X PATCH http://localhost:8080/api/features/<feature-id> \
  -H "Content-Type: application/json" \
  -d '{"complete_step": 0}'

# Mark step 1 (second step) as complete
curl -X PATCH http://localhost:8080/api/features/<feature-id> \
  -H "Content-Type: application/json" \
  -d '{"complete_step": 1}'
```

**Step numbering is 0-based** (first step = 0, second step = 1, etc.)

**When to mark complete:**
- ✅ IMMEDIATELY after finishing a step
- ✅ Even if you continue working on the feature
- ✅ Before moving to the next step
- ❌ NOT at the end when all steps are done (too late!)

**Example workflow:**
1. Start feature: `uv run htmlgraph feature start feature-123`
2. Work on step 0 (e.g., "Design models")
3. **MARK STEP 0 COMPLETE** → `curl -X PATCH ...`
4. Work on step 1 (e.g., "Create templates")
5. **MARK STEP 1 COMPLETE** → `curl -X PATCH ...`
6. Continue until all steps done
7. Complete feature: `uv run htmlgraph feature complete feature-123`

### Session End (Before Completion)
- [ ] All tests pass: `uv run pytest`
- [ ] Validate attribution: `uv run htmlgraph session validate-attribution <feature-id>`
- [ ] All feature steps complete
- [ ] No debug code or TODOs
- [ ] Commit with feature ID
- [ ] Mark feature complete: `uv run htmlgraph feature complete <id>`
- [ ] Update epic step (if applicable)

**Full checklist:** See `docs/WORKFLOW.md` → "Claude Code Session Checklist"

## Handling Drift Warnings

When you see a drift warning like:
> Drift detected (0.74): Activity may not align with feature-self-tracking

Consider:
1. **Is this expected?** Sometimes work naturally spans multiple features
2. **Should you switch features?** Use `uv run htmlgraph feature primary <id>` to change attribution
3. **Is the feature scope wrong?** The feature's file patterns or keywords may need updating

## Session Continuity

At the start of each session:
1. Review previous session summary (if provided)
2. Note current feature progress
3. Identify what remains to be done
4. Ask the user what they'd like to work on

At the end of each session:
1. The SessionEnd hook will generate a summary
2. All activities are preserved in `.htmlgraph/sessions/`
3. Feature progress is updated automatically

## Best Practices

### Commit Messages
Include feature context:
```
feat(feature-id): Description of the change

- Details about what was done
- Why this approach was chosen

🤖 Generated with Claude Code
```

### Task Descriptions
When using Bash tool, always provide a description:
```bash
# Good - descriptive
Bash(description="Install dependencies for auth feature")

# Bad - no context
Bash(command="npm install")
```

### Decision Documentation
When making architectural decisions:

1. Track with `uv run htmlgraph track "Decision" "Chose X over Y because Z"`
2. Or note in the feature's HTML file under activity log

## Dashboard Access

View progress visually:
```bash
uv run htmlgraph serve
# Open http://localhost:8080
```

The dashboard shows:
- Kanban board with feature status
- Session history with activity logs
- Graph visualization of dependencies

## Key Files

- `.htmlgraph/features/` - Feature HTML files (the graph nodes)
- `.htmlgraph/sessions/` - Session HTML files with activity logs
- `index.html` - Dashboard (open in browser)

## Integration Points

HtmlGraph hooks track:
- **SessionStart**: Creates session, provides feature context
- **PostToolUse**: Logs every tool call with attribution
- **UserPromptSubmit**: Logs user queries
- **SessionEnd**: Finalizes session with summary

All data is stored as HTML files - human-readable, git-friendly, browser-viewable.
