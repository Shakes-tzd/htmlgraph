#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
PreToolUse Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.pretooluse package module, which runs orchestrator
enforcement and work validation in parallel.

Performance: ~40-50% faster than previous subprocess-based approach.
"""

from htmlgraph.hooks.pretooluse import main

if __name__ == "__main__":
    main()
