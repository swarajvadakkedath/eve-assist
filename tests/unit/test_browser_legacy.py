"""Tests for legacy browser.py tools (web_search, navigate, extract_content)."""

import pytest
from unittest.mock import patch, MagicMock

from aios.tools.browser import web_search, navigate, extract_content
from aios.core.tool_manager import ToolResult


# ── web_search ──

@pytest.mark.asyncio
async def test_web_search_empty_query():
    result = await web_search({"query": ""})
    assert result.success is False
    assert "Query is required" in result.error


@pytest.mark.asyncio
async def test_web_search_missing_query():
    result = await web_search({})
    assert result.success is False
    assert "Query is required" in result.error


@pytest.mark.asyncio
async def test_web_search_success():
    with patch("playwright.sync_api.sync_playwright") as mock_sp:
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.inner_text.return_value = "search results here"
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_sp.return_value.__enter__.return_value = mock_p

        result = await web_search({"query": "hello"})
        assert result.success is True
        assert result.data["query"] == "hello"
        assert "results" in result.data
        mock_browser.close.assert_called_once()


@pytest.mark.asyncio
async def test_web_search_playwright_error():
    mock_page = MagicMock()
    mock_page.goto.side_effect = Exception("Navigation failed")
    with patch("playwright.sync_api.sync_playwright") as mock_sp:
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_p.chromium.launch.return_value = mock_browser
        mock_sp.return_value.__enter__.return_value = mock_p
        result = await web_search({"query": "test"})
        assert result.success is False


# ── navigate ──

@pytest.mark.asyncio
async def test_navigate_success():
    result = await navigate({"url": "https://example.com"})
    assert result.success is True
    assert result.data["url"] == "https://example.com"
    assert result.data["status"] == "navigated"


@pytest.mark.asyncio
async def test_navigate_empty_url():
    result = await navigate({"url": ""})
    assert result.success is False
    assert "URL is required" in result.error


@pytest.mark.asyncio
async def test_navigate_missing_url():
    result = await navigate({})
    assert result.success is False
    assert "URL is required" in result.error


# ── extract_content ──

@pytest.mark.asyncio
async def test_extract_content_empty_url():
    result = await extract_content({"url": ""})
    assert result.success is False
    assert "URL is required" in result.error


@pytest.mark.asyncio
async def test_extract_content_missing_url():
    result = await extract_content({})
    assert result.success is False
    assert "URL is required" in result.error


@pytest.mark.asyncio
async def test_extract_content_success():
    with patch("playwright.sync_api.sync_playwright") as mock_sp:
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.title.return_value = "Example"
        mock_page.inner_text.return_value = "Hello World"
        mock_browser.new_page.return_value = mock_page
        mock_p.chromium.launch.return_value = mock_browser
        mock_sp.return_value.__enter__.return_value = mock_p

        result = await extract_content({"url": "https://example.com"})
        assert result.success is True
        assert result.data["title"] == "Example"
        assert result.data["content"] == "Hello World"
        mock_browser.close.assert_called_once()


@pytest.mark.asyncio
async def test_extract_content_playwright_error():
    with patch("playwright.sync_api.sync_playwright") as mock_sp:
        mock_sp.side_effect = Exception("Launch failed")
        result = await extract_content({"url": "https://example.com"})
        assert result.success is False
        assert "Launch failed" in result.error
