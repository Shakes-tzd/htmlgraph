# Planning Workflow Integration

Complete guide to using HtmlGraph's integrated planning workflow with strategic analytics, spikes, tracks, and features.

## Overview

HtmlGraph provides an end-to-end planning workflow that connects:

1. **Strategic Analytics** → What should we work on?
2. **Planning Spikes** → How should we build it?
3. **Track Creation** → Organize multi-feature work
4. **Feature Implementation** → Execute the plan

## The Planning Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. STRATEGIC ANALYSIS                                       │
│  Get recommendations from dependency analytics               │
│  → /htmlgraph:recommend                                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  2. START PLANNING                                           │
│  Create spike or track depending on complexity               │
│  → /htmlgraph:plan "description"                            │
└────────────────┬────────────────────────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
      ▼                     ▼
┌──────────────┐    ┌──────────────┐
│  SPIKE PATH  │    │  TRACK PATH  │
│  (research)  │    │  (direct)    │
└──────┬───────┘    └──────┬───────┘
       │                   │
       ▼                   │
┌──────────────┐           │
│  3. RESEARCH │           │
│  Complete    │           │
│  spike steps │           │
└──────┬───────┘           │
       │                   │
       ▼                   │
┌──────────────┐           │
│  4. CREATE   │           │
│  TRACK       │◄──────────┘
│  from plan   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  5. CREATE   │
│  FEATURES    │
│  from track  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  6. IMPLEMENT│
│  Execute     │
│  features    │
└──────────────┘
```

## Detailed Workflow

### Step 1: Get Recommendations

Use strategic analytics to identify what to work on:

**Slash Command:**
```bash
/htmlgraph:recommend
```

**SDK:**
```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Get recommendations
recs = sdk.recommend_next_work(agent_count=3)
bottlenecks = sdk.find_bottlenecks(top_n=3)

# Review
for rec in recs:
    print(f"{rec['title']} (score: {rec['score']})")
    print(f"Reasons: {rec['reasons']}")
```

**Output:**
```
Top 3 Recommendations:
1. User Authentication (score: 10.0)
   - High priority
   - Directly unblocks 2 features
2. Database Migration (score: 8.5)
   - Critical bottleneck
   - Blocks 5 features
```

### Step 2A: Planning Spike (For Complex Work)

For non-trivial work, start with a research spike:

**Slash Command:**
```bash
/htmlgraph:plan "User authentication system"
```

**SDK:**
```python
plan = sdk.smart_plan(
    "User authentication system",
    create_spike=True,
    timebox_hours=4.0
)

print(f"Created spike: {plan['spike_id']}")
print(f"Context: {plan['project_context']}")
```

**What This Creates:**
- Spike with ID `spike-YYYYMMDD-HHMMSS`
- Standard planning steps:
  1. Research existing solutions
  2. Define requirements
  3. Design architecture
  4. Identify dependencies
  5. Create implementation plan
- Auto-started and assigned to you
- 4-hour timebox

### Step 2B: Direct Track (For Simple Work)

If you already know the approach, skip spike:

**Slash Command:**
```bash
/htmlgraph:plan "Fix login bug" --no-spike
```

**SDK:**
```python
track_info = sdk.smart_plan(
    "Fix login bug",
    create_spike=False
)
```

### Step 3: Complete Spike (Research Phase)

Work through the spike steps:

**SDK:**
```python
# Complete steps as you research
with sdk.spikes.edit("spike-123") as spike:
    spike.steps[0].completed = True  # Research done
    spike.steps[1].completed = True  # Requirements defined

# Document findings
with sdk.spikes.edit("spike-123") as spike:
    spike.findings = """
    Findings:
    - OAuth 2.0 with Google/GitHub providers
    - JWT for session management
    - Redis for token storage

    Decision: Use Auth0 for OAuth, custom JWT signing
    """
```

### Step 4: Create Track from Spike

Convert spike findings into a track with spec and plan:

**SDK:**
```python
track_info = sdk.create_track_from_plan(
    title="User Authentication System",
    description="OAuth 2.0 + JWT authentication",
    spike_id="spike-123",
    priority="high",
    requirements=[
        ("OAuth 2.0 integration with Google/GitHub", "must-have"),
        ("JWT token generation and validation", "must-have"),
        ("Token refresh mechanism", "must-have"),
        ("Password reset flow", "should-have")
    ],
    phases=[
        ("Phase 1: OAuth Setup", [
            "Configure OAuth providers (2h)",
            "Implement OAuth callback handler (2h)",
            "Add state verification (1h)"
        ]),
        ("Phase 2: JWT Integration", [
            "Create JWT signing service (2h)",
            "Add token refresh endpoint (1.5h)",
            "Implement middleware (2h)"
        ]),
        ("Phase 3: User Management", [
            "Create user profile endpoint (3h)",
            "Add password reset flow (4h)",
            "Write integration tests (3h)"
        ])
    ]
)

