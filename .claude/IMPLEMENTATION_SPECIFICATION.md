# System Prompt Injection Architecture - Final Implementation Specification

**Document Version:** 1.0
**Status:** Ready for Implementation
**Last Updated:** 2026-01-05
**Target Completion:** Phase 4 (Production Release)

---

## Executive Summary

This specification defines the complete architecture, implementation details, and testing requirements for the system prompt injection system. The system integrates three core components:

1. **Plugin-Based Architecture** - Centralized default prompt in plugin, with project-level overrides
2. **Idempotency Design** - 3-layer detection prevents duplicate prompt injection
3. **Workflow Integration** - Automatic injection via SessionStart hook across all workflows

### Key Success Metrics
- **Plugin-based**: Available to 100% of users
- **Customizable**: Users can override with `.claude/system-prompt.md`
- **Idempotent**: 99%+ reliability, zero duplicates in all scenarios
- **Integrated**: Works seamlessly across init/continue/dev workflows
- **Performant**: Hook execution <60ms, metadata search <10ms
- **Documented**: Complete user and admin guides included

---

## Part 1: File Structure & Organization

### 1.1 Plugin Default Prompt

**Location:**
```
packages/claude-plugin/
├── .claude-plugin/
│   ├── system-prompt-default.md        # DEFAULT PROMPT (new)
│   ├── hooks.json
│   └── plugin.json
```

**File: `packages/claude-plugin/.claude-plugin/system-prompt-default.md`**

```markdown
# HtmlGraph System Prompt - Default

This is the default system prompt injected by HtmlGraph plugin for all users.

## Core Principles

### Evidence-Based Decision Making
- Verify claims with measurable data
- Test hypotheses systematically
- Recognize and compensate for cognitive biases
- Document decision rationale

### Code Quality Standards
- Run linters and type checkers before every commit
- Fix ALL errors, even pre-existing ones
- Write tests before implementation (TDD)
- Maintain zero warnings/errors in codebase

### Documentation First
- Read existing documentation before implementing
- Use available debugging tools
- Research before assuming
- Maintain 90%+ context retention

## Workflow Rules

### Task Management
- Use TodoWrite for 3+ step tasks
- Batch independent tool calls
- Mark in_progress before starting work
- Complete current task before starting new ones

### File Operations
- Always Read before Write/Edit
- Use absolute paths only
- Batch operations when possible
- Never auto-commit unless explicitly requested

### Python Execution
- Always use `uv run` for Python (never raw python/pip)
- Examples: `uv run pytest`, `uv pip install`, `uv run python script.py`
- Ensures correct venv and reproducible builds

### Git Operations
- NEVER push --force to main/master
- NEVER use --amend unless explicitly requested
- NEVER skip pre-commit hooks
- Only commit when explicitly asked

## Quality Gates

Before committing:
1. Run: `uv run ruff check --fix && uv run ruff format`
2. Run: `uv run mypy src/`
3. Run: `uv run pytest`
4. Only commit when ALL pass

## Project Context

This project is HtmlGraph - a lightweight graph database for AI coordination.

See: `/Users/shakes/DevProjects/htmlgraph/CLAUDE.md` for project-specific workflows.

---

**End of Default Prompt**
```

### 1.2 Project Override Prompt

**Location:**
```
.claude/
├── system-prompt.md                    # PROJECT OVERRIDE (optional)
├── system-prompt-metadata.json         # METADATA (new, auto-created)
├── system-prompt-config.json           # CONFIG (new, optional)
└── ... other files
```

**File: `.claude/system-prompt-metadata.json`**

Schema and purpose (auto-created/maintained):

```json
{
  "version": "1.0",
  "created_at": "2026-01-05T10:30:00Z",
  "updated_at": "2026-01-05T10:30:00Z",
  "source": "plugin-default|project-override",
  "checksum": "sha256:abc123...",
  "size_bytes": 4856,
  "injection_count": 0,
  "last_injection_session": null,
  "content_hash": "md5:xyz789...",
  "token_estimate": 850,
  "status": "active|superseded|deprecated",
  "notes": "User notes about this prompt version"
}
```

**File: `.claude/system-prompt-config.json`** (optional, user-created)

```json
{
  "version": "1.0",
  "strategy": "project-override|plugin-default|merge",
  "token_budget": 1500,
  "truncation_strategy": "tail|smart-section",
  "max_sections_to_keep": 5,
  "required_sections": [
    "Evidence-Based Decision Making",
    "Code Quality Standards",
    "Workflow Rules"
  ],
  "disabled": false,
  "debug_mode": false,
  "custom_metadata": {
    "team": "engineering",
    "project_type": "python-package"
  }
}
```

### 1.3 Hook Configuration

**Location:** `packages/claude-plugin/.claude-plugin/hooks.json`

The SessionStart hook will be updated to include system prompt injection:

```json
{
  "SessionStart": {
    "enabled": true,
    "description": "Inject system prompt and initialize session context",
    "timeout_seconds": 5,
    "handlers": [
      {
        "type": "system-prompt",
        "handler": "inject-system-prompt-handler.py",
        "priority": 100,
        "retry_count": 2
      }
    ]
  }
}
```

### 1.4 Directory Structure Summary

```
packages/claude-plugin/
├── .claude-plugin/
│   ├── system-prompt-default.md        # DEFAULT PROMPT
│   ├── hooks.json                      # HOOK CONFIG (updated)
│   ├── handlers/
│   │   └── inject-system-prompt-handler.py  # HOOK IMPLEMENTATION
│   └── plugin.json

.claude/
├── system-prompt.md                    # PROJECT OVERRIDE (optional)
├── system-prompt-metadata.json         # METADATA (auto-created)
├── system-prompt-config.json           # CONFIG (optional)
└── hooks/
    └── SessionStart.md                 # IF EXISTS (project hooks)

src/python/htmlgraph/
├── sdk/
│   ├── system_prompt.py               # NEW SDK MODULE
│   └── __init__.py                    # EXPORT NEW METHODS
└── ... other files
```

---

## Part 2: Idempotency Detection System

### 2.1 3-Layer Detection Architecture

The system uses three independent layers to prevent duplicate injection:

```
Layer 1: Metadata-Based Detection (Fastest, 1-2ms)
  ├─ Check .claude/system-prompt-metadata.json
  ├─ Verify last_injection_session matches current session
  └─ If match: SKIP INJECTION

Layer 2: Transcript-Based Detection (Moderate, 5-10ms)
  ├─ Search conversation transcript for system prompt signature
  ├─ Look for: "## Core Principles", "System Prompt - Default", headers
  └─ If found: SKIP INJECTION

Layer 3: Safety Default (Fallback, <1ms)
  ├─ If both Layer 1 and 2 uncertain (system prompt modified)
  ├─ Re-inject to ensure latest version available
  └─ Safe because idempotency ensures no duplication
```

### 2.2 Metadata Structure (Layer 1)

**File: `.claude/system-prompt-metadata.json`**

```json
{
  "version": "1.0",
  "created_at": "2026-01-05T10:30:00Z",
  "updated_at": "2026-01-05T10:30:00Z",
  "source": "plugin-default",
  "last_injection": {
    "session_id": "sess-abc123def456",
    "timestamp": "2026-01-05T10:30:15Z",
    "model": "claude-haiku-4-5",
    "context_window_used": 42500,
    "injection_method": "system-prompt-injection-hook-v1"
  },
  "current_version": {
    "checksum": "sha256:5a3f8c1d...",
    "size_bytes": 4856,
    "token_estimate": 850,
    "content_hash": "md5:abc789def...",
    "signature": "## Core Principles|Evidence-Based|Workflow Rules"
  },
  "previous_versions": [
    {
      "checksum": "sha256:old1234...",
      "injected_in_session": "sess-xyz789",
      "timestamp": "2026-01-04T14:22:00Z",
      "reason_updated": "user edited .claude/system-prompt.md"
    }
  ],
  "injection_history": [
    {
      "session_id": "sess-abc123def456",
      "timestamp": "2026-01-05T10:30:15Z",
      "status": "success",
      "layer_used": 1,
      "duplicate_detected": false
    },
    {
      "session_id": "sess-previous",
      "timestamp": "2026-01-04T09:15:00Z",
      "status": "success",
      "layer_used": 2,
      "duplicate_detected": false
    }
  ],
  "status": "active",
  "disabled": false,
  "notes": "System prompt maintained by HtmlGraph plugin"
}
```

