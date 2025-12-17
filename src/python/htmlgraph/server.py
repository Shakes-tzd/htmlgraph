"""
HtmlGraph REST API Server.

Provides HTTP endpoints for CRUD operations on the graph database.
Uses only Python standard library (http.server) for zero dependencies.

Usage:
    from htmlgraph.server import serve
    serve(port=8080, directory=".htmlgraph")

Or via CLI:
    htmlgraph serve --port 8080
"""

import json
import re
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Node, Edge, Step
from htmlgraph.converter import node_to_dict, dict_to_node
from htmlgraph.analytics_index import AnalyticsIndex
from htmlgraph.event_log import JsonlEventLog


class HtmlGraphAPIHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with REST API support."""

    # Class-level config (set by serve())
    graph_dir: Path = Path(".htmlgraph")
    static_dir: Path = Path(".")
    graphs: dict[str, HtmlGraph] = {}
    analytics_db: AnalyticsIndex | None = None

    # Work item types (subfolders in .htmlgraph/)
    COLLECTIONS = ["features", "bugs", "spikes", "chores", "epics", "sessions", "agents"]

    def __init__(self, *args, **kwargs):
        # Set directory for static file serving
        self.directory = str(self.static_dir)
        super().__init__(*args, **kwargs)

    def _get_graph(self, collection: str) -> HtmlGraph:
        """Get or create graph for a collection."""
        if collection not in self.graphs:
            collection_dir = self.graph_dir / collection
            collection_dir.mkdir(parents=True, exist_ok=True)
            self.graphs[collection] = HtmlGraph(
                collection_dir,
                stylesheet_path="../styles.css",
                auto_load=True
            )
        return self.graphs[collection]

    def _send_json(self, data: Any, status: int = 200):
        """Send JSON response."""
        body = json.dumps(data, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int = 400):
        """Send JSON error response."""
        self._send_json({"error": message, "status": status}, status)

    def _read_body(self) -> dict:
        """Read and parse JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        return json.loads(body) if body else {}

    def _parse_path(self) -> tuple[str | None, str | None, str | None, dict]:
        """
        Parse request path into components.

        Returns: (api_prefix, collection, node_id, query_params)

        Examples:
            /api/features -> ("api", "features", None, {})
            /api/features/feat-001 -> ("api", "features", "feat-001", {})
            /api/query?status=todo -> ("api", "query", None, {"status": "todo"})
        """
        parsed = urllib.parse.urlparse(self.path)
        query_params = dict(urllib.parse.parse_qsl(parsed.query))

        parts = [p for p in parsed.path.split("/") if p]

        if not parts:
            return None, None, None, query_params

        if parts[0] != "api":
            return None, None, None, query_params

        collection = parts[1] if len(parts) > 1 else None
        node_id = parts[2] if len(parts) > 2 else None

        return "api", collection, node_id, query_params

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        api, collection, node_id, params = self._parse_path()

        # Not an API request - serve static files
        if api != "api":
            return super().do_GET()

        # GET /api/status - Overall status
        if collection == "status":
            return self._handle_status()

        # GET /api/query?selector=... - CSS selector query
        if collection == "query":
            return self._handle_query(params)

        # GET /api/analytics/... - Analytics endpoints backed by SQLite index
        if collection == "analytics":
            return self._handle_analytics(node_id, params)

        # GET /api/collections - List available collections
        if collection == "collections":
            return self._send_json({"collections": self.COLLECTIONS})

        # GET /api/{collection} - List all nodes in collection
        if collection in self.COLLECTIONS and not node_id:
            return self._handle_list(collection, params)

        # GET /api/{collection}/{id} - Get single node
        if collection in self.COLLECTIONS and node_id:
            return self._handle_get(collection, node_id)

        self._send_error_json(f"Unknown endpoint: {self.path}", 404)

    def do_POST(self):
        """Handle POST requests (create)."""
        api, collection, node_id, params = self._parse_path()

        if api != "api":
            self._send_error_json("API endpoint required", 400)
            return

        if collection not in self.COLLECTIONS:
            self._send_error_json(f"Unknown collection: {collection}", 404)
            return

        try:
            data = self._read_body()
            self._handle_create(collection, data)
        except json.JSONDecodeError as e:
            self._send_error_json(f"Invalid JSON: {e}", 400)
        except Exception as e:
            self._send_error_json(str(e), 500)

    def do_PUT(self):
        """Handle PUT requests (full update)."""
        api, collection, node_id, params = self._parse_path()

        if api != "api" or not node_id:
            self._send_error_json("PUT requires /api/{collection}/{id}", 400)
            return

        if collection not in self.COLLECTIONS:
            self._send_error_json(f"Unknown collection: {collection}", 404)
            return

        try:
            data = self._read_body()
            self._handle_update(collection, node_id, data, partial=False)
        except json.JSONDecodeError as e:
            self._send_error_json(f"Invalid JSON: {e}", 400)
        except Exception as e:
            self._send_error_json(str(e), 500)

    def do_PATCH(self):
        """Handle PATCH requests (partial update)."""
        api, collection, node_id, params = self._parse_path()

        if api != "api" or not node_id:
            self._send_error_json("PATCH requires /api/{collection}/{id}", 400)
            return

        if collection not in self.COLLECTIONS:
            self._send_error_json(f"Unknown collection: {collection}", 404)
            return

        try:
            data = self._read_body()
            self._handle_update(collection, node_id, data, partial=True)
        except json.JSONDecodeError as e:
            self._send_error_json(f"Invalid JSON: {e}", 400)
        except Exception as e:
            self._send_error_json(str(e), 500)

    def do_DELETE(self):
        """Handle DELETE requests."""
        api, collection, node_id, params = self._parse_path()

        if api != "api" or not node_id:
            self._send_error_json("DELETE requires /api/{collection}/{id}", 400)
            return

        if collection not in self.COLLECTIONS:
            self._send_error_json(f"Unknown collection: {collection}", 404)
            return

        self._handle_delete(collection, node_id)

    # =========================================================================
    # API Handlers
    # =========================================================================

    def _handle_status(self):
        """Return overall graph status."""
        status = {
            "collections": {},
            "total_nodes": 0,
            "by_status": {},
            "by_priority": {},
        }

        for collection in self.COLLECTIONS:
            graph = self._get_graph(collection)
            stats = graph.stats()
            status["collections"][collection] = stats["total"]
            status["total_nodes"] += stats["total"]

            for s, count in stats["by_status"].items():
                status["by_status"][s] = status["by_status"].get(s, 0) + count
            for p, count in stats["by_priority"].items():
                status["by_priority"][p] = status["by_priority"].get(p, 0) + count

        self._send_json(status)

    def _get_analytics(self) -> AnalyticsIndex:
        if self.analytics_db is None:
            self.analytics_db = AnalyticsIndex(self.graph_dir / "index.sqlite")
        return self.analytics_db

    def _handle_analytics(self, endpoint: str | None, params: dict):
        """
        Analytics endpoints.

        Backed by a rebuildable SQLite index at `.htmlgraph/index.sqlite`.
        If the index doesn't exist yet, we build it on-demand from `.htmlgraph/events/*.jsonl`.
        """
        if endpoint is None:
            return self._send_error_json("Specify an analytics endpoint (overview, features, session)", 400)

        db_path = self.graph_dir / "index.sqlite"
        if not db_path.exists():
            events_dir = self.graph_dir / "events"
            if not events_dir.exists() or not any(events_dir.glob("*.jsonl")):
                return self._send_error_json(
                    "Analytics index not found and no event logs present. Start tracking, or run: htmlgraph events export-sessions",
                    404,
                )

            try:
                log = JsonlEventLog(events_dir)
                index = AnalyticsIndex(db_path)
                events = (event for _, event in log.iter_events())
                index.rebuild_from_events(events)
            except Exception as e:
                return self._send_error_json(f"Failed to build analytics index: {e}", 500)

        analytics = self._get_analytics()

        since = params.get("since")
        until = params.get("until")

        if endpoint == "overview":
            return self._send_json(analytics.overview(since=since, until=until))

        if endpoint == "features":
            limit = int(params.get("limit", 50))
            return self._send_json({"features": analytics.top_features(since=since, until=until, limit=limit)})

        if endpoint == "session":
            session_id = params.get("id")
            if not session_id:
                return self._send_error_json("Missing required param: id", 400)
            limit = int(params.get("limit", 500))
            return self._send_json({"events": analytics.session_events(session_id=session_id, limit=limit)})

        if endpoint == "continuity":
            feature_id = params.get("feature_id") or params.get("feature")
            if not feature_id:
                return self._send_error_json("Missing required param: feature_id", 400)
            limit = int(params.get("limit", 200))
            return self._send_json({"sessions": analytics.feature_continuity(feature_id=feature_id, since=since, until=until, limit=limit)})

        if endpoint == "transitions":
            limit = int(params.get("limit", 50))
            feature_id = params.get("feature_id") or params.get("feature")
            return self._send_json({"transitions": analytics.top_tool_transitions(since=since, until=until, feature_id=feature_id, limit=limit)})

        return self._send_error_json(f"Unknown analytics endpoint: {endpoint}", 404)

    def _handle_query(self, params: dict):
        """Handle CSS selector query across collections."""
        selector = params.get("selector", "")
        collection = params.get("collection")  # Optional filter to single collection

        if not selector:
            # If no selector, return all nodes matching other params
            selector = self._build_selector_from_params(params)

        results = []
        collections = [collection] if collection in self.COLLECTIONS else self.COLLECTIONS

        for coll in collections:
            graph = self._get_graph(coll)
            matches = graph.query(selector) if selector else list(graph)
            for node in matches:
                node_data = node_to_dict(node)
                node_data["_collection"] = coll
                results.append(node_data)

        self._send_json({"count": len(results), "nodes": results})

    def _build_selector_from_params(self, params: dict) -> str:
        """Build CSS selector from query params."""
        parts = []
        for key in ["status", "priority", "type"]:
            if key in params:
                parts.append(f"[data-{key}='{params[key]}']")
        return "".join(parts)

    def _handle_list(self, collection: str, params: dict):
        """List all nodes in a collection."""
        graph = self._get_graph(collection)

        # Apply filters if provided
        nodes = list(graph)

        if "status" in params:
            nodes = [n for n in nodes if n.status == params["status"]]
        if "priority" in params:
            nodes = [n for n in nodes if n.priority == params["priority"]]
        if "type" in params:
            nodes = [n for n in nodes if n.type == params["type"]]

        # Sort options
        sort_by = params.get("sort", "updated")
        reverse = params.get("order", "desc") == "desc"

        if sort_by == "priority":
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            nodes.sort(key=lambda n: priority_order.get(n.priority, 99), reverse=not reverse)
        elif sort_by == "created":
            nodes.sort(key=lambda n: n.created, reverse=reverse)
        else:  # default: updated
            nodes.sort(key=lambda n: n.updated, reverse=reverse)

        # Pagination
        limit = int(params.get("limit", 100))
        offset = int(params.get("offset", 0))

        total = len(nodes)
        nodes = nodes[offset:offset + limit]

        self._send_json({
            "collection": collection,
            "total": total,
            "limit": limit,
            "offset": offset,
            "nodes": [node_to_dict(n) for n in nodes]
        })

    def _handle_get(self, collection: str, node_id: str):
        """Get a single node."""
        graph = self._get_graph(collection)
        node = graph.get(node_id)

        if not node:
            self._send_error_json(f"Node not found: {node_id}", 404)
            return

        data = node_to_dict(node)
        data["_collection"] = collection
        data["_context"] = node.to_context()  # Include lightweight context

        self._send_json(data)

    def _handle_create(self, collection: str, data: dict):
        """Create a new node."""
        # Generate ID if not provided
        if "id" not in data:
            prefix = collection[:-1] if collection.endswith("s") else collection
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            data["id"] = f"{prefix}-{timestamp}"

        # Set defaults based on collection
        if "type" not in data:
            type_map = {
                "features": "feature",
                "bugs": "bug",
                "spikes": "spike",
                "chores": "chore",
                "epics": "epic",
                "sessions": "session",
                "agents": "agent",
            }
            data["type"] = type_map.get(collection, "node")

        # Require title
        if "title" not in data:
            self._send_error_json("'title' is required", 400)
            return

        # Convert steps if provided as strings
        if "steps" in data and data["steps"]:
            if isinstance(data["steps"][0], str):
                data["steps"] = [{"description": s, "completed": False} for s in data["steps"]]

        try:
            node = dict_to_node(data)
            graph = self._get_graph(collection)
            graph.add(node)

            response = node_to_dict(node)
            response["_collection"] = collection
            response["_location"] = f"/api/{collection}/{node.id}"

            self._send_json(response, 201)
        except ValueError as e:
            self._send_error_json(str(e), 400)

    def _handle_update(self, collection: str, node_id: str, data: dict, partial: bool):
        """Update a node (full or partial)."""
        graph = self._get_graph(collection)
        existing = graph.get(node_id)

        if not existing:
            self._send_error_json(f"Node not found: {node_id}", 404)
            return

        if partial:
            # Merge with existing
            existing_data = node_to_dict(existing)
            existing_data.update(data)
            data = existing_data

        # Ensure ID matches
        data["id"] = node_id

        # Handle step completion shorthand: {"complete_step": 0}
        if "complete_step" in data:
            step_idx = data.pop("complete_step")
            if 0 <= step_idx < len(existing.steps):
                existing.complete_step(step_idx, data.get("agent"))
                graph.update(existing)
                self._send_json(node_to_dict(existing))
                return

        # Handle status transitions
        if "status" in data and data["status"] != existing.status:
            data["updated"] = datetime.now().isoformat()

        try:
            node = dict_to_node(data)
            graph.update(node)
            self._send_json(node_to_dict(node))
        except Exception as e:
            self._send_error_json(str(e), 400)

    def _handle_delete(self, collection: str, node_id: str):
        """Delete a node."""
        graph = self._get_graph(collection)

        if node_id not in graph:
            self._send_error_json(f"Node not found: {node_id}", 404)
            return

        graph.remove(node_id)
        self._send_json({"deleted": node_id, "collection": collection})

    def log_message(self, format: str, *args):
        """Custom log format."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def serve(
    port: int = 8080,
    graph_dir: str | Path = ".htmlgraph",
    static_dir: str | Path = ".",
    host: str = "localhost"
):
    """
    Start the HtmlGraph server.

    Args:
        port: Port to listen on
        graph_dir: Directory containing graph data (.htmlgraph/)
        static_dir: Directory for static files (index.html, etc.)
        host: Host to bind to
    """
    graph_dir = Path(graph_dir)
    static_dir = Path(static_dir)

    # Create graph directory structure
    graph_dir.mkdir(parents=True, exist_ok=True)
    for collection in HtmlGraphAPIHandler.COLLECTIONS:
        (graph_dir / collection).mkdir(exist_ok=True)

    # Copy default stylesheet if not present
    styles_dest = graph_dir / "styles.css"
    if not styles_dest.exists():
        styles_src = Path(__file__).parent / "styles.css"
        if styles_src.exists():
            styles_dest.write_text(styles_src.read_text())

    # Configure handler
    HtmlGraphAPIHandler.graph_dir = graph_dir
    HtmlGraphAPIHandler.static_dir = static_dir
    HtmlGraphAPIHandler.graphs = {}
    HtmlGraphAPIHandler.analytics_db = None

    server = HTTPServer((host, port), HtmlGraphAPIHandler)

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    HtmlGraph Server                          ║
╠══════════════════════════════════════════════════════════════╣
║  Dashboard:  http://{host}:{port}/
║  API:        http://{host}:{port}/api/
║  Graph Dir:  {graph_dir}
╚══════════════════════════════════════════════════════════════╝

API Endpoints:
  GET    /api/status              - Overall status
  GET    /api/collections         - List collections
  GET    /api/query?status=todo   - Query across collections
  GET    /api/analytics/overview  - Analytics overview (requires index)
  GET    /api/analytics/features  - Top features (requires index)
  GET    /api/analytics/continuity?feature_id=... - Feature continuity (requires index)
  GET    /api/analytics/transitions - Tool transitions (requires index)

  GET    /api/{{collection}}        - List nodes
  POST   /api/{{collection}}        - Create node
  GET    /api/{{collection}}/{{id}}    - Get node
  PUT    /api/{{collection}}/{{id}}    - Replace node
  PATCH  /api/{{collection}}/{{id}}    - Update node
  DELETE /api/{{collection}}/{{id}}    - Delete node

Collections: {', '.join(HtmlGraphAPIHandler.COLLECTIONS)}

Press Ctrl+C to stop.
""")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    serve()
