# Developer Guide

**Document ID:** 24-Developer-Guide  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

This document provides developers with everything they need to understand, set up, and extend AIOS.

## 2. Architecture Overview

Refer to [02-System-Architecture](02-System-Architecture.md) for the complete architecture.

## 3. Local Setup

### Prerequisites

- Node.js 18+
- Python 3.12+
- Rust (for Tauri)
- Tesseract OCR (for vision system)

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/aios/aios.git
cd aios

# Setup Python backend
cd src/backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Setup frontend
cd src/frontend
npm install

# Setup Tauri
cargo install tauri-cli

# Run development
cd ../..
npm run dev
```

## 14. Creating Modules

```python
# 1. Create module in src/backend/aios/core/
# 2. Inherit from BaseModule
# 3. Register with Event Bus
# 4. Add to dependency injection

class MyModule(BaseModule):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.event_bus.subscribe("my:event", self.handle_event)

    async def handle_event(self, event: Event):
        pass
```

## 15. Creating Tools

```python
# 1. Define tool contract
tool_contract = ToolContract(
    id="my_tool",
    name="My Tool",
    description="Does something useful",
    permission_level=PermissionLevel.SAFE,
    parameters={...},
    returns={...}
)

# 2. Implement handler
async def my_tool_handler(params: dict) -> ToolResult:
    # Implementation
    return ToolResult(success=True, data={...})

# 3. Register with Tool Manager
await tool_manager.register_tool(tool_contract, my_tool_handler)
```

## 16. Creating Plugins

```yaml
# plugin.yaml
id: "com.example.my-plugin"
name: "My Plugin"
version: "1.0.0"
min_aios_version: "1.0.0"
author: "Example Corp"
description: "Does something useful"
permissions:
  - read
  - safe
tools:
  - id: "my_tool"
    name: "My Tool"
    description: "Does something"
    permission_level: "safe"
    parameters:
      type: object
      properties:
        input:
          type: string
```

```python
# main.py
from aios_sdk import PluginAPI, ToolContract

api = PluginAPI()

async def my_tool_handler(params: dict):
    result = do_something(params["input"])
    return {"result": result}

api.register_tool(
    ToolContract(
        id="my_tool",
        name="My Tool",
        description="Does something",
        permission_level=1,
        parameters={"type": "object", "properties": {"input": {"type": "string"}}}
    ),
    my_tool_handler
)
```
