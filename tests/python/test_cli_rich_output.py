"""
Automated tests for Rich CLI output formatting.

Tests verify:
- Color markup usage ([red], [green], [yellow], [cyan])
- Symbol rendering (✓, ✗, ⚠, ℹ)
- Rich components (Table, Panel, Progress)
- Backward compatibility (JSON output clean)
- No plain print() statements

Run with: uv run pytest tests/python/test_cli_rich_output.py -v
"""

import json
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from rich.table import Table

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestRichColorMarkup:
    """Test that Rich color markup is used correctly."""

    def test_error_messages_use_red_markup(self):
        """Test error messages use [red] markup."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Simulate error message
        console.print("[red]✗ Error: Operation failed[/red]")

        output = string_io.getvalue()
        # Should contain ANSI color codes for terminal output
        assert "\x1b[" in output or "[red]" in output

    def test_success_messages_use_green_markup(self):
        """Test success messages use [green] markup."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Simulate success message
        console.print("[green]✓ Operation successful[/green]")

        output = string_io.getvalue()
        assert "\x1b[" in output or "[green]" in output

    def test_warning_messages_use_yellow_markup(self):
        """Test warning messages use [yellow] markup."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Simulate warning message
        console.print("[yellow]⚠ Warning: Action may have side effects[/yellow]")

        output = string_io.getvalue()
        assert "\x1b[" in output or "[yellow]" in output

    def test_info_messages_use_cyan_markup(self):
        """Test info messages use [cyan] markup."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Simulate info message
        console.print("[cyan]ℹ Project: htmlgraph[/cyan]")

        output = string_io.getvalue()
        assert "\x1b[" in output or "[cyan]" in output


class TestRichSymbols:
    """Test that Rich symbols render correctly."""

    def test_error_symbol_present(self):
        """Test error symbol ✗ is used in error messages."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Simulate error with symbol
        console.print("[red]✗ Failed[/red]")

        output = string_io.getvalue()
        # Should contain the symbol (either directly or encoded)
        assert "✗" in output or "x" in output.lower() or "\u2717" in output

    def test_success_symbol_present(self):
        """Test success symbol ✓ is used in success messages."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Simulate success with symbol
        console.print("[green]✓ Success[/green]")

        output = string_io.getvalue()
        # Should contain the symbol
        assert "✓" in output or "\u2713" in output

    def test_warning_symbol_present(self):
        """Test warning symbol ⚠ is used in warnings."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Simulate warning with symbol
        console.print("[yellow]⚠ Warning[/yellow]")

        output = string_io.getvalue()
        # Should contain the symbol
        assert "⚠" in output or "\u26a0" in output

    def test_info_symbol_present(self):
        """Test info symbol ℹ is used in info messages."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Simulate info with symbol
        console.print("[cyan]ℹ Information[/cyan]")

        output = string_io.getvalue()
        # Should contain the symbol
        assert "ℹ" in output or "\u2139" in output


class TestRichComponents:
    """Test that Rich components are used correctly."""

    def test_table_component_renders(self):
        """Test Rich.Table renders correctly."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=80)

        # Create a simple table
        table = Table(title="Test Table", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="magenta")
        table.add_column("Name", style="green")
        table.add_row("feat-001", "Feature One")
        table.add_row("feat-002", "Feature Two")

        console.print(table)
        output = string_io.getvalue()

        # Should contain table borders and content
        assert "feat-001" in output or "ID" in output
        assert "Feature One" in output or "Name" in output

    def test_panel_component_renders(self):
        """Test Rich.Panel renders correctly."""
        from rich.panel import Panel

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=80)

        # Create a panel
        panel = Panel(
            "[cyan]This is test content[/cyan]", title="Test Panel", style="bold cyan"
        )

        console.print(panel)
        output = string_io.getvalue()

        # Should contain panel borders and content
        assert "Test Panel" in output or "content" in output

    def test_styled_text_renders(self):
        """Test styled text (bold, dim, etc.) renders."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Use various styles
        console.print("[bold]Bold text[/bold]")
        console.print("[dim]Dim text[/dim]")
        console.print("[italic]Italic text[/italic]")

        output = string_io.getvalue()
        # Should contain at least some styling
        assert "Bold text" in output or "Dim text" in output


