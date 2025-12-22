"""
Track Builder for agent-friendly track creation.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.planning import Track, Spec, Plan, Phase, Task, Requirement, AcceptanceCriterion


class TrackBuilder:
    """
    Fluent builder for creating tracks with spec and plan.

    Example:
        track = sdk.tracks.builder() \\
            .title("Multi-Agent Collaboration") \\
            .description("Enable seamless agent collaboration") \\
            .priority("high") \\
            .with_spec(
                overview="Agents can work together...",
                requirements=[
                    ("Add assigned_agent field", "must-have"),
                    ("Implement claim CLI", "must-have")
                ]
            ) \\
            .with_plan_phases([
                ("Phase 1", ["Add field (1h)", "Implement CLI (2h)"]),
                ("Phase 2", ["Add notes (1h)", "Update hooks (2h)"])
            ]) \\
            .create()
    """

    def __init__(self, sdk: SDK):
        self.sdk = sdk
        self._title = None
        self._description = ""
        self._priority = "medium"
        self._spec_data = {}
        self._plan_phases = []

    def title(self, title: str) -> 'TrackBuilder':
        """Set track title."""
        self._title = title
        return self

    def description(self, desc: str) -> 'TrackBuilder':
        """Set track description."""
        self._description = desc
        return self

    def priority(self, priority: str) -> 'TrackBuilder':
        """Set track priority (low/medium/high/critical)."""
        self._priority = priority
        return self

    def with_spec(
        self,
        overview: str = "",
        context: str = "",
        requirements: list = None,
        acceptance_criteria: list = None
    ) -> 'TrackBuilder':
        """
        Add spec content to track.

        Args:
            overview: High-level summary
            context: Background and current state
            requirements: List of (description, priority) tuples or strings
            acceptance_criteria: List of strings or (description, test_case) tuples
        """
        self._spec_data = {
            "overview": overview,
            "context": context,
            "requirements": requirements or [],
            "acceptance_criteria": acceptance_criteria or []
        }
        return self

    def with_plan_phases(self, phases: list[tuple[str, list[str]]]) -> 'TrackBuilder':
        """
        Add plan phases with tasks.

        Args:
            phases: List of (phase_name, [task_descriptions]) tuples
                    Task descriptions can include estimates like "Task name (2h)"
        """
        self._plan_phases = phases
        return self

    def _generate_track_html(self, track: Track, track_dir: Path) -> str:
        """Generate track index.html content."""
        spec_link = '<li><a href="spec.html">📝 Specification</a></li>' if track.has_spec else ''
        plan_link = '<li><a href="plan.html">📋 Implementation Plan</a></li>' if track.has_plan else ''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{track.title}</title>
    <link rel="stylesheet" href="../../styles.css">
</head>
<body>
    <article id="{track.id}" data-type="track" data-status="{track.status}" data-priority="{track.priority}">
        <header>
            <h1>{track.title}</h1>
            <div class="metadata">
                <span class="badge status-{track.status}">{track.status.title()}</span>
                <span class="badge priority-{track.priority}">{track.priority.title()} Priority</span>
            </div>
        </header>

        <section data-description>
            <p>{track.description}</p>
        </section>

        <nav data-track-components>
            <h2>Components</h2>
            <ul>
                {spec_link}
                {plan_link}
            </ul>
        </nav>
    </article>
</body>
</html>'''

    def create(self) -> Track:
        """Execute the build and create track+spec+plan."""
        if not self._title:
            raise ValueError("Track title is required")

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

        # Save track index.html
        track_dir = Path(".htmlgraph") / "tracks" / track_id
        track_dir.mkdir(parents=True, exist_ok=True)

        # Generate track index HTML
        track_html = self._generate_track_html(track, track_dir)
        (track_dir / "index.html").write_text(track_html, encoding="utf-8")

        # Create spec if provided
        requirements = []
        if self._spec_data:
            for i, req in enumerate(self._spec_data.get("requirements", [])):
                if isinstance(req, tuple):
                    desc, priority = req
                else:
                    desc, priority = req, "must-have"

                requirements.append(Requirement(
                    id=f"req-{i+1}",
                    description=desc,
                    priority=priority
                ))

            criteria = []
            for crit in self._spec_data.get("acceptance_criteria", []):
                if isinstance(crit, tuple):
                    desc, test_case = crit
                    criteria.append(AcceptanceCriterion(description=desc, test_case=test_case))
                else:
                    criteria.append(AcceptanceCriterion(description=crit))

            spec = Spec(
                id=f"{track_id}-spec",
                title=f"{self._title} Specification",
                track_id=track_id,
                overview=self._spec_data.get("overview", ""),
                context=self._spec_data.get("context", ""),
                requirements=requirements,
                acceptance_criteria=criteria
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
                        match = re.search(r'\((\d+(?:\.\d+)?)\s*h\)', task_desc)
                        if match:
                            estimate = float(match.group(1))
                            task_desc = re.sub(r'\s*\(\d+(?:\.\d+)?\s*h\)', '', task_desc).strip()

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

        print(f"✓ Created track: {track_id}")
        if self._spec_data:
            print(f"  - Spec with {len(requirements)} requirements")
        if self._plan_phases:
            total_tasks = sum(len(tasks) for _, tasks in self._plan_phases)
            print(f"  - Plan with {len(self._plan_phases)} phases, {total_tasks} tasks")

        return track


class TrackCollection:
    """Collection interface for tracks with builder support."""

    def __init__(self, sdk: 'SDK'):
        self._sdk = sdk
        self.collection_name = "tracks"
        self.id_prefix = "track"

    def builder(self) -> TrackBuilder:
        """
        Create a new track builder with fluent interface.

        Returns:
            TrackBuilder for method chaining

        Example:
            track = sdk.tracks.builder() \\
                .title("Multi-Agent Collaboration") \\
                .priority("high") \\
                .with_spec(overview="...") \\
                .with_plan_phases([...]) \\
                .create()
        """
        return TrackBuilder(self._sdk)
