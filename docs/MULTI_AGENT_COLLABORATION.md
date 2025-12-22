# Multi-Agent Collaboration in HtmlGraph

## Overview

HtmlGraph enables multiple AI agents (Claude Code, Codex CLI, Gemini CLI) to work together on the same project, with automatic session management, work attribution, and handoff capabilities.

---

## Current Capabilities ✅

### 1. **Agent-Specific Sessions**

Each agent maintains its own session with automatic tracking:

```python
# SessionManager supports per-agent sessions
session = manager.get_active_session_for_agent(agent="claude")
```

**Benefits:**
- ✅ Prevents cross-agent pollution
- ✅ Multiple agents can work simultaneously
- ✅ Each agent's work is properly attributed

**Evidence:**
```bash
$ htmlgraph session list
ID                             Status     Agent           Events
=========================================================================
session-20251217-092958        active     cli             17
session-20251217-090157        active     gemini          2
session-20251217-084026        active     codex           2
0e6fd1e4-bc71-4424-88d4...     active     claude-code     2335
```

### 2. **Automatic Activity Attribution**

Activities are automatically attributed to features using smart scoring:

```python
# Attribution scoring weights
WEIGHT_FILE_PATTERN = 0.4   # File path matches feature patterns
WEIGHT_KEYWORD = 0.3        # Keywords in summary match feature
WEIGHT_TYPE_PRIORITY = 0.2  # Feature type priority (bug > feature > chore)
WEIGHT_IS_PRIMARY = 0.1     # Feature marked as primary
```

**Benefits:**
- ✅ No manual feature selection needed
- ✅ Work automatically linked to correct features
- ✅ Drift detection when work diverges

### 3. **Session Continuity**

Sessions preserve full context across agent handoffs:

```python
session = Session(
    id="session-001",
    agent="claude",
    continued_from="previous-session-id",  # Link to prior work
    activity_log=[...],  # Full history
    primary_feature_id="feat-123",  # What they were working on
)
```

**Benefits:**
- ✅ New agent can see what previous agent did
- ✅ Activity history preserved
- ✅ Context for continuing work

### 4. **SDK Unified Across Agents**

All agents use the same SDK API:

```python
# Works identically for all agents - just change agent name
sdk = SDK(agent="claude")  # or "codex" or "gemini"

# Same operations
feature = sdk.features.get("feat-123")
with sdk.features.edit("feat-123") as f:
    f.steps[0].completed = True
```

**Benefits:**
- ✅ No agent-specific code needed
- ✅ Skills/extensions can be nearly identical
- ✅ Easy to switch agents mid-project

---

## Gaps & Limitations ⚠️

### 1. **No Feature Assignment Mechanism**

**Problem:** Features don't have an "assigned_agent" field

**Impact:**
- ❌ No clear ownership of features
- ❌ Two agents might work on same feature simultaneously
- ❌ No way to query "what should I work on?"

**Current Workaround:**
- Primary feature mechanism (weak signal)
- Manual coordination via feature status

### 2. **No Work Claiming/Locking**

**Problem:** No mechanism to "claim" a feature before starting work

**Impact:**
- ❌ Race conditions when multiple agents active
- ❌ Duplicate work possible
- ❌ No blocking to prevent conflicts

**Example Scenario:**
```
Claude:  Sees feat-123 is "todo", starts working
Gemini:  Sees feat-123 is "todo", also starts working
Result:  Both agents working on same feature, conflicting changes
```

### 3. **Limited Handoff Context**

**Problem:** When Agent A ends session, Agent B doesn't know where to continue

**Impact:**
- ❌ Agent B must manually discover next steps
- ❌ No "recommended next task" based on previous agent's work
- ❌ Context loss between sessions

**What's Missing:**
- Handoff notes from previous agent
- Recommended next feature
- Blockers or dependencies
- Agent-specific context (e.g., "I'm better at UI than backend")

### 4. **No Agent Capability Metadata**

