"""
PreferenceManager - Learns user preferences from feedback.

This module provides preference learning and management:
1. Feedback collection - Record user acceptance/rejection of suggestions
2. Preference weighting - Calculate preference scores from feedback
3. User preferences - Store and retrieve individual user preferences
4. Recommendation tuning - Adjust suggestions based on learned preferences

Usage:
    from htmlgraph.analytics.strategic import PreferenceManager

    manager = PreferenceManager(db_path)

    # Record feedback on a suggestion
    manager.record_feedback(
        suggestion_id="sug-abc123",
        accepted=True,
        outcome="successful"
    )

    # Get user preferences
    preferences = manager.get_preferences(user_id="claude")

    # Reset preferences
    manager.reset_preferences(user_id="claude")
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback that can be recorded."""

    ACCEPTED = "accepted"  # User accepted suggestion
    REJECTED = "rejected"  # User rejected suggestion
    IGNORED = "ignored"  # User ignored suggestion
    MODIFIED = "modified"  # User modified suggestion before using


class OutcomeType(Enum):
    """Outcome types for feedback tracking."""

    SUCCESSFUL = "successful"  # Task completed successfully
    FAILED = "failed"  # Task failed
    PARTIAL = "partial"  # Partially successful
    UNKNOWN = "unknown"  # Outcome not tracked


