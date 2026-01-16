"""Tests for the snapshot command."""

import json

import pytest
from htmlgraph.cli.work.snapshot import SnapshotCommand
from htmlgraph.sdk import SDK


@pytest.fixture
def populated_sdk(tmp_path, isolated_db):
    """Create SDK with test features, tracks, and bugs."""
    sdk = SDK(
        directory=str(tmp_path / ".htmlgraph"),
        agent="test-agent",
        db_path=str(isolated_db),
    )

    # Create tracks first (features require track linkage)
    track1 = sdk.tracks.create(title="Browser-Native Query Interface").save()
    track2 = sdk.tracks.create(title="Future track").save()

    # Set status on tracks
    with sdk.tracks.edit(track1.id) as track:
        track.status = "in-progress"
    with sdk.tracks.edit(track2.id) as track:
        track.status = "todo"

    # Create features with different statuses (linked to track1)
    sdk.features.create(
        title="Implement snapshot command",
        priority="high",
        status="in-progress",
    ).set_track(track1.id).save()
    sdk.features.create(
        title="Add RefManager class for short refs",
        priority="high",
        status="todo",
    ).set_track(track1.id).save()
    sdk.features.create(
        title="Add sdk.ref() method for ref-based lookup",
        priority="medium",
        status="todo",
    ).set_track(track1.id).save()
    sdk.features.create(
        title="Completed feature",
        priority="low",
        status="done",
    ).set_track(track1.id).save()

    # Create bugs
    sdk.bugs.create(
        title="Fix snapshot formatting",
        priority="high",
        status="todo",
    ).save()

    # Create spikes
    sdk.spikes.create(
        title="Research ref system",
        status="done",
    ).save()

    return sdk


def test_snapshot_refs_format(populated_sdk, isolated_db):
    """Test snapshot command with refs format."""
    cmd = SnapshotCommand(output_format="refs", node_type="all", status="all")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    result = cmd.execute()

    assert result.exit_code == 0
    output = result.text
    assert "SNAPSHOT - Current Graph State" in output
    assert "FEATURES" in output
    assert "TRACKS" in output
    assert "BUGS" in output
    assert "SPIKES" in output
    assert "TODO:" in output
    assert "IN_PROGRESS:" in output
    assert "DONE:" in output


def test_snapshot_json_format(populated_sdk, isolated_db):
    """Test snapshot command with JSON format."""
    cmd = SnapshotCommand(output_format="json", node_type="all", status="all")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    result = cmd.execute()

    assert result.exit_code == 0
    output = result.text

    # Verify valid JSON
    data = json.loads(output)
    assert isinstance(data, list)
    assert len(data) > 0

    # Verify structure
    item = data[0]
    assert "id" in item
    assert "type" in item
    assert "title" in item
    assert "status" in item
    assert "priority" in item


def test_snapshot_text_format(populated_sdk, isolated_db):
    """Test snapshot command with text format."""
    cmd = SnapshotCommand(output_format="text", node_type="all", status="all")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    result = cmd.execute()

    assert result.exit_code == 0
    output = result.text

    # Text format should have type, title, and status (space-separated)
    assert "feature" in output.lower()
    assert "track" in output.lower()
    # Text format uses spaces, not pipes, for column separation


def test_snapshot_type_filter_feature(populated_sdk, isolated_db):
    """Test snapshot command filtering by type=feature."""
    cmd = SnapshotCommand(output_format="refs", node_type="feature", status="all")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    result = cmd.execute()

    assert result.exit_code == 0
    output = result.text

    assert "FEATURES" in output
    assert "TRACKS" not in output
    assert "BUGS" not in output
    assert "SPIKES" not in output


def test_snapshot_type_filter_track(populated_sdk, isolated_db):
    """Test snapshot command filtering by type=track."""
    cmd = SnapshotCommand(output_format="refs", node_type="track", status="all")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    result = cmd.execute()

    assert result.exit_code == 0
    output = result.text

    assert "TRACKS" in output
    assert "FEATURES" not in output
    assert "BUGS" not in output


