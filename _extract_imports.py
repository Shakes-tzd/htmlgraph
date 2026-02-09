"""
HtmlGraph FastAPI Backend - Real-time Agent Observability Dashboard

Provides REST API and WebSocket support for viewing:
- Agent activity feed with real-time event streaming
- Orchestration chains and delegation handoffs
- Feature tracker with Kanban views
- Session metrics and performance analytics

Architecture:
- FastAPI backend querying SQLite database
- Jinja2 templates for server-side rendering
- HTMX for interactive UI without page reloads
- WebSocket for real-time event streaming
"""

import asyncio
import json
import logging
import random
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_cache2.decorator import cache
from pydantic import BaseModel

from htmlgraph.api.cache import (
    CACHE_TTL,
    QueryCache,
    init_cache_backend,
)
from htmlgraph.api.services import (