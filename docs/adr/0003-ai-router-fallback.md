# ADR 0003: AI Router with Multi-Provider Fallback

**Status:** Accepted  
**Date:** 2026-07-18  
**Author:** Architecture Team

---

## Context

AIOS must not be dependent on a single AI provider. If one provider fails, the system should gracefully fall back to another.

## Decision

Implement the AI Router with a Strategy pattern for routing decisions and a Failover Manager for provider fallback.

## Rationale

- **Strategy pattern** — Routing strategies are swappable (cost, latency, performance)
- **Failover Manager** — Monitors provider health and switches automatically
- **Circuit breaker** — Prevents retry storms against failing providers
- **Local-first** — Use Ollama for simple queries (zero cost), cloud for complex

## Alternatives Rejected

| Alternative | Reason |
|-------------|--------|
| Single provider | Single point of failure, vendor lock-in |
| Round-robin | No awareness of provider capabilities or cost |
| Manual selection | Poor UX, requires user knowledge |

## Consequences

- Must implement provider abstraction for each provider
- Cost tracking needed for cloud providers
- Health checks consume API quota
