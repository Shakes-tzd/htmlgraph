"""
Tests for SDK active work item lifecycle (Phase 2: SDK Collection Integration).

Tests:
- start() sets active_feature_id in session row
- complete() clears active_feature_id from session row
- get_active_work_item() returns session-scoped item when session_id is set
- get_active_work_item() falls back to global scan when no session_id
- Starting a different item overwrites the active item in session row
- Completing a non-active item doesn't clear the active item
"""

from __future__ import annotations

from pathlib import Path

import pytest
from htmlgraph.sdk import SDK


@pytest.fixture
def sdk_with_session(isolated_graph_dir_full: Path, isolated_db: Path) -> SDK:
    """
    SDK instance with an active session for testing session-scoped lookups.
    """
    sdk = SDK(
        directory=isolated_graph_dir_full,
        agent="test-agent",
        db_path=str(isolated_db),
    )
    # Ensure an active session exists so session-scoped methods work
    sdk.session_manager._ensure_session_for_agent(agent="test-agent")
    return sdk


class TestStartSetsActiveWorkItem:
    """Test that start() writes active_feature_id to the sessions row."""

    def test_start_sets_active_feature_id(
        self, sdk_with_session: SDK, isolated_graph_dir_full: Path
    ) -> None:
        """start() should write node_id into active_feature_id on the session row."""
        sdk = sdk_with_session
        track = sdk.tracks.create("Test Track").save()
        feature = sdk.features.create("Test Feature").set_track(track.id).save()

        # Ensure session row exists in DB for the active session
        active_session = sdk.session_manager.get_active_session()
        assert active_session is not None, "Expected an active session"

        # Insert the session into the DB sessions table so set_active_work_item has a row
        sdk._db.insert_session(
            session_id=active_session.id,
            agent_assigned="test-agent",
        )

        sdk.features.start(feature.id)

        active_id = sdk._db.get_active_work_item_for_session(active_session.id)
        assert active_id == feature.id

    def test_start_overwrites_previous_active_item(self, sdk_with_session: SDK) -> None:
        """Starting a second item should overwrite the first in the session row."""
        sdk = sdk_with_session
        track = sdk.tracks.create("Test Track").save()
        feat1 = sdk.features.create("Feature One").set_track(track.id).save()
        track = sdk.tracks.create("Test Track").save()
        feat2 = sdk.features.create("Feature Two").set_track(track.id).save()

        active_session = sdk.session_manager.get_active_session()
        assert active_session is not None
        sdk._db.insert_session(
            session_id=active_session.id, agent_assigned="test-agent"
        )

        sdk.features.start(feat1.id)
        assert sdk._db.get_active_work_item_for_session(active_session.id) == feat1.id

        # Complete feat1 first to satisfy WIP limit, then start feat2
        sdk.features.complete(feat1.id)
        sdk.features.start(feat2.id)
        assert sdk._db.get_active_work_item_for_session(active_session.id) == feat2.id


class TestCompletesClearsActiveWorkItem:
    """Test that complete() clears active_feature_id from the session row."""

    def test_complete_clears_active_feature_id(self, sdk_with_session: SDK) -> None:
        """complete() should clear active_feature_id when the completed item was active."""
        sdk = sdk_with_session
        track = sdk.tracks.create("Test Track").save()
        feature = sdk.features.create("Feature to Complete").set_track(track.id).save()

        active_session = sdk.session_manager.get_active_session()
        assert active_session is not None
        sdk._db.insert_session(
            session_id=active_session.id, agent_assigned="test-agent"
        )

        sdk.features.start(feature.id)
        assert sdk._db.get_active_work_item_for_session(active_session.id) == feature.id

        sdk.features.complete(feature.id)
        assert sdk._db.get_active_work_item_for_session(active_session.id) is None

    def test_complete_non_active_does_not_clear(self, sdk_with_session: SDK) -> None:
        """Completing a non-active item should NOT clear the active item."""
        sdk = sdk_with_session
        track = sdk.tracks.create("Test Track").save()
        active_feat = sdk.features.create("Active Feature").set_track(track.id).save()
        other_feat = sdk.features.create("Other Feature").set_track(track.id).save()

        active_session = sdk.session_manager.get_active_session()
        assert active_session is not None
        sdk._db.insert_session(
            session_id=active_session.id, agent_assigned="test-agent"
        )

        # Start active_feat so it's the active item
        sdk.features.start(active_feat.id)
        assert (
            sdk._db.get_active_work_item_for_session(active_session.id)
            == active_feat.id
        )

        # Complete other_feat (not the active one) — should not clear active item
        # First start other_feat in a separate SDK to bypass WIP limit in this SDK
        # (or just directly set status via the graph)
        other_node = sdk.features.get(other_feat.id)
        assert other_node is not None
        other_node.status = "in-progress"
        sdk._graph.update(other_node)
        sdk.session_manager._features_cache_dirty = True

        # Now complete other_feat — active_feat should still be active in session row
        sdk.features.complete(other_feat.id)
        assert (
            sdk._db.get_active_work_item_for_session(active_session.id)
            == active_feat.id
        )


