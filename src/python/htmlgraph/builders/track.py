from __future__ import annotations

"""
Track Builder for agent-friendly track creation.
"""


import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.ids import generate_id
from htmlgraph.planning import (
    AcceptanceCriterion,
    Phase,
    Plan,
    Requirement,
    Spec,
    Task,
    Track,
)


class TrackBuilder:
    """
    Fluent builder for creating tracks with spec and plan.

    By default, creates a single consolidated HTML file containing track metadata,
    spec, and plan. Use .separate_files() to create the legacy 3-file format.

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
        self._title: str | None = None
        self._description = ""
        self._priority = "medium"
        self._spec_data: dict[str, Any] = {}
        self._plan_phases: list[tuple[str, list[str]]] = []
        self._consolidated = True  # Default: single file

    def title(self, title: str) -> TrackBuilder:
        """Set track title."""
        self._title = title
        return self

    def description(self, desc: str) -> TrackBuilder:
        """Set track description."""
        self._description = desc
        return self

    def priority(self, priority: str) -> TrackBuilder:
        """Set track priority (low/medium/high/critical)."""
        self._priority = priority
        return self

    def with_spec(
        self,
        overview: str = "",
        context: str = "",
        requirements: list[Any] | None = None,
        acceptance_criteria: list[Any] | None = None,
    ) -> TrackBuilder:
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
            "acceptance_criteria": acceptance_criteria or [],
        }
        return self

    def with_plan_phases(self, phases: list[tuple[str, list[str]]]) -> TrackBuilder:
        """
        Add plan phases with tasks.

        Args:
            phases: List of (phase_name, [task_descriptions]) tuples
                    Task descriptions can include estimates like "Task name (2h)"
        """
        self._plan_phases = phases
        return self

    def separate_files(self) -> TrackBuilder:
        """Use legacy 3-file format (index.html, spec.html, plan.html)."""
        self._consolidated = False
        return self

    def consolidated(self) -> TrackBuilder:
        """Use single-file format (default). Everything in one index.html."""
        self._consolidated = True
        return self

    def _generate_track_html(self, track: Track, track_dir: Path) -> str:
        """Generate track index.html content (legacy 3-file format)."""
        spec_link = (
            '<li><a href="spec.html">📝 Specification</a></li>'
            if track.has_spec
            else ""
        )
        plan_link = (
            '<li><a href="plan.html">📋 Implementation Plan</a></li>'
            if track.has_plan
            else ""
        )

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

    def _generate_consolidated_html(
        self, track: Track, requirements: list[Requirement], phases: list[Phase]
    ) -> str:
        """Generate single consolidated HTML containing track, spec, and plan."""

        # Build requirements HTML
        req_html = ""
        if requirements:
            req_items = []
            for req in requirements:
                priority_class = f"priority-{req.priority}"
                status = "✅" if req.verified else "⏳"
                req_items.append(f'''
                <article class="requirement {priority_class}" data-requirement="{req.id}" data-priority="{req.priority}">
                    <h4>{status} {req.description}</h4>
                    <span class="badge">{req.priority}</span>
                </article>''')
            req_html = f"""
            <section data-section="requirements" id="requirements">
                <h2>Requirements</h2>
                <div class="requirements-list">
                    {"".join(req_items)}
                </div>
            </section>"""

        # Build acceptance criteria HTML
        ac_html = ""
        if self._spec_data.get("acceptance_criteria"):
            ac_items = []
            for crit in self._spec_data["acceptance_criteria"]:
                if isinstance(crit, tuple):
                    desc, test_case = crit
                    test_html = f" <code>{test_case}</code>" if test_case else ""
                else:
                    desc = crit
                    test_html = ""
                ac_items.append(f"<li>⏳ {desc}{test_html}</li>")
            ac_html = f"""
            <section data-section="acceptance-criteria" id="acceptance">
                <h2>Acceptance Criteria</h2>
                <ol class="criteria-list">
                    {"".join(ac_items)}
                </ol>
            </section>"""

        # Build phases/tasks HTML
        plan_html = ""
        if phases:
            total_tasks = sum(len(p.tasks) for p in phases)
            completed_tasks = sum(
                sum(1 for t in p.tasks if t.completed) for p in phases
            )
            completion = (
                int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
            )

            phase_items = []
            for i, phase in enumerate(phases):
                task_items = []
                for task in phase.tasks:
                    status_icon = "✅" if task.completed else "○"
                    estimate_html = (
                        f' <span class="estimate">({task.estimate_hours}h)</span>'
                        if task.estimate_hours
                        else ""
                    )
                    task_items.append(f'''
                    <div data-task="{task.id}" data-status="{"done" if task.completed else "todo"}">
                        <input type="checkbox" {"checked" if task.completed else ""} disabled>
                        <div>
                            <strong>{status_icon} {task.description}</strong>
                        </div>
                        {estimate_html}
                    </div>''')

                phase_items.append(f'''
                <details {"open" if i == 0 else ""} data-phase="{phase.id}">
                    <summary>Phase {i + 1}: {phase.name} ({len([t for t in phase.tasks if t.completed])}/{len(phase.tasks)} tasks)</summary>
                    {"".join(task_items)}
                </details>''')

            plan_html = f"""
            <section data-section="plan" id="plan">
                <h2>Implementation Plan</h2>
                <div class="progress-container">
                    <div class="progress-info">
                        <span class="progress-label">{completion}% Complete</span>
                        <span class="progress-count">({completed_tasks}/{total_tasks} tasks)</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {completion}%"></div>
                    </div>
                </div>
                <div class="phases-container">
                    {"".join(phase_items)}
                </div>
            </section>"""

        # Build overview/context from spec
        overview_html = ""
        context_html = ""
        if self._spec_data:
            if self._spec_data.get("overview"):
                overview_html = f"""
            <section data-section="overview" id="overview">
                <h2>Overview</h2>
                <p>{self._spec_data["overview"]}</p>
            </section>"""
            if self._spec_data.get("context"):
                context_html = f"""
            <section data-section="context" id="context">
                <h2>Context</h2>
                <p>{self._spec_data["context"]}</p>
            </section>"""

        # Navigation based on what's present
        nav_items = ['<a href="#top" class="nav-link">Track</a>']
        if self._spec_data:
            nav_items.append('<a href="#overview" class="nav-link">Spec</a>')
        if phases:
            nav_items.append('<a href="#plan" class="nav-link">Plan</a>')

        nav_html = f"""
        <nav class="track-nav">
            {"".join(nav_items)}
        </nav>"""

        # Map Track status to Node-compatible status for HTML parsing
        status_mapping = {
            "planned": "todo",  # Not started
            "active": "in-progress",  # In progress
            "completed": "done",  # Done
            "abandoned": "blocked",  # Blocked/stopped
        }
        node_status = status_mapping.get(track.status, "todo")

        created_date = datetime.now().strftime("%Y-%m-%d")

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="htmlgraph-version" content="1.0">
    <title>Track: {self._title}</title>
    <link rel="stylesheet" href="../styles.css">
    <style>
        /* HtmlGraph Dashboard Design System - Consolidated Track */
        :root {{
            --bg-primary: #151518;
            --bg-secondary: #1C1C20;
            --bg-tertiary: #252528;
            --text-primary: #E0DED8;
            --text-secondary: #A0A0A0;
            --text-muted: #707070;
            --border: #333338;
            --border-strong: #606068;
            --accent: #CDFF00;
            --accent-text: #0A0A0A;
        }}

        * {{ box-sizing: border-box; }}

        body {{
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'JetBrains Mono', 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 14px;
            line-height: 1.6;
            margin: 0;
            padding: 2rem;
            max-width: 1200px;
            margin-inline: auto;
        }}

        .track-nav {{
            display: flex;
            gap: 0;
            margin-bottom: 2rem;
            border: 2px solid var(--border-strong);
            width: fit-content;
        }}

        .nav-link {{
            color: var(--text-secondary);
            text-decoration: none;
            padding: 0.75rem 1.5rem;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            border-right: 2px solid var(--border-strong);
            transition: all 0.15s;
        }}

        .nav-link:last-child {{ border-right: none; }}
        .nav-link:hover {{
            color: var(--accent);
            background: var(--bg-tertiary);
        }}

        article {{
            background: var(--bg-secondary);
            border: 2px solid var(--border-strong);
        }}

        header {{
            padding: 2rem;
            border-bottom: 2px solid var(--border-strong);
            background: var(--bg-tertiary);
        }}

        h1 {{
            margin: 0 0 1rem 0;
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        h2 {{
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
            margin: 0 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
        }}

        h4 {{ margin: 0; font-size: 0.875rem; }}

        .metadata {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            font-size: 0.75rem;
        }}

        .badge {{
            background: var(--bg-primary);
            color: var(--text-secondary);
            padding: 0.25rem 0.75rem;
            border: 1px solid var(--border);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.7rem;
        }}

        .status-planned {{ color: var(--text-muted); }}
        .priority-high {{ color: #f59e0b; border-color: #f59e0b; }}
        .priority-medium {{ color: var(--text-secondary); }}
        .priority-critical {{ color: #ef4444; border-color: #ef4444; }}

        section {{
            padding: 2rem;
            border-bottom: 1px solid var(--border);
        }}

        section:last-child {{ border-bottom: none; }}

        p {{ margin: 0; line-height: 1.8; }}

        .requirements-list .requirement {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            padding: 1rem;
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .criteria-list {{
            list-style: none;
            counter-reset: criteria;
            padding: 0;
            margin: 0;
        }}

        .criteria-list li {{
            counter-increment: criteria;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            padding: 1rem 1rem 1rem 3rem;
            margin-bottom: 0.5rem;
            position: relative;
        }}

        .criteria-list li::before {{
            content: counter(criteria);
            position: absolute;
            left: 1rem;
            top: 1rem;
            background: var(--accent);
            color: var(--accent-text);
            width: 1.25rem;
            height: 1.25rem;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.7rem;
        }}

        .progress-container {{
            margin-bottom: 1.5rem;
        }}

        .progress-info {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.75rem;
            text-transform: uppercase;
        }}

        .progress-label {{ color: var(--accent); font-weight: 600; }}
        .progress-count {{ color: var(--text-secondary); }}

        .progress-bar {{
            width: 100%;
            height: 0.5rem;
            background: var(--bg-primary);
            border: 2px solid var(--border-strong);
        }}

        .progress-fill {{
            height: 100%;
            background: var(--accent);
        }}

        details {{
            border: 1px solid var(--border);
            margin-bottom: 0.75rem;
            background: var(--bg-tertiary);
        }}

        summary {{
            padding: 1rem;
            cursor: pointer;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.8rem;
            background: var(--bg-primary);
            border-bottom: 1px solid var(--border);
        }}

        summary:hover {{ color: var(--accent); }}

        [data-task] {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        [data-task]:last-child {{ border-bottom: none; }}

        .estimate {{
            color: var(--text-muted);
            font-size: 0.75rem;
            margin-left: auto;
        }}

        code {{
            background: var(--bg-primary);
            padding: 0.125rem 0.375rem;
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    {nav_html}
    <article id="{track.id}" data-type="track" data-status="{node_status}" data-priority="{track.priority}">
        <header id="top">
            <h1>{self._title}</h1>
            <div class="metadata">
                <span class="badge status-{node_status}">{track.status.title()}</span>
                <span class="badge priority-{track.priority}">{track.priority.title()} Priority</span>
                <span class="badge">Created: {created_date}</span>
            </div>
        </header>

        <section data-section="description">
            <p>{track.description}</p>
        </section>
        {overview_html}{context_html}{req_html}{ac_html}{plan_html}
    </article>
</body>
</html>'''

    def create(self) -> Track:
        """Execute the build and create track+spec+plan."""
        if not self._title:
            raise ValueError("Track title is required")

        # Generate collision-resistant track ID
        track_id = generate_id(node_type="track", title=self._title)

        # Create track model
        track = Track(
            id=track_id,
            title=f"Track: {self._title}",
            description=self._description,
            priority=cast(Literal["low", "medium", "high", "critical"], self._priority),
            has_spec=bool(self._spec_data),
            has_plan=bool(self._plan_phases),
        )

        # Build requirements list
        requirements = []
        if self._spec_data:
            for i, req in enumerate(self._spec_data.get("requirements", [])):
                if isinstance(req, tuple):
                    desc, priority = req
                else:
                    desc, priority = req, "must-have"
                requirements.append(
                    Requirement(id=f"req-{i + 1}", description=desc, priority=priority)
                )

        # Build phases list
        phases = []
        if self._plan_phases:
            for i, (phase_name, tasks) in enumerate(self._plan_phases):
                phase_tasks = []
                for j, task_desc in enumerate(tasks):
                    # Parse estimate from task description
                    estimate = None
                    if "(" in task_desc and "h)" in task_desc:
                        match = re.search(r"\((\d+(?:\.\d+)?)\s*h\)", task_desc)
                        if match:
                            estimate = float(match.group(1))
                            task_desc = re.sub(
                                r"\s*\(\d+(?:\.\d+)?\s*h\)", "", task_desc
                            ).strip()

                    phase_tasks.append(
                        Task(
                            id=f"task-{i + 1}-{j + 1}",
                            description=task_desc,
                            estimate_hours=estimate,
                        )
                    )

                phases.append(
                    Phase(id=f"phase-{i + 1}", name=phase_name, tasks=phase_tasks)
                )

        # Persist features to database from plan phases
        features_created = 0
        if phases:
            for phase in phases:
                for task in phase.tasks:
                    # Generate feature ID from task description
                    feature_id = generate_id(node_type="feat", title=task.description)

                    # Insert feature into database
                    success = self.sdk._db.insert_feature(
                        feature_id=feature_id,
                        feature_type="task",  # Tasks from tracks are features of type "task"
                        title=task.description,
                        status="todo",  # All new tasks start as "todo"
                        priority=self._priority,  # Inherit priority from track
                        assigned_to=None,  # No assignment initially
                        track_id=track_id,
                        description=f"Task from {phase.name}",
                        steps_total=0,
                        tags=None,
                    )
                    if success:
                        features_created += 1

        if self._consolidated:
            # Single-file format: everything in one index.html
            track_file = self.sdk._directory / "tracks" / f"{track_id}.html"
            track_file.parent.mkdir(parents=True, exist_ok=True)

            consolidated_html = self._generate_consolidated_html(
                track, requirements, phases
            )
            track_file.write_text(consolidated_html, encoding="utf-8")

            print(f"✓ Created track: {track_id} (single file)")

        else:
            # Legacy 3-file format: index.html, spec.html, plan.html
            track_dir = self.sdk._directory / "tracks" / track_id
            track_dir.mkdir(parents=True, exist_ok=True)

            # Generate track index HTML
            track_html = self._generate_track_html(track, track_dir)
            (track_dir / "index.html").write_text(track_html, encoding="utf-8")

            # Create spec if provided
            if self._spec_data:
                criteria = []
                for crit in self._spec_data.get("acceptance_criteria", []):
                    if isinstance(crit, tuple):
                        desc, test_case = crit
                        criteria.append(
                            AcceptanceCriterion(description=desc, test_case=test_case)
                        )
                    else:
                        criteria.append(AcceptanceCriterion(description=crit))

                spec = Spec(
                    id=f"{track_id}-spec",
                    title=f"{self._title} Specification",
                    track_id=track_id,
                    overview=self._spec_data.get("overview", ""),
                    context=self._spec_data.get("context", ""),
                    requirements=requirements,
                    acceptance_criteria=criteria,
                )
                (track_dir / "spec.html").write_text(spec.to_html(), encoding="utf-8")

            # Create plan if provided
            if phases:
                plan = Plan(
                    id=f"{track_id}-plan",
                    title=f"{self._title} Implementation Plan",
                    track_id=track_id,
                    phases=phases,
                )
                (track_dir / "plan.html").write_text(plan.to_html(), encoding="utf-8")

            print(f"✓ Created track: {track_id} (3 files)")
        if self._spec_data:
            print(f"  - Spec with {len(requirements)} requirements")
        if self._plan_phases:
            total_tasks = sum(len(tasks) for _, tasks in self._plan_phases)
            print(f"  - Plan with {len(self._plan_phases)} phases, {total_tasks} tasks")
        if features_created > 0:
            print(f"  - Persisted {features_created} features to database")

        return track

    def save(self) -> Track:
        """
        Save/create the track (alias for create()).

        Provides API consistency with other builders.

        Returns:
            Track object that was created

        Example:
            track = sdk.tracks.create("My Track").save()
        """
        return self.create()
