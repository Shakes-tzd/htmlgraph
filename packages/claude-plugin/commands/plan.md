# /htmlgraph:plan

Start planning a new track with spike or create directly. Uses strategic analytics to provide project context and creates structured tracks with specs and implementation plans.

**⚠️ IMPORTANT: Research First for Complex Features**

For complex features (auth, security, real-time, integrations), you should **complete research BEFORE planning**:

1. Use `/htmlgraph:research "{topic}"` to gather best practices
2. Document findings (libraries, patterns, anti-patterns)
3. Then use `/htmlgraph:plan` with research-informed context

This research-first approach:
- ✅ Avoids reinventing wheels
- ✅ Learns from others' mistakes
- ✅ Chooses right tools upfront
- ✅ Reduces context usage (targeted vs exploratory)

## Usage

```
/htmlgraph:plan <description> [--spike] [--timebox HOURS]
```

## Parameters

- `description` (required): What you want to plan (e.g., "User authentication system")
- `--spike` (optional) (default: True): Create a planning spike first (recommended for complex work)
- `--timebox` (optional) (default: 4.0): Time limit for spike in hours


## Examples

```bash
# RECOMMENDED: Research first for complex features
/htmlgraph:research "OAuth 2.0 implementation patterns"
/htmlgraph:plan "User authentication system"
```
Research best practices, then create planning spike

```bash
/htmlgraph:plan "Real-time notifications" --timebox 3
```
Create planning spike with 3-hour timebox

```bash
/htmlgraph:plan "Simple bug fix dashboard" --no-spike
```
Create track directly without spike (use for simple, well-defined work)


## Instructions for Claude

This command uses the SDK's `smart_plan()` method which:
1. Analyzes current project state (bottlenecks, risks, parallel capacity)
2. Provides strategic context from analytics
3. Creates a planning spike (default) or track directly

**⚠️ CRITICAL: Check for Research Before Planning**

Before creating the plan, check if research was completed:
1. Check if `/htmlgraph:research` was used previously in the conversation
2. If complex feature WITHOUT research → Warn and suggest research first
3. If research completed → Pass research_completed=True and findings

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# STEP 1: Check if research was completed
# Look for research findings in conversation context
research_completed = False
research_findings = None

# If you previously ran /htmlgraph:research, extract findings
if has_previous_research():
    research_completed = True
    research_findings = {
        "topic": "<topic from research>",
        "sources_count": <number of sources>,
        "recommended_library": "<library name if specified>",
        "key_insights": ["<insight 1>", "<insight 2>", ...]
    }

# STEP 2: Validate complex features have research
is_complex = any([
    "auth" in args.description.lower(),
    "security" in args.description.lower(),
    "real-time" in args.description.lower(),
    "websocket" in args.description.lower(),
    "oauth" in args.description.lower(),
])

if is_complex and not research_completed:
    print("⚠️  Warning: Complex feature detected without research.")
    print("RECOMMENDED: Run /htmlgraph:research first to gather best practices.")
    print(f"Example: /htmlgraph:research \"{args.description}\"")
    print()
    # Still proceed, but flag the warning

# STEP 3: Create plan with research context
result = sdk.smart_plan(
    description=args.description,
    create_spike=args.spike,  # Default: True
    timebox_hours=args.timebox,  # Default: 4.0
    research_completed=research_completed,
    research_findings=research_findings
)

# STEP 4: Display result with warnings if any
print(format_output(result))

if "warnings" in result:
    for warning in result["warnings"]:
        print(f"\n{warning}")
```

### SDK API Reference

**smart_plan() signature:**
```python
sdk.smart_plan(
    description: str,        # What you want to plan
    create_spike: bool = True,   # Create spike for research
    timebox_hours: float = 4.0,  # Time limit for spike
    research_completed: bool = False,  # Whether research was done
    research_findings: dict[str, Any] | None = None  # Research results
) -> dict[str, Any]
```

**Returns:**
```python
{
    "type": "spike" | "track",
    "spike_id": "spike-abc123",  # If spike created
    "title": "Plan: User authentication system",
    "status": "todo",
    "research_informed": True,  # Whether research was provided
    "project_context": {
        "bottlenecks_count": 3,
        "high_risk_count": 5,
        "parallel_capacity": 4,
        "description": "User authentication system"
    },
    "next_steps": [...],
    "warnings": [...]  # Present if issues detected (e.g., no research)
}
```

### Creating Tracks Directly (Advanced)

If the spike reveals a well-defined plan, create a track with TrackBuilder:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Create track with spec and plan in one call
track = sdk.tracks.builder() \
    .title("User Authentication System") \
    .description("OAuth 2.0 authentication with JWT tokens") \
    .priority("high") \
    .with_spec(
        overview="Secure user authentication supporting multiple OAuth providers",
        context="Users need secure login without managing passwords",
        requirements=[
            ("Support Google and GitHub OAuth", "must-have"),
            ("JWT-based session management", "must-have"),
            ("Refresh token rotation", "should-have"),
            ("Remember me functionality", "nice-to-have")
        ],
        acceptance_criteria=[
            ("User can log in with Google", "test_google_login()"),
            ("User can log in with GitHub", "test_github_login()"),
            ("JWT tokens expire after 1 hour", "test_token_expiry()"),
            ("Refresh tokens rotate on use", "test_token_rotation()")
        ]
    ) \
    .with_plan_phases([
        ("Phase 1: OAuth Setup", [
            "Configure OAuth providers (2h)",
            "Create callback endpoints (2h)",
            "Add environment variables (0.5h)"
        ]),
        ("Phase 2: JWT Implementation", [
            "Implement token signing (2h)",
            "Add refresh token logic (1.5h)",
            "Create token middleware (1h)"
        ]),
        ("Phase 3: Testing", [
            "Write integration tests (3h)",
            "Add E2E tests (2h)",
            "Security audit (1h)"
        ])
    ]) \
    .create()

print(f"Created track: {track.id}")
```