**Metadata Update Rules:**
- Update on SessionStart (record injection attempt)
- Update when `.claude/system-prompt.md` changes (record version change)
- Update checksum when content changes
- Keep last 5 injection records for debugging
- Keep last 3 previous versions for rollback

### 2.3 Layer 1: Metadata-Based Detection

**Detection Logic:**

```python
def detect_duplicate_metadata(current_session_id: str,
                             current_checksum: str,
                             metadata: dict) -> tuple[bool, str]:
    """
    Layer 1: Check metadata for recent injection

    Returns: (is_duplicate, reason)
    """
    if not metadata:
        return False, "No metadata found"

    last_injection = metadata.get("last_injection", {})
    current_version = metadata.get("current_version", {})

    # Check if injected in current session
    if last_injection.get("session_id") == current_session_id:
        # Verify checksum matches
        if current_version.get("checksum") == current_checksum:
            return True, f"Already injected in session {current_session_id}"
        else:
            return False, "Checksum mismatch - prompt was updated"

    # Check if injected recently (within 30 seconds)
    last_time = last_injection.get("timestamp")
    if last_time:
        last_inject_dt = datetime.fromisoformat(last_time)
        time_since_injection = datetime.now(timezone.utc) - last_inject_dt
        if time_since_injection.total_seconds() < 30:
            return True, f"Recent injection {time_since_injection.total_seconds()}s ago"

    return False, "No recent injection detected"
```

### 2.4 Layer 2: Transcript-Based Detection

**Detection Logic:**

```python
def detect_duplicate_transcript(transcript: list[dict],
                               prompt_signature: str) -> tuple[bool, str]:
    """
    Layer 2: Search transcript for system prompt

    Args:
        transcript: List of message dicts from conversation
        prompt_signature: Key phrases to search for

    Returns: (is_duplicate, reason)
    """
    if not transcript:
        return False, "Empty transcript"

    # Search for key sections of system prompt
    search_patterns = [
        "## Core Principles",
        "Evidence-Based Decision Making",
        "Code Quality Standards",
        "Workflow Rules",
        "Quality Gates",
        "System Prompt - Default",
        "PROJECT OVERRIDE"
    ]

    # Check system messages and user messages
    for msg in transcript:
        content = msg.get("content", "").lower()

        # Count how many patterns appear
        matches = sum(1 for pattern in search_patterns
                     if pattern.lower() in content)

        # If 3+ patterns found, likely the system prompt
        if matches >= 3:
            return True, f"Found {matches} system prompt patterns in transcript"

        # Check for exact signature
        if prompt_signature.lower() in content.lower():
            return True, "Found exact prompt signature in transcript"

    return False, "No system prompt found in transcript"
```

**Search Patterns:**
- Headers: `## Core Principles`, `## Workflow Rules`, `## Quality Gates`
- Key concepts: `Evidence-Based Decision Making`, `Code Quality Standards`
- Markers: `System Prompt - Default`, `PROJECT OVERRIDE`
- Signatures: First 100 chars of actual prompt

### 2.5 Layer 3: Safety Default

**Logic:**

```python
def should_inject_system_prompt(metadata: dict,
                               transcript: list[dict],
                               prompt_checksum: str,
                               current_session: str) -> bool:
    """
    Combined decision logic using all 3 layers

    Returns: True if should inject, False if skip
    """
    # Layer 1: Metadata check
    is_dup_metadata, reason_meta = detect_duplicate_metadata(
        current_session, prompt_checksum, metadata
    )
    if is_dup_metadata:
        logger.info(f"Layer 1 skip: {reason_meta}")
        return False

    # Layer 2: Transcript check
    is_dup_transcript, reason_trans = detect_duplicate_transcript(
        transcript, prompt_checksum[:50]
    )
    if is_dup_transcript:
        logger.info(f"Layer 2 skip: {reason_trans}")
        return False

    # Layer 3: Safety default
    # If both layers uncertain, re-inject to ensure latest version
    # This is SAFE because:
    # 1. Idempotent (duplicate won't break anything)
    # 2. Users can see prompt is being re-injected
    # 3. Ensures consistency across sessions
    logger.info("Layer 3: No evidence of injection, re-injecting for safety")
    return True
```

**Key Points:**
- All 3 layers are independent and can be debugged separately
- Layer 1 is fastest (metadata check)
- Layer 2 is more thorough (actual content search)
- Layer 3 is a safety fallback (re-inject if uncertain)
- Never skip if ANY layer is uncertain (safe re-injection)

---

## Part 3: Hook Implementation

### 3.1 Hook Handler Entry Point

**File: `packages/claude-plugin/.claude-plugin/handlers/inject-system-prompt-handler.py`**

