"""
Pydantic models for CLI input validation.

This module provides type-safe validation for all CLI commands using Pydantic v2.
Models ensure data integrity before being passed to SDK operations.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CLIInputBase(BaseModel):
    """Base class for all CLI input models with common configuration."""

    class Config:
        extra = "forbid"  # No extra fields allowed
        str_strip_whitespace = True


# =============================================================================
# Feature Commands
# =============================================================================


class FeatureCreateInput(CLIInputBase):
    """Input model for 'feature create' command."""

    title: str = Field(..., min_length=1, max_length=200, description="Feature title")
    description: str | None = Field(
        default=None, max_length=1000, description="Feature description"
    )
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Feature priority level"
    )
    steps: int | None = Field(
        default=None, ge=1, le=50, description="Number of implementation steps"
    )
    collection: str = Field(
        default="features", description="Collection name (features, bugs, etc.)"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Ensure description is stripped if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class FeatureStartInput(CLIInputBase):
    """Input model for 'feature start' command."""

    feature_id: str = Field(..., min_length=1, description="Feature ID to start")
    collection: str = Field(default="features", description="Collection name")

    @field_validator("feature_id")
    @classmethod
    def validate_feature_id(cls, v: str) -> str:
        """Ensure feature ID is not empty."""
        if not v.strip():
            raise ValueError("Feature ID cannot be empty")
        return v.strip()


class FeatureCompleteInput(CLIInputBase):
    """Input model for 'feature complete' command."""

    feature_id: str = Field(..., min_length=1, description="Feature ID to complete")
    collection: str = Field(default="features", description="Collection name")

    @field_validator("feature_id")
    @classmethod
    def validate_feature_id(cls, v: str) -> str:
        """Ensure feature ID is not empty."""
        if not v.strip():
            raise ValueError("Feature ID cannot be empty")
        return v.strip()


class FeaturePrimaryInput(CLIInputBase):
    """Input model for 'feature primary' command."""

    feature_id: str = Field(
        ..., min_length=1, description="Feature ID to set as primary"
    )
    collection: str = Field(default="features", description="Collection name")

    @field_validator("feature_id")
    @classmethod
    def validate_feature_id(cls, v: str) -> str:
        """Ensure feature ID is not empty."""
        if not v.strip():
            raise ValueError("Feature ID cannot be empty")
        return v.strip()


class FeatureClaimInput(CLIInputBase):
    """Input model for 'feature claim' command."""

    feature_id: str = Field(..., min_length=1, description="Feature ID to claim")
    collection: str = Field(default="features", description="Collection name")

    @field_validator("feature_id")
    @classmethod
    def validate_feature_id(cls, v: str) -> str:
        """Ensure feature ID is not empty."""
        if not v.strip():
            raise ValueError("Feature ID cannot be empty")
        return v.strip()


class FeatureReleaseInput(CLIInputBase):
    """Input model for 'feature release' command."""

    feature_id: str = Field(..., min_length=1, description="Feature ID to release")
    collection: str = Field(default="features", description="Collection name")

    @field_validator("feature_id")
    @classmethod
    def validate_feature_id(cls, v: str) -> str:
        """Ensure feature ID is not empty."""
        if not v.strip():
            raise ValueError("Feature ID cannot be empty")
        return v.strip()


# =============================================================================
# Session Commands
# =============================================================================


class SessionStartInput(CLIInputBase):
    """Input model for 'session start' command."""

    session_id: str | None = Field(
        default=None, description="Optional custom session ID"
    )
    title: str | None = Field(default=None, max_length=500, description="Session title")
    agent: str | None = Field(default=None, description="Agent name")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str | None) -> str | None:
        """Ensure session ID is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v.strip() if v else None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """Ensure title is stripped if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class SessionEndInput(CLIInputBase):
    """Input model for 'session end' command."""

    session_id: str = Field(..., min_length=1, description="Session ID to end")
    notes: str | None = Field(
        default=None, max_length=2000, description="Handoff notes"
    )
    recommend: str | None = Field(
        default=None, max_length=500, description="Recommended next steps"
    )
    blocker: list[str] | None = Field(default=None, description="List of blockers")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Ensure session ID is not empty."""
        if not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v.strip()

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        """Ensure notes are stripped if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("recommend")
    @classmethod
    def validate_recommend(cls, v: str | None) -> str | None:
        """Ensure recommendation is stripped if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class SessionHandoffInput(CLIInputBase):
    """Input model for 'session handoff' command."""

    session_id: str | None = Field(default=None, description="Session ID for handoff")
    notes: str | None = Field(
        default=None, max_length=2000, description="Handoff notes"
    )
    recommend: str | None = Field(
        default=None, max_length=500, description="Recommended next steps"
    )
    blocker: list[str] | None = Field(default=None, description="List of blockers")
    show: bool = Field(default=False, description="Show current handoff context")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str | None) -> str | None:
        """Ensure session ID is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v.strip() if v else None


class SessionListInput(CLIInputBase):
    """Input model for 'session list' command."""

    status: Literal["active", "ended"] | None = Field(
        default=None, description="Filter by session status"
    )
    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum results to return"
    )
    offset: int = Field(default=0, ge=0, description="Result offset for pagination")


# =============================================================================
# Track/Activity Commands
# =============================================================================


class ActivityTrackInput(CLIInputBase):
    """Input model for 'activity track' command."""

    tool: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tool name (e.g., 'Bash', 'Read')",
    )
    summary: str = Field(
        ..., min_length=1, max_length=500, description="Activity summary"
    )
    files: list[str] | None = Field(
        default=None, description="Files involved in the activity"
    )
    session: str | None = Field(
        default=None, description="Session ID (auto-detected if not provided)"
    )
    failed: bool = Field(default=False, description="Mark as failed")

    @field_validator("tool")
    @classmethod
    def validate_tool(cls, v: str) -> str:
        """Ensure tool name is stripped and valid."""
        if not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip()

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        """Ensure summary is stripped and not empty."""
        if not v.strip():
            raise ValueError("Summary cannot be empty")
        return v.strip()


# =============================================================================
# Spike Commands
# =============================================================================


class SpikeCreateInput(CLIInputBase):
    """Input model for 'spike create' command."""

    title: str = Field(..., min_length=1, max_length=200, description="Spike title")
    findings: str | None = Field(
        default=None, max_length=5000, description="Spike findings"
    )
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Spike priority"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("findings")
    @classmethod
    def validate_findings(cls, v: str | None) -> str | None:
        """Ensure findings are stripped if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


