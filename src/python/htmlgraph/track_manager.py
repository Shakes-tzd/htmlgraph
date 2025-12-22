"""
Track manager for creating and managing tracks, specs, and plans.

Provides high-level operations for the Conductor-style planning workflow.
"""

from pathlib import Path
from datetime import datetime
from typing import Literal

from htmlgraph.planning import Track, Spec, Plan, Phase, Task, Requirement, AcceptanceCriterion
from htmlgraph.graph import HtmlGraph
from htmlgraph.ids import generate_id


class TrackManager:
    """Manager for track operations (create, update, query)."""

    def __init__(self, graph_dir: Path | str = ".htmlgraph"):
        """
        Initialize TrackManager.

        Args:
            graph_dir: Path to .htmlgraph directory
        """
        self.graph_dir = Path(graph_dir)
        self.tracks_dir = self.graph_dir / "tracks"
        self.tracks_dir.mkdir(parents=True, exist_ok=True)

    def create_track(
        self,
        title: str,
        description: str = "",
        priority: Literal["low", "medium", "high", "critical"] = "medium",
    ) -> Track:
        """
        Create a new track with a unique ID.

        Args:
            title: Track title
            description: Track description
            priority: Priority level

        Returns:
            Created Track instance
        """
        # Generate collision-resistant track ID
        track_id = generate_id(node_type="track", title=title)

        track = Track(
            id=track_id,
            title=title,
            description=description,
            priority=priority,
            status="planned",
        )

        # Create track directory
        track_path = self.tracks_dir / track_id
        track_path.mkdir(parents=True, exist_ok=True)

        # Create index.html for the track
        self._write_track_index(track, track_path)

        return track

    def create_spec(
        self,
        track_id: str,
        title: str,
        overview: str = "",
        context: str = "",
        author: str = "claude-code",
    ) -> Spec:
        """
        Create a spec for a track.

        Args:
            track_id: Parent track ID
            title: Spec title
            overview: Overview text
            context: Context/rationale
            author: Spec author

        Returns:
            Created Spec instance
        """
        track_path = self.tracks_dir / track_id
        if not track_path.exists():
            raise ValueError(f"Track '{track_id}' not found")

        spec = Spec(
            id=f"{track_id}-spec",
            title=title,
            track_id=track_id,
            overview=overview,
            context=context,
            author=author,
            status="draft",
        )

        # Write spec.html
        spec_path = track_path / "spec.html"
        spec_path.write_text(spec.to_html(), encoding="utf-8")

        # Update track to mark has_spec
        # (In a full implementation, we'd reload and update the Track object)

        return spec

    def create_plan(
        self,
        track_id: str,
        title: str,
    ) -> Plan:
        """
        Create an implementation plan for a track.

        Args:
            track_id: Parent track ID
            title: Plan title

        Returns:
            Created Plan instance
        """
        track_path = self.tracks_dir / track_id
        if not track_path.exists():
            raise ValueError(f"Track '{track_id}' not found")

        plan = Plan(
            id=f"{track_id}-plan",
            title=title,
            track_id=track_id,
            status="draft",
        )

        # Write plan.html
        plan_path = track_path / "plan.html"
        plan_path.write_text(plan.to_html(), encoding="utf-8")

        return plan

    def add_requirement(
        self,
        track_id: str,
        description: str,
        priority: Literal["must-have", "should-have", "nice-to-have"] = "must-have",
        notes: str = "",
    ) -> Spec:
        """
        Add a requirement to a track's spec.

        Args:
            track_id: Track ID
            description: Requirement description
            priority: Requirement priority
            notes: Additional notes

        Returns:
            Updated Spec instance
        """
        # Load existing spec
        spec = self.load_spec(track_id)

        # Generate requirement ID
        req_id = f"req-{len(spec.requirements) + 1}"

        requirement = Requirement(
            id=req_id,
            description=description,
            priority=priority,
            notes=notes,
        )

        spec.requirements.append(requirement)
        spec.updated = datetime.now()

        # Save updated spec
        track_path = self.tracks_dir / track_id
        spec_path = track_path / "spec.html"
        spec_path.write_text(spec.to_html(), encoding="utf-8")

        return spec

    def add_phase(
        self,
        track_id: str,
        name: str,
        description: str = "",
    ) -> Plan:
        """
        Add a phase to a track's plan.

        Args:
            track_id: Track ID
            name: Phase name
            description: Phase description

        Returns:
            Updated Plan instance
        """
        # Load existing plan
        plan = self.load_plan(track_id)

        # Generate phase ID
        phase_id = str(len(plan.phases) + 1)

        phase = Phase(
            id=phase_id,
            name=name,
            description=description,
            status="not-started",
        )

        plan.phases.append(phase)
        plan.updated = datetime.now()

        # Save updated plan
        track_path = self.tracks_dir / track_id
        plan_path = track_path / "plan.html"
        plan_path.write_text(plan.to_html(), encoding="utf-8")

        return plan

    def add_task(
        self,
        track_id: str,
        phase_id: str,
        description: str,
        priority: Literal["low", "medium", "high"] = "medium",
        estimate_hours: float | None = None,
        assigned: str | None = None,
    ) -> Plan:
        """
        Add a task to a phase in a track's plan.

        Args:
            track_id: Track ID
            phase_id: Phase ID (e.g., "1", "2")
            description: Task description
            priority: Task priority
            estimate_hours: Estimated hours
            assigned: Assigned agent

        Returns:
            Updated Plan instance
        """
        # Load existing plan
        plan = self.load_plan(track_id)

        # Find the phase
        phase = next((p for p in plan.phases if p.id == phase_id), None)
        if not phase:
            raise ValueError(f"Phase '{phase_id}' not found in plan")

        # Generate task ID
        task_id = f"{phase_id}.{len(phase.tasks) + 1}"

        task = Task(
            id=task_id,
            description=description,
            priority=priority,
            estimate_hours=estimate_hours,
            assigned=assigned,
        )

        phase.tasks.append(task)
        plan.updated = datetime.now()

        # Save updated plan
        track_path = self.tracks_dir / track_id
        plan_path = track_path / "plan.html"
        plan_path.write_text(plan.to_html(), encoding="utf-8")

        return plan

    def load_spec(self, track_id: str) -> Spec:
        """
        Load a spec from disk.

        Note: This is a simplified implementation. A full version would
        parse the HTML back into a Spec object using justhtml.

        Args:
            track_id: Track ID

        Returns:
            Spec instance (currently returns a basic instance)
        """
        track_path = self.tracks_dir / track_id
        spec_path = track_path / "spec.html"

        if not spec_path.exists():
            raise FileNotFoundError(f"Spec not found for track '{track_id}'")

        # TODO: Parse HTML back to Spec using justhtml
        # For now, return a basic spec
        return Spec(
            id=f"{track_id}-spec",
            title="Loaded Spec",
            track_id=track_id,
        )

    def load_plan(self, track_id: str) -> Plan:
        """
        Load a plan from disk.

        Note: This is a simplified implementation. A full version would
        parse the HTML back into a Plan object using justhtml.

        Args:
            track_id: Track ID

        Returns:
            Plan instance (currently returns a basic instance)
        """
        track_path = self.tracks_dir / track_id
        plan_path = track_path / "plan.html"

        if not plan_path.exists():
            raise FileNotFoundError(f"Plan not found for track '{track_id}'")

        # TODO: Parse HTML back to Plan using justhtml
        # For now, return a basic plan
        return Plan(
            id=f"{track_id}-plan",
            title="Loaded Plan",
            track_id=track_id,
        )

    def list_tracks(self) -> list[str]:
        """
        List all track IDs.

        Supports both consolidated (single .html file) and directory-based tracks.

        Returns:
            List of track IDs
        """
        if not self.tracks_dir.exists():
            return []

        tracks = set()

        for item in self.tracks_dir.iterdir():
            if item.name.startswith("."):
                continue

            if item.is_dir():
                # Directory-based track (legacy 3-file format)
                tracks.add(item.name)
            elif item.is_file() and item.suffix == ".html":
                # Consolidated single-file track
                tracks.add(item.stem)

        return sorted(tracks)

    def get_track_path(self, track_id: str) -> Path | None:
        """
        Get the path to a track (file or directory).

        Args:
            track_id: Track ID

        Returns:
            Path to track file or directory, or None if not found
        """
        # Check for consolidated format first (single file)
        track_file = self.tracks_dir / f"{track_id}.html"
        if track_file.exists():
            return track_file

        # Check for directory format
        track_dir = self.tracks_dir / track_id
        if track_dir.exists():
            return track_dir

        return None

    def is_consolidated(self, track_id: str) -> bool:
        """
        Check if a track uses the consolidated single-file format.

        Args:
            track_id: Track ID

        Returns:
            True if consolidated, False if directory-based
        """
        track_file = self.tracks_dir / f"{track_id}.html"
        return track_file.exists()

    def delete_track(self, track_id: str) -> None:
        """
        Delete a track and all its components.

        Supports both consolidated (single file) and directory-based tracks.

        Args:
            track_id: Track ID to delete

        Raises:
            ValueError: If track doesn't exist
        """
        import shutil

        # Check for consolidated format first
        track_file = self.tracks_dir / f"{track_id}.html"
        if track_file.exists():
            track_file.unlink()
            return

        # Check for directory format
        track_dir = self.tracks_dir / track_id
        if track_dir.exists():
            shutil.rmtree(track_dir)
            return

        raise ValueError(f"Track '{track_id}' not found")

    def _write_track_index(self, track: Track, track_path: Path) -> None:
        """
        Write the index.html for a track.

        Args:
            track: Track instance
            track_path: Path to track directory
        """
        # Map Track status to Node-compatible status
        status_mapping = {
            "planned": "todo",
            "active": "active",
            "completed": "done",
            "abandoned": "stale",
        }
        node_status = status_mapping.get(track.status, track.status)

        index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="htmlgraph-version" content="1.0">
    <title>Track: {track.title}</title>
    <link rel="stylesheet" href="../../.htmlgraph/styles.css">
