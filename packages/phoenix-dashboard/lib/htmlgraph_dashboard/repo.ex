defmodule HtmlgraphDashboard.Repo do
  @moduledoc """
  Direct SQLite3 reader for the HtmlGraph database.

  Read-only access to the existing .htmlgraph/htmlgraph.db file.
  Uses exqlite for lightweight SQLite3 connectivity.
  """

  @doc """
  Returns the configured database path, resolved relative to the app root.
  """
  def db_path do
    path = Application.get_env(:htmlgraph_dashboard, :db_path, "../../.htmlgraph/htmlgraph.db")

    if Path.type(path) == :relative do
      Path.join(Application.app_dir(:htmlgraph_dashboard, ""), path)
      |> Path.expand()
    else
      path
    end
  end

  @doc """
  Execute a read-only query against the HtmlGraph database.
  Returns {:ok, rows} or {:error, reason}.
  """
  def query(sql, params \\ []) do
    path = db_path()

    case Exqlite.Sqlite3.open(path, [:readonly]) do
      {:ok, conn} ->
        try do
          execute_query(conn, sql, params)
        after
          Exqlite.Sqlite3.close(conn)
        end

      {:error, reason} ->
        {:error, {:open_failed, reason, path}}
    end
  end

  @doc """
  Execute a query and return rows as maps with column name keys.
  """
  def query_maps(sql, params \\ []) do
    path = db_path()

    case Exqlite.Sqlite3.open(path, [:readonly]) do
      {:ok, conn} ->
        try do
          case Exqlite.Sqlite3.prepare(conn, sql) do
            {:ok, stmt} ->
              bind_params(conn, stmt, params)
              rows = collect_rows(conn, stmt)
              columns = get_columns(conn, stmt)
              Exqlite.Sqlite3.release(conn, stmt)

              maps =
                Enum.map(rows, fn row ->
                  columns
                  |> Enum.zip(row)
                  |> Map.new()
                end)

              {:ok, maps}

            {:error, reason} ->
              {:error, reason}
          end
        after
          Exqlite.Sqlite3.close(conn)
        end

      {:error, reason} ->
        {:error, {:open_failed, reason, path}}
    end
  end

  defp execute_query(conn, sql, params) do
    case Exqlite.Sqlite3.prepare(conn, sql) do
      {:ok, stmt} ->
        bind_params(conn, stmt, params)
        rows = collect_rows(conn, stmt)
        Exqlite.Sqlite3.release(conn, stmt)
        {:ok, rows}

      {:error, reason} ->
        {:error, reason}
    end
  end

  defp bind_params(_conn, _stmt, []), do: :ok

  defp bind_params(conn, stmt, params) do
    Exqlite.Sqlite3.bind(conn, stmt, params)
  end

  defp collect_rows(conn, stmt) do
    collect_rows(conn, stmt, [])
  end

  defp collect_rows(conn, stmt, acc) do
    case Exqlite.Sqlite3.step(conn, stmt) do
      {:row, row} -> collect_rows(conn, stmt, [row | acc])
      :done -> Enum.reverse(acc)
      {:error, _reason} -> Enum.reverse(acc)
    end
  end

  defp get_columns(conn, stmt) do
    count = Exqlite.Sqlite3.column_count(conn, stmt)

    Enum.map(0..(count - 1), fn i ->
      {:ok, name} = Exqlite.Sqlite3.column_name(conn, stmt, i)
      name
    end)
  end
end
