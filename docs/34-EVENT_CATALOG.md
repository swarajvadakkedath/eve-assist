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

### Context Events

| Event | Source | Payload | Description |
|-------|--------|---------|-------------|
| `context:changed` | ContextEngine | Context dict | Published whenever context changes |
| `context:project_changed` | ContextEngine | `{path, type, markers}` | Published when active project changes |
| `context:file_changed` | ContextEngine | `{path, app}` | Published when active file changes |
| `context:activity_changed` | ContextEngine | `{activity, previous}` | Published when user activity type changes |
| `context:application_changed` | ContextEngine | `{app, window}` | Published when active application changes |
| `context:engine_started` | ContextEngine | `{poll_interval}` | Published when ContextEngine starts polling |
| `context:engine_stopped` | ContextEngine | `{}` | Published when ContextEngine stops |
| `context:poll_error` | ContextEngine | `{}` | Published when a poll cycle fails |

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

### Tool Events

| Event | Source | Payload | Description |
|-------|--------|---------|-------------|
| `tool:started` | ToolManager | `{tool_id, params, timeout}` | Published when a tool begins execution |
| `tool:completed` | ToolManager | `{tool_id, duration, success}` | Published when a tool completes |
| `tool:failed` | ToolManager | `{tool_id, duration, error}` | Published when a tool raises an exception |
| `tool:timeout` | ToolManager | `{tool_id, duration, timeout}` | Published when a tool exceeds its timeout |

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

### DevTools Events

| Event | Source | Payload |
|-------|--------|---------|
| `debug:eval` | DebugConsole | `{expression, session_id, output, result, duration_ms}` |
| `debug:exec` | DebugConsole | `{code, session_id, output, duration_ms}` |
| `debug:inspect` | DebugConsole | `{session_id, variables, count}` |
| `debug:session_cleared` | DebugConsole | `{session_id}` |
| `health:updated` | HealthDashboard | `{component, status, checked_at}` |
| `module:inspected` | ModuleInspector | `{module_name, info}` |
| `hot_reload:completed` | HotReload | `{module, duration_ms}` |
| `hot_reload:failed` | HotReload | `{module, error}` |
| `hot_reload:watch_added` | HotReload | `{module}` |
| `hot_reload:watch_removed` | HotReload | `{module}` |
| `hot_reload:polling_started` | HotReload | `{interval}` |
| `hot_reload:polling_stopped` | HotReload | `{}` |
| `diagnostics:completed` | Diagnostics | `{results, summary}` |
| `perf:monitoring_started` | PerformanceMonitor | `{interval}` |
| `perf:monitoring_stopped` | PerformanceMonitor | `{summary}` |
| `perf:metrics` | PerformanceMonitor | `{cpu, memory, labels, timestamp}` |
| `log:entry` | LogViewer | `{level, source, message, timestamp}` |
| `log:cleared` | LogViewer | `{}` |
| `log:level_changed` | LogViewer | `{level}` |

### Windows Adapter Events

| Event | Source | Payload |
|-------|--------|---------|
| `clipboard:read` | WindowsAdapter | `{text_length}` |
| `clipboard:changed` | WindowsAdapter | `{text_length}` |
| `file:read` | WindowsAdapter | `{path}` |
| `file:changed` | WindowsAdapter | `{path, action, destination?}` |
| `process:started` | WindowsAdapter | `{pid, command}` |
| `process:stopped` | WindowsAdapter | `{pid}` |
| `active_window:changed` | WindowsAdapter | `{title, app, x, y, width, height}` |

---

## Event Ownership

| Event Prefix | Owner | Notes |
|-------------|-------|-------|
| `system:*` | app.py | Application lifecycle |
| `error:*` | Event Bus | Error reporting |
| `context:*` | ContextEngine | Workspace context changes |
| `conversation:*` | ConversationManager | Conversation lifecycle |
| `execution:*` | ExecutionEngine | Execution lifecycle |
| `tool:*` | ToolManager | Tool execution lifecycle |
| `workspace:*` | WorkspaceManager | Workspace state changes |
| `desktop:*` | StatusService | Desktop status |
| `debug:*` | DebugConsole | Debug console operations |
| `health:*` | HealthDashboard | Component health tracking |
| `module:*` | ModuleInspector | Module inspection |
| `hot_reload:*` | HotReload | Module hot reloading |
| `diagnostics:*` | Diagnostics | System diagnostics |
| `perf:*` | PerformanceMonitor | Performance metrics |
| `log:*` | LogViewer | Log entry management |
| `clipboard:*` | WindowsAdapter | Clipboard operations |
| `file:*` | WindowsAdapter | File system operations |
| `process:*` | WindowsAdapter | Process management |
| `active_window:*` | WindowsAdapter | Active window tracking |

---

## Event Granularity

Events are appropriately granular. No events are too coarse or too fine. The `execution:*` events provide the right level of detail for progress tracking without flooding the bus.

---

## Duplicate Events

None found. Each event has a unique type and source.

## Missing Events

- `plugin:*` events — Plugin lifecycle events (installed, enabled, disabled, uninstalled) are not published. Should be added when Plugin SDK is completed.
- `memory:*` events — Memory storage/retrieval events are not published. Would be useful for learning and analytics.
