"""
Integration tests for Pydantic CLI input models.

Tests validate that Pydantic models correctly validate CLI arguments
with proper error handling and type coercion.
"""

import pytest
from htmlgraph.pydantic_models import (
    ActivityTrackInput,
    ArchiveCreateInput,
    FeatureCreateInput,
    FeatureStartInput,
    SessionEndInput,
    SessionListInput,
    SessionStartInput,
    SpikeCreateInput,
    TrackCreateInput,
    TrackSpecInput,
)
from pydantic import ValidationError


class TestFeatureCreateInput:
    """Test FeatureCreateInput model validation."""

    def test_valid_minimal_input(self):
        """Test with minimal required fields."""
        input_data = FeatureCreateInput(title="My Feature")
        assert input_data.title == "My Feature"
        assert input_data.priority == "medium"
        assert input_data.description is None

    def test_valid_full_input(self):
        """Test with all fields provided."""
        input_data = FeatureCreateInput(
            title="My Feature",
            description="A detailed description",
            priority="high",
            steps=5,
            collection="features",
        )
        assert input_data.title == "My Feature"
        assert input_data.description == "A detailed description"
        assert input_data.priority == "high"
        assert input_data.steps == 5

    def test_title_stripped_whitespace(self):
        """Test that title whitespace is stripped."""
        input_data = FeatureCreateInput(title="  My Feature  ")
        assert input_data.title == "My Feature"

    def test_title_empty_raises_error(self):
        """Test that empty title raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FeatureCreateInput(title="")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_title_whitespace_only_raises_error(self):
        """Test that whitespace-only title raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FeatureCreateInput(title="   ")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_title_too_long_raises_error(self):
        """Test that title exceeding max length raises ValidationError."""
        long_title = "x" * 201
        with pytest.raises(ValidationError) as exc_info:
            FeatureCreateInput(title=long_title)
        assert "at most 200 characters" in str(exc_info.value)

    def test_invalid_priority_raises_error(self):
        """Test that invalid priority raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FeatureCreateInput(title="Feature", priority="critical")
        assert "priority" in str(exc_info.value).lower()

    def test_description_stripped_whitespace(self):
        """Test that description whitespace is stripped."""
        input_data = FeatureCreateInput(
            title="Feature", description="  A description  "
        )
        assert input_data.description == "A description"

    def test_description_whitespace_only_becomes_none(self):
        """Test that whitespace-only description becomes None."""
        input_data = FeatureCreateInput(title="Feature", description="   ")
        assert input_data.description is None

    def test_steps_validation(self):
        """Test steps field validation."""
        input_data = FeatureCreateInput(title="Feature", steps=10)
        assert input_data.steps == 10

        with pytest.raises(ValidationError):
            FeatureCreateInput(title="Feature", steps=0)

        with pytest.raises(ValidationError):
            FeatureCreateInput(title="Feature", steps=51)


class TestFeatureStartInput:
    """Test FeatureStartInput model validation."""

    def test_valid_input(self):
        """Test with valid feature ID."""
        input_data = FeatureStartInput(feature_id="feat-123")
        assert input_data.feature_id == "feat-123"
        assert input_data.collection == "features"

    def test_feature_id_stripped(self):
        """Test that feature ID is stripped."""
        input_data = FeatureStartInput(feature_id="  feat-123  ")
        assert input_data.feature_id == "feat-123"

    def test_empty_feature_id_raises_error(self):
        """Test that empty feature ID raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureStartInput(feature_id="")


class TestSessionStartInput:
    """Test SessionStartInput model validation."""

    def test_valid_minimal_input(self):
        """Test with minimal required fields."""
        input_data = SessionStartInput()
        assert input_data.session_id is None
        assert input_data.title is None
        assert input_data.agent is None

    def test_valid_full_input(self):
        """Test with all fields provided."""
        input_data = SessionStartInput(
            session_id="sess-123", title="My Session", agent="claude"
        )
        assert input_data.session_id == "sess-123"
        assert input_data.title == "My Session"
        assert input_data.agent == "claude"

    def test_session_id_stripped(self):
        """Test that session ID is stripped."""
        input_data = SessionStartInput(session_id="  sess-123  ")
        assert input_data.session_id == "sess-123"

    def test_empty_session_id_raises_error(self):
        """Test that empty session ID raises ValidationError."""
        with pytest.raises(ValidationError):
            SessionStartInput(session_id="")

    def test_title_stripped(self):
        """Test that title is stripped."""
        input_data = SessionStartInput(title="  My Session  ")
        assert input_data.title == "My Session"

    def test_title_whitespace_only_becomes_none(self):
        """Test that whitespace-only title becomes None."""
        input_data = SessionStartInput(title="   ")
        assert input_data.title is None


class TestSessionEndInput:
    """Test SessionEndInput model validation."""

    def test_valid_input(self):
        """Test with valid session ID."""
        input_data = SessionEndInput(
            session_id="sess-123",
            notes="Work completed",
            recommend="Review PR",
        )
        assert input_data.session_id == "sess-123"
        assert input_data.notes == "Work completed"
        assert input_data.recommend == "Review PR"

    def test_empty_session_id_raises_error(self):
        """Test that empty session ID raises ValidationError."""
        with pytest.raises(ValidationError):
            SessionEndInput(session_id="")

    def test_optional_fields(self):
        """Test that optional fields can be omitted."""
        input_data = SessionEndInput(session_id="sess-123")
        assert input_data.notes is None
        assert input_data.recommend is None
        assert input_data.blocker is None

    def test_blocker_list(self):
        """Test blocker field as list."""
        input_data = SessionEndInput(
            session_id="sess-123", blocker=["missing dependency", "network issue"]
        )
        assert input_data.blocker == ["missing dependency", "network issue"]


