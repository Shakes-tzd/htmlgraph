#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
Work Validation Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.validator package module, which validates tool calls
and provides guidance for proper work item tracking.
"""

from htmlgraph.hooks.validator import main

if __name__ == "__main__":
    main()
