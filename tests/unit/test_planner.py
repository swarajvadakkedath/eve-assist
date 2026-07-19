"""Tests for Planner."""

import pytest
from aios.core.planner import Planner, StepStatus


@pytest.fixture
def planner():
    return Planner()


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