### TrackBuilder API

**Core Methods:**
```python
builder = sdk.tracks.builder()

# Basic metadata
builder.title(str)           # Track title (required)
builder.description(str)     # Track description
builder.priority(str)        # low|medium|high|critical

# Add specification
builder.with_spec(
    overview: str,                    # High-level summary
    context: str,                     # Background and current state
    requirements: list,               # [(desc, priority)] or [desc]
    acceptance_criteria: list         # [desc] or [(desc, test_case)]
)

# Add implementation plan
builder.with_plan_phases([
    (phase_name, [task_descriptions])  # Tasks can include "(2h)" for estimates
])

# File format (default: consolidated single file)
builder.consolidated()      # Single index.html (default)
builder.separate_files()    # Legacy 3-file format

# Execute
builder.create()  # Returns Track object
```

### Schema Reference

**Track Model:**
```python
class Track(BaseModel):
    id: str                # Generated track ID (trk-xxxxxxxx)
    title: str             # Track title
    description: str       # Track description
    status: str            # planned|active|completed|abandoned
    priority: str          # low|medium|high|critical
    has_spec: bool         # Whether spec is included
    has_plan: bool         # Whether plan is included
    created: datetime
    updated: datetime
```

**Spec Model:**
```python
class Spec(BaseModel):
    id: str                        # Spec ID
    title: str                     # Spec title
    track_id: str                  # Parent track ID
    status: str                    # draft|review|approved|outdated
    overview: str                  # High-level summary
    context: str                   # Why we're building this
    requirements: list[Requirement]
    acceptance_criteria: list[AcceptanceCriterion]
```

**Plan Model:**
```python
class Plan(BaseModel):
    id: str                # Plan ID
    title: str             # Plan title
    track_id: str          # Parent track ID
    status: str            # draft|active|completed
    phases: list[Phase]    # Implementation phases
```

**Phase & Task:**
```python
class Phase(BaseModel):
    id: str                    # Phase ID (phase-1, phase-2, etc.)
    name: str                  # Phase name
    tasks: list[Task]          # Tasks in this phase

class Task(BaseModel):
    id: str                    # Task ID (task-1-1, task-1-2, etc.)
    description: str           # Task description
    completed: bool            # Whether completed
    estimate_hours: float      # Time estimate (optional)
```

### Workflow Guidance

**1. Complex/Undefined Work → Use Spike:**
```bash
/htmlgraph:plan "Real-time collaboration features" --spike --timebox 6
```
- Research technical approaches
- Explore libraries/tools
- Identify risks and unknowns
- Draft requirements and plan
- Then create track from spike findings

**2. Well-Defined Work → Create Track Directly:**
```bash
/htmlgraph:plan "Add dark mode toggle" --no-spike
```
- Requirements are clear
- Implementation is straightforward
- No research needed
- Can proceed immediately

**3. During Spike → Reduce Exploratory Reads:**
When working in a planning spike, you should:
- Focus on specific research questions
- Document findings in spike notes
- Draft requirements as you discover them
- Create structured plan with phases
- Avoid reading entire codebases - use targeted searches

**Example spike workflow:**
```python
# 1. Get spike context
spike = sdk.spikes.get(spike_id)

# 2. Research focused questions
# Instead of: Read entire auth module
# Do: Search for specific patterns
grep "oauth" --type py  # Find OAuth usage

# 3. Document findings
with sdk.spikes.edit(spike_id) as s:
    s.notes += "\nFound: Google OAuth already configured"
    s.add_finding("JWT library", "Uses PyJWT 2.8.0")

# 4. Create track from findings
track = sdk.create_track_from_spike(
    spike_id=spike_id,
    title="User Authentication",
    requirements=[...],  # From spike findings
    phases=[...]         # From spike plan
)
```

### Output Format:

```
## Planning Started

**Type:** {type}
**Title:** {title}
**ID:** {spike_id or track_id}
**Status:** {status}

### Project Context
- Bottlenecks: {project_context.bottlenecks_count}
- High-risk items: {project_context.high_risk_count}
- Parallel capacity: {project_context.parallel_capacity}

### What This Means
{context_interpretation}

### Next Steps
{next_steps}
```

**Context Interpretation Examples:**
- "3 bottlenecks detected - consider if this work helps unblock them"
- "5 high-risk items - ensure this doesn't add more complexity"
- "4 agents can work in parallel - look for parallelizable tasks"
