"""Intelligent model selection for task routing.

import logging

logger = logging.getLogger(__name__)

This module provides functionality to select the best AI model for a given task
based on task type, complexity, and budget constraints.

Model Selection Strategy:
- Exploration: Use Gemini (free tier) for cost-effective research
- Debugging: Use Claude Sonnet (high context) for complex error analysis
- Implementation: Use Codex (programming specialized) for code generation
- Quality: Use Claude Haiku (fast) for linting and formatting

Fallback Chain:
Each model has fallback options if primary model is unavailable:
- Gemini → Claude Haiku → Claude Sonnet
- Codex → Claude Sonnet
- Copilot → Claude Sonnet
"""

from enum import Enum


class TaskType(str, Enum):
    """Task classification types."""

    EXPLORATION = "exploration"
    DEBUGGING = "debugging"
    IMPLEMENTATION = "implementation"
    QUALITY = "quality"
    GENERAL = "general"


class ComplexityLevel(str, Enum):
    """Complexity assessment levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BudgetMode(str, Enum):
    """Budget constraints."""

    FREE = "free"  # Use only free models
    BALANCED = "balanced"  # Balance cost and quality
    QUALITY = "quality"  # Prioritize best model


class ModelSelection:
    """Intelligent model selection engine."""

    # Decision matrix: (task_type, complexity, budget) -> model
    DECISION_MATRIX = {
        # Exploration tasks - prioritize free/cheap options
        (TaskType.EXPLORATION, ComplexityLevel.LOW, BudgetMode.FREE): "gemini",
        (TaskType.EXPLORATION, ComplexityLevel.MEDIUM, BudgetMode.FREE): "gemini",
        (TaskType.EXPLORATION, ComplexityLevel.HIGH, BudgetMode.FREE): "gemini",
        (TaskType.EXPLORATION, ComplexityLevel.LOW, BudgetMode.BALANCED): "gemini",
        (TaskType.EXPLORATION, ComplexityLevel.MEDIUM, BudgetMode.BALANCED): "gemini",
        (
            TaskType.EXPLORATION,
            ComplexityLevel.HIGH,
            BudgetMode.BALANCED,
        ): "claude-sonnet",
        (
            TaskType.EXPLORATION,
            ComplexityLevel.LOW,
            BudgetMode.QUALITY,
        ): "claude-sonnet",
        (
            TaskType.EXPLORATION,
            ComplexityLevel.MEDIUM,
            BudgetMode.QUALITY,
        ): "claude-sonnet",
        (TaskType.EXPLORATION, ComplexityLevel.HIGH, BudgetMode.QUALITY): "claude-opus",
        # Debugging tasks - need strong reasoning
        (TaskType.DEBUGGING, ComplexityLevel.LOW, BudgetMode.FREE): "claude-haiku",
        (TaskType.DEBUGGING, ComplexityLevel.MEDIUM, BudgetMode.FREE): "claude-haiku",
        (TaskType.DEBUGGING, ComplexityLevel.HIGH, BudgetMode.FREE): "claude-haiku",
        (TaskType.DEBUGGING, ComplexityLevel.LOW, BudgetMode.BALANCED): "claude-sonnet",
        (
            TaskType.DEBUGGING,
            ComplexityLevel.MEDIUM,
            BudgetMode.BALANCED,
        ): "claude-sonnet",
        (TaskType.DEBUGGING, ComplexityLevel.HIGH, BudgetMode.BALANCED): "claude-opus",
        (TaskType.DEBUGGING, ComplexityLevel.LOW, BudgetMode.QUALITY): "claude-opus",
        (TaskType.DEBUGGING, ComplexityLevel.MEDIUM, BudgetMode.QUALITY): "claude-opus",
        (TaskType.DEBUGGING, ComplexityLevel.HIGH, BudgetMode.QUALITY): "claude-opus",
        # Implementation tasks - balance speed and quality
        (TaskType.IMPLEMENTATION, ComplexityLevel.LOW, BudgetMode.FREE): "claude-haiku",
        (
            TaskType.IMPLEMENTATION,
            ComplexityLevel.MEDIUM,
            BudgetMode.FREE,
        ): "claude-haiku",
        (
            TaskType.IMPLEMENTATION,
            ComplexityLevel.HIGH,
            BudgetMode.FREE,
        ): "claude-haiku",
        (TaskType.IMPLEMENTATION, ComplexityLevel.LOW, BudgetMode.BALANCED): "codex",
        (TaskType.IMPLEMENTATION, ComplexityLevel.MEDIUM, BudgetMode.BALANCED): "codex",
        (
            TaskType.IMPLEMENTATION,
            ComplexityLevel.HIGH,
            BudgetMode.BALANCED,
        ): "claude-opus",
        (
            TaskType.IMPLEMENTATION,
            ComplexityLevel.LOW,
            BudgetMode.QUALITY,
        ): "claude-opus",
        (
            TaskType.IMPLEMENTATION,
            ComplexityLevel.MEDIUM,
            BudgetMode.QUALITY,
        ): "claude-opus",
        (
            TaskType.IMPLEMENTATION,
            ComplexityLevel.HIGH,
            BudgetMode.QUALITY,
        ): "claude-opus",
        # Quality tasks - fast and cheap
        (TaskType.QUALITY, ComplexityLevel.LOW, BudgetMode.FREE): "claude-haiku",
        (TaskType.QUALITY, ComplexityLevel.MEDIUM, BudgetMode.FREE): "claude-haiku",
        (TaskType.QUALITY, ComplexityLevel.HIGH, BudgetMode.FREE): "claude-haiku",
        (TaskType.QUALITY, ComplexityLevel.LOW, BudgetMode.BALANCED): "claude-haiku",
        (
            TaskType.QUALITY,
            ComplexityLevel.MEDIUM,
            BudgetMode.BALANCED,
        ): "claude-sonnet",
        (TaskType.QUALITY, ComplexityLevel.HIGH, BudgetMode.BALANCED): "claude-sonnet",
        (TaskType.QUALITY, ComplexityLevel.LOW, BudgetMode.QUALITY): "claude-sonnet",
        (TaskType.QUALITY, ComplexityLevel.MEDIUM, BudgetMode.QUALITY): "claude-opus",
        (TaskType.QUALITY, ComplexityLevel.HIGH, BudgetMode.QUALITY): "claude-opus",
        # General tasks - safe defaults
        (TaskType.GENERAL, ComplexityLevel.LOW, BudgetMode.FREE): "claude-haiku",
        (TaskType.GENERAL, ComplexityLevel.MEDIUM, BudgetMode.FREE): "claude-haiku",
        (TaskType.GENERAL, ComplexityLevel.HIGH, BudgetMode.FREE): "claude-haiku",
        (TaskType.GENERAL, ComplexityLevel.LOW, BudgetMode.BALANCED): "claude-sonnet",
        (
            TaskType.GENERAL,
            ComplexityLevel.MEDIUM,
            BudgetMode.BALANCED,
        ): "claude-sonnet",
        (TaskType.GENERAL, ComplexityLevel.HIGH, BudgetMode.BALANCED): "claude-opus",
        (TaskType.GENERAL, ComplexityLevel.LOW, BudgetMode.QUALITY): "claude-opus",
        (TaskType.GENERAL, ComplexityLevel.MEDIUM, BudgetMode.QUALITY): "claude-opus",
        (TaskType.GENERAL, ComplexityLevel.HIGH, BudgetMode.QUALITY): "claude-opus",
    }

    # Fallback chains for when primary model is unavailable
    FALLBACK_CHAINS = {
        "gemini": ["claude-haiku", "claude-sonnet", "claude-opus"],
        "codex": ["claude-sonnet", "claude-opus"],
        "copilot": ["claude-sonnet", "claude-opus"],
        "claude-haiku": ["claude-sonnet", "claude-opus"],
        "claude-sonnet": ["claude-opus", "claude-haiku"],
        "claude-opus": ["claude-sonnet", "claude-haiku"],
    }

    @staticmethod
    def select_model(
        task_type: str | TaskType,
        complexity: str | ComplexityLevel = "medium",
        budget: str | BudgetMode = "balanced",
    ) -> str:
        """
        Select best model for the given task parameters.

        Args:
            task_type: Type of task (exploration, debugging, implementation, quality, general)
            complexity: Task complexity level (low, medium, high). Default: medium
            budget: Budget mode (free, balanced, quality). Default: balanced

        Returns:
            Model name (e.g., "claude-sonnet", "gemini")

        Example:
            >>> model = ModelSelection.select_model("implementation", "high", "balanced")
            >>> logger.info("%s", model)
            'claude-opus'
        """
        # Normalize inputs
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                task_type = TaskType.GENERAL

        if isinstance(complexity, str):
            try:
                complexity = ComplexityLevel(complexity)
            except ValueError:
                complexity = ComplexityLevel.MEDIUM

        if isinstance(budget, str):
            try:
                budget = BudgetMode(budget)
            except ValueError:
                budget = BudgetMode.BALANCED

        # Look up in decision matrix
        key = (task_type, complexity, budget)
        return ModelSelection.DECISION_MATRIX.get(key, "claude-sonnet")

    @staticmethod
    def get_fallback_chain(primary_model: str) -> list[str]:
        """
        Get fallback models if primary model is unavailable.

        Args:
            primary_model: Primary model name

        Returns:
            List of fallback models in order of preference

        Example:
            >>> fallbacks = ModelSelection.get_fallback_chain("gemini")
            >>> logger.info("%s", fallbacks)
            ['claude-haiku', 'claude-sonnet', 'claude-opus']
        """
        return ModelSelection.FALLBACK_CHAINS.get(primary_model, ["claude-sonnet"])

    @staticmethod
    def estimate_tokens(
        task_description: str, complexity: str | ComplexityLevel = "medium"
    ) -> int:
        """
        Estimate token usage for a task.

        Args:
            task_description: Description of the task
            complexity: Task complexity level

        Returns:
            Estimated tokens for the task

        Estimation formula:
        - Low complexity: ~500-1000 tokens
        - Medium complexity: ~1000-5000 tokens
        - High complexity: ~5000-20000 tokens
        """
        if isinstance(complexity, str):
            try:
                complexity = ComplexityLevel(complexity)
            except ValueError:
                complexity = ComplexityLevel.MEDIUM

        # Base estimate on description length
        description_tokens = len(task_description.split()) * 1.3  # ~1.3 tokens per word

        # Add complexity multiplier
        multipliers = {
            ComplexityLevel.LOW: 1.0,
            ComplexityLevel.MEDIUM: 2.0,
            ComplexityLevel.HIGH: 5.0,
        }

        multiplier = multipliers.get(complexity, 2.0)
        return int(description_tokens * multiplier)

    @staticmethod
    def is_model_available(model: str) -> bool:
        """
        Check if a model is available (basic check).

        Args:
            model: Model name to check

        Returns:
            True if model is known, False otherwise

        Note:
            This is a simple availability check. For actual availability,
            you should check Claude CLI, Gemini CLI, etc.
        """
        available_models = {
            "gemini",
            "codex",
            "copilot",
            "claude-haiku",
            "claude-sonnet",
            "claude-opus",
        }
        return model in available_models


def select_model(
    task_type: str = "general",
    complexity: str = "medium",
    budget: str = "balanced",
) -> str:
    """
    Convenience function for model selection.

    Args:
        task_type: Type of task. Default: general
        complexity: Complexity level. Default: medium
        budget: Budget mode. Default: balanced

    Returns:
        Recommended model name

    Example:
        >>> model = select_model("implementation", "high")
        >>> logger.info("%s", model)
    """
    return ModelSelection.select_model(task_type, complexity, budget)


def get_fallback_chain(model: str) -> list[str]:
    """
    Convenience function for getting fallback models.

    Args:
        model: Primary model name

    Returns:
        List of fallback models
    """
    return ModelSelection.get_fallback_chain(model)
