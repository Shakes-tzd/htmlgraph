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

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph import SDK

from htmlgraph.models import WorkType, Session
from htmlgraph.session_manager import SessionManager
from htmlgraph.converter import html_to_session


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
            >>> print(dist)
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
            >>> print(f"Spike-to-feature ratio: {ratio:.2f}")
            Spike-to-feature ratio: 0.63

            >>> if ratio > 0.5:
            ...     print("This was a research-heavy session")
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
            >>> print(f"Maintenance burden: {burden:.1f}%")
            Maintenance burden: 32.5%

            >>> if burden > 40:
            ...     print("⚠️  High maintenance burden - consider addressing technical debt")
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
            >>> print(f"Found {len(spike_sessions)} exploratory sessions")
        """
        session_nodes = self.sdk.sessions.all()
        matching_sessions = []

        for node in session_nodes:
            # Load full Session object
            session = self._get_session(node.id)
            if not session:
                continue

            # Check date range
            if start_date and session.started_at < start_date:
                continue
            if end_date and session.started_at > end_date:
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
            >>> print(breakdown)
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
            >>> print(f"Primary work type: {primary}")
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
