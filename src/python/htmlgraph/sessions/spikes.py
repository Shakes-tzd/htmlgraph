"""
Spike management - auto-generated spikes for session transitions.

Extracted from session_manager.py to improve modularity.
Handles session-init, transition, and conversation-init spikes.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.converter import NodeConverter, SessionConverter
from htmlgraph.ids import generate_id
from htmlgraph.models import Node, Session
from htmlgraph.spike_index import ActiveAutoSpikeIndex

logger = logging.getLogger(__name__)


class SpikeManager:
    """Manages auto-generated spikes for session transitions."""

    def __init__(
        self,
        graph_dir: Path,
        session_converter: SessionConverter,
        spike_index: ActiveAutoSpikeIndex,
        active_auto_spikes: set[str],
    ):
        self.graph_dir = graph_dir
        self.session_converter = session_converter
        self._spike_index = spike_index
        self._active_auto_spikes = active_auto_spikes

    def _get_spike_converter(self) -> NodeConverter:
        """Get a NodeConverter for the spikes directory."""
        return NodeConverter(self.graph_dir / "spikes")

    def get_active_auto_spike(self, active_features: list[Node]) -> Node | None:
        """
        Find an active auto-generated spike (session-init, conversation-init, or transition).

        Auto-spikes take precedence over regular features for attribution
        since they're specifically designed to catch transitional activities.

        Returns:
            Active auto-spike or None
        """
        for feature in active_features:
            if (
                feature.type == "spike"
                and feature.auto_generated
                and feature.spike_subtype
                in ("session-init", "conversation-init", "transition")
                and feature.status == "in-progress"
            ):
                return feature
        return None

    def create_session_init_spike(self, session: Session) -> Node | None:
        """
        Auto-create a session-init spike to catch pre-feature activities.

        This spike captures work done before the first feature is started:
        - Session startup, reviewing context
        - Planning what to work on
        - General exploration

        The spike auto-completes when the first feature is started.
        """
        spike_id = f"spike-init-{session.id[:8]}"
        spike_converter = self._get_spike_converter()

        # Check if spike already exists (idempotency)
        existing = spike_converter.load(spike_id)
        if existing:
            # Add to index if it's still active
            if existing.status == "in-progress":
                self._active_auto_spikes.add(existing.id)
                self._spike_index.add(existing.id, "session-init", session.id)
            return existing

        # Create session-init spike
        spike = Node(
            id=spike_id,
            title=f"Session Init: {session.agent}",
            type="spike",
            status="in-progress",
            priority="low",
            spike_subtype="session-init",
            auto_generated=True,
            session_id=session.id,
            model_name=session.agent,
            content=(
                "Auto-generated spike for session startup activities.\n\n"
                "Captures work before first feature is started:\n"
                "- Context review\n- Planning\n- Exploration\n\n"
                "Auto-completes when first feature is claimed."
            ),
        )

        spike_converter.save(spike)

        # Add to active auto-spikes index (both in-memory and persistent)
        self._active_auto_spikes.add(spike.id)
        self._spike_index.add(spike.id, "session-init", session.id)

        # Link session to spike
        if spike.id not in session.worked_on:
            session.worked_on.append(spike.id)
            self.session_converter.save(session)

        return spike

    def create_transition_spike(
        self, session: Session, from_feature_id: str
    ) -> Node | None:
        """
        Auto-create a transition spike after feature completion.

        This spike captures work done between features:
        - Post-completion cleanup
        - Review and planning
        - Context switching

        The spike auto-completes when the next feature is started.
        """
        spike_id = generate_id(node_type="spike", title="transition")
        spike_converter = self._get_spike_converter()

        spike = Node(
            id=spike_id,
            title=f"Transition from {from_feature_id[:12]}",
            type="spike",
            status="in-progress",
            priority="low",
            spike_subtype="transition",
            auto_generated=True,
            session_id=session.id,
            from_feature_id=from_feature_id,
            model_name=session.agent,
            content=(
                f"Auto-generated transition spike.\n\n"
                f"Captures post-completion activities:\n"
                f"- Cleanup and review\n- Planning next work\n- Context switching\n\n"
                f"From: {from_feature_id}\n"
                f"Auto-completes when next feature is started."
            ),
        )

        spike_converter.save(spike)

        # Add to active auto-spikes index (both in-memory and persistent)
        self._active_auto_spikes.add(spike.id)
        self._spike_index.add(spike.id, "transition", session.id)

        # Link session to spike
        if spike.id not in session.worked_on:
            session.worked_on.append(spike.id)
            self.session_converter.save(session)

        return spike

    def complete_transition_spikes_on_conversation_start(
        self, agent: str
    ) -> list[Node]:
        """
        Complete transition spikes from previous conversations when a new conversation starts.

        Args:
            agent: Agent starting the new conversation

        Returns:
            List of completed transition spikes
        """
        spike_converter = self._get_spike_converter()
        completed_spikes = []

        # Complete only TRANSITION spikes (not session-init, which should persist)
        for spike_id in list(self._active_auto_spikes):
            spike = spike_converter.load(spike_id)

            if not spike:
                self._active_auto_spikes.discard(spike_id)
                self._spike_index.remove(spike_id)
                continue

            # Only complete transition spikes on conversation start
            if not (
                spike.type == "spike"
                and getattr(spike, "auto_generated", False)
                and getattr(spike, "spike_subtype", None) == "transition"
                and spike.status == "in-progress"
            ):
                continue

            # Complete the transition spike
            spike.status = "done"
            spike.updated = datetime.now()
            spike.properties["completed_by"] = "conversation-start"

            spike_converter.save(spike)
            completed_spikes.append(spike)
            self._active_auto_spikes.discard(spike_id)
            self._spike_index.remove(spike_id)

            logger.debug(f"Completed transition spike {spike_id} on conversation start")

        return completed_spikes

    def complete_active_auto_spikes(
        self,
        agent: str,
        to_feature_id: str,
        get_active_session: Any,
        import_transcript_events: Any,
    ) -> list[Node]:
        """
        Auto-complete any active auto-generated spikes when a feature starts.

        When starting a regular feature, the transitional period is over,
        so we complete session-init and transition spikes.

        Args:
            agent: Agent starting the feature
            to_feature_id: Feature being started
            get_active_session: Callable to get active session for agent
            import_transcript_events: Callable to import transcript events

        Returns:
            List of completed spikes
        """
        spike_converter = self._get_spike_converter()
        completed_spikes = []

        for spike_id in list(self._active_auto_spikes):
            spike = spike_converter.load(spike_id)

            if not spike:
                self._active_auto_spikes.discard(spike_id)
                self._spike_index.remove(spike_id)
                continue

            if not (
                spike.type == "spike"
                and spike.auto_generated
                and spike.spike_subtype
                in ("session-init", "transition", "conversation-init")
                and spike.status == "in-progress"
            ):
                self._active_auto_spikes.discard(spike_id)
                self._spike_index.remove(spike_id)
                continue

            # Complete the spike
            spike.status = "done"
            spike.updated = datetime.now()
            spike.to_feature_id = to_feature_id

            spike_converter.save(spike)
            completed_spikes.append(spike)

            self._active_auto_spikes.discard(spike_id)
            self._spike_index.remove(spike_id)

        # Import transcript when auto-spikes complete (work boundary)
        if completed_spikes:
            session = get_active_session(agent=agent)
            if session and session.transcript_id:
                try:
                    from htmlgraph.transcript import TranscriptReader

                    reader = TranscriptReader()
                    transcript = reader.read_session(session.transcript_id)
                    if transcript:
                        import_transcript_events(
                            session_id=session.id,
                            transcript_session=transcript,
                            overwrite=True,
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to import transcript events on auto-spike completion: {e}"
                    )

        return completed_spikes
