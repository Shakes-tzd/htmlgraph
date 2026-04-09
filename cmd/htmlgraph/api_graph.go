package main

import (
	"database/sql"
	"net/http"
)

// graphNode represents a work item node in the graph response.
type graphNode struct {
	ID     string `json:"id"`
	Type   string `json:"type"`
	Title  string `json:"title"`
	Status string `json:"status"`
	Edges  int    `json:"edges"`
}

// graphEdge represents a directed edge between two nodes.
type graphEdge struct {
	Source string `json:"source"`
	Target string `json:"target"`
	Type   string `json:"type"`
}

// graphData is the full response shape for /api/graph.
type graphData struct {
	Nodes []graphNode `json:"nodes"`
	Edges []graphEdge `json:"edges"`
}

// graphAPIHandler returns a force-directed graph payload for the dashboard.
// By default it filters to nodes that have at least one edge; pass ?all=true
// to include orphan nodes as well.
func graphAPIHandler(database *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		includeAll := r.URL.Query().Get("all") == "true"

		// Load all nodes with their track_id for implicit edge derivation.
		nodes, trackIDs, err := loadGraphNodes(database)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Collect explicit edges from graph_edges table.
		edges, err := loadGraphEdges(database)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Build known-node set to avoid dangling edge references.
		nodeSet := make(map[string]struct{}, len(nodes))
		for _, n := range nodes {
			nodeSet[n.ID] = struct{}{}
		}

		// Derive implicit part_of edges from track_id column.
		for i, n := range nodes {
			tid := trackIDs[i]
			if tid == "" {
				continue
			}
			if _, ok := nodeSet[tid]; !ok {
				continue // target track not in node set
			}
			edges = append(edges, graphEdge{
				Source: n.ID,
				Target: tid,
				Type:   "part_of",
			})
		}

		// Deduplicate edges (explicit DB edges may duplicate implicit ones).
		edges = deduplicateEdges(edges)

		// Build edge-count index.
		edgeCounts := make(map[string]int, len(nodes))
		for _, e := range edges {
			edgeCounts[e.Source]++
			edgeCounts[e.Target]++
		}

		// Annotate nodes with their edge counts.
		for i := range nodes {
			nodes[i].Edges = edgeCounts[nodes[i].ID]
		}

		// Filter orphans unless ?all=true.
		if !includeAll {
			filtered := make([]graphNode, 0, len(nodes))
			for _, n := range nodes {
				if n.Edges > 0 {
					filtered = append(filtered, n)
				}
			}
			nodes = filtered

			// Rebuild node set after filtering.
			nodeSet = make(map[string]struct{}, len(nodes))
			for _, n := range nodes {
				nodeSet[n.ID] = struct{}{}
			}

			// Drop edges whose endpoints are no longer present.
			filteredEdges := make([]graphEdge, 0, len(edges))
			for _, e := range edges {
				if _, ok := nodeSet[e.Source]; !ok {
					continue
				}
				if _, ok := nodeSet[e.Target]; !ok {
					continue
				}
				filteredEdges = append(filteredEdges, e)
			}
			edges = filteredEdges
		}

		if nodes == nil {
			nodes = []graphNode{}
		}
		if edges == nil {
			edges = []graphEdge{}
		}

		respondJSON(w, graphData{Nodes: nodes, Edges: edges})
	}
}

// loadGraphNodes fetches every feature/bug/spike/track row from features
// and returns the nodes alongside a parallel slice of track IDs for implicit
// edge derivation. The two slices share the same indices.
func loadGraphNodes(database *sql.DB) ([]graphNode, []string, error) {
	rows, err := database.Query(`
		SELECT id, COALESCE(type,'feature'), title, COALESCE(status,'todo'),
		       COALESCE(track_id,'')
		FROM features
		ORDER BY created_at DESC`)
	if err != nil {
		return nil, nil, err
	}
	defer rows.Close()

	var nodes []graphNode
	var trackIDs []string
	for rows.Next() {
		var n graphNode
		var tid string
		if err := rows.Scan(&n.ID, &n.Type, &n.Title, &n.Status, &tid); err != nil {
			continue
		}
		nodes = append(nodes, n)
		trackIDs = append(trackIDs, tid)
	}
	return nodes, trackIDs, rows.Err()
}

// loadGraphEdges fetches all rows from graph_edges.
func loadGraphEdges(database *sql.DB) ([]graphEdge, error) {
	rows, err := database.Query(`
		SELECT from_node_id, to_node_id, relationship_type
		FROM graph_edges`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var edges []graphEdge
	for rows.Next() {
		var e graphEdge
		if err := rows.Scan(&e.Source, &e.Target, &e.Type); err != nil {
			continue
		}
		edges = append(edges, e)
	}
	return edges, rows.Err()
}

// deduplicateEdges removes duplicate (source, target, type) triples.
func deduplicateEdges(edges []graphEdge) []graphEdge {
	seen := make(map[string]struct{}, len(edges))
	result := make([]graphEdge, 0, len(edges))
	for _, e := range edges {
		key := e.Source + "|" + e.Target + "|" + e.Type
		if _, exists := seen[key]; exists {
			continue
		}
		seen[key] = struct{}{}
		result = append(result, e)
	}
	return result
}
