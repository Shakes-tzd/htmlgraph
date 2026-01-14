from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

"""
Analytics API for HtmlGraph work type analysis.

Provides methods to calculate:
- Work type distribution across sessions
- Spike-to-feature ratios
- Maintenance burden metrics
- Session filtering by work type

Example:
    from htmlgraph import SDK

    sdk = SDK(agent="claude")

    # Get work type distribution for a session
    dist = sdk.analytics.work_type_distribution(session_id="session-123")
    # Returns: {"feature-implementation": 45.2, "spike-investigation": 28.3, ...}

    # Calculate spike-to-feature ratio
    ratio = sdk.analytics.spike_to_feature_ratio(session_id="session-123")
    # Returns: 0.63 (high ratio = research-heavy session)

    # Get maintenance burden
    burden = sdk.analytics.maintenance_burden(session_id="session-123")
    # Returns: 25.5 (% of work spent on maintenance)
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph import SDK

from htmlgraph.converter import html_to_session
from htmlgraph.models import Session, WorkType, utc_now
from htmlgraph.session_manager import SessionManager


def normalize_datetime(dt: datetime | None) -> datetime | None:
    """
    Normalize datetime to UTC-aware format for safe comparisons.

    Handles three cases:
    - None: returns None
    - Naive (no timezone): assumes UTC and adds timezone
    - Aware (has timezone): converts to UTC
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)
    # Already aware - convert to UTC
    return dt.astimezone(timezone.utc)


