"""
Type definitions for HtmlGraph SDK return types.

Provides TypedDict definitions for SDK methods that return dictionaries,
improving developer experience with better type hints and IDE autocomplete.

These complement the Pydantic models in dependency_models.py by providing
type hints for dict-based return values used in the SDK for backward compatibility.
"""

import sys
from typing import Literal, TypedDict

# NotRequired was added in Python 3.11
if sys.version_info >= (3, 11):
    from typing import NotRequired
else:
    from typing_extensions import NotRequired

# ============================================================================
# Analytics Return Types
# ============================================================================


class BottleneckDict(TypedDict):
    """Bottleneck task information from find_bottlenecks()."""

    id: str
    title: str
    status: str
    priority: str
    blocks_count: int  # Number of tasks this blocks (transitive)
    impact_score: float  # Weighted impact score
    blocked_tasks: list[str]  # List of blocked task IDs


class WorkRecommendation(TypedDict):
    """Work recommendation from recommend_next_work()."""

    id: str
    title: str
    priority: str
    score: float  # Priority score
    reasons: list[str]  # Human-readable reasons for recommendation
    estimated_hours: NotRequired[float]  # Effort estimate
    unlocks_count: int  # Number of tasks this unlocks
    unlocks: list[str]  # Task IDs that become available


class ParallelWorkInfo(TypedDict):
    """Parallel work opportunities from get_parallel_work()."""

    max_parallelism: int  # Maximum number of parallel tasks
    ready_now: list[str]  # Tasks ready to start immediately
    total_ready: int  # Total count of ready tasks
    level_count: int  # Number of dependency levels
    next_level: list[str]  # Tasks in next dependency level


class RiskAssessmentDict(TypedDict):
    """Risk assessment from assess_risks()."""

    high_risk_count: int
    high_risk_tasks: list["HighRiskTask"]
    circular_dependencies: list[list[str]]
    orphaned_count: int
    orphaned_tasks: list[str]
    recommendations: list[str]


class HighRiskTask(TypedDict):
    """Individual high-risk task information."""

    id: str
    title: str
    risk_score: float
    risk_factors: list[str]


class ImpactAnalysisDict(TypedDict):
    """Impact analysis from analyze_impact()."""

    node_id: str
    direct_dependents: int
    total_impact: int  # Transitive dependents
    completion_impact: float  # Percentage of work this unlocks
    unlocks_count: int
    affected_tasks: list[str]


# ============================================================================
# Session Management Return Types
# ============================================================================


class SessionStartInfo(TypedDict):
    """Comprehensive session start information from get_session_start_info()."""

    status: "ProjectStatus"
    active_work: NotRequired["ActiveWorkItem"]  # None if no active work
    features: list["FeatureSummary"]
    sessions: list["SessionSummary"]
    git_log: NotRequired[list[str]]  # Recent commit messages
    analytics: "SessionAnalytics"


class ProjectStatus(TypedDict):
    """Project status metrics."""

    total_nodes: int
    in_progress_count: int
    todo_count: int
    done_count: int
    blocked_count: int


class ActiveWorkItem(TypedDict):
    """Currently active work item details."""

    id: str
    title: str
    type: Literal["feature", "bug", "spike", "chore", "epic"]
    status: str
    agent: NotRequired[str]  # Assigned agent
    steps_total: int
    steps_completed: int
    auto_generated: NotRequired[bool]  # For spikes
    spike_subtype: NotRequired[str]  # For spikes


class FeatureSummary(TypedDict):
    """Feature summary for session start."""

    id: str
    title: str
    status: str
    priority: str
    steps_total: int
    steps_completed: int


class SessionSummary(TypedDict):
    """Session summary information."""

    id: str
    status: str
    agent: str
    event_count: int
    started: NotRequired[str]  # ISO timestamp


class SessionAnalytics(TypedDict):
    """Strategic analytics for session start."""

    bottlenecks: list[BottleneckDict]
    recommendations: list[WorkRecommendation]
    parallel: ParallelWorkInfo


