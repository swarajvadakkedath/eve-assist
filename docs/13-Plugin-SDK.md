# Plugin SDK

**Document ID:** 13-Plugin-SDK  
**Status:** Approved  
**Version:** 2.0.0  
**Last Updated:** 2026-07-19

---

## 1. Purpose

The Plugin SDK is the **single extension mechanism** for AIOS. Every future capability integrates through this SDK, including built-in tools, official extensions, third-party plugins, and enterprise plugins. The Execution Engine never needs to know where a capability originates.

## 2. Architecture

```
Conversation Manager
        │
        ▼
Execution Engine
        │
        ▼
Capability Registry
        ▲
        │
Plugin Runtime
        ▲
        │
Plugin Loader
        ▲
        │
Plugin SDK
        ▲
        │
Plugin Package
```

**No plugin may bypass:**
- Execution Engine
- Capability Registry
- Tool Manager
- Permission Manager
- Event Bus

## 3. Plugin Package Structure

```
my_plugin/
├── plugin.yaml          # Manifest (required)
├── plugin.py            # Entry point (required)
├── README.md            # Documentation
├── LICENSE              # License
├── requirements.txt     # Python dependencies
├── icon.png             # Plugin icon
├── resources/           # Static resources
├── tools/               # Standalone tool scripts
├── tests/               # Plugin-specific tests
└── assets/              # Media assets
```

## 4. Plugin Manifest (plugin.yaml)

```yaml
id: hello-world
name: Hello World
version: 1.0.0
sdk_version: 1.0.0
author: AIOS SDK
description: A minimal AIOS plugin example
license: MIT
homepage: https://aios.ai/plugins/hello-world
repository: https://github.com/aios/hello-world
platforms:
  - all
capabilities:
  - id: hello.say_hello
    name: Say Hello
    description: Returns a friendly greeting
    permission_level: 0
    parameters:
      name:
        type: string
        description: Name to greet
        required: false
    returns:
      type: string
      description: The greeting message
permissions:
  - filesystem.read
dependencies:
  some-other-plugin: ">=1.0.0"
entry_point: plugin.py
minimum_aios_version: 1.0.0
icon: icon.png
tags:
  - example
  - demo
category: examples
documentation: README.md
configuration_schema:
  type: object
  properties:
    greeting:
      type: string
      default: "Hello"
```

### Required Fields
| Field | Description |
|-------|-------------|
| `id` | Unique lowercase alphanumeric ID (hyphens/underscores allowed) |
| `name` | Human-readable name |
| `version` | Semver version (e.g. `1.0.0`) |
| `sdk_version` | SDK version the plugin targets |
| `author` | Plugin author |
| `description` | Short description |
| `license` | SPDX license identifier |
| `homepage` | Project homepage URL |
| `repository` | Source repository URL |
| `platforms` | Supported platforms (`windows`, `linux`, `macos`, `all`) |
| `capabilities` | Array of capability definitions |
| `permissions` | Array of permission strings |
| `dependencies` | Map of plugin ID to version spec |
| `entry_point` | Relative path to the plugin module |
| `minimum_aios_version` | Minimum AIOS version required |

## 5. Plugin Implementation (plugin.py)

```python
from aios.plugins.sdk import AIOSPlugin
from aios.plugins.models import PluginResult, PluginCapability

class MyPlugin(AIOSPlugin):
    async def initialize(self):
        """Load resources, setup configuration."""
        self._greeting = await self.get_setting("greeting", "Hello")

    async def register(self):
        """Register capabilities and tools."""
        cap = PluginCapability(
            id="hello.say_hello",
            name="Say Hello",
            description="Returns a friendly greeting",
            permission_level=0,
        )
        await self.register_capability(cap)

    async def start(self):
        """Start background tasks."""

    async def stop(self):
        """Stop background tasks."""

    async def shutdown(self):
        """Cleanup resources."""

    async def dispose(self):
        """Final cleanup when removed."""
```

## 6. Plugin Lifecycle

```
DISCOVERED → VALIDATED → VERIFIED → LOADING → LOADED
                                                   ↓
                                            INITIALIZING → STARTING → ACTIVE
                                                                        ↓
                                                                   STOPPING → STOPPED → UNLOADED → REMOVED
```

Every plugin transitions through these states, validated by the Lifecycle state machine. The Runtime invokes the corresponding methods on `AIOSPlugin`:

| State | Method Called |
|-------|--------------|
| INITIALIZING → STARTING | `instance.initialize()` |
| STARTING → ACTIVE | `instance.register()`, `instance.start()` |
| STOPPING → STOPPED | `instance.stop()` |
| UNLOADED | `instance.shutdown()`, `instance.dispose()` |

## 7. Plugin SDK Developer API

### AIOSPlugin Base Class

