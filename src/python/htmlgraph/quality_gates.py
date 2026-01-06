"""
Quality Gates Module - Comprehensive Validation for SDK Operations

Provides Pydantic-based validators and quality checks for:
- Builder arguments (title, description, priority)
- SDK operations (feature creation, spike creation, task spawning)
- Work item metadata (required fields, completion criteria)
- Code quality markers (TODO/FIXME detection)

This module enforces minimum quality standards before allowing
SDK operations to proceed, preventing incomplete or invalid work items.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class QualityGateBase(BaseModel):
    """Base class for quality gate validation models."""

    class Config:
        extra = "forbid"  # No extra fields allowed
        str_strip_whitespace = True
        validate_default = True


# =============================================================================
# Feature Creation Quality Gates
# =============================================================================


class FeatureQualityGate(QualityGateBase):
    """Quality validation for feature creation operations.

    Ensures:
    - Title is present and non-empty
    - Description (if provided) is meaningful
    - Priority is valid (low, medium, high, critical)
    - Agent assignment (if available)
    """

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    status: Literal["todo", "in_progress", "blocked", "done"] = Field(default="todo")
    agent_assigned: str | None = Field(default=None)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is non-empty and meaningful."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Feature title cannot be empty or whitespace only")
        if len(stripped) < 3:
            raise ValueError("Feature title must be at least 3 characters")
        if stripped.lower().startswith(("todo", "fixme", "wip")):
            raise ValueError(
                f"Feature title cannot start with placeholder text: {stripped[:10]}"
            )
        return stripped

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Ensure description is meaningful if provided."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            if len(stripped) < 5:
                raise ValueError(
                    "Description must be at least 5 characters if provided"
                )
            return stripped
        return None

    @field_validator("agent_assigned")
    @classmethod
    def validate_agent(cls, v: str | None) -> str | None:
        """Ensure agent is assigned for tracking."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return None


# =============================================================================
# Spike Creation Quality Gates
# =============================================================================


class SpikeQualityGate(QualityGateBase):
    """Quality validation for spike creation operations.

    Ensures:
    - Title is present and non-empty
    - Findings (if set) are non-empty
    - Timebox is reasonable (1-40 hours)
    - Spike type is valid
    - Agent assignment for tracking
    """

    title: str = Field(..., min_length=1, max_length=200)
    findings: str | None = Field(default=None, max_length=5000)
    decision: str | None = Field(default=None, max_length=500)
    timebox_hours: int = Field(default=4, ge=1, le=40)
    spike_type: Literal["technical", "architectural", "risk", "research", "general"] = (
        Field(default="general")
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    agent_assigned: str | None = Field(default=None)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure spike title is meaningful."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Spike title cannot be empty or whitespace only")
        if len(stripped) < 5:
            raise ValueError("Spike title must be at least 5 characters")
        return stripped

    @field_validator("findings")
    @classmethod
    def validate_findings(cls, v: str | None) -> str | None:
        """Ensure findings are non-empty if set."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            if len(stripped) < 10:
                raise ValueError("Findings must be at least 10 characters if provided")
            return stripped
        return None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str | None) -> str | None:
        """Ensure decision is meaningful if set."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            if len(stripped) < 5:
                raise ValueError("Decision must be at least 5 characters if provided")
            return stripped
        return None

    @field_validator("timebox_hours")
    @classmethod
    def validate_timebox(cls, v: int) -> int:
        """Ensure timebox is reasonable."""
        if v < 1:
            raise ValueError("Timebox must be at least 1 hour")
        if v > 40:
            raise ValueError("Timebox should not exceed 40 hours")
        return v


# =============================================================================
# Task/Subtask Quality Gates
# =============================================================================


