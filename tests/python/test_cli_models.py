"""Tests for CLI Pydantic models in htmlgraph.cli.models.

Covers the Args models (FeatureCreateArgs, ServeArgs, StatusArgs, SnapshotArgs,
FeatureListArgs, FeatureStartArgs, FeatureCompleteArgs, OrchestratorEnableArgs,
OrchestratorDisableArgs, OrchestratorStatusArgs) as well as the existing
config/filter models to ensure comprehensive validation.

Also covers BaseCommand.parse_validated_args() integration.
"""

from __future__ import annotations

import argparse

import pytest
from htmlgraph.cli.models import (
    BootstrapConfig,
    FeatureCompleteArgs,
    FeatureCreateArgs,
    FeatureCreateConfig,
    FeatureFilter,
    FeatureListArgs,
    FeatureStartArgs,
    InitConfig,
    OrchestratorDisableArgs,
    OrchestratorEnableArgs,
    OrchestratorStatusArgs,
    ServeApiConfig,
    ServeArgs,
    ServeConfig,
    SnapshotArgs,
    StatusArgs,
    TrackFilter,
    format_validation_error,
    validate_args,
)
from pydantic import ValidationError

# ============================================================================
# FeatureCreateArgs
# ============================================================================


class TestFeatureCreateArgs:
    """Tests for FeatureCreateArgs validation."""

    def test_valid_minimal(self):
        """Minimal required fields create valid model."""
        args = FeatureCreateArgs(title="My Feature")
        assert args.title == "My Feature"
        assert args.priority == "medium"
        assert args.track_id is None
        assert args.description is None
        assert args.steps is None
        assert args.collection == "features"
        assert args.agent == "claude-code"

    def test_valid_full(self):
        """All fields provided creates valid model."""
        args = FeatureCreateArgs(
            title="My Feature",
            priority="high",
            track_id="trk-abc123",
            description="A description",
            steps=5,
            collection="bugs",
            agent="gemini",
        )
        assert args.title == "My Feature"
        assert args.priority == "high"
        assert args.track_id == "trk-abc123"
        assert args.description == "A description"
        assert args.steps == 5
        assert args.collection == "bugs"
        assert args.agent == "gemini"

    def test_title_stripped(self):
        """Title whitespace is stripped."""
        args = FeatureCreateArgs(title="  My Feature  ")
        assert args.title == "My Feature"

    def test_empty_title_rejected(self):
        """Empty title raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureCreateArgs(title="")

    def test_whitespace_only_title_rejected(self):
        """Whitespace-only title raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureCreateArgs(title="   ")

    def test_title_too_long_rejected(self):
        """Title exceeding 200 chars raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureCreateArgs(title="x" * 201)

    def test_invalid_priority_rejected(self):
        """Invalid priority raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureCreateArgs(title="Test", priority="ultra")

    def test_all_valid_priorities(self):
        """All valid priority values are accepted."""
        for priority in ("critical", "high", "medium", "low"):
            args = FeatureCreateArgs(title="T", priority=priority)
            assert args.priority == priority

    def test_steps_minimum(self):
        """Steps must be >= 1."""
        with pytest.raises(ValidationError):
            FeatureCreateArgs(title="T", steps=0)

    def test_steps_maximum(self):
        """Steps must be <= 100."""
        with pytest.raises(ValidationError):
            FeatureCreateArgs(title="T", steps=101)

    def test_steps_valid_boundary(self):
        """Steps at boundary values are accepted."""
        args = FeatureCreateArgs(title="T", steps=1)
        assert args.steps == 1
        args = FeatureCreateArgs(title="T", steps=100)
        assert args.steps == 100


# ============================================================================
# ServeArgs
# ============================================================================


