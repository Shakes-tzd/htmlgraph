"""
CostReporter for OTEL ROI Analysis - Phase 1.

Generates interactive HTML dashboards showing cost analysis of Task delegations.
Creates visualizations of delegation costs, ROI, and optimization recommendations.

Features:
- Top 10 most expensive Task delegations
- Cost breakdown by subagent type and tool type
- ROI analysis comparing delegation vs direct execution
- Interactive charts using Chart.js
- Dark theme matching HtmlGraph visual style

Usage:
    from htmlgraph.analytics.cost_analyzer import CostAnalyzer
    from htmlgraph.analytics.cost_reporter import CostReporter

    analyzer = CostAnalyzer()
    reporter = CostReporter()
    html = reporter.generate_dashboard(analyzer)
    reporter.save_dashboard(html, "cost-analysis.html")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.analytics.cost_analyzer import CostAnalyzer


class CostReporter:
    """Generate interactive HTML dashboards from cost analysis data."""

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

    def generate_dashboard(self, analyzer: CostAnalyzer) -> str:
        """
        Generate complete interactive HTML dashboard.

        Args:
            analyzer: CostAnalyzer instance with cost data

        Returns:
            Complete HTML document as string
        """
        # Gather data
        cost_breakdown = analyzer.get_cost_breakdown()
        roi_stats = analyzer.get_roi_stats()
        top_delegations = analyzer.get_top_delegations(10)
        all_delegations = analyzer.get_task_delegations_with_costs()

        # Build dashboard components
        html_parts = [
            self._html_header(),
            self._html_styles(),
            self._html_body_open(),
            self._html_header_section(roi_stats),
            self._html_summary_cards(roi_stats, cost_breakdown),
            self._html_charts_section(cost_breakdown, all_delegations),
            self._html_top_delegations_table(top_delegations),
            self._html_insights_section(roi_stats, cost_breakdown),
            self._html_footer_section(),
            self._html_body_close(),
            self._html_scripts(cost_breakdown, all_delegations),
        ]

        return "\n".join(html_parts)

    def save_dashboard(self, html: str, path: str | Path) -> None:
        """
        Save HTML dashboard to file.

        Args:
            html: HTML content to save
            path: File path to save to
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    # ===== HTML Generation Methods =====

    def _html_header(self) -> str:
        """Generate HTML document header."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cost Attribution Dashboard - HtmlGraph OTEL ROI Analysis</title>
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

.container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}}

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

.status-good {{
    color: {self.THEME["success"]};
}}

.status-warning {{
    color: {self.THEME["warning"]};
}}

.status-error {{
    color: {self.THEME["error"]};
}}

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

.footer {{
    text-align: center;
    padding-top: 20px;
    border-top: 1px solid {self.THEME["accent_primary"]};
    color: {self.THEME["text_secondary"]};
    font-size: 0.85em;
}}

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

    def _html_header_section(self, roi_stats: Any) -> str:
        """Generate dashboard header section."""
        generated_at = self.generated_at.strftime("%Y-%m-%d %H:%M:%S")

        return f"""<div class="container">
    <div class="header">
        <h1>Cost Attribution Dashboard</h1>
        <p class="subtitle">OTEL ROI Analysis - Phase 1 MVP</p>
        <div class="header-meta">
            <span>Generated: <strong>{generated_at}</strong></span>
            <span>Total Delegations: <strong>{roi_stats.total_delegations}</strong></span>
            <span>Status: <strong class="status-good">✓ Active</strong></span>
        </div>
    </div>
"""

    def _html_summary_cards(self, roi_stats: Any, cost_breakdown: Any) -> str:
        """Generate summary metric cards."""
        total_cost_usd = roi_stats.total_delegation_cost * 0.0000045

        return f"""<div class="cards">
        <div class="card">
            <div class="card-label">Total Delegation Cost</div>
            <div class="card-value">${total_cost_usd:.2f}<span class="card-unit"> USD</span></div>
            <div class="card-meta">{roi_stats.total_delegation_cost:,} tokens</div>
        </div>

        <div class="card">
            <div class="card-label">Estimated Direct Cost</div>
            <div class="card-value">${roi_stats.estimated_direct_cost * 0.0000045:.2f}<span class="card-unit"> USD</span></div>
            <div class="card-meta">{roi_stats.estimated_direct_cost:,} tokens (2.5x overhead)</div>
        </div>

        <div class="card">
            <div class="card-label">Estimated Savings</div>
            <div class="card-value"><span class="status-good">${roi_stats.estimated_savings * 0.0000045:.2f}</span></div>
            <div class="card-meta"><span class="status-good">{roi_stats.savings_percentage:.0f}% reduction</span></div>
        </div>

        <div class="card">
            <div class="card-label">Avg Cost per Delegation</div>
            <div class="card-value">{roi_stats.avg_cost_per_delegation:,.0f}<span class="card-unit"> tokens</span></div>
            <div class="card-meta">Across {roi_stats.total_delegations} delegations</div>
        </div>
    </div>
