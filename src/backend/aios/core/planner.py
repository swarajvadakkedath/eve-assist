"""Planner — task decomposition, execution graph, and recovery."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4
from aios.core.capability_registry import CapabilityRegistry


MIN_CAPABILITY_SCORE = 0.3

_step_order = {
    # Low-level filesystem / search first
    "search": 10, "search.files": 10, "search.by_extension": 10, "search.by_name": 10,
    "search.by_size": 10, "search.by_modified": 10, "search.by_regex": 10,
    "file.list": 10, "file.metadata": 10, "file.hash": 10,
    # Read / inspect
    "file.read": 20, "content.read_text": 20, "content.read_csv": 20,
    "content.read_json": 20, "content.parse_markdown": 20,
    "content.search_text": 20, "content.search_regex": 20,
    "content.search_code": 20, "content.detect_language": 20,
    "office.read_pdf": 20, "office.read_docx": 20,
    # Browser / network
    "browser": 25, "browser.navigate": 25, "http.get": 25,
    "download.file": 25,
    # Process / analyze
    "content": 30, "content.extract_links": 30, "content.markdown_outline": 30,
    "content.count_lines": 30, "content.list_functions": 30, "content.list_classes": 30,
    "content.extract_symbols": 30,
    "office": 30, "office.extract_headings": 30, "office.list_sheets": 30,
    "office.read_sheet": 30,
    # Modify content
    "content.write_text": 40, "content.replace_text": 40, "content.append_text": 40,
    "content.write_csv": 40, "content.write_json": 40,
    "file.write": 40, "file.create": 40, "file.copy": 40, "file.move": 40,
    "file.rename": 40, "file.delete": 40, "file.create_directory": 40,
    # Compress / archive
    "archive": 45, "archive.compress": 45, "archive.extract": 45,
    "archive.list": 45, "archive.validate": 45,
    # Terminal / process
    "terminal": 50, "terminal.run_command": 50,
    "powershell": 50, "powershell.run": 50,
    "git": 60,
    "git.status": 60, "git.diff": 60, "git.add": 60,
    "git.commit": 60, "git.push": 60, "git.pull": 60,
    "git.create_branch": 60, "git.checkout_branch": 60,
    # Network / notify after everything
    "notification": 90, "notification.send": 90,
    "upload.file": 90, "api.send_json": 90,
}


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

    def _order_index(self, cap_id: str) -> int:
        """Determine execution order priority for a capability."""
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
        if not plan.steps:
            validation.is_valid = False
            validation.errors.append("Plan has no steps")
        for step in plan.steps:
            if not step.capability:
                validation.is_valid = False
                validation.errors.append(f"Step {step.id} has no capability")
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
            if score >= MIN_CAPABILITY_SCORE:
                if cap.permission_level <= min_permission + 2:
                    if interface in cap.supported_interfaces:
                        return (cap.id, score)
        return None

    async def get_fallback_capability(self, task: str) -> str | None:
        """Find a fallback capability when the primary selection is unavailable."""
        if not self._capability_registry:
            return None
        ranked = await self._capability_registry.rank_for_task(task)
        for cap, score in ranked:
            if score >= MIN_CAPABILITY_SCORE:
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