class TestServeArgs:
    """Tests for ServeArgs validation."""

    def test_defaults(self):
        """Default values are set correctly."""
        args = ServeArgs()
        assert args.port == 8080
        assert args.host == "0.0.0.0"
        assert args.db_path is None
        assert args.graph_dir == ".htmlgraph"
        assert args.static_dir == "."
        assert args.no_watch is False
        assert args.auto_port is False

    def test_custom_port(self):
        """Custom port in valid range is accepted."""
        args = ServeArgs(port=9090)
        assert args.port == 9090

    def test_port_too_low_rejected(self):
        """Port below 1024 is rejected."""
        with pytest.raises(ValidationError):
            ServeArgs(port=80)

    def test_port_too_high_rejected(self):
        """Port above 65535 is rejected."""
        with pytest.raises(ValidationError):
            ServeArgs(port=65536)

    def test_port_boundary_low(self):
        """Port at minimum boundary (1024) is accepted."""
        args = ServeArgs(port=1024)
        assert args.port == 1024

    def test_port_boundary_high(self):
        """Port at maximum boundary (65535) is accepted."""
        args = ServeArgs(port=65535)
        assert args.port == 65535

    def test_empty_host_rejected(self):
        """Empty host raises ValidationError."""
        with pytest.raises(ValidationError):
            ServeArgs(host="")

    def test_whitespace_host_rejected(self):
        """Whitespace-only host raises ValidationError."""
        with pytest.raises(ValidationError):
            ServeArgs(host="   ")

    def test_db_path_optional(self):
        """db_path is optional."""
        args = ServeArgs(db_path="/path/to/db.sqlite")
        assert args.db_path == "/path/to/db.sqlite"

    def test_bool_flags(self):
        """Boolean flags are set correctly."""
        args = ServeArgs(no_watch=True, auto_port=True)
        assert args.no_watch is True
        assert args.auto_port is True


# ============================================================================
# StatusArgs
# ============================================================================


class TestStatusArgs:
    """Tests for StatusArgs validation."""

    def test_defaults(self):
        """Default values are set correctly."""
        args = StatusArgs()
        assert args.format == "text"
        assert args.verbose is False
        assert args.graph_dir == ".htmlgraph"

    def test_valid_formats(self):
        """Valid format values are accepted."""
        for fmt in ("text", "json", "html"):
            args = StatusArgs(format=fmt)
            assert args.format == fmt

    def test_invalid_format_rejected(self):
        """Invalid format raises ValidationError."""
        with pytest.raises(ValidationError):
            StatusArgs(format="xml")

    def test_verbose_flag(self):
        """Verbose flag can be set."""
        args = StatusArgs(verbose=True)
        assert args.verbose is True

    def test_custom_graph_dir(self):
        """Custom graph directory is accepted."""
        args = StatusArgs(graph_dir="/custom/.htmlgraph")
        assert args.graph_dir == "/custom/.htmlgraph"


# ============================================================================
# SnapshotArgs
# ============================================================================


class TestSnapshotArgs:
    """Tests for SnapshotArgs validation."""

    def test_defaults(self):
        """Default values are set correctly."""
        args = SnapshotArgs()
        assert args.summary is False
        assert args.format == "refs"
        assert args.type is None
        assert args.status is None
        assert args.track is None
        assert args.active is False
        assert args.blockers is False
        assert args.my_work is False

    def test_summary_flag(self):
        """Summary flag can be set."""
        args = SnapshotArgs(summary=True)
        assert args.summary is True

    def test_valid_formats(self):
        """Valid format values are accepted."""
        for fmt in ("text", "json", "refs"):
            args = SnapshotArgs(format=fmt)
            assert args.format == fmt

    def test_invalid_format_rejected(self):
        """Invalid format raises ValidationError."""
        with pytest.raises(ValidationError):
            SnapshotArgs(format="csv")

    def test_type_filter(self):
        """Type filter can be set."""
        args = SnapshotArgs(type="feature")
        assert args.type == "feature"

    def test_status_filter(self):
        """Status filter can be set."""
        args = SnapshotArgs(status="in_progress")
        assert args.status == "in_progress"

    def test_track_filter(self):
        """Track filter can be set."""
        args = SnapshotArgs(track="trk-abc123")
        assert args.track == "trk-abc123"

    def test_bool_flags(self):
        """All boolean flags can be set together."""
        args = SnapshotArgs(active=True, blockers=True, my_work=True)
        assert args.active is True
        assert args.blockers is True
        assert args.my_work is True


# ============================================================================
# Existing config models — regression coverage
# ============================================================================


class TestServeConfig:
    """Regression tests for existing ServeConfig model."""

    def test_defaults(self):
        """Default values match expected."""
        config = ServeConfig()
        assert config.port == 8080
        assert config.host == "0.0.0.0"

    def test_port_validation(self):
        """Port range is enforced."""
        with pytest.raises(ValidationError):
            ServeConfig(port=80)
        with pytest.raises(ValidationError):
            ServeConfig(port=99999)

    def test_valid_config(self):
        """Valid config is accepted."""
        config = ServeConfig(port=9000, host="127.0.0.1")
        assert config.port == 9000
        assert config.host == "127.0.0.1"


