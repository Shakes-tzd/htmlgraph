# TrackBuilder

The TrackBuilder provides a fluent API for creating tracks with specs and plans in a single command. No manual file creation, ID generation, or path management needed.

## Overview

TrackBuilder is the recommended way to create tracks in HtmlGraph. It:

- Auto-generates track IDs and timestamps
- Creates HTML files in the correct directory structure
- Validates all input with Pydantic schemas
- Parses time estimates from task descriptions
- Provides a clean, readable API

## Basic Usage

### Minimal Track

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

track = sdk.tracks.builder() \
    .title("Simple Feature") \
    .description("A simple feature without detailed planning") \
    .priority("medium") \
    .create()

print(f"Created: {track.track_id}")
# Creates: .htmlgraph/tracks/trk-xxxxxxxx/index.html
```

### Track with Specification

```python
track = sdk.tracks.builder() \
    .title("User Authentication") \
    .description("Implement OAuth 2.0 authentication") \
    .priority("high") \
    .with_spec(
        overview="Add secure user authentication with OAuth support",
        context="Current system has no authentication. Need secure login for all users.",
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
#   - .htmlgraph/tracks/trk-xxxxxxxx/index.html
#   - .htmlgraph/tracks/trk-xxxxxxxx/spec.html
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
#   - .htmlgraph/tracks/trk-xxxxxxxx/index.html
#   - .htmlgraph/tracks/trk-xxxxxxxx/plan.html
```

### Complete Track (Spec + Plan)

```python
track = sdk.tracks.builder() \
    .title("API Rate Limiting") \
    .description("Implement rate limiting for API endpoints") \
    .priority("high") \
    .with_spec(
        overview="Protect API from abuse with rate limiting",
        context="Current API has no rate limits, vulnerable to DoS attacks",
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
# ✓ Created track: trk-a1b2c3d4
#   - Spec with 4 requirements
#   - Plan with 3 phases, 9 tasks
```

## API Reference

### TrackBuilder Methods

#### `.title(title: str) -> TrackBuilder`

Set the track title. **Required.**

```python
.title("User Authentication System")
```

#### `.description(desc: str) -> TrackBuilder`

Set the track description. Optional.

```python
.description("Implement OAuth 2.0 authentication with Google and GitHub")
```

#### `.priority(priority: str) -> TrackBuilder`

Set priority. Options: `"low"`, `"medium"`, `"high"`, `"critical"`. Defaults to `"medium"`.

```python
.priority("high")
```

#### `.with_spec(...) -> TrackBuilder`

Add specification content. Optional.

**Parameters:**

- `overview: str` - High-level summary
- `context: str` - Background and constraints
- `requirements: list` - Requirements as:
  - `(description, priority)` tuples: `("Add auth", "must-have")`
  - Or strings (defaults to "must-have"): `"Add logging"`
- `acceptance_criteria: list` - Success criteria as:
  - `(description, test_case)` tuples
  - Or strings (test case optional)

**Requirement priorities:** `"must-have"`, `"should-have"`, `"nice-to-have"`

```python
.with_spec(
    overview="Add authentication",
    context="No auth currently exists",
    requirements=[
        ("OAuth 2.0", "must-have"),
        ("JWT tokens", "must-have"),
        ("Password reset", "should-have")
    ],
    acceptance_criteria=[
        ("Users can log in", "Login test passes"),
        "Tokens expire after 1 hour"
    ]
)
```

#### `.with_plan_phases(phases: list[tuple[str, list[str]]]) -> TrackBuilder`

Add implementation plan with phases. Optional.

**Format:** `[(phase_name, [task_descriptions]), ...]`

**Time Estimates:** Include `(Xh)` in task description:
- `"Implement auth (3h)"` → 3 hours
- `"Write tests (1.5h)"` → 1.5 hours
- `"Deploy"` → No estimate

```python
.with_plan_phases([
    ("Phase 1: Setup", [
        "Configure OAuth providers (2h)",
        "Set up database (1h)"
    ]),
    ("Phase 2: Implementation", [
        "Implement login (4h)",
        "Add middleware (3h)"
    ])
])
```

#### `.create() -> Track`

Execute the build and create all files. Returns `Track` object.

```python
track = builder.create()

print(track.track_id)        # "trk-a1b2c3d4"
print(track.title)           # "Track: User Authentication"
print(track.priority)        # "high"
print(track.has_spec)        # True
print(track.has_plan)        # True
```

## File Structure

TrackBuilder creates a directory with up to three HTML files:

```
.htmlgraph/tracks/trk-xxxxxxxx/
├── index.html    # Track metadata with links to spec/plan
├── spec.html     # Specification (if with_spec() used)
└── plan.html     # Implementation plan (if with_plan_phases() used)
```

All files are fully styled and can be opened in any browser.

## When to Use TrackBuilder

**Create a track when:**

- Work involves **3+ features**
- **Multi-phase** implementation needed
- Need **coordination** across sessions
- Requires **detailed planning** upfront

**Implement directly when:**

- Single feature, straightforward work
- No need for planning
- Quick fix or enhancement

## Workflow Example

### 1. Create the Track

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Create track with spec and plan
track = sdk.tracks.builder() \
    .title("Multi-Agent Collaboration") \
    .description("Enable seamless agent collaboration") \
    .priority("high") \
    .with_spec(
        overview="Multiple agents can work together on features",
        context="Current: isolated agents. Need: claiming, handoffs, notes",
        requirements=[
            ("Add assigned_agent field to features", "must-have"),
            ("Implement claim CLI command", "must-have"),
            ("Add handoff_notes field", "should-have")
        ],
        acceptance_criteria=[
            "Multiple agents work without conflicts",
            "Smooth handoffs with full context"
        ]
    ) \
    .with_plan_phases([
        ("Phase 1: Claiming", [
            "Add assigned_agent field (1h)",
            "Implement claim CLI (2h)",
            "Update feature HTML template (1h)"
        ]),
        ("Phase 2: Handoffs", [
            "Add handoff_notes field (1h)",
            "Update session hooks (2h)",
            "Add handoff CLI command (1h)"
        ]),
        ("Phase 3: Testing", [
            "Write multi-agent tests (3h)",
            "Test handoff workflow (2h)"
        ])
    ]) \
    .create()

print(f"Created track: {track.track_id}")
```

### 2. Create Features from Phases

```python
# Create a feature for each phase
phase1 = sdk.features.create(
    title="Phase 1: Agent Claiming",
    track_id=track.track_id,
    priority="high",
    steps=[
        "Add assigned_agent field",
        "Implement claim CLI",
        "Update feature template"
    ]
)

phase2 = sdk.features.create(
    title="Phase 2: Agent Handoffs",
    track_id=track.track_id,
    priority="high",
    steps=[
        "Add handoff_notes field",
        "Update session hooks",
        "Add handoff CLI command"
    ]
)

phase3 = sdk.features.create(
    title="Phase 3: Testing",
    track_id=track.track_id,
    priority="medium",
    steps=[
        "Write multi-agent tests",
        "Test handoff workflow"
    ]
)
```

### 3. Work on Features

```bash
# Start working on Phase 1
htmlgraph feature start {phase1.id}

# Complete steps as you go
# Features are automatically attributed to the track
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

**Fix:** Use valid priority values

## Tips

1. **Auto-generated IDs** - Never manually create track IDs
2. **Timestamps** - Created/updated timestamps are automatic
3. **File paths** - Builder handles all path generation
4. **HTML generation** - Spec and Plan models convert to HTML automatically
5. **Estimates** - Include `(Xh)` in task descriptions
6. **Validation** - Pydantic validates all fields before HTML generation

## Next Steps

- [Features & Tracks Guide](features-tracks.md) - Linking features to tracks
- [Sessions Guide](sessions.md) - Session tracking and attribution
- [API Reference](../api/track-builder.md) - Complete API documentation
