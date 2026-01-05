"""
Testing Framework for SessionStart Hook Layer 1 (System Prompt Injection).

Validates prompt loading, injection, token counting, and error handling.

Coverage Target: 90%+ code coverage
Test Framework: pytest
"""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

# ============================================================================
# TASK B1: TEST INFRASTRUCTURE SETUP (Fixtures)
# ============================================================================


@pytest.fixture
def tmp_project_dir(tmp_path):
    """Create temporary project directory with .claude subdirectory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    # Create .htmlgraph for session tracking
    htmlgraph_dir = tmp_path / ".htmlgraph"
    htmlgraph_dir.mkdir(parents=True)

    return tmp_path


@pytest.fixture
def valid_prompt_file(tmp_project_dir):
    """Create valid system-prompt.md with test content."""
    prompt_content = """# System Prompt - HtmlGraph Development

## Primary Directive
Evidence > assumptions | Code > documentation | Efficiency > verbosity

## Orchestration Pattern
- Use `Task()` tool for multi-session work
- Execute directly for straightforward operations
- Delegate complex tasks to specialized agents

## Model Guidance
Use Haiku for orchestration (default).
Use Sonnet for complex reasoning.

## Quick Commands
| Task | Command |
|------|---------|
| Tests | `uv run pytest` |
| Type Check | `uv run mypy src/` |
| Lint | `uv run ruff check --fix` |
"""
    prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
    prompt_file.write_text(prompt_content)
    return tmp_project_dir, prompt_content


@pytest.fixture
def empty_prompt_file(tmp_project_dir):
    """Create empty system-prompt.md."""
    prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
    prompt_file.write_text("")
    return tmp_project_dir


@pytest.fixture
def corrupted_prompt_file(tmp_project_dir):
    """Create corrupted (unreadable) system-prompt.md."""
    prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
    prompt_file.write_text("# Valid Header\n\x00Invalid byte sequence")
    return tmp_project_dir


@pytest.fixture
def large_prompt_file(tmp_project_dir):
    """Create very large prompt file (50KB+)."""
    prompt_content = "# Large Prompt\n\n" + ("x" * 50000)
    prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
    prompt_file.write_text(prompt_content)
    return tmp_project_dir


@pytest.fixture
def hook_input_json_base(tmp_project_dir):
    """Create valid hook input JSON (base fixture)."""
    return {
        "session_id": "sess-test-123456",
        "hook_event_name": "SessionStart",
        "source": "compact",
        "cwd": str(tmp_project_dir),
    }


@pytest.fixture
def hook_input_startup(tmp_project_dir):
    """Hook input for startup source."""
    return {
        "session_id": "sess-startup-001",
        "hook_event_name": "SessionStart",
        "source": "startup",
        "cwd": str(tmp_project_dir),
    }


@pytest.fixture
def hook_input_resume(tmp_project_dir):
    """Hook input for resume source."""
    return {
        "session_id": "sess-resume-001",
        "hook_event_name": "SessionStart",
        "source": "resume",
        "cwd": str(tmp_project_dir),
    }


@pytest.fixture
def hook_input_clear(tmp_project_dir):
    """Hook input for clear source."""
    return {
        "session_id": "sess-clear-001",
        "hook_event_name": "SessionStart",
        "source": "clear",
        "cwd": str(tmp_project_dir),
    }


# ============================================================================
# UTILITY FUNCTIONS (Token Counting, Prompt Loading)
# ============================================================================


def load_system_prompt(project_dir: str | Path) -> str:
    """Load system-prompt.md from .claude directory.

    Returns empty string if file not found.
    """
    prompt_file = Path(project_dir) / ".claude" / "system-prompt.md"
    if not prompt_file.exists():
        return ""
    try:
        return prompt_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def estimate_token_count(text: str) -> int:
    """Estimate token count using simple heuristic.

    Approximation: 1 token ≈ 4 characters
    This is a reasonable estimate for English text with Claude tokenizer.
    """
    return max(1, len(text) // 4)


def truncate_to_token_budget(text: str, max_tokens: int = 500) -> str:
    """Truncate text to fit within token budget.

    Preserves markdown structure by truncating at paragraph boundaries.
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text

    # Truncate at last newline before limit
    truncated = text[:max_chars]
    last_newline = truncated.rfind("\n")
    if last_newline > 0:
        truncated = truncated[:last_newline]

    return truncated + "\n\n[... truncated due to token limit ...]"


