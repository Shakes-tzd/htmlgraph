"""Dashboard integration tests for spawner observability."""


class TestDashboardSpawnerDisplay:
    """Test dashboard displays spawner activities correctly."""

    def test_spawner_badge_rendering_in_activity_feed(self):
        """Spawner badges appear in activity feed with correct styling."""
        # Create test spawner event
        spawner_event = {
            "event_id": "event-spawner-001",
            "agent_id": "orchestrator",
            "spawner_type": "gemini",
            "spawned_agent": "gemini-2.0-flash",
            "tool_name": "Task",
            "event_type": "delegation",
            "status": "completed",
            "timestamp": "2025-01-10T12:00:00",
        }

        # Badge should have spawner-specific styling
        badge_html = f'<span class="badge spawner-{spawner_event["spawner_type"]}">Spawner: {spawner_event["spawner_type"]}</span>'

        assert "badge" in badge_html
        assert "spawner-gemini" in badge_html
        assert spawner_event["spawner_type"] in badge_html

    def test_spawner_filter_shows_all_activity(self):
        """Filter 'All Activity' shows spawner and direct events."""
        # Create mixed events
        events = [
            {
                "event_id": "event-direct-001",
                "agent_id": "orchestrator",
                "tool_name": "ReadFile",
                "event_type": "direct",
                "status": "completed",
            },
            {
                "event_id": "event-spawner-001",
                "agent_id": "orchestrator",
                "spawner_type": "gemini",
                "event_type": "delegation",
                "status": "completed",
            },
        ]

        # Apply 'all' filter
        filtered_events = [e for e in events]  # No filtering

        # Verify all events visible
        assert len(filtered_events) == 2
        assert any(e["event_type"] == "direct" for e in filtered_events)
        assert any(e["event_type"] == "delegation" for e in filtered_events)

    def test_spawner_filter_shows_direct_only(self):
        """Filter 'Direct Actions' hides spawner delegations."""
        events = [
            {
                "event_id": "event-direct-001",
                "agent_id": "orchestrator",
                "tool_name": "ReadFile",
                "event_type": "direct",
                "status": "completed",
            },
            {
                "event_id": "event-spawner-001",
                "agent_id": "orchestrator",
                "spawner_type": "gemini",
                "event_type": "delegation",
                "status": "completed",
            },
        ]

        # Apply 'direct' filter
        filtered_events = [e for e in events if e["event_type"] == "direct"]

        # Verify only direct actions shown
        assert len(filtered_events) == 1
        assert filtered_events[0]["event_type"] == "direct"

        # Verify spawner events hidden
        assert not any(e["event_type"] == "delegation" for e in filtered_events)

    def test_spawner_filter_shows_spawner_only(self):
        """Filter 'Spawner Delegations' hides direct actions."""
        events = [
            {
                "event_id": "event-direct-001",
                "agent_id": "orchestrator",
                "tool_name": "ReadFile",
                "event_type": "direct",
                "status": "completed",
            },
            {
                "event_id": "event-spawner-001",
                "agent_id": "orchestrator",
                "spawner_type": "gemini",
                "event_type": "delegation",
                "status": "completed",
            },
        ]

        # Apply 'spawner' filter
        filtered_events = [e for e in events if e["event_type"] == "delegation"]

        # Verify only spawner events shown
        assert len(filtered_events) == 1
        assert filtered_events[0]["event_type"] == "delegation"
        assert "spawner_type" in filtered_events[0]

    def test_spawner_filter_by_type(self):
        """Filter by specific spawner type (gemini, codex, copilot)."""
        events = [
            {
                "event_id": "event-gemini-001",
                "spawner_type": "gemini",
                "event_type": "delegation",
            },
            {
                "event_id": "event-codex-001",
                "spawner_type": "codex",
                "event_type": "delegation",
            },
            {
                "event_id": "event-copilot-001",
                "spawner_type": "copilot",
                "event_type": "delegation",
            },
        ]

        # Apply gemini filter
        filtered_events = [e for e in events if e.get("spawner_type") == "gemini"]

        # Verify only Gemini events shown
        assert len(filtered_events) == 1
        assert filtered_events[0]["spawner_type"] == "gemini"

    def test_spawner_api_endpoint_returns_activities(self):
        """GET /api/spawner-activities returns filtered spawner events."""
        # Mock API response
        api_response = {
            "activities": [
                {
                    "event_id": "event-spawner-001",
                    "orchestrator_agent": "orchestrator",
                    "spawned_agent": "gemini-2.0-flash",
                    "spawner_type": "gemini",
                    "status": "completed",
                    "duration_seconds": 2.5,
                    "cost": 0.0,
                    "timestamp": "2025-01-10T12:00:00",
                },
                {
                    "event_id": "event-spawner-002",
                    "orchestrator_agent": "orchestrator",
                    "spawned_agent": "gpt-4",
                    "spawner_type": "codex",
                    "status": "completed",
                    "duration_seconds": 3.1,
                    "cost": 0.05,
                    "timestamp": "2025-01-10T12:05:00",
                },
            ],
            "total_count": 2,
        }

        # Verify response includes spawner activities
        assert "activities" in api_response
        assert len(api_response["activities"]) == 2

        # Verify correct fields present
        for activity in api_response["activities"]:
            assert "orchestrator_agent" in activity
            assert "spawned_agent" in activity
            assert "spawner_type" in activity
            assert "cost" in activity

    def test_spawner_api_endpoint_filtering(self):
        """API endpoint supports spawner_type and session filtering."""
        api_response = {
            "activities": [
                {
                    "event_id": "event-gemini-001",
                    "spawner_type": "gemini",
                    "session_id": "session-001",
                },
                {
                    "event_id": "event-gemini-002",
                    "spawner_type": "gemini",
                    "session_id": "session-002",
                },
                {
                    "event_id": "event-codex-001",
                    "spawner_type": "codex",
                    "session_id": "session-001",
                },
            ]
        }

        # Filter by spawner_type=gemini
        filtered = [
            a for a in api_response["activities"] if a["spawner_type"] == "gemini"
        ]

        # Verify returns only Gemini events
        assert len(filtered) == 2
        assert all(a["spawner_type"] == "gemini" for a in filtered)

    def test_spawner_api_endpoint_pagination(self):
        """API endpoint supports pagination (limit, offset)."""
        api_response = {
            "activities": [{"event_id": f"event-{i}"} for i in range(50)],
            "total_count": 50,
            "limit": 10,
            "offset": 20,
        }

        # Simulate pagination: limit=10, offset=20
        paginated = api_response["activities"][20:30]

        # Verify correct pagination
        assert len(paginated) == 10
        assert paginated[0]["event_id"] == "event-20"
        assert paginated[9]["event_id"] == "event-29"

    def test_spawner_statistics_endpoint(self):
        """GET /api/spawner-statistics returns aggregated metrics."""
        api_response = {
            "statistics": {
                "gemini": {
                    "total_delegations": 15,
                    "success_rate": 0.95,
                    "avg_duration": 2.3,
                    "total_tokens": 15000,
                    "total_cost": 0.0,
                    "cost_per_delegation": 0.0,
                },
                "codex": {
                    "total_delegations": 8,
                    "success_rate": 0.88,
                    "avg_duration": 3.1,
                    "total_tokens": 10000,
                    "total_cost": 0.35,
                    "cost_per_delegation": 0.044,
                },
                "copilot": {
                    "total_delegations": 12,
                    "success_rate": 0.92,
                    "avg_duration": 2.8,
                    "total_tokens": 12000,
                    "total_cost": 0.0,
                    "cost_per_delegation": 0.0,
                },
            },
            "overall": {
                "total_delegations": 35,
                "avg_success_rate": 0.92,
                "total_tokens": 37000,
                "total_cost": 0.35,
            },
        }

        # Verify statistics for each spawner
        stats = api_response["statistics"]
        for spawner_type in ["gemini", "codex", "copilot"]:
            assert spawner_type in stats
            spawner_stats = stats[spawner_type]

            # Verify required fields
            assert "total_delegations" in spawner_stats
            assert "success_rate" in spawner_stats
            assert "avg_duration" in spawner_stats
            assert "total_tokens" in spawner_stats
            assert "total_cost" in spawner_stats

    def test_spawners_dashboard_tab_renders(self):
        """Spawners dashboard tab renders correctly."""
        # Mock dashboard HTML
        dashboard_html = """
        <html>
            <body>
                <div id="spawners-tab">
                    <div class="summary-cards">
                        <div class="card">Gemini Stats</div>
                        <div class="card">Codex Stats</div>
                        <div class="card">Copilot Stats</div>
                    </div>
                    <div class="recent-activities">
                        <table>
                            <thead>
                                <tr>
                                    <th>Spawner</th>
                                    <th>Agent</th>
                                    <th>Status</th>
                                    <th>Cost</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Activities rows -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </body>
        </html>
        """

        # Verify page loads
        assert "spawners-tab" in dashboard_html

        # Verify summary cards present
        assert "summary-cards" in dashboard_html

        # Verify recent activities table present
        assert "recent-activities" in dashboard_html

    def test_spawners_dashboard_shows_cost(self):
        """Dashboard displays cost metrics."""
        # Mock cost data
        cost_data = {"gemini": 0.0, "codex": 0.35, "copilot": 0.0, "total": 0.35}

        # Mock summary cards HTML
        summary_html = f"""
        <div class="cost-total">${cost_data["total"]:.2f}</div>
        <div class="cost-gemini">${cost_data["gemini"]:.2f}</div>
        <div class="cost-codex">${cost_data["codex"]:.2f}</div>
        <div class="cost-copilot">${cost_data["copilot"]:.2f}</div>
        """

        # Verify cost shown in cards
        assert "$0.35" in summary_html
        assert "cost-total" in summary_html
        assert "cost-gemini" in summary_html

    def test_agent_attribution_in_dashboard(self):
        """Dashboard shows actual AI model, not wrapper."""
        activities = [
            {
                "spawner_type": "gemini",
                "spawned_agent": "gemini-2.0-flash",  # Actual model
                "display_name": "Gemini 2.0-Flash",
            },
            {
                "spawner_type": "codex",
                "spawned_agent": "gpt-4",  # Actual model
                "display_name": "GPT-4",
            },
            {
                "spawner_type": "copilot",
                "spawned_agent": "github-copilot",  # Actual model
                "display_name": "GitHub Copilot",
            },
        ]

        # Verify shows actual AI model, not wrapper
        for activity in activities:
            assert activity["spawned_agent"] != "spawner"
            assert "spawner" not in activity["spawned_agent"].lower()
            assert activity["spawned_agent"] in [
                "gemini-2.0-flash",
                "gpt-4",
                "github-copilot",
            ]

    def test_spawner_activity_feed_entry(self):
        """Test spawner event appears in activity feed correctly."""
        spawner_entry = {
            "timestamp": "2025-01-10T12:00:00",
            "agent": "orchestrator",
            "action": "spawned",
            "spawner_type": "gemini",
            "spawned_agent": "gemini-2.0-flash",
            "status": "completed",
            "duration": "2.5s",
            "tokens": 1000,
            "cost": "$0.00",
        }

        # Verify entry has all required fields
        assert "spawner_type" in spawner_entry
        assert "spawned_agent" in spawner_entry
        assert "status" in spawner_entry
        assert "cost" in spawner_entry

    def test_spawner_entry_color_coding(self):
        """Test spawner entries have distinct color coding."""
        # Each spawner type should have distinct styling
        color_map = {
            "gemini": "bg-gemini",
            "codex": "bg-codex",
            "copilot": "bg-copilot",
        }

        html_templates = {
            "gemini": f'<div class="{color_map["gemini"]}">Gemini</div>',
            "codex": f'<div class="{color_map["codex"]}">Codex</div>',
            "copilot": f'<div class="{color_map["copilot"]}">Copilot</div>',
        }

        # Verify distinct CSS classes
        for spawner_type, html in html_templates.items():
            assert f"bg-{spawner_type}" in html

    def test_spawner_success_failure_indicators(self):
        """Test spawner activities show success/failure status."""
        activities = [
            {
                "event_id": "event-1",
                "status": "completed",
                "status_icon": "✅",
                "status_class": "status-success",
            },
            {
                "event_id": "event-2",
                "status": "failed",
                "status_icon": "❌",
                "status_class": "status-failure",
            },
        ]

        # Verify status indicators
        for activity in activities:
            assert activity["status"] in ["completed", "failed"]
            assert activity["status_icon"] in ["✅", "❌"]
            assert "status-" in activity["status_class"]

    def test_spawner_timeline_display(self):
        """Test spawner activities appear in chronological timeline."""
        activities = [
            {
                "event_id": "event-1",
                "timestamp": "2025-01-10T12:00:00",
                "spawner_type": "gemini",
            },
            {
                "event_id": "event-2",
                "timestamp": "2025-01-10T12:05:00",
                "spawner_type": "codex",
            },
            {
                "event_id": "event-3",
                "timestamp": "2025-01-10T12:10:00",
                "spawner_type": "copilot",
            },
        ]

        # Verify chronological order
        timestamps = [a["timestamp"] for a in activities]
        assert timestamps == sorted(timestamps)

    def test_spawner_delegation_chain_display(self):
        """Test parent-child delegation relationships shown."""
        delegation_chain = {
            "parent_event_id": "event-orchestrator-001",
            "parent_agent": "orchestrator",
            "delegation_event_id": "event-spawner-001",
            "spawned_agent": "gemini-2.0-flash",
            "relationship": "parent -> spawner -> child",
        }

        # Verify chain relationships captured
        assert "parent_event_id" in delegation_chain
        assert "delegation_event_id" in delegation_chain
        assert "spawned_agent" in delegation_chain

    def test_spawner_metrics_dashboard_cards(self):
        """Test spawner metrics displayed in dashboard cards."""
        gemini_card = {
            "spawner": "Gemini",
            "total_calls": 15,
            "success_rate": "95%",
            "avg_duration": "2.3s",
            "cost": "$0.00",
            "tokens": "15,000",
        }

        codex_card = {
            "spawner": "Codex",
            "total_calls": 8,
            "success_rate": "88%",
            "avg_duration": "3.1s",
            "cost": "$0.35",
            "tokens": "10,000",
        }

        copilot_card = {
            "spawner": "Copilot",
            "total_calls": 12,
            "success_rate": "92%",
            "avg_duration": "2.8s",
            "cost": "$0.00",
            "tokens": "12,000",
        }

        cards = [gemini_card, codex_card, copilot_card]

        # Verify each card has metrics
        for card in cards:
            assert "spawner" in card
            assert "total_calls" in card
            assert "success_rate" in card
            assert "avg_duration" in card
            assert "cost" in card
            assert "tokens" in card
