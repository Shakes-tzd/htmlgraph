import Config

config :htmlgraph_dashboard, HtmlgraphDashboardWeb.Endpoint,
  url: [host: "localhost"],
  render_errors: [
    formats: [html: HtmlgraphDashboardWeb.ErrorHTML],
    layout: false
  ],
  pubsub_server: HtmlgraphDashboard.PubSub,
  live_view: [signing_salt: "htmlgraph_lv"]

config :htmlgraph_dashboard,
  db_path: System.get_env("HTMLGRAPH_DB_PATH") || "../../.htmlgraph/htmlgraph.db"

config :logger, :console,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]

config :phoenix, :json_library, Jason

import_config "#{config_env()}.exs"