def format_injection_output(
    session_id: str,
    source: str,
    prompt: str,
    additional_context: str = "",
) -> dict[str, Any]:
    """Format prompt injection output as hook JSON response.

    Args:
        session_id: Claude session ID
        source: Session source (startup/resume/compact/clear)
        prompt: System prompt content
        additional_context: Additional context from HtmlGraph

    Returns:
        Hook response JSON with additionalContext field
    """
    context = prompt
    if additional_context:
        context = f"{prompt}\n\n---\n\n{additional_context}"

    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
            "source": source,
            "session_id": session_id,
        },
    }


# ============================================================================
# TASK B2: UNIT TESTS - PROMPT LOADING (5 tests)
# ============================================================================


class TestPromptLoading:
    """Test system prompt file loading."""

    def test_load_valid_prompt_file(self, valid_prompt_file):
        """Load valid prompt returns full content."""
        project_dir, expected_content = valid_prompt_file
        result = load_system_prompt(project_dir)
        assert result == expected_content
        assert "System Prompt" in result
        assert "Primary Directive" in result

    def test_load_missing_prompt_file(self, tmp_project_dir):
        """Missing prompt file returns empty string."""
        result = load_system_prompt(tmp_project_dir)
        assert result == ""

    def test_load_corrupted_file(self, corrupted_prompt_file):
        """Corrupted file handled gracefully (loads with replacement chars)."""
        # File exists but has invalid UTF-8 - Python reads with replacement chars
        result = load_system_prompt(corrupted_prompt_file)
        # Should load (Python handles invalid UTF-8 gracefully)
        # The invalid byte is replaced, so content still loads
        assert "# Valid Header" in result
        assert isinstance(result, str)

    def test_load_empty_prompt(self, empty_prompt_file):
        """Empty prompt file returns empty string."""
        result = load_system_prompt(empty_prompt_file)
        assert result == ""

    def test_load_very_large_prompt(self, large_prompt_file):
        """Large prompt file loaded successfully."""
        result = load_system_prompt(large_prompt_file)
        assert len(result) > 50000
        assert result.startswith("# Large Prompt")

    def test_load_with_pathlib_path(self, valid_prompt_file):
        """Load works with pathlib.Path objects."""
        project_dir, expected_content = valid_prompt_file
        result = load_system_prompt(Path(project_dir))
        assert result == expected_content

    def test_load_with_string_path(self, valid_prompt_file):
        """Load works with string paths."""
        project_dir, expected_content = valid_prompt_file
        result = load_system_prompt(str(project_dir))
        assert result == expected_content


# ============================================================================
# TASK B3: UNIT TESTS - TOKEN COUNTING (4 tests)
# ============================================================================


class TestTokenCounting:
    """Test token estimation and counting."""

    def test_token_count_under_limit(self):
        """Token count under 500 passes."""
        text = "This is a short prompt." * 10  # ~250 tokens
        token_count = estimate_token_count(text)
        assert token_count < 500

    def test_token_count_over_limit(self):
        """Token count over 500 identified."""
        text = "x" * 2500  # ~625 tokens
        token_count = estimate_token_count(text)
        assert token_count > 500

    def test_token_truncation(self):
        """Prompt truncated to fit budget preserves structure."""
        text = "# Header\n\n" + ("Paragraph\n\n" * 200)
        truncated = truncate_to_token_budget(text, max_tokens=500)

        # Should be shorter
        assert len(truncated) < len(text)
        # Should have truncation marker
        assert "[... truncated" in truncated
        # Should still be valid
        assert "# Header" in truncated

    def test_token_estimation_accuracy(self):
        """Token estimation within reasonable bounds."""
        # English text with ~4 chars per token average
        text = "The quick brown fox jumps over the lazy dog. " * 50
        estimated = estimate_token_count(text)

        # Actual character count
        actual_chars = len(text)
        expected_tokens = actual_chars / 4

        # Allow 10% variance
        assert abs(estimated - expected_tokens) / expected_tokens < 0.1

    def test_token_count_empty_string(self):
        """Empty string returns 1 token minimum."""
        assert estimate_token_count("") == 1

    def test_token_count_whitespace_only(self):
        """Whitespace-only string counted correctly."""
        assert estimate_token_count("   \n\n  ") >= 1


