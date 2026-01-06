# HtmlGraph HTTP API Reference

REST API for HtmlGraph server. Use this when integrating HtmlGraph with external services or accessing the graph database over HTTP.

## Base URL

```
http://localhost:8080/api
```

## Starting the Server

```bash
# Via CLI
htmlgraph serve --port 8080

# Via Python
from htmlgraph import serve
serve(port=8080, directory=".htmlgraph")
```

## Response Format

All responses are JSON with consistent structure:

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2025-01-06T10:30:45.123Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Resource not found",
  "error_code": "NOT_FOUND",
  "timestamp": "2025-01-06T10:30:45.123Z"
}
```

## Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| 200 | OK | Successful request |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists or claim conflict |
| 500 | Server Error | Internal error |

---

## Endpoints

### `/api/status` - Server Status

**GET** `/api/status`

Get server status and basic information.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "running",
    "version": "0.24.1",
    "collections": {
      "features": 42,
      "bugs": 8,
      "spikes": 5,
      "chores": 12,
      "epics": 3,
      "sessions": 156,
      "agents": 12,
      "tracks": 4
    },
    "uptime_seconds": 3600,
    "timestamp": "2025-01-06T10:30:45.123Z"
  }
}
```

---

### `/api/features` - Feature Operations

**POST** `/api/features` - Create Feature

Create a new feature.

**Request Body:**
```json
{
  "title": "User Authentication System",
  "priority": "high",
  "status": "todo",
  "description": "Implement JWT-based auth",
  "steps": [
    "Design schema",
    "Implement API",
    "Add tests"
  ],
  "track": "auth",
  "agent": "claude"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "feat-abc123",
    "title": "User Authentication System",
    "type": "feature",
    "status": "todo",
    "priority": "high",
    "created_at": "2025-01-06T10:30:45.123Z",
    "updated_at": "2025-01-06T10:30:45.123Z",
    "steps": [...],
    "agent": "claude"
  }
}
```

**Parameters:**
- `title` (required, string): Feature title
- `priority` (optional, string): "low", "medium", "high", "critical" (default: "medium")
- `status` (optional, string): "todo", "in-progress", "blocked", "done" (default: "todo")
- `description` (optional, string): Feature description
- `steps` (optional, array): Implementation steps
- `track` (optional, string): Track identifier
- `agent` (optional, string): Agent identifier

---

**GET** `/api/features` - List Features

Retrieve features with optional filtering.

