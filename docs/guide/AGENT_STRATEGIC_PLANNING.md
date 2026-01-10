# Agent Strategic Planning Guide

This guide shows AI agents how to use HtmlGraph's strategic planning and dependency analytics features to make smart decisions about what to work on.

## Quick Start

```python
from htmlgraph import SDK

# Initialize with your agent ID
sdk = SDK(agent="claude")

# Get smart recommendations
recs = sdk.recommend_next_work(agent_count=1)
if recs:
    best = recs[0]
    print(f"Work on: {best['title']}")
    print(f"Why: {', '.join(best['reasons'])}")
```

## Available Features

### 1. Find Bottlenecks 🚧

**What it does**: Identifies tasks blocking the most downstream work

**When to use**:
- At the start of a work session
- When planning sprints
- When coordinating multiple agents

**Example**:
```python
bottlenecks = sdk.find_bottlenecks(top_n=5)

for bn in bottlenecks:
    print(f"{bn['title']} blocks {bn['blocks_count']} tasks")
    print(f"Impact score: {bn['impact_score']}")
    print(f"Priority: {bn['priority']}")
```

**Returns**: List of dicts with:
- `id`: Task ID
- `title`: Task title
- `status`: Current status
- `priority`: Priority level
- `blocks_count`: Number of tasks blocked
- `impact_score`: Weighted impact metric
- `blocked_tasks`: List of task IDs being blocked

### 2. Get Parallel Work ⚡

**What it does**: Finds tasks that can be worked on simultaneously by multiple agents

**When to use**:
- When coordinating multiple agents
- When planning team assignments
- When looking for independent work streams

**Example**:
```python
parallel = sdk.get_parallel_work(max_agents=5)

print(f"Can work on {parallel['max_parallelism']} tasks at once")
print(f"Ready now: {parallel['ready_now']}")
```

**Returns**: Dict with:
- `max_parallelism`: Maximum tasks that can run in parallel
- `ready_now`: List of task IDs ready to start immediately
- `total_ready`: Count of ready tasks
- `level_count`: Number of dependency levels
- `next_level`: Tasks in the next dependency level

### 3. Recommend Next Work 💡

**What it does**: Provides smart recommendations on what to work on next, considering priority, dependencies, and impact

**When to use**:
- When deciding what task to pick up
- When you need to prioritize between multiple options
- When coordinating work across agents

**Example**:
```python
recs = sdk.recommend_next_work(agent_count=3)

for rec in recs:
    print(f"{rec['title']} (score: {rec['score']})")
    print(f"Priority: {rec['priority']}")
    print(f"Reasons: {rec['reasons']}")
    print(f"Unlocks: {rec['unlocks_count']} tasks")
```

**Returns**: List of dicts with:
- `id`: Task ID
- `title`: Task title
- `priority`: Priority level
- `score`: Recommendation score (higher = better)
- `reasons`: List of reasons why this task is recommended
- `estimated_hours`: Estimated effort (if available)
- `unlocks_count`: Number of tasks this will unblock
- `unlocks`: List of task IDs that will be unblocked

### 4. Assess Risks ⚠️

**What it does**: Identifies dependency-related risks like single points of failure, circular dependencies, and orphaned tasks

**When to use**:
- During project health checks
- Before starting a sprint
- When dependencies feel complex

**Example**:
```python
risks = sdk.assess_risks()

if risks['high_risk_count'] > 0:
    print(f"Warning: {risks['high_risk_count']} high-risk tasks")
    for task in risks['high_risk_tasks']:
        print(f"  {task['title']}: {task['risk_factors']}")

if risks['circular_dependencies']:
    print("Circular dependencies detected!")
```

**Returns**: Dict with:
- `high_risk_count`: Number of high-risk tasks
- `high_risk_tasks`: List of dicts with:
  - `id`: Task ID
  - `title`: Task title
  - `risk_score`: Risk metric
  - `risk_factors`: List of risk descriptions
- `circular_dependencies`: List of dependency cycles
- `orphaned_count`: Number of orphaned tasks
- `orphaned_tasks`: List of orphaned task IDs
- `recommendations`: List of actionable recommendations

### 5. Analyze Impact 📊

**What it does**: Shows what downstream work will be unblocked by completing a specific task

**When to use**:
- Before committing to a large task
- When deciding between tasks with similar priority
- When communicating value of work