class TestActivityTrackInput:
    """Test ActivityTrackInput model validation."""

    def test_valid_input(self):
        """Test with valid tool and summary."""
        input_data = ActivityTrackInput(tool="Bash", summary="Ran tests")
        assert input_data.tool == "Bash"
        assert input_data.summary == "Ran tests"
        assert input_data.failed is False

    def test_tool_stripped(self):
        """Test that tool is stripped."""
        input_data = ActivityTrackInput(tool="  Bash  ", summary="Tests")
        assert input_data.tool == "Bash"

    def test_empty_tool_raises_error(self):
        """Test that empty tool raises ValidationError."""
        with pytest.raises(ValidationError):
            ActivityTrackInput(tool="", summary="Tests")

    def test_empty_summary_raises_error(self):
        """Test that empty summary raises ValidationError."""
        with pytest.raises(ValidationError):
            ActivityTrackInput(tool="Bash", summary="")

    def test_with_files(self):
        """Test with file list."""
        input_data = ActivityTrackInput(
            tool="Read",
            summary="Reviewed code",
            files=["/path/to/file1", "/path/to/file2"],
        )
        assert input_data.files == ["/path/to/file1", "/path/to/file2"]

    def test_failed_flag(self):
        """Test failed flag."""
        input_data = ActivityTrackInput(
            tool="Bash", summary="Build failed", failed=True
        )
        assert input_data.failed is True


class TestSpikeCreateInput:
    """Test SpikeCreateInput model validation."""

    def test_valid_input(self):
        """Test with valid title."""
        input_data = SpikeCreateInput(title="Investigation: Performance")
        assert input_data.title == "Investigation: Performance"
        assert input_data.priority == "medium"

    def test_valid_with_findings(self):
        """Test with findings."""
        input_data = SpikeCreateInput(
            title="Investigation",
            findings="Found bottleneck in rendering",
            priority="high",
        )
        assert input_data.title == "Investigation"
        assert input_data.findings == "Found bottleneck in rendering"
        assert input_data.priority == "high"

    def test_title_empty_raises_error(self):
        """Test that empty title raises ValidationError."""
        with pytest.raises(ValidationError):
            SpikeCreateInput(title="")


class TestTrackCreateInput:
    """Test TrackCreateInput model validation."""

    def test_valid_input(self):
        """Test with valid title."""
        input_data = TrackCreateInput(title="Planning Workflow")
        assert input_data.title == "Planning Workflow"
        assert input_data.priority == "medium"

    def test_with_description(self):
        """Test with description."""
        input_data = TrackCreateInput(
            title="Planning",
            description="Multi-feature planning workflow",
            priority="high",
        )
        assert input_data.title == "Planning"
        assert input_data.description == "Multi-feature planning workflow"


class TestTrackSpecInput:
    """Test TrackSpecInput model validation."""

    def test_valid_input(self):
        """Test with valid track ID and title."""
        input_data = TrackSpecInput(track_id="track-123", title="API Specification")
        assert input_data.track_id == "track-123"
        assert input_data.title == "API Specification"

    def test_with_content(self):
        """Test with content."""
        input_data = TrackSpecInput(
            track_id="track-123", title="Spec", content="Detailed specification..."
        )
        assert input_data.content == "Detailed specification..."


class TestSessionListInput:
    """Test SessionListInput model validation."""

    def test_valid_default_input(self):
        """Test with default values."""
        input_data = SessionListInput()
        assert input_data.status is None
        assert input_data.limit == 20
        assert input_data.offset == 0

    def test_with_status_filter(self):
        """Test with status filter."""
        input_data = SessionListInput(status="active")
        assert input_data.status == "active"

    def test_limit_validation(self):
        """Test limit field validation."""
        input_data = SessionListInput(limit=50)
        assert input_data.limit == 50

        with pytest.raises(ValidationError):
            SessionListInput(limit=0)

        with pytest.raises(ValidationError):
            SessionListInput(limit=101)

    def test_offset_validation(self):
        """Test offset field validation."""
        input_data = SessionListInput(offset=10)
        assert input_data.offset == 10

        with pytest.raises(ValidationError):
            SessionListInput(offset=-1)


class TestArchiveCreateInput:
    """Test ArchiveCreateInput model validation."""

    def test_valid_input(self):
        """Test with valid title."""
        input_data = ArchiveCreateInput(title="Q4 Archive")
        assert input_data.title == "Q4 Archive"

    def test_with_items_and_description(self):
        """Test with items and description."""
        input_data = ArchiveCreateInput(
            title="Archive", items=["item-1", "item-2"], description="Completed items"
        )
        assert input_data.title == "Archive"
        assert input_data.items == ["item-1", "item-2"]
        assert input_data.description == "Completed items"


class TestExtraFieldsValidation:
    """Test that extra fields are rejected."""

    def test_extra_fields_raise_error(self):
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FeatureCreateInput(title="Feature", extra_field="not allowed")
        assert "extra_field" in str(exc_info.value)
