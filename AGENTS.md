# HtmlGraph for AI Agents

**CRITICAL: AI agents must NEVER edit `.htmlgraph/` HTML files directly.**

Use the Python SDK, API, or CLI instead. This ensures all HTML is validated through Pydantic + justhtml.

---

## 🔄 NOTE: Dogfooding in Action

**IF YOU'RE WORKING ON THE HTMLGRAPH PROJECT ITSELF:**

This project uses HtmlGraph to track its own development. The `.htmlgraph/` directory in this repo is:
- ✅ **Real usage** - Not a demo, actual development tracking
- ✅ **Live examples** - Learn from these patterns for YOUR projects
- ✅ **Our roadmap** - Features we're building for HtmlGraph

**See [CLAUDE.md#dogfooding-context](./CLAUDE.md#dogfooding-context) for full details** on:
- What's general-purpose vs project-specific
- Workflows we should package for all users
- How to distinguish HtmlGraph development from HtmlGraph usage

**IF YOU'RE USING HTMLGRAPH IN YOUR OWN PROJECT:**

Ignore the HtmlGraph-specific features in `.htmlgraph/`. Focus on:
- ✅ SDK patterns shown below
- ✅ Workflow examples (they work for ANY project)
- ✅ Best practices (universal)

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

## Agent Handoff Context

Handoff enables smooth context transfer between agents when a task requires different expertise.

### Marking a Task for Handoff

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Complete work and hand off
with sdk.features.edit("feature-001") as feature:
    feature.steps[0].completed = True

# Trigger handoff with context
manager = sdk._session_manager
manager.create_handoff(
    feature_id="feature-001",
    reason="blocked_on_testing",
    notes="Implementation complete. Needs comprehensive test coverage.",
    agent="claude"
)

# Feature now shows handoff context for next agent
feature = sdk.features.get("feature-001")
print(feature.previous_agent)  # "claude"
print(feature.handoff_reason)  # "blocked_on_testing"
print(feature.handoff_notes)   # Full context
```

### Receiving a Handoff

When claiming a handoff task, the previous agent's context is available:

```python
sdk = SDK(agent="bob")

# Get handoff task
feature = sdk.features.get("feature-001")

# View handoff context
context = feature.to_context()
# Output:
# # feature-001: Implement API
# Status: in-progress | Priority: high
# ⚠️  Handoff from: claude
# Reason: blocked_on_testing
# Notes: Implementation complete. Needs comprehensive test coverage.
# Progress: 1/3 steps

# Mark as received and continue
with sdk.features.edit("feature-001") as f:
    f.agent_assigned = "bob"
    f.steps[1].completed = True
```

### Handoff Best Practices

1. **Provide context**: Always include `notes` with relevant decisions/blockers
2. **Mark progress**: Complete steps before handoff so next agent knows what's done
3. **Set clear reason**: Use structured reasons: `blocked_on_*`, `needs_*`, `ready_for_*`
4. **Preserve history**: Handoff chain shows full development history

---

## Agent Routing & Capabilities

Capability-based routing automatically assigns tasks to agents with matching skills.

### Register Agent Capabilities

```python
from htmlgraph.routing import AgentCapabilityRegistry

registry = AgentCapabilityRegistry()

# Register agents with their capabilities
registry.register_agent("alice", ["python", "backend", "databases"])
registry.register_agent("bob", ["python", "frontend", "ui"])
registry.register_agent("charlie", ["testing", "quality-assurance"])
```

### Define Task Requirements

```python
from htmlgraph.models import Node

task = Node(
    id="api-task",
    title="Build User API",
    required_capabilities=["python", "backend", "databases"]
)
```

### Route Task to Best Agent

```python
from htmlgraph.routing import CapabilityMatcher

# Find best agent for task
agents = registry.get_all_agents()
best_agent = CapabilityMatcher.find_best_agent(agents, task)

print(f"Best agent: {best_agent.agent_id}")  # "alice"
print(f"Match score: {best_agent.capabilities}")
```

### Routing with Workload Balancing

```python
# Set current workload
registry.set_wip("alice", 4)  # Alice has 4 tasks in progress
registry.set_wip("bob", 1)    # Bob has 1 task

# Routing considers workload (alice is busier)
best_agent = CapabilityMatcher.find_best_agent(agents, task)
# Might choose bob if bob has matching skills (workload penalty applied)
```

### Multi-Agent Workflow

```python
from htmlgraph import SDK
from htmlgraph.routing import AgentCapabilityRegistry, route_task_to_agent

sdk = SDK(agent="coordinator")
registry = AgentCapabilityRegistry()

# Register team
registry.register_agent("architect", ["architecture", "design"])
registry.register_agent("backend", ["python", "backend"])
registry.register_agent("qa", ["testing", "quality"])

# Get tasks needing assignment
tasks = sdk.features.where(status="todo")

# Route each task
for task in tasks:
    best_agent, score = route_task_to_agent(task, registry)
    if best_agent:
        # Assign to best agent
        print(f"Assigning {task.id} to {best_agent.agent_id} (score: {score})")
```

### Capability Scoring Algorithm

Scoring is 0-based (higher = better fit):

- **Exact match**: +100 per matching capability
- **No match**: -50 per missing capability
- **Extra capabilities**: +10 per bonus capability
- **Workload penalty**: -5 per task in progress
- **At capacity**: -100 (hard penalty for full WIP)

Example:
- Task needs: `["python", "testing"]`
- Agent has: `["python", "testing", "documentation"]`
- Score: (2 × 100) + (1 × 10) = 210 (excellent match)

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

### Using the Deployment Script (FLEXIBLE OPTIONS)

HtmlGraph includes `scripts/deploy-all.sh` with multiple modes for different scenarios:

**Quick Usage:**
```bash
# Documentation changes only (commit + push)
./scripts/deploy-all.sh --docs-only

# Full release
./scripts/deploy-all.sh 0.7.1

# Preview what would happen
./scripts/deploy-all.sh --dry-run

# Show all options
./scripts/deploy-all.sh --help
```

**Available Flags:**
- `--docs-only` - Only commit and push to git (skip build/publish)
- `--build-only` - Only build package (skip git/publish/install)
- `--skip-pypi` - Skip PyPI publishing step
- `--skip-plugins` - Skip plugin update steps
- `--dry-run` - Show what would happen without executing

**What full deployment does (7 steps):**
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

## Documentation Synchronization

### Memory File Sync Tool

HtmlGraph includes `scripts/sync_memory_files.py` to maintain consistency across AI agent documentation files:

**Usage:**
```bash
# Check if files are synchronized
python scripts/sync_memory_files.py --check

# Generate platform-specific file
python scripts/sync_memory_files.py --generate gemini
python scripts/sync_memory_files.py --generate claude
python scripts/sync_memory_files.py --generate codex

# Overwrite existing file
python scripts/sync_memory_files.py --generate gemini --force
```

**What it checks:**
- ✅ AGENTS.md exists (required central documentation)
- ✅ Platform files reference AGENTS.md properly
- ✅ Consistency across Claude, Gemini, Codex docs

**File structure:**
```
project/
├── AGENTS.md                    # Central documentation (SDK, deployment, workflows)
├── CLAUDE.md                    # Project vision + references AGENTS.md
├── GEMINI.md                    # Gemini-specific + references AGENTS.md
└── packages/
    ├── claude-plugin/skills/htmlgraph-tracker/SKILL.md
    ├── gemini-extension/GEMINI.md
    └── codex-skill/SKILL.md
```

**Why this matters:**
- Single source of truth (AGENTS.md)
- Platform files add platform-specific notes
- Easy maintenance (update once, not 3+ times)
- Automated validation

---

## Related Files

- `src/python/htmlgraph/sdk.py` - SDK implementation
- `src/python/htmlgraph/graph.py` - Low-level graph operations
- `src/python/htmlgraph/agents.py` - Agent interface (wrapped by SDK)
- `examples/sdk_demo.py` - Complete examples
- `scripts/deploy-all.sh` - Deployment automation script
