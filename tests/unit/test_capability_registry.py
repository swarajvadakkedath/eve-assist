"""Tests for Capability Registry."""

import pytest
from aios.core.capability_registry import CapabilityRegistry, Capability


@pytest.fixture
def cr():
    return CapabilityRegistry()


@pytest.mark.asyncio
async def test_register_and_find(cr):
    cap = Capability(id="file.search", name="Search Files", description="Search files",
                     provider_type="tool", provider_id="search_files",
                     tags=["file", "search"])
    await cr.register_capability(cap)
    results = await cr.find_capability("file.search")
    assert len(results) == 1
    assert results[0].id == "file.search"


@pytest.mark.asyncio
async def test_find_by_tag(cr):
    cap = Capability(id="app.open", name="Open App", description="Open application",
                     provider_type="tool", provider_id="launch_app",
                     tags=["app", "launch"])
    await cr.register_capability(cap)
    results = await cr.find_capability("app")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_best_match(cr):
    cap1 = Capability(id="web.search", name="Web Search", description="Search web",
                      provider_type="tool", provider_id="web_search_1", quality=0.8,
                      tags=["web", "search"])
    cap2 = Capability(id="web.search", name="Better Web Search", description="Better search",
                      provider_type="plugin", provider_id="web_search_2", quality=0.95,
                      tags=["web", "search"])
    await cr.register_capability(cap1)
    await cr.register_capability(cap2)
    best = await cr.find_best_match("web.search")
    assert best is not None
    assert best.quality == 0.95


@pytest.mark.asyncio
async def test_no_match(cr):
    results = await cr.find_capability("nonexistent")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_list_capabilities(cr):
    await cr.register_capability(Capability(id="a", name="A", description="A",
                                            provider_type="tool", provider_id="a"))
    await cr.register_capability(Capability(id="b", name="B", description="B",
                                            provider_type="tool", provider_id="b"))
    all_caps = await cr.list_capabilities()
    assert len(all_caps) == 2
