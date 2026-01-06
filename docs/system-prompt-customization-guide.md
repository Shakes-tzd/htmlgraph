# System Prompt Customization Guide

## Overview

HtmlGraph uses system prompts to guide AI agent behavior. Prompts are injected at session start via the SessionStart hook and survive Claude Code compact/resume cycles.

**Two-tier system:**

1. **Plugin Default** - Included with HtmlGraph plugin, automatically available to all users
2. **Project Override** - Optional, project-specific customization via `.claude/system-prompt.md`

---

## How It Works

### Architecture

System prompts are NOT stored as static configuration. Instead:

1. **SessionStart Hook** triggers when Claude Code starts a session
2. **Hook script loads** the active system prompt (project override OR plugin default)
3. **Prompt is injected** into session via `additionalContext` in hook JSON output
4. **Claude receives** the prompt alongside other session context
5. **Prompt persists** across compact/resume cycles (re-injected on each session start)

### Fallback Strategy

The hook uses an intelligent fallback strategy:

```
Session Starts
    ↓
Check: .claude/system-prompt.md exists?
    ├─ YES → Use project override
    └─ NO → Check: Plugin default exists?
            ├─ YES → Use plugin default
            └─ NO → Continue without system prompt (graceful degradation)
```

### Plugin Default Prompt

All users get the plugin default automatically when they install the HtmlGraph plugin.

**Location:** `.claude-plugin/system-prompt-default.md` (in plugin package)

**Includes:**
- Delegation directives (using Task(), AskUserQuestion(), etc.)
- Model guidance (when to use Haiku vs Sonnet vs Opus)
- Orchestration patterns
- Quality gate requirements (ruff, mypy, pytest)
- SDK usage patterns
- Key development rules

**Size:** ~350-400 tokens (leaves room for project customization)

---

## Creating Project Override

Projects can customize the default prompt for team-specific needs.

### Option 1: Manual File Creation

```bash
# Create .claude directory
mkdir -p .claude

# Create system-prompt.md
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

# Verify
cat .claude/system-prompt.md
```

### Option 2: Using SDK

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Read a template from project
with open("docs/system-prompt-template.md") as f:
    template = f.read()

# Create project override
sdk.system_prompts.create(template, overwrite=False)

# Validate
result = sdk.system_prompts.validate()
print(result['message'])
if result['warnings']:
    for warning in result['warnings']:
        print(f"  Warning: {warning}")
```

### Option 3: Programmatic Generation

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Generate custom prompt
custom_prompt = """# System Prompt - DataLab

## Stack
- Python 3.10+ with conda
- Jupyter notebooks for exploration
- Production code in src/

## Commands
| Task | Command |
|------|---------|
| Test | pytest -v --cov=src |
| Notebook | jupyter notebook |
| Build Docs | sphinx-build -b html docs/ docs/_build/ |
"""

sdk.system_prompts.create(custom_prompt)
```

---

## Validating Your Prompt

### Via SDK

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Validate active prompt
result = sdk.system_prompts.validate()
print(result['message'])
print(f"Tokens: {result['tokens']}")
print(f"Valid: {result['is_valid']}")

# Validate specific text
result = sdk.system_prompts.validate("## My Prompt\n...")

# Check what's actually in use
stats = sdk.system_prompts.get_stats()
print(f"Source: {stats['source']}")  # "project_override" or "plugin_default" or "none"
```

### Via Command Line

```bash
# Check token count and validity
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='claude')
result = sdk.system_prompts.validate()
print(result['message'])
for w in result['warnings']:
    print(f'  Warning: {w}')
"

# Get statistics
uv run python -c "
from htmlgraph import SDK
stats = SDK().system_prompts.get_stats()
print(f'Source: {stats[\"source\"]}')
print(f'Tokens: {stats[\"tokens\"]}')
"
```

---

## What to Include in Project Override

### 1. Project Rules & Standards

```markdown
## Coding Standards
- Linting: ruff
- Type checking: mypy
- Code formatting: black
- Testing: pytest with minimum 80% coverage
- No type: ignore comments without justification
```

### 2. Technology Preferences

```markdown
## Tech Stack
- Python 3.11+
- FastAPI for APIs
- SQLAlchemy 2.0+ for ORM
- Pydantic v2 for validation
- PostgreSQL 14+ for data storage

