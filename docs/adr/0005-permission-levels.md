# ADR 0005: Four-Tier Permission System

**Status:** Accepted  
**Date:** 2026-07-18  
**Author:** Architecture Team

---

## Context

AIOS executes actions on behalf of the user. Some actions are harmless (reading system info), while others are dangerous (deleting files). The system needs a permission model that balances convenience with safety.

## Decision

Implement a four-tier permission system:

| Level | Name | Auto-approve | Examples |
|-------|------|-------------|----------|
| 0 | Read | Always | Read files, system info, clipboard |
| 1 | Safe | Always | Create files, open apps, web search |
| 2 | Workspace | Session confirm | Edit files, rename, organize |
| 3 | Sensitive | Always confirm | Delete files, install software |

## Rationale

- **Progressive trust** — Read operations are always safe, sensitive always requires confirmation
- **Session permissions** — Reduces friction for repeated workspace operations
- **Clear user model** — Users understand the four levels easily
- **Configurable** — Users can adjust default levels per tool

## Alternatives Rejected

| Alternative | Reason |
|-------------|--------|
| Binary (allow/deny) | Too coarse, no middle ground |
| Full manual control | Too much friction for basic operations |
| Full automatic | Unsafe for sensitive operations |
| Capability-based only | Hard for users to understand |

## Consequences

- Session permissions expire after configurable timeout
- Permission history is logged for audit
- UI must clearly communicate permission level
