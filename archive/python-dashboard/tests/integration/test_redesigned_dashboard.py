#!/usr/bin/env python3
"""
Temporary script to test the redesigned dashboard UI.
This adds a /redesign route to serve the redesigned dashboard.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "python"))

from fastapi import Request
from fastapi.responses import HTMLResponse
from htmlgraph.api.main import create_app

# Create app
app = create_app()

# Get templates
from fastapi.templating import Jinja2Templates

template_dir = (
    Path(__file__).parent / "src" / "python" / "htmlgraph" / "api" / "templates"
)
templates = Jinja2Templates(directory=str(template_dir))


@app.get("/redesign", response_class=HTMLResponse)
async def dashboard_redesign(request: Request) -> HTMLResponse:
    """Serve the redesigned dashboard."""
    return templates.TemplateResponse(
        "dashboard-redesign.html",
        {
            "request": request,
            "title": "HtmlGraph Dashboard - Redesigned",
        },
    )


if __name__ == "__main__":
    import uvicorn

    print(
        "Starting test server with redesigned dashboard at http://localhost:8000/redesign"
    )
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