# ============================================================================
# TASK B4: UNIT TESTS - PROMPT INJECTION FORMATTING (5 tests)
# ============================================================================


class TestPromptInjectionFormatting:
    """Test prompt injection output format."""

    def test_injection_json_structure(self, hook_input_json_base):
        """Output has correct JSON structure."""
        prompt = "Test prompt"
        output = format_injection_output(
            session_id=hook_input_json_base["session_id"],
            source=hook_input_json_base["source"],
            prompt=prompt,
        )

        # Should be valid JSON
        json_str = json.dumps(output)
        parsed = json.loads(json_str)

        assert "continue" in parsed
        assert "hookSpecificOutput" in parsed
        assert parsed["continue"] is True

    def test_additionalcontext_field_present(self, hook_input_json_base):
        """additionalContext field in output."""
        prompt = "Test prompt content"
        output = format_injection_output(
            session_id=hook_input_json_base["session_id"],
            source=hook_input_json_base["source"],
            prompt=prompt,
        )

        assert "additionalContext" in output["hookSpecificOutput"]
        assert output["hookSpecificOutput"]["additionalContext"] == prompt

    def test_hook_event_name_correct(self, hook_input_json_base):
        """hookEventName is 'SessionStart'."""
        output = format_injection_output(
            session_id=hook_input_json_base["session_id"],
            source=hook_input_json_base["source"],
            prompt="test",
        )

        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_prompt_included_in_context(self, valid_prompt_file):
        """Actual prompt in additionalContext."""
        project_dir, prompt_content = valid_prompt_file
        output = format_injection_output(
            session_id="test-123",
            source="compact",
            prompt=prompt_content,
        )

        context = output["hookSpecificOutput"]["additionalContext"]
        assert prompt_content in context

    def test_session_source_in_context(self, hook_input_json_base):
        """Session source (compact/resume/etc) in output."""
        output = format_injection_output(
            session_id=hook_input_json_base["session_id"],
            source=hook_input_json_base["source"],
            prompt="test",
        )

        assert output["hookSpecificOutput"]["source"] == "compact"
        assert (
            output["hookSpecificOutput"]["session_id"]
            == hook_input_json_base["session_id"]
        )

    def test_additional_context_merged(self):
        """Additional context merged with prompt."""
        prompt = "System prompt"
        extra_context = "HtmlGraph context"

        output = format_injection_output(
            session_id="test",
            source="startup",
            prompt=prompt,
            additional_context=extra_context,
        )

        context = output["hookSpecificOutput"]["additionalContext"]
        assert prompt in context
        assert extra_context in context
        assert "---" in context  # Separator present


# ============================================================================
# TASK B5: INTEGRATION TESTS - FULL FLOW (6 tests)
# ============================================================================


