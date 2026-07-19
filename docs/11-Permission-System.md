# Permission System

**Document ID:** 11-Permission-System  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

The Permission System gates all tool execution through configurable permission levels. It ensures that AIOS never performs sensitive actions without appropriate human approval.

## 2. Architecture

```mermaid
graph TB
    subgraph "Permission Manager"
        PM[Core]
        EVAL[Evaluator]
        CACHE[Cache]
        HISTORY[History]
    end

    subgraph "Permission Levels"
        L1[Read]
        L2[Safe]
        L3[Workspace]
        L4[Sensitive]
    end

    subgraph "User Interface"
        DIALOG[Permission Dialog]
        PREF[Preferences]
        SESSION[Session Settings]
    end

    TM[Tool Manager] --> PM
    PM --> L1
    PM --> L2
    PM --> L3
    PM --> L4
    PM --> DIALOG
    PM --> PREF
    PM --> SESSION
```

## 2. Permission Levels

```mermaid
graph TD
    subgraph "Permission Levels"
        L1[Level 1: Read]
        L2[Level 2: Safe]
        L3[Level 3: Workspace]
        L4[Level 4: Sensitive]
    end

    L1 -->|Auto-approve| Execute
    L2 -->|Auto-approve| Execute
    L3 -->|Confirm once| Execute
    L4 -->|Always confirm| Execute

    L1 -.->|Examples: read files, system info| Info
    L2 -.->|Examples: create files, open apps| Info
    L3 -.->|Examples: edit files, rename| Info
    L4 -.->|Examples: delete, install, modify| Info
```

## 2. Permission Levels

| Level | Name | Auto-approve | Confirmation | Examples |
|-------|------|-------------|--------------|----------|
| 0 | **Read** | Always | None | Read files, system info, clipboard |
| 1 | **Safe** | Always | None | Create files, open apps, web search |
| 2 | **Workspace** | Session | Once per session | Edit files, rename, organize |
| 3 | **Sensitive** | Never | Always required | Delete files, install, modify system |

## 3. Confirmation Flows

### 3.1 Read Level (Auto-approve)

```mermaid
sequenceDiagram
    User->>AIOS: "How much RAM do I have?"
    AIOS->>Tool: execute(system_info)
    Tool-->>AIOS: RAM: 16GB
    AIOS->>User: "You have 16GB of RAM"
```

### 3.2 Safe Level (Auto-approve)

```mermaid
sequenceDiagram
    User->>AIOS: "Create a new folder called Projects"
    AIOS->>Tool: execute(create_folder)
    Tool-->>AIOS: Folder created
    AIOS->>User: "Created Projects folder"
```

### 3.3 Workspace Level (Session Confirm)

```mermaid
sequenceDiagram
    User->>AIOS: "Rename all .txt files to .md"
    AIOS->>Permission: Request workspace permission
    Permission->>User: "Allow file renames this session?"
    User->>Permission: Yes
    Permission->>Tool: Execute
    Tool-->>AIOS: Files renamed
    AIOS->>User: "Renamed 12 files"
```

### 3.4 Sensitive Level (Always Confirm)

```mermaid
sequenceDiagram
    User->>AIOS: "Delete the temp folder"
    AIOS->>Permission: Request sensitive permission
    Permission->>User: "⚠️ Delete entire temp folder?"
    User->>Permission: Confirm
    Permission->>Tool: Execute
    Tool-->>AIOS: Folder deleted
    AIOS->>User: "Deleted temp folder"
```

## 4. Permission Configuration

```yaml
permissions:
  default_level: "safe"
  session_timeout: 300  # seconds
  sensitive_actions:
    - delete_files
    - install_software
    - modify_registry
    - execute_commands
  auto_approve:
    - read_file
    - system_info
    - clipboard_read
```

## 5. Public Interface

```python
class PermissionManager:
    async def check_permission(self, tool_id: str, level: PermissionLevel) -> PermissionResult
    async def request_permission(self, request: PermissionRequest) -> PermissionResult
    async def grant_permission(self, request_id: str) -> None
    async def deny_permission(self, request_id: str, reason: str) -> None
    async def get_pending_requests(self) -> list[PermissionRequest]
```

## 6. Implementation Notes

- Permission levels are defined in configuration
- Session permissions expire after timeout
- Sensitive actions always require confirmation
- Permission history is persisted to SQLite
- Users can configure default permissions per tool
