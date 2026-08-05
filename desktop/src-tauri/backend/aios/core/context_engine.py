"""Context Engine — re-exported from aios.core.context package."""

from aios.core.context import ExecutionContext, ContextEngine

# Backward-compatible alias
Context = ExecutionContext

__all__ = ["Context", "ExecutionContext", "ContextEngine"]
