# Session Hierarchies Guide

## What Are Session Hierarchies?

Session hierarchies capture the **parent-child relationships** created when you delegate work to subagents. Every time an orchestrator spawns a Task(), HtmlGraph automatically creates a session hierarchy that shows:

- **Who did the work** - Orchestrator agent, subagent types
- **When work happened** - Timeline of session creation and completion
- **What was delegated** - Prompts, task scope, constraints
- **How results link back** - Parent-child session relationships

This creates a complete **development trace** that survives agent crashes, context switches, and multi-day workflows.

---

## Why Session Hierarchies Matter

### Problem: Context Loss in Complex Workflows

Without session tracking:
```
Day 1 (Claude):
- Explore codebase
- Find 20 issues
- Document findings
- (Context lost when session ends)

Day 2 (Different agent):
- "What did Claude find yesterday?"
- (No record - have to re-explore)
```

### Solution: Session Hierarchies

With HtmlGraph tracking:
```
Orchestrator Session (Claude)
├── Child Session 1 (Subagent-Gemini): Explore codebase
│   └── Found 20 issues, documented in session summary
├── Child Session 2 (Subagent-Claude): Analyze issues
│   └── Prioritized issues by severity
└── Child Session 3 (Subagent-Test): Validate fixes
    └── All tests passed

Day 2: Pick up where you left off
├── Query: sdk.get_feature_sessions("feature-001")
├── View: All 4 sessions with full context
└── Continue: From the last session's findings
```

### Benefits

- ✅ **Complete lineage** - Full development history
- ✅ **Context recovery** - No information loss
- ✅ **Debugging aid** - Trace exactly what happened
- ✅ **Team visibility** - See other agents' work
- ✅ **Cost tracking** - Understand work distribution
- ✅ **Analytics** - Measure productivity per agent/session

---

## How Parent-Child Sessions Work

### Session Creation Flow

```
1. Orchestrator starts session
   └── session_id = "sess-abc123"
       agent = "orchestrator"
       status = "in-progress"

2. Orchestrator calls Task()
   └── HtmlGraph creates child session
       parent_session_id = "sess-abc123"
       subagent_type = "general-purpose"
       delegated_prompt = "..."
       status = "pending" → "in-progress"

3. Subagent executes work
   └── Child session captures all tool calls
       tools_used = ["Bash", "Read", "Edit", "Grep"]
       events = [...]  # All activities logged
       status = "in-progress"

4. Subagent completes
   └── Child session summary created
       result = "..."
       status = "completed"
       total_time = "2m 34s"

5. Results available to orchestrator
   └── Parent can query child:
       child_session = sdk.sessions.get("sess-child-xyz")
       print(child_session.result)
```

### Event Capture

HtmlGraph captures everything that happens in a session:

```json
{
  "session_id": "sess-child-xyz",
  "parent_session_id": "sess-abc123",
  "agent": "subagent-gemini",
  "status": "completed",
  "events": [
    {
      "type": "ToolUse",
      "tool": "Bash",
      "command": "uv run pytest tests/unit/",
      "result": "45 passed, 2 failed"
    },
    {
      "type": "ToolUse",
      "tool": "Grep",
      "pattern": "TODO:",
      "result": "Found 12 TODOs"
    }
  ],
  "summary": "Ran tests and found issues",
  "total_time_seconds": 154
}
```

---

## Viewing Session Hierarchies

### Using the Python SDK

#### Get Parent Session Info

```python
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

# Get current session
current_session = sdk.sessions.get(session_id)

# View children
print(f"Child sessions: {current_session.child_session_ids}")
# → ["sess-child-1", "sess-child-2", "sess-child-3"]

# Iterate over children
for child_id in current_session.child_session_ids:
    child = sdk.sessions.get(child_id)
    print(f"{child.agent}: {child.status} - {child.summary}")
```

#### Get Feature's All Sessions

```python
# Find all sessions that worked on a feature
sessions = sdk.get_feature_sessions("feature-001")

for session in sessions:
    print(f"Agent: {session.agent}")
    print(f"Status: {session.status}")
    print(f"Parent: {session.parent_session_id}")
    print(f"Duration: {session.total_time_seconds}s")
    print(f"Tools used: {session.tools_used}")
    print("---")
```

#### Navigate the Hierarchy

