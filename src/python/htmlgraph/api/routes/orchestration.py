"""
Orchestration routes for HtmlGraph API.

Handles:
- Delegation chains and agent handoffs
- Work items (features, bugs, spikes)
- Spawner activity and statistics
- Sessions API
"""

import json
import logging
import time
from typing import Any, cast

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi_cache.decorator import cache

from htmlgraph.api.cache import CACHE_TTL
from htmlgraph.api.dependencies import Dependencies

logger = logging.getLogger(__name__)

router = APIRouter()

# Templates and dependencies will be set by main.py
_templates: Jinja2Templates | None = None
_deps: Dependencies | None = None


def init_orchestration_routes(templates: Jinja2Templates, deps: Dependencies) -> None:
    """Initialize orchestration routes with templates and dependencies."""
    global _templates, _deps
    _templates = templates
    _deps = deps


def get_templates() -> Jinja2Templates:
    """Get templates instance, raising error if not initialized."""
    if _templates is None:
        raise RuntimeError("Orchestration routes not initialized.")
    return _templates


def get_deps() -> Dependencies:
    """Get dependencies instance, raising error if not initialized."""
    if _deps is None:
        raise RuntimeError("Orchestration routes not initialized.")
    return _deps


# ========== ORCHESTRATION ENDPOINTS ==========


@router.get("/views/orchestration", response_class=HTMLResponse)
async def orchestration_view(request: Request) -> HTMLResponse:
    """Get delegation chains and agent handoffs as HTMX partial."""
    deps = get_deps()
    templates = get_templates()
    db = await deps.get_db()
    try:
        query = """
            SELECT
                event_id,
                agent_id as from_agent,
                subagent_type as to_agent,
                timestamp,
                input_summary,
                session_id,
                status
            FROM agent_events
            WHERE tool_name = 'Task'
            ORDER BY datetime(REPLACE(SUBSTR(timestamp, 1, 19), 'T', ' ')) DESC
            LIMIT 50
        """

        async with db.execute(query) as cursor:
            rows = list(await cursor.fetchall())
        logger.debug(f"orchestration_view: Query executed, got {len(rows)} rows")

        delegations = []
        for row in rows:
            from_agent = row[1] or "unknown"
            to_agent = row[2]
            task_summary = row[4] or ""

            if not to_agent:
                try:
                    input_data = json.loads(task_summary) if task_summary else {}
                    to_agent = input_data.get("subagent_type", "unknown")
                except Exception:
                    to_agent = "unknown"

            delegation = {
                "event_id": row[0],
                "from_agent": from_agent,
                "to_agent": to_agent,
                "timestamp": row[3],
                "task": task_summary or "Unnamed task",
                "session_id": row[5],
                "status": row[6] or "pending",
                "result": "",
            }
            delegations.append(delegation)

        logger.debug(f"orchestration_view: Created {len(delegations)} delegation dicts")

        return templates.TemplateResponse(
            "partials/orchestration.html",
            {
                "request": request,
                "delegations": delegations,
            },
        )
    except Exception as e:
        logger.error(f"orchestration_view ERROR: {e}")
        raise
    finally:
        await db.close()


@router.get("/api/orchestration")
@cache(expire=CACHE_TTL["orchestration"])
async def orchestration_api() -> dict[str, Any]:
    """Get delegation chains and agent coordination information as JSON."""
    deps = get_deps()
    db = await deps.get_db()
    try:
        query = """
            SELECT
                event_id,
                agent_id as from_agent,
                subagent_type as to_agent,
                timestamp,
                input_summary,
                status
            FROM agent_events
            WHERE tool_name = 'Task'
            ORDER BY datetime(REPLACE(SUBSTR(timestamp, 1, 19), 'T', ' ')) DESC
            LIMIT 1000
        """

        cursor = await db.execute(query)
        rows = await cursor.fetchall()

        delegation_chains: dict[str, list[dict[str, Any]]] = {}
        agents = set()
        delegation_count = 0

        for row in rows:
            from_agent = row[1] or "unknown"
            to_agent = row[2]
            timestamp = row[3] or ""
            task_summary = row[4] or ""
            status = row[5] or "pending"

            if not to_agent:
                try:
                    input_data = json.loads(task_summary) if task_summary else {}
                    to_agent = input_data.get("subagent_type", "unknown")
                except Exception:
                    to_agent = "unknown"

            agents.add(from_agent)
            agents.add(to_agent)
            delegation_count += 1

            if from_agent not in delegation_chains:
                delegation_chains[from_agent] = []

            delegation_chains[from_agent].append(
                {
                    "to_agent": to_agent,
                    "event_type": "delegation",
                    "timestamp": timestamp,
                    "task": task_summary or "Unnamed task",
                    "status": status,
                }
            )

        return {
            "delegation_count": delegation_count,
            "unique_agents": len(agents),
            "agents": sorted(list(agents)),
            "delegation_chains": delegation_chains,
        }

    except Exception as e:
        logger.error(f"Failed to get orchestration data: {e}")
        raise
    finally:
        await db.close()


