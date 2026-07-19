# ADR 0001: Use Tauri + Python for Desktop Application

**Status:** Accepted  
**Date:** 2026-07-18  
**Author:** Architecture Team

---

## Context

AIOS needs a desktop application framework that supports a React frontend and a Python backend, with minimal bundle size and strong security.

## Decision

Use **Tauri 2.x** as the desktop shell with a **React + TypeScript** frontend and a **Python + FastAPI** backend.

## Rationale

- **Tauri** — Lightweight (~5MB bundle vs Electron's ~150MB), Rust-based security model, native OS integration
- **React + TypeScript** — Mature ecosystem, type safety, large talent pool
- **Python + FastAPI** — Best AI/ML ecosystem, async support, auto-docs
- **Tauri sidecar** — Python runs as a sidecar process managed by Tauri

## Alternatives Rejected

| Alternative | Reason |
|-------------|--------|
| Electron | 30x larger bundle, higher memory usage, slower startup |
| Qt/C++ | Less ecosystem support for AI/ML, harder to extend |
| .NET MAUI | Windows-only, smaller ecosystem |
| Go backend | Less AI/ML library support |

## Consequences

- Python must be bundled or required as a dependency
- Tauri-Python communication via localhost HTTP
- Rust knowledge needed for Tauri configuration changes
