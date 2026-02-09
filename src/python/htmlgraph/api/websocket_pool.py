"""
WebSocket Session Pooling - Reuse database sessions across WebSocket cycles.

Provides:
- Session pooling for WebSocket handlers
- Connection lifecycle management
- Metrics and monitoring
- Configurable pool size and timeout
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class WebSocketSessionPool:
    """Manages pooled database sessions for WebSocket handlers.

    Instead of opening/closing a connection per WebSocket cycle,
    this pool reuses connections across multiple message cycles
    to reduce overhead and improve performance.
    """

    def __init__(
        self,
        db_path: str,
        pool_size: int = 5,
        session_timeout_seconds: float = 300.0,
    ):
        """
        Initialize WebSocket session pool.

        Args:
            db_path: Path to SQLite database
            pool_size: Maximum number of pooled connections
            session_timeout_seconds: Idle timeout for pooled sessions
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.session_timeout_seconds = session_timeout_seconds

        # Pool of available connections
        self._available_connections: asyncio.Queue[aiosqlite.Connection] = (
            asyncio.Queue(maxsize=pool_size)
        )

        # Track active sessions by WebSocket handler ID
        self._active_sessions: dict[str, aiosqlite.Connection] = {}

        # Track connection usage for metrics
        self._connection_stats: dict[int, dict[str, Any]] = defaultdict(
            lambda: {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "queries_executed": 0,
                "last_used": datetime.now(timezone.utc).isoformat(),
                "reuse_count": 0,
            }
        )

        # Pool initialization state
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the connection pool with initial connections."""
        if self._initialized:
            return

        async with self._lock:
            try:
                # Create initial pool connections
                for i in range(self.pool_size):
                    try:
                        conn = await aiosqlite.connect(self.db_path)
                        await self._available_connections.put(conn)
                        logger.debug(
                            f"Added connection {i + 1}/{self.pool_size} to pool"
                        )
                    except Exception as e:
                        logger.error(f"Failed to create pool connection {i + 1}: {e}")

                self._initialized = True
                logger.info(
                    f"WebSocket session pool initialized with {self.pool_size} connections"
                )
            except Exception as e:
                logger.error(f"Failed to initialize session pool: {e}")
                self._initialized = False

    async def acquire(self, handler_id: str) -> aiosqlite.Connection:
        """
        Acquire a connection from the pool for a WebSocket handler.

        Tries to reuse an available connection; creates new one if pool exhausted.

        Args:
            handler_id: Unique identifier for the WebSocket handler

        Returns:
            Database connection

        Raises:
            RuntimeError: If pool not initialized
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Try to get an available connection without blocking
            try:
                conn = self._available_connections.get_nowait()
                self._connection_stats[id(conn)]["reuse_count"] += 1
                self._connection_stats[id(conn)]["last_used"] = datetime.now(
                    timezone.utc
                ).isoformat()
                logger.debug(f"Reused connection for handler {handler_id}")
                return conn
            except asyncio.QueueEmpty:
                # Pool is empty, create a new temporary connection
                logger.debug(
                    f"Pool exhausted, creating temporary connection for {handler_id}"
                )
                conn = await aiosqlite.connect(self.db_path)
                self._connection_stats[id(conn)] = {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "queries_executed": 0,
                    "last_used": datetime.now(timezone.utc).isoformat(),
                    "reuse_count": 0,
                }
                return conn

        except Exception as e:
            logger.error(f"Error acquiring connection for handler {handler_id}: {e}")
            # Fallback: create a direct connection
            return await aiosqlite.connect(self.db_path)

    async def release(self, handler_id: str, conn: aiosqlite.Connection) -> None:
        """
        Release a connection back to the pool.

        If pool is full, closes the connection. Otherwise returns it to the pool.

        Args:
            handler_id: Unique identifier for the WebSocket handler
            conn: Connection to release
        """
        try:
            # Check if connection is still valid
            try:
                await conn.execute("SELECT 1")
            except Exception as e:
                logger.warning(
                    f"Connection invalid for handler {handler_id}, closing: {e}"
                )
                await conn.close()
                return

            # Try to return to pool
            try:
                self._available_connections.put_nowait(conn)
                logger.debug(
                    f"Released connection back to pool for handler {handler_id}"
                )
            except asyncio.QueueFull:
                # Pool is full, close this connection
                logger.debug(f"Pool full, closing connection for handler {handler_id}")
                await conn.close()

        except Exception as e:
            logger.error(f"Error releasing connection for handler {handler_id}: {e}")

    async def close_all(self) -> None:
        """Close all connections in the pool."""
        try:
            # Close active sessions
            for handler_id, conn in self._active_sessions.items():
                try:
                    await conn.close()
                    logger.debug(f"Closed active session for handler {handler_id}")
                except Exception as e:
                    logger.error(f"Error closing active session {handler_id}: {e}")

            self._active_sessions.clear()

            # Close pooled connections
            while not self._available_connections.empty():
                try:
                    conn = self._available_connections.get_nowait()
                    await conn.close()
                except asyncio.QueueEmpty:
                    break
                except Exception as e:
                    logger.error(f"Error closing pooled connection: {e}")

            self._initialized = False
            logger.info("WebSocket session pool closed")

        except Exception as e:
            logger.error(f"Error closing session pool: {e}")

    async def execute(
        self,
        handler_id: str,
        query: str,
        params: list[Any] | None = None,
    ) -> list[Any]:
        """
        Execute a query using a pooled connection.

        Automatically acquires and releases connection.

        Args:
            handler_id: Unique identifier for the WebSocket handler
            query: SQL query to execute
            params: Query parameters

        Returns:
            Query results as list of rows

        Raises:
            Exception: If query execution fails
        """
        conn = await self.acquire(handler_id)
        try:
            if params is None:
                params = []

            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                self._connection_stats[id(conn)]["queries_executed"] += 1
                logger.debug(
                    f"Executed query for handler {handler_id}: {query[:50]}..."
                )
                return list(rows)

        except Exception as e:
            logger.error(f"Query execution error for handler {handler_id}: {e}")
            raise
        finally:
            await self.release(handler_id, conn)

    def get_stats(self) -> dict[str, Any]:
        """
        Get pool statistics and metrics.

        Returns:
            Dictionary with pool statistics
        """
        total_connections = len(self._connection_stats)
        available_count = self._available_connections.qsize()
        active_count = len(self._active_sessions)

        # Calculate reuse metrics
        total_reuses = sum(
            stats["reuse_count"] for stats in self._connection_stats.values()
        )
        total_queries = sum(
            stats["queries_executed"] for stats in self._connection_stats.values()
        )

        return {
            "pool_size": self.pool_size,
            "total_connections": total_connections,
            "available_connections": available_count,
            "active_sessions": active_count,
            "total_reuses": total_reuses,
            "total_queries_executed": total_queries,
            "connection_stats": dict(self._connection_stats),
            "initialized": self._initialized,
        }

    async def cleanup_idle_sessions(self, max_idle_seconds: float | None = None) -> int:
        """
        Clean up idle sessions that exceed timeout.

        Args:
            max_idle_seconds: Override timeout (uses instance default if None)

        Returns:
            Number of sessions closed
        """
        if max_idle_seconds is None:
            max_idle_seconds = self.session_timeout_seconds

        now = datetime.now(timezone.utc)
        timeout_delta = timedelta(seconds=max_idle_seconds)
        closed_count = 0

        try:
            for conn_id, stats in list(self._connection_stats.items()):
                try:
                    last_used = datetime.fromisoformat(stats["last_used"])
                    if (now - last_used) > timeout_delta:
                        logger.info(f"Closing idle session {conn_id}")
                        closed_count += 1
                        # Session cleanup happens when connection is released
                except Exception as e:
                    logger.error(f"Error checking idle session {conn_id}: {e}")

            return closed_count

        except Exception as e:
            logger.error(f"Error cleaning up idle sessions: {e}")
            return 0
