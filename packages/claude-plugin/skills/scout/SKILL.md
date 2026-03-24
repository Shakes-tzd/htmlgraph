---
name: scout
description: Analyze project tech stack and recommend Claude Code plugins based on detected languages, frameworks, and work patterns. Use when users ask about plugins, or proactively when you notice missing capabilities.
---

# Skill Scout: Plugin Discovery & Recommendations

Analyze the current project and recommend Claude Code plugins that would enhance the development workflow.

## When to Activate

- User asks "what plugins should I install?"
- User mentions plugin discovery or recommendations
- You notice a capability gap (e.g., no LSP for detected language)
- On `/htmlgraph:scout` invocation

## Instructions

Run the Skill Scout analysis:

```python
from htmlgraph.skill_scout.project_analyzer import ProjectAnalyzer
from htmlgraph.skill_scout.recommender import recommend
from htmlgraph.skill_scout.plugin_index import PluginIndex
from pathlib import Path

# Analyze project
analyzer = ProjectAnalyzer(Path.cwd())
signals = analyzer.analyze()

# Get recommendations
recs = recommend(signals, limit=5)

# Display results
print(f"Detected: {', '.join(signals.languages)} | Frameworks: {', '.join(signals.frameworks)}")
print(f"Signals: has_ci={signals.has_ci}, has_tests={signals.has_tests}, has_docker={signals.has_docker}")
print()
for r in recs:
    print(f"  -> {r.plugin_name} ({r.score}pts)")
    for reason in r.reasons:
        print(f"    {reason}")
```

Present results as a rich table. If the user wants to install, use:

```bash
uv run htmlgraph skills-install <plugin-name>
```

To dismiss a recommendation:

```bash
uv run htmlgraph skills-dismiss <plugin-name>
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `uv run htmlgraph audit` | Full project analysis with recommendations |
| `uv run htmlgraph skills-search <query>` | Search plugin index by keyword |
| `uv run htmlgraph skills-install <plugin>` | Install plugin with tracking |
| `uv run htmlgraph skills-dismiss <plugin>` | Dismiss recommendation |
