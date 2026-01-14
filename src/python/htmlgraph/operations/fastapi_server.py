from __future__ import annotations

"""FastAPI-based server for HtmlGraph dashboard with real-time observability."""


import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from htmlgraph.mcp_server import _resolve_project_dir

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FastAPIServerHandle:
    """Handle to a running FastAPI server."""

    url: str
    port: int
    host: str
    server: Any | None = None


@dataclass(frozen=True)
class FastAPIServerStartResult:
    """Result of starting FastAPI server."""

    handle: FastAPIServerHandle
    warnings: list[str]
    config_used: dict[str, Any]


class FastAPIServerError(RuntimeError):
    """FastAPI server error."""

    pass


class PortInUseError(FastAPIServerError):
    """Requested port is already in use."""

    pass


def start_fastapi_server(
    *,
    port: int = 8000,
    host: str = "127.0.0.1",
    db_path: str | None = None,
    auto_port: bool = False,
    reload: bool = False,
) -> FastAPIServerStartResult:
    """
    Start FastAPI-based HtmlGraph dashboard server.

    Args:
        port: Port to listen on (default: 8000)
        host: Host to bind to (default: 127.0.0.1)
        db_path: Path to SQLite database file
        auto_port: Automatically find available port if in use
        reload: Enable auto-reload on file changes (development mode)

    Returns:
        FastAPIServerStartResult with handle, warnings, and config used

    Raises:
        PortInUseError: If port is in use and auto_port=False
        FastAPIServerError: If server fails to start
    """
    import uvicorn

    from htmlgraph.api.main import create_app

    warnings: list[str] = []
    original_port = port

    # Default database path - prefer project-local database if available
    if db_path is None:
        # Check for project-local database first
        project_dir = _resolve_project_dir()
        project_db = Path(project_dir) / ".htmlgraph" / "htmlgraph.db"
        if project_db.exists():
            db_path = str(project_db)  # Use project-local database
        else:
            db_path = str(
                Path.home() / ".htmlgraph" / "htmlgraph.db"
            )  # Fall back to home

    # Ensure database exists
    db_path_obj = Path(db_path)
    db_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Handle auto-port selection
    if auto_port and _check_port_in_use(port, host):
        port = _find_available_port(port + 1)
        warnings.append(f"Port {original_port} is in use, using {port} instead")

    # Check if port is in use
    if not auto_port and _check_port_in_use(port, host):
        raise PortInUseError(
            f"Port {port} is already in use. Use auto_port=True or choose a different port."
        )

    # Create FastAPI app
    app = create_app(db_path=db_path)

    # Create server config
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=reload,
        reload_dirs=None,  # Disable file watching for now
    )

    # Create server instance
    server = uvicorn.Server(config)

    # Create handle
    handle = FastAPIServerHandle(
        url=f"http://{host}:{port}",
        port=port,
        host=host,
        server=server,
    )

    # Configuration used
    config_used = {
        "port": port,
        "original_port": original_port,
        "host": host,
        "db_path": db_path,
        "auto_port": auto_port,
        "reload": reload,
    }

    return FastAPIServerStartResult(
        handle=handle,
        warnings=warnings,
        config_used=config_used,
    )


async def run_fastapi_server(handle: FastAPIServerHandle) -> None:
    """
    Run FastAPI server (async).

    Args:
        handle: FastAPIServerHandle from start_fastapi_server()

    Raises:
        FastAPIServerError: If server fails
    """
    if handle.server is None:
        raise FastAPIServerError("Invalid server handle")

    try:
        await handle.server.serve()
    except Exception as e:
        raise FastAPIServerError(f"Server error: {e}") from e


def stop_fastapi_server(handle: FastAPIServerHandle) -> None:
    """
    Stop FastAPI server.

    Args:
        handle: FastAPIServerHandle from start_fastapi_server()

    Raises:
        FastAPIServerError: If shutdown fails
    """
    if handle.server is None:
        return

    try:
        handle.server.should_exit = True
    except Exception as e:
        raise FastAPIServerError(f"Failed to stop server: {e}") from e


def _check_port_in_use(port: int, host: str = "localhost") -> bool:
    """
    Check if a port is already in use.

    Args:
        port: Port number to check
        host: Host to check on

    Returns:
        True if port is in use, False otherwise
    """
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return False
    except OSError:
        return True


def _find_available_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """
    Find an available port starting from start_port.

    Args:
        start_port: Port to start searching from
        max_attempts: Maximum number of ports to try

    Returns:
        Available port number

    Raises:
        FastAPIServerError: If no available port found
    """
    import socket

    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    raise FastAPIServerError(
        f"No available ports found in range {start_port}-{start_port + max_attempts}"
    )
