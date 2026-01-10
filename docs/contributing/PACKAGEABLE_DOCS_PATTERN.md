# Packageable Auto-Updating Documentation Pattern

**A comprehensive guide for package developers implementing versioned, customizable, auto-updating agent documentation systems**

---

## 1. Introduction

### What is Packageable Auto-Updating Documentation?

Packageable auto-updating documentation is a pattern for distributing AI agent instructions that:

1. **Ship with the package** - Documentation lives in the package, not external docs sites
2. **Auto-update** - Users get latest best practices when upgrading packages
3. **Preserve customizations** - User modifications survive package updates
4. **Version intelligently** - Track both package version and documentation schema version
5. **Migrate safely** - Guide users through breaking documentation changes

This pattern is particularly valuable for AI agent tools (Claude Code plugins, MCP servers, Gemini extensions) where the "documentation" is actually executable instructions that agents consume.

### Why This Pattern Matters

**Traditional documentation problems:**
- Users read docs once, never check for updates
- Breaking changes in APIs require manual doc updates
- No way to know if user's local instructions are stale
- Customizations get lost when copying new examples

**Agent documentation challenges:**
- Instructions are consumed programmatically, not read by humans
- Stale instructions cause agent failures
- Context budget limits require careful documentation design
- Users need to customize for their workflows
- Package updates must not break user customizations

**This pattern solves:**
- ✅ Automatic delivery of documentation improvements
- ✅ Safe preservation of user customizations
- ✅ Clear upgrade paths for breaking changes
- ✅ Version compatibility tracking
- ✅ Rollback safety for failed migrations

### Use Cases and Benefits

**Ideal for:**
1. **AI Agent Plugins** - Claude Code plugins, MCP servers, Gemini extensions
2. **CLI Tools** - Developer tools with complex configuration
3. **SDK Libraries** - Packages with agent integration
4. **Framework Starters** - Project templates that evolve

**Benefits:**
- **Users** - Always have up-to-date best practices
- **Maintainers** - Deprecate old patterns safely
- **Ecosystem** - Shared improvements propagate automatically

### When to Use This Pattern

**✅ Use this pattern when:**
- Documentation is consumed by AI agents programmatically
- Package updates include documentation improvements
- Users need to customize documentation for their needs
- You need to track documentation schema evolution
- Context budget matters (token limits)

**❌ Simpler approaches work when:**
- Documentation is only for human reading
- No user customization needed
- Package updates rarely affect documentation
- Documentation is stateless (no version tracking needed)

**Decision framework:**
```
Does your package provide AI agent instructions? YES → Continue
Do you expect to improve those instructions over time? YES → Continue
Do users need to customize instructions? YES → Continue
Is there a context budget concern? YES → Use this pattern

Otherwise: Use simple static documentation
```

---

## 2. Architecture Overview

### Two-Tier System

The pattern uses a **two-tier system** where package-provided templates combine with user customizations:

```
┌─────────────────────────────────────────────────────────┐
│                    USER PROJECT                          │
│  .claude/                                                │
│    ├── CLAUDE.md (generated, user can override blocks)  │
│    ├── .claude-docs-meta.json (version tracking)        │
│    └── templates/ (optional user overrides)             │
│        └── claude.md.jinja2 (custom blocks)             │
└─────────────────┬───────────────────────────────────────┘
                  │ extends (Jinja2 inheritance)
┌─────────────────┴───────────────────────────────────────┐
│                 PACKAGE DISTRIBUTION                     │
│  your_package/                                           │
│    ├── templates/                                        │
│    │   ├── base/                                         │
│    │   │   └── claude.md.jinja2 (base template)         │
│    │   └── platforms/                                    │
│    │       ├── gemini.md.jinja2                          │
│    │       └── codex.md.jinja2                           │
│    ├── migrations/                                       │
│    │   ├── 001_initial.py                               │
│    │   └── 002_add_orchestration.py                     │
│    └── cli.py (generate/upgrade commands)               │
└─────────────────────────────────────────────────────────┘
```

### Template Inheritance Model

**Base Template** (in package):
```jinja2
{# your_package/templates/base/claude.md.jinja2 #}
# {{ package_name }} - Claude Code Instructions

## Quick Start
{% block quickstart %}
Default quickstart content from package...
{% endblock %}

## Configuration
{% block configuration %}
Default configuration from package...
{% endblock %}

## Advanced Usage
{% block advanced %}
Default advanced usage from package...
{% endblock %}
```

**User Override** (in project):
```jinja2
{# .claude/templates/claude.md.jinja2 #}
{% extends "base/claude.md.jinja2" %}

{# Override just the configuration block #}
{% block configuration %}
## My Custom Configuration
- Custom setting 1
- Custom setting 2

{{ super() }}  {# Include package defaults too #}
{% endblock %}
```

**Result** - User gets:
- Package's quickstart (default)
- User's custom configuration + package defaults
- Package's advanced usage (default)

### Version Tracking

**Dual versioning system:**

1. **Package Version** (`0.9.5`) - Tracks package releases
2. **Doc Schema Version** (`2`) - Tracks documentation structure changes

```python
# Stored in .claude/.claude-docs-meta.json
{
  "version": "2",           # Doc schema version
  "package_version": "0.9.5",  # Package version when generated
  "generated_at": "2025-01-02T10:30:00Z",
  "platform": "claude",
  "has_customizations": true,
  "customization_blocks": ["configuration", "advanced"],
  "last_migration": "002_add_orchestration"
}
```

**Why dual versioning?**
- Package version changes frequently (bug fixes, features)
- Doc schema version changes rarely (structure changes only)
- Allows N-1 compatibility (old docs work with new package)

### Version Compatibility Matrix

```python
COMPATIBILITY_MATRIX = {
    "1": {  # Doc schema version 1
        "min_package": "0.1.0",
        "max_package": "0.8.9",
        "description": "Original single-file format"
    },
    "2": {  # Doc schema version 2
        "min_package": "0.9.0",
        "max_package": None,  # Current
        "description": "Template-based with blocks"
    }
}
```

### Context Budget Management

**Challenge:** AI agents have token limits (context budget).

**Strategy:** Progressive disclosure with template blocks

```jinja2
{# Base template - always included (high priority) #}
## Core Concepts
Essential information agents always need...

{# Optional blocks - user can exclude #}
{% block advanced_patterns %}
Advanced patterns for power users...
{% endblock %}

{% block troubleshooting %}
Detailed troubleshooting guide...
{% endblock %}

{% block examples %}
Comprehensive examples...
{% endblock %}
```

**User customization to reduce context:**
```jinja2
{% extends "base/claude.md.jinja2" %}

{# Exclude heavy blocks to save tokens #}
{% block examples %}{% endblock %}
{% block troubleshooting %}{% endblock %}
```

### Visual System Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    Package Release                        │
│  1. Developer updates base templates                     │
│  2. Creates migration script if schema changes           │
│  3. Bumps doc_schema_version if needed                   │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│              User Runs: pip install --upgrade             │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│         CLI Command: your-package docs upgrade           │
│  1. Detect current doc version                           │
│  2. Compare with package doc version                     │
│  3. Detect user customizations                           │
│  4. Run migration scripts if needed                      │
│  5. Regenerate docs preserving customizations            │
│  6. Update metadata                                      │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│                  User Gets Updated Docs                   │
│  - Latest package improvements                           │
│  - User customizations preserved                         │
│  - Version metadata updated                              │
│  - Rollback available if issues                          │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Guide

### 3.1 Template System Setup

#### Directory Structure

```
your_package/
├── templates/
│   ├── base/
│   │   ├── claude.md.jinja2       # Base template for Claude
│   │   ├── gemini.md.jinja2       # Base template for Gemini
│   │   └── shared/
│   │       ├── quickstart.md.jinja2
│   │       └── api-reference.md.jinja2
│   └── platforms/                  # Platform-specific extensions
│       └── claude-advanced.md.jinja2
├── migrations/
│   ├── __init__.py
│   ├── base.py                     # MigrationScript base class
│   ├── 001_initial.py
│   └── 002_add_orchestration.py
├── models.py                       # DocsMetadata Pydantic model
├── template_engine.py              # DocTemplateEngine class
└── cli.py                          # CLI commands
```

#### Base Template Creation with Jinja2

**Example base template:**

```jinja2
{# your_package/templates/base/claude.md.jinja2 #}
{#
  Base template for Claude Code documentation
  Users can override any {% block %} in their local templates
#}

# {{ package_name }} v{{ package_version }}

{% block header %}
**AI-Powered {{ package_name }} for Claude Code**

This documentation is auto-generated from package version {{ package_version }}.
Last updated: {{ generated_at }}
{% endblock %}

---

## Quick Start
{% block quickstart %}
```bash
# Install the package
pip install {{ package_name }}

# Initialize documentation
{{ package_name }} docs generate

# Verify setup
{{ package_name }} docs version
```
{% endblock %}

---

## Configuration
{% block configuration %}
### Basic Configuration

The package looks for configuration in:
1. `.{{ package_name }}/config.json`
2. Environment variables prefixed with `{{ package_name.upper() }}_`

**Example config.json:**
```json
{
  "agent_name": "claude",
  "features_enabled": ["tracking", "analytics"],
  "auto_update_docs": true
}
```
{% endblock %}

---

## Core Concepts
{% block core_concepts %}
### How {{ package_name }} Works

1. **Concept A** - Explanation...
2. **Concept B** - Explanation...
3. **Concept C** - Explanation...
{% endblock %}

---

## API Reference
{% block api_reference %}
### Main Classes

#### `SDK` Class
```python
from {{ package_name }} import SDK