**Example**:
```python
impact = sdk.analyze_impact("feature-001")

print(f"Direct dependents: {impact['direct_dependents']}")
print(f"Total impact: {impact['total_impact']} tasks")
print(f"Unlocks {impact['completion_impact']:.1f}% of remaining work")
```

**Returns**: Dict with:
- `node_id`: Task ID analyzed
- `direct_dependents`: Number of tasks directly depending on this
- `total_impact`: Total downstream tasks affected
- `completion_impact`: Percentage of total work this unlocks
- `unlocks_count`: Count of affected tasks
- `affected_tasks`: List of affected task IDs

## Decision Flow for AI Agents

Here's a recommended decision flow for AI agents:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# 1. Check for bottlenecks
bottlenecks = sdk.find_bottlenecks(top_n=3)
if bottlenecks:
    print(f"⚠️  {len(bottlenecks)} bottlenecks found")
    print("Consider: Focus on unblocking high-impact work")

# 2. Get smart recommendations
recs = sdk.recommend_next_work(agent_count=1)
if recs:
    top = recs[0]
    print(f"\n💡 RECOMMENDED: {top['title']}")
    print(f"   Score: {top['score']:.1f}")
    print(f"   Reasons: {', '.join(top['reasons'][:2])}")

    # 3. Analyze impact of recommended task
    impact = sdk.analyze_impact(top['id'])
    print(f"   Impact: Unlocks {impact['unlocks_count']} tasks")

    # Decision: Work on this task
    print(f"\n✅ DECISION: Starting work on {top['id']}")

# 4. Check for parallel work (if coordinating with other agents)
parallel = sdk.get_parallel_work(max_agents=3)
if parallel['total_ready'] > 1:
    print(f"\n⚡ {parallel['total_ready']} tasks can be done in parallel")
    print(f"   Other agents can work on: {parallel['ready_now'][1:]}")

# 5. Assess risks (periodic health check)
risks = sdk.assess_risks()
if risks['high_risk_count'] > 0:
    print(f"\n⚠️  Health check: {risks['high_risk_count']} high-risk items")
```

## Integration with AgentInterface

All these methods are also available through `AgentInterface` for lower-level control:

```python
from htmlgraph.agents import AgentInterface

agent = AgentInterface("features/", agent_id="claude")

# Same methods available
bottlenecks = agent.find_bottlenecks(top_n=5)
parallel = agent.get_parallel_work(max_agents=3)
recs = agent.recommend_next_work(agent_count=1)
risks = agent.assess_risks()
impact = agent.analyze_impact("feature-001")
```

## Advanced: Direct Access to Analytics Engine

For advanced use cases, you can access the underlying analytics engine:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Access the full DependencyAnalytics class
analytics = sdk.dep_analytics

# All methods return Pydantic models (more detail, less convenience)
bottlenecks = analytics.find_bottlenecks(top_n=5, min_impact=1.0)
parallel = analytics.find_parallelizable_work(status="todo")
recs = analytics.recommend_next_tasks(agent_count=3, lookahead=5)
risk = analytics.assess_dependency_risk(spof_threshold=2)
impact = analytics.impact_analysis("feature-001")

# Pydantic models have all fields, not just agent-friendly subset
for bn in bottlenecks:
    print(bn.id, bn.title, bn.transitive_blocking, bn.weighted_impact)
    print(bn.blocked_nodes)  # Full list, not limited to 5
```

## Best Practices

1. **Start with recommendations**: Use `recommend_next_work()` as your starting point
2. **Check bottlenecks regularly**: At least once per session or sprint
3. **Assess risks periodically**: Before major milestones
4. **Analyze impact for big decisions**: When choosing between high-effort tasks
5. **Use parallel work for coordination**: When multiple agents are available

## Performance Notes

- All analytics queries are O(N) or O(N log N) where N = number of nodes
- Results are computed on-demand (no caching)
- For large graphs (1000+ nodes), consider:
  - Limiting `top_n` parameters
  - Filtering by status before analysis
  - Using the lower-level API for fine-grained control

## Examples

See `demo_agent_planning.py` for a complete working example.

## See Also

- [SDK Documentation](./SDK_FOR_AI_AGENTS.md)
- [Agent Interface](./AGENTS.md)
- [Dependency Analytics API](./API_REFERENCE.md#dependency-analytics)
