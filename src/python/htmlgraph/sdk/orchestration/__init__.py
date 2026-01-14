"""
Orchestration module for spawning and coordinating subagents.

Provides:
- OrchestrationMixin: Mixin for SDK with orchestration capabilities
- Spawner utilities for creating explorer/coder agents
- Coordinator for managing multi-agent workflows

Public API:
    from htmlgraph.sdk.orchestration import OrchestrationMixin
"""

from htmlgraph.sdk.orchestration.coordinator import OrchestrationMixin

__all__ = [
    "OrchestrationMixin",
]
