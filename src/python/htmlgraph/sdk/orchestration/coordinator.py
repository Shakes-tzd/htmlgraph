"""
Orchestration coordinator - manages subagent spawning and workflows.

Provides OrchestrationMixin with:
- orchestrator property (lazy-loaded SubagentOrchestrator)
- spawn_explorer() - Spawn explorer subagent for codebase discovery
- spawn_coder() - Spawn coder subagent for implementation
- orchestrate() - Full exploration + implementation workflow
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK as SDK_TYPE
else:
    SDK_TYPE = "SDK"  # type: ignore[misc,assignment]


class OrchestrationMixin:
    """
    Mixin providing orchestration capabilities to SDK.

    Adds methods for spawning and coordinating subagents.
    Requires SDK instance with _orchestrator attribute.
    """

    _orchestrator: Any
    _directory: Any

    def __init__(self) -> None:
        """Initialize orchestration state."""
        self._orchestrator = None

    @property
    def orchestrator(self) -> Any:
        """
        Get the subagent orchestrator for spawning explorer/coder agents.

        Lazy-loaded on first access.

        Returns:
            SubagentOrchestrator instance

        Example:
            >>> sdk = SDK(agent="claude")
            >>> explorer = sdk.orchestrator.spawn_explorer(
            ...     task="Find all API endpoints",
            ...     scope="src/"
            ... )
        """
        if self._orchestrator is None:
            from htmlgraph.orchestrator import SubagentOrchestrator

            self._orchestrator = SubagentOrchestrator(self)  # type: ignore[arg-type,assignment]
        return self._orchestrator

    def spawn_explorer(
        self,
        task: str,
        scope: str | None = None,
        patterns: list[str] | None = None,
        questions: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Spawn an explorer subagent for codebase discovery.

        Explorer agents are optimized for finding files, searching patterns,
        and mapping code without modifying anything.

        Args:
            task: What to explore/discover
            scope: Directory scope (e.g., "src/")
            patterns: Glob patterns to focus on
            questions: Specific questions to answer

        Returns:
            Dict with prompt ready for Task tool

        Note:
            Returns dict with 'prompt', 'description', 'subagent_type' keys.
            Returns empty dict if spawning fails.

        Example:
            >>> prompt = sdk.spawn_explorer(
            ...     task="Find all database models",
            ...     scope="src/models/",
            ...     questions=["What ORM is used?"]
            ... )
            >>> # Execute with Task tool
            >>> Task(prompt=prompt["prompt"], description=prompt["description"])

        See also:
            spawn_coder: Spawn implementation agent with feature context
            orchestrate: Full exploration + implementation workflow
        """
        subagent_prompt = self.orchestrator.spawn_explorer(
            task=task,
            scope=scope,
            patterns=patterns,
            questions=questions,
        )
        result: dict[str, Any] = subagent_prompt.to_task_kwargs()
        return result

    def spawn_coder(
        self,
        feature_id: str,
        context: str | None = None,
        files_to_modify: list[str] | None = None,
        test_command: str | None = None,
    ) -> dict[str, Any]:
        """
        Spawn a coder subagent for implementing changes.

        Coder agents are optimized for reading, modifying, and testing code.

        Args:
            feature_id: Feature being implemented
            context: Results from explorer (string summary)
            files_to_modify: Specific files to change
            test_command: Command to verify changes

        Returns:
            Dict with prompt ready for Task tool

        Note:
            Returns dict with 'prompt', 'description', 'subagent_type' keys.
            Requires valid feature_id. Returns empty dict if feature not found.

        Example:
            >>> prompt = sdk.spawn_coder(
            ...     feature_id="feat-add-auth",
            ...     context=explorer_results,
            ...     test_command="uv run pytest tests/auth/"
            ... )
            >>> Task(prompt=prompt["prompt"], description=prompt["description"])

        See also:
            spawn_explorer: Explore codebase before implementation
            orchestrate: Full exploration + implementation workflow
        """
        subagent_prompt = self.orchestrator.spawn_coder(
            feature_id=feature_id,
            context=context,
            files_to_modify=files_to_modify,
            test_command=test_command,
        )
        result: dict[str, Any] = subagent_prompt.to_task_kwargs()
        return result

    def orchestrate(
        self,
        feature_id: str,
        exploration_scope: str | None = None,
        test_command: str | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrate full feature implementation with explorer and coder.

        Generates prompts for a two-phase workflow:
        1. Explorer discovers relevant code and patterns
        2. Coder implements the feature based on explorer findings

        Args:
            feature_id: Feature to implement
            exploration_scope: Directory to explore
            test_command: Test command for verification

        Returns:
            Dict with explorer and coder prompts

        Example:
            >>> prompts = sdk.orchestrate(
            ...     "feat-add-caching",
            ...     exploration_scope="src/cache/",
            ...     test_command="uv run pytest tests/cache/"
            ... )
            >>> # Phase 1: Run explorer
            >>> Task(prompt=prompts["explorer"]["prompt"], ...)
            >>> # Phase 2: Run coder with explorer results
            >>> Task(prompt=prompts["coder"]["prompt"], ...)

        See also:
            spawn_explorer: Just the exploration phase
            spawn_coder: Just the implementation phase
        """
        prompts = self.orchestrator.orchestrate_feature(
            feature_id=feature_id,
            exploration_scope=exploration_scope,
            test_command=test_command,
        )
        return {
            "explorer": prompts["explorer"].to_task_kwargs(),
            "coder": prompts["coder"].to_task_kwargs(),
            "workflow": [
                "1. Execute explorer Task and collect results",
                "2. Parse explorer results for files and patterns",
                "3. Execute coder Task with explorer context",
                "4. Verify coder results and update feature status",
            ],
        }