sdk = SDK(agent="claude")
```

**Methods:**
- `create_feature()` - Create a new feature
- `create_spike()` - Create a research spike
{% endblock %}

---

## Advanced Usage
{% block advanced %}
### Advanced Patterns

{% block orchestration %}
#### Orchestration Mode
For complex multi-agent workflows...
{% endblock %}

{% block analytics %}
#### Strategic Analytics
Analyze your workflow effectiveness...
{% endblock %}
{% endblock %}

---

## Troubleshooting
{% block troubleshooting %}
### Common Issues

**Issue 1: Docs out of date**
```bash
{{ package_name }} docs upgrade
```

**Issue 2: Customizations lost**
```bash
{{ package_name }} docs rollback
```
{% endblock %}

---

## Customization Guide
{% block customization_guide %}
### How to Customize This Documentation

1. Create `.claude/templates/claude.md.jinja2`
2. Extend the base template:
   ```jinja2
   {%raw%}{% extends "base/claude.md.jinja2" %}{%endraw%}

   {%raw%}{% block configuration %}{%endraw%}
   ## My Custom Configuration
   ...
   {%raw%}{% endblock %}{%endraw%}
   ```
3. Regenerate: `{{ package_name }} docs generate`
{% endblock %}

---

{% block footer %}
**Documentation Version:** {{ doc_version }}
**Package Version:** {{ package_version }}
**Generated:** {{ generated_at }}
{% endblock %}
```

#### Block-Based Structure for User Overrides

**Design principles:**

1. **Granular blocks** - Each section should be independently overridable
2. **Nested blocks** - Allow partial overrides
3. **Semantic naming** - Block names should describe content, not structure
4. **Safe defaults** - Empty blocks should not break documentation

**Example nested blocks:**
```jinja2
{% block advanced %}
### Advanced Usage

{% block orchestration %}
#### Orchestration Mode
Default orchestration docs...
{% endblock %}

{% block analytics %}
#### Analytics
Default analytics docs...
{% endblock %}

{% block custom_workflows %}
{# Empty by default - users can add custom content #}
{% endblock %}
{% endblock %}
```

**User can override at any level:**
```jinja2
{# Override entire advanced section #}
{% block advanced %}
My completely custom advanced docs...
{% endblock %}

{# OR override just orchestration #}
{% block orchestration %}
My custom orchestration docs...
{% endblock %}

{# OR add custom workflows while keeping defaults #}
{% block custom_workflows %}
## My Custom Workflows
- Workflow 1
- Workflow 2
{% endblock %}
```

#### ChoiceLoader Priority System

**Implementation:**

```python
# your_package/template_engine.py
from jinja2 import Environment, FileSystemLoader, ChoiceLoader
from pathlib import Path

class DocTemplateEngine:
    def __init__(self, package_name: str, project_root: Path):
        self.package_name = package_name
        self.project_root = project_root

        # Package templates (bundled with distribution)
        package_templates = Path(__file__).parent / "templates"

        # User templates (in project directory)
        user_templates = project_root / f".{package_name}" / "templates"
        user_templates.mkdir(parents=True, exist_ok=True)

        # Priority: User templates first, then package templates
        loader = ChoiceLoader([
            FileSystemLoader(str(user_templates)),
            FileSystemLoader(str(package_templates))
        ])

        self.env = Environment(
            loader=loader,
            autoescape=False,  # We're generating Markdown
            trim_blocks=True,
            lstrip_blocks=True
        )

    def render(self, template_name: str, context: dict) -> str:
        """Render template with user overrides taking priority"""
        template = self.env.get_template(template_name)
        return template.render(**context)

    def has_user_template(self, template_name: str) -> bool:
        """Check if user has custom template"""
        user_path = (
            self.project_root /
            f".{self.package_name}" /
            "templates" /
            template_name
        )
        return user_path.exists()
```

**Usage:**
```python
engine = DocTemplateEngine("htmlgraph", Path.cwd())

context = {
    "package_name": "htmlgraph",
    "package_version": "0.9.5",
    "doc_version": "2",
    "generated_at": datetime.now().isoformat()
}

# Renders user template if exists, falls back to package template
output = engine.render("base/claude.md.jinja2", context)
```

---

### 3.2 Version Tracking

#### Dual Versioning Model Design

**DocsMetadata Pydantic Model:**

```python
# your_package/models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import json

class DocsMetadata(BaseModel):
    """
    Tracks documentation version and customization state.

    Dual versioning:
    - doc_version: Schema version (changes when structure changes)
    - package_version: Package version when docs were generated

    This allows N-1 compatibility where old docs work with new packages
    as long as doc_version is compatible.
    """

    doc_version: str = Field(
        description="Documentation schema version (e.g., '2')"
    )

    package_version: str = Field(
        description="Package version when generated (e.g., '0.9.5')"
    )

    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of generation"
    )

    platform: str = Field(
        default="claude",
        description="Target platform (claude, gemini, codex, etc.)"
    )

    has_customizations: bool = Field(
        default=False,
        description="Whether user has custom template overrides"
    )

    customization_blocks: List[str] = Field(
        default_factory=list,
        description="List of template blocks user has customized"
    )

    last_migration: Optional[str] = Field(
        default=None,
        description="ID of last migration applied (e.g., '002_add_orchestration')"
    )

    backup_path: Optional[str] = Field(
        default=None,
        description="Path to backup created before last update"
    )

    @classmethod
    def load(cls, path: Path) -> Optional["DocsMetadata"]:
        """Load metadata from .claude-docs-meta.json"""
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            print(f"Warning: Failed to load metadata: {e}")
            return None

    def save(self, path: Path) -> None:
        """Save metadata to .claude-docs-meta.json"""
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(
                self.model_dump(mode="json"),
                f,
                indent=2,
                default=str  # Handle datetime serialization
            )

    def is_compatible_with_package(self, package_version: str) -> bool:
        """Check if docs are compatible with given package version"""
        from packaging import version

        # Get compatibility matrix for this doc version
        compat = VERSION_COMPATIBILITY.get(self.doc_version)
        if not compat:
            return False

        pkg_ver = version.parse(package_version)
        min_ver = version.parse(compat["min_package"])
        max_ver = (
            version.parse(compat["max_package"])
            if compat["max_package"]
            else None
        )

        if pkg_ver < min_ver:
            return False
        if max_ver and pkg_ver > max_ver:
            return False

        return True

    def needs_upgrade(self, current_doc_version: str) -> bool:
        """Check if docs need upgrading to current version"""
        from packaging import version
        return version.parse(self.doc_version) < version.parse(current_doc_version)
```

#### Version Compatibility Matrix

```python
# your_package/models.py

VERSION_COMPATIBILITY = {
    "1": {
        "min_package": "0.1.0",
        "max_package": "0.8.9",
        "description": "Original single-file CLAUDE.md format",
        "breaking_changes": [
            "No template system",
            "No customization support",
            "Manual updates only"
        ]
    },
    "2": {
        "min_package": "0.9.0",
        "max_package": None,  # Current version
        "description": "Template-based with Jinja2 blocks",
        "features": [
            "User customization via template inheritance",
            "Auto-update with migration support",
            "Version tracking and rollback"
        ],
        "breaking_changes": [
            "File location changed to .claude/CLAUDE.md",
            "Metadata file required (.claude-docs-meta.json)",
            "Custom blocks must use Jinja2 syntax"
        ]
    }
}

CURRENT_DOC_VERSION = "2"

def get_version_info(doc_version: str) -> dict:
    """Get compatibility info for a doc version"""
    return VERSION_COMPATIBILITY.get(doc_version, {})

def get_migration_path(from_version: str, to_version: str) -> List[str]:
    """
    Get list of migration scripts needed to upgrade.

    Example: from_version="1", to_version="2"
    Returns: ["001_to_002"]
    """
    from packaging import version

    from_ver = int(from_version)
    to_ver = int(to_version)

    if from_ver >= to_ver:
        return []

    # Return migration scripts in order
    migrations = []
    for v in range(from_ver, to_ver):
        migration_id = f"{v:03d}_to_{v+1:03d}"
        migrations.append(migration_id)

    return migrations
```

#### Migration Script Architecture

**Base Migration Class:**

```python
# your_package/migrations/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import shutil
from datetime import datetime

class MigrationScript(ABC):
    """
    Base class for documentation migration scripts.

    Each migration handles upgrading from one doc version to the next,
    while preserving user customizations.
    """

    # Subclasses must define these
    from_version: str
    to_version: str
    description: str

    def __init__(self, project_root: Path, package_name: str):
        self.project_root = project_root
        self.package_name = package_name
        self.docs_dir = project_root / f".{package_name}"

    @abstractmethod
    def detect_customizations(self) -> dict:
        """
        Detect what customizations user has made.

        Returns dict with structure like:
        {
            "has_customizations": bool,
            "customized_blocks": List[str],
            "custom_sections": dict,
            "custom_config": dict
        }
        """
        pass

    @abstractmethod
    def migrate(self, customizations: dict) -> bool:
        """
        Perform the migration, preserving customizations.

        Returns True if successful, False otherwise.
        """
        pass

    def backup(self) -> Path:
        """Create backup before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.docs_dir / "backups" / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup all files in docs directory
        for file in self.docs_dir.iterdir():
            if file.is_file():
                shutil.copy2(file, backup_dir / file.name)

        print(f"✅ Backup created: {backup_dir}")
        return backup_dir

    def rollback(self, backup_path: Path) -> bool:
        """Restore from backup"""
        if not backup_path.exists():
            print(f"❌ Backup not found: {backup_path}")
            return False

        try:
            # Restore all files from backup
            for file in backup_path.iterdir():
                if file.is_file():
                    shutil.copy2(file, self.docs_dir / file.name)

            print(f"✅ Restored from backup: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False

    def run(self) -> bool:
        """Execute migration with backup and error handling"""
        print(f"\n🔄 Migration: {self.description}")
        print(f"   From version {self.from_version} → {self.to_version}")

        # Create backup
        backup_path = self.backup()

        try:
            # Detect customizations
            print("   Detecting customizations...")
            customizations = self.detect_customizations()

            if customizations.get("has_customizations"):
                print(f"   Found customizations: {customizations['customized_blocks']}")
            else:
                print("   No customizations detected")

            # Perform migration
            print("   Migrating documentation...")
            success = self.migrate(customizations)

            if success:
                print("✅ Migration completed successfully")
                return True
            else:
                print("❌ Migration failed, rolling back...")
                self.rollback(backup_path)
                return False

        except Exception as e:
            print(f"❌ Migration error: {e}")
            print("   Rolling back...")
            self.rollback(backup_path)
            return False
```

