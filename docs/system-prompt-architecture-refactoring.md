# System Prompt Architecture Refactoring

## Executive Summary

System prompts are NOT static files stored in `.claude/system-prompt.md`. They are **dynamically generated context injected via the SessionStart hook's `additionalContext` field**. This architecture enables:

- **Plugin-provided defaults** - All users get orchestration guidance automatically
- **Project-level customization** - Teams can override defaults for their specific needs
- **Graceful degradation** - Works even if SDK or custom prompts aren't available
- **Survival across compacts** - Persists through Claude Code session compaction/resume cycles

This document outlines the refactoring to make system prompt management a true publishable plugin feature.

---

## Current Architecture (Session-Start Hook)

### Hook Flow

1. **SessionStart Hook Triggered** → Claude Code starts a session
2. **Hook Script Executes** → `packages/claude-plugin/hooks/scripts/session-start.py`
3. **Prompt Injection** → System prompt loaded and wrapped in `additionalContext`
4. **JSON Output** → Hook returns JSON with `hookSpecificOutput.additionalContext`
5. **Claude Receives Context** → Prompt injected into session alongside other context

### Current Implementation (Lines 583-671, session-start.py)

```python
def load_system_prompt(project_dir: Path) -> str | None:
    """Load system prompt from .claude/system-prompt.md"""
    prompt_file = Path(project_dir) / ".claude" / "system-prompt.md"
    if not prompt_file.exists():
        logger.warning(f"System prompt not found: {prompt_file}")
        return None
    try:
        content = prompt_file.read_text(encoding="utf-8")
        logger.info(f"Loaded system prompt ({len(content)} chars)")
        return content
    except Exception as e:
        logger.error(f"Failed to load system prompt: {e}")
        return None

def inject_prompt_via_additionalcontext(prompt: str, source: str) -> dict:
    """Create SessionStart hook output with system prompt injection."""
    context = f"""## SYSTEM PROMPT RESTORED (via SessionStart)
...
{prompt}
...
"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    return output
```

### Key Issues

1. **No Plugin Default** - If `.claude/system-prompt.md` doesn't exist, users get no system prompt
2. **No SDK Support** - No methods to create, validate, or manage system prompts programmatically
3. **Project-Specific** - Only looks for project-level files, no plugin fallback
4. **Limited Validation** - Token count validation exists but only logs warnings
5. **No Documentation** - Users don't know how to customize or what should go in prompts

---

## Proposed Architecture

### 1. Plugin Default Prompt

**File:** `packages/claude-plugin/.claude-plugin/system-prompt-default.md`

The default prompt is packaged WITH the plugin and available to ALL users when they install it. Contains:

- Delegation directives (Haiku for orchestration, etc.)
- Orchestration guidance (Task(), AskUserQuestion(), etc.)
- Model preferences (when to use Haiku vs Sonnet vs Opus)
- Quality gate requirements (ruff, mypy, pytest)
- Feature attribution instructions
- Key SDK patterns

**Size:** ~350-400 tokens (leaves room for project customization)

### 2. Project-Level Override

**File:** `.claude/system-prompt.md` (optional)

Users can OVERRIDE the plugin default with project-specific guidance:

- Project-specific patterns and conventions
- Team rules and standards
- Technology stack preferences
- Deployment and release procedures
- Project-specific tool configurations

**Strategy:**
- If `.claude/system-prompt.md` exists → Use it (override plugin default)
- Else → Use plugin default
- Graceful fallback if both missing

### 3. Hook Intelligence

**Refactored session-start.py:**

