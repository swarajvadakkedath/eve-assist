# AI Operations Center (AOC)

## Overview

The AI Operations Center (AOC) is a premium full-workspace dashboard for monitoring and controlling the entire EVE AI ecosystem. Registered as a first-class workspace alongside Chat and Activity, AOC replaces the legacy ManageProvidersPage modal experience with a dedicated, always-accessible operations hub.

AOC provides real-time visibility into provider health, model availability, routing decisions, and system performance — all in one unified interface.

---

## Architecture

### Core Components

| File | Role |
|------|------|
| `AIOperationsCenter.tsx` | Main shell with 7-tab navigation, realtime status dot, relative refresh timer, close button |
| `AioStore.ts` | Singleton pub/sub store using `useSyncExternalStore`; polling intervals (health 10s, diagnostics 15s, providers 30s, models 60s); ring-buffer activity log (200 max events) |
| `aioApi.ts` | Typed helpers over `fetchApi` for all provider/routing/health endpoints |
| `aioTypes.ts` | Full TypeScript type system for providers, models, health, routing, diagnostics, activity |

### State Management

`AioStore` is a singleton store that leverages `useSyncExternalStore` for React integration. It manages:

- **Polling orchestration**: Health (10s), diagnostics (15s), providers (30s), models (60s)
- **Delta-based snapshot detection**: Health polling detects state changes and logs activity events automatically
- **Ring-buffer activity log**: Capped at 200 events to prevent unbounded memory growth
- **Lifecycle hooks**: `start()` and `stop()` methods tied to AOC mount/unmount

### API Layer

`aioApi.ts` provides typed helper functions for all provider, routing, and health endpoints. Every call routes through the existing `fetchApi` helper, ensuring consistent auth headers, error handling, and base URL resolution.

---

## Workspace Integration

AOC is registered in `App.tsx` as workspace id `"aio"` with label "AI Operations" and icon "📊".

### Access Methods

| Method | Details |
|--------|---------|
| Top navigation | 📊 icon button in the workspace switcher |
| Keyboard shortcut | `Ctrl+Shift+A` |
| Command Palette | Search "AI Operations" |
| Custom event | `aios:open-aio` |
| Custom event | `aios:switch-workspace` with `{ workspaceId: 'aio' }` |

The legacy ManageProvidersPage modal has been removed from App.tsx. All provider management is now exclusively available through AOC.

---

## Sections

### 1. Dashboard

The Dashboard view presents 14 KPI stat cards providing at-a-glance ecosystem health:

| Metric | Description |
|--------|-------------|
| Configured Providers | Total provider instances with API keys |
| Healthy Providers | Providers passing health checks |
| Offline Providers | Providers currently unreachable |
| Total Models | Discovered + catalog models |
| Free Models | Models with `isFree: true` |
| Reasoning Models | Models with `supports_reasoning` |
| Vision Models | Models with `supports_vision` |
| Embedding Models | Models with `supports_embeddings` |
| Streaming Models | Models with `supports_streaming` |
| Avg Latency | Mean response latency across healthy providers |
| Avg Health Score | Mean health score (0-100) across providers |
| Background Workers | Active background health check and model refresh workers |
| Last Refresh | Timestamp of most recent model refresh |

### 2. Providers

Live provider cards displaying:

- **State badges**: Healthy (green), Degraded (yellow), Offline (red), Unknown (gray)
- **Metrics grid**: Latency (ms), Health Score (0-100), Success Rate (%), Model Count
- **Actions**: Test (verify API key), Refresh (re-discover models), Details (expand)
- **ProviderDetailPanel**: Expandable detail panel showing:
  - Auth status and key validation
  - Health history and uptime
  - Rate limit configuration
  - Detected capabilities
  - Available models (scrollable)
  - Feature flags and provider-specific metadata

### 3. Models

Searchable, filterable, sortable model table with:

- **Group-by-provider toggle**: Collapsible provider sections or flat table
- **11 columns**: Model, Provider, Commercial Status, Context Window, Vision, Reasoning, Tools, JSON, Embeddings, Speed, Quality
- **Search**: Free-text filter across model names and providers
- **Sort**: Click any column header to sort ascending/descending
- **Filter chips**: Quick filter by commercial status (Free, Free Tier, Credit Based, Paid)

### 4. SmartRouter

Routing intelligence visualization:

- **Commercial policy badge**: Displays current policy (FREE_ONLY, ALLOW_PAID, etc.)
- **Routing categories**: Each category shows:
  - Category name and description
  - Required capability tags
  - Assigned provider and model (resolved by SmartRouter)
- **Visual fallback graph**: Health-score ranked provider fallback chain showing:
  - Level 0: Preferred provider
  - Level 1-2: Same-provider alternates
  - Level 3-4: Free / Free-tier alternates
  - Level 5-7: Credit-based / Local / Paid (ALLOW_PAID only)
