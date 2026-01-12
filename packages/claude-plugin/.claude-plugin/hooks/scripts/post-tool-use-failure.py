#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
PostToolUseFailure Hook - Automatic Error Tracking

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.post_tool_use_failure package module.
"""

from htmlgraph.hooks.post_tool_use_failure import main

if __name__ == "__main__":
    main()