#### Example Migration Implementation

```python
# your_package/migrations/002_add_orchestration.py
from .base import MigrationScript
from pathlib import Path
import re

class Migration002AddOrchestration(MigrationScript):
    """
    Migration from doc version 1 to 2.

    Changes:
    - Add orchestration section to documentation
    - Convert single-file to template-based system
    - Preserve user's custom configuration blocks
    """

    from_version = "1"
    to_version = "2"
    description = "Add orchestration patterns and convert to template system"

    def detect_customizations(self) -> dict:
        """Detect customizations in version 1 docs"""
        old_doc_path = self.docs_dir / "CLAUDE.md"

        if not old_doc_path.exists():
            return {"has_customizations": False}

        content = old_doc_path.read_text()

        # Look for custom sections (marked with specific headers)
        custom_sections = {}

        # Detect custom configuration
        config_match = re.search(
            r"## My Configuration\n(.*?)(?=\n##|\Z)",
            content,
            re.DOTALL
        )
        if config_match:
            custom_sections["configuration"] = config_match.group(1).strip()

        # Detect custom workflows
        workflow_match = re.search(
            r"## My Workflows\n(.*?)(?=\n##|\Z)",
            content,
            re.DOTALL
        )
        if workflow_match:
            custom_sections["workflows"] = workflow_match.group(1).strip()

        return {
            "has_customizations": bool(custom_sections),
            "customized_blocks": list(custom_sections.keys()),
            "custom_sections": custom_sections
        }

    def migrate(self, customizations: dict) -> bool:
        """
        Migrate to template-based system with customizations.
        """
        from ..template_engine import DocTemplateEngine
        from ..models import DocsMetadata, CURRENT_DOC_VERSION
        from importlib.metadata import version

        # Initialize template engine
        engine = DocTemplateEngine(self.package_name, self.project_root)

        # If user has customizations, create custom template
        if customizations.get("has_customizations"):
            self._create_custom_template(customizations["custom_sections"])

        # Generate new documentation
        context = {
            "package_name": self.package_name,
            "package_version": version(self.package_name),
            "doc_version": self.to_version,
            "generated_at": datetime.now().isoformat()
        }

        new_content = engine.render("base/claude.md.jinja2", context)

        # Write new documentation
        new_doc_path = self.docs_dir / "CLAUDE.md"
        new_doc_path.write_text(new_content)

        # Update metadata
        metadata = DocsMetadata(
            doc_version=self.to_version,
            package_version=context["package_version"],
            platform="claude",
            has_customizations=customizations.get("has_customizations", False),
            customization_blocks=customizations.get("customized_blocks", []),
            last_migration=f"{self.from_version}_to_{self.to_version}"
        )
        metadata.save(self.docs_dir / ".claude-docs-meta.json")

        # Archive old documentation
        old_doc_path = self.docs_dir / "CLAUDE.md.v1"
        if (self.docs_dir / "CLAUDE.md").exists():
            shutil.move(
                self.docs_dir / "CLAUDE.md",
                old_doc_path
            )

        return True

    def _create_custom_template(self, custom_sections: dict) -> None:
        """Create user template with customizations"""
        templates_dir = self.docs_dir / "templates"
        templates_dir.mkdir(exist_ok=True)

        template_content = "{% extends 'base/claude.md.jinja2' %}\n\n"

        # Add custom blocks
        for block_name, content in custom_sections.items():
            template_content += f"{{% block {block_name} %}}\n"
            template_content += f"{content}\n"
            template_content += "{% endblock %}\n\n"

        template_path = templates_dir / "claude.md.jinja2"
        template_path.write_text(template_content)

        print(f"   Created custom template: {template_path}")
```

---

### 3.3 CLI Integration

#### Command Structure

```python
# your_package/cli.py
import click
from pathlib import Path
from .template_engine import DocTemplateEngine
from .models import DocsMetadata, CURRENT_DOC_VERSION, get_migration_path
from .migrations import get_migration, list_migrations
from importlib.metadata import version

@click.group()
def docs():
    """Documentation management commands"""
    pass

@docs.command()
@click.option(
    "--platform",
    default="claude",
    type=click.Choice(["claude", "gemini", "codex"]),
    help="Target platform"
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing documentation"
)
def generate(platform: str, force: bool):
    """
    Generate agent documentation from package templates.

    Example:
        your-package docs generate
        your-package docs generate --platform gemini
        your-package docs generate --force
    """
    project_root = Path.cwd()
    package_name = "your_package"  # Replace with your package name
    docs_dir = project_root / f".{package_name.replace('_', '-')}"

    # Check if docs already exist
    doc_path = docs_dir / f"{platform.upper()}.md"
    meta_path = docs_dir / ".claude-docs-meta.json"

    if doc_path.exists() and not force:
        click.echo(f"❌ Documentation already exists: {doc_path}")
        click.echo(f"   Use --force to overwrite or 'docs upgrade' to update")
        return

    # Initialize template engine
    engine = DocTemplateEngine(package_name, project_root)

    # Prepare context
    context = {
        "package_name": package_name,
        "package_version": version(package_name),
        "doc_version": CURRENT_DOC_VERSION,
        "generated_at": datetime.now().isoformat(),
        "platform": platform
    }

    # Render template
    click.echo(f"📝 Generating {platform} documentation...")
    content = engine.render(f"base/{platform}.md.jinja2", context)

    # Write documentation
    docs_dir.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(content)

    # Save metadata
    metadata = DocsMetadata(
        doc_version=CURRENT_DOC_VERSION,
        package_version=context["package_version"],
        platform=platform,
        has_customizations=False
    )
    metadata.save(meta_path)

    click.echo(f"✅ Documentation generated: {doc_path}")
    click.echo(f"📋 Metadata saved: {meta_path}")

@docs.command()
def version():
    """
    Show current documentation version and status.

    Example:
        your-package docs version
    """
    project_root = Path.cwd()
    package_name = "your_package"
    docs_dir = project_root / f".{package_name.replace('_', '-')}"
    meta_path = docs_dir / ".claude-docs-meta.json"

    # Load metadata
    metadata = DocsMetadata.load(meta_path)

    if not metadata:
        click.echo("❌ No documentation found. Run 'docs generate' first.")
        return

    # Show version info
    click.echo(f"\n📊 Documentation Status\n")
    click.echo(f"Platform:          {metadata.platform}")
    click.echo(f"Doc Version:       {metadata.doc_version}")
    click.echo(f"Package Version:   {metadata.package_version}")
    click.echo(f"Generated:         {metadata.generated_at}")
    click.echo(f"Customizations:    {'Yes' if metadata.has_customizations else 'No'}")

    if metadata.has_customizations:
        click.echo(f"Custom Blocks:     {', '.join(metadata.customization_blocks)}")

    # Check if upgrade needed
    current_pkg_version = version(package_name)
    if metadata.package_version != current_pkg_version:
        click.echo(f"\n⚠️  Package upgraded: {metadata.package_version} → {current_pkg_version}")
        click.echo(f"   Run 'docs upgrade' to get latest documentation")

    if metadata.needs_upgrade(CURRENT_DOC_VERSION):
        click.echo(f"\n⚠️  Documentation schema outdated: {metadata.doc_version} → {CURRENT_DOC_VERSION}")
        click.echo(f"   Run 'docs upgrade' to migrate")

@docs.command()
@click.option(
    "--auto-confirm",
    is_flag=True,
    help="Skip confirmation prompts"
)
def upgrade(auto_confirm: bool):
    """
    Upgrade documentation to latest version, preserving customizations.

    Example:
        your-package docs upgrade
        your-package docs upgrade --auto-confirm
    """
    project_root = Path.cwd()
    package_name = "your_package"
    docs_dir = project_root / f".{package_name.replace('_', '-')}"
    meta_path = docs_dir / ".claude-docs-meta.json"

    # Load current metadata
    metadata = DocsMetadata.load(meta_path)
    if not metadata:
        click.echo("❌ No documentation found. Run 'docs generate' first.")
        return

    # Check if upgrade needed
    if not metadata.needs_upgrade(CURRENT_DOC_VERSION):
        click.echo("✅ Documentation is already up to date!")
        return

    # Get migration path
    migrations = get_migration_path(metadata.doc_version, CURRENT_DOC_VERSION)

    if not migrations:
        click.echo("❌ No migration path available")
        return

    # Show upgrade plan
    click.echo(f"\n📋 Upgrade Plan\n")
    click.echo(f"Current version:  {metadata.doc_version}")
    click.echo(f"Target version:   {CURRENT_DOC_VERSION}")
    click.echo(f"Migrations:       {' → '.join(migrations)}")

    if metadata.has_customizations:
        click.echo(f"\n⚠️  You have customizations that will be preserved:")
        for block in metadata.customization_blocks:
            click.echo(f"   - {block}")

    # Confirm
    if not auto_confirm:
        if not click.confirm("\nProceed with upgrade?"):
            click.echo("❌ Upgrade cancelled")
            return

    # Run migrations
    for migration_id in migrations:
        migration_class = get_migration(migration_id)
        if not migration_class:
            click.echo(f"❌ Migration not found: {migration_id}")
            return

        migration = migration_class(project_root, package_name)
        success = migration.run()

        if not success:
            click.echo(f"❌ Migration failed: {migration_id}")
            click.echo(f"   Documentation restored from backup")
            return

    click.echo(f"\n✅ Documentation upgraded successfully!")
    click.echo(f"   New version: {CURRENT_DOC_VERSION}")

@docs.command()
@click.option(
    "--backup-id",
    help="Specific backup to rollback to (YYYYMMDD_HHMMSS)"
)
def rollback(backup_id: str):
    """
    Rollback documentation to a previous backup.

    Example:
        your-package docs rollback --backup-id 20250102_103000
        your-package docs rollback  # Shows available backups
    """
    project_root = Path.cwd()
    package_name = "your_package"
    docs_dir = project_root / f".{package_name.replace('_', '-')}"
    backups_dir = docs_dir / "backups"

    if not backups_dir.exists():
        click.echo("❌ No backups found")
        return

    # List available backups
    backups = sorted(backups_dir.iterdir(), reverse=True)

    if not backup_id:
        click.echo("\n📦 Available Backups:\n")
        for backup in backups:
            click.echo(f"   {backup.name}")
        click.echo(f"\nUse: docs rollback --backup-id <id>")
        return

    # Rollback to specific backup
    backup_path = backups_dir / backup_id
    if not backup_path.exists():
        click.echo(f"❌ Backup not found: {backup_id}")
        return

    click.echo(f"🔄 Rolling back to: {backup_id}")

    # Restore files
    for file in backup_path.iterdir():
        if file.is_file():
            shutil.copy2(file, docs_dir / file.name)

    click.echo(f"✅ Documentation restored from backup")

@docs.command()
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed diff"
)
def diff(verbose: bool):
    """
    Show differences between current docs and package template.

    Example:
        your-package docs diff
        your-package docs diff --verbose
    """
    # Implementation similar to HtmlGraph's diff_memory_files
    # Compare user's generated docs with fresh template render
    # Highlight customizations
    pass
```

