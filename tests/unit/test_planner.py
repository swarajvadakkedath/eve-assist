"""Tests for Planner."""

import pytest
from aios.core.planner import Planner, StepStatus
from aios.core.capability_registry import CapabilityRegistry, Capability


@pytest.fixture
def planner():
    return Planner()


@pytest.fixture
def planner_with_cr():
    return Planner(CapabilityRegistry())


@pytest.mark.asyncio
async def test_create_plan(planner):
    plan = await planner.create_plan("Find large files", {"path": "/"})
    assert plan.request == "Find large files"
    assert len(plan.steps) > 0


@pytest.mark.asyncio
async def test_execute_plan(planner):
    plan = await planner.create_plan("Test plan")
    result = await planner.execute_plan(plan)
    assert result.success is not None


@pytest.mark.asyncio
async def test_validate_plan(planner):
    plan = await planner.create_plan("Test plan")
    validation = await planner.validate_plan(plan)
    assert validation.is_valid


@pytest.mark.asyncio
async def test_recover_plan(planner):
    from aios.core.planner import Step
    plan = await planner.create_plan("Recovery test")
    failed = plan.steps[0]
    failed.status = StepStatus.FAILED
    recovered = await planner.recover_plan(plan, failed)
    assert recovered.id != plan.id


@pytest.mark.asyncio
async def test_select_best_capability_no_cr(planner):
    result = await planner.select_best_capability("test task")
    assert result is None


@pytest.mark.asyncio
async def test_select_best_capability(planner_with_cr):
    cr = planner_with_cr._capability_registry
    await cr.register_capability(Capability(
        id="file.read", name="Read File", description="Read files from disk",
        provider_type="tool", provider_id="fr", quality=0.9,
        tags=["file", "read"], permission_level=0,
        supported_interfaces=["chat"],
    ))
    result = await planner_with_cr.select_best_capability("read file", min_permission=0)
    assert result is not None
    assert result[0] == "file.read"
    assert result[1] > 0


@pytest.mark.asyncio
async def test_get_fallback_capability(planner_with_cr):
    cr = planner_with_cr._capability_registry
    await cr.register_capability(Capability(
        id="file.read", name="Read", description="Read files",
        provider_type="tool", provider_id="fr", tags=["file"],
    ))
    fallback = await planner_with_cr.get_fallback_capability("read")
    assert fallback == "file.read"


@pytest.mark.asyncio
async def test_get_related_capabilities(planner_with_cr):
    cr = planner_with_cr._capability_registry
    await cr.register_capability(Capability(
        id="file.read", name="Read", description="Read files",
        provider_type="tool", provider_id="fr", tags=["file", "read"],
        related_capabilities=["file.write"],
    ))
    await cr.register_capability(Capability(
        id="file.write", name="Write", description="Write files",
        provider_type="tool", provider_id="fw", tags=["file", "write"],
    ))
    related = await planner_with_cr.get_related_capabilities("file.read")
    assert len(related) > 0
    assert related[0]["id"] == "file.write"
