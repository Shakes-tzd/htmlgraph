# Track Creation Workflow

This document defines the deterministic workflow for AI agents to create and manage tracks in HtmlGraph.

## What is a Track?

A **track** is a conductor-style planning artifact that organizes a complete work stream with:
- **Specification** (spec.html) - Requirements, context, acceptance criteria
- **Implementation Plan** (plan.html) - Tasks, dependencies, phases
- **Features** - Linked work items that implement the track
- **Sessions** - Agent work sessions contributing to the track

## When to Create a Track

Create a track when:
- ✅ Work spans **multiple features** (3+ features)
- ✅ Requires upfront **specification and planning**
- ✅ Multiple **agents or sessions** will collaborate
- ✅ Has clear **phases or milestones**
- ✅ Needs **coordination** across components

Do NOT create a track for:
- ❌ Single isolated features
- ❌ Bug fixes
- ❌ One-off experiments (use spikes instead)

## Track Creation Workflow

### 1. Create Track Directory and Index

```bash
# Create track with auto-generated ID (recommended)
uv run htmlgraph track create "Track Title" "Brief description" --priority high

# Or specify custom ID
uv run htmlgraph track create "Track Title" "Brief description" --id my-track --priority high
```

This creates:
```
.htmlgraph/tracks/track-YYYYMMDD-HHMMSS/
└── index.html
```

### 2. Create Specification Document

```bash
# Create spec from template
uv run htmlgraph track spec <track-id> "Specification Title"
```

Then populate `spec.html` with:
- **Overview** - High-level summary
- **Context** - Why this work is needed
- **Current State** - What exists today
- **Gaps & Limitations** - What's missing or broken
- **Requirements** - What must be built
- **Success Criteria** - How we know it's done
- **Non-Goals** - What's explicitly out of scope

### 3. Create Implementation Plan

```bash
# Create plan from template
uv run htmlgraph track plan <track-id> "Implementation Plan Title"
```

Then populate `plan.html` with:
- **Phases** - Major stages of work
- **Tasks** - Specific implementation steps
- **Dependencies** - What depends on what
- **Risks** - Potential blockers
- **Timeline** (optional) - Rough effort estimates

### 4. Create Features from Plan

For each major task or phase in the plan:

```bash
# Create feature linked to track
uv run htmlgraph feature create \
  --title "Phase 1: Feature Assignment & Claiming" \
  --track-id <track-id> \
  --priority high \
  --steps "Design schema" "Implement SDK" "Add tests"
```

This automatically:
- Sets `track_id` on the feature
- Links feature to track
- Creates steps for granular tracking

### 5. Verify Track Setup

```bash
# Check track status
uv run htmlgraph status

# View track details
uv run htmlgraph track view <track-id>

# List features in track
uv run htmlgraph feature list --track <track-id>
```

Expected output:
- Track exists with spec and plan
- Features are linked to track
- All features have implementation steps

## Working on a Track

### Starting Work

```bash
# Claim a feature from the track
uv run htmlgraph feature start <feature-id>
```