```python
def load_system_prompt(project_dir: Path) -> str | None:
    """
    Load system prompt with intelligent fallback:
    1. Check project-level override: .claude/system-prompt.md
    2. Fall back to plugin default
    3. Return None only if neither exists
    """
    # Check project override first
    project_override = Path(project_dir) / ".claude" / "system-prompt.md"
    if project_override.exists():
        try:
            content = project_override.read_text(encoding="utf-8")
            logger.info(f"Loaded project system prompt ({len(content)} chars)")
            return content
        except Exception as e:
            logger.warning(f"Failed to load project prompt: {e}")
            # Fall through to plugin default

    # Fall back to plugin default
    try:
        plugin_default = Path(__file__).parent.parent / "system-prompt-default.md"
        if plugin_default.exists():
            content = plugin_default.read_text(encoding="utf-8")
            logger.info(f"Loaded plugin default prompt ({len(content)} chars)")
            return content
    except Exception as e:
        logger.warning(f"Failed to load plugin default: {e}")

    return None
```

### 4. SDK Support

**New File:** `src/python/htmlgraph/system_prompts.py`

```python
class SystemPromptManager:
    """Manage system prompts for a project."""

    def __init__(self, graph_dir: Path):
        self.graph_dir = graph_dir
        self.project_dir = graph_dir.parent

    def get_default(self) -> str | None:
        """Get plugin default system prompt."""
        # Load from plugin package
        pass

    def get_project(self) -> str | None:
        """Get project-level override if exists."""
        prompt_file = self.project_dir / ".claude" / "system-prompt.md"
        if prompt_file.exists():
            return prompt_file.read_text()
        return None

    def get_active(self) -> str | None:
        """Get active prompt (project override OR plugin default)."""
        project_prompt = self.get_project()
        if project_prompt:
            return project_prompt
        return self.get_default()

    def create(self, name: str, template: str) -> "SystemPromptManager":
        """Create a new system prompt from template."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        claude_dir = self.project_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = claude_dir / "system-prompt.md"
        prompt_file.write_text(template)
        return self

    def validate(self, prompt_text: str | None = None) -> dict:
        """
        Validate system prompt.
        Returns: {is_valid: bool, tokens: int, warnings: List[str]}
        """
        text = prompt_text or self.get_active() or ""

        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model("gpt-4")
            tokens = len(encoding.encode(text))
        except Exception:
            tokens = max(1, len(text) // 4)  # Fallback estimate

        warnings = []
        if tokens > 1000:
            warnings.append(f"Prompt exceeds 1000 tokens ({tokens})")
        if tokens < 50:
            warnings.append("Prompt is very short - may not provide enough guidance")

        return {
            "is_valid": tokens <= 1000 and tokens > 50,
            "tokens": tokens,
            "warnings": warnings,
        }
```

**SDK Integration:**

```python
class SDK:
    @property
    def system_prompts(self) -> SystemPromptManager:
        """Access system prompt management."""
        return SystemPromptManager(self.graph_dir)
```

**Usage:**

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Get active prompt (project override OR plugin default)
active_prompt = sdk.system_prompts.get_active()

# Get plugin default
default_prompt = sdk.system_prompts.get_default()

# Create project override
sdk.system_prompts.create(
    "project-specific",
    "## Project Rules\n..."
).validate()

# Validate current prompt
result = sdk.system_prompts.validate()
print(f"Tokens: {result['tokens']}")
print(f"Valid: {result['is_valid']}")
```

---

## Deliverables

### 1. Plugin Default Prompt

**File:** `packages/claude-plugin/.claude-plugin/system-prompt-default.md`

**Content (~350-400 tokens):**

```markdown
# System Prompt - HtmlGraph Default

## Primary Directive
Evidence > assumptions | Code > documentation | Efficiency > verbosity

## Orchestration Pattern
- Use Task() tool for multi-session work, deep research, or complex reasoning
- Delegate multi-file work to specialized subagents
- Execute directly only for straightforward, single-file operations
- Haiku: Default orchestrator (excellent at following delegation)
- Sonnet/Opus: For deep reasoning (but tends to over-execute)

## Model Guidance
**Use Haiku (Default):**
- Orchestration and delegation (excellent at following instructions)
- Quick implementations and fixes (<30 minutes)
- Refactoring and cleanup
- Following established patterns
- File operations and searches
- Cost-effective, responsive

