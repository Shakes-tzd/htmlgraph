#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
Orchestrator Enforcement Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.orchestrator package module, which enforces orchestrator
delegation patterns when orchestrator mode is active.
"""

from htmlgraph.hooks.orchestrator import main

if __name__ == "__main__":
    main()
