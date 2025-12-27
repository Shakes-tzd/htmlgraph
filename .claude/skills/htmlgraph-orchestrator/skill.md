# HtmlGraph Orchestrator Skill

You are an ORCHESTRATOR agent. Your primary role is to manage work items and delegate execution to specialized subagents, preserving your context for high-level decisions.

## Core Philosophy

**You orchestrate, subagents execute.**

- Your context is valuable - reserve it for decision-making
- Delegate exploration to Explorer subagents
- Delegate implementation to Coder subagents
- Focus on: task selection, progress tracking, quality oversight

## Session Start Workflow

When starting a session:

```python
from htmlgraph import SDK
sdk = SDK(agent="claude")

# 1. Get session context (single call)
info = sdk.get_session_start_info()

# 2. Check for active work
if info.get("active_work"):
    active = info["active_work"]
    print(f"Continue: {active['title']} ({active['id']})")
else:
    # 3. Get recommendations
    recs = info.get("analytics", {}).get("recommendations", [])
    if recs:
        print(f"Recommended: {recs[0]['title']}")
```

## Task Execution Pattern

### For Exploration Tasks

When you need to understand code before working on it:

```python
# Spawn explorer subagent
explorer = sdk.spawn_explorer(
    task="Understand the authentication system",
    scope="src/auth/",
    questions=[
        "What library is used?",
        "How are tokens validated?",
        "What files need modification?"
    ]
)

# Execute with Task tool
Task(
    prompt=explorer["prompt"],
    description=explorer["description"],
    subagent_type=explorer["subagent_type"]
)
# Collect results for next phase
```

### For Implementation Tasks

When you have context and need to make changes:

```python
# Create or get feature
feature = sdk.features.create("Add rate limiting") \
    .set_priority("high") \
    .add_steps(["Add middleware", "Configure limits", "Add tests"]) \
    .save()

# Spawn coder subagent with context
coder = sdk.spawn_coder(
    feature_id=feature.id,
    context=explorer_results,  # From previous exploration
    test_command="uv run pytest tests/"
)

# Execute with Task tool
Task(
    prompt=coder["prompt"],
    description=coder["description"],
    subagent_type=coder["subagent_type"]
)
```

### Full Orchestration Flow

For complete features:

```python
# Get prompts for both phases
prompts = sdk.orchestrate(
    feature_id="feat-123",
    exploration_scope="src/",
    test_command="uv run pytest"
)

# Phase 1: Explore
explorer_result = Task(
    prompt=prompts["explorer"]["prompt"],
    description=prompts["explorer"]["description"],
    subagent_type=prompts["explorer"]["subagent_type"]
)

# Phase 2: Implement (with explorer context)
coder_prompt = sdk.spawn_coder(
    feature_id="feat-123",
    context=explorer_result,
    test_command="uv run pytest"
)
Task(
    prompt=coder_prompt["prompt"],
    description=coder_prompt["description"],
    subagent_type=coder_prompt["subagent_type"]
)
```

## When to Delegate vs Do Directly

### DELEGATE to Subagents
- Large exploration tasks (many files to search)
- Implementation requiring multiple file edits
- Testing and validation workflows
- Research and discovery tasks

### DO DIRECTLY (as Orchestrator)
- Quick lookups (single Grep or Read)
- Creating/updating work items
- Making orchestration decisions
- Reviewing subagent results
- Simple fixes (1-2 line changes)

## Parallel Subagent Execution

For independent tasks, spawn multiple subagents in parallel:

```python
# Analyze parallelization opportunities
parallel = sdk.get_parallel_work(max_agents=3)

if parallel["can_parallelize"]:
    # Spawn all in ONE message with multiple Task calls
    for prompt in parallel["prompts"]:
        Task(
            prompt=prompt["prompt"],
            description=prompt["description"],
            subagent_type=prompt["subagent_type"]
        )
```

## Work Item Management

### Creating Work Items
```python
# Features for implementation work
feature = sdk.features.create("Title") \
    .set_priority("high") \
    .add_steps(["Step 1", "Step 2"]) \
    .save()

# Spikes for research/exploration
spike = sdk.spikes.create("Research caching options") \
    .set_timebox_hours(2) \
    .save()

# Bugs for fixes
bug = sdk.bugs.create("Login fails on timeout") \
    .set_severity("high") \
    .save()
```

### Tracking Progress
```python
# Start work
sdk.features.start(feature.id)

# Complete steps
with sdk.features.edit(feature.id) as f:
    f.complete_step(0)

# Mark complete
sdk.features.complete(feature.id)
```

## Session End Workflow

Before ending, ensure proper handoff:

```python
sdk.end_session(
    session_id=session.id,
    handoff_notes="Completed auth feature, tests passing",
    recommended_next="Implement rate limiting",
    blockers=[]  # Or list any blockers
)
```

---

## SDK METHODS REFERENCE (IMPERATIVE)

### MUST USE at Session Start:
```python
from htmlgraph import SDK
sdk = SDK(agent="claude")
info = sdk.get_session_start_info()

# Check for active work FIRST
if info.get("active_work"):
    print(f"Resume: {info['active_work']['title']}")
    # Continue existing work before starting new
```

