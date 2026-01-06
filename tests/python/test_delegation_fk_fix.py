#!/usr/bin/env python3
"""
Test delegation event recording with foreign key constraints.

This test verifies that:
1. record_delegation_event() can create sessions automatically if missing
2. Foreign key constraints don't prevent delegation recording
3. Sessions are created as placeholders when needed
4. Multiple delegations can be recorded without issues
"""

import tempfile
import unittest
from pathlib import Path

from htmlgraph.db.schema import HtmlGraphDB


class TestDelegationFKFix(unittest.TestCase):
    """Test suite for delegation foreign key constraint handling."""

    def setUp(self) -> None:
        """Create temporary database for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        self.db = HtmlGraphDB(self.db_path)

    def tearDown(self) -> None:
        """Clean up temporary database."""
        self.db.close()
        self.temp_dir.cleanup()

    def test_record_delegation_without_preexisting_session(self) -> None:
        """Test recording delegation when session doesn't exist."""
        # Record delegation with non-existent session
        handoff_id = self.db.record_delegation_event(
            from_agent="test-agent",
            to_agent="test-subagent",
            task_description="Test delegation task",
            session_id="sess-test-123",
        )

        # Verify handoff was recorded
        self.assertIsNotNone(handoff_id)
        self.assertTrue(handoff_id.startswith("hand-"))

        # Verify session was auto-created
        cursor = self.db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            "SELECT session_id, agent_assigned FROM sessions WHERE session_id = ?",
            ("sess-test-123",),
        )
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "sess-test-123")

        # Verify delegation was recorded
        cursor.execute(
            "SELECT handoff_id, from_agent, to_agent FROM agent_collaboration WHERE handoff_id = ?",
            (handoff_id,),
        )
        collab = cursor.fetchone()
        self.assertIsNotNone(collab)
        self.assertEqual(collab[1], "test-agent")
        self.assertEqual(collab[2], "test-subagent")

    def test_record_delegation_with_preexisting_session(self) -> None:
        """Test recording delegation when session already exists."""
        # Create session first
        self.db.insert_session(
            session_id="sess-existing",
            agent_assigned="existing-agent",
        )

        # Record delegation
        handoff_id = self.db.record_delegation_event(
            from_agent="test-agent",
            to_agent="test-subagent",
            task_description="Test with existing session",
            session_id="sess-existing",
        )

        # Verify handoff was recorded
        self.assertIsNotNone(handoff_id)

        # Verify session still exists
        cursor = self.db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE session_id = ?", ("sess-existing",)
        )
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)

    def test_record_delegation_without_session_id(self) -> None:
        """Test recording delegation with auto-generated session ID."""
        # Record delegation without providing session_id
        handoff_id = self.db.record_delegation_event(
            from_agent="test-agent",
            to_agent="test-subagent",
            task_description="Test with auto session",
            session_id=None,  # No session ID provided
        )

        # Verify handoff was recorded
        self.assertIsNotNone(handoff_id)

        # Verify session was created
        cursor = self.db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute("SELECT COUNT(*) FROM sessions")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0)

    def test_multiple_delegations_same_session(self) -> None:
        """Test recording multiple delegations to the same session."""
        session_id = "sess-multi-test"

        # Record first delegation
        handoff1 = self.db.record_delegation_event(
            from_agent="agent-a",
            to_agent="agent-b",
            task_description="Task 1",
            session_id=session_id,
        )

        # Record second delegation to same session
        handoff2 = self.db.record_delegation_event(
            from_agent="agent-b",
            to_agent="agent-c",
            task_description="Task 2",
            session_id=session_id,
        )

        # Both should succeed
        self.assertIsNotNone(handoff1)
        self.assertIsNotNone(handoff2)
        self.assertNotEqual(handoff1, handoff2)

        # Verify both in database
        cursor = self.db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            "SELECT COUNT(*) FROM agent_collaboration WHERE session_id = ?",
            (session_id,),
        )
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)

    def test_ensure_session_exists_idempotent(self) -> None:
        """Test that _ensure_session_exists is idempotent."""
        session_id = "sess-idempotent-test"

        # Call multiple times
        result1 = self.db._ensure_session_exists(session_id, "agent-1")
        result2 = self.db._ensure_session_exists(session_id, "agent-1")
        result3 = self.db._ensure_session_exists(session_id, "agent-1")

        # All should succeed
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertTrue(result3)

        # Should still have only one session
        cursor = self.db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE session_id = ?", (session_id,)
        )
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)

    def test_delegation_with_feature_id(self) -> None:
        """Test recording delegation with associated feature."""
        # Create feature first
        feature_id = "feat-test-123"
        self.db.insert_feature(
            feature_id=feature_id,
            feature_type="feature",
            title="Test Feature",
            status="in_progress",
        )

        # Record delegation with feature
        handoff_id = self.db.record_delegation_event(
            from_agent="test-agent",
            to_agent="test-subagent",
            task_description="Delegation for feature",
            session_id="sess-feat-test",
            feature_id=feature_id,
        )

        # Verify recorded correctly
        self.assertIsNotNone(handoff_id)

        cursor = self.db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            "SELECT feature_id FROM agent_collaboration WHERE handoff_id = ?",
            (handoff_id,),
        )
        row = cursor.fetchone()
        self.assertEqual(row[0], feature_id)

    def test_delegation_with_context(self) -> None:
        """Test recording delegation with additional context."""
        context_data = {
            "nesting_depth": 2,
            "prompt_preview": "Test prompt...",
            "custom_field": "custom_value",
        }

        handoff_id = self.db.record_delegation_event(
            from_agent="test-agent",
            to_agent="test-subagent",
            task_description="Task with context",
            session_id="sess-context-test",
            context=context_data,
        )

        # Verify context was stored
        self.assertIsNotNone(handoff_id)

        cursor = self.db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            "SELECT context FROM agent_collaboration WHERE handoff_id = ?",
            (handoff_id,),
        )
        row = cursor.fetchone()
        self.assertIsNotNone(row)

    def test_get_delegations_after_recording(self) -> None:
        """Test querying delegations after recording."""
        session_id = "sess-query-test"

        # Record multiple delegations
        self.db.record_delegation_event(
            from_agent="agent-a",
            to_agent="agent-b",
            task_description="Task A",
            session_id=session_id,
        )

        self.db.record_delegation_event(
            from_agent="agent-b",
            to_agent="agent-c",
            task_description="Task B",
            session_id=session_id,
        )

        # Query delegations
        delegations = self.db.get_delegations(session_id=session_id)

        # Verify results
        self.assertEqual(len(delegations), 2)
        self.assertEqual(delegations[0]["from_agent"], "agent-a")
        self.assertEqual(delegations[1]["from_agent"], "agent-b")


if __name__ == "__main__":
    unittest.main()