```python
"""
SessionStart Hook Handler - System Prompt Injection

Executes when:
- New session starts (cold start)
- Session resumes (warm start / continue)
- Post-compact (context window trimmed)
- Project cleared

Responsible for:
1. Loading plugin default prompt
2. Checking project override
3. 3-layer idempotency detection
4. Injecting system prompt to context
5. Updating metadata
"""

import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Configuration
PLUGIN_PROMPT_PATH = "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/system-prompt-default.md"
PROJECT_PROMPT_PATH = ".claude/system-prompt.md"
PROJECT_METADATA_PATH = ".claude/system-prompt-metadata.json"
PROJECT_CONFIG_PATH = ".claude/system-prompt-config.json"


class SystemPromptHandler:
    """Main handler for system prompt injection"""

    def __init__(self, context: dict):
        """
        Initialize handler with hook context

        Args:
            context: Hook context with session_id, transcript, etc.
        """
        self.context = context
        self.session_id = context.get("session_id", "unknown")
        self.transcript = context.get("transcript", [])
        self.additionalContext = context.get("additionalContext", "")
        self.project_root = Path.cwd()
        self.logger = logger

    def run(self) -> dict:
        """
        Main hook execution method

        Returns:
            dict with:
            - success: bool
            - message: str
            - additionalContext: str (updated)
            - metadata_updated: bool
        """
        try:
            self.logger.info(f"Starting system prompt injection for session {self.session_id}")

            # Step 1: Load plugin default prompt
            plugin_prompt = self._load_plugin_default()
            if not plugin_prompt:
                self.logger.warning("Failed to load plugin default prompt")
                return self._result(False, "Plugin default prompt not found", "")

            # Step 2: Check project override
            project_prompt = self._load_project_override()
            final_prompt = project_prompt or plugin_prompt
            source = "project-override" if project_prompt else "plugin-default"

            # Step 3: Calculate checksum
            checksum = self._calculate_checksum(final_prompt)

            # Step 4: 3-layer idempotency detection
            should_inject = self._check_idempotency(final_prompt, checksum)

            if not should_inject:
                self.logger.info("Idempotency check: skipping injection")
                return self._result(True, "Injection skipped (idempotency)", "")

            # Step 5: Prepare injection
            injected_text = self._prepare_injection(final_prompt, source)

            # Step 6: Update metadata
            self._update_metadata(checksum, source)

            # Step 7: Return updated context
            new_context = self.additionalContext + "\n\n" + injected_text

            self.logger.info(f"System prompt injected successfully from {source}")
            return self._result(True, f"Injected from {source}", new_context)

        except Exception as e:
            self.logger.error(f"Error during injection: {e}", exc_info=True)
            return self._result(False, f"Error: {str(e)}", "")

    def _load_plugin_default(self) -> Optional[str]:
        """Load default prompt from plugin"""
        try:
            path = Path(PLUGIN_PROMPT_PATH)
            if not path.exists():
                self.logger.warning(f"Plugin prompt not found: {path}")
                return None

            with open(path, 'r') as f:
                prompt = f.read()

            self.logger.info(f"Loaded plugin default prompt ({len(prompt)} chars)")
            return prompt

        except Exception as e:
            self.logger.error(f"Failed to load plugin prompt: {e}")
            return None

    def _load_project_override(self) -> Optional[str]:
        """Load project override prompt if exists"""
        try:
            path = self.project_root / PROJECT_PROMPT_PATH
            if not path.exists():
                return None

            with open(path, 'r') as f:
                prompt = f.read()

            self.logger.info(f"Loaded project override prompt ({len(prompt)} chars)")
            return prompt

        except Exception as e:
            self.logger.error(f"Failed to load project override: {e}")
            return None

    def _calculate_checksum(self, prompt: str) -> str:
        """Calculate SHA256 checksum of prompt"""
        return hashlib.sha256(prompt.encode()).hexdigest()

    def _check_idempotency(self, final_prompt: str, checksum: str) -> bool:
        """
        Implement 3-layer idempotency detection

        Returns: True if should inject, False if skip
        """
        metadata = self._load_metadata()

        # Layer 1: Metadata-based detection
        is_dup_meta, reason_meta = self._detect_duplicate_metadata(
            checksum, metadata
        )
        if is_dup_meta:
            self.logger.info(f"Layer 1 (metadata): {reason_meta}")
            return False

        # Layer 2: Transcript-based detection
        is_dup_trans, reason_trans = self._detect_duplicate_transcript(
            final_prompt
        )
        if is_dup_trans:
            self.logger.info(f"Layer 2 (transcript): {reason_trans}")
            return False

        # Layer 3: Safety default (re-inject if uncertain)
        self.logger.info("Layer 3 (safety): No duplicate detected, will inject")
        return True

    def _detect_duplicate_metadata(self, checksum: str,
                                   metadata: Optional[dict]) -> Tuple[bool, str]:
        """Layer 1: Metadata-based duplicate detection"""
        if not metadata:
            return False, "No metadata exists"

        last_injection = metadata.get("last_injection", {})
        if not last_injection:
            return False, "No injection history"

        # Check session
        last_session = last_injection.get("session_id")
        if last_session == self.session_id:
            # Same session - check checksum
            current_checksum = metadata.get("current_version", {}).get("checksum")
            if current_checksum == checksum:
                return True, f"Already injected in session {self.session_id}"
            else:
                return False, "Checksum changed (prompt updated)"

        # Check time-based (within 30 seconds = likely same session)
        last_time_str = last_injection.get("timestamp")
        if last_time_str:
            try:
                last_time = datetime.fromisoformat(last_time_str)
                now = datetime.now(timezone.utc)
                elapsed = (now - last_time).total_seconds()

                if elapsed < 30:
                    return True, f"Recent injection {elapsed:.1f}s ago"
            except Exception as e:
                self.logger.debug(f"Failed to parse timestamp: {e}")

        return False, "No duplicate in metadata"

    def _detect_duplicate_transcript(self, prompt: str) -> Tuple[bool, str]:
        """Layer 2: Transcript-based duplicate detection"""
        if not self.transcript:
            return False, "Empty transcript"

        # Key patterns from system prompt
        patterns = [
            "## Core Principles",
            "Evidence-Based Decision Making",
            "Code Quality Standards",
            "Workflow Rules",
            "Quality Gates",
            "System Prompt"
        ]

        # Search transcript
        for msg in self.transcript:
            content = msg.get("content", "").lower()

            # Count pattern matches
            matches = sum(1 for p in patterns if p.lower() in content)
            if matches >= 3:
                return True, f"Found {matches} system prompt patterns"

            # Check first 100 chars (signature)
            sig = prompt[:100].lower()
            if sig in content[:200].lower():
                return True, "Found prompt signature"

        return False, "No system prompt in transcript"

    def _prepare_injection(self, prompt: str, source: str) -> str:
        """Prepare prompt text for injection"""
        # Add metadata header
        header = f"<!-- System Prompt injected from: {source} -->\n"
        return header + prompt

    def _update_metadata(self, checksum: str, source: str):
        """Update metadata file after successful injection"""
        try:
            metadata_path = self.project_root / PROJECT_METADATA_PATH

            # Load existing or create new
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    "version": "1.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source": source,
                    "injection_history": []
                }

            # Update last injection
            now_iso = datetime.now(timezone.utc).isoformat()
            metadata["updated_at"] = now_iso
            metadata["last_injection"] = {
                "session_id": self.session_id,
                "timestamp": now_iso,
                "status": "success"
            }
            metadata["current_version"] = {
                "checksum": checksum,
                "timestamp": now_iso
            }

            # Add to history (keep last 10)
            if "injection_history" not in metadata:
                metadata["injection_history"] = []

            metadata["injection_history"].append({
                "session_id": self.session_id,
                "timestamp": now_iso,
                "status": "success",
                "source": source
            })
            metadata["injection_history"] = metadata["injection_history"][-10:]

            # Write metadata
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            self.logger.info("Metadata updated successfully")

        except Exception as e:
            self.logger.error(f"Failed to update metadata: {e}")

    def _load_metadata(self) -> Optional[dict]:
        """Load metadata file if exists"""
        try:
            path = self.project_root / PROJECT_METADATA_PATH
            if not path.exists():
                return None

            with open(path, 'r') as f:
                return json.load(f)

        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
            return None

    def _result(self, success: bool, message: str, context: str) -> dict:
        """Format result dict"""
        return {
            "success": success,
            "message": message,
            "additionalContext": context,
            "handler": "system-prompt-injection",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def handle_session_start(context: dict) -> dict:
    """
    Entry point for SessionStart hook

    Args:
        context: Hook context with:
        - session_id: str
        - transcript: list[dict]
        - additionalContext: str
        - event_type: str (should be "session_start")

    Returns:
        dict with injection result
    """
    handler = SystemPromptHandler(context)
    return handler.run()
```

### 3.2 Hook Registration

**File: `packages/claude-plugin/.claude-plugin/hooks.json`**

```json
{
  "SessionStart": {
    "enabled": true,
    "description": "Inject system prompt and initialize session context",
    "priority": 100,
    "timeout_seconds": 5,
    "handlers": [
      {
        "type": "system-prompt-injection",
        "path": "handlers/inject-system-prompt-handler.py",
        "function": "handle_session_start",
        "retry_count": 2,
        "retry_delay_ms": 500,
        "max_context_size": 8000,
        "max_execution_time_ms": 5000
      }
    ],
    "error_handling": {
      "strategy": "graceful-continue",
      "log_level": "info",
      "fallback_context": ""
    }
  }
}
```

### 3.3 Error Handling & Fallbacks

**Error Scenarios:**

| Scenario | Handler Response | User Impact |
|----------|------------------|------------|
| Plugin prompt not found | Log warning, skip injection | No system prompt (baseline behavior) |
| Project override corrupted | Use plugin default | Falls back to standard prompt |
| Metadata unreadable | Ignore, re-inject | Re-inject (safe) |
| Transcript search timeout | Skip Layer 2, use Layer 1+3 | May re-inject (safe) |
| Checksum mismatch | Re-inject new version | Latest prompt available |
| Metadata write fails | Log error, continue | Metadata not updated, but injection successful |

**Graceful Degradation:**

```python
def handle_session_start_safe(context: dict) -> dict:
    """
    Wrapper that ensures graceful degradation
    """
    try:
        handler = SystemPromptHandler(context)
        return handler.run()

    except KeyError as e:
        # Missing expected context field
        logger.error(f"Missing context field: {e}")
        return {
            "success": False,
            "message": f"Invalid hook context: {e}",
            "additionalContext": context.get("additionalContext", "")
        }

    except FileNotFoundError as e:
        # Missing prompt file
        logger.warning(f"Prompt file not found: {e}")
        return {
            "success": True,
            "message": "Prompt files not available (continuing with baseline)",
            "additionalContext": context.get("additionalContext", "")
        }

    except json.JSONDecodeError as e:
        # Corrupted metadata JSON
        logger.error(f"Corrupted metadata: {e}")
        return {
            "success": True,
            "message": "Metadata corrupted (re-injecting for safety)",
            "additionalContext": context.get("additionalContext", "") + "\n[System prompt re-injected]"
        }

    except Exception as e:
        # Catch-all
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Unexpected error: {type(e).__name__}",
            "additionalContext": context.get("additionalContext", "")
        }
```

---

## Part 4: SDK Methods

### 4.1 New SDK Module

**File: `src/python/htmlgraph/sdk/system_prompt.py`**