**Problem:** Features don't specify which agent type is best suited

**Impact:**
- ❌ Can't route UI work to frontend-focused agents
- ❌ Can't route complex reasoning to Claude Opus
- ❌ Can't route simple tasks to fast agents (Haiku)

**Example:**
```
Feature: "Design and implement authentication UI"
→ Should go to Claude Code (has browser preview)
  NOT Codex CLI (terminal only)

Feature: "Fix type error in auth.ts line 45"
→ Should go to fast agent (Haiku via Task tool)
  NOT main Claude Sonnet (expensive)
```

### 5. **No Work Queue/Priority System**

**Problem:** Agents don't have a work queue showing available tasks

**Impact:**
- ❌ Agent must manually search for next task
- ❌ High-priority bugs might be missed
- ❌ No load balancing across agents

**What's Needed:**
```python
# Get work queue for specific agent
work = sdk.work_queue.get_next(
    agent="claude",
    capabilities=["ui", "python"],
    max_complexity="medium"
)
```

---

## Proposed Enhancements 🚀

### Enhancement 1: Feature Assignment & Claiming

**Add to Feature Model:**
```python
class Node:
    # ... existing fields ...
    assigned_agent: str | None = None      # Which agent is working on this
    claimed_at: datetime | None = None     # When was it claimed
    claimed_by_session: str | None = None  # Which session claimed it
```

**CLI Commands:**
```bash
# Claim a feature before starting work
htmlgraph feature claim feat-123 --agent claude

# Release a feature (if agent stops working on it)
htmlgraph feature release feat-123

# Auto-release stale claims (older than 2 hours)
htmlgraph feature auto-release --max-age 2h
```

**SDK API:**
```python
# Try to claim feature (fails if already claimed)
feature = sdk.features.claim("feat-123")

# Automatic claim on start
with sdk.features.start("feat-123") as f:
    # Auto-claims on enter, auto-releases on exit
    f.complete_step(0)
```

**Benefits:**
- ✅ Prevents duplicate work
- ✅ Clear ownership during active development
- ✅ Auto-cleanup of stale claims

---

### Enhancement 2: Handoff Context & Notes

**Add to Session Model:**
```python
class Session:
    # ... existing fields ...
    handoff_notes: str = ""           # Notes for next agent
    recommended_next: str | None = None  # Suggested next feature
    blockers: list[str] = []          # What's blocking progress
    context_for_next_agent: dict = {} # Rich handoff context
```

**CLI Commands:**
```bash
# Add handoff notes when ending session
htmlgraph session end session-001 \
  --notes "Completed auth API, UI still needs work" \
  --recommend feat-124 \
  --blocker "Need design approval for login page"

# View handoff context from previous session
htmlgraph session handoff session-001
```

**SDK API:**
```python
# When ending session, provide handoff
sdk.session.end(
    notes="Auth API complete. Next: implement UI",
    recommend_next="feat-124-auth-ui",
    blockers=["Waiting on design review"]
)

# When starting new session, get handoff from previous
handoff = sdk.session.get_handoff(from_session="session-001")
print(handoff.notes)
print(f"Recommended next: {handoff.recommended_next}")
```

**Benefits:**
- ✅ Smooth agent transitions
- ✅ Context preservation
- ✅ Explicit communication between agents

---

### Enhancement 3: Agent Capabilities & Smart Routing

**Add to Feature Model:**
```python
class Node:
    # ... existing fields ...
    required_capabilities: list[str] = []  # ["ui", "backend", "database"]
    complexity: Literal["trivial", "simple", "medium", "complex"] = "medium"
    estimated_effort_minutes: int | None = None
```