## Dependencies
- Prefer standard library over external deps
- Pin versions in requirements.txt
- Regular security audits
```

### 3. Deployment Process

```markdown
## Release Checklist
1. Bump version in setup.py
2. Update CHANGELOG.md
3. Run tests: pytest --cov
4. Build: python -m build
5. Create git tag: git tag vX.Y.Z
6. Publish: twine upload dist/
7. Verify on PyPI

## Rollback Process
If critical issue found:
1. Yank release: twine yank package-name VERSION
2. Fix issue
3. Bump patch version
4. Re-publish
```

### 4. Team Workflow

```markdown
## Git Workflow
- Feature branches: feature/name
- Bug branches: bugfix/issue-id
- PR titles: "feat:", "fix:", "docs:", "refactor:"
- Always squash commits before merge
- Require 2+ approvals before merge
- Delete branch after merge
```

### 5. Project-Specific Tools

```markdown
## CI/CD Commands
| Task | Command |
|------|---------|
| Lint | make lint |
| Test | make test |
| Coverage | make coverage |
| Build | make build |
| Deploy Staging | make deploy-staging |
| Deploy Prod | make deploy-prod |

## Environment Variables
- REQUIRED: API_KEY, DATABASE_URL
- OPTIONAL: DEBUG_MODE, LOG_LEVEL
- File: .env (never commit)
```

### 6. Architecture & Design Decisions

```markdown
## Architecture Principles
- Layered: Models → Services → API
- Event-driven for async operations
- CQRS for complex queries
- Event sourcing for audit trail

## Design Patterns
- Repository pattern for data access
- Dependency injection for testability
- Factory pattern for object creation
- Singleton for shared resources (sparingly)
```

---

## Examples

### Example 1: Python Data Science Project

```markdown
# System Prompt - DataLab

## Primary Focus
- Jupyter notebooks for exploration and visualization
- Production code in src/ with proper modules
- Reproducible experiments with random seeds
- Documentation with Sphinx

## Environment Setup
- Python 3.10+ with conda
- Dependencies in environment.yml
- Install dev tools: `pip install -e ".[dev]"`
- Jupyter Lab for notebooks

## Workflow
1. **Exploration:** Jupyter notebooks in notebooks/
   - Name: `01-data-loading.ipynb`, `02-eda.ipynb`, etc.
   - Include markdown cells explaining analysis
   - Never commit .ipynb output cells

2. **Implementation:** src/ with proper modules
   - src/models/ - Data models and schemas
   - src/pipeline/ - Processing pipeline
   - src/visualization/ - Plot generation
   - src/utils/ - Shared utilities

3. **Testing:** pytest in tests/
   - Unit tests for utility functions
   - Integration tests for pipeline
   - Mock external services

4. **Documentation:** docs/ with auto-generated API docs
   - Sphinx for HTML generation
   - docstrings on all public functions
   - Examples in README.md

## Commands
| Task | Command |
|------|---------|
| Notebooks | jupyter lab |
| Tests | pytest -v --cov=src |
| Lint | flake8 src/ tests/ |
| Type Check | mypy src/ |
| Build Docs | cd docs && make html |
| Clean | find . -name __pycache__ -type d -exec rm -rf {} + |

## Quality Gates (Pre-commit)
```bash
flake8 src/ tests/ && \
mypy src/ && \
pytest -v --cov=src --cov-fail-under=80
```

## Reproducibility
- Fix random seeds in experiments
- Pin package versions in environment.yml
- Document data sources and preprocessing
- Version large datasets with DVC if needed
```

### Example 2: Node.js/TypeScript Project

```markdown
# System Prompt - WebApp

## Stack
- Node 18+, TypeScript 5+
- Next.js 14 for frontend
- NestJS 10+ for backend
- PostgreSQL 15+ with Prisma ORM
- Jest for testing
- pnpm for package management