# =============================================================================
# Documentation Commands
# =============================================================================


class DocsGenerateInput(CLIInputBase):
    """Input model for 'docs generate' command."""

    output_dir: str | None = Field(
        default=None, description="Output directory for generated docs"
    )
    format: Literal["markdown", "html"] = Field(
        default="markdown", description="Output format"
    )
    include_api: bool = Field(default=True, description="Include API documentation")
    include_examples: bool = Field(default=True, description="Include usage examples")


# =============================================================================
# Track Planning Commands (NEW)
# =============================================================================


class TrackCreateInput(CLIInputBase):
    """Input model for 'track create' command."""

    title: str = Field(..., min_length=1, max_length=200, description="Track title")
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Track priority"
    )
    description: str | None = Field(
        default=None, max_length=1000, description="Track description"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Ensure description is stripped if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class TrackSpecInput(CLIInputBase):
    """Input model for 'track spec' command."""

    track_id: str = Field(..., min_length=1, description="Track ID")
    title: str = Field(..., min_length=1, max_length=200, description="Spec title")
    content: str | None = Field(
        default=None, max_length=5000, description="Spec content"
    )

    @field_validator("track_id")
    @classmethod
    def validate_track_id(cls, v: str) -> str:
        """Ensure track ID is not empty."""
        if not v.strip():
            raise ValueError("Track ID cannot be empty")
        return v.strip()

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class TrackPlanInput(CLIInputBase):
    """Input model for 'track plan' command."""

    track_id: str = Field(..., min_length=1, description="Track ID")
    title: str = Field(..., min_length=1, max_length=200, description="Plan title")
    content: str | None = Field(
        default=None, max_length=5000, description="Plan content"
    )

    @field_validator("track_id")
    @classmethod
    def validate_track_id(cls, v: str) -> str:
        """Ensure track ID is not empty."""
        if not v.strip():
            raise ValueError("Track ID cannot be empty")
        return v.strip()

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class TrackDeleteInput(CLIInputBase):
    """Input model for 'track delete' command."""

    track_id: str = Field(..., min_length=1, description="Track ID to delete")
    force: bool = Field(
        default=False, description="Force deletion without confirmation"
    )

    @field_validator("track_id")
    @classmethod
    def validate_track_id(cls, v: str) -> str:
        """Ensure track ID is not empty."""
        if not v.strip():
            raise ValueError("Track ID cannot be empty")
        return v.strip()


# =============================================================================
# Archive Commands
# =============================================================================


class ArchiveCreateInput(CLIInputBase):
    """Input model for 'archive create' command."""

    title: str = Field(..., min_length=1, max_length=200, description="Archive title")
    items: list[str] | None = Field(default=None, description="Items to archive")
    description: str | None = Field(
        default=None, max_length=1000, description="Archive description"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Ensure description is stripped if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v