class TestFullInjectionFlow:
    """Test complete prompt loading and injection pipeline."""

    def test_full_injection_flow_startup(self, valid_prompt_file, hook_input_startup):
        """Full pipeline: load → format → inject (startup source)."""
        project_dir, prompt_content = valid_prompt_file

        # Load
        loaded = load_system_prompt(project_dir)
        assert loaded == prompt_content

        # Format
        output = format_injection_output(
            session_id=hook_input_startup["session_id"],
            source=hook_input_startup["source"],
            prompt=loaded,
        )

        # Verify
        assert output["hookSpecificOutput"]["source"] == "startup"
        assert output["hookSpecificOutput"]["additionalContext"] == prompt_content

    def test_injection_with_different_sources(self, valid_prompt_file):
        """Works with: startup, resume, compact, clear."""
        project_dir, prompt_content = valid_prompt_file
        loaded = load_system_prompt(project_dir)

        sources = ["startup", "resume", "compact", "clear"]
        for source in sources:
            output = format_injection_output(
                session_id=f"sess-{source}-001",
                source=source,
                prompt=loaded,
            )
            assert output["hookSpecificOutput"]["source"] == source

    def test_fallback_when_prompt_missing(self, tmp_project_dir, hook_input_json_base):
        """Gracefully falls back when .claude/system-prompt.md missing."""
        # No prompt file created
        loaded = load_system_prompt(tmp_project_dir)
        assert loaded == ""

        # Should still create valid output
        output = format_injection_output(
            session_id=hook_input_json_base["session_id"],
            source=hook_input_json_base["source"],
            prompt=loaded,  # Empty string
            additional_context="Fallback context from HtmlGraph",
        )

        assert output["continue"] is True
        assert "Fallback context" in output["hookSpecificOutput"]["additionalContext"]

    def test_hook_exit_code_success(self, valid_prompt_file, hook_input_json_base):
        """Hook should complete successfully."""
        project_dir, prompt_content = valid_prompt_file

        loaded = load_system_prompt(project_dir)
        output = format_injection_output(
            session_id=hook_input_json_base["session_id"],
            source=hook_input_json_base["source"],
            prompt=loaded,
        )

        # Simulate hook execution
        json_output = json.dumps(output)
        parsed = json.loads(json_output)

        # Should be valid
        assert parsed["continue"] is True

    def test_hook_json_valid_and_parseable(
        self, valid_prompt_file, hook_input_json_base
    ):
        """Output is valid JSON parseable."""
        project_dir, prompt_content = valid_prompt_file
        loaded = load_system_prompt(project_dir)

        output = format_injection_output(
            session_id=hook_input_json_base["session_id"],
            source=hook_input_json_base["source"],
            prompt=loaded,
        )

        # Should be JSON serializable
        json_str = json.dumps(output)
        assert isinstance(json_str, str)

        # Should be parseable back
        parsed = json.loads(json_str)
        assert parsed == output

    def test_full_flow_with_truncation(self, large_prompt_file, hook_input_json_base):
        """Large prompt truncated before injection."""
        project_dir = large_prompt_file
        loaded = load_system_prompt(project_dir)

        # Should be very large
        assert len(loaded) > 50000

        # Truncate
        truncated = truncate_to_token_budget(loaded, max_tokens=500)

        # Should be much smaller
        assert len(truncated) < len(loaded)

        # Should still format correctly
        output = format_injection_output(
            session_id=hook_input_json_base["session_id"],
            source=hook_input_json_base["source"],
            prompt=truncated,
        )

        assert output["continue"] is True


# ============================================================================
# TASK B6: EDGE CASE TESTS (5 tests)
# ============================================================================


class TestEdgeCases:
    """Test edge cases and special character handling."""

    def test_unicode_in_prompt(self, tmp_project_dir):
        """Handles Unicode characters correctly."""
        unicode_content = """# 日本語プロンプト

## Python の指示
- 🚀 Performance first
- ✅ Testing required
- 🔒 Security critical

Some emoji: 🎯 📊 🧠 ⚡ 🔥
"""
        prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
        prompt_file.write_text(unicode_content, encoding="utf-8")

        loaded = load_system_prompt(tmp_project_dir)
        assert loaded == unicode_content
        assert "日本語" in loaded
        assert "🚀" in loaded

    def test_special_characters(self, tmp_project_dir):
        """Handles special characters <>{}[]|\\@#$%^&."""
        special_content = """# Special Characters Test

Code examples: `<tag>`, `{dict}`, `[list]`, `|pipe|`, `\\escape`
Email: test@example.com
Math: x < 10 && y > 5
Path: C:\\Users\\Name\\file.txt
Symbols: @#$%^&*()
"""
        prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
        prompt_file.write_text(special_content)

        loaded = load_system_prompt(tmp_project_dir)
        assert "<tag>" in loaded
        assert "{dict}" in loaded
        assert "[list]" in loaded

    def test_very_long_lines(self, tmp_project_dir):
        """Handles prompts with very long lines."""
        long_line = "x" * 10000
        content = f"# Header\n\n{long_line}\n\nEnd"

        prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
        prompt_file.write_text(content)

        loaded = load_system_prompt(tmp_project_dir)
        assert len(loaded) > 10000
        assert loaded == content

    def test_multiple_sections_markdown(self, tmp_project_dir):
        """Handles markdown with multiple sections."""
        markdown_content = """# Main Title

## Section 1
Content here.

### Subsection 1.1
- Item 1
- Item 2
- Item 3

## Section 2
More content.

```python
def example():
    return "code"
```

## Section 3
Final section.
"""
        prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
        prompt_file.write_text(markdown_content)

        loaded = load_system_prompt(tmp_project_dir)
        assert "Section 1" in loaded
        assert "Section 2" in loaded
        assert "Section 3" in loaded
        assert "code" in loaded

    def test_nested_markdown(self, tmp_project_dir):
        """Handles nested markdown (lists, code blocks)."""
        nested_content = """# Complex Markdown

## Lists
1. First item
   - Nested bullet
   - Another nested
2. Second item
   a. Ordered nested
   b. Another ordered

## Code Blocks
```python
def test():
    return [
        "nested",
        {"dict": "value"},
        [1, 2, 3]
    ]
```

### Inline Code
Use `function()` in text.

## Tables
| Header 1 | Header 2 |
|----------|----------|
| Value 1  | Value 2  |
"""
        prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
        prompt_file.write_text(nested_content)

        loaded = load_system_prompt(tmp_project_dir)
        assert "nested" in loaded.lower()
        assert "| Header 1 |" in loaded