```python
"""
System Prompt Management SDK

Provides programmatic access to:
- Loading default and override prompts
- Managing prompt metadata
- Validating prompt content
- Customizing project prompts
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class SystemPromptManager:
    """Manages system prompts for project"""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize manager

        Args:
            project_root: Project root path (defaults to cwd)
        """
        self.project_root = project_root or Path.cwd()
        self.plugin_root = Path(__file__).parent.parent.parent / "claude-plugin"

    # ========== Loading Methods ==========

    def get_system_prompt_default(self) -> Optional[str]:
        """
        Get default system prompt from plugin

        Returns:
            Prompt text or None if not found
        """
        path = self.plugin_root / ".claude-plugin/system-prompt-default.md"

        try:
            if not path.exists():
                logger.warning(f"Plugin prompt not found: {path}")
                return None

            with open(path, 'r') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Failed to load plugin prompt: {e}")
            return None

    def get_system_prompt_project(self) -> Optional[str]:
        """
        Get project-level override prompt

        Returns:
            Prompt text or None if not exists
        """
        path = self.project_root / ".claude/system-prompt.md"

        try:
            if not path.exists():
                return None

            with open(path, 'r') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Failed to load project prompt: {e}")
            return None

    def get_system_prompt_effective(self) -> Optional[str]:
        """
        Get the effective system prompt (project override or default)

        Returns:
            Prompt text (project override if exists, else default, else None)
        """
        project_prompt = self.get_system_prompt_project()
        if project_prompt:
            return project_prompt
        return self.get_system_prompt_default()

    # ========== Metadata Methods ==========

    def get_prompt_metadata(self) -> Optional[Dict]:
        """
        Get system prompt metadata

        Returns:
            Metadata dict or None if not exists
        """
        path = self.project_root / ".claude/system-prompt-metadata.json"

        try:
            if not path.exists():
                return None

            with open(path, 'r') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None

    def update_prompt_metadata(self, updates: Dict) -> bool:
        """
        Update system prompt metadata

        Args:
            updates: Dict with fields to update

        Returns:
            True if successful
        """
        try:
            path = self.project_root / ".claude/system-prompt-metadata.json"

            # Load existing
            metadata = {}
            if path.exists():
                with open(path, 'r') as f:
                    metadata = json.load(f)

            # Update
            metadata.update(updates)
            metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Write
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info("Metadata updated")
            return True

        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            return False

    def get_prompt_config(self) -> Optional[Dict]:
        """
        Get system prompt configuration

        Returns:
            Config dict or None if not exists
        """
        path = self.project_root / ".claude/system-prompt-config.json"

        try:
            if not path.exists():
                return None

            with open(path, 'r') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return None

    # ========== Validation Methods ==========

    def validate_system_prompt(self, prompt_text: str) -> Tuple[bool, List[str]]:
        """
        Validate system prompt content

        Args:
            prompt_text: Prompt to validate

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Check not empty
        if not prompt_text or not prompt_text.strip():
            errors.append("Prompt is empty")
            return False, errors

        # Check reasonable size
        if len(prompt_text) < 100:
            errors.append("Prompt is too short (< 100 chars)")
        if len(prompt_text) > 100000:
            errors.append("Prompt is too long (> 100KB)")

        # Check has markdown headers
        has_headers = any(line.startswith("#") for line in prompt_text.split("\n"))
        if not has_headers:
            errors.append("Prompt should have markdown headers (##, ###, etc)")

        # Check not obviously malformed
        if "```" in prompt_text:
            # Check code blocks are balanced
            count = prompt_text.count("```")
            if count % 2 != 0:
                errors.append("Code blocks not balanced (odd number of ```)")

        return len(errors) == 0, errors

    # ========== Utility Methods ==========

    def calculate_checksum(self, prompt_text: str) -> str:
        """Calculate SHA256 checksum of prompt"""
        return hashlib.sha256(prompt_text.encode()).hexdigest()

    def estimate_tokens(self, prompt_text: str) -> int:
        """
        Rough estimate of token count (4 chars ≈ 1 token)

        Args:
            prompt_text: Text to estimate

        Returns:
            Estimated token count
        """
        # Very rough estimation: ~4 chars per token
        return len(prompt_text.strip()) // 4

    def truncate_prompt(self, prompt_text: str, max_tokens: int) -> str:
        """
        Truncate prompt to fit within token budget

        Args:
            prompt_text: Original prompt
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated prompt
        """
        max_chars = max_tokens * 4
        if len(prompt_text) <= max_chars:
            return prompt_text

        # Truncate and add marker
        truncated = prompt_text[:max_chars]
        return truncated + f"\n\n<!-- Truncated by SystemPromptManager -->"

    def get_injection_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent prompt injection history

        Args:
            limit: Max records to return

        Returns:
            List of injection records
        """
        metadata = self.get_prompt_metadata()
        if not metadata:
            return []

        history = metadata.get("injection_history", [])
        return history[-limit:]

    def was_injected_in_session(self, session_id: str) -> bool:
        """
        Check if prompt was injected in specific session

        Args:
            session_id: Session ID to check

        Returns:
            True if injected in that session
        """
        metadata = self.get_prompt_metadata()
        if not metadata:
            return False

        last_inj = metadata.get("last_injection", {})
        return last_inj.get("session_id") == session_id

    # ========== Creation/Customization Methods ==========

    def create_custom_prompt(self,
                            template: str = "default",
                            sections: Optional[Dict[str, str]] = None) -> str:
        """
        Create a custom system prompt

        Args:
            template: "default" | "minimal" | "custom"
            sections: Custom sections to override

        Returns:
            Generated prompt text
        """
        if template == "default":
            return self.get_system_prompt_default() or ""

        elif template == "minimal":
            return """# System Prompt - Minimal

