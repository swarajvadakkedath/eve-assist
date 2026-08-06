# HERMES INSTALLATION AUDIT

Purpose: document the current Hermes installation so a second, completely independent Hermes installation can be created for development/debugging **without touching the installation used by EVE**. Investigate-only audit — no changes were made.

---

## Executive Summary

| Item | Value |
|------|-------|
| Version | v0.20.0 (2026.8.3) |
| Install method | Official PowerShell installer (`install.ps1`) |
| Executable | `C:\Users\swara\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe` |
| Data home (`HERMES_HOME`) | `C:\Users\swara\AppData\Local\hermes` |
| Config dir | `C:\Users\swara\AppData\Local\hermes\` |
| Python | 3.12.10 (uv-managed venv) |
| Role in EVE | Sole inference provider — Hermes POSTs to EVE (`127.0.0.1:8456/v1`); EVE's SmartRouter owns all provider routing |
| Profile store | None yet (`profiles/` dir + `active_profile` marker do not exist) — the install runs as the implicit `default` profile |
| Multi-profile support | **Native.** `hermes profile {list,use,create,delete,show,alias,rename,export,import,install,update,info}`; each named profile is a fully independent `HERMES_HOME` |

**Headline conclusion:** Hermes already ships a first-class, isolated multi-profile system. The cleanest way to get a second independent install is a **named profile** (independent config, `.env`, memory, sessions, skills, logs) or a **separate `HERMES_HOME` directory** for full data isolation. Neither touches EVE's default install. A fully separate *installation* (own venv/binary) is also possible by reinstalling into a different path + separate data dir.

---

## 1. Installation Inventory

### 1.1 Executable path

- Primary: `C:\Users\swara\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe`
- PATH shims (how `hermes` resolves on the command line):
  - `C:\Users\swara\AppData\Local\hermes\bin`
  - `C:\Users\swara\AppData\Local\hermes\hermes-agent\venv\Scripts`
- Package/checkout root: `C:\Users\swara\AppData\Local\hermes\hermes-agent`
  - `hermes_constants.py` — `HERMES_HOME` resolution, platform default, `set_hermes_home_override()`
  - `cli.py` / `hermes_cli\main.py` — CLI entry, profile pre-parse (`_apply_profile_override()`)
  - `hermes_cli\profiles.py` — profile subsystem (`get_profile_dir`, `get_active_profile`, `resolve_profile_env`, etc.)

### 1.2 Config / data directory (`HERMES_HOME`)

- Env var `HERMES_HOME` = `C:\Users\swara\AppData\Local\hermes` (explicitly set, user-level)
- On win32 the *platform default* home is `%LOCALAPPDATA%\hermes` — **identical**, so `HERMES_HOME` currently just confirms the default location. `C:\Users\swara\.hermes` (the POSIX-style default) does **not** exist.
- Contents: `config.yaml` (`version: 33`), `.env`, `SOUL.md`, `state.db`, `skills/`, `sessions/`, `cron/`, `logs/`, `memories/`, `hooks/`, `sandboxes/`, `pairing/`, `cache/`, `audio_cache/`, `image_cache/`, `bin/`, `hermes-agent/`.

### 1.3 Python environment

- Python 3.12.10 (managed by uv) inside `hermes-agent\venv`
- Key packages: `hermes-agent 0.20.0`, `openai 2.24.0`, `fastapi 0.133.1`, `pydantic 2.13.4`, `httpx 0.28.1`, `rich 14.3.3`, `mcp 1.28.1`, `pywin32 311` (+90 more)

---

## 2. Startup Command

Hermes is started **by the user/agent**, not by EVE (EVE does not spawn Hermes; the direction of inference calls is Hermes → EVE):

```
hermes                      # interactive chat session
hermes chat                 # explicit chat
hermes --version            # version check -> v0.20.0
hermes doctor               # diagnostics
hermes gateway run          # persistent gateway (multi-slot)
hermes -p <profile> ...     # run under a specific named profile
```

For a dev install, run the same binary but with a different profile or a different `HERMES_HOME`.

---

## 3. Environment Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `HERMES_HOME` | `C:\Users\swara\AppData\Local\hermes` | Data home. Process-level; overridden by `-p` profile resolution. |
| `HERMES_GIT_BASH_PATH` | `C:\Program Files\Git\bin\bash.exe` | Git-bash helper for tool execution. |
| `EVE_API_KEY` | set in `C:\Users\swara\AppData\Local\hermes\.env` (`eve-dev-token-xK9mP2qR7vN4wL8j`) | Auth token for the EVE endpoint; referenced from `config.yaml` as `api_key: "${EVE_API_KEY}"`. |

No `OPENAI_*`, `GOOGLE_*`, `HERMES_PROFILE`, or other provider keys are set — consistent with the invariant that **Hermes never talks to external providers directly**; it routes all inference through EVE.

### `HERMES_HOME` resolution order (from `hermes_constants.py` + `hermes_cli\main.py`)

1. Explicit `-p/--profile` flag → `resolve_profile_env(name)` → sets `HERMES_HOME` to the profile dir.
2. If no flag and `HERMES_HOME` is already set to a path whose parent dir is named `profiles` → trust it as a profile path.
3. Else check the sticky `active_profile` marker at the default hermes root; if non-default, resolve and set `HERMES_HOME`.
4. Else fall back to `HERMES_HOME` env var → platform default (`%LOCALAPPDATA%\hermes`).

There is also a context-var override API (`set_hermes_home_override()`) and a `--ignore-user-config` CLI flag for full process-scoped isolation.

---

## 4. Profile Location & Multi-Profile Support

### 4.1 Current state

- `hermes profile list` → `◆default  eve:general  stopped  —  —` (only the implicit default profile).
- No `profiles/` directory and no `active_profile` marker file exist under `HERMES_HOME`. The install is effectively the `default` profile, whose `HERMES_HOME` is the root.

### 4.2 How the profile system works

- **Default profile** (`default`) maps to `_get_default_hermes_home()` — the platform home root (`C:\Users\swara\AppData\Local\hermes`).
- **Named profiles** live at `<default_hermes_root>\profiles\<name>\` (e.g. `...\hermes\profiles\hermes-dev\`).
- Each named profile is a **fully independent `HERMES_HOME` directory** with its own `config.yaml`, `.env`, memory, sessions, skills, gateway, cron, and logs.
- Activation:
  - Sticky: `hermes profile use <name>` writes the name to `<default_hermes_root>\active_profile`; subsequent bare `hermes` runs resolve to that profile.
  - One-shot: `hermes -p <name> ...` (flag stripped before argparse; `HERMES_HOME` set for that process only).
- Creation:
  - `hermes profile create <name>` — fresh empty profile (bundled skills synced).
  - `hermes profile create <name> --clone` — copy `config.yaml`, `.env`, `SOUL.md`, and skills from the active profile.
  - `hermes profile create <name> --clone-all` — full copy of all state (excluding per-profile history).
  - `hermes profile create <name> --clone-from <src>` — source profile instead of active.
  - `--no-alias` skips wrapper-script creation; `--no-skills` skips bundled-skill sync.

### 4.3 Isolation guarantees / limits

- **Data isolated:** yes — each profile is a separate `HERMES_HOME` (config, secrets, memory, sessions, skills, logs).
- **Binary isolated:** no — all profiles share the single venv at `hermes-agent\venv`. (Full binary isolation requires a second install path + venv.)
- **Env isolated:** profile resolution swaps `HERMES_HOME` per-process; global `HERMES_HOME` stays untouched.

---

## 5. How EVE Uses This Installation

- `src/backend/aios/agent/hermes_runtime.py` implements `AgentRuntime` for Hermes, but the `hermes_agent` Python import is **gated** (`import hermes_agent` in try/except). EVE Core imports cleanly with zero Hermes dependency.
- Actual integration (per `HERMES_INTEGRATION_REPORT.md`): Hermes is EVE's **sole inference provider**. Hermes sends `POST /v1/chat/completions` → `http://127.0.0.1:8456/v1` → `EveAgentAdapter.route()/route_stream()` → EVE SmartRouter → provider adapters → external APIs. `config.yaml` uses `provider: "custom"`, `base_url: "http://127.0.0.1:8456/v1"`, `api_key: "${EVE_API_KEY}"`, `default: "eve:general"` (capability aliases `eve:general/reasoning/coding/vision/fast/free/json/tool`).
- **EVE pins no profile.** Because EVE never spawns Hermes and Hermes reads `HERMES_HOME` from the process environment, EVE is bound only to the *default* install at `C:\Users\swara\AppData\Local\hermes`. It will not be affected by adding a new named profile or a separate data home — provided the `default` profile is never deleted and the global `HERMES_HOME` env var is not changed.

