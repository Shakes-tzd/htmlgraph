defmodule HtmlgraphDashboardWeb.CoreComponents do
  @moduledoc """
  Minimal core components for the dashboard.
  """
  use Phoenix.Component

  def flash_group(assigns) do
    ~H"""
    <div class="flash-group">
      <p :if={Phoenix.Flash.get(@flash, :info)} class="flash-info">
        <%= Phoenix.Flash.get(@flash, :info) %>
      </p>
      <p :if={Phoenix.Flash.get(@flash, :error)} class="flash-error">
        <%= Phoenix.Flash.get(@flash, :error) %>
      </p>
    </div>
    """
  end
end
