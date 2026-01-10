---
name: codex
executable: agents/codex-spawner.py
model: haiku
description: OpenAI Codex spawner - Code generation and completions with sandbox execution
capabilities:
  - code_generation
  - implementation
  - file_operations
context_window: 128K tokens
cost: PAID (OpenAI)
requires_cli: codex
---

# Codex Spawner Agent

Spawn OpenAI Codex for professional code generation, implementation tasks, and file operations.

## Usage

```
Task(
    subagent_type="htmlgraph:codex",
    prompt="Implement a secure JWT authentication middleware",
    description="Code implementation"
)
```

## Capabilities

- **Code Generation**: High-quality, production-ready code
- **Implementation**: Complete feature implementations
- **File Operations**: Read, write, and transform files
- **Sandbox Execution**: Test code in isolated environment
- **Specialized for Code**: Trained specifically on coding tasks

## When to Use

- ✅ Production code implementation
- ✅ Complex algorithms and data structures
- ✅ Security-critical implementations
- ✅ Performance-optimized code
- ✅ When you need high-quality, specialized code

## Parameters

- `--prompt`: Task description for Codex
- `--model`: Model selection (default: gpt-4-turbo)
- `--sandbox`: Enable/disable sandbox execution
- `--output-json`: Return output as JSON
- `--timeout`: Max seconds to wait (default: 120)

## Requirements

- Codex CLI installed: `pip install openai`
- Set `OPENAI_API_KEY` environment variable
- OpenAI API credits for usage

## Event Tracking

All Codex spawner invocations are automatically tracked in HtmlGraph:
- Delegation events with full context
- Execution duration and status
- Token usage and cost metrics
- Agent attribution (actual AI model, not wrapper)
- Sandbox execution details

## Pricing

Usage is billed to your OpenAI account at standard Codex rates.