@router.get("/api/orchestration/delegations")
@cache(expire=CACHE_TTL["orchestration"])
async def orchestration_delegations_api() -> dict[str, Any]:
    """Get delegation statistics and chains as JSON."""
    deps = get_deps()
    db = await deps.get_db()
    cache = deps.query_cache
    query_start_time = time.time()

    try:
        cache_key = "orchestration_delegations:all"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            query_time_ms = (time.time() - query_start_time) * 1000
            cache.record_metric(cache_key, query_time_ms, cache_hit=True)
            logger.debug(
                f"Cache HIT for orchestration_delegations (key={cache_key}, "
                f"time={query_time_ms:.2f}ms)"
            )
            return cached_result  # type: ignore[no-any-return]

        exec_start = time.time()

        query = """
            SELECT
                event_id,
                agent_id as from_agent,
                subagent_type as to_agent,
                timestamp,
                input_summary,
                status
            FROM agent_events
            WHERE tool_name = 'Task'
            ORDER BY datetime(REPLACE(SUBSTR(timestamp, 1, 19), 'T', ' ')) DESC
            LIMIT 1000
        """

        cursor = await db.execute(query)
        rows = await cursor.fetchall()

        delegation_chains: dict[str, list[dict[str, Any]]] = {}
        agents = set()
        delegation_count = 0

        for row in rows:
            from_agent = row[1] or "unknown"
            to_agent = row[2]
            timestamp = row[3] or ""
            task_summary = row[4] or ""
            status = row[5] or "pending"

            if not to_agent:
                try:
                    input_data = json.loads(task_summary) if task_summary else {}
                    to_agent = input_data.get("subagent_type", "unknown")
                except Exception:
                    to_agent = "unknown"

            agents.add(from_agent)
            agents.add(to_agent)
            delegation_count += 1

            if from_agent not in delegation_chains:
                delegation_chains[from_agent] = []

            delegation_chains[from_agent].append(
                {
                    "to_agent": to_agent,
                    "timestamp": timestamp,
                    "task": task_summary or "Unnamed task",
                    "status": status,
                }
            )

        exec_time_ms = (time.time() - exec_start) * 1000

        result = {
            "delegation_count": delegation_count,
            "unique_agents": len(agents),
            "delegation_chains": delegation_chains,
        }

        cache.set(cache_key, result)
        query_time_ms = (time.time() - query_start_time) * 1000
        cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
        logger.debug(
            f"Cache MISS for orchestration_delegations (key={cache_key}, "
            f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms, "
            f"delegations={delegation_count})"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to get orchestration delegations: {e}")
        raise
    finally:
        await db.close()


@router.get("/api/orchestration/summary")
@cache(expire=CACHE_TTL.get("orchestration", 30))
async def get_orchestration_summary(
    session_id: str | None = None,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Get orchestration summary with tool usage and model detection."""
    deps = get_deps()
    db = await deps.get_db()

    try:
        _, orch_service, _ = deps.create_services(db)
        return cast(
            dict[str, Any],
            await orch_service.get_orchestration_summary(
                session_id=session_id, agent_id=agent_id
            ),
        )
    finally:
        await db.close()


@router.get("/api/orchestration/delegation-chain/{event_id}")
async def get_delegation_chain_endpoint(event_id: str) -> dict[str, Any]:
    """Trace delegation chain for a specific event."""
    deps = get_deps()
    db = await deps.get_db()

    try:
        _, orch_service, _ = deps.create_services(db)
        return cast(
            dict[str, Any],
            await orch_service.get_delegation_chain(root_event_id=event_id),
        )
    finally:
        await db.close()


# ========== WORK ITEMS ENDPOINTS ==========


@router.get("/views/features", response_class=HTMLResponse)
async def features_view_redirect(request: Request, status: str = "all") -> HTMLResponse:
    """Redirect to work-items view (legacy endpoint for backward compatibility)."""
    return await work_items_view(request, status)


@router.get("/views/work-items", response_class=HTMLResponse)
async def work_items_view(request: Request, status: str = "all") -> HTMLResponse:
    """Get work items (features, bugs, spikes) by status as HTMX partial."""
    deps = get_deps()
    templates = get_templates()
    db = await deps.get_db()
    cache = deps.query_cache
    query_start_time = time.time()

    try:
        cache_key = f"work_items_view:{status}"
        cached_response = cache.get(cache_key)
        work_items_by_status: dict = {
            "todo": [],
            "in_progress": [],
            "blocked": [],
            "done": [],
        }

        if cached_response is not None:
            query_time_ms = (time.time() - query_start_time) * 1000
            cache.record_metric(cache_key, query_time_ms, cache_hit=True)
            logger.debug(
                f"Cache HIT for work_items_view (key={cache_key}, time={query_time_ms:.2f}ms)"
            )
            work_items_by_status = cached_response
        else:
            query = """
                SELECT id, type, title, status, priority, assigned_to, created_at, updated_at, description
                FROM features
                WHERE 1=1
            """
            params: list = []

            if status != "all":
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY priority DESC, created_at DESC LIMIT 1000"

            exec_start = time.time()
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            agents_query = """
                SELECT feature_id, agent_id
                FROM agent_events
                WHERE feature_id IS NOT NULL
                GROUP BY feature_id, agent_id
            """
            agents_cursor = await db.execute(agents_query)
            agents_rows = await agents_cursor.fetchall()

            feature_agents: dict[str, list[str]] = {}
            for row in agents_rows:
                fid, aid = row[0], row[1]
                if fid not in feature_agents:
                    feature_agents[fid] = []
                feature_agents[fid].append(aid)

            exec_time_ms = (time.time() - exec_start) * 1000

            for row in rows:
                item_id = row[0]
                item_status = row[3]
                work_items_by_status.setdefault(item_status, []).append(
                    {
                        "id": item_id,
                        "type": row[1],
                        "title": row[2],
                        "status": item_status,
                        "priority": row[4],
                        "assigned_to": row[5],
                        "created_at": row[6],
                        "updated_at": row[7],
                        "description": row[8],
                        "contributors": feature_agents.get(item_id, []),
                    }
                )

            cache.set(cache_key, work_items_by_status)
            query_time_ms = (time.time() - query_start_time) * 1000
            cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
            logger.debug(
                f"Cache MISS for work_items_view (key={cache_key}, "
                f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms)"
            )

        return templates.TemplateResponse(
            "partials/work-items.html",
            {
                "request": request,
                "work_items_by_status": work_items_by_status,
            },
        )
    finally:
        await db.close()


# ========== SPAWNERS ENDPOINTS ==========


@router.get("/views/spawners", response_class=HTMLResponse)
async def spawners_view(request: Request) -> HTMLResponse:
    """Get spawner activity dashboard as HTMX partial."""
    deps = get_deps()
    templates = get_templates()
    db = await deps.get_db()
    try:
        stats_response = await get_spawner_statistics()
        spawner_stats = stats_response.get("spawner_statistics", [])

        activities_response = await get_spawner_activities(limit=50)
        recent_activities = activities_response.get("spawner_activities", [])

        return templates.TemplateResponse(
            "partials/spawners.html",
            {
                "request": request,
                "spawner_stats": spawner_stats,
                "recent_activities": recent_activities,
            },
        )
    except Exception as e:
        logger.error(f"spawners_view ERROR: {e}")
        return templates.TemplateResponse(
            "partials/spawners.html",
            {
                "request": request,
                "spawner_stats": [],
                "recent_activities": [],
            },
        )
    finally:
        await db.close()


@router.get("/api/spawner-activities")
async def get_spawner_activities(
    spawner_type: str | None = None,
    session_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Get spawner delegation activities with clear attribution."""
    deps = get_deps()
    db = await deps.get_db()
    cache = deps.query_cache
    query_start_time = time.time()

    try:
        cache_key = f"spawner_activities:{spawner_type or 'all'}:{session_id or 'all'}:{limit}:{offset}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            query_time_ms = (time.time() - query_start_time) * 1000
            cache.record_metric(cache_key, query_time_ms, cache_hit=True)
            return cached_result  # type: ignore[no-any-return]

        exec_start = time.time()

        query = """
            SELECT
                event_id,
                agent_id AS orchestrator_agent,
                subagent_type AS spawner_type,
                subagent_type AS spawned_agent,
                tool_name,
                input_summary AS task,
                output_summary AS result,
                status,
                execution_duration_seconds AS duration,
                cost_tokens AS tokens,
                cost_usd,
                child_spike_count AS artifacts,
                timestamp,
                created_at
            FROM agent_events
            WHERE subagent_type IS NOT NULL
        """

        params: list[Any] = []
        if spawner_type:
            query += " AND subagent_type = ?"
            params.append(spawner_type)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        query += " ORDER BY datetime(REPLACE(SUBSTR(timestamp, 1, 19), 'T', ' ')) DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        events = [
            dict(zip([c[0] for c in cursor.description], row))
            for row in await cursor.fetchall()
        ]

        count_query = (
            "SELECT COUNT(*) FROM agent_events WHERE subagent_type IS NOT NULL"
        )
        count_params: list[Any] = []
        if spawner_type:
            count_query += " AND subagent_type = ?"
            count_params.append(spawner_type)
        if session_id:
            count_query += " AND session_id = ?"
            count_params.append(session_id)

        count_cursor = await db.execute(count_query, count_params)
        count_row = await count_cursor.fetchone()
        total_count = int(count_row[0]) if count_row else 0

        exec_time_ms = (time.time() - exec_start) * 1000

        result = {
            "spawner_activities": events,
            "count": len(events),
            "total": total_count,
            "offset": offset,
            "limit": limit,
        }

        cache.set(cache_key, result)
        query_time_ms = (time.time() - query_start_time) * 1000
        cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
        logger.debug(
            f"Cache MISS for spawner_activities (key={cache_key}, "
            f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms, "
            f"activities={len(events)})"
        )

        return result
    finally:
        await db.close()


@router.get("/api/spawner-statistics")
async def get_spawner_statistics(session_id: str | None = None) -> dict[str, Any]:
    """Get aggregated statistics for each spawner type."""
    deps = get_deps()
    db = await deps.get_db()
    cache = deps.query_cache
    query_start_time = time.time()

    try:
        cache_key = f"spawner_statistics:{session_id or 'all'}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            query_time_ms = (time.time() - query_start_time) * 1000
            cache.record_metric(cache_key, query_time_ms, cache_hit=True)
            return cached_result  # type: ignore[no-any-return]

        exec_start = time.time()

        query = """
            SELECT
                subagent_type AS spawner_type,
                COUNT(*) as total_delegations,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate,
                ROUND(AVG(execution_duration_seconds), 2) as avg_duration,
                SUM(cost_tokens) as total_tokens,
                ROUND(SUM(cost_usd), 2) as total_cost,
                MIN(timestamp) as first_used,
                MAX(timestamp) as last_used
            FROM agent_events
            WHERE subagent_type IS NOT NULL
        """

        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        query += " GROUP BY subagent_type ORDER BY total_delegations DESC"

        cursor = await db.execute(query, params)
        stats = [
            dict(zip([c[0] for c in cursor.description], row))
            for row in await cursor.fetchall()
        ]

        exec_time_ms = (time.time() - exec_start) * 1000

        result = {"spawner_statistics": stats}

        cache.set(cache_key, result)
        query_time_ms = (time.time() - query_start_time) * 1000
        cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
        logger.debug(
            f"Cache MISS for spawner_statistics (key={cache_key}, "
            f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms)"
        )

        return result
    finally:
        await db.close()


