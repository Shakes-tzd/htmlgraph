from __future__ import annotations

"""
SubagentOrchestrator for context-preserving delegation.

IMPERATIVE USAGE INSTRUCTIONS
=============================

As an orchestrator, you MUST follow these steps:

1. INITIALIZE
   ```python
   from htmlgraph import SDK
   sdk = SDK(agent="claude")
   ```

2. SPAWN EXPLORER (for codebase discovery)
   ```python
   explorer = sdk.spawn_explorer(
       task="Find all API endpoints",
       scope="src/api/"
   )
   # Use with Task tool:
   # Task(prompt=explorer["prompt"], subagent_type=explorer["subagent_type"])
   ```

3. SPAWN CODER (for implementation)
   ```python
   coder = sdk.spawn_coder(
       feature_id="feat-123",
       context="Explorer found endpoints in src/api/routes.py",
       test_command="uv run pytest"
   )
   # Use with Task tool:
   # Task(prompt=coder["prompt"], subagent_type=coder["subagent_type"])
   ```

4. FULL ORCHESTRATION (explore + implement)
   ```python
   prompts = sdk.orchestrate(
       feature_id="feat-123",
       exploration_scope="src/",
       test_command="uv run pytest"
   )
   # Returns: {"explorer": {...}, "coder": {...}}
   ```

DECISION GUIDE
==============

| Scenario | Method |
|----------|--------|
| Unknown codebase | spawn_explorer first, then spawn_coder |
| Known codebase | spawn_coder directly |
| Complex feature | orchestrate for full workflow |
| Multiple features | spawn_coder in parallel |

ANTI-PATTERNS
=============

NEVER:
- Implement without exploration on unknown codebases
- Spawn coder without feature_id (create feature first!)
- Edit code yourself when you should delegate

ALWAYS:
- Create work item before spawning coder
- Pass explorer context to coder
- Let subagents do the heavy lifting

Available Classes
=================

SubagentType: Enum of subagent types (EXPLORER, CODER, REVIEWER, TESTER)
SubagentPrompt: Prepared prompt for spawning subagent via Task tool
SubagentResult: Parsed results from subagent execution
SubagentOrchestrator: Main orchestration class

Key Patterns
============

1. Two-phase workflow: Explorer discovers → Coder implements
2. Stateless subagents: Each spawned agent is ephemeral and task-focused
3. Context efficiency: Main session reserves context for orchestration
4. Parallel execution: Multiple subagents can work simultaneously
"""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK


class SubagentType(Enum):
    """Types of specialized subagents."""

    EXPLORER = "explorer"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"


@dataclass
class SubagentPrompt:
    """A prepared prompt for spawning a subagent via Task tool."""

    prompt: str
    description: str
    subagent_type: str
    task_id: str | None = None

    # Expected outputs
    expected_sections: list[str] = field(default_factory=list)

    # Retry configuration
    max_retries: int = 2
    retry_delay_seconds: int = 5

    def to_task_kwargs(self) -> dict[str, Any]:
        """Convert to kwargs for Task tool invocation."""
        return {
            "prompt": self.prompt,
            "description": self.description,
            "subagent_type": self.subagent_type,
        }


@dataclass
class SubagentResult:
    """Parsed result from a subagent execution."""

    subagent_type: SubagentType
    task_id: str | None
    success: bool

    # Parsed outputs
    summary: str = ""
    files_found: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    patterns_discovered: dict[str, list[str]] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # Raw output for debugging
    raw_output: str = ""

    # Metrics
    duration_seconds: float = 0.0
    tool_calls: int = 0