---

### 3.4 Hook Integration (Optional)

#### Hook Selection

**Best hooks for documentation injection:**

1. **SessionStart** - Inject docs once at session start
   - **Pros:** Minimal context pollution, always available
   - **Cons:** Users may forget docs exist, no refresh on updates

2. **PreToolUse** - Inject docs before specific tools
   - **Pros:** Context-aware, docs when needed
   - **Cons:** Repetitive injection, context budget issues

3. **UserPromptSubmit** - Inject on keywords
   - **Pros:** On-demand, minimal overhead
   - **Cons:** Requires user to remember keywords

**Recommended:** `SessionStart` with progressive disclosure

#### Context Injection Strategy

```python
# .claude-plugin/hooks/session-start.py
import json
import sys
from pathlib import Path

def main():
    # Load hook input
    hook_input = json.loads(sys.stdin.read())

    # Find project root
    cwd = Path(hook_input.get("cwd", Path.cwd()))
    docs_dir = cwd / ".your-package"
    doc_path = docs_dir / "CLAUDE.md"
    meta_path = docs_dir / ".claude-docs-meta.json"

    # Check if docs exist
    if not doc_path.exists():
        # No docs, no injection
        print(json.dumps({"prompt": ""}))
        return

    # Load metadata for context budget management
    metadata = None
    if meta_path.exists():
        with open(meta_path) as f:
            metadata = json.load(f)

    # Read documentation
    doc_content = doc_path.read_text()

    # Progressive disclosure: Inject summary + link to full docs
    summary = extract_summary(doc_content)

    prompt = f"""
# 📚 YourPackage Documentation Available

{summary}

**Full documentation:** `.your-package/CLAUDE.md`

**Quick commands:**
- `your-package docs version` - Check doc status
- `your-package docs upgrade` - Get latest docs
- `your-package --help` - Show CLI help

💡 Use the full documentation for detailed API reference and examples.
"""

    # Add version warning if outdated
    if metadata and needs_upgrade(metadata):
        prompt += f"""
⚠️  **Documentation may be outdated!**
Current: v{metadata['doc_version']} (package v{metadata['package_version']})
Run: `your-package docs upgrade`
"""

    # Return injected prompt
    print(json.dumps({"prompt": prompt}))

def extract_summary(content: str) -> str:
    """Extract Quick Start section as summary"""
    # Parse Markdown and extract ## Quick Start section
    # Return condensed version
    lines = content.split("\n")
    in_quickstart = False
    summary_lines = []

    for line in lines:
        if line.startswith("## Quick Start"):
            in_quickstart = True
            continue
        if in_quickstart and line.startswith("##"):
            break
        if in_quickstart:
            summary_lines.append(line)

    return "\n".join(summary_lines[:15])  # First 15 lines only

def needs_upgrade(metadata: dict) -> bool:
    """Check if docs need upgrade"""
    from packaging import version
    CURRENT_DOC_VERSION = "2"  # Replace with actual

    doc_ver = metadata.get("doc_version", "0")
    return version.parse(doc_ver) < version.parse(CURRENT_DOC_VERSION)

if __name__ == "__main__":
    main()
```

#### Token Budget Management

**Strategy:** Progressive disclosure with sections

```markdown
# Documentation (Condensed for Context Budget)

## Quick Reference
[Essential API calls, always shown]

## Common Patterns
<details>
<summary>Click to expand</summary>
[Frequently used patterns]
</details>

## Advanced Usage
<details>
<summary>Click to expand</summary>
[Advanced topics]
</details>

## Full Documentation
See `.your-package/CLAUDE.md` for complete reference.
```

**Or use template blocks:**

```jinja2
{# Condensed version for hook injection #}
{% block hook_summary %}
## Quick Reference
- Command 1: Description
- Command 2: Description
- Command 3: Description

Full docs: `.your-package/CLAUDE.md`
{% endblock %}
```

---

## 4. Best Practices

### Template Design

#### Block Naming Conventions

**Use semantic names, not structural:**

✅ **Good:**
```jinja2
{% block quickstart %}
{% block configuration %}
{% block api_reference %}
{% block troubleshooting %}
{% block orchestration_patterns %}
```

❌ **Bad:**
```jinja2
{% block section_1 %}
{% block part_a %}
{% block content %}
{% block div_2 %}
```

**Naming guidelines:**
- Use snake_case for consistency
- Be specific (not generic)
- Indicate content type (e.g., `_examples`, `_reference`)
- Group related blocks (e.g., `advanced_orchestration`, `advanced_analytics`)

#### Section Organization

**Recommended structure:**

1. **Header** - Package name, version, generated timestamp
2. **Quick Start** - Get users productive fast
3. **Configuration** - Setup and customization
4. **Core Concepts** - Fundamental understanding
5. **API Reference** - Detailed reference
6. **Advanced Usage** - Power user features
7. **Troubleshooting** - Common issues
8. **Customization Guide** - How to override blocks
9. **Footer** - Version info, links

**Template organization:**
```jinja2
{# Header - Always visible #}
{% block header %}{% endblock %}

{# Critical path - Always visible #}
{% block quickstart %}{% endblock %}
{% block configuration %}{% endblock %}

{# Core content - Collapsible or always visible #}
{% block core_concepts %}{% endblock %}
{% block api_reference %}{% endblock %}

{# Advanced - User can exclude to save tokens #}
{% block advanced %}
  {% block orchestration %}{% endblock %}
  {% block analytics %}{% endblock %}
{% endblock %}

{# Support - User can exclude #}
{% block troubleshooting %}{% endblock %}
{% block examples %}{% endblock %}

{# Footer - Always visible #}
{% block footer %}{% endblock %}
```

#### Reusable Template Patterns

**Include pattern for shared content:**
```jinja2
{# templates/shared/api-common.md.jinja2 #}
## Common API Patterns

### Error Handling
All API methods follow this pattern:
```python
try:
    result = sdk.method()
except PackageError as e:
    print(f"Error: {e}")
```

{# Use in multiple templates #}
{% include "shared/api-common.md.jinja2" %}
```

**Macro pattern for repeated structures:**
```jinja2
{# Define macro #}
{% macro code_example(title, code, language="python") %}
### {{ title }}
```{{ language }}
{{ code }}
```
{% endmacro %}

{# Use macro #}
{{ code_example("Create Feature", "sdk.features.create('title')") }}
{{ code_example("Run Analytics", "sdk.analytics.recommend_next_work()") }}
```

---

### Version Management

#### When to Bump Doc Schema Version

**Bump doc_version when:**
- ✅ Template structure changes (blocks added/removed/renamed)
- ✅ Required context changes (new required sections)
- ✅ Breaking changes in customization API
- ✅ File location changes
- ✅ Metadata format changes

**Don't bump doc_version when:**
- ❌ Content updates (typo fixes, clarifications)
- ❌ New examples added
- ❌ Package version bumps (use package_version for that)
- ❌ Documentation improvements (same structure)

**Example decision tree:**
```
Did template block structure change? YES → Bump doc_version
Did metadata schema change? YES → Bump doc_version
Did file paths change? YES → Bump doc_version
Did you just improve docs content? NO → Don't bump
```

#### N-1 Compatibility Strategy