---

## 6. Recommended Strategy for a Second (Dev/Debug) Install

Three options, in increasing isolation:

### Option A — Named profile (recommended: simplest, zero risk to EVE)
```
hermes profile create hermes-dev --clone-from default --no-alias
hermes -p hermes-dev        # run the dev install
```
- Creates `C:\Users\swara\AppData\Local\hermes\profiles\hermes-dev\` — its own `config.yaml`, `.env`, `SOUL.md`, memory, sessions, skills, logs.
- EVE's `default` profile is untouched. Use `-p hermes-dev` for one-shot dev sessions (recommended, avoids sticky-switch surprises). If you prefer sticky switching, always `hermes profile use default` when done.
- Same venv/binary shared — fine for config/data-level debugging.

### Option B — Separate `HERMES_HOME` directory (full data isolation)
```
mkdir C:\Users\swara\AppData\Local\hermes-dev
# launch with a process-scoped env var — do NOT set it globally:
$env:HERMES_HOME = "C:\Users\swara\AppData\Local\hermes-dev"
& "C:\Users\swara\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe"
```
- Independent data home, independent config/.env. Global `HERMES_HOME` stays `AppData\Local\hermes` for EVE.
- Still shares the venv/binary.

### Option C — Fully separate installation (max isolation, for binary-level debugging)
```
# 1) Fresh checkout + venv, e.g. C:\Users\swara\AppData\Local\hermes-dev-agent
#    (re-run the official install.ps1 with a different target path, or git clone + uv venv + uv pip install -e .)
# 2) Independent data home: $env:HERMES_HOME = "C:\Users\swara\AppData\Local\hermes-dev"
# 3) Configure config.yaml/.env for the EVE dev endpoint (base_url http://127.0.0.1:8456/v1, EVE_API_KEY)
```
- Separate binary, separate venv, separate data. Completely independent of EVE's Hermes.
- Most work; only needed if you must test Hermes-core code changes in isolation.

---

## 7. Migration Risk

| Risk | Level | Mitigation |
|------|-------|------------|
| Creating a named profile breaks EVE | None | EVE uses only the `default` profile/root; profile creation adds a sibling dir. |
| Sticky `hermes profile use` silently redirects future runs | Low | Prefer one-shot `-p <name>`; if sticky switching is used, `hermes profile use default` after dev work. Never delete `default`. |
| Changing the global `HERMES_HOME` env var | **High — do not do this** | Would redirect the real EVE install. Use process-scoped env only (Option B) or profiles (Option A). |
| Updating `hermes-agent` while a clone-profile exists | Low | Profile cloning copies files at creation time; `hermes update` skill sync is opt-in per profile (`--no-skills` disables). |

**Bottom line:** Option A (named profile via `hermes profile create hermes-dev --clone-from default`) is the lowest-effort, zero-risk path to a second independent Hermes install for development/debugging. Use `hermes -p hermes-dev` for one-shot sessions and leave the `default` profile and the global `HERMES_HOME` untouched.

---

*Audit performed against the live install; no files, configs, env vars, or profiles were modified.*
