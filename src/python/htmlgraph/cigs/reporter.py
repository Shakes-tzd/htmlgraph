"""
CostReporter for CIGS Dashboard Generation

Generates interactive HTML dashboards showing cost analysis, violation tracking,
and savings potential from proper delegation.

Features:
- Professional HTML5 dashboard with responsive design
- Cost visualization using Chart.js
- Violation metrics and compliance statistics
- Recommendations for cost optimization
- Dark theme matching HtmlGraph visual style

Usage:
    from htmlgraph.cigs.reporter import CostReporter
    from htmlgraph.cigs.tracker import ViolationTracker

    tracker = ViolationTracker()
    reporter = CostReporter()
    html = reporter.generate_dashboard(tracker)
    reporter.save_dashboard(html, "dashboard.html")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.cigs.models import SessionViolationSummary


class CostReporter:
    """
    Generate interactive HTML dashboards from cost analysis data.

    Transforms ViolationTracker and cost data into professional HTML
    visualizations with charts, tables, and recommendations.
    """

    # Design theme
    THEME = {
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#16213e",
        "text_primary": "#e0e0e0",
        "text_secondary": "#b0b0b0",
        "accent_primary": "#0f3460",
        "accent_secondary": "#e94560",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#f44336",
    }

    def __init__(self) -> None:
        """Initialize CostReporter."""
        self.generated_at = datetime.now()

    def generate_dashboard(
        self, violation_summary: SessionViolationSummary | None = None
    ) -> str:
        """
        Generate complete interactive HTML dashboard.

        Args:
            violation_summary: SessionViolationSummary with violation data

        Returns:
            Complete HTML document as string
        """
        if violation_summary is None:
            violation_summary = self._create_empty_summary()

        # Build dashboard components
        html_parts = [
            self._html_header(),
            self._html_styles(),
            self._html_body_open(),
            self._html_header_section(violation_summary),
            self._html_summary_cards(violation_summary),
            self._html_charts_section(violation_summary),
            self._html_violations_table(violation_summary),
            self._html_insights_section(violation_summary),
            self._html_footer_section(),
            self._html_body_close(),
            self._html_scripts(),
        ]

        return "\n".join(html_parts)

    def save_dashboard(self, html: str, path: str | Path) -> None:
        """
        Save HTML dashboard to file.

        Args:
            html: HTML content to save
            path: File path to save to

        Raises:
            IOError: If file cannot be written
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    def generate_summary_metrics(
        self, violation_summary: SessionViolationSummary
    ) -> dict[str, Any]:
        """
        Extract aggregated metrics from violation summary.

        Args:
            violation_summary: Session violation data

        Returns:
            Dictionary with summary metrics
        """
        total_violations = violation_summary.total_violations
        total_waste = violation_summary.total_waste_tokens
        compliance_rate = violation_summary.compliance_rate

        # Calculate metrics
        avg_waste_per_violation = (
            int(total_waste / total_violations) if total_violations > 0 else 0
        )

        # Estimate direct vs delegated costs
        direct_cost_estimate = total_waste
        delegated_cost_estimate = int(direct_cost_estimate * 0.3)  # ~70% savings
        savings_potential = max(0, direct_cost_estimate - delegated_cost_estimate)

        return {
            "total_violations": total_violations,
            "total_waste_tokens": total_waste,
            "avg_waste_per_violation": avg_waste_per_violation,
            "compliance_rate": compliance_rate,
            "circuit_breaker_triggered": violation_summary.circuit_breaker_triggered,
            "direct_cost_estimate": direct_cost_estimate,
            "delegated_cost_estimate": delegated_cost_estimate,
            "savings_potential": savings_potential,
            "savings_percentage": (
                (savings_potential / direct_cost_estimate * 100)
                if direct_cost_estimate > 0
                else 0
            ),
        }

    def generate_cost_breakdown_by_type(
        self, violation_summary: SessionViolationSummary
    ) -> dict[str, int]:
        """
        Generate cost breakdown by violation type.

        Args:
            violation_summary: Session violation data

        Returns:
            Dictionary mapping violation types to waste tokens
        """
        breakdown: dict[str, int] = {}

        for violation in violation_summary.violations:
            vtype = str(violation.violation_type)
            breakdown[vtype] = breakdown.get(vtype, 0) + violation.waste_tokens

        return breakdown

    def generate_cost_breakdown_by_tool(
        self, violation_summary: SessionViolationSummary
    ) -> dict[str, int]:
        """
        Generate cost breakdown by tool used.

        Args:
            violation_summary: Session violation data

        Returns:
            Dictionary mapping tool names to waste tokens
        """
        breakdown: dict[str, int] = {}

        for violation in violation_summary.violations:
            tool = violation.tool
            breakdown[tool] = breakdown.get(tool, 0) + violation.waste_tokens

        return breakdown

    # ===== HTML Generation Methods =====

    def _html_header(self) -> str:
        """Generate HTML document header."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cost Attribution Dashboard - HtmlGraph</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
</head>"""

    def _html_styles(self) -> str:
        """Generate CSS styles."""
        return f"""<style>
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background-color: {self.THEME["bg_primary"]};
    color: {self.THEME["text_primary"]};
    line-height: 1.6;
}}

a {{
    color: {self.THEME["accent_secondary"]};
    text-decoration: none;
}}

a:hover {{
    text-decoration: underline;
}}

/* Layout */
.container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}}

/* Header */
.header {{
    border-bottom: 2px solid {self.THEME["accent_primary"]};
    padding-bottom: 20px;
    margin-bottom: 30px;
}}

.header h1 {{
    font-size: 2.5em;
    margin-bottom: 10px;
    color: {self.THEME["text_primary"]};
}}

.header .subtitle {{
    color: {self.THEME["text_secondary"]};
    font-size: 0.95em;
}}

.header-meta {{
    margin-top: 15px;
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    font-size: 0.9em;
    color: {self.THEME["text_secondary"]};
}}

/* Summary Cards */
.cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 40px;
}}

.card {{
    background-color: {self.THEME["bg_secondary"]};
    border: 1px solid {self.THEME["accent_primary"]};
    border-radius: 8px;
    padding: 25px;
    transition: all 0.3s ease;
}}

.card:hover {{
    border-color: {self.THEME["accent_secondary"]};
    transform: translateY(-5px);
    box-shadow: 0 10px 30px rgba(233, 69, 96, 0.2);
}}

.card-label {{
    color: {self.THEME["text_secondary"]};
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 10px;
}}

.card-value {{
    font-size: 2.5em;
    font-weight: bold;
    margin-bottom: 8px;
    color: {self.THEME["text_primary"]};
}}

.card-unit {{
    color: {self.THEME["text_secondary"]};
    font-size: 0.9em;
    font-weight: normal;
}}

.card-meta {{
    color: {self.THEME["text_secondary"]};
    font-size: 0.85em;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid {self.THEME["accent_primary"]};
}}

/* Status indicators */
.status-good {{
    color: {self.THEME["success"]};
}}

.status-warning {{
    color: {self.THEME["warning"]};
}}

.status-error {{
    color: {self.THEME["error"]};
}}

/* Charts */
.charts {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 30px;
    margin-bottom: 40px;
}}

.chart-container {{
    background-color: {self.THEME["bg_secondary"]};
    border: 1px solid {self.THEME["accent_primary"]};
    border-radius: 8px;
    padding: 20px;
}}

.chart-title {{
    font-size: 1.3em;
    font-weight: 600;
    margin-bottom: 20px;
    color: {self.THEME["text_primary"]};
}}

.chart-canvas {{
    max-height: 400px;
}}

/* Table */
.table-section {{
    margin-bottom: 40px;
}}

.table-section h2 {{
    font-size: 1.5em;
    margin-bottom: 20px;
    color: {self.THEME["text_primary"]};
}}

.table-wrapper {{
    overflow-x: auto;
    background-color: {self.THEME["bg_secondary"]};
    border: 1px solid {self.THEME["accent_primary"]};
    border-radius: 8px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th {{
    background-color: {self.THEME["accent_primary"]};
    padding: 15px;
    text-align: left;
    font-weight: 600;
    color: {self.THEME["text_primary"]};
    border-bottom: 2px solid {self.THEME["accent_secondary"]};
}}

td {{
    padding: 12px 15px;
    border-bottom: 1px solid {self.THEME["accent_primary"]};
    color: {self.THEME["text_primary"]};
}}

tr:hover {{
    background-color: {self.THEME["accent_primary"]};
}}

/* Insights */
.insights {{
    background-color: {self.THEME["bg_secondary"]};
    border: 1px solid {self.THEME["accent_primary"]};
    border-radius: 8px;
    padding: 25px;
    margin-bottom: 40px;
}}

.insights h2 {{
    font-size: 1.5em;
    margin-bottom: 20px;
    color: {self.THEME["text_primary"]};
}}

.insight {{
    margin-bottom: 20px;
    padding: 15px;
    background-color: {self.THEME["bg_primary"]};
    border-left: 4px solid {self.THEME["accent_secondary"]};
    border-radius: 4px;
}}

.insight-title {{
    font-weight: 600;
    color: {self.THEME["accent_secondary"]};
    margin-bottom: 8px;
}}

.insight-text {{
    color: {self.THEME["text_secondary"]};
    line-height: 1.6;
}}

/* Footer */
.footer {{
    text-align: center;
    padding-top: 20px;
    border-top: 1px solid {self.THEME["accent_primary"]};
    color: {self.THEME["text_secondary"]};
    font-size: 0.85em;
}}

/* Responsive */
@media (max-width: 768px) {{
    .charts {{
        grid-template-columns: 1fr;
    }}

    .header h1 {{
        font-size: 1.8em;
    }}

    .card-value {{
        font-size: 2em;
    }}

    table {{
        font-size: 0.9em;
    }}

    th, td {{
        padding: 10px;
    }}
}}
</style>"""

    def _html_body_open(self) -> str:
        """Generate opening body tag."""
        return "<body>"

    def _html_body_close(self) -> str:
        """Generate closing body tag."""
        return "</body></html>"

    def _html_header_section(self, violation_summary: SessionViolationSummary) -> str:
        """Generate dashboard header section."""
        generated_at = self.generated_at.strftime("%Y-%m-%d %H:%M:%S")
        circuit_status = (
            "YES - Circuit Breaker Triggered"
            if violation_summary.circuit_breaker_triggered
            else "No"
        )

        return f"""<div class="container">
    <div class="header">
        <h1>Cost Attribution Dashboard</h1>
        <p class="subtitle">Phase 1 MVP - HtmlGraph Delegation Cost Analysis</p>
        <div class="header-meta">
            <span>Session ID: <strong>{violation_summary.session_id}</strong></span>
            <span>Generated: <strong>{generated_at}</strong></span>
            <span>Circuit Breaker: <strong class="status-{"error" if violation_summary.circuit_breaker_triggered else "good"}">{circuit_status}</strong></span>
        </div>
    </div>
"""

    def _html_summary_cards(self, violation_summary: SessionViolationSummary) -> str:
        """Generate summary metric cards."""
        metrics = self.generate_summary_metrics(violation_summary)

        compliance_status = (
            "status-good"
            if metrics["compliance_rate"] >= 0.8
            else "status-warning"
            if metrics["compliance_rate"] >= 0.5
            else "status-error"
        )

        return f"""<div class="cards">
        <div class="card">
            <div class="card-label">Total Violations</div>
            <div class="card-value">{metrics["total_violations"]}</div>
            <div class="card-meta">Direct execution violations detected</div>
        </div>

        <div class="card">
            <div class="card-label">Total Waste</div>
            <div class="card-value">{metrics["total_waste_tokens"]:,}<span class="card-unit"> tokens</span></div>
            <div class="card-meta">Avg: {metrics["avg_waste_per_violation"]:,} per violation</div>
        </div>

        <div class="card">
            <div class="card-label">Compliance Rate</div>
            <div class="card-value"><span class="{compliance_status}">{metrics["compliance_rate"]:.0%}</span></div>
            <div class="card-meta">Delegation adherence across session</div>
        </div>

        <div class="card">
            <div class="card-label">Potential Savings</div>
            <div class="card-value">{metrics["savings_potential"]:,}<span class="card-unit"> tokens</span></div>
            <div class="card-meta"><span class="status-good">{metrics["savings_percentage"]:.0f}% reduction</span></div>
        </div>
    </div>
"""

    def _html_charts_section(self, violation_summary: SessionViolationSummary) -> str:
        """Generate charts section with visualizations."""
        breakdown_by_type = self.generate_cost_breakdown_by_type(violation_summary)
        breakdown_by_tool = self.generate_cost_breakdown_by_tool(violation_summary)

        # Prepare data for charts
        type_labels = list(breakdown_by_type.keys())
        type_data = list(breakdown_by_type.values())

        tool_labels = list(breakdown_by_tool.keys())
        tool_data = list(breakdown_by_tool.values())

        # Embed data as JSON for JavaScript
        type_data_json = json.dumps(type_labels)
        type_values_json = json.dumps(type_data)
        tool_data_json = json.dumps(tool_labels)
        tool_values_json = json.dumps(tool_data)

        return f"""<div class="charts">
        <div class="chart-container">
            <div class="chart-title">Cost by Violation Type</div>
            <canvas id="chartByType" class="chart-canvas"></canvas>
        </div>

        <div class="chart-container">
            <div class="chart-title">Cost by Tool</div>
            <canvas id="chartByTool" class="chart-canvas"></canvas>
        </div>
    </div>

    <script>
        // Chart.js configuration
        const chartConfig = {{
            type_labels: {type_data_json},
            type_data: {type_values_json},
            tool_labels: {tool_data_json},
            tool_data: {tool_values_json}
        }};
    </script>
"""

    def _html_violations_table(self, violation_summary: SessionViolationSummary) -> str:
        """Generate detailed violations table."""
        table_rows = ""

        for i, violation in enumerate(violation_summary.violations, 1):
            vtype = str(violation.violation_type)
            warning_indicator = "⚠️" if violation.was_warned else ""

            table_rows += f"""        <tr>
            <td>{i}</td>
            <td>{violation.timestamp.strftime("%H:%M:%S")}</td>
            <td><strong>{violation.tool}</strong></td>
            <td>{vtype}</td>
            <td>{violation.actual_cost_tokens:,}</td>
            <td>{violation.optimal_cost_tokens:,}</td>
            <td><span class="status-error">{violation.waste_tokens:,}</span></td>
            <td>{violation.should_have_delegated_to}</td>
            <td>{warning_indicator}</td>
        </tr>
"""

        return f"""<div class="table-section">
        <h2>Violation Details</h2>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Time</th>
                        <th>Tool</th>
                        <th>Violation Type</th>
                        <th>Actual Cost</th>
                        <th>Optimal Cost</th>
                        <th>Waste</th>
                        <th>Should Delegate To</th>
                        <th>Warned</th>
                    </tr>
                </thead>
                <tbody>
{table_rows}                </tbody>
            </table>
        </div>
    </div>
"""

    def _html_insights_section(self, violation_summary: SessionViolationSummary) -> str:
        """Generate insights and recommendations."""
        metrics = self.generate_summary_metrics(violation_summary)
        breakdown_by_type = self.generate_cost_breakdown_by_type(violation_summary)

        insights = []

        # Insight 1: Compliance
        if metrics["compliance_rate"] >= 0.8:
            insights.append(
                (
                    "Excellent Delegation Compliance",
                    "Your delegation adherence is excellent. Continue following the delegation "
                    "patterns you've established.",
                )
            )
        elif metrics["compliance_rate"] >= 0.5:
            insights.append(
                (
                    "Moderate Compliance",
                    f"Improve delegation by {(1 - metrics['compliance_rate']) * 100:.0f}%. Focus on "
                    "delegating exploration and implementation work.",
                )
            )
        else:
            insights.append(
                (
                    "Low Delegation Compliance",
                    "Significant opportunity for improvement. Consider using Task() and spawn_* "
                    "functions for major work categories.",
                )
            )

        # Insight 2: Savings potential
        if metrics["savings_potential"] > 0:
            insights.append(
                (
                    "Significant Savings Opportunity",
                    f"By properly delegating all violations, you could save approximately "
                    f"{metrics['savings_potential']:,} tokens ({metrics['savings_percentage']:.0f}% reduction).",
                )
            )

        # Insight 3: Most costly violation type
        if breakdown_by_type:
            top_violation = max(breakdown_by_type.items(), key=lambda x: x[1])
            insights.append(
                (
                    f"Highest Cost: {top_violation[0]}",
                    f"This violation type accounts for {top_violation[1]:,} tokens. "
                    "Consider this area for immediate improvement.",
                )
            )

        # Insight 4: Circuit breaker
        if violation_summary.circuit_breaker_triggered:
            insights.append(
                (
                    "Circuit Breaker Triggered",
                    "You have exceeded 3 violations in this session. Please adopt proper delegation "
                    "practices to prevent future circuit breaker activation.",
                )
            )

        insights_html = ""
        for title, text in insights:
            insights_html += f"""        <div class="insight">
            <div class="insight-title">{title}</div>
            <div class="insight-text">{text}</div>
        </div>
"""

        return f"""<div class="insights">
        <h2>Insights & Recommendations</h2>
{insights_html}    </div>
"""

    def _html_footer_section(self) -> str:
        """Generate footer section."""
        return """    <div class="footer">
        <p>HtmlGraph Cost Attribution Dashboard | Phase 1 MVP | <a href="https://code.claude.com">Claude Code</a></p>
    </div>
</div>"""

    def _html_scripts(self) -> str:
        """Generate JavaScript for interactive charts."""
        return """<script>
// Initialize charts when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const config = window.chartConfig || {
        type_labels: [],
        type_data: [],
        tool_labels: [],
        tool_data: []
    };

    // Chart.js configuration
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                labels: {
                    color: '#e0e0e0',
                    font: { size: 12 }
                }
            },
            tooltip: {
                backgroundColor: 'rgba(26, 26, 46, 0.8)',
                titleColor: '#e0e0e0',
                bodyColor: '#b0b0b0',
                borderColor: '#0f3460',
                borderWidth: 1
            }
        },
        scales: {
            y: {
                ticks: { color: '#b0b0b0' },
                grid: { color: '#16213e' }
            },
            x: {
                ticks: { color: '#b0b0b0' },
                grid: { color: '#16213e' }
            }
        }
    };

    // Pie chart - Cost by Violation Type
    if (config.type_labels.length > 0) {
        const ctxType = document.getElementById('chartByType');
        if (ctxType) {
            new Chart(ctxType, {
                type: 'doughnut',
                data: {
                    labels: config.type_labels,
                    datasets: [{
                        label: 'Waste Tokens',
                        data: config.type_data,
                        backgroundColor: [
                            '#e94560',
                            '#ff9800',
                            '#ff6f00',
                            '#d84315',
                            '#c62828'
                        ],
                        borderColor: '#1a1a2e',
                        borderWidth: 2
                    }]
                },
                options: {
                    ...chartOptions,
                    plugins: {
                        ...chartOptions.plugins,
                        legend: {
                            ...chartOptions.plugins.legend,
                            position: 'bottom'
                        }
                    }
                }
            });
        }
    }

    // Bar chart - Cost by Tool
    if (config.tool_labels.length > 0) {
        const ctxTool = document.getElementById('chartByTool');
        if (ctxTool) {
            new Chart(ctxTool, {
                type: 'bar',
                data: {
                    labels: config.tool_labels,
                    datasets: [{
                        label: 'Waste Tokens',
                        data: config.tool_data,
                        backgroundColor: '#0f3460',
                        borderColor: '#e94560',
                        borderWidth: 2,
                        borderRadius: 4
                    }]
                },
                options: {
                    ...chartOptions,
                    indexAxis: 'y',
                    plugins: {
                        ...chartOptions.plugins,
                        legend: {
                            ...chartOptions.plugins.legend,
                            display: true
                        }
                    }
                }
            });
        }
    }
});
</script>"""

    def _create_empty_summary(self) -> SessionViolationSummary:
        """Create an empty violation summary for dashboard initialization."""
        return SessionViolationSummary(
            session_id="demo-session",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=1.0,
            violations=[],
        )