**Goal:** Old docs work with new package versions

```python
# Version 1 docs can work with package 0.9.0 - 0.9.9
# Version 2 docs work with package 0.10.0+

# User on doc v1 installs package 0.9.5 → Works fine
# User on doc v1 installs package 0.10.0 → Warning + upgrade prompt
# User on doc v2 installs package 0.9.0 → Error (unsupported)
```

**Implementation:**
```python
def check_compatibility(metadata: DocsMetadata, package_version: str):
    """Check if docs are compatible with package"""
    compat = VERSION_COMPATIBILITY[metadata.doc_version]

    if not compat:
        return False, "Unknown doc version"

    pkg_ver = version.parse(package_version)
    min_ver = version.parse(compat["min_package"])
    max_ver = version.parse(compat["max_package"]) if compat["max_package"] else None

    if pkg_ver < min_ver:
        return False, f"Package too old (need >= {min_ver})"

    if max_ver and pkg_ver > max_ver:
        return False, f"Docs outdated (upgrade for >= {max_ver})"

    return True, "Compatible"
```

#### Breaking Change Communication

**When introducing breaking changes:**

1. **Announce in CHANGELOG:**
   ```markdown
   ## [0.10.0] - 2025-01-15

   ### BREAKING CHANGES
   - Documentation schema upgraded to v2
   - File moved: `CLAUDE.md` → `.your-package/CLAUDE.md`
   - Custom configurations now use Jinja2 blocks

   **Migration:** Run `your-package docs upgrade`
   ```

2. **Add upgrade prompt in CLI:**
   ```python
   if metadata.doc_version < CURRENT_DOC_VERSION:
       click.echo("\n⚠️  BREAKING CHANGE")
       click.echo(f"   Documentation schema updated: v{metadata.doc_version} → v{CURRENT_DOC_VERSION}")
       click.echo("   Your customizations will be preserved during upgrade.")
       click.echo(f"\n   Run: your-package docs upgrade")
   ```

3. **Provide clear migration path:**
   ```python
   # Migration script with clear messaging
   class Migration001To002(MigrationScript):
       description = """
       Migrate to template-based documentation system.

       What changes:
       - File moves to .your-package/CLAUDE.md
       - Custom sections become Jinja2 blocks
       - Version tracking with .claude-docs-meta.json

       What's preserved:
       - All your custom content
       - Custom configuration
       - Custom workflows
       """
   ```

---

### User Experience

#### Clear Upgrade Prompts

**Example upgrade flow:**

```bash
$ your-package docs version

📊 Documentation Status

Platform:          claude
Doc Version:       1
Package Version:   0.9.0
Generated:         2024-12-15T10:30:00Z

⚠️  Package upgraded: 0.9.0 → 0.10.2
   Run 'docs upgrade' to get latest documentation

⚠️  Documentation schema outdated: 1 → 2
   Run 'docs upgrade' to migrate

$ your-package docs upgrade

📋 Upgrade Plan

Current version:  1
Target version:   2
Migrations:       001_to_002

⚠️  You have customizations that will be preserved:
   - configuration
   - workflows

Proceed with upgrade? [y/N]: y

🔄 Migration: Migrate to template-based system
   From version 1 → 2
   Detecting customizations...
   Found customizations: ['configuration', 'workflows']
   Migrating documentation...
✅ Migration completed successfully

✅ Documentation upgraded successfully!
   New version: 2
```

#### Informative Error Messages

**Good error messages:**

```python
# ❌ Bad
raise Exception("Migration failed")

# ✅ Good
raise MigrationError(
    f"Migration {migration_id} failed during customization detection.\n\n"
    f"Possible causes:\n"
    f"1. Documentation file corrupted\n"
    f"2. Custom template syntax error\n"
    f"3. Incompatible customization format\n\n"
    f"Your documentation has been restored from backup:\n"
    f"  {backup_path}\n\n"
    f"For help, see: https://docs.example.com/migration-troubleshooting"
)
```

**Actionable errors:**
```python
if not doc_path.exists():
    click.echo("❌ Documentation not found")
    click.echo("   Expected: .your-package/CLAUDE.md")
    click.echo("   Run: your-package docs generate")
    return
```

#### Safe Defaults

**Principle:** Prefer safety over convenience

```python
# ✅ Safe: Require explicit confirmation for destructive operations
@click.option("--force", is_flag=True, help="Overwrite existing docs")
def generate(force: bool):
    if doc_exists() and not force:
        click.echo("Docs exist. Use --force to overwrite")
        return

# ✅ Safe: Create backups automatically
def migrate():
    backup_path = self.backup()  # Always backup before migration
    try:
        self.perform_migration()
    except Exception:
        self.rollback(backup_path)  # Auto-rollback on failure
```

#### Rollback Confidence

**Make rollback trustworthy:**

1. **Automatic backups:**
   ```python
   def backup(self) -> Path:
       """Create timestamped backup automatically"""
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       backup_dir = self.docs_dir / "backups" / timestamp
       # ... copy files ...
       return backup_dir
   ```

2. **List available backups:**
   ```bash
   $ your-package docs rollback

   📦 Available Backups:
      20250102_103000
      20250101_150000
      20241230_093000

   Use: docs rollback --backup-id <id>
   ```

3. **Verify rollback:**
   ```python
   def rollback(self, backup_path: Path) -> bool:
       # Restore files
       self._restore_from_backup(backup_path)

       # Verify restoration
       if self._verify_docs():
           click.echo("✅ Documentation restored successfully")
           return True
       else:
           click.echo("❌ Rollback verification failed")
           return False
   ```

---

### Testing Strategy

#### Integration Test Coverage

**Essential test scenarios:**

```python
# tests/test_docs_system.py
import pytest
from pathlib import Path
from your_package.template_engine import DocTemplateEngine
from your_package.models import DocsMetadata
from your_package.migrations import Migration001To002

@pytest.fixture
def project_dir(tmp_path):
    """Create temporary project directory"""
    return tmp_path / "test_project"

def test_generate_fresh_docs(project_dir):
    """Test generating docs in empty project"""
    engine = DocTemplateEngine("test_package", project_dir)

    context = {
        "package_name": "test_package",
        "package_version": "0.1.0",
        "doc_version": "1"
    }

    output = engine.render("base/claude.md.jinja2", context)

    assert "# test_package" in output
    assert "0.1.0" in output

def test_user_customization_preserved(project_dir):
    """Test that user customizations survive regeneration"""
    # Setup: Create custom template
    templates_dir = project_dir / ".test-package" / "templates"
    templates_dir.mkdir(parents=True)

    custom_template = templates_dir / "claude.md.jinja2"
    custom_template.write_text("""
{% extends "base/claude.md.jinja2" %}

{% block configuration %}
## My Custom Configuration
Custom content here
{% endblock %}
    """)

    # Generate docs with customization
    engine = DocTemplateEngine("test_package", project_dir)
    output = engine.render("base/claude.md.jinja2", {})

    assert "My Custom Configuration" in output

def test_migration_preserves_customizations(project_dir):
    """Test migration preserves user content"""
    # Setup: Create v1 docs with custom content
    docs_dir = project_dir / ".test-package"
    docs_dir.mkdir(parents=True)

    v1_doc = docs_dir / "CLAUDE.md"
    v1_doc.write_text("""
# Test Package

## My Configuration
Custom config here

## My Workflows
Custom workflows here
    """)

    # Run migration
    migration = Migration001To002(project_dir, "test_package")
    customizations = migration.detect_customizations()

    assert customizations["has_customizations"] is True
    assert "configuration" in customizations["customized_blocks"]

    # Perform migration
    success = migration.migrate(customizations)
    assert success is True

    # Verify custom content preserved
    v2_template = docs_dir / "templates" / "claude.md.jinja2"
    assert v2_template.exists()
    content = v2_template.read_text()
    assert "Custom config here" in content

def test_version_compatibility_check(project_dir):
    """Test version compatibility detection"""
    metadata = DocsMetadata(
        doc_version="1",
        package_version="0.9.0",
        platform="claude"
    )

    # Compatible package version
    assert metadata.is_compatible_with_package("0.9.5") is True

    # Incompatible (too new)
    assert metadata.is_compatible_with_package("0.11.0") is False

def test_backup_and_rollback(project_dir):
    """Test backup creation and rollback"""
    docs_dir = project_dir / ".test-package"
    docs_dir.mkdir(parents=True)

    # Create original doc
    doc_path = docs_dir / "CLAUDE.md"
    doc_path.write_text("Original content")

    # Create migration and backup
    migration = Migration001To002(project_dir, "test_package")
    backup_path = migration.backup()

    assert backup_path.exists()
    assert (backup_path / "CLAUDE.md").exists()

    # Modify original
    doc_path.write_text("Modified content")

    # Rollback
    success = migration.rollback(backup_path)
    assert success is True
    assert doc_path.read_text() == "Original content"
```

#### Customization Preservation Tests

**Test matrix:**

```python
@pytest.mark.parametrize("customization_type,expected_preserved", [
    ("configuration", True),
    ("workflows", True),
    ("quickstart", True),
    ("examples", True),
    ("unknown_block", True),  # Should preserve even unknown blocks
])
def test_preserve_customization_types(
    project_dir,
    customization_type,
    expected_preserved
):
    """Test different customization types are preserved"""
    # Setup custom block
    # Run migration
    # Verify preservation
    pass
```

#### Edge Case Handling

**Critical edge cases:**