class TestFeatureCreateConfig:
    """Regression tests for existing FeatureCreateConfig model."""

    def test_valid_creation(self):
        """Feature create config with required fields."""
        config = FeatureCreateConfig(title="My Feature")
        assert config.title == "My Feature"
        assert config.priority == "medium"

    def test_empty_title_rejected(self):
        """Empty title raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureCreateConfig(title="")


class TestFeatureFilter:
    """Regression tests for FeatureFilter model."""

    def test_defaults(self):
        """Default values are None."""
        f = FeatureFilter()
        assert f.status is None
        assert f.priority is None

    def test_valid_status(self):
        """Valid status values accepted."""
        for status in ("todo", "in_progress", "completed", "blocked", "all"):
            f = FeatureFilter(status=status)
            assert f.status == status

    def test_invalid_status_rejected(self):
        """Invalid status raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureFilter(status="unknown")


class TestInitConfig:
    """Regression tests for InitConfig model."""

    def test_defaults(self):
        """Default values are set correctly."""
        config = InitConfig()
        assert config.dir == "."
        assert config.install_hooks is False
        assert config.interactive is False


class TestServeApiConfig:
    """Regression tests for ServeApiConfig model."""

    def test_defaults(self):
        """Default port is 8000."""
        config = ServeApiConfig()
        assert config.port == 8000
        assert config.host == "127.0.0.1"

    def test_invalid_port_rejected(self):
        """Port below 1024 rejected."""
        with pytest.raises(ValidationError):
            ServeApiConfig(port=80)


class TestBootstrapConfig:
    """Regression tests for BootstrapConfig model."""

    def test_defaults(self):
        """Default path is current directory."""
        config = BootstrapConfig()
        assert config.project_path == "."
        assert config.no_plugins is False


class TestTrackFilter:
    """Regression tests for TrackFilter model."""

    def test_defaults(self):
        """Default values are None."""
        f = TrackFilter()
        assert f.status is None
        assert f.priority is None
        assert f.has_spec is None
        assert f.has_plan is None

    def test_invalid_status_rejected(self):
        """Invalid status raises ValidationError."""
        with pytest.raises(ValidationError):
            TrackFilter(status="unknown")


# ============================================================================
# validate_args helper
# ============================================================================


class TestValidateArgs:
    """Tests for validate_args helper function."""

    def test_with_namespace(self):
        """validate_args works with argparse Namespace."""
        from argparse import Namespace

        ns = Namespace(port=9000, host="localhost")
        config = validate_args(ServeConfig, ns)
        assert config.port == 9000
        assert config.host == "localhost"

    def test_with_dict(self):
        """validate_args works with plain dict."""
        config = validate_args(ServeConfig, {"port": 8888})
        assert config.port == 8888

    def test_filters_command_fields(self):
        """Command routing fields are filtered out."""
        from argparse import Namespace

        ns = Namespace(command="serve", func=lambda x: x, port=8080)
        config = validate_args(ServeConfig, ns)
        assert config.port == 8080


# ============================================================================
# format_validation_error helper
# ============================================================================


class TestFormatValidationError:
    """Tests for format_validation_error helper."""

    def test_formats_error_message(self):
        """Formatted error contains field names and messages."""
        try:
            ServeArgs(port=80)
        except ValidationError as e:
            msg = format_validation_error(e)
            assert "Validation error:" in msg
            assert "port" in msg


# ============================================================================
# FeatureListArgs
# ============================================================================


class TestFeatureListArgs:
    """Tests for FeatureListArgs validation."""

    def test_defaults(self):
        """Default values are set correctly."""
        args = FeatureListArgs()
        assert args.status is None
        assert args.format == "text"
        assert args.quiet is False

    def test_valid_status_values(self):
        """All valid status values are accepted."""
        for status in ("todo", "in_progress", "completed", "blocked"):
            args = FeatureListArgs(status=status)
            assert args.status == status

    def test_invalid_status_rejected(self):
        """Invalid status raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureListArgs(status="unknown")

    def test_valid_formats(self):
        """Valid format values are accepted."""
        for fmt in ("text", "json"):
            args = FeatureListArgs(format=fmt)
            assert args.format == fmt

    def test_invalid_format_rejected(self):
        """Invalid format raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureListArgs(format="csv")

    def test_quiet_flag(self):
        """quiet flag can be set."""
        args = FeatureListArgs(quiet=True)
        assert args.quiet is True


# ============================================================================
# FeatureStartArgs
# ============================================================================