## Quality Gates (Pre-commit)
```bash
npm run lint && \
npm run type-check && \
npm run test && \
npm run build
```

## Feature Workflow
1. Create feature branch: `git checkout -b feature/name`
2. Implement + write tests
3. Create PR with linked GitHub issue
4. Require 2+ approvals
5. Run e2e tests in staging
6. Merge with squash
7. Auto-deploy to production (GitHub Actions)

## Deployment
Automatic on merge to main:
1. GitHub Actions builds and tests
2. Build artifacts uploaded to S3
3. Deploy to staging environment
4. Run e2e tests
5. Approval needed for production deploy
6. Deploy to production
7. Monitor error rates for 5 minutes

## Commands
| Task | Command |
|------|---------|
| Dev | pnpm dev |
| Tests | pnpm test |
| Lint | pnpm lint |
| Type Check | pnpm type-check |
| E2E Tests | pnpm test:e2e |
| Build | pnpm build |
| Analyze | pnpm analyze |

## Environment Variables
**Frontend (.env.local):**
- NEXT_PUBLIC_API_URL (public)
- NEXT_PUBLIC_GA_ID (public)

**Backend (.env):**
- DATABASE_URL (required)
- JWT_SECRET (required)
- REDIS_URL (optional)
- LOG_LEVEL (optional)

**File:** Never commit .env, use .env.example
```

### Example 3: Rust Systems Project

```markdown
# System Prompt - RustyTools

## Stack
- Rust 1.70+ (latest stable)
- Cargo for package management
- Tokio for async runtime
- sqlx for database access
- Serde for serialization
- Tracing for observability

## Testing Strategy
- Unit tests inline with code
- Integration tests in tests/ directory
- Benchmarks in benches/ directory
- Property-based testing with proptest
- Minimum 75% code coverage

## Quality Gates (Pre-commit)
```bash
cargo fmt --check && \
cargo clippy --all-targets -- -D warnings && \
cargo test --lib && \
cargo test --doc && \
cargo build --release
```

## Performance Considerations
- No unsafe code without documentation
- Use references to avoid unnecessary copies
- Lazy initialization for heavy resources
- Benchmark-driven optimizations

## Commands
| Task | Command |
|------|---------|
| Build | cargo build --release |
| Tests | cargo test --all |
| Benchmark | cargo bench |
| Lint | cargo clippy |
| Format | cargo fmt |
| Doc | cargo doc --open |
| Release | cargo release --execute |

## Documentation
- Rust docs on all public APIs
- Architecture decision records in docs/adr/
- Performance notes in docs/performance.md
- CONTRIBUTING.md for contributors
```

---

## Management

### Getting Active Prompt Info

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Get active prompt (project override OR plugin default)
prompt = sdk.system_prompts.get_active()
if prompt:
    print(f"Active prompt ({len(prompt)} chars):")
    print(prompt[:200] + "...")

# Get plugin default
default = sdk.system_prompts.get_default()
print(f"Plugin default available: {default is not None}")

# Get project override (if exists)
project = sdk.system_prompts.get_project()
print(f"Project override exists: {project is not None}")

# Get statistics
stats = sdk.system_prompts.get_stats()
print(f"Source: {stats['source']}")
print(f"Tokens: {stats['tokens']}")
```

### Resetting to Plugin Default

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Delete project override (falls back to plugin default)
if sdk.system_prompts.delete():
    print("Deleted project override, using plugin default")
else:
    print("No project override to delete")
```

Or via command line:

```bash
# Remove project override
rm .claude/system-prompt.md

# Verify plugin default is available
uv run python -c "
from htmlgraph import SDK
default = SDK().system_prompts.get_default()
print(f'Plugin default available: {default is not None}')
"
```

### Version Control

Commit your system prompt to git for team standardization:

```bash
# Add to git
git add .claude/system-prompt.md

# Commit
git commit -m "docs: add project system prompt"

