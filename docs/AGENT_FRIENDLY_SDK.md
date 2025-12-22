# Agent-Friendly SDK for Track Creation

Making it easy for AI agents to create tracks, specs, and plans deterministically with minimal user guidance.

## Problem Statement

Currently, creating a track with spec and plan requires:
1. Manual creation of Spec/Plan objects
2. Populating many fields (id, title, requirements, tasks, etc.)
3. Understanding Pydantic model structure
4. Writing to correct file paths

Agents need:
- **Template-based creation** - Start from common patterns
- **Intelligent defaults** - Auto-populate IDs, timestamps, paths
- **Fluent API** - Builder pattern for easy construction
- **Content parsing** - Extract spec/plan from natural language or markdown
- **Single command** - Create track+spec+plan in one call

---

## Proposed SDK Enhancements

### 1. Track Builder Pattern

```python
from htmlgraph.sdk import SDK

sdk = SDK()

# Fluent API for track creation
track = sdk.tracks.builder() \
    .title("Multi-Agent Collaboration") \
    .description("Enable seamless agent collaboration") \
    .priority("high") \
    .with_spec(
        overview="Agents can work together seamlessly...",
        context="Current state: agents isolated..."
    ) \
    .with_plan_phases([
        ("Feature Claiming", ["Add assigned_agent field", "Implement claim CLI"]),
        ("Handoff Context", ["Add handoff_notes field", "Update session hooks"]),
    ]) \
    .create()

# Returns Track object with spec and plan already created
print(f"Created track: {track.id}")
print(f"  Spec: {track.has_spec}")
print(f"  Plan: {track.has_plan}")
```

**Benefits:**
- No manual ID generation
- No file path management
- Spec and plan created automatically
- Chainable, readable API

---

### 2. Template-Based Creation

```python
# Predefined templates for common track types
track = sdk.tracks.from_template(
    template="multi-phase-feature",
    title="Multi-Agent Collaboration",
    phases=[
        "Feature Assignment & Claiming",
        "Handoff Context & Notes",
        "Agent Capabilities & Smart Routing",
        "Work Queue Dashboard",
        "Enhanced Session Continuity"
    ],
    priority="high"
)

# Template auto-generates:
# - Track with proper structure
# - Spec with requirements section
# - Plan with phases (one per phase name)
# - Features (one per phase)
```

**Templates:**
- `single-feature` - One feature, simple spec/plan
- `multi-phase-feature` - Multiple phases, detailed plan
- `research` - Spike with questions, experiments
- `bug-fix-campaign` - Multiple related bug fixes
- `refactoring` - Code quality improvements

---

### 3. Markdown-to-Spec Parser

```python
# Parse markdown document into Spec object
spec = sdk.specs.from_markdown("""
# Multi-Agent Collaboration Specification

## Overview
HtmlGraph enables multiple AI agents to collaborate...

## Current Capabilities
- Agent-specific sessions
- Automatic attribution

## Requirements
- [ ] Add assigned_agent field to Node model (must-have)
- [ ] Implement feature claim CLI (must-have)
- [ ] Add handoff_notes to Session (should-have)

## Success Criteria
1. Multiple agents work without conflicts
2. Smooth handoffs with full context
""", track_id="track-123")

# Auto-extracts:
# - Overview from ## Overview section
# - Context from ## Current Capabilities
# - Requirements from checklist with priorities
# - Acceptance criteria from numbered list
```

---

### 4. Auto-Generate Plan from Phases

```python
# Natural language phase descriptions → structured plan
plan = sdk.plans.from_phases(
    track_id="track-123",
    phases=[
        {
            "name": "Phase 1: Feature Assignment",
            "description": "Implement claiming mechanism",
            "tasks": [
                "Add assigned_agent field to Node model (1h)",
                "Implement feature claim CLI (2h)",
                "Add claim enforcement (1h)"
            ]
        },
        {
            "name": "Phase 2: Handoff Context",
            "description": "Enable context passing",
            "tasks": [
                "Add handoff_notes to Session (1h)",
                "Update session-end hook (2h)"
            ]
        }
    ]
)

# Auto-generates:
# - Task IDs (task-1-1, task-1-2, etc.)
# - Estimates parsed from "(Xh)" suffix
# - Phase IDs (phase-1, phase-2)
# - Progress tracking setup
```

