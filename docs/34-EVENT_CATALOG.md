# 34. Event Catalog

## Event Naming Convention

All events follow the pattern: `{domain}:{action}`

Examples: `conversation:created`, `execution:started`, `workspace:updated`

## Complete Event Catalog

### System Events

| Event | Source | Payload | Description |
|-------|--------|---------|-------------|
| `system:startup` | app.py | `{version: str}` | Published when the application starts |
| `system:shutdown` | app.py | `{reason: str}` | Published when the application shuts down |

### Error Events

| Event | Source | Payload | Description |
|-------|--------|---------|-------------|
| `error:occurred` | Event Bus, any module | `{module: str, error: str, event_type?: str, subscription?: str}` | Published when any error occurs |

### Conversation Events

| Event | Source | Payload | Description |
|-------|--------|---------|-------------|
| `conversation:created` | ConversationManager | `{conversation_id, title, mode}` | New conversation created |
| `conversation:updated` | ConversationManager | `{conversation_id, title}` | Conversation metadata updated |
| `conversation:deleted` | ConversationManager | `{conversation_id}` | Conversation deleted |
| `conversation:message_sent` | ConversationManager | `{conversation_id, message_id, role, content}` | User message sent |
| `conversation:message_received` | ConversationManager | `{conversation_id, message_id, content}` | AI response received |
| `conversation:stream_start` | ConversationManager | `{conversation_id, message_id}` | Streaming started |
| `conversation:stream_token` | ConversationManager | `{conversation_id, message_id, token}` | Streaming token |
| `conversation:stream_end` | ConversationManager | `{conversation_id, message_id}` | Streaming ended |
| `conversation:stream_error` | ConversationManager | `{conversation_id, message_id, error}` | Streaming error |

### Execution Events

| Event | Source | Payload |
|-------|--------|---------|
| `execution:created` | ExecutionEngine | `{execution_id, objective, priority}` |
| `execution:started` | ExecutionEngine | `{execution_id}` |
| `execution:completed` | ExecutionEngine | `{execution_id, result}` |
| `execution:failed` | ExecutionEngine | `{execution_id, error}` |
| `execution:cancelled` | ExecutionEngine | `{execution_id}` |
| `execution:paused` | ExecutionEngine | `{execution_id}` |
| `execution:resumed` | ExecutionEngine | `{execution_id}` |
| `execution:task_completed` | ExecutionEngine | `{execution_id, task_id, result}` |
| `execution:task_failed` | ExecutionEngine | `{execution_id, task_id, error}` |
| `execution:progress` | ExecutionEngine | `{execution_id, percentage, current_capability, completed_tasks, total_tasks}` |

### Workspace Events

| Event | Payload |
|-------|---------|
| `workspace:updated` | `{active_window, project_count, application_count, repository_count, editor_count, terminal_count}` |
| `workspace:project_detected` | `{name, framework, language, root_path}` |
| `workspace:git_status_changed` | `{branch, dirty, ahead, behind, remote, modified_count}` |
| `workspace:editor_changed` | `{name, active_file, file_language}` |
| `workspace:application_changed` | `{process_name, window_title, category}` |
| `workspace:terminal_changed` | `{shell, cwd}` |

### Desktop Events

| Event | Source | Payload |
|-------|--------|---------|
| `desktop:status` | StatusService | `{status, metadata}` |

### Error Events

| Event | Source | Payload |
|-------|--------|---------|
| `error:occurred` | Event Bus, any module | `{module, error, event_type?, subscription?}` |

---

## Event Ownership

| Event Prefix | Owner | Notes |
|-------------|-------|-------|
| `system:*` | app.py | Application lifecycle |
| `error:*` | Event Bus | Error reporting |
| `conversation:*` | ConversationManager | Conversation lifecycle |
| `execution:*` | ExecutionEngine | Execution lifecycle |
| `workspace:*` | WorkspaceManager | Workspace state changes |
| `desktop:*` | StatusService | Desktop status |

---

## Event Granularity

Events are appropriately granular. No events are too coarse or too fine. The `execution:*` events provide the right level of detail for progress tracking without flooding the bus.

---

## Duplicate Events

None found. Each event has a unique type and source.

---

### Tool Events

| Event | Source | Payload | Description |
|-------|--------|---------|-------------|
| `tool:started` | ToolManager | `{tool_id, params, timeout}` | Published when a tool begins execution |
| `tool:completed` | ToolManager | `{tool_id, duration, success}` | Published when a tool completes successfully |
| `tool:failed` | ToolManager | `{tool_id, duration, error}` | Published when a tool raises an exception |
| `tool:timeout` | ToolManager | `{tool_id, duration, timeout}` | Published when a tool exceeds its timeout |

## Missing Events

- `plugin:*` events — Plugin lifecycle events (installed, enabled, disabled, uninstalled) are not published. Should be added when Plugin SDK is completed.
- `memory:*` events — Memory storage/retrieval events are not published. Would be useful for learning and analytics.
