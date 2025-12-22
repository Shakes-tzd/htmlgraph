# HtmlGraph Tracker Extension for Gemini CLI

HtmlGraph is tracking this session to ensure proper activity attribution and documentation.

## When This Extension Is Active

- At the start of every session when HtmlGraph is initialized
- When working on features, bugs, or other tracked work items
- When you need to mark work as complete or update progress
- Throughout your development workflow for continuous tracking

---

## ✅ AUTOMATIC SESSION MANAGEMENT

**Good News: Gemini CLI has hooks!** This extension automatically manages sessions for you:

- **SessionStart hook** → Automatically starts/resumes HtmlGraph session
- **AfterTool hook** → Automatically tracks all tool usage
- **SessionEnd hook** → Automatically finalizes session when you exit

**You don't need to manually start/end sessions** - the hooks handle it! Just focus on:
1. Starting features before coding
2. Marking steps complete as you work
3. Completing features when done

---

## Core Responsibilities

### 1. **Use SDK, Not Direct File Edits** (CRITICAL)

**ABSOLUTE RULE: You must NEVER use file operations on `.htmlgraph/` HTML files.**

All HtmlGraph operations MUST use the SDK via Bash to ensure validation through Pydantic + justhtml.

❌ **FORBIDDEN:**
```bash
# NEVER DO THIS
echo '<html>...</html>' > .htmlgraph/features/feature-123.html
sed -i 's/todo/done/' .htmlgraph/features/feature-123.html
```

✅ **REQUIRED - Use SDK via Bash:**
```bash
# Install HtmlGraph
uv pip install htmlgraph

# Check status
uv run htmlgraph status

# Start feature
uv run htmlgraph feature start feat-123

# Complete step using SDK
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='gemini')
with sdk.features.edit('feat-123') as f:
    f.steps[0].completed = True
"

# Complete feature
uv run htmlgraph feature complete feat-123
```

**Why this matters:**
- Direct file edits bypass Pydantic validation
- Bypass justhtml HTML generation (can create invalid HTML)
- Break the SQLite index sync
- Skip event logging and activity tracking
- Can corrupt graph structure and relationships

**NO EXCEPTIONS: NEVER read, write, or edit `.htmlgraph/` files directly.**

Use the SDK for ALL operations including inspection:

```bash
# ✅ CORRECT - Inspect sessions/events via SDK
uv run python -c "
from htmlgraph import SDK
from htmlgraph.session_manager import SessionManager

sdk = SDK(agent='gemini')
sm = SessionManager()

# Get current session
session = sm.get_active_session(agent='gemini')
print(f'Session: {session.id}, Events: {session.event_count}')

# Get recent events (last 10)
recent = session.get_events(limit=10, offset=session.event_count - 10)
for evt in recent:
    print(f\"{evt['event_id']}: {evt['tool']} - {evt['summary']}\")

# Query events by tool
bash_events = session.query_events(tool='Bash', limit=20)

# Get event statistics
stats = session.event_stats()
print(f\"Total: {stats['total_events']}, Tools: {stats['tools_used']}\")
"
```

❌ **FORBIDDEN - Reading files directly:**
```bash
# NEVER DO THIS
cat .htmlgraph/events/session-123.jsonl
tail -10 .htmlgraph/sessions/session-123.html
grep "feature" .htmlgraph/events/*.jsonl
```

**Documentation:**
- Event inspection guide: `docs/SDK_EVENT_INSPECTION.md`
- Complete SDK guide: `docs/SDK_FOR_AI_AGENTS.md`

---

### 2. **Feature Awareness** (MANDATORY)

You MUST always know which feature(s) are currently in progress:

```bash
# Check at session start
uv run htmlgraph status
uv run htmlgraph feature list

# View feature details
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='gemini')
features = sdk.features.where(status='in-progress')
for f in features:
    print(f'{f.id}: {f.title} - {len([s for s in f.steps if s.completed])}/{len(f.steps)} steps')
"
```

