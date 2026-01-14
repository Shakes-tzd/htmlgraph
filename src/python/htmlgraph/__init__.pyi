"""
Type stub for htmlgraph package.

This stub provides type information for mypy when the SDK class
is loaded dynamically via importlib at runtime.
"""

from pathlib import Path
from typing import Any

from htmlgraph.agent_detection import detect_agent_name as detect_agent_name
from htmlgraph.agent_detection import get_agent_display_name as get_agent_display_name
from htmlgraph.agents import AgentInterface as AgentInterface
from htmlgraph.analytics import Analytics as Analytics

# Analytics
from htmlgraph.analytics import CrossSessionAnalytics
from htmlgraph.analytics import DependencyAnalytics as DependencyAnalytics
from htmlgraph.atomic_ops import AtomicFileWriter as AtomicFileWriter
from htmlgraph.atomic_ops import DirectoryLocker as DirectoryLocker
from htmlgraph.atomic_ops import atomic_rename as atomic_rename
from htmlgraph.atomic_ops import (
    cleanup_orphaned_temp_files as cleanup_orphaned_temp_files,
)
from htmlgraph.atomic_ops import safe_temp_file as safe_temp_file
from htmlgraph.atomic_ops import validate_atomic_write as validate_atomic_write
from htmlgraph.builders import BaseBuilder as BaseBuilder
from htmlgraph.builders import FeatureBuilder as FeatureBuilder
from htmlgraph.builders import SpikeBuilder as SpikeBuilder
from htmlgraph.collections import BaseCollection as BaseCollection

# Collections
from htmlgraph.collections import (
    BugCollection,
    ChoreCollection,
    EpicCollection,
    PhaseCollection,
    TaskDelegationCollection,
    TodoCollection,
)
from htmlgraph.collections import FeatureCollection as FeatureCollection
from htmlgraph.collections import SpikeCollection as SpikeCollection
from htmlgraph.collections.insight import InsightCollection
from htmlgraph.collections.metric import MetricCollection
from htmlgraph.collections.pattern import PatternCollection
from htmlgraph.collections.session import SessionCollection
from htmlgraph.context_analytics import ContextAnalytics as ContextAnalytics
from htmlgraph.context_analytics import ContextUsage as ContextUsage
from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.decorators import RetryError as RetryError
from htmlgraph.decorators import retry as retry
from htmlgraph.decorators import retry_async as retry_async
from htmlgraph.edge_index import EdgeIndex as EdgeIndex
from htmlgraph.edge_index import EdgeRef as EdgeRef
from htmlgraph.exceptions import ClaimConflictError as ClaimConflictError
from htmlgraph.exceptions import HtmlGraphError as HtmlGraphError
from htmlgraph.exceptions import NodeNotFoundError as NodeNotFoundError
from htmlgraph.exceptions import SessionNotFoundError as SessionNotFoundError
from htmlgraph.exceptions import ValidationError as ValidationError
from htmlgraph.find_api import FindAPI as FindAPI
from htmlgraph.find_api import find as find
from htmlgraph.find_api import find_all as find_all
from htmlgraph.graph import CompiledQuery as CompiledQuery
from htmlgraph.graph import HtmlGraph as HtmlGraph
from htmlgraph.ids import generate_hierarchical_id as generate_hierarchical_id
from htmlgraph.ids import generate_id as generate_id
from htmlgraph.ids import is_legacy_id as is_legacy_id
from htmlgraph.ids import is_valid_id as is_valid_id
from htmlgraph.ids import parse_id as parse_id
from htmlgraph.learning import LearningPersistence as LearningPersistence
from htmlgraph.learning import (
    auto_persist_on_session_end as auto_persist_on_session_end,
)
from htmlgraph.models import ActivityEntry as ActivityEntry
from htmlgraph.models import AggregatedMetric as AggregatedMetric
from htmlgraph.models import Chore as Chore
from htmlgraph.models import ContextSnapshot as ContextSnapshot
from htmlgraph.models import Edge as Edge
from htmlgraph.models import Graph as Graph
from htmlgraph.models import MaintenanceType as MaintenanceType
from htmlgraph.models import Node as Node
from htmlgraph.models import Pattern as Pattern
from htmlgraph.models import Session as Session
from htmlgraph.models import SessionInsight as SessionInsight
from htmlgraph.models import Spike as Spike
from htmlgraph.models import SpikeType as SpikeType
from htmlgraph.models import Step as Step
from htmlgraph.models import WorkType as WorkType
from htmlgraph.orchestration import delegate_with_id as delegate_with_id
from htmlgraph.orchestration import generate_task_id as generate_task_id
from htmlgraph.orchestration import get_results_by_task_id as get_results_by_task_id
from htmlgraph.orchestration import parallel_delegate as parallel_delegate
from htmlgraph.orchestrator_mode import OrchestratorMode as OrchestratorMode
from htmlgraph.orchestrator_mode import (
    OrchestratorModeManager as OrchestratorModeManager,
)
from htmlgraph.parallel import AggregateResult as AggregateResult
from htmlgraph.parallel import ParallelAnalysis as ParallelAnalysis
from htmlgraph.parallel import ParallelWorkflow as ParallelWorkflow
from htmlgraph.query_builder import Condition as Condition
from htmlgraph.query_builder import Operator as Operator
from htmlgraph.query_builder import QueryBuilder as QueryBuilder
from htmlgraph.reflection import ComputationalReflection as ComputationalReflection
from htmlgraph.reflection import get_reflection_context as get_reflection_context
from htmlgraph.refs import RefManager
from htmlgraph.repo_hash import RepoHash as RepoHash
from htmlgraph.sdk.analytics import AnalyticsEngine
from htmlgraph.server import serve as serve
from htmlgraph.session_manager import SessionManager as SessionManager
from htmlgraph.session_registry import SessionRegistry as SessionRegistry
from htmlgraph.system_prompts import SystemPromptManager
from htmlgraph.track_builder import TrackCollection
from htmlgraph.types import ActiveWorkItem as ActiveWorkItem
from htmlgraph.types import AggregateResultsDict as AggregateResultsDict
from htmlgraph.types import BottleneckDict as BottleneckDict
from htmlgraph.types import FeatureSummary as FeatureSummary
from htmlgraph.types import HighRiskTask as HighRiskTask
from htmlgraph.types import ImpactAnalysisDict as ImpactAnalysisDict
from htmlgraph.types import OrchestrationResult as OrchestrationResult
from htmlgraph.types import ParallelGuidelines as ParallelGuidelines
from htmlgraph.types import ParallelPlanResult as ParallelPlanResult
from htmlgraph.types import ParallelWorkInfo as ParallelWorkInfo
from htmlgraph.types import PlanningContext as PlanningContext
from htmlgraph.types import ProjectStatus as ProjectStatus
from htmlgraph.types import RiskAssessmentDict as RiskAssessmentDict
from htmlgraph.types import SessionAnalytics as SessionAnalytics
from htmlgraph.types import SessionStartInfo as SessionStartInfo
from htmlgraph.types import SessionSummary as SessionSummary
from htmlgraph.types import SmartPlanResult as SmartPlanResult
from htmlgraph.types import SubagentPrompt as SubagentPrompt
from htmlgraph.types import TaskPrompt as TaskPrompt
from htmlgraph.types import TrackCreationResult as TrackCreationResult
from htmlgraph.types import WorkQueueItem as WorkQueueItem
from htmlgraph.types import WorkRecommendation as WorkRecommendation
from htmlgraph.work_type_utils import infer_work_type as infer_work_type
from htmlgraph.work_type_utils import infer_work_type_from_id as infer_work_type_from_id

