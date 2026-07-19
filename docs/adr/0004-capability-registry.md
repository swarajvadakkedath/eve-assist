# ADR 0004: Capability Registry for Planner-Tool Decoupling

**Status:** Accepted  
**Date:** 2026-07-18  
**Author:** Architecture Team

---

## Context

The Planner needs to execute user requests but should not know specific tool IDs. Adding a new tool should not require Planner changes.

## Decision

Create a Capability Registry that sits between the Planner and the Tool Manager. The Planner queries capabilities, and the Registry resolves them to specific tools or plugins.

## Rationale

- **Loose coupling** — Planner never imports tool IDs
- **Pluggable architecture** — New tools/plugins register capabilities
- **Conflict resolution** — Weighted scoring for best match
- **Versioning** — Multiple versions of same capability can coexist
- **Discovery** — UI can list available capabilities

## Alternatives Rejected

| Alternative | Reason |
|-------------|--------|
| Hardcoded tool list | Brittle, requires Planner changes for new tools |
| Planner knows tool IDs | Tight coupling, violates modularity |
| AI decides tools | Unpredictable, bypasses permission system |

## Consequences

- Every tool must declare its capabilities
- Conflict resolution logic needed
- Performance overhead for capability queries (mitigated by caching)