**Use Sonnet (Complex Reasoning):**
- Architecture and design decisions
- Complex algorithms and multi-step logic
- Performance optimization
- Security analysis and code review
- When previous attempts failed

**Use Opus (Novel Problems):**
- Entirely new feature design
- Deep research and investigation
- Multi-step reasoning with unknowns
- When Sonnet's attempt was insufficient

## Context Persistence
This prompt auto-injects at session start via SessionStart hook.
Survives compact/resume cycles. Available as reference throughout your session.

## HtmlGraph SDK Reference
```python
# Feature tracking
sdk.features.create('Feature name').save()

# Spike tracking (research, documentation)
sdk.spikes.create('Investigation').set_findings('...').save()

# System prompt management
prompt = sdk.system_prompts.get_active()
sdk.system_prompts.validate()
```

## Quality Gates
Before committing:
```bash
uv run ruff check --fix && uv run ruff format && \
uv run mypy src/ && uv run pytest
```

## Key Rules
1. Always Read before Write/Edit/Update
2. Use absolute paths only
3. Use `uv run` for all Python execution
4. Batch tool calls when independent
5. Fix all errors before committing
6. Research first, then implement

## Quick Commands
| Task | Command |
|------|---------|
| Tests | `uv run pytest` |
| Type Check | `uv run mypy src/` |
| Lint | `uv run ruff check --fix` |

**Note:** This is the plugin default. Projects can customize via `.claude/system-prompt.md`
```

### 2. Refactored Hook Script

**File:** `packages/claude-plugin/hooks/scripts/session-start.py`

Key changes (lines 583-606):

```python
def load_system_prompt(project_dir: Path) -> str | None:
    """
    Load system prompt with intelligent fallback:
    1. Check project-level override (.claude/system-prompt.md)
    2. Fall back to plugin default (system-prompt-default.md)
    3. Return None only if neither exists
    """
    # Strategy 1: Project-level override
    project_override = Path(project_dir) / ".claude" / "system-prompt.md"
    if project_override.exists():
        try:
            content = project_override.read_text(encoding="utf-8")
            logger.info(f"Loaded project system prompt ({len(content)} chars)")
            return content
        except Exception as e:
            logger.warning(f"Failed to load project prompt: {e}")
            # Continue to plugin default fallback

    # Strategy 2: Plugin default
    try:
        plugin_dir = Path(__file__).resolve().parent.parent.parent.parent
        plugin_default = plugin_dir / ".claude-plugin" / "system-prompt-default.md"

        if plugin_default.exists():
            content = plugin_default.read_text(encoding="utf-8")
            logger.info(f"Loaded plugin default prompt ({len(content)} chars)")
            return content
        else:
            logger.debug(f"Plugin default not found at {plugin_default}")
    except Exception as e:
        logger.warning(f"Failed to load plugin default: {e}")

    # No prompt available
    logger.info("No system prompt found (project override or plugin default)")
    return None
```

### 3. SDK Methods

**New File:** `src/python/htmlgraph/system_prompts.py`

```python
"""System prompt management for projects."""

from pathlib import Path
from typing import Optional

from htmlgraph.exceptions import HtmlGraphException