The session is automatically:
- Linked to the feature
- Attributed to the track (via feature's track_id)
- Tracked in activity log

### During Work

All tool usage is automatically logged with:
- Feature attribution
- Drift detection (if wandering from assigned feature)
- Step completion tracking

### Completing Work

```bash
# Mark feature complete
uv run htmlgraph feature complete <feature-id>

# If feature was final piece, mark track complete
uv run htmlgraph track complete <track-id>
```

## Track Directory Structure

```
.htmlgraph/tracks/
├── track-YYYYMMDD-HHMMSS/
│   ├── index.html          # Track overview
│   ├── spec.html          # Specification document
│   ├── plan.html          # Implementation plan
│   └── [other artifacts]  # Design docs, diagrams, etc.
│
└── track-another-id/
    ├── index.html
    ├── spec.html
    └── plan.html
```

## Templates

### Spec Template Structure

```html
<section data-section="overview">
  <h2>Overview</h2>
  <p>High-level summary of what we're building and why</p>
</section>

<section data-section="context">
  <h2>Context</h2>
  <p>Background, motivation, and current state</p>
</section>

<section data-section="requirements">
  <h2>Requirements</h2>
  <ul class="requirements-list">
    <li>Functional requirement 1</li>
    <li>Functional requirement 2</li>
  </ul>
</section>

<section data-section="success-criteria">
  <h2>Success Criteria</h2>
  <ol class="criteria-list">
    <li>Measurable success criterion 1</li>
    <li>Measurable success criterion 2</li>
  </ol>
</section>
```

### Plan Template Structure

```html
<section data-section="phases">
  <h2>Implementation Phases</h2>
  <ol class="phases-list">
    <li data-phase="1">
      <h3>Phase 1: Foundation</h3>
      <ul>
        <li>Task 1</li>
        <li>Task 2</li>
      </ul>
    </li>
  </ol>
</section>

<section data-section="dependencies">
  <h2>Dependencies</h2>
  <p>What must be done in order</p>
</section>

<section data-section="risks">
  <h2>Risks & Mitigations</h2>
  <ul>
    <li><strong>Risk:</strong> Description <br> <strong>Mitigation:</strong> How to handle</li>
  </ul>
</section>
```

## SDK Usage

For programmatic track management:

```python
from htmlgraph.sdk import HtmlGraphSDK

sdk = HtmlGraphSDK()

# Create track
with sdk.tracks.create("My Track", "Description", priority="high") as track:
    track_id = track.id

# Create spec and plan
sdk.tracks.create_spec(track_id, "Spec Title")
sdk.tracks.create_plan(track_id, "Plan Title")

# Create features for track
for phase in ["Phase 1", "Phase 2", "Phase 3"]:
    with sdk.features.create(
        title=phase,
        track_id=track_id,
        priority="high"
    ) as feature:
        feature.steps = [
            {"description": "Design", "completed": False},
            {"description": "Implement", "completed": False},
            {"description": "Test", "completed": False}
        ]
```

## Best Practices

### 1. Spec Before Features
Always write the spec before creating features. Features should implement the spec.

### 2. Plan Before Coding
Plan should break down work into feature-sized chunks. Each feature = one deliverable.

### 3. Link Everything
Ensure all features have `track_id` set. Sessions are auto-linked via features.

### 4. Keep Spec Current
Update spec.html as requirements evolve. It's the source of truth.

### 5. Track Progress Visually
Use the dashboard to see track progress across features and sessions.

### 6. Document Decisions
Add notes to track index.html about key decisions and why they were made.

## Common Patterns

### Multi-Phase Track

```bash
# 1. Create track
uv run htmlgraph track create "Multi-Agent Collaboration" "Enable seamless agent collaboration" --priority high

# 2. Create spec with phases
uv run htmlgraph track spec track-id "Multi-Agent Collaboration Spec"
# Edit spec.html to add requirements

# 3. Create plan with phases
uv run htmlgraph track plan track-id "Implementation Plan"
# Edit plan.html with phases

# 4. Create one feature per phase
for phase in "Phase 1" "Phase 2" "Phase 3"
do
  uv run htmlgraph feature create --title "$phase" --track-id track-id --priority high
done
```

### Research Track

```bash
# 1. Create track
uv run htmlgraph track create "Performance Analysis" "Analyze and improve performance" --priority medium

# 2. Create spec with questions to answer
uv run htmlgraph track spec track-id "Performance Questions"

# 3. Create spike features for experiments
uv run htmlgraph feature create --title "Benchmark Current State" --track-id track-id --type spike
uv run htmlgraph feature create --title "Profile Hot Paths" --track-id track-id --type spike
uv run htmlgraph feature create --title "Test Optimizations" --track-id track-id --type spike
```

## Troubleshooting

### Track not showing in dashboard

```bash
# Check if track exists
ls -la .htmlgraph/tracks/

# Verify server is watching tracks directory
# Check server logs for "Reloaded X nodes in tracks"

# Manual reload
curl http://localhost:8080/api/tracks
```

### Features not linking to track

```bash
# Check feature has track_id
uv run htmlgraph feature view <feature-id>

# Fix if missing
echo 'from htmlgraph.sdk import HtmlGraphSDK
sdk = HtmlGraphSDK()
with sdk.features.edit("feature-id") as feat:
    feat.track_id = "track-id"
' | uv run python
```

### Spec/Plan not showing

```bash
# Check files exist
ls -la .htmlgraph/tracks/<track-id>/

# If missing, create them
uv run htmlgraph track spec <track-id> "Spec Title"
uv run htmlgraph track plan <track-id> "Plan Title"
```

## Summary

**Workflow Checklist:**
1. ✅ Create track with `htmlgraph track create`
2. ✅ Create spec with `htmlgraph track spec` and populate
3. ✅ Create plan with `htmlgraph track plan` and populate
4. ✅ Create features from plan tasks
5. ✅ Link features to track via `--track-id` or SDK
6. ✅ Verify setup with `htmlgraph status`
7. ✅ Start work with `htmlgraph feature start`
8. ✅ Complete features, then track

This ensures deterministic, reproducible track creation across all AI agents.