Reference the current feature when discussing work and alert immediately if work appears to drift from the assigned feature.

---

### 3. **Step Completion** (CRITICAL)

**Mark each step complete IMMEDIATELY after finishing it:**

```python
# Use SDK to mark steps complete
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='gemini')

# Mark step 0 (first step) as complete
with sdk.features.edit('feature-id') as f:
    f.steps[0].completed = True

# Or mark multiple steps at once
with sdk.features.edit('feature-id') as f:
    f.steps[0].completed = True
    f.steps[1].completed = True
    f.steps[2].completed = True
"
```

**Step numbering is 0-based** (first step = 0, second step = 1, etc.)

**When to mark complete:**
- ✅ IMMEDIATELY after finishing a step
- ✅ Even if you continue working on the feature
- ✅ Before moving to the next step
- ❌ NOT at the end when all steps are done (too late!)

---

### 4. **Continuous Tracking** (CRITICAL)

**ABSOLUTE REQUIREMENT: ALL work MUST be tracked in HtmlGraph.**

Think of HtmlGraph tracking like Git commits - you wouldn't do work without committing it, and you shouldn't do work without tracking it.

**Every time you complete work, update HtmlGraph immediately:**
- ✅ Finished a step? → Mark it complete via SDK
- ✅ Fixed a bug? → Update bug status
- ✅ Discovered a decision? → Document it in the feature
- ✅ Changed approach? → Note it in activity log
- ✅ Completed a task? → Mark feature/bug/chore as done

**Why this matters:**
- Attribution ensures work isn't lost across sessions
- Links between sessions and features preserve context
- Drift detection helps catch scope creep early
- Analytics show real progress, not guesses

---

## Working with Tracks, Specs, and Plans

### What Are Tracks?

**Tracks are high-level containers for multi-feature work** (conductor-style planning):
- **Track** = Overall initiative with multiple related features
- **Spec** = Detailed specification with requirements and acceptance criteria
- **Plan** = Implementation plan with phases and estimated tasks
- **Features** = Individual work items linked to the track

**When to create a track:**
- Work involves 3+ related features
- Need high-level planning before implementation
- Multi-phase implementation
- Coordination across multiple sessions or agents

**When to skip tracks:**
- Single feature work
- Quick fixes or enhancements
- Direct implementation without planning phase

---

### Creating Tracks with TrackBuilder (PRIMARY METHOD)

**IMPORTANT: Use the TrackBuilder for deterministic track creation with minimal effort.**

The TrackBuilder provides a fluent API that auto-generates IDs, timestamps, file paths, and HTML files.

```bash
# Create complete track with spec and plan using Python SDK via bash
uv run python -c "
from htmlgraph import SDK

sdk = SDK(agent='gemini')

# Create track with spec and plan
track = sdk.tracks.builder() \\
    .title('User Authentication System') \\
    .description('Implement OAuth 2.0 authentication with JWT') \\
    .priority('high') \\
    .with_spec(
        overview='Add secure authentication with OAuth 2.0 support',
        context='Current system has no authentication',
        requirements=[
            ('Implement OAuth 2.0 flow', 'must-have'),
            ('Add JWT token management', 'must-have'),
            ('Create user profile endpoint', 'should-have')
        ],
        acceptance_criteria=[
            ('Users can log in with Google/GitHub', 'OAuth test passes'),
            'JWT tokens expire after 1 hour'
        ]
    ) \\
    .with_plan_phases([
        ('Phase 1: OAuth Setup', [
            'Configure OAuth providers (1h)',
            'Implement OAuth callback (2h)'
        ]),
        ('Phase 2: JWT Integration', [
            'Create JWT signing logic (2h)',
            'Add token refresh endpoint (1.5h)'
        ])
    ]) \\
    .create()

print(f'Created track: {track.id}')
print(f'Has spec: {track.has_spec}')
print(f'Has plan: {track.has_plan}')
"

# Output:
# ✓ Created track: track-20251221-220000
#   - Spec with 3 requirements
#   - Plan with 2 phases, 4 tasks
```

