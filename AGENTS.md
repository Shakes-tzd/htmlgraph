# HtmlGraph for AI Agents

**CRITICAL: AI agents must NEVER edit `.htmlgraph/` HTML files directly.**

Use the Python SDK, API, or CLI instead. This ensures all HTML is validated through Pydantic + justhtml.

---

## Quick Start (Python SDK)

```python
from htmlgraph import SDK

# Initialize (auto-discovers .htmlgraph directory)
sdk = SDK(agent="claude")

# Get project status
print(sdk.summary(max_items=10))

# Create a feature
feature = sdk.features.create("User Authentication") \
    .set_priority("high") \
    .set_description("Implement OAuth 2.0 login") \
    .add_steps([
        "Create login endpoint",
        "Add JWT middleware",
        "Write integration tests"
    ]) \
    .save()

print(f"Created: {feature.id}")

# Work on it
with sdk.features.edit(feature.id) as f:
    f.status = "in-progress"
    f.agent_assigned = "claude"
    f.steps[0].completed = True

# Query features
high_priority_todos = sdk.features.where(status="todo", priority="high")
for feat in high_priority_todos:
    print(f"- {feat.id}: {feat.title}")
```

---

## Core Principle: NEVER Edit HTML Directly

❌ **FORBIDDEN:**
```python
# NEVER DO THIS
with open(".htmlgraph/features/feature-123.html", "w") as f:
    f.write("<html>...</html>")

# NEVER DO THIS
Edit("/path/to/.htmlgraph/features/feature-123.html", ...)
```

✅ **REQUIRED - Use SDK/API/CLI:**
```python
# SDK (recommended)
with sdk.features.edit("feature-123") as f:
    f.status = "done"

# API
curl -X PATCH http://localhost:8080/api/features/feature-123 \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'

# CLI
uv run htmlgraph feature complete feature-123
```

**Why this matters:**
- Direct edits bypass Pydantic validation
- Bypass justhtml HTML generation
- Break SQLite index sync
- Can corrupt graph structure
- Skip event logging

---

## Python SDK (Recommended)

### Installation

```bash
pip install htmlgraph
# or
uv pip install htmlgraph
```

### Initialization

```python
from htmlgraph import SDK

# Auto-discover .htmlgraph directory
sdk = SDK(agent="claude")

# Or specify path
sdk = SDK(directory="/path/to/.htmlgraph", agent="claude")
```

### Get Oriented

```python
# Project summary
summary = sdk.summary(max_items=10)
print(summary)

# My workload
workload = sdk.my_work()
print(f"In progress: {workload['in_progress']}")
print(f"Completed: {workload['completed']}")
```

### Create Features

```python
# Fluent builder pattern
feature = sdk.features.create("Implement Dark Mode") \
    .set_priority("high") \
    .set_description("Add dark theme toggle to settings") \
    .add_steps([
        "Design color palette",
        "Create CSS variables",
        "Implement toggle component",
        "Add persistence (localStorage)",
        "Test across pages"
    ]) \
    .set_track("ui-improvements") \
    .save()

print(f"Created: {feature.id}")
```

### Work on Features

```python
# Context manager auto-saves on exit
with sdk.features.edit("feature-001") as f:
    f.status = "in-progress"
    f.agent_assigned = "claude"
    f.steps[0].completed = True
    f.steps[0].agent = "claude"

# Check if all steps done
with sdk.features.edit("feature-001") as f:
    all_done = all(s.completed for s in f.steps)
    if all_done:
        f.status = "done"
```

### Query Features

```python
# Declarative filtering
high_priority = sdk.features.where(status="todo", priority="high")
my_work = sdk.features.where(assigned_to="claude", status="in-progress")
track_features = sdk.features.where(track="auth-track")

# Get all
all_features = sdk.features.all()

# Get by ID
feature = sdk.features.get("feature-001")
```

### Batch Operations

```python
# Mark multiple as done
count = sdk.features.mark_done([
    "feature-001",
    "feature-002",
    "feature-003"
])
print(f"Marked {count} features as done")

# Assign multiple to agent
count = sdk.features.assign(
    ["feature-004", "feature-005"],
    agent="claude"
)
print(f"Assigned {count} features to claude")
```

### Get Next Task

```python
# Automatically find and claim next task
task = sdk.next_task(priority="high", auto_claim=True)

if task:
    print(f"Working on: {task.id} - {task.title}")

    # Work on it
    with sdk.features.edit(task.id) as f:
        for i, step in enumerate(f.steps):
            if not step.completed:
                # Do the work...
                step.completed = True
                step.agent = "claude"
                print(f"✓ Completed: {step.description}")
                break
else:
    print("No high-priority tasks available")
```

### Reload Data

```python
# Refresh from disk if files changed externally
sdk.reload()
```

---

## REST API (Alternative)

### Start Server

```bash
uv run htmlgraph serve
# Open http://localhost:8080
```

### Endpoints

#### Get All Features
```bash
curl http://localhost:8080/api/query?type=feature
```

#### Get Feature by ID
```bash
curl http://localhost:8080/api/features/feature-001
```