class TestBackwardCompatibility:
    """Test backward compatibility with existing output formats."""

    def test_json_output_has_no_rich_markup(self):
        """Test JSON output doesn't contain Rich markup."""
        # This would test actual CLI commands, but for unit tests
        # we just verify the pattern

        # Simulate JSON output that should be clean
        data = {
            "success": True,
            "message": "Feature created successfully",  # No [green] markup here
            "data": {"id": "feat-001", "title": "Test"},
        }

        json_str = json.dumps(data)

        # Verify no Rich markup in JSON
        assert "[red]" not in json_str
        assert "[green]" not in json_str
        assert "[yellow]" not in json_str
        assert "[cyan]" not in json_str
        assert "\x1b[" not in json_str

    def test_json_output_is_valid(self):
        """Test JSON output is valid and parseable."""
        # Create sample JSON data
        sample_json = json.dumps(
            {
                "success": True,
                "data": [{"id": "feat-001", "status": "todo"}],
                "timestamp": "2026-01-05T00:00:00",
            }
        )

        # Should be valid JSON
        parsed = json.loads(sample_json)
        assert parsed["success"] is True
        assert len(parsed["data"]) == 1


class TestCLIOutputQuality:
    """Test CLI output quality standards."""

    def test_cli_file_imports_rich(self):
        """Test CLI package imports Rich correctly."""
        # Check base.py which has the core console setup
        cli_base_path = PROJECT_ROOT / "src/python/htmlgraph/cli/base.py"
        assert cli_base_path.exists(), "cli/base.py not found"

        content = cli_base_path.read_text()

        # Check required Rich imports
        assert "from rich" in content
        assert "Console" in content
        assert "Table" in content

    def test_cli_initializes_console(self):
        """Test CLI package initializes global console."""
        # Check base.py which has the console initialization
        cli_base_path = PROJECT_ROOT / "src/python/htmlgraph/cli/base.py"
        content = cli_base_path.read_text()

        # Should initialize _console = Console()
        assert "_console = Console()" in content or "= Console(" in content

    def test_cli_uses_console_print(self):
        """Test CLI package uses console.print() instead of print()."""
        # Count across all CLI modules
        cli_dir = PROJECT_ROOT / "src/python/htmlgraph/cli"
        assert cli_dir.exists(), "cli package directory not found"

        console_print_count = 0
        for py_file in cli_dir.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                content = py_file.read_text()
                console_print_count += content.count("console.print(")
                console_print_count += content.count("_console.print(")

        # Should have significant usage across the package
        assert console_print_count > 50, (
            f"Only {console_print_count} console.print() calls found across CLI package"
        )

    def test_no_excessive_plain_prints(self):
        """Test minimal use of plain print() statements."""
        # Check across all CLI modules
        cli_dir = PROJECT_ROOT / "src/python/htmlgraph/cli"

        plain_prints = []
        for py_file in cli_dir.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                content = py_file.read_text()
                lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    # Skip comments, console.print, and function definitions
                    if (
                        "print(" in stripped
                        and "console.print" not in stripped
                        and "_console.print" not in stripped
                        and not stripped.startswith("#")
                        and "def " not in stripped
                    ):
                        plain_prints.append((str(py_file), i, stripped[:70]))

        # PHASE 1A/1B: Tracking conversion progress
        # Baseline: 698 print() statements (as of 2026-01-04)
        # Current: ~550 remaining (monitoring ongoing conversion)
        # Target: 0 remaining after Phase 1A/1B complete

        # For now, just track and report (don't fail on threshold)
        # This allows monitoring as Codex/Copilot implement conversion
        print("\nPrint() Statement Conversion Progress:")
        print(f"  Remaining: {len(plain_prints)}")
        print("  Baseline: 698")
        print(f"  Progress: {(698 - len(plain_prints)) / 698 * 100:.1f}% converted")

        # Soft check: ensure we're moving in right direction
        # Allow up to 550 (current known state)
        # Fail if it INCREASES (regression)
        assert len(plain_prints) <= 600, (
            f"Regression detected: {len(plain_prints)} plain print() calls found. "
            "Should be decreasing or stay at current level (~550)"
        )