**TrackBuilder Features:**
- ✅ Auto-generates track IDs with timestamps
- ✅ Creates index.html, spec.html, plan.html automatically
- ✅ Parses time estimates from task descriptions `"Task (2h)"`
- ✅ Validates requirements and acceptance criteria via Pydantic
- ✅ Fluent API with method chaining
- ✅ Single `.create()` call generates everything

---

### Linking Features to Tracks

After creating a track, link features to it:

```bash
# Create features linked to track
uv run python -c "
from htmlgraph import SDK

sdk = SDK(agent='gemini')

track_id = 'track-20251221-220000'

# Create and link features
oauth_feature = sdk.features.create('OAuth Integration') \\
    .set_track(track_id) \\
    .set_priority('high') \\
    .add_steps([
        'Configure OAuth providers',
        'Implement OAuth callback',
        'Add state verification'
    ]) \\
    .save()

print(f'Created feature {oauth_feature.id} linked to {track_id}')

# Query features by track
track_features = sdk.features.where(track=track_id)
print(f'Track has {len(track_features)} features')
"
```

**The track_id field:**
- Links features to their parent track
- Enables track-level progress tracking
- Used for querying related features
- Automatically indexed for fast lookups

---

### TrackBuilder API Reference

**Methods:**

- `.title(str)` - Set track title (REQUIRED)
- `.description(str)` - Set description (optional)
- `.priority(str)` - Set priority: "low", "medium", "high", "critical" (default: "medium")
- `.with_spec(...)` - Add specification (optional)
  - `overview` - High-level summary
  - `context` - Background and current state
  - `requirements` - List of `(description, priority)` tuples or strings
    - Priorities: "must-have", "should-have", "nice-to-have"
  - `acceptance_criteria` - List of `(description, test_case)` tuples or strings
- `.with_plan_phases(list)` - Add plan phases (optional)
  - Format: `[(phase_name, [task_descriptions]), ...]`
  - Task estimates: Include `(Xh)` in description, e.g., "Implement auth (3h)"
- `.create()` - Execute build and create all files (returns Track object)

**Documentation:**
- Quick start: `docs/TRACK_BUILDER_QUICK_START.md`
- Complete workflow: `docs/TRACK_WORKFLOW.md`
- Full proposal: `docs/AGENT_FRIENDLY_SDK.md`

---

## Working with HtmlGraph SDK

### Python SDK (PRIMARY INTERFACE)

The SDK supports ALL collections with a unified interface:

```python
from htmlgraph import SDK

# Initialize (auto-discovers .htmlgraph)
sdk = SDK(agent="gemini")

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

# Work with any collection
with sdk.bugs.edit("bug-001") as bug:
    bug.status = "in-progress"
    bug.priority = "critical"

# Query across collections
high_priority = sdk.features.where(status="todo", priority="high")
in_progress_bugs = sdk.bugs.where(status="in-progress")

# Batch operations (efficient!)
sdk.bugs.batch_update(
    ["bug-001", "bug-002", "bug-003"],
    {"status": "done", "resolution": "fixed"}
)
```

### CLI (for one-off commands)

```bash
# Quick status check
uv run htmlgraph status

# Feature management
uv run htmlgraph feature create "New Feature"
uv run htmlgraph feature start feat-123
uv run htmlgraph feature complete feat-123

# List features
uv run htmlgraph feature list --status in-progress
```

---

## Work Type Classification (Phase 1)

**NEW: HtmlGraph now automatically categorizes all work by type to differentiate exploratory work from implementation.**

### Work Type Categories

All events are automatically tagged with a work type based on the active feature:

- **feature-implementation** - Building new functionality (feat-*)
- **spike-investigation** - Research and exploration (spike-*)
- **bug-fix** - Correcting defects (bug-*)
- **maintenance** - Refactoring and tech debt (chore-*)
- **documentation** - Writing docs (doc-*)
- **planning** - Design decisions (plan-*)
- **review** - Code review
- **admin** - Administrative tasks

