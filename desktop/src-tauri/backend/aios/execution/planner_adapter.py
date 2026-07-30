"""Planner Adapter — bridges Execution Engine with the Planner."""

from typing import Any
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class PlannerAdapter:
    def __init__(self, planner: Any | None = None):
        self._planner = planner

    async def create_plan(self, objective: str, context: dict | None = None) -> Any | None:
        if not self._planner:
            logger.warning("planner_adapter.no_planner")
            return None
        try:
            plan = await self._planner.create_plan(objective, context)
            logger.info("planner_adapter.plan_created", plan_id=plan.id)
            return plan
        except Exception as e:
            logger.error("planner_adapter.create_failed", error=str(e))
            return None

    async def validate_plan(self, plan: Any) -> Any:
        if not self._planner:
            return None
        try:
            return await self._planner.validate_plan(plan)
        except Exception as e:
            logger.error("planner_adapter.validate_failed", error=str(e))
            return None

    async def recover_plan(self, plan: Any, failed_step: Any) -> Any | None:
        if not self._planner:
            return None
        try:
            return await self._planner.recover_plan(plan, failed_step)
        except Exception as e:
            logger.error("planner_adapter.recover_failed", error=str(e))
            return None