print(f"Track created: {track_info['track_id']}")
print(f"Has spec: {track_info['has_spec']}")
print(f"Has plan: {track_info['has_plan']}")
```

**What This Creates:**
- Track with ID `track-YYYYMMDD-HHMMSS`
- Spec file with requirements and acceptance criteria
- Plan file with phases and estimated tasks
- Reference to planning spike

### Step 5: Create Features from Track

Break down track phases into features:

**SDK:**
```python
track_id = "track-20251222-120000"

# Create features from each phase
oauth_feature = sdk.features.create("OAuth Integration") \
    .set_track(track_id) \
    .set_priority("high") \
    .add_steps([
        "Configure OAuth providers",
        "Implement OAuth callback handler",
        "Add state verification"
    ]) \
    .save()

jwt_feature = sdk.features.create("JWT Token Management") \
    .set_track(track_id) \
    .set_priority("high") \
    .add_steps([
        "Create JWT signing service",
        "Add token refresh endpoint",
        "Implement middleware"
    ]) \
    .save()

# Link dependencies if needed
with sdk.features.edit(jwt_feature.id) as f:
    f.add_edge(Edge(
        target_id=oauth_feature.id,
        relationship="depends_on"
    ))
```

### Step 6: Implement Features

Execute the plan:

**SDK:**
```python
# Start first feature
with sdk.features.edit(oauth_feature.id) as f:
    f.status = "in-progress"
    f.agent_assigned = "claude"

# Work on it, mark steps complete
with sdk.features.edit(oauth_feature.id) as f:
    f.steps[0].completed = True

# Complete when done
with sdk.features.edit(oauth_feature.id) as f:
    f.status = "done"
```

## Slash Commands Reference

### `/htmlgraph:recommend`

Get strategic recommendations on what to work on.

```bash
# Get top 3 recommendations
/htmlgraph:recommend

# Get more recommendations
/htmlgraph:recommend --count 5

# Skip bottleneck check
/htmlgraph:recommend --no-check-bottlenecks
```

### `/htmlgraph:plan`

Start planning new work (creates spike or track).

```bash
# Create planning spike (recommended)
/htmlgraph:plan "User authentication system"

# With custom timebox
/htmlgraph:plan "Real-time notifications" --timebox 3

# Create track directly (skip spike)
/htmlgraph:plan "Simple bug fix" --no-spike
```

### `/htmlgraph:spike`

Create a research/planning spike directly.

```bash
# Basic spike
/htmlgraph:spike "Research caching strategies"

# With context
/htmlgraph:spike "Investigate OAuth providers" --context "Need Google + GitHub support"

# With custom timebox
/htmlgraph:spike "Plan data migration" --timebox 2
```

## Complete Example

Here's a complete workflow from recommendation to implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# 1. Get recommendations
recs = sdk.recommend_next_work(agent_count=1)
top = recs[0]
print(f"Recommendation: {top['title']}")

# 2. Start planning spike
plan = sdk.smart_plan(
    top['title'],
    create_spike=True,
    timebox_hours=4.0
)
spike_id = plan['spike_id']

# 3. Complete spike research
# (agent does research, completes steps)
with sdk.spikes.edit(spike_id) as spike:
    spike.findings = "Use OAuth 2.0 + JWT"
    spike.decision = "Implement with Auth0"
    for step in spike.steps:
        step.completed = True

# 4. Create track from spike
track_info = sdk.create_track_from_plan(
    title=top['title'],
    description="Based on spike findings",
    spike_id=spike_id,
    requirements=[
        "OAuth integration",
        "JWT tokens",
        "Token refresh"
    ],
    phases=[
        ("Phase 1", ["Task 1 (2h)", "Task 2 (3h)"]),
        ("Phase 2", ["Task 3 (4h)", "Task 4 (2h)"])
    ]
)

# 5. Create features
for phase_name, tasks in [("Phase 1", ["Task 1", "Task 2"]), ("Phase 2", ["Task 3", "Task 4"])]:
    feature = sdk.features.create(phase_name) \
        .set_track(track_info['track_id']) \
        .add_steps(tasks) \
        .save()

# 6. Start implementation
first_feature = sdk.features.where(track=track_info['track_id'], status="todo")[0]
with sdk.features.edit(first_feature.id) as f:
    f.status = "in-progress"
```

## Best Practices

1. **Always check recommendations first** - Don't guess what's important
2. **Use spikes for complex work** - Timebox research before committing
3. **Document spike findings** - Capture decisions and reasoning
4. **Link everything** - Spike → Track → Features maintains context
5. **Track dependencies** - Use `depends_on` edges between features
6. **Complete steps incrementally** - Mark progress as you go

## Platform Availability

All commands work on:
- ✅ Claude Code (`/htmlgraph:command`)
- ✅ Codex (via slash commands)
- ✅ Gemini (via extension commands)

## See Also

- [Agent Strategic Planning](./AGENT_STRATEGIC_PLANNING.md) - Analytics API
- [Track Builder Guide](./TRACK_BUILDER_QUICK_START.md) - Creating tracks
- [SDK Documentation](./SDK_FOR_AI_AGENTS.md) - Complete SDK reference
- [Command Definitions](../packages/common/README.md) - DRY command system