</head>
<body>
    <article id="{track.id}" data-type="track" data-status="{node_status}" data-priority="{track.priority}">
        <header>
            <h1>Track: {track.title}</h1>
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
                <li><a href="spec.html">📝 Specification</a>{' (not created)' if not track.has_spec else ''}</li>
                <li><a href="plan.html">📋 Implementation Plan</a>{' (not created)' if not track.has_plan else ''}</li>
            </ul>
        </nav>

        <section data-related-work>
            <h2>Related Work</h2>
            <nav>
                <h3>Features:</h3>
                <ul>
                    {'<li>No features linked yet</li>' if not track.features else ''.join(f'<li><a href="../../features/{fid}.html">{fid}</a></li>' for fid in track.features)}
                </ul>

                <h3>Sessions:</h3>
                <ul>
                    {'<li>No sessions yet</li>' if not track.sessions else ''.join(f'<li><a href="../../sessions/{sid}.html">{sid}</a></li>' for sid in track.sessions)}
                </ul>
            </nav>
        </section>
    </article>
</body>
</html>
'''

        index_path = track_path / "index.html"
        index_path.write_text(index_html, encoding="utf-8")

    # =========================================================================
    # Vertical Integration: Track → Plan → Features
    # =========================================================================

    def generate_features_from_plan(
        self,
        track_id: str,
        plan: Plan | None = None,
        features_dir: Path | str = ".htmlgraph/features"
    ) -> list["Node"]:
        """
        Generate feature nodes from plan tasks.

        Creates a Node (feature) for each task in the plan, automatically
        linking them via track_id and plan_task_id.

        Args:
            track_id: Track ID
            plan: Plan instance (will load if not provided)
            features_dir: Directory to save features

        Returns:
            List of created Node (feature) instances
        """
        from htmlgraph.models import Node

        if plan is None:
            plan = self.load_plan(track_id)

        features_dir = Path(features_dir)
        features_dir.mkdir(parents=True, exist_ok=True)

        created_features = []

        for phase in plan.phases:
            for task in phase.tasks:
                # Generate feature ID from task ID
                feature_id = f"feature-{track_id}-{task.id.replace('.', '-')}"

                # Create feature node
                feature = Node(
                    id=feature_id,
                    title=task.description,
                    type="feature",
                    status="todo",
                    priority=task.priority,
                    track_id=track_id,
                    plan_task_id=task.id,
                    content=f"Implements task {task.id} from {track_id}",
                    properties={
                        "estimate_hours": task.estimate_hours,
                        "phase_id": phase.id,
                        "phase_name": phase.name,
                    }
                )

                # Save feature HTML
                from htmlgraph.converter import NodeConverter
                converter = NodeConverter(features_dir)
                converter.save(feature)

                # Link feature back to task
                task.feature_ids.append(feature_id)

                created_features.append(feature)

        # Save updated plan with feature links
        track_path = self.tracks_dir / track_id
        plan_path = track_path / "plan.html"
        plan_path.write_text(plan.to_html(), encoding="utf-8")

        return created_features

    def link_feature_to_task(
        self,
        feature_id: str,
        track_id: str,
        task_id: str
    ) -> None:
        """
        Link an existing feature to a plan task.

        Args:
            feature_id: Feature node ID
            track_id: Track ID
            task_id: Task ID within the plan
        """
        # Load the plan
        plan = self.load_plan(track_id)

        # Find the task
        task = None
        for phase in plan.phases:
            for t in phase.tasks:
                if t.id == task_id:
                    task = t
                    break
            if task:
                break

        if not task:
            raise ValueError(f"Task '{task_id}' not found in plan")

        # Add feature to task's feature list
        if feature_id not in task.feature_ids:
            task.feature_ids.append(feature_id)

        # Save updated plan
        track_path = self.tracks_dir / track_id
        plan_path = track_path / "plan.html"
        plan_path.write_text(plan.to_html(), encoding="utf-8")

    def sync_task_completion(
        self,
        track_id: str,
        graph: "HtmlGraph | None" = None
    ) -> Plan:
        """
        Sync task completion status based on linked features.

        Updates plan tasks to completed if all their linked features are done.

        Args:
            track_id: Track ID
            graph: HtmlGraph instance with features loaded

        Returns:
            Updated Plan instance
        """
        plan = self.load_plan(track_id)

        if graph is None:
            from htmlgraph.graph import HtmlGraph
            graph = HtmlGraph(".htmlgraph/features")

        for phase in plan.phases:
            for task in phase.tasks:
                if not task.feature_ids:
                    continue

                # Check if all linked features are completed
                all_done = True
                for fid in task.feature_ids:
                    if fid in graph:
                        feature = graph.get(fid)
                        if feature and feature.status != "done":
                            all_done = False
                            break
                    else:
                        all_done = False
                        break

                # Update task completion
                if all_done and not task.completed:
                    task.completed = True
                    task.completed_at = datetime.now()
                elif not all_done and task.completed:
                    task.completed = False
                    task.completed_at = None

        # Update plan status
        plan.updated = datetime.now()

        # Save updated plan
        track_path = self.tracks_dir / track_id
        plan_path = track_path / "plan.html"
        plan_path.write_text(plan.to_html(), encoding="utf-8")

        return plan

    def check_spec_satisfaction(
        self,
        track_id: str,
        graph: "HtmlGraph | None" = None
    ) -> Spec:
        """
        Check if spec requirements are satisfied by completed features.

        Updates spec acceptance criteria and requirements based on
        linked feature completion.

        Args:
            track_id: Track ID
            graph: HtmlGraph instance with features loaded

        Returns:
            Updated Spec instance
        """
        spec = self.load_spec(track_id)

        if graph is None:
            from htmlgraph.graph import HtmlGraph
            graph = HtmlGraph(".htmlgraph/features")

        # Check acceptance criteria
        for criterion in spec.acceptance_criteria:
            if not criterion.feature_ids:
                continue

            # Check if all linked features are completed
            all_done = all(
                fid in graph and (feature := graph.get(fid)) is not None and feature.status == "done"
                for fid in criterion.feature_ids
            )

            criterion.completed = all_done

        # Check requirements
        for requirement in spec.requirements:
            if not requirement.feature_ids:
                continue

            # Check if all linked features are completed
            all_done = all(
                fid in graph and (feature := graph.get(fid)) is not None and feature.status == "done"
                for fid in requirement.feature_ids
            )

            requirement.verified = all_done

        # Update spec status
        spec.updated = datetime.now()
        if all(ac.completed for ac in spec.acceptance_criteria):
            spec.status = "approved"

        # Save updated spec
        track_path = self.tracks_dir / track_id
        spec_path = track_path / "spec.html"
        spec_path.write_text(spec.to_html(), encoding="utf-8")

        return spec