---

### 5. One-Command Track Creation

```python
# Create everything in one call
track = sdk.tracks.create_complete(
    title="Multi-Agent Collaboration",
    description="Enable seamless agent collaboration with claiming, handoffs, and routing",
    priority="high",

    # Spec content
    overview="HtmlGraph enables multiple AI agents to collaborate...",
    context="Current: isolated agents. Gap: no claiming mechanism.",
    requirements=[
        ("Add assigned_agent field", "must-have"),
        ("Implement claim CLI", "must-have"),
        ("Add handoff_notes", "should-have")
    ],
    acceptance_criteria=[
        "Multiple agents work without conflicts",
        "Smooth handoffs with full context"
    ],

    # Plan content
    phases=[
        ("Phase 1: Feature Assignment", [
            ("Add assigned_agent field", 1.0),
            ("Implement claim CLI", 2.0)
        ]),
        ("Phase 2: Handoff Context", [
            ("Add handoff_notes", 1.0),
            ("Update hooks", 2.0)
        ])
    ]
)

# Creates:
# - Track at .htmlgraph/tracks/{track-id}/index.html
# - Spec at .htmlgraph/tracks/{track-id}/spec.html
# - Plan at .htmlgraph/tracks/{track-id}/plan.html
# - Features (one per phase)
```

---

### 6. AI-Friendly Prompts

```python
# Agent asks user for minimal input
track = sdk.tracks.create_interactive(
    agent_prompt=True  # Uses LLM-friendly prompts
)

# Prompts agent to ask:
# 1. "What is the track title?"
# 2. "Brief description (1 sentence)?"
# 3. "Priority (high/medium/low)?"
# 4. "List the main phases (comma-separated)?"

# Then auto-generates full track+spec+plan
```

---

### 7. Content Inference from Features

```python
# If agent already created features, infer track from them
features = [
    sdk.features.get("feature-001"),
    sdk.features.get("feature-002"),
    sdk.features.get("feature-003")
]

# Auto-generate track from existing features
track = sdk.tracks.from_features(
    features=features,
    title="Multi-Agent Collaboration"  # Optional, can infer
)

# Infers:
# - Common keywords → track description
# - Feature priorities → track priority
# - Feature steps → plan tasks
# - Feature titles → spec requirements
```

---

## Implementation Plan

### Phase 1: Builder Pattern (High Priority)
**Why:** Immediately makes SDK more usable
**Files:** `src/python/htmlgraph/sdk.py`