**Add Agent Registry:**
```python
# .htmlgraph/agents.json
{
  "claude-code": {
    "capabilities": ["ui", "backend", "python", "typescript", "browser"],
    "max_complexity": "complex",
    "cost_tier": "high"
  },
  "codex-cli": {
    "capabilities": ["backend", "python", "typescript"],
    "max_complexity": "complex",
    "cost_tier": "high"
  },
  "gemini-cli": {
    "capabilities": ["backend", "python", "analysis"],
    "max_complexity": "medium",
    "cost_tier": "medium"
  },
  "haiku-task": {
    "capabilities": ["simple-tasks", "search", "refactor"],
    "max_complexity": "simple",
    "cost_tier": "low"
  }
}
```

**CLI Commands:**
```bash
# Get work matching agent capabilities
htmlgraph work next --agent claude-code

# Filter features by capability
htmlgraph feature list --requires ui --complexity simple
```

**SDK API:**
```python
# Get best-fit work for agent
work = sdk.work_queue.next(
    agent="claude",
    capabilities=["ui", "typescript"],
    max_effort_minutes=120
)

# Create feature with capability requirements
feature = sdk.features.create("Auth UI") \
    .require_capabilities(["ui", "browser"]) \
    .set_complexity("medium") \
    .estimate_effort(90)
```

**Smart Routing Logic:**
```python
def get_next_work(agent: str, capabilities: list[str]) -> Feature | None:
    """Get best-fit feature for agent."""

    # Get available features (todo, not claimed)
    available = sdk.features.where(
        status="todo",
        assigned_agent=None
    )

    # Score each feature
    scored = []
    for feature in available:
        score = 0

        # Capability match
        if all(req in capabilities for req in feature.required_capabilities):
            score += 10

        # Priority boost
        if feature.priority == "critical":
            score += 5
        elif feature.priority == "high":
            score += 3

        # Complexity match (don't assign complex to simple agents)
        # ...

        scored.append((score, feature))

    # Return highest scoring feature
    scored.sort(reverse=True)
    return scored[0][1] if scored else None
```

**Benefits:**
- ✅ Right work goes to right agent
- ✅ Complex UI tasks go to agents with browser preview
- ✅ Simple tasks go to fast/cheap agents
- ✅ Cost optimization

---

### Enhancement 4: Work Queue Dashboard

**New CLI Command:**
```bash
# Interactive work queue
htmlgraph work queue --agent claude

Output:
┌─────────────────────────────────────────────────────────────────┐
│ Work Queue for claude-code                                      │
├─────────────────────────────────────────────────────────────────┤
│ Available Work (3 features)                                     │
│                                                                  │
│ 🔴 [CRITICAL] feat-123: Fix auth crash                          │
│    Capabilities: [backend, python]                              │
│    Effort: ~30 min                                              │
│    Blocked by: None                                             │
│                                                                  │
│ 🟠 [HIGH] feat-124: Implement login UI                          │
│    Capabilities: [ui, typescript, browser]                      │
│    Effort: ~2 hours                                             │
│    Blocked by: None                                             │
│                                                                  │
│ 🟡 [MEDIUM] feat-125: Add user profile page                     │
│    Capabilities: [ui, backend]                                  │
│    Effort: ~4 hours                                             │
│    Blocked by: feat-124 (needs auth first)                      │
│                                                                  │
│ Currently In Progress (1 feature)                               │
│                                                                  │
│ ⏳ feat-120: Database migration                                 │
│    Agent: gemini-cli                                            │
│    Progress: 2/5 steps                                          │
│    Claimed: 45 min ago                                          │
└─────────────────────────────────────────────────────────────────┘

Recommended: Start with feat-123 (critical priority, quick win)
```

**SDK API:**
```python
# Get work queue
queue = sdk.work_queue.for_agent("claude")

print(f"Available: {len(queue.available)}")
print(f"In progress by others: {len(queue.in_progress)}")
print(f"Blocked: {len(queue.blocked)}")

# Get recommended work
next_work = queue.recommended()
if next_work:
    print(f"Recommended: {next_work.id} - {next_work.title}")
    next_work.claim()  # Claim before starting
```

