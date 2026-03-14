defmodule HtmlgraphDashboard.EventPoller do
  @moduledoc """
  Polls the HtmlGraph SQLite database for new events and broadcasts
  them via Phoenix PubSub for live updates.

  Checks every 1 second for new events since last poll.
  """
  use GenServer

  alias HtmlgraphDashboard.Repo

  @poll_interval_ms 1_000
  @sync_poll_interval 3
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
      last_timestamp: nil,
      last_sync_signature: nil,
      poll_count: 0
    }

    schedule_poll()
    {:ok, state}
  end

  @impl true
  def handle_info(:poll, state) do
    new_state = poll_new_events(state)
    new_state = maybe_poll_sync_status(new_state)
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

  defp maybe_poll_sync_status(%{poll_count: count} = state) do
    state = %{state | poll_count: count + 1}

    if rem(state.poll_count, @sync_poll_interval) == 0 do
      poll_sync_status(state)
    else
      state
    end
  end

  defp poll_sync_status(state) do
    with {:ok, [[max_seq]]} <-
           Repo.query("SELECT COALESCE(MAX(seq), 0) FROM oplog"),
         {:ok, [[conflicts]]} <-
           Repo.query(
             "SELECT COUNT(*) FROM sync_conflicts WHERE status != 'resolved'"
           ),
         {:ok, [[consumer_count, max_lag, min_acked]]} <-
           Repo.query("""
           SELECT COUNT(*),
                  COALESCE(MAX(last_seen_seq - last_acked_seq), 0),
                  COALESCE(MIN(last_acked_seq), 0)
           FROM sync_cursors
           """) do
      pipeline_lag =
        if consumer_count > 0, do: max(max_seq - min_acked, 0), else: 0

      signature = {max_seq, conflicts, max_lag, consumer_count, pipeline_lag}

      if signature != state.last_sync_signature do
        Phoenix.PubSub.broadcast(
          HtmlgraphDashboard.PubSub,
          @topic,
          {:sync_status,
           %{
             server_max_seq: max_seq,
             pending_conflicts: conflicts,
             max_consumer_lag: max_lag,
             consumer_count: consumer_count,
             pipeline_lag: pipeline_lag
           }}
        )

        %{state | last_sync_signature: signature}
      else
        state
      end
    else
      _ -> state
    end
  end
end
