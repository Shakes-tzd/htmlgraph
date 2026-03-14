defmodule HtmlgraphDashboard.EventPoller do
  @moduledoc """
  Polls the HtmlGraph SQLite database for new events and broadcasts
  them via Phoenix PubSub for live updates.

  Checks every 1 second for new events since last poll.
  """
  use GenServer

  alias HtmlgraphDashboard.Repo

  @poll_interval_ms 1_000
  @topic "activity_feed"

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc "Subscribe to live event updates."
  def subscribe do
    Phoenix.PubSub.subscribe(HtmlgraphDashboard.PubSub, @topic)
  end

  @impl true
  def init(_opts) do
    state = %{
      last_event_id: nil,
      last_timestamp: nil
    }

    schedule_poll()
    {:ok, state}
  end

  @impl true
  def handle_info(:poll, state) do
    new_state = poll_new_events(state)
    schedule_poll()
    {:noreply, new_state}
  end

  defp schedule_poll do
    Process.send_after(self(), :poll, @poll_interval_ms)
  end

  defp poll_new_events(%{last_timestamp: nil} = state) do
    # First poll — just record the latest timestamp, don't broadcast history
    case Repo.query("SELECT timestamp FROM agent_events ORDER BY timestamp DESC LIMIT 1") do
      {:ok, [[ts]]} ->
        %{state | last_timestamp: ts}

      _ ->
        state
    end
  end

  defp poll_new_events(%{last_timestamp: last_ts} = state) do
    sql = """
    SELECT event_id, tool_name, event_type, timestamp, input_summary,
           output_summary, session_id, agent_id, parent_event_id,
           subagent_type, model, status, cost_tokens,
           execution_duration_seconds, feature_id, context
    FROM agent_events
    WHERE timestamp > ?
    ORDER BY timestamp ASC
    LIMIT 100
    """

    case Repo.query_maps(sql, [last_ts]) do
      {:ok, []} ->
        state

      {:ok, events} ->
        Enum.each(events, fn event ->
          Phoenix.PubSub.broadcast(
            HtmlgraphDashboard.PubSub,
            @topic,
            {:new_event, event}
          )
        end)

        latest = List.last(events)
        %{state | last_timestamp: latest["timestamp"]}

      {:error, _reason} ->
        state
    end
  end
end