class SystemPromptValidator:
    """Validate system prompts."""

    @staticmethod
    def count_tokens(text: str) -> int:
        """Estimate or count tokens in text."""
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model("gpt-4")
            return len(encoding.encode(text))
        except Exception:
            # Fallback: rough estimation (1 token ≈ 4 chars)
            return max(1, len(text) // 4)

    @staticmethod
    def validate(text: str, max_tokens: int = 1000) -> dict:
        """
        Validate system prompt.

        Args:
            text: Prompt text to validate
            max_tokens: Maximum allowed tokens

        Returns:
            {
                "is_valid": bool,
                "tokens": int,
                "warnings": List[str],
                "message": str
            }
        """
        tokens = SystemPromptValidator.count_tokens(text)
        warnings = []

        if tokens > max_tokens:
            warnings.append(
                f"Prompt exceeds budget: {tokens} > {max_tokens} tokens"
            )
        if tokens < 50:
            warnings.append("Prompt is very short - may not provide sufficient guidance")
        if len(text) < 100:
            warnings.append("Prompt is very brief - consider adding more detail")

        message = ""
        if tokens <= max_tokens and tokens >= 50:
            message = f"Valid prompt: {tokens} tokens"
        elif tokens > max_tokens:
            message = f"Invalid: {tokens} tokens exceeds {max_tokens} limit"
        else:
            message = f"Warning: {tokens} tokens is below recommended minimum (50)"

        return {
            "is_valid": tokens <= max_tokens and tokens >= 50,
            "tokens": tokens,
            "warnings": warnings,
            "message": message,
        }


class SystemPromptManager:
    """Manage system prompts for a project."""

    def __init__(self, graph_dir: Path | str):
        self.graph_dir = Path(graph_dir)
        self.project_dir = self.graph_dir.parent
        self.claude_dir = self.project_dir / ".claude"

    def get_default(self) -> Optional[str]:
        """
        Get plugin default system prompt.

        Returns:
            Default prompt text, or None if not found
        """
        try:
            # Try to load from installed package
            from importlib.resources import files

            plugin_resources = files("htmlgraph_plugin").joinpath(
                ".claude-plugin/system-prompt-default.md"
            )
            if plugin_resources.is_file():
                return plugin_resources.read_text()
        except Exception:
            pass

        # Fallback: Try relative path from package
        try:
            # When installed via pip
            import htmlgraph_plugin
            plugin_path = Path(htmlgraph_plugin.__file__).parent
            default_file = plugin_path / ".claude-plugin" / "system-prompt-default.md"
            if default_file.exists():
                return default_file.read_text()
        except Exception:
            pass

        return None

    def get_project(self) -> Optional[str]:
        """
        Get project-level system prompt override.

        Returns:
            Project prompt if exists, None otherwise
        """
        prompt_file = self.claude_dir / "system-prompt.md"
        if prompt_file.exists():
            try:
                return prompt_file.read_text(encoding="utf-8")
            except Exception as e:
                raise HtmlGraphException(
                    f"Failed to read project system prompt: {e}"
                )
        return None

    def get_active(self) -> Optional[str]:
        """
        Get active system prompt (project override OR plugin default).

        Strategy:
        1. If project override exists → use it
        2. Else if plugin default exists → use it
        3. Else → return None

        Returns:
            Active prompt text, or None if neither available
        """
        project = self.get_project()
        if project:
            return project
        return self.get_default()

    def create(
        self,
        template: str,
        overwrite: bool = False
    ) -> "SystemPromptManager":
        """
        Create or update project system prompt.

        Args:
            template: Prompt template text
            overwrite: Whether to overwrite existing prompt

        Returns:
            Self for chaining

        Raises:
            HtmlGraphException: If file exists and overwrite=False
        """
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = self.claude_dir / "system-prompt.md"

        if prompt_file.exists() and not overwrite:
            raise HtmlGraphException(
                f"System prompt already exists at {prompt_file}. "
                f"Use overwrite=True to replace."
            )

        try:
            prompt_file.write_text(template, encoding="utf-8")
        except Exception as e:
            raise HtmlGraphException(f"Failed to write system prompt: {e}")

        return self

    def validate(self, text: Optional[str] = None, max_tokens: int = 1000) -> dict:
        """
        Validate a system prompt.

        Args:
            text: Prompt to validate (uses active if None)
            max_tokens: Maximum allowed tokens (default 1000)

        Returns:
            Validation result dict
        """
        prompt_text = text or self.get_active() or ""
        return SystemPromptValidator.validate(prompt_text, max_tokens)

    def delete(self) -> bool:
        """
        Delete project system prompt override.

        Returns:
            True if deleted, False if didn't exist
        """
        prompt_file = self.claude_dir / "system-prompt.md"
        if prompt_file.exists():
            try:
                prompt_file.unlink()
                return True
            except Exception as e:
                raise HtmlGraphException(f"Failed to delete prompt: {e}")
        return False


# Integration with SDK
def _get_system_prompts_manager(sdk: "SDK") -> SystemPromptManager:
    """Get system prompt manager from SDK."""
    return SystemPromptManager(sdk.graph_dir)
```

**SDK Integration (sdk.py):**

```python
# Add to SDK class
@property
def system_prompts(self) -> SystemPromptManager:
    """
    Access system prompt management.

    Usage:
        sdk = SDK(agent="claude")

        # Get active prompt
        prompt = sdk.system_prompts.get_active()

        # Create project override
        sdk.system_prompts.create("## Custom prompt")

        # Validate
        result = sdk.system_prompts.validate()
    """
    from htmlgraph.system_prompts import SystemPromptManager
    return SystemPromptManager(self.graph_dir)
```

### 4. Documentation

**New File:** `docs/system-prompt-customization-guide.md`

```markdown
# System Prompt Customization Guide

## Overview

HtmlGraph uses system prompts to guide AI agent behavior. Prompts are injected at session start via the SessionStart hook and survive compact/resume cycles.

**Two-tier system:**
1. **Plugin Default** - Included with HtmlGraph plugin, available to all users
2. **Project Override** - Optional, project-specific customization

## Plugin Default Prompt

All users get the plugin default automatically when they install the HtmlGraph plugin.

**Includes:**
- Delegation directives (using Task(), AskUserQuestion(), etc.)
- Model guidance (when to use Haiku vs Sonnet vs Opus)
- Orchestration patterns
- Quality gate requirements
- SDK usage patterns

**Location in plugin:** `.claude-plugin/system-prompt-default.md`

## Creating Project Override

Projects can customize the prompt for team-specific needs.

### 1. Create .claude/system-prompt.md

```bash
mkdir -p .claude
cat > .claude/system-prompt.md << 'EOF'
# System Prompt - MyProject

## Primary Rule
Code > documentation | Quality gates non-negotiable

## Team Standards
- All PRs require 2 approvals
- Tests must pass before merge
- No debug code in commits

## Tech Stack Preferences
- Use TypeScript, not JavaScript
- Prefer async/await over promises
- Always use strict mode

## Deployment Process
1. Update version in package.json
2. Run `npm run build && npm run test`
3. Create PR with changelog
4. After merge: `npm run deploy`

## Project-Specific Commands
| Task | Command |
|------|---------|
| Dev | `npm run dev` |
| Tests | `npm run test -- --coverage` |
| Build | `npm run build` |
| Deploy | `npm run deploy` |
EOF
```

### 2. Using SDK to Create Prompt

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Read a template from project
with open("docs/system-prompt-template.md") as f:
    template = f.read()

# Create project override
sdk.system_prompts.create(template, overwrite=True)

# Validate
result = sdk.system_prompts.validate()
print(f"Tokens: {result['tokens']}")
print(f"Valid: {result['is_valid']}")
for warning in result['warnings']:
    print(f"  - {warning}")
```

### 3. Validate Prompt

```bash
# Via SDK
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='claude')
result = sdk.system_prompts.validate()
print(result['message'])
for w in result['warnings']:
    print(f'  Warning: {w}')