class TestFeatureStartArgs:
    """Tests for FeatureStartArgs validation."""

    def test_valid_minimal(self):
        """Valid feature_id creates model with defaults."""
        args = FeatureStartArgs(feature_id="feat-abc123")
        assert args.feature_id == "feat-abc123"
        assert args.collection == "features"

    def test_feature_id_stripped(self):
        """feature_id whitespace is stripped."""
        args = FeatureStartArgs(feature_id="  feat-abc  ")
        assert args.feature_id == "feat-abc"

    def test_empty_feature_id_rejected(self):
        """Empty feature_id raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureStartArgs(feature_id="")

    def test_whitespace_only_feature_id_rejected(self):
        """Whitespace-only feature_id raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureStartArgs(feature_id="   ")

    def test_custom_collection(self):
        """Custom collection name is accepted."""
        args = FeatureStartArgs(feature_id="feat-123", collection="bugs")
        assert args.collection == "bugs"


# ============================================================================
# FeatureCompleteArgs
# ============================================================================


class TestFeatureCompleteArgs:
    """Tests for FeatureCompleteArgs validation."""

    def test_valid_minimal(self):
        """Valid feature_id creates model with defaults."""
        args = FeatureCompleteArgs(feature_id="feat-done")
        assert args.feature_id == "feat-done"
        assert args.collection == "features"

    def test_feature_id_stripped(self):
        """feature_id whitespace is stripped."""
        args = FeatureCompleteArgs(feature_id="  feat-done  ")
        assert args.feature_id == "feat-done"

    def test_empty_feature_id_rejected(self):
        """Empty feature_id raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureCompleteArgs(feature_id="")

    def test_whitespace_only_feature_id_rejected(self):
        """Whitespace-only feature_id raises ValidationError."""
        with pytest.raises(ValidationError):
            FeatureCompleteArgs(feature_id="   ")

    def test_custom_collection(self):
        """Custom collection name is accepted."""
        args = FeatureCompleteArgs(feature_id="feat-123", collection="spikes")
        assert args.collection == "spikes"


# ============================================================================
# OrchestratorEnableArgs
# ============================================================================


class TestOrchestratorEnableArgs:
    """Tests for OrchestratorEnableArgs validation."""

    def test_default_level(self):
        """Default level is strict."""
        args = OrchestratorEnableArgs()
        assert args.level == "strict"

    def test_valid_levels(self):
        """Both valid levels are accepted."""
        for level in ("strict", "guidance"):
            args = OrchestratorEnableArgs(level=level)
            assert args.level == level

    def test_invalid_level_rejected(self):
        """Invalid level raises ValidationError."""
        with pytest.raises(ValidationError):
            OrchestratorEnableArgs(level="permissive")

    def test_invalid_level_empty_rejected(self):
        """Empty level raises ValidationError."""
        with pytest.raises(ValidationError):
            OrchestratorEnableArgs(level="")


# ============================================================================
# OrchestratorDisableArgs
# ============================================================================


class TestOrchestratorDisableArgs:
    """Tests for OrchestratorDisableArgs validation."""

    def test_instantiates_with_no_fields(self):
        """Model with no fields instantiates successfully."""
        args = OrchestratorDisableArgs()
        assert args is not None

    def test_model_has_no_required_fields(self):
        """No fields are required."""
        # Should not raise
        OrchestratorDisableArgs()


# ============================================================================
# OrchestratorStatusArgs
# ============================================================================


class TestOrchestratorStatusArgs:
    """Tests for OrchestratorStatusArgs validation."""

    def test_default_format(self):
        """Default format is text."""
        args = OrchestratorStatusArgs()
        assert args.format == "text"

    def test_valid_formats(self):
        """Both valid formats are accepted."""
        for fmt in ("text", "json"):
            args = OrchestratorStatusArgs(format=fmt)
            assert args.format == fmt

    def test_invalid_format_rejected(self):
        """Invalid format raises ValidationError."""
        with pytest.raises(ValidationError):
            OrchestratorStatusArgs(format="xml")


# ============================================================================
# BaseCommand.parse_validated_args()
# ============================================================================


class TestParseValidatedArgs:
    """Tests for BaseCommand.parse_validated_args() integration."""

    def test_validates_namespace_through_model(self):
        """parse_validated_args maps Namespace fields through the Pydantic model."""
        from htmlgraph.cli.base import BaseCommand
        from htmlgraph.cli.models import OrchestratorEnableArgs

        class _TestCmd(BaseCommand):
            _args_model = OrchestratorEnableArgs

            @classmethod
            def from_args(cls, args):
                return cls()

            def execute(self):
                pass

        ns = argparse.Namespace(level="guidance")
        result = _TestCmd.parse_validated_args(ns)
        assert result.level == "guidance"

    def test_raises_command_error_for_missing_args_model(self):
        """parse_validated_args raises CommandError when _args_model is None."""
        from htmlgraph.cli.base import BaseCommand, CommandError

        class _TestCmd(BaseCommand):
            _args_model = None

            @classmethod
            def from_args(cls, args):
                return cls()

            def execute(self):
                pass

        ns = argparse.Namespace()
        with pytest.raises(CommandError, match="_args_model"):
            _TestCmd.parse_validated_args(ns)

    def test_raises_command_error_for_invalid_input(self):
        """parse_validated_args raises CommandError for invalid Pydantic input."""
        from htmlgraph.cli.base import BaseCommand, CommandError
        from htmlgraph.cli.models import OrchestratorEnableArgs

        class _TestCmd(BaseCommand):
            _args_model = OrchestratorEnableArgs

            @classmethod
            def from_args(cls, args):
                return cls()

            def execute(self):
                pass

        ns = argparse.Namespace(level="not-valid")
        with pytest.raises(CommandError, match="Validation error"):
            _TestCmd.parse_validated_args(ns)

    def test_overrides_take_precedence(self):
        """Keyword overrides replace Namespace values."""
        from htmlgraph.cli.base import BaseCommand
        from htmlgraph.cli.models import FeatureStartArgs

        class _TestCmd(BaseCommand):
            _args_model = FeatureStartArgs

            @classmethod
            def from_args(cls, args):
                return cls()

            def execute(self):
                pass

        ns = argparse.Namespace(id="feat-from-ns", collection="features")
        # Override: map argparse 'id' -> model 'feature_id'
        result = _TestCmd.parse_validated_args(ns, feature_id="feat-override")
        assert result.feature_id == "feat-override"

    def test_commands_without_args_model_still_work(self):
        """Commands that don't use _args_model work as before (backward compat)."""
        from htmlgraph.cli.base import BaseCommand, CommandResult

        class _LegacyCmd(BaseCommand):
            # No _args_model set — uses BaseCommand default (None)

            def __init__(self, *, value: str) -> None:
                super().__init__()
                self.value = value

            @classmethod
            def from_args(cls, args):
                # Old-style: direct attribute access
                return cls(value=getattr(args, "value", "default"))

            def execute(self) -> CommandResult:
                return CommandResult(text=self.value)

        ns = argparse.Namespace(value="hello")
        cmd = _LegacyCmd.from_args(ns)
        assert cmd.value == "hello"
        result = cmd.execute()
        assert result.text == "hello"

    def test_feature_start_command_uses_validated_args(self):
        """FeatureStartCommand.from_args validates through FeatureStartArgs."""
        from htmlgraph.cli.work.features import FeatureStartCommand

        ns = argparse.Namespace(id="feat-123", collection="features")
        cmd = FeatureStartCommand.from_args(ns)
        assert cmd.feature_id == "feat-123"
        assert cmd.collection == "features"

    def test_feature_complete_command_uses_validated_args(self):
        """FeatureCompleteCommand.from_args validates through FeatureCompleteArgs."""
        from htmlgraph.cli.work.features import FeatureCompleteCommand

        ns = argparse.Namespace(id="feat-456", collection="features")
        cmd = FeatureCompleteCommand.from_args(ns)
        assert cmd.feature_id == "feat-456"
        assert cmd.collection == "features"

    def test_orchestrator_enable_command_uses_validated_args(self):
        """OrchestratorEnableCommand.from_args validates through OrchestratorEnableArgs."""
        from htmlgraph.cli.work.orchestration import OrchestratorEnableCommand

        ns = argparse.Namespace(level="guidance")
        cmd = OrchestratorEnableCommand.from_args(ns)
        assert cmd.level == "guidance"

    def test_orchestrator_enable_rejects_invalid_level(self):
        """OrchestratorEnableCommand.from_args rejects invalid level."""
        from htmlgraph.cli.base import CommandError
        from htmlgraph.cli.work.orchestration import OrchestratorEnableCommand

        ns = argparse.Namespace(level="extreme")
        with pytest.raises(CommandError, match="Validation error"):
            OrchestratorEnableCommand.from_args(ns)
