"""
Unit tests for CIGS CostReporter.

Tests cover:
- HTML generation (valid structure and all components)
- Dashboard initialization (empty and populated)
- Summary metrics calculation
- Cost breakdown by violation type and tool
- File I/O operations
- Chart data generation
- Insight generation
- Responsive design validation
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from htmlgraph.cigs.models import (
    SessionViolationSummary,
    ViolationRecord,
    ViolationType,
)
from htmlgraph.cigs.reporter import CostReporter


class TestCostReporterInitialization:
    """Tests for CostReporter initialization."""

    def test_reporter_initialization(self) -> None:
        """Test reporter creates without errors."""
        reporter = CostReporter()
        assert reporter is not None
        assert reporter.generated_at is not None

    def test_theme_configuration(self) -> None:
        """Test theme has all required colors."""
        reporter = CostReporter()
        theme = reporter.THEME

        required_keys = [
            "bg_primary",
            "bg_secondary",
            "text_primary",
            "text_secondary",
            "accent_primary",
            "accent_secondary",
            "success",
            "warning",
            "error",
        ]

        for key in required_keys:
            assert key in theme
            assert isinstance(theme[key], str)
            assert theme[key].startswith("#")


class TestDashboardGeneration:
    """Tests for dashboard HTML generation."""

    def setup_method(self) -> None:
        """Initialize reporter for each test."""
        self.reporter = CostReporter()

    def test_generate_empty_dashboard(self) -> None:
        """Test generating dashboard with no violations."""
        html = self.reporter.generate_dashboard()

        assert isinstance(html, str)
        assert len(html) > 0
        assert "<!DOCTYPE html>" in html
        assert "Cost Attribution Dashboard" in html

    def test_dashboard_has_all_sections(self) -> None:
        """Test dashboard contains all major sections."""
        html = self.reporter.generate_dashboard()

        # Check for all major sections
        assert "<head>" in html
        assert "<body>" in html
        assert 'class="header"' in html
        assert 'class="cards"' in html
        assert 'class="charts"' in html
        assert 'class="table-section"' in html
        assert 'class="insights"' in html
        assert 'class="footer"' in html

    def test_dashboard_is_valid_html(self) -> None:
        """Test generated HTML is structurally valid."""
        html = self.reporter.generate_dashboard()

        # Check HTML structure
        assert html.count("<html") == 1
        assert html.count("</html>") == 1
        assert html.count("<head>") == 1
        assert html.count("</head>") == 1
        assert html.count("<body>") == 1
        assert html.count("</body>") == 1

        # Check DOCTYPE and basic structure
        assert "<!DOCTYPE html>" in html
        assert "<meta charset" in html
        assert "</style>" in html

    def test_dashboard_includes_chart_js(self) -> None:
        """Test dashboard includes Chart.js library."""
        html = self.reporter.generate_dashboard()
        assert "chart.js" in html.lower() or "chartjs" in html.lower()
        assert "Chart(" in html or "new Chart" in html

    def test_dashboard_with_violations(self) -> None:
        """Test dashboard generation with violation data."""
        violations = self._create_test_violations()
        summary = SessionViolationSummary(
            session_id="test-session-001",
            total_violations=len(violations),
            violations_by_type={
                ViolationType.DIRECT_EXPLORATION: 2,
                ViolationType.DIRECT_IMPLEMENTATION: 1,
            },
            total_waste_tokens=15000,
            circuit_breaker_triggered=False,
            compliance_rate=0.75,
            violations=violations,
        )

        html = self.reporter.generate_dashboard(summary)

        assert "test-session-001" in html
        assert "15000" in html or "15,000" in html
        assert "75%" in html
        assert "3" in html  # Total violations

    def _create_test_violations(self) -> list[ViolationRecord]:
        """Create sample violation records for testing."""
        base_time = datetime.now()
        violations = []

        # Direct exploration violation
        violations.append(
            ViolationRecord(
                id="viol-001",
                session_id="test-session-001",
                timestamp=base_time,
                tool="Read",
                tool_params={"file_path": "/test/file.py"},
                violation_type=ViolationType.DIRECT_EXPLORATION,
                context_before="Exploring codebase",
                should_have_delegated_to="spawn_gemini()",
                actual_cost_tokens=5000,
                optimal_cost_tokens=500,
                waste_tokens=4500,
                warning_level=1,
                was_warned=False,
            )
        )

        # Direct exploration (second)
        violations.append(
            ViolationRecord(
                id="viol-002",
                session_id="test-session-001",
                timestamp=base_time + timedelta(minutes=5),
                tool="Grep",
                tool_params={"pattern": "def test"},
                violation_type=ViolationType.DIRECT_EXPLORATION,
                context_before="Searching for test functions",
                should_have_delegated_to="spawn_gemini()",
                actual_cost_tokens=3000,
                optimal_cost_tokens=500,
                waste_tokens=2500,
                warning_level=1,
                was_warned=False,
            )
        )

        # Direct implementation violation
        violations.append(
            ViolationRecord(
                id="viol-003",
                session_id="test-session-001",
                timestamp=base_time + timedelta(minutes=10),
                tool="Edit",
                tool_params={"file_path": "/test/implementation.py"},
                violation_type=ViolationType.DIRECT_IMPLEMENTATION,
                context_before="Adding new feature",
                should_have_delegated_to="spawn_codex()",
                actual_cost_tokens=7000,
                optimal_cost_tokens=800,
                waste_tokens=6200,
                warning_level=2,
                was_warned=True,
                warning_ignored=True,
            )
        )

        return violations


class TestSummaryMetrics:
    """Tests for summary metrics calculation."""

    def test_generate_summary_metrics_empty(self) -> None:
        """Test metrics for empty violation summary."""
        reporter = CostReporter()
        summary = SessionViolationSummary(
            session_id="empty",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=1.0,
        )

        metrics = reporter.generate_summary_metrics(summary)

        assert metrics["total_violations"] == 0
        assert metrics["total_waste_tokens"] == 0
        assert metrics["avg_waste_per_violation"] == 0
        assert metrics["compliance_rate"] == 1.0
        assert metrics["circuit_breaker_triggered"] is False
        assert metrics["savings_potential"] == 0

    def test_generate_summary_metrics_with_violations(self) -> None:
        """Test metrics calculation with violation data."""
        reporter = CostReporter()
        summary = SessionViolationSummary(
            session_id="test",
            total_violations=3,
            violations_by_type={
                ViolationType.DIRECT_EXPLORATION: 2,
                ViolationType.DIRECT_IMPLEMENTATION: 1,
            },
            total_waste_tokens=12000,
            circuit_breaker_triggered=True,
            compliance_rate=0.6,
        )

        metrics = reporter.generate_summary_metrics(summary)

        assert metrics["total_violations"] == 3
        assert metrics["total_waste_tokens"] == 12000
        assert metrics["avg_waste_per_violation"] == 4000
        assert metrics["compliance_rate"] == 0.6
        assert metrics["circuit_breaker_triggered"] is True
        assert metrics["savings_potential"] > 0
        assert metrics["savings_percentage"] > 0

    def test_summary_metrics_structure(self) -> None:
        """Test metrics dictionary has all required keys."""
        reporter = CostReporter()
        summary = SessionViolationSummary(
            session_id="test",
            total_violations=1,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 1},
            total_waste_tokens=5000,
            circuit_breaker_triggered=False,
            compliance_rate=0.9,
        )

        metrics = reporter.generate_summary_metrics(summary)

        required_keys = [
            "total_violations",
            "total_waste_tokens",
            "avg_waste_per_violation",
            "compliance_rate",
            "circuit_breaker_triggered",
            "direct_cost_estimate",
            "delegated_cost_estimate",
            "savings_potential",
            "savings_percentage",
        ]

        for key in required_keys:
            assert key in metrics, f"Missing key: {key}"


class TestCostBreakdown:
    """Tests for cost breakdown calculations."""

    def setup_method(self) -> None:
        """Initialize reporter and test data."""
        self.reporter = CostReporter()

        # Create test violations
        self.violations = [
            ViolationRecord(
                id="viol-001",
                session_id="test",
                timestamp=datetime.now(),
                tool="Read",
                tool_params={},
                violation_type=ViolationType.DIRECT_EXPLORATION,
                waste_tokens=5000,
            ),
            ViolationRecord(
                id="viol-002",
                session_id="test",
                timestamp=datetime.now(),
                tool="Grep",
                tool_params={},
                violation_type=ViolationType.DIRECT_EXPLORATION,
                waste_tokens=3000,
            ),
            ViolationRecord(
                id="viol-003",
                session_id="test",
                timestamp=datetime.now(),
                tool="Edit",
                tool_params={},
                violation_type=ViolationType.DIRECT_IMPLEMENTATION,
                waste_tokens=7000,
            ),
        ]

        self.summary = SessionViolationSummary(
            session_id="test",
            total_violations=3,
            violations_by_type={
                ViolationType.DIRECT_EXPLORATION: 2,
                ViolationType.DIRECT_IMPLEMENTATION: 1,
            },
            total_waste_tokens=15000,
            circuit_breaker_triggered=False,
            compliance_rate=0.7,
            violations=self.violations,
        )

    def test_cost_breakdown_by_type(self) -> None:
        """Test cost breakdown by violation type."""
        breakdown = self.reporter.generate_cost_breakdown_by_type(self.summary)

        assert len(breakdown) == 2
        assert breakdown[str(ViolationType.DIRECT_EXPLORATION)] == 8000
        assert breakdown[str(ViolationType.DIRECT_IMPLEMENTATION)] == 7000

    def test_cost_breakdown_by_tool(self) -> None:
        """Test cost breakdown by tool."""
        breakdown = self.reporter.generate_cost_breakdown_by_tool(self.summary)

        assert len(breakdown) == 3
        assert breakdown["Read"] == 5000
        assert breakdown["Grep"] == 3000
        assert breakdown["Edit"] == 7000

    def test_cost_breakdown_empty(self) -> None:
        """Test cost breakdown with empty violations."""
        summary = SessionViolationSummary(
            session_id="empty",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=1.0,
        )

        breakdown_type = self.reporter.generate_cost_breakdown_by_type(summary)
        breakdown_tool = self.reporter.generate_cost_breakdown_by_tool(summary)

        assert len(breakdown_type) == 0
        assert len(breakdown_tool) == 0


class TestFileIO:
    """Tests for file I/O operations."""

    def setup_method(self) -> None:
        """Initialize reporter."""
        self.reporter = CostReporter()

    def test_save_dashboard_creates_file(self) -> None:
        """Test saving dashboard creates file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dashboard.html"
            html = self.reporter.generate_dashboard()

            self.reporter.save_dashboard(html, path)

            assert path.exists()
            assert path.is_file()

    def test_save_dashboard_creates_parent_directory(self) -> None:
        """Test saving dashboard creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir1" / "subdir2" / "dashboard.html"

            html = self.reporter.generate_dashboard()
            self.reporter.save_dashboard(html, path)

            assert path.exists()
            assert path.parent.exists()

    def test_save_and_load_dashboard(self) -> None:
        """Test saving and loading dashboard content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dashboard.html"
            html = self.reporter.generate_dashboard()

            self.reporter.save_dashboard(html, path)

            # Load and verify
            loaded_html = path.read_text(encoding="utf-8")
            assert loaded_html == html
            assert "Cost Attribution Dashboard" in loaded_html

    def test_save_dashboard_with_violation_data(self) -> None:
        """Test saving dashboard with violation data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dashboard.html"

            violations = [
                ViolationRecord(
                    id="viol-001",
                    session_id="test-session",
                    timestamp=datetime.now(),
                    tool="Read",
                    tool_params={},
                    violation_type=ViolationType.DIRECT_EXPLORATION,
                    waste_tokens=5000,
                )
            ]

            summary = SessionViolationSummary(
                session_id="test-session",
                total_violations=1,
                violations_by_type={ViolationType.DIRECT_EXPLORATION: 1},
                total_waste_tokens=5000,
                circuit_breaker_triggered=False,
                compliance_rate=0.9,
                violations=violations,
            )

            html = self.reporter.generate_dashboard(summary)
            self.reporter.save_dashboard(html, path)

            loaded_html = path.read_text(encoding="utf-8")
            assert "test-session" in loaded_html
            assert "5000" in loaded_html or "5,000" in loaded_html


class TestChartDataGeneration:
    """Tests for chart data generation."""

    def test_charts_in_html(self) -> None:
        """Test charts are included in HTML."""
        reporter = CostReporter()
        html = reporter.generate_dashboard()

        assert "chartByType" in html
        assert "chartByTool" in html
        assert "chartConfig" in html or "type_labels" in html

    def test_chart_data_json_format(self) -> None:
        """Test chart data is properly formatted as JSON."""
        reporter = CostReporter()

        violations = [
            ViolationRecord(
                id="v1",
                session_id="test",
                timestamp=datetime.now(),
                tool="Read",
                tool_params={},
                violation_type=ViolationType.DIRECT_EXPLORATION,
                waste_tokens=5000,
            ),
        ]

        summary = SessionViolationSummary(
            session_id="test",
            total_violations=1,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 1},
            total_waste_tokens=5000,
            circuit_breaker_triggered=False,
            compliance_rate=0.9,
            violations=violations,
        )

        html = reporter.generate_dashboard(summary)

        # Check for JSON arrays in the HTML
        assert "[" in html and "]" in html
        assert "Read" in html or "Direct Exploration" in html


class TestResponsiveDesign:
    """Tests for responsive design elements."""

    def test_viewport_meta_tag(self) -> None:
        """Test viewport meta tag for mobile responsiveness."""
        reporter = CostReporter()
        html = reporter.generate_dashboard()

        assert 'name="viewport"' in html
        assert "initial-scale=1.0" in html

    def test_media_queries_in_css(self) -> None:
        """Test media queries for responsive design."""
        reporter = CostReporter()
        html = reporter.generate_dashboard()

        assert "@media" in html
        assert "768px" in html or "mobile" in html.lower()

    def test_responsive_grid_layout(self) -> None:
        """Test responsive grid classes in HTML."""
        reporter = CostReporter()
        html = reporter.generate_dashboard()

        assert "grid" in html.lower()
        assert "minmax" in html or "auto-fit" in html


class TestInsightGeneration:
    """Tests for insight generation."""

    def test_insights_for_high_compliance(self) -> None:
        """Test insights when compliance is high."""
        reporter = CostReporter()

        summary = SessionViolationSummary(
            session_id="test",
            total_violations=1,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 1},
            total_waste_tokens=3000,
            circuit_breaker_triggered=False,
            compliance_rate=0.95,
        )

        html = reporter.generate_dashboard(summary)

        assert "Excellent" in html or "excellent" in html.lower()

    def test_insights_for_low_compliance(self) -> None:
        """Test insights when compliance is low."""
        reporter = CostReporter()

        summary = SessionViolationSummary(
            session_id="test",
            total_violations=5,
            violations_by_type={
                ViolationType.DIRECT_EXPLORATION: 3,
                ViolationType.DIRECT_IMPLEMENTATION: 2,
            },
            total_waste_tokens=20000,
            circuit_breaker_triggered=True,
            compliance_rate=0.3,
        )

        html = reporter.generate_dashboard(summary)

        assert "Circuit Breaker" in html

    def test_insights_include_savings_potential(self) -> None:
        """Test insights mention savings potential."""
        reporter = CostReporter()

        summary = SessionViolationSummary(
            session_id="test",
            total_violations=3,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 3},
            total_waste_tokens=9000,
            circuit_breaker_triggered=False,
            compliance_rate=0.7,
        )

        html = reporter.generate_dashboard(summary)

        assert "Saving" in html or "saving" in html.lower()


class TestDashboardStyling:
    """Tests for CSS styling and theming."""

    def test_theme_colors_applied(self) -> None:
        """Test theme colors are applied in CSS."""
        reporter = CostReporter()
        html = reporter.generate_dashboard()

        # Check theme colors are present
        assert reporter.THEME["bg_primary"] in html
        assert reporter.THEME["accent_secondary"] in html

    def test_dark_theme_colors(self) -> None:
        """Test dark theme color scheme."""
        reporter = CostReporter()

        # Check dark theme colors
        assert reporter.THEME["bg_primary"] == "#1a1a2e"
        assert reporter.THEME["bg_secondary"] == "#16213e"
        assert reporter.THEME["text_primary"] == "#e0e0e0"

    def test_css_includes_hover_effects(self) -> None:
        """Test CSS includes hover effects."""
        reporter = CostReporter()
        html = reporter.generate_dashboard()

        assert ":hover" in html

    def test_css_includes_transitions(self) -> None:
        """Test CSS includes smooth transitions."""
        reporter = CostReporter()
        html = reporter.generate_dashboard()

        assert "transition" in html or "transform" in html