### Creating Spikes (Investigation Work)

Use Spike model for timeboxed investigation:

```bash
# Via SDK (recommended)
uv run python -c "
from htmlgraph import SDK, SpikeType

sdk = SDK(agent='gemini')

# Create a spike with classification
spike = sdk.spikes.create('Investigate OAuth providers') \\
    .set_spike_type(SpikeType.TECHNICAL) \\
    .set_timebox_hours(4) \\
    .add_steps([
        'Research OAuth 2.0 flow',
        'Compare Google vs GitHub providers',
        'Document security considerations'
    ]) \\
    .save()

print(f'Created spike: {spike.id}')
"

# Update findings after investigation
uv run python -c "
from htmlgraph import SDK

sdk = SDK(agent='gemini')

with sdk.spikes.edit('spike-123') as s:
    s.findings = 'Google OAuth has better docs but GitHub has simpler integration'
    s.decision = 'Use GitHub OAuth for MVP, migrate to Google later if needed'
    s.status = 'done'
"
```

**Spike Types:**
- `TECHNICAL` - Investigate technical implementation options
- `ARCHITECTURAL` - Research system design decisions
- `RISK` - Identify and assess project risks
- `GENERAL` - Uncategorized investigation

### Creating Chores (Maintenance Work)

Use Chore model for maintenance tasks:

```bash
# Via SDK
uv run python -c "
from htmlgraph import SDK, MaintenanceType

sdk = SDK(agent='gemini')

# Create a chore with classification
chore = sdk.chores.create('Refactor authentication module') \\
    .set_maintenance_type(MaintenanceType.PREVENTIVE) \\
    .set_technical_debt_score(7) \\
    .add_steps([
        'Extract auth logic to separate module',
        'Add unit tests for auth flows',
        'Update documentation'
    ]) \\
    .save()

print(f'Created chore: {chore.id}')
"
```

**Maintenance Types:**
- `CORRECTIVE` - Fix defects and errors
- `ADAPTIVE` - Adapt to environment changes (OS, dependencies)
- `PERFECTIVE` - Improve performance, usability, maintainability
- `PREVENTIVE` - Prevent future problems (refactoring, tech debt)

### Session Work Type Analytics

Query work type distribution for any session:

```bash
# Get work breakdown for current session
uv run python -c "
from htmlgraph import SDK
from htmlgraph.session_manager import SessionManager

sdk = SDK(agent='gemini')
sm = SessionManager()
session = sm.get_active_session(agent='gemini')

# Calculate work breakdown
breakdown = session.calculate_work_breakdown()
print(f'Work breakdown: {breakdown}')

# Get primary work type
primary = session.calculate_primary_work_type()
print(f'Primary work type: {primary}')
"
```

### Automatic Work Type Inference

**Work type is automatically inferred from feature_id prefix:**

```bash
# When you start a spike:
uv run htmlgraph spike start spike-123
# → All events auto-tagged with work_type="spike-investigation"

# When you start a feature:
uv run htmlgraph feature start feat-456
# → All events auto-tagged with work_type="feature-implementation"

# When you start a chore:
uv run htmlgraph chore start chore-789
# → All events auto-tagged with work_type="maintenance"
```

**No manual tagging required!** The system automatically categorizes your work based on what you're working on.

### Why This Matters

Work type classification enables you to:

1. **Differentiate exploration from implementation** - "How much time was spent researching vs building?"
2. **Track technical debt** - "What % of work is maintenance vs new features?"
3. **Measure innovation** - "What's our spike-to-feature ratio?"
4. **Session context** - "Was this primarily an exploratory session or implementation?"

---

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

### Decision Tree

