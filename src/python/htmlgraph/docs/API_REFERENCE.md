# HtmlGraph SDK API Reference

Complete API documentation for HtmlGraph SDK with examples for every method.

## Table of Contents

1. [Initialization](#initialization)
2. [Collections](#collections)
3. [Builders](#builders)
4. [Queries](#queries)
5. [Analytics](#analytics)
6. [Orchestration](#orchestration)
7. [Error Handling](#error-handling)

## Initialization

### SDK Constructor

```python
from htmlgraph import SDK

# Basic initialization (auto-discovers .htmlgraph directory)
sdk = SDK(agent="claude")

# With explicit directory
sdk = SDK(agent="claude", directory="/path/to/.htmlgraph")

# With parent session tracking (for nested contexts)
sdk = SDK(agent="claude", parent_session="sess-12345")
```

**Parameters:**
- `agent` (str, REQUIRED): Agent identifier for work attribution. Examples: "claude", "explorer", "coder", "tester"
- `directory` (Path | str, optional): Path to .htmlgraph directory. Auto-discovered if not provided.
- `parent_session` (str, optional): Parent session ID for nested contexts

**Raises:**
- `ValueError`: If agent cannot be determined and not provided

**Auto-Discovery Logic:**
1. Checks current directory for `.htmlgraph/`
2. Recursively checks parent directories
3. Raises error if not found

---

## Collections

All collections provide the same base interface for CRUD operations and querying.

### Collection Methods

#### `create(title: str, **kwargs) -> Builder`

Create a new work item with fluent builder interface.

```python
# Simple creation
feature = sdk.features.create("User Authentication")

# With builder pattern
feature = sdk.features.create("User Auth") \
    .set_priority("high") \
    .add_steps(["Design schema", "Implement", "Test"]) \
    .set_status("in-progress") \
    .save()

# Create with custom properties
spike = sdk.spikes.create(
    "Investigate caching strategies",
    investigation_type="technical",
    estimated_hours=8
)
```

**Parameters:**
- `title` (str): Work item title
- `**kwargs`: Additional properties

**Returns:**
- Builder instance with fluent interface (supports method chaining)

**Raises:**
- `ValidationError`: If title is empty

---

#### `get(node_id: str) -> Node | None`

Retrieve a single work item by ID.

```python
feature = sdk.features.get("feat-12345")
if feature:
    print(f"Title: {feature.title}")
    print(f"Status: {feature.status}")
else:
    print("Feature not found")
```

**Parameters:**
- `node_id` (str): Unique node identifier

**Returns:**
- `Node` object if found, `None` if not found

**Error Behavior:**
- Returns `None` (safe for conditional checks)

---

#### `all() -> list[Node]`

Retrieve all work items in collection.

```python
all_features = sdk.features.all()
print(f"Total features: {len(all_features)}")

# Safe iteration even if empty
for feature in all_features:
    print(feature.title)
```

**Returns:**
- List of Node objects (empty list if none found)

**Error Behavior:**
- Returns empty list on error (safe iteration)

---

#### `where(**filters) -> list[Node]`

Query work items with filter conditions.

```python
# Single filter
todo_features = sdk.features.where(status="todo")

# Multiple filters (AND condition)
high_priority_bugs = sdk.bugs.where(
    status="todo",
    priority="high"
)

# Complex queries
in_progress = sdk.features.where(
    status="in-progress",
    priority__in=["high", "critical"]
)
```

**Parameters:**
- `**filters`: Key-value pairs for filtering
  - Supports nested attributes: `priority__in=["high", "critical"]`
  - Multiple filters combine with AND logic

**Returns:**
- List of matching Node objects (empty list if no matches)

**Common Filters:**
- `status`: "todo", "in-progress", "blocked", "done"
- `priority`: "low", "medium", "high", "critical"
- `agent`: Agent identifier
- `track`: Track identifier

---

#### `edit(node_id: str) -> ContextManager[Node]`

Edit a work item using context manager.

```python
# Update status
with sdk.features.edit("feat-12345") as feature:
    feature.status = "done"
    feature.priority = "low"
    # Auto-saves on exit

# Modify steps
with sdk.features.edit("feat-12345") as feature:
    if feature.steps:
        feature.steps[0].completed = True
```

**Parameters:**
- `node_id` (str): Node to edit

**Returns:**
- Context manager yielding Node object
- Auto-saves on exit

**Raises:**
- `NodeNotFoundError`: If node not found

**Error Behavior:**
- Raises exception (must handle with try/except)

---

#### `mark_done(node_ids: list[str]) -> dict`

Mark multiple work items as done.

```python
result = sdk.features.mark_done([
    "feat-001",
    "feat-002",
    "feat-003"
])

print(f"Completed: {result['success_count']}")
if result['failed_ids']:
    print(f"Failed: {result['failed_ids']}")
    print(f"Reasons: {result['warnings']}")
```

**Parameters:**
- `node_ids` (list[str]): IDs to mark as done

**Returns:**
- Dict with:
  - `success_count` (int): Number successfully updated
  - `failed_ids` (list[str]): IDs that failed
  - `warnings` (list[str]): Reason for each failure

**Error Behavior:**
- Returns results dict with partial success details

---

#### `batch_update(updates: dict[str, dict]) -> dict`

Update multiple work items in batch.

```python
updates = {
    "feat-001": {"status": "done", "priority": "low"},
    "feat-002": {"status": "in-progress"},
    "feat-003": {"status": "blocked"}
}

result = sdk.features.batch_update(updates)
print(f"Updated: {result['success_count']}")
```

**Parameters:**
- `updates` (dict): Mapping of node_id to update dict

**Returns:**
- Dict with success_count, failed_ids, warnings

---

#### `delete(node_id: str) -> bool`

Delete a work item.

```python
if sdk.features.delete("feat-12345"):
    print("Deleted successfully")
else:
    print("Feature not found")
```

**Parameters:**
- `node_id` (str): Node to delete

**Returns:**
- `True` if deleted, `False` if not found

---

#### `assign(node_ids: list[str], agent: str) -> dict`

Assign work items to an agent.

```python
result = sdk.features.assign(
    ["feat-001", "feat-002"],
    agent="claude"
)
```

**Parameters:**
- `node_ids` (list[str]): IDs to assign
- `agent` (str): Agent identifier

**Returns:**
- Results dict with success_count, failed_ids

---

### Available Collections

**Work Item Collections** (all support builder pattern):
- `sdk.features` - Feature work items
- `sdk.bugs` - Bug reports
- `sdk.spikes` - Investigation/research spikes
- `sdk.chores` - Maintenance tasks
- `sdk.epics` - Large bodies of work
- `sdk.phases` - Project phases

**Support Collections**:
- `sdk.sessions` - Agent sessions
- `sdk.tracks` - Work tracks
- `sdk.agents` - Agent information
- `sdk.todos` - Persistent task tracking (mirrors TodoWrite API)
- `sdk.patterns` - Workflow patterns (optimal/anti-pattern)
- `sdk.insights` - Session health insights
- `sdk.metrics` - Aggregated time-series metrics
- `sdk.task_delegations` - Task delegation observability

---

## Builders

Builders provide fluent interface for creating and configuring work items.

### Base Builder Methods

All builders inherit from `BaseBuilder` and support these methods:

#### `set_priority(priority: str) -> Builder`

```python
feature = sdk.features.create("Feature") \
    .set_priority("high")
```

**Values:** "low", "medium", "high", "critical"

---

#### `set_status(status: str) -> Builder`

```python
feature = sdk.features.create("Feature") \
    .set_status("in-progress")
```

**Values:** "todo", "in-progress", "blocked", "done"

---

#### `add_step(description: str) -> Builder`

```python
feature = sdk.features.create("Feature") \
    .add_step("Design the schema") \
    .add_step("Implement API")
```

---

#### `add_steps(descriptions: list[str]) -> Builder`

```python
feature = sdk.features.create("Feature") \
    .add_steps([
        "Design the schema",
        "Implement API",
        "Add tests",
        "Deploy"
    ])
```

---

#### `set_description(description: str) -> Builder`

```python
feature = sdk.features.create("Feature") \
    .set_description("This feature adds user authentication")
```

---

#### `blocks(node_id: str) -> Builder`

```python
feature = sdk.features.create("Feature") \
    .blocks("feat-999")  # This blocks feat-999
```

---

#### `blocked_by(node_id: str) -> Builder`

```python
feature = sdk.features.create("Feature") \
    .blocked_by("feat-111")  # This is blocked by feat-111
```

---

#### `save() -> Node`

```python
feature = sdk.features.create("Feature") \
    .set_priority("high") \
    .add_steps(["Step 1", "Step 2"]) \
    .save()

print(f"Created: {feature.id}")
```

**Returns:**
- Saved Node object with generated ID

**Raises:**
- `ValidationError`: If required fields missing

---

### Feature-Specific Builder Methods

```python
feature = sdk.features.create("User Authentication") \
    .set_track("auth") \
    .set_priority("high") \
    .add_steps([...]) \
    .save()
```

---

### Spike-Specific Builder Methods

```python
spike = sdk.spikes.create("Investigate caching strategies") \
    .set_spike_type("technical") \
    .set_estimated_hours(8) \
    .save()
```

---

### Complete Builder Example

```python
feature = sdk.features.create("User Authentication System") \
    .set_priority("high") \
    .set_status("todo") \
    .set_description(
        "Implement JWT-based authentication with OAuth2 support"
    ) \
    .add_steps([
        "Design authentication schema",
        "Implement JWT middleware",
        "Add OAuth2 integration",
        "Write comprehensive tests",
        "Deploy to staging",
        "Perform security audit",
        "Deploy to production"
    ]) \
    .blocks("feat-post-auth-flow") \
    .blocked_by("feat-database-setup") \
    .save()

print(f"Feature {feature.id} created successfully")
```

---

## Queries

### Query Builder

For complex queries beyond basic filtering:

```python
from htmlgraph import HtmlGraph, QueryBuilder

graph = HtmlGraph("features/")

# Query with multiple conditions
results = graph.query_builder() \
    .where("status", "todo") \
    .and_("priority").in_(["high", "critical"]) \
    .and_("completion").lt(50) \
    .execute()

# Text search
results = graph.query_builder() \
    .where("title").contains("auth") \
    .or_("title").contains("login") \
    .execute()

# Numeric comparisons
results = graph.query_builder() \
    .where("estimated_hours").gte(8) \
    .and_("estimated_hours").lte(40) \
    .execute()
```

### QueryBuilder Operators

**Comparison Operators:**
- `.eq(value)` - Equal
- `.ne(value)` - Not equal
- `.gt(value)` - Greater than
- `.gte(value)` - Greater than or equal
- `.lt(value)` - Less than
- `.lte(value)` - Less than or equal
- `.in_(values)` - In list
- `.not_in(values)` - Not in list
- `.between(a, b)` - Between (inclusive)

**String Operators:**
- `.contains(text)` - String contains
- `.starts_with(text)` - Starts with
- `.ends_with(text)` - Ends with
- `.matches(regex)` - Regex match

**Null Operators:**
- `.is_null()` - Is null
- `.is_not_null()` - Is not null

**Logical Operators:**
- `.and_(field)` - AND condition
- `.or_(field)` - OR condition
- `.not_()` - NOT condition

---

## Analytics

### Work Type Analytics

```python
# Get distribution of work types
distribution = sdk.analytics.get_work_type_distribution()
# Returns: {"feature": 25, "spike": 8, "bug": 12, "chore": 5}

# Get spike to feature ratio
ratio = sdk.analytics.get_spike_to_feature_ratio()
# Returns: 0.32 (1 spike per 3 features, indicating good investigation)

# Get maintenance burden
burden = sdk.analytics.get_maintenance_burden()
# Returns: 0.17 (chores are 17% of total work)
```

---

### Dependency Analytics

```python
# Find blocking tasks
bottlenecks = sdk.dep_analytics.find_bottlenecks(top_n=5)
# Returns: [
#     {
#         "node_id": "feat-001",
#         "title": "Database Schema",
#         "blocking_count": 8,
#         "blocker_ids": [...]
#     }
# ]

# Find parallelizable work
parallel = sdk.dep_analytics.get_parallel_work(max_agents=3)
# Returns: {
#     "agent_1": ["feat-001", "feat-002"],
#     "agent_2": ["feat-003", "feat-004"],
#     "agent_3": ["feat-005"]
# }

# Get recommendations
recommendations = sdk.dep_analytics.recommend_next_tasks(agent_count=1)

# Assess dependency risk
risk = sdk.dep_analytics.assess_dependency_risk()
# Returns: {"has_cycles": false, "risk_level": "low"}

# Impact analysis
impact = sdk.dep_analytics.impact_analysis("feat-001")
# Returns: {"unlocked_nodes": [...], "impact_count": 5}
```

---

### Context Analytics

```python
# Get context usage metrics
usage = sdk.context.get_context_usage()
# Returns: {
#     "current_tokens": 45000,
#     "max_tokens": 100000,
#     "usage_percent": 45
# }

# Get efficiency score
efficiency = sdk.context.get_context_efficiency()
# Returns: 0.85 (efficiency score 0-1)
```

---

### System Prompts

```python
# Get active system prompt (project override OR plugin default)
active = sdk.system_prompts.get_active()

# Get plugin default
default = sdk.system_prompts.get_default()

# Get project override if exists
project = sdk.system_prompts.get_project()

# Create project-level override
sdk.system_prompts.create("""
# Custom System Prompt

Your custom guidance here...
""")

# Validate prompt token count
stats = sdk.system_prompts.validate()
# Returns: {
#     "tokens": 1250,
#     "max_tokens": 2000,
#     "is_valid": true
# }

# Get prompt statistics
stats = sdk.system_prompts.get_stats()

# Delete project override (fallback to default)
sdk.system_prompts.delete()
```

---

## Orchestration

### Task Delegation

```python
from htmlgraph import SDK, delegate_with_id, get_results_by_task_id

sdk = SDK(agent="orchestrator")

# Delegate task to specific agent
task_id = delegate_with_id(
    prompt="Implement authentication module",
    agent="coder",
    task_id="task-auth-001"
)

# Check results later
results = get_results_by_task_id("task-auth-001")
if results:
    print(f"Result: {results['output']}")
    print(f"Status: {results['status']}")
```

---

### Parallel Delegation

```python
from htmlgraph import parallel_delegate

# Delegate multiple tasks in parallel
results = parallel_delegate([
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
    }
])

# Aggregate results
for task_id, result in results.items():
    print(f"{task_id}: {result['status']}")
```

---

### Model Selection

```python
from htmlgraph.orchestration import select_model, TaskType, ComplexityLevel

# Select best model for task
model = select_model(
    task_type=TaskType.CODE_GENERATION,
    complexity=ComplexityLevel.HIGH,
    budget_mode="balanced"  # or "cost-optimized"
)
# Returns: "gpt-4-turbo" or "claude-opus" based on heuristics
```

---

## Error Handling

### Error Classes

```python
from htmlgraph import (
    HtmlGraphError,
    NodeNotFoundError,
    SessionNotFoundError,
    ClaimConflictError,
    ValidationError
)
```

---

### Error Handling Patterns

**Pattern 1: Safe Lookup**

```python
feature = sdk.features.get("feat-12345")
if feature:
    print(feature.title)
else:
    print("Not found - safe to ignore")
```

**Pattern 2: Safe Query**

```python
# Returns empty list - safe iteration
high_priority = sdk.features.where(status="todo", priority="high")
for item in high_priority:
    process(item)
```

**Pattern 3: Edit with Exception Handling**

```python
try:
    with sdk.features.edit("feat-12345") as feature:
        feature.status = "done"
except NodeNotFoundError:
    print("Feature not found")
```

**Pattern 4: Batch with Results**

```python
result = sdk.features.mark_done(["feat-1", "feat-2", "missing"])
if result['failed_ids']:
    print(f"Failed: {result['failed_ids']}")
    for warning in result['warnings']:
        print(f"  Reason: {warning}")
```

---

### Common Error Scenarios

| Error | Cause | Solution |
|-------|-------|----------|
| `NodeNotFoundError` | Node ID doesn't exist | Check `.get()` result or catch exception |
| `ValidationError` | Invalid input (e.g., empty title) | Validate input before creating |
| `ClaimConflictError` | Another agent claimed the item | Release claim or work with different item |
| `SessionNotFoundError` | Parent session doesn't exist | Check parent_session parameter |

---

## Complete Example

```python
from htmlgraph import SDK
from htmlgraph.exceptions import NodeNotFoundError

# Initialize
sdk = SDK(agent="claude")

# Create feature with builder
feature = sdk.features.create("User Authentication System") \
    .set_priority("high") \
    .add_steps([
        "Design schema",
        "Implement API",
        "Add tests"
    ]) \
    .save()

print(f"Created feature: {feature.id}")

# Query work
high_priority_todos = sdk.features.where(
    status="todo",
    priority="high"
)

# Update feature
try:
    with sdk.features.edit(feature.id) as f:
        f.status = "in-progress"
        f.priority = "critical"
except NodeNotFoundError:
    print("Feature was deleted")

# Batch operations
result = sdk.features.mark_done([feature.id])
print(f"Marked done: {result['success_count']}")

# Analytics
distribution = sdk.analytics.get_work_type_distribution()
bottlenecks = sdk.dep_analytics.find_bottlenecks(top_n=3)

print(f"Work distribution: {distribution}")
print(f"Bottlenecks: {bottlenecks}")
```

---

## Version

Current API version: 0.24.1

Compatible with: HtmlGraph 0.20.0+

---

## See Also

- [HTTP API Reference](HTTP_API.md) - REST endpoint documentation
- [Orchestration Patterns](ORCHESTRATION_PATTERNS.md) - Multi-agent coordination
- [Integration Guide](INTEGRATION_GUIDE.md) - Quick start and examples
