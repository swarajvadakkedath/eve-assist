"""Tests for browser tool registration and handler functions."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.tools.browser_tools import register_browser_tools
from aios.core.tool_manager import ToolManager, ToolContract
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.event_bus import EventBus


@pytest.fixture
def pm():
    return PermissionManager()


@pytest.fixture
def tm(pm):
    return ToolManager(pm)


@pytest.fixture
async def eb():
    bus = EventBus(max_retries=1, retry_delay=0.01)
    await bus.start()
    yield bus
    await bus.stop()


def _fake_tab_info(page_id, title, url, active):
    return type("TabInfo", (), {"page_id": page_id, "title": title, "url": url, "active": active})()


def _fake_nav_result(url, title, status_code):
    return type("NavResult", (), {"url": url, "title": title, "status_code": status_code})()


@pytest.fixture
def browser_engine():
    engine = MagicMock()
    engine.launch = AsyncMock(return_value="chromium_abc123")
    engine.close = AsyncMock(return_value=True)
    engine.list_instances = AsyncMock(return_value=[
        {"instance_id": "chromium_abc123", "browser_type": "chromium", "page_count": 1}
    ])
    engine.focus = AsyncMock(return_value=True)
    engine.new_tab = AsyncMock(return_value="page_def456")
    engine.close_tab = AsyncMock(return_value=True)
    engine.switch_tab = AsyncMock(return_value=True)
    engine.list_tabs = AsyncMock(return_value=[_fake_tab_info("pg1", "Title", "https://ex.com", True)])
    engine.navigate = AsyncMock(return_value=_fake_nav_result("https://ex.com", "Title", 200))
    engine.reload = AsyncMock(return_value=_fake_nav_result("https://ex.com", "Title", 200))
    engine.go_back = AsyncMock(return_value=_fake_nav_result("https://ex.com/back", "Back", 200))
    engine.go_forward = AsyncMock(return_value=_fake_nav_result("https://ex.com/fwd", "Fwd", 200))
    engine.wait_for_page = AsyncMock(return_value=_fake_nav_result("https://ex.com", "Title", 200))
    engine.click = AsyncMock(return_value=True)
    engine.double_click = AsyncMock(return_value=True)
    engine.right_click = AsyncMock(return_value=True)
    engine.hover = AsyncMock(return_value=True)
    engine.type_text = AsyncMock(return_value=True)
    engine.press_key = AsyncMock(return_value=True)
    engine.select_option = AsyncMock(return_value=True)
    engine.upload_file = AsyncMock(return_value=type("Up", (), {"success": True, "file_path": "C:\\t.txt", "error": None})())
    engine.download_file = AsyncMock(return_value=type("Dl", (), {"success": True, "file_path": "C:\\d.txt", "mime_type": "text/plain", "size": 100})())
    engine.extract_text = AsyncMock(return_value=type("Tx", (), {"text": "Hello", "count": 1})())
    engine.extract_links = AsyncMock(return_value=type("Lk", (), {"items": [{"href": "https://ex.com"}], "count": 1})())
    engine.extract_tables = AsyncMock(return_value=type("Tb", (), {"items": [[["A"]]], "count": 1})())
    engine.extract_forms = AsyncMock(return_value=type("Fm", (), {"items": [{"selector": "form"}], "count": 1})())
    engine.capture_page = AsyncMock(return_value=type("Sc", (), {"image_data": b"d", "width": 1280, "height": 720})())
    engine.capture_element = AsyncMock(return_value=type("Sc", (), {"image_data": b"d", "width": 100, "height": 50})())
    engine.wait_for_element = AsyncMock(return_value=True)
    engine.wait_for_text = AsyncMock(return_value=True)
    engine.vision_verify = AsyncMock(return_value={"available": True, "elements": []})
    engine.execute_javascript = AsyncMock(return_value=type("Js", (), {"success": True, "result": 42, "error": None})())
    engine.evaluate_expression = AsyncMock(return_value=type("Js", (), {"success": True, "result": "hi", "error": None})())
    engine.shutdown = AsyncMock()
    return engine


@pytest.mark.asyncio
async def test_register_browser_tools(tm, browser_engine):
    register_browser_tools(tm, browser_engine)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    assert len(all_tools) >= 28


@pytest.mark.asyncio
async def test_all_tools_have_contracts(tm, browser_engine):
    register_browser_tools(tm, browser_engine)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    for t in all_tools:
        assert t.name
        assert t.description
        assert t.permission_level is not None


@pytest.mark.asyncio
async def test_tool_categories(tm, browser_engine):
    register_browser_tools(tm, browser_engine)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    all_ids = [t.id for t in all_tools]
    assert "browser.launch" in all_ids
    assert "tab.new" in all_ids
    assert "browser.navigate" in all_ids
    assert "browser.click" in all_ids
    assert "browser.extract_text" in all_ids
    assert "browser.wait_for_element" in all_ids
    assert "browser.vision_verify" in all_ids


@pytest.mark.asyncio
async def test_permission_levels_valid(tm, browser_engine):
    register_browser_tools(tm, browser_engine)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    for t in all_tools:
        assert t.permission_level in (PermissionLevel.READ, PermissionLevel.SAFE, PermissionLevel.WORKSPACE, PermissionLevel.SENSITIVE)


@pytest.mark.asyncio
async def test_requires_confirmation_for_sensitive(tm, browser_engine):
    register_browser_tools(tm, browser_engine)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    sensitive = [t for t in all_tools if t.permission_level == PermissionLevel.SENSITIVE]
    for t in sensitive:
        assert t.requires_confirmation is True
    assert len(sensitive) >= 3


@pytest.mark.asyncio
async def test_tool_name_format(tm, browser_engine):
    register_browser_tools(tm, browser_engine)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    for t in all_tools:
        assert "." in t.id, f"Tool id missing dot separator: {t.id}"
        assert t.id.count(".") == 1, f"Tool id should have exactly one dot: {t.id}"


@pytest.mark.asyncio
async def test_browser_tool_happy_path(tm, browser_engine):
    register_browser_tools(tm, browser_engine)
    await asyncio.sleep(0.05)
    for tool_id, (contract, handler) in tm._tools.items():
        try:
            params = {}
            for param in contract.parameters.get("properties", {}):
                if param == "instance_id":
                    params[param] = "chromium_abc123"
                elif param == "url":
                    params[param] = "https://example.com"
                elif param == "selector":
                    params[param] = "#test"
                elif param == "text":
                    params[param] = "hello"
                elif param == "timeout":
                    params[param] = 5000
                elif param == "key":
                    params[param] = "Enter"
                elif param == "values":
                    params[param] = ["opt1"]
                elif param == "file_path":
                    params[param] = "C:\\test.txt"
                elif param == "expression":
                    params[param] = "1 + 1"
                elif param == "javascript":
                    params[param] = "1 + 1"
                elif param in ("page_id", "tab_id"):
                    params[param] = "page_abc"
                elif param == "headless":
                    params[param] = True
                elif param == "browser_type":
                    params[param] = "chromium"
                elif param == "save_path":
                    params[param] = "C:\\downloads"
            result = await handler(params)
            assert result is not None, f"{tool_id} returned None"
        except Exception as exc:
            pytest.fail(f"{tool_id} handler raised: {exc}")