# ========== SESSIONS API ENDPOINT ==========


@router.get("/api/sessions")
@cache(expire=CACHE_TTL["sessions"])
async def get_sessions(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Get sessions from the database."""
    deps = get_deps()
    db = await deps.get_db()
    cache = deps.query_cache
    query_start_time = time.time()

    try:
        cache_key = f"api_sessions:{status or 'all'}:{limit}:{offset}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            query_time_ms = (time.time() - query_start_time) * 1000
            cache.record_metric(cache_key, query_time_ms, cache_hit=True)
            logger.debug(
                f"Cache HIT for api_sessions (key={cache_key}, time={query_time_ms:.2f}ms)"
            )
            return cached_result  # type: ignore[no-any-return]

        exec_start = time.time()

        query = """
            SELECT
                session_id,
                agent_assigned,
                continued_from,
                created_at,
                status,
                start_commit,
                completed_at
            FROM sessions
            WHERE 1=1
        """
        params: list[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        count_query = "SELECT COUNT(*) FROM sessions WHERE 1=1"
        count_params: list[Any] = []
        if status:
            count_query += " AND status = ?"
            count_params.append(status)

        async with db.execute(count_query, count_params) as count_cursor:
            count_row = await count_cursor.fetchone()
        total = int(count_row[0]) if count_row else 0

        sessions = []
        for row in rows:
            sessions.append(
                {
                    "session_id": row[0],
                    "agent": row[1],
                    "continued_from": row[2],
                    "created_at": row[3],
                    "status": row[4] or "unknown",
                    "start_commit": row[5],
                    "completed_at": row[6],
                }
            )

        exec_time_ms = (time.time() - exec_start) * 1000

        result = {
            "total": total,
            "limit": limit,
            "offset": offset,
            "sessions": sessions,
        }

        cache.set(cache_key, result)
        query_time_ms = (time.time() - query_start_time) * 1000
        cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
        logger.debug(
            f"Cache MISS for api_sessions (key={cache_key}, "
            f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms, "
            f"sessions={len(sessions)})"
        )

        return result

    finally:
        await db.close()


@router.get("/api/subagent-work/{session_id}")
@cache(expire=CACHE_TTL.get("events", 30))
async def get_subagent_work(session_id: str) -> dict[str, Any]:
    """Get all work performed by subagents in a session."""
    deps = get_deps()
    db = await deps.get_db()
    cache = deps.query_cache
    query_start_time = time.time()

    try:
        cache_key = f"subagent_work:{session_id}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            query_time_ms = (time.time() - query_start_time) * 1000
            cache.record_metric(cache_key, query_time_ms, cache_hit=True)
            logger.debug(
                f"Cache HIT for subagent_work (key={cache_key}, time={query_time_ms:.2f}ms)"
            )
            return cached_result  # type: ignore[no-any-return]

        exec_start = time.time()

        # Query all events from subagents in this session
        query = """
            SELECT
                event_id,
                agent_id,
                subagent_type,
                tool_name,
                timestamp,
                status,
                parent_event_id,
                input_summary,
                output_summary
            FROM agent_events
            WHERE session_id = ? AND subagent_type IS NOT NULL
            ORDER BY datetime(REPLACE(SUBSTR(timestamp, 1, 19), 'T', ' ')) DESC
        """

        cursor = await db.execute(query, (session_id,))
        rows = await cursor.fetchall()

        # Group events by subagent_type
        subagents: dict[str, dict[str, Any]] = {}

        for row in rows:
            event_id = row[0]
            agent_id = row[1]
            subagent_type = row[2]
            tool_name = row[3]
            timestamp = row[4]
            status = row[5]
            parent_event_id = row[6]
            input_summary = row[7]
            output_summary = row[8]

            # Initialize subagent entry if not exists
            if subagent_type not in subagents:
                subagents[subagent_type] = {
                    "subagent_type": subagent_type,
                    "event_count": 0,
                    "tools_used": [],
                    "started_at": timestamp,
                    "completed_at": timestamp,
                    "parent_event_id": parent_event_id,
                    "events": [],
                }

            # Update subagent stats
            subagent_entry = subagents[subagent_type]
            subagent_entry["event_count"] += 1
            if tool_name and tool_name not in subagent_entry["tools_used"]:
                subagent_entry["tools_used"].append(tool_name)

            # Update time range
            if timestamp < subagent_entry["started_at"]:
                subagent_entry["started_at"] = timestamp
            if timestamp > subagent_entry["completed_at"]:
                subagent_entry["completed_at"] = timestamp

            # Add event details
            subagent_entry["events"].append(
                {
                    "event_id": event_id,
                    "agent_id": agent_id,
                    "tool_name": tool_name,
                    "timestamp": timestamp,
                    "status": status,
                    "input_summary": input_summary,
                    "output_summary": output_summary,
                }
            )

        exec_time_ms = (time.time() - exec_start) * 1000

        result = {
            "session_id": session_id,
            "subagent_count": len(subagents),
            "subagents": list(subagents.values()),
        }

        cache.set(cache_key, result)
        query_time_ms = (time.time() - query_start_time) * 1000
        cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
        logger.debug(
            f"Cache MISS for subagent_work (key={cache_key}, "
            f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms, "
            f"subagents={len(subagents)})"
        )

        return result

    finally:
        await db.close()
