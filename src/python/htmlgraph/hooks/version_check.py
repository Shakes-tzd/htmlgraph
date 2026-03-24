"""Hook version validation — warns when uv cache is stale."""

from __future__ import annotations

import sys


def check_pypi_version(package: str = "htmlgraph", ttl_hours: int = 24) -> str | None:
    """Check if a newer version is available on PyPI.

    Returns the latest version string if newer than installed, else None.
    Caches result at ~/.cache/htmlgraph/update-check.json with TTL.
    Returns None on any error (network, parse, etc.) — never blocks.
    """
    import json
    import time
    import urllib.request
    from importlib.metadata import version as get_version
    from pathlib import Path

    cache_file = Path.home() / ".cache" / "htmlgraph" / "update-check.json"

    # Check cache first
    try:
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            if time.time() - data.get("checked_at", 0) < ttl_hours * 3600:
                latest = data.get("latest_version")
                installed = get_version(package)
                if latest and _version_tuple(str(latest)) > _version_tuple(installed):
                    return str(latest)
                return None
    except Exception:
        pass

    # Query PyPI
    try:
        url = f"https://pypi.org/pypi/{package}/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            latest = json.loads(resp.read())["info"]["version"]

        # Update cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(
                {
                    "latest_version": latest,
                    "checked_at": time.time(),
                }
            )
        )

        installed = get_version(package)
        if _version_tuple(str(latest)) > _version_tuple(installed):
            return str(latest)
    except Exception:
        pass

    return None


def _version_tuple(version: str) -> tuple[int, ...]:
    """Convert version string to comparable tuple."""
    try:
        return tuple(int(x) for x in version.split(".")[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def check_hook_version(required: str) -> None:
    """Check that installed htmlgraph meets the minimum version requirement.

    Prints a warning to stderr if the installed version is older than
    ``required``. Uses simple tuple comparison to avoid needing the
    ``packaging`` library.

    Args:
        required: Minimum version string, e.g. "0.34.14"
    """
    try:
        from importlib.metadata import version as get_version

        installed = get_version("htmlgraph")
        # Simple tuple comparison works for our MAJOR.MINOR.PATCH scheme
        inst_parts = tuple(int(x) for x in installed.split(".")[:3])
        req_parts = tuple(int(x) for x in required.split(".")[:3])
        if inst_parts < req_parts:
            print(
                f"WARNING: Stale hook cache: htmlgraph {installed} < {required}. "
                f"Run: uv cache clean htmlgraph && restart Claude Code",
                file=sys.stderr,
            )
    except Exception:
        pass  # Never break hook execution over version checking