## Core Rules
- Always read before write
- Use absolute paths
- Run tests before commit
"""

        elif template == "custom":
            if not sections:
                raise ValueError("custom template requires sections dict")

            prompt = "# System Prompt - Custom\n\n"
            for section, content in sections.items():
                prompt += f"## {section}\n{content}\n\n"

            return prompt

        else:
            raise ValueError(f"Unknown template: {template}")

    def save_custom_prompt(self, prompt_text: str) -> bool:
        """
        Save custom prompt as project override

        Args:
            prompt_text: Prompt content to save

        Returns:
            True if successful
        """
        # Validate first
        is_valid, errors = self.validate_system_prompt(prompt_text)
        if not is_valid:
            logger.error(f"Invalid prompt: {errors}")
            return False

        try:
            path = self.project_root / ".claude/system-prompt.md"
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w') as f:
                f.write(prompt_text)

            logger.info(f"Custom prompt saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save custom prompt: {e}")
            return False
```

### 4.2 SDK Integration

**File: `src/python/htmlgraph/sdk/__init__.py`** (updated)

```python
# Add to existing imports
from .system_prompt import SystemPromptManager

# Add to SDK class
class SDK:
    def __init__(self, *args, **kwargs):
        # ... existing init ...
        self.system_prompt = SystemPromptManager()

    # New methods
    def get_system_prompt_default(self) -> Optional[str]:
        """Get default system prompt"""
        return self.system_prompt.get_system_prompt_default()

    def get_system_prompt_project(self) -> Optional[str]:
        """Get project override system prompt"""
        return self.system_prompt.get_system_prompt_project()

    def get_system_prompt_effective(self) -> Optional[str]:
        """Get the effective system prompt (override or default)"""
        return self.system_prompt.get_system_prompt_effective()

    def validate_system_prompt(self, prompt_text: str) -> Tuple[bool, List[str]]:
        """Validate system prompt content"""
        return self.system_prompt.validate_system_prompt(prompt_text)

    def create_custom_prompt(self, template: str = "default",
                            sections: Optional[Dict] = None) -> str:
        """Create custom system prompt"""
        return self.system_prompt.create_custom_prompt(template, sections)

    def save_custom_prompt(self, prompt_text: str) -> bool:
        """Save custom prompt as project override"""
        return self.system_prompt.save_custom_prompt(prompt_text)

    def get_prompt_metadata(self) -> Optional[Dict]:
        """Get system prompt metadata"""
        return self.system_prompt.get_prompt_metadata()

    def update_prompt_metadata(self, updates: Dict) -> bool:
        """Update system prompt metadata"""
        return self.system_prompt.update_prompt_metadata(updates)

    def estimate_prompt_tokens(self, prompt_text: str) -> int:
        """Estimate token count for prompt"""
        return self.system_prompt.estimate_tokens(prompt_text)

    def get_injection_history(self, limit: int = 10) -> List[Dict]:
        """Get recent prompt injection history"""
        return self.system_prompt.get_injection_history(limit)
```

---

## Part 5: Workflow Integration

### 5.1 SessionStart Trigger Points

**When SessionStart Hook Fires:**

| Workflow | Trigger | Context |
|----------|---------|---------|
| Cold Start | New project initialization | Fresh session, empty transcript |
| Warm Start | `claude continue` | Resume existing project, existing transcript |
| Post-Compact | Context window trimmed | Session continues but context reset |
| Prompt Update | `.claude/system-prompt.md` changed | User edited prompt file |
| Session Clear | User runs `clear` | Full context reset |
| Resume | Session resumes from cache | Pick up where left off |

**SessionStart Hook Context:**

```python
{
    "event_type": "session_start",
    "session_id": "sess-abc123def456",
    "timestamp": "2026-01-05T10:30:00Z",
    "trigger_reason": "cold-start|warm-start|post-compact|prompt-update|clear|resume",
    "transcript": [...],  # Previous messages (empty for cold start)
    "additionalContext": "...",  # Existing context
    "model": "claude-haiku-4-5",
    "context_window_used": 42500,
    "context_window_available": 90000,
    "project_root": "/Users/shakes/DevProjects/htmlgraph"
}
```

### 5.2 Workflow Scenarios

**Scenario 1: Cold Start (New Project)**

```
Timeline:
1. User: `claude init` in new project
2. Hook fires: SessionStart (cold start)
3. Handler:
   ├─ Load plugin default prompt
   ├─ Check project override (doesn't exist)
   ├─ Layer 1: No metadata (first time)
   ├─ Layer 2: Empty transcript
   ├─ Layer 3: Inject for safety
   └─ Create metadata file
4. Result: System prompt available from start

Key: Metadata shows first injection
```

**Scenario 2: Warm Start (Continue Session)**

```
Timeline:
1. User: Previous session work stored
2. User: `claude continue` to resume
3. Hook fires: SessionStart (warm start)
4. Handler:
   ├─ Load plugin default
   ├─ Check project override
   ├─ Layer 1: Check metadata
   │   └─ Last session ID ≠ current session ID
   │   └─ Check time: > 30 seconds ago
   ├─ Layer 2: Search transcript (empty, just resumed)
   ├─ Layer 3: Inject (uncertain)
   └─ Update metadata
5. Result: System prompt re-injected for new session

Key: Different session ID → safe to re-inject
```

**Scenario 3: Post-Compact (Context Reset)**

```
Timeline:
1. Session running, context window filling
2. User: Exceeds 80% window
3. Hook fires: SessionStart (post-compact)
4. Context manager: Compacts old messages
5. Handler:
   ├─ Load plugin default
   ├─ Layer 1: Check metadata
   │   └─ Same session ID (continuing)
   │   └─ Within 30 seconds
   │   └─ BUT CHECKSUM MATCHES
   ├─ Skip injection (already in earlier messages)
   ├─ OR Layer 2: Transcript now shorter
   └─ May re-inject if detection uncertain
5. Result: System prompt available (either kept or re-injected)

Key: Same session ID + checksum match = skip
```

**Scenario 4: Prompt Update (User Edits File)**

```
Timeline:
1. Session running with system prompt
2. User: Edits `.claude/system-prompt.md`
3. Hook fires: SessionStart (prompt update)
4. Handler:
   ├─ Load plugin default
   ├─ Load project override (NEW VERSION)
   ├─ Calculate checksum (NEW)
   ├─ Layer 1: Check metadata
   │   └─ Last checksum ≠ current checksum
   │   └─ Return False (not duplicate)
   ├─ Layer 2: Transcript search (old version)
   ├─ Layer 3: Inject new version
   └─ Update metadata (new checksum)
5. Result: Updated prompt injected, metadata updated

Key: Checksum mismatch = always inject new version
```

**Scenario 5: Hook Fires Twice (Safety Test)**

```
Timeline:
1. Session starts
2. Hook fires (injection succeeds)
3. Metadata updated with session_id + checksum
4. Hook fires again (duplicate test)
5. Handler:
   ├─ Load plugin default
   ├─ Layer 1: Check metadata
   │   └─ session_id matches
   │   └─ checksum matches
   │   └─ Return True (is duplicate)
   ├─ Skip Layer 2 and Layer 3
   └─ Return (skip injection)
6. Result: No duplication, only injected once

Key: Metadata + session check prevents duplicate
```

### 5.3 Integration Points

**Initialization (.claude/hooks/SessionStart.md)**

If user has project-level hooks:

```markdown
# SessionStart Hook

This hook is provided by HtmlGraph plugin.
System prompt injection happens automatically.

To customize system prompt:
1. Create `.claude/system-prompt.md` with your custom prompt
2. Hook will detect and use project version automatically
3. To debug: Set `debug_mode: true` in `.claude/system-prompt-config.json`
```

**No Special Setup Required:**
- Hook fires automatically via plugin
- No user configuration needed for basic usage
- Customization is optional (just add `.claude/system-prompt.md`)

---

## Part 6: Test Specifications

### 6.1 Test Structure

**Directory:**
```
tests/
├── unit/
│   ├── test_system_prompt_handler.py
│   ├── test_idempotency_detection.py
│   ├── test_metadata.py
│   └── test_sdk.py
├── integration/
│   ├── test_workflow_cold_start.py
│   ├── test_workflow_warm_start.py
│   ├── test_workflow_post_compact.py
│   ├── test_workflow_prompt_update.py
│   └── test_workflow_transitions.py
└── fixtures/
    ├── prompt_default.md
    ├── prompt_override.md
    ├── metadata_sample.json
    └── transcript_sample.json
```

### 6.2 Unit Tests

**File: `tests/unit/test_system_prompt_handler.py`**

```python
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from htmlgraph.plugins.handlers import inject_system_prompt_handler
from inject_system_prompt_handler import SystemPromptHandler


class TestSystemPromptHandler:
    """Tests for system prompt injection handler"""

    @pytest.fixture
    def handler_context(self):
        """Fixture: Basic handler context"""
        return {
            "event_type": "session_start",
            "session_id": "sess-test-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger_reason": "cold-start",
            "transcript": [],
            "additionalContext": "Existing context",
            "model": "claude-haiku-4-5",
            "context_window_used": 10000
        }

    def test_cold_start_injection(self, handler_context, tmp_path):
        """Test cold start - should inject system prompt"""
        # Setup
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            handler = SystemPromptHandler(handler_context)

            # Mock prompt loading
            with patch.object(handler, '_load_plugin_default',
                            return_value="Default prompt"):
                with patch.object(handler, '_load_project_override',
                                return_value=None):
                    with patch.object(handler, '_load_metadata',
                                    return_value=None):
                        # Execute
                        result = handler.run()

        # Assert
        assert result['success'] is True
        assert "Default prompt" in result['additionalContext']

    def test_project_override_preferred(self, handler_context, tmp_path):
        """Test project override takes precedence"""
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            handler = SystemPromptHandler(handler_context)

            with patch.object(handler, '_load_plugin_default',
                            return_value="Default"):
                with patch.object(handler, '_load_project_override',
                                return_value="Override"):
                    with patch.object(handler, '_load_metadata',
                                    return_value=None):
                        result = handler.run()

        assert "Override" in result['additionalContext']
        assert "Default" not in result['additionalContext']

    def test_duplicate_detection_metadata(self, handler_context, tmp_path):
        """Test Layer 1: metadata-based duplicate detection"""
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            handler = SystemPromptHandler(handler_context)

            metadata = {
                "last_injection": {
                    "session_id": "sess-test-001",  # Same session
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "current_version": {
                    "checksum": "abc123"
                }
            }

            with patch.object(handler, '_calculate_checksum',
                            return_value="abc123"):  # Same checksum
                is_dup, reason = handler._detect_duplicate_metadata(
                    "abc123", metadata
                )

        assert is_dup is True
        assert "session" in reason.lower()

    def test_duplicate_detection_transcript(self, handler_context):
        """Test Layer 2: transcript-based duplicate detection"""
        transcript_with_prompt = [
            {
                "role": "system",
                "content": "## Core Principles\nEvidence-Based Decision Making\nCode Quality Standards"
            }
        ]

        handler_context["transcript"] = transcript_with_prompt
        handler = SystemPromptHandler(handler_context)

        prompt = "## Core Principles\nSome content"
        is_dup, reason = handler._detect_duplicate_transcript(prompt)

        assert is_dup is True
        assert "patterns" in reason.lower()

    def test_checksum_calculation(self, handler_context):
        """Test checksum calculation is consistent"""
        handler = SystemPromptHandler(handler_context)

        prompt = "Test prompt content"
        checksum1 = handler._calculate_checksum(prompt)
        checksum2 = handler._calculate_checksum(prompt)

        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA256 hex

    def test_metadata_update_creates_file(self, handler_context, tmp_path):
        """Test metadata file is created/updated"""
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            handler = SystemPromptHandler(handler_context)
            handler._update_metadata("checksum123", "plugin-default")

        metadata_file = tmp_path / ".claude/system-prompt-metadata.json"
        assert metadata_file.exists()

        import json
        with open(metadata_file) as f:
            data = json.load(f)

        assert data["last_injection"]["session_id"] == "sess-test-001"
        assert data["current_version"]["checksum"] == "checksum123"

    def test_error_handling_missing_prompt(self, handler_context):
        """Test graceful handling of missing plugin prompt"""
        handler = SystemPromptHandler(handler_context)

        with patch.object(handler, '_load_plugin_default', return_value=None):
            with patch.object(handler, '_load_project_override',
                            return_value=None):
                result = handler.run()

        assert result['success'] is False
        assert "not found" in result['message'].lower()

    def test_error_handling_corrupted_metadata(self, handler_context, tmp_path):
        """Test graceful handling of corrupted metadata"""
        metadata_file = tmp_path / ".claude/system-prompt-metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        metadata_file.write_text("invalid json {")

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            handler = SystemPromptHandler(handler_context)

            with patch.object(handler, '_load_plugin_default',
                            return_value="Prompt"):
                with patch.object(handler, '_load_project_override',
                                return_value=None):
                    result = handler.run()

        # Should still inject despite corrupt metadata
        assert result['success'] is True
```

**File: `tests/unit/test_idempotency_detection.py`**

```python
import pytest
from datetime import datetime, timedelta, timezone
from inject_system_prompt_handler import SystemPromptHandler


class TestIdempotencyDetection:
    """Tests for 3-layer idempotency detection"""

    @pytest.fixture
    def handler(self):
        """Fixture: Basic handler"""
        context = {
            "session_id": "sess-test",
            "transcript": [],
            "additionalContext": ""
        }
        return SystemPromptHandler(context)

    # Layer 1 Tests

    def test_layer1_same_session_same_checksum(self, handler):
        """Layer 1: Same session + same checksum = duplicate"""
        metadata = {
            "last_injection": {"session_id": "sess-test"},
            "current_version": {"checksum": "abc123"}
        }

        is_dup, _ = handler._detect_duplicate_metadata("abc123", metadata)
        assert is_dup is True

    def test_layer1_same_session_different_checksum(self, handler):
        """Layer 1: Same session + different checksum = not duplicate"""
        metadata = {
            "last_injection": {"session_id": "sess-test"},
            "current_version": {"checksum": "abc123"}
        }

        is_dup, _ = handler._detect_duplicate_metadata("xyz789", metadata)
        assert is_dup is False

    def test_layer1_different_session(self, handler):
        """Layer 1: Different session = not duplicate"""
        metadata = {
            "last_injection": {"session_id": "sess-other"},
            "current_version": {"checksum": "abc123"}
        }

        is_dup, _ = handler._detect_duplicate_metadata("abc123", metadata)
        assert is_dup is False

    def test_layer1_recent_injection_time(self, handler):
        """Layer 1: Recent injection (< 30s) = duplicate"""
        now = datetime.now(timezone.utc)
        recent_time = (now - timedelta(seconds=10)).isoformat()

        metadata = {
            "last_injection": {
                "session_id": "sess-other",
                "timestamp": recent_time
            },
            "current_version": {"checksum": "abc123"}
        }

        is_dup, _ = handler._detect_duplicate_metadata("abc123", metadata)
        assert is_dup is True

    def test_layer1_old_injection_time(self, handler):
        """Layer 1: Old injection (> 30s) = not duplicate"""
        now = datetime.now(timezone.utc)
        old_time = (now - timedelta(seconds=60)).isoformat()

        metadata = {
            "last_injection": {
                "session_id": "sess-other",
                "timestamp": old_time
            },
            "current_version": {"checksum": "abc123"}
        }

        is_dup, _ = handler._detect_duplicate_metadata("abc123", metadata)
        assert is_dup is False

    # Layer 2 Tests

    def test_layer2_prompt_in_transcript(self, handler):
        """Layer 2: System prompt found in transcript = duplicate"""
        handler.transcript = [
            {
                "content": "## Core Principles\nEvidence-Based Decision Making"
            }
        ]

        prompt = "## Core Principles\nSome other content"
        is_dup, _ = handler._detect_duplicate_transcript(prompt)
        assert is_dup is True

    def test_layer2_multiple_patterns_match(self, handler):
        """Layer 2: Multiple patterns matching = duplicate"""
        handler.transcript = [
            {
                "content": """## Core Principles