```python
class TrackBuilder:
    """Fluent builder for creating tracks."""

    def __init__(self, sdk: SDK):
        self.sdk = sdk
        self._title = None
        self._description = ""
        self._priority = "medium"
        self._spec_data = {}
        self._plan_phases = []

    def title(self, title: str) -> 'TrackBuilder':
        self._title = title
        return self

    def description(self, desc: str) -> 'TrackBuilder':
        self._description = desc
        return self

    def priority(self, priority: str) -> 'TrackBuilder':
        self._priority = priority
        return self

    def with_spec(self, overview: str = "", context: str = "", requirements: list = None) -> 'TrackBuilder':
        self._spec_data = {
            "overview": overview,
            "context": context,
            "requirements": requirements or []
        }
        return self

    def with_plan_phases(self, phases: list[tuple[str, list[str]]]) -> 'TrackBuilder':
        """phases = [("Phase name", ["task1", "task2"]), ...]"""
        self._plan_phases = phases
        return self

    def create(self) -> Track:
        """Execute the build and create track+spec+plan."""
        from htmlgraph.planning import Track, Spec, Plan, Phase, Task, Requirement
        from datetime import datetime
        from pathlib import Path

        # Generate track ID
        track_id = f"track-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Create track
        track = Track(
            id=track_id,
            title=f"Track: {self._title}",
            description=self._description,
            priority=self._priority,
            has_spec=bool(self._spec_data),
            has_plan=bool(self._plan_phases)
        )

        # Save track
        track_dir = Path(f".htmlgraph/tracks/{track_id}")
        track_dir.mkdir(parents=True, exist_ok=True)
        (track_dir / "index.html").write_text(track.to_html(), encoding="utf-8")

        # Create spec if provided
        if self._spec_data:
            spec = Spec(
                id=f"{track_id}-spec",
                title=f"{self._title} Specification",
                track_id=track_id,
                overview=self._spec_data.get("overview", ""),
                context=self._spec_data.get("context", ""),
                requirements=[
                    Requirement(
                        id=f"req-{i+1}",
                        description=req if isinstance(req, str) else req[0],
                        priority=req[1] if isinstance(req, tuple) else "must-have"
                    )
                    for i, req in enumerate(self._spec_data.get("requirements", []))
                ]
            )
            (track_dir / "spec.html").write_text(spec.to_html(), encoding="utf-8")

        # Create plan if provided
        if self._plan_phases:
            phases = []
            for i, (phase_name, tasks) in enumerate(self._plan_phases):
                phase_tasks = []
                for j, task_desc in enumerate(tasks):
                    # Parse estimate from task description
                    estimate = None
                    if "(" in task_desc and "h)" in task_desc:
                        parts = task_desc.rsplit("(", 1)
                        task_desc = parts[0].strip()
                        estimate_str = parts[1].replace("h)", "").strip()
                        try:
                            estimate = float(estimate_str)
                        except ValueError:
                            pass

                    phase_tasks.append(Task(
                        id=f"task-{i+1}-{j+1}",
                        description=task_desc,
                        estimate_hours=estimate
                    ))

                phases.append(Phase(
                    id=f"phase-{i+1}",
                    name=phase_name,
                    tasks=phase_tasks
                ))

            plan = Plan(
                id=f"{track_id}-plan",
                title=f"{self._title} Implementation Plan",
                track_id=track_id,
                phases=phases
            )
            (track_dir / "plan.html").write_text(plan.to_html(), encoding="utf-8")

        return track


# Add to SDK class
class SDK:
    # ... existing code ...

    class TracksManager:
        def builder(self) -> TrackBuilder:
            """Create a new track builder."""
            return TrackBuilder(self.sdk)
```

**Usage:**
```python
track = sdk.tracks.builder() \
    .title("Multi-Agent Collaboration") \
    .description("Enable seamless agent collaboration") \
    .priority("high") \
    .with_spec(
        overview="Agents can work together...",
        requirements=[
            ("Add assigned_agent field", "must-have"),
            ("Implement claim CLI", "must-have")
        ]
    ) \
    .with_plan_phases([
        ("Phase 1: Feature Assignment", ["Add field (1h)", "Implement CLI (2h)"]),
        ("Phase 2: Handoff Context", ["Add notes field (1h)", "Update hooks (2h)"])
    ]) \
    .create()
```

---

### Phase 2: Template System
**Files:** `src/python/htmlgraph/templates.py`

```python
TEMPLATES = {
    "multi-phase-feature": {
        "spec_template": """
        ## Overview
        {overview}

        ## Requirements
        {requirements}
        """,
        "plan_phases": lambda phases: [
            {"name": phase, "tasks": [f"Implement {phase}"]}
            for phase in phases
        ]
    },
    "bug-fix-campaign": {
        "spec_template": "...",
        "plan_phases": "..."
    }
}

def from_template(template_name: str, **kwargs) -> Track:
    template = TEMPLATES[template_name]
    # Fill template and create track
    pass
```

---

### Phase 3: Markdown Parser
**Files:** `src/python/htmlgraph/parsers.py`

```python
import re
from htmlgraph.planning import Spec, Requirement, AcceptanceCriterion

def parse_spec_from_markdown(markdown: str, track_id: str) -> Spec:
    """Parse markdown into Spec object."""

    # Extract sections
    overview = extract_section(markdown, "## Overview")
    context = extract_section(markdown, "## Context") or extract_section(markdown, "## Current Capabilities")

    # Parse requirements (checkbox format)
    req_pattern = r"- \[([ x])\] (.+?) \(([^)]+)\)"
    requirements = []
    for i, match in enumerate(re.finditer(req_pattern, markdown)):
        checked, desc, priority = match.groups()
        requirements.append(Requirement(
            id=f"req-{i+1}",
            description=desc.strip(),
            priority=map_priority(priority),
            verified=checked == "x"
        ))

    # Parse acceptance criteria (numbered list)
    criteria = []
    criteria_section = extract_section(markdown, "## Success Criteria") or extract_section(markdown, "## Acceptance Criteria")
    if criteria_section:
        for line in criteria_section.split("\n"):
            if re.match(r"^\d+\.", line):
                criteria.append(AcceptanceCriterion(
                    description=re.sub(r"^\d+\.\s*", "", line).strip()
                ))

    return Spec(
        id=f"{track_id}-spec",
        title="Specification",
        track_id=track_id,
        overview=overview,
        context=context,
        requirements=requirements,
        acceptance_criteria=criteria
    )

def map_priority(text: str) -> str:
    """Map priority keywords to Literal values."""
    text_lower = text.lower()
    if "must" in text_lower or "critical" in text_lower or "high" in text_lower:
        return "must-have"
    elif "should" in text_lower or "medium" in text_lower:
        return "should-have"
    else:
        return "nice-to-have"
```

