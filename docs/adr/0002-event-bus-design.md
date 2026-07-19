# ADR 0002: Event Bus Architecture

**Status:** Accepted  
**Date:** 2026-07-18  
**Author:** Architecture Team

---

## Context

AIOS has multiple modules that need to communicate without tight coupling. The Event Bus must support async, at-least-once delivery, retry, and persistence.

## Decision

Implement an in-process async Event Bus using Python's `asyncio` with an internal message queue, retry with exponential backoff, and SQLite persistence for event history.

## Rationale

- **In-process** — No external message broker needed for a desktop app
- **asyncio** — Native Python async support, lightweight
- **At-least-once delivery** — Balance between reliability and complexity
- **Exponential backoff** — Prevents thundering herd on recovery
- **SQLite persistence** — Event history for debugging and recovery
- **Priority queue** — Critical events (permissions) delivered before informational

## Alternatives Rejected

| Alternative | Reason |
|-------------|--------|
| RabbitMQ | Overkill for single-process desktop app |
| Redis Pub/Sub | External dependency, complexity |
| gRPC streams | Too heavy for in-process communication |
| ZeroMQ | More complex than needed |

## Consequences

- Event Bus is a potential single point of failure
- Must implement health checks
- Dead letter queue needed for failed events