```python
def test_migration_with_corrupted_docs(project_dir):
    """Test migration handles corrupted documentation"""
    docs_dir = project_dir / ".test-package"
    docs_dir.mkdir(parents=True)

    # Create corrupted doc (invalid UTF-8, etc.)
    doc_path = docs_dir / "CLAUDE.md"
    doc_path.write_bytes(b'\x80\x81\x82')  # Invalid UTF-8

    migration = Migration001To002(project_dir, "test_package")

    # Should handle gracefully
    with pytest.raises(MigrationError) as exc_info:
        migration.detect_customizations()

    assert "corrupted" in str(exc_info.value).lower()

def test_migration_with_missing_metadata(project_dir):
    """Test migration when metadata is missing"""
    docs_dir = project_dir / ".test-package"
    docs_dir.mkdir(parents=True)

    # Doc exists but no metadata
    doc_path = docs_dir / "CLAUDE.md"
    doc_path.write_text("# Documentation")

    # Should create default metadata
    metadata = DocsMetadata.load(docs_dir / ".claude-docs-meta.json")
    assert metadata is None  # Missing

    # Migration should handle this
    migration = Migration001To002(project_dir, "test_package")
    success = migration.run()
    assert success is True

def test_concurrent_upgrade_attempts(project_dir):
    """Test multiple upgrade processes don't conflict"""
    # Use file locking or similar to prevent concurrent upgrades
    # This is advanced - may need process-level locks
    pass

def test_upgrade_with_partial_customizations(project_dir):
    """Test upgrade when user only customized some blocks"""
    # User customized 2 of 5 blocks
    # Verify:
    # - Customized blocks preserved
    # - Non-customized blocks updated
    pass
```

---

## 5. Reference Implementation

### DocTemplateEngine (Simplified)

```python
# your_package/template_engine.py
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, TemplateNotFound
from pathlib import Path
from typing import Optional
import re

class DocTemplateEngine:
    """
    Template engine for packageable auto-updating documentation.

    Manages Jinja2 templates with user override support via ChoiceLoader.
    User templates (in project) take priority over package templates.
    """

    def __init__(self, package_name: str, project_root: Path):
        self.package_name = package_name
        self.project_root = project_root

        # Package templates (bundled with distribution)
        package_templates = Path(__file__).parent / "templates"

        # User templates (in project .package-name/templates/)
        user_templates = project_root / f".{package_name}" / "templates"
        user_templates.mkdir(parents=True, exist_ok=True)

        # ChoiceLoader: User templates first, then package templates
        loader = ChoiceLoader([
            FileSystemLoader(str(user_templates)),
            FileSystemLoader(str(package_templates))
        ])

        self.env = Environment(
            loader=loader,
            autoescape=False,  # Markdown doesn't need HTML escaping
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )

        # Add custom filters
        self.env.filters["snake_to_title"] = lambda s: s.replace("_", " ").title()

    def render(self, template_name: str, context: dict) -> str:
        """
        Render template with context.

        User template takes priority if it exists.
        Falls back to package template.
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            raise TemplateNotFound(
                f"Template not found: {template_name}\n"
                f"Searched in:\n"
                f"  - {self.project_root / f'.{self.package_name}' / 'templates'}\n"
                f"  - {Path(__file__).parent / 'templates'}"
            )

    def has_user_template(self, template_name: str) -> bool:
        """Check if user has custom template"""
        user_path = (
            self.project_root /
            f".{self.package_name}" /
            "templates" /
            template_name
        )
        return user_path.exists()

    def detect_customized_blocks(self, template_name: str) -> list[str]:
        """
        Detect which template blocks user has customized.

        Returns list of block names found in user template.
        """
        if not self.has_user_template(template_name):
            return []

        user_path = (
            self.project_root /
            f".{self.package_name}" /
            "templates" /
            template_name
        )

        content = user_path.read_text()

        # Parse Jinja2 blocks using regex
        block_pattern = r'{%\s*block\s+(\w+)\s*%}'
        blocks = re.findall(block_pattern, content)

        return blocks

    def list_available_templates(self) -> dict[str, list[str]]:
        """
        List all available templates.

        Returns dict with:
        {
            "package": ["base/claude.md.jinja2", ...],
            "user": ["claude.md.jinja2", ...]
        }
        """
        package_templates_dir = Path(__file__).parent / "templates"
        user_templates_dir = self.project_root / f".{self.package_name}" / "templates"

        def list_templates(base_dir: Path) -> list[str]:
            if not base_dir.exists():
                return []

            templates = []
            for path in base_dir.rglob("*.jinja2"):
                rel_path = path.relative_to(base_dir)
                templates.append(str(rel_path))
            return sorted(templates)

        return {
            "package": list_templates(package_templates_dir),
            "user": list_templates(user_templates_dir)
        }
```

### DocsMetadata Model (Complete)

```python
# your_package/models.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import json
from packaging import version

class DocsMetadata(BaseModel):
    """
    Metadata for packageable auto-updating documentation.

    Tracks version, customizations, and migration state.
    Stored in .package-name/.claude-docs-meta.json
    """

    doc_version: str = Field(
        description="Documentation schema version (e.g., '2')"
    )

    package_version: str = Field(
        description="Package version when generated (e.g., '0.9.5')"
    )

    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of generation"
    )

    platform: str = Field(
        default="claude",
        description="Target platform (claude, gemini, codex, etc.)"
    )

    has_customizations: bool = Field(
        default=False,
        description="Whether user has custom template overrides"
    )

    customization_blocks: List[str] = Field(
        default_factory=list,
        description="List of template blocks user has customized"
    )

    last_migration: Optional[str] = Field(
        default=None,
        description="ID of last migration applied"
    )

    backup_path: Optional[str] = Field(
        default=None,
        description="Path to backup created before last update"
    )

    @field_validator("doc_version", "package_version")
    def validate_version_format(cls, v):
        """Ensure versions are valid semver or integer strings"""
        try:
            # Try parsing as semver
            version.parse(v)
            return v
        except:
            # Try parsing as integer
            int(v)
            return v

    @classmethod
    def load(cls, path: Path) -> Optional["DocsMetadata"]:
        """Load metadata from .claude-docs-meta.json"""
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            raise MetadataError(f"Failed to load metadata from {path}: {e}")

    def save(self, path: Path) -> None:
        """Save metadata to .claude-docs-meta.json"""
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(
                self.model_dump(mode="json"),
                f,
                indent=2,
                default=str  # Handle datetime serialization
            )

    def is_compatible_with_package(self, package_version: str) -> bool:
        """Check if docs are compatible with given package version"""
        compat = VERSION_COMPATIBILITY.get(self.doc_version)
        if not compat:
            return False

        pkg_ver = version.parse(package_version)
        min_ver = version.parse(compat["min_package"])
        max_ver = (
            version.parse(compat["max_package"])
            if compat["max_package"]
            else None
        )

        if pkg_ver < min_ver:
            return False
        if max_ver and pkg_ver > max_ver:
            return False

        return True

    def needs_upgrade(self, current_doc_version: str) -> bool:
        """Check if docs need upgrading to current version"""
        return version.parse(self.doc_version) < version.parse(current_doc_version)

class MetadataError(Exception):
    """Raised when metadata operations fail"""
    pass

# Version compatibility matrix
VERSION_COMPATIBILITY = {
    "1": {
        "min_package": "0.1.0",
        "max_package": "0.8.9",
        "description": "Original single-file format"
    },
    "2": {
        "min_package": "0.9.0",
        "max_package": None,
        "description": "Template-based with blocks"
    }
}

CURRENT_DOC_VERSION = "2"
```

### MigrationScript Base Class (Complete)

```python
# your_package/migrations/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional
import shutil
from datetime import datetime

class MigrationScript(ABC):
    """
    Base class for documentation migration scripts.

    Subclasses implement:
    - detect_customizations(): Find user customizations
    - migrate(): Perform migration preserving customizations
    """

    # Subclasses MUST define these
    from_version: str
    to_version: str
    description: str

    def __init__(self, project_root: Path, package_name: str):
        self.project_root = project_root
        self.package_name = package_name
        self.docs_dir = project_root / f".{package_name}"

    @abstractmethod
    def detect_customizations(self) -> Dict:
        """
        Detect user customizations.

        Returns:
            {
                "has_customizations": bool,
                "customized_blocks": List[str],
                "custom_content": Dict[str, str]
            }
        """
        pass

    @abstractmethod
    def migrate(self, customizations: Dict) -> bool:
        """
        Perform migration, preserving customizations.

        Returns:
            True if successful, False otherwise
        """
        pass

    def backup(self) -> Path:
        """Create timestamped backup before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.docs_dir / "backups" / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup all files
        for file in self.docs_dir.iterdir():
            if file.is_file():
                shutil.copy2(file, backup_dir / file.name)

        print(f"✅ Backup created: {backup_dir}")
        return backup_dir

    def rollback(self, backup_path: Path) -> bool:
        """Restore from backup"""
        if not backup_path.exists():
            print(f"❌ Backup not found: {backup_path}")
            return False

        try:
            for file in backup_path.iterdir():
                if file.is_file():
                    shutil.copy2(file, self.docs_dir / file.name)

            print(f"✅ Restored from backup: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False

    def run(self) -> bool:
        """Execute migration with backup and error handling"""
        print(f"\n🔄 Migration: {self.description}")
        print(f"   {self.from_version} → {self.to_version}")

        backup_path = self.backup()

        try:
            customizations = self.detect_customizations()

            if customizations.get("has_customizations"):
                blocks = customizations.get("customized_blocks", [])
                print(f"   Found customizations: {blocks}")

            success = self.migrate(customizations)

            if success:
                print("✅ Migration successful")
                return True
            else:
                print("❌ Migration failed")
                self.rollback(backup_path)
                return False

        except Exception as e:
            print(f"❌ Migration error: {e}")
            self.rollback(backup_path)
            return False

class MigrationError(Exception):
    """Raised when migration fails"""
    pass
```