---

### Phase 4: CLI Shortcuts

```bash
# Create track from markdown file
htmlgraph track create-from-md MULTI_AGENT_COLLABORATION.md \
  --title "Multi-Agent Collaboration" \
  --priority high

# Create track interactively (agent prompts user)
htmlgraph track create --interactive

# Create track from template
htmlgraph track create --template multi-phase-feature \
  --title "Multi-Agent Collaboration" \
  --phases "Feature Assignment,Handoff Context,Smart Routing"
```

---

## Agent Workflow Examples

### Example 1: Agent Creates Track from User Description

**User:** "Create a track for implementing multi-agent collaboration with 5 phases"

**Agent Code:**
```python
track = sdk.tracks.builder() \
    .title("Multi-Agent Collaboration") \
    .description("Enable seamless collaboration between multiple AI agents") \
    .priority("high") \
    .with_spec(
        overview="Multiple agents can work on same project without conflicts",
        context="Current: agents isolated. Need: claiming, handoffs, routing"
    ) \
    .with_plan_phases([
        ("Feature Assignment", ["Add assigned_agent field", "Implement claim CLI"]),
        ("Handoff Context", ["Add handoff_notes", "Update hooks"]),
        ("Smart Routing", ["Add capabilities", "Implement routing"]),
        ("Work Queue", ["Build CLI", "Add dashboard"]),
        ("Continuity", ["Update session hooks", "Add conflict detection"])
    ]) \
    .create()

print(f"Created track {track.id} with spec and plan")
```

### Example 2: Agent Parses Existing Document

**User:** "Create a track from docs/MULTI_AGENT_COLLABORATION.md"

**Agent Code:**
```python
# Read markdown
content = Path("docs/MULTI_AGENT_COLLABORATION.md").read_text()

# Create track
track_id = f"track-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
spec = sdk.specs.from_markdown(content, track_id=track_id)
plan = sdk.plans.from_markdown(content, track_id=track_id)

track = sdk.tracks.create(
    id=track_id,
    title="Multi-Agent Collaboration",
    priority="high"
)

print(f"Created track with {len(spec.requirements)} requirements and {plan.total_tasks} tasks")
```

### Example 3: Agent Uses Template

**User:** "Create a multi-phase feature track for authentication"

**Agent Code:**
```python
track = sdk.tracks.from_template(
    template="multi-phase-feature",
    title="User Authentication System",
    phases=["OAuth Integration", "Session Management", "Profile API"],
    priority="high"
)

print(f"Created track {track.id} from template")
```

---

## Benefits

### For Agents
- ✅ **Deterministic** - Same input → same output
- ✅ **Minimal input** - Only essential fields required
- ✅ **Auto-completion** - IDs, timestamps, paths handled automatically
- ✅ **Forgiving** - Accepts natural language, parses structure
- ✅ **Discoverable** - Fluent API guides usage

### For Users
- ✅ **Less guidance needed** - Agent can infer structure
- ✅ **Faster setup** - One command vs many steps
- ✅ **Consistency** - All tracks follow same pattern
- ✅ **Flexibility** - Can use builder, templates, or parsers

---

## Implementation Priority

1. **Phase 1: Builder Pattern** (1-2 days)
   - Immediate value
   - Foundation for other features

2. **Phase 2: CLI Shortcuts** (1 day)
   - Makes builder accessible from CLI

3. **Phase 3: Markdown Parser** (2-3 days)
   - Enables doc-to-track conversion

4. **Phase 4: Templates** (2-3 days)
   - Covers common use cases

Total: ~1 week to implement all phases
