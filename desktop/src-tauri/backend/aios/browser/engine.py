"""BrowserEngine — Playwright-based browser automation with multi-instance support."""

import asyncio
import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from aios.browser.models import (
    TabInfo, NavigationResult, ExtractionResult,
    ScreenshotResult, DownloadResult, UploadResult, ExecutionResult,
)


PAGE_ID_ATTR = "data-aios-page-id"


class BrowserError(Exception):
    pass


class BrowserEngine:
    """Manages multiple browser instances with Playwright async API."""

    def __init__(self, vision_engine=None, event_bus=None, download_dir: str | None = None):
        self._instances: dict[str, dict] = {}
        self._playwright = None
        self._vision = vision_engine
        self._event_bus = event_bus
        self._download_dir = download_dir or str(Path.home() / ".eve" / "browser_downloads")
        Path(self._download_dir).mkdir(parents=True, exist_ok=True)
        self._started = False

    async def _ensure_playwright(self):
        if not self._playwright:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._started = True

    def _get_instance(self, instance_id: str) -> dict:
        inst = self._instances.get(instance_id)
        if not inst:
            raise BrowserError(f"Browser instance not found: {instance_id}")
        return inst

    def _get_page(self, instance_id: str, page_id: str | None = None):
        inst = self._get_instance(instance_id)
        pid = page_id or inst.get("active_page_id")
        if not pid:
            raise BrowserError("No active page. Open a tab first.")
        page = inst.get("pages", {}).get(pid)
        if not page:
            raise BrowserError(f"Page not found: {pid}")
        return page

    async def _publish(self, event_type: str, payload: dict):
        if self._event_bus:
            await self._event_bus.publish(
                event_type, payload, source="browser_engine",
            )

    def _next_page_id(self, inst: dict) -> str:
        idx = inst["page_counter"]
        inst["page_counter"] += 1
        return f"page_{idx}_{uuid4().hex[:8]}"

    # ── Browser Lifecycle ──

    async def launch(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        proxy: dict | None = None,
        user_data_dir: str | None = None,
        args: list[str] | None = None,
    ) -> str:
        await self._ensure_playwright()
        launch_options = {"headless": headless}
        if proxy:
            launch_options["proxy"] = proxy
        if args:
            launch_options["args"] = args
        if user_data_dir:
            launch_options["user_data_dir"] = user_data_dir

        browser_map = {
            "chromium": self._playwright.chromium,
            "chrome": self._playwright.chromium,
            "edge": self._playwright.chromium,
            "firefox": self._playwright.firefox,
        }
        browser_type = browser_type.lower()
        browser_class = browser_map.get(browser_type)
        if not browser_class:
            raise BrowserError(f"Unsupported browser type: {browser_type}")

        channel = None
        if browser_type == "chrome":
            channel = "chrome"
        elif browser_type == "edge":
            channel = "msedge"
        if channel:
            launch_options["channel"] = channel

        browser = await browser_class.launch(**launch_options)
        context = await browser.new_context(
            accept_downloads=True,
            download_path=self._download_dir,
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()
        page_id = f"page_0_{uuid4().hex[:8]}"
        instance_id = f"{browser_type}_{uuid4().hex[:12]}"

        self._instances[instance_id] = {
            "instance_id": instance_id,
            "browser_type": browser_type,
            "browser": browser,
            "context": context,
            "pages": {page_id: page},
            "active_page_id": page_id,
            "headless": headless,
            "created_at": datetime.now(timezone.utc),
            "page_counter": 1,
        }

        await self._publish("browser:launched", {
            "instance_id": instance_id,
            "browser_type": browser_type,
            "headless": headless,
        })
        return instance_id

    async def close(self, instance_id: str) -> bool:
        inst = self._get_instance(instance_id)
        await inst["browser"].close()
        del self._instances[instance_id]
        await self._publish("browser:closed", {"instance_id": instance_id})
        return True

    async def list_instances(self) -> list[dict]:
        return [
            {
                "instance_id": iid,
                "browser_type": inst["browser_type"],
                "headless": inst["headless"],
                "active_page_id": inst.get("active_page_id"),
                "page_count": len(inst.get("pages", {})),
                "created_at": inst.get("created_at").isoformat() if inst.get("created_at") else "",
            }
            for iid, inst in self._instances.items()
        ]

    async def focus(self, instance_id: str) -> bool:
        self._get_instance(instance_id)
        return True

    # ── Tab Management ──

    async def new_tab(self, instance_id: str, url: str = "") -> str:
        inst = self._get_instance(instance_id)
        context = inst["context"]
        page = await context.new_page()
        page_id = self._next_page_id(inst)
        if url:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        inst["pages"][page_id] = page
        inst["active_page_id"] = page_id
        await self._publish("browser:tab_created", {
            "instance_id": instance_id, "page_id": page_id, "url": url,
        })
        return page_id

    async def close_tab(self, instance_id: str, page_id: str | None = None) -> bool:
        inst = self._get_instance(instance_id)
        pid = page_id or inst.get("active_page_id")
        if not pid:
            raise BrowserError("No page to close")
        page = inst["pages"].pop(pid, None)
        if page:
            await page.close()
        pages = inst["pages"]
        if pages:
            inst["active_page_id"] = list(pages.keys())[0]
        else:
            inst["active_page_id"] = None
        await self._publish("browser:tab_closed", {
            "instance_id": instance_id, "page_id": pid,
        })
        return True

    async def switch_tab(self, instance_id: str, page_id: str) -> bool:
        inst = self._get_instance(instance_id)
        if page_id not in inst["pages"]:
            raise BrowserError(f"Page not found: {page_id}")
        inst["active_page_id"] = page_id
        page = inst["pages"][page_id]
        await page.bring_to_front()
        return True

    async def list_tabs(self, instance_id: str) -> list[TabInfo]:
        inst = self._get_instance(instance_id)
        tabs = []
        for idx, (pid, page) in enumerate(inst["pages"].items()):
            try:
                title = await page.title()
                url = page.url
            except Exception:
                title = ""
                url = ""
            tabs.append(TabInfo(page_id=pid, title=title, url=url, index=idx))
        return tabs

    # ── Navigation ──

    async def navigate(self, instance_id: str, url: str, timeout: int = 30000, wait_until: str = "load") -> NavigationResult:
        page = self._get_page(instance_id)
        start = time.time()
        try:
            response = await page.goto(url, timeout=timeout, wait_until=wait_until)
            status = response.status if response else None
            title = await page.title()
            duration = (time.time() - start) * 1000
            await self._publish("browser:navigated", {
                "instance_id": instance_id, "url": url, "title": title, "status": status,
            })
            return NavigationResult(url=url, title=title, status_code=status, duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start) * 1000
            await self._publish("browser:navigation_failed", {
                "instance_id": instance_id, "url": url, "error": str(e),
            })
            raise BrowserError(f"Navigation failed: {e}") from e

    async def reload(self, instance_id: str, timeout: int = 30000) -> NavigationResult:
        page = self._get_page(instance_id)
        start = time.time()
        try:
            response = await page.reload(timeout=timeout)
            status = response.status if response else None
            title = await page.title()
            return NavigationResult(url=page.url, title=title, status_code=status, duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            raise BrowserError(f"Reload failed: {e}") from e

    async def go_back(self, instance_id: str, timeout: int = 30000) -> NavigationResult:
        page = self._get_page(instance_id)
        start = time.time()
        try:
            response = await page.go_back(timeout=timeout)
            status = response.status if response else None
            title = await page.title()
            return NavigationResult(url=page.url, title=title, status_code=status, duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            raise BrowserError(f"Go back failed: {e}") from e

    async def go_forward(self, instance_id: str, timeout: int = 30000) -> NavigationResult:
        page = self._get_page(instance_id)
        start = time.time()
        try:
            response = await page.go_forward(timeout=timeout)
            status = response.status if response else None
            title = await page.title()
            return NavigationResult(url=page.url, title=title, status_code=status, duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            raise BrowserError(f"Go forward failed: {e}") from e

    async def wait_for_page(self, instance_id: str, timeout: int = 30000) -> NavigationResult:
        page = self._get_page(instance_id)
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
            title = await page.title()
            return NavigationResult(url=page.url, title=title)
        except Exception as e:
            raise BrowserError(f"Wait for page failed: {e}") from e

    # ── Interaction ──

    async def _wait_selector(self, page, selector: str, timeout: int = 10000):
        await page.wait_for_selector(selector, timeout=timeout, state="visible")

    async def click(self, instance_id: str, selector: str, timeout: int = 10000, **kwargs) -> bool:
        page = self._get_page(instance_id)
        try:
            await self._wait_selector(page, selector, timeout)
            await page.click(selector, **kwargs)
            return True
        except Exception as e:
            raise BrowserError(f"Click failed on '{selector}': {e}") from e

    async def double_click(self, instance_id: str, selector: str, timeout: int = 10000) -> bool:
        page = self._get_page(instance_id)
        try:
            await self._wait_selector(page, selector, timeout)
            await page.dblclick(selector)
            return True
        except Exception as e:
            raise BrowserError(f"Double click failed on '{selector}': {e}") from e

    async def right_click(self, instance_id: str, selector: str, timeout: int = 10000) -> bool:
        page = self._get_page(instance_id)
        try:
            await self._wait_selector(page, selector, timeout)
            await page.click(selector, button="right")
            return True
        except Exception as e:
            raise BrowserError(f"Right click failed on '{selector}': {e}") from e

    async def hover(self, instance_id: str, selector: str, timeout: int = 10000) -> bool:
        page = self._get_page(instance_id)
        try:
            await self._wait_selector(page, selector, timeout)
            await page.hover(selector)
            return True
        except Exception as e:
            raise BrowserError(f"Hover failed on '{selector}': {e}") from e

    async def type_text(self, instance_id: str, selector: str, text: str, timeout: int = 10000, clear_first: bool = True) -> bool:
        page = self._get_page(instance_id)
        try:
            await self._wait_selector(page, selector, timeout)
            if clear_first:
                await page.fill(selector, "")
            await page.type(selector, text)
            return True
        except Exception as e:
            raise BrowserError(f"Type text failed on '{selector}': {e}") from e

    async def press_key(self, instance_id: str, key: str, selector: str | None = None) -> bool:
        page = self._get_page(instance_id)
        try:
            if selector:
                await self._wait_selector(page, selector, 5000)
                await page.press(selector, key)
            else:
                await page.keyboard.press(key)
            return True
        except Exception as e:
            raise BrowserError(f"Press key '{key}' failed: {e}") from e

    async def select_option(self, instance_id: str, selector: str, values: list[str], timeout: int = 10000) -> bool:
        page = self._get_page(instance_id)
        try:
            await self._wait_selector(page, selector, timeout)
            await page.select_option(selector, values)
            return True
        except Exception as e:
            raise BrowserError(f"Select option failed on '{selector}': {e}") from e

    async def upload_file(self, instance_id: str, selector: str, file_path: str, timeout: int = 30000) -> UploadResult:
        page = self._get_page(instance_id)
        try:
            resolved = Path(file_path).resolve()
            if not resolved.exists():
                return UploadResult(success=False, file_name=resolved.name, error=f"File not found: {file_path}")
            await self._wait_selector(page, selector, timeout)
            file_chooser = await page.wait_for_event("filechooser", timeout=timeout)
            await file_chooser.set_files(str(resolved))
            return UploadResult(success=True, file_name=resolved.name)
        except Exception as e:
            return UploadResult(success=False, error=f"Upload failed: {e}")

    async def download_file(self, instance_id: str, url: str | None = None, timeout: int = 60000) -> DownloadResult:
        page = self._get_page(instance_id)
        try:
            async with page.expect_download(timeout=timeout) as download_info:
                if url:
                    await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            download = await download_info.value
            suggested = download.suggested_filename
            dest = str(Path(self._download_dir) / suggested)
            await download.save_as(dest)
            size = Path(dest).stat().st_size
            return DownloadResult(file_path=dest, file_name=suggested, file_size=size, success=True)
        except Exception as e:
            return DownloadResult(success=False, error=f"Download failed: {e}")

    # ── Extraction ──

    async def extract_text(self, instance_id: str, selector: str = "body") -> ExtractionResult:
        page = self._get_page(instance_id)
        try:
            text = await page.inner_text(selector)
            return ExtractionResult(text=text, count=len(text))
        except Exception as e:
            return ExtractionResult(error=str(e))

    async def extract_links(self, instance_id: str) -> ExtractionResult:
        page = self._get_page(instance_id)
        try:
            links = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.innerText.trim(),
                    href: a.href,
                    title: a.title || ''
                }));
            }""")
            return ExtractionResult(items=links, count=len(links))
        except Exception as e:
            return ExtractionResult(error=str(e))

    async def extract_tables(self, instance_id: str) -> ExtractionResult:
        page = self._get_page(instance_id)
        try:
            tables = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('table')).map(table => {
                    const rows = Array.from(table.querySelectorAll('tr'));
                    return rows.map(row =>
                        Array.from(row.querySelectorAll('td, th')).map(cell => cell.innerText.trim())
                    );
                });
            }""")
            return ExtractionResult(items=tables, count=len(tables))
        except Exception as e:
            return ExtractionResult(error=str(e))

    async def extract_forms(self, instance_id: str) -> ExtractionResult:
        page = self._get_page(instance_id)
        try:
            forms = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('form')).map(form => ({
                    selector: 'form' + (form.id ? '#' + form.id : '') + (form.className ? '.' + form.className.split(' ').join('.') : ''),
                    action: form.action || '',
                    method: (form.method || 'get').toLowerCase(),
                    inputs: Array.from(form.querySelectorAll('input, select, textarea')).map(el => ({
                        name: el.name || '',
                        type: el.type || el.tagName.toLowerCase(),
                        selector: el.id ? '#' + el.id : el.name ? '[name=\"' + el.name + '\"]' : '',
                        placeholder: el.placeholder || '',
                        required: el.required || false,
                    })),
                    buttons: Array.from(form.querySelectorAll('button, input[type=\"submit\"]')).map(btn => ({
                        text: btn.innerText || btn.value || '',
                        type: btn.type || 'submit',
                    })),
                }));
            }""")
            return ExtractionResult(items=forms, count=len(forms))
        except Exception as e:
            return ExtractionResult(error=str(e))

    async def capture_page(self, instance_id: str, full_page: bool = True) -> ScreenshotResult:
        page = self._get_page(instance_id)
        try:
            opts = {"full_page": full_page, "type": "png"}
            data = await page.screenshot(**opts)
            viewport = page.viewport_size or {"width": 0, "height": 0}
            return ScreenshotResult(image_data=data, width=viewport["width"], height=viewport["height"])
        except Exception as e:
            return ScreenshotResult(error=str(e))

    async def capture_element(self, instance_id: str, selector: str, timeout: int = 10000) -> ScreenshotResult:
        page = self._get_page(instance_id)
        try:
            await self._wait_selector(page, selector, timeout)
            element = await page.query_selector(selector)
            if not element:
                return ScreenshotResult(error=f"Element not found: {selector}")
            data = await element.screenshot(type="png")
            box = await element.bounding_box()
            w = int(box["width"]) if box else 0
            h = int(box["height"]) if box else 0
            return ScreenshotResult(image_data=data, width=w, height=h)
        except Exception as e:
            return ScreenshotResult(error=str(e))

    # ── Automation ──

    async def wait_for_element(self, instance_id: str, selector: str, timeout: int = 30000, state: str = "visible") -> bool:
        page = self._get_page(instance_id)
        try:
            await page.wait_for_selector(selector, timeout=timeout, state=state)
            return True
        except Exception as e:
            raise BrowserError(f"Wait for element '{selector}' failed: {e}") from e

    async def wait_for_text(self, instance_id: str, text: str, timeout: int = 30000) -> bool:
        page = self._get_page(instance_id)
        try:
            await page.wait_for_function(
                f"() => document.body.innerText.includes({json.dumps(text)})",
                timeout=timeout,
            )
            return True
        except Exception as e:
            raise BrowserError(f"Wait for text '{text}' failed: {e}") from e

    async def execute_javascript(self, instance_id: str, script: str) -> ExecutionResult:
        page = self._get_page(instance_id)
        start = time.time()
        try:
            result = await page.evaluate(script)
            return ExecutionResult(success=True, result=result, duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ExecutionResult(success=False, error=str(e), duration_ms=(time.time() - start) * 1000)

    async def evaluate_expression(self, instance_id: str, expression: str) -> ExecutionResult:
        return await self.execute_javascript(instance_id, expression)

    # ── Vision Integration ──

    async def vision_verify(self, instance_id: str, description: str = "") -> dict:
        """Use Vision engine to verify page state. Returns observation dict."""
        if not self._vision:
            return {"available": False, "message": "Vision engine not available"}
        try:
            page = self._get_page(instance_id)
            screenshot = await page.screenshot(type="png")
            obs = await self._vision.analyze_image(screenshot)
            return {
                "available": True,
                "elements": [{"type": e.type, "text": e.text, "x": e.x, "y": e.y, "width": e.width, "height": e.height} for e in obs.elements],
                "layout": [{"type": r.type, "x": r.x, "y": r.y, "width": r.width, "height": r.height} for r in obs.layout] if hasattr(obs, "layout") else [],
                "text_regions": [{"text": r.text if hasattr(r, "text") else "", "x": r.x, "y": r.y} for r in obs.text_regions] if hasattr(obs, "text_regions") else [],
                "error": obs.error,
            }
        except Exception as e:
            return {"available": True, "error": str(e)}

    # ── Cleanup ──

    async def shutdown(self):
        for iid in list(self._instances.keys()):
            try:
                await self.close(iid)
            except Exception:
                pass
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            self._started = False