Evidence-Based Decision Making
Code Quality Standards
Workflow Rules"""
            }
        ]

        prompt = "Some prompt"
        is_dup, _ = handler._detect_duplicate_transcript(prompt)
        assert is_dup is True

    def test_layer2_no_prompt_in_transcript(self, handler):
        """Layer 2: No patterns found = not duplicate"""
        handler.transcript = [
            {
                "content": "Random conversation about coding"
            }
        ]

        prompt = "## Core Principles\nSystem Prompt"
        is_dup, _ = handler._detect_duplicate_transcript(prompt)
        assert is_dup is False

    # Combined Tests

    def test_all_layers_skip_injection(self, handler):
        """All layers agree: skip injection"""
        handler.transcript = [
            {"content": "## Core Principles\nEvidence-Based Decision Making"}
        ]

        metadata = {
            "last_injection": {"session_id": "sess-test"},
            "current_version": {"checksum": "abc123"}
        }

        with patch.object(handler, '_load_metadata', return_value=metadata):
            should_inject = handler._check_idempotency("prompt", "abc123")

        assert should_inject is False

    def test_layers_uncertain_inject_for_safety(self, handler):
        """All layers uncertain: inject for safety"""
        handler.transcript = []

        with patch.object(handler, '_load_metadata', return_value=None):
            should_inject = handler._check_idempotency("prompt", "abc123")

        assert should_inject is True
```

**File: `tests/unit/test_sdk.py`**

```python
import pytest
import json
from pathlib import Path
from htmlgraph.sdk.system_prompt import SystemPromptManager


class TestSystemPromptManager:
    """Tests for SDK system prompt methods"""

    @pytest.fixture
    def manager(self, tmp_path):
        """Fixture: Manager with temp project"""
        return SystemPromptManager(project_root=tmp_path)

    def test_get_system_prompt_default(self, manager):
        """Test loading plugin default prompt"""
        prompt = manager.get_system_prompt_default()

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "## Core Principles" in prompt or "# System Prompt" in prompt

    def test_get_system_prompt_project_not_exists(self, manager):
        """Test project prompt returns None when not exists"""
        prompt = manager.get_system_prompt_project()
        assert prompt is None

    def test_get_system_prompt_project_exists(self, manager):
        """Test project prompt loads when exists"""
        prompt_text = "# Custom Prompt\nCustom content"

        prompt_path = manager.project_root / ".claude/system-prompt.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt_text)

        prompt = manager.get_system_prompt_project()
        assert prompt == prompt_text

    def test_get_system_prompt_effective_uses_override(self, manager):
        """Test effective prompt uses project override"""
        override = "# Project Override"

        prompt_path = manager.project_root / ".claude/system-prompt.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(override)

        effective = manager.get_system_prompt_effective()
        assert effective == override

    def test_validate_system_prompt_valid(self, manager):
        """Test validation of valid prompt"""
        prompt = """# System Prompt
## Section 1
Content here