"
```

## What to Include in Project Override

### Project Rules & Standards
```markdown
## Coding Standards
- Linting: ruff
- Type checking: mypy
- Code formatting: black
- Testing: pytest
```

### Technology Preferences
```markdown
## Tech Stack
- Python 3.11+
- FastAPI for APIs
- SQLAlchemy for ORM
- Pydantic for validation
```

### Deployment Process
```markdown
## Release Checklist
1. Update version in setup.py
2. Run tests: pytest --cov
3. Build: python -m build
4. Publish: twine upload dist/
```

### Team Workflow
```markdown
## Git Workflow
- Feature branches: feature/name
- Bug branches: bugfix/issue-id
- PR titles: "feat:", "fix:", "docs:"
- Squash commits before merge
```

### Project-Specific Tools
```markdown
## CI/CD Commands
| Task | Command |
|------|---------|
| Lint | make lint |
| Test | make test |
| Deploy Staging | make deploy-staging |
| Deploy Prod | make deploy-prod |
```

## Examples

### Example 1: Python Data Science Project

```markdown
# System Prompt - DataLab

## Primary Focus
- Jupyter notebooks for exploration
- Production code in src/
- Reproducible experiments

## Environment Setup
- Python 3.10+ with conda
- Dependencies in environment.yml
- Install dev tools: pip install -e ".[dev]"