#### Create Feature
```bash
curl -X POST http://localhost:8080/api/features \
  -H "Content-Type: application/json" \
  -d '{
    "title": "User Authentication",
    "priority": "high",
    "status": "todo",
    "steps": [
      {"description": "Create login endpoint"},
      {"description": "Add JWT middleware"}
    ]
  }'
```

#### Update Feature
```bash
curl -X PATCH http://localhost:8080/api/features/feature-001 \
  -H "Content-Type: application/json" \
  -d '{"status": "in-progress"}'
```

#### Complete Step
```bash
curl -X PATCH http://localhost:8080/api/features/feature-001 \
  -H "Content-Type: application/json" \
  -d '{"complete_step": 0}'
```

**Step numbering is 0-based** (first step = 0, second step = 1, etc.)

---

## CLI (Alternative)

**IMPORTANT:** Always use `uv run` to ensure correct environment.

### Check Status
```bash
uv run htmlgraph status
uv run htmlgraph feature list
```

### Start Feature
```bash
uv run htmlgraph feature start <feature-id>
```

### Set Primary Feature
```bash
# When multiple features are active
uv run htmlgraph feature primary <feature-id>
```

### Complete Feature
```bash
uv run htmlgraph feature complete <feature-id>
```

### Server
```bash
uv run htmlgraph serve
```

---

## Decision Matrix: SDK vs API vs CLI

| Use Case | Recommended Interface |
|----------|----------------------|
| AI agent writing code | **SDK** (most ergonomic) |
| Scripting/automation | SDK or CLI |
| Manual testing | CLI or Dashboard |
| External integration | REST API |
| Debugging | CLI + Dashboard |

---

## Best Practices for AI Agents

### 1. Always Use SDK in Python Code

```python
# ✅ GOOD
from htmlgraph import SDK
sdk = SDK(agent="claude")
feature = sdk.features.create("Title").save()

# ❌ BAD - Don't use low-level API directly
from htmlgraph import HtmlGraph, Node
graph = HtmlGraph(".htmlgraph/features")
node = Node(id="...", title="...")
graph.add(node)
```

### 2. Use Context Managers (Auto-Save)

```python
# ✅ GOOD - Auto-saves on exit
with sdk.features.edit("feature-001") as f:
    f.status = "done"

# ❌ BAD - Easy to forget to save
feature = sdk.features.get("feature-001")
feature.status = "done"
# Forgot to call sdk._graph.update(feature)!
```

### 3. Use Declarative Queries

```python
# ✅ GOOD
todos = sdk.features.where(status="todo", priority="high")

# ❌ BAD - Manual filtering
todos = [
    f for f in sdk.features.all()
    if f.status == "todo" and f.priority == "high"
]
```

### 4. Use Batch Operations

```python
# ✅ GOOD - Single operation
sdk.features.mark_done(["feat-001", "feat-002", "feat-003"])

# ❌ BAD - Multiple operations
for id in ["feat-001", "feat-002", "feat-003"]:
    with sdk.features.edit(id) as f:
        f.status = "done"
```

### 5. Check Status Before Working

```python
# Get orientation
print(sdk.summary())

# Check your workload
workload = sdk.my_work()
if workload['in_progress'] > 5:
    print("Already at capacity!")
```

### 6. Document Decisions

```python
# If significant architectural decision
# Document in feature content
with sdk.features.edit("feature-001") as f:
    f.content += """
    <h3>Decision: Use JWT instead of sessions</h3>
    <p>Rationale: Stateless, easier to scale horizontally</p>
    """
```

---

## Complete Workflow Example

```python
from htmlgraph import SDK

def ai_agent_workflow():
    """Realistic AI agent workflow."""

    # 1. Initialize
    sdk = SDK(agent="claude")

    # 2. Get oriented
    print("=== Project Summary ===")
    print(sdk.summary(max_items=10))

    # 3. Check workload
    workload = sdk.my_work()
    print(f"\nMy Workload:")
    print(f"  In progress: {workload['in_progress']}")
    print(f"  Completed: {workload['completed']}")

    if workload['in_progress'] > 5:
        print("\n⚠️  Already at capacity!")
        return

    # 4. Get next task
    task = sdk.next_task(priority="high", auto_claim=True)

    if not task:
        print("\n✅ No high-priority tasks available")
        return

    print(f"\n=== Working on: {task.title} ===")

    # 5. Work on task
    with sdk.features.edit(task.id) as feature:
        print(f"\nSteps:")
        for i, step in enumerate(feature.steps):
            if step.completed:
                print(f"  ✅ {step.description}")
            else:
                print(f"  ⏳ {step.description}")

                # Do the work here...
                # (implementation details)

                # Mark step complete
                step.completed = True
                step.agent = "claude"
                print(f"  ✓ Completed: {step.description}")
                break

        # Check if all done
        all_done = all(s.completed for s in feature.steps)
        if all_done:
            feature.status = "done"
            print(f"\n✅ Feature complete: {feature.id}")

if __name__ == "__main__":
    ai_agent_workflow()
```

---

## API Reference

### SDK Class

