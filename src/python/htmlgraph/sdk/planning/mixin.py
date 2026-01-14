"""Planning mixin for SDK - integrates all planning functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.models import Node
    from htmlgraph.types import BottleneckDict


class PlanningMixin:
    """
    Mixin class providing planning and recommendation methods to SDK.

    This mixin delegates to specialized planning modules for:
    - Bottleneck identification (bottlenecks.py)
    - Parallel work detection (parallel.py)
    - Smart recommendations (recommendations.py)
    - Work queue management (queue.py)
    - Planning spike creation (smart_planning.py)
    - Track creation from plans (smart_planning.py)
    """

    # =========================================================================
    # Strategic Planning & Analytics (Agent-Friendly Interface)
    # =========================================================================

    def find_bottlenecks(self, top_n: int = 5) -> list[BottleneckDict]:
        """
        Identify tasks blocking the most downstream work.

        Delegates to sdk.planning.bottlenecks.find_bottlenecks()
        """
        from htmlgraph.sdk.planning.bottlenecks import find_bottlenecks

        return find_bottlenecks(self, top_n=top_n)  # type: ignore[arg-type]

    def get_parallel_work(self, max_agents: int = 5) -> dict[str, Any]:
        """
        Find tasks that can be worked on simultaneously.

        Delegates to sdk.planning.parallel.get_parallel_work()
        """
        from htmlgraph.sdk.planning.parallel import get_parallel_work

        return get_parallel_work(self, max_agents=max_agents)  # type: ignore[arg-type]

    def recommend_next_work(self, agent_count: int = 1) -> list[dict[str, Any]]:
        """
        Get smart recommendations for what to work on next.

        Delegates to sdk.planning.recommendations.recommend_next_work()
        """
        from htmlgraph.sdk.planning.recommendations import recommend_next_work

        return recommend_next_work(self, agent_count=agent_count)  # type: ignore[arg-type]

    def assess_risks(self) -> dict[str, Any]:
        """
        Assess dependency-related risks in the project.

        Delegates to sdk.planning.bottlenecks.assess_risks()
        """
        from htmlgraph.sdk.planning.bottlenecks import assess_risks

        return assess_risks(self)  # type: ignore[arg-type]

    def analyze_impact(self, node_id: str) -> dict[str, Any]:
        """
        Analyze the impact of completing a specific task.

        Delegates to sdk.planning.recommendations.analyze_impact()
        """
        from htmlgraph.sdk.planning.recommendations import analyze_impact

        return analyze_impact(self, node_id)  # type: ignore[arg-type]

    def get_work_queue(
        self, agent_id: str | None = None, limit: int = 10, min_score: float = 0.0
    ) -> list[dict[str, Any]]:
        """
        Get prioritized work queue showing recommended work, active work, and dependencies.

        Delegates to sdk.planning.queue.get_work_queue()
        """
        from htmlgraph.sdk.planning.queue import get_work_queue

        return get_work_queue(self, agent_id=agent_id, limit=limit, min_score=min_score)  # type: ignore[arg-type]

    def work_next(
        self,
        agent_id: str | None = None,
        auto_claim: bool = False,
        min_score: float = 0.0,
    ) -> Node | None:
        """
        Get the next best task for an agent using smart routing.

        Delegates to sdk.planning.queue.work_next()
        """
        from htmlgraph.sdk.planning.queue import work_next

        return work_next(
            self, agent_id=agent_id, auto_claim=auto_claim, min_score=min_score
        )  # type: ignore[arg-type]

    # =========================================================================
    # Planning Workflow Integration
    # =========================================================================

    def start_planning_spike(
        self,
        title: str,
        context: str = "",
        timebox_hours: float = 4.0,
        auto_start: bool = True,
    ) -> Node:
        """
        Create a planning spike to research and design before implementation.

        Delegates to sdk.planning.smart_planning.start_planning_spike()
        """
        from htmlgraph.sdk.planning.smart_planning import start_planning_spike

        return start_planning_spike(
            self,
            title=title,
            context=context,
            timebox_hours=timebox_hours,
            auto_start=auto_start,
        )  # type: ignore[arg-type]

    def create_track_from_plan(
        self,
        title: str,
        description: str,
        spike_id: str | None = None,
        priority: str = "high",
        requirements: list[str | tuple[str, str]] | None = None,
        phases: list[tuple[str, list[str]]] | None = None,
    ) -> dict[str, Any]:
        """
        Create a track with spec and plan from planning results.

        Delegates to sdk.planning.smart_planning.create_track_from_plan()
        """
        from htmlgraph.sdk.planning.smart_planning import create_track_from_plan

        return create_track_from_plan(
            self,  # type: ignore[arg-type]
            title=title,
            description=description,
            spike_id=spike_id,
            priority=priority,
            requirements=requirements,
            phases=phases,
        )

    def smart_plan(
        self,
        description: str,
        create_spike: bool = True,
        timebox_hours: float = 4.0,
        research_completed: bool = False,
        research_findings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Smart planning workflow: analyzes project context and creates spike or track.

        Delegates to sdk.planning.smart_planning.smart_plan()
        """
        from htmlgraph.sdk.planning.smart_planning import smart_plan

        return smart_plan(
            self,  # type: ignore[arg-type]
            description=description,
            create_spike=create_spike,
            timebox_hours=timebox_hours,
            research_completed=research_completed,
            research_findings=research_findings,
        )

    def plan_parallel_work(
        self,
        max_agents: int = 5,
        shared_files: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Plan and prepare parallel work execution.

        Delegates to sdk.planning.parallel.plan_parallel_work()
        """
        from htmlgraph.sdk.planning.parallel import plan_parallel_work

        return plan_parallel_work(
            self, max_agents=max_agents, shared_files=shared_files
        )  # type: ignore[arg-type]

    def aggregate_parallel_results(
        self,
        agent_ids: list[str],
    ) -> dict[str, Any]:
        """
        Aggregate results from parallel agent execution.

        Delegates to sdk.planning.parallel.aggregate_parallel_results()
        """
        from htmlgraph.sdk.planning.parallel import aggregate_parallel_results

        return aggregate_parallel_results(self, agent_ids=agent_ids)  # type: ignore[arg-type]