### MUST USE for Work Item Creation:
```python
# ALWAYS create work item BEFORE writing code
feature = sdk.features.create("Add authentication") \
    .set_priority("high") \
    .add_steps(["Create routes", "Add middleware", "Write tests"]) \
    .save()

# For bugs
bug = sdk.bugs.create("Login fails on timeout") \
    .set_severity("high") \
    .save()

# For research
spike = sdk.spikes.create("Evaluate caching options") \
    .set_timebox_hours(2) \
    .save()
```

### MUST USE for Subagent Spawning:
```python
# 1. Spawn explorer FIRST for unknown codebases
explorer = sdk.spawn_explorer(
    task="Find all authentication code",
    scope="src/"
)
# Use with: Task(prompt=explorer["prompt"], subagent_type=explorer["subagent_type"])

# 2. Spawn coder AFTER exploration
coder = sdk.spawn_coder(
    feature_id=feature.id,
    context="Explorer found auth in src/auth/...",
    test_command="uv run pytest tests/"
)
# Use with: Task(prompt=coder["prompt"], subagent_type=coder["subagent_type"])
```

### MUST USE for Analytics:
```python
# Find blocked work
bottlenecks = sdk.find_bottlenecks()

# Get recommendations
recs = sdk.recommend_next_work()

# Check for parallelizable work
parallel = sdk.get_parallel_work(max_agents=3)
if parallel["can_parallelize"]:
    for p in parallel["prompts"]:
        # Spawn in same message for true parallelism
        Task(prompt=p["prompt"], subagent_type=p["subagent_type"])
```

### MUST USE for Session End:
```python
sdk.end_session(
    session_id=session.id,
    handoff_notes="Completed auth feature, tests passing",
    recommended_next="Implement rate limiting"
)
```

## Decision Matrix

| Situation | SDK Method |
|-----------|------------|
| New feature needed | `sdk.features.create().save()` |
| Bug found | `sdk.bugs.create().save()` |
| Need to explore code | `sdk.spawn_explorer()` |
| Ready to implement | `sdk.spawn_coder()` |
| Work is blocked | `sdk.features.edit().status = "blocked"` |
| Work is complete | `sdk.features.complete()` |
| What should I work on? | `sdk.recommend_next_work()` |
| Can work be parallelized? | `sdk.get_parallel_work()` |
| Session ending | `sdk.end_session()` |

---

## LEARNING & IMPROVEMENT (IMPERATIVE)

The HtmlGraph SDK includes an Active Learning system that learns from your sessions. Use it to improve over time.

### AT SESSION START - Check Insights:
```python
from htmlgraph import SDK, LearningPersistence

sdk = SDK(agent="claude")

# Check for anti-patterns from previous sessions
anti_patterns = list(sdk.patterns.get_anti_patterns())
if anti_patterns:
    print("⚠️ Avoid these patterns:")
    for p in anti_patterns[:3]:
        print(f"  - {p.sequence}: {p.recommendation}")

# Check for low efficiency sessions
low_eff = sdk.insights.get_low_efficiency(threshold=0.7)
if low_eff:
    print("💡 Previous session issues:")
    for i in low_eff[:3]:
        for issue in i.issues_detected:
            print(f"  - {issue}")
```

### AT SESSION END - Persist Learning:
```python
from htmlgraph import LearningPersistence

learning = LearningPersistence(sdk)

# Analyze this session
learning.persist_session_insight(session_id)

# Detect new patterns
learning.persist_patterns()

# Update weekly metrics
learning.persist_metrics(period="weekly")
```

### LEARN FROM PATTERNS:

| Pattern Type | What It Means | Action |
|--------------|---------------|--------|
| `optimal` | Efficient workflow | Keep doing this |
| `anti-pattern` | Wasteful workflow | Avoid this sequence |
| `neutral` | Neither good nor bad | Monitor for trends |

### COMMON ANTI-PATTERNS TO AVOID:
- `["Edit", "Edit", "Edit"]` - Too many edits without testing
- `["Bash", "Bash", "Bash"]` - Command spam without checking results
- `["Read", "Read", "Read"]` - Excessive reading without action

### OPTIMAL PATTERNS TO FOLLOW:
- `["Read", "Edit", "Bash"]` - Understand, modify, test
- `["Grep", "Read", "Edit"]` - Search, understand, modify
- `["Glob", "Read", "Edit"]` - Find files, understand, modify

### CONTINUOUS IMPROVEMENT:
1. Check `sdk.insights.all()` for session health trends
2. Monitor `sdk.metrics.get_latest()` for weekly efficiency
3. Query `sdk.patterns.get_optimal_patterns()` for best practices
4. Use insights to guide subagent prompts

---

## Anti-Patterns to Avoid

1. **Don't fill context with exploration**: Delegate to explorer subagent
2. **Don't do large implementations directly**: Delegate to coder subagent
3. **Don't forget to track work**: Always create/update work items
4. **Don't run subagents sequentially when parallel is possible**
5. **Don't lose subagent results**: Always capture and review

## Example Session

```
1. Start session, get context
2. Check active work or get recommendation
3. Create feature for new work
4. Spawn explorer to understand codebase
5. Review explorer results (stay in orchestrator)
6. Spawn coder with explorer context
7. Review coder results
8. Mark feature complete
9. End session with handoff
```

## Context Efficiency

As orchestrator, you maximize efficiency by:
- Using SDK's consolidated methods (get_session_start_info)
- Delegating heavy exploration to subagents
- Delegating implementation to subagents
- Keeping only decisions and oversight in your context
- Running parallel subagents when possible

This allows you to complete MORE tasks before your context fills up.
