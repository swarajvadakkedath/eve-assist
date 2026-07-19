# Coding Standards

**Document ID:** 06-Coding-Standards  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

This document defines the coding standards for AIOS to ensure consistency, maintainability, and quality across the codebase.

## 2. Naming Conventions

### 2.1 Python

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `event_bus.py` |
| Classes | PascalCase | `EventBus` |
| Functions | snake_case | `publish_event()` |
| Variables | snake_case | `event_payload` |
| Constants | UPPER_SNAKE | `MAX_RETRY_COUNT` |
| Private | _prefix | `_validate_event` |
| Protected | _prefix | `_internal_method` |

### 2.2 TypeScript

| Element | Convention | Example |
|---------|------------|---------|
| Files | camelCase | `eventBus.ts` |
| Components | PascalCase | `ChatWindow.tsx` |
| Functions | camelCase | `sendMessage()` |
| Variables | camelCase | `eventPayload` |
| Interfaces | PascalCase | `IEventPayload` |
| Types | PascalCase | `EventType` |
| Enums | PascalCase | `PermissionLevel` |

## 3. Error Handling

```python
# Always use typed exceptions
class AIOSError(Exception):
    """Base exception for all AIOS errors."""
    code: str
    details: dict

class ToolExecutionError(AIOSError):
    """Raised when a tool fails to execute."""
    code = "TOOL_EXECUTION_ERROR"

# Always handle errors at module boundaries
try:
    result = await tool_manager.execute(tool_id, params)
except ToolExecutionError as e:
    event_bus.publish("tool:failed", {"tool_id": tool_id, "error": e})
    raise
```

## 4. Logging

```python
# Structured JSON logging
import structlog

logger = structlog.get_logger(__name__)
logger.info("tool.executed", tool_id="file_search", duration=1.2, status="success")
```

## 5. Dependency Injection

```python
# All modules receive dependencies through constructor injection
class ToolManager:
    def __init__(self, event_bus: EventBus, permission_manager: PermissionManager):
        self.event_bus = event_bus
        self.permission_manager = permission_manager
```

## 6. Configuration

```python
# Centralized configuration with Pydantic
from pydantic_settings import BaseSettings

class AiosConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIOS_")

    ai_provider: str = "openai"
    ai_api_key: str = ""
    db_path: str = "~/.aios/aios.db"
    log_level: str = "INFO"
```

## 7. Testing Standards

- Unit tests: pytest with asyncio support
- Integration tests: pytest with fixtures
- E2E tests: Playwright for UI, pytest for backend
- Coverage target: > 90%
- All tests must be async-compatible
- Mock external services (AI providers, Windows APIs)

## 8. Documentation Standards

- All public APIs have docstrings
- All modules have README files
- Architecture decisions recorded in ADRs
- Code comments explain "why", not "what"
- Documentation is versioned alongside code