```python
# Start from a child session
child_session = sdk.sessions.get("sess-child-xyz")

# Get parent
parent = sdk.sessions.get(child_session.parent_session_id)
print(f"Parent agent: {parent.agent}")

# Get siblings
siblings = [
    sdk.sessions.get(sibling_id)
    for sibling_id in parent.child_session_ids
    if sibling_id != child_session.id
]
print(f"Siblings: {[s.agent for s in siblings]}")
```

### Using the Dashboard

The HtmlGraph dashboard has an **Orchestration** tab that visualizes hierarchies:

```
┌─────────────────────────────────────────┐
│ Orchestrator Session (Claude)           │
│ Duration: 5m 23s | Status: completed   │
├─────────────────────────────────────────┤
│                                         │
│  ├─ Child: Test Runner (Haiku)         │
│  │  ├─ Tests: 145 passed, 0 failed     │
│  │  └─ Time: 1m 45s                    │
│  │                                     │
│  ├─ Child: Code Analyzer (Gemini)      │
│  │  ├─ Issues found: 3                 │
│  │  └─ Time: 2m 10s                    │
│  │                                     │
│  └─ Child: Documenter (Haiku)          │
│     ├─ Files updated: 5                │
│     └─ Time: 1m 28s                    │
│                                         │
└─────────────────────────────────────────┘
```

Click on any session to see:
- Full event log
- Tool calls executed
- Results and output
- Timing breakdown
- Agent details

### Using the CLI

```bash
# List all sessions
uv run htmlgraph session list

# Get session details
uv run htmlgraph session show sess-abc123

# View session hierarchy
uv run htmlgraph session tree sess-abc123  # Show parent-child tree

# Find sessions for a feature
uv run htmlgraph session find-feature feature-001
```

---

## Understanding Session Events

### Event Types

Each session captures different event types:

#### ToolUse Event
```python
{
    "type": "ToolUse",
    "timestamp": "2025-01-10T15:30:45Z",
    "tool": "Bash",
    "input": "uv run pytest tests/",
    "result": "45 passed, 2 failed",
    "duration_ms": 3245
}
```

#### FileEdit Event
```python
{
    "type": "FileEdit",
    "timestamp": "2025-01-10T15:31:20Z",
    "file": "src/auth/login.py",
    "old_content": "...",
    "new_content": "...",
    "reason": "Fix token validation"
}
```

#### SessionStart Event
```python
{
    "type": "SessionStart",
    "timestamp": "2025-01-10T15:30:00Z",
    "agent": "subagent-gemini",
    "parent_session_id": "sess-abc123",
    "delegated_prompt": "Run tests and report failures"
}
```

#### SessionEnd Event
```python
{
    "type": "SessionEnd",
    "timestamp": "2025-01-10T15:34:30Z",
    "status": "completed",
    "result": "All tests passed",
    "total_events": 47,
    "tools_used": ["Bash", "Read", "Grep"]
}
```

### Analyzing Events

```python
# Get all events from a session
session = sdk.sessions.get("sess-child-xyz")

# Count tool usage
tool_counts = {}
for event in session.events:
    if event['type'] == 'ToolUse':
        tool = event['tool']
        tool_counts[tool] = tool_counts.get(tool, 0) + 1

print(f"Tools used: {tool_counts}")
# → {"Bash": 3, "Read": 5, "Grep": 4}

# Find long-running tools
slow_tools = [
    e for e in session.events
    if e['type'] == 'ToolUse' and e['duration_ms'] > 1000
]
print(f"Slow operations: {len(slow_tools)}")

# Extract all file edits
edits = [
    e for e in session.events
    if e['type'] == 'FileEdit'
]
print(f"Files modified: {len(edits)}")
for edit in edits:
    print(f"  - {edit['file']}")
```

---

## Debugging with Session Traces

### Scenario 1: "What did the subagent do?"

```python
# Find the delegated task result
parent_session = sdk.sessions.get("sess-abc123")

# Get first child
child_id = parent_session.child_session_ids[0]
child = sdk.sessions.get(child_id)

# See what it executed
print(f"Prompt: {child.delegated_prompt}")
print(f"Status: {child.status}")
print(f"Result: {child.result}")
print(f"Tool calls: {len([e for e in child.events if e['type'] == 'ToolUse'])}")

# If failed, see the error
if child.status == "failed":
    print(f"Error: {child.error_message}")
    print(f"Last event: {child.events[-1]}")
```

### Scenario 2: "Did the orchestrator make the right decision?"