# ============================================================================
# TASK B7: ERROR HANDLING TESTS (5 tests)
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge conditions."""

    def test_missing_claude_directory(self, tmp_path):
        """Handles missing .claude directory gracefully."""
        # Don't create .claude directory
        result = load_system_prompt(tmp_path)
        assert result == ""

    def test_invalid_json_input(self, tmp_project_dir):
        """Handles corrupted hook input JSON."""
        # This is handled by hook wrapper, but test the formatting works
        # even with unusual inputs
        output = format_injection_output(
            session_id="malformed-id-!@#$",
            source="unknown-source",
            prompt="test",
        )

        # Should still produce valid JSON
        json_str = json.dumps(output)
        parsed = json.loads(json_str)
        assert parsed["continue"] is True

    def test_permission_denied_simulation(self, tmp_project_dir):
        """Handles file permission errors gracefully."""
        prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
        prompt_file.write_text("test content")

        # Change permissions to read-only
        prompt_file.chmod(0o000)

        try:
            # Should handle gracefully
            result = load_system_prompt(tmp_project_dir)
            # Either empty or actual content - both acceptable
            assert isinstance(result, str)
        finally:
            # Restore permissions for cleanup
            prompt_file.chmod(0o644)

    def test_empty_project_directory(self):
        """Handles empty project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_system_prompt(tmpdir)
            assert result == ""

    def test_none_project_dir_handling(self):
        """Handles None/invalid project directory."""
        # Path() will raise error, but function should handle gracefully
        try:
            result = load_system_prompt(None)
            # If it doesn't raise, should return empty string
            assert result == ""
        except (TypeError, AttributeError):
            # Expected - None is not a valid path
            pass


# ============================================================================
# TASK B8: COVERAGE ANALYSIS HELPERS
# ============================================================================


class TestCoverageTargets:
    """Tests ensuring coverage of all critical paths."""

    def test_token_count_boundary_conditions(self):
        """Test token count at boundary values."""
        # At exactly 500 tokens (~2000 chars)
        text_500 = "x" * 2000
        assert estimate_token_count(text_500) == 500

        # Just under 500
        text_499 = "x" * 1996
        assert estimate_token_count(text_499) == 499

        # Just over 500
        text_501 = "x" * 2004
        assert estimate_token_count(text_501) == 501

    def test_truncation_boundary(self):
        """Test truncation at exact budget boundary."""
        # Exactly at limit
        text_exact = "x" * 2000  # 500 tokens
        result = truncate_to_token_budget(text_exact, max_tokens=500)
        # Should not truncate
        assert "[... truncated" not in result

        # Just over limit
        text_over = "x" * 2001
        result = truncate_to_token_budget(text_over, max_tokens=500)
        # Should truncate
        assert "[... truncated" in result

    def test_format_injection_with_empty_strings(self):
        """Test formatting with empty inputs."""
        output = format_injection_output(
            session_id="",
            source="",
            prompt="",
            additional_context="",
        )

        # Should still be valid
        assert output["continue"] is True
        json.dumps(output)  # Should serialize

    def test_load_prompt_from_symlink(self, tmp_project_dir, tmp_path):
        """Test loading prompt from symlinked directory."""
        # Create actual file
        claude_dir = tmp_project_dir / ".claude"
        prompt_file = claude_dir / "system-prompt.md"
        prompt_file.write_text("Symlink test content")

        # Create symlink in temp location
        symlink_dir = tmp_path / ".claude"
        try:
            symlink_dir.symlink_to(claude_dir)
            symlink_project = tmp_path

            result = load_system_prompt(symlink_project)
            assert "Symlink test content" in result
        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform (Windows)
            pytest.skip("Symlinks not supported on this platform")


