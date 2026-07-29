# 08 — Release Checklist

> **Status:** Approved · v2.0.0  
> **Scope:** Production release process for Eve OS  
> **Last Updated:** 2026-07-21  
> **Current Version:** 1.0.0  
> **Applies To:** Eve OS (AIOS) — Python backend + TypeScript frontend

---

## Table of Contents

1. [Release Stages Overview](#1-release-stages-overview)
2. [Versioning](#2-versioning)
3. [Stage 0 — Pre-Release Planning](#3-stage-0--pre-release-planning)
4. [Stage 1 — Architecture Review](#4-stage-1--architecture-review)
5. [Stage 2 — Code Review](#5-stage-2--code-review)
6. [Stage 3 — Accessibility Review](#6-stage-3--accessibility-review)
7. [Stage 4 — Performance Review](#7-stage-4--performance-review)
8. [Stage 5 — Security Review](#8-stage-5--security-review)
9. [Stage 6 — Documentation Review](#9-stage-6--documentation-review)
10. [Stage 7 — API Review](#10-stage-7--api-review)
11. [Stage 8 — UI Review](#11-stage-8--ui-review)
12. [Stage 9 — Memory Review](#12-stage-9--memory-review)
13. [Stage 10 — Execution Review](#13-stage-10--execution-review)
14. [Stage 11 — Command Center Review](#14-stage-11--command-center-review)
15. [Stage 12 — Settings Review](#15-stage-12--settings-review)
16. [Stage 13 — Packaging](#16-stage-13--packaging)
17. [Stage 14 — Installers](#17-stage-14--installers)
18. [Stage 15 — Signing](#18-stage-15--signing)
19. [Stage 16 — Auto Update](#19-stage-16--auto-update)
20. [Stage 17 — Release Notes](#20-stage-17--release-notes)
21. [Stage 18 — Website & Assets](#21-stage-18--website--assets)
22. [Stage 19 — QA Sign-Off](#22-stage-19--qa-sign-off)
23. [Stage 20 — Rollback Plan](#23-stage-20--rollback-plan)
24. [Stage 21 — Release Execution](#24-stage-21--release-execution)
25. [Stage 22 — Post-Release Validation](#25-stage-22--post-release-validation)
26. [Appendix A — Version Source Map](#26-appendix-a--version-source-map)
27. [Appendix B — Release Artifact Inventory](#27-appendix-b--release-artifact-inventory)
28. [Appendix C — Quick Reference Card](#28-appendix-c--quick-reference-card)

---

## 1. Release Stages Overview

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                     RELEASE PIPELINE                              │
  ├──────────────────────────────────────────────────────────────────┤
  │                                                                  │
  │  PLANNING                                                        │
  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
  │  │ Scope        │──▶│ Milestones   │──▶│ Version Bump │         │
  │  │ Definition   │   │ Confirmation │   │ Planning     │         │
  │  └──────────────┘   └──────────────┘   └──────────────┘         │
  │                                                                  │
  │  REVIEWS (parallel tracks)                                       │
  │  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐          │
  │  │Architecture│ │   Code   │ │  API     │ │    UI     │          │
  │  │  Review   │ │  Review  │ │  Review  │ │  Review   │          │
  │  └───────────┘ └──────────┘ └──────────┘ └───────────┘          │
  │  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐          │
  │  │  Memory   │ │Execution │ │ Command  │ │ Settings  │          │
  │  │  Review   │ │  Review  │ │  Center  │ │  Review   │          │
  │  └───────────┘ └──────────┘ └──────────┘ └───────────┘          │
  │                                                                  │
  │  QUALITY GATES                                                   │
  │  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐          │
  │  │Accessibility│ │  Perf   │ │ Security │ │    QA     │          │
  │  │  Review   │ │  Review  │ │  Review  │ │  Sign-off │          │
  │  └───────────┘ └──────────┘ └──────────┘ └───────────┘          │
  │                                                                  │
  │  RELEASE EXECUTION                                               │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐           │
  │  │ Packaging │ │Installers│ │ Signing  │ │ Auto-     │           │
  │  │          │ │          │ │          │ │  Update   │           │
  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘           │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                         │
  │  │  Notes   │ │ Website  │ │  Assets  │                         │
  │  └──────────┘ └──────────┘ └──────────┘                         │
  │                                                                  │
  │  POST-RELEASE                                                    │
  │  ┌──────────────┐   ┌────────────────────┐   ┌──────────────┐   │
  │  │  Deploy      │──▶│ Post-Release       │──▶│ Rollback if  │   │
  │  │              │   │ Validation (48h)   │   │ Needed       │   │
  │  └──────────────┘   └────────────────────┘   └──────────────┘   │
  │                                                                  │
  └──────────────────────────────────────────────────────────────────┘
```

### 1.1 Stage Flow Rules

| Rule | Description |
|------|-------------|
| **Parallel** | Architecture, Code, API, UI, Memory, Execution, Command Center, and Settings reviews run in parallel |
| **Sequential** | Accessibility, Performance, Security, Documentation, and QA are gated after reviews complete |
| **Blocking** | Any RED item in any stage blocks the release. YELLOW items require a documented deferral |
| **Escalation** | Items unresolved for >48h are escalated to the Engineering Lead |
| **Sign-off** | Each stage requires a named sign-off. No sign-off = no release |

### 1.2 Stage Ownership

| Stage | Owner |
|-------|-------|
| Architecture Review | Engineering Lead |
| Code Review | Engineering Lead |
| Accessibility | Frontend Lead |
| Performance | Backend Lead |
| Security | Security Lead |
| Documentation | Tech Writer / Product Manager |
| API Review | Backend Lead |
| UI Review | Frontend Lead / Product Manager |
| Memory Review | Memory System Owner |
| Execution Review | Execution Engine Owner |
| Command Center | Frontend Lead |
| Settings | Backend Lead |
| QA | QA Lead |
| Release Execution | Engineering Lead |

---

## 2. Versioning

### 2.1 Scheme

Eve OS follows **Semantic Versioning 2.0.0**:

```
MAJOR.MINOR.PATCH[-PRERELEASE[+BUILD]]
```

| Component | When to Bump | Example |
|-----------|-------------|---------|
| MAJOR | Breaking API or data format changes, EOL of older version support | `2.0.0` |
| MINOR | New features, non-breaking API additions, deprecations | `1.1.0` |
| PATCH | Bug fixes, security patches, performance improvements | `1.0.1` |
| PRERELEASE | Unstable builds, RCs, alphas | `1.1.0-rc.1` |
| BUILD | CI build metadata (optional) | `1.0.0+build.42` |

### 2.2 Pre-Release Suffixes

| Suffix | Meaning | Stability |
|--------|---------|-----------|
| `-dev` | In-development, unstable | May change without notice |
| `-alpha.N` | Feature-complete, internal QA | Breaking changes possible |
| `-beta.N` | External QA, feature freeze | Only critical fixes |
| `-rc.N` | Release candidate, final testing | Only release-blocker fixes |
| (none) | Production release | Fully stable |

### 2.3 Version Source Map

Version `1.0.0` is currently hardcoded in **7 locations**. Every release must update all of them atomically:

| # | File | Variable | Current Value |
|---|------|----------|---------------|
| 1 | `src/backend/aios/__init__.py` | `__version__` | `"1.0.0"` |
| 2 | `src/backend/aios/__main__.py` | `LAUNCHER_VERSION` | `"1.0.0"` |
| 3 | `pyproject.toml` | `project.version` | `"1.0.0"` |
| 4 | `src/frontend/package.json` | `version` | `"1.0.0"` |
| 5 | `src/backend/aios/api/app.py` | `app.create_app(version=...)` | `"1.0.0"` |
| 6 | `src/backend/aios/core/capability_registry.py` | `version` field in data model | `"1.0.0"` |
| 7 | `src/backend/aios/plugins/verifier.py` | `aios_version` default | `"1.0.0"` |

### 2.4 Version Bump Tools

Two approaches are prescribed:

**Option A — Manual (current, until tooling is added):**
```bash
# Update all 7 files listed in §2.3
# Update plugin.yaml references if plugin API changed
# Commit: "chore: bump version to X.Y.Z"
# Tag:   git tag -a vX.Y.Z -m "Release X.Y.Z"
```

**Option B — Automated (recommended, to be implemented):**
Add `bumpver` to project:
```toml
[tool.bumpver]
current_version = "1.0.0"
version_pattern = "MAJOR.MINOR.PATCH"
commit_message  = "chore: bump version {old_version} -> {new_version}"
tag_message     = "Release {new_version}"
tag_scope       = "default"
```

### 2.5 Version Consistency Check

Before every release, run:

```bash
# Python backend
python -c "from aios import __version__; print(__version__)"

# Check pyproject.toml
grep "^version" pyproject.toml

# Check package.json
node -e "console.log(require('./src/frontend/package.json').version)"

# Verify all 7 sources match
```

---

## 3. Stage 0 — Pre-Release Planning

**Owner:** Engineering Lead  
**Timing:** 2 weeks before planned release date

### 3.1 Scope Definition

```
[ ] Release type:   [ ] MAJOR  [ ] MINOR  [ ] PATCH
[ ] Target version: _______
[ ] Target date:    _______
[ ] Release captain: _______
[ ] Feature freeze date: _______
[ ] Code freeze date: _______
[ ] Release date: _______
```

### 3.2 Milestone Confirmation

```
[ ] All P0 issues resolved
[ ] All P1 issues resolved or deferred with approval
[ ] No unresolved regression bugs
[ ] Feature flags reviewed (what's on/off for this release)
[ ] Breaking changes documented
[ ] Deprecation notices issued (for removals)
[ ] Migration path documented for breaking changes
```

### 3.3 Branch Strategy

```
[ ] Release branch created: release/vX.Y.Z
[ ] Main branch is open for next-version development
[ ] Cherry-pick policy defined (only bug fixes to release branch)
[ ] Release branch protected: PR required, 2 approvals
```

---

## 4. Stage 1 — Architecture Review

**Owner:** Engineering Lead  
**Sign-off required:** Yes

### 4.1 Checklist

```
Architectural Integrity
[ ] No architectural drift from documented design (docs/01_Architecture.md)
[ ] Event Bus schema changes reviewed and backwards-compatible
[ ] No new circular dependencies introduced
[ ] Module boundaries respected (no cross-layer leaks)
[ ] Plugin API surface stable and versioned
[ ] Database migration scripts tested and reversible
[ ] Configuration schema changes documented

Data Flow
[ ] Data flow diagrams updated if flow changed
[ ] No new synchronous cross-process calls
[ ] Event contracts versioned or tolerant to unknown fields
[ ] Serialization format changes reviewed (JSON schema version bump?)

Scalability
[ ] Backend can handle projected load for this release
[ ] No single-thread bottlenecks introduced in hot paths
[ ] Memory system query patterns remain O(log n) or better
[ ] Event bus history limit respected and tested

Tech Debt
[ ] No TODO/FIXME/HACK committed without linked issue
[ ] No dead code or commented-out code in release branch
[ ] No deprecated APIs called internally

Sign-off: _________________________________  Date: _______________
```

---

## 5. Stage 2 — Code Review

**Owner:** Engineering Lead  
**Sign-off required:** Yes

### 5.1 Checklist

```
Static Analysis
[ ] ruff check passes with 0 errors (Python backend)
[ ] mypy passes with 0 errors (Python backend)
[ ] npx tsc --noEmit passes with 0 errors (TypeScript frontend)
[ ] ESLint passes with 0 errors (when configured)
[ ] No console.log, print(), pdb.set_trace() in production code
[ ] No unused imports or variables
[ ] No type: ignore or @ts-ignore without justification comment

Test Coverage
[ ] pytest passes with 0 failures (Python backend)
[ ] npm test passes with 0 failures (TypeScript frontend)
[ ] Coverage meets mandatory thresholds (§14 of Testing Strategy)
[ ] New code has corresponding tests
[ ] Integration tests pass
[ ] E2E smoke tests pass
[ ] No test.skip or it.skip in committed code
[ ] Regression test exists for every bug fix

Code Quality
[ ] No PR with >400 lines changed (review fatigue threshold)
[ ] All PRs reviewed by at least 1 code owner
[ ] All review threads resolved
[ ] No merge commits in release branch (rebase or squash)
[ ] Commit messages follow conventional commits format

Sign-off: _________________________________  Date: _______________
```

### 5.2 PR Review Thresholds

| Metric | Warning | Blocking |
|--------|---------|----------|
| Lines changed per PR | >400 | >800 |
| Open review threads | >3 unresolved | Any unresolved |
| `type: ignore` count | >5 | >15 |
| `any` type usage (TS) | >10 | >25 |
| `# TODO` count | >5 | >15 |
| Test-to-code ratio | <1:4 | <1:10 |

---

## 6. Stage 3 — Accessibility Review

**Owner:** Frontend Lead  
**Sign-off required:** Yes

### 6.1 Automated Checks

```
[ ] vitest-axe passes on all components with 0 violations
[ ] All images have alt text or role="presentation"
[ ] All form inputs have associated labels
[ ] All interactive elements are keyboard-focusable
[ ] Focus order matches visual order
[ ] ARIA roles match Design System spec (§16.2)
[ ] No duplicate ARIA roles or IDs
[ ] Colour contrast passes 4.5:1 for text, 3:1 for large text
[ ] Error messages associated via aria-describedby
[ ] Dynamic content uses aria-live regions
[ ] Modal dialogs trap focus and restore on close
[ ] Touch targets >= 44×44px

### 6.2 Manual Audit

```
[ ] Screen reader test: NVDA on Windows
[ ] Screen reader test: Narrator on Windows
[ ] Keyboard-only navigation: full application walkthrough
[ ] Colour blindness simulation: protanopia, deuteranopia, tritanopia
[ ] High contrast mode: application remains usable
[ ] 200% zoom: no content loss or overlap
[ ] Reduced motion: no jarring animations

### 6.3 WCAG 2.2 Compliance

```
[ ] Level A: 0 violations
[ ] Level AA: 0 violations
[ ] Level AAA: documented exceptions only
[ ] Accessibility statement updated (if public)

Sign-off: _________________________________  Date: _______________
```

---

## 7. Stage 4 — Performance Review

**Owner:** Backend Lead  
**Sign-off required:** Yes

### 7.1 Performance Budget

```
Metric                   Target      Measured      Pass/Fail
─────────────────────────────────────────────────────────────
Chat response (1st token)  < 2s        _______       [ ]
Tool execution             < 1s        _______       [ ]
Memory query               < 500ms     _______       [ ]
Memory search (10k entries) < 2s       _______       [ ]
UI full app render         < 1s        _______       [ ]
UI interaction response    < 100ms     _______       [ ]
Concurrent tools (10+)     no degradation  _______   [ ]
App startup                < 3s        _______       [ ]
Event bus throughput        > 1000/s    _______      [ ]
```

### 7.2 Benchmark Suite

```
[ ] pytest benchmarks run and compared to baseline
[ ] No regression > 10% without documented justification
[ ] Baseline updated in docs/performance-baselines.json
[ ] 95th percentile tracked alongside mean
[ ] Memory usage profiled (no leaks detected)
[ ] Startup time measured (cold start)

### 7.3 Regression Check

```
[ ] Benchmarks compared against last release
[ ] Any regression > 5% has a linked issue
[ ] Any regression > 10% blocks release
[ ] P0 paths specifically measured (send message, execute tool, permission grant)

Sign-off: _________________________________  Date: _______________
```

---

## 8. Stage 5 — Security Review

**Owner:** Security Lead  
**Sign-off required:** Yes

### 8.1 Automated Security

```
[ ] SAST scan passes (bandit for Python, eslint-plugin-security when configured)
[ ] Dependency scan: no critical or high CVEs
[ ] npm audit: 0 critical, 0 high
[ ] pip audit: 0 critical, 0 high
[ ] Secrets scan: no credentials committed (git leaks, .env in repo)
[ ] SQL injection probes on all query paths
[ ] Command injection probes on all tool execution paths
[ ] Path traversal probes on all file access paths
```

### 8.2 Manual Security Review

```
Permission System
[ ] Permission bypass tested: tool execution without grant
[ ] Permission escalation tested: user cannot self-elevate
[ ] Session timeout enforced correctly
[ ] Default-deny verified for all new tools

Plugin System
[ ] Plugin sandbox isolation verified
[ ] Plugin resource limits enforced (CPU, memory, time)
[ ] Plugin network access controlled
[ ] Plugin filesystem access scoped
[ ] Manifest validation rejects malformed plugins

Data Security
[ ] Database file permissions: user-only access
[ ] No secrets in logs (API keys, tokens, passwords)
[ ] Config file secrets encrypted or externalised
[ ] SQLite WAL mode: no unencrypted temp files

Network Security
[ ] API binds to 127.0.0.1 only (no remote access)
[ ] CORS configured restrictively
[ ] Rate limiting enabled and tested
[ ] Input validation on all API endpoints
[ ] Output encoding on all dynamic content

### 8.3 Threat Model Review

```
[ ] Threat model reviewed for this release's changes
[ ] New attack surfaces documented
[ ] Mitigations verified for all high-risk items
[ ] Security regression tests pass

Sign-off: _________________________________  Date: _______________
```

---

## 9. Stage 6 — Documentation Review

**Owner:** Tech Writer / Product Manager  
**Sign-off required:** Yes

### 9.1 User-Facing Documentation

```
[ ] README.md updated for new release
[ ] Installation instructions verified (fresh install)
[ ] Upgrade instructions verified (from previous version)
[ ] Configuration guide reflects all new settings
[ ] Plugin SDK documentation updated (if API changed)
[ ] Keyboard shortcut reference updated
[ ] FAQ updated for known issues / common questions
```

### 9.2 Developer Documentation

```
[ ] API documentation regenerated (if auto-generated)
[ ] Architecture diagrams up to date
[ ] Data flow diagrams up to date
[ ] Component catalog updated for new/modified components
[ ] Design system updated for new tokens/patterns
[ ] Database schema documented for any migrations
[ ] Testing strategy current
```

### 9.3 Release-Specific Docs

```
[ ] Breaking changes documented with migration guide
[ ] Deprecation notices included
[ ] Known issues and workarounds documented
[ ] CHANGELOG.md updated and accurate
[ ] RELEASE_NOTES_vX.Y.Z.md drafted

### 9.4 Documentation Quality

```
[ ] No broken links (internal or external)
[ ] Code examples tested and correct
[ ] No placeholder text ("TODO", "FIXME", "lorem ipsum")
[ ] Consistent terminology throughout
[ ] Version badge / footer correct

Sign-off: _________________________________  Date: _______________
```

---

## 10. Stage 7 — API Review

**Owner:** Backend Lead  
**Sign-off required:** Yes

### 10.1 REST API (FastAPI)

```
[ ] All endpoints documented with OpenAPI/Swagger
[ ] No breaking changes to existing endpoints
[ ] New endpoints follow RESTful conventions
[ ] Request/response schemas validated with Pydantic
[ ] Error responses follow consistent format (RFC 7807)
[ ] Pagination implemented for list endpoints
[ ] Rate limiting applied to all endpoints
[ ] Authentication/authorisation verified for protected endpoints
[ ] Deprecated endpoints return 410 Gone with migration hint
[ ] API versioning strategy maintained (v1 prefix)
```

### 10.2 Event Bus API

```
[ ] All event types documented in Event Catalog
[ ] Event schema changes backwards-compatible
[ ] New events have documentation
[ ] Event versioning strategy applied
[ ] Deprecated events have migration period
```

### 10.3 Plugin SDK API

```
[ ] Plugin manifest schema unchanged (or version bumped)
[ ] All SDK hooks stable and documented
[ ] No breaking changes to plugin API
[ ] Plugin compatibility checker updated
[ ] Example plugin updated to reflect any changes
```

### 10.4 IPC / Internal API

```
[ ] Backend ↔ Frontend IPC contracts documented in API Contracts doc
[ ] No undocumented IPC calls
[ ] Error handling consistent across all IPC channels

Sign-off: _________________________________  Date: _______________
```

---

## 11. Stage 8 — UI Review

**Owner:** Frontend Lead / Product Manager  
**Sign-off required:** Yes

### 11.1 Visual Consistency

```
[ ] All screens match the Design System (docs/06_Design_System.md)
[ ] Colour tokens used correctly (no hardcoded colours)
[ ] Typography tokens used correctly (no hardcoded font sizes)
[ ] Spacing tokens used correctly (no hardcoded margins/padding)
[ ] Dark theme verified: all screens
[ ] Light theme verified: all screens
[ ] No visual regressions from previous release
```

### 11.2 Functional Verification

```
[ ] All navigation paths work (sidebar, command palette, keyboard shortcuts)
[ ] All modals open, render correctly, and close
[ ] All tooltips appear on hover/focus
[ ] All context menus function correctly
[ ] Resize behaviour: split panes, sidebar, panels
[ ] Scroll behaviour: timelines, logs, long lists
[ ] Empty states display correctly for all views
[ ] Loading states display correctly for all async operations
[ ] Error states display correctly for all failure modes
```

### 11.3 Cross-Context Verification

```
[ ] Message → Tool execution → Result displays correctly
[ ] Permission dialog → Grant → Tool continues
[ ] Memory search → Results → Selection renders correctly
[ ] Plugin install → Enable → Use
[ ] Command palette → Execute → Feedback
[ ] Settings change → Persist → Survives restart
```

### 11.4 Visual Regression

```
[ ] Screenshots of key screens captured for comparison
[ ] No unexpected layout shifts
[ ] No overlapping elements
[ ] No truncated text or overflow
[ ] No missing icons or broken images

Sign-off: _________________________________  Date: _______________
```

---

## 12. Stage 9 — Memory Review

**Owner:** Memory System Owner  
**Sign-off required:** Yes

### 12.1 Functional

```
[ ] Memory CRUD operations: all 4 operations tested
[ ] Memory search: keyword, semantic, hybrid
[ ] Memory deduplication: duplicate prevention verified
[ ] Memory pruning: TTL enforcement, importance-based eviction
[ ] Memory import/export: format preservation
[ ] Graph queries: traversal, pathfinding, subgraph extraction
[ ] Cache eviction: LRU behaviour verified
```

### 12.2 Data Integrity

```
[ ] No data loss after 1000 concurrent writes
[ ] No data corruption after 10k sequential writes
[ ] Database WAL mode: crash recovery tested
[ ] Foreign key constraints enforced
[ ] Migration from previous version tested
[ ] Rollback from migration tested
```

### 12.3 Performance

```
[ ] Memory search < 500ms for 10k entries
[ ] Memory write < 100ms (including indexing)
[ ] Graph query < 200ms for 5k nodes
[ ] Pruning < 5s for 50k entries
```

### 12.4 UI

```
[ ] Memory workspace renders correctly (grid, list, timeline views)
[ ] Memory card shows correct data (importance, confidence, tags, timestamps)
[ ] Memory search works with keyboard navigation
[ ] Memory filters work correctly
[ ] Memory pagination works correctly
[ ] Memory inspector shows full details

Sign-off: _________________________________  Date: _______________
```

---

## 13. Stage 10 — Execution Review

**Owner:** Execution Engine Owner  
**Sign-off required:** Yes

### 13.1 State Machine

```
[ ] All valid state transitions tested
[ ] All invalid state transitions rejected
[ ] Concurrent execution: no deadlocks or races
[ ] Tool cancellation: stops within timeout
[ ] Tool timeout: enforced correctly
[ ] Error recovery: retry logic verified
[ ] Error recovery: fallback strategy verified
[ ] Execution history: complete and accurate
```

### 13.2 Tool Execution

```
[ ] All 16 tool modules work correctly
[ ] Tool dependency resolution: order preserved
[ ] Tool result aggregation: collected and returned
[ ] Tool output streaming: real-time updates
[ ] Tool permission requests: dialog appears, flow works
[ ] Tool execution with large output: no truncation or crash
```

### 13.3 Permission Flow

```
[ ] Permission request → Dialog → Grant → Continue
[ ] Permission request → Dialog → Deny → Skip
[ ] Permission request → Dialog → Timeout → Default deny
[ ] Session-level permission caching works
[ ] Permission levels enforced correctly
[ ] Admin bypass works (when configured)
```

### 13.4 Performance

```
[ ] Tool execution < 1s (50th percentile)
[ ] Tool execution < 3s (95th percentile)
[ ] Concurrent tools (10): no degradation
[ ] Execution history load < 500ms for 100 entries

Sign-off: _________________________________  Date: _______________
```

---

## 14. Stage 11 — Command Center Review

**Owner:** Frontend Lead  
**Sign-off required:** Yes

### 14.1 Command Palette

```
[ ] Opens with Ctrl+K (or configured shortcut)
[ ] Closes with Escape
[ ] Search filters results by fuzzy match
[ ] All registered commands appear
[ ] Commands categorised correctly
[ ] Keyboard navigation: up/down arrows, Enter to execute
[ ] Mouse navigation: click to execute
[ ] No commands fail silently
[ ] Command history persists across sessions
[ ] Empty state when no results match
```

### 14.2 Global Shortcuts

```
[ ] Ctrl+K: Command palette
[ ] Ctrl+, : Settings
[ ] Ctrl+P : Plugins
[ ] Ctrl+T : Tools
[ ] Ctrl+M : Voice toggle
[ ] Ctrl+I : Vision toggle
[ ] All shortcuts configurable in Settings
[ ] No shortcut conflicts
[ ] Shortcuts work when app is focused
[ ] System-level shortcuts (tray, global hotkeys) work
```

### 14.3 Activity Center

```
[ ] Activity badge shows unread count
[ ] Activity center opens with correct content
[ ] Notifications are actionable
[ ] Notification dismissal works
[ ] Notification settings respected
[ ] Activity history persists across restarts

Sign-off: _________________________________  Date: _______________
```

---

## 15. Stage 12 — Settings Review

**Owner:** Backend Lead  
**Sign-off required:** Yes

### 15.1 Configuration

```
[ ] All settings are persisted correctly
[ ] All settings survive restart
[ ] Default settings are sane (config/default.yaml)
[ ] User overrides work (config override mechanism)
[ ] Invalid settings are rejected with helpful error
[ ] Settings migration from previous version tested
[ ] Environment variable overrides work
[ ] No settings silently ignored
```

### 15.2 Settings UI

```
[ ] All settings categories render correctly
[ ] Settings changes take effect immediately (or with restart notice)
[ ] Reset to defaults works
[ ] Keyboard navigation works throughout settings
[ ] Search in settings works
[ ] Nested settings work (e.g., plugin-specific settings)
```

### 15.3 Feature Flags

```
[ ] All feature flags documented
[ ] Feature flags are toggleable without restart
[ ] Disabled features are hidden (not just greyed out)
[ ] Feature flag defaults are correct for this release

Sign-off: _________________________________  Date: _______________
```

---

## 16. Stage 13 — Packaging

**Owner:** Engineering Lead  
**Sign-off required:** Yes

### 16.1 Build Verification

```
[ ] Backend builds: python -m build passes
[ ] Frontend builds: npm run build passes
[ ] CI pipeline passes for release branch
[ ] Build artifacts are deterministic (same commit = same hash)
[ ] Build output size recorded: _______ MB
[ ] No unnecessary files in build output (source maps in prod? .git?)
```

### 16.2 Dependency Freeze

```
[ ] requirements.txt versions pinned (not ranges)
[ ] package-lock.json committed and up to date
[ ] No dependency with known CVEs
[ ] All dependencies have compatible licences
[ ] Dependency tree reviewed for unnecessary bloat
[ ] Python dependencies frozen in requirements.txt:
    - FastAPI ________
    - uvicorn ________
    - pydantic ________
    - structlog ________
    - openai ________
    - anthropic ________
    - Other key deps...
[ ] Node dependencies frozen:
    - react ________
    - vite ________
    - vitest ________
    - Other key deps...
```

### 16.3 Bundle Analysis

```
[ ] Frontend bundle analysed (vite build --report)
[ ] Largest dependencies identified and justified
[ ] Code splitting verified (chunks loaded on demand)
[ ] Total JS bundle size: _______ KB (target < 500 KB)
[ ] Total CSS bundle size: _______ KB (target < 50 KB)

Sign-off: _________________________________  Date: _______________
```

---

## 17. Stage 14 — Installers

**Owner:** Engineering Lead  
**Sign-off required:** Yes

### 17.1 Installer Build

*Note: Installer infrastructure must be built. This checklist defines the requirements.*

```
[ ] Installer build pipeline created in CI
[ ] Windows installer produced (NSIS / InnoSetup / WiX / Tauri)
[ ] Installer version matches application version
[ ] Installer signed (see Stage 15)
[ ] Installer tested on:
    [ ] Windows 10 clean install
    [ ] Windows 11 clean install
    [ ] Windows 10 upgrade from previous version
    [ ] Windows 11 upgrade from previous version
    [ ] Windows Server (if supported)
```

### 17.2 Installer Verification

```
[ ] Installer size: _______ MB (target < 100 MB)
[ ] Installation time: _______ s (target < 60s on SSD)
[ ] Install path: user-selected or default
[ ] Desktop shortcut created (if opted)
[ ] Start menu entry created
[ ] Application launches after installation
[ ] Application runs without admin privileges
[ ] Uninstaller works (clean removal)
[ ] Uninstall removes all files (except user data)
[ ] Silent install works: installer.exe /S
[ ] Silent uninstall works: uninstall.exe /S
```

### 17.3 Upgrade Testing

```
[ ] Upgrade from previous version preserves user data
[ ] Upgrade from previous version preserves settings
[ ] Upgrade from previous version preserves plugins
[ ] Upgrade from previous version preserves conversation history
[ ] Upgrade from previous version preserves memory
[ ] Rollback from upgrade is possible
[ ] Downgrade protection: warns user if installed version is newer

### 17.4 Portable Mode (if supported)

```
[ ] Portable executable runs without installation
[ ] Portable executable stores data in its own directory
[ ] Portable mode detected automatically (no config flag)

Sign-off: _________________________________  Date: _______________
```

---

## 18. Stage 15 — Signing

**Owner:** Engineering Lead  
**Sign-off required:** Yes

### 18.1 Code Signing Requirements

*Note: Signing infrastructure and certificate procurement must be completed before first production release.*

```
[ ] Code signing certificate obtained (EV or OV)
[ ] Certificate trusted by Microsoft (Windows)
[ ] Certificate expiry date: _______
[ ] Certificate stored securely (HSM or Azure Key Vault / AWS KMS)
[ ] Signing pipeline configured in CI
[ ] Signing password/key not in source control
```

### 18.2 Signing Verification

```
[ ] Executable signed: signtool verify /pa aios.exe
[ ] Installer signed: signtool verify /pa aios-setup.exe
[ ] All .dll files signed
[ ] All .exe files signed
[ ] All .msi files signed (if applicable)
[ ] Timestamp added to signature
[ ] SmartScreen check: no warnings
[ ] Antivirus check: no false positives (submit to Microsoft Defender)
```

### 18.3 Authenticode

```
[ ] SHA-256 signature (SHA-1 deprecated)
[ ] RFC 3161 timestamp (not legacy)
[ ] Cross-signing certificate for compatibility

Sign-off: _________________________________  Date: _______________
```

---

## 19. Stage 16 — Auto Update

**Owner:** Engineering Lead  
**Sign-off required:** Yes

### 19.1 Update Infrastructure

*Note: Auto-update infrastructure must be built. This checklist defines the requirements.*

```
[ ] Update server endpoint operational
[ ] Update manifest format defined
[ ] Update manifest signed
[ ] Update manifest version matches release
[ ] Update manifest includes: version, URL, hash, signature, release notes URL
[ ] Update URL configured in application

### 19.2 Update Flow

```
[ ] Update check on startup
[ ] Update check periodic (every N hours, configurable)
[ ] Manual update check (Settings → Check for Updates)
[ ] Update notification displayed to user
[ ] Update download progress shown
[ ] Update download resumable
[ ] Update hash verified after download
[ ] Update signature verified after download
[ ] Update applied on restart (or live if possible)
[ ] Rollback possible if update fails
```

### 19.3 Update Scenarios

```
[ ] Update from current version to next patch
[ ] Update from current version to next minor
[ ] Update from previous major version (if supported)
[ ] Update with custom plugins installed
[ ] Update with custom configuration
[ ] Update with slow/intermittent network
[ ] Update with insufficient disk space (graceful failure)
[ ] Update cancellation works
```

### 19.4 Update Channel Strategy

```
[ ] Stable channel: production releases only
[ ] Beta channel: release candidates
[ ] Alpha channel: nightly builds (if applicable)
[ ] User can switch channels (with appropriate warnings)

Sign-off: _________________________________  Date: _______________
```

---

## 20. Stage 17 — Release Notes

**Owner:** Product Manager  
**Sign-off required:** Yes

### 20.1 CHANGELOG.md

```
[ ] CHANGELOG.md follows Keep a Changelog format
[ ] New version entry added at top
[ ] Sections: Added, Changed, Deprecated, Removed, Fixed, Security
[ ] All PRs referenced with links
[ ] All issues referenced with links
[ ] Breaking changes clearly marked with `⚠️`
[ ] Migration instructions included for breaking changes
[ ] Contributors credited (if external)
```

### 20.2 Release Notes (User-Facing)

```
[ ] Release notes written for end users (not developers)
[ ] Title and version number
[ ] Release date
[ ] Brief summary of the release
[ ] What's new (feature list with descriptions)
[ ] What's changed (behavioural changes)
[ ] What's fixed (bug fixes relevant to users)
[ ] Breaking changes (with migration instructions)
[ ] Known issues (with workarounds)
[ ] Download links
[ ] System requirements
[ ] Upgrade instructions
[ ] Support / feedback channels
[ ] License information
```

### 20.3 Technical Release Notes

```
[ ] API changes documented
[ ] Plugin SDK changes documented
[ ] Database migration details
[ ] Configuration changes
[ ] Dependency changes (new/removed/updated)
[ ] Performance improvements quantified
[ ] Security fixes documented (with CVE if applicable)
```

### 20.4 Release Artifacts

```
[ ] Release tagged in git: vX.Y.Z
[ ] GitHub Release created
[ ] Release assets attached (installer, portable, checksums)
[ ] Release notes published to GitHub Release
[ ] Release notes published to website (if separate)
[ ] Release announced on communication channels

Sign-off: _________________________________  Date: _______________
```

---

## 21. Stage 18 — Website & Assets

**Owner:** Product Manager  
**Sign-off required:** Yes

### 21.1 Website

*Note: Website infrastructure must be built if a public website is desired.*

```
[ ] Version updated on website download page
[ ] Download links updated
[ ] System requirements updated
[ ] Screenshots updated (if UI changed)
[ ] Feature descriptions updated
[ ] FAQ updated for new release
[ ] Blog post / announcement drafted (if applicable)
[ ] Changelog linked from website
[ ] Release notes linked from website
[ ] All links tested (no 404s)
```

### 21.2 Brand Assets

```
[ ] Application icon updated (if changed)
[ ] Favicon present and correctly referenced
[ ] Taskbar icon correct
[ ] System tray icon correct
[ ] Start menu icon correct
[ ] File type associations registered (if any)
[ ] Logo assets for website/social media current
[ ] Social media cards (Open Graph, Twitter Cards) updated
```

### 21.3 Asset Inventory

| Asset | Required | Status |
|-------|----------|--------|
| App icon (.ico, multiple sizes) | ✅ | Not yet created |
| App icon (.png, 512×512) | ✅ | Not yet created |
| Favicon (.ico) | ✅ | Not yet created (`/favicon.ico` referenced in index.html) |
| System tray icon | ✅ | Not yet created |
| Taskbar icon | ✅ | Not yet created |
| Installer icon | ✅ | Not yet created |
| Logo (horizontal) | 🔲 | Not yet created |
| Logo (square) | 🔲 | Not yet created |
| Social media card | 🔲 | Not yet created |
| Screenshots (for website) | 🔲 | Not yet created |

### 21.4 Open Graph / Social

```
[ ] og:title set to "Eve OS — Release X.Y.Z"
[ ] og:description summarizes the release
[ ] og:image is the social card
[ ] og:url points to the release page
[ ] Twitter Card tags present

Sign-off: _________________________________  Date: _______________
```

---

## 22. Stage 19 — QA Sign-Off

**Owner:** QA Lead  
**Sign-off required:** Yes

### 22.1 Test Execution

```
[ ] Full unit test suite: 0 failures (_______ tests)
[ ] Full integration test suite: 0 failures (_______ tests)
[ ] Full E2E test suite: 0 failures (_______ tests)
[ ] Stress tests: 0 failures (_______ tests)
[ ] Performance benchmarks: no regression > 10%
[ ] Regression tests: 0 failures (_______ tests)
[ ] Accessibility automated tests: 0 violations (_______ tests)
[ ] Manual smoke test suite: passed (_______ scenarios)
[ ] Cross-browser tests: passed (Chromium, Firefox, Edge)
```

### 22.2 QA Verification

```
[ ] Fresh install tested
[ ] Upgrade from previous version tested
[ ] All P0 and P1 issues verified as fixed
[ ] No new P0 or P1 issues introduced
[ ] All P2 issues triaged (fix / defer / known issue)
[ ] Known issues documented with workarounds
[ ] Edge cases tested (empty data, large data, special characters, network interruption)
```

### 22.3 Test Metrics

```
Total tests:       _______
Passed:            _______
Failed:            _______
Skipped:           _______
Quarantined:       _______
Coverage (Python): _______% (target >= 80%)
Coverage (TS):     _______% (target >= 70%)
E2E pass rate:     _______% (target >= 99%)
```

### 22.4 Sign-Off Statement

```
I, _________________________________, as QA Lead for Eve OS release v_______,
confirm that all QA activities have been completed, all release-blocking issues
are resolved, and the software meets the quality bar for production release.

Signed: _________________________________  Date: _______________
```

---

## 23. Stage 20 — Rollback Plan

**Owner:** Engineering Lead  
**Sign-off required:** Yes

### 23.1 Rollback Triggers

```
Automatic rollback triggers (post-release monitoring):
[ ] Error rate > 5% increase from baseline
[ ] P0 bug reported and confirmed
[ ] Crash rate > 1%
[ ] Startup failure rate > 2%
[ ] Performance regression > 30%

Manual rollback triggers:
[ ] Security vulnerability discovered
[ ] Data corruption reported
[ ] Compliance violation identified
[ ] Customer escalation (enterprise)
```

### 23.2 Rollback Procedure

```
Rollback Type: [ ] Version rollback  [ ] Feature flag toggle

Version Rollback Steps:
[ ] 1. Identify last known good version: v_______
[ ] 2. Notify stakeholders: email / Slack
[ ] 3. Revert to previous installer: distribute previous build
[ ] 4. Database: run rollback migration (if migration was applied)
[ ] 5. Config: restore previous config (if schema changed)
[ ] 6. Verify: confirm application starts and functions
[ ] 7. Monitor: watch error rates for 24 hours
[ ] 8. Post-mortem: root cause analysis within 48 hours

Feature Flag Rollback Steps:
[ ] 1. Disable feature flag for affected feature
[ ] 2. Verify: confirm feature is disabled and application stable
[ ] 3. Monitor: watch error rates for 24 hours
[ ] 4. Fix: deploy fix in next patch release
```

### 23.3 Rollback Testing

```
[ ] Database migration rollback tested
[ ] Config schema rollback tested
[ ] Downgrade installer tested
[ ] Data preservation verified after rollback
[ ] Plugin compatibility verified after rollback
```

### 23.4 Communication Plan

```
[ ] Internal notification sent (engineering, product, support)
[ ] Support team briefed on rollback and expected user impact
[ ] External communication drafted (if customer-facing)
[ ] Post-mortem scheduled within 48 hours

Sign-off: _________________________________  Date: _______________
```

---

## 24. Stage 21 — Release Execution

**Owner:** Engineering Lead  
**Sign-off required:** Yes

### 24.1 Final Verification

```
[ ] All 22 stage sign-offs collected (or documented deferrals)
[ ] Release branch: release/vX.Y.Z exists and is up to date
[ ] All CI checks pass on release branch
[ ] Version bumped in all 7 locations (see §2.3)
[ ] CHANGELOG.md finalised
[ ] Release notes finalised
[ ] Release tagged: git tag -a vX.Y.Z -m "Release X.Y.Z"
[ ] Tag pushed: git push origin vX.Y.Z
```

### 24.2 GitHub Release

```
[ ] GitHub Release created from tag
[ ] Release title: "Eve OS vX.Y.Z"
[ ] Release description references full release notes
[ ] Installer attached (.exe / .msi)
[ ] Portable build attached (if supported)
[ ] Checksum file attached (SHA-256)
[ ] Source code archive attached (auto-generated by GitHub)
[ ] Release set as [ ] Latest  [ ] Pre-release  [ ] Draft
```

### 24.3 Distribution

```
[ ] Installer published to download server/CDN
[ ] Auto-update manifest updated
[ ] Update channel updated (stable/beta/alpha)
[ ] Version endpoint updated (if applicable)
[ ] Download page updated
```

### 24.4 Final Sign-Off

```
I, _________________________________, as Engineering Lead for Eve OS release
v_______, confirm that all stages have been completed, all blockers resolved,
and this release is approved for production distribution.

Signed: _________________________________  Date: _______________
```

---

## 25. Stage 22 — Post-Release Validation

**Owner:** Engineering Lead + QA Lead  
**Duration:** 48 hours post-release  
**Sign-off required:** Yes

### 25.1 Monitoring (First 48 Hours)

```
Hour 0-2:
[ ] Application starts successfully on clean install
[ ] Application starts successfully on upgrade
[ ] No crash reports in first hour
[ ] Error rate at or below baseline
[ ] Startup time within budget

Hour 2-24:
[ ] Error rate stable (< 5% increase from baseline)
[ ] Performance metrics within expected range
[ ] No memory leak detected (monitor over 24h)
[ ] No database corruption reported
[ ] No permission system anomalies
[ ] All E2E smoke tests pass in production environment

Hour 24-48:
[ ] Error rate confirmed stable
[ ] Performance confirmed stable
[ ] No new P0/P1 bugs reported
[ ] User feedback reviewed (if available)
```

### 25.2 Metrics Collection

```
[ ] Error rate: _______ (baseline: _______)
[ ] Crash rate: _______ (baseline: _______)
[ ] Startup time P50: _______ (target: < 3s)
[ ] Startup time P95: _______ (target: < 5s)
[ ] Active users: _______
[ ] Messages sent: _______
[ ] Tools executed: _______
[ ] Permission grants: _______
[ ] Memory queries: _______
[ ] Avg response time P50: _______ (target: < 2s)
[ ] Avg response time P95: _______ (target: < 5s)
```

### 25.3 Patch Criteria

```
Patch release triggered if:
[ ] P0 bug: fix within 24 hours
[ ] P1 security: fix within 48 hours
[ ] P1 bug with workaround: next scheduled release
[ ] P2 bug: next scheduled release

Current status: [ ] Clear  [ ] Patch needed (issue #_______)
```

### 25.4 Release Retrospective

```
[ ] Retrospective scheduled within 1 week of release
[ ] What went well documented
[ ] What went wrong documented
[ ] What to improve documented
[ ] Action items assigned
[ ] Process updated for next release

Sign-off: _________________________________  Date: _______________
```

---

## 26. Appendix A — Version Source Map

### 26.1 All Version Locations

| # | File Path | Variable / Field | Type |
|---|-----------|-----------------|------|
| 1 | `src/backend/aios/__init__.py` | `__version__` | Python module version |
| 2 | `src/backend/aios/__main__.py` | `LAUNCHER_VERSION` | CLI launcher version |
| 3 | `pyproject.toml` | `project.version` | Package metadata |
| 4 | `src/frontend/package.json` | `version` | NPM package version |
| 5 | `src/backend/aios/api/app.py` | `create_app(version=...)` | API version header |
| 6 | `src/backend/aios/core/capability_registry.py` | `Capability.version` | Capability metadata |
| 7 | `src/backend/aios/plugins/verifier.py` | `aios_version` default | Plugin compatibility |
| 8 | `plugins/hello-world/plugin.yaml` | `version`, `sdk_version`, `minimum_aios_version` | Example plugin (update if API changes) |

### 26.2 Version Bump Command

Before every release, run this to verify consistency:

```bash
Write-Host "Checking version consistency..."
$versions = @(
  (Select-String -Path "src/backend/aios/__init__.py" -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value,
  (Select-String -Path "src/backend/aios/__main__.py" -Pattern 'LAUNCHER_VERSION\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value,
  (Select-String -Path "pyproject.toml" -Pattern '^version\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value,
  (Select-String -Path "src/frontend/package.json" -Pattern '"version":\s*"([^"]+)"').Matches[0].Groups[1].Value
)

if ($versions | Select-Object -Unique | Measure-Object).Count -eq 1 {
  Write-Host "  All versions match: $($versions[0])" -ForegroundColor Green
} else {
  Write-Host "  Version MISMATCH!" -ForegroundColor Red
  $versions | ForEach-Object { Write-Host "    $_" }
}
```

---

## 27. Appendix B — Release Artifact Inventory

### 27.1 Required Artifacts

| Artifact | Format | Source |
|----------|--------|--------|
| Application installer | `.exe` (NSIS/InnoSetup) | CI build step |
| Portable application | `.zip` / 7z | CI build step |
| Checksum file | `.sha256` | Generated from artifacts |
| Release notes | Markdown / HTML | `RELEASE_NOTES_vX.Y.Z.md` |
| Changelog entry | Markdown | `CHANGELOG.md` |
| Git tag | `vX.Y.Z` | `git tag` |
| GitHub Release | — | GitHub UI / CLI |
| API documentation (OpenAPI) | JSON/YAML | Auto-generated by FastAPI |

### 27.2 Recommended Infrastructure (to be built)

| Infrastructure | Priority | Notes |
|---------------|----------|-------|
| CI release workflow | P0 | Automates build, sign, publish |
| Installer build pipeline | P0 | Produces signed `.exe` |
| Code signing certificate | P0 | EV cert for Windows |
| Update server / manifest | P1 | JSON manifest, CDN-hosted |
| Download page on website | P1 | Version listing + download links |
| Brand assets (icons, logos) | P1 | Required for professional appearance |
| Docker image | P2 | For headless/server deployment |

---

## 28. Appendix C — Quick Reference Card

### 28.1 Release Timeline

```
T - 14d:  Scope definition, milestone confirmation, branch creation
T - 7d:   Feature freeze, code freeze, start reviews (Stages 1-12)
T - 3d:   Security, Performance, and Accessibility reviews complete
T - 2d:   Documentation, API, UI reviews complete. QA begins
T - 1d:   QA sign-off. Packaging and installer build
T - 0d:   Signing, release notes finalised. Release executed
T + 48h:  Post-release validation complete. Retrospective scheduled
```

### 28.2 Blocking vs Non-Blocking

| Stage | Blocking | Can Defer |
|-------|----------|-----------|
| Architecture Review | ✅ | ❌ |
| Code Review | ✅ | ❌ |
| Accessibility | ✅ | ❌ |
| Performance | ✅ | ⚠️ (< 10% regression) |
| Security | ✅ | ❌ |
| Documentation | ⚠️ (user-facing only) | ✅ (internal docs) |
| API Review | ✅ | ❌ |
| UI Review | ✅ | ❌ |
| Memory Review | ✅ | ❌ |
| Execution Review | ✅ | ❌ |
| Command Center | ✅ | ❌ |
| Settings | ✅ | ❌ |
| Packaging | ✅ | ❌ |
| Installers | ✅ | ❌ |
| Signing | ✅ | ❌ |
| Auto Update | ✅ (first stable) | ⚠️ (subsequent releases) |
| Release Notes | ✅ | ❌ |
| Website & Assets | ⚠️ | ✅ (if no public website) |
| QA | ✅ | ❌ |
| Rollback Plan | ✅ | ❌ |
| Post-Release | ✅ | ❌ |

### 28.3 Common Failure Modes

| Failure Mode | Prevention |
|-------------|-----------|
| Version mismatch | Automated consistency check in CI |
| Forgotten migration | Integration test with old DB snapshot |
| Missing changelog entry | CI check for CHANGELOG.md modification |
| Unpinned dependency | `pip freeze` and `npm ci` in CI |
| Unreviewed PR | Branch protection requiring 2 approvals |
| Flaky test in main | Quarantine within 24 hours, tracked issue |
| Signing certificate expiry | Calendar reminder 30 days before |
| Installer not tested on clean OS | Dedicated test VM in CI matrix |
