# API Specification

**Document ID:** 17-API-Specification  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

This document defines the complete API specification for AIOS, including all endpoints, request/response formats, error handling, and authentication.

## 2. API Overview

AIOS exposes a RESTful API via FastAPI on `http://localhost:PORT`. The frontend communicates with the backend through this API.

## 3. Authentication

- API is local-only (localhost)
- No external authentication required
- Internal token for Tauri-to-Python communication
- Token is generated at startup and passed via environment

## 4. Endpoints

### Chat

#### POST /api/v1/chat/message

Send a message to AIOS.

```json
// Request
{
  "conversation_id": "uuid-or-null",
  "content": "Find all PDFs larger than 10MB",
  "mode": "chat"
}

// Response
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "content": "I found 5 PDFs larger than 10MB...",
  "tool_calls": [
    {
      "id": "uuid",
      "tool_id": "file_search",
      "status": "completed",
      "result": {...}
    }
  ],
  "timestamp": "2026-07-18T12:00:00Z"
}
```

#### GET /api/v1/chat/stream

Stream a chat response.

```json
// Response (SSE)
data: {"type": "token", "content": "I"}
data: {"type": "token", "content": " found"}
data: {"type": "token", "content": " 5"}
data: {"type": "token", "content": " files"}
data: {"type": "done", "message_id": "uuid"}
```

#### GET /api/v1/chat/history

Get conversation history.

```json
// Response
{
  "conversations": [
    {
      "id": "uuid",
      "title": "File Organization",
      "message_count": 12,
      "last_message": "2026-07-18T12:00:00Z"
    }
  ]
}
```

### Tools

#### GET /api/v1/tools

List all available tools.

```json
// Response
{
  "tools": [
    {
      "id": "file_search",
      "name": "File Search",
      "description": "Search for files by name, type, or size",
      "permission_level": 0,
      "category": "files",
      "parameters": {
        "type": "object",
        "properties": {
          "pattern": {"type": "string"},
          "min_size": {"type": "string"}
        }
      }
    }
  ]
}
```

#### POST /api/v1/tools/execute

Execute a tool.

```json
// Request
{
  "tool_id": "file_search",
  "params": {
    "pattern": "*.pdf",
    "min_size": "10MB"
  }
}

// Response
{
  "success": true,
  "data": {
    "files": ["report.pdf", "manual.pdf"],
    "count": 2
  },
  "duration": 0.45
}
```

### Permissions

#### GET /api/v1/permissions/pending

Get pending permission requests.

```json
// Response
{
  "requests": [
    {
      "id": "uuid",
      "tool_id": "delete_files",
      "level": 3,
      "description": "Delete 5 files in Downloads",
      "created_at": "2026-07-18T12:00:00Z"
    }
  ]
}
```

#### POST /api/v1/permissions/grant

Grant a permission request.

```json
// Request
{
  "request_id": "uuid"
}

// Response
{
  "status": "granted",
  "tool_call_id": "uuid"
}
```

#### POST /api/v1/permissions/deny

Deny a permission request.

```json
// Request
{
  "request_id": "uuid",
  "reason": "I don't want to delete those files"
}

// Response
{
  "status": "denied"
}
```

### Memory

#### POST /api/v1/memory/search

Search memory.

```json
// Request
{
  "query": "What was my project structure?",
  "limit": 10
}

// Response
{
  "results": [
    {
      "id": "uuid",
      "type": "fact",
      "content": "User was working on a React project called AIOS",
      "importance": 0.8,
      "timestamp": "2026-07-18T10:00:00Z"
    }
  ]
}
```

#### POST /api/v1/memory/store

Store a memory.

```json
// Request
{
  "type": "preference",
  "content": "User prefers dark mode",
  "importance": 0.6
}

// Response
{
  "id": "uuid",
  "status": "stored"
}
```

### Plugins

#### GET /api/v1/plugins

List installed plugins.

```json
// Response
{
  "plugins": [
    {
      "id": "com.example.my-plugin",
      "name": "My Plugin",
      "version": "1.0.0",
      "enabled": true,
      "tools_count": 3
    }
  ]
}
```

#### POST /api/v1/plugins/install

Install a plugin.

```json
// Request
{
  "path": "/path/to/plugin.zip"
}

// Response
{
  "id": "com.example.my-plugin",
  "status": "installed",
  "tools": ["my_tool"]
}
```

### Settings

#### GET /api/v1/settings

Get all settings.

```json
// Response
{
  "settings": {
    "ai.provider": "openai",
    "ai.model": "gpt-4",
    "ui.theme": "dark",
    "permissions.default_level": "safe"
  }
}
```

#### PUT /api/v1/settings

Update settings.

```json
// Request
{
  "ai.provider": "anthropic",
  "ui.theme": "light"
}

// Response
{
  "status": "updated",
  "settings": {
    "ai.provider": "anthropic",
    "ui.theme": "light"
  }
}
```

### System

#### GET /api/v1/system/health

Health check endpoint.

```json
// Response
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600,
  "modules": {
    "event_bus": "healthy",
    "ai_router": "healthy",
    "tool_manager": "healthy",
    "memory_system": "healthy"
  }
}
```

#### GET /api/v1/system/status

Get system status.

```json
// Response
{
  "cpu_usage": 23.5,
  "memory_usage": 45.2,
  "active_providers": ["openai"],
  "active_tools": 24,
  "active_conversations": 2,
  "uptime": 3600
}
```

## 5. Error Handling

```json
// Standard Error Response
{
  "error": {
    "code": "TOOL_EXECUTION_ERROR",
    "message": "Failed to execute tool: file_search",
    "details": {
      "tool_id": "file_search",
      "reason": "Permission denied"
    },
    "request_id": "uuid"
  }
}
```

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request |
| `TOOL_NOT_FOUND` | 404 | Tool not registered |
| `PERMISSION_DENIED` | 403 | Permission not granted |
| `TOOL_EXECUTION_ERROR` | 500 | Tool execution failed |
| `AI_PROVIDER_ERROR` | 502 | AI provider unavailable |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `PLUGIN_ERROR` | 500 | Plugin execution error |
| `INTERNAL_ERROR` | 500 | Unexpected error |

## 5. API Versioning

- API version is in URL path: `/api/v1/`
- Breaking changes increment version
- Deprecated versions supported for 6 months
- Version header: `X-API-Version: 1`
