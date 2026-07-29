"""Tests for Planner."""

import pytest
from aios.core.planner import Planner, Step, StepStatus, Plan, PlanResult
from aios.core.capability_registry import CapabilityRegistry, Capability
from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager


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
async def test_validate_plan(planner):
    plan = await planner.create_plan("Test plan")
    validation = await planner.validate_plan(plan)
    assert validation.is_valid


@pytest.mark.asyncio
async def test_recover_plan(planner):
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


@pytest.mark.asyncio
async def test_execute_plan(planner):
    plan = Plan(request="Test execution", steps=[
        Step(id="s1", capability="step.one", params={}, depends_on=[], timeout=10),
        Step(id="s2", capability="step.two", params={}, depends_on=["s1"], timeout=10),
    ])
    result = await planner.execute_plan(plan)
    assert result.status == "completed"
    for s in result.steps:
        assert s.status == StepStatus.SUCCESS


@pytest.mark.asyncio
async def test_execute_plan_with_tool_manager(planner):
    tm = ToolManager(PermissionManager())
    async def handler_ok(params):
        return ToolResult(success=True, data="done")
    await tm.register_tool(
        ToolContract(id="test.tool", name="Test", description="Test tool",
                     permission_level=0),
        handler_ok,
    )
    plan = Plan(request="Test", steps=[
        Step(id="s1", capability="test.tool", params={}, timeout=10),
    ])
    result = await planner.execute_plan(plan, tool_manager=tm)
    assert result.status == "completed"
    assert result.steps[0].status == StepStatus.SUCCESS
    assert result.steps[0].result == "done"


@pytest.mark.asyncio
async def test_execute_plan_tool_not_found(planner):
    tm = ToolManager(PermissionManager())
    plan = Plan(request="Test", steps=[
        Step(id="s1", capability="nonexistent.tool", params={}, timeout=10),
    ])
    result = await planner.execute_plan(plan, tool_manager=tm)
    assert result.steps[0].status == StepStatus.FAILED
    assert "not found" in (result.steps[0].error or "").lower()


@pytest.mark.asyncio
async def test_execute_plan_timeout(planner):
    tm = ToolManager(PermissionManager())
    async def slow_handler(params):
        import asyncio
        await asyncio.sleep(10)
        return ToolResult(success=True, data="too late")
    await tm.register_tool(
        ToolContract(id="slow.tool", name="Slow", description="Slow tool",
                     permission_level=0),
        slow_handler,
    )
    plan = Plan(request="Test", steps=[
        Step(id="s1", capability="slow.tool", params={}, timeout=0.05),
    ])
    result = await planner.execute_plan(plan, tool_manager=tm)
    assert result.steps[0].status == StepStatus.TIMEOUT


@pytest.mark.asyncio
async def test_execute_plan_parallel(planner):
    tm = ToolManager(PermissionManager())
    execution_order = []
    async def make_handler(name):
        async def handler(params):
            execution_order.append(name)
            return ToolResult(success=True, data=name)
        return handler
    await tm.register_tool(
        ToolContract(id="tool.a", name="Tool A", description="A", permission_level=0),
        await make_handler("a"),
    )
    await tm.register_tool(
        ToolContract(id="tool.b", name="Tool B", description="B", permission_level=0),
        await make_handler("b"),
    )
    plan = Plan(request="Parallel test", steps=[
        Step(id="s1", capability="tool.a", params={}, depends_on=[], timeout=10),
        Step(id="s2", capability="tool.b", params={}, depends_on=[], timeout=10),
    ])
    result = await planner.execute_plan(plan, tool_manager=tm)
    assert result.status == "completed"
    assert result.steps[0].status == StepStatus.SUCCESS
    assert result.steps[1].status == StepStatus.SUCCESS


@pytest.mark.asyncio
async def test_execute_plan_dependency_skipped(planner):
    tm = ToolManager(PermissionManager())
    async def fail_handler(params):
        return ToolResult(success=False, error="Intentional failure")
    await tm.register_tool(
        ToolContract(id="failing.tool", name="Fail", description="Fails",
                     permission_level=0),
        fail_handler,
    )
    async def ok_handler(params):
        return ToolResult(success=True, data="ok")
    await tm.register_tool(
        ToolContract(id="dependent.tool", name="Dep", description="Depends on fail",
                     permission_level=0),
        ok_handler,
    )
    plan = Plan(request="Dep test", steps=[
        Step(id="s1", capability="failing.tool", params={}, depends_on=[], timeout=10),
        Step(id="s2", capability="dependent.tool", params={}, depends_on=["s1"], timeout=10),
    ])
    result = await planner.execute_plan(plan, tool_manager=tm)
    assert result.steps[0].status == StepStatus.FAILED
    assert result.steps[1].status == StepStatus.SKIPPED


