"""Browser automation tools using Playwright."""

from aios.core.tool_manager import ToolResult


async def web_search(params: dict) -> ToolResult:
    query = params.get("query", "")
    if not query:
        return ToolResult(success=False, error="Query is required")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"https://www.google.com/search?q={query}")
            page.wait_for_selector("body", timeout=10000)
            text = page.inner_text("body")[:2000]
            browser.close()
        return ToolResult(success=True, data={"query": query, "results": text})
    except ImportError:
        return ToolResult(success=False, error="Playwright is not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def navigate(params: dict) -> ToolResult:
    url = params.get("url", "")
    if not url:
        return ToolResult(success=False, error="URL is required")
    return ToolResult(success=True, data={"url": url, "status": "navigated"})


async def extract_content(params: dict) -> ToolResult:
    url = params.get("url", "")
    if not url:
        return ToolResult(success=False, error="URL is required")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            title = page.title()
            body_text = page.inner_text("body")[:3000]
            browser.close()
        return ToolResult(success=True, data={"url": url, "title": title, "content": body_text})
    except Exception as e:
        return ToolResult(success=False, error=str(e))