**Query Parameters:**
- `status` (optional): Filter by status
- `priority` (optional): Filter by priority
- `agent` (optional): Filter by assigned agent
- `track` (optional): Filter by track
- `limit` (optional): Max results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Request:**
```bash
GET /api/features?status=todo&priority=high&limit=50
```

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "feat-abc123",
        "title": "User Auth",
        "status": "todo",
        "priority": "high",
        ...
      }
    ],
    "total": 247,
    "limit": 50,
    "offset": 0
  }
}
```

---

**GET** `/api/features/{id}` - Get Feature

Retrieve a specific feature.

**Request:**
```bash
GET /api/features/feat-abc123
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "feat-abc123",
    "title": "User Authentication System",
    "type": "feature",
    "status": "todo",
    "priority": "high",
    "created_at": "2025-01-06T10:30:45.123Z",
    "updated_at": "2025-01-06T10:30:45.123Z",
    "steps": [
      {
        "description": "Design schema",
        "completed": false,
        "completed_at": null
      },
      {
        "description": "Implement API",
        "completed": false,
        "completed_at": null
      }
    ],
    "agent": "claude",
    "edges": {
      "blocks": ["feat-xyz789"],
      "blocked_by": ["feat-def456"]
    }
  }
}
```

---

**PUT** `/api/features/{id}` - Update Feature

Update a feature.

**Request Body:**
```json
{
  "status": "in-progress",
  "priority": "critical",
  "steps": [
    {
      "description": "Design schema",
      "completed": true,
      "completed_at": "2025-01-06T10:30:45.123Z"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "feat-abc123",
    "status": "in-progress",
    "priority": "critical",
    "updated_at": "2025-01-06T10:31:15.456Z",
    ...
  }
}
```

---

**DELETE** `/api/features/{id}` - Delete Feature

Delete a feature.

**Request:**
```bash
DELETE /api/features/feat-abc123
```

**Response:**
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "id": "feat-abc123"
  }
}
```

---

### `/api/bugs` - Bug Operations

Same interface as features. Endpoints:
- `POST /api/bugs` - Create bug
- `GET /api/bugs` - List bugs
- `GET /api/bugs/{id}` - Get bug
- `PUT /api/bugs/{id}` - Update bug
- `DELETE /api/bugs/{id}` - Delete bug

---

### `/api/spikes` - Spike Operations

Same interface as features. Endpoints:
- `POST /api/spikes` - Create spike
- `GET /api/spikes` - List spikes
- `GET /api/spikes/{id}` - Get spike
- `PUT /api/spikes/{id}` - Update spike
- `DELETE /api/spikes/{id}` - Delete spike

---

### `/api/chores` - Chore Operations

Same interface as features. Endpoints:
- `POST /api/chores` - Create chore
- `GET /api/chores` - List chores
- `GET /api/chores/{id}` - Get chore
- `PUT /api/chores/{id}` - Update chore
- `DELETE /api/chores/{id}` - Delete chore

---

### `/api/tasks` - Task Delegation

**POST** `/api/tasks` - Create Task Delegation

```json
{
  "prompt": "Implement user authentication",
  "agent": "coder",
  "task_id": "task-auth-001",
  "status": "pending",
  "priority": "high"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "task-auth-001",
    "status": "pending",
    "created_at": "2025-01-06T10:30:45.123Z",
    ...
  }
}
```

---

**GET** `/api/tasks` - List Task Delegations

**Query Parameters:**
- `status` (optional): "pending", "in-progress", "completed", "failed"
- `agent` (optional): Filter by assigned agent
- `limit` (optional): Max results

---

**GET** `/api/tasks/{task_id}` - Get Task

Retrieve specific task delegation with results.

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "task-auth-001",
    "prompt": "Implement user authentication",
    "agent": "coder",
    "status": "completed",
    "result": {
      "output": "Authentication module implemented...",
      "success": true,
      "tokens_used": 8432
    },
    "created_at": "2025-01-06T10:30:45.123Z",
    "completed_at": "2025-01-06T11:30:45.123Z"
  }
}
```

---

**PUT** `/api/tasks/{task_id}` - Update Task Status

```json
{
  "status": "in-progress"
}
```

---

### `/api/query` - Advanced Query

**POST** `/api/query` - Execute Complex Query

For queries beyond simple filtering, use the query endpoint.

**Request Body:**
```json
{
  "collection": "features",
  "conditions": [
    {
      "field": "status",
      "operator": "eq",
      "value": "todo"
    },
    {
      "field": "priority",
      "operator": "in",
      "value": ["high", "critical"]
    },
    {
      "field": "completion",
      "operator": "lt",
      "value": 50
    }
  ],
  "logical_op": "and"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      { "id": "feat-001", "title": "...", ... }
    ],
    "count": 12
  }
}
```

**Operators:**
- `eq` - Equal
- `ne` - Not equal
- `gt` - Greater than
- `gte` - Greater than or equal
- `lt` - Less than
- `lte` - Less than or equal
- `in` - In list
- `not_in` - Not in list
- `contains` - String contains
- `starts_with` - Starts with
- `ends_with` - Ends with
- `matches` - Regex match

---

### `/api/agent-stats` - Agent Statistics

**GET** `/api/agent-stats` - Get Agent Statistics

Get statistics for all agents.

**Response:**
```json
{
  "success": true,
  "data": {
    "agents": [
      {
        "agent_id": "claude",
        "total_tasks": 156,
        "completed": 142,
        "in_progress": 8,
        "blocked": 6,
        "completion_rate": 0.91,
        "avg_completion_time_seconds": 3600,
        "specialties": ["python", "architecture", "testing"]
      }
    ]
  }
}
```

---

**GET** `/api/agent-stats/{agent_id}` - Get Agent Details

Get detailed statistics for specific agent.

**Response:**
```json
{
  "success": true,
  "data": {
    "agent_id": "claude",
    "total_tasks": 156,
    "by_status": {
      "completed": 142,
      "in_progress": 8,
      "blocked": 6
    },
    "by_priority": {
      "low": 24,
      "medium": 89,
      "high": 35,
      "critical": 8
    },
    "completion_rate": 0.91,
    "avg_completion_time_seconds": 3600,
    "error_rate": 0.03,
    "last_active": "2025-01-06T10:30:45.123Z"
  }
}
```

---

### `/api/analytics` - Analytics

**GET** `/api/analytics/work-distribution` - Work Type Distribution

```json
{
  "success": true,
  "data": {
    "feature": 42,
    "bug": 18,
    "spike": 5,
    "chore": 12,
    "epic": 3,
    "total": 80
  }
}
```

---

**GET** `/api/analytics/bottlenecks` - Find Bottlenecks

Query Parameters:
- `limit` (optional): Number of bottlenecks to return (default: 5)

```json
{
  "success": true,
  "data": {
    "bottlenecks": [
      {
        "node_id": "feat-001",
        "title": "Database Schema",
        "blocking_count": 8,
        "blocker_ids": ["feat-002", "feat-003", ...],
        "priority": "critical"
      }
    ]
  }
}
```

---

**GET** `/api/analytics/parallel-work` - Get Parallelizable Work

Query Parameters:
- `max_agents` (optional): Max agents to plan for (default: 3)

```json
{
  "success": true,
  "data": {
    "parallel_work": {
      "agent_1": ["feat-001", "feat-002"],
      "agent_2": ["feat-003", "feat-004"],
      "agent_3": ["feat-005"]
    },
    "total_parallelizable": 5,
    "estimated_time_reduction": "33%"
  }
}
```

---

## Error Responses

### 400 Bad Request

Missing or invalid parameters.

```json
{
  "success": false,
  "error": "Invalid priority value. Must be one of: low, medium, high, critical",
  "error_code": "INVALID_PARAMETER",
  "field": "priority",
  "timestamp": "2025-01-06T10:30:45.123Z"
}
```

---

### 404 Not Found

Resource doesn't exist.

```json
{
  "success": false,
  "error": "Feature not found",
  "error_code": "NOT_FOUND",
  "resource": "feature",
  "id": "feat-missing",
  "timestamp": "2025-01-06T10:30:45.123Z"
}
```

---

### 409 Conflict

Resource already exists or claim conflict.

```json
{
  "success": false,
  "error": "Feature already claimed by another agent",
  "error_code": "CLAIM_CONFLICT",
  "resource": "feature",
  "id": "feat-abc123",
  "claimed_by": "claude",
  "timestamp": "2025-01-06T10:30:45.123Z"
}
```

---

### 500 Server Error

Internal server error.

```json
{
  "success": false,
  "error": "Internal server error",
  "error_code": "INTERNAL_ERROR",
  "details": "Optional error details for debugging",
  "timestamp": "2025-01-06T10:30:45.123Z"
}
```

---

## Pagination

List endpoints support pagination via query parameters:

```bash
# Get items 50-99
GET /api/features?limit=50&offset=50

