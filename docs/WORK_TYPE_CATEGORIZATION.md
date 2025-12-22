# Work Type Categorization in HtmlGraph

## Problem Statement

HtmlGraph currently tracks all work through features, bugs, chores, spikes, and epics, but lacks a systematic way to differentiate between:
- **Feature implementation work** - Building new functionality
- **Exploratory/research work** - Investigating unknowns, spikes
- **Maintenance work** - Bug fixes, refactoring, technical debt
- **Administrative work** - Documentation, planning, reviews

This makes it difficult to analyze sessions and answer questions like:
- "How much time was spent on exploration vs implementation?"
- "What percentage of this project was maintenance vs new features?"
- "Which sessions were primarily investigative?"

## Industry Standards Research

### 1. Agile Spike Categorization

**Spike Types:**
- **Technical Spike** - Investigate technical implementation options
- **Architectural Spike** - Research system design and architecture decisions
- **Risk Spike** - Identify and assess project risks

**Key Characteristics:**
- Timeboxed investigations (typically 1-3 days)
- Goal is to reduce uncertainty, not deliver features
- Output is knowledge/decision, not production code
- Should have clear exit criteria

**Sources:** [ONES.com](https://ones.com/blog/what-are-spikes-in-agile/), [Wrike Agile Guide](https://www.wrike.com/agile-guide/faq/what-is-a-spike-story-in-agile/)

### 2. Jira Work Item Hierarchy

**Work Item Types:**
- **Epic** - Large body of work spanning multiple sprints
- **Story** - User-centric feature or functionality
- **Task** - Operational work (not user-facing)
- **Bug** - Defect or issue to fix
- **Spike** - Investigation/research task
- **Subtask** - Breakdown of any parent item

**Key Insight:** Clear distinction between user-facing work (Stories) and internal work (Tasks, Spikes)

**Sources:** [Atlassian Jira Docs](https://support.atlassian.com/jira-cloud-administration/docs/what-are-issue-types/), [PlanyWay Blog](https://planyway.com/blog/jira-issue-types)

### 3. Software Maintenance Categories

**Four Types of Maintenance:**
1. **Corrective** - Fix defects and errors
2. **Adaptive** - Adapt to environment changes (OS, dependencies)
3. **Perfective** - Improve performance, usability, maintainability
4. **Preventive** - Prevent future problems (refactoring, tech debt)

**Refactoring Classification:**
- **Preventive Refactoring** - Proactive code improvement to prevent future issues
- **Corrective Refactoring** - Fix code smells and technical debt

**Sources:** [Stepsize Blog](https://www.stepsize.com/blog/software-maintenance-types), [Wikipedia](https://en.wikipedia.org/wiki/Code_refactoring)

## Gap Analysis: Current HtmlGraph System

### Current Collections

```python
# HtmlGraph collections (from SDK)
sdk.features    # User-facing functionality
sdk.bugs        # Defects/issues
sdk.chores      # Maintenance tasks
sdk.spikes      # Investigations
sdk.epics       # Large initiatives
sdk.tracks      # Multi-feature planning
sdk.phases      # Project phases
sdk.sessions    # Agent activity sessions
```

### Identified Gaps

#### Gap 1: No Event-Level Work Type Classification

**Problem:** Events have `feature_id` but no `work_type` field

**Impact:** Can't differentiate event types when analyzing session activity
```python
# Current event structure
{
    "event_id": "evt-abc123",
    "tool": "Bash",
    "feature_id": "feat-456",  # Links to feature but no work type
    "summary": "Run tests",
    "timestamp": "2024-12-22T10:30:00Z"
}
```

**Need:** Add `work_type` field to classify events as:
- `feature-implementation` - Building new functionality
- `spike-investigation` - Research/exploration
- `bug-fix` - Correcting defects
- `maintenance` - Refactoring, updates
- `documentation` - Writing docs
- `planning` - Design, architecture decisions
- `review` - Code review, testing

#### Gap 2: No Session-Level Work Categorization

**Problem:** Sessions don't have a primary work type or work mix breakdown

**Impact:** Can't answer "What kind of work was this session?"
```python
# Current session model
class Session(BaseModel):
    id: str
    agent: str
    status: str
    # Missing: primary_work_type, work_breakdown
```

**Need:** Add session-level categorization:
- `primary_work_type` - Dominant work type for session
- `work_breakdown` - Distribution of work types (% or count)

#### Gap 3: Limited Spike Categorization

**Problem:** Spikes exist but no subtype differentiation

**Impact:** Can't distinguish Technical vs Architectural vs Risk spikes

**Current:**
```python
# Generic spike - no categorization
spike = Spike(
    id="spike-001",
    title="Investigate OAuth providers",
    status="in-progress"
)
```

**Need:** Add spike subtypes:
- `technical` - Technical implementation research
- `architectural` - System design decisions
- `risk` - Risk identification and assessment

#### Gap 4: No Maintenance Subcategorization

**Problem:** Chores exist but no maintenance type classification

**Impact:** Can't differentiate Corrective vs Preventive vs Adaptive maintenance

**Current:**
```python
# Generic chore - no categorization
chore = Chore(
    id="chore-001",
    title="Refactor authentication module",
    status="todo"
)
```

**Need:** Add maintenance types:
- `corrective` - Fix defects
- `adaptive` - Adapt to environment changes
- `perfective` - Improve quality/performance
- `preventive` - Prevent future issues

#### Gap 5: No Analytics for Work Type Distribution

**Problem:** No SDK methods to query work type analytics

**Impact:** Can't answer questions like:
- "What % of time was exploratory vs implementation?"
- "How many events were feature work vs maintenance?"
- "What's the spike-to-feature ratio?"

**Need:** Add analytics queries:
```python
# Desired analytics API
stats = sdk.analytics.work_type_distribution(
    session_id="session-123"
)
# Returns: {"feature": 45%, "spike": 30%, "maintenance": 25%}

spike_sessions = sdk.sessions.where(primary_work_type="spike")
```

#### Gap 6: No Visual Differentiation in Dashboard

**Problem:** Dashboard doesn't visually distinguish work types

**Impact:** Can't quickly see work type mix at a glance

**Need:** Dashboard enhancements:
- Color-code events by work type
- Show work type distribution charts
- Filter sessions by primary work type
- Timeline view with work type indicators

## Proposed Solution

### Phase 1: Event-Level Classification

**1.1 Add `work_type` field to events**

Update `EventRecord` model:
```python
class EventRecord(BaseModel):
    event_id: str
    timestamp: datetime
    session_id: str
    agent: str
    tool: str
    summary: str
    success: bool
    feature_id: str | None = None
    work_type: WorkType | None = None  # NEW
    drift_score: float | None = None
    start_commit: str | None = None
    continued_from: str | None = None

class WorkType(str, Enum):
    FEATURE = "feature-implementation"
    SPIKE = "spike-investigation"
    BUG_FIX = "bug-fix"
    MAINTENANCE = "maintenance"
    DOCUMENTATION = "documentation"
    PLANNING = "planning"
    REVIEW = "review"
    ADMIN = "admin"
```

**1.2 Auto-infer work type from active work item**

```python
def infer_work_type(feature_id: str | None, sdk: SDK) -> WorkType | None:
    """Automatically infer work type from active feature/bug/spike/chore."""
    if not feature_id:
        return None

    # Check each collection
    if feature_id.startswith("feat-"):
        return WorkType.FEATURE
    elif feature_id.startswith("spike-"):
        spike = sdk.spikes.get(feature_id)
        return WorkType.SPIKE
    elif feature_id.startswith("bug-"):
        return WorkType.BUG_FIX
    elif feature_id.startswith("chore-"):
        chore = sdk.chores.get(feature_id)
        # Infer from chore metadata if available
        return WorkType.MAINTENANCE

    return None
```

### Phase 2: Work Item Subcategorization

**2.1 Add spike subtypes**

```python
class SpikeType(str, Enum):
    TECHNICAL = "technical"
    ARCHITECTURAL = "architectural"
    RISK = "risk"
    GENERAL = "general"

class Spike(BaseModel):
    id: str
    title: str
    spike_type: SpikeType = SpikeType.GENERAL  # NEW
    status: str
    timebox_hours: int | None = None  # NEW
    findings: str | None = None  # NEW
    decision: str | None = None  # NEW
```

**2.2 Add maintenance types**

```python
class MaintenanceType(str, Enum):
    CORRECTIVE = "corrective"
    ADAPTIVE = "adaptive"
    PERFECTIVE = "perfective"
    PREVENTIVE = "preventive"

class Chore(BaseModel):
    id: str
    title: str
    maintenance_type: MaintenanceType | None = None  # NEW
    status: str
    technical_debt_score: int | None = None  # NEW
```

### Phase 3: Session-Level Categorization

**3.1 Add session work type tracking**

```python
class Session(BaseModel):
    id: str
    agent: str
    status: str
    primary_work_type: WorkType | None = None  # NEW
    work_breakdown: dict[WorkType, int] | None = None  # NEW

    def calculate_work_breakdown(self, events_dir: str = ".htmlgraph/events") -> dict[WorkType, int]:
        """Calculate distribution of work types from events."""
        events = self.get_events(limit=None, events_dir=events_dir)
        breakdown = {}

        for evt in events:
            work_type = evt.get("work_type")
            if work_type:
                breakdown[work_type] = breakdown.get(work_type, 0) + 1

        return breakdown

    def calculate_primary_work_type(self) -> WorkType | None:
        """Determine primary work type based on event distribution."""
        breakdown = self.calculate_work_breakdown()
        if not breakdown:
            return None

        # Return work type with most events
        return max(breakdown, key=breakdown.get)
```

### Phase 4: Analytics API

**4.1 Add work type analytics methods**

```python
class Analytics:
    def __init__(self, sdk: SDK):
        self.sdk = sdk

    def work_type_distribution(
        self,
        session_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> dict[WorkType, float]:
        """
        Calculate work type distribution as percentages.

        Example:
            >>> analytics = sdk.analytics
            >>> dist = analytics.work_type_distribution(session_id="session-123")
            >>> print(dist)
            {
                "feature-implementation": 45.2,
                "spike-investigation": 28.3,
                "maintenance": 18.5,
                "documentation": 8.0
            }
        """
        pass

    def spike_to_feature_ratio(
        self,
        session_id: str | None = None
    ) -> float:
        """
        Calculate ratio of spike events to feature events.

        High ratio (>0.5) indicates research-heavy session.
        Low ratio (<0.2) indicates implementation-heavy session.
        """
        pass

    def maintenance_burden(
        self,
        session_id: str | None = None
    ) -> float:
        """
        Calculate percentage of work spent on maintenance vs new features.

        Returns value 0-100 representing maintenance %.
        """
        pass

# Add to SDK
class SDK:
    def __init__(self, agent: str = "claude"):
        # ... existing code ...
        self.analytics = Analytics(self)  # NEW
```

**4.2 Add session filtering by work type**

```python
# Query sessions by primary work type
exploratory_sessions = sdk.sessions.where(primary_work_type=WorkType.SPIKE)
implementation_sessions = sdk.sessions.where(primary_work_type=WorkType.FEATURE)

# Get work breakdown for project
total_breakdown = sdk.analytics.work_type_distribution()
```

### Phase 5: Dashboard Visualizations

**5.1 Work type color coding**

```css
/* Color scheme for work types */
.work-type-feature { background: #4CAF50; }  /* Green - building */
.work-type-spike { background: #2196F3; }    /* Blue - exploring */
.work-type-bug { background: #F44336; }      /* Red - fixing */
.work-type-maintenance { background: #FF9800; }  /* Orange - maintaining */
.work-type-documentation { background: #9C27B0; }  /* Purple - documenting */
.work-type-planning { background: #00BCD4; }  /* Cyan - planning */
.work-type-review { background: #FFEB3B; }    /* Yellow - reviewing */
```

**5.2 Dashboard charts**

Add to `dashboard/index.html`:
- **Pie chart**: Work type distribution for selected session
- **Stacked bar chart**: Work type timeline across sessions
- **Metric cards**:
  - Spike-to-feature ratio
  - Maintenance burden %
  - Primary work type
- **Filters**: Filter sessions by work type

**5.3 Session list enhancements**

```html
<!-- Session card with work type badge -->
<div class="session-card" data-session-id="session-123">
    <h3>Session ABC-123</h3>
    <span class="badge work-type-spike">Primary: Spike Investigation</span>

    <div class="work-breakdown">
        <div class="breakdown-bar">
            <div class="segment work-type-spike" style="width: 60%"></div>
            <div class="segment work-type-feature" style="width: 30%"></div>
            <div class="segment work-type-documentation" style="width: 10%"></div>
        </div>
        <div class="breakdown-legend">
            <span>Spike: 60%</span>
            <span>Feature: 30%</span>
            <span>Docs: 10%</span>
        </div>
    </div>
</div>
```

## Implementation Plan

### Sprint 1: Core Models (Week 1)

**Priority: HIGH**

- [ ] Add `WorkType` enum to models.py
- [ ] Update `EventRecord` with `work_type` field
- [ ] Add `SpikeType` enum and update Spike model
- [ ] Add `MaintenanceType` enum and update Chore model
- [ ] Update Session model with `primary_work_type` and `work_breakdown`
- [ ] Write migration script for existing data
- [ ] Update all tests
- [ ] Update SDK event creation to auto-infer work type

**Deliverable:** Models support work type classification

### Sprint 2: Analytics API (Week 2)

**Priority: HIGH**

- [ ] Create `Analytics` class in new `analytics.py` module
- [ ] Implement `work_type_distribution()` method
- [ ] Implement `spike_to_feature_ratio()` method
- [ ] Implement `maintenance_burden()` method
- [ ] Add `analytics` property to SDK
- [ ] Add session filtering by work type
- [ ] Write comprehensive tests
- [ ] Document analytics API in docs/SDK_ANALYTICS.md

**Deliverable:** Full analytics API for work type queries

### Sprint 3: Dashboard Visualizations (Week 3)

**Priority: MEDIUM**

- [ ] Add Chart.js library to dashboard
- [ ] Implement work type pie chart
- [ ] Implement work type timeline (stacked bar)
- [ ] Add metric cards (spike ratio, maintenance burden)
- [ ] Add work type color coding to session list
- [ ] Add work type filter to session list
- [ ] Add work breakdown bars to session cards
- [ ] Update dashboard CSS with work type colors

**Deliverable:** Visual dashboard for work type analysis

### Sprint 4: Agent Interface Updates (Week 4)

**Priority: MEDIUM**

- [ ] Update Claude Code skill with work type examples
- [ ] Update Gemini extension with work type examples
- [ ] Update Codex skill with work type examples
- [ ] Add work type guidance to WORKFLOW.md
- [ ] Create cookbook examples for work type usage
- [ ] Update quickstart guide

**Deliverable:** Agent interfaces document work type system

### Sprint 5: Documentation & Examples (Week 5)

**Priority: LOW**

- [ ] Write comprehensive guide: docs/WORK_TYPE_GUIDE.md
- [ ] Create example: examples/work-type-analytics/
- [ ] Add work type section to README.md
- [ ] Create blog post draft
- [ ] Record demo video
- [ ] Update API reference

**Deliverable:** Complete documentation and examples

## Expected Outcomes

### Answers These Questions

After implementation, users can answer:

1. **Session Analysis**
   - "What was the primary focus of this session?" → Check `session.primary_work_type`
   - "How much time was spent exploring vs building?" → Check spike vs feature percentages

2. **Project Health**
   - "What's our spike-to-feature ratio?" → `sdk.analytics.spike_to_feature_ratio()`
   - "Are we spending too much time on maintenance?" → `sdk.analytics.maintenance_burden()`

3. **Work Patterns**
   - "Which sessions were exploratory?" → `sdk.sessions.where(primary_work_type="spike")`
   - "What % of work was preventive vs corrective?" → Filter by maintenance type

4. **Trend Analysis**
   - "Is exploration increasing or decreasing over time?" → Timeline chart
   - "What's the distribution of work types this month?" → `work_type_distribution(start_date, end_date)`

### Benefits

1. **Better Session Context** - Quickly understand session purpose from work type
2. **Informed Planning** - See if project needs more exploration or implementation
3. **Health Metrics** - Track technical debt (maintenance burden), innovation (spike ratio)
4. **Attribution Clarity** - Differentiate "researching OAuth" from "implementing OAuth"
5. **Agent Coordination** - Assign agents based on work type expertise

## Alternative Approaches Considered

### Alternative 1: Tag-Based System

Instead of enum-based work types, use free-form tags:
```python
event.tags = ["exploratory", "authentication", "research"]
```

**Rejected because:**
- No standardization (typos, inconsistency)
- Harder to query and aggregate
- Less clear semantics

### Alternative 2: Separate Event Logs Per Work Type

Create separate `.jsonl` files for each work type:
```
.htmlgraph/events/session-123-features.jsonl
.htmlgraph/events/session-123-spikes.jsonl
.htmlgraph/events/session-123-maintenance.jsonl
```

**Rejected because:**
- Breaks chronological ordering
- Complex to query across work types
- More file I/O overhead

### Alternative 3: Work Type as Separate Collection

Create a new `WorkItem` collection that wraps features/spikes/bugs:
```python
work_item = WorkItem(
    id="work-001",
    type="spike",
    underlying_id="spike-123"
)
```

**Rejected because:**
- Adds unnecessary indirection
- Duplicates data
- Complicates queries

## Migration Strategy

### Backward Compatibility

**Phase 1: Additive Changes (v0.5.0)**
- Add new fields with `| None` defaults
- All existing code continues to work
- New fields are optional

**Phase 2: Auto-Migration (v0.5.1)**
- Run migration script to infer work types from existing data
- Populate `work_type` for historical events based on `feature_id` prefix
- Calculate `work_breakdown` for existing sessions

**Phase 3: Recommendations (v0.6.0)**
- Encourage explicit work type tagging
- Deprecation warnings for untyped events (but still works)

### Migration Script

```python
# scripts/migrate_work_types.py

from htmlgraph import SDK
from htmlgraph.models import WorkType

def migrate_events():
    """Add work_type to existing events based on feature_id."""
    sdk = SDK()

    # Get all sessions
    sessions = sdk.sessions.all()

    for session in sessions:
        events = session.get_events(limit=None)

        for evt in events:
            if evt.get("work_type"):
                continue  # Already has work type

            # Infer from feature_id
            feature_id = evt.get("feature_id")
            if not feature_id:
                continue

            if feature_id.startswith("feat-"):
                work_type = WorkType.FEATURE
            elif feature_id.startswith("spike-"):
                work_type = WorkType.SPIKE
            elif feature_id.startswith("bug-"):
                work_type = WorkType.BUG_FIX
            elif feature_id.startswith("chore-"):
                work_type = WorkType.MAINTENANCE
            else:
                continue

            # Update event (in-place edit of JSONL)
            evt["work_type"] = work_type
            # Write back to file...

def migrate_sessions():
    """Calculate work_breakdown for existing sessions."""
    sdk = SDK()

    sessions = sdk.sessions.all()

    for session in sessions:
        # Calculate and store work breakdown
        breakdown = session.calculate_work_breakdown()
        primary = session.calculate_primary_work_type()

        # Update session HTML
        with sdk.sessions.edit(session.id) as s:
            s.work_breakdown = breakdown
            s.primary_work_type = primary

if __name__ == "__main__":
    print("Migrating events...")
    migrate_events()

    print("Migrating sessions...")
    migrate_sessions()

    print("✅ Migration complete")
```

## Summary

This proposal adds systematic work type categorization to HtmlGraph, enabling:

1. **Event-level classification** - Tag events as feature/spike/bug/maintenance/etc
2. **Session-level analysis** - See work type distribution per session
3. **Project-level metrics** - Calculate spike ratios, maintenance burden
4. **Visual differentiation** - Color-coded dashboard with charts
5. **Better attribution** - Distinguish exploratory from implementation work

**Implementation**: 5 sprints (5 weeks)
**Priority**: HIGH (addresses core user need)
**Breaking Changes**: None (fully backward compatible)
**Dependencies**: None (builds on existing SDK)

---

**Next Steps:**
1. Review and approve this proposal
2. Create feature for Sprint 1 implementation
3. Start with core models and work type enums
4. Iterate based on feedback
