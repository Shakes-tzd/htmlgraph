"""
Cross-Agent Presence Tracking - Phase 1

Real-time visibility of which agents are active, what they're working on,
and their recent activity. Foundation for multi-AI coordination observability.

Features:
- Track agent status (active, idle, offline)
- Monitor current feature each agent is working on
- Display last tool executed
- <500ms latency from activity to UI update
- WebSocket broadcasting for real-time updates

Architecture:
- AgentPresence: Data model for agent state
- PresenceManager: In-memory presence tracking with persistence
- Integrates with event pipeline for automatic updates
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PresenceStatus(str, Enum):
    """Agent presence status."""

    ACTIVE = "active"
    IDLE = "idle"
    OFFLINE = "offline"


@dataclass
class AgentPresence:
    """
    Agent presence state.

    Tracks real-time information about an agent's activity:
    - Current status (active/idle/offline)
    - Feature being worked on
    - Last tool executed
    - Activity metrics
    """

    agent_id: str
    status: PresenceStatus = PresenceStatus.OFFLINE
    current_feature_id: str | None = None
    last_tool_name: str | None = None
    last_activity: datetime = field(default_factory=datetime.now)
    total_tools_executed: int = 0
    total_cost_tokens: int = 0
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "current_feature_id": self.current_feature_id,
            "last_tool_name": self.last_tool_name,
            "last_activity": self.last_activity.isoformat(),
            "total_tools_executed": self.total_tools_executed,
            "total_cost_tokens": self.total_cost_tokens,
            "session_id": self.session_id,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AgentPresence":
        """Create AgentPresence from dictionary."""
        return AgentPresence(
            agent_id=data["agent_id"],
            status=PresenceStatus(data.get("status", "offline")),
            current_feature_id=data.get("current_feature_id"),
            last_tool_name=data.get("last_tool_name"),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            total_tools_executed=data.get("total_tools_executed", 0),
            total_cost_tokens=data.get("total_cost_tokens", 0),
            session_id=data.get("session_id"),
        )


class PresenceManager:
    """
    Manages agent presence tracking.

    Features:
    - In-memory state for fast access
    - Periodic persistence to database
    - Idle detection based on inactivity
    - Real-time updates via WebSocket
    """

    def __init__(self, db_path: str | None = None, idle_timeout_seconds: int = 300):
        """
        Initialize presence manager.

        Args:
            db_path: Path to SQLite database for persistence
            idle_timeout_seconds: Seconds of inactivity before marking idle (default: 5 minutes)
        """
        self.db_path = db_path
        self.idle_timeout_seconds = idle_timeout_seconds

        # In-memory presence state: {agent_id: AgentPresence}
        self.agents: dict[str, AgentPresence] = {}

        # Ensure schema exists before loading
        if self.db_path:
            self._ensure_schema()

        # Load persisted state if available
        self._load_from_db()

    def update_presence(
        self,
        agent_id: str,
        event: dict[str, Any],
        websocket_manager: Any | None = None,
    ) -> AgentPresence:
        """
        Update agent presence based on event.

        Args:
            agent_id: Agent identifier
            event: Event data (tool_call, completion, error)
            websocket_manager: WebSocket manager for broadcasting updates

        Returns:
            Updated AgentPresence
        """
        # Get or create presence
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentPresence(agent_id=agent_id)

        presence = self.agents[agent_id]

        # Update fields
        presence.status = PresenceStatus.ACTIVE
        presence.last_activity = datetime.now()

        # Extract tool name
        if tool_name := event.get("tool_name"):
            presence.last_tool_name = tool_name

        # Extract feature
        if feature_id := event.get("feature_id"):
            presence.current_feature_id = feature_id

        # Extract session
        if session_id := event.get("session_id"):
            presence.session_id = session_id

        # Update metrics
        if cost_tokens := event.get("cost_tokens"):
            presence.total_cost_tokens += cost_tokens

        presence.total_tools_executed += 1

        # Persist to database
        self._save_to_db(agent_id)

        # Broadcast update via WebSocket if manager provided
        if websocket_manager:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule broadcast as task
                    asyncio.create_task(
                        self._broadcast_update(websocket_manager, presence)
                    )
            except RuntimeError:
                # No event loop - skip broadcast
                pass

        return presence

    async def _broadcast_update(
        self, websocket_manager: Any, presence: AgentPresence
    ) -> None:
        """Broadcast presence update via WebSocket."""
        try:
            await websocket_manager.broadcast_to_all_sessions(
                {
                    "type": "presence_update",
                    "event_type": "presence_update",
                    "agent_id": presence.agent_id,
                    "presence": presence.to_dict(),
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Error broadcasting presence update: {e}")

    def mark_idle(self, agent_id: str | None = None) -> list[str]:
        """
        Mark agents as idle if no activity for idle_timeout_seconds.

        Args:
            agent_id: Specific agent to check, or None to check all

        Returns:
            List of agent IDs marked as idle
        """
        marked_idle = []
        agents_to_check = [agent_id] if agent_id else list(self.agents.keys())

        for aid in agents_to_check:
            if aid not in self.agents:
                continue

            presence = self.agents[aid]
            elapsed = (datetime.now() - presence.last_activity).total_seconds()

            if (
                elapsed > self.idle_timeout_seconds
                and presence.status != PresenceStatus.IDLE
            ):
                presence.status = PresenceStatus.IDLE
                marked_idle.append(aid)
                self._save_to_db(aid)

        return marked_idle

    def mark_offline(self, agent_id: str) -> bool:
        """
        Mark agent as offline.

        Args:
            agent_id: Agent to mark offline

        Returns:
            True if agent was marked offline, False if not found
        """
        if agent_id not in self.agents:
            return False

        self.agents[agent_id].status = PresenceStatus.OFFLINE
        self._save_to_db(agent_id)
        return True

    def get_all_presence(self) -> list[AgentPresence]:
        """
        Get presence info for all agents.

        Returns:
            List of AgentPresence objects
        """
        # Mark idle agents before returning
        self.mark_idle()
        return list(self.agents.values())

    def get_agent_presence(self, agent_id: str) -> AgentPresence | None:
        """
        Get presence info for specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentPresence or None if not found
        """
        # Check if idle before returning
        self.mark_idle(agent_id)
        return self.agents.get(agent_id)

    def _ensure_schema(self) -> None:
        """Ensure database schema exists."""
        if not self.db_path:
            return

        try:
            import sqlite3

            db_path = Path(self.db_path)
            if not db_path.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check if table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_presence'"
            )
            if not cursor.fetchone():
                conn.close()
                # Initialize schema using HtmlGraphDB
                try:
                    from htmlgraph.db.schema import HtmlGraphDB

                    db = HtmlGraphDB(str(db_path))
                    db.create_tables()
                    db.disconnect()
                except Exception as e:
                    logger.debug(f"Could not create schema: {e}")
            else:
                conn.close()

        except Exception as e:
            logger.warning(f"Could not ensure schema: {e}")

    def _load_from_db(self) -> None:
        """Load presence state from database."""
        if not self.db_path:
            return

        try:
            import sqlite3

            db_path = Path(self.db_path)
            if not db_path.exists():
                return

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check if table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_presence'"
            )
            if not cursor.fetchone():
                conn.close()
                return

            # Load all presence records
            cursor.execute(
                """
                SELECT agent_id, status, current_feature_id, last_tool_name,
                       last_activity, total_tools_executed, total_cost_tokens,
                       session_id
                FROM agent_presence
            """
            )

            rows = cursor.fetchall()
            for row in rows:
                try:
                    presence = AgentPresence(
                        agent_id=row[0],
                        status=PresenceStatus(row[1]),
                        current_feature_id=row[2],
                        last_tool_name=row[3],
                        last_activity=datetime.fromisoformat(row[4]),
                        total_tools_executed=row[5] or 0,
                        total_cost_tokens=row[6] or 0,
                        session_id=row[7],
                    )
                    self.agents[presence.agent_id] = presence
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error loading presence for {row[0]}: {e}")

            conn.close()
            if rows:
                logger.info(
                    f"Loaded {len(self.agents)} agent presence records from database"
                )

        except Exception as e:
            logger.warning(f"Could not load presence from database: {e}")

    def _save_to_db(self, agent_id: str) -> None:
        """Save presence state to database."""
        if not self.db_path or agent_id not in self.agents:
            return

        try:
            import sqlite3

            presence = self.agents[agent_id]

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Ensure table exists (will be created by schema.py, but check anyway)
            cursor.execute(
                """
                INSERT OR REPLACE INTO agent_presence
                (agent_id, status, current_feature_id, last_tool_name,
                 last_activity, total_tools_executed, total_cost_tokens,
                 session_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    presence.agent_id,
                    presence.status.value,
                    presence.current_feature_id,
                    presence.last_tool_name,
                    presence.last_activity.isoformat(),
                    presence.total_tools_executed,
                    presence.total_cost_tokens,
                    presence.session_id,
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.debug(f"Could not save presence to database: {e}")

    def cleanup_stale_agents(self, max_age_hours: int = 24) -> list[str]:
        """
        Remove agents that haven't been active for max_age_hours.

        Args:
            max_age_hours: Maximum age in hours before removal

        Returns:
            List of removed agent IDs
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        removed = []

        for agent_id, presence in list(self.agents.items()):
            if presence.last_activity < cutoff:
                del self.agents[agent_id]
                removed.append(agent_id)

                # Remove from database too
                if self.db_path:
                    try:
                        import sqlite3

                        conn = sqlite3.connect(str(self.db_path))
                        cursor = conn.cursor()
                        cursor.execute(
                            "DELETE FROM agent_presence WHERE agent_id = ?",
                            (agent_id,),
                        )
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        logger.debug(f"Could not remove {agent_id} from database: {e}")

        if removed:
            logger.info(f"Cleaned up {len(removed)} stale agent presence records")

        return removed
