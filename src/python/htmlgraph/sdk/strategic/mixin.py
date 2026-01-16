"""
Strategic Analytics Mixin for SDK

Provides SDK methods for accessing Phase 3 Strategic Analytics:
- Pattern detection (tool sequences, delegation chains, error patterns)
- Suggestion generation (next actions, delegations, model selection)
- Preference management (feedback, learning, personalization)
- Cost optimization (token budgets, parallelization, model selection)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

logger = logging.getLogger(__name__)


@dataclass
class StrategicAnalyticsInterface:
    """
    Interface for strategic analytics operations.

    Provides access to:
    - PatternDetector for pattern detection
    - SuggestionEngine for generating suggestions
    - PreferenceManager for preference learning
    - CostOptimizer for cost optimization

    This interface is exposed as sdk.strategic on the SDK.
    """

    _sdk: SDK
    _db_path: Path | None = None

    def __post_init__(self) -> None:
        """Initialize database path."""
        from htmlgraph.config import get_database_path

        self._db_path = get_database_path()

    # ===== Pattern Detection =====

    def detect_patterns(
        self,
        min_frequency: int = 3,
        days_back: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Detect all patterns from event history.

        Analyzes tool sequences, delegation chains, and error patterns
        to identify successful workflows.

        Args:
            min_frequency: Minimum occurrences to be considered a pattern
            days_back: Number of days of history to analyze

        Returns:
            List of pattern dictionaries sorted by confidence

        Example:
            >>> sdk = SDK(agent="claude")
            >>> patterns = sdk.strategic.detect_patterns()
            >>> for p in patterns[:5]:
            ...     print(f"{p['pattern_type']}: {p['confidence']:.0%}")
        """
        try:
            from htmlgraph.analytics.strategic import PatternDetector

            detector = PatternDetector(self._db_path)
            patterns = detector.detect_all_patterns(
                min_frequency=min_frequency,
                days_back=days_back,
            )
            detector.close()

            return [p.to_dict() for p in patterns]
        except ImportError:
            logger.warning("Strategic analytics not available")
            return []
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return []

    def detect_tool_sequences(
        self,
        window_size: int = 3,
        min_frequency: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Detect common tool call sequence patterns.

        Args:
            window_size: Number of consecutive tools in each sequence
            min_frequency: Minimum occurrences to be considered a pattern

        Returns:
            List of tool sequence patterns

        Example:
            >>> sequences = sdk.strategic.detect_tool_sequences()
            >>> for seq in sequences[:3]:
            ...     print(f"Sequence: {' -> '.join(seq['sequence'])}")
        """
        try:
            from htmlgraph.analytics.strategic import PatternDetector

            detector = PatternDetector(self._db_path)
            patterns = detector.detect_tool_sequences(
                window_size=window_size,
                min_frequency=min_frequency,
            )
            detector.close()

            return [p.to_dict() for p in patterns]
        except Exception as e:
            logger.error(f"Error detecting tool sequences: {e}")
            return []

    def detect_delegation_chains(
        self,
        min_frequency: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Detect common delegation chain patterns.

        Identifies which agent combinations work well together.

        Args:
            min_frequency: Minimum occurrences to be considered a pattern

        Returns:
            List of delegation chain patterns

        Example:
            >>> chains = sdk.strategic.detect_delegation_chains()
            >>> for chain in chains:
            ...     print(f"Chain: {' -> '.join(chain['agents'])}")
        """
        try:
            from htmlgraph.analytics.strategic import PatternDetector

            detector = PatternDetector(self._db_path)
            patterns = detector.detect_delegation_chains(min_frequency=min_frequency)
            detector.close()

            return [p.to_dict() for p in patterns]
        except Exception as e:
            logger.error(f"Error detecting delegation chains: {e}")
            return []

    # ===== Suggestion Engine =====

    def get_suggestions(
        self,
        task_description: str = "",
        max_suggestions: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get suggestions based on current context and learned patterns.

        Args:
            task_description: Current task (optional, improves suggestions)
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggestion dictionaries sorted by score

        Example:
            >>> suggestions = sdk.strategic.get_suggestions(
            ...     task_description="Implement user authentication"
            ... )
            >>> for s in suggestions:
            ...     print(f"{s['title']} ({s['confidence']:.0%})")
        """
        try:
            from htmlgraph.analytics.strategic import SuggestionEngine
            from htmlgraph.analytics.strategic.suggestion_engine import TaskContext

            engine = SuggestionEngine(self._db_path)

            context = TaskContext(
                current_task=task_description,
                agent_type=self._sdk._agent_id or "orchestrator",
            )

            suggestions = engine.suggest(context, max_suggestions=max_suggestions)
            engine.close()

            return [s.to_dict() for s in suggestions]
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []

    def generate_task_code(self, pattern_id: str) -> str | None:
        """
        Generate Task() code from a detected pattern.

        Args:
            pattern_id: ID of pattern to generate code from

        Returns:
            Python code snippet or None if pattern not found

        Example:
            >>> code = sdk.strategic.generate_task_code("tsp-abc123")
            >>> print(code)
        """
        try:
            from htmlgraph.analytics.strategic import PatternDetector, SuggestionEngine

            detector = PatternDetector(self._db_path)
            engine = SuggestionEngine(self._db_path)

            pattern = detector.get_pattern_by_id(pattern_id)
            if pattern:
                code = engine.generate_task_code(pattern)
                detector.close()
                engine.close()
                return code

            detector.close()
            engine.close()
            return None
        except Exception as e:
            logger.error(f"Error generating task code: {e}")
            return None

    # ===== Preference Management =====

    def get_preferences(self, user_id: str = "default") -> dict[str, Any]:
        """
        Get learned preferences for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of preference settings

        Example:
            >>> prefs = sdk.strategic.get_preferences()
            >>> print(f"Model preferences: {prefs['model_preferences']}")
        """
        try:
            from htmlgraph.analytics.strategic import PreferenceManager

            manager = PreferenceManager(self._db_path)
            prefs = manager.get_preferences(user_id)
            manager.close()

            return prefs.to_dict()
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return {}

    def record_feedback(
        self,
        suggestion_id: str,
        accepted: bool,
        outcome: str = "unknown",
        comment: str | None = None,
    ) -> str | None:
        """
        Record feedback on a suggestion.

        This enables the system to learn from user decisions.

        Args:
            suggestion_id: ID of the suggestion
            accepted: Whether user accepted the suggestion
            outcome: Result of following suggestion (successful, failed, partial)
            comment: Optional text comment

        Returns:
            Feedback ID if successful, None otherwise

        Example:
            >>> sdk.strategic.record_feedback(
            ...     suggestion_id="sug-abc123",
            ...     accepted=True,
            ...     outcome="successful"
            ... )
        """
        try:
            from htmlgraph.analytics.strategic import PreferenceManager

            manager = PreferenceManager(self._db_path)
            feedback_id = manager.record_feedback(
                suggestion_id=suggestion_id,
                accepted=accepted,
                user_id="default",
                session_id=self._sdk._parent_session or "cli-session",
                outcome=outcome,
                comment=comment,
            )
            manager.close()

            return feedback_id
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")
            return None

    def reset_preferences(self, user_id: str = "default") -> bool:
        """
        Reset preferences to defaults.

        Args:
            user_id: User to reset

        Returns:
            True if reset successfully

        Example:
            >>> sdk.strategic.reset_preferences()
        """
        try:
            from htmlgraph.analytics.strategic import PreferenceManager

            manager = PreferenceManager(self._db_path)
            result = manager.reset_preferences(user_id)
            manager.close()

            return result
        except Exception as e:
            logger.error(f"Error resetting preferences: {e}")
            return False

    def get_acceptance_rate(
        self,
        suggestion_type: str | None = None,
    ) -> float:
        """
        Get suggestion acceptance rate.

        Args:
            suggestion_type: Optional filter by type

        Returns:
            Acceptance rate as percentage (0-100)

        Example:
            >>> rate = sdk.strategic.get_acceptance_rate("delegation")
            >>> print(f"Delegation suggestions: {rate:.0f}% accepted")
        """
        try:
            from htmlgraph.analytics.strategic import PreferenceManager

            manager = PreferenceManager(self._db_path)
            rate = manager.get_acceptance_rate("default", suggestion_type)
            manager.close()

            return rate
        except Exception as e:
            logger.error(f"Error getting acceptance rate: {e}")
            return 0.0

    # ===== Cost Optimization =====

    def suggest_token_budget(
        self,
        task_description: str,
        tool_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Get token budget suggestion for a task.

        Args:
            task_description: Description of the task
            tool_name: Specific tool being used (optional)

        Returns:
            Token budget recommendation

        Example:
            >>> budget = sdk.strategic.suggest_token_budget(
            ...     "Implement caching for API"
            ... )
            >>> print(f"Recommended: {budget['recommended']} tokens")
        """
        try:
            from htmlgraph.analytics.strategic import CostOptimizer

            optimizer = CostOptimizer(self._db_path)
            budget = optimizer.suggest_token_budget(task_description, tool_name)
            optimizer.close()

            return budget.to_dict()
        except Exception as e:
            logger.error(f"Error suggesting token budget: {e}")
            return {"recommended": 5000, "minimum": 2500, "maximum": 10000}

    def choose_model(
        self,
        task_description: str,
        budget_constraint: int | None = None,
    ) -> dict[str, Any]:
        """
        Get model selection recommendation.

        Args:
            task_description: Description of the task
            budget_constraint: Maximum token budget (optional)

        Returns:
            Model recommendation

        Example:
            >>> model = sdk.strategic.choose_model(
            ...     "Refactor authentication system"
            ... )
            >>> print(f"Recommended: {model['recommended_model']}")
        """
        try:
            from htmlgraph.analytics.strategic import CostOptimizer

            optimizer = CostOptimizer(self._db_path)
            recommendation = optimizer.choose_model(task_description, budget_constraint)
            optimizer.close()

            return recommendation.to_dict()
        except Exception as e:
            logger.error(f"Error choosing model: {e}")
            return {"recommended_model": "sonnet", "confidence": 0.5}

    def get_cost_summary(self, session_id: str | None = None) -> dict[str, Any]:
        """
        Get cost summary for a session.

        Args:
            session_id: Session to summarize (current if not specified)

        Returns:
            Cost breakdown by tool

        Example:
            >>> summary = sdk.strategic.get_cost_summary()
            >>> print(f"Total tokens: {summary['total_tokens']}")
        """
        try:
            from htmlgraph.analytics.strategic import CostOptimizer

            optimizer = CostOptimizer(self._db_path)
            session = session_id or self._sdk._parent_session or "cli-session"
            summary = optimizer.get_cost_summary(session)
            optimizer.close()

            return summary
        except Exception as e:
            logger.error(f"Error getting cost summary: {e}")
            return {"total_tokens": 0, "breakdown": []}

    # ===== Task Decomposition =====

    def suggest_task_decomposition(
        self,
        task_description: str,
        max_subtasks: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Suggest task decomposition based on learned patterns.

        Uses pattern detection and heuristics to break down complex tasks.

        Args:
            task_description: Task to decompose
            max_subtasks: Maximum number of subtasks

        Returns:
            List of suggested subtasks with agent recommendations

        Example:
            >>> subtasks = sdk.strategic.suggest_task_decomposition(
            ...     "Implement OAuth2 authentication"
            ... )
            >>> for task in subtasks:
            ...     print(f"{task['task']} -> {task['agent']}")
        """
        try:
            # Use orchestrator's decomposition method
            orchestrator = self._sdk.orchestrator
            result = orchestrator.suggest_task_decomposition(
                task_description, max_subtasks
            )
            return list(result) if result else []
        except Exception as e:
            logger.error(f"Error suggesting task decomposition: {e}")
            return []

    def create_task_plan(
        self,
        task_description: str,
        include_cost_estimate: bool = True,
    ) -> dict[str, Any]:
        """
        Create a comprehensive task execution plan.

        Combines pattern detection, cost optimization, and model selection.

        Args:
            task_description: Description of the task
            include_cost_estimate: Whether to include cost estimates

        Returns:
            Comprehensive execution plan

        Example:
            >>> plan = sdk.strategic.create_task_plan(
            ...     "Add caching to API endpoints"
            ... )
            >>> print(f"Subtasks: {len(plan['subtasks'])}")
            >>> print(f"Estimated tokens: {plan.get('total_estimated_tokens')}")
        """
        try:
            orchestrator = self._sdk.orchestrator
            result = orchestrator.create_task_suggestion(
                task_description, include_cost_estimate
            )
            return (
                dict(result) if result else {"task": task_description, "subtasks": []}
            )
        except Exception as e:
            logger.error(f"Error creating task plan: {e}")
            return {"task": task_description, "subtasks": []}


class StrategicAnalyticsMixin:
    """
    Mixin that adds strategic analytics capabilities to SDK.

    Provides access to Phase 3 Strategic Analytics via sdk.strategic property.
    """

    _strategic: StrategicAnalyticsInterface | None = None

    @property
    def strategic(self) -> StrategicAnalyticsInterface:
        """
        Access strategic analytics interface.

        Returns:
            StrategicAnalyticsInterface for pattern detection, suggestions, etc.

        Example:
            >>> sdk = SDK(agent="claude")
            >>> patterns = sdk.strategic.detect_patterns()
            >>> suggestions = sdk.strategic.get_suggestions()
        """
        if self._strategic is None:
            # Cast self to SDK for type checking
            from typing import cast

            from htmlgraph.sdk import SDK

            sdk_self = cast(SDK, self)
            self._strategic = StrategicAnalyticsInterface(_sdk=sdk_self)
        return self._strategic
