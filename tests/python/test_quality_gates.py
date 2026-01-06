"""
Test suite for quality gates validation module.

Tests Pydantic validators for:
- Feature creation validation
- Spike creation validation
- Task creation validation
- Code quality marker detection
"""

import pytest
from htmlgraph.quality_gates import (
    CodeQualityMarkers,
    FeatureQualityGate,
    SpikeQualityGate,
    TaskQualityGate,
    validate_code_quality,
    validate_feature_args,
    validate_spike_args,
    validate_task_args,
)
from pydantic import ValidationError

# =============================================================================
# Feature Quality Gate Tests
# =============================================================================


class TestFeatureQualityGate:
    """Test feature creation validation."""

    def test_valid_feature_minimal(self) -> None:
        """Test creating feature with minimal valid args."""
        gate = FeatureQualityGate(title="Add user authentication")
        assert gate.title == "Add user authentication"
        assert gate.priority == "medium"
        assert gate.status == "todo"

    def test_valid_feature_full(self) -> None:
        """Test creating feature with all args."""
        gate = FeatureQualityGate(
            title="Add user authentication",
            description="Implement OAuth2 flow",
            priority="high",
            status="in_progress",
            agent_assigned="claude",
        )
        assert gate.title == "Add user authentication"
        assert gate.description == "Implement OAuth2 flow"
        assert gate.priority == "high"
        assert gate.agent_assigned == "claude"

    def test_feature_title_required(self) -> None:
        """Test that feature title is required."""
        with pytest.raises(ValidationError) as exc_info:
            FeatureQualityGate()  # type: ignore
        assert "title" in str(exc_info.value).lower()

    def test_feature_title_empty(self) -> None:
        """Test that empty title fails validation."""
        with pytest.raises(ValidationError):
            FeatureQualityGate(title="")

    def test_feature_title_whitespace_only(self) -> None:
        """Test that whitespace-only title fails validation."""
        with pytest.raises(ValidationError):
            FeatureQualityGate(title="   ")

    def test_feature_title_too_short(self) -> None:
        """Test that title less than 3 chars fails."""
        with pytest.raises(ValidationError) as exc_info:
            FeatureQualityGate(title="ab")
        assert "3 characters" in str(exc_info.value).lower()

    def test_feature_title_placeholder_text(self) -> None:
        """Test that placeholder titles are rejected."""
        for placeholder in ["TODO fix this", "FIXME later", "WIP feature"]:
            with pytest.raises(ValidationError) as exc_info:
                FeatureQualityGate(title=placeholder)
            assert "placeholder" in str(exc_info.value).lower()

    def test_feature_description_too_short(self) -> None:
        """Test that description must be at least 5 chars."""
        with pytest.raises(ValidationError) as exc_info:
            FeatureQualityGate(title="Valid Title", description="abc")
        assert "5 characters" in str(exc_info.value).lower()

    def test_feature_description_empty_becomes_none(self) -> None:
        """Test that empty description becomes None."""
        gate = FeatureQualityGate(title="Valid Title", description="   ")
        assert gate.description is None

    def test_feature_invalid_priority(self) -> None:
        """Test that invalid priority fails."""
        with pytest.raises(ValidationError) as exc_info:
            FeatureQualityGate(title="Valid Title", priority="urgent")  # type: ignore
        assert "priority" in str(exc_info.value).lower()

    def test_feature_valid_priorities(self) -> None:
        """Test all valid priority values."""
        for priority in ["low", "medium", "high", "critical"]:
            gate = FeatureQualityGate(title="Valid Title", priority=priority)  # type: ignore
            assert gate.priority == priority

    def test_feature_title_whitespace_stripped(self) -> None:
        """Test that title whitespace is stripped."""
        gate = FeatureQualityGate(title="   Add auth   ")
        assert gate.title == "Add auth"

    def test_validate_feature_args_helper(self) -> None:
        """Test validate_feature_args helper function."""
        gate = validate_feature_args(
            title="Add user auth",
            description="Implement OAuth2",
            priority="high",
        )
        assert gate.title == "Add user auth"
        assert gate.priority == "high"


# =============================================================================
# Spike Quality Gate Tests
# =============================================================================


