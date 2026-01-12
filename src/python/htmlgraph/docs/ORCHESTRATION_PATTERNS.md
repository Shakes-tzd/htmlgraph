# HtmlGraph Orchestration Patterns

Guide to spawning agents, delegating tasks, and coordinating multi-agent workflows.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Agent Selection](#agent-selection)
3. [Task Delegation](#task-delegation)
4. [Result Tracking](#result-tracking)
5. [Cost Optimization](#cost-optimization)
6. [Advanced Patterns](#advanced-patterns)
7. [Troubleshooting](#troubleshooting)

---

## Core Concepts

### Agent Spawning

Dynamically spawn specialized agents for specific tasks:

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# Spawn different agents for different tasks
result = spawner.spawn_claude(
    prompt="Implement user authentication module",
    approval="auto"
)

result = spawner.spawn_gemini(
    prompt="Analyze codebase for performance issues"
    # model=None (default) - uses latest Gemini models including Gemini 3 preview
)

result = spawner.spawn_codex(
    prompt="Generate API endpoint implementation",
    sandbox="workspace-write"
)
```

### Task vs Agent

- **Agent**: An AI model spawned to complete work (Claude, Gemini, Codex, Copilot)
- **Task**: A delegated unit of work tracked in `.htmlgraph/task-delegations/`
- **Result**: The output of a completed task stored in HtmlGraph

---

## Agent Selection

### Spawn Methods

#### Claude Spawning

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

result = spawner.spawn_claude(
    prompt="Your task description",
    approval="auto",              # "auto", "manual", "never"
    model="claude-opus",          # Model to use
    max_thinking_budget=10000,    # Extended thinking budget
    output_json=False
)

if result.success:
    print(f"Output: {result.response}")
    print(f"Tokens: {result.tokens_used}")
else:
    print(f"Error: {result.error}")
```

**Claude Models:**
- `claude-opus` - Most capable, highest cost
- `claude-sonnet` - Balanced capability/cost
- `claude-haiku` - Fastest, lowest cost

---

#### Gemini Spawning

```python
result = spawner.spawn_gemini(
    prompt="Analyze this code for security issues",
    # model=None (default) - RECOMMENDED: uses latest Gemini models
    temperature=0.7,               # Creativity (0-1)
    output_json=False
)

if result.success:
    print(result.response)
else:
    print(f"Error: {result.error}")
```

**Gemini Model Selection:**
- `None` (default) - **RECOMMENDED**: CLI chooses best available model (gemini-2.5-flash-lite, gemini-3-flash-preview)
- Explicit model specification is DISCOURAGED - older models may fail with newer CLI versions

**Available models (if you must specify):**
- `gemini-2.5-flash-lite` - Fast, efficient
- `gemini-3-flash-preview` - Gemini 3 with enhanced capabilities
- `gemini-2.5-pro` - More capable, slower

**DEPRECATED models (may cause errors):**
- `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash` - Use `None` instead

---

#### Codex/GPT Spawning

```python
result = spawner.spawn_codex(
    prompt="Generate implementation for REST API",
    sandbox="workspace-write",    # Execution sandbox
    model="gpt-4-turbo",          # OpenAI model
    full_auto=False,              # Auto-execute code
    output_json=True
)

if result.success:
    print(result.response)
    # Access raw JSONL events
    for event in result.raw_output:
        if event.get("type") == "item.completed":
            print(f"Completed: {event['item']['type']}")
else:
    print(f"Error: {result.error}")
```

**Codex Sandbox Levels:**
- `read-only` - No write access (safe)
- `workspace-write` - Write to workspace only (recommended)
- `danger-full-access` - Unrestricted access (risky)

---

#### Copilot Spawning

```python
result = spawner.spawn_copilot(
    prompt="Refactor this Python function",
    model="gpt-4",
    output_json=False
)

if result.success:
    print(result.response)
else:
    print(f"Error: {result.error}")
```

---

### Model Selection Strategy

```python
from htmlgraph.orchestration import (
    select_model,
    TaskType,
    ComplexityLevel,
    BudgetMode
)

# Automatically select best model
model = select_model(
    task_type=TaskType.CODE_GENERATION,      # Task classification
    complexity=ComplexityLevel.HIGH,          # Complexity assessment
    budget_mode=BudgetMode.BALANCED           # Cost preference
)
# Returns: "gpt-4-turbo" (or other optimal model)

# Use selected model
if model == "gpt-4-turbo":
    result = spawner.spawn_codex(prompt="...", model=model)
elif model == "claude-opus":
    result = spawner.spawn_claude(prompt="...", model=model)
elif model.startswith("gemini"):
    result = spawner.spawn_gemini(prompt="...")  # model=None recommended
```

**Task Types:**
- `CODE_GENERATION` - Writing new code
- `CODE_REVIEW` - Analyzing code
- `DEBUGGING` - Finding/fixing bugs
- `DOCUMENTATION` - Writing docs
- `ARCHITECTURE` - Design decisions
- `TESTING` - Test generation
- `REFACTORING` - Code improvements

**Complexity Levels:**
- `LOW` - Simple, straightforward tasks
- `MEDIUM` - Moderate complexity
- `HIGH` - Complex, multi-step tasks

**Budget Modes:**
- `COST_OPTIMIZED` - Prefer cheaper models
- `BALANCED` - Mix cost/capability
- `QUALITY_FOCUSED` - Use best models

---

## Task Delegation

### Simple Delegation

```python
from htmlgraph import SDK, delegate_with_id

sdk = SDK(agent="orchestrator")

# Delegate single task
task_id = delegate_with_id(
    prompt="Implement JWT authentication middleware",
    agent="coder",
    task_id="task-auth-001"
)

print(f"Delegated task: {task_id}")
```

### Parallel Delegation

```python
from htmlgraph import parallel_delegate

# Delegate multiple tasks in parallel
tasks = [
    {
        "prompt": "Implement login endpoint",
        "agent": "coder",
        "task_id": "auth-login"
    },
    {
        "prompt": "Implement logout endpoint",
        "agent": "coder",
        "task_id": "auth-logout"
    },
    {
        "prompt": "Write authentication tests",
        "agent": "tester",
        "task_id": "auth-tests"
    },
    {
        "prompt": "Document authentication API",
        "agent": "writer",
        "task_id": "auth-docs"
    }
]

results = parallel_delegate(tasks)

# Process results as they complete
for task_id, result in results.items():
    print(f"{task_id}: {result['status']}")
    if result['status'] == 'completed':
        print(f"Output: {result['output']}")
```

---

### Delegation with Fallback

```python
# Try Codex, fallback to Claude if fails
result = spawner.spawn_codex(
    prompt="Generate API implementation",
    sandbox="workspace-write"
)

if not result.success:
    print(f"Codex failed: {result.error}")
    print("Falling back to Claude...")

    result = spawner.spawn_claude(
        prompt="Generate API implementation",
        approval="auto"
    )

print(f"Final result: {result.response}")
```

---

## Result Tracking

### Get Task Results

```python
from htmlgraph import get_results_by_task_id

# Check task status
results = get_results_by_task_id("task-auth-001")

if results:
    print(f"Status: {results['status']}")
    print(f"Output: {results['output']}")
    print(f"Tokens used: {results['tokens_used']}")
else:
    print("Task not found")
```

### Track Delegations in SDK

```python
sdk = SDK(agent="orchestrator")

# View all delegations
all_delegations = sdk.task_delegations.all()

# Query specific delegations
pending = sdk.task_delegations.where(status="pending")
completed = sdk.task_delegations.where(status="completed")
failed = sdk.task_delegations.where(status="failed")

# Get specific delegation
delegation = sdk.task_delegations.get("task-auth-001")
if delegation:
    print(f"Agent: {delegation.agent}")
    print(f"Status: {delegation.status}")
    print(f"Result: {delegation.result}")
```

### Delegation Results Structure

```python
{
    "task_id": "task-auth-001",
    "prompt": "Implement JWT authentication",
    "agent": "coder",
    "status": "completed",  # or "pending", "in-progress", "failed"
    "created_at": "2025-01-06T10:30:45.123Z",
    "started_at": "2025-01-06T10:31:00.123Z",
    "completed_at": "2025-01-06T10:45:00.123Z",
    "output": "Authentication module implemented...",
    "tokens_used": 8432,
    "model": "claude-opus",
    "cost": 0.45,
    "error": null  # If status is "failed"
}
```

---

## Cost Optimization

### Budget-Aware Selection

```python
# Select model based on budget
model = select_model(
    task_type=TaskType.CODE_GENERATION,
    complexity=ComplexityLevel.MEDIUM,
    budget_mode=BudgetMode.COST_OPTIMIZED
)
# Returns: "claude-haiku" (cheapest capable model)

# Spawn with selected model
if model == "claude-haiku":
    result = spawner.spawn_claude(prompt="...", model=model)
```

### Token Usage Tracking

```python
# Track tokens for cost calculation
delegations = sdk.task_delegations.all()

total_tokens = sum(d.tokens_used for d in delegations)
total_cost = sum(d.cost for d in delegations)

print(f"Total tokens: {total_tokens}")
print(f"Total cost: ${total_cost:.2f}")

# Cost by model
from collections import Counter
model_costs = Counter()
for d in delegations:
    model_costs[d.model] += d.cost

for model, cost in model_costs.items():
    print(f"{model}: ${cost:.2f}")
```

### Cost per Task Type

```python
# Analyze spending by task type
task_type_costs = {}

for delegation in sdk.task_delegations.all():
    task_type = delegation.properties.get("task_type", "unknown")
    if task_type not in task_type_costs:
        task_type_costs[task_type] = {
            "count": 0,
            "total_cost": 0,
            "avg_cost": 0
        }

    task_type_costs[task_type]["count"] += 1
    task_type_costs[task_type]["total_cost"] += delegation.cost
    task_type_costs[task_type]["avg_cost"] = (
        task_type_costs[task_type]["total_cost"] /
        task_type_costs[task_type]["count"]
    )

# Find most expensive task types
sorted_types = sorted(
    task_type_costs.items(),
    key=lambda x: x[1]["total_cost"],
    reverse=True
)

print("Cost by task type:")
for task_type, stats in sorted_types:
    print(f"  {task_type}: ${stats['total_cost']:.2f} " +
          f"({stats['count']} tasks, avg ${stats['avg_cost']:.2f})")
```

---

## Advanced Patterns

### Chain-of-Thought Delegation

Decompose complex tasks into subtasks:

```python
# Step 1: Analysis (cheap/fast)
analysis_result = spawner.spawn_gemini(
    prompt="Analyze the codebase structure"
    # model=None - uses latest Gemini models (Gemini 3 preview)
)

# Step 2: Design (more capable)
design_result = spawner.spawn_claude(
    prompt=f"""Based on this analysis:
{analysis_result.response}

Design the implementation approach.""",
    model="claude-opus"
)

# Step 3: Implementation (best model for code)
impl_result = spawner.spawn_codex(
    prompt=f"""Based on this design:
{design_result.response}

Implement the solution.""",
    sandbox="workspace-write"
)

print(f"Final implementation: {impl_result.response}")
```

### Error Recovery Pattern

```python
def spawn_with_fallback(primary_spawner_fn, fallback_spawner_fn):
    """Try primary spawner, fallback on failure."""

    result = primary_spawner_fn()

    if result.success:
        return result

    print(f"Primary failed: {result.error}")
    print("Attempting fallback...")

    fallback_result = fallback_spawner_fn()

    if fallback_result.success:
        return fallback_result

    print(f"Fallback also failed: {fallback_result.error}")
    raise RuntimeError("All spawners failed")

# Usage
result = spawn_with_fallback(
    primary_spawner_fn=lambda: spawner.spawn_codex(
        prompt="Generate API",
        sandbox="workspace-write"
    ),
    fallback_spawner_fn=lambda: spawner.spawn_claude(
        prompt="Generate API",
        approval="auto"
    )
)
```

### Feedback Loop Pattern

```python
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

def iterative_improvement(initial_prompt, improvement_cycles=3):
    """Iteratively improve output through feedback."""

    # Initial generation
    result = spawner.spawn_claude(
        prompt=initial_prompt,
        approval="auto"
    )

    output = result.response

    # Improvement cycles
    for i in range(improvement_cycles):
        # Get feedback
        feedback = spawner.spawn_claude(
            prompt=f"""Review this output and identify improvements:

{output}

Provide specific, actionable feedback.""",
            approval="auto"
        )

        # Apply improvements
        result = spawner.spawn_claude(
            prompt=f"""Based on this feedback:

{feedback.response}

Improve the output:

{output}""",
            approval="auto"
        )

        output = result.response

        # Track iteration
        sdk.task_delegations.create(
            task_id=f"improvement-cycle-{i}",
            feedback_iteration=i,
            output_tokens=result.tokens_used
        )

    return output

improved_code = iterative_improvement(
    "Generate a Python REST API",
    improvement_cycles=3
)
```

### Multi-Agent Consensus

```python
def get_consensus(prompt, num_agents=3):
    """Get consensus from multiple agents."""

    results = []

    # Get multiple perspectives
    results.append(("claude-opus", spawner.spawn_claude(
        prompt=prompt, model="claude-opus"
    )))

    results.append(("gemini", spawner.spawn_gemini(
        prompt=prompt  # model=None uses latest Gemini models
    )))

    results.append(("gpt-4-turbo", spawner.spawn_codex(
        prompt=prompt, model="gpt-4-turbo"
    )))

    # Synthesize consensus
    outputs = "\n".join(
        f"## {agent}\n{result.response}"
        for agent, result in results
        if result.success
    )

    consensus = spawner.spawn_claude(
        prompt=f"""Review these perspectives and provide consensus:

{outputs}

Synthesize the best insights.""",
        approval="auto"
    )

    return consensus.response

consensus_result = get_consensus(
    "What's the best approach for caching?"
)
```

---

## Troubleshooting

### Agent Spawn Fails

**Problem:** `spawn_claude()` returns `success=False`

**Solutions:**
1. Check API key is set
2. Verify network connectivity
3. Check rate limits
4. Try fallback spawner

```python
import os

# Verify API key
if not os.getenv("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not set")

# Check connectivity
import socket
try:
    socket.create_connection(("api.anthropic.com", 443), timeout=5)
except socket.error as e:
    print(f"Network error: {e}")

# Try with longer timeout
result = spawner.spawn_claude(
    prompt="...",
    timeout=60  # Longer timeout
)
```

---

### Task Delegation Not Tracked

**Problem:** Task doesn't appear in `sdk.task_delegations`

**Solutions:**
1. Use `delegate_with_id()` for tracking
2. Check `.htmlgraph/task-delegations/` directory exists
3. Verify task_id is unique

```python
# Create directory if missing
from pathlib import Path
Path(".htmlgraph/task-delegations").mkdir(exist_ok=True)

# Use proper delegation API
from htmlgraph import delegate_with_id

task_id = delegate_with_id(
    prompt="...",
    agent="coder",
    task_id="unique-task-id"  # Must be unique
)
```

---

### High Costs

**Problem:** Spending too much on agent spawning

**Solutions:**
1. Use cheaper models for simple tasks
2. Implement task decomposition
3. Track costs by agent/task type
4. Use budget mode: COST_OPTIMIZED

```python
# Use budget-aware selection
from htmlgraph.orchestration import (
    select_model,
    TaskType,
    ComplexityLevel,
    BudgetMode
)

model = select_model(
    task_type=TaskType.CODE_GENERATION,
    complexity=ComplexityLevel.LOW,
    budget_mode=BudgetMode.COST_OPTIMIZED
)
# Returns: cheaper model for simple tasks

# Track costs
delegations = sdk.task_delegations.where(status="completed")
total_cost = sum(d.cost for d in delegations)
avg_cost = total_cost / len(delegations) if delegations else 0
print(f"Average cost per task: ${avg_cost:.2f}")
```

---

## Best Practices

1. **Always use task IDs for tracking** - Enables result retrieval
2. **Implement fallback spawners** - Ensures reliability
3. **Monitor token usage** - Control costs
4. **Decompose complex tasks** - Improve accuracy
5. **Track delegation results** - Enable learning
6. **Use appropriate models** - Balance cost/quality
7. **Test with cheaper models first** - Validate logic
8. **Implement timeouts** - Prevent hanging
9. **Cache results** - Avoid duplicate work
10. **Monitor error rates** - Improve quality

---

## See Also

- [SDK API Reference](API_REFERENCE.md) - Complete SDK documentation
- [HTTP API Reference](HTTP_API.md) - REST endpoint documentation
- [Integration Guide](INTEGRATION_GUIDE.md) - Quick start examples