```python
# Trace the orchestrator's decisions
orchestrator_session = sdk.sessions.get("sess-orchestrator-id")

# What was delegated?
for i, child_id in enumerate(orchestrator_session.child_session_ids):
    child = sdk.sessions.get(child_id)
    print(f"Task {i+1}: {child.delegated_prompt[:100]}...")
    print(f"Result: {child.status}")

# Was it cost-effective?
total_cost = sum(
    sdk.sessions.get(child_id).estimated_cost
    for child_id in orchestrator_session.child_session_ids
)
print(f"Total estimated cost: ${total_cost:.2f}")

# Did it complete on time?
print(f"Total time: {orchestrator_session.total_time_seconds}s")
```

### Scenario 3: "Why did feature X take so long?"

```python
# Get all sessions for a feature
sessions = sdk.get_feature_sessions("feature-001")

# Calculate total time
total_time = sum(s.total_time_seconds for s in sessions)
print(f"Total development time: {total_time}s")

# Break down by agent
time_by_agent = {}
for session in sessions:
    agent = session.agent
    time_by_agent[agent] = time_by_agent.get(agent, 0) + session.total_time_seconds

for agent, time in sorted(time_by_agent.items(), key=lambda x: -x[1]):
    print(f"{agent}: {time}s ({time/total_time*100:.0f}%)")

# Find bottlenecks
for session in sessions:
    slowest_tool = max(
        [e for e in session.events if e['type'] == 'ToolUse'],
        key=lambda e: e['duration_ms'],
        default=None
    )
    if slowest_tool and slowest_tool['duration_ms'] > 5000:
        print(f"Slow operation in {session.agent}: {slowest_tool['tool']} took {slowest_tool['duration_ms']}ms")
```

### Scenario 4: "Trace a specific issue across sessions"

```python
# Find all sessions that touched a file
target_file = "src/auth/login.py"
sessions = sdk.get_feature_sessions("feature-001")

file_edits_timeline = []
for session in sessions:
    for event in session.events:
        if event['type'] == 'FileEdit' and event['file'] == target_file:
            file_edits_timeline.append({
                'session': session.id,
                'agent': session.agent,
                'timestamp': event['timestamp'],
                'reason': event.get('reason', 'no reason given')
            })

# Sort by time
file_edits_timeline.sort(key=lambda x: x['timestamp'])

# Show evolution
print(f"Evolution of {target_file}:")
for edit in file_edits_timeline:
    print(f"  {edit['agent']} ({edit['session'][:8]}...): {edit['reason']}")
```

---

## Session Hierarchy Patterns

### Pattern 1: Orchestrator + Parallel Subagents

```
Orchestrator (Claude)
├── Subagent 1 (Gemini): Explore codebase
├── Subagent 2 (Copilot): Check GitHub issues
└── Subagent 3 (Claude): Analyze security

All run in parallel
Results: Available immediately after all complete
```

**Query pattern:**
```python
orchestrator = sdk.sessions.get("sess-orchestrator")
child_sessions = [
    sdk.sessions.get(child_id)
    for child_id in orchestrator.child_session_ids
]
# All children have completed
results = [child.result for child in child_sessions]
```

### Pattern 2: Sequential Handoff

```
Task 1 (Exploration)
└── Finds issues

Task 2 (Analysis - uses Task 1 results)
└── Prioritizes issues

Task 3 (Implementation - uses Task 2 results)
└── Fixes issues
```

**Query pattern:**
```python
# Task 1 completes first
task1_result = task1.result

# Task 2 uses Task 1 results
task2 = Task(prompt=f"Based on these issues: {task1_result}, prioritize them...")

# Task 3 uses Task 2 results
task3 = Task(prompt=f"Based on priority: {task2.result}, implement fixes...")
```

### Pattern 3: Hierarchical Delegation (Nested)

```
Orchestrator (Level 0)
└── Subagent 1 (Level 1): Complex task
    ├── Grandchild 1 (Level 2): Sub-task A
    ├── Grandchild 2 (Level 2): Sub-task B
    └── Grandchild 3 (Level 2): Sub-task C
```

**Query pattern:**
```python
# Get top-level orchestrator
orchestrator = sdk.sessions.get("sess-level0")

# Get level 1 subagent
subagent_l1 = sdk.sessions.get(orchestrator.child_session_ids[0])

# Get level 2 grandchildren
grandchildren = [
    sdk.sessions.get(child_id)
    for child_id in subagent_l1.child_session_ids
]

# Full lineage: orchestrator → subagent → grandchildren
```

