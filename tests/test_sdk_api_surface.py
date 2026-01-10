"""
Tests for SDK API surface and convenience methods.

These tests verify that the SDK provides a clean, discoverable API
for common operations like serialization, even when they are thin
wrappers around Pydantic methods.
"""

from htmlgraph import SDK


def test_node_to_dict(tmp_path):
    """Test that Node.to_dict() method exists and works."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "features").mkdir()
    (graph_dir / "tracks").mkdir()
    sdk = SDK(directory=str(graph_dir), agent="test")
    track = sdk.tracks.create("Test Track").save()
    feature = sdk.features.create("Test Feature").set_track(track.id).save()

    # Test to_dict() exists and works
    data = feature.to_dict()
    assert isinstance(data, dict)
    assert data["title"] == "Test Feature"
    assert data["type"] == "feature"
    assert "id" in data
    assert "status" in data
    assert "created" in data

    # Test equivalence with model_dump()
    assert feature.to_dict() == feature.model_dump()


def test_spike_to_dict(tmp_path):
    """Test that Spike inherits to_dict() from Node."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "spikes").mkdir()
    sdk = SDK(directory=str(graph_dir), agent="test")
    spike = sdk.spikes.create("Test Spike Investigation").save()

    # Test to_dict() works on Spike subclass
    data = spike.to_dict()
    assert isinstance(data, dict)
    assert data["title"] == "Test Spike Investigation"
    assert data["type"] == "spike"

    # Test equivalence with model_dump()
    assert spike.to_dict() == spike.model_dump()


def test_session_to_dict(tmp_path):
    """Test that Session has model_dump() via Pydantic."""
    from htmlgraph.models import Session

    # Create a Session instance directly
    session = Session(id="test-session-123", agent="test")

    # Session is not a Node subclass, but should still have model_dump
    data = session.model_dump()
    assert isinstance(data, dict)
    assert "id" in data
    assert "agent" in data
    assert "status" in data
    assert data["id"] == "test-session-123"
    assert data["agent"] == "test"


def test_to_dict_contains_all_fields(tmp_path):
    """Test that to_dict() includes all Node fields."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "features").mkdir()
    (graph_dir / "tracks").mkdir()
    sdk = SDK(directory=str(graph_dir), agent="test")
    track = sdk.tracks.create("Test Track").save()
    feature = (
        sdk.features.create("Feature with fields")
        .set_track(track.id)
        .set_priority("high")
        .set_status("in-progress")
        .add_step("Step 1")
        .add_step("Step 2")
        .save()
    )

    data = feature.to_dict()

    # Check that fluent API fields are included
    assert data["priority"] == "high"
    assert data["status"] == "in-progress"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["description"] == "Step 1"
    assert data["steps"][1]["description"] == "Step 2"


def test_to_dict_serializable(tmp_path):
    """Test that to_dict() output is JSON-serializable."""
    import json

    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "features").mkdir()
    (graph_dir / "tracks").mkdir()
    sdk = SDK(directory=str(graph_dir), agent="test")
    track = sdk.tracks.create("Test Track").save()
    feature = sdk.features.create("Test Feature").set_track(track.id).save()

    data = feature.to_dict()

    # Should be JSON-serializable (raises if not)
    json_str = json.dumps(data, default=str)  # default=str for datetime objects
    assert isinstance(json_str, str)

    # Should be able to round-trip
    parsed = json.loads(json_str)
    assert parsed["title"] == "Test Feature"