# ============================================================================
# Work Queue Return Types
# ============================================================================


class WorkQueueItem(TypedDict):
    """Work queue item from get_work_queue()."""

    task_id: str
    title: str
    status: str
    priority: str
    score: float  # Routing score
    type: str  # Work item type
    complexity: NotRequired[str]
    effort: NotRequired[float]
    agent_assigned: NotRequired[str]
    blocks_count: int
    blocked_by: list[str]


# ============================================================================
# Planning Return Types
# ============================================================================


class SmartPlanResult(TypedDict):
    """Result from smart_plan()."""

    type: Literal["spike", "track"]
    spike_id: NotRequired[str]  # Present if type="spike"
    track_id: NotRequired[str]  # Present if type="track"
    title: str
    status: NotRequired[str]  # For spikes
    timebox_hours: NotRequired[float]  # For spikes
    has_spec: NotRequired[bool]  # For tracks
    has_plan: NotRequired[bool]  # For tracks
    priority: NotRequired[str]  # For tracks
    project_context: "PlanningContext"
    research_informed: bool
    next_steps: list[str]
    warnings: NotRequired[list[str]]


class PlanningContext(TypedDict):
    """Project context for planning."""

    bottlenecks_count: int
    high_risk_count: int
    parallel_capacity: int
    description: str


class TrackCreationResult(TypedDict):
    """Result from create_track_from_plan()."""

    track_id: str
    title: str
    has_spec: bool
    has_plan: bool
    spike_id: NotRequired[str]  # Original planning spike
    priority: str


# ============================================================================
# Orchestration Return Types
# ============================================================================


class SubagentPrompt(TypedDict):
    """Subagent prompt from spawn_explorer() or spawn_coder().

    This TypedDict represents the return value from SDK methods that spawn
    subagents for specialized tasks like code exploration or implementation.

    Fields:
        prompt: The full prompt text for the subagent
        description: Short description of the subagent's task
        subagent_type: Type of subagent ("Explore", "Code", etc.)
    """

    prompt: str
    description: str
    subagent_type: str


class OrchestrationResult(TypedDict):
    """Result from orchestrate() method.

    Contains prompts for a two-phase feature implementation workflow:
    1. Explorer discovers relevant code and patterns
    2. Coder implements the feature based on explorer findings

    Fields:
        explorer: Prompt for the explorer subagent
        coder: Prompt for the coder subagent
        workflow: Step-by-step workflow instructions
    """

    explorer: SubagentPrompt
    coder: SubagentPrompt
    workflow: list[str]  # Step-by-step workflow


# Type aliases for specific spawning methods
SpawnExplorerResult = SubagentPrompt
"""Return type for spawn_explorer() - same structure as SubagentPrompt."""

SpawnCoderResult = SubagentPrompt
"""Return type for spawn_coder() - same structure as SubagentPrompt."""


# ============================================================================
# Parallel Work Return Types
# ============================================================================


class ParallelPlanResult(TypedDict):
    """Result from plan_parallel_work()."""

    can_parallelize: bool
    max_parallelism: int
    ready_tasks: list[str]
    blocked_tasks: list[str]
    speedup_factor: float
    recommendation: str
    warnings: list[str]
    prompts: list["TaskPrompt"]
    task_count: NotRequired[int]
    guidelines: NotRequired["ParallelGuidelines"]
    reason: NotRequired[str]  # If can_parallelize=False


class TaskPrompt(TypedDict):
    """Individual task prompt for parallel execution."""

    prompt: str
    description: str
    task_id: str


class ParallelGuidelines(TypedDict):
    """Guidelines for parallel execution."""

    dispatch: str
    patterns: list[str]
    avoid: list[str]


class AggregateResultsDict(TypedDict):
    """Result from aggregate_parallel_results()."""

    total_agents: int
    successful: int
    failed: int
    total_duration_seconds: float
    parallel_speedup: float
    avg_health_score: float
    total_anti_patterns: int
    files_modified: list[str]
    conflicts: list[str]
    recommendations: list[str]
    validation: dict[str, bool]
    all_passed: bool
