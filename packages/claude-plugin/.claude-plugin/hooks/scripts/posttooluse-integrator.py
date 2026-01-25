#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
PostToolUse Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.posttooluse package module, which runs event tracking
and orchestrator reflection in parallel.

Performance: ~40-50% faster than previous subprocess-based approach.
"""

from htmlgraph.hooks.posttooluse import main

if __name__ == "__main__":
    main()