---

## Best Practices

### 1. Use Meaningful Feature Linking

Link sessions to features so you can trace all work:

```python
from htmlgraph import Task

# Good: Feature context included in prompt
Task(
    subagent_type="general-purpose",
    prompt=f"""
    Feature: feature-001 - User Authentication

    Task: Implement login endpoint
    ...
    """
)

# Later: Query all work on feature
sessions = sdk.get_feature_sessions("feature-001")
```

### 2. Document Key Decisions

When delegating critical work, document the decision:

```python
sdk.spikes.create(
    title="Delegated auth refactoring to parallel subagents"
).set_findings("""
Decision: Why we delegated?
- 3 independent tasks (explore, implement, test)
- Can run in parallel (faster than sequential)
- Subagents: Gemini (exploration), Claude (implementation), Test-Runner (validation)

Expected cost: $0.12 vs $0.25 for sequential
Expected time: 2 min vs 6 min for sequential
""").save()
```

### 3. Monitor Session Health

Periodically review session patterns:

```python
# Session duration tracking
feature_sessions = sdk.get_feature_sessions("feature-001")

print("Session Performance:")
for session in feature_sessions:
    print(f"{session.agent}: {session.total_time_seconds}s ({session.status})")

# Find anomalies
slow_sessions = [
    s for s in feature_sessions
    if s.total_time_seconds > 300  # > 5 minutes
]

if slow_sessions:
    print("Slow sessions - consider optimization:")
    for s in slow_sessions:
        print(f"  {s.id}: {s.total_time_seconds}s")
```

### 4. Use Hierarchy for Cost Attribution

Track which agent spent resources:

```python
feature_sessions = sdk.get_feature_sessions("feature-001")

# Cost by agent
cost_by_agent = {}
for session in feature_sessions:
    agent = session.agent
    cost = session.estimated_cost
    cost_by_agent[agent] = cost_by_agent.get(agent, 0) + cost

# Total cost
total = sum(cost_by_agent.values())
print(f"Total feature cost: ${total:.2f}")
for agent, cost in cost_by_agent.items():
    pct = cost / total * 100
    print(f"  {agent}: ${cost:.2f} ({pct:.0f}%)")
```

### 5. Preserve Context in Handoffs

When handing off between agents, reference the session:

```python
# Finishing agent documents findings
current_session = sdk.sessions.get(session_id)

sdk.spikes.create(
    title=f"Handoff context from {current_session.agent}"
).set_findings(f"""
Session ID: {session_id}
Agent: {current_session.agent}
Status: {current_session.status}

Key findings:
{current_session.summary}

For next agent:
- See event log in session for details
- All tool outputs captured in session.events
- Feature context: feature-001
""").save()
```

---

## FAQ

**Q: Are parent-child sessions created automatically?**

A: Yes! HtmlGraph automatically creates child sessions when you call Task(). You don't need to manually create them.

**Q: Can I query sessions from completed features?**

A: Yes. Sessions are stored permanently in `.htmlgraph/sessions/`. You can query them anytime, even if the feature is complete.

**Q: What's the deepest hierarchy I should create?**

A: Usually 2-3 levels (orchestrator → subagent → grandchild). Beyond that, complexity outweighs benefits.

**Q: Do I need to know session IDs?**

A: No. Use `sdk.get_feature_sessions(feature_id)` to get all sessions for a feature without knowing IDs.

**Q: Can different agents see the same session hierarchy?**

A: Yes. Sessions are shared in `.htmlgraph/sessions/`. Any agent with access to the directory can see all sessions.

**Q: How long are session records kept?**

A: Indefinitely. Sessions are stored in the `.htmlgraph/` directory which should be committed to git. They're part of your project history.

**Q: Can I manually create a session hierarchy?**

A: Usually not needed. Use Task() for automatic creation. For manual needs, see the SDK reference.

---

## Related Reading

- [Delegation Guide](delegation.md) - How to write effective delegation prompts
- [AGENTS.md - Parent-Child Session Tracking](../AGENTS.md#parent-child-session-tracking) - Quick overview
- [AGENTS.md - Agent Handoff Context](../AGENTS.md#agent-handoff-context) - Handoff patterns
- [AGENTS.md - Orchestrator Mode](../AGENTS.md#orchestrator-mode) - Session tracking benefits
- `examples/session_analysis.py` - Complete session analysis examples
