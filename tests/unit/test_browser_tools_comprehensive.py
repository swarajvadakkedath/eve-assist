"""Comprehensive error-path, edge-case, and integration tests for browser_tools."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from aios.tools.browser_tools import register_browser_tools
from aios.core.tool_manager import ToolManager, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.event_bus import EventBus


# ── Fixtures ──

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


def _make_engine():
    e = MagicMock()
    e.launch = AsyncMock(return_value="chromium_abc123")
    e.close = AsyncMock(return_value=True)
    e.list_instances = AsyncMock(return_value=[{"instance_id": "c123", "browser_type": "chromium", "page_count": 1}])
    e.focus = AsyncMock(return_value=True)
    e.new_tab = AsyncMock(return_value="page_def456")
    e.close_tab = AsyncMock(return_value=True)
    e.switch_tab = AsyncMock(return_value=True)
    e.list_tabs = AsyncMock(return_value=[MagicMock(page_id="pg1", title="T", url="https://ex.com", index=0)])
    e.navigate = AsyncMock(return_value=MagicMock(url="https://ex.com", title="T", status_code=200, duration_ms=100.0))
    e.reload = AsyncMock(return_value=MagicMock(url="https://ex.com", title="T", status_code=200, duration_ms=50.0))
    e.go_back = AsyncMock(return_value=MagicMock(url="https://ex.com/b", title="B", status_code=200, duration_ms=50.0))
    e.go_forward = AsyncMock(return_value=MagicMock(url="https://ex.com/f", title="F", status_code=200, duration_ms=50.0))
    e.wait_for_page = AsyncMock(return_value=MagicMock(url="https://ex.com", title="T"))
    e.click = AsyncMock(return_value=True)
    e.double_click = AsyncMock(return_value=True)
    e.right_click = AsyncMock(return_value=True)
    e.hover = AsyncMock(return_value=True)
    e.type_text = AsyncMock(return_value=True)
    e.press_key = AsyncMock(return_value=True)
    e.select_option = AsyncMock(return_value=True)
    e.upload_file = AsyncMock(return_value=MagicMock(success=True, file_name="f.txt", error=None))
    e.download_file = AsyncMock(return_value=MagicMock(success=True, file_path="C:\\d.txt", file_name="d.txt", file_size=100, error=None))
    e.extract_text = AsyncMock(return_value=MagicMock(text="Hello", count=5, error=None))
    e.extract_links = AsyncMock(return_value=MagicMock(items=[{"href": "https://ex.com"}], count=1, error=None))
    e.extract_tables = AsyncMock(return_value=MagicMock(items=[[["A"]]], count=1, error=None))
    e.extract_forms = AsyncMock(return_value=MagicMock(items=[{"selector": "form"}], count=1, error=None))
    e.capture_page = AsyncMock(return_value=MagicMock(image_data=b"data", width=1280, height=720, format="png", error=None))
    e.capture_element = AsyncMock(return_value=MagicMock(image_data=b"el", width=100, height=50, error=None))
    e.wait_for_element = AsyncMock(return_value=True)
    e.wait_for_text = AsyncMock(return_value=True)
    e.execute_javascript = AsyncMock(return_value=MagicMock(success=True, result=42, error=None, duration_ms=5.0))
    e.evaluate_expression = AsyncMock(return_value=MagicMock(success=True, result="hi", error=None, duration_ms=3.0))
    e.vision_verify = AsyncMock(return_value={"available": True, "elements": [], "layout": [], "text_regions": []})
    e.shutdown = AsyncMock()
    return e


@pytest.fixture
def engine():
    return _make_engine()


async def _register_async(tm, engine, vision=None, event_bus=None):
    register_browser_tools(tm, engine, vision_engine=vision, event_bus=event_bus)
    await asyncio.sleep(0.2)


async def _get_tool(tm, tool_id):
    await asyncio.sleep(0.05)
    for c, h in tm._tools.values():
        if c.id == tool_id:
            return c, h
    return None, None


# ── Registration edge cases ──

class TestRegistration:

    @pytest.mark.asyncio
    async def test_register_with_vision_engine(self, tm, engine):
        vision = MagicMock()
        await _register_async(tm, engine, vision=vision)
        tools = await tm.list_tools()
        assert len(tools) >= 28

    @pytest.mark.asyncio
    async def test_register_with_event_bus(self, tm, engine, eb):
        await _register_async(tm, engine, event_bus=eb)
        tools = await tm.list_tools()
        assert len(tools) >= 28

    @pytest.mark.asyncio
    async def test_register_all_ids_unique(self, tm, engine):
        await _register_async(tm, engine)
        ids = [c.id for c, _ in tm._tools.values()]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_register_28_tools(self, tm, engine):
        await _register_async(tm, engine)
        tools = await tm.list_tools()
        assert len(tools) >= 28

    @pytest.mark.asyncio
    async def test_contracts_have_tags(self, tm, engine):
        await _register_async(tm, engine)
        for c, _ in tm._tools.values():
            assert c.tags, f"{c.id} missing tags"
            assert isinstance(c.tags, list)

    @pytest.mark.asyncio
    async def test_contracts_have_capabilities(self, tm, engine):
        await _register_async(tm, engine)
        for c, _ in tm._tools.values():
            assert c.capabilities, f"{c.id} missing capabilities"
            assert isinstance(c.capabilities, list)

    @pytest.mark.asyncio
    async def test_contracts_have_category(self, tm, engine):
        await _register_async(tm, engine)
        for c, _ in tm._tools.values():
            assert c.category is not None


# ── Handler Error Paths ──

class TestBrowserLifecycleErrors:

    @pytest.mark.asyncio
    async def test_launch_engine_error(self, tm, engine):
        engine.launch.side_effect = Exception("Launch failed")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.launch")
        result = await h({})
        assert result.success is False
        assert "Launch failed" in result.error

    @pytest.mark.asyncio
    async def test_launch_missing_params_use_defaults(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.launch")
        result = await h({})
        assert result.success is True
        engine.launch.assert_called_once_with(browser_type="chromium", headless=True, proxy=None, args=None)

    @pytest.mark.asyncio
    async def test_close_missing_instance_id(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.close")
        result = await h({})
        assert result.success is False
        assert "instance_id is required" in result.error

    @pytest.mark.asyncio
    async def test_close_engine_error(self, tm, engine):
        engine.close.side_effect = Exception("Close failed")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.close")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_list_engine_error(self, tm, engine):
        engine.list_instances.side_effect = Exception("List failed")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.list")
        result = await h({})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_focus_engine_error(self, tm, engine):
        engine.focus.side_effect = Exception("Focus failed")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.focus")
        result = await h({"instance_id": "c123"})
        assert result.success is False


class TestTabErrors:

    @pytest.mark.asyncio
    async def test_new_tab_engine_error(self, tm, engine):
        engine.new_tab.side_effect = Exception("Tab error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "tab.new")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_close_tab_engine_error(self, tm, engine):
        engine.close_tab.side_effect = Exception("Close tab error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "tab.close")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_switch_tab_engine_error(self, tm, engine):
        engine.switch_tab.side_effect = Exception("Switch error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "tab.switch")
        result = await h({"instance_id": "c123", "page_id": "pg1"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_list_tabs_engine_error(self, tm, engine):
        engine.list_tabs.side_effect = Exception("List error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "tab.list")
        result = await h({"instance_id": "c123"})
        assert result.success is False


class TestNavigationErrors:

    @pytest.mark.asyncio
    async def test_navigate_engine_error(self, tm, engine):
        engine.navigate.side_effect = Exception("Nav error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.navigate")
        result = await h({"instance_id": "c123", "url": "https://ex.com"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_reload_engine_error(self, tm, engine):
        engine.reload.side_effect = Exception("Reload error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.reload")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_back_engine_error(self, tm, engine):
        engine.go_back.side_effect = Exception("Back error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.back")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_forward_engine_error(self, tm, engine):
        engine.go_forward.side_effect = Exception("Forward error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.forward")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_wait_for_page_engine_error(self, tm, engine):
        engine.wait_for_page.side_effect = Exception("Wait error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.wait_for_page")
        result = await h({"instance_id": "c123"})
        assert result.success is False


class TestInteractionErrors:

    @pytest.mark.asyncio
    async def test_click_engine_error(self, tm, engine):
        engine.click.side_effect = Exception("Click error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.click")
        result = await h({"instance_id": "c123", "selector": "#btn"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_double_click_engine_error(self, tm, engine):
        engine.double_click.side_effect = Exception("Dbl error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.double_click")
        result = await h({"instance_id": "c123", "selector": "#btn"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_right_click_engine_error(self, tm, engine):
        engine.right_click.side_effect = Exception("Right error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.right_click")
        result = await h({"instance_id": "c123", "selector": "#btn"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_hover_engine_error(self, tm, engine):
        engine.hover.side_effect = Exception("Hover error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.hover")
        result = await h({"instance_id": "c123", "selector": "#btn"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_type_text_engine_error(self, tm, engine):
        engine.type_text.side_effect = Exception("Type error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.type_text")
        result = await h({"instance_id": "c123", "selector": "#input", "text": "hi"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_press_key_engine_error(self, tm, engine):
        engine.press_key.side_effect = Exception("Key error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.press_key")
        result = await h({"instance_id": "c123", "key": "Enter"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_select_option_engine_error(self, tm, engine):
        engine.select_option.side_effect = Exception("Select error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.select_option")
        result = await h({"instance_id": "c123", "selector": "#sel", "values": ["a"]})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_upload_file_engine_error(self, tm, engine):
        engine.upload_file.side_effect = Exception("Upload error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.upload_file")
        result = await h({"instance_id": "c123", "selector": "#file", "file_path": "C:\\t.txt"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_download_file_engine_error(self, tm, engine):
        engine.download_file.side_effect = Exception("Download error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.download_file")
        result = await h({"instance_id": "c123"})
        assert result.success is False


class TestExtractionErrors:

    @pytest.mark.asyncio
    async def test_extract_text_engine_error(self, tm, engine):
        engine.extract_text.side_effect = Exception("Extract error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.extract_text")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_extract_links_engine_error(self, tm, engine):
        engine.extract_links.side_effect = Exception("Links error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.extract_links")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_extract_tables_engine_error(self, tm, engine):
        engine.extract_tables.side_effect = Exception("Tables error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.extract_tables")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_extract_forms_engine_error(self, tm, engine):
        engine.extract_forms.side_effect = Exception("Forms error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.extract_forms")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_capture_page_engine_error(self, tm, engine):
        engine.capture_page.side_effect = Exception("Capture error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.capture_page")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_capture_element_engine_error(self, tm, engine):
        engine.capture_element.side_effect = Exception("Element error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.capture_element")
        result = await h({"instance_id": "c123", "selector": "#el"})
        assert result.success is False


class TestAutomationErrors:

    @pytest.mark.asyncio
    async def test_wait_for_element_engine_error(self, tm, engine):
        engine.wait_for_element.side_effect = Exception("Wait error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.wait_for_element")
        result = await h({"instance_id": "c123", "selector": "#el"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_wait_for_text_engine_error(self, tm, engine):
        engine.wait_for_text.side_effect = Exception("Text error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.wait_for_text")
        result = await h({"instance_id": "c123", "text": "hello"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_javascript_engine_error(self, tm, engine):
        engine.execute_javascript.side_effect = Exception("JS error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.execute_javascript")
        result = await h({"instance_id": "c123", "script": "1+1"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_evaluate_expression_engine_error(self, tm, engine):
        engine.evaluate_expression.side_effect = Exception("Eval error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.evaluate_expression")
        result = await h({"instance_id": "c123", "expression": "1+1"})
        assert result.success is False


class TestVisionErrors:

    @pytest.mark.asyncio
    async def test_vision_verify_engine_error(self, tm, engine):
        engine.vision_verify.side_effect = Exception("Vision error")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.vision_verify")
        result = await h({"instance_id": "c123"})
        assert result.success is False


# ── Handler result structure ──

class TestHandlerResults:

    @pytest.mark.asyncio
    async def test_browser_launch_result(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.launch")
        result = await h({"browser_type": "chromium", "headless": True})
        assert result.success is True
        assert "instance_id" in result.data

    @pytest.mark.asyncio
    async def test_browser_list_result(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.list")
        result = await h({})
        assert result.success is True
        assert "instances" in result.data
        assert "count" in result.data

    @pytest.mark.asyncio
    async def test_tab_list_result(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "tab.list")
        result = await h({"instance_id": "c123"})
        assert result.success is True
        assert "tabs" in result.data
        assert "count" in result.data
        assert len(result.data["tabs"]) == 1

    @pytest.mark.asyncio
    async def test_capture_page_result(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.capture_page")
        result = await h({"instance_id": "c123"})
        assert result.success is True
        assert "screenshot_base64" in result.data
        assert result.data["size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_capture_element_result(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.capture_element")
        result = await h({"instance_id": "c123", "selector": "#el"})
        assert result.success is True
        assert "screenshot_base64" in result.data

    @pytest.mark.asyncio
    async def test_upload_file_result(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.upload_file")
        result = await h({"instance_id": "c123", "selector": "#f", "file_path": "C:\\t.txt"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_download_file_result(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.download_file")
        result = await h({"instance_id": "c123"})
        assert result.success is True
        assert "file_path" in result.data

    @pytest.mark.asyncio
    async def test_extract_text_result(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.extract_text")
        result = await h({"instance_id": "c123"})
        assert result.success is True
        assert result.data["length"] == 5

    @pytest.mark.asyncio
    async def test_type_text_returns_length(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.type_text")
        result = await h({"instance_id": "c123", "selector": "#in", "text": "hello"})
        assert result.success is True
        assert result.data["text_length"] == 5

    @pytest.mark.asyncio
    async def test_execute_javascript_result(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.execute_javascript")
        result = await h({"instance_id": "c123", "script": "1+1"})
        assert result.success is True
        assert result.data["result"] == 42


# ── Permission Levels ──

class TestPermissionLevels:

    @pytest.mark.asyncio
    async def test_browser_list_is_read(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.list")
        assert c.permission_level == PermissionLevel.READ

    @pytest.mark.asyncio
    async def test_browser_launch_is_workspace(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.launch")
        assert c.permission_level == PermissionLevel.WORKSPACE

    @pytest.mark.asyncio
    async def test_upload_file_is_sensitive(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.upload_file")
        assert c.permission_level == PermissionLevel.SENSITIVE

    @pytest.mark.asyncio
    async def test_download_file_is_sensitive(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.download_file")
        assert c.permission_level == PermissionLevel.SENSITIVE

    @pytest.mark.asyncio
    async def test_execute_javascript_is_sensitive(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.execute_javascript")
        assert c.permission_level == PermissionLevel.SENSITIVE

    @pytest.mark.asyncio
    async def test_extract_text_is_read(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.extract_text")
        assert c.permission_level == PermissionLevel.READ

    @pytest.mark.asyncio
    async def test_navigate_is_workspace(self, tm, engine):
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.navigate")
        assert c.permission_level == PermissionLevel.WORKSPACE


# ── Extraction error propagation (engine returns result with error) ──

class TestToolErrorPropagation:

    @pytest.mark.asyncio
    async def test_extract_text_with_result_error(self, tm, engine):
        engine.extract_text.return_value = MagicMock(text="", count=0, error="Page crashed")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.extract_text")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_capture_page_with_result_error(self, tm, engine):
        engine.capture_page.return_value = MagicMock(image_data=b"", width=0, height=0, error="Screenshot failed")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.capture_page")
        result = await h({"instance_id": "c123"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_download_file_with_result_error(self, tm, engine):
        engine.download_file.return_value = MagicMock(success=False, error="Download failed")
        await _register_async(tm, engine)
        c, h = await _get_tool(tm, "browser.download_file")
        result = await h({"instance_id": "c123"})
        assert result.success is False