## Workflow
1. Exploration: Jupyter notebooks in notebooks/
2. Implementation: src/ with proper modules
3. Testing: pytest in tests/
4. Documentation: docs/ with auto-generated API docs

## Commands
| Task | Command |
|------|---------|
| Notebooks | jupyter notebook |
| Tests | pytest -v --cov=src |
| Lint | flake8 src/ |
| Type Check | mypy src/ |
| Build Docs | sphinx-build -b html docs/ docs/_build/ |
```

### Example 2: Node.js/TypeScript Project

```markdown
# System Prompt - WebApp

## Stack
- Node 18+, TypeScript 5
- Next.js for frontend
- NestJS for backend
- PostgreSQL + Prisma

## Quality Gates
Before merge:
- Tests pass: `npm run test`
- No lint errors: `npm run lint`
- Type safe: `npm run type-check`
- E2E tests: `npm run test:e2e`

## Feature Workflow
1. Create feature branch from main
2. Implement + tests
3. Create PR with linked issue
4. Require 2 approvals
5. Run e2e tests in staging
6. Merge with squash

## Deployment
Automatic on merge to main:
1. Build and test (GitHub Actions)
2. Deploy to staging
3. Run e2e tests
4. Deploy to production (manual approval)
```

## FAQ

### Q: What if both project and plugin prompts exist?
**A:** Project override takes precedence. The hook loads project first, then falls back to plugin default.

### Q: How large can my system prompt be?
**A:** Recommended limit is 1000 tokens. SDK validation warns above this threshold.

### Q: Can I include multi-line code blocks?
**A:** Yes, use standard markdown code blocks. Token count includes all text.

### Q: How do I reset to plugin default?
**A:** Delete `.claude/system-prompt.md`:
```bash
rm .claude/system-prompt.md
```

### Q: Does the prompt survive session compacts?
**A:** Yes. The SessionStart hook re-injects the prompt at every session start, including after compacts and resume cycles.

### Q: Can I version control the system prompt?
**A:** Yes. Commit `.claude/system-prompt.md` to git for team standardization.

## Troubleshooting

### Prompt Not Loading
1. Check file exists: `ls -la .claude/system-prompt.md`
2. Check permissions: `chmod 644 .claude/system-prompt.md`
3. Validate syntax: `uv run python -c "from htmlgraph import SDK; SDK().system_prompts.validate()"`
4. Check logs: Look for "System prompt" lines in session logs

### Token Count Too High
1. Remove redundant sections
2. Use shorter section headers
3. Replace examples with links to documentation
4. Consider separate prompt files for different use cases

### Plugin Default Not Used
1. Verify plugin installed: `claude plugin list | grep htmlgraph`
2. Check plugin version: `claude plugin status htmlgraph`
3. Update plugin: `claude plugin update htmlgraph`

## See Also
- `/system-prompt-architecture-refactoring.md` - Technical architecture
- `/AGENTS.md` - HtmlGraph SDK reference
- `.claude/system-prompt.md` - This project's system prompt
```

---

## Implementation Timeline

### Phase 1: Core Infrastructure (2-3 hours)

1. **Create plugin default prompt** (30 min)
   - `packages/claude-plugin/.claude-plugin/system-prompt-default.md`
   - Delegation directives, model guidance, quality gates

2. **Refactor hook script** (45 min)
   - Implement intelligent fallback logic
   - Load project override OR plugin default
   - Test both paths

3. **Create SDK module** (60 min)
   - `src/python/htmlgraph/system_prompts.py`
   - SystemPromptManager class
   - SystemPromptValidator utilities

