defmodule HtmlgraphDashboardWeb.Styles do
  @moduledoc "Inline CSS for the dashboard. No build tools needed."

  def css do
    ~S"""
    :root {
      --bg-primary: #0d1117;
      --bg-secondary: #161b22;
      --bg-tertiary: #21262d;
      --bg-hover: #30363d;
      --border: #30363d;
      --text-primary: #e6edf3;
      --text-secondary: #8b949e;
      --text-muted: #6e7681;
      --accent-blue: #58a6ff;
      --accent-green: #3fb950;
      --accent-orange: #d29922;
      --accent-red: #f85149;
      --accent-purple: #bc8cff;
      --accent-cyan: #39d2c0;
      --accent-pink: #f778ba;
      --radius: 6px;
      --font-mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      background: var(--bg-primary);
      color: var(--text-primary);
      font-family: var(--font-sans);
      font-size: 14px;
      line-height: 1.5;
    }

    /* Header */
    .header {
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .header-title {
      font-size: 16px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .header-title .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent-green);
      animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }

    .header-meta {
      font-size: 12px;
      color: var(--text-secondary);
    }

    /* Activity Feed Container */
    .feed-container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 16px 24px;
    }

    /* Session Group */
    .session-group {
      margin-bottom: 24px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }

    .session-header {
      background: var(--bg-secondary);
      padding: 10px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
    }

    .session-header:hover {
      background: var(--bg-tertiary);
    }

    .session-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    /* Activity Table */
    .activity-table {
      width: 100%;
      border-collapse: collapse;
    }

    .activity-table th {
      background: var(--bg-tertiary);
      padding: 6px 12px;
      text-align: left;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-secondary);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 49px;
      z-index: 10;
    }

    /* Row styles */
    .activity-row {
      border-bottom: 1px solid var(--border);
      transition: background 0.15s;
    }

    .activity-row:hover {
      background: var(--bg-hover);
    }

    .activity-row td {
      padding: 6px 12px;
      vertical-align: middle;
      white-space: nowrap;
    }

    /* Parent row (UserQuery) */
    .activity-row.parent-row {
      background: var(--bg-secondary);
    }

    .activity-row.parent-row:hover {
      background: var(--bg-tertiary);
    }

    .activity-row.parent-row td {
      padding: 10px 12px;
      font-weight: 500;
    }

    /* Child rows — depth indentation */
    .activity-row.child-row { display: none; }
    .activity-row.child-row.expanded { display: table-row; }

    .depth-indicator {
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .depth-guide {
      display: inline-block;
      width: 20px;
      border-left: 2px solid var(--border);
      height: 100%;
      margin-right: 0;
    }

    .depth-0 .depth-indent { padding-left: 24px; }
    .depth-1 .depth-indent { padding-left: 48px; }
    .depth-2 .depth-indent { padding-left: 72px; }
    .depth-3 .depth-indent { padding-left: 96px; }

    .tree-connector {
      color: var(--text-muted);
      margin-right: 6px;
      font-family: var(--font-mono);
      font-size: 12px;
    }

    /* Toggle button */
    .toggle-btn {
      background: none;
      border: none;
      color: var(--text-secondary);
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
      transition: all 0.15s;
      display: inline-flex;
      align-items: center;
    }

    .toggle-btn:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    .toggle-btn .arrow {
      display: inline-block;
      transition: transform 0.2s;
    }

    .toggle-btn .arrow.expanded {
      transform: rotate(90deg);
    }

    /* Badges */
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
      gap: 4px;
      white-space: nowrap;
    }

    .badge-tool {
      background: rgba(88, 166, 255, 0.15);
      color: var(--accent-blue);
      font-family: var(--font-mono);
      font-size: 11px;
    }

    .badge-userquery {
      background: rgba(188, 140, 255, 0.15);
      color: var(--accent-purple);
    }

    .badge-task {
      background: rgba(247, 120, 186, 0.15);
      color: var(--accent-pink);
    }

    .badge-agent {
      background: rgba(57, 210, 192, 0.15);
      color: var(--accent-cyan);
    }

    .badge-error {
      background: rgba(248, 81, 73, 0.15);
      color: var(--accent-red);
    }

    .badge-success {
      background: rgba(63, 185, 80, 0.15);
      color: var(--accent-green);
    }

    .badge-model {
      background: rgba(210, 153, 34, 0.15);
      color: var(--accent-orange);
    }

    .badge-session {
      background: rgba(88, 166, 255, 0.1);
      color: var(--accent-blue);
      border: 1px solid rgba(88, 166, 255, 0.2);
    }

    .badge-status-active {
      background: rgba(63, 185, 80, 0.15);
      color: var(--accent-green);
    }

    .badge-status-completed {
      background: rgba(139, 148, 158, 0.15);
      color: var(--text-secondary);
    }

    .badge-feature {
      background: rgba(210, 153, 34, 0.1);
      color: var(--accent-orange);
      border: 1px solid rgba(210, 153, 34, 0.2);
    }

    .badge-subagent {
      background: rgba(57, 210, 192, 0.1);
      color: var(--accent-cyan);
      border: 1px solid rgba(57, 210, 192, 0.2);
    }

    .badge-count {
      background: var(--bg-tertiary);
      color: var(--text-secondary);
      min-width: 20px;
      text-align: center;
    }

    /* Stats row */
    .stats-badges {
      display: flex;
      gap: 6px;
      align-items: center;
    }

    /* Event dot indicator */
    .event-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      display: inline-block;
      margin-right: 6px;
      flex-shrink: 0;
    }

    .event-dot.tool_call { background: var(--accent-blue); }
    .event-dot.tool_result { background: var(--accent-green); }
    .event-dot.error { background: var(--accent-red); }
    .event-dot.task_delegation { background: var(--accent-pink); }
    .event-dot.delegation { background: var(--accent-cyan); }
    .event-dot.start { background: var(--accent-green); }
    .event-dot.end { background: var(--text-muted); }

    /* Summary text */
    .summary-text {
      color: var(--text-secondary);
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 500px;
    }

    .summary-text.prompt {
      color: var(--text-primary);
      font-weight: 500;
    }

    /* Timestamp */
    .timestamp {
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--text-muted);
    }

    /* Duration */
    .duration {
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--text-secondary);
    }

    /* New event flash animation */
    @keyframes flash-new {
      0% { background: rgba(63, 185, 80, 0.2); }
      100% { background: transparent; }
    }

    .activity-row.new-event {
      animation: flash-new 2s ease-out;
    }

    /* Live indicator */
    .live-indicator {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--accent-green);
    }

    .live-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--accent-green);
      animation: pulse 2s ease-in-out infinite;
    }

    /* Empty state */
    .empty-state {
      text-align: center;
      padding: 60px 20px;
      color: var(--text-secondary);
    }

    .empty-state h2 {
      font-size: 18px;
      margin-bottom: 8px;
      color: var(--text-primary);
    }

    /* Flash messages */
    .flash-group { padding: 0 24px; }
    .flash-info {
      background: rgba(88, 166, 255, 0.1);
      border: 1px solid rgba(88, 166, 255, 0.3);
      color: var(--accent-blue);
      padding: 8px 16px;
      border-radius: var(--radius);
      margin-top: 8px;
    }
    .flash-error {
      background: rgba(248, 81, 73, 0.1);
      border: 1px solid rgba(248, 81, 73, 0.3);
      color: var(--accent-red);
      padding: 8px 16px;
      border-radius: var(--radius);
      margin-top: 8px;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: var(--bg-tertiary); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--bg-hover); }
    """
  end
end