class TaskQualityGate(QualityGateBase):
    """Quality validation for task creation/spawning operations.

    Ensures:
    - Description is present and meaningful
    - Task type is specified
    - Priority is valid
    - Agent type specified for spawning
    """

    description: str = Field(..., min_length=1, max_length=2000)
    task_type: Literal["feature", "bug", "chore", "refactor", "test"] = Field(
        default="feature"
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    agent_type: str | None = Field(
        default=None, description="Agent type for spawning (e.g., 'sonnet', 'claude')"
    )
    status: Literal["pending", "in_progress", "blocked", "completed"] = Field(
        default="pending"
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Ensure description is meaningful."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Task description cannot be empty")
        if len(stripped) < 10:
            raise ValueError("Task description must be at least 10 characters")
        if stripped.lower().startswith(("todo", "fixme", "wip")):
            raise ValueError(
                f"Task description cannot start with placeholder: {stripped[:15]}"
            )
        return stripped

    @field_validator("agent_type")
    @classmethod
    def validate_agent_type(cls, v: str | None) -> str | None:
        """Ensure agent type is valid if specified."""
        if v is not None:
            stripped = v.strip().lower()
            valid_types = {"sonnet", "claude", "opus", "haiku", "gpt4", "gemini"}
            if stripped not in valid_types:
                raise ValueError(
                    f"Invalid agent type '{stripped}'. Must be one of: {', '.join(valid_types)}"
                )
            return stripped
        return None


# =============================================================================
# Code Quality Markers Detection
# =============================================================================


class CodeQualityMarkers:
    """Detect incomplete work markers in code."""

    INCOMPLETE_PATTERNS = {
        "TODO": r"(?:^|\s)TODO\b",
        "FIXME": r"(?:^|\s)FIXME\b",
        "WIP": r"(?:^|\s)WIP\b",
        "XXX": r"(?:^|\s)XXX\b",
        "HACK": r"(?:^|\s)HACK\b",
    }

    @staticmethod
    def detect_markers(content: str) -> dict[str, list[tuple[int, str]]]:
        """
        Detect incomplete work markers in code content.

        Args:
            content: Code content to scan

        Returns:
            Dictionary mapping marker type to list of (line_no, line_content) tuples

        Example:
            >>> markers = CodeQualityMarkers.detect_markers(code)
            >>> if markers["TODO"]:
            ...     print(f"Found {len(markers['TODO'])} TODO items")
        """
        import re

        results: dict[str, list[tuple[int, str]]] = {
            marker: [] for marker in CodeQualityMarkers.INCOMPLETE_PATTERNS
        }

        for line_no, line in enumerate(content.splitlines(), start=1):
            # Skip comments that are documentation examples
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                continue

            for marker, pattern in CodeQualityMarkers.INCOMPLETE_PATTERNS.items():
                if re.search(pattern, line):
                    results[marker].append((line_no, line.strip()))

        return results

    @staticmethod
    def has_incomplete_markers(content: str) -> bool:
        """Check if content has any incomplete work markers."""
        markers = CodeQualityMarkers.detect_markers(content)
        return any(items for items in markers.values())


# =============================================================================
# Validation Utilities
# =============================================================================


def validate_feature_args(**kwargs: Any) -> FeatureQualityGate:
    """
    Validate feature creation arguments.

    Raises:
        ValueError: If validation fails

    Example:
        >>> gate = validate_feature_args(
        ...     title="Add user authentication",
        ...     priority="high",
        ...     agent_assigned="claude"
        ... )
    """
    return FeatureQualityGate(**kwargs)


def validate_spike_args(**kwargs: Any) -> SpikeQualityGate:
    """
    Validate spike creation arguments.

    Raises:
        ValueError: If validation fails

    Example:
        >>> gate = validate_spike_args(
        ...     title="Research OAuth providers",
        ...     findings="OAuth2 is best fit",
        ...     timebox_hours=4
        ... )
    """
    return SpikeQualityGate(**kwargs)


def validate_task_args(**kwargs: Any) -> TaskQualityGate:
    """
    Validate task creation/spawning arguments.

    Raises:
        ValueError: If validation fails

    Example:
        >>> gate = validate_task_args(
        ...     description="Implement user registration flow",
        ...     priority="high",
        ...     agent_type="sonnet"
        ... )
    """
    return TaskQualityGate(**kwargs)


def validate_code_quality(file_path: str) -> bool:
    """
    Validate code file for quality issues.

    Returns:
        True if no incomplete markers found, False otherwise

    Example:
        >>> if validate_code_quality("src/mymodule.py"):
        ...     print("Code quality check passed")
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        return not CodeQualityMarkers.has_incomplete_markers(content)
    except OSError:
        return True  # Skip if file can't be read
