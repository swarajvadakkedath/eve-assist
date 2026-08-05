"""Context Engine API — /api/v1/context endpoints for AI Operations Center.

Exposes Context Engine diagnostics, provider status, and context snapshots.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from aios.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/context", tags=["context-engine"])

# Module-level references — set during app startup
_context_engine = None
_context_policy = None


def configure(context_engine, context_policy=None) -> None:
    """Set references during app startup."""
    global _context_engine, _context_policy
    _context_engine = context_engine
    _context_policy = context_policy


@router.get("/diagnostics")
async def get_diagnostics():
    """Return Context Engine diagnostics for AI Operations Center."""
    if _context_engine is None:
        return {"error": "Context Engine not initialized"}
    return _context_engine.diagnostics()


@router.get("/snapshot")
async def get_snapshot():
    """Return current ExecutionContext snapshot."""
    if _context_engine is None:
        return {"error": "Context Engine not initialized"}
    ctx = await _context_engine.snapshot()
    return ctx.to_dict()


@router.get("/providers")
async def list_providers():
    """List registered context providers and their status."""
    if _context_engine is None:
        return {"providers": []}
    return {"providers": _context_engine.list_providers()}


@router.get("/version")
async def get_version():
    """Return current context version."""
    if _context_engine is None:
        return {"version": 0}
    return {"version": _context_engine.get_version()}


@router.post("/refresh")
async def refresh_context(section: str | None = Query(None)):
    """Force a context refresh, optionally for a specific section."""
    if _context_engine is None:
        return {"error": "Context Engine not initialized"}
    if section:
        await _context_engine.refresh_section(section)
    else:
        await _context_engine.collect()
    return {"status": "refreshed", "section": section}


@router.get("/policy/evaluate")
async def evaluate_policy():
    """Evaluate current context against privacy policies."""
    if _context_engine is None or _context_policy is None:
        return {"error": "Not initialized"}
    ctx = await _context_engine.snapshot()
    decision = _context_policy.evaluate(ctx)
    return {
        "allowed": decision.allowed,
        "redacted": decision.redacted,
        "redacted_fields": decision.redacted_fields,
    }
