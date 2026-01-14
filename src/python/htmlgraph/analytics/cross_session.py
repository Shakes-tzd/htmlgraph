from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

"""
Cross-session analytics using Git commits as the continuity spine.

This module provides analytics that track work across multiple sessions
using Git commit history as the linking mechanism. Unlike session-based
analytics that only look within a single session, these analytics span
the entire commit graph to provide comprehensive insights.

Key Features:
- Query work in commit ranges (e.g., show all work between two commits)
- Track feature implementation across multiple sessions
- Analyze work by author across the project history
- Find sessions that contributed to specific commits
- Build work timelines using commit timestamps

Design:
- Uses Git commit hashes from EventRecord.payload['commit_hash']
- Leverages event logs (JSONL) as primary data source
- Falls back to Git commands when needed
- Works with both active sessions and historical work

Example:
    from htmlgraph import SDK

    sdk = SDK(agent="claude")
    cross = sdk.cross_session_analytics

    # Get all work between two commits
    work = cross.work_in_commit_range(
        from_commit="abc123",
        to_commit="def456"
    )

    # Find sessions that contributed to a feature
    sessions = cross.sessions_for_feature("feature-auth")

    # Analyze work by author
    authors = cross.work_by_author(since_commit="abc123")
"""

import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph import SDK

from htmlgraph.event_log import JsonlEventLog
from htmlgraph.models import utc_now


@dataclass
class CommitWorkSummary:
    """Summary of work done in a single commit."""

    commit_hash: str
    commit_hash_short: str
    branch: str
    author_name: str
    author_email: str
    commit_message: str
    timestamp: datetime
    features: list[str]
    sessions: list[str]
    event_count: int
    files_changed: list[str]
    insertions: int
    deletions: int


@dataclass
class CommitRangeReport:
    """Report of all work done in a commit range."""

    from_commit: str
    to_commit: str
    commits: list[CommitWorkSummary]
    total_events: int
    features: list[str]
    sessions: list[str]
    authors: dict[str, int]  # author_email -> event_count
    work_types: dict[str, int]  # work_type -> event_count


@dataclass
class FeatureCrossSessionReport:
    """Report of a feature's implementation across multiple sessions."""

    feature_id: str
    sessions: list[str]
    commits: list[str]
    authors: list[str]
    start_time: datetime | None
    end_time: datetime | None
    duration_hours: float | None
    event_count: int
    work_type_distribution: dict[str, int]


