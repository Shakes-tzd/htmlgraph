defmodule HtmlgraphDashboard.Activity do
  @moduledoc """
  Queries and structures the activity feed data from the HtmlGraph database.

  Builds a multi-level nested tree:
    Session → UserQuery (conversation turn) → Tool events → Subagent events
  """

  alias HtmlgraphDashboard.Repo

  @max_depth 4

  @doc """
  Fetch recent conversation turns with nested children, grouped by session.
  Returns a list of session groups, each containing conversation turns.
  """
  def list_activity_feed(opts \\ []) do
    limit = Keyword.get(opts, :limit, 50)
    session_id = Keyword.get(opts, :session_id, nil)
    agent_id = Keyword.get(opts, :agent_id, nil)

    # Fetch UserQuery events (conversation turns) — these are the top-level entries
    user_queries = fetch_user_queries(limit, session_id, agent_id)

    # For each UserQuery, recursively fetch children
    turns =
      Enum.map(user_queries, fn uq ->
        children = fetch_children(uq["event_id"], 0)
        stats = compute_stats(children)

        work_item = if uq["feature_id"], do: fetch_feature(uq["feature_id"]), else: nil

        %{
          user_query: uq,
          children: children,
          stats: stats,
          work_item: work_item
        }
      end)

    # Group by session
    turns
    |> Enum.group_by(fn t -> t.user_query["session_id"] end)
    |> Enum.map(fn {session_id, session_turns} ->
      session = fetch_session(session_id)

      %{
        session_id: session_id,
        session: session,
        turns: session_turns
      }
    end)
    |> Enum.sort_by(
      fn group ->
        case group.turns do
          [first | _] -> first.user_query["timestamp"]
          [] -> ""
        end
      end,
      :desc
    )
  end

  @doc """
  Fetch a single event by ID with its full subtree.
  """
  def get_event_tree(event_id) do
    sql = """
    SELECT event_id, tool_name, event_type, timestamp, input_summary,
           output_summary, session_id, agent_id, parent_event_id,
           subagent_type, model, status, cost_tokens,
           execution_duration_seconds, feature_id, context
    FROM agent_events
    WHERE event_id = ?
    """

    case Repo.query_maps(sql, [event_id]) do
      {:ok, [event]} ->
        children = fetch_children(event_id, 0)
        {:ok, Map.put(event, "children", children)}

      {:ok, []} ->
        {:error, :not_found}

      {:error, reason} ->
        {:error, reason}
    end
  end

  # --- Private ---

  defp fetch_user_queries(limit, nil, nil) do
    sql = """
    SELECT event_id, tool_name, event_type, timestamp, input_summary,
           output_summary, session_id, agent_id, parent_event_id,
           subagent_type, model, status, cost_tokens,
           execution_duration_seconds, feature_id, context
    FROM agent_events
    WHERE tool_name = 'UserQuery'
    ORDER BY timestamp DESC
    LIMIT ?
    """

    case Repo.query_maps(sql, [limit]) do
      {:ok, rows} -> rows
      {:error, _} -> []
    end
  end

  defp fetch_user_queries(limit, session_id, nil) when not is_nil(session_id) do
    sql = """
    SELECT event_id, tool_name, event_type, timestamp, input_summary,
           output_summary, session_id, agent_id, parent_event_id,
           subagent_type, model, status, cost_tokens,
           execution_duration_seconds, feature_id, context
    FROM agent_events
    WHERE tool_name = 'UserQuery' AND session_id = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """

    case Repo.query_maps(sql, [session_id, limit]) do
      {:ok, rows} -> rows
      {:error, _} -> []
    end
  end

  defp fetch_user_queries(limit, nil, agent_id) when not is_nil(agent_id) do
    sql = """
    SELECT DISTINCT uq.event_id, uq.tool_name, uq.event_type, uq.timestamp,
           uq.input_summary, uq.output_summary, uq.session_id, uq.agent_id,
           uq.parent_event_id, uq.subagent_type, uq.model, uq.status,
           uq.cost_tokens, uq.execution_duration_seconds, uq.feature_id,
           uq.context
    FROM agent_events uq
    WHERE uq.tool_name = 'UserQuery'
      AND EXISTS (
        SELECT 1 FROM agent_events child
        WHERE child.parent_event_id = uq.event_id
          AND child.agent_id LIKE '%' || ? || '%'
      )
    ORDER BY uq.timestamp DESC
    LIMIT ?
    """

    case Repo.query_maps(sql, [agent_id, limit]) do
      {:ok, rows} -> rows
      {:error, _} -> []
    end
  end

  defp fetch_user_queries(limit, session_id, agent_id) do
    sql = """
    SELECT DISTINCT uq.event_id, uq.tool_name, uq.event_type, uq.timestamp,
           uq.input_summary, uq.output_summary, uq.session_id, uq.agent_id,
           uq.parent_event_id, uq.subagent_type, uq.model, uq.status,
           uq.cost_tokens, uq.execution_duration_seconds, uq.feature_id,
           uq.context
    FROM agent_events uq
    WHERE uq.tool_name = 'UserQuery' AND uq.session_id = ?
      AND EXISTS (
        SELECT 1 FROM agent_events child
        WHERE child.parent_event_id = uq.event_id
          AND child.agent_id LIKE '%' || ? || '%'
      )
    ORDER BY uq.timestamp DESC
    LIMIT ?
    """

    case Repo.query_maps(sql, [session_id, agent_id, limit]) do
      {:ok, rows} -> rows
      {:error, _} -> []
    end
  end

  defp fetch_children(_parent_id, depth) when depth >= @max_depth, do: []

  defp fetch_children(parent_id, depth) do
    sql = """
    SELECT event_id, tool_name, event_type, timestamp, input_summary,
           output_summary, session_id, agent_id, parent_event_id,
           subagent_type, model, status, cost_tokens,
           execution_duration_seconds, feature_id, context
    FROM agent_events
    WHERE parent_event_id = ?
      AND NOT (tool_name = 'Agent' AND event_type != 'task_delegation')
    ORDER BY timestamp DESC
    """

    case Repo.query_maps(sql, [parent_id]) do
      {:ok, rows} ->
        Enum.map(rows, fn row ->
          grandchildren = fetch_children(row["event_id"], depth + 1)

          row
          |> Map.put("children", grandchildren)
          |> Map.put("depth", depth)
        end)

      {:error, _} ->
        []
    end
  end

  defp compute_stats(children) do
    flat = flatten_children(children)

    %{
      tool_count: length(flat),
      total_duration:
        flat
        |> Enum.map(fn c -> (c["execution_duration_seconds"] || 0) end)
        |> Enum.sum()
        |> Float.round(2),
      success_count: Enum.count(flat, fn c -> c["status"] in ["recorded", "success", "completed"] end),
      error_count: Enum.count(flat, fn c -> c["event_type"] == "error" end),
      models: flat |> Enum.map(fn c -> c["model"] end) |> Enum.reject(&is_nil/1) |> Enum.uniq(),
      total_tokens:
        flat
        |> Enum.map(fn c -> (c["cost_tokens"] || 0) end)
        |> Enum.sum()
    }
  end

  defp flatten_children(children) do
    Enum.flat_map(children, fn child ->
      [child | flatten_children(child["children"] || [])]
    end)
  end

  defp fetch_session(nil), do: nil

  defp fetch_session(session_id) do
    sql = """
    SELECT session_id, agent_assigned, status, created_at, completed_at,
           total_events, total_tokens_used, is_subagent, last_user_query,
           model
    FROM sessions
    WHERE session_id = ?
    """

    case Repo.query_maps(sql, [session_id]) do
      {:ok, [session]} -> session
      _ -> nil
    end
  end

  defp fetch_feature(nil), do: nil

  defp fetch_feature(feature_id) do
    sql = """
    SELECT id, type, title, status, priority
    FROM features
    WHERE id = ?
    """

    case Repo.query_maps(sql, [feature_id]) do
      {:ok, [feature]} -> feature
      _ -> nil
    end
  end
end