@pytest.mark.asyncio
async def test_get_plan_result(planner):
    plan = Plan(request="Result test", steps=[
        Step(id="s1", capability="test.step", params={}, timeout=10),
    ])
    await planner.execute_plan(plan)
    result = await planner.get_plan_result(plan.id)
    assert result is not None
    assert result.plan_id == plan.id
    assert result.success is True
    assert result.completed_steps == 1


@pytest.mark.asyncio
async def test_get_plan_result_not_found(planner):
    result = await planner.get_plan_result("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_plan(planner):
    plan = await planner.create_plan("Retrieve test")
    found = await planner.get_plan(plan.id)
    assert found is not None
    assert found.id == plan.id


@pytest.mark.asyncio
async def test_list_plans(planner):
    await planner.create_plan("Plan A")
    await planner.create_plan("Plan B")
    plans = await planner.list_plans()
    assert len(plans) >= 2


@pytest.mark.asyncio
async def test_execute_plan_already_running(planner):
    plan = Plan(request="Double exec", steps=[
        Step(id="s1", capability="test.step", params={}, timeout=10),
    ])
    plan.status = "running"
    with pytest.raises(ValueError, match="already executing"):
        await planner.execute_plan(plan)


@pytest.mark.asyncio
async def test_execute_plan_empty(planner):
    plan = Plan(request="Empty", steps=[])
    result = await planner.execute_plan(plan)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_execute_plan_unknown_dependency(planner):
    plan = Plan(request="Bad dep", steps=[
        Step(id="s1", capability="test.step", params={}, depends_on=["nonexistent"], timeout=10),
    ])
    result = await planner.execute_plan(plan)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_topological_sort_simple(planner):
    from aios.core.planner import Step
    steps = [
        Step(id="a", capability="a", depends_on=[]),
        Step(id="b", capability="b", depends_on=["a"]),
        Step(id="c", capability="c", depends_on=["b"]),
    ]
    groups = await planner._topological_sort(steps)
    assert len(groups) == 3
    assert groups[0][0].id == "a"
    assert groups[1][0].id == "b"
    assert groups[2][0].id == "c"


@pytest.mark.asyncio
async def test_topological_sort_parallel(planner):
    from aios.core.planner import Step
    steps = [
        Step(id="a", capability="a", depends_on=[]),
        Step(id="b", capability="b", depends_on=[]),
        Step(id="c", capability="c", depends_on=["a", "b"]),
    ]
    groups = await planner._topological_sort(steps)
    assert len(groups) == 2
    assert len(groups[0]) == 2
    assert groups[1][0].id == "c"


@pytest.mark.asyncio
async def test_topological_sort_cycle(planner):
    from aios.core.planner import Step
    steps = [
        Step(id="a", capability="a", depends_on=["b"]),
        Step(id="b", capability="b", depends_on=["a"]),
    ]
    with pytest.raises(ValueError, match="Circular dependency"):
        await planner._topological_sort(steps)


@pytest.mark.asyncio
async def test_event_bus_integration(planner):
    from aios.core.event_bus import EventBus
    eb = EventBus()
    await eb.start()
    planner._event_bus = eb
    events = []
    async def collect(event):
        events.append(event.type)
    await eb.subscribe("planner:plan_created", collect)
    await eb.subscribe("planner:plan_completed", collect)
    await eb.subscribe("planner:step_started", collect)
    await eb.subscribe("planner:step_completed", collect)
    plan = Plan(request="Event test", steps=[
        Step(id="s1", capability="test.event", params={}, timeout=10),
    ])
    await planner.execute_plan(plan)
    import asyncio
    await asyncio.sleep(0.05)
    assert "planner:plan_created" not in events
    assert "planner:step_started" in events
    assert "planner:step_completed" in events
    assert "planner:plan_completed" in events
    await eb.stop()


@pytest.mark.asyncio
async def test_recover_plan_removes_dependents(planner):
    plan = Plan(request="Recovery with deps", steps=[
        Step(id="s1", capability="step.a", params={}, depends_on=[], timeout=10),
        Step(id="s2", capability="step.b", params={}, depends_on=["s1"], timeout=10),
        Step(id="s3", capability="step.c", params={}, depends_on=["s2"], timeout=10),
    ])
    failed = plan.steps[0]
    recovered = await planner.recover_plan(plan, failed)
    assert len(recovered.steps) == 0


@pytest.mark.asyncio
async def test_validate_plan_unknown_dependency(planner):
    plan = Plan(request="Bad dep", steps=[
        Step(id="s1", capability="test.step", params={}, depends_on=["ghost"], timeout=10),
    ])
    validation = await planner.validate_plan(plan)
    assert not validation.is_valid
    assert any("ghost" in e for e in validation.errors)
