#!/bin/bash
# Test script to verify spawner event broadcasting with logging

echo "=== Testing Spawner Event Broadcasting ==="
echo ""
echo "Instructions:"
echo "1. Open dashboard in browser: http://localhost:8888"
echo "2. Open browser console (F12)"
echo "3. Watch for WebSocket logs"
echo "4. Press ENTER to insert test event"
echo ""
read -p "Press ENTER when dashboard is ready..."

# Insert test event
echo ""
echo "Inserting test spawner_start event..."
sqlite3 /Users/shakes/DevProjects/htmlgraph/.htmlgraph/index.sqlite << EOF
INSERT INTO live_events (event_type, event_data, spawner_type, parent_event_id, session_id)
VALUES (
    'spawner_start',
    '{"spawner_type": "gemini", "prompt_preview": "TEST BROADCAST", "status": "started", "timestamp": "2026-01-10T12:00:00Z"}',
    'gemini',
    'test-parent-event-123',
    'test-session-456'
);
EOF

echo "✅ Test event inserted!"
echo ""
echo "Expected logs:"
echo ""
echo "SERVER (terminal running 'uv run htmlgraph serve'):"
echo "  [WebSocket] Found 1 pending live_events to broadcast"
echo "  [WebSocket] Sending spawner_event: id=X, type=spawner_start, spawner=gemini"
echo "  [WebSocket] Marking 1 events as broadcast: [X]"
echo ""
echo "CLIENT (browser console):"
echo "  [WebSocket] Received message type: spawner_event"
echo "  [WebSocket] spawner_event received: spawner_start gemini handler exists: true"
echo "  [SpawnerEvent] spawner_start gemini {...}"
echo ""
echo "Check both server terminal and browser console for these logs."