**Benefits:**
- ✅ Clear visibility into available work
- ✅ See what other agents are working on
- ✅ Prioritization guidance
- ✅ Avoid duplicate work

---

### Enhancement 5: Session Continuity Improvements

**Enhanced Session Start Hook:**

When a session starts, show:
1. Previous session summary (what was done)
2. Active sessions by other agents (what others are doing)
3. Available work queue (what should I do next)
4. Blockers or urgent items (what needs attention)

**Hook Output Example:**
```markdown
## Session Continuity

**Previous Session:** session-20251220-143522 (claude-code)
- Completed: feature-auth-api (3/3 steps)
- Notes: "API endpoints done. UI implementation next."
- Recommended: feat-124-auth-ui

**Other Active Agents:**
- gemini-cli: Working on feat-130-db-migration (2/5 steps)
- codex-cli: Working on feat-135-api-docs (1/4 steps)

**Available Work for You:**
1. 🔴 feat-123: Fix auth crash (CRITICAL, 30 min)
2. 🟠 feat-124: Auth UI (HIGH, 2 hours) [RECOMMENDED from previous session]
3. 🟡 feat-125: User profile (MEDIUM, 4 hours, blocked by feat-124)

**Recommended Action:** Continue with feat-124-auth-ui (handoff from previous session)
```

**Benefits:**
- ✅ Zero context switching overhead
- ✅ Natural continuation of work
- ✅ Awareness of team activity
- ✅ Smart recommendations

---

## Implementation Plan

### Phase 1: Feature Assignment & Claiming (Week 1)
- [ ] Add `assigned_agent`, `claimed_at`, `claimed_by_session` to Node model
- [ ] Implement `feature claim/release/auto-release` CLI commands
- [ ] Add claim/release to SDK
- [ ] Update hooks to auto-release on session end
- [ ] Add claim enforcement (prevent starting claimed features)

### Phase 2: Handoff Context (Week 1)
- [ ] Add `handoff_notes`, `recommended_next`, `blockers` to Session model
- [ ] Implement `session end --notes/--recommend/--blocker` CLI
- [ ] Add `session handoff` CLI command
- [ ] Update session-end hooks to prompt for handoff notes
- [ ] Update session-start hooks to display handoff context

### Phase 3: Agent Capabilities & Routing (Week 2)
- [ ] Add `required_capabilities`, `complexity`, `estimated_effort` to Node model
- [ ] Create `.htmlgraph/agents.json` registry
- [ ] Implement `work next` CLI command with smart routing
- [ ] Add capability filtering to feature queries
- [ ] Create work queue scoring algorithm

### Phase 4: Work Queue Dashboard (Week 2)
- [ ] Implement `work queue` CLI command
- [ ] Add recommended work logic
- [ ] Show other agents' active work
- [ ] Add blocking/dependency visualization
- [ ] Integrate with session-start hook

### Phase 5: Enhanced Session Continuity (Week 3)
- [ ] Update session-start hook with full context
- [ ] Add previous session summary
- [ ] Show other active agents
- [ ] Display work queue with recommendations
- [ ] Add conflict detection (multiple agents on same feature)

---

## Migration Path

### For Existing Projects

**No Breaking Changes:**
- All new fields have defaults
- Existing features continue working
- Features without `assigned_agent` are available to all agents

**Opt-In Adoption:**
```bash
# Start using claims (optional)
htmlgraph feature claim feat-123

# Start using handoff notes (optional)
htmlgraph session end session-001 --notes "Completed auth API"

# Start using capabilities (optional)
htmlgraph feature edit feat-123 --require ui browser
```

**Gradual Migration:**
1. Install updated HtmlGraph
2. Continue working as before (no changes needed)
3. Gradually adopt new features (claims, handoffs, capabilities)
4. Full multi-agent coordination when ready

---

## Benefits Summary

### For Single Agent
- ✅ Better work organization
- ✅ Clear next steps after resuming
- ✅ Explicit feature claiming (prevents accidental reruns)