---

## 6. Common Pitfalls and Solutions

### User Templates Not Loading

**Problem:** User customizations not appearing in generated docs

**Cause:** ChoiceLoader order incorrect

**Solution:**
```python
# ❌ Wrong order
loader = ChoiceLoader([
    FileSystemLoader(package_templates),  # Package first
    FileSystemLoader(user_templates)       # User second
])

# ✅ Correct order
loader = ChoiceLoader([
    FileSystemLoader(user_templates),      # User first
    FileSystemLoader(package_templates)    # Package second
])
```

### Customizations Lost During Migration

**Problem:** User content disappears after upgrade

**Cause:** Migration didn't detect customizations properly

**Solution:**
```python
def detect_customizations(self) -> dict:
    """Robust customization detection"""

    # 1. Check for custom template file
    custom_template = self.docs_dir / "templates" / "claude.md.jinja2"
    if custom_template.exists():
        # Parse blocks from template
        return self._parse_custom_blocks(custom_template)

    # 2. Check for custom markers in generated doc
    doc_path = self.docs_dir / "CLAUDE.md"
    if doc_path.exists():
        content = doc_path.read_text()

        # Look for custom section markers
        if "## My Configuration" in content:
            return self._extract_custom_sections(content)

    # 3. Compare with base template (diff approach)
    return self._diff_with_base_template(doc_path)

def _diff_with_base_template(self, doc_path: Path) -> dict:
    """Compare user doc with base template to find customizations"""
    from difflib import unified_diff

    # Render base template
    engine = DocTemplateEngine(self.package_name, self.project_root)
    base_content = engine.render("base/claude.md.jinja2", {})

    # Compare
    user_content = doc_path.read_text()
    diff = list(unified_diff(
        base_content.splitlines(),
        user_content.splitlines()
    ))

    # Analyze diff to find customized sections
    # ...
```

### Metadata Corruption

**Problem:** `.claude-docs-meta.json` becomes invalid

**Cause:** Concurrent writes, interrupted migrations, manual edits

**Solution:**
```python
@classmethod
def load(cls, path: Path) -> Optional["DocsMetadata"]:
    """Load with corruption recovery"""
    if not path.exists():
        return None

    try:
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    except json.JSONDecodeError:
        # Corrupted JSON - try to recover
        print("⚠️  Metadata corrupted, attempting recovery...")
        backup = cls._find_latest_backup(path.parent)

        if backup:
            print(f"   Restoring from backup: {backup}")
            shutil.copy2(backup / path.name, path)
            return cls.load(path)

        print("   No backup found, creating default metadata")
        return cls._create_default()

    except Exception as e:
        raise MetadataError(f"Failed to load metadata: {e}")

@staticmethod
def _find_latest_backup(docs_dir: Path) -> Optional[Path]:
    """Find most recent backup directory"""
    backups_dir = docs_dir / "backups"
    if not backups_dir.exists():
        return None

    backups = sorted(backups_dir.iterdir(), reverse=True)
    return backups[0] if backups else None
```

### Template Syntax Errors

**Problem:** User creates invalid Jinja2 template

**Cause:** Typos in block syntax, missing `{% endblock %}`

**Solution:**
```python
def validate_user_template(self, template_name: str) -> tuple[bool, Optional[str]]:
    """
    Validate user template syntax before using it.

    Returns: (is_valid, error_message)
    """
    user_path = self.project_root / f".{self.package_name}" / "templates" / template_name

    if not user_path.exists():
        return True, None  # No user template

    try:
        # Try parsing template
        self.env.get_template(template_name)
        return True, None

    except Exception as e:
        return False, str(e)

# Use in CLI
def generate(platform: str):
    engine = DocTemplateEngine("package", Path.cwd())

    # Validate before rendering
    valid, error = engine.validate_user_template(f"{platform}.md.jinja2")
    if not valid:
        click.echo(f"❌ Template syntax error: {error}")
        click.echo(f"   Fix your template in: .package/templates/{platform}.md.jinja2")
        return

    # Proceed with generation
    ...
```

### Version Compatibility Confusion

**Problem:** Users don't understand doc_version vs package_version

**Cause:** Unclear messaging

**Solution:**
```python
# Clear explanations in CLI output
def version():
    click.echo("""
📊 Documentation Status

Doc Schema Version:    2
├─ Controls template structure
├─ Changes rarely (only with breaking changes)
└─ Current latest: 2

Package Version:       0.10.5
├─ Controls features and APIs
├─ Changes frequently (with releases)
└─ Current latest: 0.10.5

💡 Explanation:
- Doc schema version changes when template structure changes
- Package version changes with every release
- Old doc schemas may work with new packages (compatibility)
- Run 'docs upgrade' when prompted
    """)
```

---

## 7. Extension Points

### Multi-Platform Documentation

**Pattern:** Single base template, platform-specific extensions

```python
# Structure
templates/
  ├── shared/
  │   ├── quickstart.md.jinja2
  │   └── api-reference.md.jinja2
  └── platforms/
      ├── claude.md.jinja2
      ├── gemini.md.jinja2
      └── codex.md.jinja2

# Base template (shared sections)
# templates/shared/quickstart.md.jinja2
## Quick Start

{% block install %}
```bash
pip install {{ package_name }}
```
{% endblock %}

# Platform-specific template
# templates/platforms/claude.md.jinja2
{% include "shared/quickstart.md.jinja2" %}

## Claude-Specific Features
{% block claude_orchestration %}
Use orchestration mode for multi-agent workflows...
{% endblock %}
```

**CLI support:**
```bash
your-package docs generate --platform claude
your-package docs generate --platform gemini
your-package docs generate --all-platforms
```

### Internationalization (i18n)

**Pattern:** Template selection by locale

```python
# Structure
templates/
  ├── en/
  │   └── claude.md.jinja2
  ├── ja/
  │   └── claude.md.jinja2
  └── es/
      └── claude.md.jinja2

# Context with locale
context = {
    "package_name": "htmlgraph",
    "locale": "ja",
    "_": translation_function  # gettext or similar
}

# Render with locale-specific template
output = engine.render(f"{context['locale']}/claude.md.jinja2", context)
```

### Dynamic Content Injection

**Pattern:** Hook-based content providers

```python
# Allow plugins to inject content into templates

class ContentProvider(ABC):
    @abstractmethod
    def get_content(self, section: str) -> str:
        pass

# Register providers
engine.register_provider("examples", ExamplesProvider())
engine.register_provider("changelog", ChangelogProvider())

# In template
{% block examples %}
{{ providers.examples.get_content("quickstart") }}
{% endblock %}
```

### Custom Template Filters

**Pattern:** Domain-specific Jinja2 filters

```python
def setup_filters(env: Environment):
    """Add custom Jinja2 filters"""

    # Convert snake_case to Title Case
    env.filters["titleize"] = lambda s: s.replace("_", " ").title()

    # Format code blocks
    env.filters["code"] = lambda code, lang="python": f"```{lang}\n{code}\n```"

    # Format timestamps
    env.filters["datetime"] = lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S")

    # Markdown table formatter
    env.filters["table"] = format_markdown_table

# Usage in templates
{{ package_name | titleize }}
{{ code_sample | code("python") }}
{{ generated_at | datetime }}
{{ api_methods | table }}
```

---

## 8. FAQ

### Q: Why Jinja2 instead of simpler string templates?

**A:** Jinja2 provides critical features for this pattern:

1. **Template Inheritance** - Users can extend base templates
2. **Block System** - Granular override control
3. **Include/Import** - Reusable components
4. **Filters** - Custom formatting logic
5. **Conditionals** - Platform-specific content
6. **Widely Used** - Developers already know it

Simple string templates (`str.format`, f-strings) don't support inheritance or blocks, making customization preservation impossible.

### Q: How do I know when to create a migration?

**A:** Create a migration when:

✅ **Template structure changes**
- Adding/removing/renaming blocks
- Changing file locations
- Modifying metadata schema

❌ **Don't create migration for:**
- Content improvements
- Typo fixes
- Adding examples (within existing blocks)

**Decision tree:**
```
Will user's custom template break? YES → Migration needed
Did file paths change? YES → Migration needed
Did metadata schema change? YES → Migration needed
Just improving docs content? NO → No migration needed
```

### Q: Can users completely replace base documentation?

**A:** Yes, with caveats:

**Option 1: Override all blocks** (recommended)
```jinja2
{% extends "base/claude.md.jinja2" %}
{% block quickstart %}Custom quickstart{% endblock %}
{% block configuration %}Custom config{% endblock %}
{# Override every block #}
```

**Option 2: Completely custom template** (advanced)
```jinja2
{# Don't extend base template #}
# My Completely Custom Documentation
...
```

**Caveat:** Option 2 means:
- No automatic updates from package
- Must manually track changes
- Version compatibility may break

### Q: What if user customizations conflict with package updates?

**A:** Handle with migration strategy:

```python
def migrate(self, customizations: dict) -> bool:
    """Handle conflicting customizations"""

    # Detect conflicts
    conflicts = self._detect_conflicts(customizations)

    if conflicts:
        print("⚠️  Customization conflicts detected:")
        for conflict in conflicts:
            print(f"   - {conflict['block']}: {conflict['reason']}")

        # Offer resolution strategies
        print("\nResolution options:")
        print("1. Keep your customization (may lose new features)")
        print("2. Accept package update (will overwrite your customization)")
        print("3. Merge both (manual editing required)")

        choice = click.prompt("Choose", type=int)

        if choice == 1:
            # Keep user customization
            return self._migrate_keep_user(customizations)
        elif choice == 2:
            # Accept package update
            return self._migrate_accept_package(customizations)
        else:
            # Create merged template for manual editing
            return self._migrate_create_merge_template(customizations)
```