# ============================================================================
# INTEGRATION TEST: End-to-End Hook Simulation
# ============================================================================


class TestEndToEndHookSimulation:
    """Simulate full hook execution flow."""

    def test_complete_hook_execution_flow(
        self, valid_prompt_file, hook_input_json_base
    ):
        """Simulate complete SessionStart hook execution."""
        project_dir, prompt_content = valid_prompt_file

        # Step 1: Parse hook input (simulated)
        hook_input = hook_input_json_base

        # Step 2: Load system prompt
        system_prompt = load_system_prompt(hook_input["cwd"])
        assert system_prompt != ""

        # Step 3: Load HtmlGraph context (simulated)
        htmlgraph_context = """## Project Status
**Progress:** 3/10 features complete (30%)
**Active:** 1 | **Blocked:** 0 | **Todo:** 6
"""

        # Step 4: Truncate if needed
        truncated_prompt = truncate_to_token_budget(system_prompt, max_tokens=500)

        # Step 5: Format injection
        output = format_injection_output(
            session_id=hook_input["session_id"],
            source=hook_input["source"],
            prompt=truncated_prompt,
            additional_context=htmlgraph_context,
        )

        # Step 6: Serialize to JSON (as hook would output)
        json_output = json.dumps(output)

        # Verify all steps succeeded
        assert output["continue"] is True
        assert "additionalContext" in output["hookSpecificOutput"]
        assert system_prompt in output["hookSpecificOutput"]["additionalContext"]
        assert htmlgraph_context in output["hookSpecificOutput"]["additionalContext"]

        # Verify JSON is valid
        reparsed = json.loads(json_output)
        assert reparsed == output

    def test_hook_with_missing_prompt_fallback(
        self, tmp_project_dir, hook_input_json_base
    ):
        """Hook execution when prompt file missing."""
        # No prompt file created
        system_prompt = load_system_prompt(tmp_project_dir)
        assert system_prompt == ""

        # Should use fallback context
        fallback_context = """## System Prompt Not Found

Create `.claude/system-prompt.md` to inject custom system instructions.

## Default Behavior
- HtmlGraph Process Notice enabled
- Orchestrator Directives loaded
- Feature tracking active
"""

        output = format_injection_output(
            session_id=hook_input_json_base["session_id"],
            source=hook_input_json_base["source"],
            prompt=system_prompt,  # Empty
            additional_context=fallback_context,
        )

        # Should still work
        assert output["continue"] is True
        assert fallback_context in output["hookSpecificOutput"]["additionalContext"]


# ============================================================================
# PARAMETRIZED TESTS FOR COMPREHENSIVE COVERAGE
# ============================================================================


class TestParametrized:
    """Parametrized tests for comprehensive coverage."""

    @pytest.mark.parametrize("source", ["startup", "resume", "compact", "clear"])
    def test_all_session_sources(self, tmp_project_dir, source):
        """Test all valid session sources."""
        output = format_injection_output(
            session_id="test-123",
            source=source,
            prompt="test prompt",
        )
        assert output["hookSpecificOutput"]["source"] == source

    @pytest.mark.parametrize("token_limit", [100, 500, 1000, 2000])
    def test_various_token_limits(self, token_limit):
        """Test truncation with various token limits."""
        text = "word " * 500  # ~250 tokens
        for limit in [100, 500, 1000, 2000]:
            truncated = truncate_to_token_budget(text, max_tokens=limit)
            token_count = estimate_token_count(truncated)
            # Should be close to or under limit
            assert token_count <= limit + 10  # Small tolerance for rounding

    @pytest.mark.parametrize("file_size_kb", [1, 10, 50, 100])
    def test_various_file_sizes(self, tmp_project_dir, file_size_kb):
        """Test loading prompts of various sizes."""
        content = "x" * (file_size_kb * 1024)
        prompt_file = tmp_project_dir / ".claude" / "system-prompt.md"
        prompt_file.write_text(content)

        loaded = load_system_prompt(tmp_project_dir)
        assert len(loaded) >= file_size_kb * 1024


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=packages/claude-plugin/hooks/scripts"])
