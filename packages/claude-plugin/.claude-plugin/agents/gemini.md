---
name: gemini
executable: agents/gemini-spawner.py
model: haiku
description: Google Gemini 2.0-Flash spawner - FREE exploratory research and batch analysis
capabilities:
  - exploration
  - analysis
  - batch_processing
context_window: 2M tokens
cost: FREE
requires_cli: gemini
---

# Gemini Spawner Agent

Spawn Google Gemini 2.0-Flash for exploratory research, batch analysis, and large-scale document processing.

## Usage

```
Task(
    subagent_type="htmlgraph:gemini",
    prompt="Analyze the codebase for authentication patterns",
    description="Research authentication implementation"
)
```

## Capabilities

- **Exploratory Research**: FREE unlimited tokens for investigation
- **Batch Analysis**: Process multiple files and documents
- **Large Context**: 2M token context window for comprehensive analysis
- **Cost-Effective**: Zero cost - perfect for discovery and research

## When to Use

- ✅ Large-scale codebase analysis
- ✅ Document research and summarization
- ✅ Pattern discovery across multiple files
- ✅ Exploratory data analysis
- ✅ When you need maximum context without cost

## Parameters

- `--prompt`: Task description for Gemini
- `--model`: Model selection (default: gemini-2.0-flash)
- `--output-format`: json or stream-json
- `--timeout`: Max seconds to wait (default: 120)
- `--include-directories`: Directories to include for context

## Requirements

- Gemini CLI installed: `pip install google-generativeai`
- Set `GOOGLE_API_KEY` environment variable

## Event Tracking

All Gemini spawner invocations are automatically tracked in HtmlGraph:
- Delegation events with full context
- Execution duration and status
- Token usage and cost metrics
- Agent attribution (actual AI model, not wrapper)
