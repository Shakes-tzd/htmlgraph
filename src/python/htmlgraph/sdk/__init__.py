"""
HtmlGraph SDK - Modular Architecture

This package provides a fluent, ergonomic API for AI agents with:
- Auto-discovery of .htmlgraph directory
- Method chaining for all operations
- Context managers for auto-save
- Batch operations
- Minimal boilerplate

The SDK is organized into modules:
- core: Main SDK class with all functionality
- base: Core BaseSDK class with initialization and lifecycle
- discovery: Project root and agent detection
- constants: Configuration and default values (Pydantic-based)

Public API exports maintain backward compatibility.
All existing imports continue to work:
    from htmlgraph import SDK  # Still works
    from htmlgraph.sdk import SDK  # Also works (direct export)
"""

from __future__ import annotations

from htmlgraph.sdk.base import BaseSDK
from htmlgraph.sdk.constants import SDKSettings

# Direct import of SDK from core module - no lazy loading needed
from htmlgraph.sdk.core import SDK
from htmlgraph.sdk.discovery import (
    auto_discover_agent,
    discover_htmlgraph_dir,
    find_project_root,
)

__all__ = [
    # Core SDK class (direct export from core.py)
    "SDK",
    "BaseSDK",
    # Discovery utilities
    "find_project_root",
    "discover_htmlgraph_dir",
    "auto_discover_agent",
    # Constants and configuration
    "SDKSettings",
]