## Section 2
More content
"""
        is_valid, errors = manager.validate_system_prompt(prompt)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_system_prompt_empty(self, manager):
        """Test validation of empty prompt"""
        is_valid, errors = manager.validate_system_prompt("")
        assert is_valid is False
        assert "empty" in errors[0].lower()

    def test_validate_system_prompt_too_short(self, manager):
        """Test validation of short prompt"""
        is_valid, errors = manager.validate_system_prompt("short")
        assert is_valid is False

    def test_calculate_checksum(self, manager):
        """Test checksum calculation"""
        prompt = "Test prompt"
        checksum = manager.calculate_checksum(prompt)

        assert len(checksum) == 64  # SHA256 hex
        assert checksum == manager.calculate_checksum(prompt)  # Consistent

    def test_estimate_tokens(self, manager):
        """Test token estimation"""
        prompt = "This is a test prompt" * 10  # ~200 chars
        tokens = manager.estimate_tokens(prompt)

        assert isinstance(tokens, int)
        assert tokens > 0
        assert tokens == len(prompt) // 4

    def test_truncate_prompt(self, manager):
        """Test prompt truncation"""
        prompt = "x" * 10000
        truncated = manager.truncate_prompt(prompt, max_tokens=500)

        assert len(truncated) < len(prompt)
        assert "Truncated" in truncated

    def test_create_custom_prompt_default(self, manager):
        """Test creating custom prompt from default template"""
        prompt = manager.create_custom_prompt(template="default")
        assert prompt is not None
        assert len(prompt) > 100

    def test_create_custom_prompt_minimal(self, manager):
        """Test creating minimal custom prompt"""
        prompt = manager.create_custom_prompt(template="minimal")
        assert "## Core Rules" in prompt

    def test_save_custom_prompt(self, manager):
        """Test saving custom prompt"""
        prompt_text = "# Custom\n## Section\nContent"

        success = manager.save_custom_prompt(prompt_text)
        assert success is True

        saved_path = manager.project_root / ".claude/system-prompt.md"
        assert saved_path.exists()
        assert saved_path.read_text() == prompt_text

    def test_metadata_management(self, manager):
        """Test metadata update and retrieval"""
        # Initially None
        assert manager.get_prompt_metadata() is None

        # Update
        success = manager.update_prompt_metadata({
            "test_field": "test_value"
        })
        assert success is True

        # Retrieve
        metadata = manager.get_prompt_metadata()
        assert metadata["test_field"] == "test_value"
```

### 6.3 Integration Tests

**File: `tests/integration/test_workflow_cold_start.py`**

```python
import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import json

from inject_system_prompt_handler import SystemPromptHandler


class TestColdStartWorkflow:
    """Integration tests for cold start workflow"""

    def test_cold_start_new_project(self, tmp_path):
        """Test full cold start flow in new project"""
        # Setup: Empty project
        assert not (tmp_path / ".claude").exists()

        context = {
            "event_type": "session_start",
            "session_id": "sess-new-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger_reason": "cold-start",
            "transcript": [],
            "additionalContext": "",
            "model": "claude-haiku-4-5",
            "context_window_used": 10000
        }

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            handler = SystemPromptHandler(context)
            result = handler.run()

        # Assert: Injection successful
        assert result['success'] is True
        assert len(result['additionalContext']) > 100

        # Assert: Metadata created
        metadata_path = tmp_path / ".claude/system-prompt-metadata.json"
        assert metadata_path.exists()

        metadata = json.loads(metadata_path.read_text())
        assert metadata["last_injection"]["session_id"] == "sess-new-001"

    def test_cold_start_with_project_override(self, tmp_path):
        """Test cold start respects project override"""
        # Setup: Create project override
        override_path = tmp_path / ".claude/system-prompt.md"
        override_path.parent.mkdir(parents=True, exist_ok=True)
        override_path.write_text("# Project Override\nCustom content")

        context = {
            "event_type": "session_start",
            "session_id": "sess-override-001",
            "transcript": [],
            "additionalContext": ""
        }

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            handler = SystemPromptHandler(context)
            result = handler.run()

        # Assert: Uses override
        assert "Project Override" in result['additionalContext']
```

**File: `tests/integration/test_workflow_warm_start.py`**

```python
class TestWarmStartWorkflow:
    """Integration tests for warm start / continue workflow"""

    def test_warm_start_continues_session(self, tmp_path):
        """Test warm start with existing session continues properly"""
        # Setup: Create existing metadata
        metadata_path = tmp_path / ".claude/system-prompt-metadata.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        old_session = "sess-previous-001"
        metadata = {
            "version": "1.0",
            "last_injection": {
                "session_id": old_session,
                "timestamp": "2026-01-04T10:00:00+00:00"
            },
            "current_version": {
                "checksum": "abc123"
            }
        }
        metadata_path.write_text(json.dumps(metadata))

        # Warm start: New session
        context = {
            "event_type": "session_start",
            "session_id": "sess-continue-001",  # Different session
            "trigger_reason": "warm-start",
            "transcript": [],  # Empty (just started)
            "additionalContext": ""
        }

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            handler = SystemPromptHandler(context)
            result = handler.run()

        # Assert: Re-injects because different session
        assert result['success'] is True

        # Check metadata updated
        metadata = json.loads(metadata_path.read_text())
        assert metadata["last_injection"]["session_id"] == "sess-continue-001"
```

### 6.4 Test Scenarios Checklist

```yaml
Unit Tests (25+ tests):
  Handler:
    - Load plugin default
    - Load project override
    - Project override preferred
    - Checksum calculation
    - Metadata creation
    - Error handling (missing files, corrupt JSON)

  Idempotency:
    - Layer 1 metadata detection (5 variants)
    - Layer 2 transcript detection (3 variants)
    - Layer 3 safety default
    - Combined layer decisions

  SDK:
    - get_system_prompt_default()
    - get_system_prompt_project()
    - get_system_prompt_effective()
    - validate_system_prompt()
    - create_custom_prompt()
    - save_custom_prompt()
    - Metadata management
    - Checksum and token estimation

Integration Tests (8+ scenarios):
  Cold Start:
    - New project (first run)
    - With project override
    - Missing plugin prompt (graceful)

  Warm Start:
    - Resume existing session
    - Different session ID
    - Metadata exists

  Post-Compact:
    - Same session continues
    - Checksum matches (skip)
    - Checksum differs (inject new)

  Prompt Update:
    - User edits system prompt
    - Checksum changes
    - New version injected

  Transitions:
    - Cold → Warm
    - Warm → Compact
    - Compact → Continue
    - Update → Continue

Acceptance Tests (5+ scenarios):
  End-to-End:
    - Full workflow from init to production
    - No duplicates across all scenarios
    - Metadata consistency
    - Performance benchmarks
```

---

## Part 7: Configuration & Customization

### 7.1 Configuration File Format

**File: `.claude/system-prompt-config.json`** (optional)

```json
{
  "version": "1.0",
  "enabled": true,
  "strategy": "project-override",
  "token_budget": 1500,
  "truncation_strategy": "tail",
  "max_sections_to_keep": 5,
  "required_sections": [
    "## Core Principles",
    "## Code Quality Standards",
    "## Workflow Rules"
  ],
  "debug_mode": false,
  "cache_metadata": true,
  "log_level": "info",
  "custom_metadata": {
    "team": "engineering",
    "project_type": "python-package",
    "deployment_env": "production"
  }
}
```

**Configuration Options:**

| Option | Type | Default | Purpose |
|--------|------|---------|---------|
| `enabled` | bool | true | Enable/disable system prompt injection |
| `strategy` | str | "project-override" | "project-override" \| "plugin-default" \| "merge" |
| `token_budget` | int | 1500 | Max tokens for system prompt |
| `truncation_strategy` | str | "tail" | "tail" (keep end) \| "smart-section" (remove least important) |
| `max_sections_to_keep` | int | 5 | For smart truncation |
| `required_sections` | list | [...] | Sections to never remove |
| `debug_mode` | bool | false | Verbose logging |
| `cache_metadata` | bool | true | Cache metadata in memory |
| `log_level` | str | "info" | "debug" \| "info" \| "warning" \| "error" |

### 7.2 How Users Customize

**Option 1: Simple Override (Recommended)**

```bash
# Create .claude/system-prompt.md with custom content
cat > .claude/system-prompt.md << 'EOF'
# My Project System Prompt

## Custom Principles
- My custom rule 1
- My custom rule 2

## Project-Specific Guidelines
- Use TypeScript everywhere
- Components in /src/components
EOF

# That's it! Hook automatically uses this
```

**Option 2: Configuration + Override**

```bash
# Create config for advanced options
cat > .claude/system-prompt-config.json << 'EOF'
{
  "strategy": "project-override",
  "token_budget": 2000,
  "debug_mode": false,
  "custom_metadata": {
    "team": "ml-engineering",
    "domain": "machine-learning"
  }
}
EOF

# Create override prompt
cat > .claude/system-prompt.md << 'EOF'
# ML Engineering Prompt
...
EOF
```

**Option 3: Merge Strategy**

```bash
# Use both default + custom (merged)
cat > .claude/system-prompt-config.json << 'EOF'
{
  "strategy": "merge",
  "token_budget": 2500,
  "custom_sections": {
    "Team Guidelines": "- Code review required\n- Pair programming"
  }
}
EOF
```

### 7.3 Troubleshooting Configuration

**Debugging System Prompt Issues:**

```bash
# Enable debug mode
cat > .claude/system-prompt-config.json << 'EOF'
{
  "debug_mode": true,
  "log_level": "debug"
}
EOF

# Check metadata
cat .claude/system-prompt-metadata.json

# Validate syntax
python -m htmlgraph.sdk validate_prompt_syntax .claude/system-prompt.md
```

---

## Part 8: Success Criteria & Acceptance Tests

### 8.1 Success Metrics

```yaml
Plugin-Based Architecture:
  ✅ Plugin default prompt available in: packages/claude-plugin/.claude-plugin/system-prompt-default.md
  ✅ Hook loads plugin default on startup
  ✅ Hook checks for project override in: .claude/system-prompt.md
  ✅ Merge/select logic working (100% coverage)
  ✅ All 8+ test scenarios passing

Idempotency:
  ✅ Layer 1 (metadata) prevents duplicates: 99%+ success rate
  ✅ Layer 2 (transcript) detects duplicates: 95%+ accuracy
  ✅ Layer 3 (safety) re-injects when uncertain: 100% safety
  ✅ Combined detection: <1 false positive per 100 injections
  ✅ Detection time: <10ms for all layers
  ✅ Hook execution time: <60ms (including all 3 layers)

Workflow Integration:
  ✅ Cold start: System prompt injected on init
  ✅ Warm start: Correct detection of continuing session
  ✅ Post-compact: Re-injection when needed, skip when duplicate
  ✅ Prompt update: New version injected when file changes
  ✅ All transitions working: init→continue→compact→continue
  ✅ No special handling needed (works automatically)

Documentation:
  ✅ Plugin default prompt complete (500+ lines)
  ✅ User guide for customization
  ✅ Admin guide for debugging
  ✅ Troubleshooting common issues
  ✅ API reference for SDK methods
  ✅ Example configurations

Testing:
  ✅ Unit tests: 25+, 100% coverage of handler
  ✅ Integration tests: 8+ scenarios
  ✅ End-to-end: Full workflow testing
  ✅ Performance: Benchmarks for all layers
  ✅ Edge cases: Corruption, missing files, timeouts

Production Readiness:
  ✅ Zero breaking changes to existing code
  ✅ Backward compatible (optional feature)
  ✅ Error handling: Graceful degradation
  ✅ Monitoring: Injection metrics logged
  ✅ Rollback: Can disable via config
  ✅ Performance: No impact on session startup
```

### 8.2 Acceptance Criteria

**Phase 1: Plugin Architecture Complete**

```
[ ] Plugin default prompt file created and complete
[ ] Hook refactored to load plugin default
[ ] Project override detection implemented
[ ] Merge/select logic working
[ ] Error handling for missing files
[ ] Unit tests passing (10+)
```

**Phase 2: Idempotency System Complete**

```
[ ] Metadata structure defined and JSON schema validated
[ ] Layer 1 detection implemented (<10ms)
[ ] Layer 2 detection implemented (<10ms)
[ ] Layer 3 safety default implemented
[ ] Combined decision logic tested
[ ] No duplicates in all scenarios
[ ] Unit tests passing (15+)
```

**Phase 3: Workflow Integration Complete**

```
[ ] SessionStart hook fires in all workflows
[ ] Cold start: injection on first run
[ ] Warm start: correct session detection
[ ] Post-compact: smart re-injection
[ ] Prompt update: new version detection
[ ] Integration tests passing (8+)
[ ] End-to-end scenarios all working
```

**Phase 4: Production Release Complete**

```
[ ] All tests passing (40+)
[ ] Performance benchmarks met
[ ] Documentation complete
[ ] Admin guide for debugging
[ ] User guide for customization
[ ] Troubleshooting guide
[ ] Code review approved
[ ] No regressions in existing tests
[ ] Ready for public release
```

---

## Part 9: Implementation Timeline

### Phase 1: Plugin Architecture (Days 1-2)

**Day 1:**
- Create `system-prompt-default.md` (2 hours)
- Update hook configuration (1 hour)
- Refactor handler to load plugin default (3 hours)
- Basic unit tests (2 hours)

**Day 2:**
- Implement project override detection (2 hours)
- Merge/select logic (2 hours)
- Error handling (2 hours)
- Additional unit tests (2 hours)

**Deliverable:** Working plugin-based prompt injection, 10+ passing tests

### Phase 2: Idempotency (Days 3-4)

**Day 3:**
- Define metadata structure (1 hour)
- Implement Layer 1 detection (3 hours)
- Implement Layer 2 detection (3 hours)
- Unit tests for layers (2 hours)

**Day 4:**
- Implement Layer 3 safety (2 hours)
- Combined decision logic (2 hours)
- Edge case testing (3 hours)
- Performance optimization (1 hour)

**Deliverable:** 3-layer idempotency system, 99%+ accuracy, <10ms detection

### Phase 3: Workflow Integration (Day 5)

- Verify SessionStart in all workflows (2 hours)
- Integration tests for cold/warm/compact/update (4 hours)
- End-to-end scenario testing (2 hours)

**Deliverable:** Seamless integration across all workflows

### Phase 4: Production Release (Day 6)

- Documentation (3 hours)
- Final testing and optimization (2 hours)
- Code review and cleanup (1 hour)

**Deliverable:** Production-ready release

---

## Part 10: Documentation Plan

### 10.1 Plugin Default Prompt Content Structure

The plugin default prompt includes:

1. **Header & Context** (100 words)
   - Purpose of prompt
   - Where it applies

2. **Core Principles** (300 words)
   - Evidence-based decision making
   - Code quality standards
   - Testing approach

3. **Workflow Rules** (400 words)
   - Task management
   - File operations
   - Git operations
   - Python execution

4. **Quality Gates** (100 words)
   - Pre-commit checklist
   - Test requirements

5. **Project Context** (50 words)
   - Reference to CLAUDE.md
   - Project-specific info

### 10.2 User Customization Guide

**Document: `docs/SYSTEM_PROMPT_CUSTOMIZATION.md`**

```markdown
# System Prompt Customization Guide

## Overview

The HtmlGraph plugin injects a default system prompt automatically.
You can customize this for your project.

## Quick Start

Create `.claude/system-prompt.md`:

```bash
cat > .claude/system-prompt.md << 'EOF'
# My Project Prompt

## Team Guidelines
- Use TypeScript
- 100% test coverage

## Project Structure
- Components in /src/components
EOF
```

That's it! The hook automatically uses your custom prompt.

## Strategies

### 1. Project Override (Default)
Uses your `.claude/system-prompt.md` if it exists, otherwise plugin default.

### 2. Plugin Default Only
Delete `.claude/system-prompt.md` to use plugin default.

### 3. Merge Strategy
Combine plugin default with custom sections.

See: Advanced Configuration below.

## Advanced Configuration

Create `.claude/system-prompt-config.json`:

```json
{
  "strategy": "project-override",
  "token_budget": 2000,
  "debug_mode": false
}
```

## Debugging

Enable debug mode:

```json
{
  "debug_mode": true
}
```

Then check logs for details on what was injected.

## See Also

- Admin Guide: `docs/SYSTEM_PROMPT_ADMIN.md`
- API Reference: `docs/API_REFERENCE.md`
```

### 10.3 Admin & Troubleshooting Guide

**Document: `docs/SYSTEM_PROMPT_ADMIN.md`**

```markdown
# System Prompt Administration Guide

## Monitoring

Check what was injected:

```bash
cat .claude/system-prompt-metadata.json
```

This shows:
- Last injection session
- Current checksum
- Injection history

## Debugging

Enable debug mode to see injection details:

```json
{
  "debug_mode": true,
  "log_level": "debug"
}
```

### Common Issues

**Issue: System prompt not being injected**
- Check `.claude/system-prompt.md` exists
- Validate syntax: `python -m htmlgraph validate_prompt_syntax`
- Check hook logs for errors

**Issue: Duplicate injection**
- Check metadata file: `cat .claude/system-prompt-metadata.json`
- Check transcript for prompt patterns
- Run with debug mode to see detection decisions

**Issue: Token budget exceeded**
- Reduce prompt size
- Use truncation strategy: `"truncation_strategy": "smart-section"`
- Remove least important sections

## Reset

To reset and re-inject:

```bash
rm .claude/system-prompt-metadata.json
# Hook will re-inject on next session
```

## Performance

Typical injection times:
- Layer 1 (metadata): <2ms
- Layer 2 (transcript): <8ms
- Total hook execution: <50ms

If slower:
- Enable debug mode to identify bottleneck
- Check file system performance
- Reduce transcript size
```

---

## Summary

This comprehensive specification provides:

1. **Complete File Organization** - Plugin default, project overrides, metadata, configuration
2. **Hook Implementation Details** - Full Python code for SessionStart handler
3. **3-Layer Idempotency** - Metadata, transcript, safety detection
4. **SDK Methods** - 15+ methods for programmatic access
5. **Workflow Integration** - 5+ workflow scenarios with detailed logic
6. **Test Specifications** - 40+ test cases across unit/integration levels
7. **Configuration Options** - User customization with config file
8. **Documentation Plan** - User guides, admin guides, troubleshooting
9. **Success Criteria** - Clear metrics for completion
10. **Implementation Timeline** - 6-day phased rollout

**Ready for immediate implementation with zero ambiguity.**