class Analytics:
    """
    Analytics interface for work type analysis.

    Provides methods to analyze work type distribution, ratios, and trends
    across sessions and events.
    """

    def __init__(self, sdk: SDK):
        """
        Initialize Analytics with SDK instance.

        Args:
            sdk: Parent SDK instance for accessing sessions and events
        """
        self.sdk = sdk
        self._session_manager = SessionManager(graph_dir=sdk._directory)

    def work_type_distribution(
        self,
        session_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, float]:
        """
        Calculate work type distribution as percentages.

        Analyzes events and returns the percentage of work spent on each
        work type (feature, spike, bug-fix, maintenance, etc.).

        Args:
            session_id: Optional session ID to analyze (analyzes single session)
            start_date: Optional start date for date range query
            end_date: Optional end date for date range query

        Returns:
            Dictionary mapping work type to percentage (0-100)

        Example:
            >>> analytics = sdk.analytics
            >>> dist = analytics.work_type_distribution(session_id="session-123")
            >>> logger.info("%s", dist)
            {
                "feature-implementation": 45.2,
                "spike-investigation": 28.3,
                "maintenance": 18.5,
                "documentation": 8.0
            }

            >>> # Get distribution across date range
            >>> dist = analytics.work_type_distribution(
            ...     start_date=datetime(2024, 12, 1),
            ...     end_date=datetime(2024, 12, 31)
            ... )
        """
        events = self._get_events(session_id, start_date, end_date)

        if not events:
            return {}

        # Count events by work type
        work_type_counts: dict[str, int] = {}
        total_events = 0

        for event in events:
            work_type = event.get("work_type")
            if work_type:
                work_type_counts[work_type] = work_type_counts.get(work_type, 0) + 1
                total_events += 1

        if total_events == 0:
            return {}

        # Convert counts to percentages
        distribution = {
            work_type: (count / total_events) * 100
            for work_type, count in work_type_counts.items()
        }

        return distribution

    def spike_to_feature_ratio(
        self,
        session_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> float:
        """
        Calculate ratio of spike events to feature events.

        This metric indicates how much time was spent on exploration vs
        implementation:
        - High ratio (>0.5): Research-heavy session
        - Medium ratio (0.2-0.5): Balanced session
        - Low ratio (<0.2): Implementation-heavy session

        Args:
            session_id: Optional session ID to analyze
            start_date: Optional start date for date range query
            end_date: Optional end date for date range query

        Returns:
            Ratio of spike events to feature events (0.0 to infinity)
            Returns 0.0 if no feature events found

        Example:
            >>> ratio = sdk.analytics.spike_to_feature_ratio(session_id="session-123")
            >>> logger.info(f"Spike-to-feature ratio: {ratio:.2f}")
            Spike-to-feature ratio: 0.63

            >>> if ratio > 0.5:
            ...     logger.info("This was a research-heavy session")
        """
        events = self._get_events(session_id, start_date, end_date)

        if not events:
            return 0.0

        # Count spike and feature events
        spike_count = 0
        feature_count = 0

        for event in events:
            work_type = event.get("work_type")
            if work_type == WorkType.SPIKE.value:
                spike_count += 1
            elif work_type == WorkType.FEATURE.value:
                feature_count += 1

        # Avoid division by zero
        if feature_count == 0:
            return 0.0

        return spike_count / feature_count

    def maintenance_burden(
        self,
        session_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> float:
        """
        Calculate percentage of work spent on maintenance vs new features.

        Maintenance includes:
        - Bug fixes (bug-fix)
        - Chores (maintenance)
        - Refactoring

        This metric helps identify if the project is accumulating technical
        debt or spending too much time on maintenance:
        - <20%: Healthy (mostly new development)
        - 20-40%: Moderate (balanced maintenance)
        - >40%: High burden (may indicate technical debt)

        Args:
            session_id: Optional session ID to analyze
            start_date: Optional start date for date range query
            end_date: Optional end date for date range query

        Returns:
            Percentage of work spent on maintenance (0-100)

        Example:
            >>> burden = sdk.analytics.maintenance_burden(session_id="session-123")
            >>> logger.info(f"Maintenance burden: {burden:.1f}%")
            Maintenance burden: 32.5%

            >>> if burden > 40:
            ...     logger.info("⚠️  High maintenance burden - consider addressing technical debt")
        """
        events = self._get_events(session_id, start_date, end_date)

        if not events:
            return 0.0

        # Count maintenance and total events
        maintenance_count = 0
        total_events = 0

        # Maintenance work types
        maintenance_types = {
            WorkType.BUG_FIX.value,
            WorkType.MAINTENANCE.value,
        }

        for event in events:
            work_type = event.get("work_type")
            if work_type:
                total_events += 1
                if work_type in maintenance_types:
                    maintenance_count += 1

        if total_events == 0:
            return 0.0

        return (maintenance_count / total_events) * 100

    def get_sessions_by_work_type(
        self,
        primary_work_type: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[str]:
        """
        Get list of session IDs where the primary work type matches.

        Args:
            primary_work_type: Work type to filter by (e.g., "spike-investigation")
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of session IDs matching the criteria

        Example:
            >>> # Find all exploratory sessions
            >>> spike_sessions = sdk.analytics.get_sessions_by_work_type(
            ...     "spike-investigation"
            ... )
            >>> logger.info(f"Found {len(spike_sessions)} exploratory sessions")
        """
        session_nodes = self.sdk.sessions.all()
        matching_sessions = []

        for node in session_nodes:
            # Load full Session object
            session = self._get_session(node.id)
            if not session:
                continue

            # Check date range
            start_normalized = normalize_datetime(start_date)
            end_normalized = normalize_datetime(end_date)
            if start_normalized and session.started_at < start_normalized:
                continue
            if end_normalized and session.started_at > end_normalized:
                continue

            # Check primary work type
            if session.primary_work_type == primary_work_type:
                matching_sessions.append(session.id)

        return matching_sessions

    def calculate_session_work_breakdown(self, session_id: str) -> dict[str, int]:
        """
        Calculate work type breakdown (event counts) for a session.

        This is a convenience method that delegates to Session.calculate_work_breakdown()
        but can be called directly from the analytics API.

        Args:
            session_id: Session ID to analyze

        Returns:
            Dictionary mapping work type to event count

        Example:
            >>> breakdown = sdk.analytics.calculate_session_work_breakdown("session-123")
            >>> logger.info("%s", breakdown)
            {
                "feature-implementation": 45,
                "spike-investigation": 28,
                "maintenance": 15
            }
        """
        session = self._get_session(session_id)
        if not session:
            return {}

        events_dir = str(self.sdk._directory / "events")
        return session.calculate_work_breakdown(events_dir=events_dir)

    def calculate_session_primary_work_type(self, session_id: str) -> str | None:
        """
        Calculate the primary work type for a session.

        Returns the work type with the most events in the session.

        Args:
            session_id: Session ID to analyze

        Returns:
            Primary work type (most common), or None if no work type data

        Example:
            >>> primary = sdk.analytics.calculate_session_primary_work_type("session-123")
            >>> logger.info(f"Primary work type: {primary}")
            Primary work type: spike-investigation
        """
        session = self._get_session(session_id)
        if not session:
            return None

        events_dir = str(self.sdk._directory / "events")
        return session.calculate_primary_work_type(events_dir=events_dir)

    def _get_session(self, session_id: str) -> Session | None:
        """
        Load a Session object from its HTML file.

        Args:
            session_id: Session ID to load

        Returns:
            Session object or None if not found
        """
        session_path = self.sdk._directory / "sessions" / f"{session_id}.html"
        if not session_path.exists():
            return None

        try:
            return html_to_session(session_path)
        except Exception:
            return None

    def transition_time_metrics(
        self,
        session_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, float]:
        """
        Calculate time spent in transitions vs feature work.

        Analyzes time spent in transition spikes (session-init, transition,
        conversation-init) versus regular feature implementation.

        Args:
            session_id: Optional session ID to analyze (analyzes single session)
            start_date: Optional start date for date range query
            end_date: Optional end date for date range query

        Returns:
            Dictionary with transition metrics:
            - transition_minutes: Total time in transition spikes
            - feature_minutes: Total time in regular features
            - total_minutes: Combined time
            - transition_percent: % time spent in transitions (0-100)

        Example:
            >>> metrics = sdk.analytics.transition_time_metrics(session_id="session-123")
            >>> logger.info(f"Transition time: {metrics['transition_percent']:.1f}%")
            Transition time: 15.3%
        """
        from pathlib import Path

        from htmlgraph.converter import NodeConverter

        transition_minutes = 0.0
        feature_minutes = 0.0

        # Get all spikes
        spikes_dir = Path(self.sdk._directory) / "spikes"
        if not spikes_dir.exists():
            return {
                "transition_minutes": 0.0,
                "feature_minutes": 0.0,
                "total_minutes": 0.0,
                "transition_percent": 0.0,
            }

        spike_converter = NodeConverter(spikes_dir)
        all_spikes = spike_converter.load_all()

        # Filter spikes by session if specified
        if session_id:
            session = self._get_session(session_id)
            if session:
                # Only include spikes linked to this session
                spike_ids = set(session.worked_on)
                all_spikes = [s for s in all_spikes if s.id in spike_ids]

        # Calculate time for each spike
        for spike in all_spikes:
            # Apply date filters
            start_normalized = normalize_datetime(start_date)
            end_normalized = normalize_datetime(end_date)
            if start_normalized and spike.created < start_normalized:
                continue
            if end_normalized and spike.created > end_normalized:
                continue

            # Calculate duration (normalize datetimes for safe comparison)
            start_time = normalize_datetime(spike.created)
            if not start_time:
                continue  # Skip if spike creation date is missing
            if spike.status == "done" and spike.updated:
                end_time = normalize_datetime(spike.updated)
            else:
                # If still in progress, use last updated time
                end_time = normalize_datetime(
                    spike.updated if spike.updated else utc_now()
                )
            if not end_time:
                end_time = start_time  # Fallback to start time if end time missing

            duration = (
                end_time - start_time
            ).total_seconds() / 60  # Convert to minutes

            # Categorize as transition or feature work
            is_transition = spike.type == "spike" and spike.spike_subtype in (
                "session-init",
                "transition",
                "conversation-init",
            )

            if is_transition:
                transition_minutes += duration
            else:
                feature_minutes += duration

        # Also get regular features, bugs, etc.
        for collection in ["features", "bugs"]:
            collection_dir = Path(self.sdk._directory) / collection
            if not collection_dir.exists():
                continue

            converter = NodeConverter(collection_dir)
            nodes = converter.load_all()

            # Filter by session if specified
            if session_id:
                session = self._get_session(session_id)
                if session:
                    node_ids = set(session.worked_on)
                    nodes = [n for n in nodes if n.id in node_ids]

            for node in nodes:
                # Apply date filters
                start_normalized = normalize_datetime(start_date)
                end_normalized = normalize_datetime(end_date)
                if start_normalized and node.created < start_normalized:
                    continue
                if end_normalized and node.created > end_normalized:
                    continue

                # Calculate duration (normalize datetimes for safe comparison)
                start_time = normalize_datetime(node.created)
                if not start_time:
                    continue  # Skip if node creation date is missing
                if node.status == "done" and node.updated:
                    end_time = normalize_datetime(node.updated)
                else:
                    end_time = normalize_datetime(
                        node.updated if node.updated else utc_now()
                    )
                if not end_time:
                    end_time = start_time  # Fallback to start time if end time missing

                duration = (end_time - start_time).total_seconds() / 60
                feature_minutes += duration

        # Calculate metrics
        total_minutes = transition_minutes + feature_minutes
        transition_percent = (
            (transition_minutes / total_minutes * 100) if total_minutes > 0 else 0.0
        )

        return {
            "transition_minutes": round(transition_minutes, 2),
            "feature_minutes": round(feature_minutes, 2),
            "total_minutes": round(total_minutes, 2),
            "transition_percent": round(transition_percent, 2),
        }

    def _get_events(
        self,
        session_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """
        Internal helper to get events based on filters.

        Args:
            session_id: Optional session ID to filter by
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of event dictionaries
        """
        events = []
        events_dir = str(self.sdk._directory / "events")

        if session_id:
            # Get events for specific session
            session = self._get_session(session_id)
            if session:
                events = session.get_events(limit=None, events_dir=events_dir)
        else:
            # Get events across all sessions
            session_nodes = self.sdk.sessions.all()

            for node in session_nodes:
                # Load full Session object
                session = self._get_session(node.id)
                if not session:
                    continue

                # Apply date filters
                if start_date and session.started_at < start_date:
                    continue
                if end_date and session.started_at > end_date:
                    continue

                session_events = session.get_events(limit=None, events_dir=events_dir)
                events.extend(session_events)

        return events