- **Routing diagnostics**: Per-provider routing decision history and failure reasons

### 5. Health Center

Real-time health monitoring with 5 recharts visualizations:

- **Latency AreaChart**: Provider latency trends over time (per-provider color coding)
- **Health Score AreaChart**: Provider health score trends
- **Success Rate AreaChart**: Request success rate trends
- **Provider Availability BarChart**: Current availability comparison across providers
- **Empty states**: Graceful display when no health data is available yet

All charts use `ResponsiveContainer` for fluid resizing and consistent dark theme styling.

### 6. Activity

Live timeline of ecosystem events:

- Health check results (pass/fail, latency)
- Model refresh completions (new models found, errors)
- Routing decisions (which provider was selected, why)
- Provider recoveries (offline → healthy transitions)
- Errors and warnings (API failures, quota exceeded)
- Rate limit events (429 responses)
- Background job lifecycle (started, completed, failed)

Events are timestamped with relative time (e.g., "2m ago") and color-coded by severity.

### 7. Settings

Configuration and status panel:

- **Commercial policy dropdown**: Persisted via API (FREE_ONLY default)
- **Health check interval**: Read-only display (default 120s)
- **Model refresh interval**: Read-only display (default 3600s)
- **Background worker status**: Active/inactive indicators for health monitor and model refresh workers
- **Last health check**: Timestamp of most recent health check run
- **Last model refresh**: Timestamp of most recent model refresh run

---

## Data Flow

```
AOC Mount → AioStore.start()
                │
                ├── Health polling (10s interval)
                │       │
                │       ├── Delta detection → Snapshot bump
                │       └── Activity event logging
                │
                ├── Diagnostics polling (15s interval)
                │
                ├── Provider polling (30s interval)
                │
                └── Model polling (60s interval)

AOC Unmount → AioStore.stop()
                │
                └── All polling intervals cleared
```

- **No wasted resources**: Polling stops completely when AOC is not the active workspace
- **Delta-based snapshots**: Health polling detects actual state changes before triggering re-renders
- **Activity logging**: State changes automatically generate activity events in the ring buffer

---

## Performance

- **recharts** for all charts (AreaChart, BarChart, ResponsiveContainer) — no charting library overhead beyond what's needed
- **CSS-based glassmorphism** dark theme via `ai-operations.css` — no runtime style computation
- **Minimal re-renders**: `useSyncExternalStore` ensures only subscribed components update; `useMemo` for all computed values
- **Ring-buffer activity log**: Hard cap at 200 events prevents unbounded memory growth
- **Lazy polling**: Each section's data is fetched independently; no unnecessary cross-section API calls

---

## File Structure

```
src/components/aio/
├── AIOperationsCenter.tsx    # Main shell with tab navigation
├── AioStore.ts              # Singleton state store (useSyncExternalStore)
├── aioApi.ts                # Typed API helpers over fetchApi
├── aioTypes.ts              # Full TypeScript type definitions
├── ai-operations.css         # Glassmorphism dark theme styles
├── DashboardView.tsx         # 14 KPI stat cards
├── StatCard.tsx              # Reusable stat card component
├── ProvidersView.tsx         # Provider card grid
├── AioProviderCard.tsx       # Individual provider card
├── ProviderDetailPanel.tsx   # Expanded provider details
├── ModelsView.tsx            # Searchable/sortable model table
├── SmartRouterView.tsx       # Routing visualization
├── FallbackGraph.tsx         # Visual fallback chain graph
├── HealthView.tsx            # Health charts (recharts)
├── ActivityView.tsx          # Activity timeline
├── FreeModelsView.tsx        # Free model catalog
├── PerformanceView.tsx       # Session performance metrics
└── AioSettingsView.tsx       # Settings and configuration
```

---

## Future Extensions

| Extension | Description |
|-----------|-------------|
| Virtualized scrolling | Large model lists via `@tanstack/react-virtual` (already installed) |
| Export functionality | CSV/JSON export for model catalog and provider configurations |
| Custom dashboard builder | Drag-and-drop KPI card layout with persistent positions |
| Alert thresholds | Configurable alerts for latency, health score, and failure count |
| Historical trend comparison | Day-over-day and week-over-week performance comparisons |
| Webhook notifications | External alerting via Slack, Discord, or custom webhooks |
| Provider cost tracking | Per-provider token cost estimation and budget limits |
| Model usage analytics | Per-model request counts, token usage, and cost breakdowns |

---

## Related Documentation

- [EVE AI Ecosystem Report](EVE_AI_ECOSYSTEM_REPORT.md) — Full v1.2.2 ecosystem documentation
- [Provider Framework](PROVIDER_FRAMEWORK.md) — Provider adapter architecture and registry
