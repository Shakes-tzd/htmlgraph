"""Orchestration utilities for multi-agent coordination."""

from .headless_spawner import AIResult, HeadlessSpawner
from .model_selection import (
    BudgetMode,
    ComplexityLevel,
    ModelSelection,
    TaskType,
    get_fallback_chain,
    select_model,
)
from .spawner_event_tracker import SpawnerEventTracker, create_tracker_from_env

# Export modular spawners for advanced usage
from .spawners import (
    BaseSpawner,
    ClaudeSpawner,
    CodexSpawner,
    CopilotSpawner,
    GeminiSpawner,
)
from .task_coordination import (
    delegate_with_id,
    generate_task_id,
    get_results_by_task_id,
    parallel_delegate,
    save_task_results,
    validate_and_save,
)

__all__ = [
    # Headless AI spawning (unified interface)
    "HeadlessSpawner",
    "AIResult",
    # Modular spawner implementations
    "BaseSpawner",
    "GeminiSpawner",
    "CodexSpawner",
    "CopilotSpawner",
    "ClaudeSpawner",
    # Spawner event tracking
    "SpawnerEventTracker",
    "create_tracker_from_env",
    # Model selection
    "ModelSelection",
    "TaskType",
    "ComplexityLevel",
    "BudgetMode",
    "select_model",
    "get_fallback_chain",
    # Task coordination
    "delegate_with_id",
    "generate_task_id",
    "get_results_by_task_id",
    "parallel_delegate",
    "save_task_results",
    "validate_and_save",
]