@dataclass
class Feedback:
    """
    Feedback on a suggestion.

    Attributes:
        feedback_id: Unique identifier
        suggestion_id: ID of the suggestion being rated
        user_id: User providing feedback
        session_id: Session where feedback was given
        feedback_type: Type of feedback (accepted, rejected, etc.)
        outcome: Outcome of following the suggestion
        rating: Optional numeric rating (1-5)
        comment: Optional text comment
        context: Additional context about the feedback
        created_at: When feedback was recorded
    """

    feedback_id: str
    suggestion_id: str
    user_id: str
    session_id: str
    feedback_type: FeedbackType
    outcome: OutcomeType = OutcomeType.UNKNOWN
    rating: int | None = None
    comment: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert feedback to dictionary for serialization."""
        return {
            "feedback_id": self.feedback_id,
            "suggestion_id": self.suggestion_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "feedback_type": self.feedback_type.value,
            "outcome": self.outcome.value,
            "rating": self.rating,
            "comment": self.comment,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class UserPreferences:
    """
    Learned preferences for a user.

    Attributes:
        user_id: User identifier
        model_preferences: Preference weights for different models
        delegation_preferences: Preference weights for delegation types
        tool_preferences: Preference weights for different tools
        suggestion_type_preferences: Preference weights for suggestion types
        quality_thresholds: Minimum thresholds for various quality metrics
        cost_sensitivity: How much user values cost vs quality (0-1)
        speed_sensitivity: How much user values speed vs thoroughness (0-1)
        updated_at: When preferences were last updated
    """

    user_id: str
    model_preferences: dict[str, float] = field(default_factory=dict)
    delegation_preferences: dict[str, float] = field(default_factory=dict)
    tool_preferences: dict[str, float] = field(default_factory=dict)
    suggestion_type_preferences: dict[str, float] = field(default_factory=dict)
    quality_thresholds: dict[str, float] = field(default_factory=dict)
    cost_sensitivity: float = 0.5  # 0=ignore cost, 1=minimize cost
    speed_sensitivity: float = 0.5  # 0=ignore speed, 1=maximize speed
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert preferences to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "model_preferences": self.model_preferences,
            "delegation_preferences": self.delegation_preferences,
            "tool_preferences": self.tool_preferences,
            "suggestion_type_preferences": self.suggestion_type_preferences,
            "quality_thresholds": self.quality_thresholds,
            "cost_sensitivity": self.cost_sensitivity,
            "speed_sensitivity": self.speed_sensitivity,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def default(cls, user_id: str) -> "UserPreferences":
        """
        Create default preferences for a new user.

        Args:
            user_id: User identifier

        Returns:
            UserPreferences with default values
        """
        return cls(
            user_id=user_id,
            model_preferences={
                "claude-opus": 0.5,
                "claude-sonnet": 0.5,
                "claude-haiku": 0.5,
            },
            delegation_preferences={
                "researcher": 0.5,
                "coder": 0.5,
                "tester": 0.5,
                "debugger": 0.5,
            },
            tool_preferences={},  # Will be populated from usage
            suggestion_type_preferences={
                "next_action": 0.5,
                "delegation": 0.5,
                "parameter": 0.5,
                "model_selection": 0.5,
                "error_resolution": 0.5,
                "workflow": 0.5,
            },
            quality_thresholds={
                "min_test_coverage": 0.8,
                "max_loc_reduction": 0.3,
                "min_success_rate": 0.7,
            },
            cost_sensitivity=0.5,
            speed_sensitivity=0.5,
            updated_at=datetime.now(),
        )


class PreferenceManager:
    """
    Manages user preferences and feedback learning.

    Collects feedback on suggestions and learns user preferences
    to improve future recommendation quality.
    """

    def __init__(self, db_path: Path | str | None = None):
        """
        Initialize preference manager.

        Args:
            db_path: Path to HtmlGraph database. If None, uses default location.
        """
        if db_path is None:
            from htmlgraph.config import get_database_path

            db_path = get_database_path()

        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

        # Learning parameters
        self._learning_rate = 0.1  # How fast preferences update
        self._decay_factor = 0.95  # Older feedback matters less

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def record_feedback(
        self,
        suggestion_id: str,
        accepted: bool,
        user_id: str = "default",
        session_id: str = "",
        outcome: str = "unknown",
        rating: int | None = None,
        comment: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Record feedback on a suggestion.

        Args:
            suggestion_id: ID of the suggestion
            accepted: Whether user accepted the suggestion
            user_id: User providing feedback
            session_id: Current session ID
            outcome: Outcome of following suggestion (successful, failed, etc.)
            rating: Optional 1-5 rating
            comment: Optional text comment
            context: Additional context

        Returns:
            Feedback ID if successful, None otherwise
        """
        import uuid

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            feedback_id = f"fb-{uuid.uuid4().hex[:8]}"
            feedback_type = FeedbackType.ACCEPTED if accepted else FeedbackType.REJECTED

            try:
                outcome_type = OutcomeType(outcome)
            except ValueError:
                outcome_type = OutcomeType.UNKNOWN

            cursor.execute(
                """
                INSERT INTO delegation_preferences
                (feedback_id, suggestion_id, user_id, session_id, feedback_type,
                 outcome, rating, comment, context, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
                (
                    feedback_id,
                    suggestion_id,
                    user_id,
                    session_id,
                    feedback_type.value,
                    outcome_type.value,
                    rating,
                    comment,
                    json.dumps(context) if context else None,
                ),
            )

            conn.commit()

            # Update user preferences based on feedback
            self._update_preferences_from_feedback(
                user_id, suggestion_id, feedback_type, outcome_type
            )

            return feedback_id

        except sqlite3.Error as e:
            logger.error(f"Error recording feedback: {e}")
            return None

    def _update_preferences_from_feedback(
        self,
        user_id: str,
        suggestion_id: str,
        feedback_type: FeedbackType,
        outcome: OutcomeType,
    ) -> None:
        """
        Update user preferences based on feedback.

        Uses exponential moving average to update preference weights.

        Args:
            user_id: User whose preferences to update
            suggestion_id: Suggestion that was rated
            feedback_type: Type of feedback given
            outcome: Outcome of following suggestion
        """
        try:
            # Get current preferences
            preferences = self.get_preferences(user_id)

            # Get suggestion details to determine what preferences to update
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT suggestion_type, metadata FROM delegation_suggestions
                WHERE suggestion_id = ?
            """,
                (suggestion_id,),
            )

            row = cursor.fetchone()
            if not row:
                return

            suggestion_type = row["suggestion_type"]
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}

            # Calculate feedback value (-1 to 1)
            feedback_value = 0.0
            if feedback_type == FeedbackType.ACCEPTED:
                if outcome == OutcomeType.SUCCESSFUL:
                    feedback_value = 1.0
                elif outcome == OutcomeType.PARTIAL:
                    feedback_value = 0.5
                elif outcome == OutcomeType.FAILED:
                    feedback_value = -0.5
                else:
                    feedback_value = 0.3  # Unknown but accepted
            elif feedback_type == FeedbackType.REJECTED:
                feedback_value = -0.3
            elif feedback_type == FeedbackType.IGNORED:
                feedback_value = -0.1

            # Update suggestion type preference
            current = preferences.suggestion_type_preferences.get(suggestion_type, 0.5)
            new_value = current + self._learning_rate * (
                feedback_value - (current - 0.5)
            )
            new_value = max(0.0, min(1.0, new_value))  # Clamp to [0, 1]
            preferences.suggestion_type_preferences[suggestion_type] = new_value

            # Update model preference if model suggestion
            if suggestion_type == "model_selection" and "recommended_model" in metadata:
                model = metadata["recommended_model"]
                current = preferences.model_preferences.get(model, 0.5)
                new_value = current + self._learning_rate * feedback_value
                new_value = max(0.0, min(1.0, new_value))
                preferences.model_preferences[model] = new_value

            # Update delegation preference if delegation suggestion
            if suggestion_type == "delegation" and "next_agent" in metadata:
                agent = metadata["next_agent"]
                current = preferences.delegation_preferences.get(agent, 0.5)
                new_value = current + self._learning_rate * feedback_value
                new_value = max(0.0, min(1.0, new_value))
                preferences.delegation_preferences[agent] = new_value

            # Store updated preferences
            self._store_preferences(preferences)

        except Exception as e:
            logger.warning(f"Error updating preferences: {e}")

    def get_preferences(self, user_id: str) -> UserPreferences:
        """
        Get preferences for a user.

        Creates default preferences if user has no stored preferences.

        Args:
            user_id: User to get preferences for

        Returns:
            UserPreferences for the user
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT preferences_json, updated_at FROM user_preferences
                WHERE user_id = ?
            """,
                (user_id,),
            )

            row = cursor.fetchone()
            if row and row["preferences_json"]:
                data = json.loads(row["preferences_json"])
                return UserPreferences(
                    user_id=user_id,
                    model_preferences=data.get("model_preferences", {}),
                    delegation_preferences=data.get("delegation_preferences", {}),
                    tool_preferences=data.get("tool_preferences", {}),
                    suggestion_type_preferences=data.get(
                        "suggestion_type_preferences", {}
                    ),
                    quality_thresholds=data.get("quality_thresholds", {}),
                    cost_sensitivity=data.get("cost_sensitivity", 0.5),
                    speed_sensitivity=data.get("speed_sensitivity", 0.5),
                    updated_at=datetime.fromisoformat(row["updated_at"])
                    if row["updated_at"]
                    else None,
                )

            # Return default preferences for new user
            return UserPreferences.default(user_id)

        except sqlite3.Error as e:
            logger.warning(f"Error getting preferences: {e}")
            return UserPreferences.default(user_id)

    def _store_preferences(self, preferences: UserPreferences) -> bool:
        """
        Store user preferences in database.

        Args:
            preferences: Preferences to store

        Returns:
            True if stored successfully, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            preferences_json = json.dumps(
                {
                    "model_preferences": preferences.model_preferences,
                    "delegation_preferences": preferences.delegation_preferences,
                    "tool_preferences": preferences.tool_preferences,
                    "suggestion_type_preferences": preferences.suggestion_type_preferences,
                    "quality_thresholds": preferences.quality_thresholds,
                    "cost_sensitivity": preferences.cost_sensitivity,
                    "speed_sensitivity": preferences.speed_sensitivity,
                }
            )

            cursor.execute(
                """
                INSERT OR REPLACE INTO user_preferences
                (user_id, preferences_json, updated_at)
                VALUES (?, ?, datetime('now'))
            """,
                (preferences.user_id, preferences_json),
            )

            conn.commit()
            return True

        except sqlite3.Error as e:
            logger.error(f"Error storing preferences: {e}")
            return False

    def calculate_weights(self, feedback_list: list[Feedback]) -> dict[str, float]:
        """
        Calculate preference weights from a list of feedback.

        Uses time-decayed weighted average.

        Args:
            feedback_list: List of feedback to analyze

        Returns:
            Dictionary of preference weights by suggestion type
        """
        if not feedback_list:
            return {}

        weights: dict[str, float] = {}
        type_counts: dict[str, int] = {}
        type_sums: dict[str, float] = {}

        # Sort by creation time (oldest first for proper decay)
        sorted_feedback = sorted(
            feedback_list,
            key=lambda f: f.created_at or datetime.min,
        )

        for i, feedback in enumerate(sorted_feedback):
            # Calculate decay factor based on position
            decay = self._decay_factor ** (len(sorted_feedback) - i - 1)

            # Calculate feedback value
            value = 0.0
            if feedback.feedback_type == FeedbackType.ACCEPTED:
                if feedback.outcome == OutcomeType.SUCCESSFUL:
                    value = 1.0
                elif feedback.outcome == OutcomeType.PARTIAL:
                    value = 0.5
                else:
                    value = 0.3
            elif feedback.feedback_type == FeedbackType.REJECTED:
                value = -0.3

            # Get suggestion type from context
            suggestion_type = feedback.context.get("suggestion_type", "unknown")

            if suggestion_type not in type_sums:
                type_sums[suggestion_type] = 0.0
                type_counts[suggestion_type] = 0

            type_sums[suggestion_type] += value * decay
            type_counts[suggestion_type] += 1

        # Calculate weighted averages
        for suggestion_type in type_sums:
            if type_counts[suggestion_type] > 0:
                avg = type_sums[suggestion_type] / type_counts[suggestion_type]
                # Normalize to [0, 1]
                weights[suggestion_type] = (avg + 1) / 2

        return weights

    def reset_preferences(self, user_id: str) -> bool:
        """
        Reset preferences for a user to defaults.

        Args:
            user_id: User to reset

        Returns:
            True if reset successfully, False otherwise
        """
        default_prefs = UserPreferences.default(user_id)
        return self._store_preferences(default_prefs)

    def get_feedback_history(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[Feedback]:
        """
        Get feedback history for a user.

        Args:
            user_id: User to get history for
            limit: Maximum number of feedback entries

        Returns:
            List of feedback entries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT * FROM delegation_preferences
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (user_id, limit),
            )

            feedback_list = []
            for row in cursor.fetchall():
                feedback = Feedback(
                    feedback_id=row["feedback_id"],
                    suggestion_id=row["suggestion_id"],
                    user_id=row["user_id"],
                    session_id=row["session_id"],
                    feedback_type=FeedbackType(row["feedback_type"]),
                    outcome=OutcomeType(row["outcome"]),
                    rating=row["rating"],
                    comment=row["comment"],
                    context=json.loads(row["context"]) if row["context"] else {},
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None,
                )
                feedback_list.append(feedback)

            return feedback_list

        except sqlite3.Error as e:
            logger.error(f"Error getting feedback history: {e}")
            return []

    def get_acceptance_rate(
        self, user_id: str, suggestion_type: str | None = None
    ) -> float:
        """
        Calculate suggestion acceptance rate for a user.

        Args:
            user_id: User to calculate for
            suggestion_type: Optional filter by suggestion type

        Returns:
            Acceptance rate as percentage (0-100)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if suggestion_type:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN feedback_type = 'accepted' THEN 1 ELSE 0 END) as accepted
                    FROM delegation_preferences dp
                    JOIN delegation_suggestions ds ON dp.suggestion_id = ds.suggestion_id
                    WHERE dp.user_id = ?
                    AND ds.suggestion_type = ?
                """,
                    (user_id, suggestion_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN feedback_type = 'accepted' THEN 1 ELSE 0 END) as accepted
                    FROM delegation_preferences
                    WHERE user_id = ?
                """,
                    (user_id,),
                )

            row = cursor.fetchone()
            if row and row["total"] > 0:
                return float((row["accepted"] / row["total"]) * 100)
            return 0.0

        except sqlite3.Error as e:
            logger.error(f"Error calculating acceptance rate: {e}")
            return 0.0

    def apply_preferences_to_suggestions(
        self,
        suggestions: list[Any],  # List of Suggestion objects
        user_id: str,
    ) -> list[Any]:
        """
        Adjust suggestion scores based on user preferences.

        Args:
            suggestions: List of suggestions to adjust
            user_id: User whose preferences to apply

        Returns:
            Adjusted suggestions (same list, modified in place)
        """
        preferences = self.get_preferences(user_id)

        for suggestion in suggestions:
            # Get preference weight for this suggestion type
            suggestion_type = suggestion.suggestion_type.value
            pref_weight = preferences.suggestion_type_preferences.get(
                suggestion_type, 0.5
            )

            # Adjust relevance based on preference
            # Preferences > 0.5 boost relevance, < 0.5 reduce it
            adjustment = (pref_weight - 0.5) * 0.4  # Max +/- 0.2 adjustment
            suggestion.relevance = max(0.0, min(1.0, suggestion.relevance + adjustment))

            # Apply model preference if model suggestion
            if (
                suggestion_type == "model_selection"
                and "recommended_model" in suggestion.metadata
            ):
                model = suggestion.metadata["recommended_model"]
                model_pref = preferences.model_preferences.get(model, 0.5)
                model_adjustment = (model_pref - 0.5) * 0.3
                suggestion.confidence = max(
                    0.0, min(1.0, suggestion.confidence + model_adjustment)
                )

            # Apply delegation preference if delegation suggestion
            if suggestion_type == "delegation" and "next_agent" in suggestion.metadata:
                agent = suggestion.metadata["next_agent"]
                agent_pref = preferences.delegation_preferences.get(agent, 0.5)
                agent_adjustment = (agent_pref - 0.5) * 0.3
                suggestion.confidence = max(
                    0.0, min(1.0, suggestion.confidence + agent_adjustment)
                )

        return suggestions