class SubagentOrchestrator:
    """
    Orchestrates specialized subagents for exploration and coding tasks.

    Benefits:
    - Main session context reserved for orchestration decisions
    - Parallel exploration and coding via ephemeral subagents
    - Better context efficiency (subagents are stateless)
    - More tasks completed before main context fills up

    Example:
        >>> orchestrator = SubagentOrchestrator(sdk)
        >>>
        >>> # Phase 1: Explore codebase
        >>> explorer = orchestrator.spawn_explorer(
        ...     task="Map the authentication system",
        ...     scope="src/auth/",
        ... )
        >>> # Execute with Task tool, get results
        >>>
        >>> # Phase 2: Implement changes
        >>> coder = orchestrator.spawn_coder(
        ...     feature_id="feat-auth-fix",
        ...     context=explorer_results,
        ... )
    """

    def __init__(self, sdk: SDK):
        """
        Initialize orchestrator.

        Args:
            sdk: Parent SDK instance for accessing features and tracking
        """
        self.sdk = sdk
        self._directory = sdk._directory

    def spawn_explorer(
        self,
        task: str,
        scope: str | None = None,
        patterns: list[str] | None = None,
        questions: list[str] | None = None,
        max_files: int = 50,
        include_tests: bool = False,
    ) -> SubagentPrompt:
        """
        Spawn an explorer subagent for codebase discovery and analysis.

        Explorer agents are optimized for:
        - Finding files matching patterns
        - Searching for code patterns
        - Mapping dependencies and relationships
        - Answering architectural questions

        Args:
            task: What to explore/discover
            scope: Directory scope (e.g., "src/", "tests/")
            patterns: Glob patterns to focus on (e.g., ["**/*.py"])
            questions: Specific questions to answer
            max_files: Maximum files to read in detail
            include_tests: Whether to include test files

        Returns:
            SubagentPrompt ready for Task tool

        Example:
            >>> prompt = orchestrator.spawn_explorer(
            ...     task="Find all database models and their relationships",
            ...     scope="src/models/",
            ...     patterns=["**/*.py"],
            ...     questions=["What ORM is used?", "How are relationships defined?"]
            ... )
        """
        # Build scope directive
        scope_directive = ""
        if scope:
            scope_directive = f"Focus on: {scope}"
        if patterns:
            scope_directive += f"\nPatterns: {', '.join(patterns)}"

        # Build questions section
        questions_section = ""
        if questions:
            questions_section = "## Questions to Answer\n" + "\n".join(
                f"- {q}" for q in questions
            )

        prompt = f"""# Explorer Task: {task}

You are an EXPLORER subagent. Your job is to discover and analyze code, NOT modify it.

## Scope
{scope_directive or "Entire codebase"}
Max files to read in detail: {max_files}
Include tests: {include_tests}

{questions_section}

## Efficient Exploration Strategy

1. **Start with Glob** to find relevant files:
   - Use Glob with patterns like "{patterns[0] if patterns else "**/*.py"}"
   - This is faster than recursive directory exploration

2. **Use Grep for targeted search**:
   - Search for keywords, class names, function signatures
   - This finds exact locations without reading entire files

3. **Read strategically**:
   - Only read files that Grep identified as relevant
   - Read imports and class definitions first
   - Skip boilerplate and generated code

4. **Map relationships**:
   - Note imports and dependencies
   - Identify inheritance and composition
   - Document API boundaries

## Output Format

Return your findings in this exact format:

## Summary
[2-3 sentence overview of what you found]

## Files Found
- file1.py: [brief description]
- file2.py: [brief description]
...

## Key Patterns
### Pattern Name
- Description of pattern
- Where it's used
- Example code

## Answers
[Answer each question from Questions to Answer section]

## Recommendations
- [Suggestion for the coder agent]
- [Potential issues to watch for]
"""

        return SubagentPrompt(
            prompt=prompt,
            description=f"Explore: {task[:40]}",
            subagent_type="Explore",  # Use the Explore agent type
            expected_sections=["Summary", "Files Found", "Key Patterns"],
            max_retries=1,
        )

    def spawn_coder(
        self,
        feature_id: str,
        context: str | SubagentResult | None = None,
        files_to_modify: list[str] | None = None,
        test_command: str | None = None,
        style_guide: str | None = None,
    ) -> SubagentPrompt:
        """
        Spawn a coder subagent for implementing changes.

        Coder agents are optimized for:
        - Reading and modifying specific files
        - Following patterns from exploration
        - Running and fixing tests
        - Maintaining code quality

        Args:
            feature_id: Feature being implemented
            context: Results from explorer (string or SubagentResult)
            files_to_modify: Specific files to change
            test_command: Command to verify changes
            style_guide: Code style guidelines

        Returns:
            SubagentPrompt ready for Task tool

        Example:
            >>> prompt = orchestrator.spawn_coder(
            ...     feature_id="feat-add-auth",
            ...     context=explorer_results,
            ...     test_command="uv run pytest tests/auth/"
            ... )
        """
        # Get feature details
        feature = self.sdk.features.get(feature_id)
        if not feature:
            raise ValueError(f"Feature not found: {feature_id}")

        # Build context section
        context_section = ""
        if isinstance(context, SubagentResult):
            context_section = f"""## Context from Explorer

### Summary
{context.summary}

### Files to Consider
{chr(10).join(f"- {f}" for f in context.files_found[:20])}

### Patterns Discovered
{chr(10).join(f"- {k}: {v}" for k, v in list(context.patterns_discovered.items())[:5])}

### Recommendations
{chr(10).join(f"- {r}" for r in context.recommendations)}
"""
        elif isinstance(context, str):
            context_section = f"## Context from Explorer\n\n{context}"

        # Build files section
        files_section = ""
        if files_to_modify:
            files_section = "## Target Files\n" + "\n".join(
                f"- {f}" for f in files_to_modify
            )

        # Build test section
        test_section = ""
        if test_command:
            test_section = f"""## Testing

Run tests after changes:
```bash
{test_command}
```

If tests fail, fix the issues before completing.
"""

        # Build style section
        style_section = ""
        if style_guide:
            style_section = f"## Style Guide\n\n{style_guide}"

        # Get feature steps
        steps_section = ""
        if feature.steps:
            steps_lines = []
            for i, step in enumerate(feature.steps, 1):
                status = "✅" if step.completed else "⏳"
                steps_lines.append(f"{i}. {status} {step.description}")
            steps_section = "## Implementation Steps\n" + "\n".join(steps_lines)

        prompt = f"""# Coder Task: {feature.title}

You are a CODER subagent. Your job is to implement changes efficiently.

Feature ID: {feature_id}
Priority: {feature.priority}
Status: {feature.status}

{context_section}

{files_section}

{steps_section}

{style_section}

## Efficient Implementation Strategy

1. **Read before Edit**:
   - Read the target file first
   - Understand existing patterns
   - Plan your changes

2. **Batch Edits**:
   - Make multiple related changes in sequence
   - Don't switch between files unnecessarily

3. **Test incrementally**:
   - Run tests after significant changes
   - Fix issues immediately

4. **Update feature tracking**:
   - Mark steps as complete as you go
   - Note any blockers

{test_section}

## Output Format

Return your results in this exact format:

## Summary
[What was implemented]

## Files Modified
- file1.py: [what changed]
- file2.py: [what changed]

## Tests
[Test results - PASS/FAIL with details]

## Blockers
[Any issues preventing completion, or "None"]

## Status
[COMPLETE or IN_PROGRESS with next steps]
"""

        return SubagentPrompt(
            prompt=prompt,
            description=f"Code: {feature.title[:40]}",
            subagent_type="general-purpose",
            task_id=feature_id,
            expected_sections=["Summary", "Files Modified", "Status"],
            max_retries=2,
        )

    def parse_explorer_result(self, output: str) -> SubagentResult:
        """
        Parse the output from an explorer subagent.

        Args:
            output: Raw output text from the explorer

        Returns:
            Structured SubagentResult
        """
        result = SubagentResult(
            subagent_type=SubagentType.EXPLORER,
            task_id=None,
            success=True,
            raw_output=output,
        )

        # Parse sections
        current_section = ""
        current_content: list[str] = []

        for line in output.split("\n"):
            if line.startswith("## "):
                # Save previous section
                if current_section == "Summary":
                    result.summary = "\n".join(current_content).strip()
                elif current_section == "Files Found":
                    result.files_found = [
                        l.split(":")[0].strip("- ").strip()
                        for l in current_content
                        if l.strip().startswith("-")
                    ]
                elif current_section == "Recommendations":
                    result.recommendations = [
                        l.strip("- ").strip()
                        for l in current_content
                        if l.strip().startswith("-")
                    ]

                # Start new section
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        # Don't forget last section
        if current_section == "Summary":
            result.summary = "\n".join(current_content).strip()
        elif current_section == "Files Found":
            result.files_found = [
                l.split(":")[0].strip("- ").strip()
                for l in current_content
                if l.strip().startswith("-")
            ]
        elif current_section == "Recommendations":
            result.recommendations = [
                l.strip("- ").strip()
                for l in current_content
                if l.strip().startswith("-")
            ]

        return result

    def parse_coder_result(self, output: str) -> SubagentResult:
        """
        Parse the output from a coder subagent.

        Args:
            output: Raw output text from the coder

        Returns:
            Structured SubagentResult
        """
        result = SubagentResult(
            subagent_type=SubagentType.CODER,
            task_id=None,
            success="COMPLETE" in output.upper(),
            raw_output=output,
        )

        # Parse sections
        current_section = ""
        current_content: list[str] = []

        for line in output.split("\n"):
            if line.startswith("## "):
                # Save previous section
                if current_section == "Summary":
                    result.summary = "\n".join(current_content).strip()
                elif current_section == "Files Modified":
                    result.files_modified = [
                        l.split(":")[0].strip("- ").strip()
                        for l in current_content
                        if l.strip().startswith("-")
                    ]
                elif current_section == "Blockers":
                    blockers = "\n".join(current_content).strip()
                    if blockers.lower() != "none":
                        result.blockers = [blockers]
                        result.success = False

                # Start new section
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        return result

    def update_feature_from_result(
        self,
        feature_id: str,
        result: SubagentResult,
    ) -> None:
        """
        Update a feature based on coder subagent results.

        Args:
            feature_id: Feature to update
            result: Result from coder subagent
        """
        feature = self.sdk.features.get(feature_id)
        if not feature:
            return

        with self.sdk.features.edit(feature_id) as f:
            # Update status based on result
            if result.success:
                f.status = "done"
                f.properties["completed_at"] = datetime.now().isoformat()
            elif result.blockers:
                f.status = "blocked"
                f.properties["blockers"] = result.blockers
            else:
                f.status = "in-progress"

            # Store implementation details
            f.properties["files_modified"] = result.files_modified
            f.properties["implementation_summary"] = result.summary

    def orchestrate_feature(
        self,
        feature_id: str,
        exploration_scope: str | None = None,
        test_command: str | None = None,
    ) -> dict[str, SubagentPrompt]:
        """
        Generate prompts for full feature orchestration (explore then code).

        This is a convenience method that creates both explorer and coder
        prompts for a complete feature implementation workflow.

        Args:
            feature_id: Feature to implement
            exploration_scope: Directory to explore (optional)
            test_command: Test command for verification

        Returns:
            Dict with 'explorer' and 'coder' prompts

        Example:
            >>> prompts = orchestrator.orchestrate_feature(
            ...     "feat-add-caching",
            ...     exploration_scope="src/cache/",
            ...     test_command="uv run pytest tests/cache/"
            ... )
            >>> # Execute explorer first
            >>> explorer_result = execute_task(prompts['explorer'])
            >>> # Then execute coder with explorer results
            >>> coder_prompt = orchestrator.spawn_coder(
            ...     feature_id,
            ...     context=explorer_result
            ... )
        """
        feature = self.sdk.features.get(feature_id)
        if not feature:
            raise ValueError(f"Feature not found: {feature_id}")

        # Generate explorer prompt
        explorer = self.spawn_explorer(
            task=f"Explore codebase for: {feature.title}",
            scope=exploration_scope,
            questions=[
                "What existing code is relevant?",
                "What patterns should be followed?",
                "What files need modification?",
            ],
        )

        # Note: coder prompt should be generated after explorer results
        # We provide a placeholder that can be used once explorer completes
        coder = self.spawn_coder(
            feature_id=feature_id,
            context="[Insert explorer results here]",
            test_command=test_command,
        )

        return {
            "explorer": explorer,
            "coder": coder,
        }
