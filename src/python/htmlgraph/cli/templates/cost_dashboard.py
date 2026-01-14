from __future__ import annotations

"""HTML template for cost dashboard.

This module generates a beautiful, interactive HTML dashboard for cost analysis.
Separated from main CLI code for maintainability and testability.
"""


from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.cli.analytics import CostSummary


def generate_html(summary: CostSummary) -> str:
    """Generate HTML dashboard from cost summary.

    Args:
        summary: Validated cost summary data

    Returns:
        Complete HTML document as string
    """
    # Calculate derived metrics
    total_cost = summary.total_cost_tokens
    avg_cost = summary.avg_cost_per_event
    delegation_pct = summary.delegation_percentage
    cost_usd = summary.estimated_cost_usd

    # Sort tools by cost
    sorted_tools = sorted(
        summary.tool_costs.items(),
        key=lambda x: x[1].total_tokens,
        reverse=True,
    )

    # Sort sessions by cost
    sorted_sessions = sorted(
        summary.session_costs.items(),
        key=lambda x: x[1].total_tokens,
        reverse=True,
    )

    # Build tool cost rows
    tool_rows = _build_tool_rows(sorted_tools, total_cost)

    # Build session cost rows
    session_rows = _build_session_rows(sorted_sessions, total_cost)

    # Build insights
    insights = _build_insights_html(delegation_pct, sorted_tools, total_cost)

    # Generate complete HTML
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HtmlGraph Cost Dashboard</title>
    <style>
{_get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>💰 HtmlGraph Cost Dashboard</h1>
            <p class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Total Cost</div>
                    <div class="metric-value">{total_cost:,}<span class="metric-unit">tokens</span></div>
                </div>
                <div class="metric success">
                    <div class="metric-label">Estimated USD</div>
                    <div class="metric-value">${cost_usd:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Average Cost</div>
                    <div class="metric-value">{avg_cost:,.0f}<span class="metric-unit">tokens</span></div>
                </div>
                <div class="metric success">
                    <div class="metric-label">Delegation Rate</div>
                    <div class="metric-value">{delegation_pct:.1f}%</div>
                </div>
            </div>
        </header>

        <section>
            <h2>📊 Cost by Tool</h2>
            <table>
                <thead>
                    <tr>
                        <th>Tool</th>
                        <th>Count</th>
                        <th>Total Tokens</th>
                        <th>% of Total</th>
                    </tr>
                </thead>
                <tbody>
                    {tool_rows}
                </tbody>
            </table>
        </section>

        <section>
            <h2>🔄 Cost by Session</h2>
            <table>
                <thead>
                    <tr>
                        <th>Session ID</th>
                        <th>Count</th>
                        <th>Total Tokens</th>
                        <th>% of Total</th>
                    </tr>
                </thead>
                <tbody>
                    {session_rows}
                </tbody>
            </table>
        </section>

        <section>
            <h2>💡 Insights & Recommendations</h2>
            <div class="insights">
                {insights}
            </div>
        </section>

        <div class="footer">
            <p>HtmlGraph Cost Attribution Dashboard | Real-time cost tracking and optimization</p>
        </div>
    </div>
</body>
</html>"""


def _build_tool_rows(sorted_tools: list[tuple[str, Any]], total_cost: int) -> str:
    """Build HTML table rows for tool costs."""
    if not sorted_tools or total_cost == 0:
        return '<tr><td colspan="4" class="cell">No data available</td></tr>'

    rows = []
    for tool, data in sorted_tools[:20]:  # Top 20 tools
        pct = data.total_tokens / total_cost * 100
        rows.append(
            f"""
    <tr>
        <td class="cell">{tool}</td>
        <td class="cell number">{data.count}</td>
        <td class="cell number">{data.total_tokens:,}</td>
        <td class="cell number">{pct:.1f}%</td>
    </tr>"""
        )
    return "".join(rows)


def _build_session_rows(sorted_sessions: list[tuple[str, Any]], total_cost: int) -> str:
    """Build HTML table rows for session costs."""
    if not sorted_sessions or total_cost == 0:
        return '<tr><td colspan="4" class="cell">No data available</td></tr>'

    rows = []
    for session, data in sorted_sessions[:20]:  # Top 20 sessions
        pct = data.total_tokens / total_cost * 100
        session_display = session[:12] + "..." if len(session) > 12 else session
        rows.append(
            f"""
    <tr>
        <td class="cell">{session_display}</td>
        <td class="cell number">{data.count}</td>
        <td class="cell number">{data.total_tokens:,}</td>
        <td class="cell number">{pct:.1f}%</td>
    </tr>"""
        )
    return "".join(rows)


def _build_insights_html(
    delegation_pct: float, sorted_tools: list[tuple[str, Any]], total_cost: int
) -> str:
    """Build insights and recommendations section."""
    insights = []

    # Delegation insight
    delegation_msg = (
        "Continue delegation for cost efficiency!"
        if delegation_pct > 50
        else "Consider delegating more operations to reduce costs."
    )
    insights.append(
        f"""
                <div class="insight">
                    <div class="insight-title">✓ Delegation Usage</div>
                    <div class="insight-text">
                        You're delegating {delegation_pct:.1f}% of operations.
                        {delegation_msg}
                    </div>
                </div>"""
    )

    # Top cost driver insight
    if sorted_tools and total_cost > 0:
        top_tool, top_data = sorted_tools[0]
        top_pct = top_data.total_tokens / total_cost * 100
        insights.append(
            f"""
                <div class="insight">
                    <div class="insight-title">🎯 Top Cost Driver</div>
                    <div class="insight-text">
                        {top_tool} accounts for {top_pct:.1f}% of total cost.
                        Review if this tool usage is optimal.
                    </div>
                </div>"""
        )

    # Parallelization insight
    insights.append(
        """
                <div class="insight">
                    <div class="insight-title">📈 Parallelization Opportunity</div>
                    <div class="insight-text">
                        Parallel Task() calls can reduce overall execution time by ~40%.
                        Look for independent operations that can run simultaneously.
                    </div>
                </div>"""
    )

    return "".join(insights)


def _get_css_styles() -> str:
    """Get CSS styles for the dashboard.

    Extracted to separate function for maintainability.
    """
    return """        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 28px;
        }

        .timestamp {
            color: #999;
            font-size: 12px;
        }

        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .metric {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .metric-label {
            font-size: 12px;
            opacity: 0.9;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .metric-value {
            font-size: 32px;
            font-weight: bold;
        }

        .metric-unit {
            font-size: 14px;
            opacity: 0.8;
            margin-left: 8px;
        }

        .metric.warning {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }

        .metric.success {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }

        section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #ddd;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }

        td.cell {
            color: #333;
        }

        td.number {
            text-align: right;
            font-family: 'Monaco', 'Courier New', monospace;
            color: #667eea;
            font-weight: 500;
        }

        tr:hover {
            background: #f9f9f9;
        }

        .insights {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .insight {
            background: #f0f4ff;
            border-left: 4px solid #667eea;
            padding: 16px;
            border-radius: 4px;
        }

        .insight-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }

        .insight-text {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
        }

        .footer {
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 40px;
        }"""