class CrossSessionAnalytics:
    """
    Analytics that track work across sessions using Git commits.

    This class provides methods to query and analyze work that spans
    multiple sessions, using Git commit history as the continuity spine.
    """

    def __init__(self, sdk: SDK):
        """
        Initialize CrossSessionAnalytics with SDK instance.

        Args:
            sdk: Parent SDK instance for accessing events and sessions
        """
        self.sdk = sdk
        self._event_log = JsonlEventLog(sdk._directory / "events")
        self._repo_root = self._find_repo_root(sdk._directory)

    def work_in_commit_range(
        self,
        from_commit: str | None = None,
        to_commit: str = "HEAD",
        include_uncommitted: bool = False,
    ) -> CommitRangeReport:
        """
        Get all work done in a commit range.

        This method queries all events associated with commits in the
        specified range and builds a comprehensive report.

        Args:
            from_commit: Starting commit (None = from beginning)
            to_commit: Ending commit (default: HEAD)
            include_uncommitted: Include events not yet committed

        Returns:
            CommitRangeReport with all work in the range

        Example:
            >>> # Get all work in last 10 commits
            >>> report = cross.work_in_commit_range(
            ...     from_commit="HEAD~10",
            ...     to_commit="HEAD"
            ... )
            >>> logger.info(f"Total events: {report.total_events}")
            >>> logger.info(f"Features: {', '.join(report.features)}")
        """
        # Get commit list from Git
        commits = self._get_commits_in_range(from_commit, to_commit)

        # Build commit hash set for fast lookup
        commit_hashes = {c["hash"] for c in commits}

        # Query events for these commits
        commit_summaries: dict[str, CommitWorkSummary] = {}
        features_set = set()
        sessions_set = set()
        authors_count: dict[str, int] = defaultdict(int)
        work_types_count: dict[str, int] = defaultdict(int)
        total_events = 0

        for _, event in self._event_log.iter_events():
            # Check if event is associated with a commit in our range
            payload = event.get("payload", {})
            commit_hash = payload.get("commit_hash")

            if not commit_hash or commit_hash not in commit_hashes:
                continue

            # Extract event details
            feature_id = event.get("feature_id")
            session_id = event.get("session_id")
            work_type = event.get("work_type")
            author_email = payload.get("author_email", "")

            # Track summary data
            if feature_id:
                features_set.add(feature_id)
            if session_id:
                sessions_set.add(session_id)
            if work_type:
                work_types_count[work_type] += 1
            if author_email:
                authors_count[author_email] += 1

            total_events += 1

            # Build commit summary (or update existing)
            if commit_hash not in commit_summaries:
                # Find commit details
                commit_info = next(
                    (c for c in commits if c["hash"] == commit_hash), None
                )
                if not commit_info:
                    continue

                commit_summaries[commit_hash] = CommitWorkSummary(
                    commit_hash=commit_hash,
                    commit_hash_short=commit_hash[:8],
                    branch=payload.get("branch", ""),
                    author_name=payload.get("author_name", ""),
                    author_email=author_email,
                    commit_message=payload.get("commit_message", ""),
                    timestamp=self._parse_timestamp(event.get("timestamp")),
                    features=[],
                    sessions=[],
                    event_count=0,
                    files_changed=payload.get("files_changed", []),
                    insertions=payload.get("insertions", 0),
                    deletions=payload.get("deletions", 0),
                )

            # Update commit summary
            summary = commit_summaries[commit_hash]
            if feature_id and feature_id not in summary.features:
                summary.features.append(feature_id)
            if session_id and session_id not in summary.sessions:
                summary.sessions.append(session_id)
            summary.event_count += 1

        # Handle uncommitted work
        if include_uncommitted:
            # Find events without commit hashes
            for _, event in self._event_log.iter_events():
                payload = event.get("payload", {})
                if payload.get("commit_hash"):
                    continue  # Already processed

                # Track uncommitted work
                feature_id = event.get("feature_id")
                session_id = event.get("session_id")
                work_type = event.get("work_type")

                if feature_id:
                    features_set.add(feature_id)
                if session_id:
                    sessions_set.add(session_id)
                if work_type:
                    work_types_count[work_type] += 1

                total_events += 1

        return CommitRangeReport(
            from_commit=from_commit or "beginning",
            to_commit=to_commit,
            commits=sorted(
                commit_summaries.values(), key=lambda c: c.timestamp, reverse=True
            ),
            total_events=total_events,
            features=sorted(features_set),
            sessions=sorted(sessions_set),
            authors=dict(authors_count),
            work_types=dict(work_types_count),
        )

    def sessions_for_feature(
        self, feature_id: str, include_cross_session: bool = True
    ) -> list[str]:
        """
        Find all sessions that contributed to a feature.

        Args:
            feature_id: Feature ID to query
            include_cross_session: Include sessions linked via commit graph

        Returns:
            List of session IDs that worked on this feature

        Example:
            >>> sessions = cross.sessions_for_feature("feature-auth")
            >>> logger.info(f"Feature worked on in {len(sessions)} sessions")
        """
        sessions = set()

        # Direct attribution from events
        for _, event in self._event_log.iter_events():
            if event.get("feature_id") == feature_id:
                session_id = event.get("session_id")
                if session_id:
                    sessions.add(session_id)

        # Cross-session via commits (if enabled)
        if include_cross_session:
            # Find commits that mention this feature
            commits_for_feature = set()
            for _, event in self._event_log.iter_events():
                if event.get("feature_id") == feature_id:
                    payload = event.get("payload", {})
                    commit_hash = payload.get("commit_hash")
                    if commit_hash:
                        commits_for_feature.add(commit_hash)

            # Find all sessions that touched these commits
            for _, event in self._event_log.iter_events():
                payload = event.get("payload", {})
                commit_hash = payload.get("commit_hash")
                if commit_hash and commit_hash in commits_for_feature:
                    session_id = event.get("session_id")
                    if session_id:
                        sessions.add(session_id)

        return sorted(sessions)

    def feature_cross_session_report(
        self, feature_id: str
    ) -> FeatureCrossSessionReport:
        """
        Generate comprehensive cross-session report for a feature.

        Args:
            feature_id: Feature ID to analyze

        Returns:
            FeatureCrossSessionReport with complete implementation history

        Example:
            >>> report = cross.feature_cross_session_report("feature-auth")
            >>> logger.info(f"Implemented across {len(report.sessions)} sessions")
            >>> logger.info(f"Duration: {report.duration_hours:.1f} hours")
        """
        sessions = set()
        commits = set()
        authors = set()
        work_types: dict[str, int] = defaultdict(int)
        timestamps: list[datetime] = []
        event_count = 0

        # Scan all events for this feature
        for _, event in self._event_log.iter_events():
            if event.get("feature_id") != feature_id:
                continue

            event_count += 1

            # Track metadata
            session_id = event.get("session_id")
            if session_id:
                sessions.add(session_id)

            payload = event.get("payload", {})
            commit_hash = payload.get("commit_hash")
            if commit_hash:
                commits.add(commit_hash)

            author_email = payload.get("author_email")
            if author_email:
                authors.add(author_email)

            work_type = event.get("work_type")
            if work_type:
                work_types[work_type] += 1

            # Track timing
            timestamp_str = event.get("timestamp")
            if timestamp_str:
                timestamps.append(self._parse_timestamp(timestamp_str))

        # Calculate duration
        start_time = min(timestamps) if timestamps else None
        end_time = max(timestamps) if timestamps else None
        duration_hours = None
        if start_time and end_time:
            duration_hours = (end_time - start_time).total_seconds() / 3600

        return FeatureCrossSessionReport(
            feature_id=feature_id,
            sessions=sorted(sessions),
            commits=sorted(commits),
            authors=sorted(authors),
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration_hours,
            event_count=event_count,
            work_type_distribution=dict(work_types),
        )

    def work_by_author(
        self, since_commit: str | None = None, author_email: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """
        Analyze work by author across the project.

        Args:
            since_commit: Only analyze work since this commit
            author_email: Filter to specific author (None = all authors)

        Returns:
            Dictionary mapping author_email to work statistics

        Example:
            >>> authors = cross.work_by_author(since_commit="v1.0.0")
            >>> for email, stats in authors.items():
            ...     logger.info(f"{email}: {stats['event_count']} events")
        """
        authors: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "event_count": 0,
                "features": set(),
                "sessions": set(),
                "commits": set(),
                "work_types": defaultdict(int),
            }
        )

        # Get commit range if specified
        commit_hashes = None
        if since_commit:
            commits = self._get_commits_in_range(since_commit, "HEAD")
            commit_hashes = {c["hash"] for c in commits}

        # Scan events
        for _, event in self._event_log.iter_events():
            payload = event.get("payload", {})
            event_author = payload.get("author_email")

            # Skip if filtering by author
            if author_email and event_author != author_email:
                continue

            # Skip if outside commit range
            if commit_hashes:
                commit_hash = payload.get("commit_hash")
                if not commit_hash or commit_hash not in commit_hashes:
                    continue

            if not event_author:
                continue

            # Track statistics
            author_stats = authors[event_author]
            author_stats["event_count"] += 1

            feature_id = event.get("feature_id")
            if feature_id:
                author_stats["features"].add(feature_id)

            session_id = event.get("session_id")
            if session_id:
                author_stats["sessions"].add(session_id)

            commit_hash = payload.get("commit_hash")
            if commit_hash:
                author_stats["commits"].add(commit_hash)

            work_type = event.get("work_type")
            if work_type:
                author_stats["work_types"][work_type] += 1

        # Convert sets to lists for JSON serialization
        result = {}
        for email, stats in authors.items():
            result[email] = {
                "event_count": stats["event_count"],
                "features": sorted(stats["features"]),
                "sessions": sorted(stats["sessions"]),
                "commits": sorted(stats["commits"]),
                "work_types": dict(stats["work_types"]),
            }

        return result

    def commits_for_session(self, session_id: str) -> list[str]:
        """
        Get all commits associated with a session.

        Args:
            session_id: Session ID to query

        Returns:
            List of commit hashes (in chronological order)

        Example:
            >>> commits = cross.commits_for_session("session-abc")
            >>> logger.info(f"Session produced {len(commits)} commits")
        """
        commits = set()

        for _, event in self._event_log.iter_events():
            if event.get("session_id") != session_id:
                continue

            payload = event.get("payload", {})
            commit_hash = payload.get("commit_hash")
            if commit_hash:
                commits.add(commit_hash)

        # Get commit timestamps from Git for chronological ordering
        commit_list = []
        for commit_hash in commits:
            try:
                timestamp = self._get_commit_timestamp(commit_hash)
                commit_list.append((timestamp, commit_hash))
            except Exception:
                commit_list.append((datetime.min, commit_hash))

        commit_list.sort(key=lambda x: x[0])
        return [commit_hash for _, commit_hash in commit_list]

    # === Private Helper Methods ===

    def _find_repo_root(self, start_path: Path) -> Path | None:
        """Find the Git repository root directory."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(start_path),
                capture_output=True,
                text=True,
                check=True,
            )
            return Path(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _get_commits_in_range(
        self, from_commit: str | None, to_commit: str
    ) -> list[dict[str, Any]]:
        """
        Get list of commits in a range using Git.

        Args:
            from_commit: Starting commit (None = from beginning)
            to_commit: Ending commit

        Returns:
            List of commit dictionaries with hash, author, date, message
        """
        if not self._repo_root:
            return []

        try:
            # Build Git log command
            if from_commit:
                rev_range = f"{from_commit}..{to_commit}"
            else:
                rev_range = to_commit

            # Get commit info in JSON-like format
            result = subprocess.run(
                [
                    "git",
                    "log",
                    rev_range,
                    "--pretty=format:%H|%h|%an|%ae|%aI|%s",
                ],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                check=True,
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) < 6:
                    continue

                commits.append(
                    {
                        "hash": parts[0],
                        "hash_short": parts[1],
                        "author_name": parts[2],
                        "author_email": parts[3],
                        "date": parts[4],
                        "subject": parts[5],
                    }
                )

            return commits

        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def _get_commit_timestamp(self, commit_hash: str) -> datetime:
        """Get timestamp for a commit."""
        if not self._repo_root:
            raise ValueError("Not in a Git repository")

        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%aI", commit_hash],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                check=True,
            )
            return datetime.fromisoformat(result.stdout.strip())
        except subprocess.CalledProcessError:
            raise ValueError(f"Commit not found: {commit_hash}")

    def _parse_timestamp(self, timestamp: str | datetime | None) -> datetime:
        """Parse timestamp from various formats."""
        if timestamp is None:
            return utc_now()

        if isinstance(timestamp, datetime):
            return timestamp

        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return utc_now()

        return utc_now()