__version__: str

class SDK:
    """
    Main SDK interface for AI agents.

    Type stub to provide static type information for mypy.
    The actual implementation is in sdk.py.
    """

    # Core attributes
    _directory: Path
    _agent_id: str | None
    _parent_session: str | None
    _db: HtmlGraphDB
    _graph: HtmlGraph
    _bugs_graph: HtmlGraph
    _agent_interface: AgentInterface
    _orchestrator: Any
    _system_prompts: SystemPromptManager | None
    _analytics_engine: AnalyticsEngine

    # Collection interfaces
    features: FeatureCollection
    bugs: BugCollection
    chores: ChoreCollection
    spikes: SpikeCollection
    epics: EpicCollection
    phases: PhaseCollection
    sessions: SessionCollection
    tracks: TrackCollection
    agents: BaseCollection[Any]
    patterns: PatternCollection
    insights: InsightCollection
    metrics: MetricCollection
    todos: TodoCollection
    task_delegations: TaskDelegationCollection

    # Session manager
    session_manager: SessionManager

    # Refs manager
    refs: RefManager

    def __init__(
        self,
        directory: Path | str | None = None,
        agent: str | None = None,
        parent_session: str | None = None,
        db_path: str | None = None,
    ) -> None: ...
    @property
    def agent(self) -> str | None: ...
    @property
    def system_prompts(self) -> SystemPromptManager: ...
    @property
    def analytics(self) -> Analytics: ...
    @property
    def dep_analytics(self) -> DependencyAnalytics: ...
    @property
    def cross_session_analytics(self) -> CrossSessionAnalytics: ...
    @property
    def context(self) -> ContextAnalytics: ...
    @property
    def pattern_learning(self) -> Any: ...
    @property
    def orchestrator(self) -> Any: ...
    def dismiss_session_warning(self) -> bool: ...
    def get_warning_status(self) -> dict[str, Any]: ...
    def ref(self, short_ref: str) -> Node | None: ...
    def db(self) -> HtmlGraphDB: ...
    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
    def execute_query_builder(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> list[dict[str, Any]]: ...
    def export_to_html(
        self,
        output_dir: str | None = None,
        include_features: bool = True,
        include_sessions: bool = True,
        include_events: bool = False,
    ) -> dict[str, int]: ...
    def _log_event(
        self,
        event_type: str,
        tool_name: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        context: dict[str, Any] | None = None,
        cost_tokens: int = 0,
    ) -> bool: ...
    def reload(self) -> None: ...
    def summary(self, max_items: int = 10) -> str: ...
    def my_work(self) -> dict[str, Any]: ...
    def next_task(
        self, priority: str | None = None, auto_claim: bool = True
    ) -> Node | None: ...
    def get_status(self) -> dict[str, Any]: ...
    def dedupe_sessions(
        self,
        max_events: int = 1,
        move_dir_name: str = "_orphans",
        dry_run: bool = False,
        stale_extra_active: bool = True,
    ) -> dict[str, int]: ...
    def track_activity(
        self,
        tool: str,
        summary: str,
        file_paths: list[str] | None = None,
        success: bool = True,
        feature_id: str | None = None,
        session_id: str | None = None,
        parent_activity_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any: ...
    def spawn_explorer(
        self,
        task: str,
        scope: str | None = None,
        patterns: list[str] | None = None,
        questions: list[str] | None = None,
    ) -> dict[str, Any]: ...
    def spawn_coder(
        self,
        feature_id: str,
        task: str,
        context: str | None = None,
        constraints: list[str] | None = None,
    ) -> dict[str, Any]: ...
    def orchestrate(
        self,
        goal: str,
        exploration_scope: str | None = None,
        implementation_feature: str | None = None,
    ) -> dict[str, Any]: ...
    def help(self, topic: str | None = None) -> dict[str, Any]: ...

    # Session management (from SessionManagerMixin)
    def start_session(
        self,
        session_id: str | None = None,
        title: str | None = None,
        agent: str | None = None,
    ) -> Any: ...
    def end_session(
        self,
        session_id: str,
        handoff_notes: str | None = None,
        recommended_next: str | None = None,
        blockers: list[str] | None = None,
    ) -> Any: ...
    def _ensure_session_exists(
        self, session_id: str, parent_event_id: str | None = None
    ) -> None: ...

    # Session handoff (from SessionHandoffMixin)
    def prepare_handoff(
        self,
        session_id: str | None = None,
        notes: str | None = None,
        recommended_next: str | None = None,
        blockers: list[str] | None = None,
    ) -> dict[str, Any]: ...
    def receive_handoff(self, handoff_context: dict[str, Any]) -> dict[str, Any]: ...

    # Session continuity (from SessionContinuityMixin)
    def get_session_continuity(
        self, session_id: str | None = None
    ) -> dict[str, Any]: ...
    def restore_session_context(self, continuity_data: dict[str, Any]) -> bool: ...

    # Planning (from PlanningMixin)
    def find_bottlenecks(self, top_n: int = 5) -> list[BottleneckDict]: ...
    def get_parallel_work(self, max_agents: int = 5) -> dict[str, Any]: ...
    def recommend_next_work(
        self,
        agent_count: int = 1,
        include_reasons: bool = True,
    ) -> list[WorkRecommendation]: ...
    def assess_risks(self) -> RiskAssessmentDict: ...
    def analyze_impact(self, node_id: str) -> ImpactAnalysisDict: ...
    def get_work_queue(
        self,
        max_items: int = 10,
        include_blocked: bool = False,
    ) -> list[WorkQueueItem]: ...
    def work_next(self) -> ActiveWorkItem | None: ...
    def start_planning_spike(
        self,
        title: str,
        questions: list[str] | None = None,
    ) -> Any: ...
    def create_track_from_plan(
        self,
        spike_id: str,
        track_title: str | None = None,
    ) -> TrackCreationResult: ...
    def smart_plan(
        self,
        goal: str,
        constraints: list[str] | None = None,
        max_features: int = 10,
    ) -> SmartPlanResult: ...
    def plan_parallel_work(
        self,
        available_agents: int = 3,
        work_items: list[str] | None = None,
    ) -> ParallelPlanResult: ...
    def aggregate_parallel_results(
        self,
        task_ids: list[str],
        timeout_seconds: int = 300,
    ) -> AggregateResultsDict: ...

    # Session start info
    def get_session_start_info(
        self,
        include_git_log: bool = True,
        git_log_count: int = 5,
        analytics_top_n: int = 3,
        analytics_max_agents: int = 3,
    ) -> SessionStartInfo: ...

    # Active work item
    def get_active_work_item(
        self,
        agent: str | None = None,
        filter_by_agent: bool = False,
        work_types: list[str] | None = None,
    ) -> ActiveWorkItem | None: ...

__all__: list[str]