"""

    def _html_charts_section(self, cost_breakdown: Any, all_delegations: Any) -> str:
        """Generate charts section with visualizations."""
        # Prepare data for charts
        subagent_labels = list(cost_breakdown.by_subagent.keys())
        subagent_data = list(cost_breakdown.by_subagent.values())

        tool_labels = list(cost_breakdown.by_tool.keys())
        tool_data = list(cost_breakdown.by_tool.values())

        # Embed data as JSON for JavaScript
        subagent_labels_json = json.dumps(subagent_labels)
        subagent_data_json = json.dumps(subagent_data)
        tool_labels_json = json.dumps(tool_labels)
        tool_data_json = json.dumps(tool_data)

        return f"""<div class="charts">
        <div class="chart-container">
            <div class="chart-title">Cost by Subagent Type</div>
            <canvas id="chartBySubagent" class="chart-canvas"></canvas>
        </div>

        <div class="chart-container">
            <div class="chart-title">Cost by Tool Type</div>
            <canvas id="chartByTool" class="chart-canvas"></canvas>
        </div>
    </div>

    <script>
        window.chartData = {{
            subagent_labels: {subagent_labels_json},
            subagent_data: {subagent_data_json},
            tool_labels: {tool_labels_json},
            tool_data: {tool_data_json}
        }};
    </script>
"""

    def _html_top_delegations_table(self, top_delegations: list[Any]) -> str:
        """Generate top delegations table."""
        table_rows = ""

        for i, delegation in enumerate(top_delegations, 1):
            cost_usd = delegation.total_cost_tokens * 0.0000045
            timestamp = delegation.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            table_rows += f"""        <tr>
            <td>{i}</td>
            <td>{timestamp}</td>
            <td><strong>{delegation.subagent_type}</strong></td>
            <td>{delegation.tool_count}</td>
            <td>{delegation.total_cost_tokens:,}</td>
            <td>${cost_usd:.2f}</td>
            <td><code style="font-size: 0.85em; color: #b0b0b0;">{delegation.event_id[:16]}...</code></td>
        </tr>
"""

        return f"""<div class="table-section">
        <h2>Top 10 Most Expensive Delegations</h2>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Timestamp</th>
                        <th>Subagent Type</th>
                        <th>Tool Count</th>
                        <th>Cost (tokens)</th>
                        <th>Cost (USD)</th>
                        <th>Event ID</th>
                    </tr>
                </thead>
                <tbody>
{table_rows}                </tbody>
            </table>
        </div>
    </div>
"""

    def _html_insights_section(self, roi_stats: Any, cost_breakdown: Any) -> str:
        """Generate insights and recommendations."""
        insights = []

        # Insight 1: ROI summary
        if roi_stats.savings_percentage > 40:
            insights.append(
                (
                    "Strong Delegation ROI",
                    f"Your delegation strategy is effective. By properly delegating work, "
                    f"you're achieving approximately {roi_stats.savings_percentage:.0f}% cost savings "
                    f"compared to direct execution.",
                )
            )
        else:
            insights.append(
                (
                    "Delegation Opportunity",
                    f"Current delegation strategy shows {roi_stats.savings_percentage:.0f}% potential savings. "
                    f"Consider delegating more complex work to specialized subagents.",
                )
            )

        # Insight 2: Most expensive subagent
        if cost_breakdown.by_subagent:
            top_subagent = max(cost_breakdown.by_subagent.items(), key=lambda x: x[1])
            insights.append(
                (
                    f"Highest Cost Subagent: {top_subagent[0]}",
                    f"This subagent type accounts for {top_subagent[1]:,} tokens. "
                    f"Review the work being delegated here for optimization opportunities.",
                )
            )

        # Insight 3: Most expensive tool
        if cost_breakdown.by_tool:
            top_tool = max(cost_breakdown.by_tool.items(), key=lambda x: x[1])
            insights.append(
                (
                    f"Highest Cost Tool: {top_tool[0]}",
                    f"This tool is consuming {top_tool[1]:,} tokens. "
                    f"Consider batching operations or using more efficient approaches.",
                )
            )

        # Insight 4: Parallelization benefit
        insights.append(
            (
                "Parallelization Benefit",
                f"Subagent delegation enables {roi_stats.avg_parallelization_factor:.1f}x efficiency gain "
                f"through parallel execution and focused context.",
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
        <p>HtmlGraph Cost Attribution Dashboard | OTEL ROI Analysis Phase 1 | <a href="https://code.claude.com">Claude Code</a></p>
    </div>
</div>"""

    def _html_scripts(self, cost_breakdown: Any, all_delegations: Any) -> str:
        """Generate JavaScript for interactive charts."""
        return """<script>
document.addEventListener('DOMContentLoaded', function() {
    const data = window.chartData || {
        subagent_labels: [],
        subagent_data: [],
        tool_labels: [],
        tool_data: []
    };

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

    // Doughnut chart - Cost by Subagent Type
    if (data.subagent_labels.length > 0) {
        const ctxSubagent = document.getElementById('chartBySubagent');
        if (ctxSubagent) {
            new Chart(ctxSubagent, {
                type: 'doughnut',
                data: {
                    labels: data.subagent_labels,
                    datasets: [{
                        label: 'Cost (tokens)',
                        data: data.subagent_data,
                        backgroundColor: [
                            '#e94560',
                            '#ff9800',
                            '#ff6f00',
                            '#d84315',
                            '#c62828',
                            '#0f3460'
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
    if (data.tool_labels.length > 0) {
        const ctxTool = document.getElementById('chartByTool');
        if (ctxTool) {
            new Chart(ctxTool, {
                type: 'bar',
                data: {
                    labels: data.tool_labels,
                    datasets: [{
                        label: 'Cost (tokens)',
                        data: data.tool_data,
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
