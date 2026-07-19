# ADR 0006: SQLite for Local Data Storage

**Status:** Accepted  
**Date:** 2026-07-18  
**Author:** Architecture Team

---

## Context

AIOS needs to persist conversations, tool calls, memories, events, settings, and plugin data. The storage must be local, zero-config, and reliable.

## Decision

Use **SQLite** as the primary data store, with avector extension for embedding-based semantic search.

## Rationale

- **Zero configuration** — No database server needed
- **Single file** — Easy backup, portable
- **SQL** — Powerful query language, well-understood
- **JSON1 extension** — Native JSON support for flexible schemas
- **Performance** — Sufficient for single-user desktop app
- **Embedding support** — SQLite + vector extension for semantic search

## Alternatives Rejected

| Alternative | Reason |
|-------------|--------|
| PostgreSQL | Overkill for desktop app, requires server |
| MongoDB | Higher complexity, no native Windows integration |
| JSON files | No querying, no relationships, no integrity |
| DuckDB | Analytics-oriented, less ecosystem for vector search |

## Consequences

- Database size limit for vector storage
- Must handle concurrent access (WAL mode)
- Migrations needed for schema changes
- Encryption needed for sensitive data
