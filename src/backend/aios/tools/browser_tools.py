"""Browser Automation Toolkit — 28 tools for browser lifecycle, tabs, navigation, interaction, extraction, and automation."""

import asyncio
import json
from typing import Any

from aios.core.tool_manager import ToolContract, ToolResult
from aios.core.permission_manager import PermissionLevel
from aios.browser.engine import BrowserEngine, BrowserError


# ── Browser Lifecycle ──

async def _browser_launch(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        instance_id = await engine.launch(
            browser_type=params.get("browser_type", "chromium"),
            headless=params.get("headless", True),
            proxy=params.get("proxy"),
            args=params.get("args"),
        )
        return ToolResult(success=True, data={
            "instance_id": instance_id,
            "browser_type": params.get("browser_type", "chromium"),
            "headless": params.get("headless", True),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _browser_close(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        instance_id = params.get("instance_id", "")
        if not instance_id:
            return ToolResult(success=False, error="instance_id is required")
        await engine.close(instance_id)
        return ToolResult(success=True, data={"instance_id": instance_id, "closed": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _browser_list(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        instances = await engine.list_instances()
        return ToolResult(success=True, data={"instances": instances, "count": len(instances)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _browser_focus(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.focus(params.get("instance_id", ""))
        return ToolResult(success=True, data={"focused": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Tabs ──

async def _tab_new(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        page_id = await engine.new_tab(params.get("instance_id", ""), url=params.get("url", ""))
        return ToolResult(success=True, data={"page_id": page_id, "url": params.get("url", "")})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _tab_close(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.close_tab(params.get("instance_id", ""), params.get("page_id"))
        return ToolResult(success=True, data={"closed": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _tab_switch(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.switch_tab(params.get("instance_id", ""), params.get("page_id", ""))
        return ToolResult(success=True, data={"switched": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _tab_list(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        tabs = await engine.list_tabs(params.get("instance_id", ""))
        return ToolResult(success=True, data={
            "tabs": [
                {"page_id": t.page_id, "title": t.title, "url": t.url, "index": t.index}
                for t in tabs
            ],
            "count": len(tabs),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Navigation ──

async def _navigate(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.navigate(
            params.get("instance_id", ""),
            params.get("url", ""),
            timeout=params.get("timeout", 30000),
            wait_until=params.get("wait_until", "load"),
        )
        return ToolResult(success=True, data={
            "url": result.url,
            "title": result.title,
            "status_code": result.status_code,
            "duration_ms": result.duration_ms,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _reload(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.reload(params.get("instance_id", ""), timeout=params.get("timeout", 30000))
        return ToolResult(success=True, data={
            "url": result.url, "title": result.title,
            "status_code": result.status_code, "duration_ms": result.duration_ms,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _back(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.go_back(params.get("instance_id", ""), timeout=params.get("timeout", 30000))
        return ToolResult(success=True, data={
            "url": result.url, "title": result.title,
            "status_code": result.status_code, "duration_ms": result.duration_ms,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _forward(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.go_forward(params.get("instance_id", ""), timeout=params.get("timeout", 30000))
        return ToolResult(success=True, data={
            "url": result.url, "title": result.title,
            "status_code": result.status_code, "duration_ms": result.duration_ms,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _wait_for_page(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.wait_for_page(params.get("instance_id", ""), timeout=params.get("timeout", 30000))
        return ToolResult(success=True, data={
            "url": result.url, "title": result.title,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Interaction ──

async def _click(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.click(
            params.get("instance_id", ""),
            params.get("selector", ""),
            timeout=params.get("timeout", 10000),
        )
        return ToolResult(success=True, data={"selector": params.get("selector", ""), "clicked": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _double_click(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.double_click(
            params.get("instance_id", ""),
            params.get("selector", ""),
            timeout=params.get("timeout", 10000),
        )
        return ToolResult(success=True, data={"selector": params.get("selector", ""), "double_clicked": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _right_click(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.right_click(
            params.get("instance_id", ""),
            params.get("selector", ""),
            timeout=params.get("timeout", 10000),
        )
        return ToolResult(success=True, data={"selector": params.get("selector", ""), "right_clicked": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _hover(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.hover(
            params.get("instance_id", ""),
            params.get("selector", ""),
            timeout=params.get("timeout", 10000),
        )
        return ToolResult(success=True, data={"selector": params.get("selector", ""), "hovered": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _type_text(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.type_text(
            params.get("instance_id", ""),
            params.get("selector", ""),
            params.get("text", ""),
            timeout=params.get("timeout", 10000),
            clear_first=params.get("clear_first", True),
        )
        return ToolResult(success=True, data={
            "selector": params.get("selector", ""),
            "text_length": len(params.get("text", "")),
            "typed": True,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _press_key(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.press_key(
            params.get("instance_id", ""),
            params.get("key", ""),
            selector=params.get("selector"),
        )
        return ToolResult(success=True, data={"key": params.get("key", ""), "pressed": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _select_option(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        await engine.select_option(
            params.get("instance_id", ""),
            params.get("selector", ""),
            params.get("values", []),
            timeout=params.get("timeout", 10000),
        )
        return ToolResult(success=True, data={
            "selector": params.get("selector", ""),
            "values": params.get("values", []),
            "selected": True,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _upload_file(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.upload_file(
            params.get("instance_id", ""),
            params.get("selector", ""),
            params.get("file_path", ""),
            timeout=params.get("timeout", 30000),
        )
        return ToolResult(success=result.success, data={
            "success": result.success,
            "file_name": result.file_name,
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _download_file(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.download_file(
            params.get("instance_id", ""),
            url=params.get("url"),
            timeout=params.get("timeout", 60000),
        )
        return ToolResult(success=result.success, data={
            "file_path": result.file_path,
            "file_name": result.file_name,
            "file_size": result.file_size,
            "success": result.success,
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Extraction ──

async def _extract_text(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.extract_text(
            params.get("instance_id", ""),
            selector=params.get("selector", "body"),
        )
        return ToolResult(success=not result.error, data={
            "text": result.text,
            "length": result.count,
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _extract_links(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.extract_links(params.get("instance_id", ""))
        return ToolResult(success=not result.error, data={
            "links": result.items,
            "count": result.count,
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _extract_tables(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.extract_tables(params.get("instance_id", ""))
        return ToolResult(success=not result.error, data={
            "tables": result.items,
            "count": result.count,
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _extract_forms(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.extract_forms(params.get("instance_id", ""))
        return ToolResult(success=not result.error, data={
            "forms": result.items,
            "count": result.count,
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _capture_page(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.capture_page(
            params.get("instance_id", ""),
            full_page=params.get("full_page", True),
        )
        import base64
        b64 = base64.b64encode(result.image_data).decode("utf-8") if result.image_data else ""
        return ToolResult(success=not result.error, data={
            "screenshot_base64": b64,
            "width": result.width,
            "height": result.height,
            "format": result.format,
            "size_bytes": len(result.image_data),
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _capture_element(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.capture_element(
            params.get("instance_id", ""),
            params.get("selector", ""),
            timeout=params.get("timeout", 10000),
        )
        import base64
        b64 = base64.b64encode(result.image_data).decode("utf-8") if result.image_data else ""
        return ToolResult(success=not result.error, data={
            "screenshot_base64": b64,
            "width": result.width,
            "height": result.height,
            "size_bytes": len(result.image_data),
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Automation ──

async def _wait_for_element(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        found = await engine.wait_for_element(
            params.get("instance_id", ""),
            params.get("selector", ""),
            timeout=params.get("timeout", 30000),
            state=params.get("state", "visible"),
        )
        return ToolResult(success=True, data={"found": found, "selector": params.get("selector", "")})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _wait_for_text(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        found = await engine.wait_for_text(
            params.get("instance_id", ""),
            params.get("text", ""),
            timeout=params.get("timeout", 30000),
        )
        return ToolResult(success=True, data={"found": found, "text": params.get("text", "")})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _execute_javascript(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.execute_javascript(
            params.get("instance_id", ""),
            params.get("script", ""),
        )
        return ToolResult(success=result.success, data={
            "result": result.result,
            "duration_ms": result.duration_ms,
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _evaluate_expression(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        result = await engine.evaluate_expression(
            params.get("instance_id", ""),
            params.get("expression", ""),
        )
        return ToolResult(success=result.success, data={
            "result": result.result,
            "duration_ms": result.duration_ms,
            "error": result.error,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Vision Integration ──

async def _vision_verify(params: dict, engine: BrowserEngine, event_bus=None) -> ToolResult:
    try:
        obs = await engine.vision_verify(
            params.get("instance_id", ""),
            description=params.get("description", ""),
        )
        return ToolResult(success=True, data=obs)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Registration ──

def register_browser_tools(tm, engine, vision_engine=None, event_bus=None):
    """Register all browser automation tools with the ToolManager."""

    browser_tools = [
        ToolContract(
            id="browser.launch", name="Launch Browser",
            description="Launch a new browser instance (chromium, chrome, edge, firefox)",
            parameters={
                "browser_type": {"type": "string", "description": "Browser type: chromium, chrome, edge, firefox", "default": "chromium"},
                "headless": {"type": "boolean", "description": "Run in headless mode", "default": True},
                "proxy": {"type": "object", "description": "Proxy configuration {server, username, password}", "required": False},
                "args": {"type": "array", "description": "Additional browser launch arguments", "required": False},
            },
            returns={"instance_id": {"type": "string"}, "browser_type": {"type": "string"}, "headless": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.launch"],
            tags=["browser", "launch"],
        ),
        ToolContract(
            id="browser.close", name="Close Browser",
            description="Close a browser instance",
            parameters={"instance_id": {"type": "string", "description": "Browser instance ID"}},
            returns={"instance_id": {"type": "string"}, "closed": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.close"],
            tags=["browser", "close"],
        ),
        ToolContract(
            id="browser.list", name="List Browsers",
            description="List all active browser instances",
            parameters={},
            returns={"instances": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.list"],
            tags=["browser", "list"],
        ),
        ToolContract(
            id="browser.focus", name="Focus Browser",
            description="Focus a browser instance",
            parameters={"instance_id": {"type": "string", "description": "Browser instance ID"}},
            returns={"focused": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.focus"],
            tags=["browser", "focus"],
        ),
    ]

    tab_tools = [
        ToolContract(
            id="tab.new", name="New Tab",
            description="Open a new tab in the browser instance",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "url": {"type": "string", "description": "Optional URL to navigate to", "required": False},
            },
            returns={"page_id": {"type": "string"}, "url": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["tab.new"],
            tags=["tab", "new"],
        ),
        ToolContract(
            id="tab.close", name="Close Tab",
            description="Close a tab in the browser instance",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "page_id": {"type": "string", "description": "Page ID to close (optional, closes active if omitted)", "required": False},
            },
            returns={"closed": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["tab.close"],
            tags=["tab", "close"],
        ),
        ToolContract(
            id="tab.switch", name="Switch Tab",
            description="Switch to a specific tab",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "page_id": {"type": "string", "description": "Page ID to switch to"},
            },
            returns={"switched": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["tab.switch"],
            tags=["tab", "switch"],
        ),
        ToolContract(
            id="tab.list", name="List Tabs",
            description="List all open tabs in a browser instance",
            parameters={"instance_id": {"type": "string", "description": "Browser instance ID"}},
            returns={"tabs": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["tab.list"],
            tags=["tab", "list"],
        ),
    ]

    navigation_tools = [
        ToolContract(
            id="browser.navigate", name="Navigate",
            description="Navigate the current page to a URL",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "url": {"type": "string", "description": "URL to navigate to"},
                "timeout": {"type": "integer", "description": "Navigation timeout in ms", "default": 30000},
                "wait_until": {"type": "string", "description": "When to consider navigation complete: load, domcontentloaded, networkidle", "default": "load"},
            },
            returns={"url": {"type": "string"}, "title": {"type": "string"}, "status_code": {"type": "integer"}, "duration_ms": {"type": "number"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.navigate"],
            tags=["navigation"],
        ),
        ToolContract(
            id="browser.reload", name="Reload",
            description="Reload the current page",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "timeout": {"type": "integer", "description": "Navigation timeout in ms", "default": 30000},
            },
            returns={"url": {"type": "string"}, "title": {"type": "string"}, "status_code": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.reload"],
            tags=["navigation", "reload"],
        ),
        ToolContract(
            id="browser.back", name="Back",
            description="Navigate back in history",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "timeout": {"type": "integer", "description": "Navigation timeout in ms", "default": 30000},
            },
            returns={"url": {"type": "string"}, "title": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.back"],
            tags=["navigation", "back"],
        ),
        ToolContract(
            id="browser.forward", name="Forward",
            description="Navigate forward in history",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "timeout": {"type": "integer", "description": "Navigation timeout in ms", "default": 30000},
            },
            returns={"url": {"type": "string"}, "title": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.forward"],
            tags=["navigation", "forward"],
        ),
        ToolContract(
            id="browser.wait_for_page", name="Wait for Page",
            description="Wait for the current page to finish loading (network idle)",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "timeout": {"type": "integer", "description": "Timeout in ms", "default": 30000},
            },
            returns={"url": {"type": "string"}, "title": {"type": "string"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.wait_for_page"],
            tags=["navigation", "wait"],
        ),
    ]

    interaction_tools = [
        ToolContract(
            id="browser.click", name="Click",
            description="Click an element on the page using a CSS selector",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector for the element"},
                "timeout": {"type": "integer", "description": "Wait timeout in ms", "default": 10000},
            },
            returns={"selector": {"type": "string"}, "clicked": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.click"],
            tags=["interaction", "click"],
        ),
        ToolContract(
            id="browser.double_click", name="Double Click",
            description="Double-click an element on the page",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector for the element"},
                "timeout": {"type": "integer", "description": "Wait timeout in ms", "default": 10000},
            },
            returns={"selector": {"type": "string"}, "double_clicked": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.double_click"],
            tags=["interaction", "double_click"],
        ),
        ToolContract(
            id="browser.right_click", name="Right Click",
            description="Right-click an element on the page",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector for the element"},
                "timeout": {"type": "integer", "description": "Wait timeout in ms", "default": 10000},
            },
            returns={"selector": {"type": "string"}, "right_clicked": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.right_click"],
            tags=["interaction", "right_click"],
        ),
        ToolContract(
            id="browser.hover", name="Hover",
            description="Hover over an element on the page",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector for the element"},
                "timeout": {"type": "integer", "description": "Wait timeout in ms", "default": 10000},
            },
            returns={"selector": {"type": "string"}, "hovered": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.hover"],
            tags=["interaction", "hover"],
        ),
        ToolContract(
            id="browser.type_text", name="Type Text",
            description="Type text into an input field",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector for the input"},
                "text": {"type": "string", "description": "Text to type"},
                "clear_first": {"type": "boolean", "description": "Clear field before typing", "default": True},
                "timeout": {"type": "integer", "description": "Wait timeout in ms", "default": 10000},
            },
            returns={"selector": {"type": "string"}, "text_length": {"type": "integer"}, "typed": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.type_text"],
            tags=["interaction", "type"],
        ),
        ToolContract(
            id="browser.press_key", name="Press Key",
            description="Press a keyboard key (e.g. Enter, Tab, Escape)",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "key": {"type": "string", "description": "Key to press (e.g. Enter, Tab, Escape, ArrowDown)"},
                "selector": {"type": "string", "description": "Optional CSS selector to focus before pressing", "required": False},
            },
            returns={"key": {"type": "string"}, "pressed": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.press_key"],
            tags=["interaction", "keyboard"],
        ),
        ToolContract(
            id="browser.select_option", name="Select Option",
            description="Select option(s) from a dropdown/select element",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector for the select element"},
                "values": {"type": "array", "description": "Values to select (string array)"},
                "timeout": {"type": "integer", "description": "Wait timeout in ms", "default": 10000},
            },
            returns={"selector": {"type": "string"}, "values": {"type": "array"}, "selected": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="browser",
            capabilities=["browser.select_option"],
            tags=["interaction", "select"],
        ),
        ToolContract(
            id="browser.upload_file", name="Upload File",
            description="Upload a file through a file input element. Requires confirmation.",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector for the file input"},
                "file_path": {"type": "string", "description": "Absolute path to the file to upload"},
                "timeout": {"type": "integer", "description": "Wait timeout in ms", "default": 30000},
            },
            returns={"success": {"type": "boolean"}, "file_name": {"type": "string"}},
            permission_level=PermissionLevel.SENSITIVE,
            requires_confirmation=True,
            category="browser",
            capabilities=["browser.upload_file"],
            tags=["interaction", "upload"],
        ),
        ToolContract(
            id="browser.download_file", name="Download File",
            description="Download a file from the current page or a specific URL. Requires confirmation.",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "url": {"type": "string", "description": "URL to download from (optional, uses current page if omitted)", "required": False},
                "timeout": {"type": "integer", "description": "Download timeout in ms", "default": 60000},
            },
            returns={"file_path": {"type": "string"}, "file_name": {"type": "string"}, "file_size": {"type": "integer"}, "success": {"type": "boolean"}},
            permission_level=PermissionLevel.SENSITIVE,
            requires_confirmation=True,
            category="browser",
            capabilities=["browser.download_file"],
            tags=["interaction", "download"],
        ),
    ]

    extraction_tools = [
        ToolContract(
            id="browser.extract_text", name="Extract Text",
            description="Extract visible text from the page or a specific element",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector (default: body for full page)", "default": "body"},
            },
            returns={"text": {"type": "string"}, "length": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.extract_text"],
            tags=["extraction", "text"],
        ),
        ToolContract(
            id="browser.extract_links", name="Extract Links",
            description="Extract all links from the current page",
            parameters={"instance_id": {"type": "string", "description": "Browser instance ID"}},
            returns={"links": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.extract_links"],
            tags=["extraction", "links"],
        ),
        ToolContract(
            id="browser.extract_tables", name="Extract Tables",
            description="Extract all HTML tables from the current page as arrays",
            parameters={"instance_id": {"type": "string", "description": "Browser instance ID"}},
            returns={"tables": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.extract_tables"],
            tags=["extraction", "tables"],
        ),
        ToolContract(
            id="browser.extract_forms", name="Extract Forms",
            description="Extract all form structures from the current page with input metadata",
            parameters={"instance_id": {"type": "string", "description": "Browser instance ID"}},
            returns={"forms": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.extract_forms"],
            tags=["extraction", "forms"],
        ),
        ToolContract(
            id="browser.capture_page", name="Capture Page Screenshot",
            description="Take a screenshot of the current page",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "full_page": {"type": "boolean", "description": "Capture full page (including scroll)", "default": True},
            },
            returns={"screenshot_base64": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}, "size_bytes": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.capture_page"],
            tags=["extraction", "screenshot"],
        ),
        ToolContract(
            id="browser.capture_element", name="Capture Element Screenshot",
            description="Take a screenshot of a specific element on the page",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector for the element"},
                "timeout": {"type": "integer", "description": "Wait timeout in ms", "default": 10000},
            },
            returns={"screenshot_base64": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.capture_element"],
            tags=["extraction", "screenshot"],
        ),
    ]

    automation_tools = [
        ToolContract(
            id="browser.wait_for_element", name="Wait for Element",
            description="Wait for an element to appear on the page",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "selector": {"type": "string", "description": "CSS selector to wait for"},
                "timeout": {"type": "integer", "description": "Timeout in ms", "default": 30000},
                "state": {"type": "string", "description": "Element state: visible, hidden, attached, detached", "default": "visible"},
            },
            returns={"found": {"type": "boolean"}, "selector": {"type": "string"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.wait_for_element"],
            tags=["automation", "wait"],
        ),
        ToolContract(
            id="browser.wait_for_text", name="Wait for Text",
            description="Wait for specific text to appear on the page",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "text": {"type": "string", "description": "Text to wait for"},
                "timeout": {"type": "integer", "description": "Timeout in ms", "default": 30000},
            },
            returns={"found": {"type": "boolean"}, "text": {"type": "string"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.wait_for_text"],
            tags=["automation", "wait"],
        ),
        ToolContract(
            id="browser.execute_javascript", name="Execute JavaScript",
            description="Execute JavaScript in the page context. Requires confirmation.",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "script": {"type": "string", "description": "JavaScript code to execute"},
            },
            returns={"result": {"type": "any"}, "duration_ms": {"type": "number"}},
            permission_level=PermissionLevel.SENSITIVE,
            requires_confirmation=True,
            category="browser",
            capabilities=["browser.execute_javascript"],
            tags=["automation", "javascript"],
        ),
        ToolContract(
            id="browser.evaluate_expression", name="Evaluate Expression",
            description="Evaluate a JavaScript expression in the page context. Requires confirmation.",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "expression": {"type": "string", "description": "JavaScript expression to evaluate"},
            },
            returns={"result": {"type": "any"}, "duration_ms": {"type": "number"}},
            permission_level=PermissionLevel.SENSITIVE,
            requires_confirmation=True,
            category="browser",
            capabilities=["browser.evaluate_expression"],
            tags=["automation", "javascript"],
        ),
    ]

    vision_tools = [
        ToolContract(
            id="browser.vision_verify", name="Vision Verify",
            description="Use Vision AI to analyze the current page for UI verification and element detection",
            parameters={
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "description": {"type": "string", "description": "Optional description of what to verify", "required": False},
            },
            returns={"available": {"type": "boolean"}, "elements": {"type": "array"}, "layout": {"type": "array"}},
            permission_level=PermissionLevel.READ,
            category="browser",
            capabilities=["browser.vision_verify"],
            tags=["vision", "verify"],
        ),
    ]

    all_tools = browser_tools + tab_tools + navigation_tools + interaction_tools + extraction_tools + automation_tools + vision_tools

    def _wrap(handler_fn, eng=None):
        async def wrapped(params: dict) -> ToolResult:
            return await handler_fn(params, eng or engine, event_bus)
        return wrapped

    browser_handlers = [
        _wrap(_browser_launch, engine),
        _wrap(_browser_close, engine),
        _wrap(_browser_list, engine),
        _wrap(_browser_focus, engine),
    ]
    tab_handlers = [
        _wrap(_tab_new, engine),
        _wrap(_tab_close, engine),
        _wrap(_tab_switch, engine),
        _wrap(_tab_list, engine),
    ]
    navigation_handlers = [
        _wrap(_navigate, engine),
        _wrap(_reload, engine),
        _wrap(_back, engine),
        _wrap(_forward, engine),
        _wrap(_wait_for_page, engine),
    ]
    interaction_handlers = [
        _wrap(_click, engine),
        _wrap(_double_click, engine),
        _wrap(_right_click, engine),
        _wrap(_hover, engine),
        _wrap(_type_text, engine),
        _wrap(_press_key, engine),
        _wrap(_select_option, engine),
        _wrap(_upload_file, engine),
        _wrap(_download_file, engine),
    ]
    extraction_handlers = [
        _wrap(_extract_text, engine),
        _wrap(_extract_links, engine),
        _wrap(_extract_tables, engine),
        _wrap(_extract_forms, engine),
        _wrap(_capture_page, engine),
        _wrap(_capture_element, engine),
    ]
    automation_handlers = [
        _wrap(_wait_for_element, engine),
        _wrap(_wait_for_text, engine),
        _wrap(_execute_javascript, engine),
        _wrap(_evaluate_expression, engine),
    ]
    vision_handlers = [
        _wrap(_vision_verify, engine),
    ]

    all_handlers = browser_handlers + tab_handlers + navigation_handlers + interaction_handlers + extraction_handlers + automation_handlers + vision_handlers

    for contract, handler in zip(all_tools, all_handlers):
        asyncio.create_task(tm.register_tool(contract, handler))