# Get first 10
GET /api/features?limit=10
```

**Response includes:**
```json
{
  "data": {
    "items": [...],
    "total": 247,
    "limit": 50,
    "offset": 50,
    "has_next": true,
    "has_previous": true
  }
}
```

---

## Rate Limiting

No rate limiting currently implemented. Clients should implement backoff strategies for large batch operations.

---

## Authentication

Currently no authentication required. In production environments, use a reverse proxy with authentication (e.g., nginx with OAuth2).

---

## CORS Headers

Server includes standard CORS headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## Content Type

All requests and responses use:
```
Content-Type: application/json; charset=utf-8
```

---

## Complete Example

```bash
# Create a feature
curl -X POST http://localhost:8080/api/features \
  -H "Content-Type: application/json" \
  -d '{
    "title": "User Authentication",
    "priority": "high",
    "steps": ["Design", "Implement", "Test"]
  }'

# Response:
# {
#   "success": true,
#   "data": {
#     "id": "feat-abc123",
#     "title": "User Authentication",
#     ...
#   }
# }

# List high priority features
curl http://localhost:8080/api/features?priority=high

# Get specific feature
curl http://localhost:8080/api/features/feat-abc123

# Update feature status
curl -X PUT http://localhost:8080/api/features/feat-abc123 \
  -H "Content-Type: application/json" \
  -d '{"status": "in-progress"}'

# Delete feature
curl -X DELETE http://localhost:8080/api/features/feat-abc123
```

---

## See Also

- [SDK API Reference](API_REFERENCE.md) - Python SDK documentation
- [Orchestration Patterns](ORCHESTRATION_PATTERNS.md) - Multi-agent patterns
- [Integration Guide](INTEGRATION_GUIDE.md) - Quick start guide