class TestSpikeQualityGate:
    """Test spike creation validation."""

    def test_valid_spike_minimal(self) -> None:
        """Test creating spike with minimal valid args."""
        gate = SpikeQualityGate(title="Research Auth Options")
        assert gate.title == "Research Auth Options"
        assert gate.timebox_hours == 4
        assert gate.spike_type == "general"

    def test_valid_spike_full(self) -> None:
        """Test creating spike with all args."""
        gate = SpikeQualityGate(
            title="Research Auth Options",
            findings="OAuth2 is best fit",
            decision="Use Auth0",
            timebox_hours=6,
            spike_type="research",
            priority="high",
            agent_assigned="claude",
        )
        assert gate.title == "Research Auth Options"
        assert gate.findings == "OAuth2 is best fit"
        assert gate.decision == "Use Auth0"
        assert gate.timebox_hours == 6
        assert gate.priority == "high"

    def test_spike_title_required(self) -> None:
        """Test that spike title is required."""
        with pytest.raises(ValidationError):
            SpikeQualityGate()  # type: ignore

    def test_spike_title_too_short(self) -> None:
        """Test that spike title must be at least 5 chars."""
        with pytest.raises(ValidationError) as exc_info:
            SpikeQualityGate(title="auth")
        assert "5 characters" in str(exc_info.value).lower()

    def test_spike_findings_too_short(self) -> None:
        """Test that findings must be at least 10 chars."""
        with pytest.raises(ValidationError) as exc_info:
            SpikeQualityGate(title="Research Auth Options", findings="short")
        assert "10 characters" in str(exc_info.value).lower()

    def test_spike_findings_empty_becomes_none(self) -> None:
        """Test that empty findings becomes None."""
        gate = SpikeQualityGate(title="Research Auth Options", findings="   ")
        assert gate.findings is None

    def test_spike_decision_too_short(self) -> None:
        """Test that decision must be at least 5 chars if provided."""
        with pytest.raises(ValidationError) as exc_info:
            SpikeQualityGate(title="Research Auth Options", decision="yes")
        assert "5 characters" in str(exc_info.value).lower()

    def test_spike_timebox_minimum(self) -> None:
        """Test that timebox must be at least 1 hour."""
        with pytest.raises(ValidationError):
            SpikeQualityGate(title="Research Auth Options", timebox_hours=0)

    def test_spike_timebox_maximum(self) -> None:
        """Test that timebox should not exceed 40 hours."""
        with pytest.raises(ValidationError):
            SpikeQualityGate(title="Research Auth Options", timebox_hours=50)

    def test_spike_valid_timebox_values(self) -> None:
        """Test valid timebox values."""
        for hours in [1, 2, 4, 8, 16, 40]:
            gate = SpikeQualityGate(title="Research Auth Options", timebox_hours=hours)
            assert gate.timebox_hours == hours

    def test_spike_valid_types(self) -> None:
        """Test all valid spike types."""
        for spike_type in ["technical", "architectural", "risk", "research", "general"]:
            gate = SpikeQualityGate(
                title="Research Auth Options",
                spike_type=spike_type,  # type: ignore
            )
            assert gate.spike_type == spike_type

    def test_validate_spike_args_helper(self) -> None:
        """Test validate_spike_args helper function."""
        gate = validate_spike_args(
            title="Research Auth Options",
            findings="OAuth2 is best fit",
            timebox_hours=4,
        )
        assert gate.findings == "OAuth2 is best fit"


# =============================================================================
# Task Quality Gate Tests
# =============================================================================


class TestTaskQualityGate:
    """Test task creation validation."""

    def test_valid_task_minimal(self) -> None:
        """Test creating task with minimal valid args."""
        gate = TaskQualityGate(description="Implement user registration")
        assert gate.description == "Implement user registration"
        assert gate.status == "pending"
        assert gate.priority == "medium"

    def test_valid_task_full(self) -> None:
        """Test creating task with all args."""
        gate = TaskQualityGate(
            description="Implement user registration endpoint",
            task_type="feature",
            priority="high",
            agent_type="sonnet",
            status="in_progress",
        )
        assert gate.description == "Implement user registration endpoint"
        assert gate.agent_type == "sonnet"
        assert gate.priority == "high"

    def test_task_description_required(self) -> None:
        """Test that task description is required."""
        with pytest.raises(ValidationError):
            TaskQualityGate()  # type: ignore

    def test_task_description_too_short(self) -> None:
        """Test that description must be at least 10 chars."""
        with pytest.raises(ValidationError) as exc_info:
            TaskQualityGate(description="short")
        assert "10 characters" in str(exc_info.value).lower()

    def test_task_description_placeholder_text(self) -> None:
        """Test that placeholder descriptions are rejected."""
        for placeholder in ["TODO: fix this", "FIXME later", "WIP implementation"]:
            with pytest.raises(ValidationError) as exc_info:
                TaskQualityGate(description=placeholder)
            assert "placeholder" in str(exc_info.value).lower()

    def test_task_invalid_agent_type(self) -> None:
        """Test that invalid agent type fails."""
        with pytest.raises(ValidationError) as exc_info:
            TaskQualityGate(
                description="Implement user registration",
                agent_type="invalid_agent",  # type: ignore
            )
        assert "invalid agent type" in str(exc_info.value).lower()

    def test_task_valid_agent_types(self) -> None:
        """Test all valid agent types."""
        valid_types = ["sonnet", "claude", "opus", "haiku", "gpt4", "gemini"]
        for agent_type in valid_types:
            gate = TaskQualityGate(
                description="Implement user registration",
                agent_type=agent_type,
            )
            assert gate.agent_type == agent_type.lower()

    def test_task_agent_type_case_insensitive(self) -> None:
        """Test that agent type is case-insensitive."""
        gate = TaskQualityGate(
            description="Implement user registration",
            agent_type="Sonnet",
        )
        assert gate.agent_type == "sonnet"

    def test_validate_task_args_helper(self) -> None:
        """Test validate_task_args helper function."""
        gate = validate_task_args(
            description="Implement user registration endpoint",
            agent_type="sonnet",
            priority="high",
        )
        assert gate.agent_type == "sonnet"


