# Track Builder - Quick Start for AI Agents

## Overview

The TrackBuilder provides a fluent API for creating tracks with specs and plans in a single command. No manual file creation, ID generation, or path management needed.

## Installation

The TrackBuilder is included in the HtmlGraph SDK:

```python
from htmlgraph.sdk import SDK

sdk = SDK()
```

## Basic Usage

### Minimal Track (No Spec/Plan)

```python
track = sdk.tracks.builder() \
    .title("Simple Feature") \
    .description("A simple feature without detailed planning") \
    .priority("medium") \
    .create()

# Creates: .htmlgraph/tracks/track-YYYYMMDD-HHMMSS/index.html
```

### Track with Specification

```python
track = sdk.tracks.builder() \
    .title("User Authentication") \
    .description("Implement OAuth 2.0 authentication") \
    .priority("high") \
    .with_spec(
        overview="Add secure user authentication with OAuth support",
        context="Current system has no authentication. Need secure login.",
        requirements=[
            ("Implement OAuth 2.0 flow", "must-have"),
            ("Add JWT token management", "must-have"),
            ("Create user profile endpoint", "should-have"),
            "Add password reset flow"  # Defaults to "must-have"
        ],
        acceptance_criteria=[
            ("Users can log in with Google/GitHub", "OAuth login works"),
            "Tokens expire after 1 hour",
            "Password reset emails sent within 5 minutes"
        ]
    ) \
    .create()

# Creates:
#   - .htmlgraph/tracks/track-YYYYMMDD-HHMMSS/index.html
#   - .htmlgraph/tracks/track-YYYYMMDD-HHMMSS/spec.html
```

### Track with Implementation Plan

```python
track = sdk.tracks.builder() \
    .title("Database Migration") \
    .description("Migrate from SQLite to PostgreSQL") \
    .priority("critical") \
    .with_plan_phases([
        ("Phase 1: Setup", [
            "Install PostgreSQL (0.5h)",
            "Create migration scripts (2h)",
            "Set up staging environment (1h)"
        ]),
        ("Phase 2: Migration", [
            "Run migrations on staging (1h)",
            "Validate data integrity (2h)",
            "Performance testing (3h)"
        ]),
        ("Phase 3: Production", [
            "Schedule maintenance window",
            "Run production migration (2h)",
            "Monitor for 24 hours"
        ])
    ]) \
    .create()

# Creates:
#   - .htmlgraph/tracks/track-YYYYMMDD-HHMMSS/index.html
#   - .htmlgraph/tracks/track-YYYYMMDD-HHMMSS/plan.html
```

### Complete Track (Spec + Plan)

```python
track = sdk.tracks.builder() \
    .title("API Rate Limiting") \
    .description("Implement rate limiting for API endpoints") \
    .priority("high") \
    .with_spec(
        overview="Protect API from abuse with rate limiting",
        context="Current API has no rate limits, vulnerable to DoS",
        requirements=[
            ("Implement token bucket algorithm", "must-have"),
            ("Add Redis for distributed rate limiting", "must-have"),
            ("Create rate limit middleware", "must-have"),
            ("Add rate limit headers to responses", "should-have")
        ],
        acceptance_criteria=[
            ("100 requests/minute per API key", "Load test confirms limit"),
            ("429 status code when rate exceeded", "Integration test passes"),
            "Rate limits reset every 60 seconds"
        ]
    ) \
    .with_plan_phases([
        ("Phase 1: Core Implementation", [
            "Implement token bucket algorithm (3h)",
            "Add Redis client (1h)",
            "Create rate limiting middleware (2h)"
        ]),
        ("Phase 2: Integration", [
            "Add middleware to API routes (1h)",
            "Implement rate limit headers (1h)",
            "Add error handling (1h)"
        ]),
        ("Phase 3: Testing", [
            "Write unit tests (2h)",
            "Load testing (3h)",
            "Documentation (1h)"
        ])
    ]) \
    .create()

# Output:
# ✓ Created track: track-20251221-220000
#   - Spec with 4 requirements
#   - Plan with 3 phases, 9 tasks

# Creates:
#   - .htmlgraph/tracks/track-20251221-220000/index.html
#   - .htmlgraph/tracks/track-20251221-220000/spec.html (with 4 requirements)
#   - .htmlgraph/tracks/track-20251221-220000/plan.html (with 3 phases, 9 tasks)
```

## API Reference

### TrackBuilder Methods

#### `title(title: str) -> TrackBuilder`
Set the track title. **Required.**

#### `description(desc: str) -> TrackBuilder`
Set the track description. Optional, defaults to empty string.

#### `priority(priority: str) -> TrackBuilder`
Set priority. Options: `"low"`, `"medium"`, `"high"`, `"critical"`. Defaults to `"medium"`.

#### `with_spec(...) -> TrackBuilder`
Add specification content. Optional.