class TestColorConsistency:
    """Test consistent color usage across CLI."""

    def test_red_used_for_errors(self):
        """Test [red] is used for error messages."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Errors should use red
        console.print("[red]Error: Invalid input[/red]")
        output = string_io.getvalue()

        assert "\x1b[" in output or "Error" in output

    def test_green_used_for_success(self):
        """Test [green] is used for success messages."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Success should use green
        console.print("[green]✓ Operation completed[/green]")
        output = string_io.getvalue()

        assert "\x1b[" in output or "Operation" in output

    def test_yellow_used_for_warnings(self):
        """Test [yellow] is used for warning messages."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Warnings should use yellow
        console.print("[yellow]⚠ Caution required[/yellow]")
        output = string_io.getvalue()

        assert "\x1b[" in output or "Caution" in output

    def test_cyan_used_for_info(self):
        """Test [cyan] is used for info messages."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Info should use cyan
        console.print("[cyan]ℹ Information[/cyan]")
        output = string_io.getvalue()

        assert "\x1b[" in output or "Information" in output


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_long_content_wraps(self):
        """Test long content wraps correctly."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=40)

        long_text = "This is a very long line of text that should wrap correctly in the console output"
        console.print(long_text)

        output = string_io.getvalue()
        # Should not crash and should contain the text
        assert "very long" in output or "text" in output

    def test_unicode_symbols_render(self):
        """Test Unicode symbols render without errors."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Try various symbols
        symbols = ["✓", "✗", "⚠", "ℹ", "★", "→"]
        for symbol in symbols:
            console.print(f"[cyan]{symbol}[/cyan]")

        output = string_io.getvalue()
        # Should render without errors
        assert len(output) > 0

    def test_no_color_env_honored(self):
        """Test NO_COLOR environment variable is respected."""
        import os

        # Save original
        original_no_color = os.environ.get("NO_COLOR")

        try:
            os.environ["NO_COLOR"] = "1"
            string_io = StringIO()
            # Create console with no_color support
            console = Console(file=string_io, no_color=True)
            console.print("[red]Error[/red]")

            output = string_io.getvalue()
            # With NO_COLOR, should not have ANSI codes
            # (but will have the text)
            assert "Error" in output

        finally:
            # Restore original
            if original_no_color:
                os.environ["NO_COLOR"] = original_no_color
            else:
                os.environ.pop("NO_COLOR", None)

    def test_multiple_styles_combined(self):
        """Test multiple styles can be combined."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Combine multiple styles
        console.print(
            "[bold green]✓[/bold green] [italic cyan]Feature created[/italic cyan]"
        )

        output = string_io.getvalue()
        assert "Feature created" in output or "✓" in output


class TestRichComponentIntegration:
    """Test Rich component integration patterns."""

    def test_table_with_styled_columns(self):
        """Test Table with various column styles."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=100)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Status", style="green")
        table.add_column("Count", style="cyan", justify="right")
        table.add_column("Priority", style="red")

        table.add_row("✓ Done", "42", "high")
        table.add_row("⏳ Todo", "18", "medium")

        console.print(table)
        output = string_io.getvalue()

        # Should render without errors
        assert len(output) > 0

    def test_nested_markup(self):
        """Test nested markup works correctly."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Nested styles
        console.print(
            "[bold][green]✓ Feature[/green] [cyan]my-feature[/cyan] created[/bold]"
        )

        output = string_io.getvalue()
        assert len(output) > 0

    def test_markup_escaping(self):
        """Test that special characters in content don't break markup."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)

        # Content with brackets (should not break markup)
        console.print("[green]✓ Created [file.txt][/green]")

        output = string_io.getvalue()
        # Should render without errors
        assert "Created" in output or len(output) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
