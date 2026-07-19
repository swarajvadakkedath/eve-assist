"""Tests for BrowserEngine with mocked Playwright."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime

from aios.browser.engine import BrowserEngine, BrowserError


@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.title = AsyncMock(return_value="Test Page")
    page.url = "https://example.com"
    page.viewport_size = {"width": 1280, "height": 720}
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    page.evaluate = AsyncMock(return_value=[])
    page.goto = AsyncMock()
    goto_response = MagicMock()
    goto_response.status = 200
    page.goto.return_value = goto_response
    page.reload = AsyncMock()
    page.reload.return_value.status = 200
    page.go_back = AsyncMock()
    page.go_back.return_value.status = 200
    page.go_forward = AsyncMock()
    page.go_forward.return_value.status = 200
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.click = AsyncMock()
    page.dblclick = AsyncMock()
    page.hover = AsyncMock()
    page.fill = AsyncMock()
    page.type = AsyncMock()
    page.press = AsyncMock()
    page.keyboard = AsyncMock()
    page.keyboard.press = AsyncMock()
    page.select_option = AsyncMock()
    page.bring_to_front = AsyncMock()
    page.close = AsyncMock()
    page.query_selector = AsyncMock()
    page.inner_text = AsyncMock(return_value="Hello World")
    page.wait_for_function = AsyncMock()
    page.wait_for_event = AsyncMock()
    page.wait_for_event.return_value.__aenter__ = AsyncMock()
    page.wait_for_event.return_value.__aenter__.return_value = AsyncMock()
    return page


@pytest.fixture
def mock_context(mock_page):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_page)
    return context


@pytest.fixture
def mock_browser(mock_context):
    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=mock_context)
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_playwright(mock_browser):
    pw = AsyncMock()
    pw.chromium = AsyncMock()
    pw.chromium.launch = AsyncMock(return_value=mock_browser)
    pw.firefox = AsyncMock()
    pw.firefox.launch = AsyncMock(return_value=mock_browser)
    pw.stop = AsyncMock()
    return pw


@pytest.fixture
def engine(mock_playwright):
    with patch("playwright.async_api.async_playwright") as mock_ap:
        mock_cm = AsyncMock()
        mock_cm.start = AsyncMock(return_value=mock_playwright)
        mock_ap.return_value = mock_cm
        eng = BrowserEngine()
        yield eng


@pytest.mark.asyncio
async def test_launch_chromium(engine, mock_playwright, mock_browser, mock_page):
    instance_id = await engine.launch(browser_type="chromium")
    assert instance_id.startswith("chromium_")
    assert len(instance_id) > 10
    mock_playwright.chromium.launch.assert_called_once()
    mock_browser.new_context.assert_called_once()


@pytest.mark.asyncio
async def test_launch_chrome(engine, mock_playwright, mock_browser):
    instance_id = await engine.launch(browser_type="chrome")
    assert instance_id.startswith("chrome_")
    call_kwargs = mock_playwright.chromium.launch.call_args.kwargs
    assert call_kwargs.get("channel") == "chrome"


@pytest.mark.asyncio
async def test_launch_edge(engine, mock_playwright, mock_browser):
    instance_id = await engine.launch(browser_type="edge")
    assert instance_id.startswith("edge_")
    call_kwargs = mock_playwright.chromium.launch.call_args.kwargs
    assert call_kwargs.get("channel") == "msedge"


@pytest.mark.asyncio
async def test_launch_firefox(engine, mock_playwright, mock_browser):
    instance_id = await engine.launch(browser_type="firefox")
    assert instance_id.startswith("firefox_")
    mock_playwright.firefox.launch.assert_called_once()


@pytest.mark.asyncio
async def test_launch_unsupported_browser(engine):
    with pytest.raises(BrowserError, match="Unsupported browser type"):
        await engine.launch(browser_type="safari")


@pytest.mark.asyncio
async def test_launch_headless_default(engine, mock_playwright, mock_browser):
    await engine.launch(browser_type="chromium")
    call_kwargs = mock_playwright.chromium.launch.call_args.kwargs
    assert call_kwargs.get("headless") is True


@pytest.mark.asyncio
async def test_launch_visible(engine, mock_playwright, mock_browser):
    await engine.launch(browser_type="chromium", headless=False)
    call_kwargs = mock_playwright.chromium.launch.call_args.kwargs
    assert call_kwargs.get("headless") is False


@pytest.mark.asyncio
async def test_close_browser(engine):
    instance_id = await engine.launch()
    result = await engine.close(instance_id)
    assert result is True
    assert instance_id not in engine._instances


@pytest.mark.asyncio
async def test_close_nonexistent(engine):
    with pytest.raises(BrowserError, match="not found"):
        await engine.close("nonexistent")


@pytest.mark.asyncio
async def test_list_instances_empty(engine):
    instances = await engine.list_instances()
    assert instances == []


@pytest.mark.asyncio
async def test_list_instances_after_launch(engine):
    iid = await engine.launch(browser_type="chromium")
    instances = await engine.list_instances()
    assert len(instances) == 1
    assert instances[0]["instance_id"] == iid
    assert instances[0]["browser_type"] == "chromium"
    assert instances[0]["page_count"] == 1


@pytest.mark.asyncio
async def test_list_instances_multiple(engine):
    iid1 = await engine.launch(browser_type="chromium")
    iid2 = await engine.launch(browser_type="firefox")
    instances = await engine.list_instances()
    assert len(instances) == 2


@pytest.mark.asyncio
async def test_focus(engine):
    iid = await engine.launch()
    result = await engine.focus(iid)
    assert result is True


@pytest.mark.asyncio
async def test_new_tab(engine, mock_context):
    iid = await engine.launch()
    page_id = await engine.new_tab(iid)
    assert page_id is not None
    assert page_id.startswith("page_")
    assert mock_context.new_page.called


@pytest.mark.asyncio
async def test_new_tab_with_url(engine, mock_context, mock_page):
    iid = await engine.launch()
    page_id = await engine.new_tab(iid, url="https://example.com")
    mock_page.goto.assert_called_once_with("https://example.com", timeout=30000, wait_until="domcontentloaded")


@pytest.mark.asyncio
async def test_close_tab(engine, mock_page):
    iid = await engine.launch()
    tabs_before = len(engine._instances[iid]["pages"])
    pid = list(engine._instances[iid]["pages"].keys())[0]
    result = await engine.close_tab(iid, pid)
    assert result is True
    mock_page.close.assert_called_once()


@pytest.mark.asyncio
async def test_switch_tab(engine, mock_context, mock_page):
    iid = await engine.launch()
    pid2 = await engine.new_tab(iid)
    await engine.switch_tab(iid, pid2)
    assert engine._instances[iid]["active_page_id"] == pid2
    mock_page.bring_to_front.assert_called_once()


@pytest.mark.asyncio
async def test_list_tabs(engine):
    iid = await engine.launch()
    tabs = await engine.list_tabs(iid)
    assert len(tabs) == 1
    assert tabs[0].title == "Test Page"
    assert tabs[0].url == "https://example.com"


@pytest.mark.asyncio
async def test_list_tabs_multiple(engine, mock_context, mock_page):
    iid = await engine.launch()
    await engine.new_tab(iid)
    tabs = await engine.list_tabs(iid)
    assert len(tabs) == 2


@pytest.mark.asyncio
async def test_navigate(engine, mock_page):
    iid = await engine.launch()
    result = await engine.navigate(iid, "https://example.com")
    mock_page.goto.assert_called_once()
    assert result.url == "https://example.com"
    assert result.title == "Test Page"
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_navigate_failure(engine, mock_page):
    mock_page.goto.side_effect = Exception("Connection refused")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Navigation failed"):
        await engine.navigate(iid, "https://bad.example.com")


@pytest.mark.asyncio
async def test_reload(engine, mock_page):
    iid = await engine.launch()
    result = await engine.reload(iid)
    mock_page.reload.assert_called_once()
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_go_back(engine, mock_page):
    iid = await engine.launch()
    result = await engine.go_back(iid)
    mock_page.go_back.assert_called_once()


@pytest.mark.asyncio
async def test_go_forward(engine, mock_page):
    iid = await engine.launch()
    result = await engine.go_forward(iid)
    mock_page.go_forward.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_page(engine, mock_page):
    iid = await engine.launch()
    result = await engine.wait_for_page(iid)
    mock_page.wait_for_load_state.assert_called_once_with("networkidle", timeout=30000)
    assert result.url == "https://example.com"


@pytest.mark.asyncio
async def test_click(engine, mock_page):
    iid = await engine.launch()
    result = await engine.click(iid, "#my-button")
    assert result is True
    mock_page.wait_for_selector.assert_called_with("#my-button", timeout=10000, state="visible")
    mock_page.click.assert_called_with("#my-button")


@pytest.mark.asyncio
async def test_double_click(engine, mock_page):
    iid = await engine.launch()
    result = await engine.double_click(iid, "#my-button")
    assert result is True
    mock_page.dblclick.assert_called_with("#my-button")


@pytest.mark.asyncio
async def test_hover(engine, mock_page):
    iid = await engine.launch()
    result = await engine.hover(iid, "#my-button")
    assert result is True
    mock_page.hover.assert_called_with("#my-button")


@pytest.mark.asyncio
async def test_type_text(engine, mock_page):
    iid = await engine.launch()
    result = await engine.type_text(iid, "#my-input", "Hello")
    assert result is True
    mock_page.fill.assert_called_with("#my-input", "")
    mock_page.type.assert_called_with("#my-input", "Hello")


@pytest.mark.asyncio
async def test_press_key(engine, mock_page):
    iid = await engine.launch()
    result = await engine.press_key(iid, "Enter")
    assert result is True
    mock_page.keyboard.press.assert_called_with("Enter")


@pytest.mark.asyncio
async def test_press_key_with_selector(engine, mock_page):
    iid = await engine.launch()
    result = await engine.press_key(iid, "Enter", selector="#my-input")
    assert result is True
    mock_page.press.assert_called_with("#my-input", "Enter")


@pytest.mark.asyncio
async def test_select_option(engine, mock_page):
    iid = await engine.launch()
    result = await engine.select_option(iid, "#my-select", ["option1"])
    assert result is True
    mock_page.select_option.assert_called_with("#my-select", ["option1"])


@pytest.mark.asyncio
async def test_upload_file_not_found(engine):
    iid = await engine.launch()
    result = await engine.upload_file(iid, "#file-input", "/nonexistent/file.txt")
    assert result.success is False
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_extract_text(engine, mock_page):
    iid = await engine.launch()
    result = await engine.extract_text(iid)
    assert result.text == "Hello World"
    assert result.count == 11


@pytest.mark.asyncio
async def test_extract_links(engine, mock_page):
    mock_page.evaluate = AsyncMock(return_value=[{"text": "Example", "href": "https://example.com", "title": ""}])
    iid = await engine.launch()
    result = await engine.extract_links(iid)
    assert result.count == 1
    assert result.items[0]["href"] == "https://example.com"


@pytest.mark.asyncio
async def test_extract_tables(engine, mock_page):
    mock_page.evaluate = AsyncMock(return_value=[[["A", "B"], ["1", "2"]]])
    iid = await engine.launch()
    result = await engine.extract_tables(iid)
    assert result.count == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_capture_page(engine, mock_page):
    iid = await engine.launch()
    result = await engine.capture_page(iid)
    assert result.image_data == b"fake_screenshot_data"
    assert result.width == 1280
    mock_page.screenshot.assert_called_once()


@pytest.mark.asyncio
async def test_capture_element(engine, mock_page):
    mock_element = AsyncMock()
    mock_element.screenshot = AsyncMock(return_value=b"element_screenshot")
    mock_element.bounding_box = AsyncMock(return_value={"width": 100, "height": 50})
    mock_page.query_selector = AsyncMock(return_value=mock_element)
    iid = await engine.launch()
    result = await engine.capture_element(iid, "#my-element")
    assert result.image_data == b"element_screenshot"
    assert result.width == 100
    assert result.height == 50


@pytest.mark.asyncio
async def test_wait_for_element(engine, mock_page):
    iid = await engine.launch()
    result = await engine.wait_for_element(iid, "#my-element")
    assert result is True
    mock_page.wait_for_selector.assert_called_with("#my-element", timeout=30000, state="visible")


@pytest.mark.asyncio
async def test_wait_for_element_timeout(engine, mock_page):
    mock_page.wait_for_selector.side_effect = Exception("Timeout")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Wait for element"):
        await engine.wait_for_element(iid, "#my-element", timeout=1000)


@pytest.mark.asyncio
async def test_execute_javascript(engine, mock_page):
    mock_page.evaluate = AsyncMock(return_value=42)
    iid = await engine.launch()
    result = await engine.execute_javascript(iid, "1 + 1")
    assert result.success is True
    assert result.result == 42


@pytest.mark.asyncio
async def test_execute_javascript_error(engine, mock_page):
    mock_page.evaluate.side_effect = Exception("ReferenceError")
    iid = await engine.launch()
    result = await engine.execute_javascript(iid, "undefinedVar")
    assert result.success is False
    assert "error" in result.error.lower()


@pytest.mark.asyncio
async def test_evaluate_expression(engine, mock_page):
    mock_page.evaluate = AsyncMock(return_value="hello")
    iid = await engine.launch()
    result = await engine.evaluate_expression(iid, "'hello'")
    assert result.success is True
    assert result.result == "hello"


@pytest.mark.asyncio
async def test_vision_verify_no_vision(engine):
    iid = await engine.launch()
    result = await engine.vision_verify(iid)
    assert result.get("available") is False


@pytest.mark.asyncio
async def test_vision_verify_with_vision(engine, mock_page):
    mock_vision = AsyncMock()
    mock_vision.analyze_image = AsyncMock()
    mock_vision.analyze_image.return_value.elements = []
    mock_vision.analyze_image.return_value.layout = []
    mock_vision.analyze_image.return_value.error = None
    engine._vision = mock_vision
    iid = await engine.launch()
    result = await engine.vision_verify(iid)
    assert result.get("available") is True


@pytest.mark.asyncio
async def test_shutdown_closes_all(engine, mock_playwright, mock_browser):
    await engine.launch()
    await engine.launch()
    await engine.shutdown()
    assert len(engine._instances) == 0
    assert engine._playwright is None


@pytest.mark.asyncio
async def test_shutdown_no_instances(engine):
    await engine.shutdown()
    assert engine._playwright is None


@pytest.mark.asyncio
async def test_multi_tab_operations(engine, mock_context, mock_page):
    iid = await engine.launch()
    p1 = list(engine._instances[iid]["pages"].keys())[0]
    p2 = await engine.new_tab(iid)
    assert len(engine._instances[iid]["pages"]) == 2
    await engine.switch_tab(iid, p1)
    assert engine._instances[iid]["active_page_id"] == p1
    await engine.switch_tab(iid, p2)
    assert engine._instances[iid]["active_page_id"] == p2


@pytest.mark.asyncio
async def test_close_active_tab_falls_back(engine, mock_context, mock_page):
    iid = await engine.launch()
    p1 = list(engine._instances[iid]["pages"].keys())[0]
    p2 = await engine.new_tab(iid)
    await engine.close_tab(iid, p2)
    assert engine._instances[iid]["active_page_id"] == p1


@pytest.mark.asyncio
async def test_extract_forms(engine, mock_page):
    mock_page.evaluate = AsyncMock(return_value=[{
        "selector": "form#login", "action": "/login", "method": "post",
        "inputs": [{"name": "username", "type": "text", "selector": "#username", "placeholder": "User", "required": True}],
        "buttons": [{"text": "Submit", "type": "submit"}],
    }])
    iid = await engine.launch()
    result = await engine.extract_forms(iid)
    assert result.count == 1
    assert result.items[0]["action"] == "/login"


@pytest.mark.asyncio
async def test_right_click(engine, mock_page):
    iid = await engine.launch()
    result = await engine.right_click(iid, "#my-button")
    assert result is True
    mock_page.click.assert_called_with("#my-button", button="right")


@pytest.mark.asyncio
async def test_press_key_with_selector_timeout(engine, mock_page):
    mock_page.wait_for_selector.side_effect = Exception("Timeout")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Press key"):
        await engine.press_key(iid, "Enter", selector="#missing")