### Q: How much documentation should be in package vs project?

**A:** Follow this guideline:

**Package documentation (base templates):**
- ✅ Core concepts
- ✅ API reference
- ✅ Quick start
- ✅ Common patterns
- ✅ Troubleshooting

**Project documentation (user overrides):**
- ✅ Project-specific configuration
- ✅ Custom workflows
- ✅ Team conventions
- ✅ Additional examples
- ✅ Integration notes

**Principle:** Package provides comprehensive default, user customizes for their needs.

---

## 9. Examples

### Example 1: Simple Package - Basic Override

**Scenario:** CLI tool with minimal customization needs

**Package structure:**
```
simple_tool/
├── templates/
│   └── base/
│       └── README.md.jinja2
└── cli.py
```

**Base template:**
```jinja2
# {{ package_name }}

{% block description %}
A simple CLI tool for X, Y, Z.
{% endblock %}

## Installation
{% block installation %}
```bash
pip install {{ package_name }}
```
{% endblock %}

## Usage
{% block usage %}
```bash
{{ package_name }} command [options]
```
{% endblock %}
```

**User customization:**
```jinja2
{# .simple-tool/templates/README.md.jinja2 #}
{% extends "base/README.md.jinja2" %}

{% block description %}
{{ super() }}

**Our team uses this for:** Internal automation workflows
{% endblock %}

{% block usage %}
{{ super() }}

### Our Common Commands
```bash
simple-tool deploy --env production
simple-tool backup --daily
```
{% endblock %}
```

**CLI:**
```bash
simple-tool docs generate
# Generates README.md with user customizations
```

### Example 2: Medium Complexity - Multiple Platforms, One Migration

**Scenario:** AI agent SDK with Claude and Gemini support

**Package structure:**
```
ai_sdk/
├── templates/
│   ├── base/
│   │   ├── claude.md.jinja2
│   │   └── gemini.md.jinja2
│   └── shared/
│       └── api-common.md.jinja2
├── migrations/
│   └── 001_add_analytics.py
└── cli.py
```

**Migration (001_add_analytics.py):**
```python
class Migration001AddAnalytics(MigrationScript):
    from_version = "1"
    to_version = "2"
    description = "Add analytics section to documentation"

    def detect_customizations(self) -> dict:
        # Check for custom workflows section
        doc_path = self.docs_dir / "CLAUDE.md"
        content = doc_path.read_text()

        custom_workflows = "## My Workflows" in content

        return {
            "has_customizations": custom_workflows,
            "customized_blocks": ["workflows"] if custom_workflows else []
        }

    def migrate(self, customizations: dict) -> bool:
        # Regenerate with new analytics section
        engine = DocTemplateEngine("ai_sdk", self.project_root)

        # Preserve custom workflows if exists
        if customizations.get("has_customizations"):
            # Create user template with custom workflows block
            pass

        # Generate updated documentation
        output = engine.render("base/claude.md.jinja2", context)
        doc_path.write_text(output)

        return True
```

**Usage:**
```bash
# User has v1 docs with custom workflows
ai-sdk docs version
# → Doc version: 1 (outdated)

# Upgrade to v2 (adds analytics)
ai-sdk docs upgrade
# → Detects custom workflows
# → Preserves them in migration
# → Adds new analytics section

# Result: v2 docs with analytics + custom workflows preserved
```

### Example 3: Advanced - Multi-Version Migrations, Complex Customizations

**Scenario:** Full-featured framework with extensive documentation

**Package structure:**
```
advanced_framework/
├── templates/
│   ├── base/
│   │   ├── claude.md.jinja2
│   │   ├── gemini.md.jinja2
│   │   └── getting-started.md.jinja2
│   ├── shared/
│   │   ├── api-reference.md.jinja2
│   │   ├── examples.md.jinja2
│   │   └── troubleshooting.md.jinja2
│   └── advanced/
│       ├── architecture.md.jinja2
│       └── performance.md.jinja2
├── migrations/
│   ├── 001_to_002.py
│   ├── 002_to_003.py
│   └── 003_to_004.py
└── cli.py
```

**Complex customization example:**
```jinja2
{# User template: .framework/templates/claude.md.jinja2 #}
{% extends "base/claude.md.jinja2" %}

{# Override configuration with team-specific setup #}
{% block configuration %}
## Our Production Configuration

```yaml
environment: production
features:
  - advanced_caching
  - distributed_tracing
  - auto_scaling

integrations:
  - datadog
  - sentry
  - pagerduty
```

{{ super() }}  {# Include package defaults too #}
{% endblock %}

{# Add custom deployment section #}
{% block deployment %}
## Deployment Workflow

### Our CI/CD Pipeline
1. Run tests in Docker
2. Build production images
3. Deploy to staging
4. Run smoke tests
5. Deploy to production
6. Monitor metrics

### Rollback Procedure
```bash
framework rollback --version $(cat .last-stable)
```
{% endblock %}

{# Override troubleshooting with team incidents #}
{% block troubleshooting %}
{{ super() }}

### Team Incident History
- **2025-01-15**: Database connection pool exhausted
  - Solution: Increased pool size to 50
- **2025-01-10**: Cache invalidation race condition
  - Solution: Added distributed locks
{% endblock %}
```

**Multi-version migration path:**
```python
# User on version 1, package at version 4
# Migration path: 1 → 2 → 3 → 4

migrations = [
    Migration001To002,  # Add analytics
    Migration002To003,  # Restructure API reference
    Migration003To004,  # Add deployment section
]

for migration_class in migrations:
    migration = migration_class(project_root, "advanced_framework")
    success = migration.run()
    if not success:
        print("Migration failed, rolling back")
        break
```

**Conflict resolution:**
```python
# Version 3 → 4 migration adds deployment section
# User already has custom deployment section
# Detect conflict and offer resolution

def migrate(self, customizations: dict) -> bool:
    if "deployment" in customizations["customized_blocks"]:
        print("⚠️  Conflict: You have a custom deployment section")
        print("   Package v4 adds official deployment documentation")
        print("\nOptions:")
        print("1. Keep your custom deployment docs")
        print("2. Switch to package deployment docs")
        print("3. Merge both (you'll need to edit)")

        choice = click.prompt("Choose", type=int)

        if choice == 3:
            # Create merged template
            self._create_merge_template(customizations)
            print("✅ Created merged template for manual editing")
            print("   Edit: .framework/templates/claude.md.jinja2")
            return True

    # Proceed with migration
    ...
```

---

## 10. Resources

### HtmlGraph Source Code

**Reference implementation:**
- **Template Engine**: `src/python/htmlgraph/template_engine.py`
- **Models**: `src/python/htmlgraph/models.py`
- **Migrations**: `src/python/htmlgraph/migrations/`
- **CLI**: `src/python/htmlgraph/cli.py` (docs subcommands)
- **Tests**: `tests/test_docs_system.py`

**GitHub:**
- Repository: https://github.com/shakes-tzd/htmlgraph
- Templates: `/src/python/htmlgraph/templates/`
- Migration examples: `/src/python/htmlgraph/migrations/`

### External Documentation

**Jinja2:**
- Official Docs: https://jinja.palletsprojects.com/
- Template Designer Docs: https://jinja.palletsprojects.com/en/3.1.x/templates/
- API Reference: https://jinja.palletsprojects.com/en/3.1.x/api/

**Pydantic v2:**
- Documentation: https://docs.pydantic.dev/latest/
- Migration Guide (v1→v2): https://docs.pydantic.dev/latest/migration/
- Validators: https://docs.pydantic.dev/latest/concepts/validators/

**Packaging:**
- Semantic Versioning: https://semver.org/
- Python Packaging Guide: https://packaging.python.org/
- Version Specifiers: https://peps.python.org/pep-0440/

### Related Patterns

**Configuration Management:**
- Dynaconf: https://www.dynaconf.com/ (layered config)
- Hydra: https://hydra.cc/ (config composition)

**Template Systems:**
- Cookiecutter: https://cookiecutter.readthedocs.io/ (project templates)
- Copier: https://copier.readthedocs.io/ (template updates)

**Migration Systems:**
- Alembic: https://alembic.sqlalchemy.org/ (database migrations)
- Django Migrations: https://docs.djangoproject.com/en/stable/topics/migrations/

### Community Examples

**Tools using similar patterns:**
- **Cookiecutter** - Project templates with updates
- **Copier** - Template-based project generation with updates
- **Homebrew** - Formula templates with user customization
- **Oh My Zsh** - Plugin system with custom overrides

---

## Conclusion

The packageable auto-updating documentation pattern solves the challenge of keeping AI agent instructions current while preserving user customizations. By combining:

1. **Jinja2 template inheritance** for flexible customization
2. **Dual versioning** for compatibility tracking
3. **Migration scripts** for safe upgrades
4. **Metadata tracking** for state management

...developers can build documentation systems that:
- ✅ Auto-update with package releases
- ✅ Preserve user customizations
- ✅ Support safe rollback
- ✅ Work across multiple platforms
- ✅ Scale to complex use cases

**Next Steps:**
1. Review HtmlGraph's implementation for working examples
2. Adapt the pattern to your package's needs
3. Start with simple template inheritance
4. Add migrations as your documentation evolves
5. Share your learnings with the community

**Remember:** Start simple, add complexity only when needed. A basic template system is better than no system at all.

---

*This guide was created based on HtmlGraph's proven implementation. For questions or contributions, see: https://github.com/shakes-tzd/htmlgraph*
