"""Planner — task decomposition, execution graph, and recovery."""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from aios.core.capability_registry import CapabilityRegistry


MIN_CAPABILITY_SCORE = 0.3

_step_order = {
    "search": 10, "search.files": 10, "search.by_extension": 10, "search.by_name": 10,
    "search.by_size": 10, "search.by_modified": 10, "search.by_regex": 10,
    "file.list": 10, "file.metadata": 10, "file.hash": 10,
    "file.read": 20, "content.read_text": 20, "content.read_csv": 20,
    "content.read_json": 20, "content.parse_markdown": 20,
    "content.search_text": 20, "content.search_regex": 20,
    "content.search_code": 20, "content.detect_language": 20,
    "office.read_pdf": 20, "office.read_docx": 20,
    "browser": 25, "browser.navigate": 25, "http.get": 25,
    "download.file": 25,
    "content": 30, "content.extract_links": 30, "content.markdown_outline": 30,
    "content.count_lines": 30, "content.list_functions": 30, "content.list_classes": 30,
    "content.extract_symbols": 30,
    "office": 30, "office.extract_headings": 30, "office.list_sheets": 30,
    "office.read_sheet": 30,
    "content.write_text": 40, "content.replace_text": 40, "content.append_text": 40,
    "content.write_csv": 40, "content.write_json": 40,
    "file.write": 40, "file.create": 40, "file.copy": 40, "file.move": 40,
    "file.rename": 40, "file.delete": 40, "file.create_directory": 40,
    "archive": 45, "archive.compress": 45, "archive.extract": 45,
    "archive.list": 45, "archive.validate": 45,
    "terminal": 50, "terminal.run_command": 50,
    "powershell": 50, "powershell.run": 50,
    "git": 60,
    "git.status": 60, "git.diff": 60, "git.add": 60,
    "git.commit": 60, "git.push": 60, "git.pull": 60,
    "git.create_branch": 60, "git.checkout_branch": 60,
    "notification": 90, "notification.send": 90,
    "upload.file": 90, "api.send_json": 90,
}


class StepStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class Step:
    id: str = ""
    capability: str = ""
    params: dict = field(default_factory=dict)
    status: str = StepStatus.PENDING
    result: Any = None
    error: str | None = None
    depends_on: list[str] = field(default_factory=list)
    timeout: int = 30


@dataclass
class Plan:
    id: str = ""
    request: str = ""
    steps: list[Step] = field(default_factory=list)
    status: str = "pending"
    context: dict = field(default_factory=dict)
    created_at: datetime = None

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class PlanValidation:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    estimated_risk: float = 0.0
    required_permissions: list[int] = field(default_factory=list)


@dataclass
class PlanResult:
    plan_id: str = ""
    success: bool = False
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    total_steps: int = 0
    duration_ms: float = 0.0
    error: str | None = None