```
User request received
  ├─ Bug in existing feature? → Check if needs feature or direct fix
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
- "Implement session comparison view" (new UI, tests)
- "Fix attribution drift algorithm" (complex, backend tests)

**❌ IMPLEMENT DIRECTLY:**
- "Fix typo in README" (single file, trivial)
- "Update CSS color" (single file, quick, reversible)
- "Add missing import" (obvious fix, no impact)

### Default Rule

**When in doubt, CREATE A FEATURE.** Over-tracking is better than losing attribution.

---

## Workflow Checklist

**Use this checklist to guide your work:**

### At Start of Work
1. ✅ **CHECK STATUS:** `uv run htmlgraph status` (hooks already started session)
2. ✅ Review active features and decide if you need to create a new one
3. ✅ Greet user with brief status update
4. ✅ **DECIDE:** Create feature or implement directly? (use decision framework above)
5. ✅ **If creating feature:** Run `uv run htmlgraph feature start <id>`

### During Work (DO CONTINUOUSLY)
1. ✅ Feature MUST be marked "in-progress" before you write any code
2. ✅ **CRITICAL:** Mark each step complete IMMEDIATELY after finishing it (use SDK)
3. ✅ Document ALL decisions as you make them
4. ✅ Test incrementally - don't wait until the end
5. ✅ Watch for drift warnings and act on them immediately

### How to Mark Steps Complete

```python
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='gemini')

# Mark step as complete
with sdk.features.edit('feature-123') as f:
    f.steps[0].completed = True  # Mark first step complete
"
```

### Before Completing Feature (VERIFY ALL)
1. ✅ **RUN TESTS:** All tests MUST pass
2. ✅ **VERIFY ATTRIBUTION:** Check that activities are linked to correct feature
3. ✅ **CHECK STEPS:** ALL feature steps MUST be marked complete
4. ✅ **CLEAN CODE:** Remove all debug code, console.logs, TODOs
5. ✅ **COMMIT WORK:** Git commit your changes IMMEDIATELY (allows user rollback)
   - Do this BEFORE marking the feature complete
   - Include the feature ID in the commit message
6. ✅ **COMPLETE FEATURE:** `uv run htmlgraph feature complete <id>`
7. ✅ **UPDATE EPIC:** If part of epic, mark epic step complete

**Session ends automatically when you exit** - no manual action needed!

**REMINDER:** Completing a feature without doing all of the above means incomplete work. Don't skip steps.

---

## SDK Quick Reference

### Installation
```bash
uv pip install htmlgraph
```

### Common Operations

**Check Status:**
```bash
uv run htmlgraph status
```

**Start Feature:**
```bash
uv run htmlgraph feature start feat-123
```

**Complete Step:**
```python
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='gemini')
with sdk.features.edit('feat-123') as f:
    f.steps[0].completed = True
"
```

**Complete Feature:**
```bash
uv run htmlgraph feature complete feat-123
```

**Query Features:**
```python
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='gemini')
print(sdk.features.where(status='in-progress'))
"
```

**Batch Operations:**
```python
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='gemini')
sdk.bugs.batch_update(
    ['bug-001', 'bug-002'],
    {'status': 'done', 'resolution': 'fixed'}
)
"
```

---

## Key Principles

1. **USE SDK FOR ALL OPERATIONS** - Never edit .htmlgraph/ files directly
2. **TRACK CONTINUOUSLY** - Update progress as you work, not at the end
3. **MARK STEPS IMMEDIATELY** - Complete each step as you finish it
4. **CREATE FEATURES FOR NON-TRIVIAL WORK** - Use the decision framework
5. **VERIFY BEFORE COMPLETION** - All tests pass, all steps done, clean code
6. **HOOKS HANDLE SESSIONS** - You don't need to manually manage sessions

---

## Documentation

For complete SDK documentation, see:
https://github.com/Shakes-tzd/htmlgraph/blob/main/docs/SDK_FOR_AI_AGENTS.md

For HtmlGraph project:
https://github.com/Shakes-tzd/htmlgraph
