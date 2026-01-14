"""
Type stub for htmlgraph package.

This stub provides type information for mypy when the SDK class
is loaded dynamically via importlib at runtime.
"""

from htmlgraph.agent_detection import detect_agent_name as detect_agent_name
from htmlgraph.agent_detection import get_agent_display_name as get_agent_display_name
from htmlgraph.agents import AgentInterface as AgentInterface
from htmlgraph.analytics import Analytics as Analytics

# Analytics
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
from htmlgraph.collections import FeatureCollection as FeatureCollection
from htmlgraph.collections import SpikeCollection as SpikeCollection
from htmlgraph.context_analytics import ContextAnalytics as ContextAnalytics
from htmlgraph.context_analytics import ContextUsage as ContextUsage
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
from htmlgraph.repo_hash import RepoHash as RepoHash
from htmlgraph.sdk.core import SDK as SDK
from htmlgraph.server import serve as serve
from htmlgraph.session_manager import SessionManager as SessionManager
from htmlgraph.session_registry import SessionRegistry as SessionRegistry
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

# SDK is imported from htmlgraph.sdk.core (see import above)
# Re-exported here for backward compatibility

__all__: list[str]
