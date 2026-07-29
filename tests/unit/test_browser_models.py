"""Tests for browser automation data models."""

from datetime import datetime
from aios.browser.models import (
    BrowserInstance, TabInfo, NavigationResult, ExtractionResult,
    ScreenshotResult, DownloadResult, UploadResult, ExecutionResult,
    FormInfo, LinkInfo,
)


def test_browser_instance_defaults():
    inst = BrowserInstance(instance_id="abc", browser_type="chromium", headless=True)
    assert inst.instance_id == "abc"
    assert inst.browser_type == "chromium"
    assert inst.headless is True
    assert isinstance(inst.created_at, datetime)
    assert inst.active_page_id is None
    assert inst.page_count == 0


def test_browser_instance_custom():
    dt = datetime(2025, 1, 1)
    inst = BrowserInstance(
        instance_id="abc", browser_type="firefox", headless=False,
        created_at=dt, active_page_id="pg1", page_count=3,
    )
    assert inst.created_at == dt
    assert inst.active_page_id == "pg1"
    assert inst.page_count == 3


def test_tab_info():
    tab = TabInfo(page_id="pg1", title="Example", url="https://ex.com", index=0)
    assert tab.page_id == "pg1"
    assert tab.title == "Example"
    assert tab.url == "https://ex.com"
    assert tab.index == 0


def test_navigation_result():
    nr = NavigationResult(url="https://ex.com", title="Ex", status_code=200, duration_ms=150.5)
    assert nr.url == "https://ex.com"
    assert nr.title == "Ex"
    assert nr.status_code == 200
    assert nr.duration_ms == 150.5


def test_navigation_result_defaults():
    nr = NavigationResult(url="https://ex.com", title="Ex")
    assert nr.status_code is None
    assert nr.duration_ms == 0.0
    assert nr.error is None


def test_navigation_result_with_error():
    nr = NavigationResult(url="https://ex.com", title="Ex", error="Timeout")
    assert nr.error == "Timeout"


def test_extraction_result():
    er = ExtractionResult(text="hello", items=[1, 2, 3], count=3)
    assert er.text == "hello"
    assert er.items == [1, 2, 3]
    assert er.count == 3
    assert er.error is None


def test_extraction_result_defaults():
    er = ExtractionResult()
    assert er.text == ""
    assert er.items == []
    assert er.count == 0
    assert er.error is None


def test_extraction_result_error():
    er = ExtractionResult(error="Failed")
    assert er.error == "Failed"


def test_screenshot_result():
    sr = ScreenshotResult(image_data=b"data", width=800, height=600, format="png")
    assert sr.image_data == b"data"
    assert sr.width == 800
    assert sr.height == 600
    assert sr.format == "png"
    assert sr.error is None


def test_screenshot_result_defaults():
    sr = ScreenshotResult()
    assert sr.image_data == b""
    assert sr.width == 0
    assert sr.height == 0
    assert sr.format == "png"
    assert sr.error is None


def test_download_result():
    dr = DownloadResult(file_path="C:\\f.txt", file_name="f.txt", file_size=100, mime_type="text/plain", success=True)
    assert dr.file_path == "C:\\f.txt"
    assert dr.file_name == "f.txt"
    assert dr.file_size == 100
    assert dr.mime_type == "text/plain"
    assert dr.success is True


def test_download_result_defaults():
    dr = DownloadResult()
    assert dr.file_path == ""
    assert dr.file_name == ""
    assert dr.file_size == 0
    assert dr.mime_type == ""
    assert dr.success is False
    assert dr.error is None


def test_download_result_error():
    dr = DownloadResult(success=False, error="Download failed")
    assert dr.error == "Download failed"


def test_upload_result():
    ur = UploadResult(success=True, file_name="test.txt")
    assert ur.success is True
    assert ur.file_name == "test.txt"
    assert ur.error is None


def test_upload_result_defaults():
    ur = UploadResult()
    assert ur.success is False
    assert ur.file_name == ""
    assert ur.error is None


def test_upload_result_error():
    ur = UploadResult(success=False, error="Upload failed")
    assert ur.error == "Upload failed"


def test_execution_result():
    er = ExecutionResult(success=True, result=42, duration_ms=10.5)
    assert er.success is True
    assert er.result == 42
    assert er.duration_ms == 10.5
    assert er.error is None


def test_execution_result_defaults():
    er = ExecutionResult()
    assert er.success is False
    assert er.result is None
    assert er.error is None
    assert er.duration_ms == 0.0


def test_form_info():
    fi = FormInfo(
        selector="form#login",
        inputs=[{"name": "user", "type": "text"}],
        buttons=[{"text": "Submit", "type": "submit"}],
        method="post", action="/login",
    )
    assert fi.selector == "form#login"
    assert fi.inputs == [{"name": "user", "type": "text"}]
    assert fi.buttons == [{"text": "Submit", "type": "submit"}]
    assert fi.method == "post"
    assert fi.action == "/login"


def test_form_info_defaults():
    fi = FormInfo(selector="form")
    assert fi.inputs == []
    assert fi.buttons == []
    assert fi.method == "get"
    assert fi.action == ""


def test_link_info():
    li = LinkInfo(text="Click here", href="https://ex.com", title="Example", selector="a.link")
    assert li.text == "Click here"
    assert li.href == "https://ex.com"
    assert li.title == "Example"
    assert li.selector == "a.link"


def test_link_info_defaults():
    li = LinkInfo(text="", href="")
    assert li.title == ""
    assert li.selector == ""
