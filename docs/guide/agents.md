# Agents

HtmlGraph provides seamless integration with AI agents through SDKs, CLI tools, and browser extensions.

## Supported Agents

### Claude Code

Official plugin for Claude Code CLI.

**Installation:**

```bash
claude plugin install htmlgraph
```

**Features:**

- Automatic session management via hooks
- Activity tracking for all tool calls
- Drift detection and warnings
- Feature creation decision framework
- Session continuity across conversations

**Documentation:** See the `htmlgraph` skill in Claude Code.

### Gemini CLI

Extension for Gemini CLI.

**Installation:**

```bash
gemini extension install htmlgraph
```

**Features:**

- Session tracking
- Feature management
- TrackBuilder integration
- Activity logging

**Documentation:** Included in the extension's `GEMINI.md` file.

### Codex CLI

Skill for Codex CLI.

**Installation:**

```bash
codex skill install htmlgraph
```

**Features:**

- Feature tracking
- Session management
- Spec and plan creation
- CLI integration

**Documentation:** Included in the skill's `SKILL.md` file.

## Agent Workflow

### 1. Session Start

When an agent begins working:

```python
from htmlgraph import SDK

# Initialize with agent name
sdk = SDK(agent="claude")

# Check status
status = sdk.status()
print(f"Session: {status.current_session}")
print(f"Active features: {len(status.active_features)}")
```

### 2. Create or Select Feature

```python
# Create a new feature
feature = sdk.features.create(
    title="Add user profile page",
    priority="high",
    steps=["Create component", "Add routing", "Write tests"]
)

# Or select existing feature
feature = sdk.features.get("feat-a1b2c3d4")

# Start working on it
sdk.features.start(feature.id)
```

### 3. Work and Track Progress

```python
# Complete a step
feature.steps[0].completed = True
feature.save()

# Document decisions
sdk.track_activity(
    feature_id=feature.id,
    activity="Chose React Router over Reach Router (better TypeScript support)"
)

# Update status
feature.status = "in-progress"
feature.save()
```

### 4. Complete Feature

```python
# Mark all steps complete
for step in feature.steps:
    step.completed = True
feature.save()

# Mark feature as done
feature.status = "done"
feature.save()

# Or via CLI
# htmlgraph feature complete feat-a1b2c3d4
```

## Multi-Agent Collaboration

Multiple agents can work together on the same graph:

### Agent Assignment

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Claim a feature
feature = sdk.features.get("feature-001")
feature.assigned_agent = "claude"
feature.save()

# Later, another agent can take over
sdk2 = SDK(agent="gemini")
feature.assigned_agent = "gemini"
feature.handoff_notes = "OAuth setup complete. Need JWT implementation next."
feature.save()
```

### Handoff Notes

When passing work between agents, add handoff notes:

```python
# Agent 1 completes phase 1
feature.status = "blocked"
feature.handoff_notes = """
Completed:
- OAuth provider configuration
- Redirect endpoints created

Blocked on:
- Database schema (feature-005)

Next steps:
- Implement JWT signing once DB is ready
- Add token refresh logic
"""
feature.save()

# Agent 2 picks up later
feature = sdk.features.get("feature-001")
print(feature.handoff_notes)  # See what Agent 1 did
```

## SDK Integration Patterns

### Minimal Integration

For simple scripts:

```python
from htmlgraph import SDK

sdk = SDK(agent="my-script")
feature = sdk.features.create("Quick task")
# Do work...
feature.status = "done"
feature.save()
```

### Full Integration

For complex agents:

```python
from htmlgraph import SDK

class MyAgent:
    def __init__(self, name):
        self.sdk = SDK(agent=name)

    def run_task(self, task_description):
        # Create feature
        feature = self.sdk.features.create(
            title=task_description,
            priority=self.assess_priority(task_description)
        )

        # Start working
        self.sdk.features.start(feature.id)

        try:
            # Do the work
            self.execute(feature)

            # Mark complete
            feature.status = "done"
            feature.save()

        except Exception as e:
            # Record failure
            self.sdk.track_activity(
                feature_id=feature.id,
                activity=f"Failed: {str(e)}"
            )
            feature.status = "blocked"
            feature.save()
            raise

    def assess_priority(self, description):
        # Your priority logic
        return "medium"

    def execute(self, feature):
        # Your execution logic
        for i, step in enumerate(feature.steps):
            self.execute_step(step)
            feature.steps[i].completed = True
            feature.save()
```

## Hooks

HtmlGraph uses hooks to automatically track agent activity.

### Available Hooks

- **SessionStart**: Creates session, provides context
- **PostToolUse**: Logs every tool call
- **UserPromptSubmit**: Logs user queries
- **SessionEnd**: Finalizes session, generates summary

### Hook Configuration

**Claude Code:**

Hooks are configured automatically via the Claude Code plugin. The plugin bundles a `hooks.json` that registers all event handlers. Hook scripts live in `packages/claude-plugin/hooks/scripts/` in the plugin source. Install the plugin to activate all hooks:

```bash
claude plugin install htmlgraph
```

### Custom Hooks

Create your own hooks:

```python
# my-hook.py
from htmlgraph import SDK

def on_tool_use(tool_name, tool_input, tool_output):
    sdk = SDK(agent="my-agent")

    # Log activity
    sdk.track_activity(
        feature_id=sdk.current_feature_id,
        activity=f"Used {tool_name}: {tool_input}"
    )
```

## Best Practices

### 1. Feature Creation Decision Framework

Use this framework to decide when to create a feature:

**Create a feature if:**

- Estimated >30 minutes of work
- Involves 3+ files
- Requires new tests
- Affects multiple components
- Hard to revert (schema changes, API changes)
- Needs documentation

**Implement directly if:**

- Single file, obvious change
- <30 minutes work
- No cross-system impact
- Easy to revert
- No tests needed

### 2. Use TrackBuilder for Complex Work

For multi-feature projects:

```python
track = sdk.tracks.builder() \
    .title("Multi-phase project") \
    .with_spec(overview="...", requirements=[...]) \
    .with_plan_phases([...]) \
    .create()

# Create features for each phase
for phase in track.plan.phases:
    feature = sdk.features.create(
        title=phase.name,
        track_id=track.track_id,
        steps=[task.description for task in phase.tasks]
    )
```

### 3. Document Decisions

Always record important decisions:

```python
sdk.track_activity(
    feature_id=feature.id,
    activity="Chose PostgreSQL over MongoDB: better transactions, team familiarity"
)
```

### 4. One Feature at a Time

Focus on single features for clear attribution:

```bash
htmlgraph feature start feature-001
# Complete all work
htmlgraph feature complete feature-001
```

## Next Steps

- [Sessions Guide](sessions.md) - Understanding session tracking
- [Features & Tracks Guide](features-tracks.md) - Creating and managing work
- [API Reference](../api/agents.md) - Complete agent API documentation
- [Examples](../examples/agents.md) - Real-world agent examples