# =============================================================================
# Code Quality Markers Detection Tests
# =============================================================================


class TestCodeQualityMarkers:
    """Test code quality marker detection."""

    def test_detect_todo_marker(self) -> None:
        """Test detection of TODO markers."""
        code = """
def foo():
    # TODO: implement this
    pass
"""
        markers = CodeQualityMarkers.detect_markers(code)
        assert len(markers["TODO"]) == 1
        assert "implement" in markers["TODO"][0][1]

    def test_detect_fixme_marker(self) -> None:
        """Test detection of FIXME markers."""
        code = "FIXME: This is broken"
        markers = CodeQualityMarkers.detect_markers(code)
        assert len(markers["FIXME"]) == 1

    def test_detect_wip_marker(self) -> None:
        """Test detection of WIP markers."""
        code = "# WIP: work in progress"
        markers = CodeQualityMarkers.detect_markers(code)
        assert len(markers["WIP"]) == 1

    def test_detect_xxx_marker(self) -> None:
        """Test detection of XXX markers."""
        code = "# XXX: potential issue"
        markers = CodeQualityMarkers.detect_markers(code)
        assert len(markers["XXX"]) == 1

    def test_detect_hack_marker(self) -> None:
        """Test detection of HACK markers."""
        code = "# HACK: temporary solution"
        markers = CodeQualityMarkers.detect_markers(code)
        assert len(markers["HACK"]) == 1

    def test_no_incomplete_markers(self) -> None:
        """Test code with no incomplete markers."""
        code = """
def foo():
    '''Clean implementation.'''
    return 42
"""
        markers = CodeQualityMarkers.detect_markers(code)
        assert all(not items for items in markers.values())

    def test_multiple_markers(self) -> None:
        """Test detection of multiple markers."""
        code = """
def foo():
    # TODO: implement
    # FIXME: broken
    # HACK: temporary
    pass
"""
        markers = CodeQualityMarkers.detect_markers(code)
        assert len(markers["TODO"]) == 1
        assert len(markers["FIXME"]) == 1
        assert len(markers["HACK"]) == 1

    def test_marker_line_numbers(self) -> None:
        """Test that line numbers are correctly identified."""
        code = """
line 1
TODO: something
line 3
FIXME: something else
"""
        markers = CodeQualityMarkers.detect_markers(code)
        assert markers["TODO"][0][0] == 3
        assert markers["FIXME"][0][0] == 5

    def test_has_incomplete_markers_true(self) -> None:
        """Test has_incomplete_markers returns True when markers exist."""
        code = "# TODO: implement\ndef foo():\n    pass"
        assert CodeQualityMarkers.has_incomplete_markers(code) is True

    def test_has_incomplete_markers_false(self) -> None:
        """Test has_incomplete_markers returns False when no markers."""
        code = "def foo():\n    return 42"
        assert CodeQualityMarkers.has_incomplete_markers(code) is False

    def test_skip_docstring_examples(self) -> None:
        """Test that docstring start lines are skipped."""
        code = '''
def foo():
    """Clean implementation."""
    pass
'''
        # Lines starting with """ are skipped
        markers = CodeQualityMarkers.detect_markers(code)
        # Should not detect any markers
        assert all(not items for items in markers.values())


# =============================================================================
# Validation Utility Function Tests
# =============================================================================


class TestValidationUtilities:
    """Test validation utility functions."""

    def test_validate_code_quality_valid_file(self, tmp_path: object) -> None:
        """Test validate_code_quality with valid file."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def foo():\n    return 42\n")
            f.flush()
            result = validate_code_quality(f.name)
            assert result is True

    def test_validate_code_quality_invalid_file(self) -> None:
        """Test validate_code_quality with file containing markers."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def foo():\n    # TODO: implement\n    pass\n")
            f.flush()
            result = validate_code_quality(f.name)
            assert result is False

    def test_validate_code_quality_nonexistent_file(self) -> None:
        """Test validate_code_quality with nonexistent file returns True."""
        result = validate_code_quality("/nonexistent/file.py")
        assert result is True  # Skip files that can't be read