class Planner:
    def __init__(
        self,
        capability_registry: CapabilityRegistry | None = None,
        event_bus=None,
    ):
        self._plans: dict[str, Plan] = {}
        self._plan_results: dict[str, PlanResult] = {}
        self._capability_registry = capability_registry
        self._event_bus = event_bus

    def _order_index(self, cap_id: str) -> int:
        for prefix, order in sorted(_step_order.items(), key=lambda x: -len(x[0])):
            if cap_id.startswith(prefix):
                return order
        return 50

    async def create_plan(self, request: str, context: dict | None = None) -> Plan:
        plan = Plan(request=request, context=context or {})
        seen = set()
        steps_with_order = []

        if self._capability_registry:
            ranked = await self._capability_registry.rank_for_task(request)
            for cap, score in ranked:
                if score < MIN_CAPABILITY_SCORE:
                    continue
                if cap.id in seen:
                    continue
                seen.add(cap.id)
                order = self._order_index(cap.id)
                step = Step(
                    id=uuid4().hex,
                    capability=cap.id,
                    params={},
                    timeout=cap.parameters.get("timeout", 30) if hasattr(cap, "parameters") and isinstance(cap.parameters, dict) else 30,
                    depends_on=[],
                )
                steps_with_order.append((order, step))

        if not steps_with_order:
            step = Step(id=uuid4().hex, capability="request.process", params={"request": request})
            steps_with_order.append((50, step))

        steps_with_order.sort(key=lambda x: x[0])
        plan.steps = [s for _, s in steps_with_order]

        self._plans[plan.id] = plan
        await self._publish_event("planner:plan_created", {
            "plan_id": plan.id,
            "request": request,
            "step_count": len(plan.steps),
        })
        return plan

    async def validate_plan(self, plan: Plan) -> PlanValidation:
        validation = PlanValidation()
        if not plan.steps:
            validation.is_valid = False
            validation.errors.append("Plan has no steps")
            return validation

        step_ids = {s.id for s in plan.steps}

        for step in plan.steps:
            if not step.capability:
                validation.is_valid = False
                validation.errors.append(f"Step {step.id} has no capability")
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    validation.is_valid = False
                    validation.errors.append(
                        f"Step {step.id} depends on unknown step {dep_id}"
                    )

        try:
            self._topological_sort_inner(plan.steps)
        except ValueError as e:
            validation.is_valid = False
            validation.errors.append(str(e))

        return validation

    @staticmethod
    def _topological_sort_inner(steps: list[Step]) -> list[list[Step]]:
        step_map = {s.id: s for s in steps}
        in_degree = {s.id: len(s.depends_on) for s in steps}
        adj: dict[str, list[str]] = {s.id: [] for s in steps}

        for s in steps:
            for dep_id in s.depends_on:
                if dep_id in adj:
                    adj[dep_id].append(s.id)

        queue = [s.id for s in steps if in_degree[s.id] == 0]
        groups: list[list[Step]] = []
        visited: set[str] = set()

        while queue:
            group: list[Step] = []
            for node_id in queue:
                if node_id in step_map and node_id not in visited:
                    visited.add(node_id)
                    group.append(step_map[node_id])

            if not group:
                break

            groups.append(group)

            next_queue: list[str] = []
            for node_id in queue:
                for neighbor in adj[node_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0 and neighbor not in visited:
                        next_queue.append(neighbor)
            queue = next_queue

        if len(visited) < len(steps):
            cycle_ids = [s.id for s in steps if s.id not in visited]
            raise ValueError(
                f"Circular dependency detected involving steps: {cycle_ids}"
            )

        return groups

    async def _topological_sort(self, steps: list[Step]) -> list[list[Step]]:
        return self._topological_sort_inner(steps)

    async def execute_plan(
        self,
        plan: Plan,
        tool_manager=None,
    ) -> Plan:
        if plan.status == "running":
            raise ValueError("Plan is already executing")

        validation = await self.validate_plan(plan)
        if not validation.is_valid:
            plan.status = "failed"
            self._plan_results[plan.id] = PlanResult(
                plan_id=plan.id,
                success=False,
                error="; ".join(validation.errors),
            )
            return plan

        plan.status = "running"
        start_time = time.monotonic()

        try:
            groups = await self._topological_sort(plan.steps)
        except ValueError as e:
            plan.status = "failed"
            self._plan_results[plan.id] = PlanResult(
                plan_id=plan.id,
                success=False,
                error=str(e),
            )
            return plan

        for group in groups:
            tasks = []
            active_steps: list[Step] = []
            for step in group:
                if step.status == StepStatus.SKIPPED:
                    continue
                step.status = StepStatus.RUNNING
                await self._publish_event("planner:step_started", {
                    "plan_id": plan.id,
                    "step_id": step.id,
                    "capability": step.capability,
                })
                tasks.append(self._execute_step(step, tool_manager))
                active_steps.append(step)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, result in zip(active_steps, results):
                if isinstance(result, Exception):
                    step.status = StepStatus.FAILED
                    step.error = str(result)
                    await self._publish_event("planner:step_failed", {
                        "plan_id": plan.id,
                        "step_id": step.id,
                        "capability": step.capability,
                        "error": str(result),
                    })
                elif step.status == StepStatus.TIMEOUT:
                    await self._publish_event("planner:step_failed", {
                        "plan_id": plan.id,
                        "step_id": step.id,
                        "capability": step.capability,
                        "error": f"Timed out after {step.timeout}s",
                    })
                elif step.status == StepStatus.SUCCESS:
                    await self._publish_event("planner:step_completed", {
                        "plan_id": plan.id,
                        "step_id": step.id,
                        "capability": step.capability,
                    })
                elif step.status == StepStatus.FAILED:
                    await self._publish_event("planner:step_failed", {
                        "plan_id": plan.id,
                        "step_id": step.id,
                        "capability": step.capability,
                        "error": step.error,
                    })

            failed_step_ids = {s.id for s in group if s.status in (StepStatus.FAILED, StepStatus.TIMEOUT)}
            if not failed_step_ids:
                continue

            remaining_steps = [s for s in plan.steps if s not in group]
            for s in remaining_steps:
                if any(dep in failed_step_ids for dep in s.depends_on):
                    if s.status == StepStatus.PENDING:
                        s.status = StepStatus.SKIPPED
                        s.error = "Dependency failed"
                        await self._publish_event("planner:step_skipped", {
                            "plan_id": plan.id,
                            "step_id": s.id,
                            "capability": s.capability,
                            "reason": "Dependency failed",
                        })

        duration_ms = (time.monotonic() - start_time) * 1000

        completed = sum(1 for s in plan.steps if s.status == StepStatus.SUCCESS)
        failed = sum(1 for s in plan.steps if s.status in (StepStatus.FAILED, StepStatus.TIMEOUT))
        skipped = sum(1 for s in plan.steps if s.status == StepStatus.SKIPPED)

        all_ok = failed == 0
        plan.status = "completed" if all_ok else "failed"

        result = PlanResult(
            plan_id=plan.id,
            success=all_ok,
            completed_steps=completed,
            failed_steps=failed,
            skipped_steps=skipped,
            total_steps=len(plan.steps),
            duration_ms=round(duration_ms, 2),
        )
        self._plan_results[plan.id] = result

        await self._publish_event("planner:plan_completed", {
            "plan_id": plan.id,
            "success": all_ok,
            "completed_steps": completed,
            "failed_steps": failed,
            "total_steps": len(plan.steps),
            "duration_ms": result.duration_ms,
        })

        return plan

    async def _execute_step(
        self,
        step: Step,
        tool_manager=None,
    ) -> None:
        if step.status in (StepStatus.SKIPPED,):
            return
        try:
            if tool_manager:
                try:
                    tool_result = await asyncio.wait_for(
                        tool_manager.execute(step.capability, step.params),
                        timeout=step.timeout,
                    )
                    if hasattr(tool_result, "success") and tool_result.success:
                        step.status = StepStatus.SUCCESS
                        step.result = getattr(tool_result, "data", None)
                    elif hasattr(tool_result, "success") and not tool_result.success:
                        step.status = StepStatus.FAILED
                        step.error = getattr(tool_result, "error", "Execution failed")
                        if hasattr(tool_result, "data") and tool_result.data:
                            if isinstance(tool_result.data, dict) and "permission_request_id" in tool_result.data:
                                step.error = "Permission denied"
                    else:
                        step.status = StepStatus.SUCCESS
                        step.result = tool_result
                except asyncio.TimeoutError:
                    step.status = StepStatus.TIMEOUT
                    step.error = f"Step timed out after {step.timeout}s"
            else:
                step.status = StepStatus.SUCCESS
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)

    async def recover_plan(self, plan: Plan, failed_step: Step) -> Plan:
        new_plan = Plan(request=plan.request, context=plan.context)
        all_failed_ids = {failed_step.id}
        for s in plan.steps:
            if s.id == failed_step.id:
                continue
            if s.id in all_failed_ids:
                continue
            if any(dep in all_failed_ids for dep in s.depends_on):
                all_failed_ids.add(s.id)
                continue
            new_plan.steps.append(s)
        self._plans[new_plan.id] = new_plan
        await self._publish_event("planner:plan_recovered", {
            "original_plan_id": plan.id,
            "new_plan_id": new_plan.id,
            "removed_step_ids": list(all_failed_ids),
        })
        return new_plan

    async def select_best_capability(self, task: str, interface: str = "chat", min_permission: int = 0) -> tuple[str, float] | None:
        if not self._capability_registry:
            return None
        ranked = await self._capability_registry.rank_for_task(task)
        for cap, score in ranked:
            if score >= MIN_CAPABILITY_SCORE:
                if cap.permission_level <= min_permission + 2:
                    if interface in cap.supported_interfaces:
                        return (cap.id, score)
        return None

    async def get_fallback_capability(self, task: str) -> str | None:
        if not self._capability_registry:
            return None
        ranked = await self._capability_registry.rank_for_task(task)
        for cap, score in ranked:
            if score >= MIN_CAPABILITY_SCORE:
                return cap.id
        return None

    async def get_related_capabilities(self, capability_id: str, max_results: int = 5) -> list[dict]:
        if not self._capability_registry:
            return []
        alternatives = await self._capability_registry.recommend_alternatives(capability_id, max_results)
        return [
            {"id": c.id, "name": c.name, "description": c.description, "quality": c.quality}
            for c in alternatives
        ]

    async def get_plan_result(self, plan_id: str) -> PlanResult | None:
        return self._plan_results.get(plan_id)

    async def get_plan(self, plan_id: str) -> Plan | None:
        return self._plans.get(plan_id)

    async def list_plans(self, limit: int = 20) -> list[Plan]:
        plans = list(self._plans.values())
        plans.sort(key=lambda p: p.created_at, reverse=True)
        return plans[:limit]

    async def _publish_event(self, event_type: str, payload: dict) -> None:
        if self._event_bus is not None:
            try:
                await self._event_bus.publish(
                    event_type=event_type,
                    payload=payload,
                    source="planner",
                )
            except Exception:
                pass
