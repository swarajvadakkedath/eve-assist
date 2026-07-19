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


@pytest.mark.asyncio
async def test_new_metadata_fields_defaults(cr):
    cap = Capability(id="test.cap", name="Test", description="Test capability",
                     provider_type="tool", provider_id="test")
    assert cap.supported_interfaces == ["chat"]
    assert cap.supports_streaming is False
    assert cap.supports_cancellation is False
    assert cap.estimated_latency == 0.0
    assert cap.estimated_cost == 0.0
    assert cap.reliability_score == 1.0
    assert cap.requires_confirmation is False
    assert cap.related_capabilities == []


@pytest.mark.asyncio
async def test_search_by_category(cr):
    await cr.register_capability(Capability(id="file.read", name="Read", description="Read file",
                                            provider_type="tool", provider_id="r", tags=["file"]))
    await cr.register_capability(Capability(id="file.write", name="Write", description="Write file",
                                            provider_type="tool", provider_id="w", tags=["file"]))
    await cr.register_capability(Capability(id="system.info", name="Info", description="System info",
                                            provider_type="tool", provider_id="i", tags=["system"]))
    file_caps = await cr.search_by_category("file")
    assert len(file_caps) == 2
    system_caps = await cr.search_by_category("system")
    assert len(system_caps) == 1


@pytest.mark.asyncio
async def test_filter_by_permission(cr):
    await cr.register_capability(Capability(id="a", name="A", description="A",
                                            provider_type="tool", provider_id="a", permission_level=0))
    await cr.register_capability(Capability(id="b", name="B", description="B",
                                            provider_type="tool", provider_id="b", permission_level=2))
    await cr.register_capability(Capability(id="c", name="C", description="C",
                                            provider_type="tool", provider_id="c", permission_level=3))
    filtered = await cr.filter_by_permission(min_level=2)
    assert len(filtered) == 2
    filtered2 = await cr.filter_by_permission(min_level=0, max_level=1)
    assert len(filtered2) == 1


@pytest.mark.asyncio
async def test_filter_by_interface(cr):
    await cr.register_capability(Capability(id="chat", name="Chat", description="Chat",
                                            provider_type="tool", provider_id="c",
                                            supported_interfaces=["chat"]))
    await cr.register_capability(Capability(id="vision", name="Vision", description="Vision",
                                            provider_type="tool", provider_id="v",
                                            supported_interfaces=["vision"]))
    chat_caps = await cr.filter_by_interface("chat")
    assert len(chat_caps) == 1
    vision_caps = await cr.filter_by_interface("vision")
    assert len(vision_caps) == 1


@pytest.mark.asyncio
async def test_rank_for_task(cr):
    await cr.register_capability(Capability(id="file.read", name="File Reader", description="Read files from disk",
                                            provider_type="tool", provider_id="fr", quality=0.9,
                                            tags=["file", "read"]))
    await cr.register_capability(Capability(id="web.search", name="Web Search", description="Search the internet",
                                            provider_type="tool", provider_id="ws", quality=0.95,
                                            tags=["web", "search"]))
    await cr.register_capability(Capability(id="system.info", name="System Info", description="Get OS info",
                                            provider_type="tool", provider_id="si", quality=0.8,
                                            tags=["system", "info"]))
    ranked = await cr.rank_for_task("read file from disk")
    assert len(ranked) == 3
    assert ranked[0][0].id == "file.read"
    assert ranked[0][1] > 0


@pytest.mark.asyncio
async def test_recommend_alternatives_by_tags(cr):
    await cr.register_capability(Capability(id="file.read", name="Read", description="Read",
                                            provider_type="tool", provider_id="r",
                                            tags=["file", "read"], related_capabilities=["file.write"]))
    await cr.register_capability(Capability(id="file.write", name="Write", description="Write",
                                            provider_type="tool", provider_id="w",
                                            tags=["file", "write"]))
    await cr.register_capability(Capability(id="system.info", name="Info", description="Info",
                                            provider_type="tool", provider_id="i",
                                            tags=["system"]))
    recs = await cr.recommend_alternatives("file.read", max_results=5)
    ids = [c.id for c in recs]
    assert "file.write" in ids
    assert "system.info" not in ids  # no shared tags


@pytest.mark.asyncio
async def test_recommend_alternatives_no_match(cr):
    recs = await cr.recommend_alternatives("nonexistent")
    assert recs == []