```python
class AIOSPlugin(ABC):
    # Required
    async def initialize(self) -> None
    async def register(self) -> None

    # Optional
    async def start(self) -> None
    async def health(self) -> Dict[str, Any]
    async def stop(self) -> None
    async def shutdown(self) -> None
    async def dispose(self) -> None

    # Helper Methods
    async def publish_event(self, event_type: str, payload: dict) -> None
    async def request_permission(self, permission: str, level: int, reason: str) -> bool
    async def register_tool(self, tool_definition: dict) -> bool
    async def register_capability(self, capability: PluginCapability) -> bool
    async def get_setting(self, key: str, default: Any) -> Any
    def log_info(self, message: str, **kwargs) -> None
    def log_error(self, message: str, **kwargs) -> None
    def log_warning(self, message: str, **kwargs) -> None
    def log_debug(self, message: str, **kwargs) -> None

    # Properties
    @property
    def plugin_id(self) -> str
    @property
    def plugin_name(self) -> str
```

## 8. SDK Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **SDK** | `sdk.py` | Developer API base class and helper methods |
| **Manifest** | `manifest.py` | Strongly typed manifest model with JSON/YAML support |
| **Models** | `models.py` | Data models: Plugin, PluginManifest, PluginCapability, etc. |
| **Lifecycle** | `lifecycle.py` | State machine with validated transitions |
| **Loader** | `loader.py` | Package discovery, import, instantiation, service injection |
| **Discovery** | `discovery.py` | Scans built-in, user, and system directories for plugins |
| **Validator** | `validator.py` | Manifest schema, required fields, dependencies, capabilities |
| **Verifier** | `verifier.py` | Platform, AIOS version, SDK version, package integrity |
| **Runtime** | `runtime.py` | Lifecycle management, health monitoring, crash recovery |
| **Isolator** | `isolator.py` | Execution isolation (in-process, subprocess, virtual env) |
| **Registry** | `registry.py` | Thread-safe storage and lookup for loaded plugins |
| **Health** | `health.py` | Status tracking, heartbeat, error and restart counting |
| **Permissions** | `permissions.py` | Permission requests, approval, revocation |
| **Repository** | `repository.py` | Persist plugin state, config, and version history |
| **Events** | `events.py` | Standardized lifecycle events via Event Bus |
| **Exceptions** | `exceptions.py` | Typed exception hierarchy |

## 9. Event Catalog

| Event | Trigger |
|-------|---------|
| `plugin:discovered` | Plugin package found during discovery |
| `plugin:validated` | Manifest validation complete |
| `plugin:verified` | Platform/compatibility verification complete |
| `plugin:loaded` | Plugin loaded into registry |
| `plugin:started` | Plugin started and active |
| `plugin:stopped` | Plugin stopped |
| `plugin:unloaded` | Plugin unloaded from registry |
| `plugin:failed` | Plugin entered failed state |
| `plugin:health_changed` | Plugin health status changed |
| `plugin:updated` | Plugin version updated |
| `plugin:permission_requested` | Plugin requested a permission |

## 10. Plugin Management API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/plugins` | List plugins (with search) |
| GET | `/api/v1/plugins/health` | Health summary |
| GET | `/api/v1/plugins/{id}` | Plugin details |
| GET | `/api/v1/plugins/{id}/manifest` | Plugin manifest |
| GET | `/api/v1/plugins/{id}/capabilities` | Plugin capabilities |
| GET | `/api/v1/plugins/{id}/permissions` | Plugin permissions |
| GET | `/api/v1/plugins/{id}/config` | Plugin configuration |
| PUT | `/api/v1/plugins/{id}/config` | Update configuration |
| GET | `/api/v1/plugins/{id}/health` | Plugin health |
| POST | `/api/v1/plugins/install` | Install a plugin package |
| POST | `/api/v1/plugins/{id}/enable` | Enable plugin |
| POST | `/api/v1/plugins/{id}/disable` | Disable plugin |
| POST | `/api/v1/plugins/{id}/reload` | Reload plugin |
| DELETE | `/api/v1/plugins/{id}` | Remove plugin |

## 11. Security Model

- **Validation**: Every plugin is validated before loading
- **Verification**: Platform compatibility and package integrity are verified
- **Permissions**: Plugins must declare permissions; verified against Permission Manager
- **Isolation**: Plugins execute in isolated environments (in-process, subprocess, virtual env)
- **Input Sanitization**: Configuration and permission strings are sanitized
- **Duplicate Prevention**: Plugin IDs must be unique
- **Dependency Protection**: Dependency resolution cannot escape allowed directories

## 12. Hello World Plugin Example

See `plugins/hello-world/` for a complete working example.

```python
# plugin.py
from aios.plugins.sdk import AIOSPlugin
from aios.plugins.models import PluginCapability

class HelloWorldPlugin(AIOSPlugin):
    async def initialize(self):
        self._greeting = await self.get_setting("greeting", "Hello")
        self.log_info(f"HelloWorld initialized with greeting: {self._greeting}")

    async def register(self):
        await self.register_capability(PluginCapability(
            id="hello.say_hello",
            name="Say Hello",
            description="Returns a friendly greeting",
            permission_level=0,
        ))

    async def start(self):
        self.log_info("HelloWorld started")
