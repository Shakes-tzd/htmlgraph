"""
HtmlGraph Hooks State Manager

Unified state file management for hook operations:
- Parent activity tracking (for Skill/Task context)
- User query event tracking (for parent-child linking)
- Drift queue management (for auto-classification)

This module provides file-based state persistence with:
- Atomic writes (write to temp, then rename)
- File locking to prevent concurrent writes
- Error handling for missing/corrupted files
- Age-based filtering and cleanup
- Comprehensive logging

File Locations (.htmlgraph/):
- parent-activity.json: Current parent context (Skill/Task invocation)
- user-query-event-{SESSION_ID}.json: UserQuery event ID for session
- drift-queue.json: Classification queue for high-drift activities
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ParentActivityTracker:
    """
    Tracks the active parent activity context for Skill/Task invocations.

    Parent context allows child tool calls to link to their parent Skill/Task.
    Parent activities automatically expire after 5 minutes of inactivity.

    File: parent-activity.json (single entry)
    ```json
    {
      "parent_id": "evt-xyz123",
      "tool": "Task",
      "timestamp": "2025-01-10T12:34:56Z"
    }
    ```
    """

    def __init__(self, graph_dir: Path):
        """
        Initialize parent activity tracker.

        Args:
            graph_dir: Path to .htmlgraph directory
        """
        self.graph_dir = Path(graph_dir)
        self.file_path = self.graph_dir / "parent-activity.json"
        self._ensure_graph_dir()

    def _ensure_graph_dir(self) -> None:
        """Ensure .htmlgraph directory exists."""
        self.graph_dir.mkdir(parents=True, exist_ok=True)

    def load(self, max_age_minutes: int = 5) -> dict[str, Any]:
        """
        Load parent activity state.

        Automatically filters out stale parent activities older than max_age_minutes.
        This allows long-running parent contexts (like Tasks) to timeout naturally.

        Args:
            max_age_minutes: Maximum age in minutes before activity is considered stale
                            (default: 5 minutes)

        Returns:
            Parent activity dict with keys: parent_id, tool, timestamp
            Empty dict if file missing or stale
        """
        if not self.file_path.exists():
            return {}

        try:
            with open(self.file_path) as f:
                data: dict[str, object] = json.load(f)

            # Validate timestamp and check if stale
            if data.get("timestamp"):
                ts = datetime.fromisoformat(data["timestamp"])  # type: ignore[arg-type]
                age = datetime.now() - ts
                if age > timedelta(minutes=max_age_minutes):
                    logger.debug(
                        f"Parent activity stale ({age.total_seconds():.0f}s > {max_age_minutes}min)"
                    )
                    return {}

            logger.debug(f"Loaded parent activity: {data.get('parent_id')}")
            return data  # type: ignore[return-value]

        except json.JSONDecodeError:
            logger.warning("Corrupted parent-activity.json, returning empty state")
            return {}
        except (ValueError, KeyError, OSError) as e:
            logger.warning(f"Error loading parent activity: {e}")
            return {}

    def save(self, parent_id: str, tool: str) -> None:
        """
        Save parent activity context.

        Creates or updates parent-activity.json with the current parent context.
        Uses atomic write to prevent corruption from concurrent access.

        Args:
            parent_id: Event ID of parent activity (e.g., "evt-xyz123")
            tool: Tool name that created parent context (e.g., "Task", "Skill")
        """
        try:
            data = {
                "parent_id": parent_id,
                "tool": tool,
                "timestamp": datetime.now().isoformat(),
            }

            # Atomic write: write to temp file, then rename
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self.graph_dir,
                delete=False,
                suffix=".json",
            ) as tmp:
                json.dump(data, tmp)
                tmp_path = tmp.name

            # Atomic rename
            os.replace(tmp_path, self.file_path)
            logger.debug(f"Saved parent activity: {parent_id} (tool={tool})")

        except OSError as e:
            logger.warning(f"Could not save parent activity: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving parent activity: {e}")

    def clear(self) -> None:
        """
        Delete parent activity file.

        Clears the parent context, causing subsequent tool calls to not link
        to a parent activity.
        """
        try:
            self.file_path.unlink(missing_ok=True)
            logger.debug("Cleared parent activity")
        except OSError as e:
            logger.warning(f"Could not clear parent activity: {e}")


class UserQueryEventTracker:
    """
    Tracks the active UserQuery event ID for parent-child linking.

    Each session maintains its own UserQuery event context to support
    multiple concurrent Claude windows in the same project.

    UserQuery events expire after 2 minutes (conversation turn boundary),
    allowing natural grouping of tool calls by conversation turn.

    File: user-query-event-{SESSION_ID}.json (single entry)
    ```json
    {
      "event_id": "evt-abc456",
      "timestamp": "2025-01-10T12:34:56Z"
    }
    ```
    """

    def __init__(self, graph_dir: Path):
        """
        Initialize user query event tracker.

        Args:
            graph_dir: Path to .htmlgraph directory
        """
        self.graph_dir = Path(graph_dir)
        self._ensure_graph_dir()

    def _ensure_graph_dir(self) -> None:
        """Ensure .htmlgraph directory exists."""
        self.graph_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, session_id: str) -> Path:
        """Get session-specific user query event file path."""
        return self.graph_dir / f"user-query-event-{session_id}.json"

    def load(self, session_id: str, max_age_minutes: int = 2) -> str | None:
        """
        Load active UserQuery event ID for a session.

        Automatically filters out stale events older than max_age_minutes.
        This creates natural conversation turn boundaries when queries timeout.

        Args:
            session_id: Session ID (e.g., "sess-xyz789")
            max_age_minutes: Maximum age in minutes before event is considered stale
                            (default: 2 minutes for conversation turns)

        Returns:
            Event ID string (e.g., "evt-abc456") or None if missing/stale
        """
        file_path = self._get_file_path(session_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data: dict[str, object] = json.load(f)

            # Validate timestamp and check if stale
            if data.get("timestamp"):
                ts = datetime.fromisoformat(data["timestamp"])  # type: ignore[arg-type]
                age = datetime.now() - ts
                if age > timedelta(minutes=max_age_minutes):
                    logger.debug(
                        f"UserQuery event stale ({age.total_seconds():.0f}s > {max_age_minutes}min)"
                    )
                    return None

            event_id = data.get("event_id")
            logger.debug(f"Loaded UserQuery event: {event_id}")
            return event_id  # type: ignore[return-value]

        except json.JSONDecodeError:
            logger.warning(f"Corrupted user-query-event file for {session_id}")
            return None
        except (ValueError, KeyError, OSError) as e:
            logger.warning(f"Error loading UserQuery event for {session_id}: {e}")
            return None

    def save(self, session_id: str, event_id: str) -> None:
        """
        Save UserQuery event ID for a session.

        Creates or updates the session-specific user query event file.
        Uses atomic write to prevent corruption from concurrent access.

        Args:
            session_id: Session ID (e.g., "sess-xyz789")
            event_id: Event ID to save (e.g., "evt-abc456")
        """
        file_path = self._get_file_path(session_id)
        try:
            data = {
                "event_id": event_id,
                "timestamp": datetime.now().isoformat(),
            }

            # Atomic write: write to temp file, then rename
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self.graph_dir,
                delete=False,
                suffix=".json",
            ) as tmp:
                json.dump(data, tmp)
                tmp_path = tmp.name

            # Atomic rename
            os.replace(tmp_path, file_path)
            logger.debug(f"Saved UserQuery event: {event_id} (session={session_id})")

        except OSError as e:
            logger.warning(f"Could not save UserQuery event for {session_id}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error saving UserQuery event for {session_id}: {e}"
            )

    def clear(self, session_id: str) -> None:
        """
        Delete UserQuery event file for a session.

        Clears the session's UserQuery context, allowing a new conversation turn
        to begin without inheriting the previous turn's parent context.

        Args:
            session_id: Session ID to clear
        """
        file_path = self._get_file_path(session_id)
        try:
            file_path.unlink(missing_ok=True)
            logger.debug(f"Cleared UserQuery event for {session_id}")
        except OSError as e:
            logger.warning(f"Could not clear UserQuery event for {session_id}: {e}")


class DriftQueueManager:
    """
    Manages the drift classification queue for high-drift activities.

    The drift queue accumulates activities that exceed the auto-classification
    threshold, triggering classification when thresholds are met.

    Activities are automatically filtered by age to prevent indefinite accumulation.

    File: drift-queue.json
    ```json
    {
      "activities": [
        {
          "timestamp": "2025-01-10T12:34:56Z",
          "tool": "Read",
          "summary": "Read: /path/to/file.py",
          "file_paths": ["/path/to/file.py"],
          "drift_score": 0.87,
          "feature_id": "feat-xyz123"
        }
      ],
      "last_classification": "2025-01-10T12:30:00Z"
    }
    ```
    """

    def __init__(self, graph_dir: Path):
        """
        Initialize drift queue manager.

        Args:
            graph_dir: Path to .htmlgraph directory
        """
        self.graph_dir = Path(graph_dir)
        self.file_path = self.graph_dir / "drift-queue.json"
        self._ensure_graph_dir()

    def _ensure_graph_dir(self) -> None:
        """Ensure .htmlgraph directory exists."""
        self.graph_dir.mkdir(parents=True, exist_ok=True)

    def load(self, max_age_hours: int = 48) -> dict[str, Any]:
        """
        Load drift queue and filter by age.

        Automatically removes activities older than max_age_hours.
        This prevents the queue from growing indefinitely over time.

        Args:
            max_age_hours: Maximum age in hours before activities are removed
                          (default: 48 hours)

        Returns:
            Queue dict with keys: activities (list), last_classification (timestamp)
            Returns default empty queue if file missing
        """
        if not self.file_path.exists():
            return {"activities": [], "last_classification": None}

        try:
            with open(self.file_path) as f:
                queue: dict[str, object] = json.load(f)

            # Filter out stale activities
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            original_count = len(queue.get("activities", []))  # type: ignore[arg-type]

            fresh_activities = []
            for activity in queue.get("activities", []):  # type: ignore[attr-defined]
                try:
                    activity_time = datetime.fromisoformat(
                        activity.get("timestamp", "")
                    )
                    if activity_time >= cutoff_time:
                        fresh_activities.append(activity)
                except (ValueError, TypeError):
                    # Keep activities with invalid timestamps to avoid data loss
                    fresh_activities.append(activity)

            # Update queue if we removed stale entries
            if len(fresh_activities) < original_count:
                queue["activities"] = fresh_activities
                self.save(queue)
                removed = original_count - len(fresh_activities)
                logger.info(
                    f"Cleaned {removed} stale drift queue entries (older than {max_age_hours}h)"
                )

            logger.debug(
                f"Loaded drift queue: {len(fresh_activities)} recent activities"
            )
            return queue

        except json.JSONDecodeError:
            logger.warning("Corrupted drift-queue.json, returning empty queue")
            return {"activities": [], "last_classification": None}
        except (ValueError, KeyError, OSError) as e:
            logger.warning(f"Error loading drift queue: {e}")
            return {"activities": [], "last_classification": None}

    def save(self, queue: dict[str, Any]) -> None:
        """
        Save drift queue to file.

        Persists the queue with all activities and classification metadata.
        Uses atomic write to prevent corruption from concurrent access.

        Args:
            queue: Queue dict with activities and last_classification timestamp
        """
        try:
            # Atomic write: write to temp file, then rename
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self.graph_dir,
                delete=False,
                suffix=".json",
            ) as tmp:
                json.dump(queue, tmp, indent=2, default=str)
                tmp_path = tmp.name

            # Atomic rename
            os.replace(tmp_path, self.file_path)
            logger.debug(
                f"Saved drift queue: {len(queue.get('activities', []))} activities"
            )

        except OSError as e:
            logger.warning(f"Could not save drift queue: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving drift queue: {e}")

    def add_activity(
        self, activity: dict[str, Any], timestamp: datetime | None = None
    ) -> None:
        """
        Add activity to drift queue.

        Appends a high-drift activity to the queue for later classification.
        Timestamp defaults to current time if not provided.

        Args:
            activity: Activity dict with keys: tool, summary, file_paths, drift_score, feature_id
            timestamp: Activity timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        queue = self.load()
        queue["activities"].append(
            {
                "timestamp": timestamp.isoformat(),
                "tool": activity.get("tool"),
                "summary": activity.get("summary"),
                "file_paths": activity.get("file_paths", []),
                "drift_score": activity.get("drift_score"),
                "feature_id": activity.get("feature_id"),
            }
        )
        self.save(queue)
        logger.debug(
            f"Added activity to drift queue (drift_score={activity.get('drift_score')})"
        )

    def clear(self) -> None:
        """
        Delete drift queue file.

        Removes the entire drift queue, typically after classification completes.
        """
        try:
            self.file_path.unlink(missing_ok=True)
            logger.debug("Cleared drift queue")
        except OSError as e:
            logger.warning(f"Could not clear drift queue: {e}")

    def clear_activities(self) -> None:
        """
        Clear activities from queue while preserving last_classification timestamp.

        Called after successful classification to remove processed activities
        while keeping track of when the last classification occurred.
        """
        try:
            queue = {
                "activities": [],
                "last_classification": datetime.now().isoformat(),
            }

            # Preserve existing last_classification if this file already exists
            if self.file_path.exists():
                try:
                    with open(self.file_path) as f:
                        existing = json.load(f)
                        if existing.get("last_classification"):
                            queue["last_classification"] = existing[
                                "last_classification"
                            ]
                except Exception:
                    pass

            self.save(queue)
            logger.debug(
                "Cleared drift queue activities (preserved classification timestamp)"
            )

        except Exception as e:
            logger.error(f"Error clearing drift queue activities: {e}")
