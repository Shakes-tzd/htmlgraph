---
name: strategic-planning
description: Use HtmlGraph analytics to make smart work prioritization decisions. Activate when recommending work, finding bottlenecks, assessing risks, or analyzing project impact.
---

# Strategic Planning Skill

## When to Activate This Skill

**Trigger keywords:**
- "what should I work on", "recommend", "prioritize"
- "bottleneck", "blocking", "stuck"
- "risk", "impact", "dependencies"
- "strategic", "roadmap", "plan"

**Trigger situations:**
- Starting a new session (what to work on?)
- Multiple tasks available (which is most important?)
- Progress seems slow (what's blocking us?)
- Planning major changes (what's the impact?)

---

## Core Principle: Data-Driven Decisions

HtmlGraph provides analytics that consider:
- **Dependencies** - What blocks/enables other work
- **Priority** - Business importance
- **Impact** - How many tasks are unlocked
- **Risk** - Circular deps, complexity
- **Parallelism** - What can run concurrently

---

## Quick Decision Framework

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# 1. What's blocking progress?
bottlenecks = sdk.find_bottlenecks(top_n=3)
if bottlenecks:
    print("🚧 BOTTLENECKS (fix these first):")
    for bn in bottlenecks:
        print(f"   {bn['id']}: {bn['title']}")
        print(f"      Blocks {bn['blocks_count']} downstream tasks")

# 2. What should I work on?
recs = sdk.recommend_next_work(agent_count=1)
if recs:
    best = recs[0]
    print(f"\n💡 RECOMMENDED: {best['title']}")
    print(f"   Score: {best['score']:.1f}")
    print(f"   Reasons: {', '.join(best['reasons'])}")

# 3. Can we parallelize?
parallel = sdk.get_parallel_work(max_agents=3)
print(f"\n⚡ Parallel capacity: {parallel['max_parallelism']} agents")
print(f"   Ready now: {len(parallel['ready_now'])} tasks")

# 4. Any risks to watch?
risks = sdk.assess_risks()
if risks['high_risk_count'] > 0:
    print(f"\n⚠️ {risks['high_risk_count']} high-risk items")
```

---

## Method Reference

### `sdk.find_bottlenecks(top_n=5)`

Find tasks that block the most downstream work.

```python
bottlenecks = sdk.find_bottlenecks(top_n=3)

# Returns list of:
{
    "id": "feat-001",
    "title": "Database Schema",
    "status": "todo",
    "priority": "high",
    "blocks_count": 5,      # How many tasks it blocks
    "blocks": ["feat-002", "feat-003", ...]  # Which tasks
}
```

**Use when:**
- Progress feels slow
- Many tasks are "blocked"
- Planning sprint priorities

---

### `sdk.recommend_next_work(agent_count=1)`

Get scored recommendations considering all factors.

```python
recs = sdk.recommend_next_work(agent_count=3)

# Returns list of:
{
    "id": "feat-001",
    "title": "Authentication",
    "score": 85.5,
    "reasons": [
        "high_priority",
        "unblocks_many",
        "no_dependencies"
    ],
    "priority": "high",
    "status": "todo",
    "blocks_count": 3
}
```

**Scoring factors:**
- Priority weight (critical=100, high=75, medium=50, low=25)
- Blocks count (×10 per blocked task)
- No dependencies bonus (+20)
- Bottleneck bonus (+30)

---

### `sdk.get_parallel_work(max_agents=5)`

Find tasks that can run concurrently.

```python
parallel = sdk.get_parallel_work(max_agents=5)

# Returns:
{
    "max_parallelism": 4,          # How many can run at once
    "ready_now": ["f1", "f2", ...], # Level 0 (no deps)
    "blocked": ["f3", "f4", ...],   # Waiting on deps
    "dependency_levels": [          # Topological layers
        ["f1", "f2"],  # Level 0: no deps
        ["f3"],        # Level 1: depends on Level 0
        ["f4", "f5"]   # Level 2: depends on Level 1
    ]
}
```

**Use when:**
- Multiple agents available
- Want to speed up delivery
- Planning parallel sprints

---

### `sdk.assess_risks()`

Check for project health issues.

```python
risks = sdk.assess_risks()

# Returns:
{
    "high_risk_count": 2,
    "circular_dependencies": [],     # Cycles in dep graph
    "single_points_of_failure": [    # Tasks blocking many
        {"id": "feat-001", "blocks": 5}
    ],
    "stale_in_progress": [           # Stuck tasks
        {"id": "feat-002", "days_stale": 7}
    ]
}
```

**Use when:**
- Before major releases
- Sprint planning
- Health checks

---

### `sdk.analyze_impact(feature_id)`

Understand what completing a task unlocks.

```python
impact = sdk.analyze_impact("feat-001")

# Returns:
{
    "unlocks_count": 3,
    "unlocks": ["feat-002", "feat-003", "feat-004"],
    "transitive_impact": 7,  # Total downstream tasks
    "critical_path": True    # On longest dependency chain
}
```

**Use when:**
- Deciding between tasks
- Explaining prioritization
- Finding high-leverage work

---

## Decision Patterns

### Pattern 1: Start of Session

```python
sdk = SDK(agent="claude")

# Quick context
info = sdk.get_session_start_info()

print("📊 Project Status:")
print(f"   In-progress: {info['status']['wip_count']}")
print(f"   Bottlenecks: {len(info['bottlenecks'])}")
print(f"   Parallel capacity: {info['parallel']['max_parallelism']}")

# What to work on
if info['recommendations']:
    rec = info['recommendations'][0]
    print(f"\n💡 Start with: {rec['title']}")
```

---

### Pattern 2: Something Is Blocked

```python
# Find what's causing the block
bottlenecks = sdk.find_bottlenecks(top_n=5)

for bn in bottlenecks:
    if bn['status'] == 'todo':
        print(f"🎯 Unblock by completing: {bn['title']}")
        print(f"   This will enable {bn['blocks_count']} tasks")
        break
```

---

### Pattern 3: Planning Parallel Work

```python
# Check if parallelization makes sense
parallel = sdk.get_parallel_work(max_agents=3)
risks = sdk.assess_risks()

if parallel['max_parallelism'] >= 2 and risks['high_risk_count'] == 0:
    print("✅ Safe to parallelize")
    print(f"   Dispatch up to {parallel['max_parallelism']} agents")

    # Get recommendations for each agent
    recs = sdk.recommend_next_work(agent_count=parallel['max_parallelism'])
    for i, rec in enumerate(recs):
        print(f"   Agent {i+1}: {rec['title']}")
else:
    print("⚠️ Sequential execution recommended")
    if risks['high_risk_count'] > 0:
        print(f"   Reason: {risks['high_risk_count']} high-risk items")
```

---

### Pattern 4: Impact Analysis

```python
# Compare two potential tasks
task_a = "feat-001"
task_b = "feat-002"

impact_a = sdk.analyze_impact(task_a)
impact_b = sdk.analyze_impact(task_b)

print(f"Task A unlocks: {impact_a['unlocks_count']} tasks")
print(f"Task B unlocks: {impact_b['unlocks_count']} tasks")

if impact_a['transitive_impact'] > impact_b['transitive_impact']:
    print(f"💡 Prioritize Task A (higher leverage)")
else:
    print(f"💡 Prioritize Task B (higher leverage)")
```

---

## Integration with Smart Plan

The `sdk.smart_plan()` method combines these analytics:

```python
plan = sdk.smart_plan(
    description="Real-time collaboration",
    create_spike=True,
    timebox_hours=4
)

# Returns context with:
# - bottlenecks_count
# - high_risk_count
# - parallel_capacity
# - Created spike for research
```

---

## Best Practices

### DO

1. **Check bottlenecks first** - High-leverage work
2. **Use recommendations** - Considers all factors
3. **Assess risks before big changes** - Avoid surprises
4. **Analyze impact** - Understand consequences
5. **Check parallel capacity** - Optimize throughput

### DON'T

1. **Ignore blocked tasks** - They signal bottlenecks
2. **Skip risk assessment** - Before major releases
3. **Parallelize without analysis** - May cause conflicts
4. **Work on low-impact tasks** - When bottlenecks exist

---

## Quick Reference

```python
from htmlgraph import SDK
sdk = SDK(agent="claude")

# What's blocking us?
sdk.find_bottlenecks(top_n=5)

# What should I do?
sdk.recommend_next_work(agent_count=1)

# Can we parallelize?
sdk.get_parallel_work(max_agents=5)

# Any risks?
sdk.assess_risks()

# What does this unlock?
sdk.analyze_impact("feat-id")

# All-in-one session start
sdk.get_session_start_info()

# Smart planning
sdk.smart_plan("description")
```
