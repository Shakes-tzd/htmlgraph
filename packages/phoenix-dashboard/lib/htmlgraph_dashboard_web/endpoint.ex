defmodule HtmlgraphDashboardWeb.Endpoint do
  use Phoenix.Endpoint, otp_app: :htmlgraph_dashboard

  @session_options [
    store: :cookie,
    key: "_htmlgraph_dashboard_key",
    signing_salt: "htmlgraph_salt",
    same_site: "Lax"
  ]

  socket "/live", Phoenix.LiveView.Socket,
    websocket: [connect_info: [session: @session_options]]

  plug Plug.Static,
    at: "/",
    from: :htmlgraph_dashboard,
    gzip: false,
    only: HtmlgraphDashboardWeb.static_paths()

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]

  plug Plug.Parsers,
    parsers: [:urlencoded, :multipart, :json],
    pass: ["*/*"],
    json_decoder: Phoenix.json_library()

  plug Plug.MethodOverride
  plug Plug.Head
  plug Plug.Session, @session_options
  plug HtmlgraphDashboardWeb.Router
end
