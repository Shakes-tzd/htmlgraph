# HtmlGraph Common Command Definitions

**DRY (Don't Repeat Yourself) Command System**

This directory contains the **single source of truth** for all HtmlGraph slash commands across all agent platforms (Claude Code, Codex, Gemini).

## Architecture

```
packages/common/
├── command_definitions/      # YAML definitions (SOURCE OF TRUTH)
│   ├── plan.yaml
│   ├── spike.yaml
│   └── recommend.yaml
│
├── generators/               # Platform-specific generators
│   └── generate_commands.py
│
└── README.md                 # This file
```

## Workflow

### 1. Define Command (YAML)

All commands are defined in `command_definitions/*.yaml` with:
- Parameters and types
- Usage examples
- SDK method mapping
- Platform-specific behavior
- Output templates

**Example:** `command_definitions/plan.yaml`

```yaml
name: plan
short_description: Start planning a new track
parameters:
  - name: description
    required: true
    type: string
sdk_method: smart_plan
```

### 2. Generate Platform Files

Run the generator to create platform-specific command files:

```bash
# Generate for all platforms
uv run python packages/common/generators/generate_commands.py

# Generate for specific platform
uv run python packages/common/generators/generate_commands.py --platform claude
```

This creates:
- `packages/claude-plugin/commands/*.md` - Claude Code slash commands
- `packages/codex-skill/command_*.md` - Codex command sections
- `packages/gemini-extension/command_*.md` - Gemini command sections

### 3. Integrate (if needed)

For Codex and Gemini, manually integrate the generated sections into:
- `packages/codex-skill/SKILL.md`
- `packages/gemini-extension/GEMINI.md`

(Can be automated with markers in future versions)

## Benefits

✅ **Single Source of Truth** - Define once, generate everywhere
✅ **Consistency** - All platforms have identical functionality
✅ **Maintainability** - Update in one place, regenerate all
✅ **Version Control** - Track command evolution in YAML
✅ **Documentation** - YAML serves as spec and implementation

## Adding a New Command

1. Create `command_definitions/new_command.yaml`:
   ```yaml
   name: my_command
   short_description: What it does
   parameters:
     - name: param1
       required: true
       type: string
   sdk_method: method_name
   ```

2. Implement SDK method in `src/python/htmlgraph/sdk.py`:
   ```python
   def method_name(self, param1: str) -> dict[str, Any]:
       # Implementation
       pass
   ```

3. Generate command files:
   ```bash
   uv run python packages/common/generators/generate_commands.py
   ```

4. Test on all platforms

5. Commit both YAML and generated files

## Available Commands

| Command | Description | SDK Method |
|---------|-------------|------------|
| `/htmlgraph:plan` | Start planning with spike or track | `smart_plan()` |
| `/htmlgraph:spike` | Create research spike | `start_planning_spike()` |
| `/htmlgraph:recommend` | Get work recommendations | `recommend_next_work()` |

## Build Integration

### Pre-publish Hook

Add to `pyproject.toml` or publishing workflow:

```bash
# Regenerate commands before publishing
uv run python packages/common/generators/generate_commands.py

# Verify changes
git diff packages/*/commands/
git diff packages/*/command_*.md
```

### CI/CD Check

Add to GitHub Actions:

```yaml
- name: Check command sync
  run: |
    uv run python packages/common/generators/generate_commands.py
    git diff --exit-code packages/ || \
      (echo "Commands out of sync! Run generator." && exit 1)
```

## Future Enhancements

- [ ] Auto-inject sections into skill docs (markers)
- [ ] Validate YAML schemas
- [ ] Generate tests from command definitions
- [ ] Type-safe parameter parsing
- [ ] Multi-language support (if needed)

## Philosophy

> "The best code is code you don't have to write three times."

By maintaining commands as data (YAML), we separate:
- **What** the command does (definition)
- **How** it's presented (generation)
- **Where** it runs (platform)

This makes the system more maintainable, testable, and extensible.
