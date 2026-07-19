"""Planner — task decomposition, execution graph, and recovery."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4
from aios.core.capability_registry import CapabilityRegistry


class StepStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


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
            self.created_at = datetime.utcnow()


@dataclass
class PlanValidation:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    estimated_risk: float = 0.0
    required_permissions: list[int] = field(default_factory=list)


@dataclass
class PlanResult:
    success: bool
    plan: Plan
    error: str | None = None


class Planner:
    def __init__(self, capability_registry: CapabilityRegistry | None = None):
        self._plans: dict[str, Plan] = {}
        self._capability_registry = capability_registry

    async def create_plan(self, request: str, context: dict | None = None) -> Plan:
        plan = Plan(request=request, context=context or {})
        plan.steps.append(
            Step(id=uuid4().hex, capability="request.process", params={"request": request})
        )
        self._plans[plan.id] = plan
        return plan

    async def execute_plan(self, plan: Plan) -> PlanResult:
        for step in plan.steps:
            step.status = StepStatus.RUNNING
            try:
                step.status = StepStatus.SUCCESS
            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)
                return PlanResult(success=False, plan=plan, error=str(e))

        plan.status = "completed"
        return PlanResult(success=True, plan=plan)

    async def validate_plan(self, plan: Plan) -> PlanValidation:
        validation = PlanValidation()
        return validation

    async def recover_plan(self, plan: Plan, failed_step: Step) -> Plan:
        new_plan = Plan(request=plan.request, context=plan.context)
        for step in plan.steps:
            if step.id == failed_step.id:
                continue
            new_plan.steps.append(step)
        self._plans[new_plan.id] = new_plan
        return new_plan

    async def select_best_capability(self, task: str, interface: str = "chat", min_permission: int = 0) -> tuple[str, float] | None:
        """Select the best capability for a task using intelligence ranking.

        Returns (capability_id, score) or None if no capability scores above threshold.
        """
        if not self._capability_registry:
            return None
        ranked = await self._capability_registry.rank_for_task(task)
        for cap, score in ranked:
            if score > 0 and cap.permission_level <= min_permission + 2:
                if interface in cap.supported_interfaces:
                    return (cap.id, score)
        return None

    async def get_fallback_capability(self, task: str) -> str | None:
        """Find a fallback capability when the primary selection is unavailable."""
        if not self._capability_registry:
            return None
        ranked = await self._capability_registry.rank_for_task(task)
        for cap, score in ranked:
            if score > 0:
                return cap.id
        return None

    async def get_related_capabilities(self, capability_id: str, max_results: int = 5) -> list[dict]:
        """Get related/recommended capabilities for a given capability id."""
        if not self._capability_registry:
            return []
        alternatives = await self._capability_registry.recommend_alternatives(capability_id, max_results)
        return [
            {"id": c.id, "name": c.name, "description": c.description, "quality": c.quality}
            for c in alternatives
        ]
