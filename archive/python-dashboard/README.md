# Archived: Python FastAPI+HTMX Dashboard

This dashboard was replaced by the Phoenix LiveView dashboard in `packages/phoenix-dashboard/`.

## Why Archived

- Phoenix LiveView provided better real-time UX with less code
- The FastAPI+HTMX approach required significant tooling (18+ dependencies)
- The Phoenix dashboard is distributed as a Docker image

## Contents

- `api/` — FastAPI application (routes, services, WebSocket, HTMX templates)
- `fastapi_server.py` — Server startup/lifecycle operations module
- `dashboard.html` — Standalone HTMX dashboard HTML template

## To Restore

If needed, move `api/` back to `src/python/htmlgraph/api/` and `fastapi_server.py`
back to `src/python/htmlgraph/operations/fastapi_server.py`, then add the dashboard
dependencies back to `pyproject.toml` under `[project.optional-dependencies]`.