4. **SDK integration** (15 min)
   - Add `system_prompts` property to SDK class
   - Update SDK imports

### Phase 2: Documentation & Testing (1-2 hours)

5. **Create customization guide** (45 min)
   - `docs/system-prompt-customization-guide.md`
   - Examples for different project types
   - FAQ and troubleshooting

6. **Write unit tests** (30 min)
   - Test SystemPromptManager methods
   - Test fallback logic
   - Test validation

7. **Integration testing** (15 min)
   - Verify hook loads plugin default
   - Verify project override takes precedence
   - Verify SDK methods work

### Phase 3: Deployment & Packaging (30 min)

8. **Update plugin packaging**
   - Ensure `system-prompt-default.md` included in plugin distribution
   - Verify plugin.json includes plugin resources

9. **Create changelog entry**
   - Document new system prompt feature
   - Link to customization guide

---

## Success Criteria

✅ **Plugin Provides Default Prompt**
- Plugin default available to all users
- No manual setup required
- Works even without `.claude/system-prompt.md`

✅ **Project-Level Customization**
- Users can create `.claude/system-prompt.md`
- Override automatically takes precedence
- Falls back gracefully if missing

✅ **Hook Intelligence**
- Hook loads project override if exists
- Hook loads plugin default if no override
- No errors if neither available

✅ **SDK Support**
- Methods to get, create, validate prompts
- Token counting (exact or estimated)
- Integration with feature tracking

✅ **Graceful Degradation**
- Works without SDK installed
- Works without htmlgraph module
- Works without custom prompts

✅ **Documentation**
- Customization guide with examples
- FAQ addressing common questions
- Troubleshooting section

✅ **All Tests Pass**
- Existing tests still pass
- New tests cover system prompt logic
- No regressions

---

## Risk Mitigation

### Risk: Plugin Default Not Found at Runtime

**Mitigation:**
- Fallback to inline default in hook script as last resort
- Log clear warnings when default unavailable
- Non-blocking - session continues without prompt injection

### Risk: Project Prompt Exceeds Token Budget

**Mitigation:**
- Validate token count before injection
- Warn user but inject anyway (graceful degradation)
- Provide token counting tool via SDK

### Risk: Breaking Existing Projects

**Mitigation:**
- Existing `.claude/system-prompt.md` files continue to work
- No changes to existing API
- Fully backward compatible

### Risk: Performance Impact

**Mitigation:**
- Prompt loading happens once per session (minimal overhead)
- Caching at hook script level
- No impact on subsequent tool executions

---

## Future Enhancements

### 1. Multiple Prompt Variants

Support different prompts for different model types:
```python
# Load appropriate prompt for model
prompt = sdk.system_prompts.get_for_model("gpt-4")
prompt = sdk.system_prompts.get_for_model("claude-opus")
```

### 2. Prompt Templates Library

Built-in templates for common project types:
```python
# Create from template
sdk.system_prompts.from_template("typescript-react")
sdk.system_prompts.from_template("python-fastapi")
```

### 3. Prompt Composition

Combine multiple prompt files:
```python
# Load and merge multiple prompts
sdk.system_prompts.compose([
    "base.md",          # Common rules
    "team.md",          # Team standards
    "project.md"        # Project-specific
])
```

### 4. Prompt Analytics

Track which prompts are most effective:
```python
# Analyze prompt effectiveness
analytics = sdk.system_prompts.analyze()
print(analytics.feature_completion_rate)
print(analytics.error_reduction)
```

---

## Conclusion

This refactoring makes system prompt management a publishable plugin feature while maintaining backward compatibility and graceful degradation. Users get professional orchestration guidance out-of-the-box, with the option to customize for their specific needs.

The two-tier system (plugin default + project override) provides the right balance between:
- **Ease of use** - Default available to everyone
- **Flexibility** - Teams can customize
- **Robustness** - Graceful fallback if anything missing
- **Observability** - SDK support for programmatic management