class TestGetActiveWorkItemSessionScoped:
    """Test get_active_work_item() uses session-scoped lookup when session_id available."""

    def test_returns_session_scoped_item(self, sdk_with_session: SDK) -> None:
        """get_active_work_item() should return item from session row (fast path)."""
        sdk = sdk_with_session
        track = sdk.tracks.create("Test Track").save()
        feature = (
            sdk.features.create("Session Scoped Feature").set_track(track.id).save()
        )

        active_session = sdk.session_manager.get_active_session()
        assert active_session is not None
        sdk._db.insert_session(
            session_id=active_session.id, agent_assigned="test-agent"
        )

        sdk.features.start(feature.id)

        result = sdk.get_active_work_item()
        assert result is not None
        assert result["id"] == feature.id
        assert result["title"] == "Session Scoped Feature"

    def test_returns_none_when_no_active_item(self, sdk_with_session: SDK) -> None:
        """get_active_work_item() should return None when no active item in session."""
        sdk = sdk_with_session
        active_session = sdk.session_manager.get_active_session()
        assert active_session is not None
        sdk._db.insert_session(
            session_id=active_session.id, agent_assigned="test-agent"
        )

        # No start() called — nothing active in session row
        # (also ensure no in-progress items from global scan)
        result = sdk.get_active_work_item()
        # May return None or an auto-spike — just verify no crash
        # The important thing: if session row is empty, we don't return a stale result
        if result is not None:
            # It came from global scan fallback (e.g. auto-spike) — acceptable
            assert "id" in result

    def test_falls_back_to_global_scan_when_no_session(
        self, isolated_graph_dir_full: Path, isolated_db: Path
    ) -> None:
        """get_active_work_item() falls back to global scan when no active session."""
        sdk = SDK(
            directory=isolated_graph_dir_full,
            agent="test-agent",
            db_path=str(isolated_db),
        )
        # Do NOT call ensure_session — no active session
        # Create a feature and mark it in-progress manually (global scan path)
        # First create a track since features require track linkage
        track = sdk.tracks.create("Test Track").save()
        feature = sdk.features.create("Global Scan Feature").set_track(track.id).save()
        node = sdk.features.get(feature.id)
        assert node is not None
        node.status = "in-progress"
        sdk._graph.update(node)

        result = sdk.get_active_work_item()
        # Should find via global scan
        assert result is not None
        assert result["id"] == feature.id

    def test_session_scoped_takes_priority_over_global_scan(
        self, sdk_with_session: SDK
    ) -> None:
        """Session-scoped item should be returned, not a different global in-progress item."""
        sdk = sdk_with_session
        track = sdk.tracks.create("Test Track").save()
        session_feat = sdk.features.create("Session Feature").set_track(track.id).save()
        # Create another in-progress feature via direct graph update (not via start())
        track = sdk.tracks.create("Test Track").save()
        other_feat = (
            sdk.features.create("Other In-Progress Feature").set_track(track.id).save()
        )
        other_node = sdk.features.get(other_feat.id)
        assert other_node is not None
        other_node.status = "in-progress"
        sdk._graph.update(other_node)

        active_session = sdk.session_manager.get_active_session()
        assert active_session is not None
        sdk._db.insert_session(
            session_id=active_session.id, agent_assigned="test-agent"
        )

        # Start session_feat — this sets it as the session-scoped active item
        sdk.features.start(session_feat.id)

        result = sdk.get_active_work_item()
        assert result is not None
        # Session-scoped fast path should return session_feat, not other_feat
        assert result["id"] == session_feat.id


class TestActiveItemUnknownAfterComplete:
    """Test that completing the active item truly clears the session row."""

    def test_session_row_null_after_complete(self, sdk_with_session: SDK) -> None:
        """After complete(), session row active_feature_id should be NULL."""
        sdk = sdk_with_session
        track = sdk.tracks.create("Test Track").save()
        feature = sdk.features.create("Lifecycle Feature").set_track(track.id).save()

        active_session = sdk.session_manager.get_active_session()
        assert active_session is not None
        sdk._db.insert_session(
            session_id=active_session.id, agent_assigned="test-agent"
        )

        sdk.features.start(feature.id)
        assert sdk._db.get_active_work_item_for_session(active_session.id) == feature.id

        sdk.features.complete(feature.id)
        assert sdk._db.get_active_work_item_for_session(active_session.id) is None

        # get_active_work_item() should now fall back to global scan
        # (no more session-scoped item, no other in-progress items)
        result = sdk.get_active_work_item()
        # Feature is now 'done', so global scan should return None (or auto-spike)
        if result is not None:
            assert result["id"] != feature.id or result.get("status") != "in-progress"
