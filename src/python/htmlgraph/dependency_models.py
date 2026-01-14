from __future__ import annotations

"""
Data models for dependency analytics.

Provides Pydantic models for dependency-aware analytics results including:
- Critical path analysis
- Bottleneck detection
- Parallelization opportunities
- Risk assessment
- Work prioritization
"""


from typing import Literal

from pydantic import BaseModel, Field


class CriticalPathNode(BaseModel):
    """Node on critical path with timing information."""

    id: str
    title: str
    est: int = 0  # Earliest start time
    lst: int = 0  # Latest start time
    slack: float = 0.0  # LST - EST (0 = critical)
    effort: float = 0.0
    status: str = "todo"


class CriticalPathResult(BaseModel):
    """Result of critical path analysis."""

    path: list[str] = Field(default_factory=list)  # Node IDs on critical path
    length: int = 0  # Number of nodes
    total_effort: float = 0.0  # Sum of effort estimates
    nodes: list[CriticalPathNode] = Field(default_factory=list)
    bottlenecks: list[str] = Field(default_factory=list)  # High-impact nodes


class BottleneckNode(BaseModel):
    """Node identified as a bottleneck."""

    id: str
    title: str
    status: str
    priority: str
    completion_pct: float = 0.0
    direct_blocking: int = 0  # Immediate dependents
    transitive_blocking: int = 0  # All downstream nodes
    weighted_impact: float = 0.0  # Calculated impact score
    blocked_nodes: list[str] = Field(default_factory=list)


class ParallelLevel(BaseModel):
    """Group of nodes at same dependency level."""

    level: int
    nodes: list[str] = Field(default_factory=list)
    max_parallel: int = 0
    independent_groups: list[list[str]] = Field(default_factory=list)


class ParallelizationReport(BaseModel):
    """Analysis of parallelization opportunities."""

    max_parallelism: int = 0
    dependency_levels: list[ParallelLevel] = Field(default_factory=list)
    suggested_assignments: list[tuple[str, list[str]]] = Field(default_factory=list)


class RiskFactor(BaseModel):
    """Individual risk factor for a node."""

    type: Literal["spof", "deep_chain", "circular", "orphan"]
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    mitigation: str


class RiskNode(BaseModel):
    """Node with identified risks."""

    id: str
    title: str
    risk_score: float = 0.0  # 0.0-1.0
    risk_factors: list[RiskFactor] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Overall risk assessment."""

    high_risk: list[RiskNode] = Field(default_factory=list)
    circular_dependencies: list[list[str]] = Field(default_factory=list)
    orphaned_nodes: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class HealthIndicator(BaseModel):
    """Individual health metric indicator."""

    metric: str
    value: float
    status: Literal["healthy", "warning", "critical"]
    threshold: float | None = None
    message: str = ""


class HealthReport(BaseModel):
    """Overall dependency health."""

    score: float = 0.0  # 0.0-1.0
    metrics: dict[str, float] = Field(default_factory=dict)
    health_indicators: list[HealthIndicator] = Field(default_factory=list)


class TaskRecommendation(BaseModel):
    """Recommended task to work on."""

    id: str
    title: str
    priority: str
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    estimated_effort: float = 0.0
    unlocks: list[str] = Field(default_factory=list)  # What becomes available


class TaskRecommendations(BaseModel):
    """Set of task recommendations."""

    recommendations: list[TaskRecommendation] = Field(default_factory=list)
    parallel_suggestions: list[list[str]] = Field(default_factory=list)


class ImpactAnalysis(BaseModel):
    """Downstream impact analysis for a node."""

    node_id: str
    direct_dependents: int = 0
    transitive_dependents: int = 0
    affected_nodes: list[str] = Field(default_factory=list)
    completion_impact: float = 0.0  # % of total work this unlocks


class WhatIfResult(BaseModel):
    """Result of what-if completion simulation."""

    completed_nodes: list[str] = Field(default_factory=list)
    newly_available: list[str] = Field(default_factory=list)
    total_unlocked: int = 0
    parallelism_increase: int = 0
