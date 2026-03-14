defmodule HtmlgraphDashboardWeb.ActivityFeedLive do
  @moduledoc """
  Live activity feed with multi-level nested events, badges, and real-time updates.

  Architecture:
  - Polls SQLite database via EventPoller GenServer
  - Receives new events via PubSub broadcast
  - Maintains expand/collapse state per conversation turn
  - Multi-level nesting: Session > UserQuery > Tool Events > Subagent Events
  """
  use HtmlgraphDashboardWeb, :live_view

  alias HtmlgraphDashboard.Activity
  alias HtmlgraphDashboard.EventPoller

  @impl true
  def mount(params, _session, socket) do
    if connected?(socket) do
      EventPoller.subscribe()
    end

    session_id = params["session_id"]

    socket =
      socket
      |> assign(:session_filter, session_id)
      |> assign(:expanded, MapSet.new())
      |> assign(:new_event_ids, MapSet.new())
      |> load_feed()

    {:ok, socket}
  end

  @impl true
  def handle_params(params, _uri, socket) do
    session_id = params["session_id"]

    socket =
      socket
      |> assign(:session_filter, session_id)
      |> load_feed()

    {:noreply, socket}
  end

  @impl true
  def handle_event("toggle", %{"event-id" => event_id}, socket) do
    expanded = socket.assigns.expanded

    expanded =
      if MapSet.member?(expanded, event_id) do
        MapSet.delete(expanded, event_id)
      else
        MapSet.put(expanded, event_id)
      end

    {:noreply, assign(socket, :expanded, expanded)}
  end

  def handle_event("toggle_session", %{"session-id" => session_id}, socket) do
    expanded = socket.assigns.expanded
    key = "session:#{session_id}"

    expanded =
      if MapSet.member?(expanded, key) do
        MapSet.delete(expanded, key)
      else
        MapSet.put(expanded, key)
      end

    {:noreply, assign(socket, :expanded, expanded)}
  end

  @impl true
  def handle_info({:new_event, event}, socket) do
    # Mark the new event for flash animation
    new_ids = MapSet.put(socket.assigns.new_event_ids, event["event_id"])

    socket =
      socket
      |> assign(:new_event_ids, new_ids)
      |> load_feed()

    # Clear the flash after 3 seconds
    Process.send_after(self(), {:clear_new, event["event_id"]}, 3_000)

    {:noreply, socket}
  end

  def handle_info({:clear_new, event_id}, socket) do
    new_ids = MapSet.delete(socket.assigns.new_event_ids, event_id)
    {:noreply, assign(socket, :new_event_ids, new_ids)}
  end

  defp load_feed(socket) do
    opts =
      case socket.assigns[:session_filter] do
        nil -> [limit: 50]
        sid -> [limit: 50, session_id: sid]
      end

    feed = Activity.list_activity_feed(opts)
    total_events = feed |> Enum.map(fn g -> length(g.turns) end) |> Enum.sum()

    socket
    |> assign(:feed, feed)
    |> assign(:total_events, total_events)
  end

  # --- Template Helpers ---

  defp tool_badge_class(tool_name) do
    case tool_name do
      "UserQuery" -> "badge-userquery"
      "Task" -> "badge-task"
      "Agent" -> "badge-agent"
      "Bash" -> "badge-tool"
      "Read" -> "badge-tool"
      "Write" -> "badge-tool"
      "Edit" -> "badge-tool"
      "Glob" -> "badge-tool"
      "Grep" -> "badge-tool"
      _ -> "badge-tool"
    end
  end

  defp event_dot_class(event_type) do
    case event_type do
      "error" -> "error"
      "task_delegation" -> "task_delegation"
      "delegation" -> "delegation"
      "tool_result" -> "tool_result"
      _ -> "tool_call"
    end
  end

  defp format_timestamp(nil), do: ""

  defp format_timestamp(ts) when is_binary(ts) do
    # Extract HH:MM:SS from ISO timestamp
    case Regex.run(~r/(\d{2}:\d{2}:\d{2})/, ts) do
      [_, time] -> time
      _ -> ts
    end
  end

  defp format_duration(nil), do: ""
  defp format_duration(0), do: ""
  defp format_duration(0.0), do: ""

  defp format_duration(seconds) when is_number(seconds) do
    cond do
      seconds < 1 -> "#{round(seconds * 1000)}ms"
      seconds < 60 -> "#{Float.round(seconds * 1.0, 1)}s"
      true -> "#{round(seconds / 60)}m"
    end
  end

  defp format_tokens(nil), do: ""
  defp format_tokens(0), do: ""
  defp format_tokens(tokens) when tokens > 1000, do: "#{Float.round(tokens / 1000, 1)}k"
  defp format_tokens(tokens), do: "#{tokens}"

  defp truncate(nil, _), do: ""

  defp truncate(text, max_len) when is_binary(text) do
    if String.length(text) > max_len do
      String.slice(text, 0, max_len) <> "..."
    else
      text
    end
  end

  defp has_children?(event) do
    children = event["children"] || []
    length(children) > 0
  end

  defp child_count(event) do
    children = event["children"] || []
    length(children)
  end

  defp is_expanded?(expanded, event_id) do
    MapSet.member?(expanded, event_id)
  end

  defp is_new?(new_event_ids, event_id) do
    MapSet.member?(new_event_ids, event_id)
  end

  defp session_expanded?(expanded, session_id) do
    MapSet.member?(expanded, "session:#{session_id}")
  end

  defp depth_class(depth) do
    case depth do
      0 -> "depth-0"
      1 -> "depth-1"
      2 -> "depth-2"
      _ -> "depth-3"
    end
  end

  defp tree_connector(depth) do
    case depth do
      0 -> "├─"
      1 -> "│ ├─"
      2 -> "│ │ ├─"
      _ -> "│ │ │ ├─"
    end
  end

  @impl true
  def render(assigns) do
    ~H"""
    <div class="header">
      <div class="header-title">
        <span class="dot"></span>
        HtmlGraph Activity Feed
      </div>
      <div style="display: flex; align-items: center; gap: 16px;">
        <div class="live-indicator">
          <span class="live-dot"></span>
          Live
        </div>
        <div class="header-meta">
          <%= @total_events %> conversation turns
        </div>
      </div>
    </div>

    <div class="feed-container">
      <%= if @feed == [] do %>
        <div class="empty-state">
          <h2>No activity yet</h2>
          <p>Events will appear here as agents work. The feed updates in real-time.</p>
        </div>
      <% else %>
        <%= for group <- @feed do %>
          <div class="session-group">
            <!-- Session Header -->
            <div
              class="session-header"
              phx-click="toggle_session"
              phx-value-session-id={group.session_id}
            >
              <div class="session-info">
                <span class="toggle-btn">
                  <span class={["arrow", session_expanded?(@expanded, group.session_id) && "expanded"]}>
                    ▶
                  </span>
                </span>
                <span class="badge badge-session">
                  <%= truncate(group.session_id, 12) %>
                </span>
                <%= if group.session do %>
                  <span class={"badge badge-status-#{group.session["status"] || "active"}"}>
                    <%= group.session["status"] || "active" %>
                  </span>
                  <%= if group.session["agent_assigned"] do %>
                    <span class="badge badge-agent">
                      <%= group.session["agent_assigned"] %>
                    </span>
                  <% end %>
                  <%= if group.session["model"] do %>
                    <span class="badge badge-model">
                      <%= group.session["model"] %>
                    </span>
                  <% end %>
                <% end %>
              </div>
              <div class="stats-badges">
                <span class="badge badge-count">
                  <%= length(group.turns) %> turns
                </span>
                <%= if group.session do %>
                  <span class="badge badge-count">
                    <%= group.session["total_events"] || 0 %> events
                  </span>
                <% end %>
              </div>
            </div>

            <!-- Activity Table (shown when session expanded or no filter) -->
            <table
              class="activity-table"
              style={unless(session_expanded?(@expanded, group.session_id) || @session_filter, do: "display: none")}
            >
              <thead>
                <tr>
                  <th style="width: 40px"></th>
                  <th>Event</th>
                  <th>Summary</th>
                  <th>Badges</th>
                  <th style="width: 80px">Time</th>
                  <th style="width: 70px">Duration</th>
                  <th style="width: 60px">Tokens</th>
                </tr>
              </thead>
              <tbody>
                <%= for turn <- group.turns do %>
                  <!-- UserQuery Parent Row -->
                  <tr class={[
                    "activity-row parent-row",
                    is_new?(@new_event_ids, turn.user_query["event_id"]) && "new-event"
                  ]}>
                    <td>
                      <%= if length(turn.children) > 0 do %>
                        <button
                          class="toggle-btn"
                          phx-click="toggle"
                          phx-value-event-id={turn.user_query["event_id"]}
                        >
                          <span class={["arrow", is_expanded?(@expanded, turn.user_query["event_id"]) && "expanded"]}>
                            ▶
                          </span>
                        </button>
                      <% end %>
                    </td>
                    <td>
                      <span class="event-dot tool_call"></span>
                      <span class="badge badge-userquery">UserQuery</span>
                    </td>
                    <td>
                      <span class="summary-text prompt">
                        <%= truncate(turn.user_query["input_summary"], 100) %>
                      </span>
                    </td>
                    <td>
                      <div class="stats-badges">
                        <span class="badge badge-count">
                          <%= turn.stats.tool_count %> tools
                        </span>
                        <%= if turn.stats.error_count > 0 do %>
                          <span class="badge badge-error">
                            <%= turn.stats.error_count %> errors
                          </span>
                        <% end %>
                        <%= if turn.work_item do %>
                          <span class="badge badge-feature">
                            <%= truncate(turn.work_item["title"], 30) %>
                          </span>
                        <% end %>
                        <%= for model <- turn.stats.models do %>
                          <span class="badge badge-model"><%= model %></span>
                        <% end %>
                      </div>
                    </td>
                    <td>
                      <span class="timestamp">
                        <%= format_timestamp(turn.user_query["timestamp"]) %>
                      </span>
                    </td>
                    <td>
                      <span class="duration">
                        <%= format_duration(turn.stats.total_duration) %>
                      </span>
                    </td>
                    <td>
                      <span class="duration">
                        <%= format_tokens(turn.stats.total_tokens) %>
                      </span>
                    </td>
                  </tr>

                  <!-- Child Events (nested, collapsible) -->
                  <%= if is_expanded?(@expanded, turn.user_query["event_id"]) do %>
                    <%= for child <- turn.children do %>
                      <.event_row
                        event={child}
                        expanded={@expanded}
                        new_event_ids={@new_event_ids}
                      />
                    <% end %>
                  <% end %>
                <% end %>
              </tbody>
            </table>
          </div>
        <% end %>
      <% end %>
    </div>
    """
  end

  defp event_row(assigns) do
    ~H"""
    <tr class={[
      "activity-row child-row expanded",
      depth_class(@event["depth"] || 0),
      is_new?(@new_event_ids, @event["event_id"]) && "new-event"
    ]}>
      <td>
        <%= if has_children?(@event) do %>
          <button
            class="toggle-btn"
            phx-click="toggle"
            phx-value-event-id={@event["event_id"]}
          >
            <span class={["arrow", is_expanded?(@expanded, @event["event_id"]) && "expanded"]}>
              ▶
            </span>
          </button>
        <% end %>
      </td>
      <td>
        <div class={"depth-indicator #{depth_class(@event["depth"] || 0)}"}>
          <span class="depth-indent">
            <span class="tree-connector"><%= tree_connector(@event["depth"] || 0) %></span>
            <span class={"event-dot #{event_dot_class(@event["event_type"])}"}>
            </span>
            <span class={"badge #{tool_badge_class(@event["tool_name"])}"}>
              <%= @event["tool_name"] %>
            </span>
          </span>
        </div>
      </td>
      <td>
        <span class="summary-text">
          <%= truncate(@event["input_summary"] || @event["output_summary"], 80) %>
        </span>
      </td>
      <td>
        <div class="stats-badges">
          <%= if @event["subagent_type"] do %>
            <span class="badge badge-subagent">
              <%= @event["subagent_type"] %>
            </span>
          <% end %>
          <%= if @event["model"] do %>
            <span class="badge badge-model">
              <%= @event["model"] %>
            </span>
          <% end %>
          <%= if @event["event_type"] == "error" do %>
            <span class="badge badge-error">error</span>
          <% end %>
          <%= if has_children?(@event) do %>
            <span class="badge badge-count">
              <%= child_count(@event) %>
            </span>
          <% end %>
        </div>
      </td>
      <td>
        <span class="timestamp">
          <%= format_timestamp(@event["timestamp"]) %>
        </span>
      </td>
      <td>
        <span class="duration">
          <%= format_duration(@event["execution_duration_seconds"]) %>
        </span>
      </td>
      <td>
        <span class="duration">
          <%= format_tokens(@event["cost_tokens"]) %>
        </span>
      </td>
    </tr>

    <!-- Recursive children -->
    <%= if is_expanded?(@expanded, @event["event_id"]) do %>
      <%= for child <- (@event["children"] || []) do %>
        <.event_row
          event={child}
          expanded={@expanded}
          new_event_ids={@new_event_ids}
        />
      <% end %>
    <% end %>
    """
  end
end