```python
class SDK:
    def __init__(
        self,
        directory: Path | str | None = None,  # Auto-discovered if None
        agent: str | None = None
    )

    def reload(self) -> None
    def summary(self, max_items: int = 10) -> str
    def my_work(self) -> dict[str, Any]
    def next_task(
        self,
        priority: str | None = None,
        auto_claim: bool = True
    ) -> Node | None

    # Collections
    features: FeatureCollection
```

### FeatureCollection

```python
class FeatureCollection:
    def create(self, title: str, **kwargs) -> FeatureBuilder
    def get(self, feature_id: str) -> Node | None
    def edit(self, feature_id: str) -> ContextManager[Node]
    def where(
        self,
        status: str | None = None,
        priority: str | None = None,
        track: str | None = None,
        assigned_to: str | None = None
    ) -> list[Node]
    def all(self) -> list[Node]
    def mark_done(self, feature_ids: list[str]) -> int
    def assign(self, feature_ids: list[str], agent: str) -> int
```

### FeatureBuilder

```python
class FeatureBuilder:
    def set_priority(self, priority: Literal["low", "medium", "high", "critical"]) -> FeatureBuilder
    def set_status(self, status: str) -> FeatureBuilder
    def add_step(self, description: str) -> FeatureBuilder
    def add_steps(self, descriptions: list[str]) -> FeatureBuilder
    def set_track(self, track_id: str) -> FeatureBuilder
    def set_description(self, description: str) -> FeatureBuilder
    def blocks(self, feature_id: str) -> FeatureBuilder
    def blocked_by(self, feature_id: str) -> FeatureBuilder
    def save(self) -> Node
```

---

## Examples

See `examples/sdk_demo.py` for complete demonstration:

```bash
uv run python examples/sdk_demo.py
```

---

## Troubleshooting

### SDK not finding .htmlgraph directory

```python
# Specify path explicitly
sdk = SDK(directory="/path/to/project/.htmlgraph", agent="claude")
```

### Feature not found

```python
# Reload from disk
sdk.reload()
feature = sdk.features.get("feature-001")
```

### Changes not persisting

```python
# Make sure you're using context manager
with sdk.features.edit("feature-001") as f:
    f.status = "done"  # Auto-saves on exit

# Or manually save
feature = sdk.features.get("feature-001")
feature.status = "done"
sdk._graph.update(feature)  # Manual save
```

---

## Documentation

- **SDK Guide**: `docs/SDK_FOR_AI_AGENTS.md`
- **API Reference**: `docs/api-reference.md`
- **Quickstart**: `docs/quickstart.md`
- **Dashboard**: Run `uv run htmlgraph serve` and open http://localhost:8080

---

## Deployment & Release

### Using the Deployment Script

HtmlGraph includes `scripts/deploy-all.sh` to automate the entire release process:

```bash
# Run with version number
./scripts/deploy-all.sh 0.7.1

# Or auto-detect from pyproject.toml
./scripts/deploy-all.sh
```

**What it does (7 steps):**
1. **Git Push** - Pushes commits and tags to origin/main
2. **Build Package** - Creates wheel and source distributions with `uv build`
3. **Publish to PyPI** - Uploads to PyPI using token from .env
4. **Local Install** - Installs latest version locally with pip
5. **Update Claude Plugin** - Runs `claude plugin update htmlgraph`
6. **Update Gemini Extension** - Updates version in gemini-extension.json
7. **Update Codex Skill** - Checks for Codex and updates if present

**Prerequisites:**

Set your PyPI token in `.env` file:
```bash
PyPI_API_TOKEN=pypi-YOUR_TOKEN_HERE
```

**Complete Release Workflow:**

```bash
# 1. Update version numbers
# Edit: pyproject.toml, __init__.py, plugin.json, gemini-extension.json

# 2. Commit version bump
git add pyproject.toml src/python/htmlgraph/__init__.py \
  packages/claude-plugin/.claude-plugin/plugin.json \
  packages/gemini-extension/gemini-extension.json
git commit -m "chore: bump version to 0.7.1"

# 3. Create git tag
git tag v0.7.1
git push origin main --tags

# 4. Run deployment script
./scripts/deploy-all.sh 0.7.1
```

**Manual Steps (if script fails):**

```bash
# Build
uv build

# Publish to PyPI
source .env
uv publish dist/htmlgraph-0.7.1* --token "$PyPI_API_TOKEN"

# Install locally
pip install --upgrade htmlgraph==0.7.1

# Update plugins manually
claude plugin update htmlgraph
```

**Verify Deployment:**

```bash
# Check PyPI
open https://pypi.org/project/htmlgraph/

# Verify local install
python -c "import htmlgraph; print(htmlgraph.__version__)"

# Test Claude plugin
claude plugin list | grep htmlgraph
```

---

## Related Files

- `src/python/htmlgraph/sdk.py` - SDK implementation
- `src/python/htmlgraph/graph.py` - Low-level graph operations
- `src/python/htmlgraph/agents.py` - Agent interface (wrapped by SDK)
- `examples/sdk_demo.py` - Complete examples
- `scripts/deploy-all.sh` - Deployment automation script