### For Multi-Agent Teams
- ✅ Zero duplicate work
- ✅ Clear ownership and coordination
- ✅ Smart work distribution
- ✅ Smooth agent handoffs
- ✅ Cost optimization (right agent for right task)

### For Project Managers
- ✅ Visibility into who's working on what
- ✅ Progress tracking across agents
- ✅ Bottleneck identification
- ✅ Capability-based planning

---

## Examples

### Example 1: Single Project, Multiple Agents

**Scenario:** Web app with Claude (main), Codex (backend), Gemini (analysis)

```bash
# Claude starts UI work
claude> htmlgraph work queue
        → Recommended: feat-124-auth-ui (ui, browser, 2h)
claude> htmlgraph feature claim feat-124
claude> htmlgraph feature start feat-124

# Codex starts backend work
codex> htmlgraph work queue
       → Recommended: feat-125-api-endpoints (backend, python, 1h)
codex> htmlgraph feature claim feat-125
codex> htmlgraph feature start feat-125

# Gemini does analytics
gemini> htmlgraph work queue
        → Recommended: feat-130-analyze-performance (analysis, 30min)
gemini> htmlgraph feature claim feat-130
gemini> htmlgraph feature start feat-130
```

**Result:** 3 agents working in parallel, zero conflicts, all work tracked

---

### Example 2: Agent Handoff

**Scenario:** Claude starts, runs out of time, Gemini continues

```bash
# Claude's session
claude> htmlgraph feature claim feat-124
claude> # ... work for 2 hours, complete 3/5 steps ...
claude> htmlgraph session end session-001 \
          --notes "Completed auth API and login page. Profile page still needed." \
          --recommend feat-124 \
          --blocker "Need design approval for profile layout"

# Later: Gemini picks up
gemini> htmlgraph session start
        → Previous session (claude): "Completed auth API and login page. Profile page still needed."
        → Recommended: feat-124-auth-ui (3/5 steps complete)
        → Blocker: Need design approval for profile layout

gemini> # Check blocker status with user
gemini> htmlgraph feature claim feat-124  # Continues where Claude left off
gemini> # ... complete remaining 2 steps ...
gemini> htmlgraph feature complete feat-124
```

**Result:** Smooth handoff, zero context loss, explicit blocker communication

---

### Example 3: Smart Routing by Capability

**Scenario:** Mix of UI and backend work

```bash
# Create features with capability requirements
sdk.features.create("Auth UI").require_capabilities(["ui", "browser"]).save()
sdk.features.create("API Endpoints").require_capabilities(["backend", "python"]).save()
sdk.features.create("Fix typo").set_complexity("trivial").save()

# Claude Code (has browser)
claude> htmlgraph work next
        → feat-124: Auth UI (matches capabilities: ui, browser)

# Codex CLI (no browser)
codex> htmlgraph work next
       → feat-125: API Endpoints (matches capabilities: backend, python)

# Haiku Task (simple only)
haiku> htmlgraph work next
       → feat-126: Fix typo (matches complexity: trivial)
```

**Result:** Right work to right agent, automatic optimization

---

## Conclusion

HtmlGraph already has strong foundations for multi-agent collaboration:
- ✅ Agent-specific sessions
- ✅ Automatic attribution
- ✅ Session continuity
- ✅ Unified SDK

The proposed enhancements add:
- 🚀 Feature claiming (prevent conflicts)
- 🚀 Handoff context (smooth transitions)
- 🚀 Smart routing (capability-based)
- 🚀 Work queue (visibility & coordination)
- 🚀 Enhanced continuity (zero overhead)

**Next Steps:**
1. Review and approve enhancements
2. Implement Phase 1 (claims)
3. Test with real multi-agent workflows
4. Iterate based on feedback
5. Document best practices

This will make HtmlGraph the **best-in-class system for multi-agent AI collaboration**.