def test_snapshot_status_filter_todo(populated_sdk, isolated_db):
    """Test snapshot command filtering by status=todo."""
    cmd = SnapshotCommand(output_format="json", node_type="all", status="todo")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    result = cmd.execute()

    assert result.exit_code == 0
    data = json.loads(result.text)

    # All items should have status=todo
    for item in data:
        assert item["status"] == "todo"


def test_snapshot_status_filter_in_progress(populated_sdk, isolated_db):
    """Test snapshot command filtering by status=in_progress."""
    cmd = SnapshotCommand(output_format="json", node_type="all", status="in-progress")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    result = cmd.execute()

    assert result.exit_code == 0
    data = json.loads(result.text)

    # All items should have status=in_progress
    for item in data:
        assert item["status"] == "in-progress"


def test_snapshot_combined_filters(populated_sdk, isolated_db):
    """Test snapshot command with both type and status filters."""
    cmd = SnapshotCommand(output_format="json", node_type="feature", status="todo")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    result = cmd.execute()

    assert result.exit_code == 0
    data = json.loads(result.text)

    # All items should be features with status=todo
    for item in data:
        assert item["type"] == "feature"
        assert item["status"] == "todo"

    # Should have exactly 2 matching features
    assert len(data) == 2


def test_snapshot_empty_results(tmp_path, isolated_db):
    """Test snapshot command with no matching items."""
    sdk = SDK(
        directory=str(tmp_path / ".htmlgraph"),
        agent="test-agent",
        db_path=str(isolated_db),
    )

    cmd = SnapshotCommand(output_format="refs", node_type="feature", status="todo")
    cmd.graph_dir = str(sdk._directory)
    cmd.agent = sdk.agent

    result = cmd.execute()

    assert result.exit_code == 0
    output = result.text
    assert "SNAPSHOT - Current Graph State" in output


def test_snapshot_refs_sorting(populated_sdk, isolated_db):
    """Test that snapshot output is sorted by type, status, ref."""
    cmd = SnapshotCommand(output_format="json", node_type="all", status="all")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    result = cmd.execute()
    data = json.loads(result.text)

    # Verify items are sorted
    prev_type = ""
    prev_status = ""
    for item in data:
        # Types should be in order (feature, track, bug, spike, chore, epic)
        if item["type"] != prev_type:
            assert item["type"] >= prev_type or prev_type == ""
            prev_type = item["type"]
            prev_status = ""

        # Within same type, statuses should be in order
        if item["type"] == prev_type:
            assert item["status"] >= prev_status or prev_status == ""
            prev_status = item["status"]


def test_snapshot_node_to_dict_with_refs(populated_sdk, isolated_db):
    """Test that _node_to_dict includes ref when available."""
    cmd = SnapshotCommand(output_format="refs")
    cmd._sdk = populated_sdk

    feature = populated_sdk.features.all()[0]
    item_dict = cmd._node_to_dict(populated_sdk, feature)

    assert "ref" in item_dict
    assert "id" in item_dict
    assert "type" in item_dict
    assert "title" in item_dict
    assert "status" in item_dict
    assert "priority" in item_dict


def test_snapshot_handles_missing_priority(populated_sdk, isolated_db):
    """Test snapshot handles nodes without priority gracefully."""
    # Create a track (tracks may have default priority)
    track = populated_sdk.tracks.all()[0]

    cmd = SnapshotCommand(output_format="refs")
    cmd.graph_dir = str(populated_sdk._directory)
    cmd.agent = populated_sdk.agent

    item_dict = cmd._node_to_dict(populated_sdk, track)

    # Priority should be present (may be default "medium") or None
    assert "priority" in item_dict


def test_snapshot_command_from_args(isolated_db):
    """Test SnapshotCommand.from_args() method."""
    from argparse import Namespace

    args = Namespace(output_format="json", type="feature", status="todo")
    cmd = SnapshotCommand.from_args(args)

    assert cmd.output_format == "json"
    assert cmd.node_type == "feature"
    assert cmd.status == "todo"


def test_snapshot_command_from_args_defaults(isolated_db):
    """Test SnapshotCommand.from_args() with defaults."""
    from argparse import Namespace

    args = Namespace(output_format="refs")
    cmd = SnapshotCommand.from_args(args)

    assert cmd.output_format == "refs"
    assert cmd.node_type is None
    assert cmd.status is None
