"""Comprehensive edge-case and error-path tests for BrowserEngine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from aios.browser.engine import BrowserEngine, BrowserError
from aios.browser.models import (
    BrowserInstance, TabInfo, NavigationResult, ExtractionResult,
    ScreenshotResult, DownloadResult, UploadResult, ExecutionResult,
    FormInfo, LinkInfo,
)


# ── Shared Fixtures ──

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
    page.reload.return_value = MagicMock(status=200)
    page.go_back = AsyncMock()
    page.go_back.return_value = MagicMock(status=200)
    page.go_forward = AsyncMock()
    page.go_forward.return_value = MagicMock(status=200)
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
    page.wait_for_event = AsyncMock(return_value=AsyncMock())
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


@pytest.fixture
def engine_with_bus(mock_playwright):
    with patch("playwright.async_api.async_playwright") as mock_ap:
        mock_cm = AsyncMock()
        mock_cm.start = AsyncMock(return_value=mock_playwright)
        mock_ap.return_value = mock_cm
        bus = AsyncMock()
        bus.publish = AsyncMock()
        eng = BrowserEngine(event_bus=bus)
        yield eng


@pytest.fixture
async def started_engine(engine):
    iid = await engine.launch()
    return engine, iid


# ── _ensure_playwright ──

@pytest.mark.asyncio
async def test_ensure_playwright_already_started(engine):
    await engine._ensure_playwright()
    pw = engine._playwright
    await engine._ensure_playwright()
    assert engine._playwright is pw


# ── _get_instance ──

@pytest.mark.asyncio
async def test_get_instance_not_found(engine):
    with pytest.raises(BrowserError, match="not found"):
        engine._get_instance("nonexistent")


# ── _get_page ──

@pytest.mark.asyncio
async def test_get_page_no_active_page(engine):
    iid = await engine.launch()
    engine._instances[iid]["active_page_id"] = None
    with pytest.raises(BrowserError, match="No active page"):
        engine._get_page(iid)


@pytest.mark.asyncio
async def test_get_page_not_found(engine):
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Page not found"):
        engine._get_page(iid, page_id="nonexistent")


# ── _publish ──

@pytest.mark.asyncio
async def test_publish_no_event_bus(engine_with_bus):
    engine = engine_with_bus
    iid = await engine.launch()
    engine._event_bus = None
    await engine._publish("test:event", {"key": "val"})
    assert engine._event_bus is None


@pytest.mark.asyncio
async def test_publish_with_event_bus(engine_with_bus):
    engine = engine_with_bus
    engine._event_bus.publish.reset_mock()
    iid = await engine.launch()
    engine._event_bus.publish.reset_mock()
    await engine._publish("test:event", {"key": "val"})
    engine._event_bus.publish.assert_called_once_with(
        "test:event", {"key": "val"}, source="browser_engine",
    )


# ── launch ──

@pytest.mark.asyncio
async def test_launch_with_proxy(engine, mock_playwright, mock_browser):
    proxy = {"server": "http://proxy:8080", "username": "u", "password": "p"}
    iid = await engine.launch(proxy=proxy)
    call_kwargs = mock_playwright.chromium.launch.call_args.kwargs
    assert call_kwargs.get("proxy") == proxy


@pytest.mark.asyncio
async def test_launch_with_user_data_dir(engine, mock_playwright, mock_browser):
    iid = await engine.launch(user_data_dir="/tmp/profile")
    call_kwargs = mock_playwright.chromium.launch.call_args.kwargs
    assert call_kwargs.get("user_data_dir") == "/tmp/profile"


@pytest.mark.asyncio
async def test_launch_with_args(engine, mock_playwright, mock_browser):
    args = ["--disable-gpu", "--no-sandbox"]
    iid = await engine.launch(args=args)
    call_kwargs = mock_playwright.chromium.launch.call_args.kwargs
    assert call_kwargs.get("args") == args


@pytest.mark.asyncio
async def test_launch_publishes_event(engine_with_bus):
    engine = engine_with_bus
    iid = await engine.launch(browser_type="chromium", headless=True)
    engine._event_bus.publish.assert_any_call(
        "browser:launched",
        {"instance_id": iid, "browser_type": "chromium", "headless": True},
        source="browser_engine",
    )


# ── close ──

@pytest.mark.asyncio
async def test_close_publishes_event(engine_with_bus):
    engine = engine_with_bus
    iid = await engine.launch()
    await engine.close(iid)
    engine._event_bus.publish.assert_any_call(
        "browser:closed", {"instance_id": iid}, source="browser_engine",
    )


@pytest.mark.asyncio
async def test_close_browser_called(engine, mock_browser):
    iid = await engine.launch()
    await engine.close(iid)
    mock_browser.close.assert_called_once()


# ── list_instances formatting ──

@pytest.mark.asyncio
async def test_list_instances_format(engine):
    iid = await engine.launch(browser_type="chromium", headless=True)
    instances = await engine.list_instances()
    entry = instances[0]
    assert "instance_id" in entry
    assert "browser_type" in entry
    assert "headless" in entry
    assert "active_page_id" in entry
    assert "page_count" in entry
    assert "created_at" in entry
    assert isinstance(entry["created_at"], str)


# ── new_tab ──

@pytest.mark.asyncio
async def test_new_tab_no_url(engine, mock_context, mock_page):
    iid = await engine.launch()
    page_id = await engine.new_tab(iid)
    mock_page.goto.assert_not_called()


@pytest.mark.asyncio
async def test_new_tab_sets_active(engine, mock_context):
    iid = await engine.launch()
    old_id = engine._instances[iid]["active_page_id"]
    new_id = await engine.new_tab(iid)
    assert engine._instances[iid]["active_page_id"] == new_id


@pytest.mark.asyncio
async def test_new_tab_publishes_event(engine_with_bus):
    engine = engine_with_bus
    iid = await engine.launch()
    page_id = await engine.new_tab(iid, url="https://ex.com")
    engine._event_bus.publish.assert_any_call(
        "browser:tab_created",
        {"instance_id": iid, "page_id": page_id, "url": "https://ex.com"},
        source="browser_engine",
    )


# ── close_tab ──

@pytest.mark.asyncio
async def test_close_tab_no_page_id_closes_active(engine, mock_page):
    iid = await engine.launch()
    pid = list(engine._instances[iid]["pages"].keys())[0]
    new_id = await engine.new_tab(iid)
    await engine.close_tab(iid)
    mock_page.close.assert_called()
    assert engine._instances[iid]["active_page_id"] == pid


@pytest.mark.asyncio
async def test_close_tab_no_pages_left(engine, mock_page):
    iid = await engine.launch()
    pid = list(engine._instances[iid]["pages"].keys())[0]
    await engine.close_tab(iid, pid)
    assert engine._instances[iid]["active_page_id"] is None


@pytest.mark.asyncio
async def test_close_tab_no_active_page(engine):
    iid = await engine.launch()
    engine._instances[iid]["active_page_id"] = None
    with pytest.raises(BrowserError, match="No page to close"):
        await engine.close_tab(iid)


@pytest.mark.asyncio
async def test_close_tab_publishes_event(engine_with_bus):
    engine = engine_with_bus
    iid = await engine.launch()
    pid = list(engine._instances[iid]["pages"].keys())[0]
    await engine.close_tab(iid, pid)
    engine._event_bus.publish.assert_any_call(
        "browser:tab_closed",
        {"instance_id": iid, "page_id": pid},
        source="browser_engine",
    )


# ── switch_tab ──

@pytest.mark.asyncio
async def test_switch_tab_not_found(engine):
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Page not found"):
        await engine.switch_tab(iid, "nonexistent")


# ── list_tabs ──

@pytest.mark.asyncio
async def test_list_tabs_title_failure(engine, mock_page):
    mock_page.title.side_effect = Exception("fail")
    iid = await engine.launch()
    tabs = await engine.list_tabs(iid)
    assert len(tabs) == 1
    assert tabs[0].title == ""
    assert tabs[0].url == ""


# ── navigate event publishing ──

@pytest.mark.asyncio
async def test_navigate_publishes_success(engine_with_bus, mock_page):
    engine = engine_with_bus
    iid = await engine.launch()
    await engine.navigate(iid, "https://ex.com")
    engine._event_bus.publish.assert_any_call(
        "browser:navigated",
        {"instance_id": iid, "url": "https://ex.com", "title": "Test Page", "status": 200},
        source="browser_engine",
    )


@pytest.mark.asyncio
async def test_navigate_publishes_failure(engine_with_bus, mock_page):
    mock_page.goto.side_effect = Exception("Timeout")
    engine = engine_with_bus
    iid = await engine.launch()
    with pytest.raises(BrowserError):
        await engine.navigate(iid, "https://bad.ex")
    engine._event_bus.publish.assert_any_call(
        "browser:navigation_failed",
        {"instance_id": iid, "url": "https://bad.ex", "error": "Timeout"},
        source="browser_engine",
    )


# ── reload error ──

@pytest.mark.asyncio
async def test_reload_error(engine, mock_page):
    mock_page.reload.side_effect = Exception("Reload failed")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Reload failed"):
        await engine.reload(iid)


# ── go_back error ──

@pytest.mark.asyncio
async def test_go_back_error(engine, mock_page):
    mock_page.go_back.side_effect = Exception("Back failed")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Go back failed"):
        await engine.go_back(iid)


# ── go_forward error ──

@pytest.mark.asyncio
async def test_go_forward_error(engine, mock_page):
    mock_page.go_forward.side_effect = Exception("Forward failed")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Go forward failed"):
        await engine.go_forward(iid)


# ── wait_for_page error ──

@pytest.mark.asyncio
async def test_wait_for_page_error(engine, mock_page):
    mock_page.wait_for_load_state.side_effect = Exception("Timeout")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Wait for page failed"):
        await engine.wait_for_page(iid)


# ── interaction errors ──

@pytest.mark.asyncio
async def test_click_error(engine, mock_page):
    mock_page.wait_for_selector.side_effect = Exception("Timeout")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Click failed"):
        await engine.click(iid, "#btn")


@pytest.mark.asyncio
async def test_double_click_error(engine, mock_page):
    mock_page.dblclick.side_effect = Exception("Fail")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Double click failed"):
        await engine.double_click(iid, "#btn")


@pytest.mark.asyncio
async def test_right_click_error(engine, mock_page):
    mock_page.click.side_effect = Exception("Fail")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Right click failed"):
        await engine.right_click(iid, "#btn")


@pytest.mark.asyncio
async def test_hover_error(engine, mock_page):
    mock_page.hover.side_effect = Exception("Fail")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Hover failed"):
        await engine.hover(iid, "#btn")


@pytest.mark.asyncio
async def test_type_text_error(engine, mock_page):
    mock_page.fill.side_effect = Exception("Fail")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Type text failed"):
        await engine.type_text(iid, "#input", "text")


@pytest.mark.asyncio
async def test_type_text_no_clear(engine, mock_page):
    iid = await engine.launch()
    await engine.type_text(iid, "#input", "text", clear_first=False)
    mock_page.fill.assert_not_called()
    mock_page.type.assert_called_with("#input", "text")


@pytest.mark.asyncio
async def test_press_key_error_no_selector(engine, mock_page):
    mock_page.keyboard.press.side_effect = Exception("Fail")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Press key"):
        await engine.press_key(iid, "Enter")


@pytest.mark.asyncio
async def test_select_option_error(engine, mock_page):
    mock_page.select_option.side_effect = Exception("Fail")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Select option failed"):
        await engine.select_option(iid, "#sel", ["opt1"])


# ── upload_file ──

@pytest.mark.asyncio
async def test_upload_file_success(engine, mock_page, tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello")
    mock_file_chooser = AsyncMock()
    mock_page.wait_for_event = AsyncMock(return_value=mock_file_chooser)
    iid = await engine.launch()
    result = await engine.upload_file(iid, "#file-input", str(f))
    assert result.success is True
    assert result.file_name == "test.txt"
    mock_file_chooser.set_files.assert_called_once_with(str(f))


@pytest.mark.asyncio
async def test_upload_file_exception(engine, mock_page, tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello")
    mock_page.wait_for_event.side_effect = Exception("File chooser failed")
    iid = await engine.launch()
    result = await engine.upload_file(iid, "#file-input", str(f))
    assert result.success is False
    assert "Upload failed" in result.error


# ── download_file ──

@pytest.mark.asyncio
async def test_download_file_success(engine, mock_page, tmp_path):
    engine._download_dir = str(tmp_path)
    mock_download = MagicMock()
    mock_download.suggested_filename = "report.pdf"
    mock_download.save_as = AsyncMock()

    async def mock_value():
        return mock_download

    mock_cm = MagicMock()
    mock_cm.value = mock_value()

    class FakeCM:
        async def __aenter__(self):
            return mock_cm
        async def __aexit__(self, *args):
            pass

    mock_page.expect_download = MagicMock(return_value=FakeCM())
    dl_path = tmp_path / "report.pdf"
    dl_path.write_text("pdf content")
    iid = await engine.launch()
    result = await engine.download_file(iid)
    assert result.success is True
    mock_download.save_as.assert_called_once()


@pytest.mark.asyncio
async def test_download_file_error(engine, mock_page):
    class FakeCM:
        async def __aenter__(self):
            raise Exception("Download failed")
        async def __aexit__(self, *args):
            pass

    mock_page.expect_download = MagicMock(return_value=FakeCM())
    iid = await engine.launch()
    result = await engine.download_file(iid)
    assert result.success is False
    assert "Download failed" in result.error


@pytest.mark.asyncio
async def test_download_file_with_url(engine, mock_page, tmp_path):
    engine._download_dir = str(tmp_path)
    mock_download = MagicMock()
    mock_download.suggested_filename = "doc.pdf"
    mock_download.save_as = AsyncMock()

    async def mock_value():
        return mock_download

    mock_cm = MagicMock()
    mock_cm.value = mock_value()

    class FakeCM:
        async def __aenter__(self):
            return mock_cm
        async def __aexit__(self, *args):
            pass

    dl_path = tmp_path / "doc.pdf"
    dl_path.write_text("pdf content")
    mock_page.expect_download = MagicMock(return_value=FakeCM())
    iid = await engine.launch()
    result = await engine.download_file(iid, url="https://ex.com/file.pdf")
    assert result.success is True
    mock_download.save_as.assert_called_once()
    mock_page.goto.assert_called_once()


# ── extraction errors ──

@pytest.mark.asyncio
async def test_extract_text_error(engine, mock_page):
    mock_page.inner_text.side_effect = Exception("Element not found")
    iid = await engine.launch()
    result = await engine.extract_text(iid, "#missing")
    assert result.error is not None


@pytest.mark.asyncio
async def test_extract_links_error(engine, mock_page):
    mock_page.evaluate.side_effect = Exception("JS error")
    iid = await engine.launch()
    result = await engine.extract_links(iid)
    assert result.error is not None


@pytest.mark.asyncio
async def test_extract_tables_error(engine, mock_page):
    mock_page.evaluate.side_effect = Exception("JS error")
    iid = await engine.launch()
    result = await engine.extract_tables(iid)
    assert result.error is not None


@pytest.mark.asyncio
async def test_extract_forms_error(engine, mock_page):
    mock_page.evaluate.side_effect = Exception("JS error")
    iid = await engine.launch()
    result = await engine.extract_forms(iid)
    assert result.error is not None


# ── screenshot errors ──

@pytest.mark.asyncio
async def test_capture_page_error(engine, mock_page):
    mock_page.screenshot.side_effect = Exception("Screenshot failed")
    iid = await engine.launch()
    result = await engine.capture_page(iid)
    assert result.error is not None


@pytest.mark.asyncio
async def test_capture_element_not_found(engine, mock_page):
    mock_page.query_selector.return_value = None
    iid = await engine.launch()
    result = await engine.capture_element(iid, "#missing")
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_capture_element_error(engine, mock_page):
    mock_element = AsyncMock()
    mock_element.screenshot.side_effect = Exception("Fail")
    mock_page.query_selector = AsyncMock(return_value=mock_element)
    iid = await engine.launch()
    result = await engine.capture_element(iid, "#el")
    assert result.error is not None


# ── wait_for_text ──

@pytest.mark.asyncio
async def test_wait_for_text_success(engine, mock_page):
    mock_page.wait_for_function = AsyncMock()
    iid = await engine.launch()
    result = await engine.wait_for_text(iid, "hello")
    assert result is True
    mock_page.wait_for_function.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_text_error(engine, mock_page):
    mock_page.wait_for_function.side_effect = Exception("Text not found")
    iid = await engine.launch()
    with pytest.raises(BrowserError, match="Wait for text"):
        await engine.wait_for_text(iid, "missing")


# ── evaluate_expression ──

@pytest.mark.asyncio
async def test_evaluate_expression_error(engine, mock_page):
    mock_page.evaluate.side_effect = Exception("Fail")
    iid = await engine.launch()
    result = await engine.evaluate_expression(iid, "bad()")
    assert result.success is False
    assert result.error is not None


# ── vision_verify ──

@pytest.mark.asyncio
async def test_vision_verify_error(engine, mock_page):
    mock_vision = AsyncMock()
    mock_vision.analyze_image.side_effect = Exception("Vision error")
    engine._vision = mock_vision
    iid = await engine.launch()
    result = await engine.vision_verify(iid)
    assert result.get("error") == "Vision error"


@pytest.mark.asyncio
async def test_vision_verify_with_vision_data(engine, mock_page):
    class FakeObs:
        elements = [type("E", (), {"type": "button", "text": "OK", "x": 0, "y": 0, "width": 10, "height": 5})()]
        layout = [type("R", (), {"type": "container", "x": 0, "y": 0, "width": 100, "height": 50})()]
        text_regions = [type("T", (), {"text": "Hello", "x": 0, "y": 0})()]
        error = None

    mock_vision = AsyncMock()
    mock_vision.analyze_image = AsyncMock(return_value=FakeObs())
    engine._vision = mock_vision
    iid = await engine.launch()
    result = await engine.vision_verify(iid)
    assert result["available"] is True
    assert len(result["elements"]) == 1
    assert result["elements"][0]["text"] == "OK"
    assert len(result["layout"]) == 1
    assert len(result["text_regions"]) == 1


@pytest.mark.asyncio
async def test_vision_verify_screenshot_exception(engine, mock_page):
    mock_page.screenshot.side_effect = Exception("Screenshot failed")
    mock_vision = AsyncMock()
    mock_vision.analyze_image = AsyncMock()
    engine._vision = mock_vision
    iid = await engine.launch()
    result = await engine.vision_verify(iid)
    assert result.get("error") == "Screenshot failed"


# ── shutdown ──

@pytest.mark.asyncio
async def test_shutdown_close_error(engine, mock_browser):
    mock_browser.close.side_effect = Exception("Close error")
    iid = await engine.launch()
    await engine.shutdown()
    assert engine._playwright is None
    assert engine._started is False


# ── multiple instances ──

@pytest.mark.asyncio
async def test_multiple_instances_isolation(engine):
    iid1 = await engine.launch(browser_type="chromium")
    iid2 = await engine.launch(browser_type="firefox")
    assert iid1 != iid2
    tabs1 = await engine.list_tabs(iid1)
    tabs2 = await engine.list_tabs(iid2)
    assert len(tabs1) == 1
    assert len(tabs2) == 1


@pytest.mark.asyncio
async def test_operate_on_closed_instance(engine):
    iid = await engine.launch()
    await engine.close(iid)
    with pytest.raises(BrowserError, match="not found"):
        await engine.navigate(iid, "https://ex.com")


# ── download_dir ──

def test_download_dir_created(tmp_path):
    dl_dir = tmp_path / "dl"
    engine = BrowserEngine(download_dir=str(dl_dir))
    assert dl_dir.exists()


def test_download_dir_default():
    engine = BrowserEngine()
    assert engine._download_dir is not None