# Push
git push origin main
```

All team members will automatically use the project prompt on their next session.

---

## FAQ

### Q: What if both project and plugin prompts exist?
**A:** Project override takes precedence. The hook loads project first, then falls back to plugin default.

### Q: How large can my system prompt be?
**A:** Recommended limit is 1000 tokens. SDK validation warns above this threshold. Smaller is better—each token in your system prompt is one less token available for actual work.

### Q: Can I include multi-line code blocks?
**A:** Yes, use standard markdown code blocks. All text is counted in token budget, including code examples.

### Q: Does the prompt survive session compacts?
**A:** Yes. The SessionStart hook re-injects the prompt at every session start, including after Claude Code compacts and resume cycles.

### Q: Can I have different prompts for different tasks?
**A:** Not yet, but future enhancements will support prompt variants for different model types and specialized tasks.

### Q: How do I test my custom prompt?
**A:** Start a new session after creating `.claude/system-prompt.md`. The hook will load it automatically.

### Q: What happens if my prompt has a syntax error?
**A:** The hook gracefully degrades—if your prompt can't be loaded, it falls back to the plugin default.

### Q: Can I include HTML or special characters?
**A:** Yes. Your prompt is markdown, and it's injected as-is. Standard markdown syntax is supported.

### Q: How do I ensure consistency across team members?
**A:** Commit `.claude/system-prompt.md` to git. All team members will automatically use the team prompt on their next session.

---

## Troubleshooting

### Prompt Not Loading

1. **Check file exists:**
   ```bash
   ls -la .claude/system-prompt.md
   ```

2. **Check permissions:**
   ```bash
   chmod 644 .claude/system-prompt.md
   ```

3. **Validate syntax:**
   ```bash
   uv run python -c "
   from htmlgraph import SDK
   result = SDK().system_prompts.validate()
   print(result['message'])
   for w in result['warnings']:
       print(f'  - {w}')
   "
   ```

4. **Check logs:**
   Look for "System prompt" messages in Claude Code debug output

### Token Count Too High

1. Remove redundant sections
2. Replace detailed examples with links to documentation
3. Use shorter section headers
4. Consolidate similar rules

**Example reduction:**
```
Before: "When you encounter a problem, always read the documentation first..."
After: "Read docs first"
Result: 50% token savings
```

### Plugin Default Not Loading

1. **Verify plugin installed:**
   ```bash
   claude plugin list | grep htmlgraph
   ```

2. **Check plugin version:**
   ```bash
   claude plugin status htmlgraph
   ```

3. **Update plugin:**
   ```bash
   claude plugin update htmlgraph
   ```

4. **Reinstall if corrupted:**
   ```bash
   claude plugin uninstall htmlgraph
   claude plugin install htmlgraph
   ```

### Different Behavior Than Expected

1. **Verify active prompt:**
   ```bash
   uv run python -c "
   from htmlgraph import SDK
   stats = SDK().system_prompts.get_stats()
   print(f'Source: {stats[\"source\"]}')
   "
   ```

2. **Check if project override is being used:**
   ```bash
   ls -la .claude/system-prompt.md
   ```

3. **Read active prompt:**
   ```bash
   uv run python -c "
   from htmlgraph import SDK
   print(SDK().system_prompts.get_active())
   "
   ```

---

## Best Practices

1. **Keep it concise** - More tokens in system prompt = fewer tokens for actual work
2. **Focus on team standards** - Plugin default covers general guidance
3. **Make it actionable** - Include specific commands, not abstract rules
4. **Version it** - Commit to git so team members stay in sync
5. **Validate before committing** - Run validation before git commit
6. **Review regularly** - Revisit annually to remove outdated guidance
7. **Document decisions** - Comment why specific rules exist

---

## Related Documentation

- `/system-prompt-architecture-refactoring.md` - Technical architecture and implementation
- `/AGENTS.md` - HtmlGraph SDK reference
- `.claude/system-prompt.md` - This project's system prompt

---

## See Also

- Plugin Default: `packages/claude-plugin/.claude-plugin/system-prompt-default.md`
- SDK Reference: `src/python/htmlgraph/system_prompts.py`
- Hook Implementation: `packages/claude-plugin/hooks/scripts/session-start.py`