**Parameters:**
- `overview: str` - High-level summary of what needs to be built
- `context: str` - Background, current state, gaps, and constraints
- `requirements: list` - List of requirements as:
  - `(description, priority)` tuples, e.g., `("Add auth", "must-have")`
  - Or just strings (defaults to `"must-have"`), e.g., `"Add logging"`
  - Priority options: `"must-have"`, `"should-have"`, `"nice-to-have"`
- `acceptance_criteria: list` - Success criteria as:
  - `(description, test_case)` tuples
  - Or just strings (test_case optional)

#### `with_plan_phases(phases: list[tuple[str, list[str]]]) -> TrackBuilder`
Add implementation plan with phases. Optional.

**Format:** `[(phase_name, [task_descriptions]), ...]`

**Task Estimates:** Include `(Xh)` in task description to set estimate:
- `"Implement auth (3h)"` → 3-hour task
- `"Write tests (1.5h)"` → 1.5-hour task
- `"Deploy"` → No estimate

#### `create() -> Track`
Execute the build and create all files. Returns `Track` object.

## Return Value

The `create()` method returns a `Track` object with:

```python
track.id              # "track-20251221-220000"
track.title           # "Track: API Rate Limiting"
track.description     # "Implement rate limiting..."
track.priority        # "high"
track.status          # "planned"
track.has_spec        # True
track.has_plan        # True
```

## File Structure Created

```
.htmlgraph/tracks/track-YYYYMMDD-HHMMSS/
├── index.html    # Track metadata with links to spec/plan
├── spec.html     # Specification (if with_spec() used)
└── plan.html     # Implementation plan (if with_plan_phases() used)
```

## Agent Workflow

### When to Create a Track

**Create a track when:**
- Work involves 3+ features
- Multi-phase implementation needed
- Coordination across multiple sessions required
- High-level planning needed before implementation

**Implement directly when:**
- Single feature, straightforward implementation
- No need for detailed planning
- Quick fix or enhancement

### Recommended Pattern

```python
from htmlgraph.sdk import SDK

sdk = SDK()

# 1. Create track with spec and plan
track = sdk.tracks.builder() \
    .title("Multi-Agent Collaboration") \
    .description("Enable seamless agent collaboration") \
    .priority("high") \
    .with_spec(
        overview="Multiple agents can work together...",
        context="Current: isolated agents. Need: claiming, handoffs",
        requirements=[
            ("Add assigned_agent field", "must-have"),
            ("Implement claim CLI", "must-have"),
            ("Add handoff_notes", "should-have")
        ],
        acceptance_criteria=[
            "Multiple agents work without conflicts",
            "Smooth handoffs with full context"
        ]
    ) \
    .with_plan_phases([
        ("Phase 1: Claiming", ["Add field (1h)", "Implement CLI (2h)"]),
        ("Phase 2: Handoffs", ["Add notes (1h)", "Update hooks (2h)"])
    ]) \
    .create()

# 2. Create features for each phase
for phase_idx, (phase_name, tasks) in enumerate([
    ("Phase 1: Claiming", ["Add field", "Implement CLI"]),
    ("Phase 2: Handoffs", ["Add notes", "Update hooks"])
]):
    feature = sdk.features.create(phase_name) \
        .set_track(track.id) \
        .set_priority(track.priority) \
        .add_steps(tasks) \
        .save()

# 3. Start working
sdk.features.get("feature-001")
```

## Error Handling

### Missing Title
```python
track = sdk.tracks.builder() \
    .priority("high") \
    .create()
# ValueError: Track title is required
```

**Fix:** Always call `.title()` before `.create()`

### Invalid Priority
```python
track = sdk.tracks.builder() \
    .title("My Track") \
    .with_spec(
        requirements=[("Add auth", "super-critical")]  # Invalid!
    ) \
    .create()
# ValidationError: Input should be 'must-have', 'should-have' or 'nice-to-have'
```

**Fix:** Use valid priority values: `"must-have"`, `"should-have"`, `"nice-to-have"`

## Tips for Agents

1. **Auto-generated IDs** - Never manually create track IDs, the builder generates them
2. **Timestamps** - Created/updated timestamps are automatic
3. **File paths** - Builder handles all path generation
4. **HTML generation** - Spec and Plan models convert to HTML automatically
5. **Estimates** - Include `(Xh)` in task descriptions for time estimates
6. **Validation** - Pydantic validates all fields before HTML generation

## See Also

- [docs/TRACK_WORKFLOW.md](./TRACK_WORKFLOW.md) - Complete track creation workflow
- [docs/AGENT_FRIENDLY_SDK.md](./AGENT_FRIENDLY_SDK.md) - Full SDK enhancement proposal
- [src/python/htmlgraph/track_builder.py](../src/python/htmlgraph/track_builder.py) - Implementation
