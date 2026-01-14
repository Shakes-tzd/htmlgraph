"""
HtmlGraph SDK - Modular Architecture

This package provides a fluent, ergonomic API for AI agents with:
- Auto-discovery of .htmlgraph directory
- Method chaining for all operations
- Context managers for auto-save
- Batch operations
- Minimal boilerplate

The SDK is organized into modules:
- base: Core BaseSDK class with initialization and lifecycle
- discovery: Project root and agent detection
- constants: Configuration and default values (Pydantic-based)

Public API exports maintain backward compatibility.
All existing imports continue to work:
    from htmlgraph import SDK  # Still works
    from htmlgraph.sdk import SDK  # Also works (via re-export)

Phase 1 Complete - Critical Path:
- BaseSDK core class extracted to sdk/base.py
- Discovery utilities in sdk/discovery.py
- Constants with Pydantic in sdk/constants.py
- Public API re-exports below for backward compatibility
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from htmlgraph.sdk.base import BaseSDK
from htmlgraph.sdk.constants import SDKSettings
from htmlgraph.sdk.discovery import (
    auto_discover_agent,
    discover_htmlgraph_dir,
    find_project_root,
)

# Type-only import of SDK for static analysis
# At runtime, SDK is lazy-loaded via __getattr__ to avoid circular imports
if TYPE_CHECKING:
    # Import from htmlgraph package - mypy uses the .pyi stub file
    # which properly declares the SDK class with all attributes
    from htmlgraph import SDK as SDK


def __getattr__(name: str) -> type:
    """Lazy-load SDK class to avoid circular imports."""
    if name == "SDK":
        # Import SDK only when accessed, not at module load time
        # This breaks the circular dependency with sdk.py
        from htmlgraph import SDK as _SDK

        return _SDK
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Core SDK class (lazy-loaded via __getattr__ to avoid circular imports)
    "SDK",
    "BaseSDK",
    # Discovery utilities
    "find_project_root",
    "discover_htmlgraph_dir",
    "auto_discover_agent",
    # Constants and configuration
    "SDKSettings",
]
