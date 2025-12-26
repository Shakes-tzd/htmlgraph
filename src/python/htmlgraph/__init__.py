"""
HtmlGraph - HTML is All You Need

A lightweight graph database framework using HTML files as nodes,
hyperlinks as edges, and CSS selectors as the query language.
"""

from htmlgraph.exceptions import (
    HtmlGraphError,
    NodeNotFoundError,
    SessionNotFoundError,
    ClaimConflictError,
    ValidationError,
)
from htmlgraph.models import (
    Node,
    Edge,
    Step,
    Graph,
    Session,
    ActivityEntry,
    ContextSnapshot,
    Spike,
    Chore,
    WorkType,
    SpikeType,
    MaintenanceType,
)
from htmlgraph.graph import HtmlGraph
from htmlgraph.edge_index import EdgeIndex, EdgeRef
from htmlgraph.query_builder import QueryBuilder, Condition, Operator
from htmlgraph.find_api import FindAPI, find, find_all
from htmlgraph.agents import AgentInterface
from htmlgraph.server import serve
from htmlgraph.session_manager import SessionManager
from htmlgraph.sdk import SDK
from htmlgraph.analytics import Analytics, DependencyAnalytics
from htmlgraph.context_analytics import ContextAnalytics, ContextUsage
from htmlgraph.ids import generate_id, generate_hierarchical_id, parse_id, is_valid_id, is_legacy_id
from htmlgraph.work_type_utils import infer_work_type, infer_work_type_from_id
from htmlgraph.builders import BaseBuilder, FeatureBuilder, SpikeBuilder
from htmlgraph.collections import BaseCollection, FeatureCollection, SpikeCollection
from htmlgraph.agent_detection import detect_agent_name, get_agent_display_name
from htmlgraph.parallel import ParallelWorkflow, ParallelAnalysis, AggregateResult
from htmlgraph.types import (
    BottleneckDict,
    WorkRecommendation,
    ParallelWorkInfo,
    RiskAssessmentDict,
    HighRiskTask,
    ImpactAnalysisDict,
    SessionStartInfo,
    ProjectStatus,
    ActiveWorkItem,
    FeatureSummary,
    SessionSummary,
    SessionAnalytics,
    WorkQueueItem,
    SmartPlanResult,
    PlanningContext,
    TrackCreationResult,
    SubagentPrompt,
    OrchestrationResult,
    ParallelPlanResult,
    TaskPrompt,
    ParallelGuidelines,
    AggregateResultsDict,
)

__version__ = "0.13.3"
__all__ = [
    # Exceptions
    "HtmlGraphError",
    "NodeNotFoundError",
    "SessionNotFoundError",
    "ClaimConflictError",
    "ValidationError",
    # Core models
    "Node",
    "Edge",
    "Step",
    "Graph",
    "Session",
    "ActivityEntry",
    "ContextSnapshot",
    "Spike",
    "Chore",
    # Work type classification (Phase 1)
    "WorkType",
    "SpikeType",
    "MaintenanceType",
    # Graph operations
    "HtmlGraph",
    "EdgeIndex",
    "EdgeRef",
    "QueryBuilder",
    "Condition",
    "Operator",
    "FindAPI",
    "find",
    "find_all",
    "AgentInterface",
    "SessionManager",
    "SDK",
    "Analytics",  # Phase 2: Work Type Analytics
    "DependencyAnalytics",  # Advanced dependency-aware analytics
    "ContextAnalytics",  # Context usage tracking and analytics
    "ContextUsage",  # Context usage data structure
    "serve",
    # ID generation (collision-resistant, multi-agent safe)
    "generate_id",
    "generate_hierarchical_id",
    "parse_id",
    "is_valid_id",
    "is_legacy_id",
    # Work type utilities
    "infer_work_type",
    "infer_work_type_from_id",
    # Builders (modular SDK components)
    "BaseBuilder",
    "FeatureBuilder",
    "SpikeBuilder",
    # Collections (modular SDK components)
    "BaseCollection",
    "FeatureCollection",
    "SpikeCollection",
    # Agent detection
    "detect_agent_name",
    "get_agent_display_name",
    # Parallel workflow coordination
    "ParallelWorkflow",
    "ParallelAnalysis",
    "AggregateResult",
    # Type definitions (TypedDict for SDK return types)
    "BottleneckDict",
    "WorkRecommendation",
    "ParallelWorkInfo",
    "RiskAssessmentDict",
    "HighRiskTask",
    "ImpactAnalysisDict",
    "SessionStartInfo",
    "ProjectStatus",
    "ActiveWorkItem",
    "FeatureSummary",
    "SessionSummary",
    "SessionAnalytics",
    "WorkQueueItem",
    "SmartPlanResult",
    "PlanningContext",
    "TrackCreationResult",
    "SubagentPrompt",
    "OrchestrationResult",
    "ParallelPlanResult",
    "TaskPrompt",
    "ParallelGuidelines",
    "AggregateResultsDict",
]
